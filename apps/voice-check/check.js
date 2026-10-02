#!/usr/bin/env node
// 목소리 원본 녹음 자동 검사기. 외부 패키지 없음.
// 사용: node apps/voice-check/check.js <폴더나 파일...> [--json out.json] [--csv out.csv]
// 반려 코드(V02, V05, V08)가 하나라도 있으면 종료 코드 1, 읽기 실패만 있으면 2, 아니면 0.
"use strict";

const fs = require("fs");
const path = require("path");
const analysis = require("../reading-coach/analysis.js");

const REQUIRED = { rate: 48000, bits: 24, channels: 1 };
const CLIP_DB = -1;          // V02: 최대값이 이 값 이상이면 찢어짐
const PEAK_MIN_DB = -6;      // PEAK 경고 범위
const PEAK_MAX_DB = -3;
const TAIL_MIN = 0.3;        // V05: 뒤 여백(초) 범위
const TAIL_MAX = 1.0;
const ROOM_SEC = 10.0;       // ROOM: 첫 말소리가 이보다 앞이면 경고
const NOISE_DB = -60;        // NOISE: 앞 10초 평균 크기 한계
const ZERO_RUN_MS = 10;      // V08: 완전 0이 이만큼 이어지면 가공 흔적 (48kHz에서 480샘플)
const NAME_RE = /^\d{3}_[a-z0-9_]+_take\d{2}\.wav$/i;
const CHUNK_BYTES = 4 * 1024 * 1024;

const toDb = (x) => (x > 0 ? 20 * Math.log10(x) : -Infinity);

// ---- WAV 읽기 ----------------------------------------------------------

function parseHeader(fd, fileSize) {
  const head = Buffer.alloc(12);
  if (fs.readSync(fd, head, 0, 12, 0) < 12) throw new Error("파일이 너무 짧습니다");
  const tag = head.toString("latin1", 0, 4);
  if ((tag !== "RIFF" && tag !== "RF64") || head.toString("latin1", 8, 12) !== "WAVE") {
    throw new Error("WAV 헤더가 아닙니다");
  }
  let pos = 12;
  let fmt = null;
  const ch = Buffer.alloc(8);
  while (pos + 8 <= fileSize) {
    fs.readSync(fd, ch, 0, 8, pos);
    const id = ch.toString("latin1", 0, 4);
    let size = ch.readUInt32LE(4);
    const body = pos + 8;
    if (id === "fmt ") {
      const b = Buffer.alloc(Math.min(size, 40));
      fs.readSync(fd, b, 0, b.length, body);
      let format = b.readUInt16LE(0);
      if (format === 0xfffe && b.length >= 26) format = b.readUInt16LE(24); // WAVE_FORMAT_EXTENSIBLE
      fmt = {
        format,
        channels: b.readUInt16LE(2),
        rate: b.readUInt32LE(4),
        bits: b.readUInt16LE(14),
      };
    } else if (id === "data") {
      if (!fmt) throw new Error("fmt 청크가 data보다 뒤에 있습니다");
      // 크기가 0이거나 0xFFFFFFFF이거나 파일보다 크면(녹음이 중간에 끊긴 경우) 남은 길이만큼만 읽는다.
      const remain = fileSize - body;
      if (size === 0 || size === 0xffffffff || size > remain) size = remain;
      return { fmt, dataStart: body, dataBytes: size };
    }
    pos = body + size + (size % 2);
  }
  throw new Error("data 청크를 찾지 못했습니다");
}

// 샘플을 Float32Array 하나로 읽는다. 스테레오는 평균.
function readSamples(fd, info) {
  const { fmt } = info;
  const bps = fmt.bits / 8;
  const frameBytes = bps * fmt.channels;
  const frames = Math.floor(info.dataBytes / frameBytes);
  const out = new Float32Array(frames);
  const perChunk = Math.max(1, Math.floor(CHUNK_BYTES / frameBytes));
  const buf = Buffer.alloc(perChunk * frameBytes);
  const isFloat = fmt.format === 3;
  const C = fmt.channels;
  let done = 0;
  while (done < frames) {
    const n = Math.min(perChunk, frames - done);
    const got = fs.readSync(fd, buf, 0, n * frameBytes, info.dataStart + done * frameBytes);
    const gotFrames = Math.floor(got / frameBytes);
    if (gotFrames === 0) break;
    for (let i = 0; i < gotFrames; i++) {
      let sum = 0;
      const base = i * frameBytes;
      for (let c = 0; c < C; c++) {
        const o = base + c * bps;
        let v;
        if (isFloat) v = buf.readFloatLE(o);
        else if (fmt.bits === 16) v = buf.readInt16LE(o) / 32768;
        else if (fmt.bits === 24) v = buf.readIntLE(o, 3) / 8388608;
        else v = buf.readInt32LE(o) / 2147483648;
        sum += v;
      }
      out[done + i] = C === 1 ? sum : sum / C;
    }
    done += gotFrames;
    if (gotFrames < n) break;
  }
  return done < frames ? out.subarray(0, done) : out;
}

