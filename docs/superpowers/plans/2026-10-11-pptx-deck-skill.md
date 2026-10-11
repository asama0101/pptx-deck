# PPTX作成スキル（pptx-deck） Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** テーマまたは原稿から、編集可能で AI っぽくない .pptx を作る Claude Code スキル（プラグイン構成）を作る。

**Architecture:** 原稿(Markdown)→HTML プレビュー→PPTX の3段階。HTML は `pp-*` クラスだけを使う制限付きで、Playwright（Edge）で描画して DOM から位置・サイズ・フォント・色を計測し、中立な「要素モデル」(JSON) にする。同じルールエンジンを HTML 段階（DOM 由来のモデル）と PPTX 段階（生成後 XML を読み直したモデル）の両方に使う。要素モデルを pptxgenjs でネイティブの図形・テキスト・チャートに写し、LibreOffice で PDF→PNG に画像化して目視確認する。

**Tech Stack:** Node（v24 で確認済み、v20 以上）、pptxgenjs 4.0.1、playwright 1.49.1（Edge を `channel: 'msedge'` で使用）、jszip 3.10.1、fast-xml-parser 4.5.1、`node:test`、LibreOffice（推奨依存）、Python + PyMuPDF（PDF→PNG のみ）。

**Spec:** `docs/specs/2026-10-11_2215_pptx-skill-rev.md`（改訂版・正）。初版 `docs/specs/2026-10-11_2147_pptx-skill.md` は、改訂版と食い違う箇所だけ無効。

## Global Constraints

すべてのタスクに暗黙に適用する。値は SPEC からそのまま写した。

- 対象 OS は Windows のみ（Mac は対象外）。PowerShell など Windows 固有の機能を使ってよい。
- スライドサイズは 13.33×7.5in（16:9）。HTML 側は 1280×720px（96px = 1in、1px = 0.75pt）。
- フォントは BIZ UDPゴシック。未導入なら游ゴシック／メイリオ系に切り替えて再計測する。フォントは同梱しない。
- 配色は無彩色＋アクセント 1 色。サイズは、タイトル 24〜28pt、リード 18〜20pt、図解部 14〜16pt、本文 14pt 以上、注記・キャプション 10pt 以上。階層間は 4pt 以上差。
- 図解の型は 4 種（フロー、2×2 マトリクス、ピラミッド、ツリー）。HTML では「矩形・角丸矩形・円・直線矢印・テキスト」だけを使う。
- チャートは 3 種（棒の縦／横、折れ線、円）。PowerPoint のネイティブチャート。積み上げ棒・第 2 軸は作らない。
- テキストの折り返しは PowerPoint に任せる（余裕率 `wrapSafety`、初期値 0.92、Task 4 のスパイクで確定）。行間は pt 固定（`spcPts`）で写す。見出しだけ `data-fixed` で行を固定する。
- 本文を画像にしない。アイコンは画像化してよい。写真素材の自動入手はしない。
- 体裁チェックの合格基準: 安全マージン 0.4in、親の枠から 1pt 超のはみ出し、兄弟の重なり面積比 5% 超、本文 14pt 未満・注記 10pt 未満・チャート軸ラベル 10pt 未満、タイトルと本文の差 4pt 未満、コントラスト比 4.5:1 未満。
- 「AIっぽくない」の客観チェック: 同じレイアウトを 3 枚以上連続させない／10 枚以上では図解かグラフが 2 枚以上／内容領域の使用率 40〜85%／有彩色の色相グループが 1 つ以内／タイトル下のアクセント線・装飾バー・本文センタリング・タイトル末尾のピリオドを使わない。
- 自動修正は最大 3 回。超えたら停止し、分割案・削減案をユーザーに提示して承認を求める。原稿は承認なしで変えない。
- 依存はバージョン固定。ブラウザは Edge（Playwright の `channel: 'msedge'`）。
- ツールが作る一時ファイルは OS の一時フォルダ（`os.tmpdir()` / `fs.mkdtempSync`）に置く。承認対象の中間成果物（構成案・原稿・HTML・検査結果）だけ、利用者の作業フォルダ内 `deck-work/<名前>/` に置く。
- コメントとコミットメッセージは日本語。コミットメッセージの末尾に、環境が指定する `Co-Authored-By` / `Claude-Session` の行を付ける。
- テンプレ（.pptx/.potx）対応、既存 PPTX の修正、他形式からの変換、多役レビュー、複数プリセットは作らない（非目標）。

## Review Focus

SPEC が暗に求めるが、どのタスクの本線のテストも通らない入力・状態。可能性が高い順。各行のテストは、担当タスクの末尾ステップに入れてある。

1. `pp-*` 要素が 1 つもない空スライド、`section.slide` が 0 個の HTML。クラッシュせず、空のモデルか明示エラーになる（Task 8）。
2. 区切りのない長い英数字（URL など）が狭い枠からはみ出す。`overflow` 違反として検出される（Task 8）。
3. `data-chart` が壊れた JSON、または未対応の型（積み上げ棒など）。スライド番号つきの明示エラーで停止する（Task 8）。
4. 作業フォルダ名に日本語と空白が含まれる（`deck-work/日本語 名前/`）。計測・生成・画像化がすべて動く（Task 8、Task 11）。
5. Edge・LibreOffice・PyMuPDF・フォントのいずれかが未導入。`doctor` が原因と対処を示し、LibreOffice がなくても幾何検査だけで動く（Task 11）。

---

## File Structure

```
pptx-create/
├─ .claude-plugin/plugin.json            プラグインのメタ情報
├─ .gitignore
├─ README.md                              導入・使い方・注意（OneDrive の git など）
├─ docs/specs/…, docs/superpowers/plans/…
└─ skills/pptx-deck/
   ├─ SKILL.md                            Claude 向けの作業手順
   ├─ package.json                        依存を固定（node_modules はここに入る）
   ├─ config/thresholds.json              検査のしきい値（後から調整可）
   ├─ design/
   │  ├─ base.css                         既定デザインシステム（配色・フォント・サイズ階層・部品）
   │  ├─ chart-preview.js                 data-chart から SVG の近似プレビューを描く
   │  └─ catalog.html                     見本スライド 7 枚（表紙・内容・図解4種・チャート）。テストの固定入力も兼ねる
   ├─ scripts/
   │  ├─ run.js                           CLI（init / doctor / check / build / verify / render）
   │  ├─ doctor.js                        環境診断
   │  ├─ measure.js                       HTML → 要素モデル（Playwright/Edge）
   │  ├─ build.js                         要素モデル → PPTX（pptxgenjs）
   │  ├─ check-pptx.js                    PPTX(XML) → 要素モデル、パッケージ検査
   │  ├─ render.js                        PPTX → PDF → PNG（LibreOffice + PyMuPDF）
   │  ├─ pdf2png.py / pdf_lines.py        PyMuPDF の薄いラッパ
   │  ├─ suggest.js                       違反 → 自動修正の次の一手
   │  ├─ acceptance-check.js              受入条件の機械判定
   │  ├─ lib/{units,thresholds,color,fonts}.js
   │  ├─ rules/{geometry,quality,index}.js  検査ルール（モデルを入力とする純関数）
   │  └─ spike/wrap-spike.js              折り返しの実測スパイク
   ├─ samples/                            受入用の入力 3 種と期待枚数
   └─ tests/                              node:test。helpers/ と fixtures/ を含む
```

### 要素モデル（全タスク共通のデータ形式）

```js
// Model
{ slideW: 13.333, slideH: 7.5, fontFace: 'BIZ UDPゴシック', theme: { accent: '#1F4E9C', neutral: '#BFBFBF' },
  slides: [ Slide ] }
// Slide
{ index: 1, layout: 'cover'|'section'|'content'|'diagram'|'chart'|'closing', bg: '#FFFFFF', notes: '', elements: [ El ] }
// El（単位は inch / pt。座標はスライド左上が原点）
{ id: 's1-e3', type: 'text'|'shape'|'line'|'image'|'chart', role: 'title'|'lead'|'body'|'caption'|'icon'|'photo'|'',
  parent: 's1-e2'|null, decor: false, diagram: false, x, y, w, h,
  // text
  paras: [{ runs: [{ text, color, bold, pt, br? }], bullet: false }], text: '', fontPt: 16, color: '#1A1A1A', bold: false,
  align: 'left'|'center'|'right'|'justify', valign: 'top', lineSpacingPt: 24, paraSpaceAfter: 0, lineCount: 1,
  fixed: false, wrapStable: true, overflow: false,
  // shape
  kind: 'rect'|'roundRect'|'ellipse', fill: '#F3F3F3'|null, stroke: null, strokeW: 0, radius: 0.04,
  // line
  dir: 'right'|'left'|'down'|'up', arrow: false, stroke: '#555555', strokeW: 1.5,
  // image
  src: 'C:\\…\\x.png', alt: '',
  // chart
  chart: { type: 'bar'|'barh'|'line'|'pie', labels: [], values: [], highlight: 0, labelPt: 12 } }
```

違反（Violation）: `{ rule: string, slide: number|null, id: string|null, message: string, severity: 'error'|'warn' }`。

---

### Task 1: リポジトリの足場

**Files:**
- Create: `.gitignore`, `.claude-plugin/plugin.json`
- Create: `skills/pptx-deck/package.json`, `skills/pptx-deck/config/thresholds.json`
- Test: `skills/pptx-deck/tests/smoke.test.js`

**Interfaces:**
- Produces: `config/thresholds.json`（キーは次節のとおり。Task 2 の `loadThresholds` が読む）。`npm test` で全テストを走らせる。

- [ ] **Step 1: git リポジトリを初期化する**

Run（`C:\Users\sioay\OneDrive\github\pptx-create` で）:
```bash
git init
git branch -M main
```
Expected: `Initialized empty Git repository`。OneDrive 配下は同期競合で `.git` が壊れることがあるため、README に注意を書く（Task 12）。

- [ ] **Step 2: 設定ファイルを作る**

`.gitignore`:
```
node_modules/
deck-work/
__pycache__/
*.log
```

`.claude-plugin/plugin.json`:
```json
{
  "name": "pptx-deck",
  "version": "0.1.0",
  "description": "テーマまたは原稿から、編集可能で AI っぽくない PowerPoint (.pptx) を作る。Windows 専用。"
}
```

`skills/pptx-deck/package.json`:
```json
{
  "name": "pptx-deck",
  "version": "0.1.0",
  "private": true,
  "type": "commonjs",
  "engines": { "node": ">=20" },
  "dependencies": {
    "fast-xml-parser": "4.5.1",
    "jszip": "3.10.1",
    "playwright": "1.49.1",
    "pptxgenjs": "4.0.1"
  },
  "scripts": {
    "test": "node --test \"tests/**/*.test.js\""
  }
}
```

`skills/pptx-deck/config/thresholds.json`:
```json
{
  "safeMarginIn": 0.4,
  "childOverflowPt": 1,
  "overlapRatio": 0.05,
  "minFontPt": { "title": 24, "lead": 14, "body": 14, "caption": 10, "label": 10 },
  "hierarchyGapPt": 4,
  "contrastMin": 4.5,
  "wrapSafety": 0.92,
  "usage": { "min": 0.4, "max": 0.85 },
  "monotonyRun": 3,
  "diagramOrChartMinFor10Slides": 2,
  "titleAlignTolIn": 0.05,
  "maxFixAttempts": 3
}
```

- [ ] **Step 3: 失敗するスモークテストを書く**

`skills/pptx-deck/tests/smoke.test.js`:
```js
'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

test('固定した依存が読み込める', () => {
  for (const m of ['pptxgenjs', 'playwright', 'jszip', 'fast-xml-parser']) {
    assert.doesNotThrow(() => require(m), `${m} を読み込めない`);
  }
});

test('thresholds.json が妥当な JSON で、必須キーを持つ', () => {
  const t = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'config', 'thresholds.json'), 'utf8'));
  for (const k of ['safeMarginIn', 'overlapRatio', 'minFontPt', 'hierarchyGapPt', 'contrastMin', 'wrapSafety', 'usage', 'maxFixAttempts']) {
    assert.ok(k in t, `${k} がない`);
  }
  assert.equal(t.minFontPt.body, 14);
  assert.equal(t.minFontPt.caption, 10);
});
```

- [ ] **Step 4: 依存を入れずにテストを実行し、失敗を確認する**

Run: `cd skills/pptx-deck && node --test tests/smoke.test.js`
Expected: FAIL（`Cannot find module 'pptxgenjs'` など）

- [ ] **Step 5: 依存を入れてテストを通す**

Run: `cd skills/pptx-deck && npm install && node --test tests/smoke.test.js`
Expected: PASS（2 tests）。`package-lock.json` ができる。

- [ ] **Step 6: コミット**

```bash
git add .gitignore .claude-plugin skills/pptx-deck/package.json skills/pptx-deck/package-lock.json skills/pptx-deck/config skills/pptx-deck/tests docs
git commit -m "chore: リポジトリの足場と依存の固定"
```

---

### Task 2: 基盤ライブラリ（単位・しきい値・色・フォント）

**Files:**
- Create: `skills/pptx-deck/scripts/lib/units.js`, `thresholds.js`, `color.js`, `fonts.js`
- Test: `skills/pptx-deck/tests/lib.test.js`

**Interfaces:**
- Produces:
  - `units`: `PX_PER_IN = 96`, `SLIDE_W_IN = 13.333`, `SLIDE_H_IN = 7.5`, `pxToIn(px)`, `pxToPt(px)`, `emuToIn(emu)`
  - `thresholds`: `loadThresholds(overrides = {}) → object`（`config/thresholds.json` に深いマージ）
  - `color`: `parseCssColor(str) → { hex: '#RRGGBB', alpha: number } | null`、`contrastRatio(hexA, hexB) → number`、`hueInfo(hex) → { h, s, l }`（h は 0〜360、s・l は 0〜1）
  - `fonts`: `FONT_CANDIDATES`、`detectInstalledFonts() → string[]`、`pickFont(installed, candidates = FONT_CANDIDATES) → { name, fellBack }`（なければ throw）

- [ ] **Step 1: 失敗するテストを書く**

`skills/pptx-deck/tests/lib.test.js`:
```js
'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const u = require('../scripts/lib/units');
const { loadThresholds } = require('../scripts/lib/thresholds');
const { parseCssColor, contrastRatio, hueInfo } = require('../scripts/lib/color');
const { detectInstalledFonts, pickFont, FONT_CANDIDATES } = require('../scripts/lib/fonts');

test('単位: 96px = 1in、96px = 72pt、スライドは 13.333x7.5in', () => {
  assert.equal(u.pxToIn(96), 1);
  assert.equal(u.pxToPt(96), 72);
  assert.equal(u.pxToIn(1280).toFixed(3), '13.333');
  assert.equal(u.pxToIn(720), 7.5);
  assert.equal(u.emuToIn(914400), 1);
});

test('しきい値: 既定値を読み、深くマージして上書きできる', () => {
  const t = loadThresholds();
  assert.equal(t.safeMarginIn, 0.4);
  const o = loadThresholds({ minFontPt: { body: 16 }, overlapRatio: 0.1 });
  assert.equal(o.minFontPt.body, 16);
  assert.equal(o.minFontPt.caption, 10);
  assert.equal(o.overlapRatio, 0.1);
});

test('色: rgb/rgba を解析し、透明は alpha 0 で返す', () => {
  assert.deepEqual(parseCssColor('rgb(31, 78, 156)'), { hex: '#1F4E9C', alpha: 1 });
  assert.equal(parseCssColor('rgba(0, 0, 0, 0)').alpha, 0);
  assert.equal(parseCssColor('transparent'), null);
});

test('色: コントラスト比と色相', () => {
  assert.ok(Math.abs(contrastRatio('#000000', '#FFFFFF') - 21) < 0.01);
  assert.ok(contrastRatio('#CCCCCC', '#FFFFFF') < 2);
  const { h, s } = hueInfo('#1F4E9C');
  assert.ok(h > 210 && h < 225, `h=${h}`);
  assert.ok(s > 0.5);
  assert.equal(hueInfo('#808080').s, 0);
});

test('フォント: 候補の先頭から導入済みのものを選ぶ', () => {
  const c = ['BIZ UDPゴシック', 'Meiryo UI'];
  assert.deepEqual(pickFont(['Meiryo UI', 'BIZ UDPゴシック'], c), { name: 'BIZ UDPゴシック', fellBack: false });
  assert.deepEqual(pickFont(['Meiryo UI'], c), { name: 'Meiryo UI', fellBack: true });
  assert.throws(() => pickFont(['Arial'], c), /BIZ UDPゴシック/);
});

test('フォント: Windows の導入済みフォントを取得できる', () => {
  const fonts = detectInstalledFonts();
  assert.ok(fonts.length > 10);
  assert.ok(FONT_CANDIDATES.some((c) => fonts.includes(c)), '候補のどれも導入されていない');
});
```

- [ ] **Step 2: 失敗を確認する**

Run: `cd skills/pptx-deck && node --test tests/lib.test.js`
Expected: FAIL（`Cannot find module '../scripts/lib/units'`）

- [ ] **Step 3: 実装する**

`scripts/lib/units.js`:
```js
'use strict';
const PX_PER_IN = 96;
const SLIDE_W_IN = 13.333;
const SLIDE_H_IN = 7.5;
const pxToIn = (px) => px / PX_PER_IN;
const pxToPt = (px) => px * 0.75;
const emuToIn = (emu) => emu / 914400;
module.exports = { PX_PER_IN, SLIDE_W_IN, SLIDE_H_IN, pxToIn, pxToPt, emuToIn };
```

`scripts/lib/thresholds.js`:
```js
'use strict';
const fs = require('node:fs');
const path = require('node:path');

const FILE = path.join(__dirname, '..', '..', 'config', 'thresholds.json');

function merge(base, over) {
  const out = { ...base };
  for (const [k, v] of Object.entries(over || {})) {
    out[k] = v && typeof v === 'object' && !Array.isArray(v) && typeof base[k] === 'object' ? merge(base[k], v) : v;
  }
  return out;
}

function loadThresholds(overrides = {}) {
  return merge(JSON.parse(fs.readFileSync(FILE, 'utf8')), overrides);
}

module.exports = { loadThresholds };
```

