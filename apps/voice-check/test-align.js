// align.js 테스트. 합성 WAV(사인파 덩어리 + 쉼)를 임시 폴더에 만들고, 끝나면 지운다.
// 실행: node apps/voice-check/test-align.js
"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");
const { align } = require("./align.js");

const RATE = 16000;
let failed = 0;
const ok = (cond, msg) => { if (!cond) { failed++; console.log("실패: " + msg); } else console.log("통과: " + msg); };

// parts: {tone: 초} 또는 {gap: 초}. 앞뒤 1초 무음 포함.
function build(parts) {
  const all = [{ gap: 1 }, ...parts, { gap: 1 }];
  const total = all.reduce((s, p) => s + Math.round((p.tone || p.gap) * RATE), 0);
  const x = new Float32Array(total);
  let pos = 0;
  for (const p of all) {
    const n = Math.round((p.tone || p.gap) * RATE);
    if (p.tone) for (let i = 0; i < n; i++) x[pos + i] = 0.3 * Math.sin(2 * Math.PI * 220 * i / RATE);
    pos += n;
  }
  return x;
}

function writeWav(file, x) {
  const data = Buffer.alloc(x.length * 2);
  for (let i = 0; i < x.length; i++) data.writeInt16LE(Math.round(x[i] * 32767), i * 2);
  const h = Buffer.alloc(44);
  h.write("RIFF", 0); h.writeUInt32LE(36 + data.length, 4); h.write("WAVEfmt ", 8);
  h.writeUInt32LE(16, 16); h.writeUInt16LE(1, 20); h.writeUInt16LE(1, 22);
  h.writeUInt32LE(RATE, 24); h.writeUInt32LE(RATE * 2, 28); h.writeUInt16LE(2, 32); h.writeUInt16LE(16, 34);
  h.write("data", 36); h.writeUInt32LE(data.length, 40);
  fs.writeFileSync(file, Buffer.concat([h, data]));
}

// 초당 5음절이 되게 글자 수를 정한 가짜 대본
const mk = (sec, i) => ({ no: String(i + 1).padStart(3, "0"), key: "k" + (i + 1), text: "가나다라마 ".repeat(Math.round(sec * 5 / 5)).trim() + "!" });
const script = (secs) => ({ lines: secs.map(mk) });
const near = (a, b) => Math.abs(a - b) < 0.1;

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "align-test-"));
try {
  // (a) 덩어리 수 = 줄 수
  {
    const secs = [2, 3, 1, 4, 2];
    const parts = [];
    secs.forEach((s, i) => { if (i) parts.push({ gap: 1.5 }); parts.push({ tone: s }); });
    const r = align(build(parts), RATE, script(secs), 1.0);
    let t = 1;
    let exact = r.chunks.length === 5 && r.rows.length === 5;
    secs.forEach((s, i) => {
      exact = exact && near(r.rows[i].start, t) && near(r.rows[i].end, t + s) && r.rows[i].chunks === 1;
      t += s + 1.5;
    });
    ok(exact, "(a) 덩어리 5개 = 줄 5개: 시간이 정확히 맞음");
    ok(r.rows.every((x) => !x.uncertain), "(a) 불확실 표시 없음");
  }

  // (b) 한 줄이 두 덩어리 (중간 1.1초 쉼)
  {
    const secs = [2, 3, 1, 4];
    const parts = [{ tone: 2 }, { gap: 1.5 }, { tone: 1.5 }, { gap: 1.1 }, { tone: 1.5 }, { gap: 1.5 }, { tone: 1 }, { gap: 1.5 }, { tone: 4 }];
    const sc = script(secs);
    sc.lines[1] = mk(3, 1); // 3초 분량 (1.5 + 1.5)
    const r = align(build(parts), RATE, sc, 1.0);
    ok(r.chunks.length === 5, "(b) 덩어리 5개, 줄 4개");
    ok(r.rows[1].chunks === 2 && near(r.rows[1].start, 4.5) && near(r.rows[1].end, 8.6), "(b) 2번 줄이 두 덩어리를 합침");
    ok(r.rows[1].uncertain && /합침/.test(r.rows[1].reasons.join()), "(b) 합친 줄은 불확실 + 이유");
    ok(r.rows[0].chunks === 1 && r.rows[2].chunks === 1 && r.rows[3].chunks === 1, "(b) 나머지 줄은 덩어리 1개");
  }

  // (c) 두 줄이 한 덩어리로 붙음
  {
    const secs = [2, 4, 4, 3];
    const parts = [{ tone: 2 }, { gap: 1.5 }, { tone: 8 }, { gap: 1.5 }, { tone: 3 }];
    const r = align(build(parts), RATE, script(secs), 1.0);
    ok(r.chunks.length === 3 && r.rows.length === 4, "(c) 덩어리 3개, 줄 4개");
    ok(r.rows[1].uncertain && r.rows[2].uncertain, "(c) 쪼갠 두 줄은 불확실");
    ok(/쪼갬/.test(r.rows[1].reasons.join()) && /쪼갬/.test(r.rows[2].reasons.join()), "(c) 이유에 쪼갬이 적힘");
    ok(near(r.rows[1].start, 4.5) && near(r.rows[1].end, 8.5) && near(r.rows[2].start, 8.5) && near(r.rows[2].end, 12.5), "(c) 글자 수 비율로 반씩 나뉨");
    ok(!r.rows[0].uncertain && !r.rows[3].uncertain, "(c) 나머지 줄은 확실");
  }

  // CLI: CSV 칸, BOM
  {
    const secs = [2, 3, 1];
    const parts = [];
    secs.forEach((s, i) => { if (i) parts.push({ gap: 1.5 }); parts.push({ tone: s }); });
    const wav = path.join(tmp, "a.wav"), js = path.join(tmp, "s.json"), csv = path.join(tmp, "o.csv");
    writeWav(wav, build(parts));
    fs.writeFileSync(js, JSON.stringify(script(secs)));
    const p = spawnSync(process.execPath, [path.join(__dirname, "align.js"), wav, js, "--csv", csv, "--min-pause", "1.0"], { encoding: "utf8" });
    ok(p.status === 0 && /덩어리 3개, 대본 3줄/.test(p.stdout), "CLI: 요약 출력, 종료 코드 0");
    const buf = fs.readFileSync(csv);
    ok(buf[0] === 0xef && buf[1] === 0xbb && buf[2] === 0xbf, "CSV: UTF-8 BOM");
    const head = buf.toString("utf8").replace(/^﻿/, "").split(/\r?\n/)[0];
    ok(head === "no,key,text,start_sec,end_sec,dur_sec,syllables,syl_per_sec,chunks,uncertain,reason", "CSV: 칸 이름");
    ok(spawnSync(process.execPath, [path.join(__dirname, "align.js")], { encoding: "utf8" }).status === 2, "CLI: 인자 없으면 종료 코드 2");
  }
} finally {
  fs.rmSync(tmp, { recursive: true, force: true });
}
console.log(failed ? `\n${failed}개 실패` : "\n전부 통과");
process.exitCode = failed ? 1 : 0;
