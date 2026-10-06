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
    // 같은 감점 신호는 한 번만 센다(기준표: "감점 신호마다 2점"). 불러온 기록에 중복이 있어도 두 번 빼지 않는다(GPT G3-10).
    var list = (Array.isArray(penalties) ? penalties : []).filter(function (p, i, arr) { return arr.indexOf(p) === i; });
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
    if (r.skipped === true) o.skipped = true; // 위기 문항 건너뛰기: 점수 없이 '평가하지 않음'(결측)
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
          if (sc.item_id !== item.id || sc.answer_id !== ans.id) continue;
          if (sc.total == null && sc.skipped !== true) continue;
          var evidence = {};
          var scores = {};
          for (var c = 0; c < rubric.criteria.length; c++) {
            var cid = rubric.criteria[c].id;
            evidence[cid] = (sc.evidence && sc.evidence[cid]) ? sc.evidence[cid].slice() : [];
            scores[cid] = sc.skipped === true ? null : sc.scores[cid];
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
            rubric_version: sc.rubric_version || rubric.version
          };
          if (item.test_only === true) rec.test_only = true;
          if (sc.skipped === true) rec.skipped = true;
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

  // 기록 한 줄 검사. 문제가 있으면 이유(문장), 괜찮으면 null.
  // 점수는 기준표 범위의 유한한 정수만 받습니다. 빈칸(null)과 아예 없는 항목은 '결측'으로 두고, 숫자가 아닌 값·범위 밖·소수는 잘못된 값으로 봅니다.
  function validateRecord(rubric, r) {
    if (!r || typeof r !== 'object' || Array.isArray(r)) return '기록이 객체가 아니에요';
    if (typeof r.rater !== 'string' || !r.rater.trim()) return '평가자 코드가 없어요';
    if (typeof r.situation !== 'string') return '상황이 글이 아니에요';
    if (typeof r.answer !== 'string' || !r.answer) return '답변이 없어요';
    if (!r.scores || typeof r.scores !== 'object' || Array.isArray(r.scores)) return '점수가 객체가 아니에요';
    var min = rubric && rubric.scale ? rubric.scale.min : 0;
    var max = rubric && rubric.scale ? rubric.scale.max : 2;
    var keys = Object.keys(r.scores);
    for (var i = 0; i < keys.length; i++) {
      var v = r.scores[keys[i]];
      if (v === null || v === undefined) continue;
      if (typeof v !== 'number' || !isFinite(v)) return '점수 "' + keys[i] + '"가 유한한 숫자가 아니에요';
      if (Math.floor(v) !== v) return '점수 "' + keys[i] + '"가 정수가 아니에요';
      if (v < min || v > max) return '점수 "' + keys[i] + '"가 범위(' + min + '~' + max + ') 밖이에요';
    }
    if (rubric && Array.isArray(rubric.criteria)) {
      var known = {};
      rubric.criteria.forEach(function (c) { known[c.id] = true; });
      for (var k = 0; k < keys.length; k++) if (!known[keys[k]]) return '기준표에 없는 항목 "' + keys[k] + '"이에요';
    }
    if (r.penalties !== undefined && r.penalties !== null) {
      if (!Array.isArray(r.penalties)) return '감점이 배열이 아니에요';
      var defs = {};
      if (rubric && Array.isArray(rubric.penalties)) rubric.penalties.forEach(function (p) { defs[p.id] = true; });
      for (var j = 0; j < r.penalties.length; j++) {
        if (typeof r.penalties[j] !== 'string') return '감점 항목이 글이 아니에요';
        if (rubric && Array.isArray(rubric.penalties) && !defs[r.penalties[j]]) return '기준표에 없는 감점 "' + r.penalties[j] + '"이에요';
      }
    }
    return null;
  }

  // JSONL 한 덩어리(여러 줄)를 기록 목록으로. 읽지 못한 줄은 번호(bad)와 이유(problems)로 돌려줍니다.
  // rubric을 주면 기준표 항목·점수 범위·감점 이름까지 확인합니다.
  function parseJsonl(text, rubric) {
    var records = [], bad = [], problems = [];
    String(text || '').split(/\r?\n/).forEach(function (line, i) {
      if (!line.trim()) return;
      var reason = null, r = null;
      try { r = JSON.parse(line); } catch (e) { reason = '줄이 JSON이 아니에요'; }
      if (!reason) reason = validateRecord(rubric, r);
      if (reason) { bad.push(i + 1); problems.push({ line: i + 1, reason: reason }); }
      else records.push(r);
    });
    return { records: records, bad: bad, problems: problems };
  }

  // 평가자 일치도. 같은 상황·같은 답변(글자 그대로)을 2명 이상이 채점한 것만 비교합니다.
  // 항목마다 평가자 두 명씩 짝지어 '점수가 같은 비율'과 '1점 이내 비율'을 셉니다(점수가 아니라 기준이 얼마나 같게 읽히는지 보는 값).
  // 크리펜도르프 알파(서열 척도). units는 답변마다 평가자들이 준 점수 배열(빈칸은 null).
  // 우연히 같은 점수가 나올 몫을 뺀 일치도라, 평가자 수가 달라도·빠진 점수가 있어도 쓸 수 있다.
  // 1이면 완전 일치, 0이면 우연 수준. 모두 같은 점수뿐이면 우연 기대치가 0이라 계산할 수 없어 null.
  function krippendorffAlpha(units) {
    var counts = {}, o = {}, n = 0;
    units.forEach(function (vals) {
      var v = vals.filter(function (x) { return typeof x === 'number' && isFinite(x); });
      var m = v.length;
      if (m < 2) return;
      for (var i = 0; i < m; i++) for (var j = 0; j < m; j++) {
        if (i === j) continue;
        var key = v[i] + '|' + v[j];
        o[key] = (o[key] || 0) + 1 / (m - 1);
      }
      v.forEach(function (x) { counts[x] = (counts[x] || 0) + 1; });
      n += m;
    });
    var cats = Object.keys(counts).map(Number).sort(function (a, b) { return a - b; });
    if (n < 2 || cats.length < 2) return null;
    function delta2(c, k) {   // 서열 거리: c와 k 사이(양 끝은 반만) 값들의 개수 합의 제곱
      var lo = Math.min(c, k), hi = Math.max(c, k), s = 0;
      cats.forEach(function (g) { if (g >= lo && g <= hi) s += counts[g]; });
      s -= (counts[lo] + counts[hi]) / 2;
      return s * s;
    }
    var dObs = 0, dExp = 0;
    cats.forEach(function (c) {
      cats.forEach(function (k) {
        if (c === k) return;
        var d = delta2(c, k);
        dObs += (o[c + '|' + k] || 0) * d;
        dExp += counts[c] * counts[k] * d;
      });
    });
    dObs /= n; dExp /= n * (n - 1);
    return dExp === 0 ? null : 1 - dObs / dExp;
  }

  var MIN_ANSWERS = 20;   // 항목마다 '두 명 이상이 점수를 준 답변'이 이보다 적으면 '표본 적음'. 20개를 넘었다고 믿을 만하다는 보장은 아니다.

  function sameRecordContent(a, b, ids) {
    for (var i = 0; i < ids.length; i++) {
      var x = a.scores[ids[i]], y = b.scores[ids[i]];
      if ((typeof x === 'number' ? x : null) !== (typeof y === 'number' ? y : null)) return false;
    }
    return (a.penalties || []).slice().sort().join(',') === (b.penalties || []).slice().sort().join(',');
  }
  function validDate(r) {
    if (typeof r.date !== 'string' || !/^\d{4}-\d{2}-\d{2}/.test(r.date)) return null;
    var t = Date.parse(r.date);
    return isFinite(t) ? t : null;
  }
  function normText(s) { return String(s || '').replace(/\s+/g, ' ').trim(); }

  // 같은 평가자가 같은 답변을 여러 번 냈을 때 하나로 정합니다. 파일을 읽은 순서와 상관없이 같은 결과가 나옵니다.
  // 내용이 같으면 하나로, 다르면 '유효한 날짜가 하나뿐인 최신'을 씁니다. 날짜가 없거나 최신이 동률이면 그 평가자의 그 답변은 뺍니다.
  function resolveDuplicates(list, ids, info, g) {
    var first = list[0], same = true;
    for (var i = 1; i < list.length; i++) if (!sameRecordContent(first, list[i], ids)) same = false;
    if (same) { info.sameDuplicates += list.length - 1; return first; }
    var best = null, tie = false;
    list.forEach(function (r) {
      var t = validDate(r);
      if (t === null) return;
      if (best === null || t > best.t) { best = { t: t, r: r }; tie = false; }
      else if (t === best.t) {
        if (!sameRecordContent(best.r, r, ids)) tie = true;
      }
    });
    var tag = { situation: g.situation, answer_id: g.answer_id, rater: first.rater };
    if (best === null) { tag.reason = '날짜가 없어서 어느 쪽이 최신인지 알 수 없어요'; info.unresolved.push(tag); return null; }
    if (tie) { tag.reason = '가장 최신 날짜가 같은데 내용이 달라요'; info.unresolved.push(tag); return null; }
    var undated = list.filter(function (r) { return validDate(r) === null; }).length;
    tag.reason = '내용이 다른 기록이 ' + list.length + '개라 가장 최신 날짜 것을 썼어요' + (undated ? '(날짜 없는 ' + undated + '개는 뺌)' : '');
    info.conflicts.push(tag);
    return best.r;
  }

  // α의 95% 구간: 같은 상황의 답변들은 서로 닮아서 따로 뽑으면 구간이 좁아 보인다.
  // 그래서 "상황" 단위로 통째로 다시 뽑는다(GPT 아스트라 Q2 제안). 시드를 고정해 같은 자료면 같은 구간이 나온다.
  // 구간을 내지 않는 경우(reason): few(유효 상황 5개 미만), allSame(모든 점수 동일), perfect(관찰 자료에 불일치가 없음),
  // manyFailed(다시 뽑은 자료 중 α를 계산할 수 없는 것이 10% 초과). 실패한 횟수는 0이나 1로 바꾸지 않고 뺀다.
  var BOOT_MIN_CLUSTERS = 5;
  var BOOT_MAX_FAIL = 0.1;
  function bootstrapAlpha(clusters, reps, seed, onSample) {
    var keys = Object.keys(clusters);
    // 유효 상황: 평가자 2명 이상이 점수를 준 답변이 하나라도 있는 상황
    var validKeys = keys.filter(function (k) {
      return clusters[k].some(function (u) { return u.filter(function (v) { return v !== null && v !== undefined; }).length >= 2; });
    });
    var base = { lo: null, hi: null, reps: 0, ok: 0, failed: 0, clusters: keys.length, validClusters: validKeys.length, reason: null };
    if (validKeys.length < BOOT_MIN_CLUSTERS) { base.reason = 'few'; return base; }
    var all = [];
    keys.forEach(function (k) { all = all.concat(clusters[k]); });
    var point = krippendorffAlpha(all);
    if (point == null) { base.reason = 'allSame'; return base; }
    var disagree = all.some(function (u) {
      var nums = u.filter(function (v) { return v !== null && v !== undefined; });
      return nums.length >= 2 && nums.some(function (v) { return v !== nums[0]; });
    });
    if (!disagree) { base.reason = 'perfect'; return base; }
    var st = (seed >>> 0) || 1;
    function rnd() { st |= 0; st = st + 0x6D2B79F5 | 0; var t = Math.imul(st ^ st >>> 15, 1 | st); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }
    var vals = [], failed = 0;
    for (var r = 0; r < reps; r++) {
      var units = [];
      for (var k = 0; k < keys.length; k++) units = units.concat(clusters[keys[Math.floor(rnd() * keys.length)]]);
      if (onSample) onSample(units);
      var a = krippendorffAlpha(units);
      if (a == null) failed++; else vals.push(a);
    }
    base.reps = reps; base.failed = failed; base.ok = vals.length;
    if (reps && failed / reps > BOOT_MAX_FAIL) { base.reason = 'manyFailed'; return base; }
    vals.sort(function (x, y) { return x - y; });
    function q(p) { if (!vals.length) return null; var i = (vals.length - 1) * p, lo = Math.floor(i), hi = Math.ceil(i); return vals[lo] + (vals[hi] - vals[lo]) * (i - lo); }
    base.lo = q(0.025); base.hi = q(0.975);
    if (base.lo == null) base.reason = 'manyFailed';
    return base;
  }

  function computeAgreement(rubric, records) {
    var ids = rubric.criteria.map(function (c) { return c.id; });
    var info = { invalid: 0, otherVersion: 0, otherVersions: {}, noVersion: 0, sameDuplicates: 0, conflicts: [], unresolved: [] };
    var groups = {}, variants = {};
    (records || []).forEach(function (r) {
      if (validateRecord(rubric, r) !== null) { info.invalid++; return; }
      if (r.rubric_version === undefined || r.rubric_version === null || r.rubric_version === '') info.noVersion++;
      else if (rubric.version !== undefined && String(r.rubric_version) !== String(rubric.version)) {
        info.otherVersion++;
        info.otherVersions[r.rubric_version] = (info.otherVersions[r.rubric_version] || 0) + 1;
        return;
      }
      var key = r.situation + '\u0000' + r.answer;
      var g = groups[key] || (groups[key] = { situation: r.situation, answer_id: r.answer_id || '', answer: r.answer, list: {} });
      (g.list[r.rater] || (g.list[r.rater] = [])).push(r);
      var nk = normText(r.situation) + '\u0000' + normText(r.answer);
      var v = variants[nk] || (variants[nk] = { situation: r.situation, answer_id: r.answer_id || '', keys: {}, raters: {} });
      v.keys[key] = true; v.raters[r.rater] = true;
    });
    // 공백만 다른 문항·답변은 합치지 않고 '매칭 후보'로만 알립니다.
    var matchCandidates = [];
    Object.keys(variants).forEach(function (k) {
      var v = variants[k];
      if (Object.keys(v.keys).length > 1) matchCandidates.push({ situation: v.situation, answer_id: v.answer_id, variants: Object.keys(v.keys).length, raters: Object.keys(v.raters).sort() });
    });
    matchCandidates.sort(function (x, y) { return (x.situation + x.answer_id) < (y.situation + y.answer_id) ? -1 : 1; });

    var crit = rubric.criteria.map(function (c) { return { id: c.id, name: c.name, pairs: 0, exact: 0, within1: 0, units: [], clusters: {}, answersUsed: 0, ratings: 0 }; });
    var pen = { pairs: 0, same: 0 };
    var compared = [], raters = {}, splits = [];
    Object.keys(groups).sort().forEach(function (k) {
      var g = groups[k];
      var names = Object.keys(g.list).sort();
      g.byRater = {};
      names.forEach(function (n) {
        var picked = resolveDuplicates(g.list[n], ids, info, g);
        if (picked) g.byRater[n] = picked;
      });
      names = Object.keys(g.byRater).sort();
      if (names.length < 2) return;
      compared.push(g);
      names.forEach(function (n) { raters[n] = true; });
      crit.forEach(function (c) {
        var vals = names.map(function (n) { return g.byRater[n].scores[c.id]; });
        var unit = vals.map(function (v) { return typeof v === 'number' ? v : null; });
        c.units.push(unit);
        (c.clusters[g.situation] || (c.clusters[g.situation] = [])).push(unit);
        var nn = unit.filter(function (v) { return v !== null; }).length;
        if (nn >= 2) { c.answersUsed++; c.ratings += nn; }
        for (var i = 0; i < vals.length; i++) for (var j = i + 1; j < vals.length; j++) {
          if (typeof vals[i] !== 'number' || typeof vals[j] !== 'number') continue;
          c.pairs++;
          if (vals[i] === vals[j]) c.exact++;
          if (Math.abs(vals[i] - vals[j]) <= 1) c.within1++;
        }
        var nums = vals.filter(function (v) { return typeof v === 'number'; });
        if (nums.length >= 2) {
          var spread = Math.max.apply(null, nums) - Math.min.apply(null, nums);
          if (spread > 0) splits.push({ situation: g.situation, answer_id: g.answer_id, criterion: c.name, spread: spread,
            scores: names.map(function (n) { return { rater: n, score: g.byRater[n].scores[c.id] }; }) });
        }
      });
      for (var i = 0; i < names.length; i++) for (var j = i + 1; j < names.length; j++) {
        var a = (g.byRater[names[i]].penalties || []).slice().sort().join(','), b = (g.byRater[names[j]].penalties || []).slice().sort().join(',');
        pen.pairs++;
        if (a === b) pen.same++;
      }
    });
    splits.sort(function (x, y) { return y.spread - x.spread; });
    return {
      answers: compared.length,
      raters: Object.keys(raters).sort(),
      minAnswers: MIN_ANSWERS,
      criteria: crit.map(function (c) {
        return { id: c.id, name: c.name, pairs: c.pairs, answersUsed: c.answersUsed, ratings: c.ratings,
          lowSample: c.answersUsed < MIN_ANSWERS,
          exact: c.pairs ? c.exact / c.pairs : null, within1: c.pairs ? c.within1 / c.pairs : null,
          alpha: krippendorffAlpha(c.units),
          alphaCI: bootstrapAlpha(c.clusters, 2000, 20261005) };
      }),
      penalties: { pairs: pen.pairs, same: pen.pairs ? pen.same / pen.pairs : null },
      splits: splits,
      skipped: info,
      matchCandidates: matchCandidates
    };
  }

  // 알파 읽는 법(Krippendorff의 관례): 0.800 이상 믿을 만함, 0.667 이상 잠정, 그 아래는 기준 문구를 다듬을 곳.
  // 판정은 반올림 전 값으로 합니다. 화면 숫자는 소수 둘째 자리까지만 보여 줍니다.
  // 95% 구간(상황 단위로 다시 뽑기). 구간을 낼 수 없으면 이유를 적는다.
  function ciText(ci) {
    if (!ci) return '';
    if (ci.reason === 'few') return ' · 구간은 유효 상황 5개부터';
    if (ci.reason === 'allSame') return ' · 모든 점수가 같아 구간을 낼 수 없어요';
    if (ci.reason === 'perfect') return ' · 불일치가 없어 구간을 낼 수 없어요(표본이 작으면 우연일 수 있어요)';
    if (ci.reason === 'manyFailed') return ' · 계산할 수 없는 재표집이 많아 구간을 믿기 어려워요';
    if (ci.lo == null) return ' · 구간 계산 불가';
    var f = function (v) { return (Math.round(v * 100) / 100).toFixed(2); };
    return ' (95% ' + f(ci.lo) + '~' + f(ci.hi) + ')';
  }
  // 다시 뽑기에서 α를 계산할 수 없어 뺀 횟수. 구간을 시도하지 않았으면 빈 글.
  function ciFailText(ci) {
    if (!ci || !ci.reps) return '';
    return ' · ' + ci.reps.toLocaleString('en-US') + '번 중 ' + ci.failed + '번은 계산할 수 없어 뺐어요';
  }
  function alphaText(a) {
    if (a == null) return '계산 불가';
    var v = (Math.round(a * 100) / 100).toFixed(2);
    return v + (a >= 0.8 ? ' 믿을 만함' : a >= 0.667 ? ' 잠정' : ' 다듬기');
  }

  var api = {
    computeTotal: computeTotal,
    toJsonlLine: toJsonlLine,
    buildJsonl: buildJsonl,
    buildRecords: buildRecords,
    checkExample: checkExample,
    parseJsonl: parseJsonl,
    validateRecord: validateRecord,
    alphaText: alphaText,
    ciText: ciText,
    ciFailText: ciFailText,
    MIN_ANSWERS: MIN_ANSWERS,
    computeAgreement: computeAgreement,
    krippendorffAlpha: krippendorffAlpha,
    bootstrapAlpha: bootstrapAlpha,
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
    var w = document.getElementById('save-warning');
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      if (w) w.textContent = '';
    } catch (e) {
      if (w) w.textContent = '이 브라우저에 저장하지 못했습니다. 지금까지 채점한 것을 바로 JSONL로 내보내 두세요.';
    }
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
      state.draft = (s.draft && Array.isArray(s.draft.answers)) ? s.draft : null;
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
    if ((item.test_only === true) !== (draft.test_only === true)) return false; // 실제 문항과 테스트 문항은 별개
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
    if (draft.sensitive === true) item.sensitive = true;
    if (draft.source) item.source = draft.source;
    if (draft.test_item_id) item.test_item_id = draft.test_item_id;
    state.items.push(item);
    return item;
  }

  /* ---------- 등록 구역 ---------- */

  // 테스트 문항으로 채운 칸이면, 본문을 고쳐도 테스트용 표시와 출처를 유지합니다.
  // 표시는 폼을 비우는 동작(새 문항 시작·예시 불러오기)에서만 사라집니다.
  function markDraftTest(draft) {
    if (formTest) {
      if (formTest.test_only === true) draft.test_only = true; // 실제 평가 묶음 문항은 테스트용 표시를 붙이지 않음
      if (formTest.source) draft.source = formTest.source;
      if (formTest.id) draft.test_item_id = formTest.id;
      if (formTest.sensitive === true) draft.sensitive = true;
    }
    return draft;
  }

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
    ta.addEventListener('input', function () { refreshRegisterTotals(); });
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

  function saveDraft() {
    var rows = $('answers-list').querySelectorAll('textarea');
    var texts = [];
    for (var i = 0; i < rows.length; i++) texts.push(rows[i].value);
    state.draft = { situation: $('situation').value, answers: texts, test: formTest };
    save();
  }

  function setAnswerRows(texts) {
    $('answers-list').textContent = '';
    texts.forEach(function (t) { addAnswerRow(t); });
  }

  function totalLabel(sc) {
    if (!sc) return '채점 전';
    if (sc.skipped === true && sc.total == null) return '건너뜀(평가하지 않음)';
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
    var item = findItemByDraft(markDraftTest(readDraft()));
    renderAnswerTotals('answer-totals', 'total-', item);
    saveDraft();
  }

  function loadExample() {
    if (!rubric) { say('기준표를 먼저 불러오세요.'); return; }
    formTest = null;
    showContext('');
    updateGate();
    closeScoring();
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
        sc = { item_id: item.id, answer_id: a.id, scores: {}, evidence: {}, penalties: [], total: null, rater: EXAMPLE_RATER, date: now, rubric_version: rubric.version };
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
  var formTest = null; // 칸이 테스트 문항으로 채워졌으면 {id, source}. 칸을 고쳐도 유지됩니다.

  // 채점 화면을 닫습니다 (평가자·문항이 바뀌어 화면과 기록이 어긋나는 것을 막음)
  function closeScoring() {
    if ($('scoring-section').hidden) return;
    $('scoring-section').hidden = true;
    state.current = null;
    selectedCriterion = null;
    evidenceTarget = null;
    enterConfirm = false;
    save();
  }

  function newItem() {
    formTest = null;
    showContext('');
    updateGate();
    $('situation').value = '';
    setAnswerRows(['', '']);
    $('example-warning').textContent = '';
    refreshRegisterTotals();
    $('situation').focus();
    say('새 문항을 시작합니다. 칸을 비웠습니다.');
  }

  // 문항에 상황 설명(context)이 있으면 상황 칸 아래에 보여 줍니다. 없으면 숨깁니다.
  function showContext(text) {
    var box = $('situation-context');
    box.textContent = text ? '배경: ' + text : '';
    box.hidden = !text;
  }

  function fillFormFromTestItem(i) {
    var t = testItems[i];
    if (!t) return;
    formTest = { id: t.id, source: t.source };
    if (t.test_only === true) formTest.test_only = true;
    if (t.sensitive) formTest.sensitive = true;
    revealedKey = null; // 문항을 고를 때마다 위기 문항은 다시 접습니다
    if (t.sensitive && !$('scoring-section').hidden) closeScoring(); // 채점 화면에 이전 위기 문항 본문이 남지 않게
    showContext(t.context);
    $('situation').value = t.situation;
    setAnswerRows(t.answers.map(function (a) { return a.text; }));
    $('example-warning').textContent = '';
    updateGate();
    refreshRegisterTotals();
    if (t.sensitive) say('위기 문항이에요. 본문은 접어 두었어요. 읽기나 건너뛰기를 골라 주세요.');
  }

  /* ---------- 위기 문항: 본문을 접고 읽기·건너뛰기를 먼저 묻기 (calibration.md '위기 문항을 채점할 때') ---------- */

  var revealedKey = null; // 평가자가 [읽기]를 고른 위기 문항의 id. 문항을 바꾸면 비웁니다.

  function gateFolded() {
    return !!(formTest && formTest.sensitive && revealedKey !== formTest.id);
  }

  function updateGate() {
    var folded = gateFolded();
    $('register-body').hidden = folded;
    $('sensitive-gate').hidden = !folded;
    if (!folded) $('gate-status').textContent = '';
  }

  function readSensitive() {
    if (!formTest || !formTest.sensitive) return;
    revealedKey = formTest.id;
    updateGate();
    $('situation').focus();
    say('본문을 열었어요. 읽고 나면 채점 시작을 눌러 주세요. 힘들면 언제든 쉬어도 돼요.');
  }

  function skipSensitive() {
    if (!formTest || !formTest.sensitive) return;
    if (!rubric) { say('기준표를 먼저 불러오세요.'); return; }
    if (!state.rater.trim()) { say('평가자 코드를 입력해 주세요.'); $('rater').focus(); return; }
    var draft = markDraftTest(readDraft());
    var item = findItemByDraft(draft) || addItem(draft);
    item.sensitive = true;
    var i, sc;
    for (i = 0; i < item.answers.length; i++) {
      sc = findScoring(item.id, item.answers[i].id, state.rater);
      if (sc && sc.total != null) { say('이미 채점한 문항이라 건너뛸 수 없어요.'); return; }
    }
    for (i = 0; i < item.answers.length; i++) {
      sc = findScoring(item.id, item.answers[i].id, state.rater);
      if (!sc) {
        sc = { item_id: item.id, answer_id: item.answers[i].id, scores: {}, evidence: {}, penalties: [], total: null, rater: state.rater, date: nowKstIso(), rubric_version: rubric.version };
        state.scorings.push(sc);
      }
      sc.scores = {}; sc.evidence = {}; sc.penalties = []; sc.total = null; sc.skipped = true; sc.date = nowKstIso();
    }
    save();
    refreshRegisterTotals();
    renderSavedCount();
    var msg = '건너뛰었어요. 0점이 아니라 평가하지 않음으로 남아요. 다음 문항을 골라 주세요.';
    $('gate-status').textContent = msg;
    say(msg);
  }

  function useTestItems(data) {
    var list = data && Array.isArray(data.items) ? data.items : null;
    var ok = list && list.length && list.every(function (t) {
      return t && typeof t.situation === 'string' && Array.isArray(t.answers) && t.answers.length;
    });
    // 평가 묶음(test_only가 아닌 파일)은 실제 문항으로 넣는다. 문구만 다르고 처리는 같다.
    var kind = data && data.test_only === true ? '테스트 문항' : '평가 묶음 문항';
    if (!ok) {
      say(kind + ' 형식이 맞지 않습니다.');
      if (kind === '테스트 문항') $('test-items-file-wrap').hidden = false;
      return;
    }
    $('test-items-file-wrap').hidden = true;
    testItems = list.map(function (t) {
      return {
        id: t.id, test_item_id: t.id, situation: t.situation, source: t.source,
        context: typeof t.context === 'string' ? t.context : '',
        test_only: t.test_only === true || data.test_only === true,
        sensitive: t.sensitive === true,
        answers: t.answers.map(function (a, i) { return { id: answerLetter(i), text: a.text }; })
      };
    });
    testItems.forEach(function (t) {
      var found = findItemByDraft(t);
      if (!found) addItem(t); // 같은 내용의 기존(실제) 문항은 건드리지 않음
      else if (t.sensitive) found.sensitive = true;
    });
    save();
    var sel = $('test-item-select');
    sel.textContent = '';
    testItems.forEach(function (t, i) {
      sel.appendChild(el('option', { value: String(i) }, (i + 1) + '. ' + (t.id || '') + ' ' + (t.sensitive ? '(위기 문항, 본문 접힘)' : t.situation.slice(0, 30))));
    });
    $('test-item-wrap').hidden = false;
    $('test-notice').textContent = data.notice || '';
    closeScoring();
    fillFormFromTestItem(0);
    say(kind + ' ' + testItems.length + '개를 불러왔습니다. 채점 시작을 누르세요.');
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
    if (!state.rater.trim()) { say('평가자 코드를 입력해 주세요.'); $('rater').focus(); return; }
    if (gateFolded()) { say('위기 문항이에요. 먼저 읽기나 건너뛰기를 골라 주세요.'); $('gate-read').focus(); return; }
    var draft = readDraft();
    markDraftTest(draft);
    if (!draft.situation) { say('상황을 입력하세요.'); $('situation').focus(); return; }
    if (!draft.answers.length) { say('AI 답변을 하나 이상 입력하세요.'); return; }
    var item = findItemByDraft(draft) || addItem(draft);
    if (draft.sensitive) item.sensitive = true;
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
      sc = { item_id: it.id, answer_id: ans.id, scores: {}, evidence: {}, penalties: [], total: null, rater: state.rater, date: nowKstIso(), rubric_version: rubric.version };
      rubric.criteria.forEach(function (c) { sc.evidence[c.id] = []; });
      state.scorings.push(sc);
    }
    return sc;
  }

  function touch(sc) {
    sc.total = computeTotal(rubric, sc.scores, sc.penalties);
    delete sc.skipped; // 점수를 매기면 건너뜀 표시는 풀립니다
    sc.date = nowKstIso();
    enterConfirm = false;
    save();
    updateScoringView();
    renderSavedCount();
  }

  function needRater() {
    if (state.rater.trim()) return false;
    say('평가자 코드를 입력해 주세요.');
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
    var left = sc.evidence[cid].length;
    var next = left ? document.querySelector('[data-evidence-delete="' + cid + '"][data-index="' + Math.min(index, left - 1) + '"]') : $('select-' + cid);
    if (next) next.focus();
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
        var tid = 'evidence-text-' + c.id + '-' + i;
        li.appendChild(el('span', { id: tid }, '근거: ' + t));
        var del = el('button', { type: 'button', 'data-evidence-delete': c.id, 'data-index': String(i), 'aria-label': c.name + ' 근거 ' + (i + 1) + ' 삭제', 'aria-describedby': tid }, '삭제');
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
    var cur = currentItem();
    if (cur.sensitive === true && !(revealedKey && cur.test_item_id === revealedKey)) { state.current = null; save(); return; } // 위기 문항은 읽기를 고르기 전에는 열지 않음
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
      say('근거가 없는 항목: ' + noEv.map(function (c) { return c.name; }).join(', ') + '. 그래도 넘어가려면 Enter나 Space를 한 번 더 누르세요.');
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

  /* ---------- 평가자 일치도 ---------- */
  var extraRecords = [];   // 다른 평가자 파일에서 읽은 기록(저장하지 않고 이 화면에서만 씀)
  var extraSkipped = { count: 0, reasons: [] };   // 읽지 못해 건너뛴 줄: 개수와 이유
  function pct(v) { return v == null ? '-' : Math.round(v * 100) + '%'; }
  function listText(items, max) {
    return items.slice(0, max).join(' / ') + (items.length > max ? ' 외 ' + (items.length - max) + '건' : '');
  }
  function agreementNotes(r) {
    var notes = [], s = r.skipped;
    if (extraSkipped.count) {
      notes.push('읽지 못한 줄 ' + extraSkipped.count + '개는 건너뛰었어요. 이유: ' + listText(extraSkipped.reasons.map(function (x) { return x.file + ' ' + x.line + '번째 줄 ' + x.reason; }), 5) + '.');
    }
    if (s.invalid) notes.push('형식이 맞지 않아 뺀 기록이 ' + s.invalid + '건 있어요.');
    if (s.otherVersion) {
      notes.push('현재 기준표(' + rubric.version + ')와 다른 버전 기록 ' + s.otherVersion + '건은 섞지 않고 뺐어요(' +
        Object.keys(s.otherVersions).map(function (v) { return v + ' ' + s.otherVersions[v] + '건'; }).join(', ') + ').');
    }
    if (s.noVersion) notes.push('기준표 버전이 적혀 있지 않은 기록이 ' + s.noVersion + '건 있어요. 같은 기준표로 채점했는지 확인해 주세요.');
    if (s.sameDuplicates) notes.push('같은 평가자가 같은 내용으로 낸 중복 기록 ' + s.sameDuplicates + '건은 하나로 쳤어요.');
    if (s.conflicts.length) {
      notes.push('같은 평가자의 같은 답변에 내용이 다른 기록이 있어 최신 날짜 것을 썼어요: ' + listText(s.conflicts.map(function (x) { return x.rater + ' · 답변 ' + x.answer_id; }), 5) + '.');
    }
    if (s.unresolved.length) {
      notes.push('날짜가 없거나 최신이 같아서 고르지 못해 뺀 기록이 있어요: ' + listText(s.unresolved.map(function (x) { return x.rater + ' · 답변 ' + x.answer_id + '(' + x.reason + ')'; }), 5) + '. 날짜를 확인해 주세요.');
    }
    if (r.matchCandidates.length) {
      notes.push('공백만 다른 문항·답변이 있어요. 합치지 않았어요. 같은 답변이면 글을 맞춘 뒤 다시 불러 주세요: ' + listText(r.matchCandidates.map(function (x) { return '답변 ' + (x.answer_id || '?') + '(' + x.raters.join(', ') + ')'; }), 5) + '.');
    }
    return notes;
  }
  function showAgreement() {
    if (!rubric) { $('agree-status').textContent = '기준표를 먼저 불러오세요.'; return; }
    var mine = buildRecords(rubric, state);
    var r = computeAgreement(rubric, mine.concat(extraRecords));
    var box = $('agree-result');
    box.textContent = '';
    if (!r.answers) {
      $('agree-status').textContent = '두 사람 이상이 채점한 같은 답변이 아직 없어요. 평가자 코드를 바꿔 같은 문항을 채점하거나, 다른 평가자의 JSONL을 더해 주세요.';
      agreementNotes(r).forEach(function (n) { box.appendChild(el('p', { class: 'hint' }, n)); });
      return;
    }
    $('agree-status').textContent = '비교한 답변 ' + r.answers + '개 · 평가자 ' + r.raters.join(', ') + ' · 감점 신호가 같았던 비율 ' + pct(r.penalties.same);
    var t = el('table');
    var head = el('tr');
    ['항목', '같은 점수', '1점 이내', '신뢰도 α', '유효 답변', '유효 상황', '평가 수', '비교한 짝'].forEach(function (h) { head.appendChild(el('th', { scope: 'col' }, h)); });
    t.appendChild(el('thead')).appendChild(head);
    var body = t.appendChild(el('tbody'));
    var anyLow = false;
    r.criteria.forEach(function (c) {
      var tr = el('tr');
      tr.appendChild(el('th', { scope: 'row' }, c.name));
      tr.appendChild(el('td', { class: 'n' }, pct(c.exact)));
      tr.appendChild(el('td', { class: 'n' }, pct(c.within1)));
      if (c.lowSample) anyLow = true;
      tr.appendChild(el('td', { class: 'n' }, alphaText(c.alpha) + ciText(c.alphaCI) + ciFailText(c.alphaCI) + (c.lowSample ? ' · 표본 적음' : '')));
      tr.appendChild(el('td', { class: 'n' }, String(c.answersUsed)));
      tr.appendChild(el('td', { class: 'n' }, String(c.alphaCI.validClusters)));
      tr.appendChild(el('td', { class: 'n' }, String(c.ratings)));
      tr.appendChild(el('td', { class: 'n' }, String(c.pairs)));
      body.appendChild(tr);
    });
    box.appendChild(t);
    box.appendChild(el('p', { class: 'hint' }, '신뢰도 α는 우연히 같은 점수가 나올 몫을 뺀 일치도예요(크리펜도르프 알파, 1이 완전 일치, 0이 우연 수준). 모두 같은 점수만 주면 계산할 수 없어요. ' +
      '판정 경계는 0.667과 0.800이에요: 0.800 이상은 믿을 만함, 0.667 이상은 잠정, 그 아래는 기준 문구를 다듬을 항목이에요. 화면 숫자는 소수 둘째 자리까지만 보여서, 0.7999가 0.80으로 보여도 판정은 반올림 전 값으로 해 잠정이에요. ' +
      '"유효 답변"은 그 항목에 두 사람 이상이 점수를 준 답변 수예요. 이 수가 ' + r.minAnswers + '개보다 적으면 "표본 적음"으로 표시하고 숫자는 크게 흔들려요. ' +
      r.minAnswers + '개는 최소 기준일 뿐, 넘었다고 믿을 만하다는 보장은 아니에요.' +
      (anyLow ? ' 지금 "표본 적음"인 항목이 있어요. 참고로만 봐 주세요.' : '')));
    box.appendChild(el('p', { class: 'hint' }, '괄호 안 95% 구간은 상황 단위로 다시 뽑는 백분위 부트스트랩이에요(반복 2,000회, 시드 20261005). ' +
      '"유효 상황"은 그 항목에 두 사람 이상이 점수를 준 답변이 하나라도 있는 상황 수이고, 5개보다 적으면 구간을 내지 않아요. ' +
      '상황이 적으면 구간이 크게 흔들리고, 95% 구간이 참값을 95% 확률로 담는다는 뜻은 아니에요.'));
    agreementNotes(r).forEach(function (n) { box.appendChild(el('p', { class: 'hint' }, n)); });
    if (r.splits.length) {
      box.appendChild(el('p', null, '많이 갈린 곳 (큰 차이부터, 10곳까지)'));
      var ul = el('ul');
      r.splits.slice(0, 10).forEach(function (sp) {
        var who = sp.scores.map(function (x) { return x.rater + ' ' + (x.score == null ? '-' : x.score); }).join(' · ');
        ul.appendChild(el('li', null, '[' + sp.criterion + '] ' + (sp.situation.length > 30 ? sp.situation.slice(0, 30) + '…' : sp.situation) + ' / 답변 ' + sp.answer_id + ' — ' + who));
      });
      box.appendChild(ul);
    }
  }
  // 파일을 모두 읽은 뒤에 한꺼번에 더합니다. 읽기가 끝나는 순서와 상관없이 파일을 고른 순서대로 쌓아요.
  function addAgreementFiles(files) {
    var list = Array.prototype.slice.call(files || []);
    if (!list.length) return;
    var done = 0, results = new Array(list.length);
    function finish() {
      var added = 0, badLines = 0;
      results.forEach(function (res, idx) {
        if (!res) { extraSkipped.count++; extraSkipped.reasons.push({ file: list[idx].name, line: 0, reason: '파일을 읽지 못했어요' }); return; }
        extraRecords = extraRecords.concat(res.records);
        added += res.records.length; badLines += res.bad.length;
        extraSkipped.count += res.bad.length;
        res.problems.forEach(function (p) { extraSkipped.reasons.push({ file: list[idx].name, line: p.line, reason: p.reason }); });
      });
      showAgreement();
      $('agree-status').textContent = '파일 ' + list.length + '개에서 채점 ' + added + '건을 더했어요' + (badLines ? ' (읽지 못한 줄 ' + badLines + '개는 건너뛰었어요)' : '') + '. ' + $('agree-status').textContent;
    }
    list.forEach(function (f, idx) {
      var reader = new FileReader();
      reader.onload = function () {
        results[idx] = parseJsonl(reader.result, rubric);
        if (++done === list.length) finish();
      };
      reader.onerror = function () { if (++done === list.length) finish(); };
      reader.readAsText(f, 'UTF-8');
    });
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
    var rep = !!ev.repeat; // 길게 누른 반복은 채점·이동에 쓰지 않음
    var zeroKey = digit === 0 || code === 'Backquote' || key === '`';

    if (selectedCriterion && (digit === 0 || digit === 1 || digit === 2 || zeroKey)) {
      ev.preventDefault();
      if (rep) return;
      setScore(selectedCriterion, zeroKey ? 0 : digit);
      return;
    }
    if (digit >= 1 && digit <= rubric.criteria.length) {
      ev.preventDefault();
      if (rep) return;
      selectCriterion(rubric.criteria[digit - 1].id);
      return;
    }
    if (zeroKey || digit === 0) {
      ev.preventDefault();
      if (rep) return;
      say('먼저 항목을 고르세요 (1~5).');
      return;
    }
    if (key === 'e' || key === 'E' || code === 'KeyE') {
      ev.preventDefault();
      if (rep) return;
      saveEvidence();
      return;
    }
    if (key === 'Escape') {
      if (selectedCriterion || evidenceTarget) {
        selectedCriterion = null;
        evidenceTarget = null;
        updateScoringView();
        say('항목 선택을 취소했습니다.');
      } else {
        say('항목을 고르세요 (1~5).');
      }
      return;
    }
    if (key === ' ' || code === 'Space') {
      // 버튼·체크박스·링크·select 등에서는 브라우저 기본 동작(누르기)을 둡니다
      if (tag === 'BUTTON' || tag === 'A' || tag === 'SUMMARY' || tag === 'INPUT' || tag === 'SELECT') return;
      ev.preventDefault();
      if (rep) return;
      goNext(true);
      return;
    }
    if (key === 'Enter') {
      if (tag === 'BUTTON' || tag === 'A' || tag === 'SUMMARY' || tag === 'INPUT' || tag === 'SELECT') return; // 기본 동작을 둡니다
      ev.preventDefault();
      if (rep) return;
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
      selectedCriterion = null;
      evidenceTarget = null;
      enterConfirm = false;
      save();
      refreshRegisterTotals();
      if (rubric && !$('scoring-section').hidden) updateScoringView();
    });
    $('situation').addEventListener('input', function () { refreshRegisterTotals(); });
    $('add-answer').addEventListener('click', function () { addAnswerRow('').focus(); saveDraft(); });
    $('new-item').addEventListener('click', newItem);
    $('load-example').addEventListener('click', loadExample);
    $('load-test-items').addEventListener('click', loadTestItems);
    $('open-pack').addEventListener('click', function () { $('pack-file').click(); });
    $('pack-file').addEventListener('change', function (e) {
      var f = e.target.files && e.target.files[0];
      if (!f) return;
      var reader = new FileReader();
      reader.onload = function () {
        try { useTestItems(JSON.parse(reader.result)); }
        catch (err) { say('평가 묶음 파일을 읽지 못했습니다. JSON 파일이 맞는지 확인하세요.'); }
        e.target.value = '';
      };
      reader.readAsText(f, 'UTF-8');
    });
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
    $('gate-read').addEventListener('click', readSensitive);
    $('gate-skip').addEventListener('click', skipSensitive);
    $('start-scoring').addEventListener('click', startScoring);
    $('save-evidence').addEventListener('click', saveEvidence);
    $('prev-answer').addEventListener('click', goPrev);
    $('next-answer').addEventListener('click', function () { goNext(false); });
    $('export-jsonl').addEventListener('click', exportJsonl);
    $('clear-all').addEventListener('click', clearAll);
    $('agree-mine').addEventListener('click', showAgreement);
    $('agree-add').addEventListener('click', function () { $('agree-files').click(); });
    $('agree-files').addEventListener('change', function (e) { addAgreementFiles(e.target.files); e.target.value = ''; });
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
    if (state.draft) {
      formTest = state.draft.test && typeof state.draft.test === 'object' ? state.draft.test : null;
      $('situation').value = typeof state.draft.situation === 'string' ? state.draft.situation : '';
      setAnswerRows(state.draft.answers.length ? state.draft.answers.map(String) : ['', '']);
      updateGate();
    } else {
      setAnswerRows(['', '']);
    }
    renderSavedCount();
    loadRubric();
  }

  init();
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
