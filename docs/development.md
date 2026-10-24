# 開発者向けの情報

pptx-deck の内部構造・コマンド・テストの説明。利用者向けの説明は [README.md](../README.md)。

## 依存関係の詳細

`python run.py --data <絶対パス> doctor`（`run.py` はプラグインのフォルダ `plugins/pptx-deck/` にあるもの。スキルの中では `python "${CLAUDE_PLUGIN_ROOT}/run.py" --data "${CLAUDE_PLUGIN_DATA}" doctor`。置き場は環境変数 `PPTX_DECK_HOME` でも指定でき、そちらが優先される）で、下の状態を確認できる（出力は `version`（プラグインのバージョン。`python run.py --version` でも見られる）・`python`（`path` は実行に使っている専用の仮想環境の Python）・`venv`（仮想環境の場所）・`font_biz_udp_gothic`・`warnings`）。

| 区分 | 内容 | 備考 |
|---|---|---|
| 必須 | Windows、Python 3.10 以上（コードが `X \| None` の型注釈を使う。動作確認は 3.14）、Claude Code | `python` が PATH にあること |
| 必須 | 専用の仮想環境（システムの Python は使わない）。置き場 `<置き場>\venv` に承認後に作る（`python-pptx==1.0.2`・`playwright==1.52.0`・`pymupdf==1.28.2`・`lxml==6.1.3`。すべて `==` で固定）。置き場は、スキルの中では `${CLAUDE_PLUGIN_DATA}`（プラグインを更新しても残る）。Playwright の chromium（数百 MB）は Playwright の共有の場所（既定は `%LOCALAPPDATA%\ms-playwright`）に入り、専用の仮想環境の対象外 | `python run.py --data <絶対パス> setup --yes`（`run.py` は `doctor` と同じ、プラグインのフォルダのもの）。作成元の Python は 3.10 以上で、`venv` と `ensurepip` が使えること。導入にはネットワークが要る。承認なしには作らない。システムの Python には何も入れず、読まない。旧い `%LOCALAPPDATA%\pptx-deck\venv` は使わない（新しい置き場に作り直す）。`doctor` の `venv`・`python.path` で使う場所が分かる |
| 推奨（設計図・原稿の確認、スライド案の選択） | Claude Code の Playwright MCP（`browser_navigate`・`browser_evaluate`） | プラグインには同梱しない。案の選択と「回答をコピー」の受け取りに使う。ないときは、HTML を自分で開き、コピーした回答をチャットに貼り付ける |
| 推奨 | BIZ UDPゴシック（フォント） | 未導入だと、計測が代替フォントになり、PowerPoint と折り返しがずれることがある |
| 最終確認 | Microsoft PowerPoint | 確認用の画像は HTML の撮影で、PPTX の実描画ではない。PowerPoint で開いて最終確認する |

LibreOffice は使わない（不要）。

## 作品のフォルダと作成の段階

作品のフォルダは、実行したディレクトリ直下の `<名前>/` で、完成後は次の構成になる。`build` は成功すると、再生成できる派生ファイル（`variants.html`・`final.html`・`theme.css` など）を `source/` から消す。元データは残るので、あとで `revise`・`rebuild` できる。

```
<名前>/
  <名前>.pptx        成果物
  source/            設計図 design.md・原稿 script.md・slides/・answers-*.md・template.json など
```

