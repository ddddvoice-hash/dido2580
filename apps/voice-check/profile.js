#!/usr/bin/env node
// 목소리 기준 프로필 측정기. 외부 패키지 없음.
// 사용: node apps/voice-check/profile.js <wav> [--json out.json]
// 음높이(F0)는 단순 자기상관, 초당 음절은 크기 곡선 봉우리 수로 추정한 값입니다(대본 없음).
// 말소리·쉼 구간은 apps/reading-coach/analysis.js를 그대로 씁니다.
"use strict";

const fs = require("fs");
const path = require("path");
const analysis = require("../reading-coach/analysis.js");
const check = require("./check.js");

const F0_MIN = 60, F0_MAX = 500;
const F0_HOP_MS = 10, F0_WIN_MS = 40;
const VOICED_R = 0.5;          // 정규화 자기상관 최소값(유성음 판정)
const OCTAVE_KEEP = 0.9;       // 최대 봉우리의 이 비율 이상인 가장 짧은 주기를 택함(옥타브 오류 줄이기)
const PAUSE_S = 0.25;          // analysis.js의 MIN_PAUSE_MS와 같은 값(덩어리 나눌 때 씀)
const END_PAUSE_S = 0.7;       // 문장 끝으로 보는 쉼 길이
const END_TAIL_MS = 300;
const END_FLAT_ST = 1;         // ±1반음 이내면 평탄
const SYL_HOP_MS = 10;
const SYL_SMOOTH = 5;          // 프레임(50ms) 이동평균
const SYL_MIN_GAP_MS = 80;     // 봉우리 사이 최소 간격
const SYL_DIP_DB = 2;          // 봉우리 사이 골이 낮은 쪽 봉우리보다 이만큼 깊어야 별개 음절
const SYL_FLOOR_DB = 25;       // 말소리 구간 최대 크기보다 이만큼 이상 작은 봉우리는 버림

const toDb = (x) => (x > 0 ? 20 * Math.log10(x) : -Infinity);

function pct(values, p) { // 선형 보간 백분위, p는 0~100
  if (!values.length) return null;
  const s = Array.from(values).sort((a, b) => a - b);
  const pos = (p / 100) * (s.length - 1);
  const lo = Math.floor(pos), hi = Math.ceil(pos);
  return s[lo] + (s[hi] - s[lo]) * (pos - lo);
}
const mean = (v) => (v.length ? v.reduce((a, b) => a + b, 0) / v.length : null);
const semis = (a, b) => 12 * Math.log2(a / b);

// ---- F0 ------------------------------------------------------------------

// 샘플을 약 12kHz로 줄이고(상자 평균) 10ms마다 40ms 창의 자기상관으로 F0를 잰다.
// 반환: [{t(초, 창 중심), f0(Hz) 또는 null(무성/판정 불가)}] — mask(t)가 true인 프레임만 잰다.
function f0Track(samples, rate, mask) {
  const dec = Math.max(1, Math.round(rate / 12000));
  const r2 = rate / dec;
  const n = Math.floor(samples.length / dec);
  const x = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    let s = 0;
    for (let k = 0; k < dec; k++) s += samples[i * dec + k];
    x[i] = s / dec;
  }
  const win = Math.round(r2 * F0_WIN_MS / 1000);
  const hop = Math.round(r2 * F0_HOP_MS / 1000);
  const lagMin = Math.max(2, Math.floor(r2 / F0_MAX));
  const lagMax = Math.ceil(r2 / F0_MIN);
  const track = [];
  const r = new Float64Array(lagMax + 2);
  for (let s = 0; s + win + lagMax + 1 <= n; s += hop) {
    const t = (s + win / 2) / r2;
    if (mask && !mask(t)) continue;
    let m = 0;
    for (let i = 0; i < win + lagMax + 1; i++) m += x[s + i];
    m /= win + lagMax + 1;
    let e0 = 0;
    for (let i = 0; i < win; i++) { const v = x[s + i] - m; e0 += v * v; }
    if (e0 < 1e-9) { track.push({ t, f0: null }); continue; }
    for (let lag = lagMin - 1; lag <= lagMax + 1; lag++) {
      let c = 0, el = 0;
      for (let i = 0; i < win; i++) {
        const a = x[s + i] - m, b = x[s + i + lag] - m;
        c += a * b; el += b * b;
      }
      r[lag] = el > 0 ? c / Math.sqrt(e0 * el) : 0;
    }
    let maxR = 0;
    for (let lag = lagMin; lag <= lagMax; lag++) {
      if (r[lag] > r[lag - 1] && r[lag] >= r[lag + 1] && r[lag] > maxR) maxR = r[lag];
    }
    if (maxR < VOICED_R) { track.push({ t, f0: null }); continue; }
    let pick = -1;
    for (let lag = lagMin; lag <= lagMax; lag++) {
      if (r[lag] > r[lag - 1] && r[lag] >= r[lag + 1] && r[lag] >= OCTAVE_KEEP * maxR) { pick = lag; break; }
    }
    const y0 = r[pick - 1], y1 = r[pick], y2 = r[pick + 1];
    const den = y0 - 2 * y1 + y2;
    const off = den !== 0 ? 0.5 * (y0 - y2) / den : 0;
    const f0 = r2 / (pick + off);
    track.push({ t, f0: f0 >= F0_MIN && f0 <= F0_MAX ? f0 : null });
  }
  return track;
}

