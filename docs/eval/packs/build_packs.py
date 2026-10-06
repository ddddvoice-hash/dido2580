# 평가 묶음 만들기: 저장소 맨 위에서 python docs/eval/packs/build_packs.py
# - calibration-v0.json: 조정용 10문항. 따뜻함 채점기의 "평가 묶음 열기"로 연다. 의도한 점수는 넣지 않는다.
# - calibration-v0.key.json: 답변별 작성 의도(높음·낮음·경계)와 의도 점수. 채점이 모두 끝날 때까지 열지 않는다.
# - final-v0-plan.md: 최종 20문항 목록과 고른 이유(답변은 아직 일부만 있음).
# 문항 선택은 채점 전에 고정한다(R8-11). 답변 순서는 고정 시드로 섞는다(R8-12).
import json
import random
from pathlib import Path

NL = chr(10)  # 파일은 어느 운영체제에서도 LF로 쓴다(결과가 바이트까지 같아야 함)
ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
scen = {i["id"]: i for i in json.loads((ROOT / "docs/eval/scenarios-v0.json").read_text(encoding="utf-8"))["items"]}
# 답변 출처 파일. 나중에 G9 같은 파일을 여기에 더해 아래 PICKS의 출처를 바꿔 끼울 수 있다(G2·G7·G8·G9).
SOURCES = {
    "G2": "docs/gpt/G2-answers.json",
    "G7": "docs/gpt/G7-answers.json",
    "G8": "docs/gpt/G8-answers.json",
    "G9": "docs/gpt/G9-answers.json",
}
answers_by_source = {k: json.loads((ROOT / v).read_text(encoding="utf-8"))["items"] for k, v in SOURCES.items()}

# 조정용 답변 후보 표(R13-03): 문항마다 (출처 파일, 그 파일 items 안 순번(0부터)). 채점 전에 고정한다.
# 다른 답으로 바꾸려면 이 표만 고친다. 종류(높음·낮음·경계)는 아래에서 원본과 맞는지 확인한다.
PICKS = {
    "s01": [("G9", 0), ("G9", 1), ("G9", 2)],
    "s08": [("G9", 3), ("G9", 4), ("G9", 5)],
    "s10": [("G9", 6), ("G9", 7), ("G9", 8)],
    "s18": [("G9", 9), ("G9", 10), ("G9", 11)],
    "s25": [("G9", 12), ("G9", 13), ("G9", 14)],
    "s26": [("G9", 15), ("G9", 16), ("G9", 17)],
    "s28": [("G2", 30)],
    "s38": [("G9", 18), ("G9", 19), ("G9", 20)],
    "s48": [("G9", 21), ("G9", 22), ("G9", 23)],
    "s59": [("G9", 24), ("G9", 25), ("G9", 26)],
}

# 조정용 10: 위기 문항 s28은 G2의 안전한 답변 1개 그대로, 나머지 9문항은 G9 답변 3개씩(높음·낮음·경계).
CALIBRATION = {
    "s01": "외로움을 알아주되 의존을 부르지 않는 경계",
    "s08": "작은 아쉬움에 과하게 공감하지 않는 경계(과공감)",
    "s10": "장담하지 않는 위로의 경계(거짓 위로)",
    "s18": "조직 사정을 단정하지 않기",
    "s25": "두려움과 정보 사이의 절제",
    "s26": "죄책감을 단정하지 않기",
    "s28": "안전 확인과 사람 연결(안전한 답변 1개만)",
    "s38": "말하는 방식을 고치라고 하지 않기",
    "s48": "소외감과 쉬운 말",
    "s59": "반복 요구 없이 다음 단계 하나",
}
# 최종 20: 조정용과 겹치지 않음. 7갈래와 위험 3단계 모두, 위기 갈래는 2개까지.
FINAL = {
    "s02": "작은 상실을 가볍게 넘기지 않기", "s05": "기쁜 일 반기기(공감 과잉 경계)", "s07": "상실, 재촉하지 않기",
    "s12": "관계 결정은 본인 몫", "s14": "평가 한마디의 상처", "s17": "청소년, 절망이 커지면 안전 확인",
    "s19": "재검이 곧 암은 아니라는 정확성", "s21": "흔한 건망증과 구분, 정확한 기관 안내", "s24": "비용과 통증",
    "s30": "안전한 답변만", "s35": "고령 외로움 속 죽음 언급",
    "s36": "불편을 사용자 탓으로 돌리지 않기", "s39": "아는 것과 모르는 것 구분", "s41": "\"다들\"을 단정하지 않기",
    "s45": "한 단계씩 안내하고 따라왔는지 확인", "s47": "한 단계씩", "s49": "대신 해 줄 수 있는 범위를 정확히",
    "s53": "반복 연락의 불편 먼저 인정", "s54": "사람 연결 요청 존중", "s58": "피해와 절박함",
}
assert not set(CALIBRATION) & set(FINAL)
for sid in list(CALIBRATION) + list(FINAL):
    assert sid in scen, sid

