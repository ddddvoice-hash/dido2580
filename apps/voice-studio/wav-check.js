// 녹음 검사 — 브라우저용. apps/voice-check/check.js의 inspect()와 같은 기준으로 판정한다.
// 파일 대신 ArrayBuffer를 받는다. 기준값이나 판정을 바꾸면 check.js도 같이 바꾸고
// tests/parity.test.js로 두 결과가 같은지 확인한다.

(function (root) {
  "use strict";

  const analysis = typeof module !== "undefined" && module.exports
    ? require("../reading-coach/analysis.js")
    : root.ReadingAnalysis;

  const REQUIRED = { rate: 48000, bits: 24, channels: 1 };
  const CLIP_DB = -1;
  const PEAK_MIN_DB = -6;
  const PEAK_MAX_DB = -3;
  const TAIL_MIN = 0.3;
  const TAIL_MAX = 1.0;
  const ROOM_SEC = 10.0;
  const NOISE_DB = -60;
  const ZERO_RUN_SAMPLES = 480;
  const TOL = 1e-6;
  const TAIL_EDGE_SEC = 0.02;
  const PCM_GUID_TAIL = [0x00, 0x00, 0x00, 0x00, 0x10, 0x00, 0x80, 0x00, 0x00, 0xaa, 0x00, 0x38, 0x9b, 0x71];
  const NAME_RE = /^\d{3}_[a-z0-9_]+_take\d{2}\.wav$/i;

  const toDb = (x) => (x > 0 ? 20 * Math.log10(x) : -Infinity);
  const tag = (v, o) => String.fromCharCode(v.getUint8(o), v.getUint8(o + 1), v.getUint8(o + 2), v.getUint8(o + 3));

  function validateFmt(f) {
    if (!(f.rate > 0)) throw new Error(`샘플레이트가 ${f.rate}Hz입니다`);
    if (f.channels < 1 || f.channels > 2) throw new Error(`채널 ${f.channels}개는 지원하지 않습니다`);
    const okPcm = f.format === 1 && [16, 24, 32].includes(f.bits);
    const okFloat = f.format === 3 && f.bits === 32;
    if (!okPcm && !okFloat) throw new Error(`지원하지 않는 형식입니다 (코드 ${f.format}, ${f.bits}bit)`);
    if (f.blockAlign !== f.channels * f.bits / 8) {
      throw new Error(`블록 크기(${f.blockAlign})가 채널 수 x 비트 수와 다릅니다`);
    }
  }

  function parseHeader(v) {
    const fileSize = v.byteLength;
    if (fileSize < 12) throw new Error("파일이 너무 짧습니다");
    const head = tag(v, 0);
    if (head === "RF64") throw new Error("RF64(4GB 넘는 WAV)는 지원하지 않습니다");
    if (head !== "RIFF" || tag(v, 8) !== "WAVE") throw new Error("WAV 헤더가 아닙니다");
    let pos = 12;
    let fmt = null;
    while (pos + 8 <= fileSize) {
      const id = tag(v, pos);
      let size = v.getUint32(pos + 4, true);
      const body = pos + 8;
      if (id === "fmt ") {
        if (size < 16) throw new Error("fmt 청크가 너무 짧습니다");
        const len = Math.min(size, 40);
        if (body + len > fileSize) throw new Error("fmt 청크가 잘렸습니다");
        let format = v.getUint16(body, true);
        if (format === 0xfffe) {
          if (len < 40 || v.getUint16(body + 16, true) < 22) throw new Error("EXTENSIBLE fmt 청크가 올바르지 않습니다");
          for (let i = 0; i < 14; i++) {
            if (v.getUint8(body + 26 + i) !== PCM_GUID_TAIL[i]) throw new Error("EXTENSIBLE SubFormat GUID가 올바르지 않습니다");
          }
          format = v.getUint16(body + 24, true);
        }
        fmt = {
          format,
          channels: v.getUint16(body + 2, true),
          rate: v.getUint32(body + 4, true),
          blockAlign: v.getUint16(body + 12, true),
          bits: v.getUint16(body + 14, true),
        };
      } else if (id === "data") {
        if (!fmt) throw new Error("fmt 청크가 data보다 뒤에 있습니다");
        validateFmt(fmt);
        const remain = fileSize - body;
        let truncated = false;
        if (size === 0 || size === 0xffffffff || size > remain) { size = remain; truncated = true; }
        return { fmt, dataStart: body, dataBytes: size, truncated };
      }
      pos = body + size + (size % 2);
    }
    throw new Error("data 청크를 찾지 못했습니다");
  }

  function readAudio(v, info) {
    const { fmt } = info;
    const bps = fmt.bits / 8;
    const C = fmt.channels;
    const frameBytes = bps * C;
    const frames = Math.floor(info.dataBytes / frameBytes);
    const out = new Float32Array(frames);
    const isFloat = fmt.format === 3;
    const runLen = new Array(C).fill(0);
    const runStart = new Array(C).fill(0);
    const zeroRuns = [];
    let peak = 0;
    for (let i = 0; i < frames; i++) {
      let sq = 0;
      let only = 0;
      const base = info.dataStart + i * frameBytes;
      for (let c = 0; c < C; c++) {
        const o = base + c * bps;
        let s;
        if (isFloat) {
          s = v.getFloat32(o, true);
          if (!Number.isFinite(s)) throw new Error(`유한하지 않은 샘플(NaN/Infinity)이 있습니다 (프레임 ${i}, 채널 ${c + 1})`);
        } else if (fmt.bits === 16) s = v.getInt16(o, true) / 32768;
        else if (fmt.bits === 24) {
          let x = v.getUint8(o) | (v.getUint8(o + 1) << 8) | (v.getUint8(o + 2) << 16);
          if (x & 0x800000) x -= 0x1000000;
          s = x / 8388608;
        } else s = v.getInt32(o, true) / 2147483648;
        const a = s < 0 ? -s : s;
        if (a > peak) peak = a;
        sq += s * s;
        only = s;
        if (s === 0) {
          if (runLen[c] === 0) runStart[c] = i;
          runLen[c]++;
        } else if (runLen[c] > 0) {
          if (runLen[c] >= ZERO_RUN_SAMPLES) zeroRuns.push({ channel: c, start: runStart[c], length: runLen[c] });
          runLen[c] = 0;
        }
      }
      out[i] = C === 1 ? only : Math.sqrt(sq / C);
    }
    for (let c = 0; c < C; c++) {
      if (runLen[c] >= ZERO_RUN_SAMPLES) zeroRuns.push({ channel: c, start: runStart[c], length: runLen[c] });
    }
    return { samples: out, peak, zeroRuns };
  }

  function formatLabel(f) {
    const ch = f.channels === 1 ? "모노" : "스테레오";
    return `${f.rate}Hz/${f.format === 3 ? f.bits + "bit-float" : f.bits + "bit"}/${ch}`;
  }

  // 결과에는 화면에 그릴 samples, runs(말소리 구간, 초)도 담는다.
  function inspectBuffer(buffer, name) {
    const v = new DataView(buffer);
    const info = parseHeader(v);
    const audio = readAudio(v, info);
    const samples = audio.samples;
    const { fmt } = info;
    const rate = fmt.rate;
    const n = samples.length;
    const duration = n / rate;
    const zeroRuns = audio.zeroRuns;
    const peakDb = toDb(audio.peak);

    const FR = analysis.FRAME_MS;
    const frameSize = Math.max(1, Math.round(rate * FR / 1000));
    const runs = analysis.speechRuns(analysis.envelope(samples, rate));
    const hasSpeech = runs.length > 0;
    const speechStart = hasSpeech ? runs[0].start * FR / 1000 : null;
    const speechEnd = hasSpeech ? runs[runs.length - 1].end * FR / 1000 : null;
    const tail = hasSpeech ? duration - speechEnd : null;

    let nonSpeech = 0;
    let nonSpeechZero = 0;
    const countRange = (a, b) => {
      nonSpeech += b - a;
      for (let i = a; i < b; i++) if (samples[i] === 0) nonSpeechZero++;
    };
    let cursor = 0;
    for (const r of runs) {
      countRange(cursor, r.start * frameSize);
      cursor = r.end * frameSize;
    }
    countRange(Math.min(cursor, n), n);
    const zeroPct = nonSpeech ? (nonSpeechZero / nonSpeech) * 100 : 0;

    const roomEnd = Math.min(n, Math.round(ROOM_SEC * rate));
    let sq = 0;
    for (let i = 0; i < roomEnd; i++) sq += samples[i] * samples[i];
    const roomDb = roomEnd ? toDb(Math.sqrt(sq / roomEnd)) : -Infinity;

    const reject = [];
    const warn = [];
    if (peakDb >= CLIP_DB) reject.push("V02");
    if (hasSpeech && (tail < TAIL_MIN - TOL || tail > TAIL_MAX + TOL)) reject.push("V05");
    if (zeroRuns.length > 0) reject.push("V08");

    if (!NAME_RE.test(name)) warn.push("NAME");
    if (fmt.rate !== REQUIRED.rate || fmt.bits !== REQUIRED.bits || fmt.channels !== REQUIRED.channels ||
        fmt.format === 3) warn.push("FORMAT");
    if (peakDb < PEAK_MIN_DB || peakDb > PEAK_MAX_DB) warn.push("PEAK");
    if (info.truncated) warn.push("TRUNC");
    if (!hasSpeech) warn.push("NOSPEECH");
    else {
      if (speechStart < ROOM_SEC) warn.push("ROOM");
      if (Math.abs(tail - TAIL_MIN) <= TAIL_EDGE_SEC || Math.abs(tail - TAIL_MAX) <= TAIL_EDGE_SEC) warn.push("TAIL_EDGE");
    }
    if (roomDb > NOISE_DB) warn.push("NOISE");

    return {
      name, status: reject.length ? "반려" : "통과", reject, warn,
      duration, format: formatLabel(fmt), rate, peakDb, speechStart, tail, roomDb,
      zeroRuns: zeroRuns.length, zeroPct,
      // 그리기용
      samples,
      speech: runs.map((r) => ({ start: r.start * FR / 1000, end: r.end * FR / 1000 })),
      zeroMarks: zeroRuns.map((z) => ({ start: z.start / rate, end: (z.start + z.length) / rate })),
    };
  }

  // 검사 결과 CSV: check.js의 toCsv와 같은 열.
  function csvCell(v) {
    const s = v === null || v === undefined ? "" : String(v);
    return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  }
  const fmtNum = (x, d) => (x === null || x === undefined ? "-" : Number.isFinite(x) ? x.toFixed(d) : "-∞");
  function toCsv(results) {
    const cols = ["file", "status", "reject", "warn", "duration_s", "format", "peak_dbfs",
      "speech_start_s", "tail_s", "room_rms_dbfs", "zero_runs", "zero_pct_nonspeech", "error"];
    const rows = results.map((r) => r.error
      ? [r.name, "읽기 실패", "", "", "", "", "", "", "", "", "", "", r.error]
      : [r.name, r.status, r.reject.join(" "), r.warn.join(" "), r.duration.toFixed(3), r.format,
        fmtNum(r.peakDb, 2), fmtNum(r.speechStart, 2), fmtNum(r.tail, 3), fmtNum(r.roomDb, 2),
        r.zeroRuns, r.zeroPct.toFixed(3), ""]);
    return "﻿" + [cols, ...rows].map((row) => row.map(csvCell).join(",")).join("\r\n") + "\r\n";
  }

  const CODES = {
    V01: { kind: "reject", auto: "사람", text: "대본과 다르게 읽음 (한 글자라도)" },
    V02: { kind: "reject", auto: "자동", text: "찢어짐: 최대 크기가 −1 dBFS 이상" },
    V03: { kind: "reject", auto: "일부", text: "잡음·외부 소리 (차, 문, 기계)" },
    V04: { kind: "reject", auto: "사람", text: "입소리·클릭·팝" },
    V05: { kind: "reject", auto: "자동", text: "뒤 여백이 0.3초 미만이거나 1초 초과" },
    V06: { kind: "reject", auto: "사람", text: "스타일이 지정과 다름 (위로인데 안내처럼)" },
    V07: { kind: "reject", auto: "사람", text: "컨디션 문제 (쉬어서 갈라짐, 코맨 소리)" },
    V08: { kind: "reject", auto: "자동", text: "가공 흔적: 완전 0이 480샘플 넘게 이어짐 (노이즈 게이트, 압축)" },
    FORMAT: { kind: "warn", text: "48kHz·24bit·모노가 아님" },
    PEAK: { kind: "warn", text: "최대 크기가 −6 ~ −3 dBFS 밖" },
    ROOM: { kind: "warn", text: "앞 10초 안에 말소리가 있음 (룸톤 부족)" },
    NOISE: { kind: "warn", text: "앞 10초 평균이 −60 dBFS보다 큼" },
    NAME: { kind: "warn", text: "파일 이름이 001_키_take01.wav 형식이 아님" },
    TRUNC: { kind: "warn", text: "녹음이 중간에 끊긴 흔적" },
    TAIL_EDGE: { kind: "warn", text: "뒤 여백이 경계값 근처: 귀로 확인" },
    NOSPEECH: { kind: "warn", text: "말소리를 찾지 못함" },
  };

  const api = { inspectBuffer, parseHeader, toCsv, csvCell, CODES, NAME_RE };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.WavCheck = api;
})(typeof window !== "undefined" ? window : globalThis);
