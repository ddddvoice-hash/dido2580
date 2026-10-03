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

const text = build();
if (process.argv.includes("--check")) {
  const same = fs.existsSync(OUT) && fs.readFileSync(OUT, "utf8") === text;
  console.log(same ? "PASS profile-browser.js가 profile.js와 같습니다" : "FAIL profile-browser.js가 오래됐습니다. node apps/voice-studio/tools/build-profile.js 를 실행하세요");
  process.exitCode = same ? 0 : 1;
} else {
  fs.writeFileSync(OUT, text);
  console.log("만듦:", path.relative(process.cwd(), OUT));
}
