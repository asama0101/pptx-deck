---
name: create
description: テーマ・素材・原稿から、コンサルテイストの承認資料（稟議・提案・計画）を新しく作る。設計図と原稿(Markdown)を書く → HTML スライド案（型の 3 案と自由設計の 1 案）の選択 → 編集可能な PowerPoint(.pptx) の順に進める（承認は②のスライド案の選択の 1 回。直しは完成後に revise）。利用者の PPTX テンプレート（表紙・章扉・目次などのレイアウト、ヘッダー・フッター）の上に作れる。「スライドを作って」「資料を作って」「PowerPoint を作って」「稟議資料」「提案資料」「デッキ」と頼まれたときに使う。作った PPTX の直しには revise、設計図と原稿を見たいと頼まれたときの確認には review-plan を使う。既存の PPTX の編集には使わない。Windows 専用。
compatibility: Windows 専用。Python 3.10 以上と Claude Code。専用の仮想環境（`${CLAUDE_PLUGIN_DATA}` の下）だけで動かし、なければ承認を得て作る（システムの Python には何も入れない）。スライド案の選択に Playwright MCP が必要（ないときは回答を貼り付ける）。LibreOffice は使わない。
allowed-tools: 'Bash(python "${CLAUDE_PLUGIN_ROOT}/run.py" *)'
---

# pptx-deck

ビジネス上の承認文書を、コンサル資料のテイストで作る。本文を画像にせず、PowerPoint で編集できる .pptx を出す。13.33×7.5in（16:9）、BIZ UDPゴシック、無彩色＋基調 1 色＋強調 1 色。

`${CLAUDE_PLUGIN_ROOT}` は、このプラグインのフォルダ（Claude Code が実パスに置き換える）。コマンドはすべて `python "${CLAUDE_PLUGIN_ROOT}/run.py" --data "${CLAUDE_PLUGIN_DATA}" …`。`<出力先>` は成果物を置くフォルダ、`<成果物名>` は成果物の名前で、どちらも開始ページ（1.0）で決まる。`<元データ>` は `<出力先>/pptx-deck-source/<成果物名>`（作業ファイルの置き場）で、コマンドの作業フォルダの引数はすべて `"<元データ>"` にする。PPTX は `<出力先>/<成果物名>.pptx` に出る。references の中のコマンドに書かれた `${CLAUDE_PLUGIN_ROOT}`・`${CLAUDE_PLUGIN_DATA}` は、references が展開されないので、この SKILL.md に展開された実パスに読み替えて実行する。

## 0. 初回だけ（環境）

1. `python "${CLAUDE_PLUGIN_ROOT}/run.py" --data "${CLAUDE_PLUGIN_DATA}" doctor` を実行する。終了コード 3 のときは、専用の仮想環境がない・版がずれている・作成元の Python が足りない（3.10 以上、venv と ensurepip が必要）のどれかで、出力に理由が出る。**利用者に「`${CLAUDE_PLUGIN_DATA}` の下に Python の仮想環境と chromium（数百 MB。chromium は他のツールと共有の場所）を導入してよいか」を確認する**（旧い `%LOCALAPPDATA%\pptx-deck\venv` は使わず、新しい置き場に作り直す）。承認が出るまで作らない。システムの Python には何も入れない。
2. 承認後、`python "${CLAUDE_PLUGIN_ROOT}/run.py" --data "${CLAUDE_PLUGIN_DATA}" setup --yes`。
3. `doctor` の `venv`（仮想環境の場所）・`python.path` と `warnings`（BIZ UDPゴシック未導入など）を利用者に伝える。

## 1. 流れ（承認は②の 1 回）

