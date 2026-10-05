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
// ---- R7(A4) 보완 ----
const V = rubric.version;
const rv = (rater, answer, vals, extra = {}) => ({ ...rec(rater, answer, vals), rubric_version: V, date: '2026-10-03', ...extra });
const line = (o) => JSON.stringify(o) + '\n';

// 지적 1: 입력 검증
const good = rv('가', 'x', [1, 1, 1, 1, 1]);
const infLine = JSON.stringify(good).replace('"' + ids[0] + '":1', '"' + ids[0] + '":1e400');
const bads = [
  ['감점이 {}', JSON.stringify({ ...good, penalties: {} })],
  ['점수 범위 밖(3)', JSON.stringify({ ...good, scores: sc([3, 1, 1, 1, 1]) })],
  ['점수 소수(0.5)', JSON.stringify({ ...good, scores: sc([0.5, 1, 1, 1, 1]) })],
  ['점수 1e400(무한)', infLine],
  ['점수가 글자', JSON.stringify({ ...good, scores: sc(['1', 1, 1, 1, 1]) })],
  ['점수가 배열', JSON.stringify({ ...good, scores: [1, 1] })],
  ['평가자 없음', JSON.stringify({ ...good, rater: '' })],
  ['상황이 숫자', JSON.stringify({ ...good, situation: 5 })],
  ['답변 없음', JSON.stringify({ ...good, answer: '' })],
  ['감점 이름이 기준표에 없음', JSON.stringify({ ...good, penalties: ['nope'] })],
  ['JSON이 아님', 'not json'],
];
const pj = W.parseJsonl(line(good) + bads.map((b) => b[1]).join('\n') + '\n', rubric);
bads.forEach((b, i) => ok('검증: ' + b[0] + ' → 건너뜀', pj.bad.indexOf(i + 2) >= 0, (pj.problems.find((p) => p.line === i + 2) || {}).reason));
ok('검증: 올바른 기록과 빈칸(null) 결측은 통과', W.validateRecord(rubric, good) === null && W.validateRecord(rubric, { ...good, scores: sc([null, 1, 1, 1, 1]) }) === null);
ok('parseJsonl: 올바른 1건만 남고 모든 잘못된 줄에 이유', pj.records.length === 1 && pj.bad.length === bads.length && pj.problems.every((p) => p.reason));
let threw = false, badRes = null;
try { badRes = W.computeAgreement(rubric, [{ ...good, penalties: {} }, good]); } catch (e) { threw = true; }
ok('computeAgreement: 잘못된 기록이 있어도 예외 없이 개수만 셈', !threw && badRes.skipped.invalid === 1);

// α 손계산(GPT R7): 답변별 점수 [0,0,1],[1,2],[2,결측] → α=4/9, 같은 점수 25%, 1점 이내 100%(4쌍)
ok('알파 손계산 예 4/9', Math.abs(W.krippendorffAlpha([[0, 0, 1], [1, 2], [2, null]]) - 4 / 9) < 1e-12, String(W.krippendorffAlpha([[0, 0, 1], [1, 2], [2, null]])));
const hand = W.computeAgreement(rubric, [
  rv('가', 'q1', [0, 0, 0, 0, 0]), rv('나', 'q1', [0, 0, 0, 0, 0]), rv('다', 'q1', [1, 1, 1, 1, 1]),
  rv('가', 'q2', [1, 1, 1, 1, 1]), rv('나', 'q2', [2, 2, 2, 2, 2]),
  rv('가', 'q3', [2, 2, 2, 2, 2]), { ...rv('나', 'q3', [0, 0, 0, 0, 0]), scores: sc([null, null, null, null, null]) },
]);
const h0 = hand.criteria[0];
ok('손계산 예를 computeAgreement로: α=4/9, 같은 점수 25%, 1점 이내 100%, 짝 4개',
  Math.abs(h0.alpha - 4 / 9) < 1e-12 && h0.exact === 0.25 && h0.within1 === 1 && h0.pairs === 4, JSON.stringify(h0));
ok('손계산 예: 유효 답변 2개·평가 수 5(결측 제외)', h0.answersUsed === 2 && h0.ratings === 5, h0.answersUsed + '/' + h0.ratings);

// 지적 2: 중복 해결은 읽는 순서와 무관
const d1 = rv('가', 'x', [0, 0, 0, 0, 0], { date: '2026-10-01' }), d2 = rv('가', 'x', [2, 2, 2, 2, 2], { date: '2026-10-04' }), other = rv('나', 'x', [2, 2, 2, 2, 2]);
const ra = W.computeAgreement(rubric, [d1, d2, other]), rb = W.computeAgreement(rubric, [other, d2, d1]), rc = W.computeAgreement(rubric, [d2, other, d1]);
ok('중복: 최신 날짜 기록을 쓰고 어떤 순서든 결과 같음', ra.criteria[0].exact === 1 && JSON.stringify(ra) === JSON.stringify(rb) && JSON.stringify(rb) === JSON.stringify(rc));
ok('중복: 내용이 달랐다는 안내(conflicts)', ra.skipped.conflicts.length === 1);
const nd1 = { ...d1, date: '' }, nd2 = { ...d2, date: undefined };
const na = W.computeAgreement(rubric, [nd1, nd2, other]), nb = W.computeAgreement(rubric, [other, nd2, nd1]);
ok('중복: 날짜가 없고 내용이 다르면 그 평가자 기록을 빼고 안내(순서 무관)', na.answers === 0 && na.skipped.unresolved.length === 1 && JSON.stringify(na) === JSON.stringify(nb));
const ta = W.computeAgreement(rubric, [d1, { ...d2, date: '2026-10-01' }, other]);
ok('중복: 최신 날짜 동률+내용 충돌이면 빼고 안내', ta.answers === 0 && ta.skipped.unresolved.length === 1);
const sa = W.computeAgreement(rubric, [d1, { ...d1 }, other]);
ok('중복: 내용이 같으면 하나로 합치고 개수 안내', sa.answers === 1 && sa.skipped.sameDuplicates === 1 && sa.skipped.unresolved.length === 0);
const wd = W.computeAgreement(rubric, [d1, { ...d2, date: 'abc' }, other]);
ok('중복: 날짜 형식이 잘못이면 없는 것으로 봄(유효한 날짜 쪽이 이김)', wd.criteria[0].exact === 0 && wd.skipped.conflicts.length === 1);

