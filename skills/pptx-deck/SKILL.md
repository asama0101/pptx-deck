---
name: pptx-deck
description: テーマ・素材・原稿から、コンサルテイストの承認資料（稟議・提案・計画）を作る。原稿(Markdown)の承認 → HTML スライド案（各 3 案）の選択 → 最終 HTML の承認 → 編集可能な PowerPoint(.pptx) の順に進める。利用者の PPTX テンプレート（表紙・裏表紙・ヘッダー・フッター）に従える。「スライドを作って」「資料を作って」「PowerPoint を作って」「稟議資料」「提案資料」「デッキ」と頼まれたときに使う。既存 PPTX の編集には使わない。Windows 専用。
---

# pptx-deck

ビジネス上の承認文書を、コンサル資料のテイストで作る。本文を画像にせず、PowerPoint で編集できる .pptx を出す。13.33×7.5in（16:9）、BIZ UDPゴシック、無彩色＋基調 1 色＋強調 1 色。

以降の `<skill>` は、この SKILL.md があるフォルダ。コマンドはすべて `python "<skill>/run.py" …`。`<名前>` は作業フォルダ名（実行したディレクトリ直下に作る）。

## 0. 初回だけ（環境）

1. `python "<skill>/run.py" doctor` を実行する。`venv` がない（終了コード 3）または `status` に不足があるときは、**利用者に「`%LOCALAPPDATA%\pptx-deck\venv` に Python の仮想環境と chromium（数百 MB）を導入してよいか」を確認する**。承認が出るまで作らない。
2. 承認後、`python "<skill>/run.py" setup --yes`。
3. `doctor` の `warnings` を利用者に伝える（BIZ UDPゴシック未導入、LibreOffice なしなど）。

## 1. 流れ（承認は 3 回）

| 段階 | やること | 承認 |
|---|---|---|
| 入力 | 下の「1.1 入力で聞くこと」 | |
| 原稿 | `<名前>/script.md` を書く。`lint-script` が空になるまで直す | ① チャットで承認（内容を凍結） |
| スライド案 | 全スライドの 3 案を `slides/NN-A.html`〜に書き、`variants` で 1 つの HTML にする | ② HTML 上で選択＋コメント |
| 最終 HTML | 選ばれた案を `finalize` で統合し、`final-review.html` で全体を見せる | ③ HTML 上で承認／要修正（チャットでの承認でもよい） |
| PPTX | `build` で書き出し、検査と確認用の画像で崩れを確認する | |

### 1.1 入力で聞くこと
- 入口: テーマのみ／素材（メモ・文書・データ）／既存の Markdown 原稿。足りない前提（対象者・目的・枚数・期限）は先に質問する。外れたときの手戻りが大きいものは推測しない。
- 配色: プリセット（`navy`・`green`・`gray`）か、基調色 `#RRGGBB`。指定がなければ `navy`。
- 利用者の PowerPoint テンプレートの有無（`.potx` または `.pptx` のパス）。あれば、**表紙・裏表紙・ヘッダー・フッター**がそれに従う。フォントと配色は、テンプレートにかかわらず BIZ UDPゴシックと選んだ配色。16:9（13.33×7.5in）以外のテンプレートは使えない。
- フッターの文言（社外秘など）があれば `build --footer`。

### 1.2 作業フォルダ
`python "<skill>/run.py" init "<名前>" --color <プリセット|#RRGGBB> [--template "<パス>"]`。同名のフォルダが空でないときは止まる。**中身を利用者に見せて、上書きしてよいと言われたときだけ `--force`**。`init` の出力の `notes`（テンプレートの代替レイアウト、`slides/` に前の作業のファイルが残っている旨）は利用者に伝える。`--force` は既存のファイルを消さない（`theme.css` などを上書きするだけ）ので、古い案が混ざらないよう、不要な `slides/` のファイルは利用者に確認してから削除する。

