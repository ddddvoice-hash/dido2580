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
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 }, acceptDownloads: true });
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
  // 구간 듣기: 키보드로 위치 옮기기 → 번갈아 듣기, 그래프 누르기
  await page.focus("#seg-pos");
  for (let i = 0; i < 10; i++) await page.keyboard.press("ArrowRight");
  ok("화살표 키로 구간 위치 50%", (await page.inputValue("#seg-pos")) === "50" && (await page.textContent("#seg-label")).includes("50%"));
  await page.click("#seg-play");
  await page.waitForFunction(() => document.getElementById("mine-status").textContent.includes("50% 지점"), null, { timeout: 5000 });
  ok("번갈아 듣기 시작 안내", (await page.textContent("#mine-status")).includes("2초씩 번갈아"));
  const box = await page.locator("#chart").boundingBox();
  await page.mouse.click(box.x + box.width * 0.76, box.y + box.height / 2);
  ok("그래프를 누르면 그 자리(75%)로", (await page.inputValue("#seg-pos")) === "75");
  ok("구간 버튼 높이 48px 이상", (await page.locator("#seg-play").boundingBox()).height >= 47.5);


  await page.setInputFiles("#mine-file", skip);
  await page.waitForFunction(() => document.getElementById("feedback").textContent.includes("놓친 쉼"), null, { timeout: 15000 });
  ok("쉼을 건너뛴 파일은 놓친 쉼 안내", (await page.textContent("#feedback")).includes("놓친 쉼 1곳"));
  ok("'녹음 파일 올리기' 버튼 높이 48px 이상", (await page.locator("#mine-upload").boundingBox()).height >= 47.5);
  await page.focus("#mine-upload");
  ok("키보드로 '녹음 파일 올리기'에 갈 수 있음", await page.evaluate(() => document.activeElement.id === "mine-upload"));

  // ---- 연기 연습 카드 ----
  ok("카드 뽑기 전에는 녹음 버튼 꺼짐", !(await page.isEnabled("#card-rec")));
  await page.click("#card-draw");
  const cardText = await page.textContent("#card-status");
  ok("카드 세 장과 읽을 안내", (await page.textContent("#card-who")) !== "—" && /읽어 보세요/.test(cardText) && !/[가-힣](이가|가이)\b/.test(cardText), cardText.slice(0, 60));
  await page.setInputFiles("#card-file", same);
  await page.waitForSelector("#card-check:not(.hidden)");
  await page.check('#card-check input[data-c="0"]');
  await page.click("#card-save");
  const hist = await page.textContent("#history");
  ok("카드 연습 기록(점수 없음, 점검 1/3)", hist.includes("카드:") && hist.includes("1/3"), hist.slice(0, 80));

  // ---- 선생님: 문장 관리 ----
  await page.fill("#sentence-new", "<b>굵게</b> 새 문장입니다. 천천히 읽어 보세요.");
  await page.click("#sentence-add");
  ok("새 문장 추가 → 13번, 글자 그대로(HTML로 안 바뀜)", (await page.textContent("#sentence-text")).startsWith("<b>굵게</b>") && (await page.$$eval("#sentence-select option", (o) => o.length)) === 13);
  // 새 문장(시범 없음)으로 바뀐 것을 확인한 뒤 올려야, 앞 문장의 '듣기 켜짐'을 올리기 끝으로 착각하지 않는다(CI 25번 실패 원인).
  await page.waitForFunction(() => document.getElementById("demo-play").disabled && document.getElementById("demo-status").textContent.includes("아직 시범 녹음이 없습니다"));
  await page.setInputFiles("#demo-file", demo);
  await page.waitForFunction(() => !document.getElementById("demo-play").disabled && document.getElementById("demo-status").textContent.includes("시범 길이"), null, { timeout: 15000 });
  await page.fill("#sentence-edit", "고친 문장입니다. 끝까지 또렷하게.");
  await page.click("#sentence-save");
  ok("문장 고치기", (await page.textContent("#sentence-text")) === "고친 문장입니다. 끝까지 또렷하게.");
  await page.selectOption("#sentence-select", "1");
  await page.click("#sentence-delete");
  ok("지우기 첫 번째 누름은 확인만", (await page.$$eval("#sentence-select option", (o) => o.length)) === 13 && (await page.textContent("#sentence-delete")).includes("한 번 더"));
  await page.click("#sentence-delete");
  // 지우기는 시범 녹음(IndexedDB)을 먼저 지운 뒤 목록을 다시 그린다.
  const deleted = await page.waitForFunction(() => document.querySelectorAll("#sentence-select option").length === 12, null, { timeout: 5000 }).then(() => true, () => false);
  ok("두 번 누르면 지움 → 12개", deleted);

  // ---- 시범 팩 내보내기 → 새 브라우저(수강생)에서 열기 ----
  const [dl] = await Promise.all([page.waitForEvent("download"), page.click("#pack-export")]);
  const packPath = path.join(dir, "pack.json");
  await dl.saveAs(packPath);
  const pack = JSON.parse(fs.readFileSync(packPath, "utf8"));
  ok("시범 팩: 문장 12개, 시범 2개(1번·고친 13번)", pack.sentences.length === 12 && Object.keys(pack.demos).length === 2, `${pack.sentences.length}/${Object.keys(pack.demos).length}`);

  const student = await browser.newContext();
  const sp = await student.newPage();
  sp.on("pageerror", (e) => errors.push(e.message));
  await sp.goto("file://" + path.resolve(__dirname, "../index.html"));
  const bad = path.join(dir, "bad.json");
  fs.writeFileSync(bad, JSON.stringify({ ...pack, sentences: [{ id: 0, text: "" }] }));
  await sp.setInputFiles("#pack-file", bad);
  await sp.waitForFunction(() => document.getElementById("pack-status").textContent.length > 0);
  ok("잘못된 팩은 거부하고 목록 유지", (await sp.textContent("#pack-status")).includes("올바르지 않습니다") && (await sp.$$eval("#sentence-select option", (o) => o.length)) === 12);
  await sp.setInputFiles("#pack-file", packPath);
  await sp.waitForSelector("#pack-confirm:not(.hidden)");
  ok("열기 전에 확인을 물음", (await sp.textContent("#pack-confirm-text")).includes("문장 12개, 시범 녹음 2개"));
  await sp.click("#pack-apply");
  await sp.waitForFunction(() => document.getElementById("pack-status").textContent.includes("열었습니다"));
  await sp.selectOption("#sentence-select", String(11));
  await sp.waitForFunction(() => !document.getElementById("demo-play").disabled, null, { timeout: 15000 });
  ok("수강생 쪽에 고친 문장과 시범이 그대로", (await sp.textContent("#sentence-text")) === "고친 문장입니다. 끝까지 또렷하게.");
  await sp.setInputFiles("#mine-file", same);
  await sp.waitForFunction(() => !document.getElementById("result").classList.contains("hidden"), null, { timeout: 15000 });
  ok("수강생이 따라 읽기 비교까지 됨", (await sp.textContent("#score")).trim() === "100점");
  await student.close();
  ok("페이지 오류 없음", errors.length === 0, errors.join("; "));
  await browser.close();
  fs.rmSync(dir, { recursive: true, force: true });
  const fail = results.filter((x) => !x).length;
  console.log(fail ? `\n실패 ${fail}건` : `\n전부 통과 (${results.length}건)`);
  process.exitCode = fail ? 1 : 0;
})().catch((e) => { console.error(e); process.exitCode = 1; });
