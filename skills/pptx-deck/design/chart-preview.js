(function (root) {
  'use strict';

  const fmt = (v) => (typeof v === 'number' ? v.toLocaleString('en-US') : v);

  // 横棒の幾何: 左に項目名、右に値のラベルの余白を取る(はみ出して見切れないように)
  function hGeom(labels, w) {
    const labelW = Math.min(Math.max(...labels.map((l) => String(l).length), 1) * 14 + 16, w * 0.45);
    const x0 = labelW + 8;
    return { labelW, x0, maxLen: Math.max(w - x0 - 64, 40) };
  }

  function color(spec, i, theme) {
    if (spec.type === 'line') return theme.accent;
    return spec.highlight === i ? theme.accent : theme.neutral;
  }

  // 積み上げ棒の系列色: 注目の系列だけアクセント、他は無彩色の濃淡(scripts/build.js と同じ)
  const SERIES_NEUTRALS = ['#767676', '#595959', '#404040'];

  function stackedBody(spec, w, h, theme, pad, iw, ih, font) {
    const { labels, series } = spec;
    const horizontal = spec.type === 'stackedh';
    let ni = 0;
    const colors = series.map((_, i) => (i === spec.highlight ? theme.accent : SERIES_NEUTRALS[ni++ % SERIES_NEUTRALS.length]));
    const totals = labels.map((_, c) => series.reduce((a, x) => a + x.values[c], 0));
    const max = spec.type === 'stacked100' ? 100 : Math.max(...totals, 1);
    const norm = (v, c) => (spec.type === 'stacked100' ? (v / (totals[c] || 1)) * 100 : v);
    const legendH = 36;
    const plotH = ih - legendH;
    const white = 'font-family="sans-serif" font-size="14" font-weight="700" fill="#fff" text-anchor="middle"';
    let body = '';
    const hg = hGeom(labels, w);
    labels.forEach((label, c) => {
      let acc = 0;
      series.forEach((x, i) => {
        const v = x.values[c];
        const nv = norm(v, c);
        const len = (nv / max) * (horizontal ? hg.maxLen : plotH);
        if (horizontal) {
          const bh = plotH / labels.length;
          const x0 = hg.x0 + (acc / max) * hg.maxLen;
          const y0 = pad.t + c * bh + bh * 0.15;
          body += `<rect x="${x0}" y="${y0}" width="${len}" height="${bh * 0.7}" fill="${colors[i]}" stroke="#fff" stroke-width="1.5"/>`;
          if (v !== 0) body += `<text x="${x0 + len / 2}" y="${y0 + bh * 0.35 + 5}" ${white}>${fmt(v)}</text>`;
        } else {
          const bw = iw / labels.length;
          const y0 = pad.t + plotH - ((acc + nv) / max) * plotH;
          body += `<rect x="${pad.l + c * bw + bw * 0.2}" y="${y0}" width="${bw * 0.6}" height="${len}" fill="${colors[i]}" stroke="#fff" stroke-width="1.5"/>`;
          if (v !== 0) body += `<text x="${pad.l + c * bw + bw / 2}" y="${y0 + len / 2 + 5}" ${white}>${fmt(v)}</text>`;
        }
        acc += nv;
      });
      if (horizontal) body += `<text x="${hg.labelW}" y="${pad.t + c * (plotH / labels.length) + plotH / labels.length / 2 + 5}" text-anchor="end" ${font}>${label}</text>`;
      else body += `<text x="${pad.l + c * (iw / labels.length) + iw / labels.length / 2}" y="${pad.t + plotH + 20}" text-anchor="middle" ${font}>${label}</text>`;
    });
    if (spec.legend !== false) {
      series.forEach((x, i) => {
        const lx = pad.l + i * 160;
        body += `<rect x="${lx}" y="${h - 22}" width="14" height="14" fill="${colors[i]}"/><text x="${lx + 20}" y="${h - 10}" ${font}>${x.name}</text>`;
      });
    }
    return body;
  }

  function areaBody(spec, w, h, theme, pad, iw, ih, font) {
    const { labels, series } = spec;
    let ni = 0;
    const colors = series.map((_, i) => (i === spec.highlight ? theme.accent : ['#BFBFBF', '#D9D9D9', '#A6A6A6'][ni++ % 3]));
    const n = labels.length;
    const totals = labels.map((_, c) => series.reduce((a, x) => a + x.values[c], 0));
    const max = Math.max(...totals, 1);
    const plotH = ih - 36;
    const xs = (c) => pad.l + (n === 1 ? iw / 2 : (c / (n - 1)) * iw);
    const ys = (v) => pad.t + plotH - (v / max) * plotH;
    let body = '';
    const base = labels.map(() => 0);
    series.forEach((x, i) => {
      const top = x.values.map((v, c) => base[c] + v);
      const up = top.map((v, c) => `${xs(c)},${ys(v)}`);
      const down = base.map((v, c) => `${xs(c)},${ys(v)}`).reverse();
      body += `<polygon points="${up.concat(down).join(' ')}" fill="${colors[i]}" stroke="#fff" stroke-width="1.5"/>`;
      top.forEach((v, c) => { base[c] = v; });
    });
    labels.forEach((label, c) => { body += `<text x="${xs(c)}" y="${pad.t + plotH + 20}" text-anchor="middle" ${font}>${label}</text>`; });
    series.forEach((x, i) => {
      const lx = pad.l + i * 160;
      body += `<rect x="${lx}" y="${h - 22}" width="14" height="14" fill="${colors[i]}"/><text x="${lx + 20}" y="${h - 10}" ${font}>${x.name}</text>`;
    });
    return body;
  }

  // 累計の棒(cumulative)。プロット領域の割合と軸の余白は scripts/build.js の PLOT_CUM・CUM_AXIS_MARGIN と同じ
  const PLOT_CUM = { x: 0.03, y: 0.04, w: 0.94, h: 0.74 };

  function cumulativeBody(spec, w, h, theme, font) {
    const { labels, values } = spec;
    const n = values.length;
    const max = Math.max(...values, 1) * 1.15;
    const left = PLOT_CUM.x * w;
    const pw = PLOT_CUM.w * w;
    const top = PLOT_CUM.y * h;
    const ph = PLOT_CUM.h * h;
    const yOf = (v) => top + ph * (1 - v / max);
    const white = 'font-family="sans-serif" font-size="14" font-weight="700" fill="#fff" text-anchor="middle"';
    const dark = 'font-family="sans-serif" font-size="14" font-weight="700" fill="#333" text-anchor="middle"';
    const hotCls = 'font-family="sans-serif" font-size="14" font-weight="700" fill="' + (theme.accent2 || '#333') + '" text-anchor="middle"';
    const baseColor = theme.accentMid || '#BFBFBF';
    let body = '';
    values.forEach((v, i) => {
      const cx = left + ((i + 0.5) * pw) / n;
      const bw = (pw / n) / 1.5;
      const baseV = i === 0 ? v : values[i - 1];
      const inc = i === 0 ? 0 : v - values[i - 1];
      body += `<rect x="${cx - bw / 2}" y="${yOf(baseV)}" width="${bw}" height="${yOf(0) - yOf(baseV)}" fill="${baseColor}" stroke="#fff" stroke-width="1.5"/>`;
      if (inc > 0) {
        body += `<rect x="${cx - bw / 2}" y="${yOf(v)}" width="${bw}" height="${yOf(baseV) - yOf(v)}" fill="${theme.accent}" stroke="#fff" stroke-width="1.5"/>`;
        body += `<text x="${cx}" y="${(yOf(baseV) + yOf(v)) / 2 + 5}" ${white}>＋${fmt(inc)}</text>`;
      }
      body += `<text x="${cx}" y="${yOf(v) - 8}" ${spec.hot === i ? hotCls : dark}>${fmt(v)}</text>`;
      body += `<text x="${cx}" y="${yOf(0) + 22}" text-anchor="middle" ${font}>${labels[i]}</text>`;
    });
    body += `<rect x="${left}" y="${h - 22}" width="14" height="14" fill="${baseColor}"/><text x="${left + 20}" y="${h - 10}" ${font}>前年までの累計</text>`;
    body += `<rect x="${left + 160}" y="${h - 22}" width="14" height="14" fill="${theme.accent}"/><text x="${left + 180}" y="${h - 10}" ${font}>その年の増加分</text>`;
    return body;
  }

  // ウォーターフォール。幾何は scripts/lib/waterfall.js と同じ(合計は先頭と末尾が既定)
  function waterfallBody(spec, w, h, theme, font) {
    const { labels, values } = spec;
    const n = values.length;
    const tset = new Set(Array.isArray(spec.totals) ? spec.totals : [0, n - 1]);
    let run = 0;
    const parts = values.map((v, i) => {
      if (tset.has(i)) { run = v; return { kind: 'total', base: 0, size: v, top: v }; }
      const next = run + v;
      const p = { kind: v >= 0 ? 'up' : 'down', base: Math.min(run, next), size: Math.abs(v), top: Math.max(run, next) };
      run = next;
      return p;
    });
    const max = Math.max(...parts.map((p) => p.top), 1) * 1.15;
    const left = PLOT_CUM.x * w;
    const pw = PLOT_CUM.w * w;
    const top = PLOT_CUM.y * h;
    const ph = PLOT_CUM.h * h;
    const yOf = (v) => top + ph * (1 - v / max);
    const down = '#404040';
    const fills = { total: '#767676', up: theme.accent, down };
    const textFill = { total: '#333', up: theme.accent, down };
    let body = '';
    parts.forEach((p, i) => {
      const cx = left + ((i + 0.5) * pw) / n;
      const bw = (pw / n) / 1.5;
      body += `<rect x="${cx - bw / 2}" y="${yOf(p.top)}" width="${bw}" height="${yOf(p.base) - yOf(p.top)}" fill="${fills[p.kind]}" stroke="#fff" stroke-width="1.5"/>`;
      const text = p.kind === 'total' ? fmt(p.size) : (p.kind === 'up' ? '＋' : '▲') + fmt(p.size);
      body += `<text x="${cx}" y="${yOf(p.top) - 8}" font-family="sans-serif" font-size="14" font-weight="700" fill="${textFill[p.kind]}" text-anchor="middle">${text}</text>`;
      body += `<text x="${cx}" y="${yOf(0) + 22}" text-anchor="middle" ${font}>${labels[i]}</text>`;
    });
    return body;
  }

  function chartSvg(spec, w, h, theme) {
    const { type, labels } = spec;
    const stacked = ['stacked', 'stackedh', 'stacked100', 'area'].includes(type);
    const multiLine = type === 'line' && Array.isArray(spec.series);
    const values = stacked ? [] : multiLine ? spec.series[0].values : spec.values;
    if (!['bar', 'barh', 'line', 'pie', 'stacked', 'stackedh', 'stacked100', 'area', 'cumulative', 'waterfall'].includes(type)) throw new Error(`チャートの型が未対応: ${type}`);
    const n = values.length;
    const max = Math.max(...values, 1);
    const font = 'font-family="sans-serif" font-size="14" fill="#555"';
    const pad = { l: 48, r: 24, t: 24, b: 40 };
    const iw = w - pad.l - pad.r;
    const ih = h - pad.t - pad.b;
    let body = '';
    if (type === 'area') {
      body += areaBody(spec, w, h, theme, pad, iw, ih, font);
    } else if (stacked) {
      body += stackedBody(spec, w, h, theme, pad, iw, ih, font);
    } else if (type === 'cumulative') {
      body += cumulativeBody(spec, w, h, theme, font);
    } else if (type === 'waterfall') {
      body += waterfallBody(spec, w, h, theme, font);
    } else if (type === 'bar') {
      const bw = iw / n;
      values.forEach((v, i) => {
        const bh = (v / max) * ih;
        body += `<rect x="${pad.l + i * bw + bw * 0.2}" y="${pad.t + ih - bh}" width="${bw * 0.6}" height="${bh}" fill="${color(spec, i, theme)}"/>`;
        body += `<text x="${pad.l + i * bw + bw / 2}" y="${h - 14}" text-anchor="middle" ${font}>${labels[i]}</text>`;
        body += `<text x="${pad.l + i * bw + bw / 2}" y="${pad.t + ih - bh - 6}" text-anchor="middle" ${font}>${fmt(v)}</text>`;
      });
    } else if (type === 'barh') {
      const bh = ih / n;
      const hg = hGeom(labels, w);
      values.forEach((v, i) => {
        const bw = (v / max) * hg.maxLen;
        body += `<rect x="${hg.x0}" y="${pad.t + i * bh + bh * 0.2}" width="${bw}" height="${bh * 0.6}" fill="${color(spec, i, theme)}"/>`;
        body += `<text x="${hg.labelW}" y="${pad.t + i * bh + bh / 2 + 5}" text-anchor="end" ${font}>${labels[i]}</text>`;
        body += `<text x="${hg.x0 + bw + 6}" y="${pad.t + i * bh + bh / 2 + 5}" ${font}>${fmt(v)}</text>`;
      });
    } else if (multiLine) {
      // 複数系列の折れ線: 注目の系列(推奨案)だけ橙、他は無彩色の濃淡(scripts/build.js と同じ)
      const NEU = ['#767676', '#A6A6A6', '#595959'];
      const all = spec.series.flatMap((x) => x.values);
      const lmax = Math.max(...all, 1);
      const px = (i) => pad.l + (i + 0.5) * (iw / n);
      const py = (v) => pad.t + ih - (v / lmax) * ih;
      spec.series.forEach((x, si) => {
        const col = si === spec.highlight ? (theme.accent2 || theme.accent) : NEU[si % NEU.length];
        body += `<polyline points="${x.values.map((v, i) => `${px(i)},${py(v)}`).join(' ')}" fill="none" stroke="${col}" stroke-width="3"/>`;
        x.values.forEach((v, i) => { body += `<circle cx="${px(i)}" cy="${py(v)}" r="5" fill="${col}"/>`; });
        body += `<text x="${pad.l + 8 + si * 130}" y="${pad.t + 10}" ${font}><tspan fill="${col}">●</tspan> ${x.name}</text>`;
      });
      labels.forEach((l, i) => { body += `<text x="${px(i)}" y="${h - 14}" text-anchor="middle" ${font}>${l}</text>`; });
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
      // 輪郭の多角形(data-shape="poly")。data-points の px 座標で、枠を切り抜く
      document.querySelectorAll('.pp-shape[data-shape="poly"][data-points]').forEach(function (el) {
        const d = el.getAttribute('data-points').split('|').map(function (ring) {
          return 'M' + ring.trim().split(/\s+/).join(' L') + ' Z';
        }).join(' ').replace(/,/g, ' ');
        el.style.clipPath = "path('" + d + "')";
        el.style.borderRadius = '0';
      });
      const cs = getComputedStyle(document.documentElement);
      const theme = { accent: cs.getPropertyValue('--accent').trim(), neutral: cs.getPropertyValue('--neutral-chart').trim(), accent2: cs.getPropertyValue('--accent2').trim(), accentMid: cs.getPropertyValue('--accent-mid').trim() };
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
