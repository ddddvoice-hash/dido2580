# R25 · GPT(아스트라) 결과 · 성우 김디도

> 실행 기록 머리(그대로 옮김):
> ```
> model: gpt-6-astra
> reasoning effort: high
> sandbox: read-only
> session id: 01a1107b-e151-7e91-96e0-3f274f73140a
> ```
> 날짜: 2026-10-05 · 실행: 팀장이 `codex exec`로 돌림 · 아래는 GPT 답 원문(손대지 않음). 본문의 "모델 줄을 옮기지 못했다"는 말은 GPT가 자기 실행 기록을 볼 수 없어서이며, 위 머리가 실제 기록이에요.

**성우 김디도 · R25 협의 의견이에요.**

**두 축을 나누는 방향에는 동의해요. 다만 현재 초안은 NUM-R·S·U 반려 결정이 충분히 반영되지 않았고, C·P의 반려 조건은 좁으며, 치명 조건은 넓어요.** 반려는 납품 판정이고 치명은 심각도이므로 구분해야 해요.

Q13을 먼저 읽은 뒤 두 문서를 비교했어요. 이번 실행의 `model:`·`reasoning effort:`·`sandbox:` 머리말 원문은 제공받지 못했어요. Q13의 과거 실행 기록을 이번 기록으로 옮기지는 않았어요.

아래에서 **독립안**은 `docs/gpt/Q13-answer.md`, **기준표**는 `docs/eval/humanlike-voice-rubric-draft.md`, **사례안**은 `docs/case/numbers-case-plan.md`예요.

