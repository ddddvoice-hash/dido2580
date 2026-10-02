// 화면 검사: 헤드리스 Chromium(Playwright)으로 앱을 열어 키보드 조작, 파일 올리기, 판정 표시, 저장, CSV를 확인한다.
// 실행: node apps/voice-studio/tests/browser.test.js [스크린샷 폴더]
// Playwright가 필요하다 (npm i -g playwright). 합성 WAV는 임시 폴더에 만들고 지운다.
"use strict";
const fs = require("fs");
const os = require("os");
const path = require("path");
const { chromium } = require("playwright");

const APP = "file://" + path.resolve(__dirname, "../index.html");
const shots = process.argv[2];
const results = [];
const ok = (name, pass, detail = "") => { results.push(pass); console.log(`${pass ? "PASS" : "FAIL"} ${name}${detail ? " — " + detail : ""}`); };

let seed = 11;
const rnd = () => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff - 0.5; };
function wav(parts, { rate = 48000, bits = 24 } = {}) {
  const total = parts.reduce((s, p) => s + Math.round(p.sec * rate), 0);
  const bps = bits / 8, data = Buffer.alloc(total * bps), full = 2 ** (bits - 1);
  let pos = 0;
  for (const p of parts) {
    const n = Math.round(p.sec * rate);
    for (let i = 0; i < n; i++) {
      let s = 0;
      if (p.tone) s = p.amp * Math.sin(2 * Math.PI * 220 * i / rate);
      else if (p.room) s = 0.00003 * 2 * rnd();
      let v = Math.round(Math.max(-1, Math.min(0.9999, s)) * full);
      if (v === 0 && !p.zero) v = 1;
      if (bits === 16) data.writeInt16LE(v, (pos + i) * bps); else data.writeIntLE(v, (pos + i) * bps, 3);
    }
    pos += n;
  }
  const h = Buffer.alloc(44);
  h.write("RIFF", 0); h.writeUInt32LE(36 + data.length, 4); h.write("WAVE", 8); h.write("fmt ", 12);
  h.writeUInt32LE(16, 16); h.writeUInt16LE(1, 20); h.writeUInt16LE(1, 22); h.writeUInt32LE(rate, 24);
  h.writeUInt32LE(rate * bps, 28); h.writeUInt16LE(bps, 32); h.writeUInt16LE(bits, 34); h.write("data", 36); h.writeUInt32LE(data.length, 40);
  return Buffer.concat([h, data]);
}
const R = (sec) => ({ room: true, sec });
const T = (sec, amp = 0.5) => ({ tone: true, sec, amp });

