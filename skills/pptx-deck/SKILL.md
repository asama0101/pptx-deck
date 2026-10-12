---
name: pptx-deck
description: テーマ・素材・原稿から、コンサルテイストの承認資料（稟議・提案・計画）を作る。設計図と原稿(Markdown)の承認 → HTML スライド案（各 3 案）の選択 → 最終 HTML の承認 → 編集可能な PowerPoint(.pptx) の順に進める。利用者の PPTX テンプレート（表紙・裏表紙・ヘッダー・フッター）に従える。「スライドを作って」「資料を作って」「PowerPoint を作って」「稟議資料」「提案資料」「デッキ」と頼まれたときに使う。既存 PPTX の編集には使わない。Windows 専用。
compatibility: Windows 専用。Python 3.10 以上と Claude Code。初回に仮想環境（python-pptx・Playwright と chromium）を承認を得て作る。スライド案の選択に Playwright MCP、確認用の画像に LibreOffice（推奨）を使う。
---

# pptx-deck

ビジネス上の承認文書を、コンサル資料のテイストで作る。本文を画像にせず、PowerPoint で編集できる .pptx を出す。13.33×7.5in（16:9）、BIZ UDPゴシック、無彩色＋基調 1 色＋強調 1 色。

`${CLAUDE_SKILL_DIR}` は、この SKILL.md があるフォルダ（Claude Code が実パスに置き換える）。コマンドはすべて `python "${CLAUDE_SKILL_DIR}/run.py" …`。`<名前>` は作業フォルダ名（実行したディレクトリ直下に作る）。

## 0. 初回だけ（環境）

1. `python "${CLAUDE_SKILL_DIR}/run.py" doctor` を実行する。`venv` がない（終了コード 3）または `status` に不足があるときは、**利用者に「`%LOCALAPPDATA%\pptx-deck\venv` に Python の仮想環境と chromium（数百 MB）を導入してよいか」を確認する**。承認が出るまで作らない。
2. 承認後、`python "${CLAUDE_SKILL_DIR}/run.py" setup --yes`。
3. `doctor` の `warnings` を利用者に伝える（BIZ UDPゴシック未導入、LibreOffice なしなど）。

## 1. 流れ（承認は 3 回）

| 段階 | やること | 承認 |
|---|---|---|
| 入力 | 下の「1.1 入力で聞くこと」 | |
| 設計図 | 図を作る前に `<名前>/design.md` を書く（ガバニングメッセージ・論点・台帳・ページごとの設計。2.1） | ①に含める |
| 原稿 | `<名前>/script.md` を書く。`lint-script` が空になるまで直す | ① 設計図と原稿を一緒にチャットで承認（内容を凍結） |
| スライド案 | 全スライドの 3 案を `slides/NN-A.html`〜に書き、`variants` で 1 つの HTML にする | ② HTML 上で選択＋コメント |
| 最終 HTML | 選ばれた案を `finalize` で統合し、`final-review.html` で全体を見せる | ③ HTML 上で承認／要修正（チャットでの承認でもよい） |
| PPTX | `build` で書き出し、検査と確認用の画像で崩れを確認する | |

### 1.1 入力で聞くこと
- 入口: テーマのみ／素材（メモ・文書・データ）／既存の Markdown 原稿。足りない前提（対象者・目的・枚数・期限・欠けている数字）は、作業を始める前にまとめて質問する。外れたときの手戻りが大きいものは推測しない。
- 配色: プリセット（`navy`・`green`・`gray`）か、基調色 `#RRGGBB`。指定がなければ `navy`。
- 利用者の PowerPoint テンプレートの有無（`.potx` または `.pptx` のパス）。あれば、**表紙・裏表紙・ヘッダー・フッター**がそれに従う。フォントと配色は、テンプレートにかかわらず BIZ UDPゴシックと選んだ配色。16:9（13.33×7.5in）以外のテンプレートは使えない。
- フッターの文言（社外秘など）があれば `build --footer`。