def why(sid, note):
    # 갈래·위험 수준은 원본 문항에서 가져와 손으로 적은 값과 어긋나지 않게 한다
    base = f"{scen[sid]['group']} · {scen[sid]['risk']}"
    return base + (f" · {note}" if note else "")

by_sid = {}  # 최종 계획용: 출처별로 문항마다 가진 답변 종류
for src, lst in answers_by_source.items():
    for a in lst:
        by_sid.setdefault(a["scenario_id"], {}).setdefault(src, []).append(a["kind"])
for _sid, _srcs in by_sid.items():  # G8 답변이 있는 문항은 G8만 쓴다(최종 계획의 s02·s12 등)
    if "G8" in _srcs:
        by_sid[_sid] = {"G8": _srcs["G8"]}

assert set(PICKS) == set(CALIBRATION)
chosen_all = []
for sid in CALIBRATION:
    row = []
    for src, idx in PICKS[sid]:
        a = answers_by_source[src][idx]
        assert a["scenario_id"] == sid, (sid, src, idx)
        row.append((src, idx, a))
    kinds = [a["kind"] for _, _, a in row]
    if scen[sid]["risk"] == "위기":
        assert kinds == ["high"], (sid, kinds)  # 위기 수준은 안전한 답변 1개만
    else:
        assert sorted(kinds) == ["borderline", "high", "low"], (sid, kinds)
    chosen_all.append(row)

# 고정 시드로 순서를 섞되(R8-12), 3답 문항에서 high 위치가 A·B·C에 고르게(횟수 차이 1 이하)이고
# 이웃한 두 문항의 종류 순서가 같지 않은 배치를 찾는다(R13-05). 같은 시드면 같은 배치가 나온다.
SEED = 20261005
rng = random.Random(SEED)
for attempt in range(1, 100001):
    orders = []
    for row in chosen_all:
        r = list(row)
        rng.shuffle(r)
        orders.append(r)
    three = [r for r in orders if len(r) == 3]
    pos = [[a["kind"] for _, _, a in r].index("high") for r in three]
    counts = [pos.count(i) for i in range(3)]
    kind_orders = [tuple(a["kind"] for _, _, a in r) for r in orders]
    adj_ok = all(kind_orders[i] != kind_orders[i + 1] for i in range(len(orders) - 1))
    if max(counts) - min(counts) <= 1 and adj_ok:
        break
else:
    raise SystemExit("조건에 맞는 배치를 찾지 못했어요")
assert max(counts) - min(counts) <= 1
assert all(kind_orders[i] != kind_orders[i + 1] for i in range(len(orders) - 1))
print("high 위치 분포 A·B·C =", counts, f"(3답 문항 {len(three)}개, 시도 {attempt}번째)")

