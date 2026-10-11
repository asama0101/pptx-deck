'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { loadThresholds } = require('../scripts/lib/thresholds');
const g = require('../scripts/rules/geometry');
const { el, slide, model } = require('./helpers/model');

const t = loadThresholds();
const ids = (v) => v.map((x) => x.id);

test('bounds: スライド外・安全マージン外・親の枠外を検出する', () => {
  const m = model([slide([
    el({ id: 'out', x: 12.5, w: 1.5 }),
    el({ id: 'edge', x: 0.1 }),
    el({ id: 'card', type: 'shape', x: 1, y: 1, w: 4, h: 2 }),
    el({ id: 'child', parent: 'card', x: 1.2, y: 1.2, w: 5, h: 0.5 }),
    el({ id: 'ok', x: 1, y: 4 }),
  ])]);
  const v = g.checkBounds(m, t);
  assert.deepEqual(ids(v).sort(), ['child', 'edge', 'out']);
});

test('bounds: 全面背景(decor かフルブリード図形)は対象外', () => {
  const m = model([slide([
    el({ id: 'bg', type: 'shape', x: 0, y: 0, w: 13.333, h: 7.5 }),
    el({ id: 'd', type: 'shape', decor: true, x: -1, y: 0, w: 1, h: 1 }),
  ])]);
  assert.equal(g.checkBounds(m, t).length, 0);
});

test('overlap: 兄弟の 5% 超の重なりを検出し、decor・線・親子は除外する', () => {
  const m = model([slide([
    el({ id: 'a', x: 1, y: 1, w: 3, h: 1 }),
    el({ id: 'b', x: 2, y: 1.2, w: 3, h: 1 }),
    el({ id: 'c', x: 1, y: 4, w: 3, h: 1 }),
    el({ id: 'dec', type: 'shape', decor: true, x: 1, y: 4, w: 3, h: 1 }),
    el({ id: 'ln', type: 'line', x: 1, y: 4.5, w: 3, h: 0 }),
    el({ id: 'card', type: 'shape', x: 6, y: 1, w: 4, h: 2 }),
    el({ id: 'inner', parent: 'card', x: 6.2, y: 1.2, w: 3, h: 1 }),
  ])]);
  assert.deepEqual(ids(g.checkOverlap(m, t)), ['b']);
});

test('minFont: 本文14pt未満・注記10pt未満・チャート軸ラベル10pt未満を検出する', () => {
  const m = model([slide([
    el({ id: 'body13', fontPt: 13 }),
    el({ id: 'body14', fontPt: 14, y: 2 }),
    el({ id: 'cap9', role: 'caption', fontPt: 9, y: 3 }),
    el({ id: 'cap10', role: 'caption', fontPt: 10, y: 4 }),
    el({ id: 'chart9', type: 'chart', chart: { labelPt: 9 }, y: 5 }),
  ])]);
  assert.deepEqual(ids(g.checkMinFont(m, t)).sort(), ['body13', 'cap9', 'chart9']);
});

test('hierarchy: タイトルと本文の差が4pt未満なら違反', () => {
  const bad = model([slide([el({ id: 't', role: 'title', fontPt: 20 }), el({ id: 'b', y: 3, fontPt: 18 })])]);
  const ok = model([slide([el({ id: 't', role: 'title', fontPt: 28 }), el({ id: 'b', y: 3, fontPt: 16 })])]);
  assert.deepEqual(ids(g.checkHierarchy(bad, t)), ['t']);
  assert.equal(g.checkHierarchy(ok, t).length, 0);
});

test('contrast: 薄い文字は違反、暗い背景の白文字は合格(親の塗りを背景とする)', () => {
  const m = model([slide([
    el({ id: 'pale', color: '#CCCCCC' }),
    el({ id: 'card', type: 'shape', fill: '#1F4E9C', x: 1, y: 4, w: 4, h: 2 }),
    el({ id: 'white', parent: 'card', color: '#FFFFFF', x: 1.2, y: 4.2, w: 3, h: 1 }),
  ])]);
  assert.deepEqual(ids(g.checkContrast(m, t)), ['pale']);
});

test('images: 代替テキストなしと、画像だけのスライドを検出する', () => {
  const m = model([
    slide([el({ id: 'img', type: 'image', role: 'icon', alt: '', x: 1, y: 1, w: 1, h: 1 })]),
    slide([el({ id: 'full', type: 'image', role: 'photo', alt: '全面画像', x: 0.5, y: 0.5, w: 12, h: 6.5 })], { index: 2 }),
  ]);
  const v = g.checkImages(m, t);
  assert.ok(v.some((x) => x.id === 'img' && x.rule === 'images'));
  assert.ok(v.some((x) => x.id === 'full' && /画像だけ/.test(x.message)));
});

test('htmlOnly: overflow と wrapStable=false を検出する', () => {
  const m = model([slide([
    el({ id: 'o', overflow: true }),
    el({ id: 'w', wrapStable: false, y: 2 }),
    el({ id: 'fixedOk', fixed: true, wrapStable: false, y: 3 }),
  ])]);
  assert.deepEqual(ids(g.htmlOnly(m, t)).sort(), ['o', 'w']);
});

test('all: 空のスライドでもクラッシュしない', () => {
  assert.deepEqual(g.all(model([slide([])]), t), []);
});

test('htmlOnly: 計測されなかった文字(unmeasured)を違反にする', () => {
  const m = model([slide([el({ id: 'a' })], { unmeasured: ['クラスなしの段落'] })]);
  const v = g.htmlOnly(m, t);
  assert.ok(v.some((x) => x.rule === 'unmeasured' && /クラスなしの段落/.test(x.message)));
});

test('htmlOnly: pp-text の枠線(PPTX に写らない装飾)を違反にする', () => {
  const m = model([slide([el({ id: 'b', border: true }), el({ id: 'ok', border: false, y: 3 })])]);
  const v = g.htmlOnly(m, t);
  assert.deepEqual(v.filter((x) => x.rule === 'textBorder').map((x) => x.id), ['b']);
});
