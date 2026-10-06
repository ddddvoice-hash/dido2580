# R30 · GPT(아스트라) 결과 · 성우 김디도

> 실행 기록 머리(그대로 옮김):
> ```
> model: gpt-6-astra
> reasoning effort: high
> sandbox: read-only
> session id: 01a110b2-b4cc-7640-af30-fccfebfe961c
> ```
> 날짜: 2026-10-05 · 실행: 팀장이 `codex exec`로 돌림 · 아래는 GPT 답 원문(손대지 않음). 본문의 "모델 줄을 옮기지 못했다"는 말은 GPT가 자기 실행 기록을 볼 수 없어서이며, 위 머리가 실제 기록이에요.

**성우 김디도 · R30 검토 결과: R28 13건 중 12건은 닫힘, 1건은 남음이에요.** 추가로 클라우드 주소 검증·엔진 선택 순서·숫자 변환에 보완이 필요해요.

파일은 수정하지 않았어요. 이번 실행의 `model:`·`reasoning effort:`·`sandbox:` **실행 기록 원문은 제공되지 않아 옮기지 않았어요.** 과거 리뷰의 기록으로 대신하지 않았어요.

아래 파일명은 별도 표시가 없으면 `apps/dido-assistant/` 기준이에요. ‘닫힘’은 코드 확인과 메모리 모의 실행 범위의 판정이에요.

| 번호 | 파일:줄 | 문제 | 왜 문제인가 | 제안 |
|---|---|---|---|---|
| R28-1 | `server.py:71`, `server.py:83` | **닫힘 · 기존 높음** | 외부 Host·Origin과 `Origin: null`은 403, `text/plain`은 415로 거절해요. **재현 A의 R1**이에요. | 현재 검증을 유지해요. |
| R28-2 | `tts.py:25`, `tts.py:32`, `tts.py:70` | **닫힘 · 기존 높음** | 302 모의 응답에서 요청은 최초 목적지 1회뿐이고 이동하지 않았어요. 외부 평문 HTTP도 거절했어요. **재현 A의 R2**예요. | 새 클라우드 주소 우회는 N1처럼 별도로 막아요. |
| R28-3 | `brain.py:111`, `brain.py:134` | **닫힘 · 기존 높음·조건부** | 하위 링크 모의 입력에서 오류 표시 `True`, 검사기 실행 0회였어요. **재현 A의 R3**예요. 실제 링크는 생성하지 않았어요. | 검사기 자체의 `apps/voice-check/check.js:242`는 여전히 링크를 따라가므로, 이 판정은 비서 경유 호출에 한정해요. |
| R28-4 | `server.py:89`, `tts_server/server.py:70` | **남음 · 중간** | 기존 `-1`, `abc`, 과대 길이는 읽기 전에 400/413으로 막아요. 하지만 **5,000자리 숫자 길이**는 `int()`에서 `ValueError`가 나요. 비서 서버는 500, 목소리 서버는 처리되지 않은 예외예요. **재현 A의 R4**예요. | 정수 변환 전에 자릿수를 제한하고, 변환 예외도 400/413으로 처리해요. |
| R28-5 | `korean_numbers.py:82`, `korean_numbers.py:98`, `server.py:120` | **닫힘 · 기존 높음** | 번호·날짜·큰 수의 기존 반례 모두 예외 없이 처리됐고 `/api/normalize`도 200이었어요. **재현 B**예요. | 큰 수가 남는 문제와 후속 재치환은 N4로 구분해요. |
| R28-6 | `korean_numbers.py:67`, `korean_numbers.py:93` | **닫힘 · 기존 중간** | `1,234.56원` → `천이백삼십사 점 오 육 원`이에요. **재현 B**예요. | 쉼표 목록과 소수 회귀 검사를 유지해요. |
| R28-7 | `korean_numbers.py:77`, `korean_numbers.py:122` | **닫힘 · 기존 중간** | `1번째예요.` → `첫 번째예요.`예요. **재현 B**예요. | `제1장` 문제는 별도로 남아 있어요. |
| R28-8 | `brain.py:166`, `brain.py:225`, `brain.py:289` | **닫힘 · 기존 중간** | 깨진 도구 JSON은 오류 결과로 반환하고 대화 기록 4개가 완성됐어요. 예상 밖 예외는 기록 0개로 정리했고, 초기화 실패는 오프라인으로 전환했어요. **재현 A의 R8**이에요. | 현재 처리를 유지해요. |
| R28-9 | `brain.py:125`, `brain.py:162` | **닫힘 · 기존 중간** | 없는 폴더·실행 파일 없음·시간 초과 모두 오류 표시가 `True`였어요. **재현 A의 R9는 없는 폴더 경로**예요. | 실패 구분을 유지해요. |
| R28-10 | `index.html:175`, `index.html:190`, `index.html:200` | **닫힘 · 기존 중간** | Esc 후 인식 중단 1회, 자동 대화 요청 0회였어요. **재현 C의 R28-10**이에요. | 실제 마이크 동작은 별도 확인이 필요해요. |
| R28-11 | `index.html:142`, `index.html:150`, `index.html:161` | **닫힘 · 기존 중간** | 초기화 대기 중 추가 전송을 막고, 초기화 뒤 늦게 도착한 이전 답변을 버렸어요. **재현 C의 R28-11**이에요. | 현재 세대 번호 검사를 유지해요. |
| R28-12 | `index.html:71`, `index.html:216`, `index.html:223` | **닫힘 · 기존 중간** | 대본 통신 실패를 안내하고, 숫자 탭 안내도 패널 밖 공통 상태 영역에 표시했어요. **재현 C의 R28-12**예요. | 실제 화면 읽기 프로그램 검증은 남겨요. |
| R28-13 | `server.py:173`; `apps/start-assistant.cmd:17`, `:23` | **닫힘 · 기존 중간** | 포트 오류 모의 실행은 안내 후 종료값 2였어요. 시작 파일의 사전 확인·대기 확인 모두 서비스 식별값을 검사해요. **재현 A의 R13**이에요. | 시작 파일 실제 실행은 이번 범위에서 하지 않았어요. |