| 段階 | やること | 承認 |
|---|---|---|
| 開始 | 下の「1.0 開始ページ」で、入力・保存先（`<出力先>`）・成果物名を決める | |
| 入力 | 下の「1.1 入力で聞くこと」 | |
| 設計図 | 図を作る前に `<元データ>/design.md` を書く（ガバニングメッセージ・論点・台帳・ページごとの設計。2.1） | なし（承認は求めない） |
| 原稿 | `<元データ>/script.md` を書く。`lint-script` が空になるまで直す | なし（`lint-script` と 5.1 の自己確認だけ。利用者が見たいと頼んだときだけ review-plan） |
| スライド案 | 全スライドの案（型の A/B/C と自由設計の R）を `<元データ>/slides/NN-A.html`〜に書き、`variants` で 1 つの HTML にする | ② HTML 上で選択＋コメント（部位のバッジで部位を指定できる。唯一の承認） |
| 最終 HTML | 選ばれた案を `finalize` で統合する（`final-review.html` は完成後の参照用。承認は求めない） | |
| PPTX | そのまま `build` で書き出し、検査と確認用の画像（`final.html` の撮影）で崩れを確認する。直しは完成後に `revise` | |

### 1.0 開始ページ（最初にやる）
1. `python "${CLAUDE_PLUGIN_ROOT}/run.py" --data "${CLAUDE_PLUGIN_DATA}" start-page` を実行する。出力は、入力（ファイルかテキスト）・保存先のフォルダ・成果物名を選ぶ HTML のパス。一覧は作業フォルダの中だけで、ほかの場所は利用者がパス欄に手動で書く。
2. そのパスを Playwright MCP の `browser_navigate` で `file:///C:/…` として開き、「入力と保存先、成果物の名前を選んで、『回答をコピー』を押してください」と伝える。`browser_resize` で窓の大きさを変えない。ページを開いたあとに作業フォルダへ置いたファイルが一覧にないと言われたら、「フォルダを読み直す」を押してもらう（Playwright MCP のブラウザでは、フォルダ選択の代わりに、ページの作り直しを頼む `window.__regenerate` が立つ。次の 3）。
3. 3 章の手順 4 と同じ待ち方（約 100 秒ずつ、18 回まで、続行方法の質問を含む）で、次のスクリプトを `browser_evaluate` で実行する。`submitted` が true なら `md` を取る。`regenerate` が true なら、`start-page` を実行し直して新しいパスを開き直し（選んだ内容は消えると伝え、2 の案内をもう一度する）、待ちの回数を数え直して待つ。どちらも false なら同じ呼び出しを繰り返す。Playwright MCP がないときは、利用者に回答を貼り付けてもらう。

   `() => new Promise(res => { const t0 = Date.now(); const id = setInterval(() => { if (window.__submitted || window.__regenerate || Date.now() - t0 > 100000) { clearInterval(id); res({ submitted: !!window.__submitted, regenerate: !!window.__regenerate, md: window.__answersMd }); } }, 500); })`

4. 回答の md を、セッションのスクラッチパッド（OS の一時フォルダ。プロジェクトの中ではない）に保存する。
5. `python "${CLAUDE_PLUGIN_ROOT}/run.py" --data "${CLAUDE_PLUGIN_DATA}" intake "<保存した回答ファイル>"` を実行する。何も作らず、JSON（`kind`・`files`・`text`・`out_dir`・`name`・`workdir`・`pptx`・`collisions`）を出す。
   - 終了コード 2: 標準エラーのメッセージを利用者に伝え、開始ページからやり直すか、入力し直してもらう。
   - 終了コード 4: `collisions` の PPTX か元データが既にある。どのパスがあるかを利用者に伝え、「上書き」か「別の成果物名」かを聞く（黙って上書きしない。番号を自動で付けない）。上書きなら `intake` を `--allow-existing` 付きでやり直し、1.2 の `init` に `--force`、5 章の `build` に `--force` を付ける。別名なら開始ページからやり直す。
   - 成功: 出力の `workdir` が `<元データ>`、`pptx` が PPTX の置き場。1.2 の `init "<workdir>"`（`kind` が `text` なら `--input-from` 付き。次の 6）に進む。
6. `kind` が `text` のときは、本文を自分で書き写さない（長い文書が短くなるため）。`init` に `--input-from "<保存した回答ファイル>"` を付けると、`init` が `<元データ>/input.md` に本文をそのまま書く。`file` のときは、`files` のファイルを素材として読む（`--input-from` を付けても何もしない）。

