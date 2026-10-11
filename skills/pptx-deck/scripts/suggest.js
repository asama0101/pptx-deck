'use strict';
const TEXT_RULES = new Set(['overflow', 'bounds', 'wrapStable']);

function suggestFix(violations, attempt, t) {
  if (!violations.length) return { action: 'none', detail: '違反はない' };
  const hits = violations.filter((v) => TEXT_RULES.has(v.rule));
  if (!hits.length) return { action: 'manual', detail: `HTML のレイアウトを直す(対象ルール: ${[...new Set(violations.map((v) => v.rule))].join('、')})` };
  const steps = [
    { action: 'reduceSpacing', detail: 'カードの padding と要素間の gap を縮める' },
    { action: 'tightenLineHeight', detail: 'line-height を 1.5 から 1.4 に下げる(下限 1.3)' },
    { action: 'shrinkFont', detail: `フォントを下げる。ただし本文 ${t.minFontPt.body}pt・注記 ${t.minFontPt.caption}pt の下限は割らない` },
  ];
  if (attempt < Math.min(t.maxFixAttempts, steps.length)) return steps[attempt];
  return {
    action: 'proposeSplitOrTrim',
    detail: `自動修正の上限(${t.maxFixAttempts} 回)に達した。スライドの分割案と文章の削減案をユーザーに示し、承認を得てから原稿を変える`,
  };
}

module.exports = { suggestFix };
