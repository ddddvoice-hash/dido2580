// align.js 테스트. 합성 WAV(사인파 덩어리 + 쉼)를 임시 폴더에 만들고, 끝나면 지운다.
// 실행: node apps/voice-check/test-align.js
"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");
const { align, countSyllables, orderProblems } = require("./align.js");

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

  // (d) 한 덩어리를 세 줄로 나눌 때 같은 쉼을 다시 쓰지 않는다 (1~11초 덩어리, 5.8~6.2초 쉼)
  {
    const parts = [{ tone: 4.8 }, { gap: 0.4 }, { tone: 4.8 }];
    for (const n of [3, 4]) {
      const sc = { lines: Array.from({ length: n }, (_, i) => ({ no: String(i + 1).padStart(3, "0"), key: "k" + i, text: "", syllables: 10 })) };
      const r = align(build(parts), RATE, sc, 1.0);
      ok(r.chunks.length === 1 && r.rows.length === n, `(d) 덩어리 1개를 ${n}줄로 나눔`);
      ok(r.rows.every((x) => x.end - x.start > 0), `(d) ${n}줄: 모든 줄의 길이가 양수 (${r.rows.map((x) => (x.end - x.start).toFixed(2))})`);
      ok(r.rows.every((x, i) => i === 0 || x.start >= r.rows[i - 1].end - 1e-9), `(d) ${n}줄: 시간 순서가 앞에서 뒤로 이어짐`);
      ok(orderProblems(r.rows).length === 0, `(d) ${n}줄: orderProblems 없음`);
      ok(near(r.rows[0].start, 1) && near(r.rows[n - 1].end, 11), `(d) ${n}줄: 덩어리 처음과 끝에 맞음`);
    }
    ok(orderProblems([{ no: "1", start: 5, end: 6 }, { no: "2", start: 6.2, end: 5.8 }]).join() === "2", "(d) orderProblems가 음수 길이를 찾아냄");
    ok(orderProblems([{ no: "1", start: 5, end: 7 }, { no: "2", start: 6, end: 8 }]).join() === "2", "(d) orderProblems가 겹침을 찾아냄");
  }

  // (e) 경계 쉼 1.2초 기준: 1.2초는 확실, 1.18초는 불확실
  {
    const sc = { lines: [{ no: "001", key: "a", text: "", syllables: 5 }, { no: "002", key: "b", text: "", syllables: 5 }] };
    const edge = align(build([{ tone: 2 }, { gap: 1.2 }, { tone: 2 }]), RATE, sc, 1.0);
    ok(edge.rows.every((x) => !x.uncertain), `(e) 쉼 1.2초는 불확실 아님 (${edge.rows.map((x) => x.reasons)})`);
    const under = align(build([{ tone: 2 }, { gap: 1.18 }, { tone: 2 }]), RATE, sc, 1.0);
    ok(under.rows.every((x) => x.uncertain && /쉼 1\.18/.test(x.reasons.join())), `(e) 쉼 1.18초는 두 줄 모두 불확실 (${under.rows.map((x) => x.reasons)})`);
  }

  // (f) 속도 비율 기준: 중간값의 0.5배 / 2배 경계는 확실, 넘으면 불확실 (초당 5음절 3줄이 중간값)
  {
    const mkRows = (durs) => {
      const parts = [];
      durs.forEach((d, i) => { if (i) parts.push({ gap: 1.5 }); parts.push({ tone: d }); });
      const sc = { lines: durs.map((_, i) => ({ no: String(i + 1).padStart(3, "0"), key: "k" + i, text: "", syllables: 5 })) };
      return align(build(parts), RATE, sc, 1.0).rows;
    };
    const edge = mkRows([1, 1, 1, 2, 0.5]);   // 5, 5, 5, 2.5(정확히 0.5배), 10(정확히 2배)
    ok(edge.every((x) => !x.uncertain), `(f) 정확히 0.5배와 2배는 불확실 아님 (${edge.map((x) => x.rate.toFixed(2) + ":" + x.reasons)})`);
    const out = mkRows([1, 1, 1, 2.1, 0.48]); // 2.38(0.5배 미만), 10.4(2배 초과)
    ok(out.slice(0, 3).every((x) => !x.uncertain), "(f) 보통 속도 줄은 확실");
    ok(/0\.5배 미만/.test(out[3].reasons.join()), "(f) 0.5배 미만이면 불확실 + 이유");
    ok(/2배 초과/.test(out[4].reasons.join()), "(f) 2배 초과면 불확실 + 이유");
  }

  // (g) 음절 수: NFD로 분해한 한글도 같게 센다, syllables 값이 있으면 그 값을 쓴다
  {
    ok(countSyllables("가나다") === 3 && countSyllables("가나다".normalize("NFD")) === 3, "(g) NFC/NFD 같은 음절 수");
    const sc = { lines: [{ no: "001", key: "a", text: "ABC 123", syllables: 4 }, { no: "002", key: "b", text: "가나다" }] };
    const r = align(build([{ tone: 2 }, { gap: 1.5 }, { tone: 2 }]), RATE, sc, 1.0);
    ok(r.rows[0].syllables === 4 && r.rows[1].syllables === 3, "(g) 수동 음절 수(syllables)가 우선");
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
