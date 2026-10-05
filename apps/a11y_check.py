"""모든 웹앱의 접근성 자동 점검(axe-core, WCAG 2.1 A·AA). 라이트·다크 둘 다 본다.

준비: npm install axe-core@4   (또는 AXE 환경변수로 axe.min.js 위치 지정)
      따뜻함 채점기: apps/warmth-scorer 에서 python -m http.server 8765
      페르소나 실험실: apps/voice-persona 에서 streamlit run app.py --server.port 8502
실행: python apps/a11y_check.py   (Playwright 필요. Chromium 위치는 CHROMIUM 환경변수)
종료 코드: 위반·페이지 열기 실패·필수 단계 실패가 하나라도 있으면 1, 모두 깨끗하면 0.
          axe가 판정을 끝내지 못한 항목(incomplete)은 사람이 확인할 목록으로 출력하며, 종료 코드에는 넣지 않는다.
2026-10-03: 우리 코드 위반 0. 페르소나 실험실의 #MainMenu aria-expanded 1건은 Streamlit 자체 메뉴라 남음.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AXE = os.environ.get("AXE", "node_modules/axe-core/axe.min.js")

# (이름, 주소, 열고 난 뒤 차례로 거칠 상태 [(상태 이름, 누를 선택자, 그 뒤 나타나야 할 선택자)], 기다릴 ms)
PAGES = [
    ("시작 화면", (ROOT / "apps/index.html").as_uri(), [], 800),
    ("녹음 부스", (ROOT / "apps/voice-studio/index.html").as_uri(), [], 800),
    ("낭독 코치", (ROOT / "apps/reading-coach/index.html").as_uri(), [], 800),
    ("녹음 검사기 안내", (ROOT / "apps/voice-check/guide.html").as_uri(), [], 800),
    ("따뜻함 채점기", "http://127.0.0.1:8765/index.html",
     [("예시를 불러온 상태", "#load-example", None), ("채점 시작 상태", "#start-scoring", "#scoring-section:not([hidden])")], 800),
    ("페르소나 실험실", "http://127.0.0.1:8502", [], 3000),
]

# 이 점검이 열어 보지 않는 상태. 결과 끝에 항상 출력해서 '위반 0'이 '전부 검사함'으로 읽히지 않게 한다.
NOT_CHECKED = [
    "녹음 부스: 감정 세기(1~5) 선택 상태, WAV 올리기 성공·실패 결과, 테이크 목록",
    "낭독 코치: 낭독을 시작한 뒤의 결과 화면",
    "따뜻함 채점기: 점수를 매긴 뒤 화면, JSONL 내보내기, 접힌 영역을 펼친 상태",
    "페르소나 실험실: 어두운 화면, 원고를 만든 뒤 화면",
]

AXE_JS = ("async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});"
          "const m=(l)=>l.map(v=>({id:v.id,impact:v.impact,n:v.nodes.length,help:v.help,"
          "t:v.nodes.slice(0,3).map(n=>n.target.join(' ')+' | '+(n.failureSummary||'').split('\\n').slice(1,2).join(''))}));"
          "return {violations:m(r.violations),incomplete:m(r.incomplete)}}")


def main():
    from playwright.sync_api import sync_playwright

    stats = {"screens": 0, "violation_kinds": 0, "open_fail": 0, "step_fail": 0, "incomplete_kinds": 0}
    incompletes = []

    def report(label, res):
        stats["screens"] += 1
        v, inc = res["violations"], res["incomplete"]
        stats["violation_kinds"] += len(v)
        stats["incomplete_kinds"] += len(inc)
        print(f"== {label}: 위반 {len(v)}종, 확인 필요(incomplete) {len(inc)}종")
        for x in v:
            print(f"  [{x['impact']}] {x['id']} x{x['n']}: {x['help']}")
            for t in x["t"]:
                print("     ", t[:200])
        for x in inc:
            incompletes.append(label)
            print(f"  (확인 필요) {x['id']} x{x['n']}: {x['help']}")
            for t in x["t"]:
                print("     ", t[:200])

    with sync_playwright() as p:
        b = p.chromium.launch(**({"executable_path": os.environ["CHROMIUM"]} if os.environ.get("CHROMIUM") else {}))
        for name, url, steps, wait in PAGES:
            for scheme in ("light", "dark"):
                if name == "페르소나 실험실" and scheme == "dark":
                    continue  # Streamlit 어두운 화면은 아직 점검하지 않음(NOT_CHECKED에 적음)
                pg = b.new_page(viewport={"width": 1280, "height": 900}, color_scheme=scheme)
                try:
                    try:
                        pg.goto(url)
                        pg.wait_for_timeout(wait)
                    except Exception as e:
                        stats["open_fail"] += 1
                        print(f"!! {name} ({scheme}): 열기 실패 {e}")
                        continue
                    try:
                        pg.add_script_tag(path=AXE)
                        report(f"{name} ({scheme})", pg.evaluate(AXE_JS))
                    except Exception as e:
                        stats["step_fail"] += 1
                        print(f"!! {name} ({scheme}): 점검 실패 {e}")
                        continue
                    for label, click, expect in steps:
                        try:
                            pg.click(click, timeout=5000)
                            pg.wait_for_timeout(300)
                            if expect:
                                pg.wait_for_selector(expect, timeout=5000)
                            report(f"{name} · {label} ({scheme})", pg.evaluate(AXE_JS))
                        except Exception as e:
                            stats["step_fail"] += 1
                            print(f"!! {name} · {label} ({scheme}): 단계 실패 {str(e).splitlines()[0] if str(e) else e}")
                            break
                finally:
                    pg.close()
        b.close()

    fails = stats["violation_kinds"] + stats["open_fail"] + stats["step_fail"]
    print()
    print(f"검사한 화면 {stats['screens']}개 · 위반 {stats['violation_kinds']}종 · 열기 실패 {stats['open_fail']}건 · 단계 실패 {stats['step_fail']}건 · 확인 필요 {stats['incomplete_kinds']}종")
    print("검사하지 않은 상태:")
    for line in NOT_CHECKED:
        print("  -", line)
    if stats["incomplete_kinds"]:
        print("확인 필요(incomplete) 항목은 자동 판정이 끝나지 않았어요. 사람이 직접 봐야 해요.")
    print("실패" if fails else "통과", f"(실패 합계 {fails})")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
