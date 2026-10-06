// test_only 표시 검사: 평가 묶음(test_only:false) 문항을 채점해 내보낸 기록에는 test_only가 없고,
// 테스트 문항(test-items.json) 채점 기록에는 test_only:true가 그대로 붙는지 본다.
// 실행: apps/warmth-scorer 에서 python -m http.server 8765 를 켠 뒤 node apps/warmth-scorer/tests/testonly.browser.js
'use strict';
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');
const packPath = path.join(__dirname, '../../../docs/eval/packs/calibration-v0.json');
const pack = JSON.parse(fs.readFileSync(packPath, 'utf8'));

(async () => {
  const results = [];
  const ok = (name, cond, d = '') => { results.push(!!cond); console.log(`${cond ? 'PASS' : 'FAIL'} ${name}${d ? ' — ' + d : ''}`); };
  const browser = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
  const errors = [];

  async function scoreAndExport(open) {
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, acceptDownloads: true });
    const page = await ctx.newPage();
    page.on('pageerror', (e) => errors.push(e.message));
    await page.goto(process.env.APP_URL || 'http://127.0.0.1:8765/index.html');
    await page.waitForFunction(() => /불러왔습니다/.test(document.getElementById('rubric-status').textContent));
    await page.fill('#rater', 'R-A');
    await open(page);
    await page.selectOption('#test-item-select', '1'); // 두 번째(일반) 문항
    await page.click('#start-scoring');
    await page.waitForSelector('#scoring-section', { state: 'visible' });
    for (const n of ['1', '2', '3', '4', '5']) { await page.keyboard.press(n); await page.keyboard.press('1'); } // 5개 항목 모두 1점
    const [dl] = await Promise.all([page.waitForEvent('download'), page.click('#export-jsonl')]);
    const lines = fs.readFileSync(await dl.path(), 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l));
    const store = await page.evaluate(() => JSON.parse(localStorage.getItem(Object.keys(localStorage).find((k) => /warmth/.test(k)))));
    await ctx.close();
    return { lines, store };
  }

  const packRun = await scoreAndExport(async (page) => {
    await page.setInputFiles('#pack-file', packPath);
    await page.waitForFunction(() => /평가 묶음 문항/.test(document.getElementById('message').textContent));
  });
  ok('묶음 문항 채점: 내보낸 기록이 있음', packRun.lines.length > 0, String(packRun.lines.length));
  console.log('  (묶음) 내보낸 기록 test_only 값:', JSON.stringify(packRun.lines.map((l) => l.test_only)));
  ok('묶음 문항 채점: 내보낸 기록에 test_only 없음', packRun.lines.every((l) => !('test_only' in l)));
  ok('묶음 문항 채점: 저장된 문항에도 test_only 없음', packRun.store.items.every((it) => it.test_only !== true));
  ok('묶음 문항 채점: 묶음 문항 id는 남음', packRun.store.items.some((it) => it.test_item_id === pack.items[1].id));

  const testRun = await scoreAndExport(async (page) => {
    await page.click('#load-test-items');
    await page.waitForFunction(() => /테스트 문항 \d+개를 불러왔습니다/.test(document.getElementById('message').textContent));
  });
  ok('테스트 문항 채점: 내보낸 기록이 있음', testRun.lines.length > 0, String(testRun.lines.length));
  console.log('  (테스트) 내보낸 기록 test_only 값:', JSON.stringify(testRun.lines.map((l) => l.test_only)));
  ok('테스트 문항 채점: 내보낸 기록에 test_only:true', testRun.lines.every((l) => l.test_only === true));

  ok('페이지 오류 없음', errors.length === 0, errors.join('; '));
  await browser.close();
  const fail = results.filter((x) => !x).length;
  console.log(fail ? `\n실패 ${fail}건` : `\n전부 통과 (${results.length}건)`);
  process.exitCode = fail ? 1 : 0;
})().catch((e) => { console.error(e); process.exitCode = 1; });
