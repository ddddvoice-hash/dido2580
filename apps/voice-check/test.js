// check.js 테스트. 합성 WAV를 임시 폴더에 만들고, 끝나면 지운다.
// 실행: node apps/voice-check/test.js
"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");
const { inspect, toCsv, csvCell } = require("./check.js");

const RATE = 48000;
let seed = 12345;
const rnd = () => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff - 0.5; };

// 조각 목록으로 샘플(-1~1) 만들기. {tone, sec, amp} / {room, sec, amp} / {zero, sec}
function build(parts) {
  const total = parts.reduce((s, p) => s + Math.round(p.sec * RATE), 0);
  const out = new Float64Array(total);
  let pos = 0;
  for (const p of parts) {
    const n = Math.round(p.sec * RATE);
    for (let i = 0; i < n; i++) {
      if (p.tone) out[pos + i] = p.amp * Math.sin(2 * Math.PI * 220 * i / RATE);
      else if (p.room) out[pos + i] = p.amp * 2 * rnd();       // 잡음 (완전 0 없음: 아래에서 0은 1LSB로 바꿈)
    }
    pos += n;
  }
  return out;
}

// 샘플 -> WAV 파일. bits: 16/24, channels: 1/2
function writeWav(file, x, bits, channels) {
  const bps = bits / 8;
  const data = Buffer.alloc(x.length * channels * bps);
  const full = 2 ** (bits - 1);
  let o = 0;
  for (let i = 0; i < x.length; i++) {
    let v = Math.round(Math.max(-1, Math.min(0.9999, x[i])) * full);
    if (v === 0 && x[i] !== 0) v = 1; // 잡음이 우연히 0이 되지 않게
    for (let c = 0; c < channels; c++) {
      if (bits === 16) data.writeInt16LE(v, o); else data.writeIntLE(v, o, 3);
      o += bps;
    }
  }
  const h = Buffer.alloc(44);
  h.write("RIFF", 0); h.writeUInt32LE(36 + data.length, 4); h.write("WAVE", 8);
  h.write("fmt ", 12); h.writeUInt32LE(16, 16); h.writeUInt16LE(1, 20); h.writeUInt16LE(channels, 22);
  h.writeUInt32LE(RATE, 24); h.writeUInt32LE(RATE * channels * bps, 28); h.writeUInt16LE(channels * bps, 32);
  h.writeUInt16LE(bits, 34); h.write("data", 36); h.writeUInt32LE(data.length, 40);
  fs.writeFileSync(file, Buffer.concat([h, data]));
}

const ROOM_QUIET = { room: true, amp: 0.00003 };   // 약 -96 dBFS
const GOOD = (tail, amp = 0.6) => [
  { ...ROOM_QUIET, sec: 10.5 }, { tone: true, amp, sec: 6 }, { ...ROOM_QUIET, sec: tail },
];

const dir = fs.mkdtempSync(path.join(os.tmpdir(), "voice-check-test-"));
const cases = [
  // [파일 이름, 조각, bits, 채널, 반려 기대, 경고 기대(들어 있어야 함), 경고 금지]
  ["001_base_take01.wav", GOOD(0.6), 24, 1, [], [], ["NAME", "FORMAT", "PEAK", "ROOM", "NOISE"]],
  ["002_clip_take01.wav", GOOD(0.6, 0.95), 24, 1, ["V02"], ["PEAK"], ["V05"]],
  ["003_short_take01.wav", GOOD(0.1), 24, 1, ["V05"], [], ["V02", "V08"]],
  ["004_long_take01.wav", GOOD(1.6), 24, 1, ["V05"], [], ["V02", "V08"]],
  ["005_zero_take01.wav", [
    { ...ROOM_QUIET, sec: 5 }, { zero: true, sec: 0.5 }, { ...ROOM_QUIET, sec: 5 },
    { tone: true, amp: 0.6, sec: 6 }, { ...ROOM_QUIET, sec: 0.6 }], 24, 1, ["V08"], [], ["V02", "V05"]],
  ["006_room_take01.wav", [
    { ...ROOM_QUIET, sec: 4 }, { tone: true, amp: 0.6, sec: 6 }, { ...ROOM_QUIET, sec: 6 },
    { tone: true, amp: 0.6, sec: 3 }, { ...ROOM_QUIET, sec: 0.6 }], 24, 1, [], ["ROOM"], ["V05"]],
  ["007_noise_take01.wav", [
    { room: true, amp: 0.004, sec: 10.5 }, { tone: true, amp: 0.6, sec: 6 }, { room: true, amp: 0.004, sec: 0.6 }],
    24, 1, [], ["NOISE"], ["ROOM"]],
  ["010_tail03_take01.wav", GOOD(0.3), 24, 1, [], ["TAIL_EDGE"], ["V05"]],
  ["011_tail10_take01.wav", GOOD(1.0), 24, 1, [], ["TAIL_EDGE"], ["V05"]],
  ["012_tail102_take01.wav", GOOD(1.02), 24, 1, ["V05"], [], []],
  ["bad name.wav", GOOD(0.6), 24, 1, [], ["NAME"], ["FORMAT"]],
  ["008_my_turn_01_take01.wav", GOOD(0.6), 24, 1, [], [], ["NAME"]],
  ["019_dice_face_1_take02.wav", GOOD(0.6), 24, 1, [], [], ["NAME"]],
  ["my_turn_01_take01.wav", GOOD(0.6), 24, 1, [], ["NAME"], []],
  ["001_welcome_take1.wav", GOOD(0.6), 24, 1, [], ["NAME"], []],
  ["city dominion.wav", GOOD(0.6), 24, 1, [], ["NAME"], []],
  ["009_stereo_take01.wav", GOOD(0.6), 16, 2, [], ["FORMAT"], ["NAME", "V02"]],
];

