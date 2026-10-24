---
name: rebuild
description: このプラグインで作った作品の PPTX を、元データ（source/）を変えずに作り直す。スキルや環境を更新したあとに作り直したいとき、PPTX を失くしたときに使う。内容を直すときは revise を使う。Windows 専用。
compatibility: Windows 専用。create と同じ環境。作品の source/ フォルダが必要。
allowed-tools: 'Bash(python "${CLAUDE_PLUGIN_ROOT}/run.py" *)'
---

# pptx-deck rebuild

`${CLAUDE_PLUGIN_ROOT}` はこのプラグインのフォルダ。コマンドは `python "${CLAUDE_PLUGIN_ROOT}/run.py" --data "${CLAUDE_PLUGIN_DATA}" …`。`<名前>` は作品の名前。

承認は要らない（内容を変えないため）。

## 手順

1. `python "${CLAUDE_PLUGIN_ROOT}/run.py" --data "${CLAUDE_PLUGIN_DATA}" reopen "<名前>"`。`status` が `modified`・`unrecorded`（記録のない PPTX。どちらも終了コード 4）のときは、作り直すと PowerPoint での手直しや元の PPTX が消えると伝え、「上書き（`--force`）」か「別名（`build --out <パス>`）」かを選んでもらう。
2. `python "${CLAUDE_PLUGIN_ROOT}/run.py" --data "${CLAUDE_PLUGIN_DATA}" finalize "<名前>"`（`source/answers-*.md` から `final.html` を作る）。「案が決まっていません」などのエラーが出たら、回答が足りない。止まって利用者に伝え、revise を勧める。
3. `python "${CLAUDE_PLUGIN_ROOT}/run.py" --data "${CLAUDE_PLUGIN_DATA}" build "<名前>"`（上書きを選んだときは `--force`、別名のときは `--out <パス>`。`--out` が既存のファイルを指すと `--force` がない限り終了コード 4 で止まるので、同じ `--out` で再実行するときは `--force` を足す）。`ok` が false なら `violations` を伝えて止まる（直すのは revise）。
4. `previews` を開いて崩れを確認し、PowerPoint で開いて最終確認することを勧める。済んだら `clean "<名前>"`。

## 守ること

- 内容（文言・数字・案の選択）を変えない。
- 仮想環境は、承認なしに作らない。
