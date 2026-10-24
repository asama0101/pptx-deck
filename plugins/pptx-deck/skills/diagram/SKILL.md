---
name: diagram
description: 型にハマらない図（NW 構成図・トラフィックフロー・システムの障害動作・自己紹介・画面や写真への注釈など）を、素材のファイル・文章・画像、または利用者へのヒアリングから「絵」として描き、PPTX にする。絵は SVG で描いて 1 枚の画像として貼る（題・ヘッドメッセージ・注釈は編集できる文字。絵の中身は PowerPoint で直せないので、直すときは描き直す）。「図にして」「構成図を作って」「障害の流れを絵にして」「自己紹介のスライドを作って」と頼まれたとき、または create の中で既存の型に合わない図が要るときに使う。既存の型に当てはまる普通のスライドや資料全体は create、作った PPTX の文言の直しは revise を使う。他の人が作った既存の PPTX の編集には使わない。Windows 専用。
compatibility: Windows 専用。create と同じ環境（Python・Playwright・chromium）。提案・構造の確認と案の選択に Playwright MCP が必要（ないときは回答を貼り付ける）。
allowed-tools: 'Bash(python "${CLAUDE_PLUGIN_ROOT}/run.py" *)'
---

# pptx-deck diagram

`${CLAUDE_PLUGIN_ROOT}` は、このプラグインのフォルダ。コマンドはすべて `python "${CLAUDE_PLUGIN_ROOT}/run.py" --data "${CLAUDE_PLUGIN_DATA}" …`。`<元データ>` は `<出力先>/pptx-deck-source/<成果物名>`（作業ファイルの置き場。コマンドの作業フォルダの引数はすべて `"<元データ>"`）、PPTX は `<出力先>/<成果物名>.pptx`。環境の確認（`doctor`・`setup`）は create の 0 章（`${CLAUDE_PLUGIN_ROOT}/skills/create/SKILL.md`）と同じ。references の中のコマンドに書かれた `${CLAUDE_PLUGIN_ROOT}`・`${CLAUDE_PLUGIN_DATA}` は、references が展開されないので、この SKILL.md に展開された実パスに読み替えて実行する。

絵の書き方・5 種の作法・往復・聞くことは [references/picture-craft.md](${CLAUDE_PLUGIN_ROOT}/references/picture-craft.md)。部品は `${CLAUDE_PLUGIN_ROOT}/assets/pictures/parts.svg`、見本は `${CLAUDE_PLUGIN_ROOT}/assets/components/pictures/`。既存の 51 型（`${CLAUDE_PLUGIN_ROOT}/references/patterns.md`）で足りる図は、型を使うほうが速い。型に合わないときに絵にする。

## 1. 入口

- **単独で作る**: create の 1.0（`start-page` → `intake`）で出力先と成果物名を決めてから、`init "<元データ>" --color <プリセット|#RRGGBB>`（`<元データ>` は `intake` の `workdir`。create の 1.2 と同じ。同名のフォルダが空でないときは中身を見せて承認を得る）。1 枚物なので、`<元データ>/design.md` は資料全体と台帳を省いた 1 ページ分、`<元データ>/script.md` は 1 スライド（`layout: diagram`・題・ヘッドメッセージ・図表）にする。書式は `${CLAUDE_PLUGIN_ROOT}/assets/sample/`。ヘッドメッセージは create の 2.2 の規則に従い、`lint-script` を通す。
- **create の中で呼ばれた**: create の作業フォルダの `<元データ>/slides/` に、そのページの断片を書く。承認は create 側に従い、追加の承認は出さない。
- **絵にするかどうか**: 利用者が「図にして」「絵にして」と頼んだときは、そのまま絵にする（`picture-plan.json` の `asked` を true にする）。そうでなく、素材に構造（手順・関係・前後の比較・構成・経路）を見つけたときは、文章のままにせず、4 章の HTML で「ここは絵がよい」と提案する（強制しない。`asked` は false）。

## 2. インプットを読む

- 受け付けるもの: チャットの文章・箇条書き、ファイル（`.md`・`.txt`・`.docx`・`.pdf`・`.html`。標準の読み取りで読む）、画像（スクリーンショット・手書き。`Read` で見る）、既存の PPTX の図（構造を読んで作り直すだけ。元の PPTX は直接編集しない）。
- 読み取るもの: **要素**（機器・人・箱）・**関係**（つながり・順序・経路）・**強調する 1 点**・**未確定の値**（xx）。素材に無い数字・固有名詞は作らない。
- 画像・既存の図は読み違えやすいので、読み取った要素を 4 章で必ず確認する。
- 見本（架空）: 文書起点の障害報告 `${CLAUDE_PLUGIN_ROOT}/assets/sample/picture/incident-report.md`、ヒアリング起点の自己紹介 `self-intro-hearing.md`、メモ起点の構成 `network-memo.md`、提案と構造の確認の `picture-plan.example.json`（同じフォルダ）。

## 3. 足りない情報を聞く

素材が薄いとき、またはあいまいなときは、描き始める前に聞く。チャットの選択式（`AskUserQuestion`）で、1 回に 1〜4 問、答えれば図が決まる質問だけを、必要な回数だけ。図の種類ごとの質問は picture-craft.md の「聞くこと」。数字・固有名詞は聞いて埋める（作らない）。画像や文書に機密（IP アドレス・機器名・氏名）がありそうなら、伏せ字にするかも聞く。

## 4. 提案と構造の確認（HTML）