let fail = 0;
const check = (label, cond, extra) => {
  console.log(`${cond ? "통과" : "실패"}  ${label}${cond ? "" : "  " + extra}`);
  if (!cond) fail++;
};

try {
  for (const [name, parts, bits, ch, rej, warn, notWarn] of cases) {
    const file = path.join(dir, name);
    writeWav(file, build(parts), bits, ch);
    const r = inspect(file);
    const info = `reject=[${r.reject}] warn=[${r.warn}] peak=${r.peakDb.toFixed(1)} tail=${r.tail && r.tail.toFixed(2)} start=${r.speechStart} zero=${r.zeroRuns} room=${r.roomDb.toFixed(1)}`;
    check(`${name} 반려 코드 [${rej}]`, r.reject.join() === rej.join(), info);
    for (const w of warn) check(`${name} 경고 ${w} 있음`, r.warn.includes(w), info);
    for (const w of notWarn) check(`${name} 경고/코드 ${w} 없음`, !r.warn.includes(w) && !r.reject.includes(w), info);
    if (name.startsWith("005")) check("005 완전0 구간 1개", r.zeroRuns === 1, info);
    if (name.startsWith("001")) check("001 형식 48000Hz/24bit/모노", r.format === "48000Hz/24bit/모노", r.format);
    if (name.startsWith("009")) check("009 스테레오 16bit로 읽힘", r.format === "48000Hz/16bit/스테레오" && Math.abs(r.duration - 17.1) < 0.01, r.format + " " + r.duration);
  }

  // WAV 아님은 건너뛰고, 종료 코드를 확인한다.
  fs.writeFileSync(path.join(dir, "memo.mp3"), "not wav");
  const script = path.join(__dirname, "check.js");
  const run = (args) => spawnSync(process.execPath, [script, ...args], { encoding: "utf8" });
  const all = run([dir]);
  check("폴더 검사: 반려가 있으면 종료 코드 1", all.status === 1, `status=${all.status}`);
  check("mp3는 'WAV 아님'으로 건너뜀", all.stdout.includes("memo.mp3: WAV 아님"), all.stdout);
  check("합계 줄이 나옴", /합계: 검사 17개/.test(all.stdout), all.stdout);
  const clean = run([path.join(dir, "001_base_take01.wav")]);
  check("통과 파일만 검사하면 종료 코드 0", clean.status === 0 && clean.stdout.includes("001_base_take01.wav: 통과"), `status=${clean.status}\n${clean.stdout}`);
  const jsonPath = path.join(dir, "out.json");
  const csvPath = path.join(dir, "out.csv");
  run([dir, "--json", jsonPath, "--csv", csvPath]);
  check("json·csv 파일이 만들어짐", fs.existsSync(jsonPath) && fs.existsSync(csvPath) &&
    JSON.parse(fs.readFileSync(jsonPath, "utf8")).results.length === 17, "");

  // ---- 지적 반영 테스트: 임의 헤더·채널·샘플레이트 ----
  // opt: rate, bits(16/24), float, ext(true/"badguid"), blockAlign, sizeDelta, tag, rateField
  function raw(file, chans, opt = {}) {
    const rate = opt.rate || RATE, bits = opt.bits || 24, C = chans.length, bps = bits / 8;
    const frames = chans[0].length;
    const data = Buffer.alloc(frames * C * bps);
    let o = 0;
    for (let i = 0; i < frames; i++) for (let c = 0; c < C; c++) {
      const x = chans[c][i];
      if (opt.float) data.writeFloatLE(x, o);
      else {
        let v = Math.round(Math.max(-1, Math.min(0.9999, x)) * 2 ** (bits - 1));
        if (v === 0 && x !== 0) v = 1;
        if (bits === 16) data.writeInt16LE(v, o); else data.writeIntLE(v, o, 3);
      }
      o += bps;
    }
    const fmtLen = opt.ext ? 40 : 16;
    const h = Buffer.alloc(20 + fmtLen + 8);
    h.write(opt.tag || "RIFF", 0); h.writeUInt32LE(h.length - 8 + data.length, 4); h.write("WAVE", 8);
    h.write("fmt ", 12); h.writeUInt32LE(fmtLen, 16);
    h.writeUInt16LE(opt.ext ? 0xfffe : opt.float ? 3 : 1, 20); h.writeUInt16LE(C, 22);
    h.writeUInt32LE(opt.rateField !== undefined ? opt.rateField : rate, 24); h.writeUInt32LE(rate * C * bps, 28);
    h.writeUInt16LE(opt.blockAlign || C * bps, 32); h.writeUInt16LE(bits, 34);
    if (opt.ext) {
      h.writeUInt16LE(22, 36); h.writeUInt16LE(bits, 38); h.writeUInt32LE(C === 2 ? 3 : 4, 40);
      h.writeUInt16LE(opt.float ? 3 : 1, 44);
      Buffer.from([0, 0, 0, 0, 0x10, 0, 0x80, 0, 0, 0xaa, 0, 0x38, 0x9b, 0x71]).copy(h, 46);
      if (opt.ext === "badguid") h[50] = 0x11;
    }
    const dh = 20 + fmtLen;
    h.write("data", dh); h.writeUInt32LE(data.length + (opt.sizeDelta || 0), dh + 4);
    fs.writeFileSync(file, Buffer.concat([h, data]));
  }
  // 0이 아닌 잡음 샘플 n개. zeroAt/zeroLen이 있으면 그 자리를 완전 0으로.
  function noise(n, amp = 0.001, zeroAt = -1, zeroLen = 0) {
    const x = new Float64Array(n);
    for (let i = 0; i < n; i++) x[i] = (zeroAt >= 0 && i >= zeroAt && i < zeroAt + zeroLen) ? 0 : amp * (0.2 + Math.abs(rnd()));
    return x;
  }
  const tryInspect = (name, chans, opt) => {
    const f = path.join(dir, name);
    raw(f, chans, opt);
    try { return { r: inspect(f) }; } catch (e) { return { err: e.message }; }
  };

  // V08: 480샘플 고정 (샘플레이트와 상관없음)
  for (const [rate, run, want] of [[48000, 479, false], [48000, 480, true], [96000, 479, false], [96000, 480, true], [16000, 480, true], [16000, 479, false]]) {
    const { r } = tryInspect(`v08_${rate}_${run}.wav`, [noise(rate * 2, 0.001, 1000, run)], { rate });
    check(`V08 ${rate}Hz 완전0 ${run}샘플 -> ${want ? "반려" : "통과"}`, r.reject.includes("V08") === want, JSON.stringify(r.reject));
  }
  check("V08: 96kHz 480샘플 구간 1개로 셈", tryInspect("v08_count.wav", [noise(192000, 0.001, 500, 480)], { rate: 96000 }).r.zeroRuns === 1, "");

  // 스테레오: 채널별로 판정
  {
    const L = noise(96000, 0.001, 2000, 600), R = noise(96000, 0.001);
    check("스테레오: 한 채널에만 480샘플 0 -> V08", tryInspect("st_zero.wav", [L, R], {}).r.reject.includes("V08"), "");
    const L2 = noise(96000, 0.001).map((v, i) => (i < 48000 ? 0.95 : v)), R2 = noise(96000, 0.001);
    const rr = tryInspect("st_peak.wav", [L2, R2], {}).r;
    check("스테레오: 왼쪽 0.95, 오른쪽 작음 -> V02", rr.reject.includes("V02"), JSON.stringify(rr.reject));
    const tone = new Float64Array(RATE * 4).map((_, i) => (i < RATE ? 0.00003 * (1 + (i % 7)) : 0.3 * Math.sin(2 * Math.PI * 220 * i / RATE)));
    const inv = tone.map((v) => -v);
    const so = tryInspect("st_opposite.wav", [tone, inv], {}).r;
    check("스테레오: 반대 부호 두 채널 -> V08 없음, 말소리 찾음", !so.reject.includes("V08") && so.speechStart !== null, JSON.stringify(so.reject) + so.speechStart);
  }

  // 헤더·값 검증
  {
    const nanCh = new Float64Array(48000).fill(0.01); nanCh[100] = NaN;
    const e1 = tryInspect("nan.wav", [nanCh], { float: true, bits: 32 });
    check("NaN 샘플 -> 읽기 실패", e1.err && /NaN/.test(e1.err), JSON.stringify(e1));
    nanCh[100] = Infinity;
    check("Infinity 샘플 -> 읽기 실패", tryInspect("inf.wav", [nanCh], { float: true, bits: 32 }).err !== undefined, "");
    const e2 = tryInspect("rate0.wav", [noise(48000)], { rateField: 0 });
    check("0Hz 헤더 -> 읽기 실패", e2.err && /0Hz/.test(e2.err), JSON.stringify(e2));
    const e3 = tryInspect("align.wav", [noise(48000)], { blockAlign: 4 });
    check("블록 크기 불일치 -> 읽기 실패", e3.err && /블록/.test(e3.err), JSON.stringify(e3));
    const e4 = tryInspect("rf64.wav", [noise(48000)], { tag: "RF64" });
    check("RF64 -> 지원하지 않음(읽기 실패)", e4.err && /RF64/.test(e4.err), JSON.stringify(e4));
    const e5 = tryInspect("ext_ok.wav", [noise(48000)], { ext: true });
    check("EXTENSIBLE(PCM GUID) 정상 읽힘", e5.r && e5.r.format === "48000Hz/24bit/모노", JSON.stringify(e5));
    const e6 = tryInspect("ext_bad.wav", [noise(48000)], { ext: "badguid" });
    check("EXTENSIBLE GUID 틀림 -> 읽기 실패", e6.err && /GUID/.test(e6.err), JSON.stringify(e6));
    const e7 = tryInspect("trunc.wav", [noise(48000)], { sizeDelta: 300 });
    check("data 선언 크기가 실제보다 큼 -> TRUNC 경고", e7.r && e7.r.warn.includes("TRUNC"), JSON.stringify(e7));
    const e8 = tryInspect("float_ok.wav", [noise(48000)], { float: true, bits: 32 });
    check("float32 정상 읽힘 + FORMAT 경고, TRUNC 없음", e8.r && e8.r.warn.includes("FORMAT") && !e8.r.warn.includes("TRUNC"), JSON.stringify(e8));
  }

  // CSV: error 열, BOM, CR 인용
  {
    fs.writeFileSync(path.join(dir, "garbage.wav"), "this is not a wav file at all");
    const csvP = path.join(dir, "e.csv");
    run([path.join(dir, "garbage.wav"), path.join(dir, "001_base_take01.wav"), "--csv", csvP]);
    const buf = fs.readFileSync(csvP);
    check("CSV: UTF-8 BOM", buf[0] === 0xef && buf[1] === 0xbb && buf[2] === 0xbf, "");
    const rows = buf.toString("utf8").replace(/^﻿/, "").split("\r\n");
    const cols = rows[0].split(",");
    check("CSV: 마지막 열 이름이 error", cols[cols.length - 1] === "error" && cols[cols.length - 2] === "zero_pct_nonspeech", rows[0]);
    const bad = rows.find((x) => x.includes("garbage.wav")).split(",");
    check("CSV: 읽기 실패 행은 error 열에 메시지, zero_pct 열은 비움", bad.length === cols.length && bad[11] === "" && /WAV 헤더/.test(bad[12]) && bad[1] === "읽기 실패", rows.join("|"));
    const good = rows.find((x) => x.includes("001_base_take01.wav")).split(",");
    check("CSV: 성공 행은 error 열이 비고 zero_pct가 숫자", good.length === cols.length && good[12] === "" && !isNaN(parseFloat(good[11])), rows.join("|"));
    check("읽기 실패만 있어도 종료 코드 2", run([path.join(dir, "garbage.wav")]).status === 2, "");
    check("CSV 인용: 단독 CR", csvCell("bad\rheader") === '"bad\rheader"' && csvCell("a,b") === '"a,b"' && csvCell("ok") === "ok", "");
    check("toCsv 한 행이 CR로 깨지지 않음", toCsv([{ file: "x", error: "bad\rheader" }]).split("\r\n").length === 3, "");
  }

  // 저장 실패 -> 종료 코드 2 (반려가 있어도)
  {
    const nodir = path.join(dir, "없는폴더", "out.csv");
    const p = run([path.join(dir, "001_base_take01.wav"), "--csv", nodir]);
    check("CSV 저장 실패 -> 종료 코드 2, 경로 출력", p.status === 2 && p.stderr.includes("저장 실패") && p.stderr.includes("out.csv"), `status=${p.status} ${p.stderr}`);
    const p2 = run([path.join(dir, "002_clip_take01.wav"), "--json", path.join(dir, "없는폴더", "o.json")]);
    check("반려 파일 + 저장 실패 -> 종료 코드 2", p2.status === 2, `status=${p2.status}`);
  }
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}

console.log(fail ? `\n실패 ${fail}건` : "\n전부 통과");
process.exitCode = fail ? 1 : 0;
