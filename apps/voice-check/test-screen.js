// screen.js 테스트. 합성 WAV만 쓰고 임시 폴더는 끝나면 지운다.
// 실행: node apps/voice-check/test-screen.js
"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const crypto = require("crypto");
const screen = require("./screen.js");
const check = require("./check.js");

let pass = 0, fail = 0;
function ok(cond, name, extra) {
  if (cond) { pass++; console.log(`ok   ${name}`); } else { fail++; console.log(`FAIL ${name}${extra ? " | " + extra : ""}`); }
}

const RATE = 48000;
// parts: {sec, f0, f1?} 또는 {sec, silence:true}. 말소리 최대값을 peak(0~1)로 맞춘다. 룸톤 잡음(기본 -80 dBFS)을 깔아 완전 0(V08)을 피한다.
function build(parts, peak, noiseRms = 0.0001, seed = 1) {
  const total = parts.reduce((a, p) => a + p.sec, 0);
  const out = new Float32Array(Math.round(total * RATE));
  let pos = 0, phase = 0;
  for (const p of parts) {
    const n = Math.round(p.sec * RATE);
    if (!p.silence) {
      for (let i = 0; i < n; i++) {
        phase += 2 * Math.PI * (p.f0 + ((p.f1 === undefined ? p.f0 : p.f1) - p.f0) * (i / n)) / RATE;
        out[pos + i] = Math.sin(phase) + 0.5 * Math.sin(2 * phase) + 0.25 * Math.sin(3 * phase);
      }
    }
    pos += n;
  }
  let mx = 0;
  for (let i = 0; i < out.length; i++) mx = Math.max(mx, Math.abs(out[i]));
  for (let i = 0; i < out.length; i++) out[i] *= peak / mx;
  if (noiseRms > 0) {
    let s = seed;
    const rnd = () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
    for (let i = 0; i < out.length; i++) out[i] += (rnd() + rnd() + rnd() + rnd() - 2) * Math.sqrt(3) * noiseRms;
  }
  return out;
}

function wav24(samples) {
  const data = Buffer.alloc(samples.length * 3);
  for (let i = 0; i < samples.length; i++) data.writeIntLE(Math.round(Math.max(-1, Math.min(1, samples[i])) * 8388607), i * 3, 3);
  const h = Buffer.alloc(44);
  h.write("RIFF", 0, "latin1"); h.writeUInt32LE(36 + data.length, 4); h.write("WAVE", 8, "latin1");
  h.write("fmt ", 12, "latin1"); h.writeUInt32LE(16, 16); h.writeUInt16LE(1, 20); h.writeUInt16LE(1, 22);
  h.writeUInt32LE(RATE, 24); h.writeUInt32LE(RATE * 3, 28); h.writeUInt16LE(3, 32); h.writeUInt16LE(24, 34);
  h.write("data", 36, "latin1"); h.writeUInt32LE(data.length, 40);
  return Buffer.concat([h, data]);
}

// 말소리 2초 x 3 + 쉼 0.5초 x 2, 앞 1.5초 룸톤, 뒤 여백 tail초
const speech = (f0, tail, peak = 0.5, noise = 0.0001, seed = 1) => build([
  { sec: 1.5, silence: true }, { sec: 2, f0 }, { sec: 0.5, silence: true }, { sec: 2, f0: f0 * 1.05 },
  { sec: 0.5, silence: true }, { sec: 2, f0 }, { sec: tail, silence: true }], peak, noise, seed);

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "screen-test-"));
const dir = path.join(tmp, "in"), work = path.join(tmp, "work");
fs.mkdirSync(dir);
fs.mkdirSync(work);
const put = (name, buf) => fs.writeFileSync(path.join(dir, name), buf);
const shaOf = (buf) => crypto.createHash("sha256").update(buf).digest("hex");

