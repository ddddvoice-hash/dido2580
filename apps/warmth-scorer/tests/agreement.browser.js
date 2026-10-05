// 평가자 일치도 화면 검사: 예시 채점(평가자 '예시')에 다른 평가자 JSONL을 더해 표와 갈린 곳이 나오는지 본다.
// 실행: apps/warmth-scorer 에서 python -m http.server 8765 를 켠 뒤 node apps/warmth-scorer/tests/agreement.browser.js
// Playwright 필요. Chromium 위치는 CHROMIUM 환경변수.
'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');
const { chromium } = require('playwright');
const rubric = require('../rubric.json');

(async () => {
  const ex = rubric.examples ? rubric.examples[0] : rubric.example;
  const other = ex.answers.map((a, i) => JSON.stringify({
    situation: ex.situation, answer_id: a.id, answer: a.text,
    scores: Object.fromEntries(rubric.criteria.map((c, k) => [c.id, i === 1 && k === 0 ? (a.scores[c.id] === 2 ? 0 : 2) : a.scores[c.id]])),
    evidence: {}, penalties: a.penalties || [], total: null, rater: '다른평가자', date: '2026-10-03', rubric_version: rubric.version,
  })).join('\n') + '\nnot json\n';
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'agree-'));
  const file = path.join(dir, 'other.jsonl');
  fs.writeFileSync(file, other);
  const results = [];
  const ok = (name, cond, d = '') => { results.push(!!cond); console.log(`${cond ? 'PASS' : 'FAIL'} ${name}${d ? ' — ' + d : ''}`); };
  const browser = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto(process.env.APP_URL || 'http://127.0.0.1:8765/index.html');
  await page.waitForFunction(() => /불러왔습니다/.test(document.getElementById('rubric-status').textContent));
  await page.click('#agree-mine');
  ok('혼자 채점했을 때는 비교할 답변 없음 안내', (await page.textContent('#agree-status')).includes('두 사람 이상'));
  await page.click('#load-example');
  await page.setInputFiles('#agree-files', file);
  await page.waitForFunction(() => document.querySelectorAll('#agree-result tbody tr').length > 0);
  const status = await page.textContent('#agree-status');
  ok('다른 평가자 기록을 더하고 깨진 줄은 뺌', status.includes(`채점 ${ex.answers.length}건`) && status.includes('읽지 못한 줄 1개'), status);
  ok(`비교한 답변 ${ex.answers.length}개, 평가자 둘`, status.includes(`비교한 답변 ${ex.answers.length}개`) && status.includes('다른평가자') && status.includes('예시'));
  ok('항목 5줄 표', (await page.$$eval('#agree-result tbody tr', (r) => r.length)) === rubric.criteria.length);
  const firstRow = await page.$eval('#agree-result tbody tr', (r) => r.textContent);
  const expect = Math.round((ex.answers.length - 1) / ex.answers.length * 100) + '%';
  ok(`첫 항목 같은 점수 ${expect}`, firstRow.includes(expect), firstRow);
  ok('갈린 곳 목록에 2점 차 한 줄', (await page.textContent('#agree-result ul')).includes(rubric.criteria[0].name));
  ok('표에 신뢰도 α 칸', (await page.textContent('#agree-result thead')).includes('신뢰도 α'));
  ok('답변이 적으면 숫자가 흔들린다는 안내', (await page.textContent('#agree-result .hint')).includes('흔들립니다'));
  ok('버튼 높이 48px 이상', (await page.$$eval('#agree-section button', (b) => b.every((x) => x.getBoundingClientRect().height >= 47.5))));
  ok('페이지 오류 없음', errors.length === 0, errors.join('; '));
  await browser.close();
  fs.rmSync(dir, { recursive: true, force: true });
  const fail = results.filter((x) => !x).length;
  console.log(fail ? `\n실패 ${fail}건` : `\n전부 통과 (${results.length}건)`);
  process.exitCode = fail ? 1 : 0;
})().catch((e) => { console.error(e); process.exitCode = 1; });
