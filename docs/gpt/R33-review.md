# R33 · GPT(아스트라) 결과 · 성우 김디도

> 실행 기록 머리(그대로 옮김):
> ```
> model: gpt-6-astra
> reasoning effort: high
> sandbox: read-only
> session id: 01a1130e-eb09-74f3-abbd-390904d66b03
> ```
> 날짜: 2026-10-05 · 실행: 팀장이 `codex exec`로 돌림 · 아래는 GPT 답 원문(손대지 않음). 본문의 "모델 줄을 옮기지 못했다"는 말은 GPT가 자기 실행 기록을 볼 수 없어서이며, 위 머리가 실제 기록이에요.

**성우 김디도 · R33: A23은 추가 수정이 필요해요.** 기존 회귀 시험 4개는 통과했지만, 새 우회 입력·오탐·단위 읽기 회귀·경쟁 조건을 확인했어요.

파일은 수정하지 않았어요. 합성·저장·삭제는 메모리 모의로 실행했어요. 실제 발음이 금지 문구와 같다는 판단은 **추측**이며, 아래의 ‘통과’는 **모의 합성 함수에 도달했다는 뜻**이에요. 이번 실행의 설정 머리 원문은 제공되지 않아 모델·생각 깊이를 임의로 적지 않았어요.

파일 경로는 `apps/dido-assistant/` 기준이고, 재현 표시는 아래 한 줄 명령의 출력 이름이에요.

| 번호 | 파일:줄 | 문제 | 왜 문제인가 | 제안 |
|---|---|---|---|---|
| R33-1 | `mcp_server.py:146`, `:151`, `:192` | **중간 — 결합 문자·동형 문자 변형이 남아요.** `U1`: 모의 금지어 `abcd`에서 `a\u0301bcd`, 키릴 문자를 섞은 `аbcd`·`abсd` 모두 합성 호출 1회예요. | 결합 표시를 제거하기 전에 NFKC가 악센트를 합쳐요. 마지막 NFKD가 표시를 다시 분리하지만 그 뒤에는 제거하지 않아요. 키릴 동형 문자도 대응하지 않아요. | 최종 분해 뒤 결합 표시 처리도 검증해요. 동형 문자 대응은 지원 범위를 정하고 오탐 시험과 함께 추가해요. |
| R33-2 | `mcp_server.py:174`, `:177`, `:344` | **중간 — 숫자 기호 일부는 여전히 통과해요.** `U2`: 모의 금지어 `일 번`에서 `❶번`·`➀번`·`⓵번` 모두 합성 호출 1회예요. | `Nd` 또는 NFKC 결과가 ASCII 숫자인 경우만 처리해서, 이 숫자 기호들은 그대로 남아요. | 지원할 정수 숫자 기호를 명시하고 변환·차단 시험을 추가해요. 분수·단위까지 무조건 숫자로 바꾸지는 않아요. |
| R33-3 | `mcp_server.py:177`, `:342`; `korean_numbers.py:210`, `:211` | **중간 — 숫자 통일이 기존 넓이 단위 읽기를 깨뜨려요.** `N`: `면적은 3m²예요.` → `면적은 3m2예요.`이고, `넓이는 3km²예요.` → `넓이는 삼 킬로미터이예요.`예요. | 기존 `normalize()`만 호출하면 각각 `삼 제곱미터`, `삼 제곱킬로미터`로 읽어요. A23이 `²`를 먼저 `2`로 바꾸면서 단위 규칙이 적용되지 않아요. | 단위 구간을 먼저 보호하거나 분류해요. 검사 전용 숫자 통일과 실제 낭독문 변환의 적용 범위를 구분해요. |
| R33-4 | `mcp_server.py:117`, `:152`, `:192` | **중간 — 정상 문장의 오탐이 있어요.** `F`: 모의 금지어 `시`에서 `날씨는 맑아요.`, `시험`에서 `도시 험지는 피해 가요.`, `나무`에서 `소나무를 심어요.`가 모두 차단돼요. | `씨`를 `ㅅㅅㅣ`로 풀면 `시`의 `ㅅㅣ`와 부분 일치해요. 공백 제거는 낱말 경계를 합치고, 부분 문자열 비교는 다른 낱말 내부도 막아요. 실제 운영 목록에서의 빈도는 확인하지 않았어요. | 정확 일치·낱말·부분 문자열 규칙을 구분해요. 원래 음절 경계를 보존하고, 짧은 금지어의 자모 부분 일치를 제한해요. |
| R33-5 | `mcp_server.py:233`, `:241`, `:248` | **중간 — 검사 중 파일이 사라지는 경합을 처리하지 못해요.** `S`: 다른 스레드가 모의 파일을 제거하면 합계 계산 중 `FileNotFoundError`가 밖으로 나와요. 삭제 단계에서 사라지면 빈 저장소인데도 저장을 거절해요. | 합계 계산의 `stat()`는 예외 처리 밖이에요. 삭제 단계의 `FileNotFoundError`에서는 개수만 줄이고 기존 바이트 합계는 남겨요. `OUT_LOCK`은 외부 삭제까지 막지는 못해요. | 파일 정보 수집 전체를 예외 처리하고, 사라진 파일은 개수·용량 양쪽에서 제외해요. 필요하면 현재 목록을 다시 계산해요. |
| R33-6 | `mcp_server.py:314`, `:325` | **낮음 — 기다리던 재요청에 전달한 결과가 `_DONE`에도 남아요.** `J`: 첫 요청 시간 초과 → 재요청이 같은 작업을 기다림 → 완료 순서에서 결과 전달 뒤 `_DONE=1`이에요. 다음 요청에도 같은 결과를 돌려줘요. | `abandoned`는 남아 있고, 기다리던 요청의 결과 반환 경로는 완료 보관분을 소비하지 않아요. 실제 결과 유실이나 추가 합성은 이 경합에서 발생하지 않았어요. | 결과 전달 여부를 잠금 안에서 관리하고, 해당 작업의 결과를 전달했다면 완료 보관분도 일관되게 정리해요. |

