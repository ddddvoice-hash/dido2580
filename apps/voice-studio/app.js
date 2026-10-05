// 김디도 녹음 부스 — 화면 동작. 검사는 wav-check.js, 대본은 lines.js.
(function () {
  "use strict";

  const LINES = window.CITY_LINES;
  const { inspectBuffer, toCsv, csvCell, CODES } = window.WavCheck;
  const STORE = "dido-voice-studio-v1";
  const FIELDS = ["gaze", "move", "breath", "action", "memo"];
  const $ = (id) => document.getElementById(id);

  // ---- 감정 묶음 (대본 감정 지시 → 색) ----------------------------------
  const FAMILIES = [
    { id: "clear", name: "또렷한 전달", re: /또렷|분명|명확|숫자|지명|호흡/ },
    { id: "energy", name: "힘·환호", re: /힘|강하|환호|통쾌|단단|신나|활기|자신|축하|응원|상승/ },
    { id: "spark", name: "설렘·감탄", re: /설레|감탄|놀라|기대|호기심|기쁘|뿌듯|유쾌|장난|경쾌|산뜻|밝게|기분/ },
    { id: "calm", name: "차분·다정", re: /./ },
  ];
  const family = (dir) => FAMILIES.find((f) => f.re.test(dir));

  // ---- 상태 -------------------------------------------------------------
  // notes: {id: {gaze, move, breath, action, memo, level}}
  // takes: {id: [take]}  take = 검사 결과(소리 제외) + example 표시
  // audio: 이번에 올린 파일의 샘플 (저장하지 않음)
  let state = { cur: 0, notes: {}, takes: {}, other: [] };
  const audio = new Map();
  try {
    const saved = JSON.parse(localStorage.getItem(STORE) || "null");
    if (saved && typeof saved === "object") state = { ...state, ...saved };
  } catch (e) { /* 저장소를 못 쓰면 새로 시작 */ }
  if (!(state.cur >= 0 && state.cur < LINES.length)) state.cur = 0;

  function save() {
    const clean = { ...state, takes: {}, other: state.other.filter((t) => !t.example) };
    for (const [id, list] of Object.entries(state.takes)) {
      const real = list.filter((t) => !t.example);
      if (real.length) clean.takes[id] = real;
    }
    try { localStorage.setItem(STORE, JSON.stringify(clean)); return true; } catch (e) { return false; }
  }

  const say = (msg) => { const el = $("live"); el.textContent = ""; setTimeout(() => { el.textContent = msg; }, 30); };
  const line = () => LINES[state.cur];
  const takesOf = (id) => state.takes[id] || [];
  const realTakes = (id) => takesOf(id).filter((t) => !t.example);
  const lineStatus = (id) => {
    const list = realTakes(id);
    if (list.some((t) => t.status === "통과")) return "pass";
    if (list.length) return "retake";
    return "";
  };
  const hasNote = (id) => { const n = state.notes[id]; return !!n && (FIELDS.some((f) => n[f]) || n.level); };
  const pad2 = (n) => String(n).padStart(2, "0");
  const nextName = (l) => {
    let max = 0;
    for (const t of realTakes(l.id)) { const m = /_take(\d{2})\.wav$/i.exec(t.name); if (m) max = Math.max(max, +m[1]); }
    return `${l.id}_${l.key}_take${pad2(max + 1)}.wav`;
  };

  // ---- 큐 시트 ----------------------------------------------------------
  function buildList() {
    const ul = $("list");
    ul.innerHTML = "";
    let scene = "";
    LINES.forEach((l, i) => {
      if (l.scene !== scene) {
        scene = l.scene;
        const s = document.createElement("li");
        s.className = "scene"; s.textContent = scene; s.setAttribute("aria-hidden", "true");
        ul.appendChild(s);
      }
      const li = document.createElement("li");
      const b = document.createElement("button");
      b.type = "button"; b.className = "row"; b.id = "row" + i;
      b.innerHTML = `<span class="no">${l.id}</span><i class="dot"></i><span class="txt"></span>`;
      b.querySelector(".txt").textContent = l.text;
      b.addEventListener("click", () => go(i));
      li.appendChild(b);
      ul.appendChild(li);
    });
  }

  function paintList() {
    let done = 0, retake = 0;
    LINES.forEach((l, i) => {
      const b = $("row" + i);
      const st = lineStatus(l.id);
      if (st === "pass") done++; else if (st === "retake") retake++;
      b.querySelector(".dot").className = "dot " + (st || (hasNote(l.id) ? "noted" : ""));
      const label = st === "pass" ? "통과" : st === "retake" ? "다시 녹음" : "대기";
      b.setAttribute("aria-label", `${l.id}번, ${label}: ${l.text}`);
      if (i === state.cur) b.setAttribute("aria-current", "true"); else b.removeAttribute("aria-current");
    });
    $("doneCount").textContent = done;
    $("barDone").style.width = (done / LINES.length * 100) + "%";
    $("barRetake").style.width = (retake / LINES.length * 100) + "%";
    $("retakeLabel").textContent = retake ? `다시 녹음 ${retake}줄` : "";
  }

  // ---- 큐 카드와 메모 ---------------------------------------------------
  function paintCue() {
    const l = line();
    const fam = family(l.dir);
    document.documentElement.style.setProperty("--fam", `var(--fam-${fam.id})`);
    document.documentElement.style.setProperty("--fam-ink", `var(--fam-ink-${fam.id})`);
    $("cueNo").textContent = l.id;
    $("cueScene").textContent = l.scene;
    $("cueKey").textContent = l.key;
    $("cueDir").innerHTML = "";
    $("cueDir").append(l.dir + " ");
    const small = document.createElement("small"); small.textContent = fam.name; $("cueDir").append(small);
    $("cueText").textContent = l.text;
    $("fname").textContent = nextName(l);
    $("prevBtn").disabled = state.cur === 0;
    $("nextBtn").disabled = state.cur === LINES.length - 1;
    const n = state.notes[l.id] || {};
    for (const f of FIELDS) $("f_" + f).value = n[f] || "";
    for (let k = 1; k <= 5; k++) $("lv" + k).checked = n.level === k;
    $("saved").textContent = "";
  }

  function buildScale() {
    const box = $("scale");
    for (let k = 1; k <= 5; k++) {
      const input = document.createElement("input");
      input.type = "radio"; input.name = "level"; input.id = "lv" + k; input.value = k;
      const lab = document.createElement("label");
      lab.htmlFor = input.id; lab.textContent = k;
      input.addEventListener("change", () => setLevel(k));
      box.append(input, lab);
    }
  }

  function note(id) { return (state.notes[id] = state.notes[id] || {}); }
  function setLevel(k) {
    const n = note(line().id);
    n.level = k;
    $("lv" + k).checked = true;
    persist(`감정 세기 ${k}`);
  }
  function persist(what) {
    const ok = save();
    $("saved").textContent = ok ? "저장됨" : "이 브라우저에는 저장되지 않습니다. CSV로 내보내 주세요.";
    paintList();
    if (what) say(what + (ok ? " 저장" : ""));
  }

  // ---- 테이크 -----------------------------------------------------------
  const fmt = (x, d, unit = "") => (x === null || x === undefined ? "-" : Number.isFinite(x) ? x.toFixed(d) + unit : "-∞" + unit);

  function takeCard(t, where) {
    const card = document.createElement("article");
    card.className = "take";
    const verdict = t.error ? `<span class="pill reject">읽기 실패</span>`
      : `<span class="pill ${t.status === "통과" ? "pass" : "reject"}">${t.status}</span>`;
    card.innerHTML = `<div class="take-head">${verdict}${t.example ? '<span class="pill example">예시</span>' : ""}
      <span class="take-name"></span><div class="take-actions"></div></div>`;
    card.querySelector(".take-name").textContent = t.name;
    const actions = card.querySelector(".take-actions");
    const key = t.uid;
    if (audio.has(key)) {
      const play = document.createElement("button");
      play.type = "button"; play.className = "btn small"; play.textContent = "듣기";
      play.addEventListener("click", () => toggle(key, play));
      play.dataset.uid = key;
      actions.append(play);
    }
    const del = document.createElement("button");
    del.type = "button"; del.className = "btn small"; del.textContent = "지우기";
    del.setAttribute("aria-label", `${t.name} 지우기`);
    del.addEventListener("click", () => removeTake(t, where));
    actions.append(del);

    if (t.error) {
      const p = document.createElement("p");
      p.className = "metrics"; p.textContent = t.error;
      card.append(p);
      return card;
    }
    const codes = document.createElement("div");
    codes.className = "codes";
    const chip = (code, kind) => {
      const c = document.createElement("span");
      c.className = "code " + kind;
      c.innerHTML = `<b>${code}</b><span></span>`;
      c.lastChild.textContent = (CODES[code] || {}).text || "";
      codes.append(c);
    };
    t.reject.forEach((c) => chip(c, "reject"));
    t.warn.forEach((c) => chip(c, "warn"));
    if (!t.reject.length && !t.warn.length) chip("OK", "ok"), codes.lastChild.lastChild.textContent = "규격에 맞습니다";
    card.append(codes);

    if (audio.has(key)) {
      const cv = document.createElement("canvas");
      cv.className = "wave"; cv.dataset.uid = key;
      cv.setAttribute("role", "img");
      cv.setAttribute("aria-label", `파형: 말소리 시작 ${fmt(t.speechStart, 1, "초")}, 뒤 여백 ${fmt(t.tail, 2, "초")}`);
      card.append(cv);
    }
    const m = document.createElement("div");
    m.className = "metrics mono";
    m.innerHTML = [
      ["형식", t.format], ["길이", fmt(t.duration, 1, "초")], ["최대", fmt(t.peakDb, 1, " dBFS")],
      ["말소리 시작", fmt(t.speechStart, 1, "초")], ["뒤 여백", fmt(t.tail, 2, "초")],
      ["앞 10초 평균", fmt(t.roomDb, 1, " dBFS")], ["완전0 구간", t.zeroRuns + "개"],
    ].map(([k, v]) => `<span>${k} <b>${v}</b></span>`).join("");
    card.append(m);
    const cmp = where === "line" ? compareBox(t) : null;
    if (cmp) card.append(cmp);
    return card;
  }

  function paintTakes() {
    const box = $("takes");
    box.innerHTML = "";
    const list = takesOf(line().id);
    if (!list.length) {
      const e = document.createElement("div");
      e.className = "empty";
      e.textContent = `아직 이 줄의 테이크가 없습니다. ${nextName(line())} 로 저장해서 올려 주세요.`;
      box.append(e);
    }
    list.slice().reverse().forEach((t) => box.append(takeCard(t, "line")));
    const other = $("unmatched");
    other.innerHTML = "";
    state.other.slice().reverse().forEach((t) => other.append(takeCard(t, "other")));
    $("unmatchedPanel").hidden = !state.other.length;
    requestAnimationFrame(drawAll);
  }

  function removeTake(t, where) {
    if (where === "other") state.other = state.other.filter((x) => x !== t);
    else {
      const id = t.line;
      state.takes[id] = takesOf(id).filter((x) => x !== t);
      if (!state.takes[id].length) delete state.takes[id];
    }
    audio.delete(t.uid);
    stop();
    save();
    paintAll();
    say(`${t.name} 지움`);
  }

  // 음높이(팀 검사기 profile.js와 같은 계산)와 말한 길이. 원래 녹음과 비교할 때 쓴다. 실패해도 검사는 그대로 둔다.
  function measureVoice(r) {
    try {
      const prof = window.VoiceProfile ? window.VoiceProfile.profile(r.samples, r.rate, Math.pow(10, r.peakDb / 20)) : null;
      const an = window.ReadingAnalysis.analyze(r.samples, r.rate);
      return {
        hz: prof && prof.pitch.medianHz ? Math.round(prof.pitch.medianHz) : null,
        rangeSt: prof && prof.pitch.rangeSemitones != null ? +prof.pitch.rangeSemitones.toFixed(1) : null,
        speechSec: an.duration ? +an.duration.toFixed(2) : null,
      };
    } catch (e) { return null; }
  }

  // 원래 녹음의 같은 줄과 나란히 보여 준다. 점수가 아니라 차이만 말한다.
  function compareBox(t) {
    const ref = (window.CITY_REFERENCE || {})[t.line];
    if (!ref || !t.voice) return null;
    const box = document.createElement("div");
    box.className = "compare";
    const parts = [];
    let far = false;
    if (t.voice.hz && ref.hz) {
      const st = 12 * Math.log2(t.voice.hz / ref.hz);
      far = far || Math.abs(st) > 3;
      const how = Math.abs(st) < 0.5 ? "거의 같음" : `${Math.abs(st).toFixed(1)}반음 ${st > 0 ? "높음" : "낮음"}`;
      parts.push(`음높이 <b>${t.voice.hz}Hz</b> (원래 ${ref.hz}Hz, ${how})`);
    }
    if (t.voice.speechSec && ref.speechSec) {
      const pct = Math.round((t.voice.speechSec / ref.speechSec - 1) * 100);
      // 짧은 발화(예: 0.2초)는 0.05초만 달라도 25%라서, 절대 차이도 0.15초 이상일 때만 '차이 큼'으로 본다.
      // 0.15초는 말소리 길이 측정 단위(0.02초)의 약 7배로, 측정 흔들림보다 확실히 큰 값이다. 연기 비교로 다시 정할 수 있다.
      far = far || (Math.abs(pct) > 25 && Math.abs(t.voice.speechSec - ref.speechSec) >= 0.15);
      const how = Math.abs(pct) < 5 ? "거의 같음" : `${Math.abs(pct)}% ${pct > 0 ? "김" : "짧음"}`;
      parts.push(`말한 길이(중간 쉼 포함) <b>${t.voice.speechSec.toFixed(2)}초</b> (원래 ${ref.speechSec.toFixed(2)}초, ${how})`);
    }
    if (!parts.length) return null;
    box.innerHTML = `<b class="compare-title">원래 녹음과 비교</b><span>${parts.join(" · ")}</span>` +
      (ref.uncertain ? `<span class="compare-note">원래 녹음의 이 줄은 자동으로 나눈 경계가 불확실해서 참고만 하세요.</span>` :
        far ? `<span class="compare-note">원래 녹음과 차이가 큽니다(음높이 3반음 또는 길이 25%와 0.15초를 모두 넘게). 의도한 연기인지 들어 보세요.</span>` : "");
    if (far && !ref.uncertain) box.classList.add("far");
    return box;
  }

  let uidSeq = 0;
  async function addFiles(files) {
    const wavs = Array.from(files).filter((f) => /\.wav$/i.test(f.name));
    const skipped = files.length - wavs.length;
    let placed = 0, other = 0, rejected = 0;
    let lastLine = -1;
    for (const f of wavs) {
      let t;
      const uid = "u" + Date.now().toString(36) + (uidSeq++);
      try {
        const r = inspectBuffer(await f.arrayBuffer(), f.name);
        audio.set(uid, { samples: r.samples, rate: r.rate, speech: r.speech, zeroMarks: r.zeroMarks, duration: r.duration });
        t = { ...r, samples: undefined, speech: undefined, zeroMarks: undefined };
        t.voice = measureVoice(r);
      } catch (e) {
        t = { name: f.name, error: e.message, status: "읽기 실패", reject: [], warn: [] };
      }
      t.uid = uid;
      t.checkedAt = new Date().toISOString();
      if (t.status !== "통과") rejected++;
      const m = /^(\d{3})_/.exec(f.name);
      const idx = m ? LINES.findIndex((l) => l.id === m[1]) : -1;
      if (idx >= 0) {
        t.line = LINES[idx].id;
        state.takes[t.line] = takesOf(t.line).filter((x) => !x.example || x.name !== t.name).concat(t);
        placed++; lastLine = idx;
      } else { state.other.push(t); other++; }
    }
    if (wavs.length === 1 && lastLine >= 0) state.cur = lastLine;
    save();
    paintAll();
    const parts = [`${wavs.length}개 검사`];
    if (placed) parts.push(`대본 줄에 ${placed}개`);
    if (other) parts.push(`줄 번호 없는 파일 ${other}개`);
    if (rejected) parts.push(`반려·실패 ${rejected}개`);
    if (skipped) parts.push(`WAV가 아니라 건너뜀 ${skipped}개`);
    say(parts.join(", "));
  }

  // ---- 파형 -------------------------------------------------------------
  function drawAll() { document.querySelectorAll("canvas.wave").forEach((cv) => draw(cv)); }
  function draw(cv, playhead) {
    const a = audio.get(cv.dataset.uid);
    if (!a) return;
    const css = getComputedStyle(document.documentElement);
    const col = (n) => css.getPropertyValue(n).trim();
    const dpr = window.devicePixelRatio || 1;
    const w = cv.clientWidth, h = cv.clientHeight;
    if (!w) return;
    cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr);
    const g = cv.getContext("2d");
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.fillStyle = col("--surface"); g.fillRect(0, 0, w, h);
    const x = (sec) => (sec / a.duration) * w;
    g.fillStyle = col("--room-band"); g.fillRect(0, 0, Math.min(w, x(10)), h);
    const s = a.samples, n = s.length, mid = h / 2;
    const inSpeech = (sec) => a.speech.some((r) => sec >= r.start && sec < r.end);
    const wave = col("--wave"), speech = col("--wave-speech");
    for (let px = 0; px < w; px++) {
      const i0 = Math.floor(px / w * n), i1 = Math.max(i0 + 1, Math.floor((px + 1) / w * n));
      let lo = 0, hi = 0;
      for (let i = i0; i < i1 && i < n; i++) { const v = s[i]; if (v < lo) lo = v; if (v > hi) hi = v; }
      g.fillStyle = inSpeech((px + .5) / w * a.duration) ? speech : wave;
      const top = mid - hi * (mid - 2), bot = mid - lo * (mid - 2);
      g.fillRect(px, top, 1, Math.max(1, bot - top));
    }
    g.fillStyle = col("--zero-mark");
    for (const z of a.zeroMarks) g.fillRect(x(z.start), h - 6, Math.max(2, x(z.end) - x(z.start)), 6);
    if (playhead != null) { g.fillStyle = col("--onair"); g.fillRect(x(playhead), 0, 2, h); }
  }
  let resizeT;
  window.addEventListener("resize", () => { clearTimeout(resizeT); resizeT = setTimeout(drawAll, 120); });
  matchMedia("(prefers-color-scheme: dark)").addEventListener?.("change", drawAll);
  new MutationObserver(drawAll).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

  // ---- 재생 -------------------------------------------------------------
  let ctx = null, playing = null;
  function stop() {
    if (!playing) return;
    try { playing.src.onended = null; playing.src.stop(); } catch (e) { /* 이미 멈춤 */ }
    cancelAnimationFrame(playing.raf);
    const cv = document.querySelector(`canvas.wave[data-uid="${playing.uid}"]`);
    if (cv) draw(cv);
    const btn = document.querySelector(`button[data-uid="${playing.uid}"]`);
    if (btn) btn.textContent = "듣기";
    playing = null;
    $("onair").classList.remove("live");
    $("onair").setAttribute("aria-label", "재생 멈춤");
  }
  function toggle(uid, btn) {
    if (playing && playing.uid === uid) { stop(); return; }
    stop();
    const a = audio.get(uid);
    if (!a) return;
    try {
      ctx = ctx || new (window.AudioContext || window.webkitAudioContext)();
      const buf = ctx.createBuffer(1, a.samples.length, a.rate);
      buf.copyToChannel(a.samples, 0);
      const src = ctx.createBufferSource();
      src.buffer = buf; src.connect(ctx.destination);
      const t0 = ctx.currentTime;
      src.start();
      playing = { uid, src, raf: 0 };
      src.onended = stop;
      const cv = document.querySelector(`canvas.wave[data-uid="${uid}"]`);
      const tick = () => { if (!playing) return; if (cv) draw(cv, ctx.currentTime - t0); playing.raf = requestAnimationFrame(tick); };
      tick();
      if (btn) btn.textContent = "멈춤";
      $("onair").classList.add("live");
      $("onair").setAttribute("aria-label", "재생 중");
    } catch (e) {
      say("이 브라우저에서는 재생할 수 없습니다: " + e.message);
    }
  }

  // ---- 예시 테이크 (처음 열었을 때만, 저장하지 않음) ----------------------
  function exampleTake() {
    if (Object.keys(state.takes).length || state.other.length) return;
    const rate = 48000, sec = 13.25, n = Math.round(rate * sec);
    const bytes = 44 + n * 3, buf = new ArrayBuffer(bytes), v = new DataView(buf);
    const w = (o, s) => { for (let i = 0; i < 4; i++) v.setUint8(o + i, s.charCodeAt(i)); };
    w(0, "RIFF"); v.setUint32(4, bytes - 8, true); w(8, "WAVE"); w(12, "fmt "); v.setUint32(16, 16, true);
    v.setUint16(20, 1, true); v.setUint16(22, 1, true); v.setUint32(24, rate, true); v.setUint32(28, rate * 3, true);
    v.setUint16(32, 3, true); v.setUint16(34, 24, true); w(36, "data"); v.setUint32(40, n * 3, true);
    let seed = 3;
    const rnd = () => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff - 0.5; };
    // 10.5초 룸톤 → "시티 도미니언에 온 걸 환영해!" 길이의 음절 모양 소리 → 0.6초 여백
    const syl = [0.16, 0.14, 0.18, 0.15, 0.14, 0.2, 0.16, 0.15, 0.17, 0.14, 0.16, 0.3];
    let o = 44;
    for (let i = 0; i < n; i++) {
      const t = i / rate;
      let s = 0.00004 * rnd();
      if (t >= 10.5 && t < 12.65) {
        let acc = 10.5, k = 0;
        while (k < syl.length && acc + syl[k] <= t) acc += syl[k++];
        const len = syl[Math.min(k, syl.length - 1)], ph = (t - acc) / len;
        const env = Math.sin(Math.PI * Math.min(1, Math.max(0, ph))) * (k === 4 ? 0.25 : 1);
        const f0 = 210 + 40 * Math.sin((t - 10.5) * 2.2);
        s += 0.8 * env * (Math.sin(2 * Math.PI * f0 * t) + 0.35 * Math.sin(4 * Math.PI * f0 * t) + 0.15 * Math.sin(6 * Math.PI * f0 * t)) / 1.5;
      }
      let x = Math.round(Math.max(-1, Math.min(0.9999, s)) * 8388608);
      if (x === 0) x = 1;
      if (x < 0) x += 0x1000000;
      v.setUint8(o, x & 255); v.setUint8(o + 1, (x >> 8) & 255); v.setUint8(o + 2, (x >> 16) & 255);
      o += 3;
    }
    const name = "001_welcome_take01.wav";
    const r = inspectBuffer(buf, name);
    const uid = "example";
    audio.set(uid, { samples: r.samples, rate: r.rate, speech: r.speech, zeroMarks: r.zeroMarks, duration: r.duration });
    state.takes["001"] = [{ ...r, samples: undefined, speech: undefined, zeroMarks: undefined, uid, line: "001", example: true, voice: measureVoice(r) }];
  }

  // ---- CSV --------------------------------------------------------------
  function notesCsv() {
    const head = ["번호", "키", "장면", "대본 감정", "대사", "시선", "동선", "호흡", "동작", "감정 세기(1-5)", "메모"];
    const rows = LINES.map((l) => {
      const n = state.notes[l.id] || {};
      return [l.id, l.key, l.scene, l.dir, l.text, n.gaze || "", n.move || "", n.breath || "", n.action || "", n.level || "", n.memo || ""];
    });
    return "﻿" + [head, ...rows].map((r) => r.map(csvCell).join(",")).join("\r\n") + "\r\n";
  }
  function checksCsv() {
    const all = [];
    for (const l of LINES) for (const t of realTakes(l.id)) all.push(t);
    for (const t of state.other) all.push(t);
    return toCsv(all);
  }
  function download(name, text) {
    try {
      const url = URL.createObjectURL(new Blob([text], { type: "text/csv;charset=utf-8" }));
      const a = document.createElement("a");
      a.href = url; a.download = name; document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 2000);
      say(`${name} 저장`);
    } catch (e) { say("파일 저장이 막혀 있습니다. 'CSV 복사'를 써 주세요."); }
  }
  async function copy(text, what) {
    try { await navigator.clipboard.writeText(text); say(`${what} 복사됨`); }
    catch (e) { say(`복사가 막혀 있습니다. ${what}: ${text.length > 80 ? "" : text}`); }
  }
  const stamp = () => new Date().toISOString().slice(0, 10);

  // ---- 이동과 키보드 ----------------------------------------------------
  function go(i, focusRow) {
    if (i < 0 || i >= LINES.length) return;
    stop();
    state.cur = i;
    save();
    paintAll();
    const row = $("row" + i);
    row.scrollIntoView({ block: "nearest" });
    if (focusRow) row.focus();
    const l = line();
    say(`${l.id}번, ${l.dir}: ${l.text}`);
  }
  function paintAll() { paintList(); paintCue(); paintTakes(); }

  function nextRetake() {
    for (let k = 1; k <= LINES.length; k++) {
      const i = (state.cur + k) % LINES.length;
      if (lineStatus(LINES[i].id) === "retake") { go(i); return; }
    }
    say("다시 녹음할 줄이 없습니다");
  }

  document.addEventListener("keydown", (e) => {
    const typing = /^(INPUT|TEXTAREA)$/.test(e.target.tagName) && e.target.type !== "radio";
    if (e.key === "Escape" && typing) { e.target.blur(); $("cue").focus(); return; }
    if (typing || e.ctrlKey || e.metaKey || e.altKey) return;
    const k = e.key.toLowerCase();
    if (k === "e") { go(state.cur + 1); }
    else if (k === "q") { go(state.cur - 1); }
    else if (/^[1-5]$/.test(k)) { setLevel(+k); }
    else if (k === " " || e.code === "Space") {
      if (e.target.tagName === "BUTTON") return; // 버튼 위의 Space는 그 버튼을 누름
      const list = takesOf(line().id).filter((t) => audio.has(t.uid));
      if (!list.length) { say("들을 테이크가 없습니다"); }
      else { const t = list[list.length - 1]; toggle(t.uid, document.querySelector(`button[data-uid="${t.uid}"]`)); }
    }
    else if (k === "a") { $("fileInput").click(); }
    else if (k === "w") { $("f_gaze").focus(); }
    else if (k === "c") { copy($("fname").textContent, "파일 이름"); }
    else if (k === "r") { nextRetake(); }
    else return;
    e.preventDefault();
  });

  // ---- 연결 -------------------------------------------------------------
  buildScale();
  buildList();
  for (const f of FIELDS) {
    $("f_" + f).addEventListener("input", (e) => { note(line().id)[f] = e.target.value; persist(); });
  }
  $("prevBtn").addEventListener("click", () => go(state.cur - 1));
  $("nextBtn").addEventListener("click", () => go(state.cur + 1));
  $("copyName").addEventListener("click", () => copy($("fname").textContent, "파일 이름"));
  $("pickBtn").addEventListener("click", () => $("fileInput").click());
  $("fileInput").addEventListener("change", (e) => { addFiles(e.target.files); e.target.value = ""; });
  const drop = $("drop");
  drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("over"); });
  drop.addEventListener("dragleave", () => drop.classList.remove("over"));
  drop.addEventListener("drop", (e) => { e.preventDefault(); drop.classList.remove("over"); addFiles(e.dataTransfer.files); });
  // 파일 저장이 막힌 곳(웹 미리보기)에서는 저장 버튼을 복사 버튼으로 바꾼다.
  if (window.VOICE_STUDIO_NO_DOWNLOAD) {
    $("exportNotes").hidden = true;
    $("exportChecks").textContent = "검사 결과 CSV 복사";
    $("exportChecks").addEventListener("click", () => copy(checksCsv(), "검사 결과 CSV"));
  } else {
    $("exportNotes").addEventListener("click", () => download(`city-dominion-annotation-${stamp()}.csv`, notesCsv()));
    $("exportChecks").addEventListener("click", () => download(`voice-check-${stamp()}.csv`, checksCsv()));
  }
  $("copyNotes").addEventListener("click", () => copy(notesCsv(), "연기 메모 CSV"));

  const rows = $("codeRows");
  for (const code of ["V01", "V02", "V03", "V04", "V05", "V06", "V07", "V08"]) {
    const tr = document.createElement("tr");
    tr.innerHTML = "<td></td><td></td><td></td>";
    tr.children[0].textContent = code;
    tr.children[1].textContent = CODES[code].text;
    tr.children[2].textContent = CODES[code].auto === "자동" ? "앱이 검사" : CODES[code].auto === "일부" ? "일부만" : "귀로 확인";
    rows.append(tr);
  }

  exampleTake();
  paintAll();
  $("row" + state.cur).scrollIntoView({ block: "nearest" });

  // 테스트용
  window.__studio = { state, notesCsv, checksCsv, addFiles };
})();
