'use strict';
const geometry = require('./geometry');
const quality = require('./quality');

function runRules(model, t, { stage = 'html' } = {}) {
  const v = [...geometry.all(model, t)];
  if (stage === 'html') v.push(...quality.all(model, t), ...geometry.htmlOnly(model, t));
  return v;
}

function summarize(violations) {
  const byRule = {};
  let errors = 0;
  for (const v of violations) {
    byRule[v.rule] = (byRule[v.rule] || 0) + 1;
    if (v.severity === 'error') errors++;
  }
  return { errors, byRule };
}

module.exports = { runRules, summarize };
