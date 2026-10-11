'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { loadThresholds } = require('../scripts/lib/thresholds');
const q = require('../scripts/rules/quality');
const { runRules, summarize } = require('../scripts/rules');
const { el, slide, model } = require('./helpers/model');

const t = loadThresholds();
const title = (o = {}) => el({ id: 'title', role: 'title', fontPt: 28, x: 0.58, y: 0.42, w: 12.17, h: 0.6, ...o });

test('titleAlign: 表紙・章扉を除き、タイトル位置が揃わなければ違反', () => {
  const m = model([
    slide([title()], { index: 1, layout: 'cover' }),
    slide([title({ id: 't2' })], { index: 2 }),
    slide([title({ id: 't3', y: 0.9 })], { index: 3 }),
  ]);
  assert.deepEqual(q.checkTitleAlign(m, t).map((v) => v.id), ['t3']);
});

test('monotony: 同じレイアウトの3連続と、10枚以上で図解・グラフ不足を検出する', () => {
  const same = model([1, 2, 3].map((i) => slide([], { index: i, layout: 'content' })));
  assert.equal(q.checkMonotony(same, t).length, 1);
  const layouts = ['cover', 'content', 'diagram', 'content', 'chart', 'content', 'diagram', 'content', 'chart', 'closing'];
  assert.equal(q.checkMonotony(model(layouts.map((l, i) => slide([], { index: i + 1, layout: l }))), t).length, 0);
  const few = ['cover', 'content', 'section', 'content', 'diagram', 'content', 'section', 'content', 'content', 'closing'];
  const v = q.checkMonotony(model(few.map((l, i) => slide([], { index: i + 1, layout: l }))), t);
  assert.ok(v.some((x) => /図解かグラフ/.test(x.message)));
});

test('usage: 内容領域の使用率が 40〜85% の範囲外なら違反(表紙は除外)', () => {
  const empty = model([slide([el({ id: 'a', w: 2, h: 0.5 })])]);
  const good = model([slide([el({ id: 'a', type: 'shape', x: 0.5, y: 0.5, w: 10, h: 5 })])]);
  const full = model([slide([el({ id: 'a', type: 'shape', x: 0.4, y: 0.4, w: 12.5, h: 6.7 })])]);
  const cover = model([slide([el({ id: 'a', w: 2, h: 0.5 })], { layout: 'cover' })]);
  assert.equal(q.checkUsage(empty, t).length, 1);
  assert.equal(q.checkUsage(good, t).length, 0);
  assert.equal(q.checkUsage(full, t).length, 1);
  assert.equal(q.checkUsage(cover, t).length, 0);
});

test('colorCount: 有彩色の色相グループが2つ以上なら違反。同系色の濃淡は1つと数える', () => {
  const ok = model([slide([
    el({ id: 'a', color: '#1F4E9C' }), el({ id: 'b', type: 'shape', fill: '#E6EDF8' }), el({ id: 'c', type: 'shape', fill: '#F3F3F3' }),
  ])]);
  const ng = model([slide([el({ id: 'a', color: '#1F4E9C' }), el({ id: 'b', color: '#D9480F' })])]);
  assert.equal(q.checkColorCount(ok, t).length, 0);
  assert.equal(q.checkColorCount(ng, t).length, 1);
});

test('avoid: タイトル下の線・縦の装飾バー・センタリングした長い本文・末尾のピリオドを検出する', () => {
  const m = model([slide([
    title({ text: '結論です。' }),
    el({ id: 'underline', type: 'line', x: 0.58, y: 1.1, w: 5, h: 0, strokeW: 2 }),
    el({ id: 'bar', type: 'shape', fill: '#1F4E9C', x: 0.58, y: 2, w: 0.08, h: 2 }),
    el({ id: 'center', y: 4, align: 'center', lineCount: 3 }),
    el({ id: 'centerShort', y: 5.5, align: 'center', lineCount: 1 }),
  ])]);
  const rules = q.checkAvoid(m, t).map((v) => `${v.id}:${v.message.split(':')[0]}`).sort();
  assert.deepEqual(rules, ['bar:装飾バー', 'center:本文のセンタリング', 'title:タイトル末尾の句点', 'underline:タイトル下のアクセント線']);
});

test('runRules: stage により検査の範囲が変わる。空のモデルでも落ちない', () => {
  const m = model([slide([el({ id: 'x', overflow: true, w: 2, h: 0.5 })])]);
  assert.ok(runRules(m, t, { stage: 'html' }).some((v) => v.rule === 'overflow'));
  assert.ok(!runRules(m, t, { stage: 'pptx' }).some((v) => v.rule === 'overflow'));
  assert.deepEqual(runRules(model([]), t), []);
  assert.deepEqual(summarize([{ rule: 'a', severity: 'error' }, { rule: 'a', severity: 'error' }, { rule: 'b', severity: 'warn' }]), { errors: 2, byRule: { a: 2, b: 1 } });
});
