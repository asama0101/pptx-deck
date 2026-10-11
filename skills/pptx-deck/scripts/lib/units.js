'use strict';
const PX_PER_IN = 96;
const SLIDE_W_IN = 13.333;
const SLIDE_H_IN = 7.5;
const pxToIn = (px) => px / PX_PER_IN;
const pxToPt = (px) => px * 0.75;
const emuToIn = (emu) => emu / 914400;
module.exports = { PX_PER_IN, SLIDE_W_IN, SLIDE_H_IN, pxToIn, pxToPt, emuToIn };
