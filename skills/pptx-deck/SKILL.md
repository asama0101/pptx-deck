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

利用者の作業フォルダに `deck-work/<名前>/` を作り、`node "<skill>/scripts/run.js" init "deck-work/<名前>"` で `base.css`、`chart-preview.js`、`catalog.html`（見本 10 枚）、`diagrams.html`（図解の見本 9 枚）、`charts.html`（チャートの見本 4 枚）をコピーする。構成案・原稿・HTML・検査結果はすべてここに置く（再開できる）。

## 2. 流れ（承認は 2 回。テーマのみの依頼は構成案を加えた 3 回）

1. **入力の確認**: テーマのみか、原稿があるか。対象者・目的・所要時間・枚数が決まらず、外れたときの手戻りが大きいなら先に質問する。あわせて、**トーン（アクセント色）を決める**。`references/design-guide.md` の 1 を読み、一番強く伝えたい性質（trust・growth・alert・energy・premium・neutral）を選び、利用者に 1 行で伝える。
2. **構成案**（テーマのみの場合だけ）: `outline.md` にスライド一覧と、各スライドで言い切るメッセージを書き、**承認を得る**。
3. **原稿**: `script.md` に各スライドの見出し（言い切りの文）、本文、図解かグラフの指定（型と、選んだ理由を 1 行）、スピーカーノートを書く。型は `references/design-guide.md` の 2・3 の表から選ぶ。**表紙の次の 2 枚目は必ずサマリ**にする（全体の要点を 3 点前後、結論を先に。現状・提案・依頼のように言い切る）。次の**内容レビュー**を原稿の承認の前に 1〜2 回行い、直してから示す。
   - 論理の流れ: 結論→根拠→提案の順で、飛躍がないか。
   - 抜け漏れ: 対象者が知りたいことが欠けていないか。
   - 読み手の視点: 専門用語、前提の説明が足りているか。
   **原稿を承認してもらい、内容を凍結する**【承認①】。以降、承認なしに内容を変えない。
4. **HTML プレビュー**: `references/design-guide.md` を読んでから、`deck.html` を書く。`catalog.html`・`diagrams.html`・`charts.html` の見本をコピーして構造を真似る（下の「HTML の書き方」）。`<body data-tone="…">` を必ず付ける。書いたら `check` で合格させてから、承認に出す。ブラウザで開いて見せる**【承認②】**。チャートのプレビューは近似。
5. **PPTX 出力**: `node "<skill>/scripts/run.js" build "deck-work/<名前>/deck.html" "deck-work/<名前>/deck.pptx" --work "deck-work/<名前>"`
6. **結果の報告**（承認は求めない）: 検査結果、`render/slide-NN.png`（LibreOffice の近似）を見て崩れを確認した所見、PowerPoint で開いて最終確認することを勧める旨を伝える。

## 3. HTML の書き方

- **同じ大きさの四角（カード）を並べただけの構成は禁止**（`check` の `cardRow` が 2 個以上で検出する）。内容の関係に合わせて、次から選ぶ。罫線は `pp-line`（`color:var(--neutral-chart)`）、強調は文字色をアクセントにする。
  - 並列の要点・サマリ → 罫線で区切った行（ラベル＋言い切りの文＋補足）。見本 2 枚目。
  - 課題→対策、施策→狙い → 行ごとに左右へ分け、矢印でつなぐ。見本 4 枚目。
  - 経緯・期限 → 時間軸（円＋線）。費用の内訳 → 式（`3,200万円 ＋ 1,080万円 ×5年 ＝ 8,600万円`）。
  - 構成・層 → 面を 1 つにして、中を縦線で分ける（面の中の文字は DOM の子にする）。
  - 大きな数字・式は `data-role="display"`（36pt 既定。タイトルより大きくてよい。最小 24pt）。
