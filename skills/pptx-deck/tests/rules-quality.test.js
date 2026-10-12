'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { loadThresholds } = require('../scripts/lib/thresholds');
const q = require('../scripts/rules/quality');
const { runRules, summarize } = require('../scripts/rules');
const { el, slide, model } = require('./helpers/model');

const t = loadThresholds();
const title = (o = {}) => el({ id: 'title', role: 'title', fontPt: 28, x: 0.58, y: 0.42, w: 12.17, h: 0.6, ...o });

test('titleAlign: 表紙・章扉を除き、タイトル位置が揃わなければ違反', () => {
  const m = model([
    slide([title()], { index: 1, layout: 'cover' }),
    slide([title({ id: 't2' })], { index: 2 }),
    slide([title({ id: 't3', y: 0.9 })], { index: 3 }),
  ]);
  assert.deepEqual(q.checkTitleAlign(m, t).map((v) => v.id), ['t3']);
});

test('monotony: 同じレイアウトの3連続と、10枚以上で図解・グラフ不足を検出する', () => {
  const same = model([1, 2, 3].map((i) => slide([], { index: i, layout: 'content' })));
  assert.equal(q.checkMonotony(same, t).length, 1);
  const layouts = ['cover', 'content', 'diagram', 'content', 'chart', 'content', 'diagram', 'content', 'chart', 'closing'];
  assert.equal(q.checkMonotony(model(layouts.map((l, i) => slide([], { index: i + 1, layout: l }))), t).length, 0);
  const few = ['cover', 'content', 'section', 'content', 'diagram', 'content', 'section', 'content', 'content', 'closing'];
  const v = q.checkMonotony(model(few.map((l, i) => slide([], { index: i + 1, layout: l }))), t);
  assert.ok(v.some((x) => /図解かグラフ/.test(x.message)));
});

test('usage: 内容領域の使用率が 40〜85% の範囲外なら違反(表紙は除外)', () => {
  const empty = model([slide([el({ id: 'a', w: 2, h: 0.5 })])]);
  const good = model([slide([el({ id: 'a', type: 'shape', x: 0.5, y: 0.5, w: 10, h: 5 })])]);
  const full = model([slide([el({ id: 'a', type: 'shape', x: 0.4, y: 0.4, w: 12.5, h: 6.7 })])]);
  const cover = model([slide([el({ id: 'a', w: 2, h: 0.5 })], { layout: 'cover' })]);
  assert.equal(q.checkUsage(empty, t).length, 1);
  assert.equal(q.checkUsage(good, t).length, 0);
  assert.equal(q.checkUsage(full, t).length, 1);
  assert.equal(q.checkUsage(cover, t).length, 0);
});

test('colorCount: 有彩色の色相グループが2つ以上なら違反。同系色の濃淡は1つと数える', () => {
  const ok = model([slide([
    el({ id: 'a', color: '#1F4E9C' }), el({ id: 'b', type: 'shape', fill: '#E6EDF8' }), el({ id: 'c', type: 'shape', fill: '#F3F3F3' }),
  ])]);
  const ng = model([slide([el({ id: 'a', color: '#1F4E9C' }), el({ id: 'b', color: '#D9480F' })])]);
  assert.equal(q.checkColorCount(ok, t).length, 0);
  assert.equal(q.checkColorCount(ng, t).length, 1);
});

test('avoid: タイトル下の線・縦の装飾バー・センタリングした長い本文・末尾のピリオドを検出する', () => {
  const m = model([slide([
    title({ text: '結論です。' }),
    el({ id: 'underline', type: 'line', x: 0.58, y: 1.1, w: 5, h: 0, strokeW: 2, stroke: '#1F4E9C' }),
    el({ id: 'greyRule', type: 'line', x: 0.58, y: 1.15, w: 12, h: 0, strokeW: 1, stroke: '#D4D4D4' }),
    el({ id: 'bar', type: 'shape', fill: '#1F4E9C', x: 0.58, y: 2, w: 0.08, h: 2 }),
    el({ id: 'center', y: 4, align: 'center', lineCount: 3 }),
    el({ id: 'centerShort', y: 5.5, align: 'center', lineCount: 1 }),
  ])]);
  const rules = q.checkAvoid(m, t).map((v) => `${v.id}:${v.message.split(':')[0]}`).sort();
  assert.deepEqual(rules, ['bar:装飾バー', 'center:本文のセンタリング', 'title:タイトル末尾の句点', 'underline:タイトル下のアクセント色の線']);
});

