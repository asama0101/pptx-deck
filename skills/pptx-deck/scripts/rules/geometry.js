'use strict';
const { contrastRatio } = require('../lib/color');

const PT_IN = 1 / 72;

function viol(rule, slide, el, message, severity = 'error') {
  return { rule, slide: slide ? slide.index : null, id: el ? el.id : null, message, severity };
}

function overlapArea(a, b) {
  const w = Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x);
  const h = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y);
  return w > 0 && h > 0 ? w * h : 0;
}

function checkBounds(model, t) {
  const out = [];
  const tol = t.childOverflowPt * PT_IN;
  const m = t.safeMarginIn;
  for (const s of model.slides) {
    const byId = new Map(s.elements.map((e) => [e.id, e]));
    for (const e of s.elements) {
      if (e.decor) continue;
      const right = e.x + e.w;
      const bottom = e.y + e.h;
      const fullBleed = e.type === 'shape' && e.x <= tol && e.y <= tol && right >= model.slideW - tol && bottom >= model.slideH - tol;
      if (fullBleed) continue;
      if (e.x < -tol || e.y < -tol || right > model.slideW + tol || bottom > model.slideH + tol) {
        out.push(viol('bounds', s, e, 'スライドの外にはみ出している'));
      } else if (e.x < m - tol || e.y < m - tol || right > model.slideW - m + tol || bottom > model.slideH - m + tol) {
        out.push(viol('bounds', s, e, `安全マージン(${m}in)の外にある`));
      }
      const p = e.parent ? byId.get(e.parent) : null;
      if (p && (e.x < p.x - tol || e.y < p.y - tol || right > p.x + p.w + tol || bottom > p.y + p.h + tol)) {
        out.push(viol('bounds', s, e, '親の枠からはみ出している'));
      }
    }
  }
  return out;
}

function checkOverlap(model, t) {
  const out = [];
  for (const s of model.slides) {
    const groups = new Map();
    for (const e of s.elements) {
      if (e.decor || e.type === 'line') continue;
      const k = e.parent || '';
      if (!groups.has(k)) groups.set(k, []);
      groups.get(k).push(e);
    }
    for (const list of groups.values()) {
      for (let i = 0; i < list.length; i++) {
        for (let j = i + 1; j < list.length; j++) {
          const a = list[i];
          const b = list[j];
          const area = overlapArea(a, b);
          const small = Math.min(a.w * a.h, b.w * b.h);
          if (area > 0 && small > 0 && area / small > t.overlapRatio) {
            out.push(viol('overlap', s, b, `${a.id} と重なっている(${Math.round((area / small) * 100)}%)`));
          }
        }
      }
    }
  }
  return out;
}

function checkMinFont(model, t) {
  const out = [];
  for (const s of model.slides) {
    for (const e of s.elements) {
      if (e.type === 'text' && e.text && e.text.trim()) {
        const min = t.minFontPt[e.role || 'body'] ?? t.minFontPt.body;
        if (e.fontPt + 1e-6 < min) out.push(viol('minFont', s, e, `${e.fontPt}pt は最小 ${min}pt(${e.role || 'body'})を下回る`));
      }
      if (e.type === 'chart' && e.chart && e.chart.labelPt + 1e-6 < t.minFontPt.label) {
        out.push(viol('minFont', s, e, `チャートのラベル ${e.chart.labelPt}pt は最小 ${t.minFontPt.label}pt を下回る`));
      }
    }
  }
  return out;
}

function checkHierarchy(model, t) {
  const out = [];
  for (const s of model.slides) {
    const title = s.elements.find((e) => e.type === 'text' && e.role === 'title');
    const others = s.elements.filter((e) => e.type === 'text' && (e.role === 'lead' || e.role === 'body'));
    if (!title || !others.length) continue;
    const top = Math.max(...others.map((e) => e.fontPt));
    if (title.fontPt - top < t.hierarchyGapPt - 1e-6) {
      out.push(viol('hierarchy', s, title, `タイトル ${title.fontPt}pt と本文 ${top}pt の差が ${t.hierarchyGapPt}pt 未満`));
    }
  }
  return out;
}

