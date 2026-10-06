# R20 · GPT(아스트라) 결과 · 성우 김디도

> 실행 기록 머리(그대로 옮김):
> ```
> model: gpt-6-astra
> reasoning effort: high
> sandbox: read-only
> session id: 01a10fa0-2f83-7e92-9bd5-decc00072bc8
> ```
> 날짜: 2026-10-05 · 실행: 팀장이 `codex exec`로 돌림 · 아래는 GPT 답 원문(손대지 않음). 본문의 "모델 줄을 옮기지 못했다"는 말은 GPT가 자기 실행 기록을 볼 수 없어서이며, 위 머리가 실제 기록이에요.

**성우 김디도 R20 검토 결과: JSONL 형식과 현재 기준표의 합계 계산은 호환돼요. 다만 위기 문항 노출·평가자 독립성·저장 안내는 배포 전에 수정해야 해요.** 파일은 수정하지 않았어요.

실행 헤더의 `model:`·`reasoning effort:`·`sandbox:` 원문은 확인할 수 없어 임의로 전사하지 않았어요. 아래에서 **실행 확인**은 Node의 메모리상 가짜 DOM 또는 Python 메모리 검증을 뜻해요. 실제 브라우저 키보드 검사는 수행하지 않았어요.

P1은 배포 전 수정이 필요한 문제, P2는 평가 품질·사용성·배포 관리 문제예요.