test('runRules: stage により検査の範囲が変わる。空のモデルでも落ちない', () => {
  const m = model([slide([el({ id: 'x', overflow: true, w: 2, h: 0.5 })])]);
  assert.ok(runRules(m, t, { stage: 'html' }).some((v) => v.rule === 'overflow'));
  assert.ok(!runRules(m, t, { stage: 'pptx' }).some((v) => v.rule === 'overflow'));
  const tone = { ...model([]), theme: { accent: '#1F4E9C', neutral: '#BFBFBF', tone: 'trust' } };
  assert.deepEqual(runRules(tone, t), []);
  assert.deepEqual(summarize([{ rule: 'a', severity: 'error' }, { rule: 'a', severity: 'error' }, { rule: 'b', severity: 'warn' }]), { errors: 2, byRule: { a: 2, b: 1 } });
});

test('cardRow: 同じ大きさの四角の横並びは違反。図解の中・大きさや位置が違うものは対象外', () => {
  const card = (id, x, o = {}) => el({ id, type: 'shape', x, y: 2, w: 3.5, h: 3, ...o });
  const row = model([slide([card('a', 0.5), card('b', 4.5), card('c', 8.5)])]);
  assert.equal(q.checkCardRow(row, t).length, 1);
  const two = model([slide([card('a', 0.5), card('b', 4.5)])]);
  assert.equal(q.checkCardRow(two, t).length, 1);
  const inDiagram = model([slide([card('a', 0.5, { diagram: true }), card('b', 4.5, { diagram: true })])]);
  assert.equal(q.checkCardRow(inDiagram, t).length, 0);
  const stacked = model([slide([card('a', 0.5), card('b', 0.5, { y: 5.5, h: 1 })])]);
  assert.equal(q.checkCardRow(stacked, t).length, 0);
  const child = model([slide([card('a', 0.5), card('b', 4.5, { parent: 'a' })])]);
  assert.equal(q.checkCardRow(child, t).length, 0);
});

const accentText = (id, o = {}) => el({ id, color: '#1F4E9C', ...o });

test('arrowTarget: 先端に対象がない矢印は違反。対象があるもの・安全領域の端で終わるものは通る', () => {
  const arrow = (o = {}) => el({ id: 'ar', type: 'line', dir: 'right', arrow: true, x: 2, y: 2, w: 1, h: 0, ...o });
  const target = el({ id: 'tg', x: 3.2, y: 1.8, w: 2, h: 0.6 });
  const source = el({ id: 'src', x: 0.5, y: 1.8, w: 1.4, h: 0.6 });
  assert.equal(q.checkArrowTarget(model([slide([source, arrow(), target])]), t).length, 0);
  assert.equal(q.checkArrowTarget(model([slide([source, arrow()])]), t).length, 1);
  assert.equal(q.checkArrowTarget(model([slide([source, arrow({ x: 11.5, w: 1.3 })])]), t).length, 0);
  assert.equal(q.checkArrowTarget(model([slide([source, arrow({ arrow: false })])]), t).length, 0);
});

test('isolation: アクセント色が多すぎると違反。1 点なら通る', () => {
  const plain = (i) => el({ id: `p${i}`, y: 1 + i * 0.5 });
  const one = model([slide([accentText('a1'), ...[1, 2, 3, 4].map(plain)])]);
  assert.equal(q.checkIsolation(one, t).length, 0);
  const many = model([slide([accentText('a1'), accentText('a2', { y: 3 }), accentText('a3', { y: 4 }), plain(1), plain(2)])]);
  assert.equal(q.checkIsolation(many, t).length, 1);
  const cover = model([slide([accentText('a1'), accentText('a2', { y: 3 })], { layout: 'cover' })]);
  assert.equal(q.checkIsolation(cover, t).length, 0);
});

