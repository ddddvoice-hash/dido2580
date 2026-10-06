# R21 · GPT(아스트라) 결과 · 성우 김디도

> 실행 기록 머리(그대로 옮김):
> ```
> model: gpt-6-astra
> reasoning effort: high
> sandbox: read-only
> session id: 01a10fa8-42ab-73c1-a370-d7f86b5fe6f1
> ```
> 날짜: 2026-10-05 · 실행: 팀장이 `codex exec`로 돌림 · 아래는 GPT 답 원문(손대지 않음). 본문의 "모델 줄을 옮기지 못했다"는 말은 GPT가 자기 실행 기록을 볼 수 없어서이며, 위 머리가 실제 기록이에요.

**성우 김디도 · R21 검토 결과예요.** 여백 규칙은 검출 성공의 필요조건도 충분조건도 아니에요. 예비 녹음의 출발점으로는 유지할 수 있지만, `failed`와 경계 오차를 별도로 확인해야 해요. 파일은 수정하지 않았어요.

이번 실행의 `model:`·`reasoning effort:`·`sandbox:` 기록 원문은 제공되지 않아 추정해서 옮기지 않았어요.

| 번호 | 안건 | 의견(동의·반대·보완) | 근거 | 제안 |
|---|---|---|---|---|
| R21-1 | 여백 규칙의 충분성 | **보완해요. 준수해도 실패해요.** | [voice-evidence.md:67](/C:/Users/ddddv/dido2580/docs/eval/voice-evidence.md:67), [analysis.js:41](/C:/Users/ddddv/dido2580/apps/reading-coach/analysis.js:41). 아래 `weak`·`long_pause`는 규칙을 지켰지만 90백분위가 각각 **0.007071·0**이라 실패했어요. 긴 내부 쉼은 오히려 90백분위를 낮출 수도 있어요. | “여백 확보를 위한 시작 규칙이며 검출 성공을 보장하지 않아요”라고 명시해요. 내부 쉼이 많을수록 유리하다고 일반화하지 않아요. |
| R21-2 | 낮은 바닥 소음과 실패 이유 | **보완해요. 실패 원인 설명이 좁아요.** | [voice-evidence.md:13](/C:/Users/ddddv/dido2580/docs/eval/voice-evidence.md:13), [analysis.js:70](/C:/Users/ddddv/dido2580/apps/reading-coach/analysis.js:70). `floor`는 앞뒤 각 1초인데도 **0.021213 < 3×0.008**이라 `threshold`예요. `weak`·`long_pause`에는 합성한 소리가 있지만 `no_speech`예요. [Q10-answer.md:24](/C:/Users/ddddv/dido2580/docs/gpt/Q10-answer.md:24)의 주의사항과 달라요. | `threshold`는 “크기 분포 조건 미충족”, `no_speech`는 “조건을 만족하는 말소리 구간 미검출”로 설명해요. 여백 부족·실제 무음으로 단정하지 않아요. |
| R21-3 | 검출 성공과 경계 정확도 | **보완해요. 성공해도 틀릴 수 있어요.** | [analysis.js:52](/C:/Users/ddddv/dido2580/apps/reading-coach/analysis.js:52), [analysis.js:89](/C:/Users/ddddv/dido2580/apps/reading-coach/analysis.js:89). `weak_edges`는 양끝 말소리를 **200ms씩 누락**, `breath_edges`는 양끝 잡음을 **200ms씩 포함**했지만 둘 다 실패 표시가 없어요. | [voice-evidence.md:67](/C:/Users/ddddv/dido2580/docs/eval/voice-evidence.md:67)의 사람 확인을 유지해요. `failed`와 별도로 시작·끝·내부 쉼 오차를 기록해요. |
| R21-4 | 여백 규칙의 필요성 | **자동 통과 기준으로 쓰는 데 반대해요.** | [analysis.js:63](/C:/Users/ddddv/dido2580/apps/reading-coach/analysis.js:63)는 여백 규칙을 검사하지 않아요. `ratio12`는 여백 합 **12%**, `half_second`는 각 **0.5초**, `no_outer`는 앞뒤 **0초**인데 검출돼요. | 녹음 규칙 준수와 분석 성공을 별도 항목으로 관리해요. `failed`가 없다고 규칙 준수로 기록하지 않아요. |
| R21-5 | B05 가안·나안 일치 | **문구 반영에 동의해요. CSV는 미반영이에요.** | [voice-evidence.md:61](/C:/Users/ddddv/dido2580/docs/eval/voice-evidence.md:61)의 두 인용문은 [Q10-answer.md:56](/C:/Users/ddddv/dido2580/docs/gpt/Q10-answer.md:56)·[60](/C:/Users/ddddv/dido2580/docs/gpt/Q10-answer.md:60)과 **문자열이 각각 완전히 같아요**. [test-sentences.csv:11](/C:/Users/ddddv/dido2580/voice/test-sentences.csv:11)은 어느 안과도 다르고 기존 연결 약속이 남아 있어요. | 근거표의 “선택·버전 확정 전 B05 녹음·시연 보류”를 유지해요. 선택 뒤 CSV도 같은 원고로 맞춰요. |
| R21-6 | R18-2: 노출 전 선택·키보드 종료 | **대부분 반영됐지만 보완이 남아요.** | [R18-review.md:21](/C:/Users/ddddv/dido2580/docs/gpt/R18-review.md:21) → [calibration.md:50](/C:/Users/ddddv/dido2580/docs/eval/calibration.md:50). 노출 전 선택, 기능 없으면 보류, 자동 재생 금지는 반영됐어요. 키보드로 읽기·건너뛰기를 고른다는 설명은 있지만 **진행 중 중단·종료를 확인하는 절차**는 명시되지 않았어요. | 키보드만으로 중단·종료 가능한지 시작 전에 확인하고, 확인되지 않으면 보류한다고 적어요. 이번에는 화면 동작을 실행하지 않았어요. |
| R21-7 | R18-4: 작업량·도움 경로 | **부분 반영이에요.** | [R18-review.md:23](/C:/Users/ddddv/dido2580/docs/gpt/R18-review.md:23) → [calibration.md:49](/C:/Users/ddddv/dido2580/docs/eval/calibration.md:49). 담당 역할·비공개 연락 경로·반복 열람·토론·휴식은 반영됐어요. 다만 **사전 사용으로 시간 측정** 대신 “첫 회차에서 재서 고친다”로 바뀌었어요. | 첫 회차 안내용 시간은 사전 사용으로 측정하고, 첫 회차 실측으로 보정한다고 구분해요. |
| R21-8 | R18-3·5: 보상·복귀·결측 | **문서 반영에 동의해요.** | [R18-review.md:22](/C:/Users/ddddv/dido2580/docs/gpt/R18-review.md:22)·[24](/C:/Users/ddddv/dido2580/docs/gpt/R18-review.md:24) → [calibration.md:51](/C:/Users/ddddv/dido2580/docs/eval/calibration.md:51)·[52](/C:/Users/ddddv/dido2580/docs/eval/calibration.md:52)·[53](/C:/Users/ddddv/dido2580/docs/eval/calibration.md:53)·[54](/C:/Users/ddddv/dido2580/docs/eval/calibration.md:54). 복귀·보충 의무 없음, 보상 감액 금지, 마무리 대화 중단, 항목별 유효 평가 2개 이상과 결측 구분이 들어 있어요. | 유지해요. 실제 운영·계산 구현까지 검증했다는 뜻은 아니에요. |
| R21-9 | R18-1·6·7: 관련 절차 | **문서 반영에 동의해요.** | [R18-review.md:20](/C:/Users/ddddv/dido2580/docs/gpt/R18-review.md:20)·[25](/C:/Users/ddddv/dido2580/docs/gpt/R18-review.md:25)·[26](/C:/Users/ddddv/dido2580/docs/gpt/R18-review.md:26) → [calibration.md:13](/C:/Users/ddddv/dido2580/docs/eval/calibration.md:13)·[39](/C:/Users/ddddv/dido2580/docs/eval/calibration.md:39)은 28·56답으로 정리됐어요. [11](/C:/Users/ddddv/dido2580/docs/eval/calibration.md:11)의 코드·브라우저 분리, [27](/C:/Users/ddddv/dido2580/docs/eval/calibration.md:27)·[28](/C:/Users/ddddv/dido2580/docs/eval/calibration.md:28)의 배포 제한·원본 보존도 반영됐어요. | 유지해요. 이번 확인은 문서 대조예요. |
| R21-10 | 예비 녹음 수량 표현 | **보완해요. 곱셈 표기가 모호해요.** | [voice-evidence.md:67](/C:/Users/ddddv/dido2580/docs/eval/voice-evidence.md:67)은 “6개 × 3개 길이대 × 두 방식 × 2테이크”처럼 적혀 있어요. [Q10-answer.md:31](/C:/Users/ddddv/dido2580/docs/gpt/Q10-answer.md:31)·[33](/C:/Users/ddddv/dido2580/docs/gpt/Q10-answer.md:33)은 **길이대별 2개, 총 6원고 × 2방식 × 2테이크 = 24원본**이에요. | Q10의 수량을 그대로 풀어 적어요. 여백 3조건까지 합쳐 **72회 분석**이에요. |

