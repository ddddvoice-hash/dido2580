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

const DEFAULT_FIRST = "안녕하세요. 오늘도 함께 읽어 보겠습니다.";
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
  ok("피드백에 '거의 같아요'", (await page.textContent("#feedback")).includes("거의 같아요"));
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
  // R6-7: 구간 듣기를 연달아 두 번 실행해도 앞 요청은 버려져 재생 소스는 한 쌍(2개)만 예약된다.
  const segCount = await page.evaluate(async () => { await Promise.all([playSegment(), playSegment()]); return segSources.length; });
  ok("[R6-7] 구간 듣기를 연달아 두 번 눌러도 재생 소스 2개", segCount === 2, String(segCount));


  await page.setInputFiles("#mine-file", skip);
  await page.waitForFunction(() => document.getElementById("feedback").textContent.includes("놓친 쉼"), null, { timeout: 15000 });
  ok("쉼을 건너뛴 파일은 놓친 쉼 안내", (await page.textContent("#feedback")).includes("놓친 쉼 1곳"));
  ok("'녹음 파일 올리기' 버튼 높이 48px 이상", (await page.locator("#mine-upload").boundingBox()).height >= 47.5);
  await page.focus("#mine-upload");
  ok("키보드로 '녹음 파일 올리기'에 갈 수 있음", await page.evaluate(() => document.activeElement.id === "mine-upload"));

  // ---- R6-7·R6-6: 문장 전환과 늦게 끝난 요청 ----
  const sw = await page.evaluate(async () => {
    const p = playSegment(); const q = selectSentence(1);
    await Promise.all([p, q]);
    return { sources: segSources.length, resultHidden: document.getElementById("result").classList.contains("hidden") };
  });
  ok("[R6-7] 구간 듣기 디코딩 중 문장을 바꾸면 예약 재생 없음·오류 없음", sw.sources === 0 && sw.resultHidden);
  const late = await page.evaluate(async () => {
    const orig = window.getDemo;
    window.getDemo = async (id) => { if (id === 0) await new Promise((r) => setTimeout(r, 500)); return orig(id); };
    const a = selectSentence(0); const b = selectSentence(1);
    await Promise.all([a, b]);
    await new Promise((r) => setTimeout(r, 800));
    window.getDemo = orig;
    return { status: document.getElementById("demo-status").textContent, hasDemo: demoResult !== null, cur: current };
  });
  ok("[R6-6] 문장을 빨리 바꿔도 늦게 끝난 앞 문장의 시범 분석이 남지 않음", late.cur === 1 && !late.hasDemo && late.status.includes("아직 시범 녹음이 없어요"), JSON.stringify(late));
  await page.evaluate(() => selectSentence(0));
  await page.waitForFunction(() => !document.getElementById("demo-play").disabled, null, { timeout: 15000 });
  await page.setInputFiles("#mine-file", same);
  await page.waitForFunction(() => document.getElementById("score").textContent.trim() === "100점", null, { timeout: 15000 });

  // ---- R3: 업로드 ----
  const b64 = (f) => fs.readFileSync(f).toString("base64");
  // R3-2: 첫 파일(100점)의 분석이 두 번째 파일(쉼 건너뜀)보다 늦게 끝나도 최신 파일 결과만 남는다.
  const r32 = await page.evaluate(async ([a, b]) => {
    const toBlob = (x) => { const bin = atob(x); const u = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i); return new Blob([u], { type: "audio/wav" }); };
    const orig = window.decode; let release; const gate = new Promise((r) => { release = r; }); let n = 0;
    window.decode = async (blob) => { const first = n++ === 0; const r = await orig(blob); if (first) await gate; return r; };
    const bb = toBlob(b);
    const p1 = onMineRecorded(toBlob(a)); const p2 = onMineRecorded(bb);
    await p2;
    const during = document.getElementById("score").textContent;
    release(); await p1;
    window.decode = orig;
    return { during, score: document.getElementById("score").textContent, fb: document.getElementById("feedback").textContent, same: mineBlob === bb, save: document.getElementById("save").disabled };
  }, [b64(same), b64(skip)]);
  ok("[R3-2] 늦게 끝난 앞 업로드가 최신 결과를 덮지 않음", r32.score === r32.during && r32.score !== "100점" && r32.fb.includes("놓친 쉼") && r32.same && !r32.save, JSON.stringify(r32).slice(0, 120));
  // R3-1: 분석 중에는 기록 버튼이 막히고, 해독 실패 뒤에는 이전 결과가 남지 않는다.
  const r31 = await page.evaluate(async (a) => {
    const bin = atob(a); const u = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
    const orig = window.decode; let release; const gate = new Promise((r) => { release = r; });
    window.decode = async (blob) => { const r = await orig(blob); await gate; return r; };
    const p = onMineRecorded(new Blob([u], { type: "audio/wav" }));
    const lockedWhileBusy = document.getElementById("save").disabled;
    const clearedWhileBusy = document.getElementById("result").classList.contains("hidden") && document.getElementById("score").textContent === "";
    release(); await p; window.decode = orig;
    return { lockedWhileBusy, clearedWhileBusy, after: document.getElementById("save").disabled };
  }, b64(same));
  ok("[R3-1] 새 업로드를 시작하면 이전 결과를 지우고 분석 중에는 기록 버튼을 막음", r31.lockedWhileBusy && r31.clearedWhileBusy && !r31.after, JSON.stringify(r31));
  await page.setInputFiles("#mine-file", { name: "x.wav", mimeType: "audio/wav", buffer: Buffer.from("이건 오디오가 아니에요") });
  await page.waitForFunction(() => document.getElementById("mine-status").textContent.includes("지원하지 않는 형식"), null, { timeout: 15000 });
  ok("[R3-1] 해독에 실패하면 이전 점수·그래프가 남지 않음", await page.evaluate(() => document.getElementById("result").classList.contains("hidden") && document.getElementById("score").textContent === "" && document.getElementById("mine-play").disabled));
  ok("[R3-4] 해독 실패 안내: 형식·손상 가능성과 다음 행동", (await page.textContent("#mine-status")).includes("손상된 파일일 수 있어요") && (await page.textContent("#mine-status")).includes("다른 오디오 파일"));
  await page.click("#save");
  const lastRec = await page.evaluate(() => { const h = loadHistory(); return h[h.length - 1]; });
  ok("[R3-1] 분석 실패 뒤 기록해도 이전 점수가 저장되지 않음", lastRec.score === null, JSON.stringify(lastRec));
  ok("[R6-8] 연습 기록에 당시 문장 본문이 저장됨", lastRec.text === DEFAULT_FIRST);
  const r33 = await page.evaluate(async () => {
    let read = false;
    await onMineRecorded({ size: 61 * 1024 * 1024, arrayBuffer() { read = true; return new ArrayBuffer(0); } });
    const bigMsg = document.getElementById("mine-status").textContent;
    const origCtx = window.ctx;
    window.ctx = () => ({ decodeAudioData: async () => ({ duration: 601, sampleRate: 16000, getChannelData: () => new Float32Array(1) }) });
    await onMineRecorded(new Blob([new Uint8Array(10)]));
    const longMsg = document.getElementById("mine-status").textContent;
    window.ctx = origCtx;
    return { read, bigMsg, longMsg };
  });
  ok("[R3-3] 60MB 넘는 파일은 읽지 않고 안내", !r33.read && r33.bigMsg.includes("60MB") && r33.bigMsg.includes("작은 파일"), r33.bigMsg);
  ok("[R3-3] 해독 후 10분 넘는 녹음은 거부", r33.longMsg.includes("10분"), r33.longMsg);

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
  await page.waitForFunction(() => document.getElementById("demo-play").disabled && document.getElementById("demo-status").textContent.includes("아직 시범 녹음이 없어요"));
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
  ok("잘못된 팩은 거부하고 목록 유지", (await sp.textContent("#pack-status")).includes("올바르지 않아요") && (await sp.$$eval("#sentence-select option", (o) => o.length)) === 12);
  await sp.setInputFiles("#pack-file", packPath);
  await sp.waitForSelector("#pack-confirm:not(.hidden)");
  ok("열기 전에 확인을 물음", (await sp.textContent("#pack-confirm-text")).includes("문장 12개, 시범 녹음 2개"));
  await sp.click("#pack-apply");
  await sp.waitForFunction(() => document.getElementById("pack-status").textContent.includes("열었어요"));
  await sp.selectOption("#sentence-select", String(11));
  await sp.waitForFunction(() => !document.getElementById("demo-play").disabled, null, { timeout: 15000 });
  ok("수강생 쪽에 고친 문장과 시범이 그대로", (await sp.textContent("#sentence-text")) === "고친 문장입니다. 끝까지 또렷하게.");
  await sp.setInputFiles("#mine-file", same);
  await sp.waitForFunction(() => !document.getElementById("result").classList.contains("hidden"), null, { timeout: 15000 });
  ok("수강생이 따라 읽기 비교까지 됨", (await sp.textContent("#score")).trim() === "100점");

  // ---- 팩 가져오기: 거부·경쟁·실패 복구 (같은 수강생 화면에서) ----
  const mkPack = (name, body) => { const f = path.join(dir, name); fs.writeFileSync(f, JSON.stringify({ format: "reading-coach-pack", version: 1, made: "t", ...body })); return f; };
  const status = () => sp.textContent("#pack-status");
  const reject = async (name, body, needle) => {
    await sp.setInputFiles("#pack-file", mkPack(name, body));
    await sp.waitForFunction((n) => document.getElementById("pack-status").textContent.includes(n), needle, { timeout: 15000 }).catch(() => {});
    return { msg: await status(), confirmShown: await sp.evaluate(() => !document.getElementById("pack-confirm").classList.contains("hidden")) };
  };
  const real = pack.demos["0"];
  const s1 = [{ id: 0, text: "새 팩 첫 문장이에요." }, { id: 5, text: "둘째 문장이에요." }];
  // R6-3: 빈 녹음·가짜 오디오는 바꾸기 전에 거부
  let r = await reject("fake.json", { sentences: s1, demos: { 0: { type: "audio/wav", base64: Buffer.from("hello world").toString("base64") } } }, "쓸 수 없어요");
  ok("[R6-3] 오디오가 아닌 녹음이 든 팩은 교체 전에 거부", r.msg.includes("1번 문장의 시범 녹음을 쓸 수 없어요") && !r.confirmShown, r.msg);
  r = await reject("empty.json", { sentences: s1, demos: { 0: { type: "audio/wav", base64: "" } } }, "올바르지 않아요");
  ok("[R6-3] 빈 녹음이 든 팩은 거부", r.msg.includes("올바르지 않아요") && !r.confirmShown, r.msg);
  // R6-4: 위험한 정수·중복 열쇠
  r = await reject("bigid.json", { sentences: [{ id: 9007199254740992, text: "큰 번호" }], demos: {} }, "올바르지 않아요");
  ok("[R6-4] 안전하지 않은 큰 id는 거부", r.msg.includes("문장 목록이 올바르지 않아요") && !r.confirmShown, r.msg);
  r = await reject("dupkey.json", { sentences: s1, demos: { 0: real, "00": real } }, "올바르지 않아요");
  ok("[R6-4] 녹음 열쇠 \"0\"과 \"00\"이 함께 있으면 거부", r.msg.includes("녹음 정보가 올바르지 않아요") && !r.confirmShown, r.msg);
  ok("[R6-4] validSentences: 안전 범위 밖·음수·소수 id 거부", await sp.evaluate(() => [9007199254740992, 2 ** 31 * 1000, -1, 1.5].every((id) => !validSentences([{ id, text: "a" }])) && validSentences([{ id: 0, text: "a" }])));
  // R6-5: 앞서 고른 큰 파일이 늦게 읽혀도 마지막으로 고른 팩이 남는다
  await sp.evaluate(() => { const o = File.prototype.text; File.prototype.text = function () { const p = o.call(this); return this.name === "slowA.json" ? new Promise((res) => setTimeout(() => p.then(res), 700)) : p; }; });
  const s3 = [{ id: 0, text: "가" }, { id: 1, text: "나" }, { id: 2, text: "다" }];
  const slowA = mkPack("slowA.json", { sentences: s1, demos: {} }), fastB = mkPack("fastB.json", { sentences: s3, demos: {} });
  await sp.setInputFiles("#pack-file", slowA);
  await sp.setInputFiles("#pack-file", fastB);
  await sp.waitForSelector("#pack-confirm:not(.hidden)");
  await sp.waitForTimeout(1200);
  ok("[R6-5] 늦게 끝난 앞 팩이 마지막으로 고른 팩을 덮지 않음", (await sp.textContent("#pack-confirm-text")).includes("문장 3개") && await sp.evaluate(() => pendingPack.sentences.length === 3));
  await sp.click("#pack-cancel");
  // R6-1: 교체 중간에 실패하면 문장·시범이 그대로
  const before = await sp.evaluate(() => localStorage.getItem("reading-coach-sentences"));
  const snap = () => sp.evaluate(async () => ({
    n: document.querySelectorAll("#sentence-select option").length,
    ls: localStorage.getItem("reading-coach-sentences"),
    keys: await dbDo("readonly", (st) => st.getAllKeys()),
    d12: !!(await getDemo(12)), d5: !!(await getDemo(5)),
  }));
  const base = await snap();
  const packB = mkPack("packB.json", { sentences: s1, demos: { 0: real } });
  const breakers = {
    "새 녹음 저장 실패": () => { const o = window.stageDemos; window.stageDemos = () => Promise.reject(new Error("x")); window.__undo = () => { window.stageDemos = o; }; },
    "문장 목록 저장 실패": () => { const o = Storage.prototype.setItem; Storage.prototype.setItem = function () { throw new Error("quota"); }; window.__undo = () => { Storage.prototype.setItem = o; }; },
    "녹음 교체 실패": () => { const o = window.commitDemos; window.commitDemos = () => Promise.reject(new Error("x")); window.__undo = () => { window.commitDemos = o; }; },
  };
  for (const [name, brk] of Object.entries(breakers)) {
    await sp.setInputFiles("#pack-file", packB);
    await sp.waitForSelector("#pack-confirm:not(.hidden)");
    await sp.evaluate(brk);
    await sp.click("#pack-apply");
    await sp.waitForFunction(() => document.getElementById("pack-status").textContent.includes("그대로예요"), null, { timeout: 15000 });
    await sp.evaluate(() => window.__undo());
    const now = await snap();
    ok(`[R6-1] ${name} 때 문장·시범이 원래대로`, now.n === base.n && now.ls === base.ls && now.d12 && !now.d5 && JSON.stringify(now.keys) === JSON.stringify(base.keys), (await status()).slice(0, 50));
  }
  ok("[R6-1] 실패 때 localStorage 문장 목록이 그대로", before === (await snap()).ls);
  await sp.setInputFiles("#pack-file", packB);
  await sp.waitForSelector("#pack-confirm:not(.hidden)");
  await sp.click("#pack-apply");
  await sp.waitForFunction(() => document.getElementById("pack-status").textContent.includes("열었어요"), null, { timeout: 15000 });
  const done = await snap();
  ok("[R6-1] 정상 교체: 문장 2개, 옛 시범 삭제, 새 시범만, 임시 열쇠 없음", done.n === 2 && !done.d12 && JSON.stringify(done.keys) === "[0]", JSON.stringify(done.keys));
  // R6-8: 같은 번호의 다른 문장에 옛 기록이 붙지 않는다
  await sp.evaluate(() => { localStorage.setItem("reading-coach-history", JSON.stringify([{ date: "2026. 1. 1.", sentence: 0, text: "옛 팩의 첫 문장", score: 80, speed: "100%", checks: 1 }])); renderHistory(); });
  const hist2 = await sp.textContent("#history");
  ok("[R6-8] 다른 팩이 같은 번호를 써도 옛 기록은 당시 문장으로 표시", hist2.includes("지난 문장: 옛 팩의 첫 문장") && !hist2.includes("1번"), hist2.slice(0, 60));
  await student.close();

  // ---- R6-2: 되돌리기·새 문장에 옛 시범이 붙지 않음 (선생님 화면) ----
  await page.click("#sentence-reset");
  await page.waitForFunction(() => document.querySelectorAll("#sentence-select option").length === 12 && document.getElementById("teacher-status").textContent.includes("되돌렸어요"), null, { timeout: 15000 });
  await page.fill("#sentence-new", "되돌린 뒤에 새로 넣은 문장이에요.");
  await page.click("#sentence-add");
  await page.waitForFunction(() => document.querySelectorAll("#sentence-select option").length === 13, null, { timeout: 15000 });
  const reuse = await page.evaluate(async () => ({ id: sentences[sentences.length - 1].id, d12: !!(await getDemo(12)), dNew: !!(await getDemo(sentences[sentences.length - 1].id)), d0: !!(await getDemo(0)) }));
  ok("[R6-2] 되돌린 뒤 새 문장은 옛 id(12)를 재사용하지 않고 옛 시범도 안 붙음", reuse.id === 13 && !reuse.d12 && !reuse.dNew, JSON.stringify(reuse));
  ok("[R6-2] 본문이 그대로인 처음 문장(1번)의 시범은 이어짐", reuse.d0);
  ok("페이지 오류 없음", errors.length === 0, errors.join("; "));
  await browser.close();
  fs.rmSync(dir, { recursive: true, force: true });
  const fail = results.filter((x) => !x).length;
  console.log(fail ? `\n실패 ${fail}건` : `\n전부 통과 (${results.length}건)`);
  process.exitCode = fail ? 1 : 0;
})().catch((e) => { console.error(e); process.exitCode = 1; });
