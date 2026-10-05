// 평가자 일치도(computeAgreement)와 JSONL 읽기(parseJsonl) 테스트. 실행: node apps/warmth-scorer/tests/agreement.test.js
'use strict';
const path = require('path');
const W = require('../app.js');
const rubric = require('../rubric.json');
let fail = 0, n = 0;
const ok = (name, cond, d = '') => { n++; if (!cond) fail++; console.log(`${cond ? 'PASS' : 'FAIL'} ${name}${d ? ' — ' + d : ''}`); };
const ids = rubric.criteria.map((c) => c.id);
const sc = (vals) => Object.fromEntries(ids.map((id, i) => [id, vals[i]]));
const rec = (rater, answer, vals, penalties = []) => ({ situation: '상황1', answer_id: 'A', answer, scores: sc(vals), penalties, rater, total: 0 });

const records = [
  rec('가', '답변 하나', [2, 2, 1, 0, 1]),
  rec('나', '답변 하나', [2, 1, 1, 2, 1]),
  rec('가', '답변 둘', [0, 0, 0, 0, 0], ['ignored_risk']),
  rec('나', '답변 둘', [0, 1, 0, 0, 0], ['ignored_risk']),
  rec('가', '혼자 본 답변', [1, 1, 1, 1, 1]),
];
const r = W.computeAgreement(rubric, records);
ok('2명이 본 답변만 비교(2개)', r.answers === 2 && r.raters.join() === '가,나');
const c = Object.fromEntries(r.criteria.map((x) => [x.id, x]));
ok('첫 항목: 두 답변 모두 같은 점수 → 일치 100%', c[ids[0]].exact === 1 && c[ids[0]].pairs === 2);
ok('둘째 항목: 두 답변 모두 1점씩 다름 → 일치 0%, 1점 이내 100%', c[ids[1]].exact === 0 && c[ids[1]].within1 === 1);
ok('셋째 항목: 모두 같음 → 일치 100%', c[ids[2]].exact === 1);
ok('넷째 항목: 0과 2로 갈림 → 1점 이내 50%', c[ids[3]].within1 === 0.5);
ok('감점 신호 일치 100%', r.penalties.same === 1 && r.penalties.pairs === 2);
ok('가장 크게 갈린 곳이 맨 앞(2점 차)', r.splits[0].spread === 2 && r.splits[0].criterion === rubric.criteria[3].name);
ok('갈린 곳 3건(답변1의 2·4항목, 답변2의 2항목)', r.splits.length === 3, r.splits.map((s) => s.criterion).join(','));

const three = W.computeAgreement(rubric, [rec('가', 'x', [1, 1, 1, 1, 1]), rec('나', 'x', [1, 1, 1, 1, 1]), rec('다', 'x', [2, 1, 1, 1, 1])]);
ok('3명이면 짝 3개, 첫 항목 일치 1/3', three.criteria[0].pairs === 3 && Math.abs(three.criteria[0].exact - 1 / 3) < 1e-9);
const none = W.computeAgreement(rubric, [rec('가', 'x', [1, 1, 1, 1, 1])]);
ok('비교할 답변이 없으면 0과 null', none.answers === 0 && none.criteria[0].exact === null);

const jsonl = W.buildJsonl(records.map((x) => ({ ...x, evidence: {}, date: '2026-10-03', rubric_version: rubric.version })));
const parsed = W.parseJsonl(jsonl + 'not json\n{"x":1}\n');
ok('내보낸 JSONL을 다시 읽음(5줄), 깨진 줄 번호 보고', parsed.records.length === 5 && parsed.bad.join() === '6,7', parsed.bad.join());
ok('다시 읽은 기록으로 같은 결과', W.computeAgreement(rubric, parsed.records).answers === 2);

// 크리펜도르프 알파: 교과서 예시(Krippendorff 2011, 평가자 4명·단위 12개, 서열)는 0.815.
// 같은 계산을 Python krippendorff 패키지와 무작위 299개 자료로 대조해 모두 일치했다(2026-10-05).
const tb = [[1,1,null,1],[2,2,3,2],[3,3,3,3],[3,3,3,3],[2,2,2,2],[1,2,3,4],[4,4,4,4],[1,1,2,1],[2,2,2,2],[null,5,5,5],[null,null,1,1],[null,3,null,null]];
ok('알파 교과서 예시 0.815', Math.abs(W.krippendorffAlpha(tb) - 0.815) < 0.0005, W.krippendorffAlpha(tb).toFixed(4));
ok('알파: 완전 일치면 1', W.krippendorffAlpha([[0, 0], [2, 2], [1, 1]]) === 1);
ok('알파: 모두 같은 점수면 계산 불가(null)', W.krippendorffAlpha([[1, 1], [1, 1]]) === null);
ok('알파: 짝 없는 단위는 무시', W.krippendorffAlpha([[0, 0], [2, 2], [1, null]]) === 1);
ok('알파: 정반대로 갈리면 0보다 작음', W.krippendorffAlpha([[0, 2], [2, 0], [0, 2], [2, 0]]) < 0);
ok('일치도 결과에 항목별 알파(첫 항목 2·2, 0·0 → 1, 둘째 항목 2·1, 0·1 → 0.25)', r.criteria[0].alpha === 1 && Math.abs(r.criteria[1].alpha - 0.25) < 1e-9, String(r.criteria[1].alpha));
console.log(fail ? `\n실패 ${fail}건` : `\n전부 통과 (${n}건)`);
process.exitCode = fail ? 1 : 0;
