---
name: create
description: テーマ・素材・原稿から、コンサルテイストの承認資料（稟議・提案・計画）を新しく作る。設計図と原稿(Markdown)の承認 → HTML スライド案（各 3 案）の選択 → 最終 HTML の承認 → 編集可能な PowerPoint(.pptx) の順に進める。利用者の PPTX テンプレート（表紙・裏表紙・ヘッダー・フッター）に従える。「スライドを作って」「資料を作って」「PowerPoint を作って」「稟議資料」「提案資料」「デッキ」と頼まれたときに使う。作った PPTX の直しには revise、設計図と原稿の確認だけなら review-plan を使う。既存の PPTX の編集には使わない。Windows 専用。
compatibility: Windows 専用。Python 3.10 以上と Claude Code。システムの Python に python-pptx・Playwright・chromium がそろっていればそれを使い、なければ仮想環境を承認を得て作る。スライド案の選択に Playwright MCP が必要（ないときは回答を貼り付ける）。LibreOffice は使わない。
---

# pptx-deck

ビジネス上の承認文書を、コンサル資料のテイストで作る。本文を画像にせず、PowerPoint で編集できる .pptx を出す。13.33×7.5in（16:9）、BIZ UDPゴシック、無彩色＋基調 1 色＋強調 1 色。

`${CLAUDE_PLUGIN_ROOT}` は、このプラグインのフォルダ（Claude Code が実パスに置き換える）。コマンドはすべて `python "${CLAUDE_PLUGIN_ROOT}/run.py" …`。`<名前>` は作品の名前（実行したディレクトリ直下の `<名前>/`）。作業ファイルは `<名前>/source/` に作り、PPTX は `<名前>/<名前>.pptx` に出る。

## 0. 初回だけ（環境）

1. `python "${CLAUDE_PLUGIN_ROOT}/run.py" doctor` を実行する。終了コード 3 のときは、システムの Python にも仮想環境にも必要なものがそろっていない。**利用者に「`%LOCALAPPDATA%\pptx-deck\venv` に Python の仮想環境と chromium（数百 MB）を導入してよいか」を確認する**。承認が出るまで作らない。システムの Python には何も入れない。
2. 承認後、`python "${CLAUDE_PLUGIN_ROOT}/run.py" setup --yes`。
3. `doctor` の `python.kind`（`system` か `venv`）と `warnings`（BIZ UDPゴシック未導入など）を利用者に伝える。

## 1. 流れ（承認は 3 回）

| 段階 | やること | 承認 |
|---|---|---|
| 入力 | 下の「1.1 入力で聞くこと」 | |
| 設計図 | 図を作る前に `<名前>/source/design.md` を書く（ガバニングメッセージ・論点・台帳・ページごとの設計。2.1） | ①に含める |
| 原稿 | `<名前>/source/script.md` を書く。`lint-script` が空になるまで直す | ① 設計図と原稿を HTML で承認（review-plan。内容を凍結） |
| スライド案 | 全スライドの 3 案を `source/slides/NN-A.html`〜に書き、`variants` で 1 つの HTML にする | ② HTML 上で選択＋コメント |
| 最終 HTML | 選ばれた案を `finalize` で統合し、`final-review.html` で全体を見せる | ③ HTML 上で承認／要修正（チャットでの承認でもよい） |
| PPTX | `build` で書き出し、検査と確認用の画像（`final.html` の撮影）で崩れを確認する | |

### 1.1 入力で聞くこと
- 入口: テーマのみ／素材（メモ・文書・データ）／既存の Markdown 原稿。足りない前提（対象者・目的・枚数・期限・欠けている数字）は、作業を始める前にまとめて質問する。外れたときの手戻りが大きいものは推測しない。
- 配色: プリセット（`navy`・`green`・`gray`）か、基調色 `#RRGGBB`。指定がなければ `navy`。
- 利用者の PowerPoint テンプレートの有無（`.potx` または `.pptx` のパス）。あれば、**表紙・裏表紙・ヘッダー・フッター**がそれに従う。フォントと配色は、テンプレートにかかわらず BIZ UDPゴシックと選んだ配色。16:9（13.33×7.5in）以外のテンプレートは使えない。
- フッターの文言（社外秘など）があれば `build --footer`。

