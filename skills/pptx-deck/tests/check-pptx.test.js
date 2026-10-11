'use strict';
const { test, after } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const JSZip = require('jszip');
const { buildPptx } = require('../scripts/build');
const { readPptxModel, verifyPptx } = require('../scripts/check-pptx');
const { loadThresholds } = require('../scripts/lib/thresholds');
const { el, slide, model } = require('./helpers/model');

const t = loadThresholds();
const root = fs.mkdtempSync(path.join(os.tmpdir(), 'pptx-deck-check-'));
after(() => fs.rmSync(root, { recursive: true, force: true }));

const para = (text, pt = 16, color = '#1A1A1A') => ({ runs: [{ text, color, bold: false, pt }], bullet: false });
const text = (o) => el({ lineSpacingPt: 24, paraSpaceAfter: 0, paras: [para(o.text || 'あ', o.fontPt || 16, o.color || '#1A1A1A')], ...o });

async function make(name, elements) {
  const file = path.join(root, name);
  await buildPptx(model([slide(elements)]), file);
  return file;
}

test('読み戻し: 位置・サイズ・フォント・色・親子・decor・役割を復元する', async () => {
  const file = await make('ok.pptx', [
    text({ id: 's1-e1', role: 'title', fontPt: 28, text: 'タイトル', x: 0.58, y: 0.42, w: 12.17, h: 0.6 }),
    el({ id: 's1-e2', type: 'shape', kind: 'rect', fill: '#1F4E9C', x: 1, y: 2, w: 4, h: 2 }),
    text({ id: 's1-e3', parent: 's1-e2', text: '白文字', color: '#FFFFFF', x: 1.2, y: 2.2, w: 3, h: 1 }),
    el({ id: 's1-e4', type: 'chart', role: '', x: 6, y: 2, w: 5, h: 3, chart: { type: 'bar', labels: ['A', 'B'], values: [1, 2], highlight: 1, labelPt: 12 } }),
  ]);
  const { model: m, packageErrors } = await readPptxModel(file);
  assert.deepEqual(packageErrors, []);
  assert.ok(Math.abs(m.slideW - 13.333) < 0.01);
  const [title, card, inner, chart] = m.slides[0].elements;
  assert.equal(title.role, 'title');
  assert.equal(title.fontPt, 28);
  assert.ok(Math.abs(title.x - 0.58) < 0.01 && Math.abs(title.w - 12.17) < 0.01);
  assert.equal(card.fill, '#1F4E9C');
  assert.equal(inner.parent, 's1-e2');
  assert.equal(inner.color, '#FFFFFF');
  assert.equal(chart.type, 'chart');
  assert.ok(Math.abs(chart.w - 5) < 0.01);
});

test('verify: 健全なデッキは違反0件。重なり・小さい文字・薄い文字・代替テキストなしを検出する', async () => {
  const good = await verifyPptx(await make('good.pptx', [
    text({ id: 's1-e1', role: 'title', fontPt: 28, text: 'タイトル', x: 0.58, y: 0.42, w: 12.17, h: 0.6 }),
    text({ id: 's1-e2', text: '本文', x: 1, y: 2, w: 5, h: 1 }),
  ]), t);
  assert.deepEqual(good.violations, []);

  const bad = await verifyPptx(await make('bad.pptx', [
    text({ id: 's1-e1', text: '重なり1', x: 1, y: 2, w: 4, h: 1 }),
    text({ id: 's1-e2', text: '重なり2', x: 1.5, y: 2.2, w: 4, h: 1 }),
    text({ id: 's1-e3', text: '小さい', fontPt: 12, x: 1, y: 4, w: 4, h: 1 }),
    text({ id: 's1-e4', text: '薄い', color: '#CCCCCC', x: 1, y: 5.5, w: 4, h: 1 }),
  ]), t);
  const rules = new Set(bad.violations.map((v) => v.rule));
  for (const r of ['overlap', 'minFont', 'contrast']) assert.ok(rules.has(r), `${r} を検出できない`);
});

test('パッケージ検査: 壊れた XML と、宣言のない軸 ID を検出する', async () => {
  const file = await make('pkg.pptx', [
    el({ id: 's1-e1', type: 'chart', role: '', x: 1, y: 2, w: 5, h: 3, chart: { type: 'bar', labels: ['A', 'B'], values: [1, 2], highlight: 0, labelPt: 12 } }),
  ]);
  const zip = await JSZip.loadAsync(fs.readFileSync(file));
  const slideXml = await zip.file('ppt/slides/slide1.xml').async('string');
  zip.file('ppt/slides/slide1.xml', slideXml.replace('</p:sld>', ''));
  const chartName = Object.keys(zip.files).find((n) => /^ppt\/charts\/chart\d+\.xml$/.test(n));
  const chartXml = await zip.file(chartName).async('string');
  zip.file(chartName, chartXml.replace(/<c:valAx>\s*<c:axId val="\d+"\/>/, '<c:valAx><c:axId val="999999"/>'));
  const broken = path.join(root, 'broken.pptx');
  fs.writeFileSync(broken, await zip.generateAsync({ type: 'nodebuffer' }));
  const { packageErrors } = await readPptxModel(broken);
  assert.ok(packageErrors.some((e) => /slide1\.xml.*壊れ/.test(e)), packageErrors.join('\n'));
  assert.ok(packageErrors.some((e) => /軸/.test(e)), packageErrors.join('\n'));
});

test('存在しないファイルは明示エラー', async () => {
  await assert.rejects(readPptxModel(path.join(root, 'none.pptx')), /見つからない/);
});
