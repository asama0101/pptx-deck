# pptx-deck

ビジネス上の承認文書（稟議・提案・計画）を、コンサル資料のテイストで作る Claude Code プラグイン。設計図と原稿を書き、HTML のスライド案を選び、編集できる PowerPoint（.pptx）にする。

**Windows 専用。** Python 3.10 以上と Claude Code が要る。

使い方は、リポジトリ直下の [README.md](../../README.md) を参照。部品の種類・コマンド・テストは [docs/development.md](../../docs/development.md)。

## インストール

    /plugin marketplace add asama0101/pptx-deck
    /plugin install pptx-deck@pptx-deck-market

## スキル

| 入口 | 使う場面 |
|---|---|
| `/pptx-deck:create` | 資料を新しく作る |
| `/pptx-deck:revise` | 作った PPTX を直す（型・デザインの選び直し、文言・数字の修正） |
| `/pptx-deck:rebuild` | `source/` を変えずに PPTX を作り直す |
| `/pptx-deck:review-plan` | 設計図と原稿を HTML で確認する（任意） |
| `/pptx-deck:diagram` | 型に当てはまらない図（NW 構成図など）を絵にする |

5 つのスキルに `disable-model-invocation` は付けない。自然な言い方（「スライドを作って」など）で起動するのが主な入口で、成果物は実行ディレクトリ直下の `<名前>/` にだけ書き、承認は案の選択の 1 回だけで、外部への送信や不可逆な書き込みをしないため。

## 初回の準備

専用の仮想環境（Python の依存を `==` で固定）を、承認を得てから作る。システムの Python には何も入れない。環境がないときは、スキルが作成先と内容を示して確認する。状態は `python run.py --data <絶対パス> doctor` で確かめられる。

Playwright MCP は同梱しない。案の選択と回答の受け取りに使うので、Claude Code に別に設定する（ない場合は、回答を貼り付けて渡す）。

依存は `requirements.txt` で `==` に固定している。ハッシュ固定（`pip install --require-hashes`）は見送った。python-pptx・playwright・pymupdf・lxml と推移依存（Pillow・greenlet など）のすべてについて、Python 3.10〜3.14 と win32・amd64・arm64 の多数のホイール（lxml だけで十数本）のハッシュを持つ必要があり、新しい Python や CPU が出るたびにインストールが失敗し、更新のたびに手で作り直す負担が大きいため。

`${CLAUDE_PLUGIN_DATA}` に置く状態ファイル（`probe-cache.json`）には `schema_version` を入れている。形式を変える版では、ここに移行手順を書く（今の版は作り直せるキャッシュなので、版が違えば捨てて調べ直すだけで、移行は要らない）。

## アンインストールで消えるもの・残るもの

- **消える:** `~/.claude/plugins/data/pptx-deck-<マーケットプレイス名>/`（仮想環境と状態）。最後のインストール先からアンインストールすると、既定で消える。
- **残る:** Playwright の chromium（共有の場所。既定は `%LOCALAPPDATA%\ms-playwright`。ほかのツールと共有できる）と、作った作品（実行したディレクトリ直下の `<名前>/`）。

## ファイルの構成

`run.py`（入口）、`requirements.txt`（固定した依存）、`skills/`（各 `SKILL.md`）、`pptx_deck/`（Python のコード）、`references/`（SKILL.md から参照する資料）、`assets/`（部品・アイコン・テンプレート・見本）。tests・docs はリポジトリ直下にある。

## 出典

`assets/template/standard.potx` は、python-pptx 1.0.2 の既定テンプレートを元に作り替えたもの（python-pptx は MIT、Copyright (c) 2013 Steve Canny）。ライセンス全文は [NOTICE](NOTICE)。`assets/icons/`・`assets/pictures/parts.svg`・`assets/components/`・`assets/web/` は、他者の素材・コードを取り込まず、このプラグイン用に書いたもの。フォント（BIZ UDPゴシック）は同梱せず、名前で指定するだけ。

## ライセンス

MIT