- 2 枚目はサマリ（`data-layout="content"`）。見本の 2 枚目を雛形にする。
- 1 枚 = `<section class="slide" data-layout="…">`。`data-layout` は `cover | section | content | diagram | chart | closing`。同じレイアウトを 3 枚以上連続させない。10 枚以上なら図解かグラフを 2 枚以上入れる。
- 使う要素は `pp-text`（`data-role` = `title | lead | body | caption`）、`pp-shape`（`.card` など）、`pp-line`（`data-dir` = `right | left | down | up`、`data-arrow="end"`）、`pp-image`（`alt` 必須。`data-role` = `icon | photo`）、`pp-chart`（`data-chart` に JSON）。それ以外は計測されず、PPTX に出ない。
- **テキストは必ず幅を持たせる**（ブロックとして親に stretch、または `width` 指定）。幅が内容ぴったりだと PowerPoint で折り返しが変わる。`check` の `wrapStable` が検出する。
- 箇条書きは `<div class="pp-text" data-role="body"><ul><li>…</li></ul></div>` と書く。`<p class="pp-text">` の中に `<ul>` は入れられない（HTML の仕様で `<p>` が閉じ、文字が PPTX から消える。`check` が `unmeasured` で検出する）。
- `pp-*` クラスのない要素の文字は PPTX に出ない。
- カードの中の文字は、DOM でもカードの子にする（子は親に含まれていれば重なり扱いにならない）。
- 見出しの改行位置を固定したいときだけ `data-fixed` を付け、`<br>` で改行する。
- タイトルは 1 枚 1 つ、`section.slide` の直下。全角 30 字以内（2 行までなら可）。末尾に句点を付けない。
- **数字の比較はグラフで可視化する**。同じ単位（万円・億円・%・時間・台・倍・件・人など）の数字を 3 つ以上並べて比べるときは、文字や式で並べず、チャートにする（`check` の `numberCompare` が、チャートのないスライドを違反にする）。型は `references/design-guide.md` の 2 から選ぶ。例外は `<section data-numbers="…">` で示す: 円の大きさなど図解で可視化しているなら `visual`、比較ではなく要点の文章（サマリなど）なら `text`。
- **グラフの内訳と差額**: 内訳がある数字は、グラフを積み上げ（`stacked`・`stackedh`）にして内訳を見せる（本文に「内訳」があるのに積み上げでないグラフは、`chartBreakdown` が違反にする。例外は `data-breakdown="none"`）。ただし、見せたいことが推移（累計など）なら、推移を優先して棒や折れ線にし、内訳は文字で添える。累計が積み上がる推移は、累計の棒（`cumulative`）にして、各年の棒を「前年までの累計（無彩色）＋その年の増加分（アクセント色の塊）」に分け、毎年の増加分を色の塊で見せる。グラフで前後や 2 つの差額を見せるときは、**比べる棒を並べたまま、差額を数字の注記（`▲5,800万円`、`＋700万円`）でアクセント色にして書く**（`chartDiff` が、前後のカテゴリを持つグラフに差額の注記がなければ違反にする。例外は `data-diff="none"`）。差額を、実費と同じ見た目の棒や塊にしない（存在しない費用が、あるように読める）。0 のセグメントのラベルは出ない。
- **効果を謳う箇所は before/after で示す**。タイトルで効果（削減・短縮・向上・改善・増加・軽減・回避・効果 など）を謳うスライドは、「導入前／導入後」「現状／移行後」のように、前と後を並べて見せる（ビフォーアフターの図解、前後 2 本の棒グラフ、前→後を矢印でつなぐ行）。`check` の `effectBeforeAfter` が、前と後の対がないスライドを違反にする。効果を謳わない文なら `<section data-effect="none">`。
- **視線設計**（`check` が検査する。詳しくは `references/design-guide.md` の 1）: 矢印は強調したい対象にだけ向ける（`arrowTarget`）。強調（アクセント色）は 1 点に絞る（`isolation`）。強調は右か下に置き、右下を空けない（`zFlow`、警告）。アクセント色は伝えたい性質（`data-tone`）に合わせる（`colorTone`）。
- 図解は、内容の関係から選ぶ（25 種の選び方は `references/design-guide.md` の 3）。作れるのは、フロー（横・縦）、サイクル、ビフォーアフター、ツリー、ピラミッド、放射、マトリクス、数式、項目比較、規模比較、TAM-SAM-SOM、階段、ガントチャート。見本は `catalog.html` の 3・5・6・8・9 枚目と `diagrams.html`。地図・ハニカム・相関図・ベン図・トライアングルなど、斜めの線や六角形が要るものは作れない（代替は同じ表にある）。矩形・角丸矩形・円・直線矢印・テキストだけを使う。
- ガントチャートは、行の帯（`pp-shape`）の子にラベルと棒を置き、棒は最終工程だけアクセント色、他は無彩色にする。
- チャートは 9 種（`bar`、`barh`、`line`、`pie`、`stacked`、`stackedh`、`stacked100`、`area`、`cumulative`）。**データの関係から型を選び、選んだ理由を原稿に 1 行で書く**（表は `references/design-guide.md` の 2）。基本は、注目データだけアクセント色、他は無彩色。`{"type":"bar","labels":[…],"values":[…],"highlight":3,"labelPt":12}`。`cumulative` は `bar` と同じ `labels`・`values`（累計の値。前より減らない）で書く。`stacked`・`stackedh`・`stacked100`・`area` は `values` の代わりに `"series":[{"name":"系列名","values":[…]},…]` を使い、`highlight` は系列の番号。第 2 軸・ウォーターフォール・3D は使わない。
- スピーカーノートは `<aside class="notes">…</aside>`。
- 色はアクセント 1 色と無彩色だけ。装飾バー、タイトル下のアクセント線、長い本文のセンタリングは使わない。
- 文字は本文 14pt 以上（既定 16pt）、注記 10pt 以上。タイトルと本文は 4pt 以上差をつける。
- 写真素材を自動で集めない。画像は利用者が渡したものと、アイコン（SVG 可）だけ。

## 4. 検査と自動修正

`check`／`build` の JSON が `ok: false` なら、`violations` を読んで HTML を直す。`suggestion` に次の一手が出る。`severity: warning`（`zFlow`、トーン未指定）は `ok` を妨げないが、意図がなければ直す。

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