### 1.1 入力で聞くこと
- 入口: テーマのみ／素材（メモ・文書・データ）／既存の Markdown 原稿。足りない前提（対象者・目的・枚数・期限・欠けている数字）は、作業を始める前にまとめて質問する。外れたときの手戻りが大きいものは推測しない。
- 配色: プリセット（`navy`・`green`・`gray`）か、基調色 `#RRGGBB`。指定がなければ `navy`。
- 利用者の PowerPoint テンプレートの有無（`.potx` または `.pptx` のパス）。あれば、**全スライド**がテンプレートのレイアウトの上にできる（表紙・本文・裏表紙に加え、章扉・目次などの専用レイアウトも使う。使うのはタイトルの位置・背景・ロゴ・ヘッダー・フッターで、中身は図形で描く。専用レイアウトがない種類・型は本文で代える）。フォントと配色は、テンプレートにかかわらず BIZ UDPゴシックと選んだ配色。16:9（13.33×7.5in）以外のテンプレートは使えない。
- フッターの文言（社外秘など）があれば `build --footer`。

### 1.2 作業フォルダ
`python "${CLAUDE_PLUGIN_ROOT}/run.py" --data "${CLAUDE_PLUGIN_DATA}" init "<元データ>" --color <プリセット|#RRGGBB> [--template "<パス>"] [--input-from "<保存した回答ファイル>"]`（`--input-from` はテキスト入力のとき。1.0 の 6）。同名のフォルダが空でないときは止まる。**中身を利用者に見せて、上書きしてよいと言われたときだけ `--force`**。`init` の出力の `notes`（テンプレートの代替レイアウト、`slides/` に前の作業のファイルが残っている旨）は利用者に伝える。**テンプレートを指定したときは、出力の `layout_map` を対応表にして利用者に見せ、確認する**（表: 種類・型／推定したレイアウト／ない場合は「本文で代用」。専用レイアウトがない型は 1 行にまとめて示す。推定は名前による。レイアウト一覧と、各レイアウトのプレースホルダーも添える）。違う点は `template-map "<元データ>" --set 型=レイアウト名`（`--clear 型` で本文に戻す）で `template.json` に反映し、出力を見せて確かめる。標準テンプレートのときは確認しない。`--force` は既存のファイルを消さない（`theme.css` などを上書きするだけ。ただし渡さなかった `--color`・`--template`・`--footer` は既存の `template.json` の値を残す（前の利用者テンプレートのファイルが消えているときは `--template` が要るというエラーで止まる。標準テンプレートで作った成果物なら標準から写し直す）。渡したものは上書きする。同名のフォルダを使い回して標準テンプレートやフッターなしにしたいときは、前の設定が残らないよう明示して渡す。テンプレートを残したときも `layout_map` を見せて確認する。`design.md` は、既にあれば上書きしない）ので、古い案が混ざらないよう、不要な `slides/` のファイルは利用者に確認してから削除する。