test('zFlow: 最大の強調が左上にある、または右下が空なら警告', () => {
  const topLeft = model([slide([accentText('a1', { x: 0.6, y: 1.5, w: 3, h: 1 }), el({ id: 'b', x: 8, y: 5, w: 4, h: 1 })])]);
  assert.deepEqual(q.checkZFlow(topLeft, t).map((v) => v.severity), ['warning']);
  const emptyBR = model([slide([accentText('a1', { x: 8, y: 1.5, w: 3, h: 1 }), el({ id: 'b', x: 1, y: 2, w: 3, h: 1 })])]);
  assert.equal(q.checkZFlow(emptyBR, t).length, 1);
  const ok = model([slide([accentText('a1', { x: 8, y: 5, w: 4, h: 1 }), el({ id: 'b', x: 1, y: 2, w: 3, h: 1 })])]);
  assert.equal(q.checkZFlow(ok, t).length, 0);
});

test('colorTone: トーン未指定は警告、色相が合わなければ error', () => {
  const m = (theme) => ({ ...model([]), theme: { accent: '#1F4E9C', neutral: '#BFBFBF', ...theme } });
  assert.equal(q.checkColorTone(m({}), t)[0].severity, 'warning');
  assert.deepEqual(q.checkColorTone(m({ tone: 'trust' }), t), []);
  assert.equal(q.checkColorTone(m({ tone: 'alert' }), t)[0].severity, 'error');
  assert.deepEqual(q.checkColorTone(m({ tone: 'alert', accent: '#C0392B' }), t), []);
  assert.deepEqual(q.checkColorTone(m({ tone: 'neutral' }), t), []);
  assert.equal(q.checkColorTone(m({ tone: 'zzz' }), t)[0].severity, 'error');
});

test('numberCompare: 同じ単位の数字が 3 つ以上あるのにチャートがなければ違反。チャート・data-numbers があれば通る', () => {
  const nums = ['3,200万円', '2,500万円', '2,200万円'].map((x, i) => el({ id: `n${i}`, y: 1 + i, text: x }));
  assert.equal(q.checkNumberCompare(model([slide(nums)]), t).length, 1);
  assert.equal(q.checkNumberCompare(model([slide([...nums, el({ id: 'c', type: 'chart', role: '', chart: { type: 'bar' } })])]), t).length, 0);
  assert.equal(q.checkNumberCompare(model([slide(nums, { numbers: 'visual' })]), t).length, 0);
  assert.equal(q.checkNumberCompare(model([slide(nums, { numbers: 'text' })]), t).length, 0);
  assert.equal(q.checkNumberCompare(model([slide(nums, { layout: 'cover' })]), t).length, 0);
  const mixed = ['3,200万円', '800台', '5年'].map((x, i) => el({ id: `m${i}`, y: 1 + i, text: x }));
  assert.equal(q.checkNumberCompare(model([slide(mixed)]), t).length, 0);
  const same = ['100万円', '100万円', '100万円'].map((x, i) => el({ id: `s${i}`, y: 1 + i, text: x }));
  assert.equal(q.checkNumberCompare(model([slide(same)]), t).length, 0);
});

test('effectBeforeAfter: 効果を謳うタイトルに、前と後の対がなければ違反', () => {
  const t1 = (text, o = {}) => el({ id: 'title', role: 'title', text, fontPt: 28, ...o });
  const txt = (id, text) => el({ id, text, y: 2 });
  assert.equal(q.checkEffectBeforeAfter(model([slide([t1('回答時間を半分に短縮できる'), txt('a', '見積を作る')])]), t).length, 1);
  assert.equal(q.checkEffectBeforeAfter(model([slide([t1('回答時間を半分に短縮できる'), txt('a', '導入前'), txt('b', '導入後')])]), t).length, 0);
  assert.equal(q.checkEffectBeforeAfter(model([slide([t1('費用を削減できる'), txt('a', '現状維持'), txt('b', '移行後')])]), t).length, 0);
  const chart = el({ id: 'c', type: 'chart', role: '', chart: { type: 'bar', labels: ['現状（5年）', '移行後（5年）'], values: [3, 0] } });
  assert.equal(q.checkEffectBeforeAfter(model([slide([t1('費用を削減できる'), chart])]), t).length, 0);
  assert.equal(q.checkEffectBeforeAfter(model([slide([t1('費用を削減できる'), txt('a', '見積')], { effect: 'none' })]), t).length, 0);
  assert.equal(q.checkEffectBeforeAfter(model([slide([t1('市場の見通し'), txt('a', '見積')])]), t).length, 0);
  assert.equal(q.checkEffectBeforeAfter(model([slide([t1('費用を削減できる')], { layout: 'cover' })]), t).length, 0);
});