(async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "voice-studio-ui-"));
  const files = {
    "002_adventure_start_take01.wav": wav([R(10.5), T(2.5), R(0.6)]),            // 통과
    "003_room_created_take01.wav": wav([R(10.5), T(2.5, 0.97), R(0.6)]),          // V02
    "004_player_joined_take01.wav": wav([R(10.5), T(1.2), { zero: true, sec: 0.2 }, T(1.2), R(0.6)]), // V08
    "005_x_take01.wav": wav([R(2), T(2.5), R(1.8)]),                               // V05 + ROOM
    "006_x_take01.wav": wav([R(10.5), T(2.5), R(0.6)], { rate: 44100 }),          // FORMAT 경고만
    "base_001_take01.wav": wav([R(10.5), T(2.5), R(0.6)]),                         // 줄 번호 없음
    "notes.txt": Buffer.from("x"),
  };
  for (const [n, b] of Object.entries(files)) fs.writeFileSync(path.join(dir, n), b);

  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, acceptDownloads: true });
  const page = await ctx.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => { if (m.type() === "error" && !/Failed to load resource/.test(m.text())) errors.push(m.text()); });
  await page.goto(APP);
  await page.waitForSelector("#row95");

  ok("대본 96줄 표시", await page.locator("button.row").count() === 96);
  ok("처음 줄 001과 대사", (await page.textContent("#cueText")).includes("시티 도미니언에 온 걸 환영해"));
  ok("예시 테이크가 보이고 진행률에는 안 셈", await page.locator(".pill.example").count() === 1 && await page.textContent("#doneCount") === "0");
  ok("예시 파형이 그려짐", await page.locator("canvas.wave").count() === 1);

  // 키보드: E, Q, 숫자, W, Esc
  await page.locator("#cue").focus();
  await page.keyboard.press("e");
  ok("E로 다음 줄(002)", await page.textContent("#cueNo") === "002");
  await page.keyboard.press("e"); await page.keyboard.press("q");
  ok("Q로 이전 줄", await page.textContent("#cueNo") === "002");
  await page.keyboard.press("4");
  ok("숫자 4로 감정 세기", await page.isChecked("#lv4"));
  await page.keyboard.press("w");
  ok("W로 시선 칸", await page.evaluate(() => document.activeElement.id) === "f_gaze");
  await page.keyboard.type("화면 속 친구들 쪽");
  await page.keyboard.press("e");
  ok("입력 중 E는 글자로 들어감", (await page.inputValue("#f_gaze")).endsWith("e") && await page.textContent("#cueNo") === "002");
  await page.keyboard.press("Backspace");
  await page.keyboard.press("Escape");
  ok("Esc로 입력 칸에서 나옴", await page.evaluate(() => document.activeElement.id) === "cue");
  ok("다음 파일 이름 안내", await page.textContent("#fname") === "002_adventure_start_take01.wav");

  // 파일 올리기
  await page.setInputFiles("#fileInput", Object.keys(files).map((n) => path.join(dir, n)));
  await page.waitForFunction(() => document.getElementById("doneCount").textContent !== "0");
  const st = await page.evaluate(() => {
    const s = window.__studio.state, pick = (id) => (s.takes[id] || []).map((t) => [t.status, t.reject.join(","), t.warn.join(",")]);
    return { t002: pick("002"), t003: pick("003"), t004: pick("004"), t005: pick("005"), t006: pick("006"), other: s.other.map((t) => t.name) };
  });
  ok("002 정상 → 통과", st.t002[0] && st.t002[0][0] === "통과", JSON.stringify(st.t002));
  ok("003 찢어짐 → V02", st.t003[0] && st.t003[0][1].includes("V02"), JSON.stringify(st.t003));
  ok("004 게이트 → V08", st.t004[0] && st.t004[0][1].includes("V08"), JSON.stringify(st.t004));
  ok("005 룸톤 없음·긴 여백 → V05, ROOM", st.t005[0] && st.t005[0][1].includes("V05") && st.t005[0][2].includes("ROOM"), JSON.stringify(st.t005));
  ok("006 44.1kHz → 통과 + FORMAT 경고", st.t006[0] && st.t006[0][0] === "통과" && st.t006[0][2].includes("FORMAT"), JSON.stringify(st.t006));
  ok("base_001은 줄 번호 없는 파일로", st.other.length === 1 && st.other[0] === "base_001_take01.wav");
  ok("진행률: 통과 2줄, 다시 3줄", await page.textContent("#doneCount") === "2" && (await page.textContent("#retakeLabel")).includes("3"));
  ok("다음 파일 이름이 take02로", await page.textContent("#fname") === "002_adventure_start_take02.wav");
  ok("알림(aria-live)에 결과 요약", (await page.textContent("#live")).includes("WAV가 아니라 건너뜀 1개"));

  await page.locator("#cue").focus();
  await page.keyboard.press("r");
  ok("R로 다음 반려 줄(003)", await page.textContent("#cueNo") === "003");
  ok("반려 코드 설명 표시", (await page.textContent("#takes")).includes("찢어짐"));
  if (shots) { await page.screenshot({ path: path.join(shots, "light.png"), fullPage: false }); }

  // 접근성: 버튼 높이, 포커스 표시
  const small = await page.evaluate(() => [...document.querySelectorAll("button.btn, button.row, .scale label")]
    .filter((b) => b.offsetParent).map((b) => b.getBoundingClientRect().height).filter((h) => h < 47.5).length);
  ok("버튼 높이 48px 이상", small === 0, `작은 것 ${small}개`);
  await page.keyboard.press("Tab");
  const outline = await page.evaluate(() => getComputedStyle(document.activeElement).outlineStyle);
  ok("키보드 포커스 표시", outline !== "none", outline);

  // 저장 유지
  await page.reload(); await page.waitForSelector("#row95");
  await page.click("#row1");
  ok("새로고침 뒤 메모·세기 유지", await page.inputValue("#f_gaze") === "화면 속 친구들 쪽" && await page.isChecked("#lv4"));
  ok("새로고침 뒤 판정 기록 유지, 예시는 다시 안 나옴", await page.textContent("#doneCount") === "2" && await page.locator(".pill.example").count() === 0);

  // CSV
  const dl = page.waitForEvent("download");
  await page.click("#exportNotes");
  const csv = fs.readFileSync(await (await dl).path(), "utf8");
  const lines = csv.split("\r\n");
  ok("메모 CSV: BOM, 주석 표와 같은 머리줄, 96줄", csv.charCodeAt(0) === 0xfeff &&
    lines[0].replace(/^﻿/, "") === fs.readFileSync(path.resolve(__dirname, "../../../voice/city-dominion/annotation.csv"), "utf8").replace(/^﻿/, "").split("\r\n")[0] &&
    lines.filter(Boolean).length === 97);
  ok("메모 CSV에 002 값", lines[2].includes("화면 속 친구들 쪽") && lines[2].includes(",4,"), lines[2]);
  const dl2 = page.waitForEvent("download");
  await page.click("#exportChecks");
  const csv2 = fs.readFileSync(await (await dl2).path(), "utf8").split("\r\n").filter(Boolean);
  ok("검사 결과 CSV 6개 파일", csv2.length === 7 && csv2[0].includes("zero_pct_nonspeech"));

  // 어두운 화면, 휴대폰 폭
  await page.emulateMedia({ colorScheme: "dark" });
  await page.click("#row0");
  const bg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
  ok("어두운 화면 배경", bg === "rgb(16, 22, 42)", bg);
  if (shots) await page.screenshot({ path: path.join(shots, "dark.png") });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.click("#row2");
  const over = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  ok("휴대폰 폭에서 가로 스크롤 없음", over <= 0, `넘침 ${over}px`);
  if (shots) {
    await page.emulateMedia({ colorScheme: "light" });
    await page.screenshot({ path: path.join(shots, "phone.png"), fullPage: true });
  }

  ok("자바스크립트 오류 없음", errors.length === 0, errors.join(" / "));
  await browser.close();
  fs.rmSync(dir, { recursive: true, force: true });
  const fail = results.filter((x) => !x).length;
  console.log(fail ? `\n실패 ${fail}건` : `\n전부 통과 (${results.length}건)`);
  process.exitCode = fail ? 1 : 0;
})().catch((e) => { console.error(e); process.exitCode = 1; });
