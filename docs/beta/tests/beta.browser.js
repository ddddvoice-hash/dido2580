// 베타 채점 페이지 브라우저 검사 (R20 반영: 위기 문항 접기, 평가자 분리, 저장 결과, 근거 인용, 초안, 키보드).
// 실행: python docs/beta/build.py 로 index.html을 만든 뒤
//   NODE_PATH=<playwright가 있는 node_modules> CHROMIUM="C:/Program Files/Google/Chrome/Application/chrome.exe" node docs/beta/tests/beta.browser.js
// 서버 없이 file:// 로 열어요. 서버 저장은 가짜 window.claude(db·user)로 흉내 내요.
'use strict';
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');
const W = require('../../../apps/warmth-scorer/app.js');
const rubric = require('../../../apps/warmth-scorer/rubric.json');
const pack = JSON.parse(fs.readFileSync(path.join(__dirname, '../../../docs/eval/packs/calibration-v0.json'), 'utf8'));
const calib = fs.readFileSync(path.join(__dirname, '../../../docs/eval/calibration.md'), 'utf8').replace(/\r\n/g, '\n');
const URL_ = 'file:///' + path.join(__dirname, '../index.html').replace(/\\/g, '/');
const section = calib.slice(calib.indexOf('## 위기 문항을 채점할 때'));
const QUOTE = section.split('\n').find((l) => /^\s*> "/.test(l)).replace(/^\s*> "/, '').replace(/"\s*$/, '');
const sItem = pack.items.find((i) => i.sensitive);
const nItem = pack.items[0];
const crit = rubric.criteria.map((c) => c.id);

// 모든 페이지에 깔아요: 클립보드 기록, 가상 서버(sessionStorage __fake=1일 때만)
const INIT = `
  window.__clip = [];
  try { Object.defineProperty(navigator, 'clipboard', { value: { writeText: (t) => { window.__clip.push(t); return Promise.resolve(); } }, configurable: true }); } catch (e) {}
  window.__writes = []; window.__fail = false;
  if (sessionStorage.getItem('__fake') === '1') {
    window.claude = { use: (n) => Promise.resolve(n === 'user' ? { id: () => Promise.resolve('u1') } : n === 'db' ? {
      collection: () => ({ get: () => Promise.resolve({ docs: [] }) }),
      doc: (p) => ({ set: (b) => window.__fail ? Promise.reject({ code: 'unavailable' }) : (window.__writes.push([p, JSON.parse(JSON.stringify(b))]), Promise.resolve()) })
    } : null) };
  }
  if (sessionStorage.getItem('__nolocal') === '1') { Storage.prototype.setItem = function () { throw new Error('quota'); }; }
`;

(async () => {
  const results = [];
  const ok = (name, cond, d = '') => { results.push(!!cond); console.log(`${cond ? 'PASS' : 'FAIL'} ${name}${d ? ' — ' + d : ''}`); };
  const browser = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
  const errors = [];
  async function fresh(opts = {}) {
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    await ctx.addInitScript(INIT);
    const page = await ctx.newPage();
    page.on('pageerror', (e) => errors.push(e.message));
    if (opts.fake) { await page.goto(URL_); await page.evaluate(() => sessionStorage.setItem('__fake', '1')); }
    await page.goto(URL_);
    return { ctx, page };
  }
  const bodyText = (page) => page.evaluate(() => document.body.innerText);
  const leaks = async (page) => { const t = await bodyText(page); return [sItem.situation, ...sItem.answers.map((a) => a.text)].filter((x) => t.includes(x.slice(0, 15))); };
  async function begin(page, code) { await page.fill('#rater', code); await page.click('#start'); }
  async function openItem(page, id) { await page.click(`#list .item-btn:has-text("${id}")`); }
  async function rate(page, it, i, opt = {}) {
    const k = `${it.id}-${String.fromCharCode(65 + i)}`;
    for (const c of crit) {
      await page.check(`#${k}-${c}-${opt.score ?? 2}`);
      await page.fill(`#${k}-${c}-q`, opt.quote ?? it.answers[i].text.slice(2, 10));
    }
    await page.click(`#${k}-save`);
  }
  const lastClip = (page) => page.evaluate(() => window.__clip[window.__clip.length - 1] || '');
  async function tabTo(page, id, max = 500) {
    for (let n = 0; n < max; n++) {
      if ((await page.evaluate(() => document.activeElement && document.activeElement.id)) === id) return n;
      await page.keyboard.press('Tab');
    }
    throw new Error('Tab으로 못 찾음: ' + id);
  }

  // ===== R20-2 접힘 · 다시 접기 · 닫기 · 건너뛰기 · 마치기 =====
  {
    const { ctx, page } = await fresh();
    await begin(page, 'R-A');
    await openItem(page, sItem.id);
    ok('위기 문항: 처음에는 접혀 있고 본문이 화면 글에 없음', (await page.isVisible('#gate-read')) && (await leaks(page)).length === 0);
    ok('안내 문구가 calibration.md 인용문과 같음(읽기·건너뛰기·오늘은 마치기 포함)', (await page.textContent('#gate-quote')).trim() === QUOTE);
    ok('안내 영역에 읽기·건너뛰기·오늘은 마치기 버튼', (await page.textContent('#gate-read')).trim() === '읽기' && (await page.textContent('#gate-skip')).trim() === '건너뛰기' && (await page.textContent('#gate-stop')).trim() === '오늘은 마치기');
    await page.click('#gate-read');
    ok('읽기: 본문이 열리고 포커스가 새 본문 제목으로 감', (await page.isVisible('.situation')) && (await page.evaluate(() => document.activeElement.id)) === 'item-title');
    ok('읽는 도중에도 닫기·건너뛰기·오늘은 마치기가 있음', (await page.isVisible('#item-close')) && (await page.isVisible('#item-skip')) && (await page.isVisible('#item-stop')));
    await page.click('#item-close');
    ok('닫기: 다시 접힘(본문 없음)', (await page.isVisible('#gate-read')) && (await leaks(page)).length === 0);
    await page.click('#gate-read');
    await openItem(page, nItem.id);
    await openItem(page, sItem.id);
    ok('읽은 뒤 다른 문항에 갔다 오면 다시 접힘 (R20-2 재현)', (await page.isVisible('#gate-read')) && (await leaks(page)).length === 0);
    await page.click('#gate-read');
    await page.click('#nav-prev'); await page.click('#nav-next');
    ok('이전·다음으로 오가도 다시 접힘', (await page.isVisible('#gate-read')) && (await leaks(page)).length === 0);
    // 읽고 점수를 준 뒤: 건너뛰기는 막고 오늘은 마치기는 됨, 중단 기록
    await page.click('#gate-read');
    await rate(page, sItem, 0);
    ok('위기 문항도 점수를 줄 수 있음', /채점함 · 합계 10점|합계 10점/.test(await page.textContent('#out')) || (await page.textContent('#progress-chip')).startsWith('1 /'));
    await page.click('#item-skip');
    ok('이미 채점했으면 건너뛰기는 막고 안내(채점기 A10과 같음)', (await page.textContent('#live')).includes('건너뛸 수 없어요'));
    await page.click('#item-stop');
    ok('오늘은 마치기: 마치며 칸으로 이동하고 본문은 접힘', (await page.evaluate(() => document.activeElement.id)) === 'fb-time' && (await leaks(page)).length === 0);
    await page.reload();
    ok('새로고침해도 위기 문항은 접힌 채 시작', (await leaks(page)).length === 0);
    await ctx.close();
  }

  // ===== R20-1 건너뛴 위기 문항: 미리보기·복사에 본문 없음, JSONL은 채점기 검사 통과 =====
  {
    const { ctx, page } = await fresh();
    await begin(page, 'R-S');
    await rate(page, nItem, 0);
    await openItem(page, sItem.id);
    await page.click('#gate-skip');
    const out = await page.textContent('#out');
    const pieces = [sItem.situation, ...sItem.answers.map((a) => a.text)].map((x) => x.slice(0, 15));
    ok('건너뛴 뒤 JSONL 미리보기에 위기 문항 본문이 없음 (R20-1 재현)', !pieces.some((x) => out.includes(x)) && out.includes(`${sItem.id}-A · 위기 문항 · 건너뜀(평가하지 않음)`), out.slice(0, 120));
    ok('건너뛴 뒤 화면 전체 글에도 본문이 없음', (await leaks(page)).length === 0);
    await page.click('#copy');
    const clip = await lastClip(page);
    const parsed = W.parseJsonl(clip, rubric);
    ok('복사한 JSONL이 채점기 parseJsonl·validateRecord를 모두 통과', parsed.bad.length === 0 && parsed.records.length === 2 && parsed.records.every((r) => W.validateRecord(rubric, r) === null), JSON.stringify(parsed.problems));
    const sk = parsed.records.find((r) => r.skipped);
    ok('건너뜀 줄: skipped·점수 null·합계 null·본문 없음·문항/답변 번호 있음', sk && sk.total === null && crit.every((c) => sk.scores[c] === null) && sk.item_id === sItem.id && sk.answer_id === 'A' && !pieces.some((x) => clip.includes(x)));
    ok('일반 줄은 본문·근거 포함, skipped 없음', parsed.records.filter((r) => !r.skipped).every((r) => r.answer === nItem.answers[0].text && r.rubric_version === rubric.version && !('skipped' in r)));
    const agree = W.computeAgreement(rubric, parsed.records);
    ok('채점기 일치도 계산이 건너뜀을 0점으로 세지 않음', agree.criteria.every((c) => c.ratings === 0));
    // 다시 읽고 점수를 주면 건너뜀이 풀림
    await openItem(page, sItem.id); await page.click('#gate-read'); await rate(page, sItem, 0);
    await page.click('#copy');
    const again = W.parseJsonl(await lastClip(page), rubric).records.filter((r) => r.item_id === sItem.id);
    ok('건너뛴 뒤 읽고 채점하면 그 답변은 점수 기록으로 바뀜', again.length === 1 && !again[0].skipped && again[0].total === 10);
    await ctx.close();
  }

  // ===== R20-3 평가자별 저장 분리 =====
  {
    const { ctx, page } = await fresh();
    await begin(page, 'R-A');
    await rate(page, nItem, 0);
    ok('R-A가 채점하면 저장됨', (await page.textContent('#progress-chip')).startsWith('1 /'));
    ok('시작 뒤 코드 칸은 잠기고 평가자 바꾸기가 보임', (await page.isDisabled('#rater')) && (await page.isVisible('#switch')));
    await page.click('#switch');
    ok('평가자 바꾸기: 이전 평가자 기록이 화면에서 사라짐', !(await page.isVisible('#work')) && (await page.textContent('#out')) === '' && (await page.inputValue('#rater')) === '');
    await begin(page, 'R-B');
    ok('R-B로 시작하면 R-A의 점수·근거가 보이지 않음 (R20-3 재현)', (await page.textContent('#progress-chip')).startsWith('0 /') && (await page.textContent('#out')).includes('아직 저장한 채점이 없어요') && !(await page.textContent('#out')).includes('R-A'));
    await page.fill(`#${nItem.id}-A-${crit[0]}-q`, '');
    ok('R-B 화면의 답변 A는 아직 안 함, 점수 선택 없음', (await page.textContent('#item')).includes('아직 안 함') && (await page.$$eval(`#${nItem.id}-A-${crit[0]}-0, #${nItem.id}-A-${crit[0]}-1, #${nItem.id}-A-${crit[0]}-2`, (r) => r.filter((x) => x.checked).length)) === 0);
    await rate(page, nItem, 0, { score: 1 });
    await page.click('#copy');
    const rb = W.parseJsonl(await lastClip(page), rubric).records;
    ok('R-B 기록의 평가자는 R-B뿐', rb.length === 1 && rb[0].rater === 'R-B' && rb[0].total === 5);
    await page.click('#switch'); await begin(page, 'r-a');
    ok('다시 R-A(소문자 입력도 대문자로)를 넣으면 R-A의 기록이 열림', (await page.textContent('#progress-chip')).startsWith('1 /'));
    await page.click('#switch'); await page.fill('#rater', 'bad code!'); await page.click('#start');
    ok('코드에 허용하지 않는 글자가 있으면 시작하지 않고 안내', (await page.isHidden('#work')) && (await page.textContent('#rater-hint')).includes('영문·숫자·한글'));
    await ctx.close();
  }

  // ===== R20-4 저장 결과와 안내 =====
  {
    const { ctx, page } = await fresh({ fake: true });
    await page.waitForFunction(() => /운영자에게 바로 전달/.test(document.getElementById('store-chip').textContent));
    await begin(page, 'R-N');
    await page.evaluate(() => { window.__fail = true; });
    await rate(page, nItem, 0);
    await page.waitForFunction(() => /아직 전달되지 않았어요/.test(document.querySelector('#item .answer .say').textContent));
    const chip = await page.textContent('#store-chip');
    ok('서버 쓰기가 실패하면 칩이 "바로 전달"로 남지 않고 전달 못 한 기록 수를 보여 줌 (R20-4① 재현)', chip.includes('전달 못 한 기록') && !chip.includes('바로 전달돼요'), chip);
    ok('저장 문구: 이 브라우저엔 저장, 운영자엔 아직 전달 안 됨', (await page.textContent('#item .answer .say')).includes('이 브라우저에 저장했어요'));
    ok('다시 보내기 버튼이 보임', await page.isVisible('#resend'));
    await page.evaluate(() => { window.__fail = false; });
    await page.click('#resend');
    await page.waitForFunction(() => /운영자에게 바로 전달/.test(document.getElementById('store-chip').textContent));
    const w = await page.evaluate(() => window.__writes.map((x) => x[0]));
    ok('다시 보내면 밀린 채점이 서버에 올라가고 칩이 정상으로 돌아옴', w.includes('beta/u1/ratings/R-N__c01-A') && !(await page.isVisible('#resend')), w.join(','));
    ok('서버 문서에 평가자 코드·기준표 버전이 들어 있음', await page.evaluate(() => { const d = window.__writes.find((x) => x[0].includes('ratings/R-N__c01-A')); return d && d[1].rater === 'R-N' && d[1].rubric_version === '1.0'; }));
    await ctx.close();
  }
  {
    // 로컬 저장 실패 + 서버 없음: 성공이라고 말하면 안 됨
    const { ctx, page } = await fresh();
    await page.evaluate(() => sessionStorage.setItem('__nolocal', '1')); await page.reload();
    await begin(page, 'R-L');
    await rate(page, nItem, 0);
    await page.waitForFunction(() => document.querySelector('#item .answer .say').textContent.length > 0);
    const m = await page.textContent('#item .answer .say');
    ok('로컬 저장 실패+서버 없음이면 "저장하지 못했어요"와 내보내기 안내 (R20-4② 재현)', m.includes('저장하지 못했어요') && m.includes('운영자에게 보낼 것') && !m.includes('이 브라우저에 저장했어요'), m);
    ok('칩에도 이 브라우저에 저장 못 함이 표시됨', (await page.textContent('#store-chip')).includes('저장하지 못했어요'));
    await page.click('#copy');
    ok('그래도 메모리의 기록은 복사됨', W.parseJsonl(await lastClip(page), rubric).records.length === 1);
    await ctx.close();
  }
  {
    // 서버 연결이 나중에 되면 로컬에만 있던 채점도 올라감
    const { ctx, page } = await fresh();
    await begin(page, 'R-U');
    await rate(page, nItem, 0);
    await page.evaluate(() => sessionStorage.setItem('__fake', '1')); await page.reload();
    await page.waitForFunction(() => window.__writes.length > 0, null, { timeout: 5000 });
    const w = await page.evaluate(() => window.__writes.map((x) => x[0]));
    ok('로컬에 있던 채점이 서버 연결 성공 뒤 업로드됨 (R20-4③ 재현)', w.includes('beta/u1/ratings/R-U__c01-A'), w.join(','));
    await ctx.close();
  }

  // ===== R20-5 키보드만으로 끝까지 + R20-10 =====
  {
    const { ctx, page } = await fresh();
    await page.keyboard.press('Tab');
    await tabTo(page, 'rater');
    await page.keyboard.type('r-key');
    await page.keyboard.press('Enter');
    ok('키보드: 코드 입력 후 Enter로 시작하고 포커스가 본문 제목으로 감', (await page.evaluate(() => document.activeElement.id)) === 'item-title');
    for (let i = 0; i < nItem.answers.length; i++) {
      const k = `${nItem.id}-${String.fromCharCode(65 + i)}`;
      for (const c of crit) {
        await tabTo(page, `${k}-${c}-0`);
        await page.keyboard.press(String(i % 3));
        await tabTo(page, `${k}-${c}-q`);
        await page.keyboard.type(nItem.answers[i].text.slice(2, 9));
      }
      await tabTo(page, `${k}-save`);
      await page.keyboard.press('Enter');
      await page.waitForFunction((kk) => /저장했어요/.test(document.getElementById(kk + '-save').parentElement.textContent), k);
    }
    ok('키보드: 답변 3개를 점수·근거·저장까지 마침', (await page.textContent('#progress-chip')).startsWith('3 /'));
    // 위기 문항까지 Tab+Enter로 이동
    for (let n = 1; n < pack.items.findIndex((x) => x.sensitive); n++) { await tabTo(page, 'nav-next'); await page.keyboard.press('Enter'); }
    await tabTo(page, 'nav-next'); await page.keyboard.press('Enter');
    ok('키보드: 위기 문항에서 접힌 채 읽기·건너뛰기·오늘은 마치기로 Tab 이동', (await page.isVisible('#gate-read')) && (await tabTo(page, 'gate-skip')) >= 0 && (await tabTo(page, 'gate-stop')) >= 0);
    await tabTo(page, 'gate-skip'); await page.keyboard.press('Enter');
    ok('키보드: 건너뛰기로 다음 문항에 감', (await page.textContent('#item')).includes('c08') && (await leaks(page)).length === 0);
    while (!(await page.textContent('#item')).includes('c10')) { await tabTo(page, 'nav-next'); await page.keyboard.press('Enter'); }
    await tabTo(page, 'nav-next'); await page.keyboard.press('Enter');
    ok('키보드: 마치며로 이동하면 포커스가 걸린 시간 칸에 감', (await page.evaluate(() => document.activeElement.id)) === 'fb-time');
    await page.keyboard.type('1시간');
    await tabTo(page, 'fb-save'); await page.keyboard.press('Enter');
    await tabTo(page, 'copy'); await page.keyboard.press('Enter');
    const recs = W.parseJsonl(await lastClip(page), rubric);
    ok('키보드: 복사한 JSONL이 4줄(채점 3 + 건너뜀 1)이고 모두 채점기 검사 통과', recs.bad.length === 0 && recs.records.length === 4 && recs.records.filter((r) => r.skipped).length === 1 && recs.records.every((r) => W.validateRecord(rubric, r) === null), JSON.stringify(recs.problems));
    await tabTo(page, 'copy-fb'); await page.keyboard.press('Enter');
    const fb = JSON.parse(await lastClip(page));
    ok('키보드: 의견 기록 복사에 걸린 시간·평가자 코드가 들어 있음', fb.overall.time === '1시간' && fb.rater === 'R-KEY' && fb.type === 'beta_feedback');
    ok('키보드: 점수 칸에 0/1/2 키가 먹음(0·1·2점이 각 답변에 반영)', recs.records.filter((r) => !r.skipped).map((r) => r.scores[crit[0]]).join(',') === '0,1,2');
    await ctx.close();
  }

  // ===== R20-7 근거 인용 =====
  {
    const { ctx, page } = await fresh();
    await begin(page, 'R-Q');
    const k = `${nItem.id}-A`;
    for (const c of crit) await page.check(`#${k}-${c}-2`);
    for (const c of crit) await page.fill(`#${k}-${c}-q`, 'x');
    await page.click(`#${k}-save`);
    ok('답변과 무관한 "x"로 채운 근거는 저장되지 않음 (R20-7 재현)', (await page.textContent('#item .answer .say')).includes('답변에 없는 구절') && (await page.textContent('#progress-chip')).startsWith('0 /'));
    const q = nItem.answers[0].text.slice(3, 11).trim();
    for (const c of crit) await page.fill(`#${k}-${c}-q`, q);
    await page.check(`#${k}-${crit[0]}-x`);
    await page.click(`#${k}-save`);
    ok('"인용할 구절이 없어요"를 체크하고 이유가 없으면 저장되지 않음', (await page.textContent('#item .answer .say')).includes('이유를 적어 주세요'));
    await page.fill(`#${k}-${crit[0]}-n`, '답변에 해당 표현이 없어요');
    await page.fill(`#${k}-${crit[1]}-n`, '덧붙이는 설명');
    await page.click(`#${k}-save`);
    await page.waitForFunction(() => document.querySelector('#item .answer .say').textContent.includes('저장'));
    await page.click('#copy');
    const r = W.parseJsonl(await lastClip(page), rubric).records[0];
    ok('인용 없음은 표시와 이유로 기록, 인용은 구절+설명으로 기록', r && r.evidence[crit[0]][0] === '(인용할 구절 없음)' && r.evidence[crit[0]][1].includes('해당 표현') && r.evidence[crit[1]][0] === q && r.evidence[crit[1]][1] === '설명: 덧붙이는 설명', JSON.stringify(r && r.evidence));
    await page.fill(`#${k}-${crit[2]}-q`, q.slice(0, 3) + '…' + q.slice(-3));
    await ctx.close();
  }

  // ===== R20-8 의견 · 메모 내보내기, R20-9 초안, R20-12 버전 =====
  {
    const { ctx, page } = await fresh();
    await begin(page, 'R-F');
    const k = `${nItem.id}-A`;
    await page.check(`#${k}-${crit[0]}-1`);
    await page.fill(`#${k}-${crit[0]}-q`, '써 두는 중');
    ok('입력하면 "수정 중 · 저장 안 됨"이 보임', (await page.textContent('#item')).includes('수정 중'));
    await openItem(page, pack.items[1].id); await openItem(page, nItem.id);
    ok('다른 문항에 갔다 와도 저장 전 입력이 남음 (R20-9 재현)', (await page.isChecked(`#${k}-${crit[0]}-1`)) && (await page.inputValue(`#${k}-${crit[0]}-q`)) === '써 두는 중');
    await page.evaluate(() => window.dispatchEvent(new Event('resize')));
    await page.fill(`#note-${nItem.id}`, '낱말 "충분히"가 헷갈려요');
    await page.click('#item div.answer button');
    await page.fill('#fb-words', '절제 기준'); await page.fill('#fb-time', '90분'); await page.click('#fb-save');
    await page.click('#copy-fb');
    const fb = JSON.parse(await lastClip(page));
    ok('의견 기록에 문항 메모·마친 뒤 의견·걸린 시간이 들어 감 (R20-8 재현)', fb.item_notes[nItem.id] === '낱말 "충분히"가 헷갈려요' && fb.overall.words === '절제 기준' && fb.overall.time === '90분');
    ok('의견 기록 미리보기가 화면에 보임', (await page.textContent('#fb-out')).includes('beta_feedback'));
    await page.click('#save-fb');
    ok('파일로 저장 버튼이 눌림(서버 없는 환경에서도)', (await page.textContent('#fb-out-say')).length > 0);
    // 기준표 버전이 다른 기록은 섞지 않고 자기 버전으로 내보냄
    await page.evaluate(() => {
      const key = 'kdd-warmth-beta-v2:r:R-F'; const s = JSON.parse(localStorage.getItem(key));
      s.ratings['c02-A'] = { item_id: 'c02', answer_id: 'A', scores: { notice: 1, accuracy: 1, respect: 1, restraint: 1, next_step: 1 }, evidence: { notice: ['a'] }, penalties: [], total: 5, rater: 'R-F', date: '2026-10-01T10:00:00+09:00', rubric_version: '0.9' };
      localStorage.setItem(key, JSON.stringify(s));
    });
    await page.reload();
    ok('다른 버전 기록은 완료 수에 섞이지 않음', (await page.textContent('#progress-chip')).startsWith('0 /'));
    await page.click('#copy');
    const recs = W.parseJsonl(await lastClip(page), rubric).records;
    ok('내보낼 때 기록은 저장 당시 기준표 버전(0.9)을 그대로 가짐 (R20-12 재현)', recs.length === 1 && recs[0].rubric_version === '0.9' && W.validateRecord(rubric, recs[0]) === null);
    await ctx.close();
  }

  // ===== R20-10 접근성, 화면 크기 =====
  {
    const { ctx, page } = await fresh();
    await begin(page, 'R-X');
    const k = `${nItem.id}-A`;
    const pen = rubric.penalties[0].id;
    const desc = await page.getAttribute(`#${k}-p-${pen}`, 'aria-describedby');
    ok('감점 신호가 aria-describedby로 설명 문장에 연결됨 (R20-10)', desc && (await page.textContent('#' + desc)).trim() === rubric.penalties[0].why.trim());
    const hs = await page.$$eval('.pen, .lv, .noq, .btn', (b) => b.filter((x) => x.offsetParent !== null).map((x) => x.getBoundingClientRect().height));
    ok('감점·점수·체크·버튼 클릭 영역이 모두 48px 이상', hs.every((h) => h >= 47.5), String(Math.min(...hs)));
    await page.keyboard.press('Tab');
    const outline = await page.evaluate(() => { const e = document.activeElement; return getComputedStyle(e).outlineStyle + ' ' + getComputedStyle(e).outlineWidth; });
    ok('키보드 포커스 표시가 보임', /solid 3px/.test(outline), outline);
    ok('저장 결과·합계·상태 안내가 role=status/aria-live', (await page.$$eval('#live, #store-chip, .say', (n) => n.every((x) => x.getAttribute('role') === 'status' || x.getAttribute('aria-live'))))
    );
    // 평가자 코드 칸 이외의 곳에서 1을 눌러도 체크박스가 점수로 바뀌지 않음
    await page.focus(`#${k}-${crit[0]}-x`); await page.keyboard.press('1');
    ok('체크박스에서 숫자 키가 점수를 바꾸지 않음', (await page.$$eval(`input[name="${k}-${crit[0]}"]`, (r) => r.filter((x) => x.checked).length)) === 0);
    await ctx.close();
  }

  // ===== 화이트리스트: 답 열쇠 필드가 페이지에 없음 =====
  {
    const html = fs.readFileSync(path.join(__dirname, '../index.html'), 'utf8');
    const data = JSON.parse(html.match(/var DATA = (\{.*?\});\r?\n/s)[1].replace(/<\\\//g, '</'));
    const keys = new Set();
    (function walk(o) { if (o && typeof o === 'object') for (const [k, v] of Object.entries(o)) { if (!Array.isArray(o)) keys.add(k); walk(v); } })(data.pack);
    ok('페이지 데이터의 묶음 필드는 허용 목록뿐', [...keys].every((k) => ['pack', 'items', 'id', 'situation', 'context', 'source', 'answers', 'text', 'sensitive'].includes(k)), [...keys].join(','));
  }

  ok('페이지 오류 없음', errors.length === 0, errors.join('; '));
  await browser.close();
  const fail = results.filter((x) => !x).length;
  console.log(`\n${results.length - fail}/${results.length} 통과`);
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
