# R31 · GPT(아스트라) 결과 · 성우 김디도

> 실행 기록 머리(그대로 옮김):
> ```
> model: gpt-6-astra
> reasoning effort: high
> sandbox: read-only
> session id: 01a11157-8ebe-76f2-b419-c69b289dd900
> ```
> 날짜: 2026-10-05 · 실행: 팀장이 `codex exec`로 돌림 · 아래는 GPT 답 원문(손대지 않음). 본문의 "모델 줄을 옮기지 못했다"는 말은 GPT가 자기 실행 기록을 볼 수 없어서이며, 위 머리가 실제 기록이에요.

**성우 김디도 · R31 검토 결과: A19·A20에 수정이 필요한 문제가 남아 있어요.** 숫자 시험 11개는 통과했고, G15 원문과 직접 비교하면 **30문장 중 29문장**이 일치해요.

실행 머리의 `model:`·`reasoning effort:`·`sandbox:` 원문은 제공되지 않아 임의로 적지 않았어요. 게시판과 결과 파일은 수정하지 않았어요.

아래 파일명은 `apps/dido-assistant/` 기준이에요. **현재 출력은 직접 실행한 결과**예요. 새 반례의 기대 읽기는 문맥에 따른 검수 제안이며, 별도 표준 자료로 확인하지 않은 판단은 **추측**이에요.

