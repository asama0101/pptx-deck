'use strict';
const fs = require('node:fs');
const PptxGenJS = require('pptxgenjs');

const hexNo = (h) => (h || '#000000').replace('#', '').toUpperCase();
const objName = (e) => `${e.id}|p=${e.parent || ''}|d=${e.decor ? 1 : 0}|r=${e.role || ''}|t=${e.type}`;

function textRuns(e) {
  const out = [];
  e.paras.forEach((p, pi) => {
    const start = out.length;
    p.runs.forEach((r) => {
      if (r.br) {
        if (out.length > start) out[out.length - 1].options.breakLine = true;
        else out.push({ text: '', options: { breakLine: true } });
        return;
      }
      out.push({ text: r.text, options: { bold: !!r.bold, color: hexNo(r.color || e.color), fontSize: r.pt || e.fontPt } });
    });
    if (out.length === start) out.push({ text: '', options: {} });
    if (p.bullet) out[start].options.bullet = true;
    if (pi < e.paras.length - 1) out[out.length - 1].options.breakLine = true;
  });
  return out;
}

function addText(slide, e, model) {
  slide.addText(textRuns(e), {
    x: e.x, y: e.y, w: e.w, h: e.h, margin: 0,
    valign: e.valign || 'top', align: e.align || 'left',
    fontFace: model.fontFace, fontSize: e.fontPt, color: hexNo(e.color), bold: !!e.bold,
    lineSpacing: e.lineSpacingPt, paraSpaceAfter: e.paraSpaceAfter || 0,
    wrap: !e.fixed, fit: 'none', isTextBox: true, objectName: objName(e),
  });
}

function addShape(pres, slide, e) {
  const type = { rect: pres.shapes.RECTANGLE, roundRect: pres.shapes.ROUNDED_RECTANGLE, ellipse: pres.shapes.OVAL }[e.kind || 'rect'];
  slide.addShape(type, {
    x: e.x, y: e.y, w: e.w, h: e.h,
    fill: e.fill ? { color: hexNo(e.fill) } : { type: 'none' },
    line: e.stroke ? { color: hexNo(e.stroke), width: e.strokeW || 1 } : { type: 'none' },
    rectRadius: e.kind === 'roundRect' ? e.radius || 0.04 : undefined,
    objectName: objName(e),
  });
}

function addLine(pres, slide, e) {
  slide.addShape(pres.shapes.LINE, {
    x: e.x, y: e.y, w: e.w, h: e.h,
    flipH: e.dir === 'left', flipV: e.dir === 'up',
    line: { color: hexNo(e.stroke), width: e.strokeW || 1.5, endArrowType: e.arrow ? 'triangle' : undefined },
    objectName: objName(e),
  });
}

function addImage(slide, e) {
  if (!fs.existsSync(e.src)) throw new Error(`画像が見つからない: ${e.src}`);
  slide.addImage({ path: e.src, x: e.x, y: e.y, w: e.w, h: e.h, altText: e.alt || '', objectName: objName(e) });
}

// 累計の棒(cumulative): 各年の棒を「前年までの累計(無彩色)＋その年の増加分(アクセント色の塊)」に分ける。
// 合計と増加分の数字は、棒の位置から計算したテキストボックスで置く。位置を決めるため、プロット領域と軸の範囲を固定する
// (design/chart-preview.js の PLOT_CUM と同じ値)
const PLOT_CUM = { x: 0.03, y: 0.04, w: 0.94, h: 0.74 };
const CUM_AXIS_MARGIN = 1.15;

function cumulativeParts(values) {
  const base = values.map((v, i) => (i === 0 ? v : values[i - 1]));
  const inc = values.map((v, i) => (i === 0 ? 0 : v - values[i - 1]));
  return { base, inc };
}

