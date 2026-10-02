#!/usr/bin/env node
// 대본 줄과 녹음 구간 맞추기. 외부 패키지 없음. 음성 인식은 하지 않고 쉼과 글자 수 비율만 씁니다.
// 사용: node apps/voice-check/align.js <wav> <script.json> --csv <out.csv> [--min-pause 1.0]
"use strict";

const fs = require("fs");
const check = require("./check.js");
const analysis = require("../reading-coach/analysis.js");

const BOUNDARY_MIN = 1.2;   // 앞뒤 줄과의 경계 쉼이 이보다 짧으면 불확실
const RATE_LOW = 0.5;       // 초당 음절 수가 중간값의 이 배수 미만이면 불확실
const RATE_HIGH = 2;        // 이 배수 초과여도 불확실
const MERGE_PENALTY = 0.05; // 덩어리를 합치거나 쪼개는 것을 살짝 꺼리는 값

function countSyllables(text) {
  const m = String(text).match(/[가-힣]/g);
  return m ? m.length : 0;
}

function readWav(file) {
  const fd = fs.openSync(file, "r");
  try {
    const info = check.parseHeader(fd, fs.fstatSync(fd).size);
    const f = info.fmt;
    const ok = (f.format === 1 && [16, 24, 32].includes(f.bits)) || (f.format === 3 && f.bits === 32);
    if (!ok) throw new Error("지원하지 않는 WAV 형식입니다");
    return { samples: check.readSamples(fd, info), rate: f.rate };
  } finally {
    fs.closeSync(fd);
  }
}

// 말소리 덩어리: 긴 쉼(minPause초 이상)으로만 나눈다. inner는 덩어리 안쪽 짧은 쉼 위치.
function findChunks(samples, rate, minPause) {
  const FR = analysis.FRAME_MS / 1000;
  const runs = analysis.speechRuns(analysis.envelope(samples, rate));
  const chunks = [];
  for (const r of runs) {
    const s = r.start * FR, e = r.end * FR;
    const last = chunks[chunks.length - 1];
    if (last && s - last.end < minPause - 1e-9) {
      last.inner.push({ from: last.end, to: s });
      last.end = e;
    } else chunks.push({ start: s, end: e, inner: [] });
  }
  return chunks;
}

const lg = (x) => Math.log(Math.max(x, 1e-6));

// 덩어리 >= 줄: 한 줄 = 연속된 덩어리 1개 이상. 비용 = (log(실제 길이 / 기대 길이))^2 합.
function assignMerge(chunks, syl, perSyl) {
  const N = chunks.length, M = syl.length;
  const INF = Infinity;
  const cost = (i, j, l) => { // 덩어리 i..j-1 (반열림)을 줄 l에
    const dur = chunks[j - 1].end - chunks[i].start;
    const d = lg(dur) - lg(Math.max(syl[l], 1) * perSyl);
    return d * d + MERGE_PENALTY * (j - i - 1);
  };
  const dp = Array.from({ length: M + 1 }, () => new Array(N + 1).fill(INF));
  const back = Array.from({ length: M + 1 }, () => new Array(N + 1).fill(-1));
  dp[0][0] = 0;
  for (let l = 1; l <= M; l++) {
    for (let j = l; j <= N - (M - l); j++) {
      for (let i = l - 1; i < j; i++) {
        if (dp[l - 1][i] === INF) continue;
        const c = dp[l - 1][i] + cost(i, j, l - 1);
        if (c < dp[l][j]) { dp[l][j] = c; back[l][j] = i; }
      }
    }
  }
  const out = new Array(M);
  let j = N;
  for (let l = M; l >= 1; l--) { const i = back[l][j]; out[l - 1] = [i, j]; j = i; }
  return out;
}

// 덩어리 < 줄: 덩어리마다 줄 1개 이상.
function assignSplit(chunks, syl, perSyl) {
  const N = chunks.length, M = syl.length;
  const INF = Infinity;
  const pre = [0];
  syl.forEach((s) => pre.push(pre[pre.length - 1] + Math.max(s, 1)));
  const cost = (c, a, b) => { // 줄 a..b-1을 덩어리 c에
    const d = lg(chunks[c].end - chunks[c].start) - lg((pre[b] - pre[a]) * perSyl);
    return d * d + MERGE_PENALTY * (b - a - 1);
  };
  const dp = Array.from({ length: N + 1 }, () => new Array(M + 1).fill(INF));
  const back = Array.from({ length: N + 1 }, () => new Array(M + 1).fill(-1));
  dp[0][0] = 0;
  for (let c = 1; c <= N; c++) {
    for (let b = c; b <= M - (N - c); b++) {
      for (let a = c - 1; a < b; a++) {
        if (dp[c - 1][a] === INF) continue;
        const v = dp[c - 1][a] + cost(c - 1, a, b);
        if (v < dp[c][b]) { dp[c][b] = v; back[c][b] = a; }
      }
    }
  }
  const out = [];
  let b = M;
  for (let c = N; c >= 1; c--) { const a = back[c][b]; out.unshift([a, b]); b = a; }
  return out; // 덩어리별 [첫 줄, 끝 줄+1]
}

