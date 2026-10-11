'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

test('固定した依存が読み込める', () => {
  for (const m of ['pptxgenjs', 'playwright', 'jszip', 'fast-xml-parser']) {
    assert.doesNotThrow(() => require(m), `${m} を読み込めない`);
  }
});

test('thresholds.json が妥当な JSON で、必須キーを持つ', () => {
  const t = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'config', 'thresholds.json'), 'utf8'));
  for (const k of ['safeMarginIn', 'overlapRatio', 'minFontPt', 'hierarchyGapPt', 'contrastMin', 'wrapSafety', 'usage', 'maxFixAttempts']) {
    assert.ok(k in t, `${k} がない`);
  }
  assert.equal(t.minFontPt.body, 14);
  assert.equal(t.minFontPt.caption, 10);
});