### 1.2 作業フォルダ
`python "${CLAUDE_SKILL_DIR}/run.py" init "<名前>" --color <プリセット|#RRGGBB> [--template "<パス>"]`。同名のフォルダが空でないときは止まる。**中身を利用者に見せて、上書きしてよいと言われたときだけ `--force`**。`init` の出力の `notes`（テンプレートの代替レイアウト、`slides/` に前の作業のファイルが残っている旨）は利用者に伝える。`--force` は既存のファイルを消さない（`theme.css` などを上書きするだけ。`design.md` は、既にあれば上書きしない）ので、古い案が混ざらないよう、不要な `slides/` のファイルは利用者に確認してから削除する。

| 置き場所 | ファイル |
|---|---|
| スキル `${CLAUDE_SKILL_DIR}/`（読み取り専用） | `SKILL.md`、`assets/`（`components/` の断片、`web/`、`icons/`、`template/`）、コード |
| 作業フォルダ `<名前>/` | `design.md`（設計図。`init` が雛形を置く）、`script.md`、`slides/NN-X.html`、`variants.html`、`final.html`、`<名前>.pptx`、`theme.css`・`base.css`・`icons/`・`_template/`（`init` が作る） |
| OS の一時フォルダ `%TEMP%\pptx-deck\<名前>\` | 確認用の PNG（`render/`）、SVG の画像化 |

## 2. 設計図と原稿（design.md・script.md）

図から作り始めない。先に設計図で各ページのヘッド（`見出し`）と論理を決め、それを原稿に写す。

- 数字を作らない。素材に無い数字は、前提を明記した試算にするか「xx」で残す（それらしく埋めない）。素材に無い固有名詞・出来事を足さない。

### 2.1 設計図（design.md）
書式は `assets/sample/design.md`（`init` が `<名前>/design.md` に置く雛形。中身は見本）に従う。1 枚物なら、資料全体と台帳は省く。

- 資料全体: **ガバニングメッセージ**（資料全体の結論）を 1 つ立て、各ページのヘッドをその下にぶら下げる。**論点**（決めさせること）は 3〜6 個に番号を付ける。冒頭のサマリで番号つきで予告し、最終ページで同じ番号で回収する。最終ページは、決定事項・日程・判断基準を載せた一番重いページにする。
- 台帳を先に作る: `| No | ヘッド | 文型 | 上位への集約 | 直前からの接続語 | 本体の型 | 論点 |`。縦の検証: ヘッドを縦に通読し、隣り合うページが「だから／なぜなら」で繋がる。横の検証: 同じ階層の並びは切り口 1 つ・粒度をそろえる（「何で割ったか」を 1 語で言える）。
- ページごと: ヘッド／文型／型（`references/components.md` の一覧から）／図表タイトル（名詞句。時点と単位を含める）／レイアウト記述（縦軸・横軸・各エリアの中身・強調の 1 点）／証拠対応表（ヘッドの各節を、本体のどの要素が証明するか）／注記と出所（出所は必要なときだけ）。

### 2.2 ヘッドの規則（`見出し`）
細則（判断語の例・文型・書き方の 5 段階・逆テスト・`lint-script` が見るものと人が見るもの）は [references/head-rules.md](references/head-rules.md) にある。ヘッドを書く前に読み、従う。要点:
- 主語と述語のある完全な文で、事実＋判断を 1 文に持つ。判断語は `lint-script` の固定リスト。1 ページ 1 メッセージ。
- 30〜60 字。まず 1 行（28px で約 41 字）に収め、入らないときだけ 2 行（題の高さを `height:80px` にする）。
- 禁止: 「A。B」の二段構え／要素の数え上げ／体言止め／ダッシュ（—）／自己言及。実質数値は 1 文に 2 つまで。隣り合う 3 枚で同じ文型を続けない。
- So What 帯は置かず、示唆はヘッドに書く。決定を求めるページだけ論点ボックスに「〜の可否」を 1 行で書く。

### 2.3 原稿（script.md）
書式は `assets/sample/script.md`（書式の手本であり、構成の手本ではない。決定のページが 2 枚目（S03）で、§2.1 の「最終ページで回収」の構成とは逆。11 枚。表紙と、見本の 10 枚の内容。架空の会社の中期経営計画）に従う。冒頭に目的・対象・`論点`（設計図の論点を番号つきの項目で）・配色を書き、スライドごとに次を書く。

- `layout`（`cover|section|agenda|content|diagram|table|chart|closing`）、`見出し`（**2.2 の規則に従うヘッド**）、`章名`（そのスライドが答える問い）、`本文`、`図表`（型と選んだ理由を 1 行）、必要なときだけ `出典`、判断が要るスライドは `判断の枠`（決めること・期限・推奨）。
- 1 スライド 1 メッセージ。結論 → 根拠の順。出典は必要なときだけ書く（既定では書かない）。スピーカーノートは作らない。
- 書いたら `python "${CLAUDE_SKILL_DIR}/run.py" lint-script "<名前>/script.md"`。問題は全件出る。空になり、5.1 のヘッド・論理の確認を済ませてから、設計図と原稿を一緒にチャットで示して承認を求める。承認後は、承認なしに内容を変えない。
- `lint-script` が検査する範囲と、人が見る範囲（完全文・体言止め・数え上げ・行数・逆テスト・縦読み・論点の回収・証拠対応）は [references/head-rules.md](references/head-rules.md) の表にある。

## 3. スライド案（3 案）

1. `assets/components/` の断片から、設計図の型とレイアウト記述に合う型を選ぶ（`references/components.md`）。断片をコピーして、内容と数字を差し替え、`<名前>/slides/NN-A.html` に書く。
2. **3 案は、同じ型のまま配置・強調・密度を変える**（A: 標準／B: 強調や大きな数字を前に出す／C: 情報量を増やして密度を上げる）。基本として、**図と表を多用して説明する**。内容（文言と数字）は 3 案で同じ。
3. `python "${CLAUDE_SKILL_DIR}/run.py" variants "<名前>"` → `<名前>/variants.html`。Playwright MCP の `browser_navigate` で `file:///C:/.../variants.html` を開き、「左の一覧から 1 枚ずつ見て、案を選び、直したい点はコメントに書いて、判断欄の右端の『回答をコピー』を押してください」と伝える。**`browser_resize` で窓の大きさを変えない**。ページの構成とボタンの扱いは [references/review-flow.md](references/review-flow.md)。
4. 「回答をコピー」が押されるのを待つ（ユーザーに「完了」と入力させない）。押されると `window.__submitted` が立つ。`browser_evaluate` で次を実行し、送信されるか約 100 秒たつまでブロックして結果を返す。`submitted` が false なら同じ呼び出しを繰り返す（合計約 30 分、18 回まで）。ユーザーがターミナルに入力したときは待ちをやめて、その内容に従う。

   `() => new Promise(res => { const t0 = Date.now(); const id = setInterval(() => { if (window.__submitted || Date.now() - t0 > 100000) { clearInterval(id); res({ submitted: !!window.__submitted, md: window.__answersMd }); } }, 500); })`