**아래는 직접 실행한 합성음 결과예요.** 8kHz·100Hz 사인파와 고정 시드 잡음을 메모리에서 만들었어요. 잡음은 낮은 바닥 소음·호흡 구간을 대신하는 인공 입력이며 실제 숨소리 재현은 아니에요. 실제 녹음에서도 같은 빈도로 발생한다는 판단은 **추측**이에요.

여기서 길이는 첫~끝 말소리 사이 시간이고 내부 쉼을 포함해요. “검출”은 `failed !== true`라는 뜻이에요. 성공 반환값에는 실제로 `failed: false` 필드가 없어요.

| 조건 ID | 입력 조건 | 여백 규칙 | 실제 결과 |
|---|---|---|---|
| `base` | 소리 20초, 앞뒤 각 1.5초 | 준수: 합 15% | 검출, 경계 오차 0 |
| `weak` | 진폭 0.01 소리 4초, 각 1초 | 준수 | `no_speech`; 90백분위 0.007071 |
| `long_pause` | 소리 0.4초＋쉼 10초＋소리 0.4초, 각 1초 | 준수: 2÷10.8 = 18.52% | `no_speech`; 90백분위 0 |
| `floor` | 진폭 0.03 소리 4초, 각 1초의 잡음 RMS 0.008 | 준수 | `threshold`; 90백분위 0.021213 < 0.024 |
| `weak_edges` | 4초 소리 양끝 0.2초만 진폭 0.01, 각 1초 | 준수 | 검출, 시작 **+200ms**·끝 **−200ms**, `spoken=3.6초` |
| `breath_edges` | 4초 소리 앞뒤 여백 각 1초 중 인접 0.2초에 RMS 0.04 잡음 | 준수 | 검출, 시작 **−200ms**·끝 **+200ms**, `spoken=4.4초` |
| `long_short` | 소리 20초, 각 1초 | 위반: 합 10% | `threshold`; 10·90백분위 모두 0.141421 |
| `ratio12` | 소리 20초, 각 1.2초 | 위반: 합 12% | 검출, 경계 오차 0 |
| `half_second` | 소리 4초, 각 0.5초 | 위반: 각각 1초 미만 | 검출, 경계 오차 0 |
| `no_outer` | 소리 2초＋쉼 2초＋소리 2초, 외부 여백 없음 | 위반 | 검출, 내부 쉼 2초도 검출 |

