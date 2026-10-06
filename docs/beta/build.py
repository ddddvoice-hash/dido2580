"""베타테스트 판 만들기 (성우 김디도 따뜻함 채점 베타).

    python docs/beta/build.py          # index.html 다시 만들기
    python docs/beta/build.py --check  # 저장된 index.html이 원본과 같은지 확인(CI)

기준표(apps/warmth-scorer/rubric.json)와 조정용 묶음(docs/eval/packs/calibration-v0.json)을
template.html에 넣어요. 답 열쇠(*.key.json)는 절대 넣지 않아요.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = ROOT / "docs" / "beta"
VERSION = "v0.1"
CRISIS_NOTICE = ("이번 채점에는 자살 위기와 관련된 상황과 답변이 들어 있어요. 본문을 열기 전에 위기 문항 전체나 하나만 "
                 "건너뛸 수 있고, 읽다가도 언제든 쉬거나 그만두거나 일반 문항으로 바꿀 수 있어요. 이유나 개인 경험은 "
                 "말하지 않아도 돼요. 건너뛰면 0점이 아니라 '평가하지 않음'으로 남고, 쉬거나 그만둬도 불이익이 없어요.")


def build():
    rubric = json.loads((ROOT / "apps/warmth-scorer/rubric.json").read_text(encoding="utf-8"))
    pack = json.loads((ROOT / "docs/eval/packs/calibration-v0.json").read_text(encoding="utf-8"))
    data = {
        "version": VERSION,
        "crisisNotice": CRISIS_NOTICE,
        "rubric": {k: rubric[k] for k in ("name", "version", "criteria", "penalties", "scoring")},
        "pack": {"pack": pack["pack"], "items": [
            {k: it[k] for k in ("id", "situation", "context", "source", "answers") if k in it}
            | ({"sensitive": True} if it.get("sensitive") else {})
            for it in pack["items"]]},
    }
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = (HERE / "template.html").read_text(encoding="utf-8").replace("/*__DATA__*/null", blob, 1)
    assert "/*__DATA__*/" not in html
    # 안전장치: 답 열쇠의 낱말이 들어가면 안 됨
    for bad in ("intended", "intent_score", "key.json"):
        assert bad not in html, bad
    # 넣은 데이터가 원본과 같은지
    got = json.loads(re.search(r"var DATA = (\{.*?\});\n", html, re.S).group(1).replace("<\\/", "</"))
    assert got["rubric"]["criteria"] == rubric["criteria"] and got["rubric"]["penalties"] == rubric["penalties"]
    assert [i["answers"] for i in got["pack"]["items"]] == [i["answers"] for i in pack["items"]]
    return html


def main(argv):
    html = build()
    out = HERE / "index.html"
    if len(argv) > 1 and argv[1] == "--check":
        if out.read_text(encoding="utf-8") != html:
            print("index.html이 원본과 달라요. python docs/beta/build.py 로 다시 만들어 주세요.")
            return 1
        print("통과: 베타 index.html이 기준표·조정용 묶음과 같아요")
        return 0
    out.write_text(html, encoding="utf-8")
    n = sum(len(i["answers"]) for i in json.loads((ROOT / "docs/eval/packs/calibration-v0.json").read_text(encoding="utf-8"))["items"])
    print(f"만들었어요: {out} (답변 {n}개, {len(html) // 1024}KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
