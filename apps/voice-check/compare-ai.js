#!/usr/bin/env node
// AI 복제 목소리 시험 문장과 원본(기준 WAV) 비교표. 외부 패키지 없음.
// 사용: node apps/voice-check/compare-ai.js --ai <폴더> --sentences <csv> --ref <기준.wav> [--md out.md] [--json out.json]
// 파일은 읽기만 합니다. 비WAV는 ffmpeg가 있으면 <폴더>/converted 에 WAV로 변환해 씁니다.
"use strict";

const fs = require("fs");
const path = require("path");
const cp = require("child_process");
const check = require("./check.js");
const prof = require("./profile.js");

// ---- 점수 규칙(대표가 바꿀 수 있게 상수로) -----------------------------------
// 점수는 rubric.json의 scale(0~2)과 같습니다. 기준 대비 비율 차이로 매깁니다.
const RULES = {
  pace: { good: 0.15, ok: 0.30 },   // 초당 음절이 기준 대비 ±15% 안이면 2, ±30% 안이면 1, 밖이면 0
  pause: { good: 0.25, ok: 0.50 },  // 쉼 중간값이 기준 대비 ±25% 안이면 2, ±50% 안이면 1, 밖·쉼 없음이면 0
  shortPunctMax: 1,                 // 쉼표·마침표 등이 이 개수 이하인 짧은 문장에서 쉼이 없으면 '해당 없음'
  refScore: 2,                      // 기준(원본) 자신의 점수
};
const PUNCT_RE = /[,.?!，。？！…、]/g;
const EPS = 1e-9;
const NO_SERVICE = "대표 기입 필요";
const EMPTY_MSG = "대표가 시험 문장 10개를 AI로 만들어 _work\\ai 에 A01.wav처럼 저장하면 시작합니다.";
const HUMAN_CELL = "대표가 듣고 채점";

// ---- CSV ---------------------------------------------------------------------

// 따옴표 안의 쉼표·줄바꿈·"" 를 처리하는 CSV 파서. BOM은 버린다.
function parseCsv(text) {
  if (text.charCodeAt(0) === 0xfeff) text = text.slice(1);
  const rows = [];
  let row = [], cur = "", q = false, any = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) {
      if (c === '"') { if (text[i + 1] === '"') { cur += '"'; i++; } else q = false; }
      else cur += c;
    } else if (c === '"') { q = true; any = true; }
    else if (c === ",") { row.push(cur); cur = ""; any = true; }
    else if (c === "\n" || c === "\r") {
      if (c === "\r" && text[i + 1] === "\n") i++;
      if (any || cur !== "") { row.push(cur); rows.push(row); }
      row = []; cur = ""; any = false;
    } else { cur += c; any = true; }
  }
  if (any || cur !== "") { row.push(cur); rows.push(row); }
  return rows;
}

function readSentences(file) {
  const rows = parseCsv(fs.readFileSync(file, "utf8"));
  if (rows.length < 2) throw new Error("시험 문장 CSV에 줄이 없습니다");
  const head = rows[0].map((s) => s.trim());
  const idx = (name) => head.indexOf(name);
  const [iNo, iUse, iText, iCheck] = ["번호", "용도", "문장", "확인할 점"].map(idx);
  if (iNo < 0 || iText < 0) throw new Error("CSV 머리글에 '번호', '문장'이 필요합니다");
  return rows.slice(1).filter((r) => (r[iNo] || "").trim()).map((r) => ({
    no: r[iNo].trim(), use: iUse >= 0 ? r[iUse] || "" : "", text: r[iText] || "", note: iCheck >= 0 ? r[iCheck] || "" : "",
  }));
}

// ---- 기준표(rubric) ------------------------------------------------------------

function readVoiceCriteria(file) {
  const j = JSON.parse(fs.readFileSync(file, "utf8"));
  if (!Array.isArray(j.voice_criteria)) throw new Error("rubric.json에 voice_criteria가 없습니다");
  return j.voice_criteria.map((c) => ({ id: c.id, name: c.name, measure: c.measure }));
}

// ---- 점수 ----------------------------------------------------------------------

function countHangul(text) {
  let n = 0;
  for (const ch of String(text).normalize("NFC")) { const c = ch.codePointAt(0); if (c >= 0xac00 && c <= 0xd7a3) n++; }
  return n;
}