test('chartBreakdown: 「内訳」があるのに積み上げでないグラフは違反', () => {
  const txt = el({ id: 'a', text: '内訳は次のとおり', y: 2 });
  const chart = (type, extra = {}) => el({ id: 'c', type: 'chart', role: '', chart: { type, labels: ['a'], values: [1], ...extra } });
  assert.equal(q.checkChartBreakdown(model([slide([txt, chart('bar')])]), t).length, 1);
  assert.equal(q.checkChartBreakdown(model([slide([txt, chart('stackedh', { series: [{ name: 'x', values: [1] }] })])]), t).length, 0);
  assert.equal(q.checkChartBreakdown(model([slide([txt, chart('bar')], { breakdown: 'none' })]), t).length, 0);
  assert.equal(q.checkChartBreakdown(model([slide([el({ id: 'b', text: '概要', y: 2 }), chart('bar')])]), t).length, 0);
});

test('chartDiff: 前後を比べるグラフは、差額を数字の注記で示す', () => {
  const chart = el({ id: 'c', type: 'chart', role: '', chart: { type: 'stacked', labels: ['現状維持', '移行後'], series: [{ name: '費用', values: [5, 0] }] } });
  const note = (text) => el({ id: 'n', text, y: 2 });
  assert.equal(q.checkChartDiff(model([slide([chart])]), t).length, 1);
  assert.equal(q.checkChartDiff(model([slide([chart, note('費用の説明')])]), t).length, 1);
  assert.equal(q.checkChartDiff(model([slide([chart, note('差額 ▲5,800万円')])]), t).length, 0);
  assert.equal(q.checkChartDiff(model([slide([chart, note('▲5,800万円')])]), t).length, 0);
  assert.equal(q.checkChartDiff(model([slide([chart], { diff: 'none' })]), t).length, 0);
  const other = el({ id: 'c', type: 'chart', role: '', chart: { type: 'bar', labels: ['A社', 'B社'], values: [1, 2] } });
  assert.equal(q.checkChartDiff(model([slide([other])]), t).length, 0);
});

const withTheme = (m, theme) => ({ ...m, theme: { accent: '#1F4E9C', neutral: '#BFBFBF', ...theme } });

test('colorCount: --accent2 があれば有彩色は 2 グループまで。--accent2 と違う色相は違反', () => {
  const two = model([slide([el({ id: 'a', color: '#1F4E9C' }), el({ id: 'b', type: 'shape', fill: '#B85A0B' }), el({ id: 'c', type: 'shape', fill: '#FDF0E1' })])]);
  assert.equal(q.checkColorCount(withTheme(two, { accent2: '#B85A0B' }), t).length, 0);
  assert.equal(q.checkColorCount(withTheme(two, {}), t).length, 1);
  const three = model([slide([el({ id: 'a', color: '#1F4E9C' }), el({ id: 'b', color: '#B85A0B' }), el({ id: 'c', color: '#2E7D4F' })])]);
  assert.equal(q.checkColorCount(withTheme(three, { accent2: '#B85A0B' }), t).length, 1);
  const wrong = model([slide([el({ id: 'a', color: '#1F4E9C' }), el({ id: 'b', color: '#2E7D4F' })])]);
  assert.match(q.checkColorCount(withTheme(wrong, { accent2: '#B85A0B' }), t)[0].message, /--accent2/);
});

