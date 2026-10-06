# 성우 김디도 AI 비서

성우 김디도의 목소리로 말하는 AI 음성 비서예요. 설계: `docs/assistant/plan.md`.

## 켜기

`apps/start-assistant.cmd`를 두 번 누르면 비서가 앱 창으로 열려요(작업실 첫 화면 6번 카드로도 갈 수 있어요). 이 컴퓨터 안(127.0.0.1:8770)에서만 열려요.

| 탭 | 하는 일 |
|---|---|
| 대화 | 말(Alt+Q)이나 글로 묻고 소리로 들어요. 다시 듣기 Alt+W, 멈추기 Esc |
| 대본 점검 | 대본을 붙여 넣으면 숫자가 든 문장마다 읽는 법을 보여 줘요 |
| 숫자 읽기 | 문장 하나를 사람이 읽듯 풀어 들려줘요 |

## 층 (바꿔 끼우기)

| 층 | 파일 | 지금 |
|---|---|---|
| 듣기 | `index.html` (브라우저 음성 인식, 엣지·크롬) | 됨 |
| 생각 | `brain.py` | AI 연결이 있으면 Claude(`claude-opus-5-5`, 거절 시 서버 쪽 대체 모델 사용), 없으면 오프라인 모드(시각·숫자 읽기·대본 점검) |
| 말 다듬기 | `korean_numbers.py` | 성우 김디도 숫자 사례 20문장 통과 |
| 목소리 | `tts.py` | `DIDO_TTS=browser`(기본, 대표 목소리 아님) 또는 `DIDO_TTS=http` + `DIDO_TTS_URL`(목소리 서버) |
| 목소리 서버 | `tts_server/server.py` | 엔비디아 그래픽카드 서버에서 Qwen3-TTS로 대표 목소리 복제. 참고 녹음은 저장소에 올리지 않음 |

## AI 연결 켜기

비서 PC에서 `pip install anthropic`을 하고, Anthropic 계정에서 만든 API 키를 **본인 PC의 환경 변수** `ANTHROPIC_API_KEY`에 넣어요. 키는 저장소·게시판·대화창 어디에도 붙여 넣지 않아요.

## 지킬 것

- 첫인사와 화면에 AI라는 것을 밝혀요.
- 녹음 검사 도구는 녹음 기본 폴더(`DIDO_RECORDINGS`, 기본 `문서\voice-raw`) 안만 열어요.
- 목소리 서버를 밖에서 부르게 열 때는 접근 토큰(`DIDO_TTS_TOKEN`)이 꼭 있어야 켜져요.

## 확인

```
python apps/dido-assistant/tests/test_korean_numbers.py
python apps/dido-assistant/tests/test_server.py
```