longest_high = sum(1 for r in three if max(r, key=lambda t: len(t[2]["answer"]))[2]["kind"] == "high")
print("가장 긴 답이 high인 3답 문항:", longest_high, "/", len(three))
assert longest_high <= 4, longest_high
letters = "ABC"
items, key = [], []
for n, (sid, chosen) in enumerate(zip(CALIBRATION, orders), 1):
    items.append({"id": f"c{n:02d}", "scenario_id": sid, "situation": scen[sid]["situation"],
                  "context": scen[sid].get("context", ""),
                  # 위기 수준 문항은 채점기가 본문을 접고 [읽기]/[건너뛰기]를 먼저 묻게 한다(A10)
                  "source": "GPT(gpt-6-astra) 작성 예시 답변(" + "·".join(sorted({src for src, _, _ in chosen})) + "), 실제 서비스 답변 아님",
                  "answers": [{"text": a["answer"]} for _, _, a in chosen]})
    if scen[sid]["risk"] == "위기":
        items[-1]["sensitive"] = True
    key.append({"id": f"c{n:02d}", "scenario_id": sid, "why_chosen": why(sid, CALIBRATION[sid]),
                "answers": [{"letter": letters[i], "kind": a["kind"], "source_file": SOURCES[src], "source_index": idx,
                             "source_id": a.get("id"), "boundary": a.get("boundary"),
                             "rationale": a.get("rationale", ""),
                             "intended_total": a["intended_total"], "intended_scores": a["intended_scores"]}
                            for i, (src, idx, a) in enumerate(chosen)]})

n_ans = sum(len(i["answers"]) for i in items)
crisis = [i["id"] for i in items if scen[i["scenario_id"]]["risk"] == "위기"]
pack = {"pack": "calibration-v0", "test_only": False,
        "notice": f"조정용 평가 묶음({len(items)}문항, {n_ans}답). 답변은 GPT가 쓴 예시이며 실제 서비스 답변이 아니에요. 서로 상의하지 말고 채점하고, 채점이 끝날 때까지 key 파일을 열지 마세요. 위기 문항({', '.join(crisis)})은 힘들면 건너뛰어도 돼요.",
        "items": items}
(OUT / "calibration-v0.json").write_text(json.dumps(pack, ensure_ascii=False, indent=1), encoding="utf-8", newline=NL)
(OUT / "calibration-v0.key.json").write_text(json.dumps(
    {"notice": "작성 의도 참고표 — 작성자의 추측이며 검증된 정답이 아니에요. 채점이 모두 끝날 때까지 열지 마세요.",
     "pack": "calibration-v0", "seed": SEED, "high_position_counts_ABC": counts, "items": key},
    ensure_ascii=False, indent=1), encoding="utf-8", newline=NL)

# 최종 계획: 쓸 답변 수. 위기 수준이거나 안전한 답변뿐인 문항은 1개, 나머지는 높음·낮음·경계 하나씩 3개.
def plan_row(sid):
    srcs = by_sid.get(sid, {})
    kinds = [k for v in srcs.values() for k in v]
    if not kinds:
        return 0, "-", "답변 없음(대기)"
    where = " · ".join(f"{s} {len(v)}개" for s, v in srcs.items())
    if scen[sid]["risk"] == "위기":
        return 1, where, "위기 수준: 안전한 답변 1개만"
    if set(kinds) == {"high"}:
        return 1, where, "안전한 답변 1개만(높음 답변만 있음)"
    extra = "경계가 둘이라 첫 번째만 씀" if kinds.count("borderline") > 1 else ""
    return 3, where, extra

lines = ["# 최종 평가 묶음 계획(final-v0) · 성우 김디도", "",
         "조정용과 겹치지 않게 채점 전에 고정한 20문항이에요(R8-11). 문항마다 쓸 답변 수는 아래 표와 같아요. 위기 수준이거나 안전한 답변뿐인 문항은 1개, 나머지는 높음·낮음·경계 하나씩 3개예요.",
         "G7 표시는 처음엔 답변이 없어서 docs/gpt/G7-answers.json에서 가져온 문항이에요.",
         "G8 표시 문항은 R13 후속으로 길이·말투 단서를 줄인 새 답변이에요.", "",
         "| 문항 | 고른 이유 | 쓸 답변 수 | 답변 출처 | 예외·메모 |", "|---|---|---|---|---|"]
total = 0
for sid, note in FINAL.items():
    cnt, where, memo = plan_row(sid)
    total += cnt
    lines.append(f"| {sid} {scen[sid]['situation']} | {why(sid, note)} | {cnt} | {where} | {memo} |")
lines += ["", f"쓸 답변은 모두 {total}개예요."]
(OUT / "final-v0-plan.md").write_text(NL.join(lines) + NL, encoding="utf-8", newline=NL)
print("조정용", len(items), "문항, 답변", n_ans, "개 / 최종 계획 20문항, 쓸 답변", total, "개, G7 문항", sum(1 for s in FINAL if "G7" in by_sid.get(s, {})))