function checkContrast(model, t) {
  const out = [];
  for (const s of model.slides) {
    const byId = new Map(s.elements.map((e) => [e.id, e]));
    for (const e of s.elements) {
      if (e.decor || e.type !== 'text' || !e.text || !e.text.trim() || !e.color) continue;
      let bg = s.bg;
      let p = e.parent ? byId.get(e.parent) : null;
      while (p) {
        if (p.fill) { bg = p.fill; break; }
        p = p.parent ? byId.get(p.parent) : null;
      }
      const ratio = contrastRatio(e.color, bg);
      if (ratio < t.contrastMin) out.push(viol('contrast', s, e, `コントラスト比 ${ratio.toFixed(2)} は ${t.contrastMin} 未満(${e.color} on ${bg})`));
    }
  }
  return out;
}

function checkImages(model) {
  const out = [];
  const slideArea = model.slideW * model.slideH;
  for (const s of model.slides) {
    for (const e of s.elements) {
      if (e.type === 'image' && !(e.alt && e.alt.trim())) out.push(viol('images', s, e, '画像に代替テキスト(alt)がない'));
    }
    const hasText = s.elements.some((e) => e.type === 'text' && e.text && e.text.trim());
    const hasChart = s.elements.some((e) => e.type === 'chart');
    const big = s.elements.find((e) => e.type === 'image' && e.role !== 'icon' && (e.w * e.h) / slideArea >= 0.6);
    if (big && !hasText && !hasChart) out.push(viol('images', s, big, '画像だけのスライド(本文が画像になっている)'));
  }
  return out;
}

function checkOverflow(model) {
  const out = [];
  for (const s of model.slides) {
    for (const e of s.elements) if (e.overflow) out.push(viol('overflow', s, e, '内容が枠からあふれている'));
  }
  return out;
}

function checkWrapStable(model, t) {
  const out = [];
  for (const s of model.slides) {
    for (const e of s.elements) {
      if (e.type === 'text' && !e.fixed && e.wrapStable === false) {
        out.push(viol('wrapStable', s, e, `幅を ${Math.round(t.wrapSafety * 100)}% に狭めると行数が増える(PowerPoint で折り返しが変わる恐れ)`));
      }
    }
  }
  return out;
}

function checkUnmeasured(model) {
  const out = [];
  for (const s of model.slides) {
    for (const txt of s.unmeasured || []) out.push(viol('unmeasured', s, null, `pp-* の外にある文字は PPTX に出ない: 「${txt}」(pp-text を付ける。箇条書きは <p> でなく <div class="pp-text"> に <ul> を入れる)`));
  }
  return out;
}

function checkTextBorder(model) {
  const out = [];
  for (const s of model.slides) {
    for (const e of s.elements) {
      if (e.type === 'text' && e.border) out.push(viol('textBorder', s, e, 'pp-text の枠線(border)は PPTX に写らない。線は pp-line、囲みは pp-shape で作る'));
    }
  }
  return out;
}

function all(model, t) {
  return [
    ...checkBounds(model, t), ...checkOverlap(model, t), ...checkMinFont(model, t),
    ...checkHierarchy(model, t), ...checkContrast(model, t), ...checkImages(model, t),
  ];
}

function htmlOnly(model, t) {
  return [...checkOverflow(model, t), ...checkWrapStable(model, t), ...checkUnmeasured(model), ...checkTextBorder(model)];
}

module.exports = {
  all, htmlOnly, checkBounds, checkOverlap, checkMinFont, checkHierarchy, checkContrast, checkImages, checkOverflow, checkWrapStable, checkUnmeasured, checkTextBorder,
};
