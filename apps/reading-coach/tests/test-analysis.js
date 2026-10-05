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

const longPause = A.compare(demo, A.analyze(build(demoParts(1, 1.2)), RATE));
check("쉼을 두 배로 길게 쉬면 길이 차이 2곳", longPause.lengthDiffs.length === 2, JSON.stringify(longPause.lengthDiffs.map(d => d.mine.toFixed(2))));
check("피드백에 '조금 짧게 쉬어 보세요'", A.feedback(longPause).some(l => l.includes("시범 0.6초, 내 낭독 1.2초") && l.includes("조금 짧게")));
check("쉼 길이 차이는 점수에 안 들어감(자리가 맞으면 쉼 50점 그대로)", longPause.matched.length === 2);
check("같은 낭독에는 길이 안내 없음", same.lengthDiffs.length === 0 && !A.feedback(same).some(l => l.includes("번째 쉼")));
const tiny = A.compare(demo, A.analyze(build(demoParts(1, 0.7)), RATE));
check("0.1초 차이는 안내하지 않음", tiny.lengthDiffs.length === 0);
const scoreRange = [same, slow, missOne, extra].every(r => r.score >= 0 && r.score <= 100);
check("점수는 0~100 사이", scoreRange);

// ---- R6-9: 쉼 길이 차이는 정수 밀리초로 비교(경계값) ----
const pz = (at, ms) => ({ at, length: ms / 1000, lengthMs: ms });
const res = (pauses) => ({ duration: 5, pauses });
const edge = (d, m) => A.compare(res([pz(0.5, d)]), res([pz(0.5, m)])).lengthDiffs.length;
check("경계: 시범 0.6초, 내 낭독 0.8초(정확히 0.2초 차이)는 안내 없음", edge(600, 800) === 0);
check("경계: 0.2초보다 1ms 더 다르면(0.801초) 30% 조건도 넘으니 안내", edge(600, 801) === 1);
check("경계: 시범 1.0초, 내 낭독 1.3초(30% 딱 같음)는 안내 없음", edge(1000, 1300) === 0);
check("경계: 시범 1.0초, 내 낭독 1.301초는 안내", edge(1000, 1301) === 1);
check("부동소수점 오차가 있는 길이(0.6, 0.8)도 안내 없음(lengthMs 없는 옛 형식)",
  A.compare(res([{ at: 0.5, length: 0.6 }]), res([{ at: 0.5, length: 0.8 }])).lengthDiffs.length === 0);
const frames = A.compare(demo, A.analyze(build(demoParts(1, 0.8)), RATE));
check("합성 소리 0.6초 -> 0.8초 쉼(프레임 10개 차이)도 안내 없음", frames.lengthDiffs.length === 0, JSON.stringify(frames.lengthDiffs.map(d => d.diffMs)));
check("analyze가 쉼 길이를 정수 밀리초로도 돌려줌", demo.pauses.every(p => Number.isInteger(p.lengthMs) && p.lengthMs >= 500));

// ---- R6-10: 앞 쉼을 놓쳐도 시범의 원래 쉼 번호 유지 ----
const d3 = res([pz(0.25, 600), pz(0.75, 600)]);
const lateOnly = A.compare(d3, res([pz(0.75, 1500)]));
check("첫 쉼을 놓치고 두 번째만 맞으면 안내 번호는 2", lateOnly.matched.length === 1 && lateOnly.lengthDiffs.length === 1 && lateOnly.lengthDiffs[0].order === 2, JSON.stringify(lateOnly.lengthDiffs.map(d => d.order)));
check("피드백 문장도 '2번째 쉼'", A.feedback(lateOnly).some(l => l.includes("같은 자리 2번째 쉼")));

console.log(fail ? `\n실패 ${fail}건 (${count}건 중)` : `\n전부 통과 (${count}건)`);
process.exitCode = fail ? 1 : 0;