| 번호 | 파일:줄 | 문제 | 왜 문제인가 | 제안 |
|---|---|---|---|---|
| R31-1 | `mcp_server.py:99` | **높음 — 유니코드 변형으로 금지 문구 검사를 통과해요.** 재현 `M1`: 원문·일반 띄어쓰기는 차단하지만, 한글 분해형(NFD)·U+200B 삽입형은 통과해요. | 공백 제거만 하고 유니코드 정규화는 하지 않아요. 같은 문구의 표기 변형을 놓쳐요. 실제 음성 출력은 검사하지 않았어요. | 입력과 금지 목록을 같은 방식으로 정규화하고, 보이지 않는 문자 처리 기준을 정해요. |
| R31-2 | `mcp_server.py:199`, `:205` | **높음 — 숫자를 풀면서 생기는 금지 문구를 놓쳐요.** 재현 `M2`: 메모리 금지 목록을 무해한 시험 문구 `일 번`으로 두면, 입력 `1번`이 변환 후 금지 문구가 되어도 합성 함수에 도달해요. | 금지 검사가 숫자 변환 전에만 있어요. 결과는 `False True preparing 1`이에요. | 원문과 최종 합성문 모두 검사해요. |
| R31-3 | `mcp_server.py:142`, `:225`, `:230` | **중간 — 저장 용량 상한을 넘겨도 성공해요.** 재현 `M3`: 기존 용량이 104,857,600바이트일 때 1바이트를 추가해 `ok=True`, 총 104,857,601바이트예요. | 저장 전에 기존 파일만 계산하고, 새 소리 크기는 포함하지 않아요. | 기존 용량과 새 소리 크기를 합쳐 검사하고, 정리·저장을 하나의 잠금 안에서 처리해요. |
| R31-4 | `mcp_server.py:188`, `:190`, `:215` | **높음 — 시간 초과 후에도 합성 작업이 누적돼요.** 재현 `M4`: 모의 시계의 두 분 구간에서 요청 20개가 모두 `preparing`으로 반환되고, 작업 20개가 미완료 상태로 남아요. | 분당 호출 제한은 동시 작업 수를 제한하지 않아요. 시험에서는 대기 시간을 0으로 줄여 재현했어요. 실제 자원 고갈은 실행하지 않았고, 그 영향은 **추측**이에요. | 실행 중 작업 수·대기열 상한을 두고, 같은 글의 진행 중 작업은 재사용해요. |
| R31-5 | `korean_numbers.py:135`, `:139` | **중간 — 시각과 점수를 뒤바꿔요.** 재현 `N`: `경기 점수는 3:10이에요.` → `경기 점수는 세 시 십 분이에요.` / `시각은 9:5예요.` → `시각은 구 대 오예요.` | 오른쪽 숫자의 자릿수로 뜻을 결정해요. | 기대 읽기(**추측**): `경기 점수는 삼 대 십이에요.` / `시각은 아홉 시 오 분이에요.` 문맥이나 명시적 읽기 유형을 받아요. |
| R31-6 | `korean_numbers.py:129`, `:132`, `:162` | **중간 — 버전을 날짜·소수로 읽어요.** 재현 `N`: `버전 2026.10.06` → `버전 이천이십육 년 시월 육 일`; `버전 2.10` → `버전 이 점 일 영`. | 날짜 규칙이 먼저 적용되고, 두 부분 버전은 버전 규칙에서 빠져요. | 기대 읽기(**추측**, 기존 버전 규칙과 일관된 안): `버전 이천이십육 점 십 점 육` / `버전 이 점 십`. |
| R31-7 | `korean_numbers.py:119`, `:180`, `:185` | **중간 — 보존한 범위를 뒤 규칙이 다시 바꿔요.** 재현 `N`: `범위는 20-10개예요.` → `범위는 이십-열 개예요.` | 하이픈 규칙에서 원문을 반환해도 이후 단위 규칙의 처리 대상에 남아요. | 모호한 덩어리는 끝까지 보존해요. 범위로 확정한 경우의 기대 읽기(**추측**)는 `범위는 스무 개에서 열 개예요.`예요. |
| R31-8 | `korean_numbers.py:172`, `:180` | **중간 — 공백 두 칸 때문에 순서가 개수로 바뀌어요.** 재현 `N`: `제  3장과 제  4권` → `제 세 장과 제 네 권`. | `제` 뒤 공백을 최대 한 글자만 허용해요. 마지막 공백 정리는 이미 잘못 변환한 뒤예요. | 기대 읽기: `제삼 장과 제사 권`. 공백 변형에도 기존 순서 규칙을 적용해요. |
| R31-9 | `korean_numbers.py:145`, `:185` | **중간 — 띄어 쓴 전화번호에서 자릿수가 사라져요.** 재현 `N`: `가상 전화번호는 000 0000 0000이에요.` → `가상 전화번호는 영 영 영이에요.` | 하이픈이 없으면 각 묶음을 정수 0으로 축약해요. 전부 0인 시험용 문자열로 확인했어요. | 기대 읽기(**추측**, 현재 ‘영’ 정책 유지): `가상 전화번호는 영영영, 영영영영, 영영영영이에요.` 번호 문맥에서는 자릿수를 보존해요. |
| R31-10 | `tests/test_korean_numbers.py:77` | **낮음 — G15 기대값을 구현에 맞춰 바꿔 시험하고 있어요.** 재현 `G15`: 21번 입력·현재 출력 모두 `가짜 전화번호 형식은 0X0-XXXX-XXXX예요.`예요. | 원문 기대 읽기는 `가짜 전화번호 형식은 공 엑스 공 하이픈 엑스 엑스 엑스 엑스 하이픈 엑스 엑스 엑스 엑스예요.`예요. 게시판에 예외를 보고했지만, 원래 완료 조건인 30문장 일치와는 달라요. | 이 항목을 승인된 예외로 완료 조건에 명시하거나, 형식 낭독 기능을 구현해요. |

설정 보존은 검사한 범위에서 통과했어요. `connect.py:101`·`:223`의 병합 함수를 **메모리 문자열과 모의 경로**로 호출해 다른 서버·일반 설정·기존 `env`·`timeout` 보존, 반복 실행, BOM·CRLF, 여러 줄 배열을 확인했어요. 지원하지 않는 TOML 점 표기와 잘못된 JSON은 쓰기 없이 거절했어요. 실제 파일 백업·원자적 교체는 검사하지 않았어요.