| 段階 | 内容 | 承認 |
|---|---|---|
| 1. 入力 | 目的・対象・枚数、配色、テンプレートの有無を確認する | |
| 2. 設計図・原稿 | 先に設計図 `design.md`（ガバニングメッセージ・論点 3〜6 個・台帳・ページごとのヘッド・型・レイアウト記述・証拠対応表）を作り、それを `script.md`（題＝20 字以内の名詞句・ヘッドメッセージ＝判断を言い切る 30〜60 字の 1 文・章名・本文・図表の型と理由・必要なときだけ出典・判断の枠）に写す。書式の手本は `assets/sample/`（架空の会社の中期経営計画。表紙＋10 枚） | なし（`lint-script` と自己確認だけ。見たいときは `review-plan` を任意で） |
| 3. スライド案 | 全スライドの案（型違いの A＝第 1 候補、B・C＝次点に、型にとらわれない自由設計の R を加える。図と表を多用する）を 1 つの HTML にまとめる。型を選ぶと、その型のデザイン 1〜3 を選べる（2 段）。左に一覧、右に 1 枚ずつ（大きなスライド → 見どころ・部位のコメント → 案・デザインのサムネ。承認／要修正／全部承認・コメント・「回答をコピー」は画面下に固定。「承認」で次のスライドへ進み、「全部承認」は案が決まっていて判定もコメントもないスライドをまとめて承認し、「要修正」は直す点（コメントか部位のコメント）を書いたときだけ付いて次へ進む。部位のコメントで自動で付いた要修正は、1 回押すと確定して進む。コメントを書いたか、編集モードで文字を直したのに判定のないスライドがあると、「回答をコピー」はそのスライドへ移って止まる）で見て、「回答をコピー」を押す（Claude が約 100 秒ごとに送信を確認し、約 30 分（18 回）で届かなければ続行方法を質問して止まる。Playwright MCP がないときはチャットに貼り付ける）。コメントのあったスライドは、前回のコメントと今回の直しを添えて、直した 1 案だけを再提示する | HTML 上で選択（唯一の承認） |
| 4. 最終 HTML | 選ばれた案を統合する（`final-review.html` は完成後に全体を見返す参照用で、承認は求めない） | |
| 5. PPTX | HTML の位置を測り、テンプレートを土台に PowerPoint の要素として書き出す。体裁を検査し、確認用の画像（`final.html` の撮影）で崩れを確認する。確認後は `clean` で一時の画像を消す | |


### 絵（型に当てはまらない図）の流れ

`diagram` は、次の順に進む。承認は案の選択の 1 回で、ほかのページは内容の合意。2 の提案と構造の確認（`picture-review.html`）は、create の承認②（スライド案の選択）とは別の確認で、絵の内容を合意するためのもの。

| 段階 | 内容 | 利用者の操作 |
|---|---|---|
| 1. 入力 | 文章・ファイル（md・txt・docx・pdf・html）・画像・既存 PPTX の図から、要素・関係・強調する 1 点を読み取る。足りなければチャットの選択式で聞く（数字・固有名詞は作らず、分からない値は「xx」） | 質問に答える |
| 2. 提案と構造の確認 | `picture-plan.json` から `picture-review.html` を作る。絵にする箇所の提案（「図にして」と頼んだ箇所は省く）と、読み取った構造の各項目を確認する | 提案ごとに する／しない、構造ごとに OK／修正（HTML） |
| 3. 案 | 要素が少なければ 1 案、多ければ構図の違う 2〜3 案を `slides/NN-A.html` に描く。`draft` で確認用の画像と検査の結果を得る | 案が複数なら構図を選ぶ（HTML） |
| 4. 往復 | 確認用の画像を見ながら、チャットの指示で描き直す。直す前に `history snapshot` で版を残し、戻すときは `history restore` | チャットで指示 |
| 5. PPTX | `finalize` → `build`（絵は画像として貼られ、PowerPoint では直せないこと、機密を含まないかを利用者に一言伝える。最終確認の承認は挟まない）。直しは完成後に `revise` か 4 の往復 | |

絵は `<div class="pp-picture" data-alt="…">` の中のインライン SVG。`build` が Chromium で絵の範囲だけを透過・3 倍の PNG にして貼る。部品（機器アイコン・矢じり）は `assets/pictures/parts.svg`、見本 5 種は `assets/components/pictures/`、書き方と作法は `references/picture-craft.md`。

## 部品の種類と使い分け

