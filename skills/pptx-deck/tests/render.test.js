'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const PptxGenJS = require('pptxgenjs');
const { findSoffice, renderPptx, pdfLineCounts } = require('../scripts/render');

const soffice = findSoffice();

test('LibreOffice を見つけられる（未導入ならこの環境ではスキップ）', { skip: !soffice }, () => {
  assert.ok(fs.existsSync(soffice));
});

test('PPTX を PDF と PNG にできる（日本語・空白を含むパスでも）', { skip: !soffice }, async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'pptx-deck-test-'));
  const work = path.join(dir, '日本語 フォルダ');
  fs.mkdirSync(work);
  const pres = new PptxGenJS();
  pres.layout = 'LAYOUT_WIDE';
  pres.addSlide().addText('画像化のテスト', { x: 1, y: 1, w: 5, h: 1, fontSize: 24, margin: 0 });
  pres.addSlide().addText('二枚目', { x: 1, y: 1, w: 5, h: 1, fontSize: 24, margin: 0 });
  const pptx = path.join(work, 'デッキ.pptx');
  await pres.writeFile({ fileName: pptx });
  const out = path.join(work, 'png');
  const r = renderPptx(pptx, out, { dpi: 60 });
  assert.ok(fs.existsSync(r.pdf));
  assert.equal(r.pngs.length, 2);
  for (const p of r.pngs) assert.ok(fs.statSync(p).size > 1000, `${p} が小さすぎる`);
  assert.deepEqual(pdfLineCounts(r.pdf), [1, 1]);
  fs.rmSync(dir, { recursive: true, force: true });
});

test('存在しない PPTX は分かりやすいエラーにする', { skip: !soffice }, () => {
  assert.throws(() => renderPptx('C:\\no\\such\\file.pptx', os.tmpdir()), /見つからない/);
});