`scripts/lib/color.js`:
```js
'use strict';

function parseCssColor(str) {
  const m = /rgba?\(([^)]+)\)/.exec(str || '');
  if (!m) return null;
  const p = m[1].split(',').map((s) => parseFloat(s));
  const hex = '#' + p.slice(0, 3).map((n) => Math.round(n).toString(16).padStart(2, '0')).join('').toUpperCase();
  return { hex, alpha: p.length > 3 ? p[3] : 1 };
}

function channels(hex) {
  return [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
}

function luminance(hex) {
  const [r, g, b] = channels(hex).map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrastRatio(a, b) {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

function hueInfo(hex) {
  const [r, g, b] = channels(hex);
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;
  const d = max - min;
  let h = 0;
  let s = 0;
  if (d > 0) {
    s = d / (1 - Math.abs(2 * l - 1));
    if (max === r) h = ((g - b) / d) % 6;
    else if (max === g) h = (b - r) / d + 2;
    else h = (r - g) / d + 4;
    h = (h * 60 + 360) % 360;
  }
  return { h, s, l };
}

module.exports = { parseCssColor, contrastRatio, hueInfo };
```

`scripts/lib/fonts.js`:
```js
'use strict';
const { execFileSync } = require('node:child_process');

const FONT_CANDIDATES = ['BIZ UDPゴシック', 'Yu Gothic UI', 'Meiryo UI', 'Yu Gothic', 'Meiryo', '游ゴシック', 'メイリオ'];

function detectInstalledFonts() {
  const script = '[Console]::OutputEncoding=[Text.Encoding]::UTF8; Add-Type -AssemblyName System.Drawing; ' +
    '(New-Object System.Drawing.Text.InstalledFontCollection).Families | ForEach-Object { $_.Name }';
  const out = execFileSync('powershell', ['-NoProfile', '-Command', script], { encoding: 'utf8' });
  return out.split(/\r?\n/).map((s) => s.trim()).filter(Boolean);
}

function pickFont(installed, candidates = FONT_CANDIDATES) {
  const name = candidates.find((c) => installed.includes(c));
  if (!name) throw new Error(`日本語フォントが見つからない。次のいずれかをインストールする: ${candidates.join('、')}`);
  return { name, fellBack: name !== candidates[0] };
}

module.exports = { FONT_CANDIDATES, detectInstalledFonts, pickFont };
```

- [ ] **Step 4: 通ることを確認する**

Run: `cd skills/pptx-deck && node --test tests/lib.test.js`
Expected: PASS（6 tests）

- [ ] **Step 5: コミット**

```bash
git add skills/pptx-deck/scripts/lib skills/pptx-deck/tests/lib.test.js
git commit -m "feat: 単位・しきい値・色・フォントの基盤ライブラリ"
```

---

### Task 3: 画像化（LibreOffice → PDF → PNG）

**Files:**
- Create: `skills/pptx-deck/scripts/render.js`, `scripts/pdf2png.py`, `scripts/pdf_lines.py`
- Test: `skills/pptx-deck/tests/render.test.js`

**Interfaces:**
- Consumes: なし
- Produces:
  - `findSoffice() → string | null`
  - `pythonCmd() → string`（環境変数 `PYTHON`、なければ `python`）
  - `renderPptx(pptxPath, outDir, { dpi = 80 } = {}) → { pdf: string, pngs: string[] }`（LibreOffice がなければ throw。180 秒で打ち切り、`soffice.bin` を強制終了する）
  - `pdfLineCounts(pdfPath) → number[]`（ページごとのテキスト行数。Task 4 のスパイクが使う）
- 前提: `pip install pymupdf`（PDF→PNG のみに使う。`doctor` が確認する）。LibreOffice は `soffice --version` が終了しないことがあるので、変換以外では起動しない。

- [ ] **Step 1: 失敗するテストを書く**

`skills/pptx-deck/tests/render.test.js`:
```js
'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const PptxGenJS = require('pptxgenjs');
const { findSoffice, renderPptx, pdfLineCounts } = require('../scripts/render');

const soffice = findSoffice();

test('LibreOffice を見つけられる（未導入ならこの環境ではスキップ）', { skip: !soffice }, () => {
  assert.ok(fs.existsSync(soffice));
});

test('PPTX を PDF と PNG にできる（日本語・空白を含むパスでも）', { skip: !soffice }, async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'pptx-deck-test-'));
  const work = path.join(dir, '日本語 フォルダ');
  fs.mkdirSync(work);
  const pres = new PptxGenJS();
  pres.layout = 'LAYOUT_WIDE';
  pres.addSlide().addText('画像化のテスト', { x: 1, y: 1, w: 5, h: 1, fontSize: 24, margin: 0 });
  pres.addSlide().addText('二枚目', { x: 1, y: 1, w: 5, h: 1, fontSize: 24, margin: 0 });
  const pptx = path.join(work, 'デッキ.pptx');
  await pres.writeFile({ fileName: pptx });
  const out = path.join(work, 'png');
  const r = renderPptx(pptx, out, { dpi: 60 });
  assert.ok(fs.existsSync(r.pdf));
  assert.equal(r.pngs.length, 2);
  for (const p of r.pngs) assert.ok(fs.statSync(p).size > 1000, `${p} が小さすぎる`);
  assert.deepEqual(pdfLineCounts(r.pdf), [1, 1]);
  fs.rmSync(dir, { recursive: true, force: true });
});

test('存在しない PPTX は分かりやすいエラーにする', { skip: !soffice }, () => {
  assert.throws(() => renderPptx('C:\\no\\such\\file.pptx', os.tmpdir()), /見つからない/);
});
```

- [ ] **Step 2: 失敗を確認する**

Run: `cd skills/pptx-deck && node --test tests/render.test.js`
Expected: FAIL（`Cannot find module '../scripts/render'`）

- [ ] **Step 3: 実装する**

`scripts/pdf2png.py`:
```python
import json
import sys

import pymupdf

pdf, out, dpi = sys.argv[1], sys.argv[2], int(sys.argv[3])
doc = pymupdf.open(pdf)
paths = []
for i, page in enumerate(doc, 1):
    p = f"{out}/slide-{i:02d}.png"
    page.get_pixmap(dpi=dpi).save(p)
    paths.append(p)
print(json.dumps(paths))
```

`scripts/pdf_lines.py`:
```python
import json
import sys

import pymupdf

doc = pymupdf.open(sys.argv[1])
counts = []
for page in doc:
    n = 0
    for b in page.get_text("dict")["blocks"]:
        if b.get("type") == 0:
            n += len(b["lines"])
    counts.append(n)
print(json.dumps(counts))
```

`scripts/render.js`:
```js
'use strict';
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { pathToFileURL } = require('node:url');

function findSoffice() {
  const cands = [
    process.env.SOFFICE_PATH,
    'C:\\Program Files\\LibreOffice\\program\\soffice.exe',
    'C:\\Program Files (x86)\\LibreOffice\\program\\soffice.exe',
  ].filter(Boolean);
  return cands.find((p) => fs.existsSync(p)) || null;
}

function pythonCmd() {
  return process.env.PYTHON || 'python';
}

function runPython(script, args) {
  const r = spawnSync(pythonCmd(), [path.join(__dirname, script), ...args], { encoding: 'utf8' });
  if (r.status !== 0) {
    throw new Error(`Python(${script}) が失敗した。PyMuPDF が必要: pip install pymupdf\n${r.stderr || r.error}`);
  }
  return JSON.parse(r.stdout);
}

function convertToPdf(pptxPath, outDir) {
  const soffice = findSoffice();
  if (!soffice) throw new Error('LibreOffice が見つからない。インストールするか、環境変数 SOFFICE_PATH を設定する');
  if (!fs.existsSync(pptxPath)) throw new Error(`PPTX が見つからない: ${pptxPath}`);
  fs.mkdirSync(outDir, { recursive: true });
  // 他のインスタンスとの衝突・ハングを避けるため、専用プロファイルを使う
  const profile = pathToFileURL(path.join(os.tmpdir(), 'pptx-deck-lo-profile')).href;
  const r = spawnSync(
    soffice,
    ['--headless', '--norestore', `-env:UserInstallation=${profile}`, '--convert-to', 'pdf', '--outdir', outDir, pptxPath],
    { encoding: 'utf8', timeout: 180000, killSignal: 'SIGKILL' },
  );
  if (r.error || r.status !== 0) {
    spawnSync('taskkill', ['/F', '/IM', 'soffice.bin'], { encoding: 'utf8' });
    throw new Error(`LibreOffice の変換に失敗した(180 秒で打ち切り): ${r.error ? r.error.message : r.stderr}`);
  }
  const pdf = path.join(outDir, path.basename(pptxPath).replace(/\.pptx$/i, '.pdf'));
  if (!fs.existsSync(pdf)) throw new Error(`PDF ができなかった: ${pdf}`);
  return pdf;
}

function renderPptx(pptxPath, outDir, { dpi = 80 } = {}) {
  const pdf = convertToPdf(pptxPath, outDir);
  const pngs = runPython('pdf2png.py', [pdf, outDir, String(dpi)]);
  return { pdf, pngs };
}

function pdfLineCounts(pdfPath) {
  return runPython('pdf_lines.py', [pdfPath]);
}

module.exports = { findSoffice, pythonCmd, renderPptx, pdfLineCounts };
```

- [ ] **Step 4: PyMuPDF を入れてテストを通す**

Run: `pip install pymupdf && cd skills/pptx-deck && node --test tests/render.test.js`
Expected: PASS（3 tests）。LibreOffice 未導入の環境では skip になる。

- [ ] **Step 5: コミット**

```bash
git add skills/pptx-deck/scripts/render.js skills/pptx-deck/scripts/pdf2png.py skills/pptx-deck/scripts/pdf_lines.py skills/pptx-deck/tests/render.test.js
git commit -m "feat: LibreOffice による PPTX の画像化"
```

---

### Task 4: スパイク — 日本語の折り返しを実測して `wrapSafety` を決める（ゲート）

HTML（Edge）の行数と、LibreOffice で描画した PPTX の行数を、日本語段落 10 種で比べる。結果で `wrapSafety` を確定する。**ここで方式が成立しなければ、以降のタスクに進まずユーザーに報告する。**

**Files:**
- Create: `skills/pptx-deck/scripts/spike/wrap-spike.js`
- Modify: `skills/pptx-deck/config/thresholds.json`（`wrapSafety`）

**Interfaces:**
- Consumes: `fonts.detectInstalledFonts/pickFont`、`render.renderPptx/pdfLineCounts`
- Produces: 標準出力に、段落ごとの行数の比較表と、推奨 `wrapSafety`（または「方式不成立」）。`spike-report.md` を OS の一時フォルダに保存する。

- [ ] **Step 1: スパイクスクリプトを書く**

`scripts/spike/wrap-spike.js`:
```js
'use strict';
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const PptxGenJS = require('pptxgenjs');
const { chromium } = require('playwright');
const { detectInstalledFonts, pickFont } = require('../lib/fonts');
const { renderPptx, pdfLineCounts } = require('../render');

const PARAS = [
  '売上は前年同期比で12%増加し、特に新規開拓の商談化率が1.8倍に改善しました。',
  '導入の目的は、属人化した見積業務を標準化し、回答までの時間を半分に短縮することです。',
  '「重要」な顧客ほど、担当者の異動時に関係が途切れやすい。（第2四半期の調査より）',
  '詳細は https://example.com/report/2026/q2/summary をご参照ください。',
  '2026年度第2四半期の営業レビュー：結論、課題、次の打ち手の順にまとめています。',
  'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 の英数字が連続して現れる場合の折り返し。',
  '、。」）といった行頭に置けない約物が、ちょうど行末に来る場合の処理を確認するための文章です。',
  '東京都港区芝公園四丁目二番八号東京タワーのふもとで、新製品の発表会を開催する予定です。',
  '短い文。',
  '本資料は、社内の営業担当者および関連部門の管理職を対象に、今期の重点施策と、その進め方、必要な支援の内容を、できるだけ具体的に示すことを目的としています。',
];
const FACTORS = [1, 0.96, 0.92, 0.88, 0.84, 0.8];
const BOX_IN = 4.0;
const FONT_PT = 16;
const LINE_PT = 24;

async function htmlLines(fontName, factor) {
  const browser = await chromium.launch({ channel: 'msedge' });
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
    const html = `<html lang="ja"><body style="margin:0">${PARAS.map((p, i) =>
      `<div id="p${i}" style="font-family:'${fontName}';font-size:${FONT_PT / 0.75}px;line-height:${LINE_PT / 0.75}px;width:${BOX_IN * 96 * factor}px">${p}</div>`).join('')}</body></html>`;
    await page.setContent(html);
    await page.evaluate(() => document.fonts.ready);
    return await page.evaluate((lh) => [...document.querySelectorAll('div')].map((d) => Math.round(d.getBoundingClientRect().height / lh)), LINE_PT / 0.75);
  } finally {
    await browser.close();
  }
}

async function main() {
  const font = pickFont(detectInstalledFonts()).name;
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'pptx-deck-spike-'));
  const pres = new PptxGenJS();
  pres.layout = 'LAYOUT_WIDE';
  for (const p of PARAS) {
    pres.addSlide().addText(p, { x: 1, y: 1, w: BOX_IN, h: 5, fontFace: font, fontSize: FONT_PT, lineSpacing: LINE_PT, margin: 0, valign: 'top', wrap: true });
  }
  const pptx = path.join(dir, 'spike.pptx');
  await pres.writeFile({ fileName: pptx });
  const { pdf } = renderPptx(pptx, path.join(dir, 'out'), { dpi: 60 });
  const lo = pdfLineCounts(pdf);

  const byFactor = {};
  for (const f of FACTORS) byFactor[f] = await htmlLines(font, f);

  const rows = PARAS.map((p, i) => `| ${i + 1} | ${p.length} | ${lo[i]} | ${FACTORS.map((f) => byFactor[f][i]).join(' | ')} |`);
  const under = FACTORS.map((f) => PARAS.filter((_, i) => byFactor[f][i] < lo[i]).length);
  const ok = FACTORS.filter((f, i) => under[i] === 0);
  const rec = ok.length ? Math.max(...ok.filter((f) => f <= 1)) : null;

  const report = [
    `フォント: ${font} / 枠幅 ${BOX_IN}in / ${FONT_PT}pt / 行間 ${LINE_PT}pt`,
    `| # | 文字数 | LibreOffice | ${FACTORS.map((f) => `HTML×${f}`).join(' | ')} |`,
    `|---|---|---|${FACTORS.map(() => '---').join('|')}|`,
    ...rows,
    `LibreOffice より行数が少なく見積もった段落数（係数ごと）: ${FACTORS.map((f, i) => `×${f}=${under[i]}`).join(' / ')}`,
    rec ? `推奨 wrapSafety: ${rec}（見積もり不足が 0 件になる最大の係数）` : '方式不成立: どの係数でも HTML が LibreOffice より行数を少なく見積もる。ユーザーに報告して方式を見直す',
  ].join('\n');
  fs.writeFileSync(path.join(dir, 'spike-report.md'), report);
  console.log(report);
  console.log(`\nレポート: ${path.join(dir, 'spike-report.md')}`);
  process.exitCode = rec ? 0 : 3;
}

main().catch((e) => { console.error(e); process.exit(1); });
```

- [ ] **Step 2: 実行する**

Run: `cd skills/pptx-deck && node scripts/spike/wrap-spike.js`
Expected: 比較表と `推奨 wrapSafety: <値>` が出る（終了コード 0）。

- [ ] **Step 3: ゲートを判定する**

- 推奨値が出た（終了コード 0）→ Step 4 へ。
- 「方式不成立」（終了コード 3）または推奨値が 0.80 の場合 → **ここで停止**し、比較表をユーザーに報告して方式の見直しを相談する。以降のタスクには進まない。
- 同時に確認する: LibreOffice の PDF のフォント名に `BIZ-UDPGothic` が含まれる（PPTX に日本語名「BIZ UDPゴシック」を書いて解決できている）。含まれなければ、PPTX に書くフォント名を英語名 `BIZ UDPGothic` に変えて再実行し、決まった表記を Task 9 の `model.fontFace` に反映する（`FONT_CANDIDATES` の先頭の表記も合わせる）。

- [ ] **Step 4: `wrapSafety` を確定する**

`config/thresholds.json` の `"wrapSafety"` を、Step 2 の推奨値に書き換える（0.92 のままなら変更なし）。

- [ ] **Step 5: コミット**

```bash
git add skills/pptx-deck/scripts/spike skills/pptx-deck/config/thresholds.json
git commit -m "feat: 折り返しの実測スパイクと wrapSafety の確定"
```

---

### Task 5: 検査ルール（幾何・画像・HTML 固有）

**Files:**
- Create: `skills/pptx-deck/scripts/rules/geometry.js`
- Create: `skills/pptx-deck/tests/helpers/model.js`
- Test: `skills/pptx-deck/tests/rules-geometry.test.js`

**Interfaces:**
- Consumes: `color.contrastRatio`、`loadThresholds`（テストのみ）
- Produces: `geometry.all(model, t) → Violation[]`（`bounds`, `overlap`, `minFont`, `hierarchy`, `contrast`, `images`）、`geometry.htmlOnly(model, t) → Violation[]`（`overflow`, `wrapStable`）。各関数は個別にも export: `checkBounds, checkOverlap, checkMinFont, checkHierarchy, checkContrast, checkImages, checkOverflow, checkWrapStable`。
- Produces（テスト用）: `tests/helpers/model.js` の `el(o)`, `slide(elements, o)`, `model(slides)`

- [ ] **Step 1: テスト用ヘルパとテストを書く**

`tests/helpers/model.js`:
```js
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
```

`tests/rules-geometry.test.js`:
```js
'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { loadThresholds } = require('../scripts/lib/thresholds');
const g = require('../scripts/rules/geometry');
const { el, slide, model } = require('./helpers/model');

const t = loadThresholds();
const ids = (v) => v.map((x) => x.id);

test('bounds: スライド外・安全マージン外・親の枠外を検出する', () => {
  const m = model([slide([
    el({ id: 'out', x: 12.5, w: 1.5 }),
    el({ id: 'edge', x: 0.1 }),
    el({ id: 'card', type: 'shape', x: 1, y: 1, w: 4, h: 2 }),
    el({ id: 'child', parent: 'card', x: 1.2, y: 1.2, w: 5, h: 0.5 }),
    el({ id: 'ok', x: 1, y: 4 }),
  ])]);
  const v = g.checkBounds(m, t);
  assert.deepEqual(ids(v).sort(), ['child', 'edge', 'out']);
});

test('bounds: 全面背景(decor かフルブリード図形)は対象外', () => {
  const m = model([slide([
    el({ id: 'bg', type: 'shape', x: 0, y: 0, w: 13.333, h: 7.5 }),
    el({ id: 'd', type: 'shape', decor: true, x: -1, y: 0, w: 1, h: 1 }),
  ])]);
  assert.equal(g.checkBounds(m, t).length, 0);
});

