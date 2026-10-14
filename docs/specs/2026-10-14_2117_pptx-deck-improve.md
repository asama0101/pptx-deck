# pptx-deck 改善 SPEC

## 概要
- 目的: pptx-deck の承認フローの手間を減らし、LibreOffice なしで動かし、完成した PPTX を同じスキルで再修正できるようにする。
- 対象: `skills/pptx-deck`（`~/.claude/skills/pptx-deck` はそこへのリンク）の SKILL.md・コード・README。プラグイン化（項目 8）の後は `plugins/pptx-deck/` が対象になる。
- ゴール: 下の受入条件がすべて満たされること。

## 変更内容（9 項目）
1. **前回承認の自動選択**: 再提示（`variants --round N+1`）と最終確認（`finalize`/`review-final`）のページで、`answers-*.md` の最新の判定が「承認」のスライドは、案・デザイン・判定が選択済みで開く。「要修正」と未回答は未選択。選択済みのものも「回答をコピー」に含める。
2. **承認で次へ移動**: 「承認」を押すと自動で次のスライドへ移る。最後のスライドでは移らない。「要修正」ではコメントを書くため移らない。
3. **回答の自動確認は維持し、上限で質問して止まる**: `window.__submitted` の自動確認（約 100 秒ごと、18 回＝約 30 分）は今のまま使う。18 回を超えても送信されないときは、続行方法（もう一度待つ／貼り付けで渡す／中止）を利用者に質問して止まる。この「上限後の動き」を SKILL.md の手順 4 と `review-flow.md` に書き足す（grill-form の手順と同じ）。ユーザーがターミナルに入力したときに待ちをやめる動きは今のまま。
4. **LibreOffice を使わない**:
   - `render.py` の PPTX→PDF→PNG と `find_soffice` を廃止し、`doctor` の LibreOffice の項目・警告も削除する。
   - 下地画像は、テンプレートの XML から背景色（単色）を読み、HTML の背景を単色で塗る。ロゴや装飾は HTML に出ない（PPTX には出る）。コントラスト判定は単色で行う。
   - 確認用の画像は、`final.html` を Playwright(chromium) で撮った画像（OS の一時フォルダ）に置き換える。PPTX の実描画は PowerPoint で人が確認する。
   - README・SKILL.md（`compatibility`・本文）・`部品見本.html` の説明（画像は LibreOffice の描画）を更新する。
5. **完成した PPTX を同じスキルで再修正**: 再修正は 2 パターンを用意する。
   - **(a) 型・デザインを選び直す**: `slides/NN-*.html` の全案と `answers-*.md` から、前回の選択を引き継いだ `variants` を出し直し、選び直す。
   - **(b) 文言・数字だけ直す**: 選ばれた案（`slides/NN-X.html`）と `script.md` を直し、`finalize` → `build` で作り直す。
   - 入口は新しいサブコマンド `reopen <名前>`: 削除済みの派生ファイル（`theme.css`・`base.css`・`icons/` など）を `template.json` から再生成し、後述の指紋を確認してから、上の 2 パターンの案内を出す。
   - PPTX への元データの埋め込みはしない（PowerPoint での想定外の変更を避けるため）。PowerPoint での手直しの取り込み（逆変換）もしない。
