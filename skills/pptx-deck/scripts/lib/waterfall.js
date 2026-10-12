'use strict';

// ウォーターフォール(増減の連なり)の棒の幾何。values は、合計の位置(totals。既定は先頭と末尾)では合計の値、他は増減の値。
// 合計は、それまでの増減の合計と一致していなければならない。累計は 0 を下回れない
function waterfallParts(values, totals) {
  const n = values.length;
  const tset = new Set(Array.isArray(totals) ? totals : [0, n - 1]);
  let run = 0;
  return values.map((v, i) => {
    if (tset.has(i)) {
      if (i > 0 && Math.abs(v - run) > 1e-9) throw new Error(`${i + 1} 番目の合計 ${v} が、それまでの増減の合計 ${run} と合わない`);
      run = v;
      return { kind: 'total', base: 0, size: v, top: v, run };
    }
    const next = run + v;
    if (next < 0) throw new Error(`${i + 1} 番目で累計が 0 を下回る(ウォーターフォールは 0 以上の範囲で書く)`);
    const part = { kind: v >= 0 ? 'up' : 'down', base: Math.min(run, next), size: Math.abs(v), top: Math.max(run, next), run: next, delta: v };
    run = next;
    return part;
  });
}

module.exports = { waterfallParts };
