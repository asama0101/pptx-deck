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

test('積み上げ棒: 系列ごとに色を分け、注目の系列だけアクセント色にする', async () => {
  const out = path.join(root, 'stacked.pptx');
  const chart = { type: 'stackedh', labels: ['直接削減'], series: [{ name: '更新費', values: [3800] }, { name: '保守・賃料', values: [2000] }], highlight: 1, labelPt: 12 };
  await buildPptx(model([slide([el({ type: 'chart', role: '', x: 1, y: 1, w: 8, h: 3, chart })])]), out);
  const zip = await JSZip.loadAsync(fs.readFileSync(out));
  const name = Object.keys(zip.files).find((n) => /^ppt\/charts\/chart\d+\.xml$/.test(n));
  const xml = await zip.file(name).async('string');
  assert.match(xml, /<c:grouping val="stacked"\/>/);
  assert.match(xml, /<c:barDir val="bar"\/>/);
  assert.equal((xml.match(/<c:ser>/g) || []).length, 2);
  assert.match(xml, /1F4E9C/);
  assert.match(xml, /767676/);
});

test('100% 積み上げ棒・面: ネイティブチャートの種別と積み方を書く', async () => {
  const mk = (type) => ({ type, labels: ['2025', '2026', '2027'], series: [{ name: '既存', values: [5, 5, 5] }, { name: '新規', values: [1, 3, 6] }], highlight: 1, labelPt: 12 });
  for (const [type, tag, grouping] of [['stacked100', 'barChart', 'percentStacked'], ['area', 'areaChart', 'stacked']]) {
    const out = path.join(root, `${type}.pptx`);
    await buildPptx(model([slide([el({ type: 'chart', role: '', x: 1, y: 1, w: 8, h: 4, chart: mk(type) })])]), out);
    const zip = await JSZip.loadAsync(fs.readFileSync(out));
    const name = Object.keys(zip.files).find((n) => /^ppt\/charts\/chart\d+\.xml$/.test(n));
    const xml = await zip.file(name).async('string');
    assert.match(xml, new RegExp(`<c:${tag}>`), type);
    assert.match(xml, new RegExp(`<c:grouping val="${grouping}"/>`), type);
    assert.equal((xml.match(/<c:ser>/g) || []).length, 2);
    assert.match(xml, /1F4E9C/);
  }
});

test('横棒: 先頭の項目を上にし、値軸は隠す', async () => {
  const out = path.join(root, 'barh.pptx');
  await buildPptx(model([slide([el({ type: 'chart', role: '', x: 1, y: 1, w: 8, h: 4, chart: { type: 'barh', labels: ['1位', '2位'], values: [3, 2], highlight: 1, labelPt: 12 } })])]), out);
  const zip = await JSZip.loadAsync(fs.readFileSync(out));
  const name = Object.keys(zip.files).find((n) => /^ppt\/charts\/chart\d+\.xml$/.test(n));
  const xml = await zip.file(name).async('string');
  assert.match(xml, /<c:orientation val="maxMin"\/>/);
  assert.match(xml, /<c:delete val="1"\/>/);
});

test('累計の棒: 前年までの累計と増加分の 2 系列を積み上げ、合計と増加分を装飾のテキストで置く', async () => {
  const out = path.join(root, 'cumulative.pptx');
  const chart = { type: 'cumulative', labels: ['初期', '1年目', '2年目'], values: [3200, 4280, 5360], labelPt: 14 };
  await buildPptx(model([slide([el({ id: 's1-e9', type: 'chart', role: '', x: 1, y: 1, w: 8, h: 4, chart })])]), out);
  const zip = await JSZip.loadAsync(fs.readFileSync(out));
  const name = Object.keys(zip.files).find((n) => /^ppt\/charts\/chart\d+\.xml$/.test(n));
  const chartXml = await zip.file(name).async('string');
  assert.match(chartXml, /<c:grouping val="stacked"\/>/);
  assert.equal((chartXml.match(/<c:ser>/g) || []).length, 2);
  assert.match(chartXml, /<c:manualLayout>/);
  assert.match(chartXml, /1F4E9C/);
  const slideXml = await zip.file('ppt/slides/slide1.xml').async('string');
  assert.equal((slideXml.match(/＋1,080/g) || []).length, 2);
  assert.match(slideXml, /5,360/);
  assert.equal((slideXml.match(/s1-e10\d\d\|p=\|d=1\|r=body\|t=text/g) || []).length, 5); // 合計 3 + 増加分 2
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
  await assert.rejects(buildPptx(model([slide([el({ type: 'chart', chart: { type: 'radar', labels: [], values: [] } })])]), path.join(root, 'x.pptx')), /未対応/);
  await assert.rejects(buildPptx(model([slide([el({ type: 'image', src: path.join(root, 'nothing.png'), alt: 'x' })])]), path.join(root, 'y.pptx')), /画像が見つからない/);
});