function median(arr) {
  const s = arr.slice().sort((a, b) => a - b);
  if (!s.length) return 0;
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

// 덩어리 하나를 줄 여러 개로 쪼갠다. 글자 수 비율 위치 가까이(덩어리 길이의 20% 이내)에 안쪽 쉼이 있으면 거기에 맞춘다.
function splitChunk(chunk, sylList) {
  const total = sylList.reduce((a, b) => a + Math.max(b, 1), 0);
  const len = chunk.end - chunk.start;
  const cuts = [];
  let acc = 0;
  for (let k = 0; k < sylList.length - 1; k++) {
    acc += Math.max(sylList[k], 1);
    const t = chunk.start + len * (acc / total);
    let best = null;
    for (const g of chunk.inner) {
      const mid = (g.from + g.to) / 2;
      if (Math.abs(mid - t) <= len * 0.2 && (!best || Math.abs(mid - t) < Math.abs(best.mid - t))) best = { mid, g };
    }
    cuts.push(best ? best.g : { from: t, to: t });
  }
  const segs = [];
  let s = chunk.start;
  for (const c of cuts) { segs.push([s, c.from]); s = c.to; }
  segs.push([s, chunk.end]);
  return segs;
}

function align(samples, rate, script, minPause) {
  const lines = script.lines;
  const chunks = findChunks(samples, rate, minPause);
  const syl = lines.map((l) => countSyllables(l.text));
  const totalSyl = syl.reduce((a, b) => a + Math.max(b, 1), 0);
  const totalDur = chunks.reduce((a, c) => a + (c.end - c.start), 0);
  const perSyl = totalDur / Math.max(totalSyl, 1);
  const rows = lines.map((l, i) => ({
    no: l.no, key: l.key, text: l.text, syllables: syl[i],
    start: null, end: null, chunks: 0, reasons: [],
  }));
  if (!chunks.length || !lines.length) return { chunks, rows, mode: "none" };

  let mode;
  if (chunks.length >= lines.length) {
    mode = "merge";
    assignMerge(chunks, syl, perSyl).forEach(([i, j], l) => {
      rows[l].start = chunks[i].start; rows[l].end = chunks[j - 1].end; rows[l].chunks = j - i;
      if (j - i > 1) rows[l].reasons.push(`덩어리 ${j - i}개를 합침`);
    });
  } else {
    mode = "split";
    assignSplit(chunks, syl, perSyl).forEach(([a, b], c) => {
      if (b - a === 1) {
        rows[a].start = chunks[c].start; rows[a].end = chunks[c].end; rows[a].chunks = 1;
        return;
      }
      splitChunk(chunks[c], syl.slice(a, b)).forEach(([s, e], k) => {
        const r = rows[a + k];
        r.start = s; r.end = e; r.chunks = 1;
        r.reasons.push(`덩어리 하나를 줄 ${b - a}개로 쪼갬`);
      });
    });
  }

  rows.forEach((r) => { r.dur = r.end - r.start; r.rate = r.syllables / r.dur; });
  const med = median(rows.map((r) => r.rate));
  rows.forEach((r, i) => {
    if (med > 0 && r.rate < med * RATE_LOW) r.reasons.push(`초당 음절 ${r.rate.toFixed(1)} (중간값 ${med.toFixed(1)}의 0.5배 미만)`);
    if (med > 0 && r.rate > med * RATE_HIGH) r.reasons.push(`초당 음절 ${r.rate.toFixed(1)} (중간값 ${med.toFixed(1)}의 2배 초과)`);
    if (i > 0) {
      const g = r.start - rows[i - 1].end;
      if (g < BOUNDARY_MIN) r.reasons.push(`앞 줄과 쉼 ${g.toFixed(2)}초`);
    }
    if (i < rows.length - 1) {
      const g = rows[i + 1].start - r.end;
      if (g < BOUNDARY_MIN) r.reasons.push(`뒤 줄과 쉼 ${g.toFixed(2)}초`);
    }
    r.uncertain = r.reasons.length > 0;
  });
  return { chunks, rows, mode, median: med };
}

function csvCell(v) {
  const s = v == null ? "" : String(v);
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

function toCsv(rows) {
  const head = ["no", "key", "text", "start_sec", "end_sec", "dur_sec", "syllables", "syl_per_sec", "chunks", "uncertain", "reason"];
  const f = (x) => (x == null ? "" : x.toFixed(3));
  const body = rows.map((r) => [
    r.no, r.key, r.text, f(r.start), f(r.end), f(r.dur), r.syllables,
    r.rate == null ? "" : r.rate.toFixed(2), r.chunks, r.uncertain ? "Y" : "", r.reasons.join("; "),
  ].map(csvCell).join(","));
  return "﻿" + [head.join(","), ...body].join("\r\n") + "\r\n";
}

function main(argv) {
  const pos = [];
  let csv = null, minPause = 1.0;
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--csv") csv = argv[++i];
    else if (argv[i] === "--min-pause") minPause = parseFloat(argv[++i]);
    else pos.push(argv[i]);
  }
  if (pos.length !== 2 || !csv || !(minPause > 0)) {
    console.error("사용: node apps/voice-check/align.js <wav> <script.json> --csv <out.csv> [--min-pause 1.0]");
    return 2;
  }
  try {
    const script = JSON.parse(fs.readFileSync(pos[1], "utf8"));
    const { samples, rate } = readWav(pos[0]);
    const res = align(samples, rate, script, minPause);
    if (!res.chunks.length) { console.error("말소리를 찾지 못했습니다."); return 1; }
    fs.writeFileSync(csv, toCsv(res.rows));
    const bad = res.rows.filter((r) => r.uncertain);
    console.log(`덩어리 ${res.chunks.length}개, 대본 ${res.rows.length}줄 (${res.mode === "merge" ? "덩어리를 합쳐 배정" : "덩어리를 쪼개 배정"}), 최소 쉼 ${minPause}초`);
    console.log(`불확실 ${bad.length}줄`);
    bad.forEach((r) => console.log(`  ${r.no} ${r.key}: ${r.reasons.join("; ")}`));
    console.log(`저장: ${csv}`);
    return 0;
  } catch (e) {
    console.error("실패: " + e.message);
    return 2;
  }
}

if (require.main === module) process.exitCode = main(process.argv.slice(2));
module.exports = { align, findChunks, countSyllables, toCsv, main };
