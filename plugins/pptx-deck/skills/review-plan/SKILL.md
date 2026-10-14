---
name: review-plan
description: 設計図（design.md）と原稿（script.md）を HTML のレビューページで確認し、承認／要修正とコメントを受け取る。create の承認①として呼ばれるほか、「設計図と原稿を確認したい」と頼まれたときに単独でも使う。Windows 専用。
compatibility: Windows 専用。create と同じ環境。Playwright MCP が必要（ないときは回答を貼り付ける）。
---

# pptx-deck review-plan

`${CLAUDE_PLUGIN_ROOT}` はこのプラグインのフォルダ。コマンドは `python "${CLAUDE_PLUGIN_ROOT}/run.py" …`。`<名前>` は作品の名前。

## 手順

1. `python "${CLAUDE_PLUGIN_ROOT}/run.py" lint-script "<名前>/source/script.md"` が空であることを確かめる。
2. `python "${CLAUDE_PLUGIN_ROOT}/run.py" review-plan "<名前>"` → `<名前>/source/plan-review.html`。Playwright MCP の `browser_navigate` で `file:///C:/…/plan-review.html` を開き、「資料全体とスライドごとの設計・原稿を見て、『承認』か『要修正』を選び、『回答をコピー』を押してください。直したい点はコメントに書いてください」と伝える。`browser_resize` で窓の大きさを変えない。
3. 回答を待つ。`browser_evaluate` で次を実行し、送信されるか約 100 秒たつまでブロックして結果を返す。`submitted` が false なら同じ呼び出しを繰り返す（合計約 30 分、18 回まで）。18 回を超えても送信されないときは、続行方法（もう一度待つ／回答を貼り付けて渡す／中止）を利用者に質問して止まる。ユーザーがターミナルに入力したときは待ちをやめて、その内容に従う。

   `() => new Promise(res => { const t0 = Date.now(); const id = setInterval(() => { if (window.__submitted || Date.now() - t0 > 100000) { clearInterval(id); res({ submitted: !!window.__submitted, md: window.__answersMd }); } }, 500); })`

4. `submitted` が true なら、`md` を `<名前>/source/answers-plan-N.md` に書く（N は何回目か）。貼り付けられた md も同じように書く。
5. 要修正またはコメントがあるスライドは、設計図と原稿を直して 2 から出し直す（前回承認したスライドは選択済みで開く）。全部承認されたら、内容を凍結する（以降、承認なしに変えない）。

## 守ること

- 承認後は、承認なしに設計図と原稿の内容を変えない。