test('ウォーターフォール: 土台・合計・増加・減少の 4 系列を積み上げ、土台は背景色にし、増減の値を装飾のテキストで置く', async () => {
  const out = path.join(root, 'waterfall.pptx');
  const chart = { type: 'waterfall', labels: ['前期', '新規', '人件費', '当期'], values: [100, 45, -20, 125], labelPt: 14 };
  const m = model([slide([el({ id: 's1-e9', type: 'chart', role: '', x: 1, y: 1, w: 8, h: 4, chart })])]);
  m.theme = { accent: '#1F4E9C', accent2: '#B85A0B', neutral: '#BFBFBF' };
  await buildPptx(m, out);
  const zip = await JSZip.loadAsync(fs.readFileSync(out));
  const name = Object.keys(zip.files).find((n) => /^ppt\/charts\/chart\d+\.xml$/.test(n));
  const chartXml = await zip.file(name).async('string');
  assert.match(chartXml, /<c:grouping val="stacked"\/>/);
  assert.equal((chartXml.match(/<c:ser>/g) || []).length, 4);
  assert.match(chartXml, /<c:manualLayout>/);
  assert.match(chartXml, /FFFFFF/); // 土台は背景色
  assert.match(chartXml, /767676/); // 合計
  assert.match(chartXml, /1F4E9C/); // 増加
  assert.match(chartXml, /404040/); // 減少(橙は推奨専用)
  assert.doesNotMatch(chartXml, /B85A0B/);
  const slideXml = await zip.file('ppt/slides/slide1.xml').async('string');
  assert.match(slideXml, /＋45/);
  assert.match(slideXml, /▲20/);
  assert.equal((slideXml.match(/s1-e10\d\d\|p=\|d=1\|r=body\|t=text/g) || []).length, 4);
});

test('斜めの線・三角形・半透明の塗り: 向きに合わせて反転し、透過を書き、重なりの許可をオブジェクト名に残す', async () => {
  const out = path.join(root, 'diag.pptx');
  const m = model([slide([
    el({ id: 's1-e1', type: 'line', dir: 'ur', arrow: true, stroke: '#555555', strokeW: 1.5, x: 1, y: 1, w: 2, h: 1 }),
    el({ id: 's1-e2', type: 'line', dir: 'dr', arrow: false, stroke: '#555555', strokeW: 1.5, x: 4, y: 1, w: 2, h: 1 }),
    el({ id: 's1-e3', type: 'line', dir: 'ul', arrow: true, stroke: '#555555', strokeW: 1.5, x: 7, y: 1, w: 2, h: 1 }),
    el({ id: 's1-e4', type: 'shape', kind: 'triangle', fill: '#1F4E9C', fillAlpha: 0.35, overlapOk: true, x: 1, y: 3, w: 3, h: 3, stroke: null, strokeW: 0 }),
  ])]);
  await buildPptx(m, out);
  const zip = await JSZip.loadAsync(fs.readFileSync(out));
  const xml = await zip.file('ppt/slides/slide1.xml').async('string');
  assert.match(xml, /prst="triangle"/);
  assert.match(xml, /<a:alpha val="35000"\/>/);
  assert.match(xml, /name="s1-e4\|p=\|d=0\|r=body\|t=shape\|o=1"/);
  const flips = [...xml.matchAll(/<a:xfrm([^>]*)>/g)].map((x) => x[1]).filter((a) => /flip/.test(a));
  assert.equal(flips.filter((a) => /flipV="1"/.test(a) && !/flipH/.test(a)).length, 1); // ur
  assert.equal(flips.filter((a) => /flipH="1"/.test(a) && /flipV="1"/.test(a)).length, 1); // ul
});

test('輪郭の多角形: PowerPoint のフリーフォーム(custGeom)に、輪郭ごとの moveTo と close を書く', async () => {
  const out = path.join(root, 'poly.pptx');
  const m = model([slide([el({ id: 's1-e1', type: 'shape', kind: 'poly', fill: '#9DB8E3', stroke: '#FFFFFF', strokeW: 0.75, x: 1, y: 1, w: 2, h: 2,
    points: [[[0, 0], [2, 0], [2, 1], [0, 2]], [[0.2, 0.2], [0.5, 0.2], [0.5, 0.5]]] })])]);
  await buildPptx(m, out);
  const zip = await JSZip.loadAsync(fs.readFileSync(out));
  const xml = await zip.file('ppt/slides/slide1.xml').async('string');
  assert.match(xml, /<a:custGeom>/);
  assert.equal((xml.match(/<a:moveTo>/g) || []).length, 2);
  assert.equal((xml.match(/<a:close \/>/g) || []).length, 2);
  assert.equal((xml.match(/<a:lnTo>/g) || []).length, 5);
});

test('複数系列の折れ線: 系列ごとの線を引き、注目の系列だけ橙、凡例を出す', async () => {
  const out = path.join(root, 'multiline.pptx');
  const chart = { type: 'line', labels: ['1年目', '2年目', '3年目'], series: [{ name: '現状維持', values: [3, 5, 8] }, { name: 'クラウド移行', values: [2, 4, 6] }], highlight: 1, labelPt: 14 };
  const m = model([slide([el({ id: 's1-e9', type: 'chart', role: '', x: 1, y: 1, w: 8, h: 4, chart })])]);
  m.theme.accent2 = '#B85A0B';
  await buildPptx(m, out);
  const zip = await JSZip.loadAsync(fs.readFileSync(out));
  const name = Object.keys(zip.files).find((n) => /^ppt\/charts\/chart\d+\.xml$/.test(n));
  const xml = await zip.file(name).async('string');
  assert.match(xml, /<c:lineChart>/);
  assert.equal((xml.match(/<c:ser>/g) || []).length, 2);
  assert.match(xml, /B85A0B/);
  assert.match(xml, /<c:legend>/);
});
