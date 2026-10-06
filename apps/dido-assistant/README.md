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
3. 그다음부터 비서와 연결된 AI들이 **성우 김디도 목소리**로 말해요. 목소리 엔진은 아래 순서로, **쓸 수 있는 첫 번째**를 스스로 골라요(안전하지 않은 주소 같은 쓸 수 없는 후보는 건너뛰어요).
   1. 클라우드 맞춤 목소리: `ELEVENLABS_API_KEY`와 `DIDO_ELEVEN_VOICE_ID`가 있을 때(주소는 공식 `https://api.elevenlabs.io`로 고정).
   2. 목소리 서버: `DIDO_TTS_URL`이 있을 때(밖의 주소는 https만).
   3. 이 컴퓨터: `voice/ref.wav`·`voice/ref.txt`와 qwen-tts가 있을 때(그래픽카드가 없으면 CPU라 느려요). 같은 글은 저장해 두어 다음부터 바로 나와요. 참고 녹음·참고 문장·모델(`DIDO_TTS_MODEL`)을 바꾸면 이전 저장본을 쓰지 않고 새로 만들어요.
   4. 모두 없으면 브라우저 기본 목소리(대표 목소리 아님).
   `DIDO_TTS=eleven`·`http`·`local`로 직접 고르면 그 엔진만 써 보고, 안 되면 이유를 화면에 적고 기본 목소리로 읽어요.
4. 이 컴퓨터(CPU) 엔진은 **처음 한 번이 오래 걸려요**(모델 내려받기·불러오기). `setup-voice.cmd`가 3단계에서 미리 해 두고, 그래도 첫 합성이 45초를 넘으면 AI에게 "준비 중"이라고 답한 뒤 뒤에서 계속 만들어요. 1~2분 뒤 같은 글로 다시 부르면 바로 나와요. Codex에는 도구 제한 시간(`tool_timeout_sec`)을 120초로 적어 둬요. 실제 CPU 합성 시간은 아직 재 보지 못했어요.

## Claude·GPT·Gemini에서 부르기

`mcp_server.py`는 AI 앱이 바깥 도구를 부르는 공통 규격(MCP) 서버예요. `connect.py`(setup-voice.cmd가 실행)가 설치된 앱에 연결해요. 설정 파일은 이렇게 다뤄요: 바꾸기 전에 `.bak`(이미 있으면 날짜시각을 붙인 `.bak-…`)을 남기고, 우리 항목의 `command`·`args`만 바꾸고(같은 항목의 `env`·`timeout`과 다른 서버·다른 설정은 그대로), 임시 파일에 쓴 뒤 바꿔치기해요. 파일이 깨졌거나 예상 밖 모양이면 손대지 않고 실패로 알려요(종료 코드 1). `--dry-run`은 바꿀 것만 보여 줘요.

| AI | 연결 방법 | 확인 |
|---|---|---|
| Claude 데스크톱 | `claude_desktop_config.json`에 자동 추가 | 앱을 다시 켜면 도구 목록에 보임 |
| Claude Code | `claude mcp add`로 자동 추가 | `claude mcp list` |
| GPT (Codex CLI) | `~/.codex/config.toml`에 자동 추가 | Codex에서 도구 목록 |
| Gemini (Gemini CLI) | `~/.gemini/settings.json`에 자동 추가 | `/mcp` |
| ChatGPT 웹·앱 | 이 컴퓨터의 설정 파일로는 붙지 않아요. 두 길이 있어요. (가) 공개 HTTPS 주소: `DIDO_MCP_TOKEN`을 정하고 `python mcp_server.py --http`를 HTTPS 프록시 뒤에 두어 그 주소를 연결에 넣어요. (나) 비공개 서버: OpenAI의 Secure MCP Tunnel로 연결해요. 둘 다 계정·작업공간에 사용자 지정 MCP 권한이 있어야 하고, 서버가 계속 켜져 있어야 해요 | 공개 서버를 연 뒤. 도구 연결과 웹 소리 재생은 따로 확인해야 해요 |

AI에게 이렇게 말하면 돼요: "김디도 목소리로 '오전 9시 30분에 출발해요' 읽어 줘", "이 대본 숫자 점검해 줘".

