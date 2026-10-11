'use strict';
function el(o = {}) {
  return Object.assign({
    id: 'e1', type: 'text', role: 'body', parent: null, decor: false, diagram: false,
    x: 1, y: 1, w: 3, h: 1, text: 'あ', fontPt: 16, color: '#1A1A1A', fill: null,
    align: 'left', lineCount: 1, fixed: false, wrapStable: true, overflow: false,
  }, o);
}
function slide(elements, o = {}) {
  return Object.assign({ index: 1, layout: 'content', bg: '#FFFFFF', notes: '', elements }, o);
}
function model(slides) {
  return { slideW: 13.333, slideH: 7.5, fontFace: 'BIZ UDPゴシック', theme: { accent: '#1F4E9C', neutral: '#BFBFBF' }, slides };
}
module.exports = { el, slide, model };
