(function (root) {
  'use strict';

  function color(spec, i, theme) {
    if (spec.type === 'line') return theme.accent;
    return spec.highlight === i ? theme.accent : theme.neutral;
  }

  function chartSvg(spec, w, h, theme) {
    const { type, labels, values } = spec;
    if (!['bar', 'barh', 'line', 'pie'].includes(type)) throw new Error(`チャートの型が未対応: ${type}`);
    const n = values.length;
    const max = Math.max(...values, 1);
    const font = 'font-family="sans-serif" font-size="14" fill="#555"';
    const pad = { l: 48, r: 24, t: 24, b: 40 };
    const iw = w - pad.l - pad.r;
    const ih = h - pad.t - pad.b;
    let body = '';
    if (type === 'bar') {
      const bw = iw / n;
      values.forEach((v, i) => {
        const bh = (v / max) * ih;
        body += `<rect x="${pad.l + i * bw + bw * 0.2}" y="${pad.t + ih - bh}" width="${bw * 0.6}" height="${bh}" fill="${color(spec, i, theme)}"/>`;
        body += `<text x="${pad.l + i * bw + bw / 2}" y="${h - 14}" text-anchor="middle" ${font}>${labels[i]}</text>`;
        body += `<text x="${pad.l + i * bw + bw / 2}" y="${pad.t + ih - bh - 6}" text-anchor="middle" ${font}>${v}</text>`;
      });
    } else if (type === 'barh') {
      const bh = ih / n;
      values.forEach((v, i) => {
        const bw = (v / max) * (iw - 40);
        body += `<rect x="${pad.l + 40}" y="${pad.t + i * bh + bh * 0.2}" width="${bw}" height="${bh * 0.6}" fill="${color(spec, i, theme)}"/>`;
        body += `<text x="${pad.l + 34}" y="${pad.t + i * bh + bh / 2 + 5}" text-anchor="end" ${font}>${labels[i]}</text>`;
        body += `<text x="${pad.l + 46 + bw}" y="${pad.t + i * bh + bh / 2 + 5}" ${font}>${v}</text>`;
      });
    } else if (type === 'line') {
      const pts = values.map((v, i) => `${pad.l + (i + 0.5) * (iw / n)},${pad.t + ih - (v / max) * ih}`);
      body += `<polyline points="${pts.join(' ')}" fill="none" stroke="${theme.accent}" stroke-width="3"/>`;
      values.forEach((v, i) => {
        body += `<circle cx="${pad.l + (i + 0.5) * (iw / n)}" cy="${pad.t + ih - (v / max) * ih}" r="5" fill="${theme.accent}"/>`;
        body += `<text x="${pad.l + (i + 0.5) * (iw / n)}" y="${h - 14}" text-anchor="middle" ${font}>${labels[i]}</text>`;
      });
    } else {
      const total = values.reduce((a, b) => a + b, 0) || 1;
      const cx = w / 2;
      const cy = h / 2;
      const r = Math.min(w, h) / 2 - 24;
      let a0 = -Math.PI / 2;
      values.forEach((v, i) => {
        const a1 = a0 + (v / total) * Math.PI * 2;
        const large = a1 - a0 > Math.PI ? 1 : 0;
        const p = (a) => `${cx + r * Math.cos(a)},${cy + r * Math.sin(a)}`;
        body += `<path d="M${cx},${cy} L${p(a0)} A${r},${r} 0 ${large} 1 ${p(a1)} Z" fill="${color(spec, i, theme)}" stroke="#fff" stroke-width="2"/>`;
        a0 = a1;
      });
    }
    return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">${body}</svg>`;
  }

  if (typeof module !== 'undefined' && module.exports) module.exports = { chartSvg };

  if (typeof document !== 'undefined') {
    document.addEventListener('DOMContentLoaded', function () {
      const cs = getComputedStyle(document.documentElement);
      const theme = { accent: cs.getPropertyValue('--accent').trim(), neutral: cs.getPropertyValue('--neutral-chart').trim() };
      document.querySelectorAll('.pp-chart[data-chart]').forEach(function (el) {
        try {
          const r = el.getBoundingClientRect();
          el.innerHTML = chartSvg(JSON.parse(el.getAttribute('data-chart')), Math.round(r.width), Math.round(r.height), theme);
        } catch (e) {
          el.textContent = 'チャートのプレビューを描けない: ' + e.message;
        }
      });
    });
  }
})(this);
