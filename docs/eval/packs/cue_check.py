# 평가 묶음 단서 검사: 답변 겉모양(물음표 개수·첫 문장 길이 등) 하나만으로 높음·낮음·경계 답을 골라낼 수 있는지 잰다.
# 평가자가 글을 읽지 않고 겉모양으로 점수를 짐작하면 일치도가 부풀기 때문이다(R13·R14).
# 실행: 저장소 맨 위에서 python docs/eval/packs/cue_check.py [--strict]
# 선택 규칙(R14-20): 수치 단서는 최댓값(또는 최솟값)이 문항에서 유일할 때만 그 답을 고른다. 동률이면 고르지 않는다.
#   이진 단서(있음/없음)도 해당하는 답이 문항에서 딱 하나일 때만 고른다.
# 단서마다 높음·낮음·경계 세 가지 종류를 모두 검사한다(R14-16). 이진 단서는 있음·없음 양쪽을 검사한다(R14-13).
# 출력: 전체 적중 h/N · 선택 범위 s/N · 선택 시 정확도 h/s (N=3답 문항 수).
# 주의: 80%는 운영상 임시 경고선이고, 통과가 단서 없음을 증명하지 않는다(R14-19·21).
#   검사한 단서는 정답표를 본 뒤 고른 것이라 많이 살필수록 우연히 맞는 규칙도 늘고, 새 문항에서 같다고 보장하지 못한다(R14-18).
# --strict: 어떤 단서든 전체 적중이 문항의 80%를 넘으면 종료 코드 1.
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIMIT = 0.8  # 임시 경고선
KINDS = ["high", "low", "borderline"]
KO = {"high": "높음", "low": "낮음", "borderline": "경계"}

def sents(t):
    return [s.strip() for s in re.split(r"[.!?]+", t) if s.strip()]

def first(t):
    return sents(t)[0] if sents(t) else ""

def cnt(words, t):
    return sum(t.count(w) for w in words.split("/"))

# 수치 단서: (이름, 함수). 최댓값·최솟값 양쪽 검사.
NUMERIC = {
    "전체 길이": lambda t: len(t),
    "첫 문장 길이": lambda t: len(first(t)),
    "첫 문장 어절 수": lambda t: len(first(t).split()),
    "물음표 개수": lambda t: t.count("?"),
    "느낌표 개수": lambda t: t.count("!"),
    "질문·제안 어미('실래요·볼까요·드릴까요·어떨까요') 횟수": lambda t: cnt("실래요/볼까요/드릴까요/어떨까요", t),
    "쉼표 수": lambda t: t.count(","),
    "문장 수": lambda t: len(sents(t)),
    "'겠어요' 횟수": lambda t: t.count("겠어요"),
    "'군요·겠어요' 합계": lambda t: cnt("군요/겠어요", t),
    "'권유(하세요·보세요·주세요)' 횟수": lambda t: cnt("하세요/보세요/주세요", t),
    "공감 낱말 수": lambda t: cnt("허전/아쉬/힘드/힘든/힘들/서운/당황/무서/걱정/무거/불편/답답/위로/불안/속상/막막", t),
    "숫자 묶음 수": lambda t: len(re.findall(r"\d+", t)),
    "'본인' 횟수": lambda t: t.count("본인"),
    "(첫 문장이 '군요'로 끝남, 첫 문장 길이) 조합": lambda t: (first(t).endswith("군요"), len(first(t))),
}

# 이진 단서: 있음·없음 양쪽 검사.
BINARY = {
    "물음표가 있음": lambda t: "?" in t,
    "물음표로 끝남": lambda t: t.strip().endswith("?"),
    "첫 문장이 질문": lambda t: bool(re.match(r"^[^.!?]*\?", t)),
    "느낌표가 있음": lambda t: "!" in t,
    "숫자가 있음": lambda t: bool(re.search(r"\d", t)),
    "'원하시면'이 있음": lambda t: "원하시면" in t,
    "'~세요' 권유가 있음": lambda t: bool(re.search(r"(하세요|보세요|주세요)", t)),
    "첫 문장이 '군요'로 끝남": lambda t: first(t).endswith("군요"),
    "첫 문장이 '겠어요'로 끝남": lambda t: first(t).endswith("겠어요"),
    "첫 문장이 2어절 이하": lambda t: len(first(t).split()) <= 2,
    "마지막이 '도 돼요'": lambda t: bool(re.search(r"도 돼요[.!?]*$", t.strip())),
    "마지막이 '겠어요'": lambda t: bool(re.search(r"겠어요[.!?]*$", t.strip())),
    "직접 호칭(당신·그대·여러분·고객님·사용자님·선생님)이 있음": lambda t: cnt("당신/그대/여러분/고객님/사용자님/선생님", t) > 0,
    "사과('죄송·미안·사과')가 있음": lambda t: cnt("죄송/미안/사과", t) > 0,
    "기관 표현(병원·의료진·의사·상담전화·센터·기관·접수처)이 있음": lambda t: cnt("병원/의료진/의사/상담전화/센터/기관/접수처", t) > 0,
}

