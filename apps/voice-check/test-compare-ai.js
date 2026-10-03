// compare-ai.js 테스트. 합성 WAV만 쓰고 임시 폴더는 끝나면 지운다.
// 실행: node apps/voice-check/test-compare-ai.js
"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const crypto = require("crypto");
const cmp = require("./compare-ai.js");

let pass = 0, fail = 0;
function ok(cond, name, extra) {
  if (cond) { pass++; console.log(`ok   ${name}`); } else { fail++; console.log(`FAIL ${name}${extra ? " | " + extra : ""}`); }
}

const RATE = 48000;
function build(parts) {
  const total = parts.reduce((a, p) => a + p.sec, 0);
  const out = new Float32Array(Math.round(total * RATE));
  let pos = 0, phase = 0;
  for (const p of parts) {
    const n = Math.round(p.sec * RATE);
    if (!p.silence) {
      for (let i = 0; i < n; i++) {
        phase += 2 * Math.PI * p.f0 / RATE;
        out[pos + i] = (Math.sin(phase) + 0.5 * Math.sin(2 * phase) + 0.25 * Math.sin(3 * phase)) * 0.2 / 1.75;
      }
    }
    pos += n;
  }
  return out;
}
function wavBuffer(samples) {
  const data = Buffer.alloc(samples.length * 2);
  for (let i = 0; i < samples.length; i++) data.writeInt16LE(Math.round(Math.max(-1, Math.min(1, samples[i])) * 32767), i * 2);
  const h = Buffer.alloc(44);
  h.write("RIFF", 0, "latin1"); h.writeUInt32LE(36 + data.length, 4); h.write("WAVE", 8, "latin1");
  h.write("fmt ", 12, "latin1"); h.writeUInt32LE(16, 16); h.writeUInt16LE(1, 20); h.writeUInt16LE(1, 22);
  h.writeUInt32LE(RATE, 24); h.writeUInt32LE(RATE * 2, 28); h.writeUInt16LE(2, 32); h.writeUInt16LE(16, 34);
  h.write("data", 36, "latin1"); h.writeUInt32LE(data.length, 40);
  return Buffer.concat([h, data]);
}
// 말소리 2토막(2초씩, 사이 0.6초 쉼)
const TWO = () => wavBuffer(build([{ sec: 0.5, silence: true }, { sec: 2, f0: 150 }, { sec: 0.6, silence: true }, { sec: 2, f0: 150 }, { sec: 0.5, silence: true }]));
// 말소리 1토막(쉼 없음)
const ONE = () => wavBuffer(build([{ sec: 0.5, silence: true }, { sec: 3, f0: 150 }, { sec: 0.5, silence: true }]));
const sha = (file) => crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");

const FAKE_REF = {
  pitch: { medianHz: 150 }, pauses: { count: 30, medianS: 0.6 },
  sentenceEnd: { downRatio: 0.85, count: 79 }, syllables: { perSecSpoken: 5 },
};
const rubric = path.join(__dirname, "..", "warmth-scorer", "rubric.json");
const rubricSha = sha(rubric);

// 1. CSV 파싱: BOM, 따옴표 안 쉼표, "" 이스케이프, 따옴표 안 줄바꿈, CRLF
{
  const rows = cmp.parseCsv('﻿번호,용도,문장,확인할 점\r\nA01,비서,"안녕하세요, 저는 ""디도""예요.","a, b"\r\nA02,비서,쉼표 없음,"두 줄\n짜리"\r\n');
  ok(rows.length === 3 && rows[0][0] === "번호", "CSV: BOM 제거, 3줄");
  ok(rows[1].length === 4 && rows[1][2] === '안녕하세요, 저는 "디도"예요.' && rows[1][3] === "a, b", "CSV: 따옴표 안 쉼표와 \"\" 처리");
  ok(rows[2][3] === "두 줄\n짜리", "CSV: 따옴표 안 줄바꿈");
  const real = cmp.readSentences(path.join(__dirname, "..", "..", "voice", "test-sentences.csv"));
  ok(real.length === 10 && real[0].no === "A01" && real[9].no === "B05", "실제 CSV: 10문장 A01~B05");
  ok(real[0].text.startsWith("안녕하세요, 저는 디도") && real[0].note.includes("질문 끝은 살짝 올림"), "실제 CSV: 쉼표 든 문장과 확인할 점 칸");
}

// 2. 한글 음절 수: NFC, 숫자·영문 제외
ok(cmp.countHangul("안녕 abc 123, 해요.") === 4, "한글 음절만 센다");
ok(cmp.countHangul("한글".normalize("NFD")) === 2, "NFD 입력도 NFC로 센다");

