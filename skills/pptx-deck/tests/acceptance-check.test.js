'use strict';
const { test, after } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { buildPptx } = require('../scripts/build');
const { acceptanceCheck } = require('../scripts/acceptance-check');
const { loadThresholds } = require('../scripts/lib/thresholds');
const { el, slide, model } = require('./helpers/model');

const t = loadThresholds();
const root = fs.mkdtempSync(path.join(os.tmpdir(), 'pptx-deck-accept-'));
after(() => fs.rmSync(root, { recursive: true, force: true }));

const text = (o) => el({ lineSpacingPt: 24, paraSpaceAfter: 0, paras: [{ runs: [{ text: 'あ', color: '#1A1A1A', bold: false, pt: 16 }], bullet: false }], ...o });

test('枚数が範囲内で違反がなければ合格、範囲外・違反ありなら不合格の理由を返す', async () => {
  const file = path.join(root, 'a.pptx');
  await buildPptx(model([slide([text({ id: 's1-e1', x: 1, y: 2 })]), slide([text({ id: 's2-e1', x: 1, y: 2 })], { index: 2 })]), file);
  assert.equal((await acceptanceCheck(file, 1, 3, t)).ok, true);
  const out = await acceptanceCheck(file, 5, 8, t);
  assert.equal(out.ok, false);
  assert.match(out.failures.join('\n'), /枚数/);

  const bad = path.join(root, 'b.pptx');
  await buildPptx(model([slide([text({ id: 's1-e1', fontPt: 11, paras: [{ runs: [{ text: 'あ', color: '#1A1A1A', bold: false, pt: 11 }], bullet: false }], x: 1, y: 2 })])]), bad);
  const r = await acceptanceCheck(bad, 1, 1, t);
  assert.equal(r.ok, false);
  assert.match(r.failures.join('\n'), /minFont/);
});

test('HTML を渡すと、AIっぽさの客観チェック(HTML 段階のルール)も判定に含める', async () => {
  const file = path.join(root, 'c.pptx');
  await buildPptx(model([slide([text({ id: 's1-e1', x: 1, y: 2 })])]), file);
  const css = require('node:url').pathToFileURL(path.join(__dirname, '..', 'design', 'base.css')).href;
  const html = path.join(root, 'tiny.html');
  fs.writeFileSync(html, `<!doctype html><html lang="ja"><head><meta charset="utf-8"><link rel="stylesheet" href="${css}"></head><body><section class="slide" data-layout="content"><p class="pp-text" data-role="body" style="position:absolute;left:56px;top:300px;width:600px;font-size:10px">小さい文字</p></section></body></html>`);
  assert.equal((await acceptanceCheck(file, 1, 1, t)).ok, true);
  const r = await acceptanceCheck(file, 1, 1, t, { html });
  assert.equal(r.ok, false);
  assert.match(r.failures.join('\n'), /HTML.*minFont/);
});
