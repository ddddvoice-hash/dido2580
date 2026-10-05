# G6 · 성우 김디도의 따뜻한 AI 목소리 평가 키트 소개 문구 초안
> 실행 기록 머리(그대로 옮김): `model: gpt-6-astra` · `reasoning effort: high` · `sandbox: workspace-write [workdir, /tmp, $TMPDIR]` · `session id: 01a109a0-0efc-7921-b080-1a242736f10e`
날짜: 2026-10-05 · 브랜드: 성우 김디도 · 작성: GPT(외부 협력사) 초안, Claude 팀 검증 전

대표작 계획을 소개할 때 쓸 문구 초안이에요. 저장소에서 확인한 평가 자료와 앞으로 검증할 일을 구분했어요. 영문 요약에서도 브랜드는 **성우 김디도**로 표기해요. 대표작 방향은 계획 문서에 대표 승인 전으로 표시되어 있어요.

## 담백한 톤

### 한 줄 소개

성우 김디도는 AI 답변의 따뜻함을 기준과 근거로 살피고, 글과 목소리를 함께 검토하는 평가 키트를 만들고 있어요.

### 세 줄 소개

성우 김디도는 AI가 상대의 상황을 알아차리고, 정확하고 존중하는 말로 답하는지 살펴요.  
글 평가 기준표와 채점 도구, 한국어 상황 문항 초안을 바탕으로 판단의 근거를 남겨요.  
목소리의 속도와 쉼도 참고해, 내용에 어울리는 전달인지 살피는 작업을 이어가려 해요.

### 영문 요약

성우 김디도 is a voice actor developing a toolkit for evaluating warmth in AI responses, across text and voice. The current materials include a text evaluation rubric, a tool for recording scores and supporting evidence, and draft Korean scenarios. Planned voice evaluation will use speech pace and pauses to support human judgments about whether the delivery fits the message.

근거: [대표작 계획](../FLAGSHIP.md)의 구성과 [기준표](../../apps/warmth-scorer/rubric.json)의 `definition`, `criteria`, `voice_note`를 바탕으로 썼어요. 채점 근거 기록은 [채점기 코드](../../apps/warmth-scorer/app.js)의 `saveEvidence`, `toJsonlLine`에서 확인했어요. [상황 문항 파일](../eval/scenarios-v0.json)의 초안 표시도 확인했어요. 이 톤의 소개 문구에는 수량이나 성과 수치를 넣지 않았어요.

## 따뜻한 톤

### 한 줄 소개

성우 김디도는 상대의 말을 헤아리고 다음 걸음을 돕는 AI의 말과 목소리를 위해, 따뜻함을 살필 기준을 만들고 있어요.

### 세 줄 소개

성우 김디도는 상대의 상황을 정확히 이해하고, 그 사람이 선택할 수 있는 작은 다음 걸음을 건네는 답변을 지향해요.  
그 마음을 구체적으로 살필 수 있도록 기준표와 상황 문항 초안, 판단의 근거를 남기는 채점 도구를 준비했어요.  
목소리도 내용에 어울리는지 살피되, 듣는 사람의 마음을 수치로 단정하지 않으려 해요.

### 영문 요약

성우 김디도 is a voice actor working toward AI responses that acknowledge a person’s situation and offer a manageable next step, while respecting their choices. The toolkit brings together a rubric, draft scenarios, and a tool for recording the reasons behind each score. Planned voice evaluation will consider how the delivery fits the message, without claiming to measure a listener’s feelings.

근거: [기준표](../../apps/warmth-scorer/rubric.json)의 `definition`, `respect`, `next_step`, `voice_note`와 [채점기 코드](../../apps/warmth-scorer/app.js)의 근거 저장 기능을 바탕으로 썼어요. 상대가 실제로 위로받았다는 실험 결과가 아니라, 작업이 지향하는 방향을 소개해요. 이 톤의 소개 문구에는 수량이나 성과 수치를 넣지 않았어요.

## 전문적인 톤

### 한 줄 소개

성우 김디도는 AI 답변의 따뜻함을 평가할 기준표와 근거 기록 도구를 갖추고, 목소리 측정을 사람의 판단에 연결하는 평가 키트를 개발하고 있어요.

