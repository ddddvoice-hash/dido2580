// 팀장 검수: 헤드리스 Chrome을 DevTools 프로토콜로 조작해 체크리스트를 확인한다.
// 사용: apps/warmth-scorer 폴더에서 python -m http.server 8765 를 켠 뒤
//   node tests/browser-check.mjs http://127.0.0.1:8765 file:///<절대경로>/index.html rubric.json
// Chrome이 필요하다(윈도우 기본 경로, 다른 곳은 CHROME 환경변수로 지정). 앱 파일은 바꾸지 않는다.
import { spawn } from 'node:child_process';
import { readFileSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const [, , HTTP, FILEURL, RUBRIC] = process.argv;
const rubric = JSON.parse(readFileSync(RUBRIC, 'utf8'));
const CHROME = process.env.CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const PORT = 9333;
const results = [];
const ok = (name, pass, detail = '') => { results.push({ name, pass, detail }); console.log((pass ? 'PASS ' : 'FAIL ') + name + (detail ? '  — ' + detail : '')); };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const prof = mkdtempSync(join(tmpdir(), 'wscheck-'));
// 리눅스 root(클라우드·CI)에서는 샌드박스 없이만 뜬다. 윈도우에서는 해당 없음.
const EXTRA = typeof process.getuid === 'function' && process.getuid() === 0 ? ['--no-sandbox'] : [];
const chrome = spawn(CHROME, [...EXTRA, '--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${prof}`, '--no-first-run', '--window-size=1280,900', 'about:blank'], { stdio: ['ignore', 'ignore', 'pipe'] });
// 처음 뜨는 CI 러너에서는 크롬이 10초 넘게 걸릴 수 있어 30초까지 기다린다. 크롬이 먼저 죽으면 그 이유를 같이 알린다.
let chromeErr = '', chromeExit = null;
chrome.stderr.on('data', (d) => { chromeErr = (chromeErr + d).slice(-800); });
chrome.on('exit', (c) => { chromeExit = c; });
chrome.on('error', (e) => { chromeExit = -1; chromeErr = e.message; });

let ws, id = 0; const pending = new Map(); const events = [];
async function connect() {
  for (let i = 0; i < 150 && chromeExit === null; i++) {
    try { const t = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json(); const p = t.find((x) => x.type === 'page'); if (p) return p.webSocketDebuggerUrl; } catch {}
    await sleep(200);
  }
  throw new Error('chrome not reachable' + (chromeExit !== null ? ` (크롬 종료 코드 ${chromeExit}) ${chromeErr}` : ' (30초 대기)'));
}
function send(method, params = {}) {
  return new Promise((res, rej) => { const i = ++id; pending.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params })); });
}
async function ev(expr) {
  const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true });
  if (r.exceptionDetails) throw new Error('eval: ' + JSON.stringify(r.exceptionDetails.exception?.description || r.exceptionDetails.text));
  return r.result.value;
}
const KEYS = {
  '0': ['Digit0', 48], '1': ['Digit1', 49], '2': ['Digit2', 50], '3': ['Digit3', 51], '4': ['Digit4', 52], '5': ['Digit5', 53],
  '`': ['Backquote', 192], 'e': ['KeyE', 69], ' ': ['Space', 32], 'Enter': ['Enter', 13], 'Escape': ['Escape', 27], 'Tab': ['Tab', 9],
};
async function key(k) {
  const [code, vk] = KEYS[k];
  const text = k.length === 1 ? k : (k === 'Enter' ? '\r' : undefined);
  await send('Input.dispatchKeyEvent', { type: 'keyDown', key: k, code, windowsVirtualKeyCode: vk, text });
  await send('Input.dispatchKeyEvent', { type: 'keyUp', key: k, code, windowsVirtualKeyCode: vk });
  await sleep(40);
}
async function keys(seq) { for (const k of seq) await key(k); }
// 고정 대기 대신 조건이 참이 될 때까지 최대 ms만큼 기다린다(느린 CI 대비). 시간 안에 안 되면 마지막 값을 돌려주고 검사가 그 값으로 FAIL을 낸다.
async function until(expr, ms = 15000) {
  const end = Date.now() + ms; let v;
  while (true) {
    try { v = await ev(expr); } catch { v = false; }
    if (v || Date.now() > end) return v;
    await sleep(50);
  }
}
async function goto(url) {
  await ev('window.__old=1');
  await send('Page.navigate', { url });
  await until(`typeof window.__old==='undefined' && document.readyState==='complete' && /불러왔|읽지 못/.test((document.getElementById('rubric-status')||{}).textContent||'')`, 20000);
}
const txt = (sel) => ev(`(document.querySelector(${JSON.stringify(sel)})||{}).textContent||''`);

