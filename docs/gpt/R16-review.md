# R16 · GPT(아스트라) 결과 · 성우 김디도

> 실행 기록 머리(그대로 옮김):
> ```
> model: gpt-6-astra
> reasoning effort: high
> sandbox: read-only
> session id: 01a10d46-3ae4-7cc1-a32e-fc558d7a8992
> ```
> 날짜: 2026-10-05 · 실행: 팀장이 `codex exec`로 돌림 · 아래는 GPT 답 원문(손대지 않음). 본문의 "모델 줄을 옮기지 못했다"는 말은 GPT가 자기 실행 기록을 볼 수 없어서이며, 위 머리가 실제 기록이에요.

**성우 김디도 · R16 리뷰: 수정이 필요해요.** 상황을 묶어 뽑는 구현은 확인했지만, 경계값·결측·계산 실패를 처리하고 설명하는 부분이 부족해요. 일치도 테스트는 **57건 모두 통과**했어요. 어떤 파일도 수정하지 않았어요.

실행 기록의 `model:`·`reasoning effort:`·`sandbox:` 원문은 제공되지 않아 옮기지 못했어요. 모델 이름은 추측해서 적지 않았어요.

| 번호 | 파일:줄 | 문제 | 왜 문제인가 | 제안 |
|---|---|---|---|---|
| 1 | [app.js:269](C:/Users/ddddv/dido2580/apps/warmth-scorer/app.js:269), [agreement.test.js:148](C:/Users/ddddv/dido2580/apps/warmth-scorer/tests/agreement.test.js:148) | **높음 — 완전 일치의 `[1,1]`을 일반적인 95% 구간처럼 표시해요.** 재현 ①에서 5·10상황 모두 이렇게 나와요. | 관찰 자료에 불일치가 없으면 재표집으로 새로운 불일치를 만들 수 없어요. 폭이 0이라는 사실이 모집단의 불확실성까지 0이라는 근거는 아니에요. 현재 테스트는 `[1,1]`을 기대하지만, 경계 경고는 검사하지 않아요. | 점추정 `α=1`은 유지하되, 구간에는 **“완전 일치로 재표집 분포가 퇴화해 불확실성을 추정하기 어려워요”**라고 표시해요. 경계 처리와 안내를 함께 테스트해요. |
| 2 | [app.js:267](C:/Users/ddddv/dido2580/apps/warmth-scorer/app.js:267), [app.js:364](C:/Users/ddddv/dido2580/apps/warmth-scorer/app.js:364) | **높음 — 계산 불가를 제외한 구간인데 실패 횟수가 화면에 없어요.** 재현 ②에서 실패가 **688/2,000회·711/2,000회**예요. | 반환 객체에는 `failed`가 있지만, 화면은 이를 사용하지 않아요. 따라서 사용자는 약 3분의 1이 제외된 **계산 가능 표본만의 조건부 구간**이라는 사실을 알 수 없어요. 유효 반복 수가 충분한지도 확인하지 않아요. | 시도·성공·실패 횟수와 실패율을 표시해요. 실패가 많은 경우 일반적인 95% 구간 표시를 보류하거나 조건부 결과임을 명시해요. 실패값을 임의로 0이나 1로 대체하지 않아요. |
| 3 | [app.js:259](C:/Users/ddddv/dido2580/apps/warmth-scorer/app.js:259), [app.js:318](C:/Users/ddddv/dido2580/apps/warmth-scorer/app.js:318) | **높음 — 점수가 모두 빠진 상황도 ‘상황 5개’에 포함해요.** 재현 ③은 실제 유효 상황이 **1개**인데 구간을 계산해요. | `clusters`에 넣은 뒤 유효 평가 수를 확인하므로, 해당 항목이 전부 결측인 상황도 최소치에 포함돼요. 유효 답변 3개만으로 `clusters=5`, `[1,1]`이 나와요. | 계산 허용 기준에는 **해당 항목에 유효 평가자 짝이 있는 상황 수**를 사용해요. 전체 상황 수와 유효 상황 수를 구분하고, 결측 상황을 재표집에 포함하는 정책도 설명해요. |
| 4 | [app.js:352](C:/Users/ddddv/dido2580/apps/warmth-scorer/app.js:352), [app.js:1047](C:/Users/ddddv/dido2580/apps/warmth-scorer/app.js:1047), [index.html:163](C:/Users/ddddv/dido2580/apps/warmth-scorer/index.html:163) | **중간 — 방법·시드·반복 수·작은 상황 수의 한계가 화면에서 빠져요.** 재현 ④에서는 시드만 바꿔 하한이 **0.35165 → 0.21333**으로 달라져요. | 고정 시드는 반복 실행 결과를 같게 만들지만 구간의 안정성을 보장하지는 않아요. 이 자료는 10상황·30답변이어서 `표본 적음` 경고도 없어져요. 화면에는 단순히 `95%`만 붙어요. | 상황 단위 백분위 구간, 2,000회, 시드, 유효 상황 수를 함께 표시해요. 여러 시드·반복 수에서 끝점의 안정성을 검사하고, 평가자를 고정한 탐색 결과라는 한계를 밝혀요. |

**① 완전 일치 경계 재현 — 상황마다 답변 3개예요.**

```powershell
node -e "const W=require('./apps/warmth-scorer/app.js');for(const n of [5,10]){const c=Object.fromEntries(Array.from({length:n},(_,i)=>['s'+i,Array.from({length:3},()=>[i%2*2,i%2*2])]));console.log(n,W.krippendorffAlpha(Object.values(c).flat()),W.bootstrapAlpha(c,2000,20261005));}"
```

