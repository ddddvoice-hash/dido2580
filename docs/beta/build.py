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
VERSION = "v0.2"
CRISIS_NOTICE = ("이번 채점에는 자살 위기와 관련된 상황과 답변이 들어 있어요. 본문을 열기 전에 위기 문항 전체나 하나만 "
                 "건너뛸 수 있고, 읽다가도 언제든 쉬거나 그만두거나 일반 문항으로 바꿀 수 있어요. 이유나 개인 경험은 "
                 "말하지 않아도 돼요. 건너뛰면 0점이 아니라 '평가하지 않음'으로 남고, 쉬거나 그만둬도 불이익이 없어요. "
                 "지금 읽기, 건너뛰기, 오늘은 마치기 중에 골라 주세요.")


# 허용 필드 목록(화이트리스트): 페이지에 들어가는 필드는 여기 있는 것뿐이에요.
# 원본에 목록 밖 필드(답 열쇠의 kind·intended_*·rationale 같은 것)가 보이면 만들지 않고 멈춰요.
RUBRIC_KEYS = ("name", "version", "criteria", "penalties", "scoring")
CRITERION_KEYS = ("id", "name", "question", "levels")
PENALTY_KEYS = ("id", "name", "effect", "example", "why")
ITEM_SOURCE_KEYS = {"id", "scenario_id", "situation", "context", "source", "answers", "sensitive"}  # 원본에서 받아들이는 필드
ITEM_OUT_KEYS = ("id", "situation", "context", "source", "answers", "sensitive")                   # 페이지로 나가는 필드
ANSWER_SOURCE_KEYS = {"text"}
PACK_OUT_KEYS = {"pack", "items"}
DATA_KEYS = {"version", "crisisNotice", "rubric", "pack"}


def pick(src, keys, where):
    missing = [k for k in keys if k not in src]
    if missing:
        raise SystemExit(f"{where}: 필요한 필드가 없어요 {missing}")
    return {k: src[k] for k in keys}


def build_data(rubric, pack):
    items = []
    for it in pack["items"]:
        extra = set(it) - ITEM_SOURCE_KEYS
        if extra:
            raise SystemExit(f"묶음 문항 {it.get('id')}에 허용하지 않은 필드가 있어요: {sorted(extra)}")
        answers = []
        for a in it["answers"]:
            extra = set(a) - ANSWER_SOURCE_KEYS
            if extra:
                raise SystemExit(f"묶음 문항 {it.get('id')}의 답변에 허용하지 않은 필드가 있어요: {sorted(extra)}")
            answers.append({"text": a["text"]})  # 답변은 {text}만 명시적으로 만듦
        out = pick({**it, "answers": answers}, ("id", "situation", "context", "source", "answers"), it.get("id"))
        if it.get("sensitive"):
            out["sensitive"] = True
        items.append(out)
    return {
        "version": VERSION,
        "crisisNotice": CRISIS_NOTICE,
        "rubric": {
            **{k: rubric[k] for k in ("name", "version", "scoring")},
            "criteria": [pick(c, CRITERION_KEYS, "기준") for c in rubric["criteria"]],
            "penalties": [pick(p, PENALTY_KEYS, "감점") for p in rubric["penalties"]],
        },
        "pack": {"pack": pack["pack"], "items": items},
    }


def check_data(data):
    """만든 데이터에 허용 필드 밖의 것이 없는지 다시 확인(어떻게 만들었든 마지막에 한 번 더)."""
    assert set(data) == DATA_KEYS, set(data) ^ DATA_KEYS
    assert set(data["pack"]) == PACK_OUT_KEYS
    assert set(data["rubric"]) == {"name", "version", "scoring", "criteria", "penalties"}
    for c in data["rubric"]["criteria"]:
        assert set(c) == set(CRITERION_KEYS), set(c)
    for p in data["rubric"]["penalties"]:
        assert set(p) == set(PENALTY_KEYS), set(p)
    for it in data["pack"]["items"]:
        assert set(it) <= set(ITEM_OUT_KEYS), set(it) - set(ITEM_OUT_KEYS)
        for a in it["answers"]:
            assert set(a) == {"text"}, set(a)


def build():
    rubric = json.loads((ROOT / "apps/warmth-scorer/rubric.json").read_text(encoding="utf-8"))
    pack = json.loads((ROOT / "docs/eval/packs/calibration-v0.json").read_text(encoding="utf-8"))
    data = build_data(rubric, pack)
    check_data(data)
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = (HERE / "template.html").read_text(encoding="utf-8").replace("/*__DATA__*/null", blob, 1)
    assert "/*__DATA__*/" not in html
    # 보조 안전장치: 답 열쇠의 낱말·표식이 들어가면 안 됨(주 방어는 위의 허용 필드 목록)
    for bad in ("intended", "intent_score", "key.json", "rationale", "\"kind\""):
        assert bad not in html, bad
    # 넣은 데이터가 원본과 같은지
    got = json.loads(re.search(r"var DATA = (\{.*?\});\n", html, re.S).group(1).replace("<\\/", "</"))
    check_data(got)
    assert got["rubric"]["criteria"] == data["rubric"]["criteria"] and got["rubric"]["penalties"] == data["rubric"]["penalties"]
    assert [i["answers"] for i in got["pack"]["items"]] == [[{"text": a["text"]} for a in i["answers"]] for i in pack["items"]]
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
