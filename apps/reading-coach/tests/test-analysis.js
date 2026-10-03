// 낭독 코치 분석 함수(analysis.js) 테스트. 합성 소리로 속도·쉼 비교와 피드백 문장을 확인한다.
// 실행: node apps/reading-coach/tests/test-analysis.js
"use strict";
const A = require("../analysis.js");

const RATE = 16000;
// parts: [초, 소리 크기]. 크기 0이면 아주 작은 잡음(완전 무음 대신).
function build(parts) {
  const total = parts.reduce((s, [sec]) => s + Math.round(sec * RATE), 0);
  const out = new Float32Array(total);
  let pos = 0, seed = 1;
  for (const [sec, amp] of parts) {
    const n = Math.round(sec * RATE);
    for (let i = 0; i < n; i++) {
      seed = (seed * 1103515245 + 12345) & 0x7fffffff;
      const noise = (seed / 0x7fffffff - 0.5) * 0.0004;
      out[pos + i] = amp ? amp * Math.sin(2 * Math.PI * 200 * i / RATE) : noise;
    }
    pos += n;
  }
  return out;
}
// 시범: 1초 말, 0.6초 쉼, 1초 말, 0.6초 쉼, 1초 말 (앞뒤 여백 0.3초)
const demoParts = (k = 1, pause = 0.6) => [[0.3, 0], [1 * k, .5], [pause, 0], [1 * k, .5], [pause, 0], [1 * k, .5], [0.3, 0]];

let fail = 0, count = 0;
function check(name, cond, detail = "") {
  count++;
  if (!cond) fail++;
  console.log(`${cond ? "ok  " : "FAIL"} ${name}${detail ? " — " + detail : ""}`);
}

const demo = A.analyze(build(demoParts()), RATE);
check("시범에서 쉼 2곳을 찾음", demo.pauses.length === 2, JSON.stringify(demo.pauses.map(p => p.length)));
check("말소리 시작 약 0.3초", Math.abs(demo.speechStart - 0.3) < 0.03, demo.speechStart);

const same = A.compare(demo, A.analyze(build(demoParts()), RATE));
check("같은 낭독은 100점", same.ok && same.score === 100, same.score);
check("같은 낭독 피드백은 '거의 같습니다'", A.feedback(same)[0] === "속도가 시범과 거의 같습니다.");

const slow = A.compare(demo, A.analyze(build(demoParts(1.2, 0.72)), RATE));
check("20% 느리게 읽으면 속도 비율 약 1.2", Math.abs(slow.speedRatio - 1.2) < 0.03, slow.speedRatio.toFixed(3));
check("느린 낭독 피드백에 '느리게'", /느리게/.test(A.feedback(slow)[0]), A.feedback(slow)[0]);
check("쉼 자리는 그대로라 2곳 모두 맞음", slow.matched.length === 2 && slow.missing.length === 0);

const missOne = A.compare(demo, A.analyze(build([[0.3, 0], [1, .5], [0.6, 0], [2, .5], [0.3, 0]]), RATE));
check("두 번째 쉼을 건너뛰면 놓친 쉼 1곳", missOne.missing.length === 1 && missOne.matched.length === 1);
check("놓친 쉼이 있으면 100점 아님", missOne.score < 100, missOne.score);
check("피드백에 놓친 쉼 안내", A.feedback(missOne).some(l => l.includes("놓친 쉼 1곳")));

const extra = A.compare(demo, A.analyze(build([[0.3, 0], [0.5, .5], [0.4, 0], [0.5, .5], [0.6, 0], [1, .5], [0.6, 0], [1, .5], [0.3, 0]]), RATE));
check("시범에 없는 쉼은 extra로 셈", extra.extra.length >= 1, extra.extra.length);
check("피드백에 '시범에 없는 쉼'", A.feedback(extra).some(l => l.includes("시범에 없는 쉼")));

const silent = A.compare(demo, A.analyze(build([[2, 0]]), RATE));
check("무음 녹음은 비교하지 않고 다시 녹음 안내", !silent.ok && /다시 녹음/.test(A.feedback(silent)[0]));
check("아주 작은 소리는 말소리 기준이 무한대", A.threshold(A.envelope(build([[1, 0]]), RATE)) === Infinity);

const short = A.analyze(build([[0.3, 0], [0.05, .5], [0.3, 0]]), RATE);
check("80ms보다 짧은 소리는 말소리로 안 셈", short.duration === 0);

const scoreRange = [same, slow, missOne, extra].every(r => r.score >= 0 && r.score <= 100);
check("점수는 0~100 사이", scoreRange);

console.log(fail ? `\n실패 ${fail}건 (${count}건 중)` : `\n전부 통과 (${count}건)`);
process.exitCode = fail ? 1 : 0;
