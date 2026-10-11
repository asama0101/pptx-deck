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

function addChart(pres, slide, e, model) {
  const c = e.chart;
  const types = { bar: pres.charts.BAR, barh: pres.charts.BAR, line: pres.charts.LINE, pie: pres.charts.PIE };
  if (!types[c.type]) throw new Error(`チャートの型が未対応: ${c.type}`);
  const accent = hexNo(model.theme.accent);
  const neutral = hexNo(model.theme.neutral);
  const pt = c.labelPt || 12;
  const colors = c.type === 'line' ? [accent] : c.values.map((_, i) => (i === c.highlight ? accent : neutral));
  const base = {
    x: e.x, y: e.y, w: e.w, h: e.h, chartColors: colors,
    catAxisLabelFontFace: model.fontFace, valAxisLabelFontFace: model.fontFace,
    catAxisLabelFontSize: pt, valAxisLabelFontSize: pt,
    dataLabelFontFace: model.fontFace, dataLabelFontSize: pt, dataLabelColor: '333333',
    showLegend: c.type === 'pie', legendPos: 'r', legendFontFace: model.fontFace, legendFontSize: pt,
    valGridLine: { style: 'none' },
  };
  const data = [{ name: c.seriesName || '系列1', labels: c.labels, values: c.values }];
  if (c.type === 'bar' || c.type === 'barh') {
    slide.addChart(types[c.type], data, { ...base, barDir: c.type === 'barh' ? 'bar' : 'col', barGapWidthPct: 60, showValue: c.showValue !== false, dataLabelPosition: 'outEnd' });
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
