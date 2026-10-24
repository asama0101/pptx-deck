---
name: revise
description: このプラグインで作った PPTX を、あとから直す。型・デザインを選び直す、または文言・数字だけを直して（部位の名前で指示できる）、PPTX を作り直す。「作った資料を直したい」「スライドの文言を変えたい」「デザインを選び直したい」と頼まれたときに使う。PowerPoint で手直しした内容は取り込まない（作り直すと消える）。新しく作るときは create、内容を変えずに作り直すだけなら rebuild を使う。他の人が作った既存の PPTX の編集には使わない。Windows 専用。
compatibility: Windows 専用。create と同じ環境。成果物の PPTX と、その隣の pptx-deck-source/<成果物名>/ が必要。
allowed-tools: 'Bash(python "${CLAUDE_PLUGIN_ROOT}/run.py" *)'
---

# pptx-deck revise

`${CLAUDE_PLUGIN_ROOT}` はこのプラグインのフォルダ。コマンドは `python "${CLAUDE_PLUGIN_ROOT}/run.py" --data "${CLAUDE_PLUGIN_DATA}" …`。直す対象は、利用者が渡す `<出力先>/<成果物名>.pptx` のパス。元データ `<元データ>` は、その隣の `<出力先>/pptx-deck-source/<成果物名>/`。コマンドの作業フォルダの引数は `"<元データ>"`（この .pptx のパスを渡してもよい）。

`pptx-deck-source/<成果物名>/` がない、または利用者が旧配置（`source` フォルダに元データを置く形）のパスを渡したときは、止まって利用者に伝える（旧配置は未対応。PPTX を移動・改名していないか確かめてもらい、旧配置のものは作り直す）。

## 手順

1. `python "${CLAUDE_PLUGIN_ROOT}/run.py" --data "${CLAUDE_PLUGIN_DATA}" reopen "<元データ>"`。出力の `status` を見る。
   - `ok`: 続ける。
   - `modified`（終了コード 4）: PPTX が前回のビルドのあとに変更されている。作り直すと PowerPoint での手直しが消えると利用者に伝え、「上書きして続ける（`--force`）」か「別名で保存する（`build --out <パス>`）」かを選んでもらう。選ぶまで進めない。
   - `unrecorded`（終了コード 4）: PPTX はあるが `build.json` の記録がない（元の資料を置いた、記録が壊れた、など）。作り直すとその PPTX が消えると伝え、`modified` と同じく「上書きして続ける（`--force`）」か「別名で保存する（`build --out <パス>`）」かを選んでもらう。選ぶまで進めない。
   - `missing_pptx`: PPTX がない。そのまま続けてよいと伝える。
2. 利用者に直し方を選んでもらう。
   - **(a) 型・デザインを選び直す**: `python "${CLAUDE_PLUGIN_ROOT}/run.py" --data "${CLAUDE_PLUGIN_DATA}" variants "<元データ>"` で `variants.html` を作り（前回承認したスライドは選択済み）、create（`${CLAUDE_PLUGIN_ROOT}/skills/create/SKILL.md`）の 3 章の手順 3〜6 と同じ手順で、選んでもらう。直したいスライドだけ、案を選び直して承認する。
   - **(b) 文言・数字だけ直す**: 直す内容を聞き、`<元データ>/slides/NN-X.html`（選ばれている案）と `<元データ>/script.md` の該当箇所を直す。数字を作らない（素材に無い数字は「xx」）。直したスライドは `<元データ>/round-N-notes.md`（N は再提示する回）に「S01: 直した内容」（S と 2 桁の番号。番号だけの行は読まない）と書く。
     - 利用者は部位の名前で指示できる（例: 「3 枚目の出典を直して」「5 枚目のスティッカー②を短く」）。部位名は断片の `data-part`（`${CLAUDE_PLUGIN_ROOT}/references/html-rules.md`）。スライド番号と部位名で `<元データ>/slides/NN-X.html` の要素を探し、同じ部位が複数あるときの番号は、スライド内の左上から右下の順。部位が見つからない（その型にない）、または番号が決まらないときは、推測せずに利用者に聞く。
   - **(c) 絵（`pp-picture`）を描き直す**: 絵の中身は PowerPoint で直せない。直す内容を聞き、`diagram`（`${CLAUDE_PLUGIN_ROOT}/skills/diagram/SKILL.md`）の 6 章の往復に従う（直す前に `history "<元データ>" snapshot`、直したら `draft "<元データ>"` で確認）。
3. 回答に `- 編集:` の行があれば、先に `python "${CLAUDE_PLUGIN_ROOT}/run.py" --data "${CLAUDE_PLUGIN_DATA}" apply-edits "<元データ>"` で断片へ反映する（反映できない編集があると終了コード 1 と標準エラーの一覧で分かる。断片か回答を直して `--answers <回答ファイル>` を付けて再実行するか、断片を手で直す。`final-review.html` で直した編集は、「回答をコピー」の内容を `<元データ>/answers-final.md` に保存すれば同じく対象になる）。そのうえで `python "${CLAUDE_PLUGIN_ROOT}/run.py" --data "${CLAUDE_PLUGIN_DATA}" finalize "<元データ>"`（回答は `<元データ>/answers-N.md` を回の順に自動で使う）。続けて `python "${CLAUDE_PLUGIN_ROOT}/run.py" --data "${CLAUDE_PLUGIN_DATA}" check "<元データ>/final.html"` で違反 0 件を確かめる（HTML だけの出力では `build` の検査が走らない）。承認は求めず、そのまま手順 4 へ進む（`final-review.html` は参照用）。
4. `python "${CLAUDE_PLUGIN_ROOT}/run.py" --data "${CLAUDE_PLUGIN_DATA}" output-format "<元データ>"` で出力形式を読み、`pptx` なら `build`、`html` なら `export-html "<元データ>" --prune`、`both` なら `export-html "<元データ>"` のあとに `build` を実行する（`export-html` に PPTX の上書き確認はない）。以下は `build` のとき。`python "${CLAUDE_PLUGIN_ROOT}/run.py" --data "${CLAUDE_PLUGIN_DATA}" build "<元データ>"`。手順 1 で上書きを選んだとき（`modified`・`unrecorded`）は `--force`、別名のときは `--out <パス>` を付ける（手順 3 の `finalize` のあとの `build` も、直して 3 に戻ってからの `build` も同じ。付け忘れると再び終了コード 4 で止まる。`--out` が既存のファイルを指すときも終了コード 4 なので、同じ `--out` で再実行するなら `--force` を足す）。`ok` が false なら `violations` を読んで `<元データ>/slides/` を直し、3 に戻る。
5. `previews` を開いて崩れを確認し、**PowerPoint で開いて最終確認することを勧める**。済んだら `clean "<元データ>"`。

## 守ること

- 利用者が直すと言った内容以外は変えない。
- 回答を待つときは create の手順 4 に従う。18 回（約 30 分）を超えたら続行方法を質問して止まる。
- 仮想環境は、承認なしに作らない。