| 置き場所 | ファイル |
|---|---|
| プラグイン `${CLAUDE_PLUGIN_ROOT}`（読み取り専用） | `skills/`、`assets/`（`components/` の断片、`web/`、`icons/`、`template/`）、`references/`、コード |
| `<出力先>/` | `<成果物名>.pptx`（成果物）と `pptx-deck-source/<成果物名>/`（`<元データ>`） |
| `<元データ>/` | `design.md`（`init` が雛形を置く）、`script.md`、`slides/NN-X.html`、`answers-*.md`、`template.json`、`_template/template.<拡張子>`、`build.json`。作業中だけ `variants.html`・`plan-review.html`・`final.html`・`final-review.html`・`theme.css`・`base.css`・`chart-preview.js`・`icons/` |
| OS の一時フォルダ `%TEMP%\pptx-deck\<成果物名>-<ハッシュ>\` | 確認用の画像（`preview/`）、SVG の画像化 |

## 2. 設計図と原稿（design.md・script.md）

図から作り始めない。先に設計図で各ページの題・ヘッドメッセージ（ヘッド。`題`・`ヘッドメッセージ`）と論理を決め、それを原稿に写す。

- 数字を作らない。素材に無い数字は、前提を明記した試算にするか「xx」で残す（それらしく埋めない）。素材に無い固有名詞・出来事を足さない。

### 2.1 設計図（design.md）
書式は `${CLAUDE_PLUGIN_ROOT}/assets/sample/design.md`（`init` が `<元データ>/design.md` に置く雛形。中身は見本）に従う。1 枚物なら、資料全体と台帳は省く。

- 資料全体: **ガバニングメッセージ**（資料全体の結論）を 1 つ立て、各ページのヘッドをその下にぶら下げる。**論点**（決めさせること）は 3〜6 個に番号を付ける。冒頭のサマリで番号つきで予告し、最終ページで同じ番号で回収する。最終ページは、決定事項・日程・判断基準を載せた一番重いページにする。
- 台帳を先に作る: `| No | ヘッド | 文型 | 上位への集約 | 直前からの接続語 | 本体の型 | 論点 |`。縦の検証: ヘッドを縦に通読し、隣り合うページが「だから／なぜなら」で繋がる。横の検証: 同じ階層の並びは切り口 1 つ・粒度をそろえる（「何で割ったか」を 1 語で言える）。
- ページごと: 題／ヘッドメッセージ（ヘッド）／文型／型（`${CLAUDE_PLUGIN_ROOT}/references/patterns.md` の選定表で第 1 候補・次点を決め、`${CLAUDE_PLUGIN_ROOT}/references/components.md` の一覧で確かめる）／チャートタイトル（名詞句。時点と単位を含める）／レイアウト記述（縦軸・横軸・各エリアの中身・強調の 1 点）／証拠対応表（ヘッドの各節を、本体のどの要素が証明するか）／注記と出所（出所は必要なときだけ）。

### 2.2 題とヘッドメッセージ（ヘッド）の規則
ページ枠は 題 → ヘッドメッセージの帯 → チャートタイトル → 本体 → 注釈。**題**（原稿の `題`）は名詞句 20 字以内で主題だけを書く（判断は書かない。`lint-script` が検査）。**ヘッドメッセージ**（原稿の `見出し`）に判断を言い切る。
細則（判断語の例・文型・書き方の 5 段階・逆テスト・`lint-script` が見るものと人が見るもの）は [references/head-rules.md](${CLAUDE_PLUGIN_ROOT}/references/head-rules.md) にある。ヘッドを書く前に読み、従う。要点:
- 主語と述語のある完全な文で、事実＋判断を 1 文に持つ。判断語は `lint-script` の固定リスト。1 ページ 1 メッセージ。
- ヘッドメッセージは 30〜60 字（`check` が警告）。帯の中に収め、入らないときは設計図に戻って削る。題は 20 字以内。
- 禁止: 「A。B」の二段構え／要素の数え上げ／体言止め／ダッシュ（—）／自己言及。実質数値は 1 文に 2 つまで。隣り合う 3 枚で同じ文型を続けない。
- So What 帯は置かず、示唆はヘッドに書く。決定を求めるページだけメッセージボックスに「〜の可否」を 1 行で書く。

### 2.3 原稿（script.md）
書式は `${CLAUDE_PLUGIN_ROOT}/assets/sample/script.md`（書式の手本であり、構成の手本ではない。決定のページが 2 枚目（S03）で、§2.1 の「最終ページで回収」の構成とは逆。11 枚。表紙と、見本の 10 枚の内容。架空の会社の中期経営計画）に従う。冒頭に目的・対象・`論点`（設計図の論点を番号つきの項目で）・配色を書き、スライドごとに次を書く。

- `layout`（`cover|section|agenda|content|diagram|table|chart|closing`）、`題`（本文スライドのみ。20 字以内の名詞句）、`ヘッドメッセージ`（**2.2 の規則に従うヘッドメッセージ**）、`章名`（そのスライドが答える問い）、`本文`、`図表`（型と選んだ理由を 1 行）、必要なときだけ `出典`、判断が要るスライドは `判断の枠`（決めること・期限・推奨）。
- 1 スライド 1 メッセージ。結論 → 根拠の順。出典は必要なときだけ書く（既定では書かない）。スピーカーノートは作らない。
- 既存の型に合わない図（NW 構成図・トラフィックフロー・障害動作・自己紹介・画面への注釈など）は、`図表` に `絵/<種類>` と理由を書く。絵にする箇所があるときは、設計図と原稿を仕上げる前に `diagram` の 4 章（`${CLAUDE_PLUGIN_ROOT}/skills/diagram/SKILL.md`。`picture-plan.json`・`review-picture`）で、絵にする提案と読み取った構造を HTML で確認する（利用者が「図にして」と頼んだ箇所は提案を省き、構造だけ確認する）。
- 書いたら `python "${CLAUDE_PLUGIN_ROOT}/run.py" --data "${CLAUDE_PLUGIN_DATA}" lint-script "<元データ>/script.md"`。問題は全件出る。空になり、5.1 のヘッド・論理の確認を済ませたら、承認を挟まずに 3 章へ進む（設計図と原稿の人の承認はない。文言・数字の直しは、②のコメントか編集モードで行う）。利用者が設計図と原稿を見たいと頼んだときだけ、`review-plan` の手順で `plan-review.html` を出して確認する（任意。`review-plan` の SKILL.md）。
- `lint-script` が検査する範囲と、人が見る範囲（完全文・体言止め・数え上げ・行数・逆テスト・縦読み・論点の回収・証拠対応）は [references/head-rules.md](${CLAUDE_PLUGIN_ROOT}/references/head-rules.md) の表にある。

## 3. スライド案（型の 3 案と自由設計の R）

1. スライドの主張から「問い」を決め、`${CLAUDE_PLUGIN_ROOT}/references/patterns.md` の選定表で型の第 1 候補・次点 1・次点 2 を取る。断片は `${CLAUDE_PLUGIN_ROOT}/assets/components/` から、型の一覧は `${CLAUDE_PLUGIN_ROOT}/references/components.md`。断片をコピーして、内容と数字を差し替え、`<元データ>/slides/NN-A.html` に書く。
2. **3 案は型違い**（A: 第 1 候補／B: 次点 1／C: 次点 2。候補が足りなければ 2 案、型が一意なら 1 案）。内容（文言と数字）は全案で同じ。基本として、**図と表を多用して説明する**。**型の案に加えて、自由設計の推奨案 R（`NN-R.html`）を 1 つ足す**。R は、選定表の型にとらわれず、そのページの主張をいちばんよく見せる構成を Claude が自由に設計する（`data-variant="自由設計｜選んだ理由"`。理由には、型の案と何が違うかを書く）。部品は `pp-*` だけで、**絵（`pp-picture`）は使わない**（`variants` が止める）。デザインは 1 つだけで、`NN-R-d2.html` は作らない（R を選ぶとデザインの選択は出ない）。**図・表・グラフのページに足す**。型が一意で自由設計の余地がないページ（表紙・章扉・目次・裏表紙・単純な文章のページ）と、絵のページ（構図の案）には足さず、足さない理由は書く必要はない。R も、5.1 の検査（`check` が違反 0 件）を満たす。**デザイン違いは案にしない**: 利用者が型を選んだあとに、デザイン 1〜3 から選ぶ。デザイン 2・3 は `NN-A-d2.html`・`NN-A-d3.html`（B・C も同様）に書く。デザインを出さない型（デザイン 1 のみ）は書かなくてよい。各断片に `data-variant="型名｜選んだ理由"` を付けると、案の下に型名、大きな画面の下に理由が出る。
3. `python "${CLAUDE_PLUGIN_ROOT}/run.py" --data "${CLAUDE_PLUGIN_DATA}" variants "<元データ>"`（回は次の回が自動で選ばれる） → `<元データ>/variants.html`。Playwright MCP の `browser_navigate` で `file:///C:/.../variants.html` を開き、「左の一覧から 1 枚ずつ見て、型（A/B/C）か自由設計（R）を選び、続けてデザイン 1〜3 を選んで、画面下の『承認』か『要修正』を押してください（『承認』で次のスライドへ進みます。内容に問題がなければ『全部承認』で、案を選んだ残りをまとめて承認できます）。『要修正』は、コメント欄か部位のコメントに直したい点を書いたときだけ付き、次へ進みます。直したい点や、どの案でもない場合はコメントに書いて（案は選ばず『要修正』）、画面下の『回答をコピー』を押してください。見どころ・型と選んだ理由・部位のバッジは、題の右のチェックで出せます」と伝える。**`browser_resize` で窓の大きさを変えない**。ページの構成とボタンの扱いは [references/review-flow.md](${CLAUDE_PLUGIN_ROOT}/references/review-flow.md)。
4. 「回答をコピー」が押されるのを待つ（ユーザーに「完了」と入力させない）。押されると `window.__submitted` が立つ。`browser_evaluate` で次を実行し、送信されるか約 100 秒たつまでブロックして結果を返す。`submitted` が false なら同じ呼び出しを繰り返す（合計約 30 分、18 回まで）。18 回（約 30 分）を超えても送信されないときは、待ちをやめて、続行方法（もう一度待つ／回答を貼り付けて渡す／中止）を利用者に質問して止まる。ユーザーがターミナルに入力したときは待ちをやめて、その内容に従う。

   `() => new Promise(res => { const t0 = Date.now(); const id = setInterval(() => { if (window.__submitted || Date.now() - t0 > 100000) { clearInterval(id); res({ submitted: !!window.__submitted, md: window.__answersMd }); } }, 500); })`