5. `submitted` が true なら、`md` を `<名前>/answers-N.md` に書く（N は何回目か）。利用者がチャットに貼り付けた md も同じように書く。回答の書式は [references/review-flow.md](references/review-flow.md)。
6. **コメントがあるスライドだけ**、選ばれた案を直して 1 案にし（`NN-A.html` を上書き、`NN-B/C` は削除）、`variants --round N+1` で再提示する。**利用者には直したスライドだけ答えてもらう**。コメントが未反映のうちは `finalize` が止まる。別案に戻す条件と `round-(N+1)-notes.md` の書き方は [references/review-flow.md](references/review-flow.md)。
7. すべて決まったら、これまでの回答を**回の順に全部**渡す: `python "${CLAUDE_SKILL_DIR}/run.py" finalize "<名前>" --answers "<名前>/answers-1.md" --answers "<名前>/answers-2.md"` → `final.html`（`build` が使う素のページ。変えない）と、確認用の `final-review.html`。
8. `final-review.html` を `browser_navigate` で開き、「1 枚ずつ見て、『承認』か『要修正』を選び、『回答をコピー』を押してください」と伝える。待ち方と `md` の扱いは 4・5 と同じ（保存先は `<名前>/answers-final.md`）。『要修正』があれば、コメントに沿って `slides/` を直して `finalize` からやり直す。チャットで承認を受けた場合は、この手順は省いてよい。細則は [references/review-flow.md](references/review-flow.md)。

