#!/usr/bin/env node
// 뒤 여백 자른 사본 만들기. 외부 패키지 없음.
// 사용: node apps/voice-check/trim.js <in.wav> <out.wav> [--tail 0.8]
// 마지막 말소리 끝 뒤 여백을 --tail 초(기본 0.8, 0~1초)로 자른다. 이미 더 짧으면 그대로 복사한다(늘리지 않음).
// 헤더·샘플은 바이트 그대로 복사하고 RIFF/data 크기 두 값만 고친다. data 뒤의 다른 청크(LIST 등)는 버린다.
// 입력 파일은 읽기만 한다.
"use strict";

const fs = require("fs");
const path = require("path");
const analysis = require("../reading-coach/analysis.js");
const check = require("./check.js");

function samePath(a, b) {
  if (path.resolve(a).toLowerCase() === path.resolve(b).toLowerCase()) return true;
  try {
    const x = fs.statSync(a), y = fs.statSync(b);
    return x.ino !== 0 && x.ino === y.ino && x.dev === y.dev;
  } catch (e) { return false; }
}

function trim(inFile, outFile, tail) {
  if (!(tail >= 0 && tail <= 1)) throw new Error("--tail은 0~1초 사이여야 합니다");
  if (samePath(inFile, outFile)) throw new Error("입력과 출력 경로가 같습니다");
  const fd = fs.openSync(inFile, "r");
  let result, head, data;
  try {
    const info = check.parseHeader(fd, fs.fstatSync(fd).size);
    const audio = check.readAudio(fd, info);
    const rate = info.fmt.rate;
    const runs = analysis.speechRuns(analysis.envelope(audio.samples, rate));
    if (!runs.length) throw new Error("말소리를 찾지 못했습니다");
    const speechEnd = runs[runs.length - 1].end * analysis.FRAME_MS / 1000;
    const frames = audio.samples.length;
    const keepFrames = Math.min(frames, Math.round((speechEnd + tail) * rate));
    const keepBytes = keepFrames * info.fmt.blockAlign;
    head = Buffer.alloc(info.dataStart);
    fs.readSync(fd, head, 0, head.length, 0);
    data = Buffer.alloc(keepBytes);
    fs.readSync(fd, data, 0, keepBytes, info.dataStart);
    result = { rate, frames, keepFrames, keepBytes, dataStart: info.dataStart, speechEnd };
  } finally { fs.closeSync(fd); }
  const pad = result.keepBytes % 2;
  head.writeUInt32LE(result.keepBytes, head.length - 4);
  head.writeUInt32LE(head.length + result.keepBytes + pad - 8, 4);
  fs.writeFileSync(outFile, Buffer.concat([head, data, Buffer.alloc(pad)]));
  return {
    ...result,
    oldTail: result.frames / result.rate - result.speechEnd,
    newTail: result.keepFrames / result.rate - result.speechEnd,
  };
}

function main(argv) {
  const pos = [];
  let tail = 0.8;
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--tail") tail = Number(argv[++i]);
    else pos.push(argv[i]);
  }
  if (pos.length !== 2 || Number.isNaN(tail)) {
    console.error("사용: node apps/voice-check/trim.js <in.wav> <out.wav> [--tail 0.8]");
    return 2;
  }
  try {
    const r = trim(pos[0], pos[1], tail);
    console.log(`저장: ${pos[1]}`);
    console.log(`말소리 끝 ${r.speechEnd.toFixed(2)}초 | 뒤 여백 ${r.oldTail.toFixed(2)}초 -> ${r.newTail.toFixed(2)}초 | 샘플 ${r.frames} -> ${r.keepFrames}`);
    return 0;
  } catch (e) { console.error(`실패: ${e.message}`); return 2; }
}

if (require.main === module) process.exitCode = main(process.argv.slice(2));
module.exports = { trim, main };
