# pptx-deck

ビジネス上の承認文書（稟議・提案・計画）を、コンサル資料のテイストで作る Claude Code スキル。設計図と原稿の承認 → HTML スライド案（各 3 案）の選択 → 最終 HTML の承認 → 編集可能な PowerPoint(.pptx) の順に進める。Windows 専用。

- 本文を画像にせず、PowerPoint の図形・文字・表・グラフで出力する（編集できる）。
- 13.33×7.5in（16:9）、BIZ UDPゴシック、無彩色＋基調 1 色＋強調 1 色。配色はプリセット（紺・緑・灰）か、基調色 `#RRGGBB` の指定で変えられる。
- 利用者の PowerPoint テンプレート（`.potx`／`.pptx`）がある場合は、**表紙・裏表紙・ヘッダー・フッター**がそれに従う（マスター／レイアウトが残る）。フォントと配色はテンプレートにかかわらず固定。
- 既存の PPTX の編集と、テンプレートの本文スライドの流用には使わない。

## 依存関係

`python run.py doctor`（`run.py` はプラグインのフォルダ `plugins/pptx-deck/` にあるもの。スキルの中では `${CLAUDE_PLUGIN_ROOT}/run.py`）で、下の状態を確認できる（出力は `python`（`kind` は `system` か `venv`。`system_missing` はシステムの Python に足りないもの）・`venv`・`font_biz_udp_gothic`・`warnings`）。

| 区分 | 内容 | 備考 |
|---|---|---|
| 必須 | Windows、Python 3.10 以上（コードが `X \| None` の型注釈を使う。動作確認は 3.14）、Claude Code | `python` が PATH にあること |
| 必須 | システムの Python に `python-pptx`・`playwright`・`pymupdf`・`lxml`・chromium がそろっていればそれを使う。なければ `%LOCALAPPDATA%\pptx-deck\venv` に承認後に作る（`python-pptx==1.0.2`・`playwright==1.52.0`・`pymupdf==1.28.2`・`lxml>=5`、Playwright の chromium は数百 MB） | `python run.py setup --yes`（`run.py` は `doctor` と同じ、プラグインのフォルダのもの）。導入にはネットワークが要る。承認なしには作らない。システムの Python には何も入れない。`doctor` の `python.kind`（`system` か `venv`）で使われる方が分かる |
| 推奨（スライド案・最終 HTML の確認） | Claude Code の Playwright MCP（`browser_navigate`・`browser_evaluate`） | プラグインには同梱しない。案の選択と「回答をコピー」の受け取りに使う。ないときは、HTML を自分で開き、コピーした回答をチャットに貼り付ける |
| 推奨 | BIZ UDPゴシック（フォント） | 未導入だと、計測が代替フォントになり、PowerPoint と折り返しがずれることがある |
| 最終確認 | Microsoft PowerPoint | 確認用の画像は HTML の撮影で、PPTX の実描画ではない。PowerPoint で開いて最終確認する |

LibreOffice は使わない（不要）。

## 導入

プラグインとして導入する（GitHub に公開した後）:

    /plugin marketplace add asama0101/pptx-deck
    /plugin install pptx-deck@pptx-deck-market

公開せずに手元のフォルダから導入する（push なし。外部には何も送らない）:

    /plugin marketplace add C:\Users\<ユーザー名>\...\pptx-deck
    /plugin install pptx-deck@pptx-deck-market

導入元は作業ツリーそのものなので、ブランチを切り替えると導入したプラグインの中身も変わる。導入後は `/reload-plugins` で一覧に `pptx-deck:create` などが出ることを確認する。

開発中にローカルで試す: `claude --plugin-dir plugins/pptx-deck`（変更は `/reload-plugins` で反映）。

Playwright MCP はプラグインに含まれない。案の選択と回答の受け取りに使うので、Claude Code に別に設定する（ない場合は、回答を貼り付けて渡す）。

## 使い方

入口（スキル）は 4 つ。