### 型の選び方
型の一覧（51 本の用途・使い分け・決定の型か情報の型か・文書の種類ごとの組み合わせ）は [references/components.md](references/components.md) にある。選ぶ前に読み、各断片の先頭のコメント（用途・差し替える所）も読む。

- 本文の部品に共通の構成: 見出し（判断を言い切る 1 文）→ 図表タイトル（`data-role="lead"`）→ 図表本体 → 注（`caption`）。箱・行・棒のすべてに定量を 1 つ以上書き、本文領域の下端（y 640）まで使う。
- **決定を求める型**は最下部に論点ボックス（「論点　〜の可否」1 行）を置く。**情報の型**は論点ボックスを置かず、注の末尾を「→ 含意」の 1 文で締める。
- 内容に合う型がなければ、断片の部品で組む。新しい型を作ったら、`assets/components/` に足し、一覧にも加え、`check` で違反が 0 件になることを確かめる。

## 4. HTML の書き方

細則（部品のクラス・`data-role`・`data-note`・色・文字サイズ・視線誘導・`data-chart`・配色の 3 役・配置の 4 原則・記号文法・階調・グラフと表の作法・禁止事項）は [references/html-rules.md](references/html-rules.md) にある。断片を書く前に読み、従う。最低限:

- 1 枚 = `<section class="slide" data-layout="…">`（1280×720px）。部品は `pp-text`・`pp-shape`・`pp-line`・`pp-image`・`pp-table`・`pp-chart` だけ。**これ以外のクラスの文字や図は PPTX に出ない**。
- 色は `var(--accent)` などの変数だけ。**強調色（`f-emph`・`t-emph`）は 1 スライドに 1 点**。
- 本文 14pt（約 19px）以上、注記 10pt（14px）以上。ダッシュ（—）はどこにも使わない。

## 5. PPTX の出力

`python "${CLAUDE_SKILL_DIR}/run.py" build "<名前>" [--footer "文言"]`。出力 JSON の `ok` が false なら、`violations` を読んで `slides/` の断片を直し、`finalize` からやり直す（内容は変えない。直すのは配置・サイズ・色）。直しが原稿の変更（文章を減らす、スライドを分ける）を伴うときは、案を示して利用者の承認を得る。

`ok` が true なら、`pngs`（確認用の画像。LibreOffice の描画）を開いて崩れを確認し、所見を伝える。PowerPoint で開いて最終確認することを勧める。成果物は `<名前>/<名前>.pptx`。

`violations` の `rule`（`overflow`・`overlap`・`keepout`・`fontMin`・`contrast`・`imageAlt`・`bodyImage`・`titleMissing` と、警告の `dash`・`sameWord`・`orphanLine`・`emptyBand`）ごとの直し方は [references/check-rules.md](references/check-rules.md) にある。

警告（`severity: warning`）は `ok` を false にしないが、5.1 で 0 件にする。`build` の前に見るときは `python "${CLAUDE_SKILL_DIR}/run.py" check "<名前>/final.html"`。

### 5.1 工程5（計測で検証）
出す前（設計図と原稿の承認①の前と、PPTX を渡す前）に、次を自分で確認し、外れていれば直す。

- ヘッド: `lint-script` が空。加えて、完全文か・体言止めや数え上げがないか・実質数値は 2 つまでか・1 行（約 41 字）に入るか（入らなければ 2 行。それでも超えるなら設計図に戻る）。
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