// PPTX 側の検査が読める名前(s<スライド>-e<番号>)にする。他の要素の番号と重ならないよう 1000 以上にする
function noteId(id, i) {
  const m = /^(s\d+)-e(\d+)$/.exec(id);
  return m ? `${m[1]}-e${1000 + Number(m[2]) * 10 + i}` : `${id}-n${i}`;
}

function addCumulativeNotes(slide, e, model) {
  const c = e.chart;
  const n = c.values.length;
  const maxAxis = Math.max(...c.values) * CUM_AXIS_MARGIN;
  const catW = (PLOT_CUM.w * e.w) / n;
  const boxH = 0.07 * e.h;
  const top = (v) => e.y + (PLOT_CUM.y + PLOT_CUM.h * (1 - v / maxAxis)) * e.h;
  const { base, inc } = cumulativeParts(c.values);
  const put = (text, i, k, cx, y, color) => slide.addText(text, {
    x: cx - catW / 2, y, w: catW, h: boxH, margin: 0, valign: 'middle', align: 'center',
    fontFace: model.fontFace, fontSize: c.labelPt || 12, bold: true, color, isTextBox: true,
    objectName: `${noteId(e.id, i * 2 + k)}|p=|d=1|r=body|t=text`, // 装飾(重なり検査の対象外)
  });
  c.values.forEach((v, i) => {
    const cx = e.x + (PLOT_CUM.x + (PLOT_CUM.w * (i + 0.5)) / n) * e.w;
    put(v.toLocaleString('en-US'), i, 0, cx, top(v) - boxH - 0.005 * e.h, '333333');
    if (inc[i] > 0) put(`＋${inc[i].toLocaleString('en-US')}`, i, 1, cx, top(base[i] + inc[i] / 2) - boxH / 2, 'FFFFFF');
  });
}