function bandScore(value, ref, rule) {
  if (!Number.isFinite(value) || !Number.isFinite(ref) || ref <= 0) return 0;
  const d = Math.abs(value / ref - 1);
  if (d <= rule.good + EPS) return 2;
  if (d <= rule.ok + EPS) return 1;
  return 0;
}
// 반환 {score(0~2 또는 null), label}
function scorePace(sylPerSec, refSylPerSec) {
  const s = bandScore(sylPerSec, refSylPerSec, RULES.pace);
  return { score: s, label: String(s) };
}
function scorePause(pauseMedianS, refPauseMedianS, text) {
  if (pauseMedianS === null || pauseMedianS === undefined) {
    const n = (String(text || "").match(PUNCT_RE) || []).length;
    if (n <= RULES.shortPunctMax) return { score: null, label: "해당 없음" };
    return { score: 0, label: "0 (쉼 없음)" };
  }
  const s = bandScore(pauseMedianS, refPauseMedianS, RULES.pause);
  return { score: s, label: String(s) };
}

// ---- 파일 찾기 -----------------------------------------------------------------

function hasFfmpegDefault() {
  try { return cp.spawnSync("ffmpeg", ["-version"], { stdio: "ignore" }).status === 0; } catch (e) { return false; }
}
function convertDefault(inFile, outFile) {
  const r = cp.spawnSync("ffmpeg", ["-y", "-i", inFile, "-ac", "1", "-c:a", "pcm_s24le", outFile], { stdio: "ignore" });
  if (r.status !== 0) throw new Error("ffmpeg 변환 실패");
}

// 폴더 바로 아래에서 이름(확장자 앞)이 번호와 같은 파일. 대소문자 무시, WAV 우선.
function findFile(no, listing) {
  if (!listing) return null;
  const hits = listing.filter((n) => path.basename(n, path.extname(n)).toLowerCase() === no.toLowerCase());
  hits.sort((a, b) => {
    const wa = path.extname(a).toLowerCase() === ".wav" ? 0 : 1, wb = path.extname(b).toLowerCase() === ".wav" ? 0 : 1;
    return wa - wb || a.localeCompare(b);
  });
  return hits.length ? hits[0] : null;
}

function readService(dir) {
  try {
    const t = fs.readFileSync(path.join(dir, "service.txt"), "utf8").replace(/^﻿/, "");
    const first = t.split(/\r?\n/)[0].trim();
    return first || NO_SERVICE;
  } catch (e) { return NO_SERVICE; }
}

// ---- 실행 ----------------------------------------------------------------------

const semis = (a, b) => 12 * Math.log2(a / b);

function refSummary(p) {
  return {
    pitchHz: p.pitch.medianHz, pauseMedianS: p.pauses.count ? p.pauses.medianS : null,
    endDownRatio: p.sentenceEnd.downRatio, endCount: p.sentenceEnd.count,
    sylPerSec: p.syllables.perSecSpoken,
  };
}

