() => {
  const px = (v) => parseFloat(v) || 0;
  const hex2 = (n) => Math.round(n).toString(16).padStart(2, '0').toUpperCase();
  const parseColor = (c) => {
    c = c || '';
    let m = /rgba?\(([^)]+)\)/.exec(c);
    if (m) {
      const [r, g, b, a = 1] = m[1].split(/[ ,\/]+/).filter(Boolean).map(Number);
      return { hex: hex2(r) + hex2(g) + hex2(b), a };
    }
    m = /color\(srgb ([^)]+)\)/.exec(c);       // color-mix() の結果は color(srgb r g b / a) で返る
    if (m) {
      const [r, g, b, a = 1] = m[1].split(/[ \/]+/).filter(Boolean).map(Number);
      return { hex: hex2(r * 255) + hex2(g * 255) + hex2(b * 255), a };
    }
    return null;
  };
  const slides = [...document.querySelectorAll('section.slide')];

  return slides.map((slide, si) => {
    const sr = slide.getBoundingClientRect();
    const rel = (r) => ({ x: r.left - sr.left, y: r.top - sr.top, w: r.width, h: r.height });
    const bgVar = getComputedStyle(slide).getPropertyValue('--bg').trim();
    const slideBg = (bgVar || '#FFFFFF').replace('#', '').toUpperCase();
    const slideRgb = [0, 2, 4].map((i) => parseInt(slideBg.slice(i, i + 2), 16));

    // 背後の実効色: スライドの下地に、DOM 順で前にある塗りつぶし済みの面（pp-shape）のうち、
    // 対象の中心を含むものを順に重ねる。面と文字が兄弟要素でも、親子でも同じ結果になる。
    const els = [...slide.querySelectorAll('.pp-text,.pp-shape,.pp-line,.pp-image,.pp-table,.pp-chart')];
    const fills = els.map((e, i) => {
      if (!e.classList.contains('pp-shape')) return null;
      const f = parseColor(getComputedStyle(e).backgroundColor);
      return f && f.a > 0 ? { i, f, r: rel(e.getBoundingClientRect()) } : null;
    }).filter(Boolean);
    const effBg = (r, idx) => {
      const cx = r.x + r.w / 2, cy = r.y + r.h / 2;
      let base = slideRgb.slice();
      for (const s of fills) {
        if (s.i >= idx) break;
        if (cx < s.r.x || cx > s.r.x + s.r.w || cy < s.r.y || cy > s.r.y + s.r.h) continue;
        const rgb = [0, 2, 4].map((k) => parseInt(s.f.hex.slice(k, k + 2), 16));
        base = base.map((v, k) => v * (1 - s.f.a) + rgb[k] * s.f.a);
      }
      return base.map(hex2).join('');
    };

    const runsOf = (block) => {
      const runs = [];
      const walk = (node) => {
        if (node.nodeType === 3) {
          const t = node.textContent.replace(/\s+/g, ' ');
          if (!t.trim() && !runs.length) return;
          const cs = getComputedStyle(node.parentElement);
          runs.push({
            text: t, size_px: px(cs.fontSize), bold: parseInt(cs.fontWeight) >= 600,
            italic: cs.fontStyle === 'italic', color: (parseColor(cs.color) || { hex: '000000' }).hex,
          });
        } else if (node.nodeType === 1) {
          if (node.tagName === 'BR') { runs.push({ br: true }); return; }
          if (node.tagName === 'UL' || node.tagName === 'OL') return;
          node.childNodes.forEach(walk);
        }
      };
      block.childNodes.forEach(walk);
      const first = runs.find((r) => r.text !== undefined);
      if (first) first.text = first.text.replace(/^\s+/, '');
      const last = [...runs].reverse().find((r) => r.text !== undefined);
      if (last) last.text = last.text.replace(/\s+$/, '');
      return runs.filter((r) => r.br || r.text);
    };

    const alignOf = (cs) => {
      const a = cs.textAlign;
      return a === 'center' || a === 'right' || a === 'justify' ? a : a === 'end' ? 'right' : 'left';
    };

    const parasOf = (el) => {
      let blocks = [...el.querySelectorAll(':scope > p, :scope > ul > li, :scope > ol > li')];
      if (!blocks.length) blocks = [el];
      return blocks.map((b) => {
        const cs = getComputedStyle(b);
        const fs = px(cs.fontSize);
        const lh = cs.lineHeight === 'normal' ? 1.2 : px(cs.lineHeight) / fs;
        return {
          align: alignOf(cs), bullet: b.tagName === 'LI', lh, mb: px(cs.marginBottom),
          runs: runsOf(b),
        };
      }).filter((p) => p.runs.length);
    };

    const base = (el, kind, idx) => {
      const r = rel(el.getBoundingClientRect());
      return {
        kind, idx, rect: r, role: el.dataset.role || null, ph: el.dataset.ph || null,
        bg: effBg(r, idx), overlap: el.dataset.overlap !== undefined, chrome: el.dataset.chrome !== undefined,
      };
    };

    const borderOf = (cs, side) => {
      const w = px(cs['border' + side + 'Width']);
      const c = parseColor(cs['border' + side + 'Color']);
      return w > 0 && cs['border' + side + 'Style'] !== 'none' && c && c.a > 0 ? { hex: c.hex, w } : null;
    };

    const elements = els.map((el, idx) => {
      const cs = getComputedStyle(el);
      if (el.classList.contains('pp-text')) {
        const e = base(el, 'text', idx);
        const range = document.createRange();
        range.selectNodeContents(el);
        const cr = range.getBoundingClientRect();
        const crr = rel(cr);
        const padL = px(cs.paddingLeft), padR = px(cs.paddingRight);
        e.box = { x: e.rect.x + padL, y: crr.y, w: e.rect.w - padL - padR, h: crr.h };
        e.overflow = crr.y + crr.h > e.rect.y + e.rect.h + 2 || crr.x + crr.w > e.rect.x + e.rect.w + 2;
        e.paras = parasOf(el);
        const tn = []; const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
        for (let n = w.nextNode(); n; n = w.nextNode()) if (n.textContent.trim()) tn.push(n);
        e.lastLineChars = null;
        if (tn.length) {
          const last = tn[tn.length - 1], r2 = document.createRange();
          const total = last.textContent.length, rows = new Map();
          for (let i = 0; i < total; i++) {
            r2.setStart(last, i); r2.setEnd(last, i + 1);
            const b = r2.getBoundingClientRect();
            if (b.width > 0) rows.set(Math.round(b.top), (rows.get(Math.round(b.top)) || 0) + 1);
          }
          if (rows.size > 1) e.lastLineChars = rows.get([...rows.keys()].sort((a, b) => a - b).pop());
        }
        return e;
      }
      if (el.classList.contains('pp-shape')) {
        const e = base(el, 'shape', idx);
        const f = parseColor(cs.backgroundColor);
        const radius = px(cs.borderTopLeftRadius);
        e.shape = el.dataset.shape || (radius > 0 ? 'round' : 'rect');
        e.fill = f && f.a > 0 ? f : null;
        e.line = borderOf(cs, 'Top');
        e.radius_px = radius;
        return e;
      }
      if (el.classList.contains('pp-line')) {
        const e = base(el, 'line', idx);
        e.fill = parseColor(cs.backgroundColor) || { hex: '000000', a: 1 };
        e.arrow = el.dataset.arrow === 'end';
        e.reverse = el.dataset.dir === 'rev';      // 矢印を逆向き（右→左、下→上）にする
        return e;
      }
      if (el.classList.contains('pp-image')) {
        const e = base(el, 'image', idx);
        e.src = el.currentSrc || el.getAttribute('src') || '';
        e.alt = el.getAttribute('alt') || '';
        return e;
      }
      if (el.classList.contains('pp-chart')) {
        const e = base(el, 'chart', idx);
        e.chart = JSON.parse(el.dataset.chart);
        return e;
      }
      // pp-table
      const e = base(el, 'table', idx);
      const cells = [...el.querySelectorAll('td,th')].map((c) => rel(c.getBoundingClientRect()));
      const xs = [...new Set(cells.flatMap((c) => [Math.round(c.x), Math.round(c.x + c.w)]))].sort((a, b) => a - b);
      const rows = [...el.rows].map((tr) => ({
        h: tr.getBoundingClientRect().height,
        cells: [...tr.cells].map((td) => {
          const r = rel(td.getBoundingClientRect());
          const tcs = getComputedStyle(td);
          const f = parseColor(tcs.backgroundColor);
          const c0 = xs.indexOf(Math.round(r.x));
          const c1 = xs.indexOf(Math.round(r.x + r.w));
          return {
            c0, c1, rowspan: td.rowSpan || 1,
            fill: f && f.a > 0 ? f : null,
            borders: { l: borderOf(tcs, 'Left'), r: borderOf(tcs, 'Right'), t: borderOf(tcs, 'Top'), b: borderOf(tcs, 'Bottom') },
            pad: { l: px(tcs.paddingLeft), r: px(tcs.paddingRight), t: px(tcs.paddingTop), b: px(tcs.paddingBottom) },
            valign: tcs.verticalAlign === 'top' || tcs.verticalAlign === 'bottom' ? tcs.verticalAlign : 'middle',
            paras: parasOf(td), bg: effBg(r, idx),
          };
        }),
      }));
      e.table = { xs, rows };
      return e;
    });
    return { index: si + 1, layout: slide.dataset.layout || 'content', bg: slideBg, elements };
  });
}