test('overlap: 兄弟の 5% 超の重なりを検出し、decor・線・親子は除外する', () => {
  const m = model([slide([
    el({ id: 'a', x: 1, y: 1, w: 3, h: 1 }),
    el({ id: 'b', x: 2, y: 1.2, w: 3, h: 1 }),
    el({ id: 'c', x: 1, y: 4, w: 3, h: 1 }),
    el({ id: 'dec', type: 'shape', decor: true, x: 1, y: 4, w: 3, h: 1 }),
    el({ id: 'ln', type: 'line', x: 1, y: 4.5, w: 3, h: 0 }),
    el({ id: 'card', type: 'shape', x: 6, y: 1, w: 4, h: 2 }),
    el({ id: 'inner', parent: 'card', x: 6.2, y: 1.2, w: 3, h: 1 }),
  ])]);
  assert.deepEqual(ids(g.checkOverlap(m, t)), ['b']);
});

test('minFont: 本文14pt未満・注記10pt未満・チャート軸ラベル10pt未満を検出する', () => {
  const m = model([slide([
    el({ id: 'body13', fontPt: 13 }),
    el({ id: 'body14', fontPt: 14, y: 2 }),
    el({ id: 'cap9', role: 'caption', fontPt: 9, y: 3 }),
    el({ id: 'cap10', role: 'caption', fontPt: 10, y: 4 }),
    el({ id: 'chart9', type: 'chart', chart: { labelPt: 9 }, y: 5 }),
  ])]);
  assert.deepEqual(ids(g.checkMinFont(m, t)).sort(), ['body13', 'cap9', 'chart9']);
});

test('hierarchy: タイトルと本文の差が4pt未満なら違反', () => {
  const bad = model([slide([el({ id: 't', role: 'title', fontPt: 20 }), el({ id: 'b', y: 3, fontPt: 18 })])]);
  const ok = model([slide([el({ id: 't', role: 'title', fontPt: 28 }), el({ id: 'b', y: 3, fontPt: 16 })])]);
  assert.deepEqual(ids(g.checkHierarchy(bad, t)), ['t']);
  assert.equal(g.checkHierarchy(ok, t).length, 0);
});

test('contrast: 薄い文字は違反、暗い背景の白文字は合格(親の塗りを背景とする)', () => {
  const m = model([slide([
    el({ id: 'pale', color: '#CCCCCC' }),
    el({ id: 'card', type: 'shape', fill: '#1F4E9C', x: 1, y: 4, w: 4, h: 2 }),
    el({ id: 'white', parent: 'card', color: '#FFFFFF', x: 1.2, y: 4.2, w: 3, h: 1 }),
  ])]);
  assert.deepEqual(ids(g.checkContrast(m, t)), ['pale']);
});

test('images: 代替テキストなしと、画像だけのスライドを検出する', () => {
  const m = model([
    slide([el({ id: 'img', type: 'image', role: 'icon', alt: '', x: 1, y: 1, w: 1, h: 1 })]),
    slide([el({ id: 'full', type: 'image', role: 'photo', alt: '全面画像', x: 0.5, y: 0.5, w: 12, h: 6.5 })], { index: 2 }),
  ]);
  const v = g.checkImages(m, t);
  assert.ok(v.some((x) => x.id === 'img' && x.rule === 'images'));
  assert.ok(v.some((x) => x.id === 'full' && /画像だけ/.test(x.message)));
});

test('htmlOnly: overflow と wrapStable=false を検出する', () => {
  const m = model([slide([
    el({ id: 'o', overflow: true }),
    el({ id: 'w', wrapStable: false, y: 2 }),
    el({ id: 'fixedOk', fixed: true, wrapStable: false, y: 3 }),
  ])]);
  assert.deepEqual(ids(g.htmlOnly(m, t)).sort(), ['o', 'w']);
});

test('all: 空のスライドでもクラッシュしない', () => {
  assert.deepEqual(g.all(model([slide([])]), t), []);
});
```

- [ ] **Step 2: 失敗を確認する**

Run: `cd skills/pptx-deck && node --test tests/rules-geometry.test.js`
Expected: FAIL（`Cannot find module '../scripts/rules/geometry'`）

- [ ] **Step 3: 実装する**

`scripts/rules/geometry.js`:
```js
'use strict';
const { contrastRatio } = require('../lib/color');

const PT_IN = 1 / 72;

function viol(rule, slide, el, message, severity = 'error') {
  return { rule, slide: slide ? slide.index : null, id: el ? el.id : null, message, severity };
}

function overlapArea(a, b) {
  const w = Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x);
  const h = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y);
  return w > 0 && h > 0 ? w * h : 0;
}

function checkBounds(model, t) {
  const out = [];
  const tol = t.childOverflowPt * PT_IN;
  const m = t.safeMarginIn;
  for (const s of model.slides) {
    const byId = new Map(s.elements.map((e) => [e.id, e]));
    for (const e of s.elements) {
      if (e.decor) continue;
      const right = e.x + e.w;
      const bottom = e.y + e.h;
      const fullBleed = e.type === 'shape' && e.x <= tol && e.y <= tol && right >= model.slideW - tol && bottom >= model.slideH - tol;
      if (fullBleed) continue;
      if (e.x < -tol || e.y < -tol || right > model.slideW + tol || bottom > model.slideH + tol) {
        out.push(viol('bounds', s, e, 'スライドの外にはみ出している'));
      } else if (e.x < m - tol || e.y < m - tol || right > model.slideW - m + tol || bottom > model.slideH - m + tol) {
        out.push(viol('bounds', s, e, `安全マージン(${m}in)の外にある`));
      }
      const p = e.parent ? byId.get(e.parent) : null;
      if (p && (e.x < p.x - tol || e.y < p.y - tol || right > p.x + p.w + tol || bottom > p.y + p.h + tol)) {
        out.push(viol('bounds', s, e, '親の枠からはみ出している'));
      }
    }
  }
  return out;
}

function checkOverlap(model, t) {
  const out = [];
  for (const s of model.slides) {
    const groups = new Map();
    for (const e of s.elements) {
      if (e.decor || e.type === 'line') continue;
      const k = e.parent || '';
      if (!groups.has(k)) groups.set(k, []);
      groups.get(k).push(e);
    }
    for (const list of groups.values()) {
      for (let i = 0; i < list.length; i++) {
        for (let j = i + 1; j < list.length; j++) {
          const a = list[i];
          const b = list[j];
          const area = overlapArea(a, b);
          const small = Math.min(a.w * a.h, b.w * b.h);
          if (area > 0 && small > 0 && area / small > t.overlapRatio) {
            out.push(viol('overlap', s, b, `${a.id} と重なっている(${Math.round((area / small) * 100)}%)`));
          }
        }
      }
    }
  }
  return out;
}

function checkMinFont(model, t) {
  const out = [];
  for (const s of model.slides) {
    for (const e of s.elements) {
      if (e.type === 'text' && e.text && e.text.trim()) {
        const min = t.minFontPt[e.role || 'body'] ?? t.minFontPt.body;
        if (e.fontPt + 1e-6 < min) out.push(viol('minFont', s, e, `${e.fontPt}pt は最小 ${min}pt(${e.role || 'body'})を下回る`));
      }
      if (e.type === 'chart' && e.chart && e.chart.labelPt + 1e-6 < t.minFontPt.label) {
        out.push(viol('minFont', s, e, `チャートのラベル ${e.chart.labelPt}pt は最小 ${t.minFontPt.label}pt を下回る`));
      }
    }
  }
  return out;
}

function checkHierarchy(model, t) {
  const out = [];
  for (const s of model.slides) {
    const title = s.elements.find((e) => e.type === 'text' && e.role === 'title');
    const others = s.elements.filter((e) => e.type === 'text' && (e.role === 'lead' || e.role === 'body'));
    if (!title || !others.length) continue;
    const top = Math.max(...others.map((e) => e.fontPt));
    if (title.fontPt - top < t.hierarchyGapPt - 1e-6) {
      out.push(viol('hierarchy', s, title, `タイトル ${title.fontPt}pt と本文 ${top}pt の差が ${t.hierarchyGapPt}pt 未満`));
    }
  }
  return out;
}

function checkContrast(model, t) {
  const out = [];
  for (const s of model.slides) {
    const byId = new Map(s.elements.map((e) => [e.id, e]));
    for (const e of s.elements) {
      if (e.decor || e.type !== 'text' || !e.text || !e.text.trim() || !e.color) continue;
      let bg = s.bg;
      let p = e.parent ? byId.get(e.parent) : null;
      while (p) {
        if (p.fill) { bg = p.fill; break; }
        p = p.parent ? byId.get(p.parent) : null;
      }
      const ratio = contrastRatio(e.color, bg);
      if (ratio < t.contrastMin) out.push(viol('contrast', s, e, `コントラスト比 ${ratio.toFixed(2)} は ${t.contrastMin} 未満(${e.color} on ${bg})`));
    }
  }
  return out;
}

function checkImages(model) {
  const out = [];
  const slideArea = model.slideW * model.slideH;
  for (const s of model.slides) {
    for (const e of s.elements) {
      if (e.type === 'image' && !(e.alt && e.alt.trim())) out.push(viol('images', s, e, '画像に代替テキスト(alt)がない'));
    }
    const hasText = s.elements.some((e) => e.type === 'text' && e.text && e.text.trim());
    const hasChart = s.elements.some((e) => e.type === 'chart');
    const big = s.elements.find((e) => e.type === 'image' && e.role !== 'icon' && (e.w * e.h) / slideArea >= 0.6);
    if (big && !hasText && !hasChart) out.push(viol('images', s, big, '画像だけのスライド(本文が画像になっている)'));
  }
  return out;
}

function checkOverflow(model) {
  const out = [];
  for (const s of model.slides) {
    for (const e of s.elements) if (e.overflow) out.push(viol('overflow', s, e, '内容が枠からあふれている'));
  }
  return out;
}

function checkWrapStable(model, t) {
  const out = [];
  for (const s of model.slides) {
    for (const e of s.elements) {
      if (e.type === 'text' && !e.fixed && e.wrapStable === false) {
        out.push(viol('wrapStable', s, e, `幅を ${Math.round(t.wrapSafety * 100)}% に狭めると行数が増える(PowerPoint で折り返しが変わる恐れ)`));
      }
    }
  }
  return out;
}

function all(model, t) {
  return [
    ...checkBounds(model, t), ...checkOverlap(model, t), ...checkMinFont(model, t),
    ...checkHierarchy(model, t), ...checkContrast(model, t), ...checkImages(model, t),
  ];
}

function htmlOnly(model, t) {
  return [...checkOverflow(model, t), ...checkWrapStable(model, t)];
}

module.exports = {
  all, htmlOnly, checkBounds, checkOverlap, checkMinFont, checkHierarchy, checkContrast, checkImages, checkOverflow, checkWrapStable,
};
```

- [ ] **Step 4: 通ることを確認する**

Run: `cd skills/pptx-deck && node --test tests/rules-geometry.test.js`
Expected: PASS（9 tests）

- [ ] **Step 5: コミット**

```bash
git add skills/pptx-deck/scripts/rules/geometry.js skills/pptx-deck/tests/helpers skills/pptx-deck/tests/rules-geometry.test.js
git commit -m "feat: 幾何・コントラスト・画像の検査ルール"
```

---

### Task 6: 品質ルール（AIっぽさ）・ルール統合・自動修正の提案

**Files:**
- Create: `skills/pptx-deck/scripts/rules/quality.js`, `scripts/rules/index.js`, `scripts/suggest.js`
- Test: `skills/pptx-deck/tests/rules-quality.test.js`, `tests/suggest.test.js`

**Interfaces:**
- Consumes: Task 5 の `geometry`、`color.hueInfo`、`tests/helpers/model.js`
- Produces:
  - `quality.all(model, t) → Violation[]`（`titleAlign`, `monotony`, `usage`, `colorCount`, `avoid`）。個別にも export: `checkTitleAlign, checkMonotony, checkUsage, checkColorCount, checkAvoid`
  - `runRules(model, t, { stage = 'html' } = {}) → Violation[]`（`'html'` は幾何＋品質＋HTML 固有、`'pptx'` は幾何のみ）
  - `summarize(violations) → { errors: number, byRule: { [rule]: number } }`
  - `suggestFix(violations, attempt, t) → { action, detail }`。`action` は `none | reduceSpacing | tightenLineHeight | shrinkFont | proposeSplitOrTrim | manual`

- [ ] **Step 1: 失敗するテストを書く**

`tests/rules-quality.test.js`:
```js
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
    el({ id: 'underline', type: 'line', x: 0.58, y: 1.1, w: 5, h: 0, strokeW: 2 }),
    el({ id: 'bar', type: 'shape', fill: '#1F4E9C', x: 0.58, y: 2, w: 0.08, h: 2 }),
    el({ id: 'center', y: 4, align: 'center', lineCount: 3 }),
    el({ id: 'centerShort', y: 5.5, align: 'center', lineCount: 1 }),
  ])]);
  const rules = q.checkAvoid(m, t).map((v) => `${v.id}:${v.message.split(':')[0]}`).sort();
  assert.deepEqual(rules, ['bar:装飾バー', 'center:本文のセンタリング', 'title:タイトル末尾の句点', 'underline:タイトル下のアクセント線']);
});

test('runRules: stage により検査の範囲が変わる。空のモデルでも落ちない', () => {
  const m = model([slide([el({ id: 'x', overflow: true, w: 2, h: 0.5 })])]);
  assert.ok(runRules(m, t, { stage: 'html' }).some((v) => v.rule === 'overflow'));
  assert.ok(!runRules(m, t, { stage: 'pptx' }).some((v) => v.rule === 'overflow'));
  assert.deepEqual(runRules(model([]), t), []);
  assert.deepEqual(summarize([{ rule: 'a', severity: 'error' }, { rule: 'a', severity: 'error' }, { rule: 'b', severity: 'warn' }]), { errors: 2, byRule: { a: 2, b: 1 } });
});
```

`tests/suggest.test.js`:
```js
'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { loadThresholds } = require('../scripts/lib/thresholds');
const { suggestFix } = require('../scripts/suggest');

const t = loadThresholds();
const over = [{ rule: 'overflow', severity: 'error', id: 'a', slide: 1, message: '' }];

test('suggestFix: 違反がなければ none', () => {
  assert.equal(suggestFix([], 0, t).action, 'none');
});

test('suggestFix: 余白 → 行間 → フォント縮小 → 分割・削減の提案の順に進む', () => {
  assert.equal(suggestFix(over, 0, t).action, 'reduceSpacing');
  assert.equal(suggestFix(over, 1, t).action, 'tightenLineHeight');
  assert.equal(suggestFix(over, 2, t).action, 'shrinkFont');
  const stop = suggestFix(over, 3, t);
  assert.equal(stop.action, 'proposeSplitOrTrim');
  assert.match(stop.detail, /承認/);
});

test('suggestFix: 本文量が原因でない違反は manual', () => {
  const v = [{ rule: 'overlap', severity: 'error', id: 'a', slide: 1, message: '' }];
  assert.equal(suggestFix(v, 0, t).action, 'manual');
});
```

- [ ] **Step 2: 失敗を確認する**

Run: `cd skills/pptx-deck && node --test tests/rules-quality.test.js tests/suggest.test.js`
Expected: FAIL（モジュールが見つからない）

- [ ] **Step 3: 実装する**

`scripts/rules/quality.js`:
```js
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

function coverage(slide, model, margin) {
  const step = 0.1;
  const x0 = margin;
  const y0 = margin;
  const cols = Math.floor((model.slideW - 2 * margin) / step);
  const rows = Math.floor((model.slideH - 2 * margin) / step);
  const rects = slide.elements.filter((e) => !e.decor && e.type !== 'line' && e.w > 0 && e.h > 0);
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
    const u = coverage(s, model, t.safeMarginIn);
    if (u < t.usage.min) out.push(viol('usage', s, null, `内容領域の使用率 ${Math.round(u * 100)}% が下限 ${t.usage.min * 100}% 未満(余白が無意味に大きい)`));
    else if (u > t.usage.max) out.push(viol('usage', s, null, `内容領域の使用率 ${Math.round(u * 100)}% が上限 ${t.usage.max * 100}% 超(詰め込み)`));
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
    if (title && /[。.]\s*$/.test(title.text || '')) out.push(viol('avoid', s, title, 'タイトル末尾の句点を付けない'));
    for (const e of s.elements) {
      const thin = Math.min(e.w, e.h) <= 0.08;
      if ((e.type === 'line' || e.type === 'shape') && thin && title && Math.max(e.w, e.h) >= 0.3 * title.w
          && e.y > title.y + title.h - 0.05 && e.y < title.y + title.h + 0.35 && e.x < title.x + title.w && e.x + e.w > title.x) {
        out.push(viol('avoid', s, e, 'タイトル下のアクセント線を使わない'));
      } else if (e.type === 'shape' && e.w <= 0.12 && e.h >= 0.8) {
        out.push(viol('avoid', s, e, '装飾バーを使わない'));
      }
      if (e.type === 'text' && e.role === 'body' && e.align === 'center' && e.lineCount > 2) {
        out.push(viol('avoid', s, e, '本文のセンタリングを避ける(3 行以上)'));
      }
    }
  }
  return out;
}

function all(model, t) {
  return [...checkTitleAlign(model, t), ...checkMonotony(model, t), ...checkUsage(model, t), ...checkColorCount(model, t), ...checkAvoid(model, t)];
}

module.exports = { all, checkTitleAlign, checkMonotony, checkUsage, checkColorCount, checkAvoid };
```

`scripts/rules/index.js`:
```js
'use strict';
const geometry = require('./geometry');
const quality = require('./quality');

function runRules(model, t, { stage = 'html' } = {}) {
  const v = [...geometry.all(model, t)];
  if (stage === 'html') v.push(...quality.all(model, t), ...geometry.htmlOnly(model, t));
  return v;
}

function summarize(violations) {
  const byRule = {};
  let errors = 0;
  for (const v of violations) {
    byRule[v.rule] = (byRule[v.rule] || 0) + 1;
    if (v.severity === 'error') errors++;
  }
  return { errors, byRule };
}

