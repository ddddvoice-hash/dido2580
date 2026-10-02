// profile.js, trim.js 테스트. 합성 신호만 쓰고 임시 파일은 끝나면 지운다.
// 실행: node apps/voice-check/test-profile.js
"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const prof = require("./profile.js");
const trimmer = require("./trim.js");
const check = require("./check.js");

let pass = 0, fail = 0;
function ok(cond, name, extra) {
  if (cond) { pass++; console.log(`ok   ${name}`); } else { fail++; console.log(`FAIL ${name}${extra ? " | " + extra : ""}`); }
}

const RATE = 48000;
// 조각 목록으로 신호 만들기. {sec, f0(시작), f1(끝, 없으면 f0), amp} 또는 {sec, silence:true}
function build(parts, harmonics = [1, 0.5, 0.25]) {
  const total = parts.reduce((a, p) => a + p.sec, 0);
  const out = new Float32Array(Math.round(total * RATE));
  let pos = 0, phase = 0;
  for (const p of parts) {
    const n = Math.round(p.sec * RATE);
    if (!p.silence) {
      for (let i = 0; i < n; i++) {
        const fr = p.f0 + ((p.f1 === undefined ? p.f0 : p.f1) - p.f0) * (i / n);
        phase += 2 * Math.PI * fr / RATE;
        let v = 0;
        harmonics.forEach((h, k) => { v += h * Math.sin((k + 1) * phase); });
        out[pos + i] = v * (p.amp || 0.2) / 1.75;
      }
    }
    pos += n;
  }
  return out;
}

function wavBuffer(samples, bits = 16, extraTail = null) {
  const bps = bits / 8;
  const data = Buffer.alloc(samples.length * bps);
  for (let i = 0; i < samples.length; i++) {
    const v = Math.max(-1, Math.min(1, samples[i]));
    if (bits === 16) data.writeInt16LE(Math.round(v * 32767), i * 2);
    else data.writeIntLE(Math.round(v * 8388607), i * 3, 3);
  }
  const h = Buffer.alloc(44);
  h.write("RIFF", 0, "latin1"); h.writeUInt32LE(36 + data.length, 4); h.write("WAVE", 8, "latin1");
  h.write("fmt ", 12, "latin1"); h.writeUInt32LE(16, 16); h.writeUInt16LE(1, 20); h.writeUInt16LE(1, 22);
  h.writeUInt32LE(RATE, 24); h.writeUInt32LE(RATE * bps, 28); h.writeUInt16LE(bps, 32); h.writeUInt16LE(bits, 34);
  h.write("data", 36, "latin1"); h.writeUInt32LE(data.length, 40);
  return Buffer.concat([h, data, extraTail || Buffer.alloc(0)]);
}

const near = (a, b, tol) => Math.abs(a - b) <= tol;

// 1. F0 추정: 알려진 주파수(사인, 하모닉) 오차 3% 이내
for (const [hz, harm, label] of [[120, [1], "사인 120Hz"], [220, [1], "사인 220Hz"], [150, [1, 0.5, 0.25], "하모닉 150Hz"],
  [100, [1, 0.8, 0.6, 0.4], "하모닉 100Hz"], [300, [1, 0.5], "하모닉 300Hz"]]) {
  const sig = build([{ sec: 1, silence: true }, { sec: 3, f0: hz }, { sec: 1, silence: true }], harm);
  const p = prof.profile(sig, RATE, 0.2);
  ok(near(p.pitch.medianHz, hz, hz * 0.03), `F0 ${label}: 중간값 ${p.pitch.medianHz && p.pitch.medianHz.toFixed(1)}Hz`);
  ok(near(p.pitch.meanHz, hz, hz * 0.03), `F0 ${label}: 평균 ${p.pitch.meanHz && p.pitch.meanHz.toFixed(1)}Hz`);
}

