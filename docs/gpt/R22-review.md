# R22 · GPT(아스트라) 결과 · 성우 김디도

> 실행 기록 머리(그대로 옮김):
> ```
> model: gpt-6-astra
> reasoning effort: high
> sandbox: read-only
> session id: 01a10fa8-425b-70a0-afe5-d81ce18f47fd
> ```
> 날짜: 2026-10-05 · 실행: 팀장이 `codex exec`로 돌림 · 아래는 GPT 답 원문(손대지 않음). 본문의 "모델 줄을 옮기지 못했다"는 말은 GPT가 자기 실행 기록을 볼 수 없어서이며, 위 머리가 실제 기록이에요.

**R22 검토 결과, 두 초안 모두 보완이 필요해요.** 비교 초안은 숨·억양 변화를 높은 점수의 조건으로 유도하는 부분이 있고, G14는 의미 전달과 자연스러움을 충분히 구분하는지 검증이 필요해요. 소개 페이지는 초안임을 밝히지만, 링크 모음에는 같은 제한을 추가해야 해요.

G14를 먼저 읽고 비교 초안을 읽었어요. 아래의 **확인**은 문서·코드 대조 결과이고, **추측**은 예상되는 평가 편향이에요. 이번 실행의 `model:`·`reasoning effort:`·`sandbox:` 기록 원문은 제공되지 않아 임의로 적지 않았어요.

표에서 **독립안**은 `docs/gpt/G14-humanlike-rubric.md`, **비교안**은 `docs/eval/humanlike-voice-rubric-draft.md`를 뜻해요.