**R32-1~4의 종결 판단은 다음과 같아요.**

| 항목 | 판정 | 직접 확인한 근거 |
|---|---|---|
| R32-1 | **부분 해결·남음** | 기존 NFD·제로폭·두 방식의 조합·결합 표시·문장부호·호환자모는 차단됐어요. 내장 목록 7개에 변형 6종을 적용한 **42건 모두 차단**됐어요. 새 변형은 R33-1에 남아요. |
| R32-2 | **부분 해결·남음** | 기존 `1번`·`１번`·`١번`·`①번`·`¹번`·`一번`은 모두 합성 호출 0회예요. 새 숫자 기호와 단위 회귀는 R33-2·3이에요. |
| R32-3 | **기존 결함은 닫힘** | 기존 파일 2개·상한 2개·삭제 실패에서 동시 요청 8건 모두 거절하고 저장 0회였어요. 삭제가 가능한 동시 요청 8건은 용량 상한 100바이트에서 최대 60바이트였고, 저장은 모두 잠금 안에서 수행됐어요. 외부 삭제 경합은 R33-5로 남아요. |
| R32-4 | **기존 결과 유실은 닫힘** | 시간 초과 뒤 완료된 결과를 재요청하면 합성 총 1회로 반환하고 `_DONE`을 비웠어요. 다만 완료를 기다리는 재요청과의 경합은 R33-6으로 남아요. |

추가로 자모 순서를 바꾼 `ㅅㅓㅎㅣㅁ`, 초성만 쓴 `ㅅㅎ`, 라틴 문자를 섞은 `ㅅl험`은 통과했고, 숫자·자모 혼합 `1ㅂㅓㄴ`은 차단됐어요. 앞의 세 입력이 원래 문구와 같은 뜻·발음인지는 **추측**이므로 확정 우회 건수에는 넣지 않았어요. `試驗` 통과는 A23 보고에 명시된 한자 사전 미지원 범위예요. `1.0번`도 통과하지만 낭독문이 `일 점 영 번`이어서 `일 번`과 같은 반례로 취급하지 않았어요.

동시 합성 상한도 유지됐어요. 실행 중 작업은 2개였고 추가 20건은 모두 `busy`였어요. 완료 결과 10건을 만들었을 때 보관은 8건으로 제한됐고, 모의 시계를 유효기간 이후로 이동한 다음 호출에서는 만료된 결과가 제거됐어요.

아래는 저장소 루트에서 실행하는 **공통 재현 명령 한 줄**이에요. `U1·U2`는 우회, `F`는 오탐, `N`은 단위 회귀, `S·J`는 스레드 경합을 재현해요. 실제 설정·음성·파일 저장을 사용하지 않아요.

