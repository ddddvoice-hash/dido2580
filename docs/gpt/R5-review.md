# R5 · GPT(아스트라) 결과 · 성우 김디도

> 실행 기록 머리(그대로 옮김):
> ```
> model: gpt-6-astra
> reasoning effort: high
> sandbox: read-only
> session id: 01a10992-93ba-7493-b435-056b75e52443
> ```
> 날짜: 2026-10-05 · 실행: 팀장이 `codex exec`로 돌림 · 아래는 GPT 답 원문(손대지 않음). 본문의 "모델 줄을 옮기지 못했다"는 말은 GPT가 자기 실행 기록을 볼 수 없어서이며, 위 머리가 실제 기록이에요.

**성우 김디도 — R5 리뷰예요.** 지정한 커밋 범위와 현재 파일을 검토했고, 파일은 수정하지 않았어요.

실행 기록의 `model:`·`reasoning effort:`·`sandbox:` 원문은 제공되지 않아 그대로 옮기지 못했어요. 모델 이름은 추측하지 않았어요.

| 번호 | 파일:줄 | 문제 | 왜 문제인가 | 제안 |
|---|---|---|---|---|
| 1 | `.github/workflows/tests.yml:37` | **중간 — 설정 첫 줄의 오류를 놓쳐요.** | `tail -n +2`가 첫 줄을 무조건 제외해요. 메모리 실험에서 첫 줄을 잘못된 문법으로 바꾸어도 나머지 줄 비교는 일치했고, 설정 파서는 오류를 반환했어요. 현재 두 설정 자체는 같아요. | 두 파일을 `tomllib`으로 읽어 문법과 설정값을 함께 비교해요. 읽기·파싱 실패도 단계 실패로 처리해요. |
| 2 | `.github/workflows/tests.yml:83` | **낮음 — 서버 시작 실패를 해당 단계에서 확인하지 않아요.** | 백그라운드 실행 후 상태 확인이 없고 오류 출력도 버려요. 후속 브라우저 검사에서 실패할 수 있지만, 시작 실패 원인은 남지 않아요. 실제 CI에서 발생했는지는 미확인이에요. | 서버 프로세스 생존과 HTTP 응답을 제한 시간 안에 확인하고, 실패하면 로그와 함께 비정상 종료해요. |
| 3 | `.github/workflows/tests.yml:16,30,44,78` | **낮음 — 테스트에 불필요한 인증 정보가 남아요.** | 체크아웃 기본값은 작업 종료까지 인증 토큰을 로컬 설정에 보관해요. 이후 설치·테스트 코드에서 접근할 수 있어요. 실제 유출을 발견한 것은 아니에요. [동작 근거](https://github.com/actions/checkout/tree/v4#readme) | 네 곳 모두 `persist-credentials: false`를 지정해요. |

잘된 점이에요.

- `contents: read`로 권한을 제한했고, 검토한 워크플로에 비밀값 직접 참조·출력은 없어요.
- 일반 테스트 명령은 기본 셸의 `-e`로 실패 시 중단돼요. 여러 줄이라는 이유로 앞 명령의 실패가 덮이지는 않아요. [셸 실행 규칙](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idstepsshell)
- 연결된 테스트의 실패 집계·종료 코드 처리와 브라우저 검사 예외의 실패 처리를 확인했어요.

전체 CI는 실행하지 않았어요. 셸 재현 시도는 `CreateFileMapping … Win32 error 5`로 시작부터 실패했으므로 재현 성공으로 계산하지 않았어요.

**검토한 파일 목록:** `AGENTS.md`, `TEAM_BOARD.md`의 R5, `.github/workflows/tests.yml`과 지정 커밋 이력, 두 `.streamlit/config.toml`, 연결된 테스트의 종료 처리 부분, `tools/build-profile.js`의 검사 분기 · **실행해 본 것:** 이력·차이·상태 조회, 메모리에서 설정 비교·문법 오류 확인, 셸 재현 시도(환경 제한으로 실패).
