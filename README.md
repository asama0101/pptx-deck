# pptx-deck

ビジネス上の承認文書（稟議・提案・計画）を、コンサル資料のテイストで作る Claude Code スキル。設計図と原稿の承認 → HTML スライド案（各 3 案）の選択 → 最終 HTML の承認 → 編集可能な PowerPoint(.pptx) の順に進める。Windows 専用。

- 本文を画像にせず、PowerPoint の図形・文字・表・グラフで出力する（編集できる）。
- 13.33×7.5in（16:9）、BIZ UDPゴシック、無彩色＋基調 1 色＋強調 1 色。配色はプリセット（紺・緑・灰）か、基調色 `#RRGGBB` の指定で変えられる。
- 利用者の PowerPoint テンプレート（`.potx`／`.pptx`）がある場合は、**表紙・裏表紙・ヘッダー・フッター**がそれに従う（マスター／レイアウトが残る）。フォントと配色はテンプレートにかかわらず固定。
- 既存の PPTX の編集と、テンプレートの本文スライドの流用には使わない。

## 依存関係

`python run.py doctor` で、下の状態を確認できる（不足は `status` と `warnings` に出る）。

| 区分 | 内容 | 備考 |
|---|---|---|
| 必須 | Windows、Python 3.10 以上（コードが `X \| None` の型注釈を使う。動作確認は 3.14）、Claude Code | `python` が PATH にあること |
| 必須（初回に導入） | 仮想環境 `%LOCALAPPDATA%\pptx-deck\venv` に、`python-pptx==1.0.2`・`playwright==1.52.0`・`pymupdf==1.28.2`・`lxml>=5`、Playwright の chromium（数百 MB） | `python run.py setup --yes`。導入にはネットワークが要る。承認なしには作らない |
| 必須（スライド案・最終 HTML の確認） | Claude Code の Playwright MCP（`browser_navigate`・`browser_evaluate`） | 案の選択と「回答をコピー」の受け取りに使う。MCP がなければ、HTML を自分で開き、コピーした回答をチャットに貼り付ける |
| 推奨 | LibreOffice（`soffice`。`C:\Program Files\LibreOffice\` か PATH） | 確認用の画像（`pngs`）とテンプレートの下地画像に使う。なくても `.pptx` は出るが、画像での崩れの確認ができない |
| 推奨 | BIZ UDPゴシック（フォント） | 未導入だと、計測が代替フォントになり、PowerPoint と折り返しがずれることがある |
| 最終確認 | Microsoft PowerPoint | LibreOffice の画像は近似。PowerPoint で開いて最終確認する |

## 使い方

Claude Code で「スライドを作って」「稟議資料を作って」と頼む。入口は、テーマのみ／素材（メモ・文書・データ）／既存の Markdown 原稿のいずれか。

| 段階 | 内容 | 承認 |
|---|---|---|
| 1. 入力 | 目的・対象・枚数、配色、テンプレートの有無を確認する | |
| 2. 設計図・原稿 | 先に設計図 `design.md`（ガバニングメッセージ・論点 3〜6 個・台帳・ページごとのヘッド・型・レイアウト記述・証拠対応表）を作り、それを `script.md`（見出し＝判断を言い切る 30〜60 字の 1 文・章名・本文・図表の型と理由・必要なときだけ出典・判断の枠）に写す。書式の手本は `assets/sample/`（架空の会社の中期経営計画。表紙＋10 枚） | 設計図と原稿を一緒にチャットで承認（内容を凍結） |
| 3. スライド案 | 全スライドの 3 案（同じ型のまま配置・強調・密度を変える。図と表を多用する）を 1 つの HTML にまとめる。左に一覧、右に 1 枚ずつ（大きなスライドと見どころの枠、判断欄に案のサムネ・承認／要修正・コメント）で見て、「回答をコピー」を押す（待ち受けていれば自動で届き、そうでなければチャットに貼り付ける） | HTML 上で選択 |
| 4. 最終 HTML | 選ばれた案を統合し、`final-review.html` で全体を確認する。コメントのあったスライドは、前回のコメントと今回の直しを添えて、直した 1 案だけを再提示する | HTML 上で承認／要修正（チャットでもよい） |
| 5. PPTX | HTML の位置を測り、テンプレートを土台に PowerPoint の要素として書き出す。体裁を検査し、確認用の画像で崩れを確認する | |

初回は、仮想環境（`%LOCALAPPDATA%\pptx-deck\venv`。Python・python-pptx・Playwright・chromium）の作成の承認を求められる。承認なしには作らない。

## ファイルの置き場所

| 場所 | 内容 |
|---|---|
| `skills/pptx-deck/`（スキル） | `SKILL.md`、テンプレート（`assets/components/` のレイアウト 7・図解 19・表 15・グラフ 10。稟議・障害報告・検証計画・検証結果報告・業務フロー・設計書・設備増減の計画を作れる型をそろえ、時系列・業務フロー・構成図・Before/After は横と縦の 2 パターンを持つ。本文の部品は「見出し → 図表タイトル → 本体 → 注」の構成で、決定を求める型は最下部に論点ボックスを置く、`assets/icons/` のアイコン 14、`assets/template/standard.potx`）、設計図と原稿の手本（`assets/sample/`）、コード |
| `部品見本.html`（リポジトリ直下） | 部品 51 本の見本を 1 ページに並べた一覧（ブラウザで開く。画像は LibreOffice の描画）。部品を足したり直したりしたら作り直す |
| 実行したディレクトリ直下の `<名前>/` | `design.md`（`init` が雛形を置く）、`script.md`、`slides/`、`variants.html`、`final.html`、`final-review.html`、`<名前>.pptx` ほか |
| OS の一時フォルダ `%TEMP%\pptx-deck\<名前>\` | 確認用の画像など一過性のもの |

## 自動検査

`build` の前後に、文字のはみ出し、図形の重なり（テンプレートのヘッダー・フッターを含む）、文字サイズの下限（本文 14pt・注記 10pt）、文字のコントラスト比（4.5:1。大きい文字は 3:1）、画像の使い方（本文を画像にしない）を検査する。あわせて、ダッシュ（—）、同じ文言の 1 枚内の重複、1〜2 字の孤立改行、本文の下の空白帯を警告する（警告では出力を止めない）。違反は JSON で返る。破線・点線は PowerPoint の線種で書き出し、グラフの軸は `data-chart` の `axis` で最小・最大・目盛を固定できる。

`lint-script` は原稿の書式と見出しの規則（30〜60 字・判断語か接続語・「A。B」の二段構え・ダッシュ・「本ページ」などの自己言及・隣り合う 3 枚の文型の連続）、論点の個数（3〜6）を検査する。

以前に書いた原稿は、新しいヘッドの規則（判断語・1 行 41 字を目安とする長さなど）で `lint-script` に落ちることがある。直すか、正しい見出しなら `pptx_deck/script_lint.py` の `_JUDGE` に語を足す。

古い作業フォルダは `base.css`・`theme.css`・`chart-preview.js` が `init` 時の写しなので、新しい部品（`f-soft2`・`dashed`・`axis`）を使うには `init --force` で更新する（`script.md` などの既存ファイルは消えない。`design.md` は既にあれば上書きしない）。

## ライセンス

MIT
## 部品の種類と使い分け

`skills/pptx-deck/assets/components/` に 51 本ある（一覧は `部品見本.html`）。各部品の先頭のコメントに「用途」と「差し替える所」がある。設計図の「型」はここから選ぶ。

**共通の構成** 見出し（判断を言い切る 1 文）→ 図表タイトル → 図表本体 → 注。**決定を求める型**は最下部に論点ボックス（「論点　〜の可否」）を置く。**情報の型**は論点ボックスを置かず、注の末尾を「→ 含意」で締める。

### レイアウト（7）

| 型 | 使いどころ | 種別 |
|---|---|---|
| `cover` | 表紙 | — |
| `section` | 章扉。章の問いと、この章で判断すること | — |
| `agenda` | 目次。章ごとの結論 1 行とページ | — |
| `summary` | 数字サマリ。数字カード 4 枚と根拠の表 | 決定 |
| `decision` | クロージングの決定事項。表・スケジュール・審議基準 | 決定 |
| `closing` | 裏表紙。決定事項の再掲と承認後のアクション | — |
| `incident` | 障害の概要。停止時間・影響範囲・損失・復旧手段 | 情報 |

### 図解（19）

| 型 | 使いどころ | 種別 |
|---|---|---|
| `flow-h` | 手順。段階ごとの期間・成果物・承認点 | 情報 |
| `tree` | ロジックツリー。要因を寄与つきで分解する | 情報 |
| `pyramid` | 階層。層ごとの権限・件数・金額 | 情報 |
| `cycle` | 循環。段階ごとの指標・頻度・担当 | 情報 |
| `gantt` | フェーズごとの予定。現在線と判断点 | 決定 |
| `venn` | 2 条件の重なりで候補を絞る | 情報 |
| `layers` | 層×系列のマップ。自社の守備範囲 | 情報 |
| `side-by-side` | 左右比較。現行｜計画を同じ項目で並べる | 決定 |
| `before-after` | 現行と改革後（上下）。工程が横に流れる | 情報 |
| `before-after-h` | 現行と改革後（左右）。工程が縦に流れる。5〜6 段のとき | 情報 |
| `timeline-h` | 時系列（横）。区間の長さで待ちを見せる | 情報 |
| `timeline-v` | 時系列（縦）。件数が多く、文で読ませる | 情報 |
| `cause` | 原因の連鎖。事象から根本原因まで時間順に追う | 情報 |
| `swimlane-h` | 業務フロー（横）。レーン＝部門。工程 6 段まで | 情報 |
| `swimlane-v` | 業務フロー（縦）。工程 7〜8 段 | 情報 |
| `architecture` | システム構成図（上下の層） | 情報 |
| `topology` | 系統図（左右）。拠点とセンターを回線で結ぶ | 情報 |
| `org` | 体制図。責任者・PM・チームと人数 | 情報 |
| `roadmap` | 更改ロードマップ。設備×年度の増設・更改・撤去 | 情報 |

### 表（15）

| 型 | 使いどころ | 種別 |
|---|---|---|
| `compare` | エグゼクティブサマリ。論点｜求める決定｜根拠 | 決定 |
| `rating` | 論証テーブル。事実と含意の 2 段 | 決定 |
| `options` | 案の評価表。評価軸×A/B/C 案、推奨の列を強調 | 決定 |
| `risk` | リスク｜影響（定量）｜対策｜残存｜オーナー | 決定 |
| `cost` | 費用。費目×年度に 5 年計・累計 | 情報 |
| `quote` | 見積内容。単価・数量・金額と見積合計 | 情報 |
| `quote-compare` | 過去見積との比較。前回｜今回｜差額｜理由 | 決定 |
| `effort` | 工数比較。工程×2 案の人日と差 | 情報 |
| `spec` | 項目一覧。検証項目・機能・要件に共用 | 情報 |
| `result` | 判定結果。基準と実測値、○△× | 決定 |
| `issues` | 課題・不具合一覧。重要度・期限・状態 | 情報 |
| `actions` | 再発防止策。恒久（■）と暫定（□） | 決定 |
| `delta` | 設備増減表。現状・増・減・計画後 | 情報 |
| `matrix` | 配置表。拠点種別×設備の台数 | 情報 |
| `raci` | 役割分担表。工程×部門の責任・実行・支援 | 決定 |

### グラフ（10）

| 型 | 使いどころ |
|---|---|
| `bar` / `line` / `stacked` / `waterfall` | 棒・折れ線・積み上げ・滝。全幅で見せ、注目点は吹き出し 2 つまで |
| `bar-note` / `line-note` / `stacked-note` / `waterfall-note` | 同じグラフに内訳の表を添える。所見が長文のとき |
| `effort-bar` | 工数比較の横棒。表だけなら `effort` |
| `quote-bridge` | 見積差額の滝グラフ。表だけなら `quote-compare` |

### 同じ内容で見せ方が 2 つある型

| 内容 | 横・上下 | 縦・左右 |
|---|---|---|
| 時系列 | `timeline-h`（区間の長さで待ちを見せる） | `timeline-v`（件数が多く文で読ませる） |
| 業務フロー | `swimlane-h`（工程 6 段まで） | `swimlane-v`（工程 7 段以上） |
| 構成図 | `architecture`（上下の層） | `topology`（左右の系統） |
| 現行と改革後 | `before-after`（工程が横に流れる） | `before-after-h`（工程が縦に流れる） |
| 工数・見積差 | 表（`effort`・`quote-compare`） | 図（`effort-bar`・`quote-bridge`） |

### 文書の種類と使う型

| 文書 | 冒頭 | 本体でよく使う型 | 結び |
|---|---|---|---|
| 稟議 | `summary`・`compare` | `options`・`cost`・`quote`・`quote-compare`・`effort`・`risk`・`flow-h`・`gantt`・`org` | `decision`・`closing` |
| 障害報告 | `incident` | `timeline-h`/`-v`・`cause`・`tree`・`actions`・`issues` | `decision`・`closing` |
| 検証計画 | `summary` | `spec`・`architecture`/`topology`・`org`・`raci`・`gantt`・`options` | `decision`・`closing` |
| 検証結果報告 | `summary` | `result`・`bar`/`line`・`issues`・`spec` | `decision`・`closing` |
| 業務フロー | `section` | `swimlane-h`/`-v`・`before-after`/`-h`・`raci`・`cycle` | `decision`・`closing` |
| 設計書 | `agenda` | `architecture`/`topology`・`layers`・`spec`・`options`・`matrix` | `summary`・`closing` |
| 設備増減の計画 | `summary` | `delta`・`matrix`・`roadmap`・`side-by-side`・`stacked`/`waterfall`・`cost` | `decision`・`closing` |

内容に合う型がなければ、断片の部品で組む。新しい型を作ったら `assets/components/` に足し、`check` で違反が 0 件になることを確かめる。

