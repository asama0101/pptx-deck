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

const tmp = path.join(root, 'tmp'); // 一時フォルダを隔離して、build が出す pptx-deck/<作業名> を確認する
fs.mkdirSync(tmp, { recursive: true });

function run(args, env = {}) {
  const r = spawnSync('node', [RUN, ...args], { encoding: 'utf8', timeout: 300000, env: { ...process.env, TEMP: tmp, TMP: tmp, TMPDIR: tmp, ...env } });
  let json = null;
  try { json = JSON.parse(r.stdout); } catch { /* 標準出力が JSON でない場合は null */ }
  return { status: r.status, json, stdout: r.stdout, stderr: r.stderr };
}

test('init: 作業フォルダに base.css・chart-preview.js・icons/ だけを置く(見本は design/ を参照)', () => {
  const r = run(['init', work]);
  assert.equal(r.status, 0, r.stderr);
  for (const f of ['base.css', 'chart-preview.js']) assert.ok(fs.existsSync(path.join(work, f)), f);
  assert.ok(!fs.existsSync(path.join(work, 'catalog.html')));
  assert.equal(r.json.samples, path.join(__dirname, '..', 'design'));
  // 以降のテストの入力として、見本を作業フォルダに置く
  for (const f of ['catalog.html', 'diagrams.html', 'charts.html', 'consulting.html', 'planning.html']) fs.copyFileSync(path.join(r.json.samples, f), path.join(work, f));
  assert.equal(r.json.icons, 22);
  for (const f of ['cloud.svg', 'cloud-o.svg', 'cloud-w.svg']) assert.ok(fs.existsSync(path.join(work, 'icons', f)), f);
});

test('icons: base.css の --accent・--accent2 の色でアイコンを作り直す', () => {
  const css = path.join(work, 'base.css');
  fs.writeFileSync(css, fs.readFileSync(css, 'utf8').replace('--accent: #1F4E9C', '--accent: #2E7D4F').replace('--accent2: #B85A0B', '--accent2: #C0392B'));
  const r = run(['icons', work]);
  assert.equal(r.status, 0, r.stderr);
  assert.match(fs.readFileSync(path.join(work, 'icons', 'cloud.svg'), 'utf8'), /stroke="#2E7D4F"/);
  assert.match(fs.readFileSync(path.join(work, 'icons', 'cloud-o.svg'), 'utf8'), /stroke="#C0392B"/);
  assert.match(fs.readFileSync(path.join(work, 'icons', 'cloud-w.svg'), 'utf8'), /stroke="#FFFFFF"/);
  run(['init', work]); // 既定の色に戻す
});

test('check: 見本カタログは違反 0 件で合格する', () => {
  const r = run(['check', path.join(work, 'catalog.html')]);
  assert.equal(r.status, 0, `${r.stdout}\n${r.stderr}`);
  assert.equal(r.json.ok, true);
  assert.deepEqual(r.json.violations, []);
  assert.ok(r.json.font.name);
});

test('check: 図解・チャート・コンサル資料風・検証計画の見本集は、警告を含めて違反 0 件で合格する', () => {
  for (const f of ['diagrams.html', 'charts.html', 'consulting.html', 'planning.html']) {
    const r = run(['check', path.join(work, f)]);
    assert.equal(r.status, 0, `${f}
${r.stdout}
${r.stderr}`);
    assert.deepEqual(r.json.violations, [], f);
  }
});

test('build: ベン図・三角形・斜めの線を含む図解の見本も、PPTX 出力後の検査に通る', () => {
  const out = path.join(work, 'diagrams.pptx');
  const r = run(['build', path.join(work, 'diagrams.html'), out, '--no-render']);
  assert.equal(r.status, 0, `${r.stdout}
${r.stderr}`);
  assert.equal(r.json.ok, true);
  assert.deepEqual(r.json.violations, []);
  assert.deepEqual(r.json.packageErrors, []);
});

test('check: 違反のある HTML は終了コード 2 と、修正の提案を返す', () => {
  const html = fs.readFileSync(path.join(work, 'catalog.html'), 'utf8')
    .replace('</body>', '<section class="slide" data-layout="content" data-source="none"><p class="pp-text" data-role="title">小さい文字の確認</p><p class="pp-text" data-role="body" style="position:absolute;left:76px;top:200px;width:384px;font-size:10px">訪問件数</p></section></body>');
  const bad = path.join(work, 'bad.html');
  fs.writeFileSync(bad, html);
  const r = run(['check', bad, '--attempt', '0']);
  assert.equal(r.status, 2);
  assert.equal(r.json.ok, false);
  assert.ok(r.json.violations.some((v) => v.rule === 'minFont'));
  assert.ok(r.json.suggestion.action);
});

test('check: 何も指さない矢印・アクセント色だらけの HTML は、実際の DOM 計測でも検出する', () => {
  const html = fs.readFileSync(path.join(work, 'catalog.html'), 'utf8')
    .replace('</body>', '<section class="slide" data-layout="content"><p class="pp-text" data-role="title">矢印の確認</p>'
      + '<div class="pp-line" data-dir="right" data-arrow="end" style="position:absolute;left:100px;top:400px;width:60px"></div>'
      + ['a', 'b', 'c'].map((k, i) => `<p class="pp-text acc" data-role="body" style="position:absolute;left:${300 + i * 200}px;top:300px;width:180px;color:var(--accent)">${k}</p>`).join('')
      + '</section></body>');
  const f = path.join(work, 'arrow.html');
  fs.writeFileSync(f, html);
  const r = run(['check', f]);
  assert.equal(r.status, 2);
  const rules = r.json.violations.map((v) => v.rule);
  assert.ok(rules.includes('arrowTarget'), rules.join());
  assert.ok(rules.includes('isolation'), rules.join());
});

test('build: 合格した HTML から PPTX を作り、検証し、(LibreOffice があれば) 画像化する', { skip: !findSoffice() }, () => {
  const out = path.join(work, 'catalog.pptx');
  const r = run(['build', path.join(work, 'catalog.html'), out, '--work', work]);
  assert.equal(r.status, 0, `${r.stdout}\n${r.stderr}`);
  assert.equal(r.json.ok, true);
  assert.ok(fs.existsSync(out));
  assert.deepEqual(r.json.packageErrors, []);
  assert.equal(r.json.pngs.length, 10);
  assert.ok(r.json.pngs.every((p) => p.startsWith(tmp)), r.json.pngs[0]); // 画像は作業フォルダでなく一時フォルダ
  assert.ok(!fs.existsSync(path.join(work, 'render')));
  assert.ok(!fs.existsSync(path.join(work, 'report.json')));
  assert.equal(r.json.reportPath, path.join(tmp, 'pptx-deck', path.basename(work), 'report.json'));
  assert.ok(fs.existsSync(r.json.reportPath));
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
  assert.ok(fs.existsSync(r.json.reportPath));
});

test('check: --attempt に値がない・数値でないときは、段階がずれる前にエラーにする', () => {
  for (const args of [['check', path.join(work, 'catalog.html'), '--attempt'], ['check', path.join(work, 'catalog.html'), '--attempt', 'abc']]) {
    const r = run(args);
    assert.equal(r.status, 1, r.stdout);
    assert.match(r.stderr, /--attempt/);
  }
});
