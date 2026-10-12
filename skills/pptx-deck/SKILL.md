---
name: pptx-deck
description: テーマや原稿から、編集可能で AI っぽくない PowerPoint(.pptx)を作る。構成案→原稿→HTML プレビュー→PPTX の順に承認を取りながら進め、体裁を自動検査する。「スライドを作って」「資料を作って」「PowerPoint を作って」「プレゼン資料」「デッキ」と頼まれたときに使う。既存 PPTX の編集やテンプレ(.potx)への流し込みには使わない。Windows 専用。
---

# pptx-deck

テーマまたは原稿から、PowerPoint で編集できる .pptx を作る。本文を画像にしない。13.33×7.5in（16:9）、BIZ UDPゴシック、無彩色＋基調のアクセント＋強調色 1 色（コンサル資料風）。

以降の `<skill>` は、このファイルがあるフォルダ（`skills/pptx-deck`）を指す。コマンドはすべて `node "<skill>/scripts/run.js" …`。設計の詳細は `references/design-guide.md`。

## 0. 初回だけ

1. `cd "<skill>" && npm install`
2. `pip install pymupdf`（画像化に使う。LibreOffice も推奨）
3. `doctor` が `[NG]` を出さないことを確認する。`[警告]` は画像化が使えないだけで、幾何検査は動く。

## 1. 作業フォルダ

`deck-work/<名前>/` を作り、`init "deck-work/<名前>"` で、`base.css`・`chart-preview.js`・`icons/` を書き出す（`deck.html` が相対パスで読む）。構成案・原稿・HTML・PPTX はここに置く（再開できる）。見本 5 種（内訳は guide の 7）はコピーせず、`<skill>/design/` を直接読む。確認用の画像（`render/`）と検査結果（`report.json`）は、作業フォルダではなく OS の一時フォルダ `pptx-deck/<作業名>/` に出る（`build` の出力の `tempDir`・`reportPath`）。配色を変えたら `icons "deck-work/<名前>"` でアイコンを作り直す。

**ファイルの置き場所**（原則: `deck.html` が読むものは作業フォルダ、手本はスキル、使い捨ては OS の一時フォルダ）