// ---- 음절(추정) ---------------------------------------------------------

function countSyllables(samples, rate, runsSec) {
  const hop = Math.round(rate * SYL_HOP_MS / 1000);
  const frames = Math.floor(samples.length / hop);
  const env = new Float32Array(frames);
  for (let f = 0; f < frames; f++) {
    let sum = 0;
    for (let i = f * hop; i < (f + 1) * hop; i++) sum += samples[i] * samples[i];
    env[f] = Math.sqrt(sum / hop);
  }
  const sm = new Float32Array(frames);
  const h = Math.floor(SYL_SMOOTH / 2);
  for (let f = 0; f < frames; f++) {
    let s = 0, c = 0;
    for (let k = -h; k <= h; k++) if (f + k >= 0 && f + k < frames) { s += env[f + k]; c++; }
    sm[f] = toDb(s / c);
  }
  let total = 0;
  const minGap = Math.round(SYL_MIN_GAP_MS / SYL_HOP_MS);
  for (const [a, b] of runsSec) {
    const f0 = Math.max(0, Math.floor(a * 1000 / SYL_HOP_MS)), f1 = Math.min(frames, Math.ceil(b * 1000 / SYL_HOP_MS));
    if (f1 - f0 < 3) continue;
    let top = -Infinity;
    for (let f = f0; f < f1; f++) if (sm[f] > top) top = sm[f];
    const peaks = [];
    for (let f = Math.max(f0, 1); f < Math.min(f1, frames - 1); f++) {
      if (sm[f] > sm[f - 1] && sm[f] >= sm[f + 1] && sm[f] > top - SYL_FLOOR_DB) peaks.push(f);
    }
    // 가까운 봉우리·얕은 골은 합친다(높은 쪽 유지)
    let changed = true;
    while (changed && peaks.length > 1) {
      changed = false;
      for (let i = 0; i < peaks.length - 1; i++) {
        const p = peaks[i], q = peaks[i + 1];
        let dip = Infinity;
        for (let f = p; f <= q; f++) if (sm[f] < dip) dip = sm[f];
        const lower = Math.min(sm[p], sm[q]);
        if (q - p < minGap || lower - dip < SYL_DIP_DB) {
          peaks.splice(sm[p] >= sm[q] ? i + 1 : i, 1);
          changed = true;
          break;
        }
      }
    }
    total += peaks.length;
  }
  return total;
}

// ---- 프로필 --------------------------------------------------------------