| 置き場所 | ファイル |
|---|---|
| スキル `<skill>/`（読み取り専用） | `SKILL.md`、`assets/`（`components/` の断片、`web/`、`icons/`、`template/`）、コード |
| 作業フォルダ `<名前>/` | `script.md`、`slides/NN-X.html`、`variants.html`、`final.html`、`<名前>.pptx`、`theme.css`・`base.css`・`icons/`・`_template/`（`init` が作る） |
| OS の一時フォルダ `%TEMP%\pptx-deck\<名前>\` | 確認用の PNG（`render/`）、SVG の画像化 |

## 2. 原稿（script.md）

書式は `assets/sample/script.md`（10 枚）に従う。スライドごとに次を書く。

- `layout`（`cover|section|agenda|content|diagram|table|chart|closing`）、`見出し`（**結論を言い切る 1 文**）、`章名`（そのスライドが答える問い）、`本文`、`図表`（型と選んだ理由を 1 行）、必要なときだけ `出典`、判断が要るスライドは `判断の枠`（決めること・期限・推奨）。
- 1 スライド 1 メッセージ。結論 → 根拠の順。出典は必要なときだけ書く（既定では書かない）。スピーカーノートは作らない。
- 書いたら `python "<skill>/run.py" lint-script "<名前>/script.md"`。問題は全件出る。空になってからチャットで承認を求める。承認後は、承認なしに内容を変えない。

## 3. スライド案（3 案）

1. `assets/components/` の断片から、内容に合う型を選ぶ（下の一覧）。断片をコピーして、内容と数字を差し替え、`<名前>/slides/NN-A.html` に書く。
2. **3 案は、同じ型のまま配置・強調・密度を変える**（A: 標準／B: 強調や大きな数字を前に出す／C: 情報量を増やして密度を上げる）。基本として、**図と表を多用して説明する**。内容（文言と数字）は 3 案で同じ。
3. `python "<skill>/run.py" variants "<名前>"` → `<名前>/variants.html`。Playwright MCP の `browser_navigate` で `file:///C:/.../variants.html` を開き、「左の一覧から 1 枚ずつ見て、案を選び、直したい点はコメントに書いて、判断欄の右端の『回答をコピー』を押してください」と伝える。ページは、左に一覧（状態の点つき）、右に大きな 1 案と下に案のサムネ（押すと大きく見える）、コメント欄、前へ／次へ。見てほしい要素に付けた `data-note` は、枠と番号で重なる。ページの構成は、点検ページ（Artifact）と同じ。左に一覧（状態の点つき）、右に 1 枚ずつ縦に並べる（大きなスライド → 見どころ・前回のコメント・今回の直し → 判断欄）。スクロールして見る（1280×720〜1920×1080 で確認済み）。**`browser_resize` で窓の大きさを変えない**（窓とページの大きさがずれる）。3 択の下に「承認／要修正」のボタンがある（案を選んでいなければ、表示中の案が選ばれる。1 案だけのスライドはこのボタンだけで答える）。選んだラジオとボタンは、もう一度押すか「選択を外す」で外せる。「回答をコピー」は判断欄の最後の行（右端）にある（固定しない）。
4. 「回答をコピー」が押されるのを待つ（ユーザーに「完了」と入力させない）。押されると、回答はクリップボードに入り、同時に `window.__submitted` が立つ。`browser_evaluate` で次を実行し、送信されるか約 100 秒たつまでブロックして結果を返す。`submitted` が false なら同じ呼び出しを繰り返す（合計約 30 分、18 回まで）。ユーザーがターミナルに入力したときは待ちをやめて、その内容に従う。

   `() => new Promise(res => { const t0 = Date.now(); const id = setInterval(() => { if (window.__submitted || Date.now() - t0 > 100000) { clearInterval(id); res({ submitted: !!window.__submitted, md: window.__answersMd }); } }, 500); })`

