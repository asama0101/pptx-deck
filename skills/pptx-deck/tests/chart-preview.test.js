'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { chartSvg } = require('../design/chart-preview');

const theme = { accent: '#1F4E9C', neutral: '#BFBFBF' };

test('棒グラフ: 値の数だけ rect を描き、注目データだけアクセント色にする', () => {
  const svg = chartSvg({ type: 'bar', labels: ['A', 'B', 'C'], values: [1, 2, 3], highlight: 2 }, 600, 400, theme);
  assert.match(svg, /^<svg/);
  assert.equal((svg.match(/<rect /g) || []).length, 3);
  assert.equal((svg.match(/#1F4E9C/g) || []).length, 1);
  assert.equal((svg.match(/#BFBFBF/g) || []).length, 2);
});

test('横棒・折れ線・円もそれぞれ SVG を返す', () => {
  const base = { labels: ['A', 'B'], values: [1, 3], highlight: 1 };
  assert.equal((chartSvg({ ...base, type: 'barh' }, 600, 400, theme).match(/<rect /g) || []).length, 2);
  assert.match(chartSvg({ ...base, type: 'line' }, 600, 400, theme), /<polyline/);
  assert.equal((chartSvg({ ...base, type: 'pie' }, 600, 400, theme).match(/<path /g) || []).length, 2);
});

test('未対応の型は明示エラー', () => {
  assert.throws(() => chartSvg({ type: 'stacked', labels: [], values: [] }, 100, 100, theme), /未対応/);
});