| 도구 | 하는 일 |
|---|---|
| `speak_as_dido` | 글을 성우 김디도 목소리(AI)로 읽은 소리 파일(WAV 또는 MP3)을 만들어요. 이 컴퓨터용 연결(stdio)에서는 스피커로 틀기를 요청하고, 주소(`--http`) 연결에서는 소리를 응답에 직접 실어요(서버 파일 경로는 알려 주지 않고 `result_id`만). 만들기와 틀기는 따로라 틀기가 실패해도 만든 결과는 돌려줘요. 읽기 전용이 아니에요(파일을 만들고 글을 목소리 엔진에 보내요) |
| `read_numbers_like_dido` | 숫자를 사람이 읽는 말로 풀어 글로 돌려줘요(읽기 전용, 2000자 이하) |
| `check_script_numbers` | 대본의 숫자 문장마다 읽는 법(읽기 전용, 20000자 이하) |
| `dido_voice_status` | 지금 쓰는 목소리 엔진, 목소리 폴더 준비 상태(읽기 전용) |

**악용 막기는 서버가 강제해요**(AI에게 주는 안내 글에만 맡기지 않아요): 글 길이(입력 400자, 숫자를 풀어 읽은 뒤 600자), 분당 10회·하루 300회(`DIDO_MCP_PER_MIN`·`DIDO_MCP_PER_DAY`), `voice/out`의 파일 50개·100MB 상한, 사기·협박·정치 광고로 보이는 문구 거절(최소한의 바닥선이고, `voice/blocklist.txt`에 줄마다 더할 수 있어요), `voice/out/audit.jsonl`에 만든 기록(글 원문은 남기지 않음), `--http`는 토큰 없이는 켜지지 않고 `127.0.0.1`에만 열려요. 공개 서비스로 열기 전에는 사용자별 로그인·권한이 더 필요해요(인계 문서 6번).

## 층 (바꿔 끼우기)

| 층 | 파일 | 지금 |
|---|---|---|
| 듣기 | `index.html` (브라우저 음성 인식, 엣지·크롬) | 됨 |
| 생각 | `brain.py` | AI 연결이 있으면 Claude(`claude-opus-5-5`, 거절 시 서버 쪽 대체 모델 사용), 없으면 오프라인 모드(시각·숫자 읽기·대본 점검) |
| 말 다듬기 | `korean_numbers.py` | 성우 김디도 숫자 사례 20문장 통과 |
| 목소리 | `tts.py` | 위 "음성만 넣으면 바로 구동"의 순서로 자동 선택(`DIDO_TTS`로 직접 고를 수도 있어요). 기본 목소리는 대표 목소리가 아니에요 |
| 목소리 서버 | `tts_server/server.py` | 엔비디아 그래픽카드 서버에서 Qwen3-TTS로 대표 목소리 복제. 참고 녹음은 저장소에 올리지 않음 |

## AI 연결 켜기

비서 PC에서 `pip install anthropic`을 하고, Anthropic 계정에서 만든 API 키를 **본인 PC의 환경 변수** `ANTHROPIC_API_KEY`에 넣어요. 키는 저장소·게시판·대화창 어디에도 붙여 넣지 않아요.

## 지킬 것

- 첫인사와 화면에 AI라는 것을 밝혀요.
- 녹음 검사 도구는 녹음 기본 폴더(`DIDO_RECORDINGS`, 기본 `문서\voice-raw`) 안만 열어요.
- 목소리 서버를 밖에서 부르게 열 때는 접근 토큰(`DIDO_TTS_TOKEN`)이 꼭 있어야 켜져요.
- 클라우드 목소리 키는 공식 주소로만 가요. 목소리 서버·비서 모두 리디렉션을 따라가지 않아요.

## 확인

```
python apps/dido-assistant/tests/test_korean_numbers.py
python apps/dido-assistant/tests/test_server.py
python apps/dido-assistant/tests/test_connect.py
python apps/dido-assistant/tests/test_mcp.py     (pip install mcp 필요, 가짜 목소리 모델로 음성 폴더→목소리 파일까지 확인)
```
