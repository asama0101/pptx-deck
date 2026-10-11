#!/usr/bin/env node
'use strict';
const { verifyPptx } = require('./check-pptx');
const { loadThresholds } = require('./lib/thresholds');
const { detectInstalledFonts, pickFont } = require('./lib/fonts');
const { measureHtml } = require('./measure');
const { runRules } = require('./rules');

async function acceptanceCheck(pptxPath, min, max, t, { html } = {}) {
  const v = await verifyPptx(pptxPath, t);
  const failures = [];
  const n = v.model.slides.length;
  if (n < min || n > max) failures.push(`枚数 ${n} が期待の範囲 ${min}〜${max} にない`);
  for (const e of v.packageErrors) failures.push(`パッケージ: ${e}`);
  for (const x of v.violations) failures.push(`${x.rule}(スライド ${x.slide}, ${x.id}): ${x.message}`);
  if (html) {
    // 「AIっぽくない」の客観チェックは HTML 段階のモデルで判定する
    const model = await measureHtml(html, { fontName: pickFont(detectInstalledFonts()).name, thresholds: t });
    for (const x of runRules(model, t, { stage: 'html' })) failures.push(`HTML ${x.rule}(スライド ${x.slide}, ${x.id}): ${x.message}`);
  }
  return { ok: failures.length === 0, slides: n, failures };
}

module.exports = { acceptanceCheck };

if (require.main === module) {
  const [file, min, max, html] = process.argv.slice(2);
  if (!file || !min || !max) { console.error('使い方: acceptance-check.js <deck.pptx> <最小枚数> <最大枚数> [deck.html]'); process.exit(1); }
  acceptanceCheck(file, Number(min), Number(max), loadThresholds(), { html }).then((r) => {
    console.log(r.ok ? `PASS(${r.slides} 枚)` : `FAIL\n- ${r.failures.join('\n- ')}`);
    process.exitCode = r.ok ? 0 : 2;
  }).catch((e) => { console.error(`エラー: ${e.message}`); process.exit(1); });
}