5. `submitted` が true なら、`md` を `<元データ>/answers-N.md` に書く（N は何回目か）。利用者がチャットに貼り付けた md も同じように書く。回答の書式は [references/review-flow.md](${CLAUDE_PLUGIN_ROOT}/references/review-flow.md)。
6. 回答に `- 編集:` の行があれば（画面の「編集モード」で直した文字）、`python "${CLAUDE_PLUGIN_ROOT}/run.py" --data "${CLAUDE_PLUGIN_DATA}" apply-edits "<元データ>"` で断片へ反映する（直前の版は `history` に残る。`final.html` は消えるので `finalize` をやり直す。反映できなかった編集は終了コード 1 と標準エラーの一覧で分かる。断片か回答を直して `--answers <回答ファイル>` を付けて再実行するか、断片を手で直す。`final-review.html` で直した編集も、「回答をコピー」の内容を `<元データ>/answers-final.md` に保存すれば同じ手順で反映できる）。そのうえで、**コメントがあるスライドだけ**、選ばれた案を直して 1 案にし（`NN-A.html` を上書き、`NN-B/C` は削除）、`variants --round N+1` で再提示する。**利用者には直したスライドだけ答えてもらう**。コメントが未反映のうちは `finalize` が止まる。別案に戻す条件と `round-(N+1)-notes.md` の書き方は [references/review-flow.md](${CLAUDE_PLUGIN_ROOT}/references/review-flow.md)。
7. すべて決まったら、`python "${CLAUDE_PLUGIN_ROOT}/run.py" --data "${CLAUDE_PLUGIN_DATA}" finalize "<元データ>"`（`--answers` を省くと `<元データ>/answers-*.md` を回の順に全部使う。後の回答が前の回答を上書きする） → `final.html`（`build` が使う素のページ。変えない）と、完成後の参照用の `final-review.html`（承認は求めない）。`python "${CLAUDE_PLUGIN_ROOT}/run.py" --data "${CLAUDE_PLUGIN_DATA}" output-format "<元データ>"` で出力形式を読み（回答の `- 配色:` は `finalize` が反映する。PPTX が既にあるときは警告だけなので、`set-color` で変える）、`pptx` なら 5 章の `build`、`html` なら `export-html "<元データ>" --prune`、`both` なら `export-html "<元データ>"` のあとに `build` へ進む（最終 HTML の承認は挟まない。HTML 出力はグラフがブラウザの近似で、編集の画面は付かない）。`apply-edits` を使ったときは、`finalize` のあと `python "${CLAUDE_PLUGIN_ROOT}/run.py" --data "${CLAUDE_PLUGIN_DATA}" check "<元データ>/final.html"` で違反 0 件を確かめる（HTML だけの出力では `build` の検査が走らない）。直しは、完成後に `revise`（部位名で指示できる。例: 「3 枚目の出典を直して」）。

