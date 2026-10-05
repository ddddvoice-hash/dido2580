# 평가 묶음 단서 검사: 답변 겉모양(물음표·길이 순위 등) 하나만으로 "높음" 답변을 골라낼 수 있는지 잰다.
# 평가자가 글을 읽지 않고 겉모양으로 점수를 짐작하면 일치도가 부풀기 때문이다(R13).
# 실행: 저장소 맨 위에서 python docs/eval/packs/cue_check.py [--strict]
# --strict: 단서 하나가 "높음"을 문항의 80% 넘게 맞히면 실패(종료 코드 1).
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIMIT = 0.8

FEATURES = {
    "물음표가 있음": lambda t: "?" in t,
    "물음표로 끝남": lambda t: t.strip().endswith("?"),
    "느낌표가 있음": lambda t: "!" in t,
    "숫자가 있음": lambda t: bool(re.search(r"\d", t)),
    "'원하시면'이 있음": lambda t: "원하시면" in t,
    "'~세요' 권유가 있음": lambda t: bool(re.search(r"(하세요|보세요|주세요)", t)),
}

def check(name):
    pack = json.loads((HERE / f"{name}.json").read_text(encoding="utf-8"))
    key = {i["id"]: i for i in json.loads((HERE / f"{name}.key.json").read_text(encoding="utf-8"))["items"]}
    rows, worst = [], 0.0
    three = [it for it in pack["items"] if len(it["answers"]) >= 3]
    # 길이 순위: 가장 긴 답이 높음인 문항 비율
    hit = sum(1 for it in three
              if key[it["id"]]["answers"][max(range(len(it["answers"])), key=lambda i: len(it["answers"][i]["text"]))]["kind"] == "high")
    rows.append(("가장 긴 답", hit, len(three)))
    for fname, f in FEATURES.items():
        hit = n = 0
        for it in three:
            kinds = [a["kind"] for a in key[it["id"]]["answers"]]
            marks = [f(a["text"]) for a in it["answers"]]
            if sum(marks) != 1:  # 단서가 한 답에만 있을 때만 그 답을 "골라낸" 것으로 센다
                continue
            n += 1
            hit += kinds[marks.index(True)] == "high"
        rows.append((fname + "(한 답에만)", hit, len(three)))
    print(f"[{name}] 3답 문항 {len(three)}개, 우연히 맞힐 비율 1/3")
    for label, hit, total in rows:
        rate = hit / total if total else 0
        worst = max(worst, rate)
        flag = "  ← 단서 의심" if rate > LIMIT else ""
        print(f"  {label}: 높음을 {hit}/{total} 문항에서 골라냄{flag}")
    return worst

names = sorted(p.stem for p in HERE.glob("*.json") if not p.stem.endswith(".key") and (HERE / f"{p.stem}.key.json").exists())
worst = max(check(n) for n in names)
if "--strict" in sys.argv and worst > LIMIT:
    sys.exit(1)