// 3. pace 경계
{
  const s = (v) => cmp.scorePace(v, 5).score;
  ok(s(5) === 2 && s(5.75) === 2 && s(4.25) === 2, "pace: ±15% 경계 2점");
  ok(s(5.76) === 1 && s(4.24) === 1 && s(6.5) === 1 && s(3.5) === 1, "pace: ±15% 밖 ~ ±30% 경계 1점");
  ok(s(6.51) === 0 && s(3.49) === 0 && s(10) === 0, "pace: ±30% 밖 0점");
}
// 4. pause 경계
{
  const s = (v, t) => cmp.scorePause(v, 0.6, t || "가, 나. 다.");
  ok(s(0.6).score === 2 && s(0.75).score === 2 && s(0.45).score === 2, "pause: ±25% 경계 2점");
  ok(s(0.76).score === 1 && s(0.44).score === 1 && s(0.9).score === 1 && s(0.3).score === 1, "pause: ±50% 경계 1점");
  ok(s(0.91).score === 0 && s(0.29).score === 0, "pause: ±50% 밖 0점");
  ok(s(null).score === 0 && /쉼 없음/.test(s(null).label), "pause: 쉼 없음은 0점 (구두점 여럿)");
  const na = s(null, "네.");
  ok(na.score === null && na.label === "해당 없음", "pause: 구두점 하나뿐인 짧은 문장은 해당 없음");
  ok(s(0.5, "네.").score === 2, "pause: 쉼이 있으면 짧은 문장도 점수 매김");
}

