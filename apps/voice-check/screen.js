#!/usr/bin/env node
// 새 녹음 한 번에 검사기. 외부 패키지 없음.
// 사용: node apps/voice-check/screen.js <폴더> --ref <기준.wav> --work <_work 폴더> [--exclude-sha <파일>] [--json out.json] [--md out.md]
// 폴더(원본)는 읽기만 한다. 쓰기는 --work 아래(converted/, upload/)와 --json/--md 경로뿐이다.
"use strict";

const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const cp = require("child_process");
const analysis = require("../reading-coach/analysis.js");
const check = require("./check.js");
const prof = require("./profile.js");
const trimmer = require("./trim.js");

const AUDIO_EXT = new Set([".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".oga", ".opus", ".wma", ".aif", ".aiff", ".amr", ".mp4", ".webm", ".3gp", ".caf"]);
const TAIL_TARGET = 0.8;
const TONE_ST = 3;             // 기준과 음높이 차이(반음)가 이보다 크면 톤 다름
const BG_MEDIAN_DB = -50;      // (a) 말소리 밖 RMS 중간값이 이보다 크고
const BG_FRAME_DB = -55;       // (a) 이 값보다 큰 프레임이
const BG_FRAME_RATIO = 0.75;   // (a) 이 비율 이상이면 계속 시끄러움
const BG_EDGE_SEC = 0.5;       // (a) 파일 앞·뒤 이 구간은 뺌
const BG_MIN_FRAMES = 25;      // (a) 이보다 프레임이 적으면 판단하지 않음
const TWO_GAP_ST = 7;          // (b) 두 무리 중심 차이(반음) 최소
const TWO_SMALL_RATIO = 0.2;   // (b) 작은 무리 비율 최소
const TWO_VALLEY = 0.25;       // (b) 사이 밀도가 각 봉우리의 이 비율 미만
const TWO_MIN_FRAMES = 50;

const GENERIC_WORDS = ["recording", "sample", "voice", "take", "base", "new", "rec", "음성", "녹음", "샘플", "평소", "기본", "테스트"];
const NAME_OK_RE = /^\d{3}_[a-z0-9_]+_take\d{2}$/;

// ---- 도우미 --------------------------------------------------------------

const sha256File = (p) => crypto.createHash("sha256").update(fs.readFileSync(p)).digest("hex");

function readExcludeShas(file) {
  const set = new Set();
  for (const raw of fs.readFileSync(file, "utf8").split(/\r?\n/)) {
    const line = raw.replace(/#.*/, "").trim().toLowerCase();
    const m = line.match(/^[0-9a-f]{64}/);
    if (m) set.add(m[0]);
  }
  return set;
}

function nameNeedsReview(fileName) {
  const stem = path.basename(fileName, path.extname(fileName)).normalize("NFC").toLowerCase();
  if (NAME_OK_RE.test(stem)) return false;
  let s = stem;
  for (const w of GENERIC_WORDS.slice().sort((a, b) => b.length - a.length)) s = s.split(w).join("");
  s = s.replace(/[\d\s_\-()[\]（）]/g, "");
  return s.length > 0;
}

function hasFfmpegDefault() {
  try { return cp.spawnSync("ffmpeg", ["-version"], { stdio: "ignore" }).status === 0; } catch (e) { return false; }
}

function convertDefault(inFile, outFile) {
  const r = cp.spawnSync("ffmpeg", ["-y", "-i", inFile, "-ac", "1", "-c:a", "pcm_s24le", outFile], { stdio: "ignore" });
  if (r.status !== 0) throw new Error("ffmpeg 변환 실패");
}

function inside(child, parent) {
  const rel = path.relative(path.resolve(parent).toLowerCase(), path.resolve(child).toLowerCase());
  return rel === "" || (!rel.startsWith("..") && !path.isAbsolute(rel));
}

// ---- 섞임 의심 -----------------------------------------------------------

// (a) 말소리 밖 구간이 계속 시끄러운가
function noisyBackground(samples, rate) {
  const env = analysis.envelope(samples, rate);
  const runs = analysis.speechRuns(env);
  if (!runs.length) return false;
  const inSpeech = new Uint8Array(env.length);
  for (const r of runs) for (let f = r.start; f < r.end; f++) inSpeech[f] = 1;
  const FR = analysis.FRAME_MS / 1000;
  const total = samples.length / rate;
  const dbs = [];
  for (let f = 0; f < env.length; f++) {
    if (inSpeech[f]) continue;
    const t0 = f * FR, t1 = (f + 1) * FR;
    if (t0 < BG_EDGE_SEC || t1 > total - BG_EDGE_SEC) continue;
    dbs.push(env[f] > 0 ? 20 * Math.log10(env[f]) : -200);
  }
  if (dbs.length < BG_MIN_FRAMES) return false;
  const med = prof.pct(dbs, 50);
  const loudRatio = dbs.filter((d) => d > BG_FRAME_DB).length / dbs.length;
  return med > BG_MEDIAN_DB && loudRatio >= BG_FRAME_RATIO;
}

// (b) 유성 프레임 F0가 두 무리인가 (반음 단위 2-평균)
function twoPitchGroups(f0s) {
  if (f0s.length < TWO_MIN_FRAMES) return false;
  const st = f0s.map((f) => 12 * Math.log2(f / 100));
  let c1 = prof.pct(st, 10), c2 = prof.pct(st, 90);
  let g1 = [], g2 = [];
  for (let it = 0; it < 100; it++) {
    g1 = []; g2 = [];
    for (const v of st) (Math.abs(v - c1) <= Math.abs(v - c2) ? g1 : g2).push(v);
    if (!g1.length || !g2.length) return false;
    const n1 = g1.reduce((a, b) => a + b, 0) / g1.length, n2 = g2.reduce((a, b) => a + b, 0) / g2.length;
    if (n1 === c1 && n2 === c2) break;
    c1 = n1; c2 = n2;
  }
  const lo = Math.min(c1, c2), hi = Math.max(c1, c2);
  if (hi - lo < TWO_GAP_ST) return false;
  if (Math.min(g1.length, g2.length) / st.length < TWO_SMALL_RATIO) return false;
  const density = (x) => { let n = 0; for (const v of st) if (v >= x - 0.5 && v <= x + 0.5) n++; return n; };
  const mid = (lo + hi) / 2;
  let valley = 0;
  for (let x = mid - 1; x <= mid + 1 + 1e-9; x += 0.25) valley = Math.max(valley, density(x));
  const peakOf = (a, b) => { let m = 0; for (let x = a; x <= b + 1e-9; x += 0.25) m = Math.max(m, density(x)); return m; };
  const minSt = Math.min(...st), maxSt = Math.max(...st);
  const pLo = peakOf(minSt, mid), pHi = peakOf(mid, maxSt);
  return valley < TWO_VALLEY * pLo && valley < TWO_VALLEY * pHi;
}

// ---- 파일 하나 분석 --------------------------------------------------------

function analyzeWav(file) {
  const fd = fs.openSync(file, "r");
  let info, audio;
  try {
    info = check.parseHeader(fd, fs.fstatSync(fd).size);
    audio = check.readAudio(fd, info);
  } finally { fs.closeSync(fd); }
  const rate = info.fmt.rate;
  const ins = check.inspect(file);
  const out = { reject: ins.reject, duration: ins.duration, tail: ins.tail, medianHz: null, pauseMed: null, endDown: null, spoken: null, mix: [] };
  if (ins.tail === null) { out.noSpeech = true; return out; }
  let p;
  try { p = prof.profile(audio.samples, rate, audio.peak); } catch (e) { out.noSpeech = true; return out; }
  out.medianHz = p.pitch.medianHz;
  out.pauseMed = p.pauses.medianS;
  out.endDown = p.sentenceEnd.count ? { ratio: p.sentenceEnd.downRatio, down: p.sentenceEnd.down, count: p.sentenceEnd.count } : null;
  out.spoken = p.syllables.spokenSec;
  if (noisyBackground(audio.samples, rate)) out.mix.push("배경 계속 시끄러움");
  const runs = analysis.speechRuns(analysis.envelope(audio.samples, rate)).map((r) => [r.start * analysis.FRAME_MS / 1000, r.end * analysis.FRAME_MS / 1000]);
  const track = prof.f0Track(audio.samples, rate, (t) => runs.some(([a, b]) => t >= a && t < b));
  if (twoPitchGroups(track.filter((q) => q.f0 !== null).map((q) => q.f0))) out.mix.push("두 음높이 섞임");
  return out;
}

function verdictOf(a, tone) {
  if (a.noSpeech) return { verdict: "쓰지 않음", marks: ["말소리 없음"] };
  const marks = [];
  if (a.mix.length) marks.push(`섞임 의심(${a.mix.join(", ")})`);
  if (tone) marks.push("톤 다름");
  if (marks.length) return { verdict: "쓰지 않음", marks };
  if (!a.reject.length) return { verdict: "쓸 수 있음", marks };
  if (a.reject.length === 1 && a.reject[0] === "V05") return { verdict: "뒤 여백 자르면 쓸 수 있음", marks };
  return { verdict: "반려", marks };
}

const isUsable = (v) => v === "쓸 수 있음" || v === "뒤 여백 자르면 쓸 수 있음";

// upload 사본: 뒤 여백 0.8초 초과면 자르고, 아니면 그대로 복사
function makeUpload(src, dest, tail) {
  if (tail <= TAIL_TARGET + 1e-6) fs.copyFileSync(src, dest);
  else trimmer.trim(src, dest, TAIL_TARGET);
  const c = check.inspect(dest);
  return { ok: !c.reject.includes("V05"), duration: c.duration, tail: c.tail };
}

// ---- 전체 --------------------------------------------------------------

function run(opts) {
  const folder = opts.folder, work = opts.work;
  if (inside(work, folder)) throw new Error("--work 폴더는 검사할 폴더 안에 둘 수 없습니다");
  const hasFfmpeg = opts.hasFfmpeg === undefined ? hasFfmpegDefault() : !!opts.hasFfmpeg;
  const convert = opts.convert || convertDefault;
  const refPath = path.resolve(opts.ref);
  const excluded = opts.excludeSha ? readExcludeShas(opts.excludeSha) : new Set();
  const uploadDir = path.join(work, "upload"), convDir = path.join(work, "converted");
  fs.mkdirSync(uploadDir, { recursive: true });

  const items = fs.readdirSync(folder).sort().map((name) => ({ name, path: path.join(folder, name) }))
    .filter((it) => fs.statSync(it.path).isFile() && AUDIO_EXT.has(path.extname(it.name).toLowerCase()));
  for (const it of items) { it.sha = sha256File(it.path); it.isRef = path.resolve(it.path) === refPath; }
  const refSha = sha256File(refPath);
  const skippedOther = fs.readdirSync(folder).length - items.length;

  // 이름 가림 번호 (기준 파일은 제외)
  let maskN = 0;
  for (const it of items) if (!it.isRef && nameNeedsReview(it.name)) it.mask = `이름 가림 #${++maskN}`;
  const disp = (it) => it.mask || it.name;

  const groups = new Map();
  for (const it of items) { if (it.isRef) continue; if (!groups.has(it.sha)) groups.set(it.sha, []); groups.get(it.sha).push(it); }

  // 기준 파일 분석
  const refName = path.basename(refPath);
  const refA = analyzeWav(refPath);
  const refV = verdictOf(refA, false);
  const refRow = {
    display: refName, isRef: true, sha8: refSha.slice(0, 8), duration: refA.duration, reject: refA.reject,
    medianHz: refA.medianHz, diffSt: null, pauseMed: refA.pauseMed, endDown: refA.endDown, spoken: refA.spoken,
    marks: ["기준", ...refV.marks], verdict: refV.verdict, usable: false, inTotals: true, mix: refA.mix,
  };
  const rows = [refRow];
  const uploadList = [];
  // 기준 파일은 판정과 상관없이 upload 사본을 만들고 합계(기준 포함)에 넣는다.
  uploadList.push({ row: refRow, src: refPath, name: refName, tail: refA.tail });

  for (const it of items) {
    if (it.isRef) continue;
    const row = { display: disp(it), sha8: it.sha.slice(0, 8), masked: !!it.mask, duration: null, reject: [], medianHz: null, diffSt: null,
      pauseMed: null, endDown: null, spoken: null, marks: [], verdict: "쓰지 않음", usable: false, mix: [] };
    rows.push(row);
    row.kind = "";
    if (excluded.has(it.sha)) { row.marks = ["이전에 제외한 파일"]; row.kind = "excluded"; continue; }
    if (it.sha === refSha) { row.marks = ["기준과 중복"]; row.kind = "refdup"; continue; }
    const first = groups.get(it.sha)[0];
    if (first !== it) { row.marks = [`중복(=${disp(first)})`]; row.kind = "dup"; continue; }
    if (it.mask) { row.marks = ["대표 확인(이름)"]; row.kind = "name"; continue; }
    let wavPath = it.path, wavName = it.name;
    if (path.extname(it.name).toLowerCase() !== ".wav") {
      if (!hasFfmpeg) { row.marks = ["압축 원본 · 변환 불가(ffmpeg 없음)"]; row.kind = "noconv"; continue; }
      fs.mkdirSync(convDir, { recursive: true });
      wavName = path.basename(it.name, path.extname(it.name)) + ".wav";
      wavPath = path.join(convDir, wavName);
      try { convert(it.path, wavPath); } catch (e) { row.marks = ["압축 원본 · 변환 실패"]; row.kind = "noconv"; continue; }
      row.marks.push("압축 원본");
    }
    let a;
    try { a = analyzeWav(wavPath); } catch (e) { row.marks.push("읽기 실패"); row.kind = "error"; continue; }
    row.duration = a.duration; row.reject = a.reject; row.medianHz = a.medianHz; row.pauseMed = a.pauseMed;
    row.endDown = a.endDown; row.spoken = a.spoken; row.mix = a.mix;
    if (a.medianHz !== null && refA.medianHz) row.diffSt = 12 * Math.log2(a.medianHz / refA.medianHz);
    const tone = row.diffSt !== null && Math.abs(row.diffSt) > TONE_ST;
    const v = verdictOf(a, tone);
    row.verdict = v.verdict;
    row.marks.push(...v.marks);
    row.usable = isUsable(v.verdict);
    row.kind = row.usable ? "usable" : v.verdict === "반려" ? "reject" : "flag";
    if (row.usable) uploadList.push({ row, src: wavPath, name: wavName, tail: a.tail });
  }

  // upload 사본
  for (const u of uploadList) {
    const r = makeUpload(u.src, path.join(uploadDir, u.name), u.tail);
    u.row.uploadOk = r.ok;
    u.row.uploadDuration = r.duration;
    if (!r.ok) { u.row.marks.push("upload 사본 V05"); }
  }

  return summarize(rows, { skippedOther, hasFfmpeg });
}

function summarize(rows, extra) {
  const sum = (list, key) => list.reduce((a, r) => a + (r[key] || 0), 0);
  const usableOthers = rows.filter((r) => !r.isRef && r.usable);
  const usableAll = rows.filter((r) => r.usable || r.inTotals);
  const tot = (list) => ({ count: list.length, duration: sum(list, "duration"), spoken: sum(list, "spoken"), uploadDuration: sum(list, "uploadDuration") });
  const totals = { withoutRef: tot(usableOthers), withRef: tot(usableAll) };
  const verdicts = {};
  for (const r of rows) if (!r.isRef) verdicts[r.verdict] = (verdicts[r.verdict] || 0) + 1;
  const others = rows.filter((r) => !r.isRef);
  const counts = {
    files: others.length, verdicts,
    mixSuspect: others.filter((r) => r.mix && r.mix.length).length,
    nameMasked: others.filter((r) => r.masked).length,
    duplicates: others.filter((r) => r.kind === "dup" || r.kind === "refdup").length,
    excluded: others.filter((r) => r.kind === "excluded").length,
    notConverted: others.filter((r) => r.kind === "noconv").length,
    refMixSuspect: rows[0].mix.length > 0,
  };
  return { rows, totals, counts, ...extra };
}

// ---- 출력 --------------------------------------------------------------

const fmtTime = (s) => { const t = Math.round(s); return `${Math.floor(t / 60)}분 ${String(t % 60).padStart(2, "0")}초`; };
const num = (x, d, unit = "") => (x === null || x === undefined || !Number.isFinite(x) ? "-" : x.toFixed(d) + unit);

function rowCells(r) {
  const diff = r.isRef ? "기준" : r.diffSt === null ? "-" : `${r.diffSt >= 0 ? "+" : ""}${r.diffSt.toFixed(1)} 반음`;
  const end = r.endDown ? `${(r.endDown.ratio * 100).toFixed(0)}% (${r.endDown.down}/${r.endDown.count})` : "-";
  const shown = r.masked ? `${r.display} (해시 ${r.sha8})` : r.display;
  return [shown, r.duration === null ? "-" : fmtTime(r.duration), r.reject.length ? r.reject.join(",") : "-",
    num(r.medianHz, 1, " Hz"), diff, num(r.pauseMed, 2, "초"), end, r.marks.length ? r.marks.join(" · ") : "-", r.verdict]
    .map((c) => String(c).replace(/\|/g, "\\|"));
}

function reachLine(label, t) {
  const parts = [10, 20, 30].map((m) => `${m}분 ${t.duration >= m * 60 ? "넘음" : "못 넘음"}`);
  return `${label} ${fmtTime(t.duration)} (말한 시간 ${fmtTime(t.spoken)}): ${parts.join(", ")}`;
}

function toMarkdown(res) {
  const L = [];
  L.push("| 파일 | 길이 | 반려 코드 | 음높이 중간값 | 기준과 차이 | 쉼 중간값 | 문장 끝 내림 | 표시 | 판정 |");
  L.push("|---|---|---|---|---|---|---|---|---|");
  for (const r of res.rows) L.push(`| ${rowCells(r).join(" | ")} |`);
  L.push("");
  const T = res.totals, C = res.counts;
  L.push("| 합계 | 파일 수 | 길이 | 말한 시간 | upload 사본 길이 |");
  L.push("|---|---|---|---|---|");
  for (const [label, t] of [["쓸 수 있는 파일(기준 미포함)", T.withoutRef], ["쓸 수 있는 파일(기준 포함)", T.withRef]]) {
    L.push(`| ${label} | ${t.count}개 | ${fmtTime(t.duration)} | ${fmtTime(t.spoken)} | ${fmtTime(t.uploadDuration)} |`);
  }
  L.push("");
  L.push(`${reachLine("기준 미포함", T.withoutRef)} / ${reachLine("기준 포함", T.withRef)}`);
  L.push("");
  const vs = Object.entries(C.verdicts).map(([k, v]) => `${k} ${v}개`).join(", ");
  L.push(`판정별: ${vs || "없음"} (기준 제외 ${C.files}개) | 섞임 의심 ${C.mixSuspect}개 | 이름 가림 ${C.nameMasked}개 | 중복 ${C.duplicates}개 | 이전에 제외 ${C.excluded}개 | 변환 불가 ${C.notConverted}개`);
  const ref = res.rows[0];
  L.push("");
  L.push(`기준: ${ref.display} | 길이 ${fmtTime(ref.duration)} | 음높이 중간값 ${num(ref.medianHz, 1, " Hz")} | 쉼 중간값 ${num(ref.pauseMed, 2, "초")} | 문장 끝 내림 ${ref.endDown ? (ref.endDown.ratio * 100).toFixed(0) + "%" : "-"} | 섞임 의심 ${C.refMixSuspect ? "있음(" + ref.mix.join(", ") + ")" : "없음"}`);
  return L.join("\n") + "\n";
}

function toJson(res) {
  const rows = res.rows.map((r) => ({
    file: r.display, sha8: r.sha8, duration_s: r.duration, reject: r.reject, median_hz: r.medianHz, diff_semitones: r.diffSt,
    pause_median_s: r.pauseMed, sentence_end_down: r.endDown, spoken_s: r.spoken, marks: r.marks, verdict: r.verdict,
    usable: r.usable, in_totals: !!r.inTotals, mix: r.mix, upload_duration_s: r.uploadDuration === undefined ? null : r.uploadDuration,
    upload_has_v05: r.uploadOk === undefined ? null : !r.uploadOk,
  }));
  return JSON.stringify({ rows, totals: res.totals, counts: res.counts }, null, 2);
}

function main(argv, injected = {}) {
  const o = { folder: null };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--ref") o.ref = argv[++i];
    else if (a === "--work") o.work = argv[++i];
    else if (a === "--exclude-sha") o.excludeSha = argv[++i];
    else if (a === "--json") o.json = argv[++i];
    else if (a === "--md") o.md = argv[++i];
    else if (!o.folder) o.folder = a;
    else { o.bad = true; }
  }
  if (!o.folder || !o.ref || !o.work || o.bad) {
    console.error("사용: node apps/voice-check/screen.js <폴더> --ref <기준.wav> --work <_work 폴더> [--exclude-sha <파일>] [--json out.json] [--md out.md]");
    return 2;
  }
  let res;
  try { res = run({ ...o, ...injected }); } catch (e) { console.error(`실패: ${e.message}`); return 2; }
  const md = toMarkdown(res);
  console.log(md);
  let code = 0;
  const save = (p, text) => { try { fs.writeFileSync(p, text); console.log(`저장: ${p}`); } catch (e) { code = 2; console.error(`저장 실패: ${p} (${e.message})`); } };
  if (o.md) save(o.md, md);
  if (o.json) save(o.json, toJson(res));
  return code;
}

if (require.main === module) process.exitCode = main(process.argv.slice(2));
module.exports = { run, main, toMarkdown, toJson, nameNeedsReview, twoPitchGroups, noisyBackground, readExcludeShas };