test('isolation: --accent2 の強調も数える。薄色・中間色は数えない', () => {
  const plain = (i) => el({ id: `p${i}`, y: 1 + i * 0.5 });
  const mixed = withTheme(model([slide([accentText('a1'), accentText('a2', { y: 3, color: '#B85A0B' }), accentText('a3', { y: 4 }), plain(1), plain(2)])]), { accent2: '#B85A0B' });
  assert.equal(q.checkIsolation(mixed, t).length, 1);
  const tints = withTheme(model([slide([accentText('a1'), el({ id: 't1', type: 'shape', fill: '#E6EDF8', y: 3 }), el({ id: 't2', type: 'shape', fill: '#9DB8E3', y: 4 }), plain(1), plain(2), plain(3)])]), { accent2: '#B85A0B' });
  assert.equal(q.checkIsolation(tints, t).length, 0);
});

test('accent2Reco: 橙の要素があるのに推奨・承認・判断の語がないスライドは警告。共通の枠・語があれば通る', () => {
  const th = { accent2: '#B85A0B' };
  const orange = (o = {}) => accentText('o1', { color: '#B85A0B', text: '最優先の施策', ...o });
  const bad = withTheme(model([slide([orange()])]), th);
  const r = q.checkAccent2Reco(bad);
  assert.equal(r.length, 1);
  assert.equal(r[0].severity, 'warning');
  assert.equal(q.checkAccent2Reco(withTheme(model([slide([orange(), el({ id: 'k', y: 3, text: '推奨：A社' })])]), th)).length, 0);
  assert.equal(q.checkAccent2Reco(withTheme(model([slide([orange({ chrome: true })])]), th)).length, 0);
  assert.equal(q.checkAccent2Reco(withTheme(model([slide([orange()], { layout: 'cover' })]), th)).length, 0);
  assert.equal(q.checkAccent2Reco(model([slide([orange()])])).length, 0); // --accent2 がなければ対象外
});

test('colorTone: --accent2 の色相が基調に近いと警告', () => {
  assert.deepEqual(q.checkColorTone(withTheme(model([]), { tone: 'trust', accent2: '#B85A0B' }), t), []);
  const near = q.checkColorTone(withTheme(model([]), { tone: 'trust', accent2: '#2F6FBF' }), t);
  assert.equal(near.length, 1);
  assert.equal(near[0].severity, 'warning');
});

test('sourceMissing: 数字があるのに出典がないスライドは警告。出典があるもの・data-source="none" は通る', () => {
  const num = el({ id: 'n', text: '初期費用は3,200万円' });
  const src = el({ id: 's', role: 'caption', text: '出典：社内集計', y: 6 });
  assert.equal(q.checkSourceMissing(model([slide([num])]), t).length, 1);
  assert.equal(q.checkSourceMissing(model([slide([num])]), t)[0].severity, 'warning');
  assert.equal(q.checkSourceMissing(model([slide([num, src])]), t).length, 0);
  assert.equal(q.checkSourceMissing(model([slide([num], { source: 'none' })]), t).length, 0);
  assert.equal(q.checkSourceMissing(model([slide([el({ id: 'n', text: '方針を決める' })])]), t).length, 0);
  assert.equal(q.checkSourceMissing(model([slide([num], { layout: 'cover' })]), t).length, 0);
});

test('arrowTarget: 斜めの矢印は、終点(dr=右下、ur=右上、dl=左下、ul=左上)で判定する', () => {
  const target = el({ id: 'tg', x: 6, y: 1.5, w: 2, h: 1 });
  const diag = (dir, o = {}) => el({ id: 'ar', type: 'line', dir, arrow: true, x: 3, y: 1, w: 2.9, h: 1, ...o });
  // 右下へ向かう矢印の終点は (5.9, 2) で、対象(6〜8, 1.5〜2.5)に届く
  assert.equal(q.checkArrowTarget(model([slide([diag('dr'), target])]), t).length, 0);
  // 右上へ向かう矢印は、枠の右上が終点。y=1.5 に置けば終点 (5.9, 1.5) が対象に届く
  assert.equal(q.checkArrowTarget(model([slide([diag('ur', { y: 1.5 }), target])]), t).length, 0);
  assert.equal(q.checkArrowTarget(model([slide([diag('ur'), target])]), t).length, 1); // y=1 だと終点 (5.9, 1) は遠い
  // 左下へ向かう矢印の終点は (3, 2)。対象から遠いので違反
  assert.equal(q.checkArrowTarget(model([slide([diag('dl'), target])]), t).length, 1);
});
