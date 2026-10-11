'use strict';
const { test, after } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { measureHtml } = require('../scripts/measure');
const { loadThresholds } = require('../scripts/lib/thresholds');
const { writeFixture } = require('./helpers/fixture');

const t = loadThresholds();
const root = fs.mkdtempSync(path.join(os.tmpdir(), 'pptx-deck-measure-'));
after(() => fs.rmSync(root, { recursive: true, force: true }));

function page(body, name) {
  const css = require('node:url').pathToFileURL(path.join(__dirname, '..', 'design', 'base.css')).href;
  const file = path.join(root, `${name}.html`);
  fs.writeFileSync(file, `<!doctype html><html lang="ja"><head><meta charset="utf-8"><link rel="stylesheet" href="${css}"></head><body>${body}</body></html>`);
  return file;
}

test('基本: 役割・親子・線・画像・チャート・ノート・箇条書きを要素モデルにする', async () => {
  const dir = path.join(root, '日本語 フォルダ'); // 日本語と空白を含むパス
  const m = await measureHtml(writeFixture('basic', dir), { fontName: 'BIZ UDPゴシック', thresholds: t, rasterDir: root });
  assert.equal(m.slides.length, 1);
  assert.equal(m.fontFace, 'BIZ UDPゴシック');
  assert.equal(m.theme.accent, '#1F4E9C');
  const s = m.slides[0];
  assert.equal(s.layout, 'content');
  assert.equal(s.notes.trim(), 'ノートの本文');
  const byRole = (r) => s.elements.filter((e) => e.role === r);
  const title = byRole('title')[0];
  assert.equal(title.fontPt, 28);
  assert.ok(Math.abs(title.x - 56 / 96) < 0.01 && Math.abs(title.y - 40 / 96) < 0.01);
  const card = s.elements.find((e) => e.type === 'shape');
  assert.equal(card.kind, 'roundRect');
  assert.equal(card.fill, '#F3F3F3');
  const inner = s.elements.find((e) => e.parent === card.id);
  assert.equal(inner.text, 'カード内の本文');
  const line = s.elements.find((e) => e.type === 'line');
  assert.equal(line.dir, 'right');
  assert.equal(line.arrow, true);
  assert.equal(line.h, 0);
  const img = s.elements.find((e) => e.type === 'image');
  assert.equal(img.alt, 'アイコン');
  assert.match(img.src, /\.png$/i);
  assert.ok(fs.existsSync(img.src));
  const chart = s.elements.find((e) => e.type === 'chart');
  assert.equal(chart.chart.type, 'bar');
  assert.equal(chart.chart.highlight, 1);
  assert.equal(chart.chart.labelPt, 12);
  const list = s.elements.find((e) => e.type === 'text' && e.paras && e.paras.length === 2);
  assert.ok(list.paras.every((p) => p.bullet));
  assert.equal(list.paras[1].runs.length, 2);
  assert.equal(list.paras[1].runs[0].bold, true);
});

test('wrapStable: 幅を 92% に狭めると行数が増える段落を検出する', async () => {
  const kanji = '春夏秋冬東西南北天地人山川海空風雨雪花'; // 20字。漢字は全角固定幅
  const file = page(
    `<section class="slide"><div class="pp-text" data-role="body" id="tight" style="position:absolute;left:56px;top:100px;width:214px">${kanji}</div>
     <div class="pp-text" data-role="body" id="loose" style="position:absolute;left:56px;top:300px;width:700px">${kanji}</div></section>`, 'wrap');
  const m = await measureHtml(file, { fontName: 'BIZ UDPゴシック', thresholds: t, rasterDir: root });
  const [tight, loose] = m.slides[0].elements;
  assert.equal(tight.wrapStable, false);
  assert.equal(loose.wrapStable, true);
});

test('overflow: 固定高の枠をあふれる内容と、区切りのない長い英数字を検出する', async () => {
  const file = page(
    `<section class="slide"><div class="pp-text" data-role="body" style="position:absolute;left:56px;top:100px;width:200px;height:40px">${'長い文章です。'.repeat(10)}</div>
     <div class="pp-text" data-role="body" style="position:absolute;left:56px;top:300px;width:120px">https://example.com/very/long/unbreakable/path/segment</div></section>`, 'overflow');
  const m = await measureHtml(file, { fontName: 'BIZ UDPゴシック', thresholds: t, rasterDir: root });
  assert.equal(m.slides[0].elements[0].overflow, true);
  assert.equal(m.slides[0].elements[1].overflow, true);
});

test('空のスライドは要素なしのモデル、スライドが無い HTML は明示エラー', async () => {
  const m = await measureHtml(page('<section class="slide" data-layout="section"></section>', 'empty'), { thresholds: t, rasterDir: root });
  assert.deepEqual(m.slides[0].elements, []);
  await assert.rejects(measureHtml(page('<p>スライドなし</p>', 'none'), { thresholds: t, rasterDir: root }), /section\.slide/);
});

test('data-chart が壊れた JSON、または未対応の型ならスライド番号つきで停止する', async () => {
  const bad = page('<section class="slide"><div class="pp-chart" data-chart="{oops" style="width:100px;height:100px"></div></section>', 'badjson');
  await assert.rejects(measureHtml(bad, { thresholds: t, rasterDir: root }), /スライド 1.*data-chart.*JSON/);
  const stacked = page(`<section class="slide"><div class="pp-chart" data-chart='{"type":"stacked","labels":["a"],"values":[1]}' style="width:100px;height:100px"></div></section>`, 'stacked');
  await assert.rejects(measureHtml(stacked, { thresholds: t, rasterDir: root }), /スライド 1.*未対応/);
});

test('スライドが 1280x720px でなければ明示エラー', async () => {
  await assert.rejects(measureHtml(page('<section class="slide" style="width:800px"></section>', 'size'), { thresholds: t, rasterDir: root }), /1280x720/);
});

test('unmeasured: pp-* の外にある文字(クラスの付け忘れ、<p> の中の <ul>)は検出する', async () => {
  const file = page(
    `<section class="slide"><p>クラスを付け忘れた段落です。</p>
     <p class="pp-text" data-role="body" style="position:absolute;left:56px;top:300px;width:600px"><ul><li>pの中のリスト</li></ul></p></section>`, 'unmeasured');
  const m = await measureHtml(file, { fontName: 'BIZ UDPゴシック', thresholds: t, rasterDir: root });
  const un = m.slides[0].unmeasured;
  assert.ok(un.some((x) => x.includes('クラスを付け忘れた')), JSON.stringify(un));
  assert.ok(un.some((x) => x.includes('pの中のリスト')), JSON.stringify(un));
});

test('入れ子の箇条書きは、親も子も段落として落とさない', async () => {
  const file = page(
    `<section class="slide"><div class="pp-text" data-role="body" style="position:absolute;left:56px;top:100px;width:600px"><ul><li>親項目<ul><li>子項目</li></ul></li><li>次の親</li></ul></div></section>`, 'nested');
  const m = await measureHtml(file, { fontName: 'BIZ UDPゴシック', thresholds: t, rasterDir: root });
  const texts = m.slides[0].elements[0].paras.map((p) => p.runs.map((r) => r.text).join(''));
  assert.deepEqual(texts, ['親項目', '子項目', '次の親']);
  assert.deepEqual(m.slides[0].unmeasured, []);
});