6. **成果物以外の整理**: `build` 成功時に、再生成できる派生ファイルと一時ファイルを自動で削除する。残す物は次の `source/` だけ。
   - 構成: `<名前>/<名前>.pptx` と `<名前>/source/` の 2 つだけ。
   - `source/` に**残す**: `design.md`・`script.md`・`slides/`（全案）・`answers-*.md`（承認①の回答 `answers-plan-*.md` を含む）・`round-*-notes.md`・`template.json`・`_template/template.<拡張子>`（テンプレートの写し）・`build.json`（PPTX の指紋）。
   - **削除**: `variants.html`・`final-review.html`・`plan-review.html`・`final.html`・`theme.css`・`base.css`・`chart-preview.js`・`icons/`・下地 PNG・`%TEMP%\pptx-deck\<名前>\`。
   - 作業中の置き場は、実行したフォルダ直下の `<名前>/`。`init` は `<名前>/source/` を作り、設計図・原稿・案・回答・派生ファイルをすべて `source/` の中で扱う（コマンドは `<名前>` を受け取り、`<名前>/source/` を作業フォルダとして解決する）。PPTX の出力先は `<名前>/<名前>.pptx`。（実装判断。レビューで追記）
7. **設計図と原稿（承認①）の HTML 確認**: 新しいサブコマンド `review-plan <名前>` が、`design.md` と `script.md` から 1 つの HTML ページ（`plan-review.html`）を作る。先頭に資料全体（ガバニングメッセージ・論点・台帳）、続けてスライドごとの設計と原稿を縦に並べる。操作はスライド案と同じ（左の一覧に状態の点、スライドごとに承認／要修正とコメント、承認で次へ、前回承認の自動選択、「回答をコピー」と自動確認）。回答は `answers-plan-N.md` に保存する。承認前は内容を凍結するルールは今のまま。
8. **プラグイン化**（設計。公式ドキュメントで確認した仕様に基づく）:
   - **スキルを 4 つの入口に分ける**: `plugins/pptx-deck/skills/` に `create`・`revise`・`rebuild`・`review-plan` を置く。それぞれが `/pptx-deck:create` などで呼べ、説明文で自動発動もする（create=「スライドを作って」、revise=「作った PPTX を直したい」など）。各 SKILL.md は短くし、共通の規則は `references/` を参照する。
     - `create`: 新規作成の全手順（入力→設計図と原稿→スライド案→最終 HTML→PPTX）。承認①は `review-plan` を呼ぶ。
     - `revise`: 完成した PPTX の再修正。`reopen`（指紋の確認と派生ファイルの再生成）→「型・デザインの選び直し」か「文言・数字の修正」→ `finalize` → 承認③ → `build`。
     - `rebuild`: `source/` の内容を変えずに PPTX だけ作り直す（`reopen` → `finalize` → `check` → `build`）。承認は要らない。
     - `review-plan`: 設計図と原稿の HTML 確認だけを出して、回答を受け取る。
   - **共通部の置き場**: コードと部品（`run.py`・`pptx_deck/`・`assets/`・`references/`）はプラグインのルート（`plugins/pptx-deck/`）に置き、各 SKILL.md から `${CLAUDE_PLUGIN_ROOT}` で参照する。
   - **リポジトリ構成**: `plugins/pptx-deck/` にプラグイン本体（`.claude-plugin/plugin.json`・`skills/`・上の共通部）を `git mv` で移す。ルートには `.claude-plugin/marketplace.json`（`plugins[0].source` は `./plugins/pptx-deck`、`name` はマニフェストと一致）を置き、README・docs・`部品見本.html`・LICENSE はルートに残す。
   - **導入**: `/plugin marketplace add asama0101/pptx-deck` → `/plugin install pptx-deck@<マーケットプレイス名>`。スキル名は `/pptx-deck:create` などの 4 つ（自動発動は説明文でこれまでどおり）。`plugin.json` の version は手動で `0.3.0` に上げる（配布版を固定し、変えたときだけ更新される）。
   - **Python 環境**: 項目 9 に従う。venv を作る場合の場所は `%LOCALAPPDATA%\pptx-deck\venv`（プラグインの更新で消えない場所）で、承認を得て `setup --yes`。フックでの自動作成はしない（「承認なしに作らない」を守る）。
   - **Playwright MCP**: 同梱しない。README に前提として明記する（なければ回答を貼り付ける、は今のまま）。SKILL.md はツール名の接頭辞に依存しない書き方（`browser_navigate`・`browser_evaluate`）を保つ。
   - **パス**: SKILL.md 内の `run.py` のパスは `${CLAUDE_PLUGIN_ROOT}` で書く（スキル本文で使える変数）。固定パスや利用者名を書かない。
   - **開発**: 開発中は `claude --plugin-dir plugins/pptx-deck` で試し、`/reload-plugins` で反映する。
   - **従来のリンク**: プラグインに一本化する。`~/.claude/skills/pptx-deck`（リポジトリへのリンクのみ。実体は消えない）は、導入の確認後に利用者の了承を得て外す。移動後はリンク先も存在しなくなるため。
9. **実行する Python の選択（システム優先、なければ venv）**: `run.py` は、次の順で実行に使う Python を決める。
   1. システムの Python（`python`）に必要なものがそろっていればそれを使う。そろっているとは、`python-pptx==1.0.2`・`playwright==1.52.0`・`pymupdf==1.28.2`・`lxml>=5` がその版で入っていて、Playwright の chromium が使えること。
   2. そろっていなければ、`%LOCALAPPDATA%\pptx-deck\venv` を使う。なければ、これまでどおり利用者の承認を得て `setup --yes` で作る（承認なしには作らない）。
   - `doctor` の出力に、使う Python（`system` か `venv`）と、足りないものを出す。
   - システムの Python には何も入れない（pip install しない）。足りないときは venv に入れる。
   - 版が違う場合はそろっていないとみなし、venv に回す（システム側の版は変えない）。

## 再修正の流れ（変更後）
1. 利用者が「`<名前>` を直したい」と依頼する。
2. `reopen <名前>` が派生ファイルを再生成し、`build.json` の指紋と `<名前>.pptx` を比べる。違っていれば「PowerPoint での手直しが消える」と警告して止まる。利用者が「上書き」か「別名で保存」を選ぶ。
3. 利用者が (a) 型・デザインの選び直し、(b) 文言・数字の修正のどちらかを選ぶ。
4. (a) は `variants` を出し直す（前回承認が選択済み）。(b) は該当の案と原稿を直す。どちらも `finalize` で最終 HTML を作り、承認③のあと `build` する。
5. `build` 成功で、成果物以外の派生ファイルを自動で削除する。

## 受入条件
1. 再提示の HTML と最終確認の HTML で、前回「承認」だったスライドが選択済みで開き、「回答をコピー」に含まれる。
2. 「承認」を押すと次のスライドへ移り、最後のスライドでは移らない。「要修正」では移らない。
3. SKILL.md と `review-flow.md` に、18 回を超えたときに続行方法を質問して止まる記述がある。
4. LibreOffice が入っていない環境（`find_soffice` に相当する処理がコードにない状態）で、`init`・`variants`・`finalize`・`build`・`doctor` が通る。`doctor` の `warnings` に LibreOffice が出ない。`build` の `violations` が 0 件のとき `ok: true`。
5. テンプレートを指定した `init`（LibreOffice なし）で、HTML の背景がテンプレートの背景色になり、`check` の判定が通る。
6. 完成した `<名前>/` に `reopen` を実行して、(a)(b) の両方で PPTX を再生成できる。`source/` 以外のファイルがなくても動く。
7. `build` 成功後、`<名前>/` の直下に `<名前>.pptx` と `source/` だけが残り、`source/` には上記の「残す」物だけがある。
8. PPTX を手直し（保存）したあと `reopen` すると、指紋の違いを警告して止まる。
9. `review-plan` が、`assets/sample/` の `design.md` と `script.md` から、スライドごとの承認／要修正が付いたページを作る。
10. README・SKILL.md・`compatibility`・`doctor` の出力が、LibreOffice の記述なしで一致している。
11. `claude plugin validate plugins/pptx-deck` が通る。`/pptx-deck:create`・`:revise`・`:rebuild`・`:review-plan` の 4 つが呼べ、それぞれの SKILL.md が自分の手順だけを書いている（`rebuild` は承認を求めずに PPTX を作り直す）。マーケットプレイスから導入した環境（`~/.claude/skills/pptx-deck` のリンクなし）で、`doctor`・`init`・`variants`・`finalize`・`build`・`reopen` が通る。README に導入手順（Playwright MCP が前提であること）がある。
12. システムの Python に必要なものがそろっている環境では、venv を作らずにシステム側で動く。そろっていない環境では、承認のあとに venv を作って動く。`doctor` に使う Python が出る。

13. 通しの検証が再現できる。`assets/sample/` の原稿と部品を使い、`init`→`variants`→`finalize`→`build`→`reopen`（(a)(b)）を LibreOffice の呼び出しなしで実行する手順（スクリプトまたは手順書）がリポジトリにある（既存のテストは見当たらないため新設する）。

## 非目標
- PPTX への元データの埋め込み、PowerPoint で手直しした内容の取り込み（逆変換）。
- PPTX の実描画の画像化（LibreOffice・PowerPoint COM を含む）。
- グラフ・図の描画品質の改善、型・デザインの追加。
- `grill-form`・`grilling` スキルの変更（今回の自動待ち受けの廃止は pptx-deck の範囲）。
- Mac・Linux への対応。
- Playwright MCP とフックの同梱、`${CLAUDE_PLUGIN_DATA}` への環境の移行、システムの Python への導入（pip install）、chromium から Edge への置き換え。

## リスクと扱い
- **画像と実描画のずれ**: 確認用の画像は PPTX ではなく HTML の描画になる。PowerPoint での最終確認を、報告で必ず勧める（SKILL.md に明記）。
- **下地の再現が単色**: テンプレートの背景が画像・グラデーションのときは、実際の背景と色が違いうる。`init` の `notes` に「背景を単色で近似した」と出し、必要なら代表色を指定できるようにする。
- **旧形式の作業フォルダ**: `source/` を持たない既存の `<名前>/` は、`reopen` が「旧形式」と判定し、`source/` へ移す案内を出す（自動では移さない）。
- **指紋の誤検知**: PowerPoint で開いて保存しただけでも指紋が変わる。この場合も警告し、利用者が「上書き」を選べるようにする。
- **自動削除の取り消し不可**: 削除の対象は派生物と一時ファイルに限り、`source/` の「残す」物は削除しない。削除するパスを `build` の出力 JSON に一覧する。
- **プラグインの未確認点**: `${CLAUDE_PLUGIN_ROOT}` が `run.py` の呼び出し（Bash）で期待どおり展開されるか、`marketplace add` が GitHub のリポジトリを要すること（push が要る）は、実装時に `claude plugin validate` と実際の導入で確かめる。食い違いがあれば SPEC に戻って相談する。
- **システムの Python の判定**: 版の違いや壊れた導入を取りこぼすと、実行時に落ちる。判定は import と版の確認とし、失敗したら venv に回す。システム側に chromium がない場合も、venv 側の導入（数百 MB）の承認を求める。
- **外部公開は確認を取る**: マーケットプレイスから導入するには GitHub への push が要る。push は外部への公開なので、そのときに利用者の了承を得る（実装の途中で勝手に push しない）。
- **リンクの取り外し**: 取り外しの前に、導入できたことを確認する。
- **`部品見本.html`**: 画像が LibreOffice の描画のため、作り直しの方法を実装時に調べる（未確認）。

## 決定ログ
- (4) LibreOffice の代替: HTML 側で確認する。PowerPoint COM と自前描画は採用しない。
- (4) 下地画像: テンプレートの背景色で塗る。図形の SVG 再現と下地なしは採用しない。
- (5) 再修正の方式: PPTX への埋め込みは、PowerPoint での想定外の変更を避けるため見送り。`source/` に元データを残す。PowerPoint の手直しは取り込まない。
- (5) 再修正の 2 パターン: 型・デザインの選び直しと、文言・数字だけの修正。
- (3) 回答の受け渡し: 自動確認（`window.__submitted`）を維持し、上限（18 回）後は質問して止まる。待ち受けの廃止と、ローカル受信は採用しない。トークン消費は、待つ時間に比例する（1 回の出力は約 100 トークンだが、毎回会話全体をキャッシュから読み直す。実測はしていない）。
- プラグイン化: この SPEC に含める（利用者の判断）。構成は `plugins/pptx-deck/` へ再配置し、スキルを `create`・`revise`・`rebuild`・`review-plan` の 4 入口に分け、Playwright MCP は同梱しない、フックは同梱しない、従来のリンクは外して一本化。
- (6) 削除: `build` 成功時に自動削除するが、対象は不要な一時ファイルと派生ファイルのみ。再生成に必要なファイルは残す。
- (6) 置き場所: 実行したフォルダ直下の `<名前>/` のまま。構成は `<名前>.pptx` と `source/`。
- (6) 上書き: 指紋で変更を検知し、止まって確認する。
- (7) 承認①の HTML: 1 つのページにまとめ、スライドごとに承認／要修正（スライド案と同じ操作）。
- Python 環境: システムの Python に必要なものがそろっていればそれを使い、なければ venv（承認後に作る）。venv は必須ではない。chromium は Edge に置き換えない。pymupdf はアイコンの変換で残る。
- プラグイン化で、Python 環境は項目 9 に従う（前のログの「今の場所と承認フローのまま」は、venv を作る場合に限る）。
- 進め方: SPEC を承認してから実装する。