module.exports = { runRules, summarize };
```

`scripts/suggest.js`:
```js
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
```

- [ ] **Step 4: 通ることを確認する**

Run: `cd skills/pptx-deck && node --test tests/rules-quality.test.js tests/suggest.test.js`
Expected: PASS（6 + 3 tests）

- [ ] **Step 5: コミット**

```bash
git add skills/pptx-deck/scripts/rules skills/pptx-deck/scripts/suggest.js skills/pptx-deck/tests/rules-quality.test.js skills/pptx-deck/tests/suggest.test.js
git commit -m "feat: AIっぽさの品質ルール・ルール統合・自動修正の提案"
```

---

### Task 7: デザイン資産（base.css・チャートプレビュー・見本 catalog.html）

**Files:**
- Create: `skills/pptx-deck/design/base.css`, `design/chart-preview.js`, `design/catalog.html`
- Test: `skills/pptx-deck/tests/chart-preview.test.js`

**Interfaces:**
- Produces:
  - HTML 規約（Task 8 の `measure.js` と SKILL.md が前提とする）: スライドは `<section class="slide" data-layout="…">`（1280×720px）。要素は `pp-text`（`data-role` = title|lead|body|caption、`data-fixed` で行固定）、`pp-shape`、`pp-line`（`data-dir` = right|left|down|up、`data-arrow="end"`）、`pp-image`（`<img>`、`data-role` = icon|photo、`alt` 必須）、`pp-chart`（`data-chart` に JSON）。装飾は `data-decor`、図解の目印は `data-diagram`。ノートは `<aside class="notes">`。テキストは必ず幅を持たせる（ブロックとして親に stretch、または `width` 指定）。
  - CSS 変数: `--accent`、`--neutral-chart`、`--font-main`、`--pt`（= 1.33333px）。
  - `chartSvg(spec, w, h, theme) → string`（`spec` は `data-chart` の JSON。`theme = { accent, neutral }`）。ブラウザでは `.pp-chart[data-chart]` に SVG を差し込む。

- [ ] **Step 1: 失敗するテストを書く**

`tests/chart-preview.test.js`:
```js
'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { chartSvg } = require('../design/chart-preview');

const theme = { accent: '#1F4E9C', neutral: '#BFBFBF' };