function run(opts) {
  const sentences = readSentences(opts.sentences);
  const criteria = readVoiceCriteria(opts.rubric);
  const refName = path.basename(opts.ref);
  const refP = opts.refProfile || prof.profileFile(opts.ref);
  const ref = refSummary(refP);
  let listing = null;
  try { listing = fs.readdirSync(opts.ai, { withFileTypes: true }).filter((d) => d.isFile()).map((d) => d.name); } catch (e) { listing = null; }
  const service = listing ? readService(opts.ai) : NO_SERVICE;
  const hasFfmpeg = opts.hasFfmpeg || hasFfmpegDefault;
  const convert = opts.convert || convertDefault;
  let ffmpegOk = null;
  const auto = criteria.filter((c) => c.measure === "auto").map((c) => c.id);
  const humans = criteria.filter((c) => c.measure !== "auto");

  const rows = sentences.map((s) => {
    const row = {
      no: s.no, use: s.use, text: s.text, note: s.note, file: null, status: "없음",
      duration: null, reject: [], warn: [], pitchHz: null, pitchDiffSt: null, pauseMedianS: null, pauseCount: null,
      endDownRatio: null, endUpCount: null, endCount: null, syllables: countHangul(s.text), spokenSec: null, sylPerSec: null,
      scores: {}, lower: [],
    };
    const name = findFile(s.no, listing);
    if (!name) return row;
    row.file = name;
    let wav = path.join(opts.ai, name);
    if (path.extname(name).toLowerCase() !== ".wav") {
      if (ffmpegOk === null) ffmpegOk = !!hasFfmpeg();
      if (!ffmpegOk) { row.status = "변환 불가"; return row; }
      const dir = path.join(opts.ai, "converted");
      try {
        fs.mkdirSync(dir, { recursive: true });
        const out = path.join(dir, path.basename(name, path.extname(name)) + ".wav");
        convert(wav, out);
        wav = out;
      } catch (e) { row.status = "변환 불가"; return row; }
    }
    try {
      const c = check.inspect(wav);
      row.duration = c.duration;
      row.reject = c.reject;
      row.warn = c.warn.filter((w) => w !== "NAME");
      const p = prof.profileFile(wav);
      row.status = "측정함";
      row.pitchHz = p.pitch.medianHz;
      if (row.pitchHz && ref.pitchHz) row.pitchDiffSt = semis(row.pitchHz, ref.pitchHz);
      row.pauseCount = p.pauses.count;
      row.pauseMedianS = p.pauses.count ? p.pauses.medianS : null;
      row.endCount = p.sentenceEnd.count;
      row.endDownRatio = p.sentenceEnd.downRatio;
      row.endUpCount = p.sentenceEnd.up;
      row.spokenSec = p.syllables.spokenSec;
      row.sylPerSec = row.spokenSec > 0 ? row.syllables / row.spokenSec : null;
    } catch (e) { row.status = "읽기 실패"; row.error = e.message; return row; }
    if (auto.includes("pace")) row.scores.pace = scorePace(row.sylPerSec, ref.sylPerSec);
    if (auto.includes("pause")) row.scores.pause = scorePause(row.pauseMedianS, ref.pauseMedianS, s.text);
    for (const c of criteria) {
      if (c.measure !== "auto") continue;
      const sc = row.scores[c.id];
      if (sc && sc.score !== null && sc.score < RULES.refScore) row.lower.push(`${c.name}(${sc.score}<${RULES.refScore})`);
    }
    return row;
  });
  return { refName, ref, service, aiDir: opts.ai, folderExists: !!listing, criteria, humans, rows, anyFile: rows.some((r) => r.file) };
}

// ---- 출력 ----------------------------------------------------------------------

const f = (x, d) => (x === null || x === undefined || !Number.isFinite(x) ? "-" : x.toFixed(d));
const esc = (s) => String(s).replace(/\|/g, "\\|").replace(/\r?\n/g, " ");
const sign = (x, d) => (x >= 0 ? "+" : "") + x.toFixed(d);
const pctText = (x) => (x === null || x === undefined ? "-" : `${Math.round(x * 100)}%`);

function measuredNote(r) {
  const out = [];
  const t = r.note;
  if (/올림/.test(t)) out.push(r.endCount ? `끝 올림 ${r.endUpCount}/${r.endCount}곳(마지막 끝은 못 잼)` : "문장 끝 0곳");
  if (/내림/.test(t)) out.push(r.endCount ? `끝 내림 ${pctText(r.endDownRatio)} (문장 끝 ${r.endCount}곳)` : "문장 끝 0곳");
  if (/쉼/.test(t)) out.push(r.pauseMedianS === null ? "쉼 없음" : `쉼 중간값 ${f(r.pauseMedianS, 2)}초`);
  if (/음높이/.test(t) && r.pitchDiffSt !== null) out.push(`음높이 ${sign(r.pitchDiffSt, 1)}반음`);
  if (/속도/.test(t)) out.push(`초당 음절 ${f(r.sylPerSec, 1)}`);
  return out.length ? ` → 측정: ${out.join(", ")}` : "";
}

function rowCells(res, r) {
  const humanCell = res.humans.map((h) => `${h.name}: ${HUMAN_CELL}`).join(" / ");
  const scoreCell = (id) => (r.scores[id] ? r.scores[id].label : "-");
  const stateCell = r.file ? `${r.file}${r.status === "측정함" ? "" : ` (${r.status})`}` : "없음";
  const m = r.status === "측정함";
  const reject = m ? (r.reject.length ? r.reject.join(",") : "없음") + (r.warn.length ? ` / 경고 ${r.warn.join(",")}` : "") : "-";
  return [
    r.no, r.use, stateCell, m ? `${f(r.duration, 1)}초` : "-", reject,
    m ? `${f(r.pitchHz, 1)}Hz (${r.pitchDiffSt === null ? "-" : sign(r.pitchDiffSt, 1) + "반음"})` : "-",
    m ? (r.pauseMedianS === null ? "쉼 없음" : `${f(r.pauseMedianS, 2)}초 (${r.pauseCount}개)`) : "-",
    m ? (r.endCount ? `${pctText(r.endDownRatio)} (문장 끝 ${r.endCount}곳)` : "문장 끝 0곳") : "-",
    m ? `${f(r.sylPerSec, 2)} (${r.syllables}음절/${f(r.spokenSec, 1)}초)` : "-",
    scoreCell("pace"), scoreCell("pause"), m ? humanCell : "-",
    m ? (r.lower.length ? r.lower.join(", ") : "없음") : "-",
    r.note + (m ? measuredNote(r) : ""),
  ];
}

