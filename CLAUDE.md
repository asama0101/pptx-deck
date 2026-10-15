# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Windows 専用の Claude Code プラグイン `pptx-deck`（`plugins/pptx-deck/`）。承認文書を、HTML スライドを経由して編集可能な PPTX にする。利用者向けの説明は README.md。

## コマンド

すべてリポジトリのルートで実行する。リンタ・ビルド設定はなく、検証は `unittest` と、プラグイン自身の検査コマンドで行う。

    # 全テスト（Playwright が要るので venv の Python で）
    "$LOCALAPPDATA/pptx-deck/venv/Scripts/python.exe" -m unittest discover -s tests -t . -v

    # 1 ファイル・1 テスト
    "$LOCALAPPDATA/pptx-deck/venv/Scripts/python.exe" -m unittest tests.test_answers -v
    "$LOCALAPPDATA/pptx-deck/venv/Scripts/python.exe" -m unittest tests.test_answers.<クラス>.<メソッド>

    # プラグインの CLI（サブコマンド一覧は README の「コマンド」）
    python plugins/pptx-deck/run.py doctor
    python plugins/pptx-deck/run.py check <名前>/source/final.html    # 部品を足した・直したら違反 0 件を確かめる

システムの Python に `playwright` がないと、`tests.test_review_page`・`tests.test_plan_review` は import でエラーになる（既知。venv なら通る）。

## アーキテクチャ