| 번호 | 안건 | 의견(동의·반대·보완) | 근거 | 제안 |
|---|---|---|---|---|
| R25-1 | **다른 점: NUM-R·S·U 반려** | **반대해요. 대표 결정과 불일치해요.** | [기준표:52](C:/Users/ddddv/dido2580/docs/eval/humanlike-voice-rubric-draft.md:52), [사례안:16](C:/Users/ddddv/dido2580/docs/case/numbers-case-plan.md:16)은 값이 유지되는 수사 선택을 자연스러움 축으로 넘겨요. [독립안:34](C:/Users/ddddv/dido2580/docs/gpt/Q13-answer.md:34)의 R·S·U 처리와 [대표 결정:229](C:/Users/ddddv/dido2580/TEAM_BOARD.md:229)은 오류가 확정되면 반려해요. | **“확정된 정답·허용 읽기를 벗어난 NUM-R·S·U는 값 보존 여부와 무관하게 반려해요”**로 명시해요. 의미가 보존된 오류를 반려하더라도 자동으로 치명이라고 하지는 않아요. |
| R25-2 | **다른 점: C·P 반려 범위** | **보완해요. 현재 조건은 좁아요.** | [기준표:53](C:/Users/ddddv/dido2580/docs/eval/humanlike-voice-rubric-draft.md:53), [사례안:17](C:/Users/ddddv/dido2580/docs/case/numbers-case-plan.md:17)은 끊는 자리 때문에 **다른 숫자**로 들리는 경우만 명시해요. [독립안:37](C:/Users/ddddv/dido2580/docs/gpt/Q13-answer.md:37)은 단위·연결 대상·의도 오해, 과도한 이해 노력, 합의한 자연스러움 기준 미달도 포함해요. | C와 P 모두에 반려 경로를 둬요. 숫자를 맞게 받아써도 문장 의도를 오해하거나 이해에 상당한 노력이 들 수 있어요. 자연스러움만으로 반려하려면 납품 조건과 구체적 결함을 사전에 정해요. 이 적용안은 **추측을 포함한 운영 제안**이에요. |
| R25-3 | **치명으로 올리는 조건** | **기준표는 넓고, 독립안 표현도 보완이 필요해요.** | [기준표:52](C:/Users/ddddv/dido2580/docs/eval/humanlike-voice-rubric-draft.md:52)의 “안전·돈·건강이 걸린 숫자는 치명”은 분야만으로 심각도를 정해요. MQM은 **전체 내용의 목적 부적합 또는 심각한 피해 위험**을 기준으로 삼아요. [독립안:66](C:/Users/ddddv/dido2580/docs/gpt/Q13-answer.md:66)의 “전체 기능 실패”도 목적 부적합을 기능 고장으로 좁혀 읽힐 수 있어요. [MQM 원문](https://www.themqm.org/guidance/values-and-scores/) | 평가 대상과 사용 맥락을 정하고, 오류가 심각한 피해 위험이나 **평가 대상 전체의 목적 부적합**을 만드는 근거를 적어요. 금액·건강 문항이라는 이유, 기계 같은 인상, 낮은 점수만으로 치명 처리하지 않아요. 치명 근거가 확인되면 다수결을 기다리지 않아요. |
| R25-4 | **MQM 인용: 가중치와 적용 범위** | **보완해요. 숫자는 맞지만 고정 규정처럼 보일 수 있어요.** | [기준표:52](C:/Users/ddddv/dido2580/docs/eval/humanlike-voice-rubric-draft.md:52)의 25·5·1·0은 MQM이 제시한 **예시 배점**이에요. [사례안:19](C:/Users/ddddv/dido2580/docs/case/numbers-case-plan.md:19)의 정확성 축에만 적용한다는 제한도 자체 선택이에요. MQM 심각도는 문체·유창성 등에도 적용돼요. [MQM 원문](https://www.themqm.org/guidance/values-and-scores/) | “MQM 예시 가중치를 참고한 자체안”이라고 표시해요. 자연스러움 점수를 별도로 유지하되 C·P에도 영향 심각도를 기록할 수 있게 해요. |
| R25-5 | **ISO 5060 인용** | **오류 유형·벌점 방식이라는 설명에는 동의해요. 적용 범위는 보완해요.** | [기준표:52](C:/Users/ddddv/dido2580/docs/eval/humanlike-voice-rubric-draft.md:52)의 설명은 공식 개요와 맞아요. 다만 ISO 5060:2024는 **번역 결과에 대한 사람의 평가** 지침이에요. 이번에도 공개 개요만 확인했고 유료 본문의 세부 조항은 확인하지 못했어요. [ISO 공식 개요](https://www.iso.org/standard/80701.html) | [독립안:25](C:/Users/ddddv/dido2580/docs/gpt/Q13-answer.md:25)처럼 “분류·평가 설계를 참고했으며 한국어 숫자 음성의 반려선을 직접 규정하지 않아요”라고 한계를 명시해요. |
| R25-6 | **ITU-T P.85 인용** | **취지에 동의해요. 정확한 평가 항목과 판본을 붙여요.** | [기준표:53](C:/Users/ddddv/dido2580/docs/eval/humanlike-voice-rubric-draft.md:53), [사례안:10](C:/Users/ddddv/dido2580/docs/case/numbers-case-plan.md:10)의 분리 취지는 타당해요. P.85는 정보 이해 과제와 청취 노력·발음·수용성 등을 평가해요. 2013년 추가 부록은 쉼·억양·강세를 별도로 다루지만 **오디오북 대상의 비규범적 부록**이에요. [P.85 본문](https://www.itu.int/rec/dologin_pub.asp?id=T-REC-P.85-199406-I%21%21PDF-E&lang=e&type=items), [추가 부록 I](https://www.itu.int/rec/dologin_pub.asp?id=T-REC-P.85-201303-I%21Amd1%21PDF-E&lang=e&type=items) | “이해 과제와 주관적 음성 품질을 분리하는 절차를 참고해요”로 정확히 써요. 0·1·2점이나 C·P 반려선을 P.85가 정한 값처럼 표시하지 않아요. |
| R25-7 | **SSML 인용** | **해석 방식 구분의 참고로는 동의해요. 심각도 근거로는 부족해요.** | [기준표:52](C:/Users/ddddv/dido2580/docs/eval/humanlike-voice-rubric-draft.md:52)에 연결한 `say-as`는 텍스트 해석을 돕는 단서예요. SSML 1.1은 가능한 속성값 전체를 열거하지 않으며, 한국어 정답이나 반려 등급을 정하지 않아요. [SSML 1.1 §3.1.9](https://www.w3.org/TR/speech-synthesis11/#S3.1.9) | [독립안:28](C:/Users/ddddv/dido2580/docs/gpt/Q13-answer.md:28)처럼 읽기 해석은 `say-as`, 쉼은 `break`, 운율은 `prosody`를 참고했다고 한정해요. 출력의 적절성은 별도 청취로 확인해요. |
| R25-8 | **다른 점: 받아쓰기 확인 절차** | **보완해요. 확인 방법이 재현 가능할 만큼 정해지지 않았어요.** | [기준표:53](C:/Users/ddddv/dido2580/docs/eval/humanlike-voice-rubric-draft.md:53), [사례안:17](C:/Users/ddddv/dido2580/docs/case/numbers-case-plan.md:17)은 평가 인원·첫 청취·재청취·오답 원인 처리 규칙이 없어요. [독립안:48](C:/Users/ddddv/dido2580/docs/gpt/Q13-answer.md:48)은 첫 응답 보존과 학습 효과 통제를 제안해요. | 원고를 모르는 청취자에게 처음 들은 숫자·단위·뜻을 받고, 이해 노력과 운율은 따로 평가해요. 반복 청취 결과를 구분하고 원고 모호함·재생 문제는 보류해요. 두 검수자의 합의를 일반 청취자의 이해 검증으로 대신하지 않아요. |
| R25-9 | **독립안 자체의 약점: 수치 경계** | **보완해요. 12명·3명·8명을 확정 기준으로 옮기면 안 돼요.** | [독립안:45](C:/Users/ddddv/dido2580/docs/gpt/Q13-answer.md:45), [독립안:60](C:/Users/ddddv/dido2580/docs/gpt/Q13-answer.md:60)의 인원과 투표 경계는 검증 전 제안이에요. P.808의 자극당 최소 8명·조건당 96표는 ACR 크라우드 평가 설계 권고이며, 이 반려선을 보증하지 않아요. [P.808 §6.3.1.3](https://www.itu.int/rec/dologin_pub.asp?id=T-REC-P.808-202106-I%21%21PDF-E&lang=e&type=items) | **추측·시범 운영값** 표시를 유지해요. 허용 음원과 결함 음원으로 오반려·누락을 확인한 뒤 경계를 정해요. 두 안의 0~2점과 1~5점도 단순 환산하지 않아요. |
| R25-10 | **같은 점: 정확성과 자연스러움 분리** | **동의해요. 유지해요.** | [기준표:50](C:/Users/ddddv/dido2580/docs/eval/humanlike-voice-rubric-draft.md:50), [사례안:19](C:/Users/ddddv/dido2580/docs/case/numbers-case-plan.md:19), [독립안:51](C:/Users/ddddv/dido2580/docs/gpt/Q13-answer.md:51)은 숫자가 맞는 것만으로 자연스러움을 통과시키지 않아요. | 두 축을 유지하고 **이해 노력**을 추가 확인해요. 이해 노력은 별도 평가 대상이라는 근거가 있어요. [P.800 §B.4.5](https://www.itu.int/rec/dologin_pub.asp?id=T-REC-P.800-199608-I%21%21PDF-E&lang=e&type=items) |
| R25-11 | **같은 점: 허용 읽기와 취향 차이 보호** | **동의해요. 미확정 문항 처리를 보완해요.** | [기준표:24](C:/Users/ddddv/dido2580/docs/eval/humanlike-voice-rubric-draft.md:24), [사례안:57](C:/Users/ddddv/dido2580/docs/case/numbers-case-plan.md:57), [독립안:40](C:/Users/ddddv/dido2580/docs/gpt/Q13-answer.md:40)은 개인 취향과 미확정 정답을 오류로 단정하지 않아요. | “확인 필요” 문항은 반려 집계에서 빼되 통과로 세지 말고, 보류 수와 사유를 별도로 보고해요. |
| R25-12 | **판정 기록과 적용 단위** | **보완해요. 반려·치명·점수를 각각 남겨요.** | [사례안:21](C:/Users/ddddv/dido2580/docs/case/numbers-case-plan.md:21)은 “점수/심각도”로 묶고 납품 판정 칸이 없어요. [기준표:60](C:/Users/ddddv/dido2580/docs/eval/humanlike-voice-rubric-draft.md:60)에도 분리가 필요해요. [독립안:14](C:/Users/ddddv/dido2580/docs/gpt/Q13-answer.md:14)는 이를 구분해요. | 카드에 **오류 코드·자연스러움 점수·심각도·납품 판정·근거**를 따로 둬요. 판정 단위는 해당 문장·음원으로 명시하고, 같은 결함의 C·P 중복 기록을 중복 벌점으로 만들지 않아요. |

**합의 문구 제안이에요.** “NUM-R·S·U는 오류 확정 시 반려해요. NUM-C·P는 의미·의도 전달 실패, 과도한 이해 노력, 사전에 합의한 자연스러움 요건 미달을 확인해 반려 여부를 정해요. 치명은 별도의 영향 근거로 판단해요. 국제 자료에서 평가 원칙과 방법을 참고했으며, 한국어 적용과 수치 경계는 추측을 포함한 자체 운영안으로 검증해요.”

검토한 파일 목록: `AGENTS.md`, `TEAM_BOARD.md`의 R25·Q13·대표 결정 부분, `docs/gpt/Q13-answer.md`, `docs/eval/humanlike-voice-rubric-draft.md`, `docs/case/numbers-case-plan.md`예요. | 실행해 본 것: 파일 읽기·줄 번호 대조·국제 자료 웹 원문 확인·작업 상태 조회예요. 음원 청취·받아쓰기 실험·통계 검증은 하지 않았고, 어떤 파일도 수정하지 않았어요.