| 번호 | 파일:줄 | 문제 | 왜 문제인가 | 제안 |
|---|---|---|---|---|
| R20-1 | [template.html:399](C:/Users/ddddv/dido2580/docs/beta/template.html:399), [template.html:406](C:/Users/ddddv/dido2580/docs/beta/template.html:406) | **P1 · 건너뛴 위기 문항이 JSONL 미리보기에 노출돼요.** | **실행 확인:** c07 건너뛰기 처리 뒤 `#out.textContent`에 해당 상황·답변 전체가 들어 있었어요. 읽기를 선택하지 않아도 하단에서 본문을 보게 돼요. [절차:50](C:/Users/ddddv/dido2580/docs/eval/calibration.md:50)의 비동의자 본문 비노출과 맞지 않아요. | 건너뜀 기록의 화면 표시에서 본문을 제외해요. [절차:52](C:/Users/ddddv/dido2580/docs/eval/calibration.md:52)에 맞는 식별자 중심 결측 기록을 정하고, 채점기 가져오기와 함께 지원해요. |
| R20-2 | [template.html:258](C:/Users/ddddv/dido2580/docs/beta/template.html:258), [template.html:269](C:/Users/ddddv/dido2580/docs/beta/template.html:269) | **P1 · 한 번 읽으면 다시 접히지 않고, 읽는 도중 건너뛸 버튼도 없어져요.** | **실행 확인:** 읽기 → 다음 문항 → c07 재방문에서 안내 영역이 0개였어요. `opened.c07=true`도 저장돼요. [절차:51](C:/Users/ddddv/dido2580/docs/eval/calibration.md:51)의 재열람 전 닫기·다시 선택과 달라요. | 문항 이탈·완료·새 세션 때 다시 접어요. 열린 상태에도 닫기·건너뛰기·마치기를 제공하고, 중단 여부를 기록해요. |
| R20-3 | [template.html:146](C:/Users/ddddv/dido2580/docs/beta/template.html:146), [template.html:303](C:/Users/ddddv/dido2580/docs/beta/template.html:303), [template.html:415](C:/Users/ddddv/dido2580/docs/beta/template.html:415) | **P1 · 평가자 코드를 바꿔도 이전 평가자의 점수·근거가 보여요.** | **실행 확인:** R-A 저장 후 R-B로 시작해도 이전 저장 점수 3개가 표시됐고, 내보낸 기록의 평가자는 R-A였어요. 공통 저장 키를 쓰며 평가자별 분리가 없어요. “다른 사람의 점수는 이 화면에 보이지 않아요”라는 안내를 보장하지 못해요. | 저장 상태를 평가자·인증 사용자별로 분리하고, 코드 변경 시 이전 자료를 표시하거나 덮어쓰지 않도록 해요. 개인별 브라우저 프로필 사용 안내도 추가해요. 서버 읽기 권한은 별도로 검증해야 해요. |
| R20-4 | [template.html:154](C:/Users/ddddv/dido2580/docs/beta/template.html:154), [template.html:207](C:/Users/ddddv/dido2580/docs/beta/template.html:207), [template.html:223](C:/Users/ddddv/dido2580/docs/beta/template.html:223), [template.html:368](C:/Users/ddddv/dido2580/docs/beta/template.html:368) | **P1 · 실제 저장 결과와 안내가 달라요.** | **실행 확인:** ① 서버 쓰기를 `unavailable`로 실패시키면 `remote='on'`이 유지돼요. ② 로컬 저장을 예외로 실패시키고 서버도 없게 해도 “이 브라우저에 저장했어요”가 나와요. ③ 로컬 기록이 있는 상태에서 서버 연결을 성공시켜도 평가자 표지만 쓰고 채점 기록은 업로드하지 않았어요. | 로컬·서버 저장 성공을 각각 확인해 표시해요. 미전송 기록을 추적하고 재전송하며, 모두 실패하면 즉시 내보내기를 안내해요. 연결 성공만으로 전달 완료를 표시하지 않아요. |
| R20-5 | [make_beta_zip.py:44](C:/Users/ddddv/dido2580/tools/make_beta_zip.py:44), [make_beta_zip.py:56](C:/Users/ddddv/dido2580/tools/make_beta_zip.py:56), [make_beta_zip.py:63](C:/Users/ddddv/dido2580/tools/make_beta_zip.py:63) | **P1 · 답 열쇠 검사가 압축 작성 이후라서, 실패한 압축에 열쇠가 남아요.** | **조건부 재현 확인:** 압축 후보에 답 열쇠를 메모리로 추가하자 검사는 실패했지만, 이미 닫힌 메모리 ZIP에는 열쇠가 들어 있었어요. 현재 열쇠가 실제 ZIP에 들어갔다는 뜻은 아니에요. `.key.json`은 후보를 거르는 조건에도 없어요. | 후보를 먼저 전부 검사하고 열쇠를 제외해요. 검사 통과 후 압축을 만들고, 완료된 결과만 배포용 이름으로 확정해요. |
| R20-6 | [build.py:30](C:/Users/ddddv/dido2580/docs/beta/build.py:30), [build.py:38](C:/Users/ddddv/dido2580/docs/beta/build.py:38) | **P2 · 페이지의 답 열쇠 방어가 특정 낱말 검사에만 의존해요.** | 현재 페이지 답변에는 `text`만 있었어요. 하지만 **메모리 입력 변형 검사**에서 답변 객체에 `scores`를 추가해도 검사가 통과하고 페이지에 포함됐어요. `answers` 내부는 허용 필드로 제한하지 않아요. | 답변을 `{text: ...}`로 명시적으로 구성하고, 예상하지 않은 필드는 빌드 단계에서 거부해요. 낱말 검사는 보조 검사로 유지해요. |
| R20-7 | [template.html:102](C:/Users/ddddv/dido2580/docs/beta/template.html:102), [template.html:362](C:/Users/ddddv/dido2580/docs/beta/template.html:362), [GPT_PROMPT.md:12](C:/Users/ddddv/dido2580/apps/warmth-scorer/GPT_PROMPT.md:12) | **P2 · 근거 인용이 선택 사항처럼 안내돼요.** | 기준별 입력란이 있으므로 **한 줄이라는 길이 자체가 문제는 아니에요.** 다만 명세는 답변 문장 인용을 요구하는데, 안내는 “옮겨도 돼요”이고 검사는 빈칸만 걸러요. **실행 확인:** 답변과 무관한 `x` 한 글자로 다섯 근거를 채워도 저장됐어요. | “각 기준의 판단 근거가 되는 답변 구절을 인용해 주세요”로 명확히 안내해요. 인용문과 선택 설명을 구분하고, 인용할 내용이 없는 판단의 기록 방식도 정해요. |
| R20-8 | [template.html:289](C:/Users/ddddv/dido2580/docs/beta/template.html:289), [template.html:392](C:/Users/ddddv/dido2580/docs/beta/template.html:392), [template.html:424](C:/Users/ddddv/dido2580/docs/beta/template.html:424) | **P2 · 오프라인 전달에서 문항 메모·베타 의견·소요 시간이 빠져요.** | **실행 확인:** 세 종류를 저장해도 복사되는 JSONL에는 모두 없었어요. 특히 문항별 메모에는 별도 내보내기도 없어요. 베타의 주요 목적인 헷갈린 기준·불편한 점 수집이 누락될 수 있어요. | 채점 JSONL과 별도로 의견을 복사·저장할 수 있게 해요. 무엇을 운영자에게 전달해야 하는지 함께 안내해요. |
| R20-9 | [template.html:304](C:/Users/ddddv/dido2580/docs/beta/template.html:304), [template.html:231](C:/Users/ddddv/dido2580/docs/beta/template.html:231), [template.html:387](C:/Users/ddddv/dido2580/docs/beta/template.html:387) | **P2 · 저장 전 입력이 화면 재생성 때 사라져요.** | **실행 확인:** 점수·근거를 입력하고 `renderItem()`을 다시 호출하면 입력이 모두 없어졌어요. 문항 이동뿐 아니라 늦게 끝난 서버 초기화도 `render()`를 호출해요. 서버 초기화 완료가 실제 입력 중간에 겹칠지는 **추측**이지만, 해당 삭제 경로는 있어요. | 초안을 상태에 보관하고 문항 이동·비동기 갱신에도 유지해요. 저장 여부와 수정 중 여부를 구분해 표시해요. |
| R20-10 | [template.html:269](C:/Users/ddddv/dido2580/docs/beta/template.html:269), [template.html:352](C:/Users/ddddv/dido2580/docs/beta/template.html:352), [template.html:77](C:/Users/ddddv/dido2580/docs/beta/template.html:77) | **P2 · 키보드 흐름과 감점 설명 접근성이 불완전해요.** | **코드 확인:** 읽기 버튼은 자신을 제거하는 `render()` 후 포커스를 옮기지 않아요. 감점 이유는 라벨의 `title`에만 있고 체크박스 설명으로 연결되지 않아요. 감점 클릭 영역의 최소 높이는 44px이에요. 실제 브라우저의 포커스 결과와 전체 키보드 완주는 미확인이에요. | 읽기 뒤 새 본문 제목으로 포커스를 옮겨요. 감점 이유를 화면에 제공하고 `aria-describedby`로 연결하며 클릭 영역을 48px 이상으로 맞춰요. Tab·방향키·Space만으로 저장·건너뜀·내보내기까지 실측해요. |
| R20-11 | [make_beta_zip.py:16](C:/Users/ddddv/dido2580/tools/make_beta_zip.py:16), [make_beta_zip.py:42](C:/Users/ddddv/dido2580/tools/make_beta_zip.py:42) | **P2 · 현재 로컬 가상환경도 배포 후보에 포함돼요.** | **실행 확인:** 실제 존재하는 `apps/voice-persona/.venv/pyvenv.cfg`를 후보 함수에 넣으면 통과했어요. `.venv`가 제외 목록에 없고, 추적 여부와 무관하게 `apps/` 전체를 훑어요. 전체 압축 크기는 측정하지 않았어요. | 배포할 파일을 허용 목록으로 정해요. 최소한 가상환경·로컬 설정을 제외하고, 디렉터리 탐색 단계에서도 제외해요. |
| R20-12 | [template.html:365](C:/Users/ddddv/dido2580/docs/beta/template.html:365), [template.html:399](C:/Users/ddddv/dido2580/docs/beta/template.html:399) | **P2 · 과거 채점에 새 기준표 버전이 붙을 수 있어요.** | 저장 기록에는 기준표 버전이 없고, 내보낼 때 현재 페이지 버전을 붙여요. **조건부 재현 확인:** 기록에 다른 버전을 넣어도 내보내기는 현재 `1.0`으로 바뀌었어요. 실제 기준표 변경 후에는 이전 평가가 새 기준 평가로 표시될 수 있어요. | 저장 시 `rubric_version`과 평가 묶음 버전을 기록하고 그대로 내보내요. 버전이 다른 기록은 분리해요. |

