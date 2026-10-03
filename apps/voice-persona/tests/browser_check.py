"""개발용 브라우저 검증. 앱 실행에는 Playwright가 필요하지 않습니다.

먼저 앱을 켜 둡니다:
  streamlit run app.py --server.address 127.0.0.1 --server.port 8502 --server.headless true
그다음: python tests/browser_check.py
Chromium 위치는 CHROMIUM 환경변수로 바꿀 수 있습니다(없으면 Playwright 기본값).
"""
from pathlib import Path
import json, math, os, struct, zipfile
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests/artifacts"; OUT.mkdir(exist_ok=True)
URL = os.environ.get("APP_URL", "http://127.0.0.1:8502")
# 마이크 위젯에도 숨은 <audio>가 있어서, 재생기만 센다.
PLAYER = "audio[data-testid=stAudio]"
REGRESSION = "파일 업로드가 실패했습니다. 파일은 삭제되지 않았습니다. '다시 업로드'를 눌러 주세요."


def wav24(path, pause):
    """48kHz·24bit 모노: 0.5초 무음, 1초 소리, pause초 무음, 1초 소리, 0.5초 무음 (가이드 규격 녹음 흉내)."""
    rate, parts = 48000, [(.5, 0), (1, .5), (pause, 0), (1, .5), (.5, 0)]
    frames = bytearray()
    for sec, amp in parts:
        for i in range(round(rate * sec)):
            v = int(amp * 8388607 * math.sin(2 * math.pi * 220 * i / rate))
            frames += v.to_bytes(4, "little", signed=True)[:3]
    head = b"RIFF" + struct.pack("<I", 36 + len(frames)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 3, 3, 24)
    path.write_bytes(head + b"data" + struct.pack("<I", len(frames)) + bytes(frames))


results = []
def ok(name, cond, detail=""):
    results.append(bool(cond)); print(("PASS " if cond else "FAIL ") + name + (f" — {detail}" if detail else ""))


A, B = OUT / "a-24bit.wav", OUT / "b-24bit.wav"
wav24(A, .3); wav24(B, .9)
launch = {"headless": True}
if os.environ.get("CHROMIUM"):
    launch["executable_path"] = os.environ["CHROMIUM"]

with sync_playwright() as p:
    browser = p.chromium.launch(**launch)
    page = browser.new_page(viewport={"width": 1440, "height": 1100}); errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(URL)
    source = page.get_by_role("textbox", name="읽을 안내 문장", exact=True)
    source.fill(REGRESSION); source.press("Tab")
    page.get_by_text("어려운 표현만 쉽게 (등록된 표현만 쉽게 바꾸기)", exact=True).click()
    page.get_by_role("button", name="원고 만들기 →", exact=True).click()
    page.get_by_text("파일을 올리지 못했습니다. 파일은 삭제되지 않았습니다. '다시 업로드'를 눌러 주세요.", exact=True).wait_for()
    ok("회귀 사례: 파일 업로드 실패가 계정 잠김으로 바뀌지 않음", page.get_by_text("계정이 잠겼", exact=False).count() == 0)

    page.locator("input[type=file]").nth(1).set_input_files(str(A))
    page.wait_for_function("document.querySelectorAll('audio[data-testid=stAudio]').length>=1", timeout=30000)
    page.locator("input[type=file]").nth(2).set_input_files(str(B))
    page.wait_for_function("document.querySelectorAll('audio[data-testid=stAudio]').length>=2", timeout=30000)
    page.get_by_text("쉼 중간값", exact=True).wait_for(timeout=30000)
    table = page.locator("[data-testid=stTable]").inner_text()
    ok("24bit WAV 두 개가 받아짐", page.locator(PLAYER).count() == 2)
    ok("A/B 표에 실제 쉼 값 (A 0.30초, B 0.90초)", "0.30초" in table and "0.90초" in table, table.replace("\n", " ")[:200])
    ok("B 목표는 참고 칸에만", "B 목표(참고)" in table)

    notes = page.get_by_role("textbox", name="더 잘 전달된 낭독과 그 이유", exact=True)
    notes.fill("B는 두 문장 사이 쉼이 더 길어 다음 행동이 잘 들렸습니다."); notes.press("Tab")
    page.wait_for_timeout(1500)
    with page.expect_download() as dl:
        page.get_by_role("button", name="작업 전체 저장", exact=True).click()
    backup = OUT / "workshop.json"; dl.value.save_as(backup)
    data = json.loads(backup.read_text())
    ok("작업 JSON에 녹음 2개와 메모", len(data["audio"]) == 2 and data["notes"].startswith("B는"))
    with page.expect_download() as dl:
        page.get_by_role("button", name="녹음과 원고 묶음 받기 (ZIP)", exact=True).click()
    dl.value.save_as(OUT / "comparison.zip")
    with zipfile.ZipFile(OUT / "comparison.zip") as z:
        ok("ZIP 안의 A 녹음이 원본과 같음", z.testzip() is None and z.read("persona-A.wav") == A.read_bytes())

    source.fill("내용이 변경됐습니다."); source.press("Tab")
    page.get_by_text("입력이 바뀌었습니다.", exact=False).wait_for()
    ok("입력이 바뀌면 이전 녹음을 숨김", page.locator(PLAYER).count() == 0)

    fresh = browser.new_page(viewport={"width": 390, "height": 844})
    fresh.on("pageerror", lambda e: errors.append(str(e)))
    fresh.goto(URL)
    fresh.get_by_text("저장해 둔 작업 불러오기", exact=True).click()
    fresh.locator("input[type=file]").first.set_input_files(str(backup))
    fresh.get_by_text("지금 화면의 내용을 불러온 작업으로 바꿉니다", exact=True).click()
    fresh.get_by_role("button", name="불러오기", exact=True).click()
    fresh.wait_for_function("document.querySelectorAll('audio[data-testid=stAudio]').length>=2", timeout=30000)
    expect(fresh.get_by_role("textbox", name="더 잘 전달된 낭독과 그 이유", exact=True)).to_have_value("B는 두 문장 사이 쉼이 더 길어 다음 행동이 잘 들렸습니다.")
    ok("새 세션에서 원문·녹음·메모 복원", True)
    ok("휴대폰 폭 390px 가로 넘침 없음", fresh.evaluate("document.documentElement.scrollWidth<=innerWidth"))
    ok("사이드바 없음", fresh.locator("[data-testid=stSidebar]").count() == 0)
    small = fresh.evaluate("[...document.querySelectorAll('[data-testid=stMain] button')].filter(b=>b.getBoundingClientRect().width>0&&b.getBoundingClientRect().height<48).length")
    ok("본문 버튼 높이 48px 이상", small == 0, f"작은 버튼 {small}개")
    fresh.screenshot(path=str(OUT / "mobile.png"), full_page=True)

    data["result"]["text"] = "계정이 잠겼습니다."
    bad = OUT / "bad.json"; bad.write_text(json.dumps(data, ensure_ascii=False))
    fresh.locator("input[type=file]").first.set_input_files(str(bad))
    fresh.get_by_role("button", name="불러오기", exact=True).click()
    fresh.get_by_text("저장된 변환 기록이 원문·등록 규칙과 일치하지 않습니다.", exact=True).wait_for()
    ok("변조된 백업 거부, 기존 녹음 유지", fresh.locator(PLAYER).count() == 2)
    ok("페이지 자바스크립트 오류 없음", not errors, "; ".join(errors))
    browser.close()

fail = results.count(False)
print(f"\n{'실패 ' + str(fail) + '건' if fail else '전부 통과'} ({len(results)}건)")
raise SystemExit(1 if fail else 0)
