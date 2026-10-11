'use strict';
const fs = require('node:fs');
const path = require('node:path');

const FILE = path.join(__dirname, '..', '..', 'config', 'thresholds.json');

function merge(base, over) {
  const out = { ...base };
  for (const [k, v] of Object.entries(over || {})) {
    out[k] = v && typeof v === 'object' && !Array.isArray(v) && typeof base[k] === 'object' ? merge(base[k], v) : v;
  }
  return out;
}

function loadThresholds(overrides = {}) {
  return merge(JSON.parse(fs.readFileSync(FILE, 'utf8')), overrides);
}

module.exports = { loadThresholds };
