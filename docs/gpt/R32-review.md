# R32 · GPT(아스트라) 결과 · 성우 김디도

> 실행 기록 머리(그대로 옮김):
> ```
> model: gpt-6-astra
> reasoning effort: high
> sandbox: read-only
> session id: 01a11233-3365-7892-8681-3b8fd6f1872d
> ```
> 날짜: 2026-10-05 · 실행: 팀장이 `codex exec`로 돌림 · 아래는 GPT 답 원문(손대지 않음). 본문의 "모델 줄을 옮기지 못했다"는 말은 GPT가 자기 실행 기록을 볼 수 없어서이며, 위 머리가 실제 기록이에요.

**성우 김디도 · R32: 수정이 필요한 문제 9건을 확인했어요.** 기존 숫자 시험은 **13개 통과**, R31 숫자 반례는 **7개 통과**, G15는 **29/30 일치**예요.

파일은 수정하지 않았어요. 합성·저장은 메모리 모의로만 실행했어요. 실제 음성의 발음은 확인하지 않았으며, 아래 기대 읽기는 기존 규칙과 문맥에 따른 **제안·추측**이에요. 이번 실행의 설정 머리 원문은 제공되지 않아 임의로 옮기지 않았어요.

아래 파일 경로는 `apps/dido-assistant/` 기준이에요. 재현 표시는 마지막 **한 줄 명령의 출력 이름**이에요.

| 번호 | 파일:줄 | 문제 | 왜 문제인가 | 제안 |
|---|---|---|---|---|
| R32-1 | `mcp_server.py:102`·`:103` | **높음 — 정규화 조합으로 금지 검사를 우회해요.** 재현 `P`: NFD와 제로폭 문자는 각각 차단하지만, **분리된 자모 사이에 제로폭 문자를 넣으면 합성 함수에 도달해요.** | NFKC를 먼저 적용하고 문자를 제거해서, 제거 후 남은 자모를 다시 합치지 않아요. Mn·변형 선택자·문장부호·호환자모·한자 변형도 통과했어요. 내장 목록에서도 NFD+제로폭·Mn·문장부호·한자 변형의 통과를 확인했어요. | 검사 대상 문자를 정리한 **뒤에도 정규화**해요. 호환자모·한자는 별도 처리 정책을 정해요. 모든 결합 문자를 무조건 삭제하는 방식은 피하고 오탐도 검증해요. |
| R32-2 | `mcp_server.py:242`·`:243`, `korean_numbers.py:245` | **중간 — 숫자 표기 변형은 재검사를 통과해요.** 재현 `D`: 모의 금지 문구 `일 번`에서 `1번`·`１번`·`١번`은 차단하지만, `①번`·`¹번`·`一번`은 합성 함수에 도달해요. | 검사에서 NFKC로 바꾼 숫자를 숫자 읽기 함수는 받지 않아요. 최종 발음이 금지 문구와 같을지는 **추측**이며 실제 합성은 하지 않았어요. | 지원할 숫자 표기를 먼저 통일하고 숫자를 풀어 읽은 뒤 검사해요. 한자 숫자는 지원 범위를 따로 정해요. |
| R32-3 | `mcp_server.py:159`·`:164`·`:166` | **중간 — 삭제 실패 시 파일 개수 상한을 넘겨요.** 재현 `S`: 상한 2개, 기존 2개, 삭제 실패에서 `ok=True`, 저장 후 **3개**예요. | 실제 삭제 성공 전에 목록에서 파일을 빼요. 실패해도 파일 수가 줄었다고 판단해요. 바이트 합계는 유지해서 용량 초과는 거절했어요. | 삭제 성공한 파일만 개수에서 제외해요. 실패한 파일도 최종 개수에 포함해요. |
| R32-4 | `mcp_server.py:204`·`:221`·`:228` | **중간 — 시간 초과 후 완료된 결과를 재사용하지 못해요.** 재현 `J`: 완료 후 같은 글 재요청에서 `preparing`, 같은 글 합성 호출 **2회**예요. | 완료 즉시 `_JOBS`에서 결과 상자까지 제거해요. “같은 글로 다시 요청하면 바로 나온다”는 설명과 달라요. 엔진 자체 캐시가 없는 경우의 반복 비용은 **추측**이에요. | 실행 중 작업과 완료 결과를 분리하고, 완료 결과에 용량·유효기간 제한을 둬요. |
| R32-5 | `korean_numbers.py:126`·`:135`·`:141` | **중간 — 시각/점수 구별이 여전히 틀려요.** 재현 `N1`~`N3`. | 앞 15글자만 보고, `경기`를 점수 단서로 취급해요. 뒤의 `시작해요`·`이겼어요`를 보지 않으며 시각·점수 단서가 함께 있으면 보존해요. | 숫자 앞뒤의 문맥을 함께 분류해요. 명시적인 `시각` 같은 단서의 우선순위도 정해요. |
| R32-6 | `korean_numbers.py:183`·`:188`·`:217` | **중간 — 조사·콜론이 붙으면 버전을 날짜나 소수로 읽어요.** 재현 `N4`~`N6`. | 버전 규칙은 `버전` 바로 뒤의 공백과 숫자만 받아요. `버전은`·`버전:`은 빠져요. | 버전 문맥을 먼저 판별한 뒤 전체 숫자 덩어리를 처리해요. |
| R32-7 | `korean_numbers.py:114`·`:119`·`:252` | **중간 — 보존 처리가 전각 숫자를 보호하지 못하고 사용자 영역 문자를 바꿔요.** 재현 `N7`~`N9`. | 정규식은 전각 숫자도 잡지만 `_PROTECT`는 ASCII만 보호해요. 또한 입력에 있던 U+E031~U+E033도 마지막에 `123`으로 바뀌어요. | 원문 구간을 별도로 보관해요. 사용자 입력과 충돌하는 고정 문자 치환 대신 구간별 변환을 사용해요. |
| R32-8 | `korean_numbers.py:161`·`:200`·`:251` | **중간 — 전화번호의 공백 변형·혼합 구분자에서 자릿수가 사라져요.** 재현 `N10`~`N12`. | 전화번호 규칙은 ASCII 공백 한 칸만 받아요. 공백 정리는 숫자를 이미 정수로 축약한 뒤에 실행해요. | 전화번호 전체를 먼저 식별하고, 연속 공백·탭·혼합 구분자를 같은 번호 안에서 처리해요. |
| R32-9 | `tests/test_korean_numbers.py:78`·`:122`·`:128` | **낮음 — G15 21번은 아직 완료되지 않았어요.** 재현 `G15-21`: 형식 문자열을 그대로 반환해요. | 원래 기대값은 복구됐지만 시험은 별도 미완료 값과 비교해 통과해요. `13개 통과`가 `G15 30문장 일치`를 뜻하지 않아요. | 형식 낭독을 구현하거나 승인된 예외를 완료 조건에 반영해요. 그전까지 미완료로 유지해요. |

