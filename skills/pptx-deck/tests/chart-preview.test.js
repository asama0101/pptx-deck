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
  assert.throws(() => chartSvg({ type: 'radar', labels: [], values: [] }, 100, 100, theme), /未対応/);
});

test('積み上げ棒: セグメントの数だけ rect を描き、注目の系列だけアクセント色にする', () => {
  const spec = { labels: ['A', 'B'], series: [{ name: 'x', values: [1, 2] }, { name: 'y', values: [3, 1] }], highlight: 1 };
  for (const type of ['stacked', 'stackedh']) {
    const svg = chartSvg({ ...spec, type }, 600, 400, theme);
    assert.equal((svg.match(/<rect /g) || []).length, 4 + 2); // セグメント 4 + 凡例 2
    assert.equal((svg.match(/#1F4E9C/g) || []).length, 3); // セグメント 2 + 凡例 1
  }
});

test('100% 積み上げ棒・面: 各カテゴリを 100% に正規化し、面は系列ごとに polygon を描く', () => {
  const spec = { labels: ['A', 'B'], series: [{ name: 'x', values: [1, 3] }, { name: 'y', values: [1, 1] }], highlight: 1 };
  const s100 = chartSvg({ ...spec, type: 'stacked100' }, 600, 400, theme);
  assert.equal((s100.match(/<rect /g) || []).length, 4 + 2);
  const area = chartSvg({ ...spec, type: 'area' }, 600, 400, theme);
  assert.equal((area.match(/<polygon /g) || []).length, 2);
  assert.equal((area.match(/#1F4E9C/g) || []).length, 2); // 面 1 + 凡例 1
});

test('横棒: 項目名と値のラベルが、描画領域からはみ出さない(見切れない)', () => {
  const w = 548;
  const spec = { labels: ['当期予算', '初期費用（一括）', '当期支出（分割後）'], values: [2500, 3200, 2200], highlight: 2 };
  for (const svg of [chartSvg({ ...spec, type: 'barh' }, w, 190, theme), chartSvg({ type: 'stackedh', labels: spec.labels, series: [{ name: 'x', values: spec.values }] }, w, 190, theme)]) {
    const rects = [...svg.matchAll(/<rect x="([\d.]+)"[^>]*width="([\d.]+)"/g)].map((m) => Number(m[1]) + Number(m[2]));
    assert.ok(Math.max(...rects) <= w - 60, `最大の棒の右端 ${Math.max(...rects)}`);
    const labelEnd = Number(/text-anchor="end"/.test(svg) && /<text x="([\d.]+)"[^>]*text-anchor="end"/.exec(svg)[1]);
    assert.ok(labelEnd >= 14 * 9 + 16 - 1, `項目名の右端 ${labelEnd}`); // 最長 9 文字が収まる幅
  }
  assert.match(chartSvg({ ...spec, type: 'barh' }, w, 190, theme), />3,200</);
});

test('累計の棒: 各年を「前年までの累計＋その年の増加分」に分け、増加分だけアクセント色にする', () => {
  const svg = chartSvg({ type: 'cumulative', labels: ['初期', '1年目', '2年目'], values: [3200, 4280, 5360] }, 740, 480, theme);
  assert.match(svg, /＋1,080</);
  assert.equal((svg.match(/＋1,080</g) || []).length, 2);
  assert.match(svg, />5,360</);
  assert.equal((svg.match(/fill="#1F4E9C" stroke/g) || []).length, 2); // 増加分の塊は 2 つ(初期にはない)
});
