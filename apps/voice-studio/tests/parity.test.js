// 앱 검사기(wav-check.js)가 팀 검사기(apps/voice-check/check.js)와 같은 판정을 내는지 확인한다.
// 합성 WAV를 임시 폴더에 만들고 끝나면 지운다. 실행: node apps/voice-studio/tests/parity.test.js
"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const cli = require("../../voice-check/check.js");
const app = require("../wav-check.js");

let seed = 7;
const rnd = () => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff - 0.5; };

// parts: {tone, sec, amp} | {room, sec, amp} | {zero, sec}
function build(parts, rate) {
  const total = parts.reduce((s, p) => s + Math.round(p.sec * rate), 0);
  const out = new Float64Array(total);
  let pos = 0;
  for (const p of parts) {
    const n = Math.round(p.sec * rate);
    for (let i = 0; i < n; i++) {
      if (p.tone) out[pos + i] = p.amp * Math.sin(2 * Math.PI * 220 * i / rate);
      else if (p.room) out[pos + i] = p.amp * 2 * rnd();
    }
    pos += n;
  }
  return out;
}

function wav(x, { rate = 48000, bits = 24, channels = 1, float = false, flipSecond = false } = {}) {
  const bps = bits / 8;
  const data = Buffer.alloc(x.length * channels * bps);
  const full = 2 ** (bits - 1);
  let o = 0;
  for (let i = 0; i < x.length; i++) {
    for (let c = 0; c < channels; c++) {
      const s = flipSecond && c === 1 ? -x[i] : x[i];
      if (float) data.writeFloatLE(s, o);
      else {
        let v = Math.round(Math.max(-1, Math.min(0.9999, s)) * full);
        if (v === 0 && s !== 0) v = 1;
        if (bits === 16) data.writeInt16LE(v, o); else data.writeIntLE(v, o, 3);
      }
      o += bps;
    }
  }
  const h = Buffer.alloc(44);
  h.write("RIFF", 0); h.writeUInt32LE(36 + data.length, 4); h.write("WAVE", 8);
  h.write("fmt ", 12); h.writeUInt32LE(16, 16); h.writeUInt16LE(float ? 3 : 1, 20); h.writeUInt16LE(channels, 22);
  h.writeUInt32LE(rate, 24); h.writeUInt32LE(rate * channels * bps, 28); h.writeUInt16LE(channels * bps, 32);
  h.writeUInt16LE(bits, 34); h.write("data", 36); h.writeUInt32LE(data.length, 40);
  return Buffer.concat([h, data]);
}

const Q = { room: true, amp: 0.00003 };
const good = (tail = 0.6, amp = 0.6) => [{ ...Q, sec: 10.5 }, { tone: true, amp, sec: 3 }, { ...Q, sec: tail }];

const cases = [
  ["001_welcome_take01.wav", good(), {}, [], []],
  ["002_adventure_start_take01.wav", good(0.6, 0.95), {}, ["V02"], ["PEAK"]],
  ["003_room_created_take01.wav", [{ ...Q, sec: 10.5 }, { tone: true, amp: 0.6, sec: 1.5 }, { zero: true, sec: 0.3 }, { tone: true, amp: 0.6, sec: 1.5 }, { ...Q, sec: 0.6 }], {}, ["V08"], []],
  ["004_player_joined_take01.wav", [{ ...Q, sec: 2 }, { tone: true, amp: 0.6, sec: 3 }, { ...Q, sec: 0.6 }], {}, [], ["ROOM"]],
  ["005_x_take01.wav", good(), { rate: 44100 }, [], ["FORMAT"]],
  ["006_x_take01.wav", good(1.6), {}, ["V05"], []],
  ["007_x_take01.wav", good(0.1), {}, ["V05"], []],
  ["008_x_take01.wav", good(), { bits: 16, channels: 2, flipSecond: true }, [], ["FORMAT"]],
  ["009_x_take01.wav", good(), { float: true, bits: 32 }, [], ["FORMAT"]],
  ["녹음 1.wav", good(0.6, 0.2), {}, [], ["NAME", "PEAK"]],
  ["010_x_take01.wav", [{ ...Q, sec: 11 }], {}, [], ["NOSPEECH"]],
];

const dir = fs.mkdtempSync(path.join(os.tmpdir(), "voice-studio-parity-"));
let fail = 0;
const close = (a, b) => (a === b) || (Number.isFinite(a) && Number.isFinite(b) && Math.abs(a - b) < 1e-9);
try {
  for (const [name, parts, opt, wantReject, wantWarn] of cases) {
    const buf = wav(build(parts, opt.rate || 48000), opt);
    const file = path.join(dir, name);
    fs.writeFileSync(file, buf);
    const a = cli.inspect(file);
    const b = app.inspectBuffer(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.length), name);
    const problems = [];
    for (const k of ["status", "format", "zeroRuns"]) if (a[k] !== b[k]) problems.push(`${k}: ${a[k]} ≠ ${b[k]}`);
    for (const k of ["reject", "warn"]) if (a[k].join() !== b[k].join()) problems.push(`${k}: ${a[k]} ≠ ${b[k]}`);
    for (const k of ["duration", "peakDb", "speechStart", "tail", "roomDb", "zeroPct"]) if (!close(a[k], b[k])) problems.push(`${k}: ${a[k]} ≠ ${b[k]}`);
    for (const c of wantReject) if (!b.reject.includes(c)) problems.push(`반려 ${c} 기대`);
    if (!wantReject.length && b.reject.length) problems.push(`반려 없음 기대, 실제 ${b.reject}`);
    for (const c of wantWarn) if (!b.warn.includes(c)) problems.push(`경고 ${c} 기대`);
    if (problems.length) { fail++; console.log(`FAIL ${name}: ${problems.join(" | ")}`); }
    else console.log(`PASS ${name}: ${b.status} ${b.reject.join(",")} ${b.warn.join(",")}`);
  }
  // 검사 결과 CSV 열이 팀 검사기와 같은지
  const head = (s) => s.replace(/^﻿/, "").split("\r\n")[0];
  if (head(app.toCsv([])) !== head(cli.toCsv([]))) { fail++; console.log("FAIL CSV 열이 다릅니다"); } else console.log("PASS CSV 열 같음");
  // 잘못된 파일은 읽기 실패(예외)
  try { app.inspectBuffer(new Uint8Array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]).buffer, "x.wav"); fail++; console.log("FAIL 잘못된 헤더가 통과함"); }
  catch (e) { console.log("PASS 잘못된 헤더 → " + e.message); }
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}
console.log(fail ? `\n실패 ${fail}건` : "\n전부 통과");
process.exitCode = fail ? 1 : 0;
