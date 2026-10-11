'use strict';
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const PptxGenJS = require('pptxgenjs');
const { chromium } = require('playwright');
const { detectInstalledFonts, pickFont } = require('../lib/fonts');
const { renderPptx, pdfLineCounts } = require('../render');

const PARAS = [
  '売上は前年同期比で12%増加し、特に新規開拓の商談化率が1.8倍に改善しました。',
  '導入の目的は、属人化した見積業務を標準化し、回答までの時間を半分に短縮することです。',
  '「重要」な顧客ほど、担当者の異動時に関係が途切れやすい。（第2四半期の調査より）',
  '詳細は https://example.com/report/2026/q2/summary をご参照ください。',
  '2026年度第2四半期の営業レビュー：結論、課題、次の打ち手の順にまとめています。',
  'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 の英数字が連続して現れる場合の折り返し。',
  '、。」）といった行頭に置けない約物が、ちょうど行末に来る場合の処理を確認するための文章です。',
  '東京都港区芝公園四丁目二番八号東京タワーのふもとで、新製品の発表会を開催する予定です。',
  '短い文。',
  '本資料は、社内の営業担当者および関連部門の管理職を対象に、今期の重点施策と、その進め方、必要な支援の内容を、できるだけ具体的に示すことを目的としています。',
];
const FACTORS = [1, 0.96, 0.92, 0.88, 0.84, 0.8];
const BOX_IN = 4.0;
const FONT_PT = 16;
const LINE_PT = 24;

async function htmlLines(fontName, factor) {
  const browser = await chromium.launch({ channel: 'msedge' });
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
    const html = `<html lang="ja"><body style="margin:0">${PARAS.map((p, i) =>
      `<div id="p${i}" style="font-family:'${fontName}';font-size:${FONT_PT / 0.75}px;line-height:${LINE_PT / 0.75}px;width:${BOX_IN * 96 * factor}px">${p}</div>`).join('')}</body></html>`;
    await page.setContent(html);
    await page.evaluate(() => document.fonts.ready);
    return await page.evaluate((lh) => [...document.querySelectorAll('div')].map((d) => Math.round(d.getBoundingClientRect().height / lh)), LINE_PT / 0.75);
  } finally {
    await browser.close();
  }
}

async function main() {
  const font = pickFont(detectInstalledFonts()).name;
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'pptx-deck-spike-'));
  const pres = new PptxGenJS();
  pres.layout = 'LAYOUT_WIDE';
  for (const p of PARAS) {
    pres.addSlide().addText(p, { x: 1, y: 1, w: BOX_IN, h: 5, fontFace: font, fontSize: FONT_PT, lineSpacing: LINE_PT, margin: 0, valign: 'top', wrap: true });
  }
  const pptx = path.join(dir, 'spike.pptx');
  await pres.writeFile({ fileName: pptx });
  const { pdf } = renderPptx(pptx, path.join(dir, 'out'), { dpi: 60 });
  const lo = pdfLineCounts(pdf);

  const byFactor = {};
  for (const f of FACTORS) byFactor[f] = await htmlLines(font, f);

  const rows = PARAS.map((p, i) => `| ${i + 1} | ${p.length} | ${lo[i]} | ${FACTORS.map((f) => byFactor[f][i]).join(' | ')} |`);
  const under = FACTORS.map((f) => PARAS.filter((_, i) => byFactor[f][i] < lo[i]).length);
  const ok = FACTORS.filter((f, i) => under[i] === 0);
  const rec = ok.length ? Math.max(...ok.filter((f) => f <= 1)) : null;

  const report = [
    `フォント: ${font} / 枠幅 ${BOX_IN}in / ${FONT_PT}pt / 行間 ${LINE_PT}pt`,
    `| # | 文字数 | LibreOffice | ${FACTORS.map((f) => `HTML×${f}`).join(' | ')} |`,
    `|---|---|---|${FACTORS.map(() => '---').join('|')}|`,
    ...rows,
    `LibreOffice より行数が少なく見積もった段落数（係数ごと）: ${FACTORS.map((f, i) => `×${f}=${under[i]}`).join(' / ')}`,
    rec ? `推奨 wrapSafety: ${rec}（見積もり不足が 0 件になる最大の係数）` : '方式不成立: どの係数でも HTML が LibreOffice より行数を少なく見積もる。ユーザーに報告して方式を見直す',
  ].join('\n');
  fs.writeFileSync(path.join(dir, 'spike-report.md'), report);
  console.log(report);
  console.log(`\nレポート: ${path.join(dir, 'spike-report.md')}`);
  process.exitCode = rec ? 0 : 3;
}

main().catch((e) => { console.error(e); process.exit(1); });