다음 항목도 직접 확인했어요.

- `2026/10/06`·`2026.10.06`은 모두 `이천이십육 년 시월 육 일`로 읽어요.
- `20-10`은 그대로 보존하고, `제3장과 제4권`은 `제삼 장과 제사 권`으로 읽어요.
- `00:05`, `0:2`, `2.10.3`, 점 세 개인 `192.0.2.10`은 게시판에 적힌 처리 방식과 일치해요.
- 입력 401자는 거절하고, 입력 395자가 변환 후 791자가 되는 경우도 합성 전에 거절해요.
- 한 제한기에서 분당 11번째·하루 301번째 호출은 거절해요. 새 제한기에는 기록이 이어지지 않아요.
- 인증 머리글 누락·잘못된 값은 401, 웹소켓은 1008로 거절해요. 토큰 없는 HTTP 시작도 거절했어요. 실제 토큰은 읽거나 만들지 않았어요.

각 지적의 재현 표시는 아래 **한 줄 명령**의 출력 이름이에요. 저장소 루트에서 실행하며, 설정 저장·음성 저장·합성은 모두 모의 객체로 대체해요.

```powershell
python -B -X utf8 -c "exec('import sys,json,tomllib,copy,re,os,unicodedata,threading\nfrom pathlib import Path\nfrom types import SimpleNamespace as S\nfrom unittest.mock import Mock,MagicMock,patch\nsys.path.insert(0,\'apps/dido-assistant\')\nimport korean_numbers as k,connect as c,mcp_server as m\nfor s in [\'2026/10/06\',\'2026.10.06\',\'20-10\',\'제3장과 제4권\',\'00:05\',\'0:2\',\'IP 192.0.2.10\',\'버전 2.10.3\',\'경기 점수는 3:10이에요.\',\'시각은 9:5예요.\',\'버전 2026.10.06\',\'버전 2.10\',\'범위는 20-10개예요.\',\'제  3장과 제  4권\',\'가상 전화번호는 000 0000 0000이에요.\']:\n print(\'N\',s,\'=>\',k.normalize(s))\nrows=[[x.strip() for x in line.split(\'|\')[1:-1]] for line in Path(\'docs/gpt/G15-number-sentences.md\').read_text(encoding=\'utf-8\').splitlines() if re.match(r\'\\| \\d{2} \\|\',line)]\nprint(\'G15\',sum(k.normalize(r[2])==r[3] for r in rows),len(rows))\nfor r in rows:\n if k.normalize(r[2])!=r[3]:print(\'G15 mismatch\',r[0],r[2],k.normalize(r[2]),r[3])\nc.server_cmd=lambda:(\'python\',[\'mcp_server.py\'])\nq=chr(34);ts=\'theme = \'+q+\'dark\'+q+\'\\n[mcp_servers.\'+c.NAME+\']\\ncommand = \'+q+\'old\'+q+\'\\nargs = []\\nenv = { MODE = \'+q+\'demo\'+q+\' }\\ntimeout = 42\\n[other]\\ncount = 7\\n\'\njs=json.dumps({\'theme\':\'dark\',\'mcpServers\':{c.NAME:{\'command\':\'old\',\'args\':[],\'env\':{\'MODE\':\'demo\'},\'timeout\':42},\'other\':{\'command\':\'keep\'}}})\nfor fn,raw,parse,key in [(c.merge_codex,ts,tomllib.loads,\'mcp_servers\'),(c.merge_json,js,json.loads,\'mcpServers\')]:\n p=Mock();p.exists.return_value=True;p.read_bytes.return_value=raw.encode()\n with patch.object(c,\'_backup\'),patch.object(c,\'_atomic_write\') as w:\n  state=fn(p,False)[0];after=parse(w.call_args.args[1].decode());want=copy.deepcopy(parse(raw));mine=want[key][c.NAME];mine.update(command=\'python\',args=[\'mcp_server.py\'])\n  if key==\'mcp_servers\':mine.setdefault(\'tool_timeout_sec\',120)\n  print(\'C\',key,state,\'preserved\',after==want)\nwith patch.object(m.pathlib.Path,\'read_text\',return_value=\'\'):\n t=m.BUILTIN_BLOCKED[4]\n print(\'M1 blocked\',[bool(m.check_policy(s)) for s in [t,\' \'.join(t),unicodedata.normalize(\'NFD\',t),chr(8203).join(t)]])\neng=S(name=\'test\',label=\'성우 김디도\',mime=\'audio/wav\')\nwith patch.object(m.pathlib.Path,\'read_text\',return_value=\'일 번\'),patch.object(m,\'_audit\'),patch.object(m,\'engine\',return_value=eng),patch.object(m,\'_synth_with_budget\',return_value=None) as synth,patch.object(m,\'LIMIT\',m.RateLimit()):\n print(\'M2\',bool(m.check_policy(\'1번\')),bool(m.check_policy(k.normalize(\'1번\'))),m.speak_core(\'1번\',False)[0].get(\'status\'),synth.call_count)\nold=Mock();old.is_file.return_value=True;old.stat.return_value=S(st_size=m.MAX_OUT_BYTES,st_mtime=0)\nout=MagicMock();out.glob.return_value=[old]\nwith patch.object(m,\'OUT_DIR\',out),patch.object(m,\'_audit\'),patch.object(m,\'check_policy\',return_value=None),patch.object(m,\'LIMIT\',m.RateLimit()),patch.object(m,\'engine\',return_value=eng),patch.object(m,\'_synth_with_budget\',return_value=(b\'x\',None)):\n r=m.speak_core(\'안녕하세요\',False)[0];print(\'M3\',r[\'ok\'],old.unlink.call_count,m.MAX_OUT_BYTES+len(out.__truediv__.return_value.write_bytes.call_args.args[0]))\nrelease=threading.Event();started=[];finished=[]\ndef synth(eng,text):\n started.append(text);release.wait(3);finished.append(text);return b\'x\',None\nwith patch.dict(os.environ,{\'DIDO_MCP_BUDGET\':\'0\',\'DIDO_MCP_PER_MIN\':\'10\',\'DIDO_MCP_PER_DAY\':\'300\'}),patch.object(m,\'check_policy\',return_value=None),patch.object(m,\'_audit\'),patch.object(m,\'LIMIT\',m.RateLimit()),patch.object(m,\'engine\',return_value=eng),patch.object(m,\'synth_or_none\',side_effect=synth),patch.object(m.time,\'time\',return_value=1000) as tm:\n try:\n  for minute in range(2):\n   tm.return_value=1000+minute*61\n   for i in range(10):assert m.speak_core(\'안녕하세요\',False)[0].get(\'status\')==\'preparing\'\n  print(\'M4\',len(started),len(finished))\n finally:release.set()\n')"
```

검사 도중 모의 합성 함수 지정이 빠진 실행에서 출력 폴더 생성 시도가 있었지만, 읽기 전용 환경이 차단했어요. 모의 처리를 보완한 뒤 다시 검사했어요. 실제 사용자 설정·외부 합성 서비스는 호출하지 않았고, 금지된 명령도 실행하지 않았어요.

검토한 파일 목록: `AGENTS.md`, `TEAM_BOARD.md`의 R31·A19·A20, `docs/gpt/G15-number-sentences.md`, `apps/dido-assistant/`의 `korean_numbers.py`, `connect.py`, `mcp_server.py`, 관련 시험 3개, `tts.py`·`brain.py` 관련 부분 · 실행해 본 것: `python -c` 숫자 반례·G15 30문장 비교·메모리 설정 보존·모의 제한 검사, 기존 숫자 시험 11개 통과, 작업 전후 Git 상태 확인이에요.