| 번호 | 안건 | 의견(동의·반대·보완) | 근거 | 제안 |
|---|---|---|---|---|
| R22-1 | 숨을 넣어야 높은 점수를 받는 구조 | **반대해요** | **확인:** [비교안:29](/C:/Users/ddddv/dido2580/docs/eval/humanlike-voice-rubric-draft.md:29)은 숨이 없으면 0점인데, [비교안:39](/C:/Users/ddddv/dido2580/docs/eval/humanlike-voice-rubric-draft.md:39)은 원고에 없는 숨을 결함으로 표시해요. [독립안:90](/C:/Users/ddddv/dido2580/docs/gpt/G14-humanlike-rubric.md:90)은 숨의 유무를 고득점 조건으로 삼지 않아요. **추측:** 불필요한 숨 삽입이나 정상적인 숨의 결함 표시를 유도할 수 있어요. | 숨의 유무보다 들리는 숨의 위치·연결을 판단해요. 원고에 없다는 이유만으로 숨을 결함으로 표시하지 않아요. |
| R22-2 | 변화가 많아야 자연스럽다는 유도 | **반대해요** | **확인:** [비교안:30](/C:/Users/ddddv/dido2580/docs/eval/humanlike-voice-rubric-draft.md:30)의 ‘고르지 않게’, [비교안:31](/C:/Users/ddddv/dido2580/docs/eval/humanlike-voice-rubric-draft.md:31)의 ‘문장마다 무늬가 다름’이 높은 점수의 방향이에요. [독립안:34](/C:/Users/ddddv/dido2580/docs/gpt/G14-humanlike-rubric.md:34)·[78](/C:/Users/ddddv/dido2580/docs/gpt/G14-humanlike-rubric.md:78)은 일정함이나 음높이 폭 자체를 감점하지 않아요. **추측:** 필요한 반복이나 담담한 발화를 불리하게 볼 수 있어요. | ‘변화가 있는가’를 ‘변화하거나 유지되는 방식이 문맥에 맞는가’로 바꿔요. |
| R22-3 | 한국어 말끝을 닫힘·열림으로 단순화 | **반대해요** | **확인:** [비교안:32](/C:/Users/ddddv/dido2580/docs/eval/humanlike-voice-rubric-draft.md:32)은 ‘서술은 닫히고 물음은 열리는’ 방향을 제시해요. [독립안:56](/C:/Users/ddddv/dido2580/docs/gpt/G14-humanlike-rubric.md:56)·[64](/C:/Users/ddddv/dido2580/docs/gpt/G14-humanlike-rubric.md:64)은 연결어미·차례 넘김을 포함하고 상승·하강 고정 규칙을 막아요. [voice-evidence.md:91](/C:/Users/ddddv/dido2580/docs/eval/voice-evidence.md:91)에도 같은 방향 유도를 고친 기록이 있어요. | 기존 수정 원칙을 유지해요. 끝냄·이어감·차례 넘김이 주어진 상황에서 어떻게 들렸는지 묻고, 특정 억양 방향을 정답으로 주지 않아요. |
| R22-4 | 두 초안 모두 부족한 한국어 맥락 구분 | **보완해요** | **확인:** [비교안:32](/C:/Users/ddddv/dido2580/docs/eval/humanlike-voice-rubric-draft.md:32), [독립안:56](/C:/Users/ddddv/dido2580/docs/gpt/G14-humanlike-rubric.md:56)·[70](/C:/Users/ddddv/dido2580/docs/gpt/G14-humanlike-rubric.md:70)에 기능·문맥은 있지만, 같은 어미가 정보 질문·재확인·동의 요청으로 쓰이는 경우와 강조 위치가 바뀌는 경우를 나눈 검증 문항은 없어요. | **추측·제안:** 같은 문장을 다른 앞뒤 대화에 놓고 비교해요. 어미의 종류, 말끝 길이·높이·크기, 강조 위치를 따로 기록해요. 제안한 구분이 실제 판정에 도움이 되는지는 청취로 확인해요. |
| R22-5 | 겹치는 항목과 중복 반영 | **보완해요** | **확인:** [비교안:29](/C:/Users/ddddv/dido2580/docs/eval/humanlike-voice-rubric-draft.md:29)의 6항목은 독립안의 속도·쉼을 합치고, 호흡·음색을 나눈 구성이에요. 억양·말끝·내용 일치는 양쪽에 있어요. 같은 끊김이 여러 항목과 결함 표시에 걸릴 수 있는데, 비교안에는 [독립안:137](/C:/Users/ddddv/dido2580/docs/gpt/G14-humanlike-rubric.md:137)의 우선 기록 규칙이 없어요. | 현상마다 우선 기록 항목을 정해요. 다른 항목에도 영향을 줬다면 별도 이유를 남겨요. 항목 구성과 가중치가 달라 두 초안의 합계를 직접 비교하지 않아요. |
| R22-6 | 비교안에 부족한 발음·연음 평가 | **보완해요** | **확인:** [비교안:37](/C:/Users/ddddv/dido2580/docs/eval/humanlike-voice-rubric-draft.md:37)은 오독을 결함으로 기록하지만, [독립안:110](/C:/Users/ddddv/dido2580/docs/gpt/G14-humanlike-rubric.md:110)의 발음·음절 연결 0·1·2점 구분은 없어요. 알아들을 수 있어도 받침 연결 등이 어색한 경우를 어디에 기록할지 불분명해요. | 독립안의 발음 항목을 검토해요. 허용할 읽기와 구어 축약을 먼저 정하고, 오독 여부와 연결의 자연스러움을 구분해요. |
| R22-7 | 독립안에서 덜 드러나는 음질 결함 | **보완해요** | **확인:** [비교안:33](/C:/Users/ddddv/dido2580/docs/eval/humanlike-voice-rubric-draft.md:33)은 금속성·지글거림·뭉개짐을 명시해요. [독립안:88](/C:/Users/ddddv/dido2580/docs/gpt/G14-humanlike-rubric.md:88)은 급격한 음색 전환·단절 중심이에요. 반대로 비교안의 ‘한두 번’은 결함 강도·길이와의 관계가 정해져 있지 않아요. | 독립안에 지속되는 음질 이상도 관찰 단서로 넣어요. 횟수만으로 점수를 정하지 않고 구간·지속시간·청취 영향을 기록해요. 원인이 합성인지 녹음·재생인지 확인되지 않으면 추측으로 남겨요. |
| R22-8 | 내용 적합성과 사람 같은 소리의 혼합 | **보완해요** | **확인:** [비교안:34](/C:/Users/ddddv/dido2580/docs/eval/humanlike-voice-rubric-draft.md:34)은 특정 내용과 말투 조합을 바로 0점으로 정해요. [독립안:98](/C:/Users/ddddv/dido2580/docs/gpt/G14-humanlike-rubric.md:98)은 상대·상황을 보지만, [138](/C:/Users/ddddv/dido2580/docs/gpt/G14-humanlike-rubric.md:138)의 합계에는 이 항목도 들어가요. **추측:** 상황에 부적절한 말투와 합성음의 부자연스러움이 같은 낮은 점수로 섞일 수 있어요. | 내용·상황 적합성을 별도 결과로 보여 줘요. 사람 같은 정도의 합계에 넣을지는 검증 전까지 보류해요. 기존 기준표는 수정하지 않아요. |
| R22-9 | 독립안도 이해 가능성에 치우친 점수 설명 | **보완해요** | **확인:** [독립안:32](/C:/Users/ddddv/dido2580/docs/gpt/G14-humanlike-rubric.md:32)·[60](/C:/Users/ddddv/dido2580/docs/gpt/G14-humanlike-rubric.md:60)·[74](/C:/Users/ddddv/dido2580/docs/gpt/G14-humanlike-rubric.md:74)은 0점을 의미·기능·핵심 파악의 어려움에 연결해요. **추측:** 뜻은 또렷하지만 전 구간이 부자연스러운 소리가 1점에 몰릴 수 있어요. | ‘뜻을 알아듣는가’와 ‘얼마나 지속적으로 어색한가’를 구분해요. 점수 경계는 실제 청취 사례로 조정하고, 두 초안의 설명을 아직 검증된 기준으로 소개하지 않아요. |
| R22-10 | 비교안에 부족한 보류·측정 한계·판단 순서 | **보완해요** | **확인:** [비교안:18](/C:/Users/ddddv/dido2580/docs/eval/humanlike-voice-rubric-draft.md:18)은 수치를 점수로 바꾸지 않는다고 하지만, 보류와 최초 판단 저장은 명시하지 않아요. 독립안에는 [22](/C:/Users/ddddv/dido2580/docs/gpt/G14-humanlike-rubric.md:22)·[126](/C:/Users/ddddv/dido2580/docs/gpt/G14-humanlike-rubric.md:126)·[136](/C:/Users/ddddv/dido2580/docs/gpt/G14-humanlike-rubric.md:136)에 있어요. [profile.js:215](/C:/Users/ddddv/dido2580/apps/voice-check/profile.js:215)·[222](/C:/Users/ddddv/dido2580/apps/voice-check/profile.js:222)의 말끝 값도 실제 상승·하강 궤적이 아니에요. | 보류를 0점과 구분해요. 측정 실패·후보 없음도 따로 기록해요. [voice-evidence.md:75](/C:/Users/ddddv/dido2580/docs/eval/voice-evidence.md:75)처럼 평가 묶음의 첫 판단을 모두 저장한 뒤 수치를 공개하도록 양쪽에 명시해요. |
| R22-11 | 사람 녹음 비교와 맞히기 시험의 차이 | **보완해요** | **확인:** [비교안:9](/C:/Users/ddddv/dido2580/docs/eval/humanlike-voice-rubric-draft.md:9)·[43](/C:/Users/ddddv/dido2580/docs/eval/humanlike-voice-rubric-draft.md:43)은 사람 녹음 비교와 별도 맞히기 시험을 제안해요. [독립안:7](/C:/Users/ddddv/dido2580/docs/gpt/G14-humanlike-rubric.md:7)은 출처 맞히기를 제외해요. 비교안 [45](/C:/Users/ddddv/dido2580/docs/eval/humanlike-voice-rubric-draft.md:45)는 50% 근처를 해석하지만 [47](/C:/Users/ddddv/dido2580/docs/eval/humanlike-voice-rubric-draft.md:47)은 설계 전 해석을 제한해요. | 두 과제를 분리하는 데 동의해요. 독립안에는 사람 녹음을 참고할 경우의 운영 절차를 보완해요. 비교안은 설계 확정 전에는 비율을 기록하는 데 그치도록 45·47줄을 일치시켜요. |
| R22-12 | 공통 윤리 원칙과 비교안의 누락 | **동의하되 보완해요** | **확인:** [비교안:19](/C:/Users/ddddv/dido2580/docs/eval/humanlike-voice-rubric-draft.md:19)·[46](/C:/Users/ddddv/dido2580/docs/eval/humanlike-voice-rubric-draft.md:46)은 AI임을 숨기지 않는 원칙과 시험 안내가 있어요. [독립안:149](/C:/Users/ddddv/dido2580/docs/gpt/G14-humanlike-rubric.md:149)·[150](/C:/Users/ddddv/dido2580/docs/gpt/G14-humanlike-rubric.md:150)에 있는 공개 범위·복제 동의 구분은 비교안에 없어요. | 비교용 사용, 복제·변환, 외부 공개의 허용 범위를 각각 확인하는 절차를 연결해요. 높은 청취 점수를 진정성·신뢰성의 증거로 쓰지 않는 원칙도 유지해요. |