// 2. 쉼 개수와 길이
{
  const sig = build([{ sec: 1, silence: true }, { sec: 1, f0: 150 }, { sec: 0.4, silence: true }, { sec: 1, f0: 150 },
    { sec: 0.8, silence: true }, { sec: 1, f0: 150 }, { sec: 1.5, silence: true }, { sec: 1, f0: 150 },
    { sec: 2.4, silence: true }, { sec: 1, f0: 150 }, { sec: 1, silence: true }]);
  const p = prof.profile(sig, RATE, 0.2);
  const Z = p.pauses;
  ok(Z.count === 4, `쉼 개수 4 (실제 ${Z.count})`);
  ok(near(Z.maxS, 2.4, 0.05), `쉼 최대 2.4초 (실제 ${Z.maxS && Z.maxS.toFixed(2)})`);
  ok(near(Z.medianS, 1.15, 0.05), `쉼 중간값 1.15초 (실제 ${Z.medianS && Z.medianS.toFixed(2)})`);
  ok(Z.bins["0.25-0.5"] === 1 && Z.bins["0.5-1"] === 1 && Z.bins["1-2"] === 1 && Z.bins["2+"] === 1,
    `쉼 구간별 1/1/1/1 (실제 ${JSON.stringify(Z.bins)})`);
  // 분당: 첫~끝 말소리 span = 1+0.4+1+0.8+1+1.5+1+2.4+1 = 10.1초
  ok(near(Z.perMinute, 4 / (10.1 / 60), 0.5), `분당 쉼 횟수 (실제 ${Z.perMinute && Z.perMinute.toFixed(1)})`);
}

// 3. 문장 끝 음높이: 내림, 평탄, 올림
{
  const mk = (a, b) => [{ sec: 2, f0: a, f1: b }, { sec: 1, silence: true }];
  const down = build([{ sec: 1, silence: true }, ...mk(200, 120), ...mk(200, 120), { sec: 1, f0: 150 }, { sec: 1, silence: true }]);
  const flat = build([{ sec: 1, silence: true }, ...mk(150, 150), ...mk(150, 150), { sec: 1, f0: 150 }, { sec: 1, silence: true }]);
  const up = build([{ sec: 1, silence: true }, ...mk(120, 200), ...mk(120, 200), { sec: 1, f0: 150 }, { sec: 1, silence: true }]);
  const d = prof.profile(down, RATE, 0.2).sentenceEnd;
  const fl = prof.profile(flat, RATE, 0.2).sentenceEnd;
  const u = prof.profile(up, RATE, 0.2).sentenceEnd;
  ok(d.count === 2 && d.down === 2 && d.meanChangeSemitones < -2, `끝에서 내려가는 신호는 내림 (${JSON.stringify(d)})`);
  ok(fl.count === 2 && fl.flat === 2, `평탄 신호는 평탄 (${JSON.stringify(fl)})`);
  ok(u.count === 2 && u.up === 2 && u.meanChangeSemitones > 2, `끝에서 올라가는 신호는 올림 (${JSON.stringify(u)})`);
  // 0.7초 미만 쉼 앞은 문장 끝으로 세지 않음
  const short = build([{ sec: 1, silence: true }, { sec: 2, f0: 200, f1: 120 }, { sec: 0.6, silence: true }, { sec: 2, f0: 150 }, { sec: 1, silence: true }]);
  ok(prof.profile(short, RATE, 0.2).sentenceEnd.count === 0, "0.6초 쉼은 문장 끝으로 세지 않음");
}

// 4. 음절(추정): 5Hz 변조(0.2초 주기) 20번 -> 20개 안팎
{
  const base = build([{ sec: 4, f0: 150 }]);
  for (let i = 0; i < base.length; i++) {
    const ph = (i / RATE) * 5 % 1;
    const w = 0.5 * (1 - Math.cos(2 * Math.PI * ph));
    base[i] *= w * w;
  }
  const sig = new Float32Array(base.length + 2 * RATE);
  sig.set(base, RATE);
  const p = prof.profile(sig, RATE, 0.2);
  ok(near(p.syllables.count, 20, 2) && p.syllables.estimated, `음절 추정 20 +-2 (실제 ${p.syllables.count})`);
}

