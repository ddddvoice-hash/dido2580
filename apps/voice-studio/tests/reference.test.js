// reference.js(원래 녹음 줄별 측정값)가 대본 96줄과 맞는지, profile-browser.js가 팀 검사기와 같은지 확인한다.
// 실행: node apps/voice-studio/tests/reference.test.js
"use strict";
const { execFileSync } = require("child_process");
const path = require("path");
const LINES = require("../lines.js");
const REF = require("../reference.js");
let fail = 0;
const ok = (name, cond, detail = "") => { if (!cond) fail++; console.log(`${cond ? "PASS" : "FAIL"} ${name}${detail ? " — " + detail : ""}`); };
ok("대본 96줄 모두 기준값이 있음", LINES.every((l) => REF[l.id]), `${Object.keys(REF).length}줄`);
ok("음높이는 사람 목소리 범위(80~500Hz)", Object.values(REF).every((r) => r.hz >= 80 && r.hz <= 500));
ok("말한 길이는 0초보다 김", Object.values(REF).every((r) => r.speechSec > 0));
ok("불확실 표시 12줄", Object.values(REF).filter((r) => r.uncertain).length === 12);
try {
  execFileSync(process.execPath, [path.join(__dirname, "../tools/build-profile.js"), "--check"], { stdio: "pipe" });
  ok("profile-browser.js가 팀 profile.js에서 만든 최신본", true);
} catch (e) { ok("profile-browser.js가 팀 profile.js에서 만든 최신본", false, String(e.stdout)); }
console.log(fail ? `\n실패 ${fail}건` : "\n전부 통과");
process.exitCode = fail ? 1 : 0;