소개 문구는 다음처럼 판단해요.

| 번호 | 안건 | 의견(동의·반대·보완) | 근거 | 제안 |
|---|---|---|---|---|
| R22-13 | ‘성우 김디도의 인간에 가까운 AI 목소리 평가 키트’라는 이름 | **방향에는 동의해요** | **확인:** [TEAM_BOARD.md:220](/C:/Users/ddddv/dido2580/TEAM_BOARD.md:220)의 명명 지시와 일치해요. [template.html:99](/C:/Users/ddddv/dido2580/docs/showcase/template.html:99)·[106](/C:/Users/ddddv/dido2580/docs/showcase/template.html:106)은 초안과 미완료 항목을 밝혀요. 이름 자체가 성능 달성을 주장한다고 보기는 어려워요. | 이름은 유지하되 ‘초안·검증 전’을 가까이 표시해요. |
| R22-14 | 소개 페이지의 ‘얼마나 가까운지 판단’ | **보완해요** | **확인:** [template.html:100](/C:/Users/ddddv/dido2580/docs/showcase/template.html:100)·[101](/C:/Users/ddddv/dido2580/docs/showcase/template.html:101)은 판단·근거 기록을 현재형으로 설명하지만, [106](/C:/Users/ddddv/dido2580/docs/showcase/template.html:106)은 비교 음성과 독립 채점 결과가 없다고 밝혀요. **추측:** 검증된 척도가 이미 작동하는 것으로 읽힐 수 있어요. | 머리말을 ‘AI 목소리를 듣고 어색한 구간과 이유를 기록할 평가 키트를 만들고 있어요’로 좁혀요. ‘기록해요’보다 ‘기록하도록 설계하고 있어요’가 현재 상태에 맞아요. |
| R22-15 | 링크 모음의 완료된 키트처럼 보이는 설명 | **보완이 필요해요** | **확인:** [index.html:49](/C:/Users/ddddv/dido2580/docs/links/index.html:49)·[52](/C:/Users/ddddv/dido2580/docs/links/index.html:52)에는 초안·검증 전 표시가 없어요. 실제 참여 링크 설명인 [61](/C:/Users/ddddv/dido2580/docs/links/index.html:61)은 말의 내용 채점이에요. **추측:** 목소리 평가에 바로 참여할 수 있다고 오해할 수 있어요. | 첫 설명에서 목소리 평가 준비 상태와 현재 참여 가능한 내용 채점을 함께 밝혀요. |
| R22-16 | 경력 기간 표현의 근거 | **보완해요** | **확인:** [template.html:101](/C:/Users/ddddv/dido2580/docs/showcase/template.html:101)과 [index.html:82](/C:/Users/ddddv/dido2580/docs/links/index.html:82)의 기간 표현은 [FLAGSHIP.md:19](/C:/Users/ddddv/dido2580/docs/FLAGSHIP.md:19)에도 있어요. 다만 같은 표현의 반복만으로 정확한 경과 기간이 검증되지는 않아요. | 경과 기간과 ‘몇 년 차’를 구분해요. 이번 검토에서 시작 월일까지 확인하지 못했으므로, 소개 문구는 ‘성우 김디도의 낭독 경험을 바탕으로’라고 쓰면 근거 범위를 넘지 않아요. |