細則は [references/review-flow.md](${CLAUDE_PLUGIN_ROOT}/references/review-flow.md)。

### 型の選び方
型の選び方は [references/patterns.md](${CLAUDE_PLUGIN_ROOT}/references/patterns.md)（問い → 型 → デザインの選定表）、型の一覧（51 型・147 本の用途・判断を求める型か情報の型か・文書の種類ごとの組み合わせ）は [references/components.md](${CLAUDE_PLUGIN_ROOT}/references/components.md) にある。選ぶ前に読み、各断片の先頭のコメント（用途・差し替える所・デザイン 1 との違い）も読む。

- 本文の部品に共通の構成: 題（`data-role="title"`。20 字以内の名詞句）→ ヘッドメッセージの帯（`data-role="lead"`。判断を言い切る 30〜60 字）→ チャートタイトル → 図表本体 → 注釈（`caption`）。箱・行・棒のすべてに定量を 1 つ以上書き、本文領域の下端（y 640）まで使う。
- **判断を求める型**（`decision`・`summary`・`decisions`・`argument`・`options`・`raci`・`actions`・`gantt`）は最下部にメッセージボックス（「論点　〜の可否」1 行）を置く。**情報の型**はメッセージボックスを置かず、注釈の末尾を「→ 含意」の 1 文で締める。
- 内容に合う型がなければ、`diagram`（`${CLAUDE_PLUGIN_ROOT}/skills/diagram/SKILL.md`）の手順で、SVG の絵（`pp-picture`）にする。見本は `${CLAUDE_PLUGIN_ROOT}/assets/components/pictures/`、作法は [references/picture-craft.md](${CLAUDE_PLUGIN_ROOT}/references/picture-craft.md)。絵のページの案・承認は create の流れ（②）に従い、追加の承認は出さない。絵の中身は PowerPoint で直せない（描き直す）。新しい型やデザインを作ったら、`${CLAUDE_PLUGIN_ROOT}/assets/components/` に足し、`components.md`・`patterns.md` にも加え、`check` で違反が 0 件になることを確かめる。