### 1.2 作業フォルダ
`python "${CLAUDE_PLUGIN_ROOT}/run.py" init "<名前>" --color <プリセット|#RRGGBB> [--template "<パス>"]`。同名のフォルダが空でないときは止まる。**中身を利用者に見せて、上書きしてよいと言われたときだけ `--force`**。`init` の出力の `notes`（テンプレートの代替レイアウト、`slides/` に前の作業のファイルが残っている旨）は利用者に伝える。`--force` は既存のファイルを消さない（`theme.css` などを上書きするだけ。`design.md` は、既にあれば上書きしない）ので、古い案が混ざらないよう、不要な `slides/` のファイルは利用者に確認してから削除する。

| 置き場所 | ファイル |
|---|---|
| プラグイン `${CLAUDE_PLUGIN_ROOT}`（読み取り専用） | `skills/`、`assets/`（`components/` の断片、`web/`、`icons/`、`template/`）、`references/`、コード |
| `<名前>/` | `<名前>.pptx`（成果物）と `source/` |
| `<名前>/source/` | `design.md`（`init` が雛形を置く）、`script.md`、`slides/NN-X.html`、`answers-*.md`、`template.json`、`_template/template.<拡張子>`、`build.json`。作業中だけ `variants.html`・`plan-review.html`・`final.html`・`final-review.html`・`theme.css`・`base.css`・`chart-preview.js`・`icons/` |
| OS の一時フォルダ `%TEMP%\pptx-deck\<名前>\` | 確認用の画像（`preview/`）、SVG の画像化 |

## 2. 設計図と原稿（design.md・script.md）

図から作り始めない。先に設計図で各ページの題・リード文（ヘッド。`題`・`見出し`）と論理を決め、それを原稿に写す。

- 数字を作らない。素材に無い数字は、前提を明記した試算にするか「xx」で残す（それらしく埋めない）。素材に無い固有名詞・出来事を足さない。

### 2.1 設計図（design.md）
書式は `assets/sample/design.md`（`init` が `<名前>/source/design.md` に置く雛形。中身は見本）に従う。1 枚物なら、資料全体と台帳は省く。

- 資料全体: **ガバニングメッセージ**（資料全体の結論）を 1 つ立て、各ページのヘッドをその下にぶら下げる。**論点**（決めさせること）は 3〜6 個に番号を付ける。冒頭のサマリで番号つきで予告し、最終ページで同じ番号で回収する。最終ページは、決定事項・日程・判断基準を載せた一番重いページにする。
- 台帳を先に作る: `| No | ヘッド | 文型 | 上位への集約 | 直前からの接続語 | 本体の型 | 論点 |`。縦の検証: ヘッドを縦に通読し、隣り合うページが「だから／なぜなら」で繋がる。横の検証: 同じ階層の並びは切り口 1 つ・粒度をそろえる（「何で割ったか」を 1 語で言える）。
- ページごと: 題／リード文（ヘッド）／文型／型（`references/patterns.md` の選定表で第 1 候補・次点を決め、`references/components.md` の一覧で確かめる）／図表タイトル（名詞句。時点と単位を含める）／レイアウト記述（縦軸・横軸・各エリアの中身・強調の 1 点）／証拠対応表（ヘッドの各節を、本体のどの要素が証明するか）／注記と出所（出所は必要なときだけ）。

### 2.2 題とリード文（ヘッド）の規則
ページ枠は 題 → リード文の帯 → 図表タイトル → 本体 → 注。**題**（原稿の `題`）は名詞句 20 字以内で主題だけを書く（判断は書かない。`lint-script` が検査）。**リード文**（原稿の `見出し`）に判断を言い切る。
細則（判断語の例・文型・書き方の 5 段階・逆テスト・`lint-script` が見るものと人が見るもの）は [references/head-rules.md](references/head-rules.md) にある。ヘッドを書く前に読み、従う。要点:
- 主語と述語のある完全な文で、事実＋判断を 1 文に持つ。判断語は `lint-script` の固定リスト。1 ページ 1 メッセージ。
- リード文は 30〜60 字（`check` が警告）。帯の中に収め、入らないときは設計図に戻って削る。題は 20 字以内。
- 禁止: 「A。B」の二段構え／要素の数え上げ／体言止め／ダッシュ（—）／自己言及。実質数値は 1 文に 2 つまで。隣り合う 3 枚で同じ文型を続けない。
- So What 帯は置かず、示唆はヘッドに書く。決定を求めるページだけ論点ボックスに「〜の可否」を 1 行で書く。

### 2.3 原稿（script.md）
書式は `assets/sample/script.md`（書式の手本であり、構成の手本ではない。決定のページが 2 枚目（S03）で、§2.1 の「最終ページで回収」の構成とは逆。11 枚。表紙と、見本の 10 枚の内容。架空の会社の中期経営計画）に従う。冒頭に目的・対象・`論点`（設計図の論点を番号つきの項目で）・配色を書き、スライドごとに次を書く。

- `layout`（`cover|section|agenda|content|diagram|table|chart|closing`）、`題`（本文スライドのみ。20 字以内の名詞句）、`見出し`（**2.2 の規則に従うリード文**）、`章名`（そのスライドが答える問い）、`本文`、`図表`（型と選んだ理由を 1 行）、必要なときだけ `出典`、判断が要るスライドは `判断の枠`（決めること・期限・推奨）。
- 1 スライド 1 メッセージ。結論 → 根拠の順。出典は必要なときだけ書く（既定では書かない）。スピーカーノートは作らない。
- 書いたら `python "${CLAUDE_PLUGIN_ROOT}/run.py" lint-script "<名前>/source/script.md"`。問題は全件出る。空になり、5.1 のヘッド・論理の確認を済ませてから、`python "${CLAUDE_PLUGIN_ROOT}/run.py" review-plan "<名前>"` で `plan-review.html` を作り、Playwright MCP の `browser_navigate` で開いて、「資料全体とスライドごとの設計・原稿を見て、『承認』か『要修正』を選び、『回答をコピー』を押してください」と伝える。待ち方と回答の保存は 3 章の手順 4・5 と同じ（保存先は `<名前>/source/answers-plan-N.md`）。要修正があれば、コメントに沿って設計図と原稿を直し、`review-plan` を出し直す（前回承認したスライドは選択済みで開く）。承認後は、承認なしに内容を変えない。
- `lint-script` が検査する範囲と、人が見る範囲（完全文・体言止め・数え上げ・行数・逆テスト・縦読み・論点の回収・証拠対応）は [references/head-rules.md](references/head-rules.md) の表にある。

## 3. スライド案（3 案）

1. スライドの主張から「問い」を決め、`references/patterns.md` の選定表で型の第 1 候補・次点 1・次点 2 を取る。断片は `assets/components/` から、型の一覧は `references/components.md`。断片をコピーして、内容と数字を差し替え、`<名前>/source/slides/NN-A.html` に書く。
2. **3 案は型違い**（A: 第 1 候補／B: 次点 1／C: 次点 2。候補が足りなければ 2 案、型が一意なら 1 案）。内容（文言と数字）は 3 案で同じ。基本として、**図と表を多用して説明する**。**デザイン違いは案にしない**: 利用者が型を選んだあとに、デザイン 1〜3 から選ぶ。デザイン 2・3 は `NN-A-d2.html`・`NN-A-d3.html`（B・C も同様）に書く。デザインを出さない型（デザイン 1 のみ）は書かなくてよい。各断片に `data-variant="型名｜選んだ理由"` を付けると、案の下に型名、大きな画面の下に理由が出る。
3. `python "${CLAUDE_PLUGIN_ROOT}/run.py" variants "<名前>"`（回は次の回が自動で選ばれる） → `<名前>/source/variants.html`。Playwright MCP の `browser_navigate` で `file:///C:/.../variants.html` を開き、「左の一覧から 1 枚ずつ見て、型（A/B/C）を選び、続けてデザイン 1〜3 を選んで、『承認』か『要修正』を押してください。直したい点や、どの案でもない場合はコメントに書いて（案は選ばず『要修正』）、判断欄の右端の『回答をコピー』を押してください」と伝える。**`browser_resize` で窓の大きさを変えない**。ページの構成とボタンの扱いは [references/review-flow.md](references/review-flow.md)。
4. 「回答をコピー」が押されるのを待つ（ユーザーに「完了」と入力させない）。押されると `window.__submitted` が立つ。`browser_evaluate` で次を実行し、送信されるか約 100 秒たつまでブロックして結果を返す。`submitted` が false なら同じ呼び出しを繰り返す（合計約 30 分、18 回まで）。18 回（約 30 分）を超えても送信されないときは、待ちをやめて、続行方法（もう一度待つ／回答を貼り付けて渡す／中止）を利用者に質問して止まる。ユーザーがターミナルに入力したときは待ちをやめて、その内容に従う。

   `() => new Promise(res => { const t0 = Date.now(); const id = setInterval(() => { if (window.__submitted || Date.now() - t0 > 100000) { clearInterval(id); res({ submitted: !!window.__submitted, md: window.__answersMd }); } }, 500); })`