링크 모음의 대체 문구는 이렇게 제안해요.

> 성우 김디도의 인간에 가까운 AI 목소리 평가 키트를 만들고 있어요. 사람이 듣고 어색한 구간과 이유를 기록할 목소리 기준표는 초안이며, 비교 음성과 독립 채점 결과는 아직 준비 중이에요. 현재 참여할 수 있는 베타는 답변 내용의 따뜻함 채점이에요.

어떤 파일도 수정하지 않았어요. 검토 중 작업 폴더 상태가 바뀌었고, 마지막 확인에서 `TEAM_BOARD.md`에 병합 충돌 표시가 있었어요. 충돌은 수정하지 않았어요.

검토한 파일 목록: `AGENTS.md`, `TEAM_BOARD.md` 해당 업무·관련 줄, `docs/gpt/G14-humanlike-rubric.md`, `docs/eval/humanlike-voice-rubric-draft.md`, `docs/showcase/template.html`, `docs/links/index.html`, `docs/eval/voice-evidence.md`, `apps/voice-check/profile.js`, `apps/warmth-scorer/rubric.json` 관련 부분, `docs/eval/calibration.md` 관련 줄, 검색 일치 부분인 `docs/FLAGSHIP.md`·`docs/positioning/strengths-claude.md`·`docs/gpt/Q12-answer.md`·`docs/showcase/index.html` · 실행해 본 것: 읽기·문구 검색·줄 번호 대조·`git status --short`예요. 파일 수정, 음성 분석·청취·채점 실험, 브라우저 동작 검사는 하지 않았어요.