## 4. HTML の書き方

細則（部品のクラス・`data-role`・`data-note`・色・文字サイズ・視線誘導・`data-chart`・配色の 3 役・配置の 4 原則・記号文法・階調・グラフと表の作法・禁止事項）は [references/html-rules.md](${CLAUDE_PLUGIN_ROOT}/references/html-rules.md) にある。断片を書く前に読み、従う。最低限:

- 1 枚 = `<section class="slide" data-layout="…">`（1280×720px）。部品は `pp-text`・`pp-shape`・`pp-line`・`pp-image`・`pp-table`・`pp-chart` と、絵の `pp-picture` だけ。**これ以外のクラスの文字や図は PPTX に出ない**。
- 色は `var(--accent)` などの変数だけ。**強調色（`f-emph`・`t-emph`）は 1 スライドに 1 点**。
- 本文 14pt（約 19px）以上、注記 10pt（14px）以上。ダッシュ（—）はどこにも使わない。

## 5. PPTX の出力

`python "${CLAUDE_PLUGIN_ROOT}/run.py" --data "${CLAUDE_PLUGIN_DATA}" build "<元データ>" [--footer "文言"] [--out <パス>] [--force]`。出力 JSON のキーは `ok`・`violations`・`pptx`・`previews`・`removed`・`notes`。`ok` が false なら、`violations` を読んで `<元データ>/slides/` の断片を直し、`finalize` からやり直す（内容は変えない。直すのは配置・サイズ・色）。直しが原稿の変更（文章を減らす、スライドを分ける）を伴うときは、案を示して利用者に確かめる。終了コード 4 は、PPTX が前回のビルド後に変更されている（手直しが消える）か、`build.json` に記録のない PPTX が既定の出力先にある（元の資料かもしれない）か、`--out <パス>` が既存のファイルを指していて `--force` がない（検査の失敗で書き出し済みのあとに同じ `--out` で再実行したときなど。その場合は `--force` を付ける）。前の 2 つは利用者に確認し、`--force`（上書き）か `--out <パス>`（別名）を選んでもらう。

