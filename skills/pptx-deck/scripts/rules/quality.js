'use strict';
const { hueInfo } = require('../lib/color');

function viol(rule, slide, el, message, severity = 'error') {
  return { rule, slide: slide ? slide.index : null, id: el ? el.id : null, message, severity };
}

const NO_BODY_LAYOUTS = ['cover', 'section', 'closing'];

function checkTitleAlign(model, t) {
  const out = [];
  let ref = null;
  for (const s of model.slides) {
    if (NO_BODY_LAYOUTS.includes(s.layout)) continue;
    const title = s.elements.find((e) => e.type === 'text' && e.role === 'title');
    if (!title) continue;
    if (!ref) { ref = title; continue; }
    if (Math.abs(title.x - ref.x) > t.titleAlignTolIn || Math.abs(title.y - ref.y) > t.titleAlignTolIn) {
      out.push(viol('titleAlign', s, title, `タイトル位置が他のスライドとずれている(基準 ${ref.x.toFixed(2)},${ref.y.toFixed(2)}in)`));
    }
  }
  return out;
}

function checkMonotony(model, t) {
  const out = [];
  let run = 0;
  let prev = null;
  for (const s of model.slides) {
    run = s.layout === prev ? run + 1 : 1;
    prev = s.layout;
    if (run === t.monotonyRun) out.push(viol('monotony', s, null, `同じレイアウト(${s.layout})が ${run} 枚連続している`));
  }
  if (model.slides.length >= 10) {
    const rich = model.slides.filter((s) => s.layout === 'diagram' || s.layout === 'chart'
      || s.elements.some((e) => e.type === 'chart' || e.diagram)).length;
    if (rich < t.diagramOrChartMinFor10Slides) {
      out.push(viol('monotony', null, null, `10 枚以上なのに図解かグラフが ${rich} 枚しかない(${t.diagramOrChartMinFor10Slides} 枚以上必要)`));
    }
  }
  return out;
}

function coverage(slide, model, margin) {
  const step = 0.1;
  const x0 = margin;
  const y0 = margin;
  const cols = Math.floor((model.slideW - 2 * margin) / step);
  const rows = Math.floor((model.slideH - 2 * margin) / step);
  const rects = slide.elements.filter((e) => !e.decor && e.type !== 'line' && e.w > 0 && e.h > 0);
  let hit = 0;
  for (let r = 0; r < rows; r++) {
    const cy = y0 + (r + 0.5) * step;
    for (let c = 0; c < cols; c++) {
      const cx = x0 + (c + 0.5) * step;
      if (rects.some((e) => cx >= e.x && cx <= e.x + e.w && cy >= e.y && cy <= e.y + e.h)) hit++;
    }
  }
  return hit / (cols * rows);
}

function checkUsage(model, t) {
  const out = [];
  for (const s of model.slides) {
    if (NO_BODY_LAYOUTS.includes(s.layout)) continue;
    const u = coverage(s, model, t.safeMarginIn);
    if (u < t.usage.min) out.push(viol('usage', s, null, `内容領域の使用率 ${Math.round(u * 100)}% が下限 ${t.usage.min * 100}% 未満(余白が無意味に大きい)`));
    else if (u > t.usage.max) out.push(viol('usage', s, null, `内容領域の使用率 ${Math.round(u * 100)}% が上限 ${t.usage.max * 100}% 超(詰め込み)`));
  }
  return out;
}

function checkColorCount(model) {
  const hues = [];
  for (const s of model.slides) {
    for (const e of s.elements) {
      const cs = [e.color, e.fill, e.stroke, e.type === 'chart' && e.chart ? e.chart.accent : null].filter(Boolean);
      for (const c of cs) {
        const { h, s: sat, l } = hueInfo(c);
        if (sat > 0.25 && l > 0.1 && l < 0.97) hues.push(h);
      }
    }
  }
  const groups = [];
  for (const h of hues) {
    const g = groups.find((r) => Math.min(Math.abs(r - h), 360 - Math.abs(r - h)) <= 20);
    if (!g) groups.push(h);
  }
  return groups.length > 1
    ? [viol('colorCount', null, null, `有彩色の色相グループが ${groups.length} 個ある(アクセント 1 色のみ)`)]
    : [];
}

function checkAvoid(model) {
  const out = [];
  for (const s of model.slides) {
    const title = s.elements.find((e) => e.type === 'text' && e.role === 'title');
    if (title && /[。.]\s*$/.test(title.text || '')) out.push(viol('avoid', s, title, 'タイトル末尾の句点: 付けない'));
    for (const e of s.elements) {
      const thin = Math.min(e.w, e.h) <= 0.08;
      if ((e.type === 'line' || e.type === 'shape') && thin && title && Math.max(e.w, e.h) >= 0.3 * title.w
          && e.y > title.y + title.h - 0.05 && e.y < title.y + title.h + 0.35 && e.x < title.x + title.w && e.x + e.w > title.x) {
        out.push(viol('avoid', s, e, 'タイトル下のアクセント線: 使わない'));
      } else if (e.type === 'shape' && e.w <= 0.12 && e.h >= 0.8) {
        out.push(viol('avoid', s, e, '装飾バー: 使わない'));
      }
      if (e.type === 'text' && e.role === 'body' && e.align === 'center' && e.lineCount > 2) {
        out.push(viol('avoid', s, e, '本文のセンタリング: 3 行以上では避ける'));
      }
    }
  }
  return out;
}

function all(model, t) {
  return [...checkTitleAlign(model, t), ...checkMonotony(model, t), ...checkUsage(model, t), ...checkColorCount(model, t), ...checkAvoid(model, t)];
}

module.exports = { all, checkTitleAlign, checkMonotony, checkUsage, checkColorCount, checkAvoid };