try {
  const refBuf = wav24(speech(120, 0.6));
  const refFile = path.join(tmp, "ref.wav");
  fs.writeFileSync(refFile, refBuf);

  const passBuf = wav24(speech(125, 0.6));
  put("음성 (1).wav", passBuf);
  put("음성 (2).wav", passBuf);                                  // 중복 (1)
  put("음성 (3).wav", refBuf);                                   // 기준과 중복
  const exBuf = wav24(speech(123, 0.6));
  put("음성 (4).wav", exBuf);                                    // exclude-sha
  fs.writeFileSync(path.join(tmp, "ex.sha256"), `# 제외 목록\n${shaOf(exBuf).toUpperCase()}  # 메모\n\n`);
  put("비밀회사작업.wav", wav24(speech(121, 0.6)));              // 이름 가림
  put("음성 (5).mp3", Buffer.from("not really mp3"));            // 비WAV, ffmpeg 없음
  put("음성 (6).wav", wav24(speech(122, 0.6, 0.5, 0.0056, 7)));  // 계속 시끄러운 배경(-45 dBFS)
  put("음성 (7).wav", wav24(build([
    { sec: 1.5, silence: true }, { sec: 2, f0: 100 }, { sec: 0.5, silence: true }, { sec: 2, f0: 200 },
    { sec: 0.5, silence: true }, { sec: 2, f0: 100 }, { sec: 0.5, silence: true }, { sec: 2, f0: 200 },
    { sec: 0.6, silence: true }], 0.5)));                         // 두 음높이 섞임
  put("음성 (8).wav", wav24(speech(220, 0.6)));                  // 톤 다름
  put("음성 (9).wav", wav24(speech(126, 1.6)));                  // V05만
  put("음성 (10).wav", wav24(speech(124, 0.6, 0.3)));            // 통과
  put("음성 (11).wav", wav24(speech(127, 0.6, 0.97)));           // V02
  put("메모.txt", Buffer.from("무시"));

  const untouched = {};
  for (const f of fs.readdirSync(dir)) untouched[f] = shaOf(fs.readFileSync(path.join(dir, f)));

  const mdOut = path.join(tmp, "out.md"), jsonOut = path.join(tmp, "out.json");
  const upDir = path.join(work, "upload");
  fs.mkdirSync(upDir);
  fs.writeFileSync(path.join(upDir, "남겨둘.txt"), "keep");
  const origLog = console.log;
  console.log = () => {};
  let code;
  try {
    code = screen.main([dir, "--ref", refFile, "--work", work, "--exclude-sha", path.join(tmp, "ex.sha256"), "--md", mdOut, "--json", jsonOut],
      { hasFfmpeg: false });
  } finally { console.log = origLog; }
  ok(code === 0, "종료 코드 0", String(code));
  const md = fs.readFileSync(mdOut, "utf8");
  if (process.env.SCREEN_DEBUG) console.error(md);
  const json = fs.readFileSync(jsonOut, "utf8");
  const data = JSON.parse(json);
  const by = (n) => data.rows.find((r) => r.file === n);
  const v = (n) => (by(n) || {}).verdict;
  const marks = (n) => ((by(n) || {}).marks || []).join(" ");

  ok(v("음성 (1).wav") === "쓸 수 있음" && v("음성 (10).wav") === "쓸 수 있음", "통과 -> 쓸 수 있음");
  ok(v("음성 (2).wav") === "쓰지 않음" && marks("음성 (2).wav") === "중복(=음성 (1).wav)", "중복 표시", marks("음성 (2).wav"));
  ok(marks("음성 (3).wav") === "기준과 중복" && v("음성 (3).wav") === "쓰지 않음", "기준과 중복");
  ok(marks("음성 (4).wav") === "이전에 제외한 파일" && v("음성 (4).wav") === "쓰지 않음", "exclude-sha(대문자·주석 허용)");
  const masked = data.rows.find((r) => r.file.startsWith("이름 가림"));
  ok(masked && masked.marks.join("").includes("대표 확인(이름)") && masked.verdict === "쓰지 않음", "이름 가림 표시");
  ok(!md.includes("비밀회사") && !json.includes("비밀회사"), "이름 가림 파일 이름이 md/json에 없음");
  ok(!fs.existsSync(path.join(upDir, "비밀회사작업.wav")), "이름 가림 파일은 upload에 없음");
  ok(marks("음성 (5).mp3").includes("압축 원본 · 변환 불가(ffmpeg 없음)") && v("음성 (5).mp3") === "쓰지 않음", "비WAV + ffmpeg 없음", marks("음성 (5).mp3"));
  ok(marks("음성 (6).wav").includes("섞임 의심") && v("음성 (6).wav") === "쓰지 않음", "계속 시끄러운 배경", marks("음성 (6).wav"));
  ok(marks("음성 (7).wav").includes("섞임 의심") && v("음성 (7).wav") === "쓰지 않음", "두 음높이 섞임", marks("음성 (7).wav"));
  ok(marks("음성 (8).wav").includes("톤 다름") && v("음성 (8).wav") === "쓰지 않음", "톤 다름", marks("음성 (8).wav"));
  ok(v("음성 (9).wav") === "뒤 여백 자르면 쓸 수 있음" && by("음성 (9).wav").reject.join() === "V05", "V05만", v("음성 (9).wav"));
  ok(v("음성 (11).wav") === "반려" && by("음성 (11).wav").reject.includes("V02"), "V02 -> 반려", v("음성 (11).wav"));
  ok(data.rows[0].file === "ref.wav" && data.rows[0].marks[0] === "기준" && data.rows[0].mix.length === 0, "첫 줄은 기준(섞임 없음)");
  ok(v("메모.txt") === undefined, "오디오가 아닌 파일은 무시");

  // upload 사본
  const ups = fs.readdirSync(upDir).sort();
  const expectUp = ["ref.wav", "음성 (1).wav", "음성 (10).wav", "음성 (9).wav"].sort();
  ok(JSON.stringify(ups.filter((n) => n.endsWith(".wav")).sort()) === JSON.stringify(expectUp), "upload에는 쓸 수 있는 파일과 기준만", ups.join(","));
  ok(fs.existsSync(path.join(upDir, "남겨둘.txt")), "upload에 있던 기존 파일은 지우지 않음");
  for (const n of expectUp) {
    const c = check.inspect(path.join(upDir, n));
    ok(!c.reject.includes("V05"), `upload 사본 V05 없음: ${n}`, c.reject.join());
  }
  const t9 = check.inspect(path.join(upDir, "음성 (9).wav")).tail;
  ok(Math.abs(t9 - 0.8) < 0.03, "V05 파일은 뒤 여백 0.8초로 잘림", String(t9));
  ok(shaOf(fs.readFileSync(path.join(upDir, "음성 (1).wav"))) === shaOf(passBuf), "여백 0.8 이하는 그대로 복사");
  for (const f of Object.keys(untouched)) ok(shaOf(fs.readFileSync(path.join(dir, f))) === untouched[f], `원본 그대로: ${f.includes("비밀") ? "(이름 가림)" : f}`);

  // 합계
  ok(data.totals.withoutRef.count === 3 && data.totals.withRef.count === 4, "합계 개수(기준 미포함 3 / 포함 4)", JSON.stringify(data.totals));
  ok(/기준 미포함 .*10분 못 넘음/.test(md) && md.split("\n")[0].startsWith("| 파일 | 길이 | 반려 코드"), "md 표 머리글과 합계 줄");
  ok(data.counts.nameMasked === 1 && data.counts.duplicates === 2 && data.counts.mixSuspect === 2, "개수 요약", JSON.stringify(data.counts));

  // ffmpeg 있는 경우(주입한 가짜 변환기)
  const dir2 = path.join(tmp, "in2"), work2 = path.join(tmp, "work2");
  fs.mkdirSync(dir2); fs.mkdirSync(work2);
  fs.writeFileSync(path.join(dir2, "음성 (1).m4a"), "fake");
  const origLog2 = console.log; console.log = () => {};
  let res;
  try {
    res = screen.run({ folder: dir2, ref: refFile, work: work2, hasFfmpeg: true, convert: (i, o) => fs.writeFileSync(o, passBuf) });
  } finally { console.log = origLog2; }
  const r2 = res.rows[1];
  ok(r2.marks.includes("압축 원본") && r2.verdict === "쓸 수 있음", "비WAV + ffmpeg 있음(주입)", r2.marks.join());
  ok(fs.existsSync(path.join(work2, "converted", "음성 (1).wav")) && fs.existsSync(path.join(work2, "upload", "음성 (1).wav")), "converted/upload 사본 생성");

  // work 폴더가 입력 폴더 안이면 거부
  let threw = false;
  try { screen.run({ folder: dir, ref: refFile, work: path.join(dir, "w"), hasFfmpeg: false }); } catch (e) { threw = true; }
  ok(threw, "work가 입력 폴더 안이면 거부");
} finally {
  fs.rmSync(tmp, { recursive: true, force: true });
}

console.log(`\n통과 ${pass} / 실패 ${fail}`);
process.exitCode = fail ? 1 : 0;