5. `submitted` が true なら、`md` を `<名前>/answers-N.md` に書く（N は何回目か）。待ち受けずに、利用者がチャットに貼り付けた場合も、貼られた md を同じように書く。回答の形式は `## SNN` / `- 選択:` / `- 判定:`（承認・要修正。空でもよい。古い回答にはない）/ `- コメント:`。ボタンは「回答をコピー」の 1 つだけ（送信ボタンはない）。`finalize` は、判定が「要修正」のスライドも、コメントが残るスライドと同じく止める。
6. **コメントがあるスライドだけ**、選ばれた案を直して 1 案にし（`NN-A.html` を上書き、`NN-B/C` は削除）、`variants --round N+1` で再提示する（「採用／要修正」の選択になる）。ページには全スライドが出るが、**利用者には直したスライドだけ答えてもらう**（ほかは前回の選択のまま。未回答でよい）。別案の希望があるときだけ 3 案に戻す。コメントが未反映のうちは `finalize` が止まる。再提示のページは、前回のコメントを `answers-N.md` から自動で出す。**直した内容は `<名前>/round-(N+1)-notes.md` に「NN: 直した内容」の行で書く**と、同じスライドの「今回の直し」として並ぶ（書かなくてもよい）。
7. すべて決まったら、これまでの回答を**回の順に全部**渡す: `python "<skill>/run.py" finalize "<名前>" --answers "<名前>/answers-1.md" --answers "<名前>/answers-2.md"` → `final.html`（`build` が使う素のページ。変えない）と、確認用の `final-review.html`。後の回答が前の回答を上書きし、選択が空のスライドは前の回答を消さない。
8. `final-review.html` を `browser_navigate` で開き、「1 枚ずつ見て、『承認』か『要修正』を選び、『回答をコピー』を押してください」と伝える。待ち方と `md` の扱いは 4・5 と同じ（保存先は `<名前>/answers-final.md`）。『要修正』があれば、コメントに沿って `slides/` を直して `finalize` からやり直す。チャットで承認を受けた場合は、この手順は省いてよい。`finalize` を使わずにページだけ作り直すときは `review-final "<名前>" --answers …`（`finalize` と同じ引数）。

### 型の一覧（`assets/components/`）
- レイアウト: `cover`（表紙）・`section`（章扉）・`agenda`（目次）・`decision`（判断・承認依頼）・`closing`（裏表紙）
- 図解: `flow-h`（手順）・`tree`（分解）・`matrix`（2×2）・`pyramid`（階層・優先度）・`cycle`（循環）・`gantt`（計画）・`venn`（重なり）・`before-after`（前後）・`layers`（構成）・`compare`（3 案の比較）
- 表: `compare`（比較）・`rating`（◎○△）・`cost`（費用）・`schedule`（予定）
- グラフ: `bar`・`line`・`stacked`・`waterfall`（注目点を吹き出しで書く。グラフは全幅）と、所見が長文のときの `bar-note`・`line-note`・`stacked-note`・`waterfall-note`（右の欄に「グラフから分からないこと」を書く）。円グラフ（`pie`）の型は置かない（`data-chart` の `pie` は使える。書き方は断片のコメントと下記）
- 内容に合う型がなければ、断片の部品（下記）で組む。新しい型を作ったら、`assets/components/` に足して `tests/test_components.py` を通す。

## 4. HTML の書き方