| 入口 | 使う場面 |
|---|---|
| `/pptx-deck:create` | 資料を新しく作る。「スライドを作って」「稟議資料を作って」と頼んでもよい。入口は、テーマのみ／素材（メモ・文書・データ）／既存の Markdown 原稿のいずれか |
| `/pptx-deck:revise` | 作った PPTX を直す（型・デザインの選び直し、文言・数字の修正）。PowerPoint での手直しは取り込まないので、作り直すと消える |
| `/pptx-deck:rebuild` | `source/` を変えずに PPTX を作り直す（環境の更新後、PPTX を失くしたとき） |
| `/pptx-deck:review-plan` | 設計図と原稿を HTML で確認し、承認／要修正を受け取る。`create` の承認①でも使われる |

作品のフォルダは、実行したディレクトリ直下の `<名前>/` で、完成後は次の構成になる。`build` は成功すると、再生成できる派生ファイル（`variants.html`・`final.html`・`theme.css` など）を `source/` から消す。元データは残るので、あとで `revise`・`rebuild` できる。

```
<名前>/
  <名前>.pptx        成果物
  source/            設計図 design.md・原稿 script.md・slides/・answers-*.md・template.json など
```

| 段階 | 内容 | 承認 |
|---|---|---|
| 1. 入力 | 目的・対象・枚数、配色、テンプレートの有無を確認する | |
| 2. 設計図・原稿 | 先に設計図 `design.md`（ガバニングメッセージ・論点 3〜6 個・台帳・ページごとのヘッド・型・レイアウト記述・証拠対応表）を作り、それを `script.md`（題＝20 字以内の名詞句・見出し＝リード文として判断を言い切る 30〜60 字の 1 文・章名・本文・図表の型と理由・必要なときだけ出典・判断の枠）に写す。書式の手本は `assets/sample/`（架空の会社の中期経営計画。表紙＋10 枚） | 設計図と原稿を HTML（`review-plan`）で承認（内容を凍結） |
| 3. スライド案 | 全スライドの 3 案（型違い。A＝第 1 候補、B・C＝次点。図と表を多用する）を 1 つの HTML にまとめる。型を選ぶと、その型のデザイン 1〜3 を選べる（2 段）。左に一覧、右に 1 枚ずつ（大きなスライドと見どころの枠、判断欄に案のサムネ・承認／要修正・コメント）で見て、「回答をコピー」を押す（Claude が約 100 秒ごとに送信を確認し、約 30 分（18 回）で届かなければ続行方法を質問して止まる。Playwright MCP がないときはチャットに貼り付ける） | HTML 上で選択 |
| 4. 最終 HTML | 選ばれた案を統合し、`final-review.html` で全体を確認する。コメントのあったスライドは、前回のコメントと今回の直しを添えて、直した 1 案だけを再提示する | HTML 上で承認／要修正（チャットでもよい） |
| 5. PPTX | HTML の位置を測り、テンプレートを土台に PowerPoint の要素として書き出す。体裁を検査し、確認用の画像（`final.html` の撮影）で崩れを確認する。確認後は `clean` で一時の画像を消す | |

システムの Python に必要なものがそろっていないときは、仮想環境（`%LOCALAPPDATA%\pptx-deck\venv`。Python・python-pptx・Playwright・chromium）の作成の承認を求められる。承認なしには作らない。

## 部品の種類と使い分け

`plugins/pptx-deck/assets/components/` に 51 型・147 本ある（一覧は `部品見本.html`）。1 つの型に最大 3 つのデザイン（`<型>.html`・`<型>-d2.html`・`<型>-d3.html`）があり、同じ原稿のまま形だけを選べる（`cover`・`effort`・`relation` は 1 つ）。各部品の先頭のコメントに「用途」と「差し替える所」（デザイン 2・3 は「デザイン 1 との違い」）がある。設計図の「型」はここから選び、第 1 候補・次点は `references/patterns.md`（型の選定表）で決める。