// 5. 통합: 폴더 없음 / 일부만 / 대소문자 / service.txt / 낮음 / human 비어 있음
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "cmpai-"));
try {
  const csv = path.join(tmp, "s.csv");
  const t20 = "가나다라마바사아자차카타파하가나다라마바"; // 20음절
  const t40 = t20 + t20;
  fs.writeFileSync(csv, "﻿번호,용도,문장,확인할 점\n" + [
    `A01,비서,"${t20}, 가나.","질문 끝은 올림, 앞 문장 끝은 내림"`,
    `A02,비서,"${t40}, 가나, 다라.","쉼표 자리 쉼이 있는지"`,
    `A03,상담,네.,짧은 문장`,
    `A04,상담,"가, 나, 다, 라.",쉼이 있는지`,
    `A05,상담,"${t20}, 가나.",변환 확인`,
  ].join("\r\n") + "\n");
  const refWav = path.join(tmp, "ref.wav");
  const base = { sentences: csv, rubric, ref: refWav, refProfile: FAKE_REF, hasFfmpeg: () => false };

  // 5-1 폴더 없음
  const missing = path.join(tmp, "nodir");
  let res = cmp.run({ ...base, ai: missing });
  ok(res.rows.length === 5 && res.rows.every((r) => r.status === "없음" && r.file === null), "폴더 없음: 전부 '없음'");
  ok(!fs.existsSync(missing), "폴더 없음: 폴더를 만들지 않음");
  ok(res.service === "대표 기입 필요", "폴더 없음: 서비스 이름은 '대표 기입 필요'");
  let md = cmp.toMarkdown(res);
  ok(md.split("\n")[0].startsWith("기준(ref)") && md.includes(cmp.EMPTY_MSG) && md.includes("서비스 이름: 대표 기입 필요") && !md.includes("| 번호 |"),
    "파일 없음 md: 기준 줄 + 안내 + 서비스 이름만");

  // 5-2 빈 폴더
  const ai = path.join(tmp, "ai");
  fs.mkdirSync(ai);
  res = cmp.run({ ...base, ai });
  ok(!res.anyFile && cmp.toMarkdown(res).includes(cmp.EMPTY_MSG), "빈 폴더: 안내만");

  // 5-3 일부만 (대소문자, service 없음)
  fs.writeFileSync(path.join(ai, "a01.WAV"), TWO());
  fs.writeFileSync(path.join(ai, "A02.wav"), TWO());
  fs.writeFileSync(path.join(ai, "A03.wav"), ONE());
  fs.writeFileSync(path.join(ai, "A04.wav"), ONE());
  fs.writeFileSync(path.join(ai, "A05.mp3"), "not audio");
  res = cmp.run({ ...base, ai });
  const by = Object.fromEntries(res.rows.map((r) => [r.no, r]));
  ok(by.A01.file === "a01.WAV" && by.A01.status === "측정함", "대소문자: a01.WAV를 A01로 찾음");
  ok(res.service === "대표 기입 필요", "service.txt 없음: '대표 기입 필요'");
  ok(by.A05.status === "변환 불가" && !fs.existsSync(path.join(ai, "converted")), "mp3 + ffmpeg 없음: 변환 불가, converted 폴더 안 만듦");
  const spoken = by.A01.spokenSec;
  ok(spoken > 3.5 && spoken < 4.5, `말한 시간 약 4초 (${spoken.toFixed(2)})`);
  ok(Math.abs(by.A01.sylPerSec - 22 / spoken) < 1e-9 && by.A01.syllables === 22, "초당 음절 = 한글 음절 수 / 말한 시간");
  ok(by.A01.scores.pace.score === 2 || by.A01.scores.pace.score === 1, "A01 pace 점수는 2 또는 1(약 5.5음절/초)");
  ok(by.A01.pitchDiffSt !== null && Math.abs(by.A01.pitchDiffSt) < 0.6, `음높이 차이 약 0반음 (${by.A01.pitchDiffSt.toFixed(2)})`);
  ok(by.A01.pauseMedianS > 0.5 && by.A01.pauseMedianS < 0.7 && by.A01.scores.pause.score === 2, "A01 쉼 0.6초 근처, 2점");
  ok(by.A02.syllables === 44 && by.A02.scores.pace.score === 0 && by.A02.lower.some((x) => x.startsWith("속도")), "A02: 음절 많아 pace 0, '원본보다 낮음' 표시");
  ok(by.A01.lower.every((x) => !x.startsWith("쉼")), "A01: 쉼 2점이면 쉼은 낮음 표시 없음");
  ok(by.A03.scores.pause.label === "해당 없음" && by.A03.lower.every((x) => !x.startsWith("쉼")), "A03: 짧은 문장·쉼 없음은 해당 없음 (낮음 표시 안 함)");
  ok(by.A04.scores.pause.score === 0 && by.A04.lower.some((x) => x.startsWith("쉼")), "A04: 쉼 없음 0점, 원본보다 낮음");
  ok(Object.keys(by.A01.scores).sort().join() === "pace,pause", "점수는 auto 항목(pace, pause)만");
  md = cmp.toMarkdown(res);
  ok(md.includes("끝음 처리: 대표가 듣고 채점") && md.includes("호흡·음색: 대표가 듣고 채점"), "human 항목은 '대표가 듣고 채점'으로 비워 둠");
  ok(md.includes("±15%") && md.includes("±25%") && md.includes("정의상"), "md에 점수 규칙 표시");
  ok(md.includes("질문 끝은 올림, 앞 문장 끝은 내림 → 측정:"), "확인할 점은 그대로 + 측정값");
  ok(md.split("\n").filter((l) => l.startsWith("| A")).length === 5, "표에 문장 5줄");
  const ai2 = path.join(tmp, "ai2");
  fs.mkdirSync(ai2);
  fs.writeFileSync(path.join(ai2, "A01.wav"), TWO());
  const md2 = cmp.toMarkdown(cmp.run({ ...base, ai: ai2 }));
  ok(md2.includes("| A02 | 비서 | 없음 |") && md2.includes("| A01 | 비서 | A01.wav |"), "일부만 있음: 없는 번호는 '없음' 칸");

  // 5-4 service.txt, ffmpeg 있음(가짜 변환)
  fs.writeFileSync(path.join(ai, "service.txt"), "﻿가짜서비스\r\n둘째 줄\r\n");
  let converted = 0;
  res = cmp.run({ ...base, ai, hasFfmpeg: () => true, convert: (i, o) => { converted++; fs.writeFileSync(o, TWO()); } });
  ok(res.service === "가짜서비스", "service.txt 첫 줄이 서비스 이름");
  ok(converted === 1 && fs.existsSync(path.join(ai, "converted", "A05.wav")), "ffmpeg 있으면 converted/에 변환");
  ok(res.rows.find((r) => r.no === "A05").status === "측정함", "변환본을 측정");
  ok(cmp.toMarkdown(res).includes("서비스 이름: 가짜서비스"), "md에 서비스 이름");
  fs.writeFileSync(path.join(ai, "service.txt"), "\n");
  ok(cmp.run({ ...base, ai }).service === "대표 기입 필요", "service.txt 비어 있으면 '대표 기입 필요'");

  // 5-5 main: md/json 저장
  const out = path.join(tmp, "o.md"), outJ = path.join(tmp, "o.json");
  const origLog = console.log; console.log = () => {};
  let code;
  try { code = cmp.main(["--ai", ai, "--sentences", csv, "--ref", refWav, "--md", out, "--json", outJ], { refProfile: FAKE_REF, hasFfmpeg: () => false }); } finally { console.log = origLog; }
  ok(code === 0 && fs.existsSync(out) && JSON.parse(fs.readFileSync(outJ, "utf8")).rows.length === 5, "main: md·json 저장, 종료 코드 0");
  const origErr = console.error; console.error = () => {};
  try { ok(cmp.main(["--ai", ai], {}) === 2, "main: 인자 부족이면 종료 코드 2"); } finally { console.error = origErr; }
} finally { fs.rmSync(tmp, { recursive: true, force: true }); }
ok(!fs.existsSync(tmp), "임시 폴더 삭제");
ok(sha(rubric) === rubricSha, "rubric.json은 그대로");

console.log(`\n통과 ${pass}개, 실패 ${fail}개`);
process.exitCode = fail ? 1 : 0;
