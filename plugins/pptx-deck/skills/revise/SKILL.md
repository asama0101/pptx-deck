---
name: revise
description: このプラグインで作った PPTX を、あとから直す。型・デザインを選び直す、または文言・数字だけを直して、PPTX を作り直す。「作った資料を直したい」「スライドの文言を変えたい」「デザインを選び直したい」と頼まれたときに使う。PowerPoint で手直しした内容は取り込まない（作り直すと消える）。Windows 専用。
compatibility: Windows 専用。create と同じ環境。作品の source/ フォルダが必要。
---

# pptx-deck revise

`${CLAUDE_PLUGIN_ROOT}` はこのプラグインのフォルダ。コマンドは `python "${CLAUDE_PLUGIN_ROOT}/run.py" …`。`<名前>` は作品の名前（`<名前>/<名前>.pptx` と `<名前>/source/` があるフォルダ）。

## 手順

1. `python "${CLAUDE_PLUGIN_ROOT}/run.py" reopen "<名前>"`。出力の `status` を見る。
   - `ok`: 続ける。
   - `modified`（終了コード 4）: PPTX が前回のビルドのあとに変更されている。作り直すと PowerPoint での手直しが消えると利用者に伝え、「上書きして続ける（`--force`）」か「別名で保存する（`build --out <パス>`）」かを選んでもらう。選ぶまで進めない。
   - `missing_pptx`・`unrecorded`: PPTX がない、または記録がない。そのまま続けてよいと伝える。
   - `legacy: true`: 旧形式のフォルダ。そのまま扱えると伝える。
2. 利用者に直し方を選んでもらう。
   - **(a) 型・デザインを選び直す**: `python "${CLAUDE_PLUGIN_ROOT}/run.py" variants "<名前>"` で `variants.html` を作り（前回承認したスライドは選択済み）、create の 3 章の手順 3〜6 と同じ手順で、選んでもらう。直したいスライドだけ、案を選び直して承認する。
   - **(b) 文言・数字だけ直す**: 直す内容を聞き、`source/slides/NN-X.html`（選ばれている案）と `source/script.md` の該当箇所を直す。数字を作らない（素材に無い数字は「xx」）。直したスライドは `source/round-N-notes.md` に「NN: 直した内容」と書く。
3. `python "${CLAUDE_PLUGIN_ROOT}/run.py" finalize "<名前>"`（回答は `source/answers-*.md` を回の順に自動で使う）。`final-review.html` を開いて、create の 3 章の手順 8 と同じ手順で承認を得る（保存先は `source/answers-final.md` を上書き）。
4. `python "${CLAUDE_PLUGIN_ROOT}/run.py" build "<名前>"`。`ok` が false なら `violations` を読んで `source/slides/` を直し、3 に戻る。
5. `previews` を開いて崩れを確認し、**PowerPoint で開いて最終確認することを勧める**。済んだら `clean "<名前>"`。

## 守ること

- 利用者が直すと言った内容以外は変えない。
- 回答を待つときは create の手順 4 に従う。18 回（約 30 分）を超えたら続行方法を質問して止まる。
- 仮想環境は、承認なしに作らない。
