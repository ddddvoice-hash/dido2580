# R29 · GPT(아스트라) 결과 · 성우 김디도

> 실행 기록 머리(그대로 옮김):
> ```
> model: gpt-6-astra
> reasoning effort: high
> sandbox: read-only
> session id: 01a110b2-b4dc-7271-98a8-64ba5c07a0c3
> ```
> 날짜: 2026-10-05 · 실행: 팀장이 `codex exec`로 돌림 · 아래는 GPT 답 원문(손대지 않음). 본문의 "모델 줄을 옮기지 못했다"는 말은 GPT가 자기 실행 기록을 볼 수 없어서이며, 위 머리가 실제 기록이에요.

**성우 김디도 · R29 읽기 전용 리뷰**

**수정이 필요해요.** 설정 형식 자체는 공식 문서와 맞지만, 기존 설정 병합·재생 실패 처리·웹 음성 전달에 문제가 있어요. 파일은 수정하지 않았어요.

검토 기준일은 **2026-10-06**이에요. 실행 기록의 `model:`·`reasoning effort:`·`sandbox:` 원문은 제공되지 않아 임의로 작성하지 않았어요.

공식 문서와 대조한 기본 설정 형식은 다음과 같아요.

- **Codex:** `~/.codex/config.toml`의 `[mcp_servers.<이름>]`, `command`, `args`는 맞아요. 생성한 TOML의 메모리 파싱도 통과했어요. [공식 설정 문서](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)
- **Gemini CLI:** `~/.gemini/settings.json`의 최상위 `mcpServers` 아래 `command`, `args`는 맞아요. [공식 MCP 문서](https://geminicli.com/docs/tools/mcp-server/)
- **Claude 데스크톱:** `%APPDATA%\Claude\claude_desktop_config.json`과 `mcpServers` 구조는 맞아요. 이 설정은 로컬 데스크톱 연결용이에요. [공식 로컬 연결 안내](https://modelcontextprotocol.io/docs/2026-07-28/develop/connect-local-servers), [앱 공식 도움말](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp)

아래 파일명은 별도 표기가 없으면 `apps/dido-assistant/` 아래예요. **높음**은 설정 손상·핵심 기능 실패·공개 전 차단이 필요한 문제이고, **보통**은 조건부 실패나 계약·안내 불일치예요.

| 번호 | 파일:줄 | 문제 | 왜 문제인가 | 제안 |
|---|---|---|---|---|
| R29-01 | `connect.py:70–77` | **높음 — 기존 TOML을 손상시키거나 오래된 연결을 유지해요.** | **메모리 재현:** 따옴표로 쓴 기존 서버 테이블을 인식하지 못하고 같은 테이블을 추가해서 `TOMLDecodeError`가 발생했어요. 반대로 정확히 같은 머리글이 있으면 실행 경로가 오래돼도 “이미 연결됨”으로 끝나요. [TOML 규격](https://toml.io/en/v1.0.0#table) | 문자열 검색 대신 TOML 구조로 서버를 찾아 필요한 값만 갱신하고, 저장 전 전체 설정을 파싱해요. |
| R29-02 | `connect.py:49–60` | **높음 — 같은 서버의 추가 JSON 설정을 지워요.** | **메모리 재현:** 기존 `env`, `timeout`이 사라지고 `command`, `args`만 남았어요. 이 필드들은 공식 지원 설정이에요. 또한 `[]`, `null`, `mcpServers: null`에는 `AttributeError`가 발생했어요. [공식 설정 속성](https://geminicli.com/docs/tools/mcp-server/) | 객체 구조를 검사하고 기존 서버 객체에서 실행 명령·인자만 갱신해요. 다른 설정은 보존해요. |
| R29-03 | `mcp_server.py:32–38, 69–88, 118–123` | **높음·공개 연결 전 — 악용 금지 문구를 서버가 강제하지 않아요.** | **코드 확인:** 금지 안내는 모델에 주는 문장뿐이에요. 합성 함수에는 사용자 권한·사용량·용도 검사가 없고 출력 파일도 계속 쌓여요. 현재는 루프백에 묶여 있으므로 인터넷에 이미 노출됐다는 뜻은 아니에요. [MCP 전송 보안 요건](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports) | 공개 연결 전에 인증·권한·호출량·저장량 제한과 정책 검사 경로를 마련해요. 모델 안내를 접근 통제로 간주하지 않아요. |
| R29-04 | `apps/setup-voice.cmd:5, 23, 33–37`; `connect.py:50–51, 118–121` | **보통 — 실패해도 완료 안내가 나와요.** | **코드 확인·분리 재현:** `cd`, 참고 문장 복사, 연결, 상태 확인의 실패를 검사하지 않아요. JSON 연결 실패도 문자열로만 보고해서 종료 코드에 반영되지 않아요. 앞 명령 실패 뒤 상태 확인이 성공하면 최종 종료 코드가 0이 되는 흐름을 확인했어요. [종료 코드 검사 문서](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/if) | 필수 단계마다 즉시 실패를 검사해 중단하고, `connect.py`도 실패를 종료 코드로 전달해요. |
| R29-05 | `mcp_server.py:69–79, 92–100` | **보통 — 입력 400자는 제한하지만 합성량은 제한하지 않아요.** | **함수 재현:** 399·400자는 합성 단계에 도달하고 401자는 거절됐어요. 다만 `99% ` 반복 입력은 공백 제거 후 399자에서 변환 후 799자가 되어 그대로 전달됐어요. 숫자 변환·대본 점검 도구에는 별도 길이 제한이 없어요. 출처는 해당 코드와 직접 호출 결과예요. | 입력 제한은 유지하고, 변환 후 합성 길이·대본 크기·출력 크기에 별도 상한을 정해요. |
| R29-06 | `mcp_server.py:51–60, 85–88` | **보통 — 재생 실패가 합성 결과까지 오류로 만들어요.** | **모의 재현:** 파일 저장 뒤 `_play()`에서 `OSError`가 발생하면 함수 밖으로 나가요. 또 MP3의 `os.startfile()` 성공은 연결 프로그램 실행을 뜻하며 실제 재생 확인은 아니에요. [재생 인터페이스](https://docs.python.org/3/library/winsound.html), [파일 실행 의미](https://docs.python.org/3/library/os.html#os.startfile) | 생성 성공과 재생 성공을 분리해요. 재생 실패에도 생성 결과를 반환하고, 실행 요청 여부와 확인된 재생 상태를 구분해요. |
| R29-07 | `tts.py:118–121` | **보통 — 참고 녹음이나 모델을 바꿔도 이전 음성을 재사용해요.** | **모의 재현:** 캐시 키에는 참고 문장과 출력 문장만 들어가요. 참고 녹음·모델을 변경해도 기존 캐시를 반환하고 모델을 호출하지 않았어요. 출처는 해당 코드와 메모리 재현이에요. | 참고 녹음 내용의 해시, 모델 식별자·버전, 합성 설정을 캐시 키에 포함해요. |
| R29-08 | `tts.py:3–8, 173–188` | **보통 — 자동 선택 설명과 구현이 다르고, 잘못된 주소가 로컬 선택을 막아요.** | **코드 확인:** 설명은 클라우드 우선인데 구현은 HTTP 우선이에요. **모의 재현:** 로컬 사용 가능 상태에서도 잘못된 HTTP 주소가 있으면 즉시 `browser`가 선택돼요. MCP에서는 이 엔진으로 음성을 만들지 못해요. | 우선순위를 명시해 문서와 맞추고, `auto`에서는 사용할 수 없는 후보를 건너뛸지 정해요. 명시 선택 실패는 별도로 설명해요. |
| R29-09 | `tts.py:105–114, 125–126`; `connect.py:64–67` | **보통·추측 — CPU 첫 합성이 도구 제한 시간을 넘을 수 있어요.** | **확인:** 모의 로더에는 `device_map='cpu'`, `dtype=float32`가 전달됐어요. 실제 다운로드·CPU 합성 시간은 미확인이에요. 첫 호출 안에서 모델을 불러오는데 Codex 기본 도구 제한 시간은 60초예요. [모델 로딩 구현](https://github.com/QwenLM/Qwen3-TTS/blob/main/qwen_tts/inference/qwen3_tts_model.py), [도구 제한 시간](https://learn.chatgpt.com/docs/extend/mcp?surface=cli) | 실제 CPU에서 첫 호출·재호출 시간을 측정하고, 사전 준비·진행 상태·적절한 제한 시간을 설계해요. 현재 검증을 “CPU 합성 성공”으로 기록하지 않아요. |
| R29-10 | `mcp_server.py:63–68, 83, 91–105` | **보통 — 도구 설명이 실제 결과와 선택 조건을 충분히 설명하지 않아요.** | **코드 확인:** WAV를 만든다고 설명하지만 MP3도 반환해요. “이 컴퓨터”는 서버 실행 컴퓨터인데 원격 호출에서는 사용자 컴퓨터로 오해할 수 있어요. 각 도구에 읽기 전용 여부도 명시하지 않았어요. [공식 도구 설계 지침](https://developers.openai.com/plugins/plan/tools) | 음성 생성·숫자 변환·대본 점검의 선택 조건을 구분해요. 형식, 저장·재생 위치, 전제 조건을 적고 실제 동작에 맞는 `readOnlyHint` 등을 지정해요. |
| R29-11 | `connect.py:11`; `README.md:31`; `docs/assistant/HANDOFF.md:23` | **보통 — “공개 HTTPS 서버만 가능” 안내가 현재 문서와 달라요.** | 현재 공식 문서는 서버 URL 연결 외에 **Secure MCP Tunnel**로 비공개 서버를 연결하는 경로도 안내해요. [공식 터널 문서](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels) | 공개 HTTPS 방식과 비공개 터널 방식을 나눠 안내해요. 계정·작업공간 권한과 상시 실행 조건도 적어요. |
| R29-12 | `mcp_server.py:85–88, 108–109` | **높음·원격 음성 사용 — 서버 파일 경로만 반환해 웹에서 소리를 받을 수 없어요.** | **코드 확인:** 응답은 서버의 절대 파일 경로예요. 오디오 콘텐츠·다운로드 URL·리소스 제공은 없고 재생도 서버에서 해요. 경로에는 불필요한 로컬 계정 정보가 포함될 수 있어요. [공식 도구 결과 지침](https://developers.openai.com/plugins/plan/tools) | 인증된 오디오 전달 방법을 구현하고 실제 웹 재생을 확인해요. 응답에는 내부 절대 경로 대신 결과 식별자를 사용해요. |

**배치 문법은 확인 범위를 구분해야 해요.** 괄호 블록, 공백·괄호가 있는 인용 경로, Python 대체 실행 구문 형태, `if errorlevel 1`을 `cmd.exe`에서 분리 실행했고 문법 오류는 없었어요. `.cmd` 내부의 `&&` 자체도 유효해요. 설치·복사·설정 변경을 수행하는 전체 배치는 실행하지 않았어요. [명령 해석기 공식 문서](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/cmd)

**ChatGPT 웹 연결에는 다음이 필요해요.**

1. 해당 계정·작업공간에서 사용자 지정 MCP를 추가·사용할 권한이 필요해요.
2. 연결 경로를 선택해요. 공개 방식은 도달 가능한 HTTPS MCP 주소와 접근 통제가 필요해요. 비공개 터널 방식은 터널 식별자, 필요한 권한, 실행 자격 증명, 계속 실행되는 `tunnel-client`가 필요해요. 이번 검토에서는 자격 증명을 만들거나 출력하지 않았어요.
3. 웹의 플러그인 추가 화면에서 서버 URL 또는 터널을 지정하고 인증을 설정한 뒤 설치해요. 지원 전송은 SSE와 스트리밍 HTTP예요. [공식 연결 절차](https://developers.openai.com/api/docs/guides/custom-mcp-server), [터널 준비 조건](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
4. 도구 연결과 웹 음성 재생은 따로 검증해야 해요. 현재 코드에는 위 R29-12의 음성 전달 기능이 빠져 있어요.

검증에는 `python -B -X utf8 -c`를 사용했고, 파일 쓰기와 외부 통신을 차단하거나 메모리 모형으로 대체했어요. 실제 MCP·음성 합성 패키지가 설치돼 있지 않아 SDK 연결, 실제 CPU 합성, 스피커 재생, 각 앱 연결 성공은 확인하지 못했어요. 기존 테스트는 임시 파일을 생성하므로 실행하지 않았어요. 검토 대상 파일의 Git 변경은 없어요.

검토한 파일 목록: `AGENTS.md`, `TEAM_BOARD.md` R29, `apps/dido-assistant/{mcp_server.py,connect.py,tts.py,korean_numbers.py,README.md}`, `brain.py` 관련 부분, `tests/{test_mcp.py,test_connect.py,fakes/torch/__init__.py,fakes/qwen_tts/__init__.py,fakes/soundfile.py}`, `apps/setup-voice.cmd`, `docs/assistant/HANDOFF.md` · 실행해 본 것: 메모리 구문 검사·설정 병합 재현·길이 경계값·재생 예외·자동 선택·CPU 인자·캐시 재사용 확인, 분리한 윈도우 명령 구문 실행, 공식 문서 웹 대조, Git 상태 확인이에요.