**새 지적이에요.**

| 번호 | 파일:줄 | 문제 | 왜 문제인가 | 제안 |
|---|---|---|---|---|
| N1 | `tts.py:148`, `tts.py:152` | **높음·설정 조건부 — 클라우드 API 주소 검증이 없어요.** | 빈 인증값과 모의 전송기로 확인했어요. `DIDO_ELEVEN_API=http://remote.invalid/`도 요청을 만들고 `xi-api-key` 헤더를 붙여요. 리디렉션 차단은 **최초 목적지**를 검증하지 않아요. 실제 키가 설정됐을 때의 유출 가능성은 **코드에 근거한 추측**이에요. [공식 인증 안내](https://elevenlabs.io/docs/api-reference/authentication) | 운영 주소를 공식 HTTPS 호스트로 고정해요. 시험 주소는 모의 전송기 주입으로 분리해요. |
| N2 | `tts.py:3`, `tts.py:176`, `tts.py:183` | **중간 — 자동 선택 순서가 설명과 달라요.** | 두 설정이 있으면 실제 선택은 `http`예요. HTTP 주소가 안전하지 않으면 바로 `browser`를 반환해 준비된 클라우드 후보도 건너뛰어요. **직접 모의 실행으로 확인했어요.** 출처는 해당 코드와 상단 설명이에요. | 의도한 우선순위를 확정해 구현·설명·검사를 일치시켜요. |
| N3 | `korean_numbers.py:98` | **중간 — 유효하지 않은 날짜도 확정 변환해요.** | `2026-99-99` → `이천이십육 년 구십구월 구십구 일`, `2026-02-31` → `이천이십육 년 이월 삼십일 일`이에요. **재현 B**, 날짜 정규식·치환 함수가 출처예요. | 달력 유효성을 검사하고 잘못된 날짜는 원문과 확인 안내를 반환해요. |
| N4 | `korean_numbers.py:82`, `korean_numbers.py:109`, `korean_numbers.py:129`, `korean_numbers.py:136` | **중간 — `_safe`가 남긴 원문을 후속 규칙이 다시 바꿔요.** | `10000000000000000.5원` → `10000000000000000.오 원`, `10000000000000000/2` → `10000000000000000/이`예요. **재현 B**, 순차 치환 루프가 출처예요. | 실패한 숫자 덩어리를 보호하고, 미지원 구간을 별도로 반환해요. |

**클라우드 규격은 2026년 10월 6일 조회한 공식 문서 기준으로 확인했어요.**

| 확인 항목 | 판정 |
|---|---|
| 주소·요청 | `POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}`, JSON의 `text`·`model_id` 구조가 현재 코드와 맞아요. [공식 API 규격](https://elevenlabs.io/docs/api-reference/text-to-speech/convert) |
| 인증 | `xi-api-key` 헤더가 맞아요. 코드에서도 헤더 이름을 확인했으며 실제 인증값은 사용하지 않았어요. [공식 인증 안내](https://elevenlabs.io/docs/api-reference/authentication) |
| 응답 형식 | 응답은 오디오 바이트이고, `output_format` 기본값은 `mp3_44100_128`이에요. 현재 `audio/mpeg` 지정과 맞아요. 형식을 명시하면 계약이 더 분명해져요. [공식 API 규격](https://elevenlabs.io/docs/api-reference/text-to-speech/convert) |
| 현재 기본 모델 | `eleven_multilingual_v2`는 한국어 지원 모델이므로 **잘못된 ID가 아니에요**. [공식 모델 목록](https://elevenlabs.io/docs/overview/models) |
| 최신 한국어 후보 | `eleven_v4`, 실시간 후보 `eleven_v4_turbo`가 공식 목록에 있고 한국어를 지원해요. 발표는 2026-09-28, 갱신은 2026-10-05로 표시돼요. 실제 한국어 품질 우열은 **미검증**이에요. [공식 모델 목록](https://elevenlabs.io/docs/overview/models), [공식 발표](https://elevenlabs.io/blog/eleven-v4) |
| 최신 모델 연결 방식 | 빠른 시작 문서는 `eleven_v4`의 TTS 호출을 보여 줘요. `eleven_v4_turbo` 실시간 안내는 별도 `wss://api.elevenlabs.io/v1/text-to-dialogue/stream-input` 규격이에요. 현재 REST 엔진에서 ID만 바꾸면 동작한다고 단정하지 않아요. [빠른 시작](https://elevenlabs.io/docs/eleven-api/quickstart), [실시간 연결 규격](https://elevenlabs.io/docs/eleven-api/guides/how-to/websockets/realtime-tdd) |
| 화면 재생 | `audio_type`이 대화·숫자 읽기·다시 듣기에 전달돼요. 모의 실행에서 두 재생 모두 `data:audio/mpeg;…`였어요. 실제 디코딩·청취는 하지 않았어요. |

키의 **로그·오류 안내 노출은 검사한 경로에서 재현되지 않았어요.** `synth_or_none()`에 HTTP·연결·실행·값 오류를 넣었을 때 오류 본문의 일반 표식이 반환값·표준 출력·표준 오류에 나타나지 않았어요. 서버의 일반 오류 응답과 도구 예외도 원문을 숨겨요. 운영 로그와 실제 키를 넣은 호출은 확인하지 않았으므로, 모든 경로의 무유출을 보증하는 판정은 아니에요.

**R27 숫자 반례도 남아 있어요.** G15 30문장을 다시 돌린 결과는 **17개 일치·13개 불일치**로 이전과 같아요. 20·26번은 띄어쓰기 차이이며, 초안의 잠정 읽기도 있어 13개를 모두 오독으로 집계하면 안 돼요.

| 범위 | 현재 남은 출력 |
|---|---|
| 시각·대분수·순서·개수 | `00:05` → `영:오`, `1 1/2` → `일 이분의 일`, `제1장` → `제한 장`, `3자루` → `삼자루` |
| 기호·식별자 | `3.2㎞` → `삼 점 이㎞`, `0.75㎏` → `영 점 칠 오㎏`, `-3℃` → `-삼℃`, `0:2` → `영:이`, `2.10.3` → `이 점 일 영.삼` |
| R27 추가 반례 | `2026/10/06` → `십분의 이천이십육/육`, `20-10` → `이영, 일영`, `제3장과 제4권` → `제세 장과 제네 권`, `6 월` → `육 월`, `3km²` → `삼 킬로미터²` |
| 미지원 보존 | `10000000000000000`은 그대로 남으며 별도 경고가 없어요. |
| 개선·유지 | 하이픈 날짜는 개선됐어요. 쉼표 소수·쉼표 목록·숫자 없는 문장은 이번 검사에서도 정상 처리됐어요. |

재현 명령은 저장소 루트에서 실행해요. 각 블록은 **한 줄 전체를 붙여 넣고 Enter 한 번**이면 돼요. 파일을 쓰거나 서버를 띄우지 않아요.

**A — R28의 1·2·3·4·8·9·13번이에요.** R4의 `VALUE_ERROR`가 남은 문제예요.

```powershell
python -B -X utf8 -c "exec('import sys,io,os,types,runpy,urllib.request as u,urllib.response as r,urllib.error\nfrom pathlib import Path\nfrom unittest.mock import patch\nsys.path[:0]=[\'apps/dido-assistant/tests\',\'apps/dido-assistant\']\nimport server,tts,brain,test_server as t\npatch.dict(os.environ,{},clear=True).start()\ndef h(C,H):\n x=object.__new__(C); x.headers=H; x.rfile=io.BytesIO(b\'{}\'); x.path=\'/tts\'; x.server=types.SimpleNamespace(server_address=(\'127.0.0.1\',8770)); x._json=x._err=lambda c,o:print(\'HTTP\',c); return x\nbase={\'Host\':\'127.0.0.1:8770\',\'Content-Type\':\'application/json\',\'Content-Length\':\'2\'}\nfor e in ({\'Host\':\'x.invalid\'},{\'Origin\':\'null\'},{\'Origin\':\'https://x.invalid\'},{\'Content-Type\':\'text/plain\'},{}):\n x=h(server.Handler,base|e); print(\'R1\',x._guard(),x._body()[1])\nV=runpy.run_path(\'apps/dido-assistant/tts_server/server.py\')[\'Handler\']\nfor C in (server.Handler,V):\n for n in (\'-1\',\'abc\',\'999999999\',\'9\'*5000):\n  x=h(C,base|{\'Content-Length\':n})\n  try: print(\'R4\',C.__module__,len(n),x._body() if C is server.Handler else x.do_POST())\n  except ValueError: print(\'R4 VALUE_ERROR\',C.__module__,len(n))\ndef wire(self,q):\n self.calls+=1; z=r.addinfourl(io.BytesIO(),{\'Location\':\'https://target.invalid/\'},q.full_url,302); z.msg=\'Found\'; return z\nm=type(\'M\',(u.HTTPSHandler,),{\'https_open\':wire,\'calls\':0})()\nwith patch(\'socket.create_connection\',side_effect=AssertionError(\'network\')):\n try: u.build_opener(u.ProxyHandler({}),m,tts._NoRedirect()).open(\'https://source.invalid/\')\n except urllib.error.HTTPError: print(\'R2\',m.calls)\nroot=Path(\'apps/dido-assistant\').resolve()\nwith patch.object(brain,\'recordings_root\',return_value=root),patch.object(brain.os,\'walk\',return_value=[(str(root),[\'link\'],[])]),patch.object(brain.os.path,\'realpath\',side_effect=lambda p:str(root.parent) if str(p).endswith(\'link\') else str(p)),patch.object(brain.subprocess,\'run\') as run:\n print(\'R3\',brain.run_tool(\'check_recordings\',{})[1],run.call_count)\nwith patch.object(brain.os.environ,\'get\',side_effect=lambda k,d=None:True if k==\'ANTHROPIC_API_KEY\' else d):\n x=t.ClaudePath()\n for n in (\'test_bad_tool_json_becomes_error_result\',\'test_unexpected_exception_cleans_history\',\'test_client_creation_failure_goes_offline\'): getattr(x,n)()\n print(\'R8 PASS\')\nwith patch.object(brain.pathlib.Path,\'is_dir\',return_value=False): print(\'R9\',brain.run_tool(\'check_recordings\',{})[1])\nwith patch.object(server,\'Server\',side_effect=OSError()): print(\'R13\',server.main([]),Path(\'apps/start-assistant.cmd\').read_text(encoding=\'utf-8\').count(\'service -eq\'))')"
```

**B — R28의 5·6·7번, R27 전체 숫자 반례, N3·N4예요.**

```powershell
python -B -X utf8 -c "import sys,re,unittest; from pathlib import Path; sys.path.insert(0,'apps/dido-assistant'); from korean_numbers import normalize as n; unittest.TextTestRunner().run(unittest.defaultTestLoader.discover('apps/dido-assistant/tests',pattern='test_korean_numbers.py')); rows=[list(map(str.strip,l.strip('|').split('|'))) for l in Path('docs/gpt/G15-number-sentences.md').read_text(encoding='utf-8').splitlines() if re.match(r'\| \d{2} \|',l)]; print('TOTAL',len(rows),'EXACT',sum(n(r[2])==r[3] for r in rows)); [print(r[0],r[2],'=>',n(r[2])) for r in rows if n(r[2])!=r[3]]; [print('R27',s,'=>',n(s)) for s in [l.split(' => ')[0] for l in Path('docs/gpt/R27-review.md').read_text(encoding='utf-8').splitlines() if ' => ' in l]]; [print(s,'=>',n(s)) for s in ['시험 번호는 12-12예요.','날짜는 2026-10-06이에요.','10000000000000000원이에요.','1,234.56원이에요.','1번째예요.','2026-99-99','2026-02-31','10000000000000000.5원','10000000000000000/2']]"
```

**C — R28의 10·11·12번과 `audio_type` 재생이에요.** Python에서 화면 코드를 메모리상의 JavaScript 실행기로 전달해요.

```powershell
python -B -X utf8 -c "import subprocess; j='const fs=require(\'fs\'),vm=require(\'vm\');const html=fs.readFileSync(\'apps/dido-assistant/index.html\',\'utf8\'),src=html.split(\'<script>\')[1].split(\'</script>\')[0];const nodes={},docEvents={},requests=[],sounds=[];let rec,aborts=0;function el(){return {value:\'\',children:[],events:{},hidden:false,classList:{add(){},remove(){}},setAttribute(){},focus(){},appendChild(x){this.children.push(x)},addEventListener(n,f){this.events[n]=f},set textContent(t){this.txt=t;this.children=[]},get textContent(){return this.txt||\'\'}}}function get(id){return nodes[id]||(nodes[id]=el())}const replies={};const ctx={document:{getElementById:get,createElement:el,addEventListener:(n,f)=>docEvents[n]=f},speechSynthesis:{cancel(){},getVoices(){return []},speak(){}},SpeechSynthesisUtterance:function(){},Audio:function(url){sounds.push(url);this.pause=()=>{};this.play=()=>Promise.resolve()},SpeechRecognition:function(){rec=this;this.start=()=>{};this.abort=()=>aborts++;this.stop=()=>{}},fetch:(url,opts)=>{requests.push(url);return url===\'/api/status\'?Promise.resolve({json:()=>Promise.resolve({mode:\'offline\',engine:\'browser\',greeting:\'AI 비서\'})}):replies[url]()}};ctx.window=ctx;vm.runInNewContext(src,ctx);const flush=async()=>{for(let i=0;i<8;i++)await Promise.resolve()};const ok=x=>({json:()=>Promise.resolve(x)});(async()=>{await flush();get(\'mic\').events.click();rec.onresult({results:[[{transcript:\'시험\'}]]});docEvents.keydown({key:\'Escape\'});rec.onend();await flush();console.log(\'R28-10\',aborts,requests.filter(x=>x===\'/api/chat\').length);let chatEnd,resetEnd;replies[\'/api/chat\']=()=>new Promise(r=>chatEnd=r);replies[\'/api/reset\']=()=>new Promise(r=>resetEnd=r);get(\'q\').value=\'x\';get(\'send\').events.click();get(\'reset\').events.click();get(\'q\').value=\'y\';get(\'send\').events.click();console.log(\'R28-11-pending\',requests.filter(x=>x===\'/api/chat\').length);resetEnd(ok({ok:true}));await flush();chatEnd(ok({text:\'OLD\',speak:\'OLD\'}));await flush();console.log(\'R28-11-log\',get(\'log\').children.length,get(\'log\').children.some(x=>x.textContent===\'OLD\'));replies[\'/api/script\']=()=>Promise.reject(Error(\'offline\'));get(\'script\').value=\'3\';get(\'script-go\').events.click();await flush();console.log(\'R28-12-script\',get(\'say\').textContent.includes(\'닿지 못\'));get(\'t-num\').events.click();replies[\'/api/speak\']=()=>Promise.resolve(ok({speak:\'세 시\',audio:\'SUQz\',audio_type:\'audio/mpeg\',note:\'NOTICE\'}));get(\'num\').value=\'3\';get(\'num-go\').events.click();await flush();get(\'again\').events.click();console.log(\'AUDIO_TYPE\',sounds.every(x=>x.startsWith(\'data:audio/mpeg;\')),sounds.length);console.log(\'R28-12-note\',get(\'say\').textContent===\'NOTICE\',\'status_outside_panel\',html.indexOf(\'id=\x22say\x22\')<html.indexOf(\'<section\'));})();'; r=subprocess.run(['node','-e',j],capture_output=True,text=True,encoding='utf-8'); print(r.stdout); print(r.stderr); assert r.returncode==0"
```

**검토한 파일 목록:** `AGENTS.md`, `TEAM_BOARD.md` R30·관련 지시, `docs/gpt/R28-review.md`, `R27-review.md`, `G15-number-sentences.md`, 비서의 `server.py`, `tts.py`, `korean_numbers.py`, `brain.py`, `index.html`, `tts_server/server.py`, `tests/test_server.py`, `tests/test_korean_numbers.py`, `tests/assistant.browser.js`, `apps/start-assistant.cmd`, `apps/voice-check/check.js` 관련 부분 · **실행해 본 것:** 숫자 테스트 9개 통과, 독립 30문장·추가 반례, 핸들러·리디렉션·도구·오류·화면 이벤트 메모리 모의 실행, 공식 문서 조회예요. 파일 수정·서버 기동·실제 음성 API 호출·청취는 하지 않았어요.
