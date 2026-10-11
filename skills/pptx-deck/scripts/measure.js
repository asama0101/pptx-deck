'use strict';
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { pathToFileURL, fileURLToPath } = require('node:url');
const { chromium } = require('playwright');
const { SLIDE_W_IN, SLIDE_H_IN } = require('./lib/units');

const CHART_TYPES = ['bar', 'barh', 'line', 'pie'];

// ブラウザ内で実行される。外側のスコープを参照しないこと。
function extractInPage({ safety }) {
  const PX = 96;
  const TYPES = ['pp-text', 'pp-shape', 'pp-line', 'pp-image', 'pp-chart'];
  const toHex = (c) => {
    const m = /rgba?\(([^)]+)\)/.exec(c || '');
    if (!m) return null;
    const p = m[1].split(',').map((s) => parseFloat(s));
    if (p.length > 3 && p[3] === 0) return null;
    return '#' + p.slice(0, 3).map((n) => Math.round(n).toString(16).padStart(2, '0')).join('').toUpperCase();
  };
  const r2 = (n) => Math.round(n * 100) / 100;
  const r4 = (n) => Math.round(n * 10000) / 10000;

  const collectRuns = (src) => {
    const runs = [];
    const walk = (node) => {
      node.childNodes.forEach((ch) => {
        if (ch.nodeType === 3) {
          const text = ch.textContent.replace(/\s+/g, ' ');
          if (!text.trim() && !runs.length) return;
          const pcs = getComputedStyle(ch.parentElement);
          runs.push({ text, color: toHex(pcs.color), bold: parseInt(pcs.fontWeight, 10) >= 600, pt: r2(parseFloat(pcs.fontSize) * 0.75) });
        } else if (ch.nodeType === 1) {
          if (ch.tagName === 'BR') runs.push({ text: '', br: true });
          else if (ch.tagName !== 'UL' && ch.tagName !== 'OL') walk(ch);
        }
      });
    };
    walk(src);
    while (runs.length && !runs[runs.length - 1].br && !runs[runs.length - 1].text.trim()) runs.pop();
    if (runs.length && !runs[0].br) runs[0].text = runs[0].text.replace(/^\s+/, '');
    if (runs.length && !runs[runs.length - 1].br) runs[runs.length - 1].text = runs[runs.length - 1].text.replace(/\s+$/, '');
    return runs;
  };

  const root = getComputedStyle(document.documentElement);
  const theme = {
    accent: root.getPropertyValue('--accent').trim().toUpperCase(),
    neutral: root.getPropertyValue('--neutral-chart').trim().toUpperCase(),
  };
  const slides = [];
  document.querySelectorAll('section.slide').forEach((sec, si) => {
    const sr = sec.getBoundingClientRect();
    const slide = {
      index: si + 1,
      layout: sec.dataset.layout || 'content',
      bg: toHex(getComputedStyle(sec).backgroundColor) || '#FFFFFF',
      notes: (sec.querySelector('aside.notes') || {}).textContent || '',
      size: [Math.round(sr.width), Math.round(sr.height)],
      elements: [],
    };
    const nodes = [...sec.querySelectorAll(TYPES.map((c) => '.' + c).join(','))];
    const ids = new Map();
    nodes.forEach((el, i) => {
      const id = `s${si + 1}-e${i + 1}`;
      ids.set(el, id);
      el.setAttribute('data-pp-id', id);
    });
    nodes.forEach((el) => {
      const cs = getComputedStyle(el);
      const r = el.getBoundingClientRect();
      const type = TYPES.find((c) => el.classList.contains(c)).slice(3);
      let parent = null;
      for (let p = el.parentElement; p && p !== sec; p = p.parentElement) {
        if (ids.has(p)) { parent = ids.get(p); break; }
      }
      const e = {
        id: ids.get(el), type, role: el.dataset.role || (type === 'text' ? 'body' : ''), parent,
        decor: el.hasAttribute('data-decor'), diagram: !!el.closest('[data-diagram]'),
        x: r4((r.left - sr.left) / PX), y: r4((r.top - sr.top) / PX), w: r4(r.width / PX), h: r4(r.height / PX),
      };
      if (type === 'text') {
        const blocks = [...el.querySelectorAll(':scope > p, :scope > li, :scope > ul > li, :scope > ol > li')];
        const sources = blocks.length ? blocks : [el];
        e.paras = sources.map((src) => ({ runs: collectRuns(src), bullet: src.tagName === 'LI' }));
        e.text = e.paras.map((p) => p.runs.map((x) => (x.br ? '\n' : x.text)).join('')).join('\n');
        const sizes = e.paras.flatMap((p) => p.runs.filter((x) => !x.br).map((x) => x.pt));
        e.fontPt = sizes.length ? Math.min(...sizes) : r2(parseFloat(cs.fontSize) * 0.75);
        const first = e.paras.flatMap((p) => p.runs).find((x) => !x.br);
        e.color = (first && first.color) || toHex(cs.color);
        e.bold = !!(first && first.bold);
        e.align = { start: 'left', end: 'right' }[cs.textAlign] || cs.textAlign;
        e.valign = el.dataset.valign || 'top';
        const lh = parseFloat(cs.lineHeight);
        const lhPx = Number.isFinite(lh) ? lh : parseFloat(cs.fontSize) * 1.3;
        e.lineSpacingPt = r2(lhPx * 0.75);
        e.paraSpaceAfter = blocks.length ? r2(parseFloat(getComputedStyle(blocks[0]).marginBottom) * 0.75) : 0;
        e.lineCount = Math.max(1, Math.round(r.height / lhPx));
        e.fixed = el.hasAttribute('data-fixed');
        e.overflow = el.scrollHeight > el.clientHeight + 1 || el.scrollWidth > el.clientWidth + 1;
        e.wrapStable = true;
        if (!e.fixed && e.text.trim()) {
          const prev = { w: el.style.width, f: el.style.flex, m: el.style.maxWidth };
          el.style.flex = 'none';
          el.style.maxWidth = 'none';
          el.style.width = r.width * safety + 'px';
          const narrowed = el.getBoundingClientRect().height;
          el.style.width = prev.w;
          el.style.flex = prev.f;
          el.style.maxWidth = prev.m;
          e.wrapStable = narrowed <= r.height + 0.5;
        }
      } else if (type === 'shape') {
        e.fill = toHex(cs.backgroundColor);
        const bw = parseFloat(cs.borderTopWidth);
        e.stroke = bw > 0 ? toHex(cs.borderTopColor) : null;
        e.strokeW = bw > 0 ? r2(bw * 0.75) : 0;
        const radius = cs.borderTopLeftRadius;
        if (radius.includes('%') && parseFloat(radius) >= 50) e.kind = 'ellipse';
        else if (parseFloat(radius) > 0) { e.kind = 'roundRect'; e.radius = r4(parseFloat(radius) / PX); } else e.kind = 'rect';
      } else if (type === 'line') {
        e.dir = el.dataset.dir || 'right';
        e.arrow = el.dataset.arrow === 'end';
        e.stroke = toHex(cs.color);
        e.strokeW = r2(Math.max(parseFloat(cs.borderTopWidth), parseFloat(cs.borderLeftWidth)) * 0.75);
        if (e.dir === 'right' || e.dir === 'left') {
          e.y = r4((r.top + r.height / 2 - sr.top) / PX);
          e.h = 0;
        } else {
          e.x = r4((r.left + r.width / 2 - sr.left) / PX);
          e.w = 0;
        }
      } else if (type === 'image') {
        e.alt = el.getAttribute('alt') || '';
        e.src = el.currentSrc || el.src;
      } else if (type === 'chart') {
        e.chartRaw = el.getAttribute('data-chart');
      }
      slide.elements.push(e);
    });
    slides.push(slide);
  });
  return { slides, theme };
}

