# R2 · GPT(아스트라) 결과 · 성우 김디도

> 실행 기록 머리(그대로 옮김):
> ```
> model: gpt-6-astra
> reasoning effort: high
> sandbox: read-only
> session id: 01a10992-92fd-70f3-ab8c-8bee7a1db679
> ```
> 날짜: 2026-10-05 · 실행: 팀장이 `codex exec`로 돌림 · 아래는 GPT 답 원문(손대지 않음). 본문의 "모델 줄을 옮기지 못했다"는 말은 GPT가 자기 실행 기록을 볼 수 없어서이며, 위 머리가 실제 기록이에요.

**성우 김디도 — R2 리뷰예요.** `e487e29`의 비교 로직에서 보완할 점 4건을 확인했어요. 파일은 수정하지 않았어요.

실행 기록의 `model:`·`reasoning effort:`·`sandbox:` 원문은 제공되지 않아 전사하지 못했어요. 모델 이름은 추측해 적지 않았어요.

| 번호 | 파일:줄 | 문제 | 왜 문제인가 | 제안 |
|---|---|---|---|---|
| R2-1 | [app.js:272](/C:/Users/ddddv/dido2580/apps/voice-studio/app.js:272), [reference.js:25](/C:/Users/ddddv/dido2580/apps/voice-studio/reference.js:25) | **[중간] 짧은 발화에도 25% 기준을 일률 적용해요.** | 019번 기준 0.20초에 0.26초를 입력하면, 음높이가 같고 차이가 0.06초뿐이어도 ‘차이 큼’이 표시되는 것을 재현했어요. **추측:** 짧은 캐릭터 발화의 자연스러운 변화를 과하게 강조할 수 있어요. | 상대 차이와 절대 시간 차이를 함께 적용하고, 짧은 발화는 수치만 보여 주세요. 임계값은 실제 연기 비교로 정해 주세요. |
| R2-2 | [app.js:252](/C:/Users/ddddv/dido2580/apps/voice-studio/app.js:252) | **[중간] ‘말한 길이’에 중간 쉼도 포함돼요.** | `an.duration`은 첫 말소리부터 마지막 말소리까지의 길이예요. 합성음에서 실제 소리 구간은 모두 1초인데, 중간 쉼만 바꾸자 1.2초→1.6초로 측정되어 ‘차이 큼’이 표시됐어요. | ‘중간 쉼을 포함한 발화 길이’로 명시하거나, 말소리 길이와 쉼을 분리해 주세요. 측정 정의를 바꾸면 원래 녹음의 기준값도 함께 다시 산출해야 해요. |
| R2-3 | [tools/build-profile.js:13](/C:/Users/ddddv/dido2580/apps/voice-studio/tools/build-profile.js:13) | **[중간] 잘라내기 경계만 확인해 의존성 누락을 놓쳐요.** | 메모리에서 `F0_HOP_MS`·`F0_WIN_MS` 선언을 시작 경계 앞으로 옮겼어요. 원본은 정상 측정했지만 생성본은 `--check`를 통과하고도 `F0_WIN_MS is not defined`로 실패했어요. 앱에서는 예외를 삼켜 비교가 사라져요. | 측정 함수를 공용 모듈로 분리해 주세요. 생성 방식을 유지한다면 브라우저 환경에서 생성본을 실행하고, 합성음 측정 결과를 원본과 비교하는 검사를 추가해 주세요. |
| R2-4 | [tools/build-profile.js:35](/C:/Users/ddddv/dido2580/apps/voice-studio/tools/build-profile.js:35) | **[낮음] 줄바꿈 차이를 오래된 생성본으로 오인해요.** | 현재 원본은 LF, 생성본은 CRLF여서 직접 실행한 `--check`가 실패했어요. 줄바꿈을 정규화하면 내용은 일치했어요. | 비교 전에 줄바꿈을 정규화하거나, 저장소에서 관련 파일의 줄바꿈을 통일해 주세요. |

3반음 기준도 연기 의도와 무관하게 강조 표시를 만들어요. 다만 실제 녹음을 듣지 않았으므로, 이 기준이 캐릭터 연기를 부당하게 평가한다는 판단은 **추측**이에요. 연기 품질 기준으로 검증됐다고 볼 근거는 검토 범위에서 확인하지 못했어요.

잘된 점은 비교 결과가 통과·반려 판정에 영향을 주지 않고, 경계가 불확실한 12줄은 강조에서 제외하며, 의도한 연기인지 직접 들어 보도록 안내한다는 점이에요.

검증에서는 문법 검사 2건과 기존 기준값 검사 4항목이 통과했어요. 기존 테스트의 하위 프로세스 실행은 `EPERM`으로 막혔어요. 브라우저·실제 녹음 청취 검증은 하지 않았어요.

검토한 파일 목록: `AGENTS.md`, `TEAM_BOARD.md`의 R2, `apps/voice-studio/{app.js,reference.js,profile-browser.js,index.html,README.md,tools/build-profile.js,tests/reference.test.js,tests/browser.test.js,tests/parity.test.js}`, `apps/voice-check/profile.js`, `apps/reading-coach/analysis.js`, `.github/workflows/tests.yml` 관련 부분 · 실행해 본 것: 커밋 비교, 문법 검사, 기준값 테스트, 생성본 `--check`, 메모리 내 짧은 발화·쉼 변경·구조 변경 재현, 줄바꿈 비교예요.
