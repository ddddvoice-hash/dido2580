# 소개 페이지 만들기: 저장소 맨 위에서 `python docs/showcase/build.py` 를 실행하면
# template.html에 상황 문항(docs/eval/scenarios-v0.json)·기준표(apps/warmth-scorer/rubric.json)·아이콘을
# 그대로 넣어 docs/showcase/index.html을 만든다. 원본을 고치지 않고 옮기기만 한다(R12-8, C1).
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "docs" / "showcase"
GH = "https://github.com/ddddvoice-hash/dido2580/blob/ccr-dfaecddb-lml56o"
# 이 페이지의 접근성 검사 범위와 결과. 문구를 바꾸면 실제로 다시 검사한 뒤에 바꾼다.
A11Y = "2026-10-05 axe-core 자동 검사(WCAG 2.1 A·AA), 밝은·어두운 화면, 폭 390px·1200px, 첫 화면과 문항을 펼친 화면에서 위반 0건. 사람의 화면 낭독기 사용 시험은 아직 하지 않았어요."
DATE = "2026년 10월"

scen = json.loads((ROOT / "docs/eval/scenarios-v0.json").read_text(encoding="utf-8"))
rubric = json.loads((ROOT / "apps/warmth-scorer/rubric.json").read_text(encoding="utf-8"))
icon = re.search(r'<link rel="icon" type="image/svg\+xml" href="(data:[^"]*)">',
                 (ROOT / "apps/index.html").read_text(encoding="utf-8")).group(1)

def js(obj):
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")

ex = rubric["examples"][0]
data = {"groups": scen["groups"],
        "items": [{k: it[k] for k in ["id", "group", "risk", "situation", "context", "must", "must_not", "voice"]}
                  for it in scen["items"]]}
pen = {p["id"]: {"name": p["name"], "effect": p["effect"], "why": p["why"]} for p in rubric["penalties"]}
exdata = {"criteria": [{"id": c["id"], "name": c["name"]} for c in rubric["criteria"]], "answers": ex["answers"]}

t = (HERE / "template.html").read_text(encoding="utf-8")
for key, val in {
    "__ICON__": icon, "__GH__": GH, "__A11Y__": html.escape(A11Y), "__DATE__": DATE,
    "__RVER__": html.escape(str(rubric["version"])), "__SITUATION__": html.escape(ex["situation"]),
    "__LESSON__": html.escape(ex["lesson"]), "__N__": str(len(scen["items"])),
    "__STATUS__": html.escape(scen.get("status", "")),
    "__DATA__": js(data), "__PEN__": js(pen), "__EX__": js(exdata),
}.items():
    t = t.replace(key, val)
left = re.findall(r"__[A-Z0-9]+__", t)
if left:
    raise SystemExit(f"채우지 못한 자리: {left}")
(HERE / "index.html").write_text(t, encoding="utf-8")

# 페이지 안 문항 데이터가 원본과 같은지 확인(R12-8)
embedded = json.loads(re.search(r"var DATA = (.*?);\nvar PEN", t, re.S).group(1).replace("<\\/", "</"))
assert embedded == data, "페이지 안 문항 데이터가 원본과 다름"
print(f"index.html {len(t)}자, 문항 {len(data['items'])}개 원본과 일치")