1. `<元データ>/picture-plan.json` を書く。形は `pptx_deck/picture_plan.py` の先頭の説明。`proposals` は絵にする箇所ごと（`id` は `P1`・`P2` …、`title`・`reason`（提案の理由）・`asked`・`summary`・`items`（`id` は `P1-1` …、`kind` は 要素/関係/順序/強調/未確定、`text`）・`source`）。強調は 1 点だけ。
2. `review-picture "<元データ>"` → `<元データ>/picture-review.html`。Playwright MCP の `browser_navigate` で `file:///C:/…/picture-review.html` を開き、「絵にする箇所（提案）と、読み取った構造を見て、提案は『絵にする／しない』、構造の各項目は『OK／修正』を選び、『回答をコピー』を押してください」と伝える。`browser_resize` で窓の大きさを変えない。
3. 回答を待つ。`browser_evaluate` で次を実行し、送信されるか約 100 秒たつまでブロックして結果を返す。`submitted` が false なら同じ呼び出しを繰り返す（合計約 30 分、18 回まで）。18 回を超えても送信されないときは、続行方法（もう一度待つ／回答を貼り付けて渡す／中止）を利用者に質問して止まる。ユーザーがターミナルに入力したときは待ちをやめて、その内容に従う。

   `() => new Promise(res => { const t0 = Date.now(); const id = setInterval(() => { if (window.__submitted || Date.now() - t0 > 100000) { clearInterval(id); res({ submitted: !!window.__submitted, md: window.__answersMd }); } }, 500); })`

4. `submitted` が true なら、`md` を `<元データ>/answers-picture-N.md` に書く（N は何回目か。貼り付けられた md も同じ）。
5. `picture-status "<元データ>"` を実行する。`fixes`（修正の項目とコメント）があれば、`picture-plan.json` を直して 2 からやり直す（直した項目だけ答えてもらう。`picture-status` は回の順に後勝ちで重ねる）。`pending` があれば、未回答を聞く。終了コード 0（`frozen`）になったら構造を凍結し、`draw` の箇所だけを描く。`skip` の箇所は絵にしない。以降、文言・数字を変えるときは利用者に確かめる。

## 5. 描く（初回の案）

- 要素が少ない絵（自己紹介など）: 凍結した構造のとおり、1 案を `<元データ>/slides/NN-A.html` に書く。
- 要素が多い・あいまいな絵（NW 構成図・障害動作など）: **構図の違う 2〜3 案**（左から右の流れ／上下の層／中心と周辺など）を `NN-A.html`・`NN-B.html`・`NN-C.html` に書く。内容（文言・数字）は案の間で同じにする。各案に `data-variant="構図名｜選んだ理由"` を付ける。
- 見本（`${CLAUDE_PLUGIN_ROOT}/assets/components/pictures/`）をコピーして差し替える。書き方と図の種類ごとの作法は picture-craft.md に従う。型で足りる図は、patterns.md の型を使う。
- 描いたら `draft "<元データ>"`（`--slide NN`）で確認用の画像と検査の結果を得て、`violations` が 0 件になるまで直す。

## 6. 構図の選択（案が複数のとき）と往復

1. 案が複数のとき: create の 3 章の手順 3〜5（`variants`・待ち方・回答の保存。保存先は `<元データ>/answers-N.md`）で、構図（A/B/C）を選んでもらう。案が 1 つのときは、構図の選択を省く（`<元データ>/answers-1.md` に `## SNN` と `- 選択: A` だけを書く。判定は書かない）。
2. 往復: 選ばれた案を 1 案にして、利用者と描き直す。**直す前に** `history "<元データ>" snapshot --label "<直す内容>"`。確認用の画像（`draft`）を見せ、チャットの指示で直す。戻すときは `history "<元データ>" restore <版>`。位置・形・色・構図・凡例の見せ方は、利用者の指示で直してよい。文言・数字を変えるときは、先に利用者に確かめる。

## 7. PPTX

1. `finalize "<元データ>"` → `final.html` と `final-review.html`（参照用）。最終確認の承認は挟まない（6 章の往復で、確認用の画像を見て直し終えている）。利用者には、「絵は画像として PPTX に貼られ、PowerPoint では直せません（描き直します）。機密が絵に含まれていないかも見てください」と一言伝え、そのまま次へ進む。直したいときは、完成後に `revise` か 6 章の往復に戻る。
2. `build "<元データ>" [--footer …] [--force|--out …]`（終了コード 4 の扱いは create の 5 章）。`ok` が false なら `violations` を読んで直し、`finalize` からやり直す。`ok` なら `previews` を開いて崩れを確認し、**PowerPoint で開いて、絵の解像度・フォント・位置を最終確認することを勧める**。済んだら `clean "<元データ>"`。

## 守ること

- 絵の中身は PowerPoint で直せないことを、ビルドの前に利用者に伝える。直す依頼は、描き直して `build` する。
- 数字・固有名詞を作らない（素材に無いものは、前提つきの試算か「xx」）。
- 強調色は 1 枚に 1 点。絵の中の色はテーマのクラスだけ。文字は 14pt 以上。
- 画像・既存の図の機密（IP アドレス・機器名・氏名）は、利用者に伏せ字の要否を聞く。素材はリポジトリに残さない。
- 直す前に `history snapshot` で版を残す。
- 仮想環境は、承認なしに作らない。既存の作業フォルダは、中身を見せて承認を得てから上書きする。エラーが出たら、原因と対処を示して止まる。
- スクリプトは Playwright MCP を使わない。MCP は、提案・構造の確認、案の選択、画面確認の受け取りだけに使う。
