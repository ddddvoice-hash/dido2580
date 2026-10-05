# 평가 묶음 만들기: 저장소 맨 위에서 python docs/eval/packs/build_packs.py
# - calibration-v0.json: 조정용 10문항. 따뜻함 채점기의 "평가 묶음 열기"로 연다. 의도한 점수는 넣지 않는다.
# - calibration-v0.key.json: 답변별 작성 의도(높음·낮음·경계)와 의도 점수. 채점이 모두 끝날 때까지 열지 않는다.
# - final-v0-plan.md: 최종 20문항 목록과 고른 이유(답변은 아직 일부만 있음).
# 문항 선택은 채점 전에 고정한다(R8-11). 답변 순서는 고정 시드로 섞는다(R8-12).
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
scen = {i["id"]: i for i in json.loads((ROOT / "docs/eval/scenarios-v0.json").read_text(encoding="utf-8"))["items"]}
g2 = json.loads((ROOT / "docs/gpt/G2-answers.json").read_text(encoding="utf-8"))

# 조정용 10: 7갈래 모두, 위기 수준은 1개(답변 1개만, 안전한 답변).
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

by_sid = {}
for a in g2["items"]:
    by_sid.setdefault(a["scenario_id"], []).append(a)

rng = random.Random(20261005)
items, key = [], []
for n, sid in enumerate(CALIBRATION, 1):
    cands = by_sid[sid]
    if scen[sid]["risk"] == "위기":
        chosen = [a for a in cands if a["kind"] == "high"][:1]
    else:  # 높음·낮음·경계 하나씩(경계가 둘이면 첫 번째)
        chosen = [next(a for a in cands if a["kind"] == k) for k in ("high", "low", "borderline")]
    rng.shuffle(chosen)
    letters = "ABC"
    items.append({"id": f"c{n:02d}", "scenario_id": sid, "situation": scen[sid]["situation"],
                  "source": "GPT(gpt-6-astra) 작성 예시 답변(G2), 실제 서비스 답변 아님",
                  "answers": [{"text": a["answer"]} for a in chosen]})
    key.append({"id": f"c{n:02d}", "scenario_id": sid, "why_chosen": why(sid, CALIBRATION[sid]),
                "answers": [{"letter": letters[i], "kind": a["kind"], "intended_total": a["intended_total"],
                             "intended_scores": a["intended_scores"]} for i, a in enumerate(chosen)]})

pack = {"pack": "calibration-v0", "test_only": False,
        "notice": "조정용 평가 묶음(10문항). 답변은 GPT가 쓴 예시이며 실제 서비스 답변이 아니에요. 서로 상의하지 말고 채점하고, 채점이 끝날 때까지 key 파일을 열지 마세요. 위기 문항(c07)은 힘들면 건너뛰어도 돼요.",
        "items": items}
(OUT / "calibration-v0.json").write_text(json.dumps(pack, ensure_ascii=False, indent=1), encoding="utf-8")
(OUT / "calibration-v0.key.json").write_text(json.dumps({"pack": "calibration-v0", "seed": 20261005, "items": key}, ensure_ascii=False, indent=1), encoding="utf-8")

lines = ["# 최종 평가 묶음 계획(final-v0) · 성우 김디도", "",
         "조정용과 겹치지 않게 채점 전에 고정한 20문항이에요(R8-11). 답변 3개씩이 필요하고, 위기 수준 문항은 안전한 답변만 써요.", "",
         "| 문항 | 고른 이유 | 답변 |", "|---|---|---|"]
for sid, note in FINAL.items():
    have = len(by_sid.get(sid, []))
    lines.append(f"| {sid} {scen[sid]['situation']} | {why(sid, note)} | {'G2에 ' + str(have) + '개' if have else '아직 없음(G7)'} |")
(OUT / "final-v0-plan.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("조정용", len(items), "문항, 답변", sum(len(i["answers"]) for i in items), "개 / 최종 계획 20문항, 답변 없는 문항", sum(1 for s in FINAL if s not in by_sid))
