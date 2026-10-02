(function (root) {
  'use strict';

  var STORAGE_KEY = 'warmthScorer.v1';
  var EXAMPLE_RATER = '예시';

  /* ================= 순수 함수 (Node에서도 사용) ================= */

  // 항목 5개가 다 있으면 합계(숫자), 하나라도 없으면 null
  function computeTotal(rubric, scores, penalties) {
    if (!rubric || !Array.isArray(rubric.criteria) || !scores) return null;
    var min = rubric.scale ? rubric.scale.min : 0;
    var max = rubric.scale ? rubric.scale.max : 2;
    var sum = 0;
    for (var i = 0; i < rubric.criteria.length; i++) {
      var v = scores[rubric.criteria[i].id];
      if (typeof v !== 'number' || !isFinite(v) || Math.floor(v) !== v || v < min || v > max) return null;
      sum += v;
    }
    var list = Array.isArray(penalties) ? penalties : [];
    var defs = rubric.penalties || [];
    for (var j = 0; j < list.length; j++) {
      for (var k = 0; k < defs.length; k++) {
        if (defs[k].id === list[j]) {
          if (defs[k].effect === 'zero') return 0;
          if (typeof defs[k].effect === 'number') sum += defs[k].effect;
        }
      }
    }
    return sum < 0 ? 0 : sum;
  }

  // 채점 한 건을 JSONL 한 줄(문자열)로. 필드 순서를 고정합니다.
  function toJsonlLine(record) {
    var r = record || {};
    var o = {
      situation: r.situation == null ? '' : r.situation,
      answer_id: r.answer_id == null ? '' : r.answer_id,
      answer: r.answer == null ? '' : r.answer,
      scores: r.scores || {},
      evidence: r.evidence || {},
      penalties: r.penalties || [],
      total: r.total == null ? null : r.total,
      rater: r.rater == null ? '' : r.rater,
      date: r.date == null ? '' : r.date,
      rubric_version: r.rubric_version == null ? '' : r.rubric_version
    };
    if (r.test_only === true) o.test_only = true;
    return JSON.stringify(o);
  }

  function buildJsonl(records) {
    var list = records || [];
    if (!list.length) return '';
    return list.map(toJsonlLine).join('\n') + '\n';
  }

  // 한국 시간이 들어간 ISO 문자열 (예: 2026-10-03T14:20:00+09:00)
  function nowKstIso(now) {
    var d = new Date((now == null ? Date.now() : now) + 9 * 3600 * 1000);
    return d.toISOString().slice(0, 19) + '+09:00';
  }

  function dateStamp(iso) {
    return iso.slice(0, 10).replace(/-/g, '');
  }

  function answerLetter(index) {
    return index < 26 ? String.fromCharCode(65 + index) : 'Z' + (index - 25);
  }

  // 저장 상태에서 내보낼 기록 목록을 만듭니다 (합계가 있는 채점만)
  function buildRecords(rubric, state) {
    var out = [];
    var items = state.items || [];
    var scorings = state.scorings || [];
    for (var i = 0; i < items.length; i++) {
      var item = items[i];
      for (var a = 0; a < item.answers.length; a++) {
        var ans = item.answers[a];
        for (var s = 0; s < scorings.length; s++) {
          var sc = scorings[s];
          if (sc.item_id !== item.id || sc.answer_id !== ans.id || sc.total == null) continue;
          var evidence = {};
          var scores = {};
          for (var c = 0; c < rubric.criteria.length; c++) {
            var cid = rubric.criteria[c].id;
            evidence[cid] = (sc.evidence && sc.evidence[cid]) ? sc.evidence[cid].slice() : [];
            scores[cid] = sc.scores[cid];
          }
          var rec = {
            situation: item.situation,
            answer_id: ans.id,
            answer: ans.text,
            scores: scores,
            evidence: evidence,
            penalties: (sc.penalties || []).slice(),
            total: sc.total,
            rater: sc.rater,
            date: sc.date,
            rubric_version: rubric.version
          };
          if (item.test_only === true) rec.test_only = true;
          out.push(rec);
        }
      }
    }
    return out;
  }

  // 예시 점검: [{id, computed, expected}] (다른 것만 mismatch에 모음)
  function checkExample(rubric, example) {
    var res = [];
    for (var i = 0; i < example.answers.length; i++) {
      var a = example.answers[i];
      var computed = computeTotal(rubric, a.scores, a.penalties);
      res.push({ id: a.id, computed: computed, expected: a.total, ok: computed === a.total });
    }
    return res;
  }

  var api = {
    computeTotal: computeTotal,
    toJsonlLine: toJsonlLine,
    buildJsonl: buildJsonl,
    buildRecords: buildRecords,
    checkExample: checkExample,
    nowKstIso: nowKstIso,
    dateStamp: dateStamp
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.WarmthScorer = api;

  /* ================= 화면 (브라우저에서만) ================= */

  if (typeof document === 'undefined') return;

  var rubric = null;
  var state = { rater: '', items: [], scorings: [], current: null };
  var selectedCriterion = null; // 항목 id 또는 null
  var evidenceTarget = null;    // 마지막으로 고른 항목 (선택이 풀려도 근거 저장에 씀)
  var enterConfirm = false;     // 근거 없는 항목 경고 후 두 번째 Enter 대기

  function $(id) { return document.getElementById(id); }

  function el(tag, attrs, text) {
    var e = document.createElement(tag);
    if (attrs) for (var k in attrs) {
      if (k === 'class') e.className = attrs[k]; else e.setAttribute(k, attrs[k]);
    }
    if (text != null) e.textContent = text;
    return e;
  }

  function say(text) { $('message').textContent = text || ''; }

  /* ---------- 저장 ---------- */

  function save() {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch (e) { /* 저장 불가 */ }
  }

  function load() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      var s = JSON.parse(raw);
      state.rater = typeof s.rater === 'string' ? s.rater : '';
      state.items = Array.isArray(s.items) ? s.items : [];
      state.scorings = Array.isArray(s.scorings) ? s.scorings : [];
      state.current = s.current || null;
    } catch (e) { /* 깨진 저장은 무시 */ }
  }

  /* ---------- 찾기 ---------- */

  function findScoring(itemId, answerId, rater) {
    for (var i = 0; i < state.scorings.length; i++) {
      var s = state.scorings[i];
      if (s.item_id === itemId && s.answer_id === answerId && s.rater === rater) return s;
    }
    return null;
  }

  function getItem(id) {
    for (var i = 0; i < state.items.length; i++) if (state.items[i].id === id) return state.items[i];
    return null;
  }

  function sameContent(item, draft) {
    if (item.situation !== draft.situation || item.answers.length !== draft.answers.length) return false;
    for (var i = 0; i < draft.answers.length; i++) {
      if (item.answers[i].text !== draft.answers[i].text) return false;
    }
    return true;
  }

  function findItemByDraft(draft) {
    for (var i = 0; i < state.items.length; i++) if (sameContent(state.items[i], draft)) return state.items[i];
    return null;
  }

  function addItem(draft) {
    var max = 0;
    state.items.forEach(function (it) {
      var n = parseInt(String(it.id).replace('item-', ''), 10);
      if (n > max) max = n;
    });
    var item = { id: 'item-' + (max + 1), situation: draft.situation, answers: draft.answers };
    if (draft.test_only === true) item.test_only = true;
    if (draft.source) item.source = draft.source;
    state.items.push(item);
    return item;
  }

  /* ---------- 등록 구역 ---------- */

  function readDraft() {
    var answers = [];
    var rows = $('answers-list').querySelectorAll('textarea');
    for (var i = 0; i < rows.length; i++) {
      var t = rows[i].value.trim();
      if (t) answers.push({ id: answerLetter(answers.length), text: t });
    }
    return { situation: $('situation').value.trim(), answers: answers };
  }

  function renumberAnswerRows() {
    var rows = $('answers-list').querySelectorAll('.answer-row');
    for (var i = 0; i < rows.length; i++) {
      var id = answerLetter(i);
      rows[i].querySelector('label').textContent = '답변 ' + id;
      rows[i].querySelector('label').setAttribute('for', 'answer-input-' + id);
      rows[i].querySelector('textarea').id = 'answer-input-' + id;
      rows[i].querySelector('textarea').setAttribute('data-answer-id', id);
      rows[i].querySelector('button').setAttribute('aria-label', '답변 ' + id + ' 빼기');
    }
  }

  function addAnswerRow(text) {
    var row = el('div', { 'class': 'answer-row' });
    row.appendChild(el('label'));
    var ta = el('textarea');
    ta.value = text || '';
    ta.addEventListener('input', refreshRegisterTotals);
    row.appendChild(ta);
    var line = el('div', { 'class': 'row' });
    var rm = el('button', { type: 'button' }, '이 답변 빼기');
    rm.addEventListener('click', function () {
      if ($('answers-list').children.length <= 1) { say('답변은 하나 이상 있어야 합니다.'); return; }
      row.remove();
      renumberAnswerRows();
      refreshRegisterTotals();
    });
    line.appendChild(rm);
    row.appendChild(line);
    $('answers-list').appendChild(row);
    renumberAnswerRows();
    return ta;
  }

  function setAnswerRows(texts) {
    $('answers-list').textContent = '';
    texts.forEach(function (t) { addAnswerRow(t); });
  }

  function totalLabel(sc) {
    if (!sc) return '채점 전';
    if (sc.total != null) return sc.total + '점';
    var n = Object.keys(sc.scores || {}).length;
    return '채점 중 (' + n + '/' + rubric.criteria.length + ')';
  }

  function renderAnswerTotals(containerId, prefix, item) {
    var box = $(containerId);
    box.textContent = '';
    if (!item || !rubric) return;
    var head = el('span', null, '답변별 합계 (평가자 ' + (state.rater || '-') + ')');
    box.appendChild(head);
    item.answers.forEach(function (a) {
      box.appendChild(el('span', { id: prefix + a.id, 'data-answer-id': a.id }, a.id + ': ' + totalLabel(findScoring(item.id, a.id, state.rater))));
    });
  }

  function refreshRegisterTotals() {
    var item = findItemByDraft(readDraft());
    renderAnswerTotals('answer-totals', 'total-', item);
  }

  function loadExample() {
    if (!rubric) { say('기준표를 먼저 불러오세요.'); return; }
    var ex = rubric.examples && rubric.examples[0];
    if (!ex) { say('기준표에 예시가 없습니다.'); return; }
    state.rater = EXAMPLE_RATER;
    $('rater').value = EXAMPLE_RATER;
    $('situation').value = ex.situation;
    setAnswerRows(ex.answers.map(function (a) { return a.text; }));
    var draft = { situation: ex.situation, answers: ex.answers.map(function (a) { return { id: a.id, text: a.text }; }) };
    var item = findItemByDraft(draft) || addItem(draft);
    var now = nowKstIso();
    ex.answers.forEach(function (a) {
      var sc = findScoring(item.id, a.id, EXAMPLE_RATER);
      if (!sc) {
        sc = { item_id: item.id, answer_id: a.id, scores: {}, evidence: {}, penalties: [], total: null, rater: EXAMPLE_RATER, date: now };
        state.scorings.push(sc);
      }
      sc.scores = JSON.parse(JSON.stringify(a.scores));
      sc.evidence = {};
      rubric.criteria.forEach(function (c) { sc.evidence[c.id] = []; });
      sc.penalties = (a.penalties || []).slice();
      sc.total = computeTotal(rubric, sc.scores, sc.penalties); // total을 복사하지 않고 직접 계산
      sc.date = now;
    });
    var bad = checkExample(rubric, ex).filter(function (r) { return !r.ok; });
    $('example-warning').textContent = bad.length
      ? '예시 합계가 맞지 않습니다: ' + bad.map(function (r) { return r.id + ' 계산 ' + r.computed + ', 기준 ' + r.expected; }).join(', ')
      : '';
    save();
    refreshRegisterTotals();
    renderSavedCount();
    say('예시를 불러왔습니다. 평가자는 "' + EXAMPLE_RATER + '"입니다.');
  }

  var testItems = [];

  function fillFormFromTestItem(i) {
    var t = testItems[i];
    if (!t) return;
    $('situation').value = t.situation;
    setAnswerRows(t.answers.map(function (a) { return a.text; }));
    $('example-warning').textContent = '';
    refreshRegisterTotals();
  }

  function useTestItems(data) {
    var list = data && Array.isArray(data.items) ? data.items : null;
    var ok = list && list.length && list.every(function (t) {
      return t && typeof t.situation === 'string' && Array.isArray(t.answers) && t.answers.length;
    });
    if (!ok) {
      say('테스트 문항 형식이 맞지 않습니다.');
      $('test-items-file-wrap').hidden = false;
      return;
    }
    $('test-items-file-wrap').hidden = true;
    testItems = list.map(function (t) {
      return {
        id: t.id, situation: t.situation, source: t.source,
        test_only: t.test_only === true || data.test_only === true,
        answers: t.answers.map(function (a, i) { return { id: answerLetter(i), text: a.text }; })
      };
    });
    testItems.forEach(function (t) {
      var found = findItemByDraft(t);
      if (found) { if (t.test_only) found.test_only = true; }
      else addItem(t);
    });
    save();
    var sel = $('test-item-select');
    sel.textContent = '';
    testItems.forEach(function (t, i) {
      sel.appendChild(el('option', { value: String(i) }, (i + 1) + '. ' + (t.id || '') + ' ' + t.situation.slice(0, 30)));
    });
    $('test-item-wrap').hidden = false;
    $('test-notice').textContent = data.notice || '';
    fillFormFromTestItem(0);
    say('테스트 문항 ' + testItems.length + '개를 불러왔습니다. 채점 시작을 누르세요.');
  }

  function loadTestItems() {
    fetch('test-items.json')
      .then(function (r) { if (!r.ok) throw new Error('fetch'); return r.json(); })
      .then(useTestItems)
      .catch(function () {
        say('테스트 문항을 자동으로 읽지 못했습니다. 아래에서 test-items.json 파일을 열어 주세요.');
        $('test-items-file-wrap').hidden = false;
      });
  }

  function startScoring() {
    if (!rubric) { say('기준표를 먼저 불러오세요.'); return; }
    if (!state.rater.trim()) { say('평가자 이름을 입력하세요.'); $('rater').focus(); return; }
    var draft = readDraft();
    var tsel = testItems.filter(function (t) { return sameContent(t, draft); })[0];
    if (tsel) { draft.test_only = tsel.test_only; draft.source = tsel.source; }
    if (!draft.situation) { say('상황을 입력하세요.'); $('situation').focus(); return; }
    if (!draft.answers.length) { say('AI 답변을 하나 이상 입력하세요.'); return; }
    var item = findItemByDraft(draft) || addItem(draft);
    if (draft.test_only) item.test_only = true;
    state.current = { itemId: item.id, answerIndex: 0 };
    save();
    refreshRegisterTotals();
    showScoring();
    say('채점을 시작합니다.');
  }

  /* ---------- 채점 구역 ---------- */

  function buildCriteria() {
    var box = $('criteria-list');
    box.textContent = '';
    rubric.criteria.forEach(function (c, idx) {
      var row = el('div', { 'class': 'criterion', id: 'criterion-' + c.id, 'data-criterion': c.id });
      var head = el('div', { 'class': 'head' });
      var sel = el('button', { type: 'button', id: 'select-' + c.id, 'data-select-criterion': c.id }, (idx + 1) + '. ' + c.name);
      sel.addEventListener('click', function () { selectCriterion(c.id); });
      head.appendChild(sel);
      head.appendChild(el('span', null, c.question));
      row.appendChild(head);
      var scores = el('div', { 'class': 'scores', role: 'group', 'aria-label': c.name + ' 점수' });
      for (var n = rubric.scale.min; n <= rubric.scale.max; n++) {
        (function (n) {
          var b = el('button', { type: 'button', id: 'score-' + c.id + '-' + n, 'data-criterion': c.id, 'data-score': String(n), 'aria-pressed': 'false' });
          b.appendChild(el('b', null, n + '점'));
          b.appendChild(document.createTextNode(c.levels[String(n)] || ''));
          b.addEventListener('click', function () { setScore(c.id, n); });
          scores.appendChild(b);
        })(n);
      }
      row.appendChild(scores);
      row.appendChild(el('ul', { 'class': 'evidence', id: 'evidence-' + c.id, 'aria-label': c.name + ' 근거' }));
      box.appendChild(row);
    });
  }

  function buildPenalties() {
    var box = $('penalties-list');
    box.textContent = '';
    rubric.penalties.forEach(function (p) {
      var lab = el('label', { 'class': 'penalty' });
      var cb = el('input', { type: 'checkbox', id: 'penalty-' + p.id, 'data-penalty': p.id });
      cb.addEventListener('change', function () { togglePenalty(p.id, cb.checked); });
      lab.appendChild(cb);
      var txt = el('span');
      var name = el('span', null, p.name);
      txt.appendChild(name);
      if (p.effect === 'zero') txt.appendChild(el('span', { 'class': 'zero' }, '합계 0점'));
      else if (typeof p.effect === 'number') txt.appendChild(el('span', { 'class': 'small' }, ' (' + p.effect + '점)'));
      txt.appendChild(el('small', null, p.example));
      lab.appendChild(txt);
      box.appendChild(lab);
    });
  }

  function currentItem() { return state.current ? getItem(state.current.itemId) : null; }
  function currentAnswer() {
    var it = currentItem();
    return it ? it.answers[state.current.answerIndex] : null;
  }

  function currentScoring(create) {
    var it = currentItem(), ans = currentAnswer();
    if (!it || !ans) return null;
    var sc = findScoring(it.id, ans.id, state.rater);
    if (!sc && create) {
      sc = { item_id: it.id, answer_id: ans.id, scores: {}, evidence: {}, penalties: [], total: null, rater: state.rater, date: nowKstIso() };
      rubric.criteria.forEach(function (c) { sc.evidence[c.id] = []; });
      state.scorings.push(sc);
    }
    return sc;
  }

  function touch(sc) {
    sc.total = computeTotal(rubric, sc.scores, sc.penalties);
    sc.date = nowKstIso();
    enterConfirm = false;
    save();
    updateScoringView();
    renderSavedCount();
  }

  function needRater() {
    if (state.rater.trim()) return false;
    say('평가자 이름을 입력하세요.');
    return true;
  }

  function selectCriterion(cid) {
    selectedCriterion = cid;
    evidenceTarget = cid;
    enterConfirm = false;
    updateScoringView();
    var c = rubric.criteria.filter(function (x) { return x.id === cid; })[0];
    say(c.name + ': 점수를 누르세요 (0·1·2)');
  }

  function setScore(cid, n) {
    if (needRater()) return;
    var sc = currentScoring(true);
    sc.scores[cid] = n;
    selectedCriterion = null;
    evidenceTarget = cid;
    touch(sc);
  }

  function togglePenalty(pid, on) {
    if (needRater()) { updateScoringView(); return; }
    var sc = currentScoring(true);
    var i = sc.penalties.indexOf(pid);
    if (on && i < 0) sc.penalties.push(pid);
    if (!on && i >= 0) sc.penalties.splice(i, 1);
    touch(sc);
  }

  function saveEvidence() {
    var cid = selectedCriterion || evidenceTarget;
    if (!cid) { say('먼저 항목을 고르세요 (1~5).'); return; }
    var ta = $('answer-text');
    var s = ta.selectionStart, e = ta.selectionEnd;
    var text = (s == null || e == null || s === e) ? '' : ta.value.slice(s, e).trim();
    if (!text) { say('먼저 답변에서 문장을 고르세요.'); return; }
    if (needRater()) return;
    var sc = currentScoring(true);
    if (!sc.evidence[cid]) sc.evidence[cid] = [];
    sc.evidence[cid].push(text);
    touch(sc);
    var c = rubric.criteria.filter(function (x) { return x.id === cid; })[0];
    say(c.name + '에 근거를 저장했습니다.');
  }

  function deleteEvidence(cid, index) {
    var sc = currentScoring(false);
    if (!sc || !sc.evidence[cid]) return;
    sc.evidence[cid].splice(index, 1);
    touch(sc);
    say('근거를 삭제했습니다.');
  }

  function updateScoringView() {
    var it = currentItem(), ans = currentAnswer();
    if (!it || !ans) return;
    var sc = currentScoring(false);
    $('answer-position').textContent = '답변 ' + (state.current.answerIndex + 1) + ' / ' + it.answers.length + ' (' + ans.id + ')';

    rubric.criteria.forEach(function (c, idx) {
      var row = $('criterion-' + c.id);
      row.classList.toggle('selected', selectedCriterion === c.id);
      for (var n = rubric.scale.min; n <= rubric.scale.max; n++) {
        var pressed = !!sc && sc.scores[c.id] === n;
        $('score-' + c.id + '-' + n).setAttribute('aria-pressed', pressed ? 'true' : 'false');
      }
      var ul = $('evidence-' + c.id);
      ul.textContent = '';
      var list = (sc && sc.evidence && sc.evidence[c.id]) || [];
      list.forEach(function (t, i) {
        var li = el('li');
        li.appendChild(el('span', null, '근거: ' + t));
        var del = el('button', { type: 'button', 'data-evidence-delete': c.id, 'data-index': String(i), 'aria-label': c.name + ' 근거 삭제' }, '삭제');
        del.addEventListener('click', function () { deleteEvidence(c.id, i); });
        li.appendChild(del);
        ul.appendChild(li);
      });
    });

    rubric.penalties.forEach(function (p) {
      $('penalty-' + p.id).checked = !!sc && sc.penalties.indexOf(p.id) >= 0;
    });

    var banner = $('mode-banner');
    if (selectedCriterion) {
      var c = rubric.criteria.filter(function (x) { return x.id === selectedCriterion; })[0];
      banner.textContent = c.name + ': 점수를 누르세요 (0·1·2)';
      banner.classList.add('active');
    } else {
      banner.textContent = '항목을 고르세요 (1~5)';
      banner.classList.remove('active');
    }

    var count = sc ? Object.keys(sc.scores).length : 0;
    var total = $('total');
    if (sc && sc.total != null) {
      var zero = sc.penalties.some(function (pid) {
        return rubric.penalties.some(function (p) { return p.id === pid && p.effect === 'zero'; });
      });
      total.textContent = '합계 ' + sc.total + '점' + (zero ? ' (감점 신호로 0점)' : '');
    } else {
      total.textContent = '채점 중 (' + count + '/' + rubric.criteria.length + ')';
    }
    renderAnswerTotals('answer-totals-scoring', 'scoring-total-', it);
  }

  function renderAnswer() {
    var it = currentItem(), ans = currentAnswer();
    if (!it || !ans) return;
    $('scoring-situation').textContent = it.situation;
    $('test-badge').hidden = it.test_only !== true;
    $('answer-text').value = ans.text;
    selectedCriterion = null;
    evidenceTarget = null;
    enterConfirm = false;
    updateScoringView();
  }

  function showScoring() {
    if (!rubric || !currentItem()) return;
    $('scoring-section').hidden = false;
    renderAnswer();
    $('scoring-section').scrollIntoView();
    $('answer-text').focus();
  }

  function goPrev() {
    if (!state.current || state.current.answerIndex <= 0) { say('첫 답변입니다.'); return; }
    state.current.answerIndex--;
    save();
    renderAnswer();
    $('answer-text').focus();
  }

  function goNext(fromKey) {
    var it = currentItem();
    if (!it) return;
    var sc = currentScoring(false);
    var missing = rubric.criteria.filter(function (c) { return !sc || typeof sc.scores[c.id] !== 'number'; });
    if (missing.length) {
      say('점수가 빠진 항목: ' + missing.map(function (c) { return c.name; }).join(', '));
      return;
    }
    var noEv = rubric.criteria.filter(function (c) { return !sc.evidence || !sc.evidence[c.id] || !sc.evidence[c.id].length; });
    if (noEv.length && !enterConfirm) {
      enterConfirm = true;
      say('근거가 없는 항목: ' + noEv.map(function (c) { return c.name; }).join(', ') + '. 그래도 넘어가려면 Enter를 한 번 더 누르세요.');
      return;
    }
    enterConfirm = false;
    if (state.current.answerIndex >= it.answers.length - 1) {
      say('마지막 답변입니다. 아래에서 내보내세요.');
      $('export-section').scrollIntoView();
      $('export-jsonl').focus();
      return;
    }
    state.current.answerIndex++;
    save();
    renderAnswer();
    $('answer-text').focus();
    say('다음 답변입니다.');
  }

  /* ---------- 저장·내보내기 ---------- */

  function renderSavedCount() {
    var n = state.scorings.filter(function (s) { return s.total != null; }).length;
    $('saved-count').textContent = String(n);
  }

  function exportJsonl() {
    if (!rubric) { say('기준표를 먼저 불러오세요.'); return; }
    var records = buildRecords(rubric, state);
    if (!records.length) { say('내보낼 채점이 없습니다.'); return; }
    var text = buildJsonl(records);
    var blob = new Blob([text], { type: 'application/x-ndjson;charset=utf-8' });
    var url = URL.createObjectURL(blob);
    var a = el('a', { href: url, download: 'warmth-scores-' + dateStamp(nowKstIso()) + '.jsonl' });
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
    say(records.length + '건을 내보냈습니다.');
  }

  function clearAll() {
    if (!window.confirm('저장된 문항과 채점을 모두 삭제할까요?')) return;
    state.items = [];
    state.scorings = [];
    state.current = null;
    save();
    $('scoring-section').hidden = true;
    $('answer-totals').textContent = '';
    $('example-warning').textContent = '';
    renderSavedCount();
    say('전체 삭제했습니다.');
  }

  /* ---------- 키보드 ---------- */

  function isEditable(t) {
    if (!t || !t.tagName) return false;
    if (t.isContentEditable) return true;
    var tag = t.tagName.toUpperCase();
    if (tag === 'SELECT') return true;
    if (tag === 'TEXTAREA') return !t.readOnly;
    if (tag === 'INPUT') {
      var type = (t.type || 'text').toLowerCase();
      if (['checkbox', 'radio', 'button', 'submit', 'reset', 'file'].indexOf(type) >= 0) return false;
      return !t.readOnly;
    }
    return false;
  }

  function onKey(ev) {
    if (ev.ctrlKey || ev.altKey || ev.metaKey || ev.isComposing) return;
    if ($('scoring-section').hidden || !rubric) return;
    if (isEditable(ev.target)) return;
    var tag = ev.target && ev.target.tagName ? ev.target.tagName.toUpperCase() : '';
    var key = ev.key;
    var code = ev.code || '';

    var digit = null;
    if (/^[0-9]$/.test(key)) digit = parseInt(key, 10);
    else if (/^(Digit|Numpad)[0-9]$/.test(code)) digit = parseInt(code.slice(-1), 10);
    var zeroKey = digit === 0 || code === 'Backquote' || key === '`';

    if (selectedCriterion && (digit === 0 || digit === 1 || digit === 2 || zeroKey)) {
      ev.preventDefault();
      setScore(selectedCriterion, zeroKey ? 0 : digit);
      return;
    }
    if (digit >= 1 && digit <= rubric.criteria.length) {
      ev.preventDefault();
      selectCriterion(rubric.criteria[digit - 1].id);
      return;
    }
    if (zeroKey || digit === 0) {
      ev.preventDefault();
      say('먼저 항목을 고르세요 (1~5).');
      return;
    }
    if (key === 'e' || key === 'E' || code === 'KeyE') {
      ev.preventDefault();
      saveEvidence();
      return;
    }
    if (key === 'Escape') {
      if (selectedCriterion) {
        selectedCriterion = null;
        updateScoringView();
        say('항목 선택을 취소했습니다.');
      }
      return;
    }
    if (key === ' ' || code === 'Space') {
      // 버튼·체크박스·링크·select 등에서는 브라우저 기본 동작(누르기)을 둡니다
      if (tag === 'BUTTON' || tag === 'A' || tag === 'SUMMARY' || tag === 'INPUT' || tag === 'SELECT') return;
      ev.preventDefault();
      goNext(true);
      return;
    }
    if (key === 'Enter') {
      if (tag === 'BUTTON' || tag === 'A' || tag === 'SUMMARY') return; // 버튼은 기본 동작
      ev.preventDefault();
      goNext(true);
    }
  }

  /* ---------- 기준표 ---------- */

  function useRubric(data, label) {
    if (!data || !Array.isArray(data.criteria) || !Array.isArray(data.penalties) || !data.scale) {
      $('rubric-status').textContent = '기준표 형식이 맞지 않습니다. 다른 파일을 열어 주세요.';
      $('rubric-file-wrap').hidden = false;
      return;
    }
    rubric = data;
    $('rubric-status').textContent = '기준표 ' + data.version + '을 불러왔습니다' + (label ? ' (' + label + ')' : '') + '.';
    $('rubric-file-wrap').hidden = true;
    buildCriteria();
    buildPenalties();
    if (currentItem()) showScoring();
    refreshRegisterTotals();
    renderSavedCount();
  }

  function loadRubric() {
    fetch('rubric.json')
      .then(function (r) { if (!r.ok) throw new Error('fetch'); return r.json(); })
      .then(function (d) { useRubric(d); })
      .catch(function () {
        $('rubric-status').textContent = '기준표를 자동으로 읽지 못했습니다. 아래에서 rubric.json 파일을 열어 주세요.';
        $('rubric-file-wrap').hidden = false;
      });
  }

  function init() {
    load();
    $('rater').value = state.rater;
    $('rater').addEventListener('input', function () {
      state.rater = $('rater').value.trim();
      save();
      refreshRegisterTotals();
      if (rubric && !$('scoring-section').hidden) updateScoringView();
    });
    $('situation').addEventListener('input', refreshRegisterTotals);
    $('add-answer').addEventListener('click', function () { addAnswerRow('').focus(); });
    $('load-example').addEventListener('click', loadExample);
    $('load-test-items').addEventListener('click', loadTestItems);
    $('test-item-select').addEventListener('change', function () { fillFormFromTestItem(parseInt($('test-item-select').value, 10)); });
    $('test-items-file').addEventListener('change', function (e) {
      var f = e.target.files && e.target.files[0];
      if (!f) return;
      var reader = new FileReader();
      reader.onload = function () {
        try { useTestItems(JSON.parse(reader.result)); }
        catch (err) { say('파일을 읽지 못했습니다. JSON 파일이 맞는지 확인하세요.'); }
      };
      reader.readAsText(f, 'UTF-8');
    });
    $('start-scoring').addEventListener('click', startScoring);
    $('save-evidence').addEventListener('click', saveEvidence);
    $('prev-answer').addEventListener('click', goPrev);
    $('next-answer').addEventListener('click', function () { goNext(false); });
    $('export-jsonl').addEventListener('click', exportJsonl);
    $('clear-all').addEventListener('click', clearAll);
    $('rubric-file').addEventListener('change', function (e) {
      var f = e.target.files && e.target.files[0];
      if (!f) return;
      var reader = new FileReader();
      reader.onload = function () {
        try { useRubric(JSON.parse(reader.result), f.name); }
        catch (err) { $('rubric-status').textContent = '파일을 읽지 못했습니다. JSON 파일이 맞는지 확인하세요.'; }
      };
      reader.readAsText(f, 'UTF-8');
    });
    document.addEventListener('keydown', onKey);
    setAnswerRows(['', '']);
    renderSavedCount();
    loadRubric();
  }

  init();
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