5. `submitted` が true なら、`md` を `<名前>/source/answers-N.md` に書く（N は何回目か）。利用者がチャットに貼り付けた md も同じように書く。回答の書式は [references/review-flow.md](references/review-flow.md)。
6. **コメントがあるスライドだけ**、選ばれた案を直して 1 案にし（`NN-A.html` を上書き、`NN-B/C` は削除）、`variants --round N+1` で再提示する。**利用者には直したスライドだけ答えてもらう**。コメントが未反映のうちは `finalize` が止まる。別案に戻す条件と `round-(N+1)-notes.md` の書き方は [references/review-flow.md](references/review-flow.md)。
7. すべて決まったら、`python "${CLAUDE_PLUGIN_ROOT}/run.py" finalize "<名前>"`（`--answers` を省くと `source/answers-*.md` を回の順に全部使う。後の回答が前の回答を上書きする） → `final.html`（`build` が使う素のページ。変えない）と、確認用の `final-review.html`。
8. `final-review.html` を `browser_navigate` で開き、「1 枚ずつ見て、『承認』か『要修正』を選び、『回答をコピー』を押してください」と伝える。待ち方と `md` の扱いは 4・5 と同じ（保存先は `<名前>/source/answers-final.md`。コマンドは `review-final "<名前>"`、`--answers` を省くと `answers-*.md` を自動で使う）。『要修正』があれば、コメントに沿って `source/slides/` を直して `finalize` からやり直す。チャットで承認を受けた場合は、この手順は省いてよい。細則は [references/review-flow.md](references/review-flow.md)。