| 置き場所 | ファイル | 役割 |
|---|---|---|
| スキル `<skill>/`（読み取り専用） | `design/` の見本 5 種・`base.css`・`chart-preview.js`・`japan-map.json`、`references/`（guide・`icons/`）、`scripts/`、`config/` | 手本・原本・コード。作業中に書き換えない |
| 作業フォルダ `deck-work/<名前>/` | `outline.md`（構成案）、`script.md`（原稿）、`deck.html`（プレビュー、PPTX の元）、`deck.pptx`（最終成果物） | Claude と `build` が作る |
| | `base.css`・`chart-preview.js`・`icons/` | `deck.html` が読む。`init` が原本から写す。配色はここで変える |
| OS の一時フォルダ `%TEMP%\pptx-deck\<作業名>\` | `render/`（PDF・PNG）、`report.json` | 確認用の画像と検査結果。消さない（OS の掃除に任せる） |

## 2. 流れ（承認は 2 回。テーマのみの依頼は構成案を加えた 3 回）

1. **入力の確認**: テーマのみか、原稿があるか。対象者・目的・所要時間・枚数が決まらず、外れたときの手戻りが大きいなら先に質問する。あわせて**トーン（アクセント色）を決める**: guide の 1 から、一番強く伝えたい性質を選び、利用者に 1 行で伝える。
2. **構成案**（テーマのみの場合だけ）: `outline.md` にスライド一覧と、各スライドで言い切るメッセージを書き、**承認を得る**。
3. **原稿**: `script.md` に各スライドの次の項目を書く。型は guide の 2・3 から選ぶ。
   - 章名（そのスライドが答える問い。例「3案のどれを選ぶか」）と、見出し（問いへの答えを言い切る文）
   - 本文
   - 図解かグラフの指定（型と選んだ理由を 1 行）
   - 判断が要るスライド（比較・費用・計画・リスク・判定）だけ、判断の枠（決めること・期限・推奨）。説明が目的のスライドには付けない
   - 比較・評価がある場合の記号（玉＝満ちるほど良い、棒＝長いほど良い、四角 3 つ＝リスク、◆＝判断点）と、推奨する案（橙にする対象）
   - スピーカーノート**2 枚目は必ずサマリ**（要点 3 点前後、結論を先に）。原稿の承認の前に**内容レビュー**を 1〜2 回行い、直してから示す: 論理の流れ（結論→根拠→提案）、抜け漏れ、読み手の視点（専門用語・前提）。
   **原稿を承認してもらい、内容を凍結する**【承認①】。以降、承認なしに内容を変えない。
4. **HTML プレビュー**: guide を読み、`<skill>/design/` の見本を読み、その構造を真似て `deck.html` を書く（節 3）。`<body data-tone="…">` を必ず付ける。`check` に合格させてから、ブラウザで開いて見せる**【承認②】**。チャートのプレビューは近似。
5. **PPTX 出力**: `build "deck-work/<名前>/deck.html" "deck-work/<名前>/deck.pptx" --work "deck-work/<名前>"`
6. **結果の報告**（承認は求めない）: 検査結果と、`build` の出力の `pngs`（一時フォルダの `render/slide-NN.png`。LibreOffice の近似）を見て崩れを確認した所見を伝え、PowerPoint で開いて最終確認することを勧める。

## 3. HTML の書き方

**構造**
- 1 枚 = `<section class="slide" data-layout="…">`。`data-layout` は `cover | section | content | diagram | chart | closing`。同じレイアウトを 3 枚以上連続させない。10 枚以上なら図解かグラフを 2 枚以上入れる。
- 使う要素は `pp-text`（`data-role` = `title | lead | body | caption | display`）、`pp-shape`、`pp-line`（`data-dir`、`data-arrow="end"`）、`pp-image`（`alt` 必須。`data-role` = `icon | photo`）、`pp-chart`（`data-chart` に JSON）。**これ以外のクラスの文字は計測されず、PPTX に出ない**（`unmeasured`）。
- テキストは必ず幅を持たせる（`wrapStable`）。面の中の文字は DOM でも面の子にする。箇条書きは `<div class="pp-text"><ul>…</ul></div>`（`<p>` の中に `<ul>` は入れない）。
- タイトルは 1 枚 1 つ、`section.slide` の直下。全角 30 字以内、末尾に句点なし。改行位置を固定したいときだけ `data-fixed` と `<br>`。
- スピーカーノートは `<aside class="notes">…</aside>`。文字は本文 14pt 以上、注記 10pt 以上、タイトルと本文は 4pt 以上差をつける。

**見せ方のルール**（検査名と例外。理由と書き方は guide）
- 同じ大きさの四角を並べない（`cardRow`）。内容の関係に合わせて、罫線で区切った行・矢印・時間軸・式・面の分割・図解を選ぶ。
- 同じ単位の数字を 3 つ以上比べるときはチャートにする（`numberCompare`。例外 `data-numbers="visual|text"`）。型は guide の 2。
- 内訳は積み上げ（`chartBreakdown`。例外 `data-breakdown="none"`）。前後を比べるグラフは差額を `▲5,800万円` の注記で書く（`chartDiff`。例外 `data-diff="none"`）。累計の推移は `cumulative`。→ guide の 5
- 効果を謳うタイトルは、前と後を並べて示す（`effectBeforeAfter`。例外 `data-effect="none"`）。→ guide の 4
- 視線設計: 矢印は強調対象にだけ（`arrowTarget`）、強調は 1 点（`isolation`）、右下を空けない（`zFlow`）、色は `data-tone` に合わせる（`colorTone`）、橙は推奨・承認の語があるスライドだけ（`accent2Reco`、警告）。→ guide の 1
- 図解は内容の関係から選ぶ（guide の 3。見本は `diagrams.html` の 18 枚）。矩形・角丸矩形・円・三角形・直線矢印（水平・垂直・斜め）・テキストで作る。地図は日本全国の都道府県の輪郭（`design/japan-map.json`）、立体は平面の重ね。六角形が要るもの（ハニカム）は作れない。
- チャートは 10 種（棒・横棒・折れ線・円・積み上げ・横積み上げ・100% 積み上げ・面・累計の棒・ウォーターフォール）。選んだ理由を原稿に 1 行で書く。第 2 軸・3D は使わない。書き方は guide の 2 と `charts.html`。

**色と部品**（guide の 6）
- 色は無彩色＋基調のアクセント＋強調色（橙）の 2 色まで。橙は「推奨・承認を求める案」だけ（guide の 6）。判断が要るスライドは、見出しの下に判断の枠（決めること・期限・推奨）を置く。表（行×列）と、図の横の説明パネルは使わず、図の中のラベルで説明する。装飾バー、タイトル下のアクセント色の線、長い本文のセンタリングは使わない。
- アイコン（`pp-shape dot` の中に `pp-image`）、章タグ・出典・ページ番号・結論の帯（`data-chrome` を付ける）を使ってよい。数字があるスライドは出典を書く（`sourceMissing`。例外 `data-source="none"`）。
- 写真素材を自動で集めない。画像は利用者が渡したものと、同梱のアイコンだけ。

## 4. 検査と自動修正

`check`／`build` の JSON が `ok: false` なら、`violations` を読んで HTML を直す。`suggestion` に次の一手が出る。`severity: warning` は `ok` を妨げないが、意図がなければ直す。

| action | やること |
|---|---|
| `none` | 違反なし。次へ進む |
| `widenText` | 折り返しの不安定さだけが原因のとき。テキストの幅を広げる（親の padding・gap を縮める）。効かなければ `shrinkFont` |
| `reduceSpacing` | カードの padding と gap を縮める |
| `tightenLineHeight` | line-height を 1.4 に（下限 1.3） |
| `shrinkFont` | フォントを下げる（本文 14pt・注記 10pt の下限は割らない） |
| `proposeSplitOrTrim` | 自動修正の上限（3 回）。**スライドの分割案と文章の削減案をユーザーに示し、承認を得てから**原稿を変える |
| `manual` | 重なり・配置などは HTML を直接直す |

修正のたびに `--attempt <これまでの修正回数>` を付けて再実行する。PPTX の再出力は、出力後検査で違反が出たときに限る。

## 5. 守ること

- 原稿の承認後は、承認なしで内容を変えない。
- エラーが出たら、原因と対処を示して止まる。推測で別の方法に切り替えない。