function profile(samples, rate, peak) {
  const FR = analysis.FRAME_MS;
  const duration = samples.length / rate;
  const frameSize = Math.max(1, Math.round(rate * FR / 1000));
  const runs = analysis.speechRuns(analysis.envelope(samples, rate));
  // 말소리 구간이 없거나 analyze가 측정 실패(failed)면 쉼 0개·길이 0으로 쓰지 않고 측정 실패로 던진다.
  const a = analysis.analyze(samples, rate);
  if (!runs.length || a.failed) throw new Error("말소리를 찾지 못했습니다 (측정 실패)");
  const runsSec = runs.map((r) => [r.start * FR / 1000, r.end * FR / 1000]);
  const spoken = runsSec.reduce((a, [s, e]) => a + (e - s), 0);

  // 말소리 덩어리: 0.25초 미만 틈은 같은 덩어리
  const chunks = [];
  for (const [s, e] of runsSec) {
    const last = chunks[chunks.length - 1];
    if (last && s - last.end < PAUSE_S - 1e-9) last.end = e;
    else chunks.push({ start: s, end: e });
  }

  // 1. 음높이
  const starts = runsSec.map((r) => r[0]), ends = runsSec.map((r) => r[1]);
  const mask = (t) => {
    let lo = 0, hi = starts.length - 1;
    while (lo <= hi) {
      const mid = (lo + hi) >> 1;
      if (t < starts[mid]) hi = mid - 1; else if (t >= ends[mid]) lo = mid + 1; else return true;
    }
    return false;
  };
  const track = f0Track(samples, rate, mask);
  const voiced = track.filter((p) => p.f0 !== null);
  const f0s = voiced.map((p) => p.f0);
  const p10 = pct(f0s, 10), p90 = pct(f0s, 90);
  const pitch = {
    frames: track.length, voicedFrames: voiced.length,
    voicedRatio: track.length ? voiced.length / track.length : 0,
    medianHz: pct(f0s, 50), meanHz: mean(f0s), p10Hz: p10, p90Hz: p90,
    rangeSemitones: p10 && p90 ? semis(p90, p10) : null,
  };

  // 2. 음절(추정)
  const syl = countSyllables(samples, rate, runsSec);
  const syllables = {
    estimated: true, count: syl,
    perSecSpoken: spoken > 0 ? syl / spoken : null,
    perSecTotal: duration > 0 ? syl / duration : null,
    spokenSec: spoken, totalSec: duration,
  };

  // 3. 쉼
  const lens = a.pauses.map((p) => p.length);
  const bins = { "0.25-0.5": 0, "0.5-1": 0, "1-2": 0, "2+": 0 };
  for (const l of lens) {
    if (l < 0.5 - 1e-9) bins["0.25-0.5"]++;
    else if (l < 1 - 1e-9) bins["0.5-1"]++;
    else if (l < 2 - 1e-9) bins["1-2"]++;
    else bins["2+"]++;
  }
  const spanMin = a.duration / 60;
  const pauses = {
    count: lens.length, perMinute: spanMin > 0 ? lens.length / spanMin : null,
    medianS: pct(lens, 50), p25S: pct(lens, 25), p75S: pct(lens, 75), p90S: pct(lens, 90),
    maxS: lens.length ? Math.max(...lens) : null, bins,
    spanSec: a.duration,
  };

  // 4. 문장 끝 음높이
  const endChanges = [];
  let skipped = 0;
  for (let i = 0; i < chunks.length - 1; i++) {
    const gap = chunks[i + 1].start - chunks[i].end;
    if (gap < END_PAUSE_S - 1e-9) continue;
    const c = chunks[i];
    const inChunk = voiced.filter((p) => p.t >= c.start && p.t < c.end).map((p) => p.f0);
    const inTail = voiced.filter((p) => p.t >= c.end - END_TAIL_MS / 1000 && p.t < c.end).map((p) => p.f0);
    if (inChunk.length < 10 || inTail.length < 3) { skipped++; continue; }
    endChanges.push(semis(pct(inTail, 50), pct(inChunk, 50)));
  }
  const nDown = endChanges.filter((v) => v < -END_FLAT_ST).length;
  const nUp = endChanges.filter((v) => v > END_FLAT_ST).length;
  const nEnd = endChanges.length;
  const sentenceEnd = {
    count: nEnd, skipped,
    down: nDown, flat: nEnd - nDown - nUp, up: nUp,
    downRatio: nEnd ? nDown / nEnd : null,
    flatRatio: nEnd ? (nEnd - nDown - nUp) / nEnd : null,
    upRatio: nEnd ? nUp / nEnd : null,
    meanChangeSemitones: mean(endChanges),
  };

  // 5. 크기 (dBFS, LUFS 아님)
  let sqAll = 0;
  for (let i = 0; i < samples.length; i++) sqAll += samples[i] * samples[i];
  let sqSp = 0, nSp = 0;
  for (const r of runs) {
    for (let i = r.start * frameSize; i < Math.min(samples.length, r.end * frameSize); i++) { sqSp += samples[i] * samples[i]; nSp++; }
  }
  const loudness = {
    unit: "dBFS (LUFS 아님)",
    overallRmsDb: toDb(Math.sqrt(sqAll / samples.length)),
    speechRmsDb: nSp ? toDb(Math.sqrt(sqSp / nSp)) : null,
    peakDb: toDb(peak),
  };

  return { durationSec: duration, rate, speechRuns: runs.length, pitch, syllables, pauses, sentenceEnd, loudness };
}

function profileFile(file) {
  const fd = fs.openSync(file, "r");
  try {
    const info = check.parseHeader(fd, fs.fstatSync(fd).size);
    const audio = check.readAudio(fd, info);
    return profile(audio.samples, info.fmt.rate, audio.peak);
  } finally { fs.closeSync(fd); }
}

// ---- 출력 ----------------------------------------------------------------

const f = (x, d) => (x === null || x === undefined || !Number.isFinite(x) ? "-" : x.toFixed(d));
const p100 = (x) => (x === null ? "-" : `${(x * 100).toFixed(0)}%`);

