'use strict';
const { execFileSync } = require('node:child_process');

const FONT_CANDIDATES = ['BIZ UDPゴシック', 'Yu Gothic UI', 'Meiryo UI', 'Yu Gothic', 'Meiryo', '游ゴシック', 'メイリオ'];

function detectInstalledFonts() {
  const script = '[Console]::OutputEncoding=[Text.Encoding]::UTF8; Add-Type -AssemblyName System.Drawing; ' +
    '(New-Object System.Drawing.Text.InstalledFontCollection).Families | ForEach-Object { $_.Name }';
  const out = execFileSync('powershell', ['-NoProfile', '-Command', script], { encoding: 'utf8' });
  return out.split(/\r?\n/).map((s) => s.trim()).filter(Boolean);
}

// 列挙されるフォント名はシステムの表示言語で変わる(日本語名のことも英語名のこともある)
const ALIASES = { 'BIZ UDPゴシック': ['BIZ UDPGothic'], '游ゴシック': ['Yu Gothic'], 'メイリオ': ['Meiryo'] };

function pickFont(installed, candidates = FONT_CANDIDATES) {
  const name = candidates.find((c) => installed.includes(c) || (ALIASES[c] || []).some((a) => installed.includes(a)));
  if (!name) throw new Error(`日本語フォントが見つからない。次のいずれかをインストールする: ${candidates.join('、')}`);
  return { name, fellBack: name !== candidates[0] };
}

module.exports = { FONT_CANDIDATES, detectInstalledFonts, pickFont };