숫자 반례의 **입력·현재 출력·기대 읽기**는 다음과 같아요. `\t`는 탭, `\uE031` 등은 실제 해당 코드포인트를 뜻해요. 보존 사례의 기대값은 현재의 “모호하면 원문 유지” 정책 기준이에요.

| 재현 | 입력 | 지금 출력 | 기대 읽기 또는 보존값 |
|---|---|---|---|
| N1 | `경기는 3:10에 시작해요.` | `경기는 삼 대 십에 시작해요.` | `경기는 세 시 십 분에 시작해요.` |
| N2 | `3:10으로 이겼어요.` | `세 시 십 분으로 이겼어요.` | `삼 대 십으로 이겼어요.` |
| N3 | `경기 시작 시각은 3:10이에요.` | 입력 그대로예요. | `경기 시작 시각은 세 시 십 분이에요.` |
| N4 | `버전은 2026.10.06이에요.` | `버전은 이천이십육 년 시월 육 일이에요.` | `버전은 이천이십육 점 십 점 육이에요.` |
| N5 | `버전은 2.10이에요.` | `버전은 이 점 일 영이에요.` | `버전은 이 점 십이에요.` |
| N6 | `버전: 2.10` | `버전: 이 점 일 영` | `버전: 이 점 십` |
| N7 | `범위는 ２０-１０개예요.` | `범위는 이십-열 개예요.` | 입력 그대로 보존해요. |
| N8 | `혼합 비율은 ３:５예요.` | `혼합 비율은 삼:오예요.` | 입력 그대로 보존해요. ASCII `3:5`는 실제로 보존됐어요. |
| N9 | `문자 \uE031\uE032\uE033` | `문자 123` | 원래 코드포인트를 보존해요. |
| N10 | `가상 전화번호는 000  0000  0000이에요.` | `가상 전화번호는 영 영 영이에요.` | `가상 전화번호는 영영영, 영영영영, 영영영영이에요.` |
| N11 | `가상 전화번호는 000\t0000\t0000이에요.` | `가상 전화번호는 영\t영\t영이에요.` | N10과 같아요. |
| N12 | `가상 전화번호는 000 0000-0000이에요.` | `가상 전화번호는 영 영영영영, 영영영영이에요.` | N10과 같아요. |
| G15-21 | `가짜 전화번호 형식은 0X0-XXXX-XXXX예요.` | 입력 그대로예요. | `가짜 전화번호 형식은 공 엑스 공 하이픈 엑스 엑스 엑스 엑스 하이픈 엑스 엑스 엑스 엑스예요.` — G15 원문 기대값이에요. |