**共通の構成** 題（名詞句 20 字以内）→ リード文の帯（判断を言い切る 30〜60 字）→ 図表タイトル → 図表本体 → 注。**判断を求める型**（`decision`・`summary`・`decisions`・`argument`・`options`・`raci`・`actions`・`gantt`）は最下部に論点ボックス（「論点　〜の可否」）を置く。**情報の型**は論点ボックスを置かず、注の末尾を「→ 含意」で締める。

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

内容に合う型がなければ、断片の部品で組む。新しい型を作ったら `assets/components/` に足し、`check` で違反が 0 件になることを確かめる。

## ファイルの置き場所

| 場所 | 内容 |
|---|---|
| `plugins/pptx-deck/`（プラグイン） | `skills/`（`create`・`revise`・`rebuild`・`review-plan` の各 `SKILL.md`）、`run.py`、`references/`（SKILL.md から参照する資料。`components.md`＝型の一覧と使い分け、`html-rules.md`＝HTML の書き方と描画の規準、`head-rules.md`＝題とリード文（ヘッド）の規則、`review-flow.md`＝スライド案と最終 HTML のレビューの細則、`check-rules.md`＝検査の rule と直し方）、テンプレート（`assets/components/` の 51 型・147 本。1 型に最大 3 つのデザイン。稟議・障害報告・検証計画・検証結果報告・業務フロー・設計書・設備増減の計画を作れる型をそろえる。本文の部品は「題 → リード文 → 図表タイトル → 本体 → 注」の構成で、判断を求める型は最下部に論点ボックスを置く。`patterns.md` は型の選定表）、`assets/icons/` のアイコン 14、`assets/template/standard.potx`）、設計図と原稿の手本（`assets/sample/`）、コード |
| `部品見本.html`（リポジトリ直下） | 部品 51 型・147 本の見本を 9 区分で 1 ページに並べた一覧（ブラウザで開く。画像はファイルに埋め込み済み）。画像は以前に描いたもので、このリポジトリには作り直す手順（生成スクリプト）がまだない。部品を足したり直したりしても、見本は自動では更新されない |
| 実行したディレクトリ直下の `<名前>/` | `<名前>.pptx`（成果物）と `source/`（`design.md`・`script.md`・`slides/`・`answers-*.md`・`template.json` など。作業中だけ `variants.html`・`final.html`・`final-review.html` ほか） |
| OS の一時フォルダ `%TEMP%\pptx-deck\<名前>\` | 確認用の画像など一過性のもの |

## 自動検査

`build` の前後に、文字のはみ出し、図形の重なり（テンプレートのヘッダー・フッターを含む）、文字サイズの下限（本文 14pt・注記 10pt）、文字のコントラスト比（4.5:1。大きい文字は 3:1）、画像の使い方（本文を画像にしない）を検査する。あわせて、ダッシュ（—）、同じ文言の 1 枚内の重複、1〜2 字の孤立改行、本文の下の空白帯を警告する（警告では出力を止めない）。違反は JSON で返る。破線・点線は PowerPoint の線種で書き出し、グラフの軸は `data-chart` の `axis` で最小・最大・目盛を固定できる。

`lint-script` は原稿の書式と題（20 字以内の名詞句）、見出し〔リード文〕の規則（30〜60 字・判断語か接続語・「A。B」の二段構え・ダッシュ・「本ページ」などの自己言及・隣り合う 3 枚の文型の連続）、論点の個数（3〜6）を検査する。

以前に書いた原稿は、本文スライドに「題」がなければ移行の案内が出る（エラーではない。見出しはそのままリード文になるので、`- 題:` を足す）。新しいヘッドの規則（判断語・1 行 41 字を目安とする長さなど）で `lint-script` に落ちることがある。直すか、正しい見出しなら `pptx_deck/script_lint.py` の `_JUDGE` に語を足す。

古い作業フォルダは `base.css`・`theme.css`・`chart-preview.js` が `init` 時の写しなので、新しい部品（`f-soft2`・`dashed`・`axis`）を使うには `init --force` で更新する（`reopen` は派生ファイルを作り直す）（`script.md` などの既存ファイルは消えない。`design.md` は既にあれば上書きしない）。

## ライセンス

MIT