// ---- 분석 ---------------------------------------------------------------

function inspect(file) {
  const name = path.basename(file);
  const fd = fs.openSync(file, "r");
  let info, samples;
  try {
    const size = fs.fstatSync(fd).size;
    info = parseHeader(fd, size);
    const f = info.fmt;
    const okPcm = f.format === 1 && [16, 24, 32].includes(f.bits);
    const okFloat = f.format === 3 && f.bits === 32;
    if (!okPcm && !okFloat) throw new Error(`지원하지 않는 형식입니다 (코드 ${f.format}, ${f.bits}bit)`);
    if (f.channels < 1 || f.channels > 2) throw new Error(`채널 ${f.channels}개는 지원하지 않습니다`);
    samples = readSamples(fd, info);
  } finally {
    fs.closeSync(fd);
  }
  const { fmt } = info;
  const rate = fmt.rate;
  const n = samples.length;
  const duration = n / rate;

  // 최대값, 완전 0 구간
  let peak = 0;
  const minRun = Math.max(1, Math.round(rate * ZERO_RUN_MS / 1000));
  const zeroRuns = []; // [start, length]
  let runStart = -1;
  for (let i = 0; i <= n; i++) {
    const v = i < n ? samples[i] : 1;
    if (i < n) {
      const a = v < 0 ? -v : v;
      if (a > peak) peak = a;
    }
    if (v === 0) {
      if (runStart < 0) runStart = i;
    } else if (runStart >= 0) {
      if (i - runStart >= minRun) zeroRuns.push([runStart, i - runStart]);
      runStart = -1;
    }
  }
  const peakDb = toDb(peak);

  // 말소리 구간 (analysis.js 재사용)
  const FR = analysis.FRAME_MS;
  const frameSize = Math.max(1, Math.round(rate * FR / 1000));
  const runs = analysis.speechRuns(analysis.envelope(samples, rate));
  const hasSpeech = runs.length > 0;
  const speechStart = hasSpeech ? runs[0].start * FR / 1000 : null;
  const speechEnd = hasSpeech ? runs[runs.length - 1].end * FR / 1000 : null;
  const tail = hasSpeech ? duration - speechEnd : null;

  // 말소리가 아닌 구간의 완전 0 샘플 비율
  let nonSpeech = 0;
  let nonSpeechZero = 0;
  const countRange = (a, b) => {
    nonSpeech += b - a;
    for (let i = a; i < b; i++) if (samples[i] === 0) nonSpeechZero++;
  };
  let cursor = 0;
  for (const r of runs) {
    countRange(cursor, r.start * frameSize);
    cursor = r.end * frameSize;
  }
  countRange(Math.min(cursor, n), n);
  const zeroPct = nonSpeech ? (nonSpeechZero / nonSpeech) * 100 : 0;

  // 앞 10초 평균 크기(RMS)
  const roomEnd = Math.min(n, Math.round(ROOM_SEC * rate));
  let sq = 0;
  for (let i = 0; i < roomEnd; i++) sq += samples[i] * samples[i];
  const roomDb = roomEnd ? toDb(Math.sqrt(sq / roomEnd)) : -Infinity;

  // 코드 판정
  const reject = [];
  const warn = [];
  if (peakDb >= CLIP_DB) reject.push("V02");
  if (hasSpeech && (tail < TAIL_MIN || tail > TAIL_MAX)) reject.push("V05");
  if (zeroRuns.length > 0) reject.push("V08");

  if (!NAME_RE.test(name)) warn.push("NAME");
  if (fmt.rate !== REQUIRED.rate || fmt.bits !== REQUIRED.bits || fmt.channels !== REQUIRED.channels ||
      fmt.format === 3) warn.push("FORMAT");
  if (peakDb < PEAK_MIN_DB || peakDb > PEAK_MAX_DB) warn.push("PEAK");
  if (!hasSpeech) warn.push("NOSPEECH");
  else if (speechStart < ROOM_SEC) warn.push("ROOM");
  if (roomDb > NOISE_DB) warn.push("NOISE");

  return {
    file, name, status: reject.length ? "반려" : "통과", reject, warn,
    duration, format: formatLabel(fmt), peakDb, speechStart, tail, roomDb,
    zeroRuns: zeroRuns.length, zeroPct,
  };
}

function formatLabel(f) {
  const ch = f.channels === 1 ? "모노" : "스테레오";
  return `${f.rate}Hz/${f.format === 3 ? f.bits + "bit-float" : f.bits + "bit"}/${ch}`;
}