function toMarkdown(res) {
  const R = res.ref;
  const base = path.basename(res.refName, ".wav");
  const L = [];
  L.push(`기준(${base}): 음높이 중간값 ${f(R.pitchHz, 1)}Hz, 쉼 중간값 ${f(R.pauseMedianS, 2)}초, 문장 끝 내림 ${pctText(R.endDownRatio)} (문장 끝 ${R.endCount}곳), 초당 음절 ${f(R.sylPerSec, 2)} (추정, 말한 시간 기준)`);
  L.push("");
  L.push(`서비스 이름: ${res.service}`);
  L.push("");
  if (!res.anyFile) {
    L.push(EMPTY_MSG);
    return L.join("\n") + "\n";
  }
  L.push("점수 규칙 (0~2점. 바꾸려면 compare-ai.js 맨 위 RULES를 고칩니다)");
  L.push(`- 속도(pace): 초당 음절이 기준 대비 ±${RULES.pace.good * 100}% 안이면 2, ±${RULES.pace.ok * 100}% 안이면 1, 밖이면 0`);
  L.push(`- 쉼(pause): 쉼 중간값이 기준 대비 ±${RULES.pause.good * 100}% 안이면 2, ±${RULES.pause.ok * 100}% 안이면 1, 밖이거나 쉼 없음이면 0. 쉼표·마침표 등이 ${RULES.shortPunctMax}개 이하인 짧은 문장에서 쉼이 없으면 '해당 없음'`);
  L.push(`- 기준(${base}) 자신의 점수는 정의상 속도 ${RULES.refScore}, 쉼 ${RULES.refScore}. AI 점수가 이보다 낮으면 '원본보다 낮은 항목'에 적습니다.`);
  L.push(`- ${res.humans.map((h) => h.name).join(", ")}은(는) 자동으로 재지 않습니다. 대표가 듣고 채점합니다.`);
  L.push("- 초당 음절 = 문장의 한글 음절 수 ÷ 말한 시간. 기준 값은 추정치라 재는 방식이 서로 다릅니다. 문장 끝은 1~2곳뿐이라 비율이 거칩니다.");
  L.push("");
  const head = ["번호", "용도", "파일", "길이", "반려", "음높이(기준과 차이)", "쉼 중간값", "문장 끝 내림", "초당 음절", "속도(pace)", "쉼(pause)", "사람 채점", "원본보다 낮은 항목", "확인할 점"];
  L.push("| " + head.join(" | ") + " |");
  L.push("|" + head.map(() => "---").join("|") + "|");
  for (const r of res.rows) L.push("| " + rowCells(res, r).map(esc).join(" | ") + " |");
  return L.join("\n") + "\n";
}

function toJson(res) {
  return JSON.stringify({ refName: res.refName, ref: res.ref, service: res.service, rules: RULES, rows: res.rows }, null, 2);
}

function main(argv, injected = {}) {
  const o = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--ai") o.ai = argv[++i];
    else if (a === "--sentences") o.sentences = argv[++i];
    else if (a === "--ref") o.ref = argv[++i];
    else if (a === "--md") o.md = argv[++i];
    else if (a === "--json") o.json = argv[++i];
    else o.bad = true;
  }
  if (!o.ai || !o.sentences || !o.ref || o.bad) {
    console.error("사용: node apps/voice-check/compare-ai.js --ai <폴더> --sentences <csv> --ref <기준.wav> [--md out.md] [--json out.json]");
    return 2;
  }
  o.rubric = path.join(__dirname, "..", "warmth-scorer", "rubric.json");
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
module.exports = { run, main, toMarkdown, toJson, parseCsv, readSentences, readVoiceCriteria, countHangul, scorePace, scorePause, findFile, readService, RULES, NO_SERVICE, EMPTY_MSG };
