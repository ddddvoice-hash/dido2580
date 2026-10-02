// check.js 테스트. 합성 WAV를 임시 폴더에 만들고, 끝나면 지운다.
// 실행: node apps/voice-check/test.js
"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");
const { inspect } = require("./check.js");

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
  check("합계 줄이 나옴", /합계: 검사 14개/.test(all.stdout), all.stdout);
  const clean = run([path.join(dir, "001_base_take01.wav")]);
  check("통과 파일만 검사하면 종료 코드 0", clean.status === 0 && clean.stdout.includes("001_base_take01.wav: 통과"), `status=${clean.status}\n${clean.stdout}`);
  const jsonPath = path.join(dir, "out.json");
  const csvPath = path.join(dir, "out.csv");
  run([dir, "--json", jsonPath, "--csv", csvPath]);
  check("json·csv 파일이 만들어짐", fs.existsSync(jsonPath) && fs.existsSync(csvPath) &&
    JSON.parse(fs.readFileSync(jsonPath, "utf8")).results.length === 14, "");
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}

console.log(fail ? `\n실패 ${fail}건` : "\n전부 통과");
process.exitCode = fail ? 1 : 0;
