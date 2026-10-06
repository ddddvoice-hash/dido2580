// 위기 문항 접기 검사: 묶음에서 sensitive 문항을 고르면 본문을 접은 채 안내 문구와 [읽기]/[건너뛰기]만 보이는지,
// 읽기로 펼치고 건너뛰기로 결측(skipped)이 남아 일치도 계산에서 빠지는지, 키보드만으로 되는지 본다.
// 실행: apps/warmth-scorer 에서 python -m http.server 8765 를 켠 뒤 node apps/warmth-scorer/tests/sensitive.browser.js
// Playwright 필요. Chromium 위치는 CHROMIUM 환경변수.
'use strict';
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');
const W = require('../app.js');
const rubric = require('../rubric.json');
const packPath = path.join(__dirname, '../../../docs/eval/packs/calibration-v0.json');
const pack = JSON.parse(fs.readFileSync(packPath, 'utf8'));
const calib = fs.readFileSync(path.join(__dirname, '../../../docs/eval/calibration.md'), 'utf8').replace(/\r\n/g, '\n');
// calibration.md '위기 문항을 채점할 때'의 인용문(> "..." 한 줄)
const section = calib.slice(calib.indexOf('## 위기 문항을 채점할 때'));
const quoteLine = section.split('\n').find((l) => /^\s*> "/.test(l));
const QUOTE = quoteLine.replace(/^\s*> "/, '').replace(/"\s*$/, '');

(async () => {
  const results = [];
  const ok = (name, cond, d = '') => { results.push(!!cond); console.log(`${cond ? 'PASS' : 'FAIL'} ${name}${d ? ' — ' + d : ''}`); };
  const sIdx = pack.items.findIndex((it) => it.sensitive === true);
  const sItem = pack.items[sIdx];
  const normalIdx = pack.items.findIndex((it) => it.sensitive !== true);
  ok('묶음에 sensitive 문항이 있고 위기 수준 문항만 해당', sIdx >= 0 && pack.items.filter((i) => i.sensitive).length === 1 && sItem.scenario_id === 's28');
  ok('calibration.md 인용문을 찾음', QUOTE.length > 100 && QUOTE.startsWith('이번 채점에는'), QUOTE.slice(0, 20));

  const browser = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, acceptDownloads: true });
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto(process.env.APP_URL || 'http://127.0.0.1:8765/index.html');
  await page.waitForFunction(() => /불러왔습니다/.test(document.getElementById('rubric-status').textContent));
  await page.fill('#rater', 'R-A');
  await page.setInputFiles('#pack-file', packPath);
  await page.waitForFunction(() => /평가 묶음 문항/.test(document.getElementById('message').textContent));

  const visibleText = () => page.evaluate(() => document.body.innerText);
  const answersText = sItem.answers.map((a) => a.text);
  const leaks = async () => {
    const t = await visibleText();
    return [sItem.situation, ...answersText].filter((x) => t.includes(x.slice(0, 15)));
  };

  // 1. 첫 문항(일반)은 평소처럼 보임
  ok('일반 문항은 본문이 그대로 보임', (await page.isVisible('#situation')) && !(await page.isVisible('#sensitive-gate')));

  // 2. 위기 문항을 고르면 접힘
  await page.selectOption('#test-item-select', String(sIdx));
  ok('위기 문항: 상황 칸이 보이지 않음', !(await page.isVisible('#situation')));
  ok('위기 문항: 답변 칸이 보이지 않음', (await page.$$eval('#answers-list textarea', (t) => t.filter((x) => x.offsetParent !== null).length)) === 0);
  ok('위기 문항: 화면 글에 상황·답변 본문이 없음', (await leaks()).length === 0, (await leaks()).join('|'));
  ok('위기 문항: 문항 목록에도 본문이 드러나지 않음', !(await page.$$eval('#test-item-select option', (o) => o.map((x) => x.textContent).join('|'))).includes(sItem.situation.slice(0, 10)));
  ok('안내 문구가 calibration.md 인용문과 같음', (await page.textContent('#gate-quote')).trim() === QUOTE);
  ok('안내 영역에 읽기·건너뛰기 버튼', (await page.isVisible('#gate-read')) && (await page.isVisible('#gate-skip')) && (await page.textContent('#gate-read')).trim() === '읽기' && (await page.textContent('#gate-skip')).trim() === '건너뛰기');
  const hs = await page.$$eval('#gate-read, #gate-skip', (b) => b.map((x) => x.getBoundingClientRect().height));
  ok('두 버튼 높이 48px 이상', hs.every((h) => h >= 47.5), hs.join(','));
  ok('안내 상태는 aria-live로 알림', (await page.getAttribute('#gate-status', 'aria-live')) === 'polite' && (await page.getAttribute('#message', 'aria-live')) === 'polite' && (await page.textContent('#message')).includes('위기 문항'));
  await page.click('#start-scoring');
  ok('접힌 채로 채점 시작을 누르면 막고 안내', !(await page.isVisible('#scoring-section')) && (await page.textContent('#message')).includes('읽기나 건너뛰기'));

  // 3. 키보드만으로: 목록에서 Tab → 읽기 → Tab → 건너뛰기, 포커스 표시
  await page.focus('#test-item-select');
  await page.keyboard.press('Tab');
  ok('목록 다음 Tab이 [읽기]로 감', (await page.evaluate(() => document.activeElement.id)) === 'gate-read');
  const outline = await page.$eval('#gate-read', (b) => getComputedStyle(b).outlineStyle + ' ' + getComputedStyle(b).outlineWidth);
  ok('키보드 포커스 표시가 보임', /solid 3px/.test(outline), outline);
  await page.keyboard.press('Tab');
  ok('다음 Tab이 [건너뛰기]로 감', (await page.evaluate(() => document.activeElement.id)) === 'gate-skip');
  await page.keyboard.press('Shift+Tab');

  // 4. Enter로 읽기 → 펼침, 평소처럼 채점(키보드)
  await page.keyboard.press('Enter');
  ok('읽기: 상황 본문이 펼쳐짐', (await page.isVisible('#situation')) && (await page.inputValue('#situation')) === sItem.situation);
  ok('읽기: 답변 본문이 펼쳐짐', (await page.$$eval('#answers-list textarea', (t) => t.map((x) => x.value))).join('|') === answersText.join('|'));
  ok('읽기: 안내 영역이 사라지고 상태 안내', !(await page.isVisible('#sensitive-gate')) && (await page.textContent('#message')).includes('본문을 열었어요'));
  await page.focus('#start-scoring');
  await page.keyboard.press('Enter');
  ok('읽기 뒤 채점 화면이 열림', (await page.isVisible('#scoring-section')) && (await page.inputValue('#answer-text')) === answersText[0]);
  await page.keyboard.press('1');
  await page.keyboard.press('2');
  ok('읽기 뒤 키보드로 점수가 들어감', (await page.textContent('#total')).includes('1/5'), await page.textContent('#total'));

  // 5. 다른 문항으로 갔다가 돌아오면 다시 접힘 (채점 화면에도 본문이 남지 않음)
  await page.selectOption('#test-item-select', String(normalIdx));
  ok('일반 문항으로 가면 본문이 보임', await page.isVisible('#situation'));
  await page.selectOption('#test-item-select', String(sIdx));
  ok('다시 위기 문항을 고르면 접힘', !(await page.isVisible('#situation')) && (await page.isVisible('#sensitive-gate')));
  ok('다시 접힌 뒤 채점 화면에도 본문이 없음', !(await page.isVisible('#scoring-section')) && (await leaks()).length === 0);

  // 6. 같은 문항을 다시 골라도 접힘(펼친 뒤 같은 항목 재선택)
  await page.focus('#gate-read');
  await page.keyboard.press('Enter');
  await page.selectOption('#test-item-select', String(sIdx));
  ok('같은 문항을 다시 고르면 또 접힘', !(await page.isVisible('#situation')));

  // 7. 건너뛰기: 이미 점수를 준 문항은 건너뛸 수 없음 → 다른 평가자 R-S로 바꿔서 건너뛰기
  await page.fill('#rater', 'R-S');
  await page.focus('#gate-skip');
  await page.keyboard.press('Enter');
  const skipMsg = await page.textContent('#gate-status');
  ok('건너뛰기: 상태 안내에 평가하지 않음', skipMsg.includes('건너뛰었어요') && skipMsg.includes('평가하지 않음'), skipMsg);
  ok('건너뛰기: 본문은 접힌 그대로', !(await page.isVisible('#situation')) && (await leaks()).length === 0);
  const totalsText = await page.textContent('#answer-totals');
  ok('건너뛰기: 답변별 합계에 건너뜀 표시', totalsText.includes('건너뜀'), totalsText);
  ok('건너뛰기는 저장된 채점 건수에 안 셈', (await page.textContent('#saved-count')) === '0', await page.textContent('#saved-count'));
  const store = await page.evaluate(() => JSON.parse(localStorage.getItem(Object.keys(localStorage).find((k) => /warmth/.test(k)))));
  const skips = store.scorings.filter((s) => s.rater === 'R-S' && s.skipped === true);
  ok('저장소에 답변마다 skipped 기록(점수·합계 없음)', skips.length === sItem.answers.length && skips.every((s) => s.total === null && Object.keys(s.scores).length === 0), String(skips.length));

  // 8. 내보내기 JSONL: skipped 표시, 점수 null
  const [dl] = await Promise.all([page.waitForEvent('download'), page.click('#export-jsonl')]);
  const exported = fs.readFileSync(await dl.path(), 'utf8');
  const lines = exported.split('\n').filter(Boolean).map((l) => JSON.parse(l));
  const sk = lines.filter((l) => l.skipped === true);
  ok('JSONL에 skipped 표시 줄이 답변 수만큼', sk.length === sItem.answers.length, String(sk.length));
  ok('skipped 줄은 점수가 모두 null이고 합계 null', sk.every((l) => l.total === null && rubric.criteria.every((c) => l.scores[c.id] === null)));
  ok('skipped 줄이 기록 검사를 통과', W.parseJsonl(exported, rubric).bad.length === 0);
  ok('점수를 준 줄에는 skipped 표시가 없음', lines.filter((l) => l.skipped !== true).every((l) => !('skipped' in l)));

  // 9. 일치도에서 빠짐: 건너뛴 R-S + 점수를 준 R-B·R-C 둘 → 둘의 평가만 쓰임, 건너뛴 R-S + R-B 하나뿐이면 계산 대상 아님
  const base = sk[0];
  const mk = (rater, aid, v) => ({ ...base, answer_id: aid, rater, skipped: undefined, scores: Object.fromEntries(rubric.criteria.map((c) => [c.id, v])), total: 5, date: '2026-10-06T10:00:00+09:00' });
  const parsed = W.parseJsonl(exported, rubric).records;
  const withTwo = W.computeAgreement(rubric, parsed.concat([mk('R-B', 'A', 2), mk('R-C', 'A', 1)]));
  ok('건너뛴 사람이 있어도 나머지 둘의 평가는 계산에 쓰임', withTwo.criteria.every((c) => c.ratings === 2 && c.answersUsed === 1), JSON.stringify(withTwo.criteria[0]));
  const withOne = W.computeAgreement(rubric, parsed.concat([mk('R-B', 'A', 2)]));
  ok('건너뛴 사람 + 한 사람뿐이면 계산에 안 쓰임', withOne.criteria.every((c) => c.ratings === 0 && c.answersUsed === 0 && c.pairs === 0), JSON.stringify(withOne.criteria[0]));
  const skipOnly = W.computeAgreement(rubric, parsed);
  ok('건너뛴 기록은 0점으로 세지 않음', skipOnly.criteria.every((c) => c.ratings === 0 && c.pairs === 0));

  // 10. 새로고침 후에도 접힌 채(문서 저장된 초안의 위기 표시 유지) → 본문 안 보임
  await page.reload();
  await page.waitForFunction(() => /불러왔습니다/.test(document.getElementById('rubric-status').textContent));
  ok('새로고침해도 위기 문항은 접혀 있음', !(await page.isVisible('#situation')) && (await page.isVisible('#sensitive-gate')) && (await leaks()).length === 0);

  ok('페이지 오류 없음', errors.length === 0, errors.join('; '));
  await browser.close();
  const fail = results.filter((x) => !x).length;
  console.log(fail ? `\n실패 ${fail}건` : `\n전부 통과 (${results.length}건)`);
  process.exitCode = fail ? 1 : 0;
})().catch((e) => { console.error(e); process.exitCode = 1; });