// 5. 크기: 진폭 0.1 사인파의 RMS
{
  const sig = build([{ sec: 1, silence: true }, { sec: 3, f0: 200, amp: 0.1 * 1.75 }, { sec: 1, silence: true }], [1]);
  // build는 amp/1.75를 곱함 -> 진폭 0.1 사인
  const p = prof.profile(sig, RATE, 0.1);
  ok(near(p.loudness.speechRmsDb, 20 * Math.log10(0.1 / Math.SQRT2), 0.6), `말소리 RMS ${p.loudness.speechRmsDb.toFixed(1)} dBFS`);
  ok(near(p.loudness.peakDb, -20, 0.01), "최대 dBFS는 넘겨준 peak 기준");
  ok(p.loudness.overallRmsDb < p.loudness.speechRmsDb, "전체 RMS가 말소리 RMS보다 작음");
}

// 6. trim: 뒤 여백 자르기, 앞부분 바이트 동일, 입력 보호
{
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "trimtest-"));
  try {
    const inF = path.join(dir, "in.wav"), outF = path.join(dir, "out.wav");
    const sig = build([{ sec: 1, silence: true }, { sec: 2, f0: 150 }, { sec: 3, silence: true }]);
    const extra = Buffer.concat([Buffer.from("LIST", "latin1"), Buffer.from([4, 0, 0, 0, 1, 2, 3, 4])]);
    const orig = wavBuffer(sig, 24, extra);
    fs.writeFileSync(inF, orig);
    const r = trimmer.trim(inF, outF, 0.8);
    ok(near(r.newTail, 0.8, 0.001) && near(r.oldTail, 3, 0.05), `뒤 여백 ${r.oldTail.toFixed(2)} -> ${r.newTail.toFixed(2)}초`);
    const out = fs.readFileSync(outF);
    ok(fs.readFileSync(inF).equals(orig), "입력 파일은 그대로");
    const cut = r.dataStart + r.keepBytes;
    ok(out.length === cut, "출력 길이 = 헤더 + 남긴 샘플 (뒤 청크 버림)");
    ok(out.subarray(44, cut).equals(orig.subarray(44, cut)), "남긴 샘플이 바이트 단위로 같음");
    ok(out.subarray(0, 4).equals(orig.subarray(0, 4)) && out.subarray(8, 40).equals(orig.subarray(8, 40)), "헤더 형식 필드 유지");
    ok(out.readUInt32LE(4) === out.length - 8 && out.readUInt32LE(40) === r.keepBytes, "RIFF/data 크기 갱신");
    const res = check.inspect(outF);
    ok(!res.reject.includes("V05") && near(res.tail, 0.8, 0.03), `사본 check: V05 없음, 뒤 여백 ${res.tail.toFixed(2)}`);
    ok(check.inspect(inF).reject.includes("V05"), "원본(테스트용)은 V05");
    let msg = "";
    try { trimmer.trim(inF, inF, 0.8); } catch (e) { msg = e.message; }
    ok(/같습니다/.test(msg), "입력과 출력 경로가 같으면 거부");
    msg = "";
    try { trimmer.trim(inF, outF, 1.5); } catch (e) { msg = e.message; }
    ok(/0~1초/.test(msg), "tail 1초 초과 거부");
    // 이미 짧으면 늘리지 않음
    const r2 = trimmer.trim(outF, path.join(dir, "out2.wav"), 1);
    ok(r2.keepFrames === r2.frames, "이미 짧은 여백은 늘리지 않음");
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
}

console.log(`\n통과 ${pass}개, 실패 ${fail}개`);
process.exitCode = fail ? 1 : 0;
