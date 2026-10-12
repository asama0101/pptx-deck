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

test('アイコン: references/icons の全 SVG を、基調色・強調色・白の 3 色で書き出す。色は base.css から読む', () => {
  const fs = require('node:fs');
  const os = require('node:os');
  const path = require('node:path');
  const { writeIcons, readAccents } = require('../scripts/lib/icons');
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'pptx-deck-icons-'));
  try {
    const names = writeIcons(dir, { accent: '#112233', accent2: '#445566' });
    assert.ok(names.length >= 20, `${names.length} 種`);
    for (const n of names) {
      const base = fs.readFileSync(path.join(dir, 'icons', `${n}.svg`), 'utf8');
      assert.match(base, /stroke="#112233"/);
      assert.match(fs.readFileSync(path.join(dir, 'icons', `${n}-o.svg`), 'utf8'), /stroke="#445566"/);
      assert.match(fs.readFileSync(path.join(dir, 'icons', `${n}-w.svg`), 'utf8'), /stroke="#FFFFFF"/);
      assert.match(base, /^<svg /);
    }
    const css = path.join(dir, 'a.css');
    fs.writeFileSync(css, ':root { --accent: #1F4E9C; --accent2: #B85A0B; }');
    assert.deepEqual(readAccents(css), { accent: '#1F4E9C', accent2: '#B85A0B' });
    assert.deepEqual(readAccents(path.join(dir, 'none.css')), { accent: undefined, accent2: undefined });
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('ウォーターフォール: 合計と増減の棒の幾何を作り、合計の不一致・0 未満の累計は拒否する', () => {
  const { waterfallParts } = require('../scripts/lib/waterfall');
  const parts = waterfallParts([100, 45, -5, -20, -10, 110]);
  assert.deepEqual(parts.map((p) => p.kind), ['total', 'up', 'down', 'down', 'down', 'total']);
  assert.deepEqual([parts[1].base, parts[1].top], [100, 145]);
  assert.deepEqual([parts[3].base, parts[3].top], [120, 140]); // 減少は、減った後の値から元の値まで
  assert.equal(parts[5].size, 110);
  assert.throws(() => waterfallParts([100, 45, 120]), /合計.*合わない/);
  assert.throws(() => waterfallParts([10, -20, -10], [0, 2]), /0 を下回る/);
  const mid = waterfallParts([100, 20, 120, -30, 90], [0, 2, 4]); // 途中の小計
  assert.deepEqual(mid.map((p) => p.kind), ['total', 'up', 'total', 'down', 'total']);
});

test('日本地図の輪郭データ: 47 都道府県、すべての輪郭が枠の内側、沖縄は挿入の枠の中にある', () => {
  const fs = require('node:fs');
  const path = require('node:path');
  const d = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'design', 'japan-map.json'), 'utf8'));
  assert.equal(d.prefs.length, 47);
  assert.equal(new Set(d.prefs.map((p) => p.name)).size, 47);
  for (const k of ['北海道', '東京', '大阪', '沖縄']) assert.ok(d.prefs.some((p) => p.name === k), k);
  const [w, h] = d.meta.size;
  for (const p of d.prefs) {
    assert.ok(p.rings.length >= 1 && p.rings.every((r) => r.length >= 3), p.name);
    for (const ring of p.rings) for (const [x, y] of ring) assert.ok(x >= -1 && y >= -1 && x <= w + 1 && y <= h + 1, `${p.name} ${x},${y}`);
  }
  assert.match(d.meta.source, /Natural Earth/);
  assert.ok(d.meta.points < 4000, `点の数 ${d.meta.points}`);
});