확인한 정상 동작도 있어요.

- 베타의 실제 저장 처리로 만든 **28개 기록 모두** `parseJsonl`·`validateRecord`를 통과했어요. 건너뜀 기록도 항목 점수·합계가 `null`인 상태로 통과했어요.
- 점수·감점 조합 **62,208개에서 합계 차이가 0개**였어요. 예시 **A=0, B=4, C=10**, `zero` 감점도 일치했어요.
- `build.py --check`가 통과했어요. 현재 생성 페이지의 답변 필드는 `text`뿐이고 답 열쇠 표식은 없었어요.
- 서버 접근권한·실제 다운로드·클립보드·스크린리더 동작은 확인하지 않았어요. 전체 ZIP은 만들지 않았고, 압축 방어 검사는 메모리에서만 했어요.

아래 한 줄은 베타의 실제 `jsonl()` 함수를 추출해 일반 채점과 건너뜀을 합친 28줄을 재검증해요. 파일을 작성하지 않아요.

```powershell
'const fs=require("fs"),api=require("./apps/warmth-scorer/app.js"),h=fs.readFileSync("docs/beta/index.html","utf8"),d=JSON.parse(h.match(/var DATA = (\{.*?\});\r?\n/s)[1]),r=JSON.parse(fs.readFileSync("apps/warmth-scorer/rubric.json","utf8")),state={ratings:{}};for(const it of d.pack.items)it.answers.forEach((a,i)=>{state.ratings[it.id+"-"+String.fromCharCode(65+i)]={scores:Object.fromEntries(r.criteria.map(c=>[c.id,2])),evidence:Object.fromEntries(r.criteria.map(c=>[c.id,["probe"]])),penalties:[],total:it.sensitive?null:10,skipped:!!it.sensitive,rater:"R-TEST",date:new Date().toISOString()}});const code=h.slice(h.indexOf("  function jsonl()"),h.indexOf("  function refreshOut()"));const out=Function("rubric","pack","state","const letter=i=>String.fromCharCode(65+i);const akey=(it,i)=>it.id+"+JSON.stringify("-")+"+letter(i);"+code+"return jsonl();")(r,d.pack,state);const p=api.parseJsonl(out,r);console.log(JSON.stringify({records:p.records.length,bad:p.bad,skipped:p.records.filter(x=>x.skipped).length,validationErrors:p.records.map(x=>api.validateRecord(r,x)).filter(Boolean)}));' | node; if ($?) { python -B -X utf8 docs/beta/build.py --check }
```

실행 결과는 `records:28`, `bad:[]`, `skipped:1`, `validationErrors:[]`와 빌드 검사 통과였어요.

검토한 파일 목록: `AGENTS.md`, `TEAM_BOARD.md` R20 주변, `docs/beta/{template.html,index.html,build.py}`, `tools/make_beta_zip.py`, `apps/warmth-scorer/{app.js,rubric.json,GPT_PROMPT.md}`, `docs/eval/calibration.md`, `docs/eval/packs/calibration-v0.json`, 관련 배포 설정·시작 스크립트이며 답 열쇠 파일은 메모리 압축 재현에만 사용했어요. **실행해 본 것:** Node 저장·JSONL 검증·62,208개 합계 대조·상태 전환·저장 실패 재현, Python 빌드 검사·메모리 ZIP 및 입력 변형 검사, 작업 상태 확인이며 파일 수정은 없어요.