def load(name):
    pack = json.loads((HERE / f"{name}.json").read_text(encoding="utf-8"))
    key = {i["id"]: i for i in json.loads((HERE / f"{name}.key.json").read_text(encoding="utf-8"))["items"]}
    # 묶음·열쇠 정합성(R14-20)
    assert set(key) == {i["id"] for i in pack["items"]}, "묶음과 열쇠의 문항 id가 달라요"
    for it in pack["items"]:
        k = key[it["id"]]
        assert len(it["answers"]) == len(k["answers"]), (it["id"], "답 개수가 열쇠와 달라요")
        assert [a["letter"] for a in k["answers"]] == list("ABC"[:len(it["answers"])]), (it["id"], "열쇠 글자 순서")
        kinds = [a["kind"] for a in k["answers"]]
        if len(kinds) == 3:
            assert sorted(kinds) == ["borderline", "high", "low"], (it["id"], kinds)
        else:
            assert kinds == ["high"], (it["id"], kinds)
    three = [(it, [a["kind"] for a in key[it["id"]]["answers"]]) for it in pack["items"] if len(it["answers"]) == 3]
    return three

def select(values, mode):
    """값 목록에서 유일한 최댓값/최솟값의 위치. 동률이면 None."""
    best = max(values) if mode == "max" else min(values)
    return values.index(best) if values.count(best) == 1 else None

def evaluate(three, picker, kind):
    hit = sel = 0
    for it, kinds in three:
        idx = picker([a["text"] for a in it["answers"]])
        if idx is None:
            continue
        sel += 1
        hit += kinds[idx] == kind
    return hit, sel

def rows_for(three):
    rows = []
    for label, f in NUMERIC.items():
        for mode, mlabel in (("max", "가장 큰"), ("min", "가장 작은")):
            picker = lambda texts, f=f, mode=mode: select([f(t) for t in texts], mode)
            for kind in KINDS:
                rows.append((f"{label} {mlabel} 답 → {KO[kind]}", *evaluate(three, picker, kind)))
    for label, f in BINARY.items():
        for want, wlabel in ((True, "있는"), (False, "없는")):
            def picker(texts, f=f, want=want):
                m = [i for i, t in enumerate(texts) if bool(f(t)) == want]
                return m[0] if len(m) == 1 else None
            for kind in KINDS:
                rows.append((f"{label} · {wlabel} 답이 하나뿐 → {KO[kind]}", *evaluate(three, picker, kind)))
    return rows

def check(name):
    three = load(name)
    n = len(three)
    rows = rows_for(three)
    print(f"[{name}] 3답 문항 {n}개, 문항마다 답이 3개라 우연히 맞힐 비율 1/3 (문항의 실제 답 수 기준)")
    print(f"  경고선 {LIMIT:.0%}는 임시이고, 통과가 단서 없음을 증명하지 않아요.")
    ranked = sorted(rows, key=lambda r: (-r[1], -(r[1] / r[2] if r[2] else 0)))
    worst = max(r[1] for r in rows) / n if n else 0
    shown = [r for r in ranked if r[1] / n > LIMIT] + [r for r in ranked if r[1] / n <= LIMIT][:10]
    for label, hit, sel in shown:
        acc = f"{hit}/{sel}" if sel else "-"
        flag = "  ← 단서 의심" if hit / n > LIMIT else ""
        print(f"  {label}: 전체 적중 {hit}/{n} · 선택 범위 {sel}/{n} · 선택 시 정확도 {acc}{flag}")
    print(f"  (검사한 단서·방향·종류 조합 {len(rows)}개 중 위 {len(shown)}개만 보여 줘요. 가장 높은 전체 적중 {max(r[1] for r in rows)}/{n})")
    return worst

names = sorted(p.stem for p in HERE.glob("*.json") if not p.stem.endswith(".key") and (HERE / f"{p.stem}.key.json").exists())
assert names, "묶음 파일이 없어요"
worst = max(check(n) for n in names)
if "--strict" in sys.argv and worst > LIMIT:
    sys.exit(1)
