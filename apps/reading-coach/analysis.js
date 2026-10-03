// 낭독 분석 — 브라우저와 Node 양쪽에서 쓰는 순수 함수 모음.
// 소리 크기 곡선(엔벨로프)을 만들고, 말한 구간과 쉰 구간을 나눈 뒤,
// 시범 낭독과 따라 읽기를 비교한다. 음성 인식은 하지 않는다.

(function (root) {
  "use strict";

  const FRAME_MS = 20;        // 한 프레임 길이
  const MIN_PAUSE_MS = 250;   // 이보다 짧은 무음은 숨 고르기로 보고 쉼으로 세지 않는다
  const MIN_SPEECH_MS = 80;   // 이보다 짧은 소리는 잡음으로 본다
  const PAUSE_MATCH = 0.08;
  const PAUSE_LEN_SEC = 0.2;    // 쉼 길이 차이 안내 기준(초)
  const PAUSE_LEN_RATIO = 0.3;  // 그리고 시범 쉼 길이의 이 비율보다 클 때   // 시범 쉼과 이 거리(전체 길이 비율) 안이면 같은 쉼으로 본다

  // 프레임별 RMS(소리 크기)
  function envelope(samples, sampleRate) {
    const size = Math.max(1, Math.round(sampleRate * FRAME_MS / 1000));
    const count = Math.floor(samples.length / size);
    const env = new Float32Array(count);
    for (let f = 0; f < count; f++) {
      let sum = 0;
      const start = f * size;
      for (let i = start; i < start + size; i++) sum += samples[i] * samples[i];
      env[f] = Math.sqrt(sum / size);
    }
    return env;
  }

  function percentile(values, p) {
    const sorted = Array.from(values).sort((a, b) => a - b);
    if (!sorted.length) return 0;
    return sorted[Math.min(sorted.length - 1, Math.floor(p * sorted.length))];
  }

  // 녹음 환경마다 잡음 크기가 달라서 기준을 녹음마다 다시 잡는다:
  // 잡음 바닥(하위 10%)과 말소리(상위 90%) 사이의 15% 지점.
  // 가장 큰 소리도 작거나 잡음과 차이가 없으면 말소리가 없는 녹음으로 본다.
  function threshold(env) {
    const floor = percentile(env, 0.1);
    const peak = percentile(env, 0.9);
    if (peak < 0.01 || peak < floor * 3) return Infinity;
    return floor + (peak - floor) * 0.15;
  }

  // 말한 구간 목록 [{start, end}] (프레임 단위)
  function speechRuns(env) {
    const th = threshold(env);
    const minSpeech = Math.ceil(MIN_SPEECH_MS / FRAME_MS);
    const runs = [];
    let start = -1;
    for (let f = 0; f <= env.length; f++) {
      const loud = f < env.length && env[f] > th;
      if (loud && start < 0) start = f;
      if (!loud && start >= 0) {
        if (f - start >= minSpeech) runs.push({ start, end: f });
        start = -1;
      }
    }
    return runs;
  }

  // 한 녹음의 분석 결과. 시간은 초, 쉼 위치는 발화 구간 안에서의 비율(0~1).
  function analyze(samples, sampleRate) {
    const env = envelope(samples, sampleRate);
    const runs = speechRuns(env);
    const sec = (frames) => frames * FRAME_MS / 1000;
    if (!runs.length) {
      return { env, speechStart: 0, speechEnd: 0, duration: 0, pauses: [], spoken: 0 };
    }
    const first = runs[0].start;
    const last = runs[runs.length - 1].end;
    const span = last - first;
    const minPause = Math.ceil(MIN_PAUSE_MS / FRAME_MS);
    const pauses = [];
    let spoken = 0;
    for (let i = 0; i < runs.length; i++) {
      spoken += runs[i].end - runs[i].start;
      if (i === 0) continue;
      const gap = runs[i].start - runs[i - 1].end;
      if (gap >= minPause) {
        const mid = (runs[i - 1].end + runs[i].start) / 2;
        pauses.push({ at: (mid - first) / span, length: sec(gap), time: sec(mid) });
      }
    }
    return {
      env,
      speechStart: sec(first),
      speechEnd: sec(last),
      duration: sec(span),
      spoken: sec(spoken),
      pauses,
    };
  }

  // 시범과 따라 읽기 비교
  function compare(demo, mine) {
    if (!demo.duration || !mine.duration) {
      return { ok: false, message: "말소리를 찾지 못했습니다. 마이크 가까이에서 다시 녹음해 보세요." };
    }
    const speedRatio = mine.duration / demo.duration; // 1보다 크면 느림
    const used = new Set();
    const matched = [];
    const missing = [];
    for (const p of demo.pauses) {
      let best = -1;
      let bestDist = Infinity;
      mine.pauses.forEach((q, j) => {
        const d = Math.abs(q.at - p.at);
        if (!used.has(j) && d < bestDist) { best = j; bestDist = d; }
      });
      if (best >= 0 && bestDist <= PAUSE_MATCH) {
        used.add(best);
        matched.push({ demo: p, mine: mine.pauses[best] });
      } else {
        missing.push(p);
      }
    }
    const extra = mine.pauses.filter((_, j) => !used.has(j));
    // 같은 자리 쉼의 길이 차이. 0.2초 넘게, 그리고 시범 길이의 30% 넘게 다를 때만 알린다(짧은 숨 고르기 흔들림은 무시).
    const lengthDiffs = matched
      .map((m, k) => ({ order: k + 1, demo: m.demo.length, mine: m.mine.length, diff: m.mine.length - m.demo.length }))
      .filter((d) => Math.abs(d.diff) > PAUSE_LEN_SEC && Math.abs(d.diff) > d.demo * PAUSE_LEN_RATIO);
    const total = demo.pauses.length;
    // 점수: 속도 50점 + 쉼 50점. 속도는 ±25% 벗어나면 0점.
    const speedScore = Math.max(0, 1 - Math.abs(speedRatio - 1) / 0.25) * 50;
    const pauseScore = total
      ? Math.max(0, (matched.length - extra.length * 0.5) / total) * 50
      : (extra.length ? Math.max(0, 50 - extra.length * 15) : 50);
    return {
      ok: true,
      speedRatio,
      matched,
      missing,
      extra,
      lengthDiffs,
      score: Math.round(speedScore + pauseScore),
    };
  }

  // 사람이 읽을 피드백 문장
  function feedback(result) {
    if (!result.ok) return [result.message];
    const lines = [];
    const pct = Math.round(Math.abs(result.speedRatio - 1) * 100);
    if (pct <= 5) lines.push("속도가 시범과 거의 같습니다.");
    else if (result.speedRatio > 1) lines.push(`시범보다 ${pct}% 느리게 읽었습니다.`);
    else lines.push(`시범보다 ${pct}% 빠르게 읽었습니다.`);
    const total = result.matched.length + result.missing.length;
    if (total) lines.push(`시범의 쉼 ${total}곳 중 ${result.matched.length}곳을 같은 자리에서 쉬었습니다.`);
    if (result.missing.length) lines.push(`놓친 쉼 ${result.missing.length}곳은 아래 그림에서 빨간 표시로 보입니다.`);
    if (result.extra.length) lines.push(`시범에 없는 쉼이 ${result.extra.length}곳 있습니다.`);
    // 쉼 길이는 점수에 넣지 않고 안내만 한다. 많으면 두 곳까지만.
    for (const d of (result.lengthDiffs || []).slice(0, 2)) {
      lines.push(`같은 자리 ${d.order}번째 쉼: 시범 ${d.demo.toFixed(1)}초, 내 낭독 ${d.mine.toFixed(1)}초 — ${d.diff > 0 ? "조금 짧게" : "조금 더 길게"} 쉬어 보세요.`);
    }
    return lines;
  }

  const api = { FRAME_MS, envelope, threshold, speechRuns, analyze, compare, feedback };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.ReadingAnalysis = api;
})(typeof window !== "undefined" ? window : globalThis);