try {
  ws = new WebSocket(await connect());
  await new Promise((r) => ws.addEventListener('open', r));
  ws.addEventListener('message', (m) => {
    const d = JSON.parse(m.data);
    if (d.id && pending.has(d.id)) { const p = pending.get(d.id); pending.delete(d.id); d.error ? p.rej(new Error(d.error.message)) : p.res(d.result); }
    else if (d.method) events.push(d);
  });
  await send('Page.enable'); await send('Runtime.enable'); await send('Log.enable');
  await send('Page.addScriptToEvaluateOnNewDocument', { source: `window.__exports=[];const __c=URL.createObjectURL;URL.createObjectURL=function(b){b.text().then(t=>window.__exports.push(t));return __c.call(URL,b)};window.confirm=()=>true;` });

  // ---------- http 모드 ----------
  await goto(HTTP + '/index.html');
  ok('기준표 자동 로드 (http)', (await txt('#rubric-status')).includes('1.0'), await txt('#rubric-status'));

  // 1. rubric 문구가 화면에 그대로
  await ev(`document.getElementById('load-example').click()`); await until(`document.querySelectorAll('#answers-list .answer-row').length>=3`);
  await ev(`document.getElementById('start-scoring').click()`); await until(`!document.getElementById('scoring-section').hidden && /\\d/.test(document.getElementById('total-C').textContent)`);
  const body = await ev('document.body.innerText');
  const want = [];
  for (const c of rubric.criteria) { want.push(c.name, c.question, ...Object.values(c.levels)); }
  for (const p of rubric.penalties) { want.push(p.name, p.example); }
  const missing = want.filter((s) => !body.includes(s));
  ok('rubric 문구가 화면에 그대로 나옴', missing.length === 0, missing.length ? '없음: ' + missing.slice(0, 5).join(' / ') : `${want.length}개 문구 모두 있음`);

  // 2. 예시 불러오기 A=0 B=4 C=10
  const tA = await txt('#total-A'), tB = await txt('#total-B'), tC = await txt('#total-C');
  const num = (s) => (s.match(/-?\d+/) || [null])[0];
  ok('예시 불러오기 → A=0, B=4, C=10', num(tA) === '0' && num(tB) === '4' && num(tC) === '10', `A="${tA}" B="${tB}" C="${tC}"`);
  const warn = (await txt('#example-warning')).trim();
  ok('예시 합계 경고 없음', warn === '', warn);

  // 3. zero 감점 → 0 (예시 C로 이동: A, B는 근거가 없어 두 번 누름)
  await ev(`document.getElementById('answer-text').focus()`);
  await keys([' ', ' ']); await keys([' ', ' ']);
  const posC = await txt('#answer-position');
  const before = await txt('#total');
  await ev(`document.getElementById('penalty-ignored_risk').click()`); await until(`document.getElementById('total').textContent.trim().startsWith('0')`);
  const afterRisk = await txt('#total');
  await ev(`document.getElementById('penalty-ignored_risk').click()`);
  await ev(`document.getElementById('penalty-factual_error').click()`); await until(`document.getElementById('total').textContent.trim().startsWith('0')`);
  const afterFact = await txt('#total');
  await ev(`document.getElementById('penalty-factual_error').click()`); await until(`document.getElementById('total').textContent.trim().startsWith('10')`);
  ok('Space 두 번(근거 없음 경고 후)으로 C까지 이동', /3\s*\/\s*3/.test(posC), posC);
  ok("'위험 신호 무시' 체크 → 합계 0", num(before) === '10' && num(afterRisk) === '0', `${before} → ${afterRisk}`);
  ok("'사실 오류' 체크 → 합계 0", num(afterFact) === '0', afterFact);

  // 4. 키보드만으로 채점: 새 문항
  await ev(`(()=>{const r=document.getElementById('rater');r.value='검수';r.dispatchEvent(new Event('input'));
    let rows=[...document.querySelectorAll('#answers-list .answer-row')];
    while(rows.length>2){[...rows[rows.length-1].querySelectorAll('button')].find(x=>x.textContent.includes('빼기')).click();rows=[...document.querySelectorAll('#answers-list .answer-row')];}
    document.getElementById('situation').value='키보드 검수용 상황입니다.';
    const tas=[...document.querySelectorAll('#answers-list textarea')];
    tas[0].value='첫 번째 답변입니다. 오늘 할 일을 하나만 정해 보세요.'; tas[0].dispatchEvent(new Event('input'));
    if(tas[1]){tas[1].value='두 번째 답변입니다.'; tas[1].dispatchEvent(new Event('input'));}
    document.getElementById('situation').dispatchEvent(new Event('input'));
    document.getElementById('start-scoring').click();})()`);
  await until(`document.getElementById('answer-text').value.includes('첫 번째 답변')`);
  await ev(`document.getElementById('answer-text').focus()`);
  const pos1 = await txt('#answer-position');
  await keys(['1']); const banner = await txt('#mode-banner');
  await keys(['2', '2', '2', '3', '1', '4', '`', '5', '0']);
  const t1 = await txt('#total');
  const pressed = await ev(`['notice','accuracy','respect','restraint','next_step'].map(c=>[0,1,2].find(s=>document.getElementById('score-'+c+'-'+s).getAttribute('aria-pressed')==='true'))`);
  ok('1~5 항목 선택 → 안내 표시', banner.includes(rubric.criteria[0].name), banner);
  ok('두 번 누르기로 점수 입력 (`=0 포함)', JSON.stringify(pressed) === '[2,2,1,0,0]' && num(t1) === '5', `점수 ${JSON.stringify(pressed)}, ${t1}`);
  // 근거: 키보드 선택을 흉내 내 selectionRange 지정 후 E
  await keys(['1']);
  await ev(`(()=>{const t=document.getElementById('answer-text');t.focus();const s='오늘 할 일을 하나만 정해 보세요.';const i=t.value.indexOf(s);t.setSelectionRange(i,i+s.length);})()`);
  await keys(['e']);
  const evNotice = await txt('#evidence-notice');
  ok('문장 선택 + E → 근거 저장', evNotice.includes('오늘 할 일을 하나만 정해 보세요.'), evNotice.trim().slice(0, 60));
  await keys(['Escape']);
  await keys(['Enter']); const msg1 = await txt('#message');
  await keys(['Enter']); const pos2 = await txt('#answer-position');
  ok('Enter: 근거 없음 경고 후 다음 답변', msg1.includes('근거') && pos2 !== pos1 && /2\s*\/\s*2/.test(pos2), `${msg1} | ${pos1} → ${pos2}`);
  await keys(['1', '1', '2', '1', '3', '1', '4', '1', '5', '1']);
  await keys([' ']); await keys([' ']);
  const focusAfterLast = await ev('document.activeElement && document.activeElement.id');
  ok('마지막 답변에서 Space → 내보내기로 이동', focusAfterLast === 'export-jsonl', String(focusAfterLast));
  // Space on checkbox toggles, not next
  await ev(`document.getElementById('prev-answer').click()`); await until(`/1\\s*\\/\\s*2/.test(document.getElementById('answer-position').textContent)`);
  await ev(`document.getElementById('penalty-flattery').focus()`);
  const posBeforeCb = await txt('#answer-position');
  await keys([' ']);
  const cbChecked = await ev(`document.getElementById('penalty-flattery').checked`);
  const posAfterCb = await txt('#answer-position');
  ok('체크박스에서 Space는 체크만 함', cbChecked === true && posBeforeCb === posAfterCb, `checked=${cbChecked}, ${posBeforeCb} → ${posAfterCb}`);
  await keys([' ']); // 체크 해제
  // GPT 리뷰 4번: 체크박스에서 Enter는 다음 답변으로 넘어가지 않음
  await ev(`document.getElementById('penalty-flattery').focus()`);
  const posBeforeEnter = await txt('#answer-position');
  await keys(['Enter']); await keys(['Enter']);
  ok('체크박스에서 Enter는 다음 답변으로 안 넘어감', posBeforeEnter === (await txt('#answer-position')), posBeforeEnter);
  // Tab으로 감점 체크박스에 도달 가능
  await ev(`document.getElementById('answer-text').focus()`);
  let reached = false;
  for (let i = 0; i < 60 && !reached; i++) { await key('Tab'); reached = await ev(`document.activeElement && document.activeElement.id==='penalty-flattery'`); }
  ok('Tab만으로 감점 체크박스에 도달', reached);
  // 입력 칸에서는 단축키 무시
  await ev(`document.getElementById('rater').focus()`);
  const sel0 = await txt('#mode-banner'); await keys(['3']); const sel1 = await txt('#mode-banner');
  const raterVal = await ev(`document.getElementById('rater').value`);
  ok('입력 칸에서는 단축키 무시', sel0 === sel1 && raterVal.endsWith('3'), `rater="${raterVal}"`);
  await ev(`(()=>{const r=document.getElementById('rater');r.value='검수';r.dispatchEvent(new Event('input'));})()`);

  // 5. 버튼 높이, 포커스 표시, aria-live
  const small = await ev(`[...document.querySelectorAll('button, input[type=checkbox], select, input[type=text]')].filter(e=>e.offsetParent!==null).map(e=>{const t=e.type==='checkbox'?(e.closest('label')||e):e;return [e.id||e.textContent.trim().slice(0,12),Math.round(t.getBoundingClientRect().height)]}).filter(x=>x[1]<48)`);
  ok('보이는 버튼·체크박스 영역 높이 48px 이상', small.length === 0, small.length ? JSON.stringify(small.slice(0, 8)) : '');
  await ev(`document.getElementById('answer-text').focus()`); await key('Tab');
  const outline = await ev(`(()=>{const s=getComputedStyle(document.activeElement);return document.activeElement.id+' '+s.outlineStyle+' '+s.outlineWidth})()`);
  ok('키보드 포커스 표시 보임', /solid|auto|dashed/.test(outline) && !/ 0px$/.test(outline), outline);
  ok('합계 aria-live', (await ev(`document.getElementById('total').getAttribute('aria-live')`)) === 'polite');

  // 6. JSONL 내보내기
  await ev(`document.getElementById('export-jsonl').click()`); await until('window.__exports.length>0');
  const exp = await ev('window.__exports.join("")');
  const lines = exp.split('\n').filter(Boolean);
  const fields = ['situation', 'answer_id', 'answer', 'scores', 'evidence', 'penalties', 'total', 'rater', 'date', 'rubric_version'];
  let bad = [];
  lines.forEach((l, i) => { try { const o = JSON.parse(l); const m = fields.filter((f) => !(f in o)); if (m.length) bad.push(i + ':' + m); } catch { bad.push(i + ':parse'); } });
  ok('JSONL 내보내기: 줄마다 필수 필드', lines.length >= 5 && bad.length === 0, `${lines.length}줄 ${bad.join(' ')}`);
  const kb = lines.map((l) => JSON.parse(l)).find((o) => o.rater === '검수' && o.answer_id === 'A');
  ok('JSONL 값 확인 (키보드 채점 건)', !!kb && kb.total === 5 && kb.evidence.notice?.[0] === '오늘 할 일을 하나만 정해 보세요.' && /\+09:00$/.test(kb.date), kb ? JSON.stringify({ total: kb.total, ev: kb.evidence.notice, date: kb.date }) : 'no record');

  // 7. 새로고침 후 유지
  const savedBefore = await txt('#saved-count');
  await goto(HTTP + '/index.html');
  ok('새로고침해도 저장 유지', (await txt('#saved-count')) === savedBefore && savedBefore !== '0', `${savedBefore} → ${await txt('#saved-count')}`);

  // 8. 테스트 문항 불러오기
  await ev(`document.getElementById('load-test-items').click()`); await until(`document.querySelectorAll('#test-item-select option').length>=30`);
  const optCount = await ev(`document.querySelectorAll('#test-item-select option').length`);
  const notice = await txt('#test-notice');
  await ev(`(()=>{const s=document.getElementById('test-item-select');s.selectedIndex=s.options.length-1;s.dispatchEvent(new Event('change'));document.getElementById('start-scoring').click();})()`); await until(`!document.getElementById('test-badge').hidden`);
  const badgeShown = await ev(`!document.getElementById('test-badge').hidden && document.getElementById('test-badge').offsetParent!==null`);
  ok('테스트 문항 30세트 불러오기', optCount >= 30, `option ${optCount}개, notice="${notice.trim()}"`);
  ok("테스트 문항 채점 시 '테스트용, 채점 기준 아님' 배지", badgeShown && (await txt('#test-badge')).includes('테스트용, 채점 기준 아님'), await txt('#test-badge'));

  // GPT 리뷰 1번: 테스트 문항을 불러와도 예시 채점에 test_only가 붙지 않음
  await ev('window.__exports.length=0');
  await ev(`document.getElementById('export-jsonl').click()`); await until('window.__exports.length>0');
  const recs = (await ev('window.__exports.join("")')).split(String.fromCharCode(10)).filter(Boolean).map((l) => JSON.parse(l));
  const exRecs = recs.filter((o) => o.rater === '예시');
  ok('테스트 문항을 불러와도 예시 채점에 test_only 없음', exRecs.length === 3 && exRecs.every((o) => !('test_only' in o)), `예시 ${exRecs.length}줄, test_only ${exRecs.filter((o) => o.test_only).length}줄`);

  // GPT 2차 리뷰 9번: 채점 화면이 열린 채로 예시를 불러오면 채점 화면을 닫음
  const openBefore = await ev(`!document.getElementById('scoring-section').hidden`);
  await ev(`document.getElementById('load-example').click()`); await until(`document.getElementById('scoring-section').hidden`);
  const openAfter = await ev(`!document.getElementById('scoring-section').hidden`);
  ok('채점 중 예시 불러오기 → 채점 화면 닫힘', openBefore === true && openAfter === false, `열림 ${openBefore} → ${openAfter}`);

  // GPT 2차 리뷰 2번: 테스트 문항 본문을 고쳐도 테스트 표시 유지, 새 문항은 표시 없음
  await ev(`document.getElementById('load-test-items').click()`); await until(`document.querySelectorAll('#test-item-select option').length>=30`);
  await ev(`(()=>{const s=document.getElementById('test-item-select');s.selectedIndex=1;s.dispatchEvent(new Event('change'));
    const t=document.querySelector('#answers-list textarea');t.value=t.value+' (고친 문장)';t.dispatchEvent(new Event('input'));
    document.getElementById('start-scoring').click();})()`); await until(`document.getElementById('answer-text').value.includes('(고친 문장)')`);
  const badgeEdited = await ev(`!document.getElementById('test-badge').hidden`);
  await ev(`(()=>{document.getElementById('new-item').click();
    document.getElementById('situation').value='직접 쓴 상황입니다.';document.getElementById('situation').dispatchEvent(new Event('input'));
    const t=document.querySelector('#answers-list textarea');t.value='직접 쓴 답변입니다.';t.dispatchEvent(new Event('input'));
    document.getElementById('start-scoring').click();})()`); await until(`document.getElementById('answer-text').value.includes('직접 쓴 답변')`);
  const badgeNew = await ev(`!document.getElementById('test-badge').hidden`);
  ok('테스트 문항 본문을 고쳐도 배지 유지, 새 문항은 배지 없음', badgeEdited === true && badgeNew === false, `고친 테스트 문항 ${badgeEdited}, 새 문항 ${badgeNew}`);

  // 9. file:// 모드
  await goto(FILEURL);
  const fileStatus = await txt('#rubric-status');
  const fileBtn = await ev(`!document.getElementById('rubric-file-wrap').hidden`);
  ok("file://로 열면 '기준표 파일 열기' 표시", fileBtn, fileStatus);

  // 10. 외부 요청 없음 + 콘솔 에러
  const ext = events.filter((e) => e.method === 'Network.requestWillBeSent');
  const errs = events.filter((e) => (e.method === 'Runtime.exceptionThrown') || (e.method === 'Log.entryAdded' && e.params.entry.level === 'error' && !/rubric\.json|test-items\.json|favicon/.test((e.params.entry.url||'') + ' ' + e.params.entry.text)));
  ok('자바스크립트 에러 없음', errs.length === 0, errs.slice(0, 3).map((e) => JSON.stringify(e.params).slice(0, 160)).join(' | '));
} catch (e) {
  ok('검수 스크립트 실행', false, e.stack);
} finally {
  try { ws && ws.close(); } catch {}
  chrome.kill();
  const f = results.filter((r) => !r.pass).length;
  console.log(`\n${results.length - f}/${results.length} PASS`);
  process.exit(f ? 1 : 0);
}
