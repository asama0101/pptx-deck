#!/usr/bin/env node
'use strict';
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { loadThresholds } = require('./lib/thresholds');
const { detectInstalledFonts, pickFont } = require('./lib/fonts');
const { measureHtml } = require('./measure');
const { runRules, summarize } = require('./rules');
const { suggestFix } = require('./suggest');
const { buildPptx } = require('./build');
const { verifyPptx } = require('./check-pptx');
const { findSoffice, renderPptx } = require('./render');

const DESIGN = path.join(__dirname, '..', 'design');

function parseArgs(argv) {
  const pos = [];
  const opt = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) opt[a.slice(2)] = argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[++i] : true;
    else pos.push(a);
  }
  return { pos, opt };
}

const print = (report) => console.log(JSON.stringify(report, null, 2));

async function checkHtml(htmlPath, opt, t) {
  const font = pickFont(detectInstalledFonts());
  const rasterDir = fs.mkdtempSync(path.join(os.tmpdir(), 'pptx-deck-raster-'));
  const model = await measureHtml(htmlPath, { fontName: font.name, thresholds: t, rasterDir });
  const violations = runRules(model, t, { stage: 'html' });
  const summary = summarize(violations);
  const report = {
    ok: summary.errors === 0, stage: 'html', font, violations, summary,
    suggestion: suggestFix(violations, Number(opt.attempt || 0), t),
  };
  return { report, model, rasterDir };
}

async function main() {
  const { pos, opt } = parseArgs(process.argv.slice(2));
  const [cmd, a, b] = pos;
  const t = loadThresholds();

  if (cmd === 'init') {
    if (!a) throw new Error('使い方: run.js init <作業フォルダ>');
    fs.mkdirSync(a, { recursive: true });
    for (const f of ['base.css', 'chart-preview.js', 'catalog.html']) fs.copyFileSync(path.join(DESIGN, f), path.join(a, f));
    console.log(JSON.stringify({ ok: true, dir: path.resolve(a) }));
    return;
  }
  if (cmd === 'doctor') {
    process.exitCode = (await require('./doctor').run()) ? 0 : 1;
    return;
  }
  if (cmd === 'check') {
    if (!a) throw new Error('使い方: run.js check <deck.html> [--attempt N]');
    const { report, rasterDir } = await checkHtml(a, opt, t);
    fs.rmSync(rasterDir, { recursive: true, force: true });
    print(report);
    process.exitCode = report.ok ? 0 : 2;
    return;
  }
  if (cmd === 'build') {
    if (!a || !b) throw new Error('使い方: run.js build <deck.html> <out.pptx> [--work <dir>] [--attempt N] [--no-render]');
    const { report, model, rasterDir } = await checkHtml(a, opt, t);
    try {
      if (!report.ok) { print(report); process.exitCode = 2; return; }
      fs.mkdirSync(path.dirname(path.resolve(b)), { recursive: true });
      await buildPptx(model, b);
      const v = await verifyPptx(b, t);
      const summary = summarize(v.violations);
      const out = {
        ...report, stage: 'pptx', ok: summary.errors === 0 && v.packageErrors.length === 0,
        violations: v.violations, summary, packageErrors: v.packageErrors, pptx: path.resolve(b),
        suggestion: suggestFix(v.violations, Number(opt.attempt || 0), t),
      };
      if (!opt['no-render'] && findSoffice()) {
        const dir = path.join(opt.work || path.dirname(path.resolve(b)), 'render');
        out.pngs = renderPptx(b, dir).pngs;
        out.renderNote = 'LibreOffice による近似の画像。PowerPoint で開いて最終確認することを勧める';
      } else if (!opt['no-render']) {
        out.renderNote = 'LibreOffice が未導入のため画像化を省略した(幾何検査のみ)';
      }
      if (opt.work) fs.writeFileSync(path.join(opt.work, 'report.json'), JSON.stringify(out, null, 2));
      print(out);
      process.exitCode = out.ok ? 0 : 2;
    } finally {
      fs.rmSync(rasterDir, { recursive: true, force: true });
    }
    return;
  }
  if (cmd === 'verify') {
    if (!a) throw new Error('使い方: run.js verify <deck.pptx>');
    const v = await verifyPptx(a, t);
    const summary = summarize(v.violations);
    print({ ok: summary.errors === 0 && v.packageErrors.length === 0, stage: 'pptx', violations: v.violations, summary, packageErrors: v.packageErrors });
    process.exitCode = summary.errors === 0 && v.packageErrors.length === 0 ? 0 : 2;
    return;
  }
  if (cmd === 'render') {
    if (!a || !b) throw new Error('使い方: run.js render <deck.pptx> <出力フォルダ>');
    print({ ok: true, ...renderPptx(a, b) });
    return;
  }
  throw new Error('使い方: run.js <init|doctor|check|build|verify|render> …');
}

main().catch((e) => { console.error(`エラー: ${e.message}`); process.exit(1); });