### 型の選び方
型の選び方は [references/patterns.md](references/patterns.md)（問い → 型 → デザインの選定表）、型の一覧（51 型・147 本の用途・判断を求める型か情報の型か・文書の種類ごとの組み合わせ）は [references/components.md](references/components.md) にある。選ぶ前に読み、各断片の先頭のコメント（用途・差し替える所・デザイン 1 との違い）も読む。

- 本文の部品に共通の構成: 題（`data-role="title"`。20 字以内の名詞句）→ リード文の帯（`data-role="lead"`。判断を言い切る 30〜60 字）→ 図表タイトル → 図表本体 → 注（`caption`）。箱・行・棒のすべてに定量を 1 つ以上書き、本文領域の下端（y 640）まで使う。
- **判断を求める型**（`decision`・`summary`・`decisions`・`argument`・`options`・`raci`・`actions`・`gantt`）は最下部に論点ボックス（「論点　〜の可否」1 行）を置く。**情報の型**は論点ボックスを置かず、注の末尾を「→ 含意」の 1 文で締める。
- 内容に合う型がなければ、断片の部品で組む。新しい型やデザインを作ったら、`assets/components/` に足し、`components.md`・`patterns.md` にも加え、`check` で違反が 0 件になることを確かめる。

## 4. HTML の書き方

細則（部品のクラス・`data-role`・`data-note`・色・文字サイズ・視線誘導・`data-chart`・配色の 3 役・配置の 4 原則・記号文法・階調・グラフと表の作法・禁止事項）は [references/html-rules.md](references/html-rules.md) にある。断片を書く前に読み、従う。最低限:

