// 낭독 코치 브라우저 검사: 시범 파일과 내 녹음 파일을 올려 결과(점수·피드백·그래프)가 나오는지 본다.
// 실행: node apps/reading-coach/tests/browser.test.js   (Playwright 필요, CHROMIUM 환경변수로 위치 지정 가능)
"use strict";
const fs = require("fs");
const os = require("os");
const path = require("path");
const { chromium } = require("playwright");

function wav(file, parts, rate = 16000) {
  const total = parts.reduce((s, [sec]) => s + Math.round(sec * rate), 0);
  const data = Buffer.alloc(total * 2);
  let pos = 0;
  for (const [sec, amp] of parts) {
    for (let i = 0; i < Math.round(sec * rate); i++, pos++) {
      const v = amp ? amp * Math.sin(2 * Math.PI * 200 * i / rate) : (Math.random() - 0.5) * 0.0004;
      data.writeInt16LE(Math.round(v * 32767), pos * 2);
    }
  }
  const h = Buffer.alloc(44);
  h.write("RIFF", 0); h.writeUInt32LE(36 + data.length, 4); h.write("WAVE", 8); h.write("fmt ", 12);
  h.writeUInt32LE(16, 16); h.writeUInt16LE(1, 20); h.writeUInt16LE(1, 22); h.writeUInt32LE(rate, 24);
  h.writeUInt32LE(rate * 2, 28); h.writeUInt16LE(2, 32); h.writeUInt16LE(16, 34); h.write("data", 36); h.writeUInt32LE(data.length, 40);
  fs.writeFileSync(file, Buffer.concat([h, data]));
}

(async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "coach-"));
  const demo = path.join(dir, "demo.wav"), same = path.join(dir, "same.wav"), skip = path.join(dir, "skip.wav");
  const parts = [[0.3, 0], [1, .5], [0.6, 0], [1, .5], [0.6, 0], [1, .5], [0.3, 0]];
  wav(demo, parts); wav(same, parts);
  wav(skip, [[0.3, 0], [1, .5], [0.6, 0], [2, .5], [0.3, 0]]);
  const results = [];
  const ok = (name, cond, detail = "") => { results.push(!!cond); console.log(`${cond ? "PASS" : "FAIL"} ${name}${detail ? " — " + detail : ""}`); };
  const browser = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("file://" + path.resolve(__dirname, "../index.html"));
  await page.click("summary");
  await page.setInputFiles("#demo-file", demo);
  await page.waitForFunction(() => !document.getElementById("demo-play").disabled, null, { timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(800);

  await page.setInputFiles("#mine-file", same);
  await page.waitForFunction(() => !document.getElementById("result").classList.contains("hidden"), null, { timeout: 15000 });
  ok("같은 낭독 파일을 올리면 100점", (await page.textContent("#score")).trim() === "100점", await page.textContent("#score"));
  ok("피드백에 '거의 같습니다'", (await page.textContent("#feedback")).includes("거의 같습니다"));
  ok("내 녹음 듣기 버튼이 켜짐", await page.isEnabled("#mine-play"));

  await page.setInputFiles("#mine-file", skip);
  await page.waitForFunction(() => document.getElementById("feedback").textContent.includes("놓친 쉼"), null, { timeout: 15000 });
  ok("쉼을 건너뛴 파일은 놓친 쉼 안내", (await page.textContent("#feedback")).includes("놓친 쉼 1곳"));
  ok("'녹음 파일 올리기' 버튼 높이 48px 이상", (await page.locator("#mine-upload").boundingBox()).height >= 47.5);
  await page.focus("#mine-upload");
  ok("키보드로 '녹음 파일 올리기'에 갈 수 있음", await page.evaluate(() => document.activeElement.id === "mine-upload"));
  ok("페이지 오류 없음", errors.length === 0, errors.join("; "));
  await browser.close();
  fs.rmSync(dir, { recursive: true, force: true });
  const fail = results.filter((x) => !x).length;
  console.log(fail ? `\n실패 ${fail}건` : `\n전부 통과 (${results.length}건)`);
  process.exitCode = fail ? 1 : 0;
})().catch((e) => { console.error(e); process.exitCode = 1; });