function rows(p) {
  const P = p.pitch, S = p.syllables, Z = p.pauses, E = p.sentenceEnd, L = p.loudness;
  return [
    ["길이", `${f(p.durationSec, 1)}초 (말소리 ${f(S.spokenSec, 1)}초, 말소리 구간 ${p.speechRuns}개)`, "analysis.js 말소리 구간"],
    ["음높이 중간값", `${f(P.medianHz, 1)} Hz`, "말소리 구간 F0(자기상관, 60~500Hz) 중간값"],
    ["음높이 평균", `${f(P.meanHz, 1)} Hz`, "같은 F0 평균"],
    ["음높이 10/90 백분위", `${f(P.p10Hz, 1)} / ${f(P.p90Hz, 1)} Hz`, "같은 F0 백분위"],
    ["음높이 범위", `${f(P.rangeSemitones, 1)} 반음`, "12*log2(p90/p10)"],
    ["유성음 비율", `${p100(P.voicedRatio)} (${P.voicedFrames}/${P.frames}프레임)`, "10ms 간격 40ms 창, 자기상관 0.5 이상"],
    ["음절 수(추정)", `${S.count}개`, "크기 곡선 봉우리 수 (대본 없음, 추정)"],
    ["초당 음절(추정, 말한 시간)", `${f(S.perSecSpoken, 2)}`, "음절 수 / 쉼 뺀 말소리 시간"],
    ["초당 음절(추정, 전체 시간)", `${f(S.perSecTotal, 2)}`, "음절 수 / 전체 시간"],
    ["쉼 개수", `${Z.count}개 (분당 ${f(Z.perMinute, 1)}회)`, "0.25초 이상 쉼, 첫~끝 말소리 사이"],
    ["쉼 길이 중간값", `${f(Z.medianS, 2)}초`, "쉼 길이 중간값"],
    ["쉼 길이 25/75/90 백분위", `${f(Z.p25S, 2)} / ${f(Z.p75S, 2)} / ${f(Z.p90S, 2)}초`, "쉼 길이 백분위"],
    ["쉼 길이 최대", `${f(Z.maxS, 2)}초`, "최대"],
    ["쉼 구간별 개수", `0.25-0.5초 ${Z.bins["0.25-0.5"]} | 0.5-1초 ${Z.bins["0.5-1"]} | 1-2초 ${Z.bins["1-2"]} | 2초+ ${Z.bins["2+"]}`, "쉼 길이 구간"],
    ["문장 끝 음높이", `내림 ${p100(E.downRatio)} (${E.down}) | 평탄 ${p100(E.flatRatio)} (${E.flat}) | 올림 ${p100(E.upRatio)} (${E.up}) / 판정 ${E.count}곳, 제외 ${E.skipped}곳`,
      "0.7초 이상 쉼 앞 덩어리: 마지막 300ms F0 중간값 vs 덩어리 F0 중간값, ±1반음"],
    ["문장 끝 평균 변화", `${f(E.meanChangeSemitones, 2)} 반음`, "위 변화량 평균"],
    ["전체 RMS", `${f(L.overallRmsDb, 1)} dBFS`, "전체 샘플 RMS (LUFS 아님)"],
    ["말소리 구간 평균", `${f(L.speechRmsDb, 1)} dBFS`, "말소리 구간 샘플 RMS"],
    ["최대", `${f(L.peakDb, 1)} dBFS`, "샘플 절댓값 최대"],
  ];
}

function main(argv) {
  const files = [];
  let jsonOut = null;
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--json") { jsonOut = argv[++i]; if (!jsonOut) { console.error("--json 뒤에 경로가 필요합니다"); return 2; } }
    else files.push(argv[i]);
  }
  if (files.length !== 1) { console.error("사용: node apps/voice-check/profile.js <wav> [--json out.json]"); return 2; }
  let p;
  try { p = profileFile(files[0]); } catch (e) { console.error(`읽기 실패: ${e.message}`); return 2; }
  console.log(`${path.basename(files[0])} 기준 프로필 (음절은 추정, F0는 단순 자기상관)`);
  console.log("항목 | 값 | 재는 방법");
  for (const r of rows(p)) console.log(r.join(" | "));
  if (jsonOut) {
    try { fs.writeFileSync(jsonOut, JSON.stringify(p, null, 2)); } catch (e) { console.error(`저장 실패: ${jsonOut} (${e.message})`); return 2; }
  }
  return 0;
}

if (require.main === module) process.exitCode = main(process.argv.slice(2));
module.exports = { profile, profileFile, f0Track, countSyllables, pct, rows, main };