test('棒グラフ: 値の数だけ rect を描き、注目データだけアクセント色にする', () => {
  const svg = chartSvg({ type: 'bar', labels: ['A', 'B', 'C'], values: [1, 2, 3], highlight: 2 }, 600, 400, theme);
  assert.match(svg, /^<svg/);
  assert.equal((svg.match(/<rect /g) || []).length, 3);
  assert.equal((svg.match(/#1F4E9C/g) || []).length, 1);
  assert.equal((svg.match(/#BFBFBF/g) || []).length, 2);
});

test('横棒・折れ線・円もそれぞれ SVG を返す', () => {
  const base = { labels: ['A', 'B'], values: [1, 3], highlight: 1 };
  assert.equal((chartSvg({ ...base, type: 'barh' }, 600, 400, theme).match(/<rect /g) || []).length, 2);
  assert.match(chartSvg({ ...base, type: 'line' }, 600, 400, theme), /<polyline/);
  assert.equal((chartSvg({ ...base, type: 'pie' }, 600, 400, theme).match(/<path /g) || []).length, 2);
});

test('未対応の型は明示エラー', () => {
  assert.throws(() => chartSvg({ type: 'stacked', labels: [], values: [] }, 100, 100, theme), /未対応/);
});
```

- [ ] **Step 2: 失敗を確認する**

Run: `cd skills/pptx-deck && node --test tests/chart-preview.test.js`
Expected: FAIL（`Cannot find module '../design/chart-preview'`）

- [ ] **Step 3: チャートプレビューを実装する**

`design/chart-preview.js`:
```js
(function (root) {
  'use strict';

  function color(spec, i, theme) {
    if (spec.type === 'line') return theme.accent;
    return spec.highlight === i ? theme.accent : theme.neutral;
  }

  function chartSvg(spec, w, h, theme) {
    const { type, labels, values } = spec;
    if (!['bar', 'barh', 'line', 'pie'].includes(type)) throw new Error(`チャートの型が未対応: ${type}`);
    const n = values.length;
    const max = Math.max(...values, 1);
    const font = 'font-family="sans-serif" font-size="14" fill="#555"';
    const pad = { l: 48, r: 24, t: 24, b: 40 };
    const iw = w - pad.l - pad.r;
    const ih = h - pad.t - pad.b;
    let body = '';
    if (type === 'bar') {
      const bw = iw / n;
      values.forEach((v, i) => {
        const bh = (v / max) * ih;
        body += `<rect x="${pad.l + i * bw + bw * 0.2}" y="${pad.t + ih - bh}" width="${bw * 0.6}" height="${bh}" fill="${color(spec, i, theme)}"/>`;
        body += `<text x="${pad.l + i * bw + bw / 2}" y="${h - 14}" text-anchor="middle" ${font}>${labels[i]}</text>`;
        body += `<text x="${pad.l + i * bw + bw / 2}" y="${pad.t + ih - bh - 6}" text-anchor="middle" ${font}>${v}</text>`;
      });
    } else if (type === 'barh') {
      const bh = ih / n;
      values.forEach((v, i) => {
        const bw = (v / max) * (iw - 40);
        body += `<rect x="${pad.l + 40}" y="${pad.t + i * bh + bh * 0.2}" width="${bw}" height="${bh * 0.6}" fill="${color(spec, i, theme)}"/>`;
        body += `<text x="${pad.l + 34}" y="${pad.t + i * bh + bh / 2 + 5}" text-anchor="end" ${font}>${labels[i]}</text>`;
        body += `<text x="${pad.l + 46 + bw}" y="${pad.t + i * bh + bh / 2 + 5}" ${font}>${v}</text>`;
      });
    } else if (type === 'line') {
      const pts = values.map((v, i) => `${pad.l + (i + 0.5) * (iw / n)},${pad.t + ih - (v / max) * ih}`);
      body += `<polyline points="${pts.join(' ')}" fill="none" stroke="${theme.accent}" stroke-width="3"/>`;
      values.forEach((v, i) => {
        body += `<circle cx="${pad.l + (i + 0.5) * (iw / n)}" cy="${pad.t + ih - (v / max) * ih}" r="5" fill="${theme.accent}"/>`;
        body += `<text x="${pad.l + (i + 0.5) * (iw / n)}" y="${h - 14}" text-anchor="middle" ${font}>${labels[i]}</text>`;
      });
    } else {
      const total = values.reduce((a, b) => a + b, 0) || 1;
      const cx = w / 2;
      const cy = h / 2;
      const r = Math.min(w, h) / 2 - 24;
      let a0 = -Math.PI / 2;
      values.forEach((v, i) => {
        const a1 = a0 + (v / total) * Math.PI * 2;
        const large = a1 - a0 > Math.PI ? 1 : 0;
        const p = (a) => `${cx + r * Math.cos(a)},${cy + r * Math.sin(a)}`;
        body += `<path d="M${cx},${cy} L${p(a0)} A${r},${r} 0 ${large} 1 ${p(a1)} Z" fill="${color(spec, i, theme)}" stroke="#fff" stroke-width="2"/>`;
        a0 = a1;
      });
    }
    return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">${body}</svg>`;
  }

  if (typeof module !== 'undefined' && module.exports) module.exports = { chartSvg };

  if (typeof document !== 'undefined') {
    document.addEventListener('DOMContentLoaded', function () {
      const cs = getComputedStyle(document.documentElement);
      const theme = { accent: cs.getPropertyValue('--accent').trim(), neutral: cs.getPropertyValue('--neutral-chart').trim() };
      document.querySelectorAll('.pp-chart[data-chart]').forEach(function (el) {
        try {
          const r = el.getBoundingClientRect();
          el.innerHTML = chartSvg(JSON.parse(el.getAttribute('data-chart')), Math.round(r.width), Math.round(r.height), theme);
        } catch (e) {
          el.textContent = 'チャートのプレビューを描けない: ' + e.message;
        }
      });
    });
  }
})(this);
```

- [ ] **Step 4: 通ることを確認する**

Run: `cd skills/pptx-deck && node --test tests/chart-preview.test.js`
Expected: PASS（3 tests）

- [ ] **Step 5: 既定デザインシステムを書く**

`design/base.css`:
```css
/* 既定デザインシステム: 無彩色 + アクセント1色。サイズはpt基準(--pt = 1pt のpx換算 ×(96/72)) */
:root {
  --pt: 1.33333px;
  --font-main: "BIZ UDPゴシック", "Yu Gothic UI", "Meiryo UI", sans-serif;
  --ink: #1A1A1A;
  --sub: #555555;
  --paper: #FFFFFF;
  --card: #F3F3F3;
  --accent: #1F4E9C;
  --accent-tint: #E6EDF8;
  --neutral-chart: #BFBFBF;
}
* { box-sizing: border-box; }
body { margin: 0; background: #7A7A7A; }
aside.notes { display: none; }

/* スライド: 1280x720px = 13.333x7.5in */
section.slide {
  position: relative; width: 1280px; height: 720px; margin: 24px auto;
  background: var(--paper); color: var(--ink); font-family: var(--font-main); overflow: hidden;
}
/* 本文領域(安全マージン 0.4in の内側)。area 自体は計測対象ではない */
.area { position: absolute; left: 56px; top: 144px; width: 1168px; height: 528px; }
.area.full { top: 56px; height: 608px; }
.row { display: flex; align-items: stretch; }

/* テキスト: 余白 0、行間は px 固定で計測される */
.pp-text { margin: 0; padding: 0; line-height: 1.5; }
.pp-text p, .pp-text li { margin: 0; }
.pp-text ul, .pp-text ol { margin: 0; padding-left: 1.2em; }
.pp-text[data-role="title"] { font-size: calc(28 * var(--pt)); font-weight: 700; line-height: 1.3; }
.pp-text[data-role="lead"] { font-size: calc(20 * var(--pt)); font-weight: 700; line-height: 1.4; }
.pp-text[data-role="body"] { font-size: calc(16 * var(--pt)); line-height: 1.5; }
.pp-text[data-role="caption"] { font-size: calc(11 * var(--pt)); color: var(--sub); line-height: 1.4; }
/* タイトルは常に同じ位置(titleAlign の対策) */
section.slide > .pp-text[data-role="title"] { position: absolute; left: 56px; top: 40px; width: 1168px; }

/* 図形 */
.pp-shape { border-radius: 4px; }
.card { background: var(--card); padding: 24px; border-radius: 4px; }
.card.accent { background: var(--accent); color: #FFFFFF; }
.card.tint { background: var(--accent-tint); }

/* 線: 横は border-top、縦は border-left で太さを持たせ、色は color で指定 */
.pp-line { color: var(--sub); flex: none; }
.pp-line[data-dir="right"], .pp-line[data-dir="left"] { height: 0; border-top: 2px solid currentColor; }
.pp-line[data-dir="up"], .pp-line[data-dir="down"] { width: 0; border-left: 2px solid currentColor; }

.pp-image { display: block; }
.pp-chart { display: block; }
```

- [ ] **Step 6: 見本スライド 7 枚を書く**

`design/catalog.html`:
```html
<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>見本カタログ</title>
<link rel="stylesheet" href="base.css">
<script src="chart-preview.js"></script>
</head>
<body>

<!-- 1. 表紙 -->
<section class="slide" data-layout="cover">
  <div class="area full" style="display:flex;flex-direction:column;justify-content:center">
    <p class="pp-text" data-role="title" data-fixed style="width:1000px;font-size:calc(40*var(--pt))">四半期の営業成果と<br>次の打ち手</p>
    <p class="pp-text" data-role="lead" style="width:1000px;margin-top:24px;font-weight:400;color:var(--sub)">2026年度 第2四半期 営業レビュー</p>
  </div>
  <aside class="notes">表紙。結論から話す前に、目的と所要時間を伝える。</aside>
</section>

<!-- 2. 内容(カード3枚) -->
<section class="slide" data-layout="content">
  <p class="pp-text" data-role="title">結論：新規開拓に人員を寄せると売上が最も伸びる</p>
  <div class="area row" style="gap:32px">
    <div class="pp-shape card" style="flex:1;height:360px">
      <p class="pp-text" data-role="lead">① 新規開拓</p>
      <p class="pp-text" data-role="body" style="margin-top:12px">商談化率が既存深耕の1.8倍。人員を2名追加して、訪問件数を増やす。</p>
    </div>
    <div class="pp-shape card" style="flex:1;height:360px">
      <p class="pp-text" data-role="lead">② 既存深耕</p>
      <p class="pp-text" data-role="body" style="margin-top:12px">解約率は低位で安定。定例訪問を月1回から四半期1回へ減らして負荷を下げる。</p>
    </div>
    <div class="pp-shape card accent" style="flex:1;height:360px">
      <p class="pp-text" data-role="lead">③ 見積業務</p>
      <p class="pp-text" data-role="body" style="margin-top:12px">テンプレ化で回答までの時間を半分にする。今期中に全拠点へ展開する。</p>
    </div>
  </div>
  <p class="pp-text" data-role="caption" style="position:absolute;left:56px;top:640px;width:1168px">出典：2026年度第2四半期 営業実績（社内集計）</p>
</section>

<!-- 3. 図解: フロー -->
<section class="slide" data-layout="diagram">
  <p class="pp-text" data-role="title">導入は4つのステップで進める</p>
  <div class="area row" data-diagram style="align-items:center;justify-content:space-between">
    <div class="pp-shape card" style="flex:none;width:248px;height:320px">
      <p class="pp-text" data-role="lead">1. 現状把握</p>
      <p class="pp-text" data-role="body" style="margin-top:12px">見積の流れと所要時間を計測する。</p>
    </div>
    <div class="pp-line" data-dir="right" data-arrow="end" style="width:36px"></div>
    <div class="pp-shape card" style="flex:none;width:248px;height:320px">
      <p class="pp-text" data-role="lead">2. 標準化</p>
      <p class="pp-text" data-role="body" style="margin-top:12px">項目と承認ルールを統一する。</p>
    </div>
    <div class="pp-line" data-dir="right" data-arrow="end" style="width:36px"></div>
    <div class="pp-shape card" style="flex:none;width:248px;height:320px">
      <p class="pp-text" data-role="lead">3. 試行</p>
      <p class="pp-text" data-role="body" style="margin-top:12px">2拠点で1か月運用し、課題を洗い出す。</p>
    </div>
    <div class="pp-line" data-dir="right" data-arrow="end" style="width:36px"></div>
    <div class="pp-shape card accent" style="flex:none;width:248px;height:320px">
      <p class="pp-text" data-role="lead">4. 全拠点展開</p>
      <p class="pp-text" data-role="body" style="margin-top:12px">研修とマニュアルを整えて展開する。</p>
    </div>
  </div>
</section>

<!-- 4. 図解: 2×2マトリクス -->
<section class="slide" data-layout="diagram">
  <p class="pp-text" data-role="title">優先度は「影響度×実現しやすさ」で決める</p>
  <div class="area" data-diagram style="display:grid;grid-template-columns:1fr 1fr;grid-template-rows:1fr 1fr;gap:24px;height:470px">
    <div class="pp-shape card"><p class="pp-text" data-role="lead">計画して進める</p><p class="pp-text" data-role="body" style="margin-top:8px">影響が大きく難しい。全拠点の見積システム統合。</p></div>
    <div class="pp-shape card accent"><p class="pp-text" data-role="lead">最優先で着手</p><p class="pp-text" data-role="body" style="margin-top:8px">影響が大きく容易。見積テンプレの標準化。</p></div>
    <div class="pp-shape card"><p class="pp-text" data-role="lead">後回しにする</p><p class="pp-text" data-role="body" style="margin-top:8px">影響が小さく難しい。旧帳票の完全な移行。</p></div>
    <div class="pp-shape card tint"><p class="pp-text" data-role="lead">すぐ片付ける</p><p class="pp-text" data-role="body" style="margin-top:8px">影響が小さく容易。入力項目の表記ゆれ修正。</p></div>
  </div>
  <p class="pp-text" data-role="caption" style="position:absolute;left:56px;top:632px;width:1168px">横軸：実現しやすさ（右ほど容易）／縦軸：影響度（上ほど大きい）</p>
</section>

<!-- 5. 図解: ピラミッド -->
<section class="slide" data-layout="diagram">
  <p class="pp-text" data-role="title">方針から実行まで、4つの階層で整理する</p>
  <div class="area" data-diagram style="display:flex;flex-direction:column;align-items:center;gap:12px">
    <div class="pp-shape card accent" style="width:360px;height:108px;display:flex;flex-direction:column;justify-content:center;padding:0 24px"><p class="pp-text" data-role="lead" style="text-align:center">ビジョン</p><p class="pp-text" data-role="body" style="text-align:center">目指す姿</p></div>
    <div class="pp-shape card tint" style="width:600px;height:108px;display:flex;flex-direction:column;justify-content:center;padding:0 24px"><p class="pp-text" data-role="lead" style="text-align:center">戦略</p><p class="pp-text" data-role="body" style="text-align:center">勝ち筋と重点領域</p></div>
    <div class="pp-shape card" style="width:840px;height:108px;display:flex;flex-direction:column;justify-content:center;padding:0 24px"><p class="pp-text" data-role="lead" style="text-align:center">施策</p><p class="pp-text" data-role="body" style="text-align:center">四半期ごとの打ち手と担当</p></div>
    <div class="pp-shape card" style="width:1080px;height:108px;display:flex;flex-direction:column;justify-content:center;padding:0 24px"><p class="pp-text" data-role="lead" style="text-align:center">日々の行動</p><p class="pp-text" data-role="body" style="text-align:center">訪問・提案・見積の実行と記録</p></div>
  </div>
</section>

<!-- 6. 図解: ツリー(絶対配置) -->
<section class="slide" data-layout="diagram">
  <p class="pp-text" data-role="title">営業組織は3つのチームで構成する</p>
  <div class="area" data-diagram>
    <div class="pp-shape card accent" style="position:absolute;left:384px;top:0;width:400px;height:130px"><p class="pp-text" data-role="lead">営業本部</p><p class="pp-text" data-role="body" style="margin-top:8px">全体の目標と配分を決める。</p></div>
    <div class="pp-line" data-dir="down" style="position:absolute;left:584px;top:130px;height:65px"></div>
    <div class="pp-line" data-dir="right" style="position:absolute;left:170px;top:195px;width:828px"></div>
    <div class="pp-line" data-dir="down" style="position:absolute;left:170px;top:195px;height:65px"></div>
    <div class="pp-line" data-dir="down" style="position:absolute;left:584px;top:195px;height:65px"></div>
    <div class="pp-line" data-dir="down" style="position:absolute;left:998px;top:195px;height:65px"></div>
    <div class="pp-shape card" style="position:absolute;left:0;top:260px;width:340px;height:240px"><p class="pp-text" data-role="lead">新規開拓チーム</p><p class="pp-text" data-role="body" style="margin-top:8px">新規顧客の発掘と初回提案。</p></div>
    <div class="pp-shape card" style="position:absolute;left:414px;top:260px;width:340px;height:240px"><p class="pp-text" data-role="lead">既存深耕チーム</p><p class="pp-text" data-role="body" style="margin-top:8px">既存顧客の継続と拡大。</p></div>
    <div class="pp-shape card" style="position:absolute;left:828px;top:260px;width:340px;height:240px"><p class="pp-text" data-role="lead">営業企画チーム</p><p class="pp-text" data-role="body" style="margin-top:8px">見積・資料・分析の支援。</p></div>
  </div>
</section>

<!-- 7. チャート -->
<section class="slide" data-layout="chart">
  <p class="pp-text" data-role="title">第4四半期の売上は年間で最大になった</p>
  <div class="pp-chart" data-chart='{"type":"bar","labels":["第1四半期","第2四半期","第3四半期","第4四半期"],"values":[120,135,128,172],"highlight":3,"labelPt":12}' style="position:absolute;left:56px;top:144px;width:740px;height:480px"></div>
  <div class="pp-shape card" style="position:absolute;left:828px;top:144px;width:396px;height:480px">
    <p class="pp-text" data-role="lead">ポイント</p>
    <p class="pp-text" data-role="body" style="margin-top:12px">第4四半期は前期比で+34%。新規開拓チームの大型案件2件が押し上げた。</p>
    <p class="pp-text" data-role="body" style="margin-top:12px">第1〜第3四半期は横ばい。第4四半期の水準を維持できるかが課題。</p>
  </div>
  <p class="pp-text" data-role="caption" style="position:absolute;left:56px;top:640px;width:1168px">単位：百万円。出典：社内集計</p>
</section>

</body>
</html>
```

- [ ] **Step 7: コミット**

```bash
git add skills/pptx-deck/design skills/pptx-deck/tests/chart-preview.test.js
git commit -m "feat: 既定デザインシステム・チャートプレビュー・見本カタログ"
```

見本カタログが全ルールに合格するかは、Task 8（計測）と Task 11（CLI の統合テスト）で確かめる。合格しないときは、**しきい値ではなくカタログ側を直す**。

---

### Task 8: HTML の計測（HTML → 要素モデル）

**Files:**
- Create: `skills/pptx-deck/scripts/measure.js`
- Create: `skills/pptx-deck/tests/helpers/fixture.js`, `tests/fixtures/basic.html`, `tests/fixtures/icon.svg`
- Test: `skills/pptx-deck/tests/measure.test.js`

**Interfaces:**
- Consumes: `units.SLIDE_W_IN/SLIDE_H_IN`、`design/base.css` の規約（Task 7）
- Produces: `measureHtml(htmlPath, { fontName, thresholds, channel, rasterDir }) → Promise<Model>`。`fontName` は CSS 変数 `--font-main` を上書きし、`model.fontFace` に入る。`thresholds.wrapSafety` で `wrapStable` を判定する。SVG の画像は Edge で PNG に落とし、`rasterDir`（なければ OS の一時フォルダ）に置く。
- Produces（テスト用）: `writeFixture(name, dir, extra = {}) → htmlPath`（`{{BASE_CSS}}`、`{{ICON}}` を絶対 URL に置換して `dir` に書く）

- [ ] **Step 1: フィクスチャとヘルパを書く**

`tests/fixtures/icon.svg`:
```xml
<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 48 48"><circle cx="24" cy="24" r="20" fill="#1F4E9C"/></svg>
```

`tests/fixtures/basic.html`:
```html
<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><link rel="stylesheet" href="{{BASE_CSS}}"></head><body>
<section class="slide" data-layout="content">
  <p class="pp-text" data-role="title">タイトルです</p>
  <div class="area">
    <div class="pp-shape card" style="width:500px;height:200px">
      <p class="pp-text" data-role="body">カード内の本文</p>
    </div>
    <div class="pp-line" data-dir="right" data-arrow="end" style="position:absolute;left:600px;top:50px;width:100px"></div>
    <img class="pp-image" data-role="icon" alt="アイコン" src="{{ICON}}" style="position:absolute;left:800px;top:20px;width:48px;height:48px">
    <div class="pp-chart" data-chart='{"type":"bar","labels":["A","B"],"values":[1,2],"highlight":1}' style="position:absolute;left:600px;top:150px;width:400px;height:250px"></div>
    <div class="pp-text" data-role="body" style="position:absolute;left:0;top:260px;width:500px"><ul><li>項目1</li><li><b>項目2</b>です</li></ul></div>
  </div>
  <aside class="notes">ノートの本文</aside>
</section>
</body></html>
```

`tests/helpers/fixture.js`:
```js
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

const FIX = path.join(__dirname, '..', 'fixtures');
const BASE_CSS = pathToFileURL(path.join(__dirname, '..', '..', 'design', 'base.css')).href;
const ICON = pathToFileURL(path.join(FIX, 'icon.svg')).href;

function writeFixture(name, dir, extra = {}) {
  let html = fs.readFileSync(path.join(FIX, `${name}.html`), 'utf8').replaceAll('{{BASE_CSS}}', BASE_CSS).replaceAll('{{ICON}}', ICON);
  for (const [k, v] of Object.entries(extra)) html = html.replaceAll(`{{${k}}}`, v);
  fs.mkdirSync(dir, { recursive: true });
  const out = path.join(dir, `${name}.html`);
  fs.writeFileSync(out, html);
  return out;
}

module.exports = { writeFixture };
```

- [ ] **Step 2: 失敗するテストを書く**

`tests/measure.test.js`:
```js
'use strict';
const { test, after } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { measureHtml } = require('../scripts/measure');
const { loadThresholds } = require('../scripts/lib/thresholds');
const { writeFixture } = require('./helpers/fixture');

const t = loadThresholds();
const root = fs.mkdtempSync(path.join(os.tmpdir(), 'pptx-deck-measure-'));
after(() => fs.rmSync(root, { recursive: true, force: true }));

function page(body, name) {
  const css = require('node:url').pathToFileURL(path.join(__dirname, '..', 'design', 'base.css')).href;
  const file = path.join(root, `${name}.html`);
  fs.writeFileSync(file, `<!doctype html><html lang="ja"><head><meta charset="utf-8"><link rel="stylesheet" href="${css}"></head><body>${body}</body></html>`);
  return file;
}

test('基本: 役割・親子・線・画像・チャート・ノート・箇条書きを要素モデルにする', async () => {
  const dir = path.join(root, '日本語 フォルダ'); // 日本語と空白を含むパス
  const m = await measureHtml(writeFixture('basic', dir), { fontName: 'BIZ UDPゴシック', thresholds: t, rasterDir: root });
  assert.equal(m.slides.length, 1);
  assert.equal(m.fontFace, 'BIZ UDPゴシック');
  assert.equal(m.theme.accent, '#1F4E9C');
  const s = m.slides[0];
  assert.equal(s.layout, 'content');
  assert.equal(s.notes.trim(), 'ノートの本文');
  const byRole = (r) => s.elements.filter((e) => e.role === r);
  const title = byRole('title')[0];
  assert.equal(title.fontPt, 28);
  assert.ok(Math.abs(title.x - 56 / 96) < 0.01 && Math.abs(title.y - 40 / 96) < 0.01);
  const card = s.elements.find((e) => e.type === 'shape');
  assert.equal(card.kind, 'roundRect');
  assert.equal(card.fill, '#F3F3F3');
  const inner = s.elements.find((e) => e.parent === card.id);
  assert.equal(inner.text, 'カード内の本文');
  const line = s.elements.find((e) => e.type === 'line');
  assert.equal(line.dir, 'right');
  assert.equal(line.arrow, true);
  assert.equal(line.h, 0);
  const img = s.elements.find((e) => e.type === 'image');
  assert.equal(img.alt, 'アイコン');
  assert.match(img.src, /\.png$/i);
  assert.ok(fs.existsSync(img.src));
  const chart = s.elements.find((e) => e.type === 'chart');
  assert.equal(chart.chart.type, 'bar');
  assert.equal(chart.chart.highlight, 1);
  assert.equal(chart.chart.labelPt, 12);
  const list = s.elements.find((e) => e.type === 'text' && e.paras && e.paras.length === 2);
  assert.ok(list.paras.every((p) => p.bullet));
  assert.equal(list.paras[1].runs.length, 2);
  assert.equal(list.paras[1].runs[0].bold, true);
});

test('wrapStable: 幅を 92% に狭めると行数が増える段落を検出する', async () => {
  const kanji = '春夏秋冬東西南北天地人山川海空風雨雪花'; // 20字。漢字は全角固定幅
  const file = page(
    `<section class="slide"><div class="pp-text" data-role="body" id="tight" style="position:absolute;left:56px;top:100px;width:214px">${kanji}</div>
     <div class="pp-text" data-role="body" id="loose" style="position:absolute;left:56px;top:300px;width:700px">${kanji}</div></section>`, 'wrap');
  const m = await measureHtml(file, { fontName: 'BIZ UDPゴシック', thresholds: t, rasterDir: root });
  const [tight, loose] = m.slides[0].elements;
  assert.equal(tight.wrapStable, false);
  assert.equal(loose.wrapStable, true);
});

test('overflow: 固定高の枠をあふれる内容と、区切りのない長い英数字を検出する', async () => {
  const file = page(
    `<section class="slide"><div class="pp-text" data-role="body" style="position:absolute;left:56px;top:100px;width:200px;height:40px">${'長い文章です。'.repeat(10)}</div>
     <div class="pp-text" data-role="body" style="position:absolute;left:56px;top:300px;width:120px">https://example.com/very/long/unbreakable/path/segment</div></section>`, 'overflow');
  const m = await measureHtml(file, { fontName: 'BIZ UDPゴシック', thresholds: t, rasterDir: root });
  assert.equal(m.slides[0].elements[0].overflow, true);
  assert.equal(m.slides[0].elements[1].overflow, true);
});

test('空のスライドは要素なしのモデル、スライドが無い HTML は明示エラー', async () => {
  const m = await measureHtml(page('<section class="slide" data-layout="section"></section>', 'empty'), { thresholds: t, rasterDir: root });
  assert.deepEqual(m.slides[0].elements, []);
  await assert.rejects(measureHtml(page('<p>スライドなし</p>', 'none'), { thresholds: t, rasterDir: root }), /section\.slide/);
});

test('data-chart が壊れた JSON、または未対応の型ならスライド番号つきで停止する', async () => {
  const bad = page('<section class="slide"><div class="pp-chart" data-chart="{oops" style="width:100px;height:100px"></div></section>', 'badjson');
  await assert.rejects(measureHtml(bad, { thresholds: t, rasterDir: root }), /スライド 1.*data-chart.*JSON/);
  const stacked = page(`<section class="slide"><div class="pp-chart" data-chart='{"type":"stacked","labels":["a"],"values":[1]}' style="width:100px;height:100px"></div></section>`, 'stacked');
  await assert.rejects(measureHtml(stacked, { thresholds: t, rasterDir: root }), /スライド 1.*未対応/);
});

test('スライドが 1280x720px でなければ明示エラー', async () => {
  await assert.rejects(measureHtml(page('<section class="slide" style="width:800px"></section>', 'size'), { thresholds: t, rasterDir: root }), /1280x720/);
});
```

- [ ] **Step 3: 失敗を確認する**

Run: `cd skills/pptx-deck && node --test tests/measure.test.js`
Expected: FAIL（`Cannot find module '../scripts/measure'`）

- [ ] **Step 4: 実装する**

`scripts/measure.js`:
```js
'use strict';
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { pathToFileURL, fileURLToPath } = require('node:url');
const { chromium } = require('playwright');
const { SLIDE_W_IN, SLIDE_H_IN } = require('./lib/units');

const CHART_TYPES = ['bar', 'barh', 'line', 'pie'];

// ブラウザ内で実行される。外側のスコープを参照しないこと。
function extractInPage({ safety }) {
  const PX = 96;
  const TYPES = ['pp-text', 'pp-shape', 'pp-line', 'pp-image', 'pp-chart'];
  const toHex = (c) => {
    const m = /rgba?\(([^)]+)\)/.exec(c || '');
    if (!m) return null;
    const p = m[1].split(',').map((s) => parseFloat(s));
    if (p.length > 3 && p[3] === 0) return null;
    return '#' + p.slice(0, 3).map((n) => Math.round(n).toString(16).padStart(2, '0')).join('').toUpperCase();
  };
  const r2 = (n) => Math.round(n * 100) / 100;
  const r4 = (n) => Math.round(n * 10000) / 10000;

  const collectRuns = (src) => {
    const runs = [];
    const walk = (node) => {
      node.childNodes.forEach((ch) => {
        if (ch.nodeType === 3) {
          const text = ch.textContent.replace(/\s+/g, ' ');
          if (!text.trim() && !runs.length) return;
          const pcs = getComputedStyle(ch.parentElement);
          runs.push({ text, color: toHex(pcs.color), bold: parseInt(pcs.fontWeight, 10) >= 600, pt: r2(parseFloat(pcs.fontSize) * 0.75) });
        } else if (ch.nodeType === 1) {
          if (ch.tagName === 'BR') runs.push({ text: '', br: true });
          else if (ch.tagName !== 'UL' && ch.tagName !== 'OL') walk(ch);
        }
      });
    };
    walk(src);
    while (runs.length && !runs[runs.length - 1].br && !runs[runs.length - 1].text.trim()) runs.pop();
    if (runs.length && !runs[0].br) runs[0].text = runs[0].text.replace(/^\s+/, '');
    if (runs.length && !runs[runs.length - 1].br) runs[runs.length - 1].text = runs[runs.length - 1].text.replace(/\s+$/, '');
    return runs;
  };

  const root = getComputedStyle(document.documentElement);
  const theme = {
    accent: root.getPropertyValue('--accent').trim().toUpperCase(),
    neutral: root.getPropertyValue('--neutral-chart').trim().toUpperCase(),
  };
  const slides = [];
  document.querySelectorAll('section.slide').forEach((sec, si) => {
    const sr = sec.getBoundingClientRect();
    const slide = {
      index: si + 1,
      layout: sec.dataset.layout || 'content',
      bg: toHex(getComputedStyle(sec).backgroundColor) || '#FFFFFF',
      notes: (sec.querySelector('aside.notes') || {}).textContent || '',
      size: [Math.round(sr.width), Math.round(sr.height)],
      elements: [],
    };
    const nodes = [...sec.querySelectorAll(TYPES.map((c) => '.' + c).join(','))];
    const ids = new Map();
    nodes.forEach((el, i) => {
      const id = `s${si + 1}-e${i + 1}`;
      ids.set(el, id);
      el.setAttribute('data-pp-id', id);
    });
    nodes.forEach((el) => {
      const cs = getComputedStyle(el);
      const r = el.getBoundingClientRect();
      const type = TYPES.find((c) => el.classList.contains(c)).slice(3);
      let parent = null;
      for (let p = el.parentElement; p && p !== sec; p = p.parentElement) {
        if (ids.has(p)) { parent = ids.get(p); break; }
      }
      const e = {
        id: ids.get(el), type, role: el.dataset.role || (type === 'text' ? 'body' : ''), parent,
        decor: el.hasAttribute('data-decor'), diagram: !!el.closest('[data-diagram]'),
        x: r4((r.left - sr.left) / PX), y: r4((r.top - sr.top) / PX), w: r4(r.width / PX), h: r4(r.height / PX),
      };
      if (type === 'text') {
        const blocks = [...el.querySelectorAll(':scope > p, :scope > li, :scope > ul > li, :scope > ol > li')];
        const sources = blocks.length ? blocks : [el];
        e.paras = sources.map((src) => ({ runs: collectRuns(src), bullet: src.tagName === 'LI' }));
        e.text = e.paras.map((p) => p.runs.map((x) => (x.br ? '\n' : x.text)).join('')).join('\n');
        const sizes = e.paras.flatMap((p) => p.runs.filter((x) => !x.br).map((x) => x.pt));
        e.fontPt = sizes.length ? Math.min(...sizes) : r2(parseFloat(cs.fontSize) * 0.75);
        const first = e.paras.flatMap((p) => p.runs).find((x) => !x.br);
        e.color = (first && first.color) || toHex(cs.color);
        e.bold = !!(first && first.bold);
        e.align = { start: 'left', end: 'right' }[cs.textAlign] || cs.textAlign;
        e.valign = el.dataset.valign || 'top';
        const lh = parseFloat(cs.lineHeight);
        const lhPx = Number.isFinite(lh) ? lh : parseFloat(cs.fontSize) * 1.3;
        e.lineSpacingPt = r2(lhPx * 0.75);
        e.paraSpaceAfter = blocks.length ? r2(parseFloat(getComputedStyle(blocks[0]).marginBottom) * 0.75) : 0;
        e.lineCount = Math.max(1, Math.round(r.height / lhPx));
        e.fixed = el.hasAttribute('data-fixed');
        e.overflow = el.scrollHeight > el.clientHeight + 1 || el.scrollWidth > el.clientWidth + 1;
        e.wrapStable = true;
        if (!e.fixed && e.text.trim()) {
          const prev = { w: el.style.width, f: el.style.flex, m: el.style.maxWidth };
          el.style.flex = 'none';
          el.style.maxWidth = 'none';
          el.style.width = r.width * safety + 'px';
          const narrowed = el.getBoundingClientRect().height;
          el.style.width = prev.w;
          el.style.flex = prev.f;
          el.style.maxWidth = prev.m;
          e.wrapStable = narrowed <= r.height + 0.5;
        }
      } else if (type === 'shape') {
        e.fill = toHex(cs.backgroundColor);
        const bw = parseFloat(cs.borderTopWidth);
        e.stroke = bw > 0 ? toHex(cs.borderTopColor) : null;
        e.strokeW = bw > 0 ? r2(bw * 0.75) : 0;
        const radius = cs.borderTopLeftRadius;
        if (radius.includes('%') && parseFloat(radius) >= 50) e.kind = 'ellipse';
        else if (parseFloat(radius) > 0) { e.kind = 'roundRect'; e.radius = r4(parseFloat(radius) / PX); } else e.kind = 'rect';
      } else if (type === 'line') {
        e.dir = el.dataset.dir || 'right';
        e.arrow = el.dataset.arrow === 'end';
        e.stroke = toHex(cs.color);
        e.strokeW = r2(Math.max(parseFloat(cs.borderTopWidth), parseFloat(cs.borderLeftWidth)) * 0.75);
        if (e.dir === 'right' || e.dir === 'left') {
          e.y = r4((r.top + r.height / 2 - sr.top) / PX);
          e.h = 0;
        } else {
          e.x = r4((r.left + r.width / 2 - sr.left) / PX);
          e.w = 0;
        }
      } else if (type === 'image') {
        e.alt = el.getAttribute('alt') || '';
        e.src = el.currentSrc || el.src;
      } else if (type === 'chart') {
        e.chartRaw = el.getAttribute('data-chart');
      }
      slide.elements.push(e);
    });
    slides.push(slide);
  });
  return { slides, theme };
}

async function measureHtml(htmlPath, { fontName, thresholds, channel, rasterDir } = {}) {
  const ch = channel || process.env.PPTX_DECK_BROWSER_CHANNEL || 'msedge';
  let browser;
  try {
    browser = await chromium.launch({ channel: ch });
  } catch (e) {
    throw new Error(`ブラウザ(channel=${ch})を起動できない。Microsoft Edge をインストールする。詳細: ${e.message.split('\n')[0]}`);
  }
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 3 });
    await page.goto(pathToFileURL(path.resolve(htmlPath)).href);
    if (fontName) await page.addStyleTag({ content: `:root{--font-main:"${fontName}";}` });
    await page.evaluate(() => document.fonts.ready);
    const raw = await page.evaluate(extractInPage, { safety: thresholds ? thresholds.wrapSafety : 0.92 });
    if (!raw.slides.length) throw new Error('section.slide が見つからない。スライドは <section class="slide"> で書く');
    const dir = rasterDir || fs.mkdtempSync(path.join(os.tmpdir(), 'pptx-deck-raster-'));
    const slides = [];
    for (const s of raw.slides) {
      const [w, h] = s.size;
      if (w !== 1280 || h !== 720) throw new Error(`スライド ${s.index}: サイズが ${w}x${h}px。1280x720px にする`);
      const elements = [];
      for (const e of s.elements) {
        if (e.type === 'chart') {
          let spec;
          try { spec = JSON.parse(e.chartRaw); } catch (err) { throw new Error(`スライド ${s.index}: data-chart が不正な JSON: ${err.message}`); }
          if (!CHART_TYPES.includes(spec.type)) throw new Error(`スライド ${s.index}: チャートの型 "${spec.type}" は未対応(${CHART_TYPES.join('/')})`);
          if (!Array.isArray(spec.labels) || !Array.isArray(spec.values) || spec.labels.length !== spec.values.length || spec.values.some((v) => typeof v !== 'number')) {
            throw new Error(`スライド ${s.index}: data-chart の labels と values は同じ長さで、values は数値にする`);
          }
          e.chart = { labelPt: 12, ...spec };
          delete e.chartRaw;
        }
        if (e.type === 'image') {
          const file = fileURLToPath(e.src);
          if (/\.svg$/i.test(file)) {
            const png = path.join(dir, `${e.id}.png`);
            await page.locator(`[data-pp-id="${e.id}"]`).screenshot({ path: png, omitBackground: true });
            e.src = png;
          } else {
            e.src = file;
          }
        }
        elements.push(e);
      }
      slides.push({ index: s.index, layout: s.layout, bg: s.bg, notes: s.notes, elements });
    }
    return { slideW: SLIDE_W_IN, slideH: SLIDE_H_IN, fontFace: fontName || 'BIZ UDPゴシック', theme: raw.theme, slides };
  } finally {
    await browser.close();
  }
}

module.exports = { measureHtml };
```

- [ ] **Step 5: 通ることを確認する**

Run: `cd skills/pptx-deck && node --test tests/measure.test.js`
Expected: PASS（6 tests）。`wrapStable` の 2 件目が通らない場合は、`tight` の幅（214px）が 20 字 × 21.33px = 426px の約半分（2 行）になっているか、フォントの漢字の送り幅が 1em か、をブラウザで確認して幅を調整する（対象はテストの値で、実装ではない）。

- [ ] **Step 6: コミット**

```bash
git add skills/pptx-deck/scripts/measure.js skills/pptx-deck/tests/measure.test.js skills/pptx-deck/tests/helpers/fixture.js skills/pptx-deck/tests/fixtures
git commit -m "feat: HTML を DOM 計測して要素モデルにする"
```

---

### Task 9: PPTX の生成（要素モデル → pptxgenjs）

**Files:**
- Create: `skills/pptx-deck/scripts/build.js`
- Test: `skills/pptx-deck/tests/build.test.js`

**Interfaces:**
- Consumes: 要素モデル（冒頭の定義）
- Produces: `buildPptx(model, outPath) → Promise<string>`。各要素の `objectName` に `<id>|p=<親ID>|d=<decor 0/1>|r=<role>|t=<type>` を書く（Task 10 が読み戻して親子・decor・役割を復元する）。行間は `lineSpacing`（pt 固定）。`fixed` のテキストは `wrap: false`。チャートは `bar/barh/line/pie` の 4 種で、注目データだけアクセント色（`model.theme.accent`）、他は `model.theme.neutral`。ノートは `addNotes`。画像は `altText`。
- 注意（pptxgenjs の既知の落とし穴）: オプションのオブジェクトは呼び出しごとに新しく作る（共有しない）。色は `#` なしの 6 桁 16 進。

- [ ] **Step 1: 失敗するテストを書く**

`tests/build.test.js`:
```js
'use strict';
const { test, after } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const JSZip = require('jszip');
const { buildPptx } = require('../scripts/build');
const { el, slide, model } = require('./helpers/model');

const root = fs.mkdtempSync(path.join(os.tmpdir(), 'pptx-deck-build-'));
after(() => fs.rmSync(root, { recursive: true, force: true }));

const PNG = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==', 'base64');

function sample() {
  const png = path.join(root, 'icon.png');
  fs.writeFileSync(png, PNG);
  const para = (text, extra = {}) => ({ runs: [{ text, color: '#1A1A1A', bold: false, pt: 16, ...extra }], bullet: false });
  return model([
    slide([
      el({ id: 's1-e1', role: 'title', fontPt: 28, bold: true, x: 0.58, y: 0.42, w: 12.17, h: 0.6, text: '結論です', paras: [para('結論です', { pt: 28, bold: true })], lineSpacingPt: 36, paraSpaceAfter: 0 }),
      el({ id: 's1-e2', type: 'shape', kind: 'roundRect', fill: '#F3F3F3', radius: 0.04, x: 0.58, y: 1.6, w: 4, h: 2, stroke: null, strokeW: 0 }),
      el({ id: 's1-e3', parent: 's1-e2', x: 0.9, y: 1.9, w: 3.3, h: 1, text: '本文', paras: [{ runs: [{ text: '項目', color: '#1A1A1A', bold: false, pt: 16 }, { text: '', br: true }, { text: '次の行', color: '#1A1A1A', bold: false, pt: 16 }], bullet: true }], lineSpacingPt: 24, paraSpaceAfter: 6 }),
      el({ id: 's1-e4', type: 'line', dir: 'right', arrow: true, stroke: '#555555', strokeW: 1.5, x: 5, y: 2.5, w: 1, h: 0 }),
      el({ id: 's1-e5', type: 'image', role: 'icon', src: png, alt: 'アイコン', x: 6.5, y: 1.6, w: 0.5, h: 0.5 }),
      el({ id: 's1-e6', type: 'chart', role: '', x: 7.5, y: 1.6, w: 4.5, h: 3, chart: { type: 'bar', labels: ['A', 'B', 'C'], values: [1, 2, 3], highlight: 2, labelPt: 12 } }),
      el({ id: 's1-e7', role: 'title', fixed: true, decor: true, x: 0.58, y: 5, w: 6, h: 1, text: '固定\n行', paras: [para('固定', { pt: 40 })], lineSpacingPt: 52, fontPt: 40 }),
    ], { notes: '話す内容のメモ' }),
  ]);
}

async function build() {
  const out = path.join(root, 'deck.pptx');
  await buildPptx(sample(), out);
  return JSZip.loadAsync(fs.readFileSync(out));
}

test('テキスト: フォント・サイズ・pt固定の行間・オブジェクト名を書く', async () => {
  const zip = await build();
  const xml = await zip.file('ppt/slides/slide1.xml').async('string');
  assert.match(xml, /typeface="BIZ UDPゴシック"/);
  assert.match(xml, /sz="2800"/);
  assert.match(xml, /<a:spcPts val="3600"\/>/);
  assert.match(xml, /name="s1-e1\|p=\|d=0\|r=title\|t=text"/);
  assert.match(xml, /name="s1-e3\|p=s1-e2\|d=0\|r=body\|t=text"/);
  assert.match(xml, /name="s1-e7\|p=\|d=1\|r=title\|t=text"/);
});

test('固定行の見出しは折り返さず、箇条書きと改行を持つ', async () => {
  const xml = await (await build()).file('ppt/slides/slide1.xml').async('string');
  assert.match(xml, /wrap="none"/);
  assert.match(xml, /<a:buChar/);
  assert.match(xml, /次の行/);
});

test('図形・線・画像: 角丸・矢印・代替テキストを書く', async () => {
  const xml = await (await build()).file('ppt/slides/slide1.xml').async('string');
  assert.match(xml, /prst="roundRect"/);
  assert.match(xml, /<a:tailEnd type="triangle"/);
  assert.match(xml, /descr="アイコン"/);
  assert.match(xml, /<p:pic>/);
});

test('チャート: ネイティブチャートで、注目データだけ別色にする', async () => {
  const zip = await build();
  const chart = await zip.file('ppt/charts/chart1.xml').async('string');
  assert.match(chart, /<c:barChart>/);
  assert.equal((chart.match(/<c:dPt>/g) || []).length >= 1, true);
  assert.match(chart, /1F4E9C/);
  assert.match(chart, /BFBFBF/);
});

test('ノート: スピーカーノートを書く', async () => {
  const zip = await build();
  const names = Object.keys(zip.files).filter((n) => /notesSlide\d+\.xml$/.test(n));
  assert.equal(names.length, 1);
  assert.match(await zip.file(names[0]).async('string'), /話す内容のメモ/);
});

test('空のスライド・未対応のチャート型・存在しない画像は明示エラー', async () => {
  const out = path.join(root, 'empty.pptx');
  await buildPptx(model([slide([])]), out);
  assert.ok(fs.existsSync(out));
  await assert.rejects(buildPptx(model([slide([el({ type: 'chart', chart: { type: 'stacked', labels: [], values: [] } })])]), path.join(root, 'x.pptx')), /未対応/);
  await assert.rejects(buildPptx(model([slide([el({ type: 'image', src: path.join(root, 'nothing.png'), alt: 'x' })])]), path.join(root, 'y.pptx')), /画像が見つからない/);
});
```

- [ ] **Step 2: 失敗を確認する**

Run: `cd skills/pptx-deck && node --test tests/build.test.js`
Expected: FAIL（`Cannot find module '../scripts/build'`）

- [ ] **Step 3: 実装する**

`scripts/build.js`:
```js
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
```

- [ ] **Step 4: 通ることを確認する**

Run: `cd skills/pptx-deck && node --test tests/build.test.js`
Expected: PASS（6 tests）。pptxgenjs の出力の細部（`<a:tailEnd>` の属性、`<c:dPt>` の有無、`wrap="none"`）に差があって落ちた場合は、実際の XML を `unzip -p` などで確認し、**実装側のオプション**を直す（テストの期待は SPEC の要件＝矢印・注目データの別色・折り返しなしを表している）。

- [ ] **Step 5: コミット**

```bash
git add skills/pptx-deck/scripts/build.js skills/pptx-deck/tests/build.test.js
git commit -m "feat: 要素モデルをネイティブ PPTX に変換する"
```

---

### Task 10: PPTX の読み戻しとパッケージ検査

**Files:**
- Create: `skills/pptx-deck/scripts/check-pptx.js`
- Test: `skills/pptx-deck/tests/check-pptx.test.js`

**Interfaces:**
- Consumes: `buildPptx`（テストのみ）、`runRules`、Task 9 の `objectName` 規約
- Produces:
  - `readPptxModel(pptxPath) → Promise<{ model, packageErrors: string[] }>`（生成後の XML を要素モデルに戻す。`layout` は `'content'` 固定、チャートは `type: 'chart'`、親子・decor・role は名前から復元）
  - `verifyPptx(pptxPath, thresholds) → Promise<{ violations, packageErrors, model }>`（`runRules(..., { stage: 'pptx' })` を実行）

- [ ] **Step 1: 失敗するテストを書く**

`tests/check-pptx.test.js`:
```js
'use strict';
const { test, after } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const JSZip = require('jszip');
const { buildPptx } = require('../scripts/build');
const { readPptxModel, verifyPptx } = require('../scripts/check-pptx');
const { loadThresholds } = require('../scripts/lib/thresholds');
const { el, slide, model } = require('./helpers/model');

const t = loadThresholds();
const root = fs.mkdtempSync(path.join(os.tmpdir(), 'pptx-deck-check-'));
after(() => fs.rmSync(root, { recursive: true, force: true }));

const para = (text, pt = 16, color = '#1A1A1A') => ({ runs: [{ text, color, bold: false, pt }], bullet: false });
const text = (o) => el({ lineSpacingPt: 24, paraSpaceAfter: 0, paras: [para(o.text || 'あ', o.fontPt || 16, o.color || '#1A1A1A')], ...o });

async function make(name, elements) {
  const file = path.join(root, name);
  await buildPptx(model([slide(elements)]), file);
  return file;
}

test('読み戻し: 位置・サイズ・フォント・色・親子・decor・役割を復元する', async () => {
  const file = await make('ok.pptx', [
    text({ id: 's1-e1', role: 'title', fontPt: 28, text: 'タイトル', x: 0.58, y: 0.42, w: 12.17, h: 0.6 }),
    el({ id: 's1-e2', type: 'shape', kind: 'rect', fill: '#1F4E9C', x: 1, y: 2, w: 4, h: 2 }),
    text({ id: 's1-e3', parent: 's1-e2', text: '白文字', color: '#FFFFFF', x: 1.2, y: 2.2, w: 3, h: 1 }),
    el({ id: 's1-e4', type: 'chart', role: '', x: 6, y: 2, w: 5, h: 3, chart: { type: 'bar', labels: ['A', 'B'], values: [1, 2], highlight: 1, labelPt: 12 } }),
  ]);
  const { model: m, packageErrors } = await readPptxModel(file);
  assert.deepEqual(packageErrors, []);
  assert.ok(Math.abs(m.slideW - 13.333) < 0.01);
  const [title, card, inner, chart] = m.slides[0].elements;
  assert.equal(title.role, 'title');
  assert.equal(title.fontPt, 28);
  assert.ok(Math.abs(title.x - 0.58) < 0.01 && Math.abs(title.w - 12.17) < 0.01);
  assert.equal(card.fill, '#1F4E9C');
  assert.equal(inner.parent, 's1-e2');
  assert.equal(inner.color, '#FFFFFF');
  assert.equal(chart.type, 'chart');
  assert.ok(Math.abs(chart.w - 5) < 0.01);
});

test('verify: 健全なデッキは違反0件。重なり・小さい文字・薄い文字・代替テキストなしを検出する', async () => {
  const good = await verifyPptx(await make('good.pptx', [
    text({ id: 's1-e1', role: 'title', fontPt: 28, text: 'タイトル', x: 0.58, y: 0.42, w: 12.17, h: 0.6 }),
    text({ id: 's1-e2', text: '本文', x: 1, y: 2, w: 5, h: 1 }),
  ]), t);
  assert.deepEqual(good.violations, []);

  const bad = await verifyPptx(await make('bad.pptx', [
    text({ id: 's1-e1', text: '重なり1', x: 1, y: 2, w: 4, h: 1 }),
    text({ id: 's1-e2', text: '重なり2', x: 1.5, y: 2.2, w: 4, h: 1 }),
    text({ id: 's1-e3', text: '小さい', fontPt: 12, x: 1, y: 4, w: 4, h: 1 }),
    text({ id: 's1-e4', text: '薄い', color: '#CCCCCC', x: 1, y: 5.5, w: 4, h: 1 }),
  ]), t);
  const rules = new Set(bad.violations.map((v) => v.rule));
  for (const r of ['overlap', 'minFont', 'contrast']) assert.ok(rules.has(r), `${r} を検出できない`);
});

test('パッケージ検査: 壊れた XML と、宣言のない軸 ID を検出する', async () => {
  const file = await make('pkg.pptx', [
    el({ id: 's1-e1', type: 'chart', role: '', x: 1, y: 2, w: 5, h: 3, chart: { type: 'bar', labels: ['A', 'B'], values: [1, 2], highlight: 0, labelPt: 12 } }),
  ]);
  const zip = await JSZip.loadAsync(fs.readFileSync(file));
  const slideXml = await zip.file('ppt/slides/slide1.xml').async('string');
  zip.file('ppt/slides/slide1.xml', slideXml.replace('</p:sld>', ''));
  const chartXml = await zip.file('ppt/charts/chart1.xml').async('string');
  zip.file('ppt/charts/chart1.xml', chartXml.replace(/<c:valAx>\s*<c:axId val="\d+"\/>/, '<c:valAx><c:axId val="999999"/>'));
  const broken = path.join(root, 'broken.pptx');
  fs.writeFileSync(broken, await zip.generateAsync({ type: 'nodebuffer' }));
  const { packageErrors } = await readPptxModel(broken);
  assert.ok(packageErrors.some((e) => /slide1\.xml.*壊れ/.test(e)), packageErrors.join('\n'));
  assert.ok(packageErrors.some((e) => /軸/.test(e)), packageErrors.join('\n'));
});

test('存在しないファイルは明示エラー', async () => {
  await assert.rejects(readPptxModel(path.join(root, 'none.pptx')), /見つからない/);
});
```

- [ ] **Step 2: 失敗を確認する**

Run: `cd skills/pptx-deck && node --test tests/check-pptx.test.js`
Expected: FAIL（`Cannot find module '../scripts/check-pptx'`）

- [ ] **Step 3: 実装する**

`scripts/check-pptx.js`:
```js
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

const NAME = /^(s\d+-e\d+)\|p=([^|]*)\|d=(\d)\|r=([^|]*)\|t=(\w+)$/;
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
    ? { id: m[1], parent: m[2] || null, decor: m[3] === '1', role: m[4], type: m[5] }
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
    const used = [...xml.matchAll(/<c:axId val="(\d+)"\/>/g)].map((m) => m[1]);
    const declared = [...xml.matchAll(/<c:(?:catAx|valAx|dateAx|serAx)>\s*<c:axId val="(\d+)"\/>/g)].map((m) => m[1]);
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
        ...(id.type === 'text' ? { ...body, align: 'left', lineCount: 1, fixed: false, wrapStable: true, overflow: false } : { fill: hexOf(spPr) }),
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
```

- [ ] **Step 4: 通ることを確認する**

Run: `cd skills/pptx-deck && node --test tests/check-pptx.test.js`
Expected: PASS（4 tests）。チャートの `labelPt` は XML から読めないので固定値 12 としている（チャートの軸ラベルの最小サイズ検査は HTML 段階で行う。この制約は SKILL.md に書く）。pptxgenjs の XML の要素名が想定と違って読み戻せない場合は、`unzip -p deck.pptx ppt/slides/slide1.xml` で実物を見て、`readPptxModel` のパスを合わせる。

- [ ] **Step 5: コミット**

```bash
git add skills/pptx-deck/scripts/check-pptx.js skills/pptx-deck/tests/check-pptx.test.js
git commit -m "feat: 生成後の PPTX を XML から読み戻して検査する"
```

---

### Task 11: CLI・環境診断・見本カタログの統合テスト

**Files:**
- Create: `skills/pptx-deck/scripts/run.js`, `scripts/doctor.js`
- Test: `skills/pptx-deck/tests/cli.test.js`

**Interfaces:**
- Consumes: 全モジュール
- Produces（CLI。終了コード 0=合格、2=違反あり、1=実行エラー）:
  - `node scripts/run.js init <dir>`: `design/base.css`、`chart-preview.js`、`catalog.html` を `<dir>` にコピーする。
  - `node scripts/run.js doctor`: 環境を診断する。
  - `node scripts/run.js check <deck.html> [--attempt N]`: フォントを選び、HTML を計測して検査する。JSON レポートを標準出力へ。
  - `node scripts/run.js build <deck.html> <out.pptx> [--work <dir>] [--attempt N] [--no-render]`: `check` に合格したら PPTX を生成し、`verify`、画像化（LibreOffice があれば）まで行う。
  - `node scripts/run.js verify <deck.pptx>`、`node scripts/run.js render <deck.pptx> <outDir>`。
- レポート: `{ ok, stage, font: {name, fellBack}, violations, summary, suggestion, packageErrors?, pptx?, pngs? }`。

- [ ] **Step 1: 失敗するテストを書く**

`tests/cli.test.js`:
```js
'use strict';
const { test, after } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { findSoffice } = require('../scripts/render');

const RUN = path.join(__dirname, '..', 'scripts', 'run.js');
const root = fs.mkdtempSync(path.join(os.tmpdir(), 'pptx-deck-cli-'));
after(() => fs.rmSync(root, { recursive: true, force: true }));
const work = path.join(root, 'deck-work', '日本語 名前'); // 日本語と空白を含む作業フォルダ

function run(args) {
  const r = spawnSync('node', [RUN, ...args], { encoding: 'utf8', timeout: 300000 });
  let json = null;
  try { json = JSON.parse(r.stdout); } catch { /* 標準出力が JSON でない場合は null */ }
  return { status: r.status, json, stdout: r.stdout, stderr: r.stderr };
}

test('init: 作業フォルダに見本一式をコピーする', () => {
  const r = run(['init', work]);
  assert.equal(r.status, 0, r.stderr);
  for (const f of ['base.css', 'chart-preview.js', 'catalog.html']) assert.ok(fs.existsSync(path.join(work, f)), f);
});

test('check: 見本カタログは違反 0 件で合格する', () => {
  const r = run(['check', path.join(work, 'catalog.html')]);
  assert.equal(r.status, 0, `${r.stdout}\n${r.stderr}`);
  assert.equal(r.json.ok, true);
  assert.deepEqual(r.json.violations, []);
  assert.ok(r.json.font.name);
});

test('check: 違反のある HTML は終了コード 2 と、修正の提案を返す', () => {
  const html = fs.readFileSync(path.join(work, 'catalog.html'), 'utf8')
    .replace('data-role="body" style="margin-top:12px">商談化率が既存深耕の1.8倍。人員を2名追加して、訪問件数を増やす。', 'data-role="body" style="margin-top:12px;font-size:10px">商談化率');
  const bad = path.join(work, 'bad.html');
  fs.writeFileSync(bad, html);
  const r = run(['check', bad, '--attempt', '0']);
  assert.equal(r.status, 2);
  assert.equal(r.json.ok, false);
  assert.ok(r.json.violations.some((v) => v.rule === 'minFont'));
  assert.ok(r.json.suggestion.action);
});

test('build: 合格した HTML から PPTX を作り、検証し、(LibreOffice があれば) 画像化する', { skip: !findSoffice() }, () => {
  const out = path.join(work, 'catalog.pptx');
  const r = run(['build', path.join(work, 'catalog.html'), out, '--work', work]);
  assert.equal(r.status, 0, `${r.stdout}\n${r.stderr}`);
  assert.equal(r.json.ok, true);
  assert.ok(fs.existsSync(out));
  assert.deepEqual(r.json.packageErrors, []);
  assert.equal(r.json.pngs.length, 7);
});

test('build: HTML 段階で違反があれば PPTX を作らない', () => {
  const out = path.join(work, 'never.pptx');
  const r = run(['build', path.join(work, 'bad.html'), out, '--no-render']);
  assert.equal(r.status, 2);
  assert.ok(!fs.existsSync(out));
});

test('doctor: 必須項目の結果を一覧で出す', () => {
  const r = run(['doctor']);
  assert.match(r.stdout, /\[(OK|NG)\] Node/);
  assert.match(r.stdout, /Edge/);
  assert.match(r.stdout, /フォント/);
});
```

- [ ] **Step 2: 失敗を確認する**

Run: `cd skills/pptx-deck && node --test tests/cli.test.js`
Expected: FAIL（`scripts/run.js` が存在しない）

- [ ] **Step 3: 環境診断を実装する**

`scripts/doctor.js`:
```js
'use strict';
const { spawnSync } = require('node:child_process');
const { chromium } = require('playwright');
const { detectInstalledFonts, pickFont } = require('./lib/fonts');
const { findSoffice, pythonCmd } = require('./render');

async function run() {
  const results = [];
  const add = (name, ok, hint, required = true) => results.push({ name, ok, hint, required });

  add('Node 20 以上', Number(process.versions.node.split('.')[0]) >= 20, 'Node 20 以上をインストールする');
  for (const m of ['pptxgenjs', 'playwright', 'jszip', 'fast-xml-parser']) {
    let ok = true;
    try { require(m); } catch { ok = false; }
    add(`npm パッケージ ${m}`, ok, 'skills/pptx-deck で npm install を実行する');
  }
  let edge = true;
  try { const b = await chromium.launch({ channel: 'msedge' }); await b.close(); } catch { edge = false; }
  add('Edge (Playwright channel=msedge)', edge, 'Microsoft Edge をインストールする');
  try {
    const f = pickFont(detectInstalledFonts());
    add(`日本語フォント: ${f.name}${f.fellBack ? '（代替。BIZ UDPゴシックが未導入）' : ''}`, true, '');
  } catch (e) {
    add('日本語フォント', false, e.message);
  }
  add('LibreOffice（画像化の検証）', !!findSoffice(), 'LibreOffice をインストールする。なくても幾何検査だけで動く', false);
  const py = spawnSync(pythonCmd(), ['-c', 'import pymupdf'], { encoding: 'utf8' });
  add('Python + PyMuPDF（PDF→PNG）', py.status === 0, 'pip install pymupdf を実行する。なくても幾何検査だけで動く', false);

  let failed = false;
  for (const r of results) {
    const mark = r.ok ? 'OK' : r.required ? 'NG' : '警告';
    console.log(`[${mark}] ${r.name}${r.ok ? '' : ` → ${r.hint}`}`);
    if (!r.ok && r.required) failed = true;
  }
  return !failed;
}

module.exports = { run };
```

- [ ] **Step 4: CLI を実装する**

`scripts/run.js`:
```js
#!/usr/bin/env node
'use strict';
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { loadThresholds } = require('./lib/thresholds');
const { detectInstalledFonts, pickFont } = require('./lib/fonts');
const { measureHtml } = require('./measure');
const { runRules, summarize } = require('./rules');
const { suggestFix } = require('./suggest');
const { buildPptx } = require('./build');
const { verifyPptx } = require('./check-pptx');
const { findSoffice, renderPptx } = require('./render');

const DESIGN = path.join(__dirname, '..', 'design');

function parseArgs(argv) {
  const pos = [];
  const opt = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) opt[a.slice(2)] = argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[++i] : true;
    else pos.push(a);
  }
  return { pos, opt };
}

const print = (report) => console.log(JSON.stringify(report, null, 2));

async function checkHtml(htmlPath, opt, t) {
  const font = pickFont(detectInstalledFonts());
  const rasterDir = fs.mkdtempSync(path.join(os.tmpdir(), 'pptx-deck-raster-'));
  const model = await measureHtml(htmlPath, { fontName: font.name, thresholds: t, rasterDir });
  const violations = runRules(model, t, { stage: 'html' });
  const summary = summarize(violations);
  const report = {
    ok: summary.errors === 0, stage: 'html', font, violations, summary,
    suggestion: suggestFix(violations, Number(opt.attempt || 0), t),
  };
  return { report, model, rasterDir };
}

async function main() {
  const { pos, opt } = parseArgs(process.argv.slice(2));
  const [cmd, a, b] = pos;
  const t = loadThresholds();

  if (cmd === 'init') {
    if (!a) throw new Error('使い方: run.js init <作業フォルダ>');
    fs.mkdirSync(a, { recursive: true });
    for (const f of ['base.css', 'chart-preview.js', 'catalog.html']) fs.copyFileSync(path.join(DESIGN, f), path.join(a, f));
    console.log(JSON.stringify({ ok: true, dir: path.resolve(a) }));
    return;
  }
  if (cmd === 'doctor') {
    process.exitCode = (await require('./doctor').run()) ? 0 : 1;
    return;
  }
  if (cmd === 'check') {
    if (!a) throw new Error('使い方: run.js check <deck.html> [--attempt N]');
    const { report, rasterDir } = await checkHtml(a, opt, t);
    fs.rmSync(rasterDir, { recursive: true, force: true });
    print(report);
    process.exitCode = report.ok ? 0 : 2;
    return;
  }
  if (cmd === 'build') {
    if (!a || !b) throw new Error('使い方: run.js build <deck.html> <out.pptx> [--work <dir>] [--attempt N] [--no-render]');
    const { report, model, rasterDir } = await checkHtml(a, opt, t);
    try {
      if (!report.ok) { print(report); process.exitCode = 2; return; }
      fs.mkdirSync(path.dirname(path.resolve(b)), { recursive: true });
      await buildPptx(model, b);
      const v = await verifyPptx(b, t);
      const summary = summarize(v.violations);
      const out = {
        ...report, stage: 'pptx', ok: summary.errors === 0 && v.packageErrors.length === 0,
        violations: v.violations, summary, packageErrors: v.packageErrors, pptx: path.resolve(b),
        suggestion: suggestFix(v.violations, Number(opt.attempt || 0), t),
      };
      if (!opt['no-render'] && findSoffice()) {
        const dir = path.join(opt.work || path.dirname(path.resolve(b)), 'render');
        out.pngs = renderPptx(b, dir).pngs;
        out.renderNote = 'LibreOffice による近似の画像。PowerPoint で開いて最終確認することを勧める';
      } else if (!opt['no-render']) {
        out.renderNote = 'LibreOffice が未導入のため画像化を省略した(幾何検査のみ)';
      }
      if (opt.work) fs.writeFileSync(path.join(opt.work, 'report.json'), JSON.stringify(out, null, 2));
      print(out);
      process.exitCode = out.ok ? 0 : 2;
    } finally {
      fs.rmSync(rasterDir, { recursive: true, force: true });
    }
    return;
  }
  if (cmd === 'verify') {
    if (!a) throw new Error('使い方: run.js verify <deck.pptx>');
    const v = await verifyPptx(a, t);
    const summary = summarize(v.violations);
    print({ ok: summary.errors === 0 && v.packageErrors.length === 0, stage: 'pptx', violations: v.violations, summary, packageErrors: v.packageErrors });
    process.exitCode = summary.errors === 0 && v.packageErrors.length === 0 ? 0 : 2;
    return;
  }
  if (cmd === 'render') {
    if (!a || !b) throw new Error('使い方: run.js render <deck.pptx> <出力フォルダ>');
    print({ ok: true, ...renderPptx(a, b) });
    return;
  }
  throw new Error('使い方: run.js <init|doctor|check|build|verify|render> …');
}

main().catch((e) => { console.error(`エラー: ${e.message}`); process.exit(1); });
```

- [ ] **Step 5: 実行して、見本カタログを合格させる**

Run: `cd skills/pptx-deck && node --test tests/cli.test.js`
Expected: PASS（6 tests）。

`check: 見本カタログは違反 0 件` が落ちたら、レポートの `violations` を読み、**`design/catalog.html` か `design/base.css` を直す**（しきい値は変えない）。よくある原因:
- `wrapStable`: 幅ぎりぎりの短文。カードの padding を減らす、または文言を短くする。
- `usage`: 余白が大きすぎる／詰めすぎ。カードの高さを調整する。
- `bounds`: 絶対配置の caption の `top` が低すぎる。
- `overlap`: タイトルが 2 行になって本文領域に食い込んでいる。タイトルを短くする。

- [ ] **Step 6: コミット**

```bash
git add skills/pptx-deck/scripts/run.js skills/pptx-deck/scripts/doctor.js skills/pptx-deck/tests/cli.test.js skills/pptx-deck/design
git commit -m "feat: CLI と環境診断、見本カタログの統合テスト"
```

---

### Task 12: SKILL.md・README・サンプル・受入チェック

**Files:**
- Create: `skills/pptx-deck/SKILL.md`, `README.md`
- Create: `skills/pptx-deck/samples/01-theme-only.md`, `02-long-script.md`, `03-diagram-chart.md`, `expected.json`
- Create: `skills/pptx-deck/scripts/acceptance-check.js`
- Test: `skills/pptx-deck/tests/acceptance-check.test.js`

**Interfaces:**
- Consumes: `verifyPptx`、`readPptxModel`、`loadThresholds`
- Produces: `node scripts/acceptance-check.js <deck.pptx> <最小枚数> <最大枚数>`（終了コード 0=合格、2=不合格。枚数の範囲、体裁チェック 0 件、パッケージエラー 0 件、`<p:pic>` が本文の代わりになっていないこと）。関数 `acceptanceCheck(pptxPath, min, max, t) → Promise<{ ok, slides, failures: string[] }>`。

- [ ] **Step 1: 失敗するテストを書く**

`tests/acceptance-check.test.js`:
```js
'use strict';
const { test, after } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { buildPptx } = require('../scripts/build');
const { acceptanceCheck } = require('../scripts/acceptance-check');
const { loadThresholds } = require('../scripts/lib/thresholds');
const { el, slide, model } = require('./helpers/model');

const t = loadThresholds();
const root = fs.mkdtempSync(path.join(os.tmpdir(), 'pptx-deck-accept-'));
after(() => fs.rmSync(root, { recursive: true, force: true }));

const text = (o) => el({ lineSpacingPt: 24, paraSpaceAfter: 0, paras: [{ runs: [{ text: 'あ', color: '#1A1A1A', bold: false, pt: 16 }], bullet: false }], ...o });

test('枚数が範囲内で違反がなければ合格、範囲外・違反ありなら不合格の理由を返す', async () => {
  const file = path.join(root, 'a.pptx');
  await buildPptx(model([slide([text({ id: 's1-e1', x: 1, y: 2 })]), slide([text({ id: 's2-e1', x: 1, y: 2 })], { index: 2 })]), file);
  assert.equal((await acceptanceCheck(file, 1, 3, t)).ok, true);
  const out = await acceptanceCheck(file, 5, 8, t);
  assert.equal(out.ok, false);
  assert.match(out.failures.join('\n'), /枚数/);

  const bad = path.join(root, 'b.pptx');
  await buildPptx(model([slide([text({ id: 's1-e1', fontPt: 11, paras: [{ runs: [{ text: 'あ', color: '#1A1A1A', bold: false, pt: 11 }], bullet: false }], x: 1, y: 2 })])]), bad);
  const r = await acceptanceCheck(bad, 1, 1, t);
  assert.equal(r.ok, false);
  assert.match(r.failures.join('\n'), /minFont/);
});
```

- [ ] **Step 2: 失敗を確認する**

Run: `cd skills/pptx-deck && node --test tests/acceptance-check.test.js`
Expected: FAIL（`Cannot find module '../scripts/acceptance-check'`）

- [ ] **Step 3: 受入チェックを実装する**

`scripts/acceptance-check.js`:
```js
#!/usr/bin/env node
'use strict';
const { verifyPptx } = require('./check-pptx');
const { loadThresholds } = require('./lib/thresholds');

async function acceptanceCheck(pptxPath, min, max, t) {
  const v = await verifyPptx(pptxPath, t);
  const failures = [];
  const n = v.model.slides.length;
  if (n < min || n > max) failures.push(`枚数 ${n} が期待の範囲 ${min}〜${max} にない`);
  for (const e of v.packageErrors) failures.push(`パッケージ: ${e}`);
  for (const x of v.violations) failures.push(`${x.rule}(スライド ${x.slide}, ${x.id}): ${x.message}`);
  return { ok: failures.length === 0, slides: n, failures };
}

module.exports = { acceptanceCheck };

if (require.main === module) {
  const [file, min, max] = process.argv.slice(2);
  if (!file || !min || !max) { console.error('使い方: acceptance-check.js <deck.pptx> <最小枚数> <最大枚数>'); process.exit(1); }
  acceptanceCheck(file, Number(min), Number(max), loadThresholds()).then((r) => {
    console.log(r.ok ? `PASS(${r.slides} 枚)` : `FAIL\n- ${r.failures.join('\n- ')}`);
    process.exitCode = r.ok ? 0 : 2;
  }).catch((e) => { console.error(`エラー: ${e.message}`); process.exit(1); });
}
```

- [ ] **Step 4: 通ることを確認する**

Run: `cd skills/pptx-deck && node --test tests/acceptance-check.test.js`
Expected: PASS（1 test）

- [ ] **Step 5: サンプル入力 3 種を書く**

`samples/expected.json`:
```json
[
  { "file": "01-theme-only.md", "slidesMin": 10, "slidesMax": 15 },
  { "file": "02-long-script.md", "slidesMin": 10, "slidesMax": 15 },
  { "file": "03-diagram-chart.md", "slidesMin": 10, "slidesMax": 15 }
]
```

`samples/01-theme-only.md`:
```markdown
# サンプル依頼1: テーマのみ

「新入社員向けの情報セキュリティ研修」の資料を作ってください。
対象は入社1週間以内の新入社員、所要時間は45分、10〜15枚程度。
```

`samples/02-long-script.md`:
```markdown
# サンプル依頼2: 長めの原稿

次の原稿から、経営会議用のスライドを10〜15枚で作ってください。

## 背景
2026年度第2四半期の売上は前年同期比で12%増加した。増加の主な要因は新規開拓の商談化率の改善で、既存顧客向けの売上はほぼ横ばいだった。一方で、見積の回答に平均3.2営業日かかっており、競合に案件を奪われる事例が複数あった。

## 分析
新規開拓チームの商談化率は18%から32%に上がり、既存深耕チームの1.8倍になった。訪問1件あたりの工数は新規開拓のほうが約1.4倍大きいが、受注単価も約2.1倍あり、投入工数あたりの売上は新規開拓が優位である。既存深耕の解約率は年率2.1%で安定している。見積業務は拠点ごとに様式が異なり、確認と差し戻しで日数が延びている。

## 提案
1. 新規開拓チームに2名を追加配置する。既存深耕の定例訪問を月1回から四半期1回へ減らし、その分を振り向ける。
2. 見積様式を標準化し、回答までの日数を3.2日から1.6日に短縮する。まず2拠点で1か月試行し、課題を洗い出してから全拠点へ展開する。
3. 四半期ごとに、商談化率・見積回答日数・解約率の3指標をレビューする。

## 期待効果と費用
追加配置と標準化により、第4四半期の売上を第2四半期比で約8%押し上げる見込み。費用は人員の再配置のみで、新規の採用は伴わない。見積システムの改修費として、初期に200万円を見込む。

## リスク
新規開拓に偏ると既存顧客の満足度が下がる恐れがある。解約率が3%を超えた場合は、定例訪問の頻度を戻す。
```

`samples/03-diagram-chart.md`:
```markdown
# サンプル依頼3: 図解・グラフ多め

次の内容で、図解とグラフを多く使ったスライドを10〜15枚で作ってください。

- 売上推移（百万円）: 第1四半期120、第2四半期135、第3四半期128、第4四半期172。第4四半期を強調する棒グラフ。
- 顧客セグメント別の売上構成比: 製造40%、小売25%、金融20%、その他15%。円グラフ。
- 拠点別の商談化率（%）: 東京34、大阪29、名古屋26、福岡22、札幌18。横棒グラフで東京を強調。
- 導入の流れ: 現状把握 → 標準化 → 試行 → 全拠点展開（フロー図）。
- 施策の優先度: 影響度×実現しやすさの2×2マトリクス（4象限の例を各1つ）。
- 組織: 営業本部の下に新規開拓・既存深耕・営業企画の3チーム（ツリー図）。
- 方針から実行までの階層: ビジョン・戦略・施策・日々の行動（ピラミッド図）。
```

- [ ] **Step 6: SKILL.md を書く**

`skills/pptx-deck/SKILL.md`:
````markdown
---
name: pptx-deck
description: テーマや原稿から、編集可能で AI っぽくない PowerPoint(.pptx)を作る。構成案→原稿→HTML プレビュー→PPTX の順に承認を取りながら進め、体裁を自動検査する。「スライドを作って」「資料を作って」「PowerPoint を作って」「プレゼン資料」「デッキ」と頼まれたときに使う。既存 PPTX の編集やテンプレ(.potx)への流し込みには使わない。Windows 専用。
---

# pptx-deck

テーマまたは原稿から、PowerPoint で編集できる .pptx を作る。本文を画像にしない。13.33×7.5in（16:9）、BIZ UDPゴシック、無彩色＋アクセント 1 色。

以降の `<skill>` は、このファイルがあるフォルダ（`skills/pptx-deck`）を指す。コマンドはすべて `node "<skill>/scripts/run.js" …`。

## 0. 初回だけ

1. `cd "<skill>" && npm install`
2. `pip install pymupdf`（画像化に使う。LibreOffice も推奨）
3. `node "<skill>/scripts/run.js" doctor` が `[NG]` を出さないことを確認する。`[警告]` は画像化が使えないだけで、幾何検査は動く。

## 1. 作業フォルダ

利用者の作業フォルダに `deck-work/<名前>/` を作り、`node "<skill>/scripts/run.js" init "deck-work/<名前>"` で `base.css`、`chart-preview.js`、`catalog.html`（見本 7 枚）をコピーする。構成案・原稿・HTML・検査結果はすべてここに置く（再開できる）。

## 2. 流れ（承認は 2 回。テーマのみの依頼は構成案を加えた 3 回）

1. **入力の確認**: テーマのみか、原稿があるか。対象者・目的・所要時間・枚数が決まらず、外れたときの手戻りが大きいなら先に質問する。
2. **構成案**（テーマのみの場合だけ）: `outline.md` にスライド一覧と、各スライドで言い切るメッセージを書き、**承認を得る**。
3. **原稿**: `script.md` に各スライドの見出し（言い切りの文）、本文、図解かグラフの指定、スピーカーノートを書く。次の**内容レビュー**を原稿の承認の前に 1〜2 回行い、直してから示す。
   - 論理の流れ: 結論→根拠→提案の順で、飛躍がないか。
   - 抜け漏れ: 対象者が知りたいことが欠けていないか。
   - 読み手の視点: 専門用語、前提の説明が足りているか。
   **原稿を承認してもらい、内容を凍結する**【承認①】。以降、承認なしに内容を変えない。
4. **HTML プレビュー**: `deck.html` を書く。`catalog.html` をコピーして構造を真似る（下の「HTML の書き方」）。書いたら `check` で合格させてから、承認に出す。ブラウザで開いて見せる**【承認②】**。チャートのプレビューは近似。
5. **PPTX 出力**: `node "<skill>/scripts/run.js" build "deck-work/<名前>/deck.html" "deck-work/<名前>/deck.pptx" --work "deck-work/<名前>"`
6. **結果の報告**（承認は求めない）: 検査結果、`render/slide-NN.png`（LibreOffice の近似）を見て崩れを確認した所見、PowerPoint で開いて最終確認することを勧める旨を伝える。

## 3. HTML の書き方

- 1 枚 = `<section class="slide" data-layout="…">`。`data-layout` は `cover | section | content | diagram | chart | closing`。同じレイアウトを 3 枚以上連続させない。10 枚以上なら図解かグラフを 2 枚以上入れる。
- 使う要素は `pp-text`（`data-role` = `title | lead | body | caption`）、`pp-shape`（`.card` など）、`pp-line`（`data-dir` = `right | left | down | up`、`data-arrow="end"`）、`pp-image`（`alt` 必須。`data-role` = `icon | photo`）、`pp-chart`（`data-chart` に JSON）。それ以外は計測されず、PPTX に出ない。
- **テキストは必ず幅を持たせる**（ブロックとして親に stretch、または `width` 指定）。幅が内容ぴったりだと PowerPoint で折り返しが変わる。`check` の `wrapStable` が検出する。
- カードの中の文字は、DOM でもカードの子にする（子は親に含まれていれば重なり扱いにならない）。
- 見出しの改行位置を固定したいときだけ `data-fixed` を付け、`<br>` で改行する。
- タイトルは 1 枚 1 つ、`section.slide` の直下。全角 30 字以内（2 行までなら可）。末尾に句点を付けない。
- 図解は 4 種（フロー、2×2 マトリクス、ピラミッド、ツリー）。`catalog.html` の 3〜6 枚目を雛形にする。矩形・角丸矩形・円・直線矢印・テキストだけを使う。
- チャートは 3 種（`bar`、`barh`、`line`、`pie`）。`{"type":"bar","labels":[…],"values":[…],"highlight":3,"labelPt":12}`。注目データを `highlight` で 1 つ指定し、他は無彩色にする。積み上げ棒・第 2 軸は使わない。
- スピーカーノートは `<aside class="notes">…</aside>`。
- 色はアクセント 1 色と無彩色だけ。装飾バー、タイトル下のアクセント線、長い本文のセンタリングは使わない。
- 文字は本文 14pt 以上（既定 16pt）、注記 10pt 以上。タイトルと本文は 4pt 以上差をつける。
- 写真素材を自動で集めない。画像は利用者が渡したものと、アイコン（SVG 可）だけ。

## 4. 検査と自動修正

`check`／`build` の JSON が `ok: false` なら、`violations` を読んで HTML を直す。`suggestion` に次の一手が出る。

| action | やること |
|---|---|
| `reduceSpacing` | カードの padding と gap を縮める |
| `tightenLineHeight` | line-height を 1.4 に（下限 1.3） |
| `shrinkFont` | フォントを下げる（本文 14pt・注記 10pt の下限は割らない） |
| `proposeSplitOrTrim` | 自動修正の上限（3 回）。**スライドの分割案と文章の削減案をユーザーに示し、承認を得てから**原稿を変える |
| `manual` | 重なり・配置などは HTML を直接直す |

修正のたびに `--attempt <これまでの修正回数>` を付けて再実行する。PPTX の再出力は、出力後検査で違反が出たときに限る。

## 5. 守ること

- 本文を画像にしない。アイコン以外の画像には `alt` を付ける。
- 原稿の承認後は、承認なしで内容を変えない。
- LibreOffice の画像は近似にすぎない。「PowerPoint で開いて確認してください」と必ず伝える。
- エラーが出たら、原因と対処を示して止まる。推測で別の方法に切り替えない。
````

- [ ] **Step 7: README を書く**

`README.md`:
```markdown
# pptx-deck

テーマまたは原稿から、PowerPoint で編集できる .pptx を作る Claude Code スキル（プラグイン構成）。Windows 専用。

## できること

- 構成案 → 原稿 → HTML プレビュー → PPTX の順に、承認を取りながら進める。
- 本文を画像にせず、ネイティブの図形・テキスト・チャートで出力する。
- はみ出し・重なり・最小フォントサイズ・コントラスト・AIっぽさ（単調さ・色数・余白など）を自動で検査する。
- LibreOffice があれば、PPTX を画像化して崩れを目視確認する。

## 必要なもの

| 必須 | Node 20 以上、Microsoft Edge、BIZ UDPゴシック（または游ゴシック／メイリオ系） |
|---|---|
| 推奨 | LibreOffice、Python と `pip install pymupdf`（画像化） |

## 使い方

```bash
cd skills/pptx-deck
npm install
node scripts/run.js doctor          # 環境診断
node scripts/run.js init deck-work/sample
node scripts/run.js check deck-work/sample/catalog.html
node scripts/run.js build deck-work/sample/catalog.html deck-work/sample/catalog.pptx --work deck-work/sample
npm test
```

通常は Claude Code から「スライドを作って」と頼む（`skills/pptx-deck/SKILL.md` の手順に従う）。

## 注意

- 画像化は LibreOffice による近似で、PowerPoint の表示と完全には一致しない。最終確認は PowerPoint で行う。
- フォントは同梱しない。BIZ UDPゴシックがない環境では代替フォントになり、折り返しが変わることがある。
- このフォルダを OneDrive の配下に置くと、同期の競合で `.git` が壊れることがある。壊れたときは、リモートから取り直す。
- テンプレ（.pptx/.potx）への流し込み、既存 PPTX の修正は未対応。
- ライセンスは未決定（公開前に決める）。
```

- [ ] **Step 8: 全テストを実行する**

Run: `cd skills/pptx-deck && npm test`
Expected: 全件 PASS（LibreOffice 未導入の環境では render 関連が skip）。

- [ ] **Step 9: コミット**

```bash
git add skills/pptx-deck/SKILL.md skills/pptx-deck/samples skills/pptx-deck/scripts/acceptance-check.js skills/pptx-deck/tests/acceptance-check.test.js README.md
git commit -m "docs: SKILL.md・README・受入サンプルと受入チェック"
```

---

### Task 13: 受入確認（サンプル 3 種で通す）

自動テストでは判定できない項目（LLM の作業フロー全体、主観判定、PowerPoint での目視）を確認する。**実装が終わっただけでは完了にしない。**

**Files:** なし（`deck-work/` に成果物ができる。コミットしない）

- [ ] **Step 1: 環境を確認する**

Run: `node skills/pptx-deck/scripts/run.js doctor`
Expected: `[NG]` なし。

- [ ] **Step 2: サンプル 3 種で、SKILL.md の流れを通す**

Claude Code で `samples/01-theme-only.md`、`02-long-script.md`、`03-diagram-chart.md` の依頼文をそれぞれ実行し、SKILL.md の手順（承認を含む）で `deck-work/sample1〜3/deck.pptx` を作る。

- [ ] **Step 3: 機械判定を行う**

```bash
cd skills/pptx-deck
node scripts/acceptance-check.js ../../deck-work/sample1/deck.pptx 10 15
node scripts/acceptance-check.js ../../deck-work/sample2/deck.pptx 10 15
node scripts/acceptance-check.js ../../deck-work/sample3/deck.pptx 10 15
```
Expected: 3 件とも `PASS`。FAIL なら、理由に従って HTML を直して再出力する（SKILL.md の自動修正のとおり、最大 3 回）。

- [ ] **Step 4: 主観判定をユーザーに依頼する**

各サンプルについて、`render/slide-NN.png` をユーザーに示し、「10 枚中 8 枚以上が修正不要か」を判定してもらう。満たさないサンプルは、指摘された点をデザイン（`base.css`／`catalog.html`／SKILL.md の規約）に反映して、再度 Step 2〜4 を行う。

- [ ] **Step 5: PowerPoint での最終確認（開発時のみ）**

3 本の PPTX を OneDrive にアップロードして Web 版 PowerPoint で開き、文字のはみ出し・折り返し・フォントを目視する。余裕率（`wrapSafety`）が足りず崩れた場合は、`config/thresholds.json` を下げて Task 4 のスパイクの結果と合わせて見直す。これはスキル作成時の確認で、スキルの実行フローには含めない。

- [ ] **Step 6: 公式 pptx スキルとの発火の重複を確認する**

`anthropic-skills:pptx` が入った状態で、「スライドを作って」「PowerPoint を作って」と頼み、どちらが発火するかを見る。意図と違うほうが発火する場合は、`SKILL.md` の `description` を調整する（`skill-creator` の description 最適化を使ってよい）。

- [ ] **Step 7: 完了の報告**

受入条件（SPEC）を 1 項目ずつ、満たした根拠（コマンドの出力、枚数、判定結果）を添えて報告する。外部公開は行わない（完成後に別途ユーザーの承認を取る）。

---

## Self-Review

**1. SPEC のカバレッジ**

| SPEC の要求 | 担当 |
|---|---|
| 流れ 1〜7（入力、構成案、原稿＋内容レビュー、HTML、PPTX、検査、報告） | SKILL.md（Task 12）、CLI（Task 11） |
| 承認 2 回／テーマのみは 3 回 | SKILL.md（Task 12） |
| DOM 計測→pptxgenjs、Edge | Task 8、9 |
| 折り返しを PowerPoint に任せる、余裕率、見出しだけ行固定、行間 pt 固定 | Task 4（実測）、8（`wrapStable`、`fixed`）、9（`wrap:false`、`lineSpacing`） |
| 体裁チェック基準（はみ出し・重なり・最小フォント・階層・画像本文・破損） | Task 5、10 |
| 「AIっぽくない」の客観チェック | Task 6 |
| オーバーフロー時の自動修正（最大 3 回、原稿は承認なしで変えない） | Task 6（`suggestFix`）、SKILL.md |
| スライドサイズ 13.33×7.5、フォント、サイズ階層 | Task 7（base.css）、9（LAYOUT_WIDE、`fontFace`） |
| フォント運用（導入確認、代替、同梱しない） | Task 2、11（doctor） |
| 図解 4 種・チャート 3 種（型は `bar/barh/line/pie`）、注目データだけ有彩色、ネイティブチャート | Task 7（catalog）、9 |
| 画像・アイコン、alt、アクセシビリティ（コントラスト 4.5:1） | Task 5、8（SVG→PNG）、9 |
| スピーカーノート | Task 8、9 |
| エラー処理（ブラウザ・フォント・空・巨大な入力） | Task 8、11（doctor） |
| 中間成果物 `deck-work/<名前>/`、一時ファイルは OS の一時フォルダ | Task 11、12 |
| 依存のバージョン固定、導入手順 | Task 1、README |
| 受入条件（サンプル 3 種固定ファイル、0 件、validate、主観判定、スパイク） | Task 4、12、13 |
| 開発時の確認（Web 版 PowerPoint、スキルの実行フローに含めない） | Task 13 |
| 公式 pptx スキルとの発火重複の確認 | Task 13 Step 6 |
| 非目標 | Global Constraints に明記し、対応するタスクを作っていない |

漏れ: SPEC の「余裕率 92% の確定」は Task 4 で行う。「README に OneDrive の git の注意」は Task 12 で書く。

**2. プレースホルダ走査**: 「TBD」「あとで」「適切に」などはない。Task 9 と 10 の Step 4 にある「XML の細部に差があれば実物を見て実装側を直す」は、pptxgenjs の出力が未検証であることへの対処手順で、直す対象と確認方法を示している。

**3. 型の整合**: 要素モデルのキー（`paras`, `lineSpacingPt`, `paraSpaceAfter`, `fixed`, `wrapStable`, `overflow`, `kind`, `radius`, `dir`, `arrow`, `alt`, `src`, `chart`）は、Task 5（ヘルパとルール）、Task 8（生成）、Task 9（消費）、Task 10（読み戻し）で同じ名前を使っている。`objectName` の書式は Task 9 が書き、Task 10 が `NAME` の正規表現で読む（同一）。`runRules` の `stage` は `'html' | 'pptx'`、`suggestFix(violations, attempt, t)` の引数順は Task 6 とタスク 11 で一致している。チャートの `labelPt` は HTML 段階で検査し、PPTX 段階では読み戻せないため固定値 12 とする（Task 10 に明記）。

**4. Review Focus の担当**: 1 → Task 8（空スライド、スライドなし）、2 → Task 8（`overflow`）、3 → Task 8（`data-chart`）、4 → Task 3・8・11（日本語と空白のパス）、5 → Task 11（`doctor`、LibreOffice なしで skip）。

**未確認の前提（実装中に実物で確かめる）**: pptxgenjs 4.0.1 が `objectName`・`wrap:false`・`lineSpacing` を期待どおり XML に書くこと、単一系列の棒グラフで `chartColors` が点ごとの色（`c:dPt`）になること。Task 9 のテストがこれを検出する。