```powershell
python -B -X utf8 -c "exec('import sys,os,threading\nfrom types import SimpleNamespace as S\nfrom unittest.mock import patch,MagicMock,Mock\nsys.path.insert(0,\'apps/dido-assistant\')\nimport mcp_server as m\ne=S(name=\'test\',label=\'성우 김디도\',mime=\'audio/wav\')\nwith patch.object(m.pathlib.Path,\'read_text\',return_value=\'\'),patch.object(m,\'_audit\'),patch.object(m,\'engine\',return_value=e),patch.object(m,\'LIMIT\',S(allow=lambda:True)):\n with patch.object(m,\'_synth_with_budget\',return_value=None) as syn:\n  cases=[(\'U1\',\'abcd\',\'a\\u0301bcd\'),(\'U1\',\'abcd\',\'\\u0430bcd\'),(\'U1\',\'abcd\',\'ab\\u0441d\'),(\'U2\',\'일 번\',\'❶번\'),(\'U2\',\'일 번\',\'➀번\'),(\'U2\',\'일 번\',\'⓵번\'),(\'N\',\'제곱미터\',\'면적은 3m²예요.\'),(\'N\',\'제곱킬로미터\',\'넓이는 3km²예요.\'),(\'F\',\'시\',\'날씨는 맑아요.\'),(\'F\',\'나무\',\'소나무를 심어요.\'),(\'F\',\'시험\',\'도시 험지는 피해 가요.\')]\n  for label,term,s in cases:\n   with patch.object(m,\'BUILTIN_BLOCKED\',(term,)):\n    syn.reset_mock();m.speak_core(s,False);print(label,repr(term),repr(s),\'synth\',syn.call_count,\'before\',m.normalize(s),\'after\',m.normalize(m._unify_digits(s)))\n with patch.object(m,\'check_policy\',return_value=None),patch.object(m,\'_synth_with_budget\',return_value=(b\'x\'*60,None)),patch.object(m,\'MAX_OUT_BYTES\',100),patch.object(m,\'MAX_OUT_FILES\',2):\n  for stage in [\'stat\',\'unlink\']:\n   state={\'exists\':True,\'stats\':0};erase=threading.Event();erased=threading.Event();f=Mock();out=MagicMock();out.glob.return_value=[f];f.is_file.return_value=True\n   def stat():\n    state[\'stats\']+=1\n    if stage==\'stat\' and state[\'stats\']==2:erase.set();assert erased.wait(2)\n    if not state[\'exists\']:raise FileNotFoundError(\'mock\')\n    return S(st_size=50,st_mtime=0)\n   def unlink():\n    erase.set();assert erased.wait(2);raise FileNotFoundError(\'mock\')\n   def remove():\n    assert erase.wait(2);state[\'exists\']=False;erased.set()\n   f.stat.side_effect=stat;f.unlink.side_effect=unlink;t=threading.Thread(target=remove);t.start()\n   with patch.object(m,\'OUT_DIR\',out):\n    try:print(\'S\',stage,\'ok\',m.speak_core(\'안녕하세요\',False)[0][\'ok\'])\n    except FileNotFoundError:print(\'S\',stage,\'FileNotFoundError\')\n   t.join(2);print(\'S\',stage,\'exists\',state[\'exists\'],\'writes\',out.__truediv__.return_value.write_bytes.call_count)\nRealThread=threading.Thread\nrelease=threading.Event();entered=threading.Event();waiting=threading.Event();calls=[];results=[]\nclass T(RealThread):\n def join(self,timeout=None):\n  if threading.current_thread().name==\'retry\':waiting.set()\n  return super().join(timeout)\ndef fake(e,s):\n calls.append(s);entered.set();assert release.wait(3);return b\'x\',None\nwith patch.dict(os.environ,{\'DIDO_MCP_BUDGET\':\'0\'}),patch.object(m,\'synth_or_none\',side_effect=fake),patch.object(m,\'_JOBS\',{}),patch.object(m,\'_DONE\',{}),patch.object(m.threading,\'Thread\',T):\n assert m._synth_with_budget(e,\'안녕하세요\') is None;assert entered.wait(2)\n os.environ[\'DIDO_MCP_BUDGET\']=\'2\'\n retry=RealThread(name=\'retry\',target=lambda:results.append(m._synth_with_budget(e,\'안녕하세요\')));retry.start();assert waiting.wait(2);release.set();retry.join(3)\n print(\'J\',\'delivered\',results==[(b\'x\',None)],\'done_after_delivery\',len(m._DONE),\'calls\',len(calls))\n print(\'J\',\'again\',m._synth_with_budget(e,\'안녕하세요\'),\'calls\',len(calls))\n')"
```

검토한 파일 목록: `AGENTS.md`, `TEAM_BOARD.md`의 R33·A23 및 관련 보고, `docs/gpt/R31-review.md`, `docs/gpt/R32-review.md`, `apps/dido-assistant/mcp_server.py`, `tests/test_mcp.py`, `korean_numbers.py`, `tts.py`, `brain.py` 관련 부분이에요. 실행해 본 것: `python -c` 우회·오탐·단위 반례, 내장 목록 변형 42건, A23 회귀 시험 4개 통과, 메모리 저장·삭제·합성의 스레드 경합, 완료 결과 상한·만료 검사, Git 상태 확인이에요.
