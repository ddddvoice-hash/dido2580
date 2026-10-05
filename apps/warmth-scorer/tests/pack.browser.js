// 평가 묶음 열기 검사: docs/eval/packs/calibration-v0.json을 열면 실제 문항(테스트용 아님)으로 들어가고,
// 묶음 파일에 의도한 점수가 들어 있지 않은지 본다.
// 실행: apps/warmth-scorer 에서 python -m http.server 8765 를 켠 뒤 node apps/warmth-scorer/tests/pack.browser.js
'use strict';
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');
const packPath = path.join(__dirname, '../../../docs/eval/packs/calibration-v0.json');
const pack = JSON.parse(fs.readFileSync(packPath, 'utf8'));

(async () => {
  const results = [];
  const ok = (name, cond, d = '') => { results.push(!!cond); console.log(`${cond ? 'PASS' : 'FAIL'} ${name}${d ? ' — ' + d : ''}`); };
  const raw = fs.readFileSync(packPath, 'utf8');
  ok('묶음 파일에 의도한 점수·종류가 없음', !/intended|"kind"|rationale/.test(raw));
  ok('묶음은 실제 평가용(test_only 아님)', pack.test_only === false);
  const browser = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto(process.env.APP_URL || 'http://127.0.0.1:8765/index.html');
  await page.waitForFunction(() => /불러왔습니다/.test(document.getElementById('rubric-status').textContent));
  const btnH = await page.$eval('#open-pack', (b) => b.getBoundingClientRect().height);
  ok('평가 묶음 열기 버튼 48px 이상', btnH >= 47.5, String(btnH));
  await page.setInputFiles('#pack-file', packPath);
  await page.waitForFunction(() => /평가 묶음 문항/.test(document.getElementById('message').textContent));
  const msg = await page.textContent('#message');
  ok(`평가 묶음 문항 ${pack.items.length}개를 불러옴`, msg.includes(`평가 묶음 문항 ${pack.items.length}개`), msg);
  const stored = await page.evaluate(() => JSON.parse(localStorage.getItem(Object.keys(localStorage).find((k) => /warmth/.test(k)) || '{}')));
  const items = (stored.items || []);
  ok('저장된 문항이 묶음 수와 같음', items.length === pack.items.length, String(items.length));
  ok('테스트용 표시가 붙지 않음', items.every((it) => it.test_only !== true));
  ok('첫 문항 상황이 칸에 채워짐', (await page.inputValue('#situation')) === pack.items[0].situation);
  ok('안내 문구 표시', (await page.textContent('#test-notice')).includes('조정용 평가 묶음'));
  ok('페이지 오류 없음', errors.length === 0, errors.join('; '));
  await browser.close();
  const fail = results.filter((x) => !x).length;
  console.log(fail ? `\n실패 ${fail}건` : `\n전부 통과 (${results.length}건)`);
  process.exitCode = fail ? 1 : 0;
})();