- 1 枚 = `<section class="slide" data-layout="…">`（1280×720px）。部品は `pp-text`・`pp-shape`・`pp-line`・`pp-image`・`pp-table`・`pp-chart` だけ。**これ以外のクラスの文字や図は PPTX に出ない**。
- 色は `var(--accent)` などの変数だけ。**強調色（`f-emph`・`t-emph`）は 1 スライドに 1 点**。
- 本文 14pt（約 19px）以上、注記 10pt（14px）以上。ダッシュ（—）はどこにも使わない。

## 5. PPTX の出力

`python "${CLAUDE_PLUGIN_ROOT}/run.py" build "<名前>" [--footer "文言"] [--out <パス>] [--force]`。出力 JSON のキーは `ok`・`violations`・`pptx`・`previews`・`removed`・`notes`。`ok` が false なら、`violations` を読んで `source/slides/` の断片を直し、`finalize` からやり直す（内容は変えない。直すのは配置・サイズ・色）。直しが原稿の変更（文章を減らす、スライドを分ける）を伴うときは、案を示して利用者の承認を得る。終了コード 4 は、PPTX が前回のビルド後に変更されている（手直しが消える）。利用者に確認し、`--force`（上書き）か `--out <パス>`（別名）を選んでもらう。

`ok` が true なら、`previews`（確認用の画像。`final.html` を Chromium で撮ったもので、PPTX の実描画ではない）を開いて崩れを確認し、所見を伝える。**PowerPoint で開いて最終確認することを必ず勧める**。確認が済んだら `python "${CLAUDE_PLUGIN_ROOT}/run.py" clean "<名前>"` で一時の画像を消す。成果物は `<名前>/<名前>.pptx`。`build` は成功すると、再生成できる派生ファイルを `source/` から自動で消す（`removed` に一覧が出る）。元データ（`design.md`・`script.md`・`slides/`・`answers-*.md`・`template.json` など）は残るので、あとで `revise` で直せる。

`violations` の `rule`（`overflow`・`overlap`・`keepout`・`fontMin`・`contrast`・`imageAlt`・`bodyImage`・`titleMissing`・`shapeKind` と、警告の `dash`・`sameWord`・`orphanLine`・`emptyBand`・`leadMissing`・`leadLength`・`titleLength`）ごとの直し方は [references/check-rules.md](references/check-rules.md) にある。

警告（`severity: warning`）は `ok` を false にしないが、5.1 で 0 件にする。`build` の前に見るときは `python "${CLAUDE_PLUGIN_ROOT}/run.py" check "<名前>/source/final.html"`。

### 5.1 工程5（計測で検証）
出す前（設計図と原稿の承認①の前と、PPTX を渡す前）に、次を自分で確認し、外れていれば直す。

- ヘッド: `lint-script` が空。加えて、題が主題だけの名詞句か・リード文が完全文で体言止めや数え上げがないか・実質数値は 2 つまでか・リード文の帯に収まるか（収まらなければ設計図に戻る）。
- 数値: ヘッドの数字＝本体の数字（合計）。素材に無い数字は作らず、前提を明記した試算か「xx」で残す。
- 証拠: 設計図の証拠対応表のとおり、ヘッドの各節を本体の要素が証明している（文字の注記だけで支える節を残さない）。
- 論理: ヘッドを縦に読んで筋が通る。並列の要素は切り口 1 つ・粒度がそろう。論点の番号が、サマリの予告と最終ページの回収で対応する。
- 見た目: `build` の `violations` が、エラー・警告とも 0 件。線種と塗りの意味が全ページで同じ。確認用の画像に崩れがない。

手直しは 1 周。直せない項目は、利用者への報告に「未達」と明記する（理由も添える）。承認①の後で内容（文言・数字）を変える直しは、案を示して承認を得る。

## 6. 守ること

- 原稿の承認後は、承認なしで内容を変えない。
- 数字・固有名詞を作らない（素材に無い数字は、前提つきの試算か「xx」）。
- 仮想環境は、承認なしに作らない。既存の作業フォルダは、中身を見せて承認を得てから上書きする。
- エラーが出たら、原因と対処を示して止まる。推測で別の方法に切り替えない。
- スクリプトは Playwright MCP を使わない。MCP は、案の選択の受け取りと画面確認だけに使う。
