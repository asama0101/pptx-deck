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
  if (model.theme.sample) return out; // 見本集(data-sample)は、型を並べて見せるので対象外
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

function coverage(slide, model, margin, pad = 0) {
  const step = 0.1;
  const x0 = margin;
  const y0 = margin;
  const cols = Math.floor((model.slideW - 2 * margin) / step);
  const rows = Math.floor((model.slideH - 2 * margin) / step);
  const rects = slide.elements
    .filter((e) => !e.decor && (pad > 0 ? e.type === 'line' || e.type === 'text' || (e.w > 0 && e.h > 0) : e.type !== 'line' && e.w > 0 && e.h > 0))
    .map((e) => ({ x: e.x - pad, y: e.y - pad, w: e.w + 2 * pad, h: e.h + 2 * pad }));
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
    const u = coverage(s, model, t.safeMarginIn, t.usage.textPadIn);
    const raw = coverage(s, model, t.safeMarginIn);
    if (u < t.usage.min) out.push(viol('usage', s, null, `内容領域の使用率 ${Math.round(u * 100)}% が下限 ${t.usage.min * 100}% 未満(余白が無意味に大きい)`));
    else if (raw > t.usage.max) out.push(viol('usage', s, null, `内容領域の使用率 ${Math.round(raw * 100)}% が上限 ${t.usage.max * 100}% 超(詰め込み)`));
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

// 同じ大きさの四角を横に並べただけの構成(カード並べ)を禁止する。図解(data-diagram)の中は対象外
function checkCardRow(model, t) {
  const out = [];
  const tol = 0.05;
  for (const s of model.slides) {
    const cards = s.elements.filter((e) => e.type === 'shape' && !e.decor && !e.diagram && !e.parent && e.w > 0 && e.h > 0);
    const seen = new Set();
    for (const a of cards) {
      if (seen.has(a.id)) continue;
      const row = cards.filter((b) => Math.abs(b.y - a.y) <= tol && Math.abs(b.w - a.w) / a.w <= 0.05 && Math.abs(b.h - a.h) / a.h <= 0.05);
      row.forEach((b) => seen.add(b.id));
      if (row.length >= t.cardRowMin) {
        out.push(viol('cardRow', s, a, `同じ大きさの四角を ${row.length} 個並べただけの構成になっている(時間軸・式・課題→対策の対応・罫線で区切った行・図解に作り直す)`));
      }
    }
  }
  return out;
}


// --- 視線設計と色彩心理(矢印効果・孤立効果・Zの法則・色彩心理) ---
const sameColor = (a, b) => !!a && !!b && a.toUpperCase() === b.toUpperCase();
const isAccent = (e, t0) => (e.type === 'text' && sameColor(e.color, t0.accent)) || (e.type === 'shape' && sameColor(e.fill, t0.accent));
const isContentLayout = (s) => !NO_BODY_LAYOUTS.includes(s.layout);
const inRect = (px, py, r, pad = 0) => px >= r.x - pad && px <= r.x + r.w + pad && py >= r.y - pad && py <= r.y + r.h + pad;

// 矢印効果: 矢印は強調したい対象を指す。先端に何もない矢印は違反(安全領域の端で終わる矢印は「続き」として許す)
function checkArrowTarget(model, t) {
  const out = [];
  for (const s of model.slides) {
    for (const a of s.elements.filter((e) => e.type === 'line' && e.arrow)) {
      const tip = { right: [a.x + a.w, a.y], left: [a.x, a.y], down: [a.x, a.y + a.h], up: [a.x, a.y] }[a.dir];
      const tail = { right: [a.x, a.y], left: [a.x + a.w, a.y], down: [a.x, a.y], up: [a.x, a.y + a.h] }[a.dir];
      const edge = t.arrowEdgeIn;
      const nearEdge = tip[0] >= model.slideW - t.safeMarginIn - edge || tip[1] >= model.slideH - t.safeMarginIn - edge;
      const targets = s.elements.filter((e) => e.type !== 'line' && !e.decor && e.id !== a.id);
      const hit = targets.some((e) => inRect(tip[0], tip[1], e, t.arrowReachIn) && !inRect(tail[0], tail[1], e));
      if (!hit && !nearEdge) out.push(viol('arrowTarget', s, a, `矢印の先 ${t.arrowReachIn}in 以内に、指す対象の要素がない(矢印は強調したい対象を指す)`));
    }
  }
  return out;
}

// 孤立効果: 強調(アクセント色)は他と違う 1 点に絞る。多すぎると孤立しない
function checkIsolation(model, t) {
  const out = [];
  for (const s of model.slides) {
    if (!isContentLayout(s)) continue;
    const items = s.elements.filter((e) => (e.type === 'text' || e.type === 'shape') && e.role !== 'title' && !e.decor);
    const acc = items.filter((e) => isAccent(e, model.theme));
    if (!acc.length) continue;
    if (acc.length > t.isolation.maxCount || acc.length / items.length > t.isolation.maxRatio) {
      out.push(viol('isolation', s, acc[0], `強調(アクセント色)が ${acc.length} 個(同種の要素の ${Math.round((acc.length / items.length) * 100)}%)ある。1 点に絞ると孤立効果で目立つ`));
    }
  }
  return out;
}

// Zの法則: 視線は左上(タイトル)→右上→右下へ動く。強調は右か下に置き、終点(右下)を空けない
function checkZFlow(model, t) {
  const out = [];
  for (const s of model.slides) {
    if (!isContentLayout(s)) continue;
    const W = model.slideW;
    const H = model.slideH;
    const body = s.elements.filter((e) => e.type !== 'line' && e.role !== 'title' && !e.decor && e.w > 0 && e.h > 0);
    const acc = body.filter((e) => isAccent(e, model.theme));
    if (acc.length) {
      const big = acc.reduce((m, e) => (e.w * e.h > m.w * m.h ? e : m));
      if ((big.x + big.w / 2) / W < t.zFlow.startX && (big.y + big.h / 2) / H < t.zFlow.startY) {
        out.push(viol('zFlow', s, big, '最も目立つ強調が左上(視線の始点)にある。右か下(Z の終点)に寄せる', 'warning'));
      }
    }
    if (body.length && !body.some((e) => e.x + e.w > W * 0.5 && e.y + e.h > H * 0.5)) {
      out.push(viol('zFlow', s, null, '右下(視線の終点)に何もない。結論・出典・次の行動などを置く', 'warning'));
    }
  }
  return out;
}

// 色彩心理: アクセント色の色相が、伝えるメッセージの性質(data-tone)に合っているか
function checkColorTone(model, t) {
  const tone = model.theme.tone;
  if (!tone) return [viol('colorTone', null, null, '<body data-tone="…"> が未指定(trust/growth/alert/energy/premium/neutral から、伝える性質に合うものを選ぶ)', 'warning')];
  const range = t.tones[tone];
  if (!range) return [viol('colorTone', null, null, `data-tone "${tone}" は未対応(${Object.keys(t.tones).join('/')})`)];
  if (range === 'any') return [];
  const { h, s } = hueInfo(model.theme.accent);
  const [lo, hi] = range;
  const ok = lo <= hi ? h >= lo && h <= hi : h >= lo || h <= hi;
  return ok && s > 0.25 ? [] : [viol('colorTone', null, null, `アクセント色 ${model.theme.accent}(色相 ${Math.round(h)}°)が、トーン "${tone}"(${lo}〜${hi}°)に合わない。色を変えるか、トーンを選び直す`)];
}

// 数字の比較はグラフで可視化する。同じ単位の数字が 3 つ以上あるのに、チャートがないスライドは違反。
// 図解で可視化している(規模比較など)なら data-numbers="visual"、比較ではなく要点の文章なら data-numbers="text" を section に付ける
const QUANTITY = /(\d[\d,.]*)\s*(百万円|万円|億円|円|%|％|時間|台|倍|件|人|名)/g;
function checkNumberCompare(model, t) {
  const out = [];
  for (const s of model.slides) {
    if (!isContentLayout(s) || s.numbers === 'visual' || s.numbers === 'text') continue;
    if (s.elements.some((e) => e.type === 'chart')) continue;
    const byUnit = {};
    for (const e of s.elements.filter((x) => x.type === 'text' && x.role !== 'caption' && !x.decor)) {
      for (const m of String(e.text || '').matchAll(QUANTITY)) (byUnit[m[2]] ||= new Set()).add(m[1]);
    }
    const hit = Object.entries(byUnit).find(([, v]) => v.size >= t.numberCompareMin);
    if (hit) out.push(viol('numberCompare', s, null, `同じ単位(${hit[0]})の数字が ${hit[1].size} 個ある。数字の比較はグラフで可視化する(図解で見せているなら data-numbers="visual"、比較でなければ data-numbers="text")`));
  }
  return out;
}

// 効果を謳う箇所は before/after で示す。タイトルが効果を謳うスライドに、「前」と「後」の対がなければ違反。
// 効果を謳わない文(タイトルの語がたまたま一致した場合)は data-effect="none" を section に付ける
const EFFECT_WORDS = /削減|短縮|向上|改善|増加|低減|軽減|回避|効果|圧縮|避け|減ら|増や/;
const BEFORE_WORDS = /(導入|移行|改善|施策|実施|変更|対策|開始|適用|統合)前|現状|現在|現行|従来|ビフォー|before/i;
const AFTER_WORDS = /(導入|移行|改善|施策|実施|変更|対策|開始|適用|統合)後|アフター|after|将来|今後/i;
function checkEffectBeforeAfter(model) {
  const out = [];
  for (const s of model.slides) {
    if (!isContentLayout(s) || s.effect === 'none') continue;
    const title = s.elements.find((e) => e.type === 'text' && e.role === 'title');
    if (!title || !EFFECT_WORDS.test(title.text || '')) continue;
    const words = s.elements.flatMap((e) => (e.type === 'text' ? [e.text || ''] : e.type === 'chart' && e.chart
      ? [...(e.chart.labels || []), ...(e.chart.series || []).map((x) => x.name)] : [])).join(' ');
    if (!(BEFORE_WORDS.test(words) && AFTER_WORDS.test(words))) {
      out.push(viol('effectBeforeAfter', s, title, '効果を謳っているのに、before/after の対がない。「導入前／導入後」「現状／移行後」のように前と後を並べて示す(効果を謳わない文なら data-effect="none")'));
    }
  }
  return out;
}

// グラフの内訳と差額: 内訳がある数字は積み上げで見せる。前後を比べるグラフは、差額の系列で差を見せる
const STACKED_FAMILY = ['stacked', 'stackedh', 'stacked100', 'area', 'cumulative'];
function checkChartBreakdown(model) {
  const out = [];
  for (const s of model.slides) {
    if (!isContentLayout(s) || s.breakdown === 'none') continue;
    const bodyText = s.elements.filter((e) => e.type === 'text' && e.role !== 'title').map((e) => e.text || '').join(' ');
    if (!/内訳/.test(bodyText)) continue;
    const flat = s.elements.find((e) => e.type === 'chart' && e.chart && !STACKED_FAMILY.includes(e.chart.type));
    if (flat) out.push(viol('chartBreakdown', s, flat, '「内訳」があるのに、グラフが積み上げになっていない。内訳は積み上げ棒(stacked・stackedh)の系列で見せる(内訳のないグラフなら data-breakdown="none")'));
  }
  return out;
}

function checkChartDiff(model) {
  const out = [];
  for (const s of model.slides) {
    if (!isContentLayout(s) || s.diff === 'none') continue;
    const note = s.elements.some((x) => x.type === 'text' && /差額|[▲△▼]\s*[\d,]+/.test(x.text || ''));
    for (const e of s.elements.filter((x) => x.type === 'chart' && x.chart)) {
      const labels = (e.chart.labels || []).join(' ');
      if (!(BEFORE_WORDS.test(labels) && AFTER_WORDS.test(labels))) continue;
      if (!note) out.push(viol('chartDiff', s, e, '前後を比べるグラフで、差額が数字で示されていない。差額を「▲5,800万円」のような注記(アクセント色)で、グラフの近くに書く。差額を実費と同じ見た目の棒や塊にしない(比べないグラフなら data-diff="none")'));
    }
  }
  return out;
}

function all(model, t) {
  return [...checkTitleAlign(model, t), ...checkMonotony(model, t), ...checkUsage(model, t), ...checkColorCount(model, t), ...checkAvoid(model, t), ...checkCardRow(model, t), ...checkArrowTarget(model, t), ...checkIsolation(model, t), ...checkZFlow(model, t), ...checkColorTone(model, t), ...checkNumberCompare(model, t), ...checkEffectBeforeAfter(model, t), ...checkChartBreakdown(model, t), ...checkChartDiff(model, t)];
}

module.exports = { all, checkTitleAlign, checkMonotony, checkUsage, checkColorCount, checkAvoid, checkCardRow, checkArrowTarget, checkIsolation, checkZFlow, checkColorTone, checkNumberCompare, checkEffectBeforeAfter, checkChartBreakdown, checkChartDiff };
