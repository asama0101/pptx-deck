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