**2 層に分かれる。** プラグイン（`plugins/pptx-deck/`）は読み取り専用で、利用者が作る作品は別の場所（実行ディレクトリ直下の `<名前>/source/` と `<名前>/<名前>.pptx`）に置く。確認用の画像は `%TEMP%\pptx-deck\<名前>\`。

**実行の入口。** `run.py`・`paths.py`・`env.py` は標準ライブラリだけで動く。`run.py` が、システムの Python（`python-pptx`・`playwright`・`pymupdf`・`lxml`・chromium がそろっていれば）か `%LOCALAPPDATA%\pptx-deck\venv`（`PPTX_DECK_HOME` で変更可）を選び、`python -m pptx_deck <サブコマンド>` を子プロセスで実行する。`setup` だけは `run.py` が直接処理する（argparse に載らない）。

**HTML が正本で、PPTX はそこから測って作る。**

1. `source/design.md`（設計図）→ `script.md`（原稿。`script_lint.py` が検査）→ 承認①（`plan_review.py`）。
2. `source/slides/NN-A.html`・`NN-B.html`・`NN-A-d2.html` などの断片（型は `assets/components/` からコピーして内容を差し替える。型の A/B/C に加え、型にとらわれない自由設計の `NN-R.html` を足す。R はデザイン 1 のみ・`pp-picture` 不可で、`variants.collect_designs` が検査する）→ `variants.py` が `variants.html` を作る → 回答 `answers-N.md`（回の順に後勝ちで上書き。`answers-final.md` は案の決定に使わない）。
3. `finalize` が選ばれた案を `final.html` に統合し、参照用の `final-review.html` を作る（最終 HTML の承認は求めない。承認は ①② の 2 回で、直しは完成後に `revise`）。
4. `measure.py` が Playwright で `final.html` を開き、`measure.js` が `.pp-*` 部品の位置・サイズ・書式をモデルにする。**`pp-text`・`pp-shape`・`pp-line`・`pp-image`・`pp-table`・`pp-chart`・`pp-picture` 以外のクラスは PPTX に出ない。**
5. `cli.py` の `build` が、測ったモデルを `check.check_model` で検査し（エラーがあれば PPTX を作らない）、`build.py` が python-pptx でテンプレート（既定は `assets/template/standard.potx`、利用者のもあり）の上に書き出し、できた PPTX を `check.check_pptx` で再検査する。グラフは `charts.py` がネイティブのグラフにする。`template.py` がテンプレートからヘッダー・フッター・背景色・レイアウトを読み、`init` が `template.json` と CSS 変数にして作業フォルダに残す。

**絵（`pp-picture`）。** 型に当てはまらない図は、`<div class="pp-picture" data-alt>` の中のインライン SVG で描く。`measure.js` が位置・代替テキスト・内部の文字の大きさと範囲・色の指定を測り、`measure.py` の `measure(html, raster_dir=…)` が、絵だけを透過・3 倍の PNG にして（他の部品を隠して 1 枚ずつ撮る）`src` に入れ、`build.py` が `pp-picture` という名前の画像として貼る。検査は `check.py` の `_check_picture`。絵の内部の重なりは検査せず、絵全体と他の部品の重なりは検査する。絵の中身は PowerPoint で直せない。ワークフローは `skills/diagram`、作法は `references/picture-craft.md`。提案・構造の確認ページは `picture_plan.py`（`review-picture`・`picture-status`）、往復の確認は `draft.py`、版の管理は `history.py`。

**派生ファイルと指紋。** `variants.html`・`final.html`・`theme.css`・`base.css`・`chart-preview.js`・`icons/` などは再生成できる派生ファイルで、`build` 成功時に `lifecycle.DERIVED_FILES` だけが消される（`source/` の元データは消さない）。PPTX の SHA-256 を `build.json` に残し、手直しされた PPTX を `build`・`reopen` が検知して止まる。`theme.css`・`base.css`・`chart-preview.js` は `init` 時に `assets/web/` から作業フォルダへ**写される**ので、プラグイン側を直しても既存の作業フォルダには `init --force` か `reopen` まで届かない。

**ワークフローはスキルが握っている。** `skills/*/SKILL.md`（create・revise・rebuild・review-plan・diagram）が手順を持ち、詳細な規則は `references/*.md`（`head-rules`・`html-rules`・`patterns`・`components`・`review-flow`・`check-rules`）にある。CLI は手順書から呼ばれる部品で、承認のゲート（設計図・原稿の凍結、案の選択、最終確認）はスキル側の責務。型の追加は `assets/components/` に足したうえで `references/components.md`・`patterns.md` も更新する。

## 注意

- 部位の名前（タイトル・ヘッドメッセージ・チャートタイトル・注釈・出典・メッセージボックスなど）は、断片の `data-part` で付ける（`references/html-rules.md`）。`variants.py` のページが `data-part` から番号つきバッジを重ね、部位ごとのコメントを回答 md の `- 部位: 名前 ／ コメント: …` に出す。バッジは画面専用で PPTX に出ない。`data-role` は測定・検査が使うので、部位名の置き換えに使わない。

- **レビューページと、スライドのテーマが同じ DOM・同じ CSS 変数を共有する。** `variants.py` のページ側の変数は `--rv-bg`・`--rv-line` のように接頭辞を付けてある。`--bg`・`--line`・`--text` などテーマ側（`theme.css`）と同名にすると、スライドの背景や罫線が上書きされて見えなくなる。
- 絵の SVG の中の色は、`base.css` の `sv-f-*`・`sv-s-*`（テーマの変数）で塗る。`parts.svg` のアイコンも同じ。`marker` は path の終点にだけ付くので、矢印は 1 本ずつ別の path にする。絵を撮るときは、他の部品を `visibility:hidden` にして背景を透明にする（`measure.py` の `_SNAP_CSS`）。`<defs>` の `symbol`・`marker` は、絵の `<svg>` の中に置く（外の定義は撮るときに隠れる）。
- `chart-preview.js` はブラウザ用の近似で、`fmt`（桁区切りなど）や軸は PowerPoint の実際のグラフと一致しない。
- `tests/test_docs.py` が文書を検査する: SKILL.md にハードコードしたパス（`C:/Users`・`${CLAUDE_SKILL_DIR}`）を書かない（`${CLAUDE_PLUGIN_ROOT}` を使う）、LibreOffice を依存として書かない（README を含む）。
- `部品見本.html` は生成スクリプトがなく、部品を直しても自動では更新されない。
- 行末は LF 固定（`.gitattributes`）。`docs/*.pdf` は著作物なのでコミットしない。
- コメント・コミットメッセージ・文書は日本語（既存の履歴に合わせる）。README.md に関わる変更をしたら README も更新する。
