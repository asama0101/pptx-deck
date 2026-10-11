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
- 箇条書きは `<div class="pp-text" data-role="body"><ul><li>…</li></ul></div>` と書く。`<p class="pp-text">` の中に `<ul>` は入れられない（HTML の仕様で `<p>` が閉じ、文字が PPTX から消える。`check` が `unmeasured` で検出する）。
- `pp-*` クラスのない要素の文字は PPTX に出ない。
- カードの中の文字は、DOM でもカードの子にする（子は親に含まれていれば重なり扱いにならない）。
- 見出しの改行位置を固定したいときだけ `data-fixed` を付け、`<br>` で改行する。
- タイトルは 1 枚 1 つ、`section.slide` の直下。全角 30 字以内（2 行までなら可）。末尾に句点を付けない。
- 図解は 4 種（フロー、2×2 マトリクス、ピラミッド、ツリー）。`catalog.html` の 2・4・6・7 枚目（フロー・マトリクス・ピラミッド・ツリー）を雛形にする。矩形・角丸矩形・円・直線矢印・テキストだけを使う。
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

- 本文を画像にしない。すべての画像（アイコンを含む）に `alt` を付ける。
- 原稿の承認後は、承認なしで内容を変えない。
- LibreOffice の画像は近似にすぎない。「PowerPoint で開いて確認してください」と必ず伝える。
- エラーが出たら、原因と対処を示して止まる。推測で別の方法に切り替えない。
