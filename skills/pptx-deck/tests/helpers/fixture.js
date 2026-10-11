'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

const FIX = path.join(__dirname, '..', 'fixtures');
const BASE_CSS = pathToFileURL(path.join(__dirname, '..', '..', 'design', 'base.css')).href;
const ICON = pathToFileURL(path.join(FIX, 'icon.svg')).href;

function writeFixture(name, dir, extra = {}) {
  let html = fs.readFileSync(path.join(FIX, `${name}.html`), 'utf8').replaceAll('{{BASE_CSS}}', BASE_CSS).replaceAll('{{ICON}}', ICON);
  for (const [k, v] of Object.entries(extra)) html = html.replaceAll(`{{${k}}}`, v);
  fs.mkdirSync(dir, { recursive: true });
  const out = path.join(dir, `${name}.html`);
  fs.writeFileSync(out, html);
  return out;
}

module.exports = { writeFixture };
