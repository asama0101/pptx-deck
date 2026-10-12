'use strict';
const fs = require('node:fs');
const JSZip = require('jszip');
const { XMLParser, XMLValidator } = require('fast-xml-parser');
const { emuToIn } = require('./lib/units');
const { runRules } = require('./rules');

const parser = new XMLParser({
  ignoreAttributes: false,
  attributeNamePrefix: '@_',
  parseTagValue: false,
  trimValues: false,
  isArray: (name) => ['p:sp', 'p:pic', 'p:cxnSp', 'p:graphicFrame', 'a:p', 'a:r'].includes(name),
});

const NAME = /^(s\d+-e\d+)\|p=([^|]*)\|d=(\d)\|r=([^|]*)\|t=(\w+)(\|o=1)?$/;
const alphaOf = (node) => {
  const a = node && node['a:solidFill'] && node['a:solidFill']['a:srgbClr'] && node['a:solidFill']['a:srgbClr']['a:alpha'];
  const v = a && a['@_val'] !== undefined ? Number(a['@_val']) / 100000 : null;
  return Number.isFinite(v) && v < 1 ? v : undefined;
};
const hexOf = (node) => {
  const v = node && node['a:solidFill'] && node['a:solidFill']['a:srgbClr'] && node['a:solidFill']['a:srgbClr']['@_val'];
  return v ? '#' + v.toUpperCase() : null;
};

function geometry(xfrm, off = 'a:off', ext = 'a:ext') {
  if (!xfrm) return { x: 0, y: 0, w: 0, h: 0 };
  return {
    x: emuToIn(Number(xfrm[off]['@_x'])), y: emuToIn(Number(xfrm[off]['@_y'])),
    w: emuToIn(Number(xfrm[ext]['@_cx'])), h: emuToIn(Number(xfrm[ext]['@_cy'])),
  };
}

function identity(cNvPr, fallbackId, fallbackType) {
  const m = NAME.exec((cNvPr && cNvPr['@_name']) || '');
  return m
    ? { id: m[1], parent: m[2] || null, decor: m[3] === '1', role: m[4], type: m[5], ...(m[6] ? { overlapOk: true } : {}) }
    : { id: fallbackId, parent: null, decor: false, role: '', type: fallbackType };
}

function readText(sp) {
  const paras = (sp['p:txBody'] && sp['p:txBody']['a:p']) || [];
  const runs = paras.flatMap((p) => p['a:r'] || []);
  const sizes = runs.map((r) => Number(r['a:rPr'] && r['a:rPr']['@_sz'] ? r['a:rPr']['@_sz'] : 1800) / 100);
  const text = paras.map((p) => (p['a:r'] || []).map((r) => (typeof r['a:t'] === 'string' ? r['a:t'] : '')).join('')).join('\n');
  const first = runs[0];
  return {
    text,
    fontPt: sizes.length ? Math.min(...sizes) : 0,
    color: first ? hexOf(first['a:rPr']) : null,
    bold: !!(first && first['a:rPr'] && first['a:rPr']['@_b'] === '1'),
  };
}

async function validatePackage(zip) {
  const errors = [];
  if (!zip.file('[Content_Types].xml')) errors.push('[Content_Types].xml がない');
  for (const name of Object.keys(zip.files)) {
    if (zip.files[name].dir || !/\.(xml|rels)$/.test(name)) continue;
    const xml = await zip.file(name).async('string');
    const r = XMLValidator.validate(xml);
    if (r !== true) errors.push(`${name}: XML が壊れている(${r.err.msg})`);
  }
  for (const name of Object.keys(zip.files).filter((n) => /^ppt\/charts\/chart\d+\.xml$/.test(n))) {
    const xml = await zip.file(name).async('string');
    // pptxgenjs は 2D のチャートにも 3 つ目(系列軸)の axId を宣言なしで書く。PowerPoint は問題なく開くので対象外とし、
    // 値軸・項目軸の 2 つ(各チャート要素の先頭 2 つ)が宣言されているかだけを見る
    const declared = [...xml.matchAll(/<c:(?:catAx|valAx|dateAx|serAx)>\s*<c:axId val="(\d+)"\/>/g)].map((m) => m[1]);
    const used = [];
    for (const g of xml.matchAll(/<c:(?:barChart|lineChart)>[\s\S]*?<\/c:(?:barChart|lineChart)>/g)) {
      used.push(...[...g[0].matchAll(/<c:axId val="(\d+)"\/>/g)].slice(0, 2).map((m) => m[1]));
    }
    const missing = used.filter((id) => !declared.includes(id));
    if (missing.length) errors.push(`${name}: 宣言のない軸 ID がある(${[...new Set(missing)].join(',')})。PowerPoint で開けなくなる`);
  }
  return errors;
}

