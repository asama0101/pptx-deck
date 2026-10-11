'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { loadThresholds } = require('../scripts/lib/thresholds');
const { suggestFix } = require('../scripts/suggest');

const t = loadThresholds();
const over = [{ rule: 'overflow', severity: 'error', id: 'a', slide: 1, message: '' }];

test('suggestFix: 違反がなければ none', () => {
  assert.equal(suggestFix([], 0, t).action, 'none');
});

test('suggestFix: 余白 → 行間 → フォント縮小 → 分割・削減の提案の順に進む', () => {
  assert.equal(suggestFix(over, 0, t).action, 'reduceSpacing');
  assert.equal(suggestFix(over, 1, t).action, 'tightenLineHeight');
  assert.equal(suggestFix(over, 2, t).action, 'shrinkFont');
  const stop = suggestFix(over, 3, t);
  assert.equal(stop.action, 'proposeSplitOrTrim');
  assert.match(stop.detail, /承認/);
});

test('suggestFix: 本文量が原因でない違反は manual', () => {
  const v = [{ rule: 'overlap', severity: 'error', id: 'a', slide: 1, message: '' }];
  assert.equal(suggestFix(v, 0, t).action, 'manual');
});

test('suggestFix: wrapStable だけの違反には、行間でなく幅を広げる→フォント縮小を提案する', () => {
  const wrap = [{ rule: 'wrapStable', severity: 'error', id: 'a', slide: 1, message: '' }];
  assert.equal(suggestFix(wrap, 0, t).action, 'widenText');
  assert.equal(suggestFix(wrap, 1, t).action, 'shrinkFont');
  const stop = suggestFix(wrap, 2, t);
  assert.equal(stop.action, 'proposeSplitOrTrim');
  assert.match(stop.detail, /承認/);
  const mixed = [...wrap, { rule: 'overflow', severity: 'error', id: 'b', slide: 1, message: '' }];
  assert.equal(suggestFix(mixed, 1, t).action, 'tightenLineHeight');
});
