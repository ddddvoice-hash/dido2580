# 성우 김디도 AI 비서

성우 김디도의 목소리로 말하는 AI 음성 비서예요. 설계: `docs/assistant/plan.md`.

## 켜기

`apps/start-assistant.cmd`를 두 번 누르면 비서가 앱 창으로 열려요(작업실 첫 화면 6번 카드로도 갈 수 있어요). 이 컴퓨터 안(127.0.0.1:8770)에서만 열려요.

| 탭 | 하는 일 |
|---|---|
| 대화 | 말(Alt+Q)이나 글로 묻고 소리로 들어요. 다시 듣기 Alt+W, 멈추기 Esc |
| 대본 점검 | 대본을 붙여 넣으면 숫자가 든 문장마다 읽는 법을 보여 줘요 |
| 숫자 읽기 | 문장 하나를 사람이 읽듯 풀어 들려줘요 |

## 음성만 넣으면 바로 구동

1. `voice/ref_sentence.txt`의 문장을 평소처럼 읽어 `voice/ref.wav`로 저장해요(10~15초, 잡음 없이).
2. `apps/setup-voice.cmd`를 두 번 눌러요. 부품 설치, 목소리 폴더 확인, AI 앱 연결까지 한 번에 해요.
3. 그다음부터 비서와 연결된 AI들이 **성우 김디도 목소리**로 말해요. 목소리 엔진은 스스로 골라요: 목소리 서버 주소(`DIDO_TTS_URL`)가 있으면 그 서버, 없으면 이 컴퓨터(그래픽카드가 없으면 CPU라 느림, 같은 문장은 저장해 두어 다음부터 바로).

## Claude·GPT·Gemini에서 부르기

`mcp_server.py`는 AI 앱이 바깥 도구를 부르는 공통 규격(MCP) 서버예요. `connect.py`(setup-voice.cmd가 실행)가 설치된 앱에 연결해요. 원래 설정은 `.bak`으로 남기고 다른 설정은 건드리지 않아요.

| AI | 연결 방법 | 확인 |
|---|---|---|
| Claude 데스크톱 | `claude_desktop_config.json`에 자동 추가 | 앱을 다시 켜면 도구 목록에 보임 |
| Claude Code | `claude mcp add`로 자동 추가 | `claude mcp list` |
| GPT (Codex CLI) | `~/.codex/config.toml`에 자동 추가 | Codex에서 도구 목록 |
| Gemini (Gemini CLI) | `~/.gemini/settings.json`에 자동 추가 | `/mcp` |
| ChatGPT 웹·앱 | 인터넷에서 닿는 HTTPS 주소가 필요해요. `python mcp_server.py --http`를 공개 서버에 올리고 접근 제한을 건 뒤, ChatGPT 설정의 개발자 모드 연결에 그 주소를 넣어요 | 공개 서버를 연 뒤 |

AI에게 이렇게 말하면 돼요: "김디도 목소리로 '오전 9시 30분에 출발해요' 읽어 줘", "이 대본 숫자 점검해 줘".

| 도구 | 하는 일 |
|---|---|
| `speak_as_dido` | 글을 성우 김디도 목소리(AI)로 읽어 WAV를 만들고 이 컴퓨터에서 틀어요 |
| `read_numbers_like_dido` | 숫자를 사람이 읽는 말로 풀어요 |
| `check_script_numbers` | 대본의 숫자 문장마다 읽는 법 |
| `dido_voice_status` | 지금 쓰는 목소리 엔진, 목소리 폴더 준비 상태 |

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
python apps/dido-assistant/tests/test_connect.py
python apps/dido-assistant/tests/test_mcp.py     (pip install mcp 필요, 가짜 목소리 모델로 음성 폴더→목소리 파일까지 확인)
```
