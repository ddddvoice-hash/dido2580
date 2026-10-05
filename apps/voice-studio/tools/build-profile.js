// apps/voice-check/profile.js의 측정 함수(상수~profile)를 그대로 떼어 브라우저용 profile-browser.js를 만든다.
// 손으로 옮기지 않으므로 팀 검사기와 측정이 갈라지지 않는다. profile.js를 고치면 이걸 다시 실행한다.
// 실행: node apps/voice-studio/tools/build-profile.js   (확인만: --check)
"use strict";
const fs = require("fs");
const path = require("path");

const SRC = path.join(__dirname, "../../voice-check/profile.js");
const OUT = path.join(__dirname, "../profile-browser.js");

function build() {
  const src = fs.readFileSync(SRC, "utf8");
  const start = src.indexOf("const F0_MIN");
  const end = src.indexOf("function profileFile");
  if (start < 0 || end < 0 || end < start) throw new Error("profile.js 구조가 바뀌었습니다. build-profile.js의 잘라 낼 위치를 고쳐 주세요.");
  const body = src.slice(start, end).trimEnd();
  return `// 자동 생성 파일: apps/voice-check/profile.js에서 만듦. 직접 고치지 말고 tools/build-profile.js를 다시 실행하세요.
(function (root) {
  "use strict";
  const analysis = typeof module !== "undefined" && module.exports
    ? require("../reading-coach/analysis.js")
    : root.ReadingAnalysis;

${body.split("\n").map((l) => (l ? "  " + l : l)).join("\n")}

  const api = { profile, f0Track, countSyllables, pct };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.VoiceProfile = api;
})(typeof window !== "undefined" ? window : globalThis);
`;
}

// 줄바꿈(LF/CRLF) 차이는 내용 차이가 아니다.
const norm = (t) => t.replace(/\r\n?/g, "\n");

// 생성본을 브라우저처럼(module 없이, 전역에 ReadingAnalysis만 둔 채) 실제로 실행해, 원본 profile.js와 같은 측정값을 내는지 본다.
// 잘라 낼 때 빠진 상수·함수가 있으면 여기서 "is not defined"로 드러난다.
function runtimeCheck(generated) {
  const vm = require("vm");
  const ctx = { ReadingAnalysis: require("../../reading-coach/analysis.js"), Math, Float64Array, Float32Array, Array, Object, Number };
  ctx.globalThis = ctx;
  vm.createContext(ctx);
  vm.runInContext(generated, ctx);
  const gen = ctx.VoiceProfile;
  if (!gen || typeof gen.profile !== "function") throw new Error("생성본에 VoiceProfile.profile이 없습니다");
  const orig = require(SRC);
  const rate = 16000;
  // 합성음: 220Hz에 느린 떨림을 준 1초 + 쉼 0.4초 + 300Hz 0.8초. 쉼과 음높이 변화가 모두 들어 있다.
  const x = new Float64Array(Math.round(2.2 * rate));
  for (let i = 0; i < x.length; i++) {
    const t = i / rate;
    if (t < 1) x[i] = 0.4 * Math.sin(2 * Math.PI * (220 + 15 * Math.sin(2 * Math.PI * 3 * t)) * t);
    else if (t >= 1.4) x[i] = 0.4 * Math.sin(2 * Math.PI * 300 * t) * (0.6 + 0.4 * Math.sin(2 * Math.PI * 4 * t));
  }
  const a = JSON.stringify(orig.profile(x, rate, 0.4));
  const b = JSON.stringify(gen.profile(x, rate, 0.4));
  if (a !== b) throw new Error("생성본의 측정값이 원본과 다릅니다");
  if (!JSON.parse(a).pitch || !JSON.parse(a).pitch.medianHz) throw new Error("검사용 합성음에서 음높이가 잡히지 않았습니다");
}

const text = build();
if (process.argv.includes("--check")) {
  let ok = fs.existsSync(OUT) && norm(fs.readFileSync(OUT, "utf8")) === norm(text);
  console.log(ok ? "PASS profile-browser.js가 profile.js와 같습니다" : "FAIL profile-browser.js가 오래됐습니다. node apps/voice-studio/tools/build-profile.js 를 실행하세요");
  try {
    runtimeCheck(text);
    console.log("PASS 생성본을 실제로 실행해 원본과 같은 측정값을 냅니다");
  } catch (e) {
    ok = false;
    console.log("FAIL 생성본 실행 검사: " + e.message);
  }
  process.exitCode = ok ? 0 : 1;
} else {
  fs.writeFileSync(OUT, text);
  console.log("만듦:", path.relative(process.cwd(), OUT));
}