- 1 枚 = `<section class="slide" data-layout="…">`（1280×720px）。部品は `pp-text`・`pp-shape`・`pp-line`・`pp-image`・`pp-table`・`pp-chart` だけ。**これ以外のクラスの文字や図は PPTX に出ない**。
- 見てほしい要素（題・強調・差し替える所など、2〜4 点）には `data-note="題：結論の一文"` を付ける。レビューページが枠と番号で示す。同じ文を付けた要素は 1 つの見どころとして、枠でまとまる。PPTX には影響しない。型庫（`assets/components/`）の断片には付けてある。差し替えるときは、文が内容に合うかを見直す。
- 位置は `style="left;top;width;height"`（px）。文字には必ず幅を付ける。面と文字は兄弟要素にし、文字の中心を含む面が背景色になる。
- 文字: `data-role` = `title|lead|body|caption|display`。表紙・裏表紙の題と副題は `data-ph="title|subtitle"`（位置はテンプレート）。箇条書きは `<div class="pp-text"><ul><li>`。
- 色は `var(--accent)` などの変数だけ。基調色の文字は白地かつ 24px 以上のときだけ（薄い面の上の大きな数字は `num t-dark`）。**強調色（`f-emph`・`t-emph`）は 1 スライドに 1 点**（推奨・承認を求める対象）。
- 本文 14pt（約 19px）以上、注記 10pt（14px）以上。出典を書くときだけ、`data-role="caption" data-chrome` で本文領域の下端（`top:calc(var(--area-y) + var(--area-h))`。標準は y 640〜664）に置く。領域が標準より狭いテンプレートでは、出典が上がって本文と重なるので、`overlap` の指摘に従って本文の位置を直す。
- 視線誘導: 読む順は **Z の法則**（左上 → 右上 → 左下へ斜め → 右下）に従い、始点（題・結論）を左上、終点（承認・結論の帯）を右下まで届かせる。文の寄せ方は変えない（文は左寄せ。右寄せは数字の列だけ）。使える場面では次の 3 つも使う。**矢印効果**（矢印で読む順・因果を示す。循環は輪と矢印で回して見せ、直線の矢印だけにしない。矢印は矢じり付きで、手順・因果の図には必ず入れる）、**孤立効果**（目立たせたい 1 点だけ色・大きさを変える。強調色は 1 点）、**類同の法則**（同じ種類の要素は形・色・大きさをそろえ、違う種類は変える）。
- 画像はアイコン（`icons/<名前>-<accent|emphasis|white|gray>.svg`、`alt` 必須）と利用者の写真だけ。
- 重ねる図（ベン図など）は、重なる要素の両方に `data-overlap`。
- グラフ: `data-chart='{"type":"bar|barh|line|pie|stacked|stacked100|waterfall","categories":[…],"series":[{"name":"…","values":[…]}],"highlight":番号,"fmt":"#,##0","totals":[…]}'`。ブラウザのプレビューは近似で、実際は PowerPoint のグラフになる。

## 5. PPTX の出力

`python "<skill>/run.py" build "<名前>" [--footer "文言"]`。出力 JSON の `ok` が false なら、`violations` を読んで `slides/` の断片を直し、`finalize` からやり直す（内容は変えない。直すのは配置・サイズ・色）。直しが原稿の変更（文章を減らす、スライドを分ける）を伴うときは、案を示して利用者の承認を得る。

`ok` が true なら、`pngs`（確認用の画像。LibreOffice の描画）を開いて崩れを確認し、所見を伝える。PowerPoint で開いて最終確認することを勧める。成果物は `<名前>/<名前>.pptx`。

| rule | 直し方 |
|---|---|
| `overflow` | 文字の枠を広げるか、文章を減らす |
| `overlap` | 位置をずらす。意図的なら両方に `data-overlap` |
| `keepout` | テンプレートのヘッダー・フッターの領域（y 676 以降が標準）を避ける |
| `fontMin` | 本文 14pt（19px）・注記 10pt（14px）以上にする |
| `contrast` | 文字色か面の色を変える（基調色の文字は白地で 24px 以上） |
| `imageAlt`・`bodyImage` | `alt` を付ける／本文を画像にしない |
| `titleMissing` | `data-role="title"`（表紙・裏表紙は `data-ph="title"`）を付ける |

## 6. 守ること

- 原稿の承認後は、承認なしで内容を変えない。
- 仮想環境は、承認なしに作らない。既存の作業フォルダは、中身を見せて承認を得てから上書きする。
- エラーが出たら、原因と対処を示して止まる。推測で別の方法に切り替えない。
- スクリプトは Playwright MCP を使わない。MCP は、案の選択の受け取りと画面確認だけに使う。
