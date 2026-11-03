---
name: rebuild
description: このプラグインで作った成果物の PPTX を、元データ（pptx-deck-source/）を変えずに作り直す。スキルや環境を更新したあとに作り直したいとき、PPTX を失くしたときに使う。内容を直すときは revise を使う。Windows 専用。
compatibility: Windows 専用。create と同じ環境。成果物の PPTX と、その隣の pptx-deck-source/<成果物名>/ が必要。
allowed-tools: 'Bash(python "${CLAUDE_PLUGIN_ROOT}/run.py" *)'
---

# pptx-deck rebuild

`${CLAUDE_PLUGIN_ROOT}` はこのプラグインのフォルダ。コマンドは `python "${CLAUDE_PLUGIN_ROOT}/run.py" --data "${CLAUDE_PLUGIN_DATA}" …`。直す対象は、利用者が渡す `<出力先>/<成果物名>.pptx` のパス。元データ `<元データ>` は、その隣の `<出力先>/pptx-deck-source/<成果物名>/`。コマンドの作業フォルダの引数は `"<元データ>"`（この .pptx のパスを渡してもよい。ただしファイルのパスを取るコマンド（`check "<元データ>/final.html"`・`lint-script` など）には使えず、`<元データ>/…` のパスを渡す）。

`pptx-deck-source/<成果物名>/` がない、または利用者が旧配置（`source` フォルダに元データを置く形）のパスを渡したときは、止まって利用者に伝える（旧配置は未対応。PPTX を移動・改名していないか確かめてもらう）。

承認は要らない（内容を変えないため）。

## 手順

1. `python "${CLAUDE_PLUGIN_ROOT}/run.py" --data "${CLAUDE_PLUGIN_DATA}" reopen "<元データ>"`。`status` が `modified`・`unrecorded`（記録のない PPTX。どちらも終了コード 4）のときは、作り直すと PowerPoint での手直しや元の PPTX が消えると伝え、「上書き（`--force`）」か「別名（`build --out <パス>`）」かを選んでもらう。
2. `python "${CLAUDE_PLUGIN_ROOT}/run.py" --data "${CLAUDE_PLUGIN_DATA}" finalize "<元データ>"`（`<元データ>/answers-*.md` から `final.html` を作る）。「案が決まっていません」などのエラーが出たら、回答が足りない。止まって利用者に伝え、revise を勧める。
3. `python "${CLAUDE_PLUGIN_ROOT}/run.py" --data "${CLAUDE_PLUGIN_DATA}" build "<元データ>"`（上書きを選んだときは `--force`、別名のときは `--out <パス>`。`--out` が既存のファイルを指すと `--force` がない限り終了コード 4 で止まるので、同じ `--out` で再実行するときは `--force` を足す）。`ok` が false なら `violations` を伝えて止まる（直すのは revise）。
4. `previews` を開いて崩れを確認し、PowerPoint で開いて最終確認することを勧める。済んだら `clean "<元データ>"`。

## 守ること

- 内容（文言・数字・案の選択）を変えない。
- 仮想環境は、承認なしに作らない。