### 세 줄 소개

성우 김디도는 알아차림·정확함·존중·절제·다음 걸음의 5개 항목을 기준으로 AI 답변을 검토하고, 점수의 근거를 기록해요.  
한국어 상황 문항 60개는 대표 승인 전으로 표시된 평가용 초안으로 준비되어 있어요.  
목소리 측정값은 사람이 판단할 때 참고하는 근거로 쓰고, 실제 사람 평가 자료에서의 일치도와 개선 효과는 앞으로 검증하려 해요.

숫자 근거:

- **5개 항목**: [기준표](../../apps/warmth-scorer/rubric.json)의 `criteria` 배열 길이를 Python으로 직접 확인했어요. 항목 이름도 원문과 대조했어요.
- **60개 문항**: [상황 문항 파일](../eval/scenarios-v0.json)의 `items` 배열 길이와 고유 `id` 수를 Python으로 직접 확인했어요. `status`에 대표 승인 전으로 표시되어 있어요. 평가를 완료한 사례 수나 실제 서비스 답변 수를 뜻하지 않아요.

### 영문 요약

성우 김디도 is a voice actor developing a toolkit for evaluating warmth in AI dialogue. The text rubric covers five dimensions: recognition of the user’s situation, accuracy, respect, restraint, and actionable next steps. A scoring tool supports evidence recording, and 60 Korean evaluation scenarios are available as drafts marked as pending approval. Planned voice evaluation will use acoustic measurements to inform human judgment. Agreement in actual human ratings and evidence of improvement remain to be established.

숫자 근거:

- **five dimensions**: [기준표](../../apps/warmth-scorer/rubric.json)의 `criteria` 배열에서 확인한 **5개 항목**을 옮겼어요. 영문 항목명은 이 초안의 번역이에요.
- **60 Korean evaluation scenarios**: [상황 문항 파일](../eval/scenarios-v0.json)의 `items`에서 확인한 **60개 문항**을 뜻해요. 파일의 초안·승인 전 상태를 영문에도 함께 적었어요.

그 밖의 근거: [대표작 계획](../FLAGSHIP.md)의 목소리 측정, 평가자 신뢰도, 시연 사례 구성을 참고했어요. 일치도 계산 도구의 존재를 실제 사람 평가의 일치도가 입증된 것으로 표현하지 않았어요.

## 확인한 범위와 검증 전인 내용

- **확인한 것:** 기준표의 항목 이름과 개수, 상황 문항 파일의 문항 수·고유 ID 수·초안 표시, 채점기 코드의 근거 저장·내보내기 부분을 확인했어요.
- **문서 상태 차이:** 대표작 계획의 상황 문항 구성에는 현재 자료가 없다고 적힌 부분이 있지만, 저장소에는 상황 문항 파일이 있어요. 소개 문구는 해당 파일의 존재와 파일 안의 초안 표시를 기준으로 썼어요.
- **실행하지 않은 것:** 브라우저 조작, 사람 평가, 청취 실험은 이번 업무에서 하지 않았어요. 따뜻함이나 안전성의 개선 효과, 실제 평가자 일치도는 검증된 성과로 소개하지 않았어요.
- **추측:** 톤에 따라 독자가 느끼는 친근함이나 전문성이 달라질 수 있어요. 어떤 톤이 더 설득력 있는지는 독자 반응을 확인하지 않아 몰라요.
- **검토가 필요한 것:** 영문 요약의 자연스러움과 소개 자리에서의 전달 효과는 별도 검토가 필요해요. 대표작 방향 승인과 팀 검증을 마친 최종 홍보 문구는 아니에요.

검토한 파일 목록: `AGENTS.md`, `TEAM_BOARD.md`의 G6 업무와 적용 지침, `docs/FLAGSHIP.md`, `apps/warmth-scorer/rubric.json`의 관련 항목, `docs/eval/scenarios-v0.json`의 구조·상태, `apps/warmth-scorer/app.js`의 근거 저장·내보내기 부분, `docs/gpt/G6-pitch.md`예요. 실행해 본 것: Python으로 근거 JSON을 읽어 항목 수·문항 수·고유 ID 수를 집계했고, 소개 문구의 숫자와 대조했어요.