`plugins/pptx-deck/assets/components/` に 51 型・147 本ある（一覧は `部品見本.html`）。1 つの型に最大 3 つのデザイン（`<型>.html`・`<型>-d2.html`・`<型>-d3.html`）があり、同じ原稿のまま形だけを選べる（`cover`・`effort`・`relation` は 1 つ）。各部品の先頭のコメントに「用途」と「差し替える所」（デザイン 2・3 は「デザイン 1 との違い」）がある。設計図の「型」はここから選び、第 1 候補・次点は `references/patterns.md`（型の選定表）で決める。

**共通の構成** 題（名詞句 20 字以内）→ ヘッドメッセージの帯（判断を言い切る 30〜60 字）→ チャートタイトル → 図表本体 → 注。**判断を求める型**（`decision`・`summary`・`decisions`・`argument`・`options`・`raci`・`actions`・`gantt`）は最下部にメッセージボックス（「論点　〜の可否」）を置く。**情報の型**はメッセージボックスを置かず、注釈の末尾を「→ 含意」で締める。

問い（何を見せたいか）で 9 区分に分ける。

| 区分 | 型 |
|---|---|
| 1 ページの骨格 | `cover`（表紙）・`agenda`（目次）・`section`（章扉）・`closing`（裏表紙。要点の再掲と次のステップ） |
| 2 判断を求める・要約する | `decision`（クロージング決定）・`summary`（数字サマリ・障害の概要）・`decisions`（論点｜決定｜根拠）・`argument`（課題→現状→打ち手の論証）・`options`（案の評価表）・`raci`（役割分担） |
| 3 同格のものを並べる・位置づける | `parallel`（並列）・`positioning`（4 象限）・`venn`（重なり・絞り込み）・`text`（文だけ）・`screenshot`（画面） |
| 4 前後・左右で比べる | `before-after`（工程・体制の前後）・`delta`（数値の前後） |
| 5 順を追う | `flow-h`・`flow-v`・`flow-text`・`flow-box`・`swimlane`（担当をまたぐ手順）・`steps`（階段）・`cycle-2`（2 要素の往復）・`cycle`（3〜6 要素の循環） |
| 6 時間で測る | `timeline`（発生順の事象）・`gantt`（工程×時間）・`roadmap`（更改計画） |
| 7 構成・範囲を見せる | `architecture`（層）・`topology`（系統）・`org`（体制）・`enclosure`（包括）・`area`（担当領域）・`site-matrix`（配置表） |
| 8 要因・内訳に分解する | `tree`・`cause`（原因の連鎖）・`formula`（数式）・`funnel`（じょうろ型）・`pyramid`・`relation`（相互関係） |
| 9 数値で見せる | グラフ `bar`・`hbar`・`line`・`stacked`・`pie`・`waterfall`（デザイン 1＝グラフだけ、2＝グラフ＋内訳表、3＝グラフ＋結論カード）、表 `cost`・`quote`・`effort`・`spec`（検証の計画と結果）・`actions`（対応一覧） |

### 文書の種類と使う型

| 文書 | 冒頭 | 本体でよく使う型 | 結び |
|---|---|---|---|
| 稟議 | `summary`・`decisions` | `options`・`cost`・`quote`・`delta`・`waterfall`・`effort`・`actions`・`flow-h`・`gantt`・`org` | `decision`・`closing` |
| 障害報告 | `summary` | `timeline`・`cause`・`tree`・`before-after`・`actions` | `decision`・`closing` |
| 検証計画 | `summary` | `spec`・`architecture`/`topology`・`org`・`raci`・`gantt`・`options` | `decision`・`closing` |
| 検証結果報告 | `summary` | `spec`（結果）・`bar`/`line`・`actions` | `decision`・`closing` |
| 業務フロー | `section` | `swimlane`・`before-after`・`raci`・`cycle` | `decision`・`closing` |
| 設計書 | `agenda` | `architecture`/`topology`・`spec`・`options`・`site-matrix` | `summary`・`closing` |
| 設備増減の計画 | `summary` | `delta`・`site-matrix`・`roadmap`・`parallel`・`stacked`/`waterfall`・`cost` | `decision`・`closing` |

