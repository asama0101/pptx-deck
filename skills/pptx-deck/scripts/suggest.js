'use strict';
const TEXT_RULES = new Set(['overflow', 'bounds', 'wrapStable']);

function suggestFix(violations, attempt, t) {
  if (!violations.length) return { action: 'none', detail: '違反はない' };
  const hits = violations.filter((v) => TEXT_RULES.has(v.rule));
  if (!hits.length) return { action: 'manual', detail: `HTML のレイアウトを直す(対象ルール: ${[...new Set(violations.map((v) => v.rule))].join('、')})` };
  // 折り返しの不安定さだけが原因なら、行間は効かない。幅を広げる→フォント縮小の順にする
  if (hits.every((v) => v.rule === 'wrapStable')) {
    const wrapSteps = [
      { action: 'widenText', detail: 'テキストの幅を広げる(親の padding を減らす、gap を縮める)' },
      { action: 'shrinkFont', detail: `フォントを下げる。ただし本文 ${t.minFontPt.body}pt・注記 ${t.minFontPt.caption}pt の下限は割らない` },
    ];
    if (attempt < Math.min(t.maxFixAttempts, wrapSteps.length)) return wrapSteps[attempt];
    return {
      action: 'proposeSplitOrTrim',
      detail: '幅とフォントでは収まらない。文の短縮案(言い換え)をユーザーに示し、承認を得てから原稿を変える',
    };
  }
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
