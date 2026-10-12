# pptx-deck

ビジネス上の承認文書（稟議・提案・計画）を、コンサル資料のテイストで作る Claude Code スキル。原稿の承認 → HTML スライド案（各 3 案）の選択 → 最終 HTML の承認 → 編集可能な PowerPoint(.pptx) の順に進める。Windows 専用。

- 本文を画像にせず、PowerPoint の図形・文字・表・グラフで出力する（編集できる）。
- 13.33×7.5in（16:9）、BIZ UDPゴシック、無彩色＋基調 1 色＋強調 1 色。配色はプリセット（紺・緑・灰）か、基調色 `#RRGGBB` の指定で変えられる。
- 利用者の PowerPoint テンプレート（`.potx`／`.pptx`）がある場合は、**表紙・裏表紙・ヘッダー・フッター**がそれに従う（マスター／レイアウトが残る）。フォントと配色はテンプレートにかかわらず固定。
- 既存の PPTX の編集と、テンプレートの本文スライドの流用には使わない。

## 使い方

Claude Code で「スライドを作って」「稟議資料を作って」と頼む。入口は、テーマのみ／素材（メモ・文書・データ）／既存の Markdown 原稿のいずれか。

| 段階 | 内容 | 承認 |
|---|---|---|
| 1. 入力 | 目的・対象・枚数、配色、テンプレートの有無を確認する | |
| 2. 原稿 | `script.md`（見出し・章名・本文・図表の型と理由・出典・判断の枠）を作る | チャットで承認（内容を凍結） |
| 3. スライド案 | 全スライドの 3 案（同じ型のまま配置・強調・密度を変える。図と表を多用する）を 1 つの HTML にまとめ、ブラウザで選択とコメントを送信する | HTML 上で選択 |
| 4. 最終 HTML | 選ばれた案を統合して全体を確認する。コメントのあったスライドは、直した 1 案だけを再提示する | チャットで承認 |
| 5. PPTX | HTML の位置を測り、テンプレートを土台に PowerPoint の要素として書き出す。体裁を検査し、確認用の画像で崩れを確認する | |

初回は、仮想環境（`%LOCALAPPDATA%\pptx-deck\venv`。Python・python-pptx・Playwright・chromium）の作成の承認を求められる。承認なしには作らない。

## ファイルの置き場所

| 場所 | 内容 |
|---|---|
| `skills/pptx-deck/`（スキル） | `SKILL.md`、テンプレート（`assets/components/` のレイアウト 5・図解 10・表 4・グラフ 5、`assets/icons/` のアイコン 14、`assets/template/standard.potx`）、コード |
| 実行したディレクトリ直下の `<名前>/` | `script.md`、`slides/`、`variants.html`、`final.html`、`<名前>.pptx` ほか |
| OS の一時フォルダ `%TEMP%\pptx-deck\<名前>\` | 確認用の画像など一過性のもの |

## 自動検査

`build` の前後に、文字のはみ出し、図形の重なり（テンプレートのヘッダー・フッターを含む）、文字サイズの下限（本文 14pt・注記 10pt）、文字のコントラスト比（4.5:1。大きい文字は 3:1）、画像の使い方（本文を画像にしない）を検査する。違反は JSON で返る。

## 開発

```bash
cd skills/pptx-deck
python run.py setup --yes                       # 仮想環境の作成
"$LOCALAPPDATA/pptx-deck/venv/Scripts/python.exe" -m pip install -r requirements-dev.txt
"$LOCALAPPDATA/pptx-deck/venv/Scripts/python.exe" -m pytest
```

設計の経緯は `docs/specs/2026-10-12_1607_pptx-deck-rebuild.md`（現行の仕様）と `docs/superpowers/plans/`（実装計画）。それ以前の SPEC（`docs/specs/2026-10-11_*`・`2026-10-12_0044_*`・`0051_*`・`1100_*`）は旧実装のもので、現行の仕様ではない。

## ライセンス

MIT
