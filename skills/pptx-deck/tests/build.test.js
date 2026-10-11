'use strict';
const { test, after } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const JSZip = require('jszip');
const { buildPptx } = require('../scripts/build');
const { el, slide, model } = require('./helpers/model');

const root = fs.mkdtempSync(path.join(os.tmpdir(), 'pptx-deck-build-'));
after(() => fs.rmSync(root, { recursive: true, force: true }));

const PNG = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==', 'base64');

function sample() {
  const png = path.join(root, 'icon.png');
  fs.writeFileSync(png, PNG);
  const para = (text, extra = {}) => ({ runs: [{ text, color: '#1A1A1A', bold: false, pt: 16, ...extra }], bullet: false });
  return model([
    slide([
      el({ id: 's1-e1', role: 'title', fontPt: 28, bold: true, x: 0.58, y: 0.42, w: 12.17, h: 0.6, text: '結論です', paras: [para('結論です', { pt: 28, bold: true })], lineSpacingPt: 36, paraSpaceAfter: 0 }),
      el({ id: 's1-e2', type: 'shape', kind: 'roundRect', fill: '#F3F3F3', radius: 0.04, x: 0.58, y: 1.6, w: 4, h: 2, stroke: null, strokeW: 0 }),
      el({ id: 's1-e3', parent: 's1-e2', x: 0.9, y: 1.9, w: 3.3, h: 1, text: '本文', paras: [{ runs: [{ text: '項目', color: '#1A1A1A', bold: false, pt: 16 }, { text: '', br: true }, { text: '次の行', color: '#1A1A1A', bold: false, pt: 16 }], bullet: true }], lineSpacingPt: 24, paraSpaceAfter: 6 }),
      el({ id: 's1-e4', type: 'line', dir: 'right', arrow: true, stroke: '#555555', strokeW: 1.5, x: 5, y: 2.5, w: 1, h: 0 }),
      el({ id: 's1-e5', type: 'image', role: 'icon', src: png, alt: 'アイコン', x: 6.5, y: 1.6, w: 0.5, h: 0.5 }),
      el({ id: 's1-e6', type: 'chart', role: '', x: 7.5, y: 1.6, w: 4.5, h: 3, chart: { type: 'bar', labels: ['A', 'B', 'C'], values: [1, 2, 3], highlight: 2, labelPt: 12 } }),
      el({ id: 's1-e7', role: 'title', fixed: true, decor: true, x: 0.58, y: 5, w: 6, h: 1, text: '固定\n行', paras: [para('固定', { pt: 40 })], lineSpacingPt: 52, fontPt: 40 }),
    ], { notes: '話す内容のメモ' }),
  ]);
}

async function build() {
  const out = path.join(root, 'deck.pptx');
  await buildPptx(sample(), out);
  return JSZip.loadAsync(fs.readFileSync(out));
}

test('テキスト: フォント・サイズ・pt固定の行間・オブジェクト名を書く', async () => {
  const zip = await build();
  const xml = await zip.file('ppt/slides/slide1.xml').async('string');
  assert.match(xml, /typeface="BIZ UDPゴシック"/);
  assert.match(xml, /sz="2800"/);
  assert.match(xml, /<a:spcPts val="3600"\/>/);
  assert.match(xml, /name="s1-e1\|p=\|d=0\|r=title\|t=text"/);
  assert.match(xml, /name="s1-e3\|p=s1-e2\|d=0\|r=body\|t=text"/);
  assert.match(xml, /name="s1-e7\|p=\|d=1\|r=title\|t=text"/);
});

test('固定行の見出しは折り返さず、箇条書きと改行を持つ', async () => {
  const xml = await (await build()).file('ppt/slides/slide1.xml').async('string');
  assert.match(xml, /wrap="none"/);
  assert.match(xml, /<a:buChar/);
  assert.match(xml, /次の行/);
});

test('図形・線・画像: 角丸・矢印・代替テキストを書く', async () => {
  const xml = await (await build()).file('ppt/slides/slide1.xml').async('string');
  assert.match(xml, /prst="roundRect"/);
  assert.match(xml, /<a:tailEnd type="triangle"/);
  assert.match(xml, /descr="アイコン"/);
  assert.match(xml, /<p:pic>/);
});

test('チャート: ネイティブチャートで、注目データだけ別色にする', async () => {
  const zip = await build();
  // pptxgenjs はチャートの連番をプロセス内で引き継ぐため、番号は固定しない
  const chartName = Object.keys(zip.files).find((n) => /^ppt\/charts\/chart\d+\.xml$/.test(n));
  const chart = await zip.file(chartName).async('string');
  assert.match(chart, /<c:barChart>/);
  assert.equal((chart.match(/<c:dPt>/g) || []).length >= 1, true);
  assert.match(chart, /1F4E9C/);
  assert.match(chart, /BFBFBF/);
});

test('ノート: スピーカーノートを書く', async () => {
  const zip = await build();
  const names = Object.keys(zip.files).filter((n) => /notesSlide\d+\.xml$/.test(n));
  assert.equal(names.length, 1);
  assert.match(await zip.file(names[0]).async('string'), /話す内容のメモ/);
});

test('空のスライド・未対応のチャート型・存在しない画像は明示エラー', async () => {
  const out = path.join(root, 'empty.pptx');
  await buildPptx(model([slide([])]), out);
  assert.ok(fs.existsSync(out));
  await assert.rejects(buildPptx(model([slide([el({ type: 'chart', chart: { type: 'stacked', labels: [], values: [] } })])]), path.join(root, 'x.pptx')), /未対応/);
  await assert.rejects(buildPptx(model([slide([el({ type: 'image', src: path.join(root, 'nothing.png'), alt: 'x' })])]), path.join(root, 'y.pptx')), /画像が見つからない/);
});