async function measureHtml(htmlPath, { fontName, thresholds, channel, rasterDir } = {}) {
  const ch = channel || process.env.PPTX_DECK_BROWSER_CHANNEL || 'msedge';
  let browser;
  try {
    browser = await chromium.launch({ channel: ch });
  } catch (e) {
    throw new Error(`ブラウザ(channel=${ch})を起動できない。Microsoft Edge をインストールする。詳細: ${e.message.split('\n')[0]}`);
  }
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 3 });
    await page.goto(pathToFileURL(path.resolve(htmlPath)).href);
    if (fontName) await page.addStyleTag({ content: `:root{--font-main:"${fontName}";}` });
    await page.evaluate(() => document.fonts.ready);
    const raw = await page.evaluate(extractInPage, { safety: thresholds ? thresholds.wrapSafety : 0.92 });
    if (!raw.slides.length) throw new Error('section.slide が見つからない。スライドは <section class="slide"> で書く');
    const dir = rasterDir || fs.mkdtempSync(path.join(os.tmpdir(), 'pptx-deck-raster-'));
    const slides = [];
    for (const s of raw.slides) {
      const [w, h] = s.size;
      if (w !== 1280 || h !== 720) throw new Error(`スライド ${s.index}: サイズが ${w}x${h}px。1280x720px にする`);
      const elements = [];
      for (const e of s.elements) {
        if (e.type === 'chart') {
          let spec;
          try { spec = JSON.parse(e.chartRaw); } catch (err) { throw new Error(`スライド ${s.index}: data-chart が不正な JSON: ${err.message}`); }
          if (!CHART_TYPES.includes(spec.type)) throw new Error(`スライド ${s.index}: チャートの型 "${spec.type}" は未対応(${CHART_TYPES.join('/')})`);
          if (!Array.isArray(spec.labels) || !Array.isArray(spec.values) || spec.labels.length !== spec.values.length || spec.values.some((v) => typeof v !== 'number')) {
            throw new Error(`スライド ${s.index}: data-chart の labels と values は同じ長さで、values は数値にする`);
          }
          e.chart = { labelPt: 12, ...spec };
          delete e.chartRaw;
        }
        if (e.type === 'image') {
          const file = fileURLToPath(e.src);
          if (/\.svg$/i.test(file)) {
            const png = path.join(dir, `${e.id}.png`);
            await page.locator(`[data-pp-id="${e.id}"]`).screenshot({ path: png, omitBackground: true });
            e.src = png;
          } else {
            e.src = file;
          }
        }
        elements.push(e);
      }
      slides.push({ index: s.index, layout: s.layout, bg: s.bg, notes: s.notes, elements });
    }
    return { slideW: SLIDE_W_IN, slideH: SLIDE_H_IN, fontFace: fontName || 'BIZ UDPゴシック', theme: raw.theme, slides };
  } finally {
    await browser.close();
  }
}

module.exports = { measureHtml };