두 경우 모두 `α=1`, 구간 `[1,1]`이에요. 실패는 각각 **171회·5회**예요. 이 경계는 Q2가 인용한 [α 부트스트랩 설명 자료](https://www.afhayes.com/public/alphaboot.pdf)에서도 적용 제외로 다뤄요. 다만 그 자료의 쌍 재표집과 현재 상황 재표집은 서로 다른 방법이에요.

**② 실패 제외와 모든 점수 동일 재현이에요.**

```powershell
node -e "const W=require('./apps/warmth-scorer/app.js');for(const n of [5,10])for(const same of [false,true]){const c=Object.fromEntries(Array.from({length:n},(_,i)=>['s'+i,Array.from({length:3},()=>same?[1,1]:i===n-1?[0,2]:[0,0])]));console.log(n,same,{alpha:W.krippendorffAlpha(Object.values(c).flat()),...W.bootstrapAlpha(c,2000,20261005)});}"
```

| 자료 | 점추정 α | 반환 구간 | 실패 |
|---|---:|---|---:|
| 5상황, 마지막 상황만 불일치 | −0.07407 | [−0.38095, −0.07407] | 688/2,000 |
| 10상황, 마지막 상황만 불일치 | −0.03509 | [−0.15686, −0.03509] | 711/2,000 |
| 모든 점수가 1 | `null` | `[null,null]` | 2,000/2,000 |

모든 점수가 같을 때 α를 계산하지 않는 처리는 맞아요. **실패 제외가 항상 구간을 좁히거나 양수 쪽으로 민다는 것은 확인하지 못했어요.** 위 사례에서는 구간 전체가 음수예요. 확인한 문제는 실패를 제외한 조건부 결과라는 사실을 숨긴다는 점이에요.

**③ 유효 상황 1개가 최소 기준을 통과하는 재현이에요.**

```powershell
node -e "const W=require('./apps/warmth-scorer/app.js'),r=[];for(let i=0;i<5;i++)for(let j=0;j<3;j++)for(let k=0;k<2;k++)r.push({situation:'s'+i,answer:'a'+j,rater:'r'+k,scores:{x:i===0?j:null}});console.log(W.computeAgreement({criteria:[{id:'x',name:'x'}]},r).criteria[0]);"
```

`answersUsed=3`, `clusters=5`, 구간 `[1,1]`, 실패 **645회**예요.

**④ 양수 구간과 시드 민감도 재현이에요.**

```powershell
node -e "const W=require('./apps/warmth-scorer/app.js'),a=[...Array(5).fill([0,0]),...Array(4).fill([2,2]),[0,2]],c=Object.fromEntries(a.map((v,i)=>['s'+i,[v,v,v]]));console.log('alpha',W.krippendorffAlpha(Object.values(c).flat()));for(const s of [20261005,42])console.log(s,W.bootstrapAlpha(c,2000,s));"
```

점추정은 **0.80135**이고, 구간은 각각 **[0.35165, 1]**, **[0.21333, 1]**이에요. 양수 구간 자체가 오류라는 뜻은 아니에요. 같은 자료에서 시드에 따라 하한이 약 **0.13832** 달라지는 것을 확인한 사례예요.

상황 **5개 미만에서 산출을 보류하는 운영 기준은 가능해요.** 하지만 5개 이상이면 명목 95% 포함률이 확보된다는 근거는 확인하지 못했어요. Q2도 공통 최소치는 없다고 명시해요. 예를 들어 상황 유형 `[0,0]`, `[2,2]`, `[0,2]`가 각각 40%·40%·20%이고 상황 안 답변 3개가 같은 점수쌍인 **가정 모형**에서는 모집단 α가 0.6이에요. 그런데 표본에 두 종류의 일치 상황만 들어와 `[1,1]`로 퇴화하는 사건의 확률은 `0.8ⁿ−2×0.4ⁿ`, 즉 **5상황에서 30.72%, 10상황에서 10.716%**예요. 실제 자료에 대한 추측이 아니라, 최소 상황 수만으로 보장할 수 없음을 보여 주는 계산 예예요.

추가로 확인한 사항이에요.

- **묶음 재표집:** 같은 상황의 모든 답변과 평가자 점수를 통째로 가져와요. 답변 3개를 따로 뽑는 구현은 아니에요.
- **재현성:** 화면 계산은 2,000회·시드 `20261005`예요. 같은 입력으로 반복하거나 기록 순서를 뒤집어도 통합 계산 결과가 같았어요.
- **문구:** “참값이 95% 확률로 들어 있다”라는 직접적인 과장 문장은 없어요. 대신 방법과 한계 설명이 빠져 있어요.
- **테스트:** 점추정을 구간이 포함하는 한 사례는 95% 포함률 검증이 아니에요. 현재 부트스트랩 테스트에는 실패 횟수, 전부 동일한 점수, 항목별 유효 상황 수, 3답변 묶음 유지 검사가 빠져 있어요.
- **실행 범위:** 브라우저 테스트는 임시 파일을 작성하므로 실행하지 않았어요. 화면 문구는 소스와 메모리에서 실행한 `ciText`로 확인했어요. 예시 합계 `A=0, B=4, C=10`과 두 `zero` 감점의 합계 0도 확인했어요.

검토한 파일 목록: `AGENTS.md`, `TEAM_BOARD.md` R16, `docs/gpt/Q1-Q8-answers.md` Q2, `apps/warmth-scorer/{app.js,index.html,rubric.json}`, `tests/{agreement.test.js,agreement.browser.js,alpha_crosscheck.py,scenarios.test.js}` 및 테스트 폴더 관련 검색 결과 · 실행해 본 것: 일치도 테스트 57건 통과, 구문 검사, Node 직접 재현·시드·순서 비교·가정 모형 계산·예시 및 감점 확인, 작업 전후 상태 확인; 파일 수정 없음.