**R31 종결 판정은 4건 닫힘, 6건 남음이에요.** 기존 반례만 통과해도 같은 문제가 새 입력에서 재현되면 ‘남음’으로 판단했어요.

| 항목 | 판정 | 직접 확인한 근거 |
|---|---|---|
| R31-1 | **남음** | 기존 NFD·공백·제로폭 반례는 차단해요. 조합 변형은 통과해요(`P`). |
| R31-2 | **닫힘** | `1번` → `일 번` 변환 후 차단하며 합성 호출 0회예요(`D`). 다른 숫자 표기 문제는 R32-2예요. |
| R31-3 | **닫힘** | 기존 용량과 새 파일을 합산해요. 정확한 상한은 허용하고, 단독 초과·삭제 실패로 인한 용량 초과는 거절했어요. 개수 문제는 R32-3예요. |
| R31-4 | **닫힘** | 실행 중 작업 2개, 같은 글 재사용, 추가 20건은 모두 `busy`였어요(`J`). 완료 결과 소실은 R32-4예요. |
| R31-5 | **남음** | 기존 두 문장은 수정됐지만 N1~N3에서 시각/점수 문제가 재현돼요. |
| R31-6 | **남음** | `버전 2.10` 등은 수정됐지만 N4~N6은 틀려요. |
| R31-7 | **남음** | ASCII `20-10개`는 보존하지만 전각 숫자는 후속 규칙이 다시 바꿔요(N7·N8). |
| R31-8 | **닫힘** | `제  3장과 제  4권` → `제삼 장과 제사 권`을 확인했어요. |
| R31-9 | **남음** | 공백 한 칸은 수정됐지만 두 칸·탭·혼합 구분자는 자릿수를 잃어요(N10~N12). |
| R31-10 | **남음** | 기대값 복구와 미완료 표시는 완료됐어요. 낭독 구현 또는 예외 승인은 남았으며 G15는 29/30이에요. |

저장 검사에서는 **동시 요청 8건**도 메모리로 실행했어요. 상한 100바이트, 출력당 60바이트에서 저장 중 최대 합계는 60바이트였고, 저장 함수가 잠금 안에서 호출됨을 확인했어요. 실제 파일 삭제·음성 생성·외부 서비스는 실행하지 않았어요.

아래는 저장소 루트에서 실행하는 **공통 재현 명령 한 줄**이에요. `P`·`D`는 무해한 모의 금지 목록을 사용하고, `S`·`J`는 저장과 합성을 모의로 대체해요.

