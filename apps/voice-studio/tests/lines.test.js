// lines.js가 voice/city-dominion/annotation.csv의 앞 다섯 칸과 같은지 확인한다.
// 실행: node apps/voice-studio/tests/lines.test.js
"use strict";
const fs = require("fs");
const path = require("path");
const LINES = require("../lines.js");

function parse(r) {
  const out = []; let cur = "", q = false;
  for (let i = 0; i < r.length; i++) {
    const ch = r[i];
    if (q) { if (ch === '"' && r[i + 1] === '"') { cur += '"'; i++; } else if (ch === '"') q = false; else cur += ch; }
    else if (ch === '"') q = true; else if (ch === ",") { out.push(cur); cur = ""; } else cur += ch;
  }
  out.push(cur); return out;
}
const csv = fs.readFileSync(path.join(__dirname, "../../../voice/city-dominion/annotation.csv"), "utf8")
  .replace(/^﻿/, "").trim().split("\r\n").slice(1).map(parse);
let fail = 0;
if (csv.length !== LINES.length) { fail++; console.log(`FAIL 줄 수 ${csv.length} ≠ ${LINES.length}`); }
csv.forEach((c, i) => {
  const l = LINES[i] || {};
  const want = [l.id, l.key, l.scene, l.dir, l.text];
  if (c.slice(0, 5).join("|") !== want.join("|")) { fail++; console.log(`FAIL ${c[0]} 다름`); }
});
console.log(fail ? `실패 ${fail}건` : `PASS ${LINES.length}줄이 주석 표와 같음`);
process.exitCode = fail ? 1 : 0;
