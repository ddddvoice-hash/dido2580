// 비서 화면 검사(오프라인 모드). 실행: DIDO_OFFLINE=1 python apps/dido-assistant/server.py --port 8770 을 켠 뒤
//   NODE_PATH=<playwright> CHROMIUM=<크롬 경로> node apps/dido-assistant/tests/assistant.browser.js
const { chromium } = require('playwright');
const URL_ = process.env.APP_URL || 'http://127.0.0.1:8770/';
let pass = 0, fail = 0;
function check(name, ok, info) { if (ok) pass++; else fail++; console.log((ok ? 'PASS ' : 'FAIL ') + name + (info ? '  — ' + info : '')); }
(async () => {
  const browser = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
  const page = await browser.newPage({ viewport: { width: 390, height: 860 } });
  const errs = []; page.on('pageerror', e => errs.push(e.message));
  await page.goto(URL_);
  await page.waitForFunction(() => document.querySelectorAll('#log .msg.ai').length >= 1);
  check('첫인사에서 AI라고 밝힘', (await page.textContent('#log')).includes('AI 비서'));
  check('상태 표시: 오프라인', (await page.textContent('#mode-chip')).includes('오프라인'));
  await page.fill('#q', '총 1,234,500원 어떻게 읽어?');
  await page.keyboard.press('Enter');
  await page.waitForFunction(() => document.querySelectorAll('#log .msg.ai').length >= 2);
  const last = await page.locator('#log .msg.ai').last().textContent();
  check('숫자 질문에 사람 읽기로 대답', last.includes('백이십삼만 사천오백 원'), last);
  await page.click('#t-script');
  check('탭 전환: 대본 점검 보임', await page.isVisible('#p-script') && !(await page.isVisible('#p-chat')));
  await page.fill('#script', '안녕하세요. 예약 번호는 4719-2386이에요.');
  await page.click('#script-go');
  await page.waitForFunction(() => document.querySelector('#script-out').textContent.length > 0);
  check('대본 점검 결과', (await page.textContent('#script-out')).includes('사칠일구, 이삼팔육'));
  await page.keyboard.press('ArrowRight');
  await page.click('#t-num');
  await page.fill('#num', '3시가 아니라 4시에 만나요.');
  await page.keyboard.press('Enter');
  await page.waitForFunction(() => document.querySelector('#num-out').textContent.length > 0);
  check('숫자 읽기 탭', (await page.textContent('#num-out')) === '세 시가 아니라 네 시에 만나요.');
  const btnH = await page.$$eval('button', bs => Math.min(...bs.filter(b => b.offsetParent).map(b => b.getBoundingClientRect().height)));
  check('보이는 버튼 높이 48px 이상', btnH >= 48, String(btnH));
  check('가로 넘침 없음(390px)', await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
  check('페이지 오류 없음', errs.length === 0, errs.join(' | '));
  await browser.close();
  console.log(`\n${pass}/${pass + fail} 통과`);
  process.exit(fail ? 1 : 0);
})();
