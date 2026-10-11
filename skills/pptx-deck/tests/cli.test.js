'use strict';
const { test, after } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { findSoffice } = require('../scripts/render');

const RUN = path.join(__dirname, '..', 'scripts', 'run.js');
const root = fs.mkdtempSync(path.join(os.tmpdir(), 'pptx-deck-cli-'));
after(() => fs.rmSync(root, { recursive: true, force: true }));
const work = path.join(root, 'deck-work', '日本語 名前'); // 日本語と空白を含む作業フォルダ

function run(args, env = {}) {
  const r = spawnSync('node', [RUN, ...args], { encoding: 'utf8', timeout: 300000, env: { ...process.env, ...env } });
  let json = null;
  try { json = JSON.parse(r.stdout); } catch { /* 標準出力が JSON でない場合は null */ }
  return { status: r.status, json, stdout: r.stdout, stderr: r.stderr };
}

test('init: 作業フォルダに見本一式をコピーする', () => {
  const r = run(['init', work]);
  assert.equal(r.status, 0, r.stderr);
  for (const f of ['base.css', 'chart-preview.js', 'catalog.html']) assert.ok(fs.existsSync(path.join(work, f)), f);
});

test('check: 見本カタログは違反 0 件で合格する', () => {
  const r = run(['check', path.join(work, 'catalog.html')]);
  assert.equal(r.status, 0, `${r.stdout}\n${r.stderr}`);
  assert.equal(r.json.ok, true);
  assert.deepEqual(r.json.violations, []);
  assert.ok(r.json.font.name);
});

test('check: 違反のある HTML は終了コード 2 と、修正の提案を返す', () => {
  const html = fs.readFileSync(path.join(work, 'catalog.html'), 'utf8')
    .replace('data-role="body" style="margin-top:12px">商談化率が既存深耕の1.8倍。人員を2名追加して、訪問件数を増やす。', 'data-role="body" style="margin-top:12px;font-size:10px">商談化率');
  const bad = path.join(work, 'bad.html');
  fs.writeFileSync(bad, html);
  const r = run(['check', bad, '--attempt', '0']);
  assert.equal(r.status, 2);
  assert.equal(r.json.ok, false);
  assert.ok(r.json.violations.some((v) => v.rule === 'minFont'));
  assert.ok(r.json.suggestion.action);
});

test('build: 合格した HTML から PPTX を作り、検証し、(LibreOffice があれば) 画像化する', { skip: !findSoffice() }, () => {
  const out = path.join(work, 'catalog.pptx');
  const r = run(['build', path.join(work, 'catalog.html'), out, '--work', work]);
  assert.equal(r.status, 0, `${r.stdout}\n${r.stderr}`);
  assert.equal(r.json.ok, true);
  assert.ok(fs.existsSync(out));
  assert.deepEqual(r.json.packageErrors, []);
  assert.equal(r.json.pngs.length, 7);
});

test('build: HTML 段階で違反があれば PPTX を作らない', () => {
  const out = path.join(work, 'never.pptx');
  const r = run(['build', path.join(work, 'bad.html'), out, '--no-render']);
  assert.equal(r.status, 2);
  assert.ok(!fs.existsSync(out));
});

test('doctor: 必須項目の結果を一覧で出す', () => {
  const r = run(['doctor']);
  assert.match(r.stdout, /\[(OK|NG)\] Node/);
  assert.match(r.stdout, /Edge/);
  assert.match(r.stdout, /フォント/);
});

test('build: 画像化に失敗しても(PyMuPDF なし)検査結果は返し、理由を renderNote に書く', { skip: !findSoffice() }, () => {
  const out = path.join(work, 'norender.pptx');
  const r = run(['build', path.join(work, 'catalog.html'), out, '--work', work], { PYTHON: 'no-such-python-for-test' });
  assert.equal(r.status, 0, `${r.stdout}
${r.stderr}`);
  assert.equal(r.json.ok, true);
  assert.ok(!r.json.pngs);
  assert.match(r.json.renderNote, /画像化に失敗/);
  assert.ok(fs.existsSync(path.join(work, 'report.json')));
});

test('check: --attempt に値がない・数値でないときは、段階がずれる前にエラーにする', () => {
  for (const args of [['check', path.join(work, 'catalog.html'), '--attempt'], ['check', path.join(work, 'catalog.html'), '--attempt', 'abc']]) {
    const r = run(args);
    assert.equal(r.status, 1, r.stdout);
    assert.match(r.stderr, /--attempt/);
  }
});