완전 무음 여백과 일정한 소리만 있다면, 여백 합 15%는 파일 전체의 약 **13.04%**라 10백분위 확보에 여유가 있어요. 하지만 절대 크기 하한, 바닥 대비 크기, 90백분위, 연속 80ms 조건까지 보장하지는 않아요.

재현 명령이에요. **저장소 루트의 PowerShell에서 한 줄 전체를 실행**하면 위 10조건이 출력돼요. 파일을 쓰지 않아요.

```powershell
node -e "const a=require('./apps/reading-coach/analysis.js'); const sr=8000; const z=t=>[t,0]; const s=(t,v=.2)=>[t,v]; const n=(t,v)=>[t,v,'n']; const cases=[['base',1.5,21.5,[z(1.5),s(20),z(1.5)]],['weak',1,5,[z(1),s(4,.01),z(1)]],['long_pause',1,11.8,[z(1),s(.4),z(10),s(.4),z(1)]],['floor',1,5,[n(1,.008),s(4,.03),n(1,.008)]],['weak_edges',1,5,[z(1),s(.2,.01),s(3.6),s(.2,.01),z(1)]],['breath_edges',1,5,[z(.8),n(.2,.04),s(4),n(.2,.04),z(.8)]],['long_short',1,21,[z(1),s(20),z(1)]],['ratio12',1.2,21.2,[z(1.2),s(20),z(1.2)]],['half_second',.5,4.5,[z(.5),s(4),z(.5)]],['no_outer',0,6,[s(2),z(2),s(2)]]];for(const [id,start,end,parts] of cases){let seed=1;const noise=()=>{seed^=seed<<13;seed^=seed>>>17;seed^=seed<<5;return seed&1?1:-1;};const x=Float32Array.from(parts.flatMap(([t,v,k])=>Array.from({length:Math.round(t*sr)},(_,i)=>v*(k==='n'?noise():Math.sin(2*Math.PI*100*i/sr)))));const r=a.analyze(x,sr),e=Array.from(r.env).sort((x,y)=>x-y),p=q=>e[Math.floor(q*e.length)],front=start,back=x.length/sr-end,span=end-start,th=a.threshold(r.env),f=v=>+v.toFixed(6);console.log(JSON.stringify({id,front:f(front),back:f(back),span:f(span),rule:[front>=1-1e-9,back>=1-1e-9,front+back>=span*.15-1e-9].every(Boolean),p10:f(p(.1)),p90:f(p(.9)),threshold:Number.isFinite(th)?f(th):'Infinity',failed:r.failed===true,reason:r.reason||'-',detected:[r.speechStart,r.speechEnd],spoken:r.spoken,pauses:r.pauses.map(p=>p.length),errorMs:r.failed?null:[Math.round((r.speechStart-start)*1000),Math.round((r.speechEnd-end)*1000)]}));}"
```

검토한 파일 목록: `AGENTS.md`, `TEAM_BOARD.md`의 R21 줄, `apps/reading-coach/analysis.js`, `docs/eval/voice-evidence.md`, `docs/eval/calibration.md`, `docs/gpt/Q10-answer.md`, `docs/gpt/R18-review.md`, `voice/test-sentences.csv`, 코드 검토 스킬 지침이에요. **실행해 본 것:** Node v24.19.0 합성음 10조건 분석, B05 문자열 동등 비교, R18 문서 대조, Git 상태 확인이에요. 실제 녹음·청취·브라우저 검증과 파일 수정은 하지 않았어요.
