'use strict';
const { spawnSync } = require('node:child_process');
const { chromium } = require('playwright');
const { detectInstalledFonts, pickFont } = require('./lib/fonts');
const { findSoffice, pythonCmd } = require('./render');

async function run() {
  const results = [];
  const add = (name, ok, hint, required = true) => results.push({ name, ok, hint, required });

  add('Node 20 以上', Number(process.versions.node.split('.')[0]) >= 20, 'Node 20 以上をインストールする');
  for (const m of ['pptxgenjs', 'playwright', 'jszip', 'fast-xml-parser']) {
    let ok = true;
    try { require(m); } catch { ok = false; }
    add(`npm パッケージ ${m}`, ok, 'skills/pptx-deck で npm install を実行する');
  }
  let edge = true;
  try { const b = await chromium.launch({ channel: 'msedge' }); await b.close(); } catch { edge = false; }
  add('Edge (Playwright channel=msedge)', edge, 'Microsoft Edge をインストールする');
  try {
    const f = pickFont(detectInstalledFonts());
    add(`日本語フォント: ${f.name}${f.fellBack ? '（代替。BIZ UDPゴシックが未導入）' : ''}`, true, '');
  } catch (e) {
    add('日本語フォント', false, e.message);
  }
  add('LibreOffice（画像化の検証）', !!findSoffice(), 'LibreOffice をインストールする。なくても幾何検査だけで動く', false);
  const py = spawnSync(pythonCmd(), ['-c', 'import pymupdf'], { encoding: 'utf8' });
  add('Python + PyMuPDF（PDF→PNG）', py.status === 0, 'pip install pymupdf を実行する。なくても幾何検査だけで動く', false);

  let failed = false;
  for (const r of results) {
    const mark = r.ok ? 'OK' : r.required ? 'NG' : '警告';
    console.log(`[${mark}] ${r.name}${r.ok ? '' : ` → ${r.hint}`}`);
    if (!r.ok && r.required) failed = true;
  }
  return !failed;
}

module.exports = { run };
