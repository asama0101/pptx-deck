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
const { writeIcons, readAccents } = require('./lib/icons');

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

function attemptOf(opt) {
  if (opt.attempt === undefined) return 0;
  const n = Number(opt.attempt);
  if (opt.attempt === true || !Number.isInteger(n) || n < 0) throw new Error('--attempt には 0 以上の整数を付ける(これまでの修正回数)');
  return n;
}

async function checkHtml(htmlPath, opt, t) {
  const font = pickFont(detectInstalledFonts());
  const rasterDir = fs.mkdtempSync(path.join(os.tmpdir(), 'pptx-deck-raster-'));
  const model = await measureHtml(htmlPath, { fontName: font.name, thresholds: t, rasterDir });
  const violations = runRules(model, t, { stage: 'html' });
  const summary = summarize(violations);
  const report = {
    ok: summary.errors === 0, stage: 'html', font, violations, summary,
    suggestion: suggestFix(violations, attemptOf(opt), t),
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
    // 作業フォルダには、deck.html が参照する base.css・chart-preview.js・icons/ だけを置く。見本 5 種は参照用なので、スキルの design/ をそのまま読む
    for (const f of ['base.css', 'chart-preview.js']) fs.copyFileSync(path.join(DESIGN, f), path.join(a, f));
    const icons = writeIcons(a, readAccents(path.join(a, 'base.css')));
    console.log(JSON.stringify({ ok: true, dir: path.resolve(a), icons: icons.length, samples: DESIGN }));
    return;
  }
  if (cmd === 'icons') {
    if (!a) throw new Error('使い方: run.js icons <作業フォルダ>  (作業フォルダの base.css の --accent・--accent2 の色で icons/ を作り直す)');
    const icons = writeIcons(a, readAccents(path.join(a, 'base.css')));
    console.log(JSON.stringify({ ok: true, dir: path.resolve(a, 'icons'), icons: icons.length }));
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
    if (!a || !b) throw new Error('使い方: run.js build <deck.html> <out.pptx> [--work <作業フォルダ(一時フォルダ内の名前に使う)>] [--attempt N] [--no-render]');
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
        suggestion: suggestFix(v.violations, attemptOf(opt), t),
      };
      // 確認用の画像・検査結果は作業フォルダに置かず、OS の一時フォルダ(pptx-deck/<作業名>)に出す。消すのは OS の掃除に任せる
      const tempDir = path.join(os.tmpdir(), 'pptx-deck', path.basename(path.resolve(opt.work || b)).replace(/\.pptx$/i, ''));
      fs.mkdirSync(tempDir, { recursive: true });
      out.tempDir = tempDir;
      if (!opt['no-render'] && findSoffice()) {
        const dir = path.join(tempDir, 'render');
        try {
          out.pngs = renderPptx(b, dir).pngs;
          out.renderNote = 'LibreOffice による近似の画像。PowerPoint で開いて最終確認することを勧める';
        } catch (e) {
          out.renderNote = `画像化に失敗した(検査結果は有効): ${e.message.split('\n')[0]}`;
        }
      } else if (!opt['no-render']) {
        out.renderNote = 'LibreOffice が未導入のため画像化を省略した(幾何検査のみ)';
      }
      out.reportPath = path.join(tempDir, 'report.json');
      fs.writeFileSync(out.reportPath, JSON.stringify(out, null, 2));
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
  throw new Error('使い方: run.js <init|icons|doctor|check|build|verify|render> …');
}

main().catch((e) => { console.error(`エラー: ${e.message}`); process.exit(1); });
