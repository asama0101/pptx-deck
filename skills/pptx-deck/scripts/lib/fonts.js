'use strict';
const { execFileSync } = require('node:child_process');

const FONT_CANDIDATES = ['BIZ UDPゴシック', 'Yu Gothic UI', 'Meiryo UI', 'Yu Gothic', 'Meiryo', '游ゴシック', 'メイリオ'];

function detectInstalledFonts() {
  const script = '[Console]::OutputEncoding=[Text.Encoding]::UTF8; Add-Type -AssemblyName System.Drawing; ' +
    '(New-Object System.Drawing.Text.InstalledFontCollection).Families | ForEach-Object { $_.Name }';
  const out = execFileSync('powershell', ['-NoProfile', '-Command', script], { encoding: 'utf8' });
  return out.split(/\r?\n/).map((s) => s.trim()).filter(Boolean);
}

function pickFont(installed, candidates = FONT_CANDIDATES) {
  const name = candidates.find((c) => installed.includes(c));
  if (!name) throw new Error(`日本語フォントが見つからない。次のいずれかをインストールする: ${candidates.join('、')}`);
  return { name, fellBack: name !== candidates[0] };
}

module.exports = { FONT_CANDIDATES, detectInstalledFonts, pickFont };
