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

  // ---- R28 화면 지적 10·11·12: 가짜 음성 인식과 느린·실패하는 통신으로 확인 ----
  async function fresh() {
    const pg = await browser.newPage({ viewport: { width: 390, height: 860 } });
    pg.on('pageerror', e => errs.push(e.message));
    await pg.addInitScript(() => {
      window.__calls = [];
      window.SpeechRecognition = window.webkitSpeechRecognition = function () {
        const me = this; window.__rec = me;
        const end = () => setTimeout(() => me.onend && me.onend(), 0);
        me.start = () => window.__calls.push('start');
        me.stop = () => { window.__calls.push('stop'); end(); };
        me.abort = () => { window.__calls.push('abort'); end(); };
      };
    });
    await pg.goto(URL_);
    await pg.waitForFunction(() => document.querySelectorAll('#log .msg.ai').length >= 1);
    return pg;
  }
  {
    // 10: Esc가 음성 인식을 멈추고, 들린 글을 자동으로 보내지 않음
    const pg = await fresh(); let chats = 0;
    await pg.route('**/api/chat', r => { chats++; r.continue(); });
    await pg.click('#mic');
    await pg.evaluate(() => window.__rec.onresult({ results: [[{ transcript: '지금 몇 시야' }]] }));
    await pg.keyboard.press('Escape');
    await pg.waitForTimeout(300);
    check('Esc가 음성 인식을 멈춤', (await pg.evaluate(() => window.__calls)).some(c => c === 'abort' || c === 'stop'));
    check('Esc 뒤 자동으로 보내지 않음', chats === 0, String(chats));
    check('Esc 뒤 입력 글은 남아 있음', (await pg.inputValue('#q')) === '지금 몇 시야');
    check('마이크 버튼이 원래대로', (await pg.getAttribute('#mic', 'aria-pressed')) === 'false');
    await pg.close();
  }
  {
    // 11: 새 대화를 누르면 이전 대답이 새 화면에 섞이지 않음
    const pg = await fresh(); let release; const gate = new Promise(r => { release = r; });
    await pg.route('**/api/chat', async r => { await gate; r.continue(); });
    await pg.fill('#q', '지금 몇 시야?'); await pg.keyboard.press('Enter');
    await pg.click('#reset');
    await pg.waitForFunction(() => document.querySelectorAll('#log .msg').length === 1);
    release(); await pg.waitForTimeout(600);
    const n = await pg.locator('#log .msg').count();
    check('새 대화 뒤 이전 답변이 섞이지 않음', n === 1 && (await pg.textContent('#log')).includes('AI 비서'), String(n));
    await pg.close();
  }
  {
    // 11b: 새 대화 초기화가 실패하면 알림
    const pg = await fresh();
    await pg.route('**/api/reset', r => r.abort());
    await pg.click('#reset');
    await pg.waitForFunction(() => document.querySelector('#say').textContent.includes('닿지 못했어요'));
    check('초기화 통신 실패를 안내', true);
    await pg.close();
  }
  {
    // 12: 대본·숫자 탭의 통신 실패가 보이는 상태 영역에 나옴
    const pg = await fresh();
    await pg.route('**/api/script', r => r.abort());
    await pg.route('**/api/speak', r => r.abort());
    await pg.click('#t-script'); await pg.fill('#script', '예약 번호는 4719-2386이에요.'); await pg.click('#script-go');
    await pg.waitForFunction(() => document.querySelector('#say').textContent.includes('닿지 못했어요'));
    check('대본 점검 실패가 보이는 곳에 안내됨', await pg.isVisible('#say'));
    await pg.click('#t-num'); await pg.fill('#num', '3시'); await pg.click('#num-go');
    await pg.waitForTimeout(400);
    check('숫자 탭에서도 안내가 보임', await pg.isVisible('#say') && (await pg.textContent('#say')).includes('닿지 못했어요'));
    check('안내 영역이 읽어 주는 영역(status)', (await pg.getAttribute('#say', 'role')) === 'status');
    await pg.close();
  }

  const btnH = await page.$$eval('button', bs => Math.min(...bs.filter(b => b.offsetParent).map(b => b.getBoundingClientRect().height)));
  check('보이는 버튼 높이 48px 이상', btnH >= 48, String(btnH));
  check('가로 넘침 없음(390px)', await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
  check('페이지 오류 없음', errs.length === 0, errs.join(' | '));
  await browser.close();
  console.log(`\n${pass}/${pass + fail} 통과`);
  process.exit(fail ? 1 : 0);
})();