function addChart(pres, slide, e, model) {
  const c = e.chart;
  const types = { bar: pres.charts.BAR, barh: pres.charts.BAR, line: pres.charts.LINE, pie: pres.charts.PIE, stacked: pres.charts.BAR, stackedh: pres.charts.BAR, stacked100: pres.charts.BAR, area: pres.charts.AREA, cumulative: pres.charts.BAR };
  if (!types[c.type]) throw new Error(`チャートの型が未対応: ${c.type}`);
  const accent = hexNo(model.theme.accent);
  const neutral = hexNo(model.theme.neutral);
  const pt = c.labelPt || 12;
  const stacked = ['stacked', 'stackedh', 'stacked100', 'area'].includes(c.type);
  // 積み上げ棒の系列色: 注目の系列だけアクセント、他は白文字が読める無彩色の濃淡(design/chart-preview.js と同じ)
  const SERIES_NEUTRALS = c.type === 'area' ? ['BFBFBF', 'D9D9D9', 'A6A6A6'] : ['767676', '595959', '404040'];
  let ni = 0;
  const colors = stacked
    ? c.series.map((_, i) => (i === c.highlight ? accent : SERIES_NEUTRALS[ni++ % SERIES_NEUTRALS.length]))
    : c.type === 'line' ? [accent] : c.values.map((_, i) => (i === c.highlight ? accent : neutral));
  const base = {
    x: e.x, y: e.y, w: e.w, h: e.h, chartColors: colors,
    catAxisLabelFontFace: model.fontFace, valAxisLabelFontFace: model.fontFace,
    catAxisLabelFontSize: pt, valAxisLabelFontSize: pt,
    dataLabelFontFace: model.fontFace, dataLabelFontSize: pt, dataLabelColor: '333333',
    showLegend: c.type === 'pie', legendPos: 'r', legendFontFace: model.fontFace, legendFontSize: pt,
    valGridLine: { style: 'none' },
  };
  const data = stacked
    ? c.series.map((x) => ({ name: x.name, labels: c.labels, values: x.values }))
    : [{ name: c.seriesName || '系列1', labels: c.labels, values: c.values }];
  if (c.type === 'cumulative') {
    const { base: baseV, inc } = cumulativeParts(c.values);
    slide.addChart(pres.charts.BAR, [
      { name: '前年までの累計', labels: c.labels, values: baseV },
      { name: 'その年の増加分', labels: c.labels, values: inc },
    ], {
      ...base, chartColors: ['BFBFBF', accent], layout: PLOT_CUM, barDir: 'col', barGrouping: 'stacked', barGapWidthPct: 50,
      showValue: false, showLegend: true, legendPos: 'b', dataBorder: { pt: 1.5, color: 'FFFFFF' }, valAxisHidden: true,
      valAxisMinVal: 0, valAxisMaxVal: Math.max(...c.values) * CUM_AXIS_MARGIN,
    });
    addCumulativeNotes(slide, e, model);
  } else if (c.type === 'area') {
    // 面グラフ: 新しく積み上がる領域(注目の系列)だけアクセント。値ラベルは出さない
    slide.addChart(types.area, data, { ...base, barGrouping: 'stacked', showValue: false, showLegend: true, legendPos: 'b', valAxisLabelColor: '555555', catAxisLabelColor: '555555' });
  } else if (stacked) {
    slide.addChart(types[c.type], data, {
      ...base, barDir: c.type === 'stackedh' ? 'bar' : 'col', barGrouping: c.type === 'stacked100' ? 'percentStacked' : 'stacked', barGapWidthPct: 50,
      showValue: c.showValue !== false, dataLabelPosition: 'ctr', dataLabelColor: 'FFFFFF', dataLabelFontBold: true,
      ...(c.type === 'stackedh' ? { catAxisOrientation: 'maxMin' } : {}), // 横の積み上げ棒も、先頭の項目を上にする
      showLegend: c.legend !== false, legendPos: 'b', dataBorder: { pt: 1.5, color: 'FFFFFF' }, valAxisHidden: true,
      dataLabelFormatCode: '#,##0;-#,##0;;', // 0 のセグメントのラベルは出さない
    });
  } else if (c.type === 'bar' || c.type === 'barh') {
    // 横棒は、先頭の項目を上にする(順位・ランキングが上から並ぶ)。値は棒の端のラベルで読めるので値軸は隠す
    const horizontal = c.type === 'barh';
    slide.addChart(types[c.type], data, {
      ...base, barDir: horizontal ? 'bar' : 'col', barGapWidthPct: 60, showValue: c.showValue !== false, dataLabelPosition: 'outEnd',
      ...(horizontal ? { catAxisOrientation: 'maxMin', valAxisHidden: true } : {}),
      valAxisMaxVal: Math.max(...c.values) * 1.2, // 棒の端のラベルが折り返さないよう、余白を取る
      valAxisMinVal: Math.min(0, ...c.values), // 0 を含む棒が、負の軸に伸びないようにする
    });
  } else if (c.type === 'line') {
    slide.addChart(types.line, data, { ...base, lineSize: 3, lineDataSymbolSize: 8, showValue: c.showValue !== false });
  } else {
    slide.addChart(types.pie, data, { ...base, showPercent: true, showValue: false });
  }
}

async function buildPptx(model, outPath) {
  const pres = new PptxGenJS();
  pres.layout = 'LAYOUT_WIDE';
  pres.theme = { headFontFace: model.fontFace, bodyFontFace: model.fontFace };
  for (const s of model.slides) {
    const slide = pres.addSlide();
    slide.background = { color: hexNo(s.bg) };
    if (s.notes && s.notes.trim()) slide.addNotes(s.notes.trim());
    for (const e of s.elements) {
      if (e.type === 'text') addText(slide, e, model);
      else if (e.type === 'shape') addShape(pres, slide, e);
      else if (e.type === 'line') addLine(pres, slide, e);
      else if (e.type === 'image') addImage(slide, e);
      else if (e.type === 'chart') addChart(pres, slide, e, model);
    }
  }
  await pres.writeFile({ fileName: outPath });
  return outPath;
}

module.exports = { buildPptx };
