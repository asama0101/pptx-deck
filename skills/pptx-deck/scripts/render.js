'use strict';
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { pathToFileURL } = require('node:url');

function findSoffice() {
  const cands = [
    process.env.SOFFICE_PATH,
    'C:\\Program Files\\LibreOffice\\program\\soffice.exe',
    'C:\\Program Files (x86)\\LibreOffice\\program\\soffice.exe',
  ].filter(Boolean);
  return cands.find((p) => fs.existsSync(p)) || null;
}

function pythonCmd() {
  return process.env.PYTHON || 'python';
}

function runPython(script, args) {
  const r = spawnSync(pythonCmd(), [path.join(__dirname, script), ...args], { encoding: 'utf8' });
  if (r.status !== 0) {
    throw new Error(`Python(${script}) が失敗した。PyMuPDF が必要: pip install pymupdf\n${r.stderr || r.error}`);
  }
  return JSON.parse(r.stdout);
}

function convertToPdf(pptxPath, outDir) {
  const soffice = findSoffice();
  if (!soffice) throw new Error('LibreOffice が見つからない。インストールするか、環境変数 SOFFICE_PATH を設定する');
  if (!fs.existsSync(pptxPath)) throw new Error(`PPTX が見つからない: ${pptxPath}`);
  fs.mkdirSync(outDir, { recursive: true });
  // 他のインスタンスとの衝突・ハングを避けるため、専用プロファイルを使う
  const profile = pathToFileURL(path.join(os.tmpdir(), 'pptx-deck-lo-profile')).href;
  const r = spawnSync(
    soffice,
    ['--headless', '--norestore', `-env:UserInstallation=${profile}`, '--convert-to', 'pdf', '--outdir', outDir, pptxPath],
    { encoding: 'utf8', timeout: 180000, killSignal: 'SIGKILL' },
  );
  if (r.error || r.status !== 0) {
    throw new Error(`LibreOffice の変換に失敗した(180 秒で打ち切り): ${r.error ? r.error.message : r.stderr}`);
  }
  const pdf = path.join(outDir, path.basename(pptxPath).replace(/\.pptx$/i, '.pdf'));
  if (!fs.existsSync(pdf)) throw new Error(`PDF ができなかった: ${pdf}`);
  return pdf;
}

function renderPptx(pptxPath, outDir, { dpi = 80 } = {}) {
  const pdf = convertToPdf(pptxPath, outDir);
  for (const f of fs.readdirSync(outDir)) if (/^slide-[0-9]+\.png$/.test(f)) fs.rmSync(path.join(outDir, f));
  const pngs = runPython('pdf2png.py', [pdf, outDir, String(dpi)]);
  return { pdf, pngs };
}

function pdfLineCounts(pdfPath) {
  return runPython('pdf_lines.py', [pdfPath]);
}

module.exports = { findSoffice, pythonCmd, renderPptx, pdfLineCounts };