```powershell
python -B -X utf8 -c "exec('import sys,os,threading,unicodedata as u,runpy\nfrom types import SimpleNamespace as S\nfrom unittest.mock import patch,Mock,MagicMock\nsys.path.insert(0,\'apps/dido-assistant\')\nimport mcp_server as m,korean_numbers as k\neng=S(name=\'test\',label=\'성우 김디도\',mime=\'audio/wav\')\nwith patch.object(m.pathlib.Path,\'read_text\',return_value=\'\'),patch.object(m,\'BUILTIN_BLOCKED\',(\'시험\',\'abcd\',\'일 번\')),patch.object(m,\'_audit\'),patch.object(m,\'engine\',return_value=eng),patch.object(m,\'LIMIT\',S(allow=lambda:True)):\n with patch.object(m,\'_synth_with_budget\',return_value=None) as syn:\n  variants=[(\'원형\',\'시험\'),(\'공백\',\'시 험\'),(\'NFD\',u.normalize(\'NFD\',\'시험\')),(\'Cf\',\'시\\u200b험\'),(\'NFD+Cf\',\'\\u200b\'.join(u.normalize(\'NFD\',\'시험\'))),(\'Mn\',\'시\\u034f험\'),(\'VS\',\'시\\ufe0f험\'),(\'Me\',\'시\\u20dd험\'),(\'Mc\',\'시\\u0903험\'),(\'Cc\',\'시\\x00험\'),(\'채움\',\'시\\u3164험\'),(\'구두점\',\'시.험\'),(\'한자\',\'試驗\'),(\'호환자모\',\'ㅅㅣㅎㅓㅁ\'),(\'소문자\',\'aBcD\'),(\'전각\',\'ＡＢＣＤ\')]\n  for label,s in variants:\n   syn.reset_mock();m.speak_core(s,False);print(\'P\',label,\'blocked\',bool(m.check_policy(s)),\'synth\',syn.call_count)\n  for s in [\'1번\',\'１번\',\'١번\',\'①번\',\'¹번\',\'一번\',\'1.0번\']:\n   syn.reset_mock();m.speak_core(s,False);print(\'D\',s,\'=>\',k.normalize(s),\'synth\',syn.call_count)\n fs=[Mock(),Mock()];out=MagicMock();out.glob.return_value=fs\n for f in fs:\n  f.is_file.return_value=True;f.stat.return_value=S(st_size=50,st_mtime=0);f.unlink.side_effect=PermissionError(\'mock\')\n with patch.object(m,\'OUT_DIR\',out),patch.object(m,\'MAX_OUT_FILES\',2),patch.object(m,\'MAX_OUT_BYTES\',100),patch.object(m,\'_synth_with_budget\',return_value=(b\'x\',None)):\n  print(\'S\',\'단독초과\',m._prune_out(101),\'삭제실패용량\',m._prune_out(1))\n  for f in fs:f.stat.return_value=S(st_size=1,st_mtime=0)\n  r=m.speak_core(\'안녕하세요\',False)[0];writes=out.__truediv__.return_value.write_bytes.call_count\n  print(\'S\',\'삭제실패개수\',\'ok\',r[\'ok\'],\'writes\',writes,\'files\',len(fs)+writes)\n release=threading.Event();entered=threading.Event();calls=[]\n def fake(e,s):\n  calls.append(s);entered.set();release.wait();return b\'x\',None\n with patch.dict(os.environ,{\'DIDO_MCP_BUDGET\':\'0\'}),patch.object(m,\'synth_or_none\',side_effect=fake),patch.object(m,\'_JOBS\',{}):\n  try:\n   for s in [\'첫째\',\'둘째\']:\n    entered.clear();assert m._synth_with_budget(eng,s) is None;assert entered.wait(2)\n   same=m._synth_with_budget(eng,\'첫째\')\n   busy=sum(m._synth_with_budget(eng,\'추가\'+str(i)) is m.BUSY for i in range(20))\n   print(\'J\',\'jobs\',len(m._JOBS),\'calls\',len(calls),\'same_preparing\',same is None,\'busy\',busy)\n  finally:\n   ts=[t for t,b in m._JOBS.values()];release.set()\n   for t in ts:t.join()\n  print(\'J\',\'finished_jobs\',len(m._JOBS));release.clear();entered.clear()\n  try:\n   r=m._synth_with_budget(eng,\'첫째\');assert entered.wait(2)\n   print(\'J\',\'retry_preparing\',r is None,\'same_text_calls\',calls.count(\'첫째\'))\n  finally:\n   ts=[t for t,b in m._JOBS.values()];release.set()\n   for t in ts:t.join()\ncases=[\'경기는 3:10에 시작해요.\',\'3:10으로 이겼어요.\',\'경기 시작 시각은 3:10이에요.\',\'버전은 2026.10.06이에요.\',\'버전은 2.10이에요.\',\'버전: 2.10\',\'범위는 ２０-１０개예요.\',\'혼합 비율은 ３:５예요.\',\'문자 \\ue031\\ue032\\ue033\',\'가상 전화번호는 000  0000  0000이에요.\',\'가상 전화번호는 000\\t0000\\t0000이에요.\',\'가상 전화번호는 000 0000-0000이에요.\']\nfor i,s in enumerate(cases,1):print(\'N\'+str(i),repr(s),\'=>\',repr(k.normalize(s)))\nd=runpy.run_path(\'apps/dido-assistant/tests/test_korean_numbers.py\')\nprint(\'R31숫자\',sum(k.normalize(s)==w for s,w in d[\'R31\']),len(d[\'R31\']))\nprint(\'G15\',sum(k.normalize(s)==w for s,w in d[\'G15\']),len(d[\'G15\']))\nprint(\'G15-21\',d[\'G15\'][20][0],\'=>\',k.normalize(d[\'G15\'][20][0]),\'expected\',d[\'G15\'][20][1])')"
```

검토한 파일 목록: `AGENTS.md`, `TEAM_BOARD.md`의 R32·A21·A22·관련 보고, `docs/gpt/R31-review.md`, `docs/gpt/G15-number-sentences.md`, `apps/dido-assistant/`의 `mcp_server.py`, `korean_numbers.py`, 관련 시험 2개, `tts.py`·`brain.py` 관련 부분이에요. **실행해 본 것:** `python -c` 정규화·숫자 반례·내장 목록 검사·메모리 저장 및 동시 합성 모의, 숫자 시험 13개, G15 원문 비교, 관련 파일 Git 변경 확인이에요.
