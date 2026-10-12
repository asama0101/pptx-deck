'use strict';
const fs = require('node:fs');
const path = require('node:path');

const SRC = path.join(__dirname, '..', '..', 'references', 'icons');
const SRC_COLOR = '#1F4E9C';

// references/icons の線画 SVG を、基調色(<名前>.svg)・強調色(<名前>-o.svg)・白(<名前>-w.svg)の 3 色で作業フォルダに書き出す
function writeIcons(destDir, { accent = '#1F4E9C', accent2 = '#B85A0B' } = {}) {
  const dir = path.join(destDir, 'icons');
  fs.mkdirSync(dir, { recursive: true });
  const names = [];
  for (const f of fs.readdirSync(SRC).filter((x) => x.endsWith('.svg'))) {
    const name = f.replace(/\.svg$/, '');
    const src = fs.readFileSync(path.join(SRC, f), 'utf8');
    for (const [suffix, color] of [['', accent], ['-o', accent2], ['-w', '#FFFFFF']]) {
      fs.writeFileSync(path.join(dir, `${name}${suffix}.svg`), src.replace(SRC_COLOR, color));
    }
    names.push(name);
  }
  return names;
}

// base.css の --accent・--accent2 を読む(アイコンの色を、配色に合わせる)
function readAccents(cssPath) {
  const css = fs.existsSync(cssPath) ? fs.readFileSync(cssPath, 'utf8') : '';
  const pick = (n) => (new RegExp(`--${n}:\\s*(#[0-9a-fA-F]{6})`).exec(css) || [])[1];
  return { accent: pick('accent'), accent2: pick('accent2') };
}

module.exports = { writeIcons, readAccents };