`ok` が true なら、`previews`（確認用の画像。`final.html` を Chromium で撮ったもので、PPTX の実描画ではない）を開いて崩れを確認し、所見を伝える。**PowerPoint で開いて最終確認することを必ず勧める**。確認が済んだら `python "${CLAUDE_PLUGIN_ROOT}/run.py" --data "${CLAUDE_PLUGIN_DATA}" clean "<元データ>"` で一時の画像を消す。成果物は `<出力先>/<成果物名>.pptx`。`build` は成功すると、再生成できる派生ファイルを `<元データ>/` から自動で消す（`removed` に一覧が出る）。元データ（`design.md`・`script.md`・`slides/`・`answers-*.md`・`template.json` など）は残るので、あとで `revise` で直せる。

`violations` の `rule`（`overflow`・`overlap`・`keepout`・`fontMin`・`contrast`・`imageAlt`・`bodyImage`・`titleMissing`・`shapeKind` と、警告の `dash`・`sameWord`・`orphanLine`・`emptyBand`・`leadMissing`・`leadLength`・`titleLength`）ごとの直し方は [references/check-rules.md](${CLAUDE_PLUGIN_ROOT}/references/check-rules.md) にある。

警告（`severity: warning`）は `ok` を false にしないが、5.1 で 0 件にする。`build` の前に見るときは `python "${CLAUDE_PLUGIN_ROOT}/run.py" --data "${CLAUDE_PLUGIN_DATA}" check "<元データ>/final.html"`。

### 5.1 工程5（計測で検証）
出す前（設計図と原稿を仕上げる前と、PPTX を渡す前）に、次を自分で確認し、外れていれば直す。

- ヘッド: `lint-script` が空。加えて、題が主題だけの名詞句か・ヘッドメッセージが完全文で体言止めや数え上げがないか・実質数値は 2 つまでか・ヘッドメッセージの帯に収まるか（収まらなければ設計図に戻る）。
- 数値: ヘッドの数字＝本体の数字（合計）。素材に無い数字は作らず、前提を明記した試算か「xx」で残す。
- 証拠: 設計図の証拠対応表のとおり、ヘッドの各節を本体の要素が証明している（文字の注記だけで支える節を残さない）。
- 論理: ヘッドを縦に読んで筋が通る。並列の要素は切り口 1 つ・粒度がそろう。論点の番号が、サマリの予告と最終ページの回収で対応する。
- 見た目: `build` の `violations` が、エラー・警告とも 0 件。線種と塗りの意味が全ページで同じ。確認用の画像に崩れがない。

手直しは 1 周。直せない項目は、利用者への報告に「未達」と明記する（理由も添える）。内容（文言・数字）を変える直しは、②のコメントか編集モードで行う。完成後は `revise`。

## 6. 守ること

- 内容（文言・数字）の直しは、②のコメントか編集モード、完成後は `revise` で行う。承認は②の 1 回で、設計図と原稿に人の承認の関門はない。
- 数字・固有名詞を作らない（素材に無い数字は、前提つきの試算か「xx」）。
- 仮想環境は、承認なしに作らない。既存の作業フォルダは、中身を見せて承認を得てから上書きする。
- エラーが出たら、原因と対処を示して止まる。推測で別の方法に切り替えない。
- スクリプトは Playwright MCP を使わない。MCP は、案の選択の受け取りと画面確認だけに使う。