// 지적 3: 기준표 버전
const vm = W.computeAgreement(rubric, [rv('가', 'x', [1, 1, 1, 1, 1]), rv('나', 'x', [1, 1, 1, 1, 1], { rubric_version: 'v-옛날' })]);
ok('버전: 다른 버전 기록은 섞지 않고 개수 표시', vm.answers === 0 && vm.skipped.otherVersion === 1 && vm.skipped.otherVersions['v-옛날'] === 1);
const nv = W.computeAgreement(rubric, [rv('가', 'x', [1, 1, 1, 1, 1]), { ...rv('나', 'x', [1, 1, 1, 1, 1]), rubric_version: undefined }]);
ok('버전: 버전이 없는 기록은 개수를 따로 표시', nv.skipped.noVersion === 1);

// 지적 4: 항목별 표본
const few = W.computeAgreement(rubric, [rv('가', 'x', [1, 1, 1, 1, 1]), rv('나', 'x', [1, 1, 1, 1, 1])]);
ok('표본: 항목별 유효 답변·평가 수·짝 수와 표본 적음', few.criteria[0].answersUsed === 1 && few.criteria[0].ratings === 2 && few.criteria[0].pairs === 1 && few.criteria[0].lowSample === true);
const many = [];
for (let i = 0; i < 20; i++) many.push(rv('가', 'a' + i, [i % 3, 1, 1, 1, 1]), rv('나', 'a' + i, [(i + 1) % 3, 1, 1, 1, 1]));
ok('표본: 두 사람이 점수를 준 답변이 20개면 경고 해제, 19개면 경고', W.computeAgreement(rubric, many).criteria[0].lowSample === false && W.computeAgreement(rubric, many.slice(2)).criteria[0].lowSample === true && W.MIN_ANSWERS === 20);
const part = [];
for (let i = 0; i < 20; i++) part.push(rv('가', 'p' + i, [1, 1, 1, 1, 1]), { ...rv('나', 'p' + i, [1, 1, 1, 1, 1]), scores: sc([i < 2 ? 1 : null, 1, 1, 1, 1]) });
const pp = W.computeAgreement(rubric, part);
ok('표본: 답변 20개여도 그 항목에 짝이 있는 답변이 2개면 표본 적음(GPT 재현)', pp.answers === 20 && pp.criteria[0].answersUsed === 2 && pp.criteria[0].lowSample && !pp.criteria[1].lowSample);

// 지적 5: 공백만 다른 답변
const ws = W.computeAgreement(rubric, [rv('가', '같은  문장', [1, 1, 1, 1, 1]), rv('나', '같은 문장', [1, 1, 1, 1, 1])]);
ok('공백: 합치지 않고(비교 0개) 매칭 후보로 알림', ws.answers === 0 && ws.matchCandidates.length === 1 && ws.matchCandidates[0].raters.join() === '가,나');
ok('공백: 같은 글이면 후보 없음', few.matchCandidates.length === 0);

// 지적 8: 경계값
ok('경계: 0.8 이상 믿을 만함, 0.7999는 0.80으로 보여도 잠정', W.alphaText(0.8).endsWith('믿을 만함') && W.alphaText(0.7999) === '0.80 잠정');
ok('경계: 0.667 이상 잠정, 0.6668은 0.67로 보여도 다듬기', W.alphaText(0.667).endsWith('잠정') && W.alphaText(0.6668) === '0.67 다듬기' && W.alphaText(null) === '계산 불가');
const appSrc = require('fs').readFileSync(path.join(__dirname, '..', 'app.js'), 'utf8');
ok('안내 문구에 경계 0.667·0.800과 반올림 설명, 20개는 보장이 아니라는 말', appSrc.includes('0.667과 0.800') && appSrc.includes('반올림 전 값') && appSrc.includes('보장은 아니에요'));


// 같은 감점 신호가 기록에 두 번 들어가도 한 번만 뺀다(기준표 scoring, GPT G3-10).
const full = Object.fromEntries(rubric.criteria.map((c) => [c.id, 2]));
ok('감점 중복은 한 번만: 10 - 2 = 8', W.computeTotal(rubric, full, ['flattery', 'flattery']) === 8, String(W.computeTotal(rubric, full, ['flattery', 'flattery'])));
ok('서로 다른 감점은 각각: 10 - 2 - 2 = 6', W.computeTotal(rubric, full, ['flattery', 'lecturing']) === 6);
console.log(fail ? `\n실패 ${fail}건` : `\n전부 통과 (${n}건)`);
process.exitCode = fail ? 1 : 0;