async function readPptxModel(pptxPath) {
  if (!fs.existsSync(pptxPath)) throw new Error(`PPTX が見つからない: ${pptxPath}`);
  const zip = await JSZip.loadAsync(fs.readFileSync(pptxPath));
  const packageErrors = await validatePackage(zip);
  const pres = parser.parse(await zip.file('ppt/presentation.xml').async('string'));
  const sz = pres['p:presentation']['p:sldSz'];
  const slideNames = Object.keys(zip.files)
    .filter((n) => /^ppt\/slides\/slide\d+\.xml$/.test(n))
    .sort((a, b) => Number(a.match(/(\d+)\.xml$/)[1]) - Number(b.match(/(\d+)\.xml$/)[1]));
  const slides = [];
  for (const [i, name] of slideNames.entries()) {
    let doc;
    try { doc = parser.parse(await zip.file(name).async('string')); } catch (e) { packageErrors.push(`${name}: 解析できない`); continue; }
    const cSld = doc['p:sld']['p:cSld'];
    const tree = cSld['p:spTree'] || {};
    const bg = cSld['p:bg'] && cSld['p:bg']['p:bgPr'] ? hexOf(cSld['p:bg']['p:bgPr']) : null;
    const elements = [];
    let anon = 0;
    for (const sp of tree['p:sp'] || []) {
      const cNvPr = sp['p:nvSpPr']['p:cNvPr'];
      const id = identity(cNvPr, `s${i + 1}-x${++anon}`, 'shape');
      const spPr = sp['p:spPr'] || {};
      const body = readText(sp);
      elements.push({
        ...id, diagram: false, ...geometry(spPr['a:xfrm']),
        ...(id.type === 'text' ? { ...body, align: 'left', lineCount: 1, fixed: false, wrapStable: true, overflow: false } : { fill: hexOf(spPr), ...(alphaOf(spPr) !== undefined ? { fillAlpha: alphaOf(spPr) } : {}) }),
      });
    }
    for (const cx of tree['p:cxnSp'] || []) {
      const id = identity(cx['p:nvCxnSpPr']['p:cNvPr'], `s${i + 1}-x${++anon}`, 'line');
      elements.push({ ...id, type: 'line', diagram: false, ...geometry(cx['p:spPr']['a:xfrm']), stroke: hexOf(cx['p:spPr']['a:ln']) });
    }
    for (const pic of tree['p:pic'] || []) {
      const cNvPr = pic['p:nvPicPr']['p:cNvPr'];
      const id = identity(cNvPr, `s${i + 1}-x${++anon}`, 'image');
      elements.push({ ...id, type: 'image', diagram: false, ...geometry(pic['p:spPr']['a:xfrm']), alt: cNvPr['@_descr'] || '' });
    }
    for (const gf of tree['p:graphicFrame'] || []) {
      const id = identity(gf['p:nvGraphicFramePr']['p:cNvPr'], `s${i + 1}-x${++anon}`, 'chart');
      elements.push({ ...id, type: 'chart', role: '', diagram: false, ...geometry(gf['p:xfrm']), chart: { labelPt: 12 } });
    }
    slides.push({ index: i + 1, layout: 'content', bg: bg || '#FFFFFF', notes: '', elements });
  }
  const model = {
    slideW: emuToIn(Number(sz['@_cx'])), slideH: emuToIn(Number(sz['@_cy'])),
    fontFace: '', theme: { accent: '', neutral: '' }, slides,
  };
  return { model, packageErrors };
}

async function verifyPptx(pptxPath, thresholds) {
  const { model, packageErrors } = await readPptxModel(pptxPath);
  return { violations: runRules(model, thresholds, { stage: 'pptx' }), packageErrors, model };
}

module.exports = { readPptxModel, verifyPptx };