// ---- 파일 찾기 ----------------------------------------------------------

function collect(target, wavs, skipped) {
  const st = fs.statSync(target);
  if (st.isDirectory()) {
    const entries = fs.readdirSync(target).sort();
    for (const e of entries) collect(path.join(target, e), wavs, skipped);
  } else if (/\.wav$/i.test(target)) wavs.push(target);
  else skipped.push(target);
}

// ---- 출력 ---------------------------------------------------------------

const fmtNum = (x, d) => (x === null || x === undefined ? "-" : Number.isFinite(x) ? x.toFixed(d) : "-∞");

function line(r) {
  const verdict = r.reject.length
    ? `반려 ${r.reject.join(",")}${r.warn.length ? ` | 경고 ${r.warn.join(",")}` : ""}`
    : r.warn.length ? `통과 | 경고 ${r.warn.join(",")}` : "통과";
  return `${r.name}: ${verdict}\n    길이 ${fmtNum(r.duration, 1)}초 | ${r.format} | 최대 ${fmtNum(r.peakDb, 1)} dBFS | ` +
    `앞 말소리 시작 ${fmtNum(r.speechStart, 1)}초 | 뒤 여백 ${fmtNum(r.tail, 2)}초 | ` +
    `완전0 구간 ${r.zeroRuns}개 (말소리 밖 완전0 ${fmtNum(r.zeroPct, 2)}%) | 앞 10초 평균 ${fmtNum(r.roomDb, 1)} dBFS`;
}

function csvCell(v) {
  const s = v === null || v === undefined ? "" : String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

function toCsv(results) {
  const cols = ["file", "status", "reject", "warn", "duration_s", "format", "peak_dbfs",
    "speech_start_s", "tail_s", "room_rms_dbfs", "zero_runs", "zero_pct_nonspeech"];
  const rows = results.map((r) => r.error
    ? [r.file, "읽기 실패", "", "", "", "", "", "", "", "", "", r.error]
    : [r.file, r.status, r.reject.join(" "), r.warn.join(" "), r.duration.toFixed(3), r.format,
      fmtNum(r.peakDb, 2), fmtNum(r.speechStart, 2), fmtNum(r.tail, 3), fmtNum(r.roomDb, 2),
      r.zeroRuns, r.zeroPct.toFixed(3)]);
  return "﻿" + [cols, ...rows].map((row) => row.map(csvCell).join(",")).join("\r\n") + "\r\n";
}

function main(argv) {
  const targets = [];
  let jsonOut = null;
  let csvOut = null;
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--json") jsonOut = argv[++i];
    else if (argv[i] === "--csv") csvOut = argv[++i];
    else targets.push(argv[i]);
  }
  if (!targets.length || (argv.includes("--json") && !jsonOut) || (argv.includes("--csv") && !csvOut)) {
    console.error("사용: node apps/voice-check/check.js <폴더나 파일...> [--json out.json] [--csv out.csv]");
    return 2;
  }
  const wavs = [];
  const skipped = [];
  for (const t of targets) {
    try { collect(t, wavs, skipped); } catch (e) { console.error(`열 수 없음: ${t} (${e.message})`); return 2; }
  }

  const results = [];
  for (const f of wavs) {
    let r;
    try { r = inspect(f); } catch (e) { r = { file: f, name: path.basename(f), error: e.message }; }
    results.push(r);
    console.log(r.error ? `${r.name}: 읽기 실패 | ${r.error}` : line(r));
  }
  for (const s of skipped) console.log(`${path.basename(s)}: WAV 아님 (건너뜀)`);

  const ok = results.filter((r) => !r.error);
  const rejected = ok.filter((r) => r.reject.length).length;
  const errors = results.length - ok.length;
  const warned = ok.filter((r) => !r.reject.length && r.warn.length).length;
  console.log(`\n합계: 검사 ${results.length}개 | 통과 ${ok.length - rejected}개 (그중 경고만 ${warned}개) | ` +
    `반려 ${rejected}개 | 읽기 실패 ${errors}개 | WAV 아님 ${skipped.length}개`);

  const stamp = results.map((r) => (r.error ? r : { ...r, peakDb: finiteOrNull(r.peakDb), roomDb: finiteOrNull(r.roomDb) }));
  if (jsonOut) fs.writeFileSync(jsonOut, JSON.stringify({ results: stamp, skipped }, null, 2));
  if (csvOut) fs.writeFileSync(csvOut, toCsv(results));
  return rejected ? 1 : errors ? 2 : 0;
}

function finiteOrNull(x) { return Number.isFinite(x) ? x : null; }

if (require.main === module) process.exitCode = main(process.argv.slice(2));
module.exports = { inspect, main };
