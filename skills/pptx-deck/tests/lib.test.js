'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const u = require('../scripts/lib/units');
const { loadThresholds } = require('../scripts/lib/thresholds');
const { parseCssColor, contrastRatio, hueInfo } = require('../scripts/lib/color');
const { detectInstalledFonts, pickFont, FONT_CANDIDATES } = require('../scripts/lib/fonts');

test('単位: 96px = 1in、96px = 72pt、スライドは 13.333x7.5in', () => {
  assert.equal(u.pxToIn(96), 1);
  assert.equal(u.pxToPt(96), 72);
  assert.equal(u.pxToIn(1280).toFixed(3), '13.333');
  assert.equal(u.pxToIn(720), 7.5);
  assert.equal(u.emuToIn(914400), 1);
});

test('しきい値: 既定値を読み、深くマージして上書きできる', () => {
  const t = loadThresholds();
  assert.equal(t.safeMarginIn, 0.4);
  const o = loadThresholds({ minFontPt: { body: 16 }, overlapRatio: 0.1 });
  assert.equal(o.minFontPt.body, 16);
  assert.equal(o.minFontPt.caption, 10);
  assert.equal(o.overlapRatio, 0.1);
});

test('色: rgb/rgba を解析し、透明は alpha 0 で返す', () => {
  assert.deepEqual(parseCssColor('rgb(31, 78, 156)'), { hex: '#1F4E9C', alpha: 1 });
  assert.equal(parseCssColor('rgba(0, 0, 0, 0)').alpha, 0);
  assert.equal(parseCssColor('transparent'), null);
});

test('色: コントラスト比と色相', () => {
  assert.ok(Math.abs(contrastRatio('#000000', '#FFFFFF') - 21) < 0.01);
  assert.ok(contrastRatio('#CCCCCC', '#FFFFFF') < 2);
  const { h, s } = hueInfo('#1F4E9C');
  assert.ok(h > 210 && h < 225, `h=${h}`);
  assert.ok(s > 0.5);
  assert.equal(hueInfo('#808080').s, 0);
});

test('フォント: 候補の先頭から導入済みのものを選ぶ', () => {
  const c = ['BIZ UDPゴシック', 'Meiryo UI'];
  assert.deepEqual(pickFont(['Meiryo UI', 'BIZ UDPゴシック'], c), { name: 'BIZ UDPゴシック', fellBack: false });
  assert.deepEqual(pickFont(['Meiryo UI'], c), { name: 'Meiryo UI', fellBack: true });
  assert.throws(() => pickFont(['Arial'], c), /BIZ UDPゴシック/);
});

test('フォント: Windows の導入済みフォントを取得できる', () => {
  const fonts = detectInstalledFonts();
  assert.ok(fonts.length > 10);
  assert.ok(FONT_CANDIDATES.some((c) => fonts.includes(c)), '候補のどれも導入されていない');
});

test('フォント: システムの表示言語により英語名で列挙されても、日本語名の候補として選べる', () => {
  assert.deepEqual(pickFont(['BIZ UDPGothic', 'Meiryo']), { name: 'BIZ UDPゴシック', fellBack: false });
  assert.deepEqual(pickFont(['Meiryo'], ['BIZ UDPゴシック', 'メイリオ']), { name: 'メイリオ', fellBack: true });
});