内容に合う型がなければ、`diagram` で絵にする（上の「絵の流れ」）。新しい型を作ったら `assets/components/` に足し、`check` で違反が 0 件になることを確かめる。

## ファイルの置き場所

| 場所 | 内容 |
|---|---|
| `.claude-plugin/marketplace.json` | プラグインの配布の定義（マーケットプレイス名 `pptx-deck-market`） |
| `plugins/pptx-deck/`（プラグイン） | `.claude-plugin/plugin.json`（プラグインの定義）、`run.py`（コマンドの入口）、`requirements.txt`（仮想環境に入れるもの）、`skills/`（`create`・`revise`・`rebuild`・`review-plan`・`diagram` の各 `SKILL.md`）、`pptx_deck/`（Python のコード）、`references/`（SKILL.md から参照する資料。`components.md`＝型の一覧と使い分け、`patterns.md`＝型の選定表、`html-rules.md`＝HTML の書き方と描画の規準、`head-rules.md`＝題とヘッドメッセージ（ヘッド）の規則、`review-flow.md`＝スライド案のレビューと統合の細則、`check-rules.md`＝検査の rule と直し方、`picture-craft.md`＝絵の作法）、`assets/` |
| `plugins/pptx-deck/assets/` | `components/`（51 型・147 本の HTML 断片。1 型に最大 3 つのデザイン。本文の部品は「題 → ヘッドメッセージ → チャートタイトル → 本体 → 注釈」の構成で、判断を求める型は最下部にメッセージボックスを置く）、`web/`（`base.css`・`chart-preview.js`。作業フォルダとレビューページが使う）、`icons/`（アイコン 123 種。一覧は `references/icons.md`。それぞれ `accent`・`emphasis`・`white`・`gray` の 4 色）、`template/standard.potx`（既定のテンプレート）、`sample/`（設計図と原稿の書式の手本）、`pictures/parts.svg`（絵の部品。機器アイコン 12 種と矢じり）、`components/pictures/`（絵の見本 5 種） |
| `tests/` | 単体・通しのテスト（`pytest`。実行方法は後述） |
| `部品見本.html`（リポジトリ直下） | 部品 51 型・147 本の見本を 9 区分で 1 ページに並べた一覧（ブラウザで開く。画像はファイルに埋め込み済み）。画像は以前に描いたもので、このリポジトリには作り直す手順（生成スクリプト）がまだない。部品を足したり直したりしても、見本は自動では更新されない |
| 実行したディレクトリ直下の `<名前>/` | `<名前>.pptx`（成果物）と `source/`（`design.md`・`script.md`・`slides/`・`answers-*.md`・`history/`（絵の往復の版）・`material/`（利用者の画像の素材）・`template.json` など。作業中だけ `variants.html`・`final.html`・`final-review.html` ほか） |
| OS の一時フォルダ `%TEMP%\pptx-deck\<名前>-<作業フォルダのハッシュ 8 桁>\` | 確認用の画像など一過性のもの（同名の別の作品と混ざらない） |

## コマンド

普段はスキルが呼ぶので、直接実行する必要はない。`python run.py --data <絶対パス> <コマンド>`（`run.py` は `plugins/pptx-deck/` にある。`--data` は先頭に置く。環境変数 `PPTX_DECK_HOME` を設定すれば省ける）。どちらもなければ、終了コード 3 で止まる。

| コマンド | 内容 |
|---|---|
| `doctor` | 専用の仮想環境の場所と使う Python のパス、足りないもの、フォントの有無を確認する |
| `setup [--yes]` | 仮想環境（`<置き場>\venv`。置き場は `--data`＝スキルでは `${CLAUDE_PLUGIN_DATA}`、または `PPTX_DECK_HOME`）と chromium を入れる。`--yes` は利用者の承認後に付ける |
| `init <名前> --color … [--template …] [--footer …]` | 作業フォルダ `<名前>/source/` を作る（`--footer` は左下のコピーライト）。`--force` で既存の派生ファイルを上書きする（渡さなかった `--color`・`--template`・`--footer` は既存の値を残す。前の利用者テンプレートのファイル（`_template/` の写し）が消えているのに `--template` がないときは、標準に替えず終了コード 2 で止める。標準テンプレートで作った作品なら、標準から写し直す。テンプレートの出どころの記録（`template.json` の `custom_template`）がない古い作業フォルダは、利用者テンプレートとみなして止める。テーマ・基本 CSS の更新は `init --force`、派生ファイルの作り直しは `reopen`）。出力の `layout_map` は、テンプレートのレイアウトと、章扉・目次・型との推定結果 |
| `template-map <名前> [--set 型=レイアウト名] [--clear 型]` | レイアウトとの対応を出す。`--set agenda=目次`・`--set gantt=スケジュール` のように直し、`--clear gantt` で本文での代用に戻す（`template.json` に反映） |
| `lint-script <script.md>` | 原稿の書式・題・ヘッドメッセージを検査する |
| `review-plan <名前> [--round N]` | 設計図と原稿の確認ページ `plan-review.html` を作る |
| `variants <名前> [--round N]` | スライド案の選択ページ `variants.html` を作る |
| `finalize <名前> [--answers …]` | 選ばれた案を統合して `final.html` と `final-review.html` を作る |
| `apply-edits <名前> [--answers …]` | 回答の `- 編集:` を `source/slides/*.html` へ反映する（直前に `history` へ `before-apply-edits` の版を残す。`final.html`・`final-review.html` は消す。回答に `- 編集の反映: 済み` を足す）。反映後は `finalize` をやり直す。反映できなかった編集（断片がない・対象が合わない・記録された元の文字と今の断片の文字が違う・読めない行）は標準エラーに回答名・断片・対象・理由で列挙し、終了コード 1 で終わる（反映できるものは反映し、反映済みの印も足すので、止まり続けることはない）。未反映の編集があると `finalize`・`review-final`・`build`・`export-html` は終了コード 2 で止まる |
| `set-color <名前> <プリセット名\|#RRGGBB>` | 配色（navy・green・gray・作品の独自色）を `template.json` と `theme.css` に反映する。PPTX があるときは、これで変えてから `build` する |
| `output-format <名前>` | 回答の `- 出力形式:` の最新（`pptx`・`html`・`both`。なければ `pptx`）を 1 語で出す |
| `export-html <名前> [--out <パス>] [--prune]` | `final.html` から、CSS・JS・画像を埋め込んだ 1 枚の HTML `<名前>/<名前>.html` を作る。`--prune` は終わったあとに派生ファイルを消す（出力形式が `html` のとき） |
| `review-final <名前>` | 参照用ページ `final-review.html` だけを作り直す |
| `check <final.html>` | 体裁を検査する（`build` の前に見るとき） |
| `build <名前> [--footer …] [--out …] [--force]` | PPTX を書き出し、検査と確認用の画像を作る。`--out` が既存のファイルなら `--force` がない限り上書きせず終了コード 4。既定の出力先の PPTX が前回のビルド後に変更されている、または `build.json` に記録がない（元の資料を置いたときなど）ときも、`--force` がない限り終了コード 4（PPTX がまだないときは止めない）。`--out` がフォルダ、または拡張子が `.pptx` でないときは測定の前に終了コード 2 で止める。出力先に書けないとき（PowerPoint で開いているなど）も測定の前に終了コード 2 で止める。成功すると派生ファイルを消す |
| `reopen <名前> [--force]` | 派生ファイルを作り直し、PPTX が手直しされていないかを調べる。`--force` は変更されていても、記録がなくても続ける（手直しや元の PPTX は消える）。PPTX が変更されている（`modified`）、または記録がない（`unrecorded`）と終了コード 4 |
| `clean <名前>` | 一時フォルダの確認用の画像を消す |
| `draft <名前> [--slide NN] [--pick A]` | `slides/` の断片を束ね、確認用の画像と検査の結果を返す（絵の往復用。PPTX は出さない。画像は実行ごとの一時フォルダに出し、1 日より古いものは消す） |
| `review-picture <名前> [--round N]` | `picture-plan.json` から、絵にする箇所の提案と構造の確認ページ `picture-review.html` を作る |
| `picture-status <名前>` | `answers-picture-*.md` から、絵にする箇所・直す項目・未決を出す（終了コード 0＝構造を凍結してよい） |
| `history <名前> snapshot\|list\|restore [版] [--label …] [--slide NN]` | 絵を直す前の `slides/` の版を `source/history/NNN/`（版の番号だけの名前。ラベルは中の `label.txt`）に残す・一覧・戻す。並行して実行しても版の番号は重ならない。`restore` は `final.html`・`final-review.html` を消す（`finalize` をやり直す）。`build` は消さない。`--slide` は 2 桁の番号で、その版に断片があるものだけ（違えば版を作らずに終了コード 2） |

### 画面での編集・配色・出力形式

`variants.html`・`final-review.html` の上部の「編集モード」のスイッチを入れると、大きな 1 案の文字をその場で直せる。

- 直せる対象: `pp-text`、表のセル（セル内の段落・箇条書きは 1 つずつ）、グラフのラベル（カテゴリ名・系列名。数値は直せない）。`pp-shape` は文字を持たないので対象外。絵（`pp-picture`）の中の文字も直せない。
- 「リセット」で、押したツールバーのスライドの、フォーカス中（なければ最後に選んだ範囲を含む）の段落・セルを元の内容に戻し、その `- 編集:` の記録も消す（グラフのラベルは対象外）。
- 許す装飾: 太字・改行・テーマ色のクラス・任意の色・文字サイズ。これ以外は取り除かれる。
- 直した内容は、回答の `## SNN` の下に `- 編集: {"f","t","before","after"}` の 1 行で出る。直しただけでは判定にならないので、直したスライドも「承認」か「要修正」を押す（押していないと「回答をコピー」がそのスライドへ移って止まる）。`apply-edits` が断片へ文字列で書き戻す（元の文字が一致するかは確かめずに上書きする。直前の版が `history` に残るので、戻すときは `history restore`）。`apply-edits` が終了コード 1 で終わったときは、標準エラーに出た編集だけが入っていない。断片か回答を直して `--answers <回答ファイル>` を付けて再実行する（その回答の編集をすべて読み直す）か、断片を手で直す。`final-review.html` で直した編集は、`variants.html` と同じく「回答をコピー」した内容を `source/answers-final.md` に保存してから、`apply-edits` と `finalize` をやり直す。反映後は `finalize`（回を続けるなら `variants --round N+1`）をやり直す。
- `variants.html` だけ、配色（navy・green・gray・作品の独自色）の切り替えと、出力形式（PPTX・HTML・両方）の選択がある。読み込み時から変えたときだけ、回答に `- 配色: <名前または #RRGGBB>`・`- 出力形式: pptx|html|both` が出る。`finalize` は成功後に最新の配色を `template.json` と `theme.css` へ反映する（PPTX が既にあるときは警告だけで、変えるには `set-color` → `build`）。一度反映した回答の配色は、`set-color` で変えたあとの `finalize` で戻さない。あとの回のページで同じ色を選び直したときは反映する。`reopen` は配色を変えない。

出力形式が `pptx` なら `build`、`html` なら `export-html --prune`、`both` なら `export-html` のあとに `build` を実行する。

同じ作業フォルダで `build`・`draft` などを並行して実行することは対応していない。ただし、片付け（`build` 成功時の prune）は、作ってから 10 分以内の `draft-*.html` を消さない。

HTML 出力の注意:

- スライドを縦に並べた 1 ファイルで、編集の画面は付かない。
- グラフはブラウザの近似で描くので、軸や桁区切りは PowerPoint のグラフと一致しないことがある。
- 画面上の配色切り替えは、アイコンの `<img src="icons/*-accent.svg">` の色に追従しない（既知の制限）。

## テスト

リポジトリのルートで、専用の仮想環境の Python を使って実行する。置き場（開発用の任意の場所）に、`setup --yes` で仮想環境を作っておく（システムの Python に `playwright` がないと、ブラウザを使うテストはエラーになる。そのテストには `slow` マークが付き、`-m "not slow"` で除ける）。

    python plugins/pptx-deck/run.py --data <置き場> setup --yes
    "<置き場>\venv\Scripts\python.exe" -m pip install -r requirements-dev.txt
    set PYTHONUTF8=1
    set PPTX_DECK_HOME=<置き場>
    "<置き場>\venv\Scripts\python.exe" -m pytest
    "<置き場>\venv\Scripts\python.exe" -m ruff check .
    "<置き場>\venv\Scripts\python.exe" -m ruff format --check .

## 自動検査

`build` の前後に、文字のはみ出し・取りこぼし（入れ子の `ul` など PPTX に入らない書き方）、グラフ指定と画像の `src` の誤り、図形の重なり（テンプレートのヘッダー・フッターを含む）、文字サイズの下限（本文 14pt・注記 10pt）、文字のコントラスト比（4.5:1。大きい文字は 3:1）、画像の使い方（本文を画像にしない。絵は `pp-picture`）を検査する。絵は、代替テキスト（`data-alt`）・中の文字の大きさ（14pt 以上）・絵の外へのはみ出し・色（テーマの変数以外は警告）・文字どうしの重なり（警告）も見る。絵の内部の重なりは検査しない。あわせて、ダッシュ（—）、同じ文言の 1 枚内の重複、1〜2 字の孤立改行、本文の下の空白帯を警告する（警告では出力を止めない）。違反は JSON で返る。破線・点線は PowerPoint の線種で書き出し、グラフの軸は `data-chart` の `axis` で最小・最大・目盛を固定できる。

`lint-script` は原稿の書式と題（20 字以内の名詞句）、ヘッドメッセージの規則（30〜60 字・判断語か接続語・「A。B」の二段構え・ダッシュ・「本ページ」などの自己言及・隣り合う 3 枚の文型の連続）、論点の個数（3〜6）を検査する。スライドは `S01`〜`S99` の 99 枚までで、`slides/` の断片の名前（`NN-A.html`・`NN-A-d2.html` の形）が合わないファイルは名前を挙げて止める。利用者が書くファイル（原稿・設計図・回答・メモ・`picture-plan.json`）は UTF-8（BOM 付きも可）で保存する。UTF-8 でなければ「UTF-8 で保存してください」と止まる。

本文スライドに「題」がなければ、`lint-script` が案内を出す（エラーではない。ヘッドメッセージはそのまま題の代わりになるので、`- 題:` を足す）。ヘッドメッセージの規則（判断語・長さなど）で `lint-script` に落ちたときは、直すか、正しいヘッドメッセージなら `pptx_deck/script_lint.py` の `_JUDGE` に語を足す。

古い作業フォルダは `base.css`・`theme.css`・`chart-preview.js` が `init` 時の写しなので、新しい部品（`f-soft2`・`dashed`・縦の破線の `vl`・`axis`・絵の `pp-picture`・`sv-f-*`）を使うには `init --force` で更新する（`reopen` は派生ファイルを作り直す）（`script.md` などの既存ファイルは消えない。`design.md` は既にあれば上書きしない）。テンプレートの専用レイアウト（章扉・目次・型ごと）の対応も、`template.json` を作る `init` で入るので、古い作業フォルダは `init --force` で作り直す。原稿のキー `見出し` は `ヘッドメッセージ` に改称したので、古い `script.md` は書き換える。
