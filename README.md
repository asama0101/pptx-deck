# pptx-deck

稟議・提案・計画などの承認文書を、コンサル資料のテイストの編集できる PowerPoint（.pptx）にする Claude Code プラグイン。

## 機能

- テーマ・素材・原稿から、設計図と原稿を作り、HTML のスライド案を選ぶだけで PPTX になる（承認はスライド案の選択の 1 回）。
- 本文は画像にせず、PowerPoint の図形・文字・表・グラフで出力するので、あとから PowerPoint で直せる。
- 50 種類以上の型（比較・手順・構成・時間・数値のグラフや表など）から、1 枚ごとに 3 案＋自由設計 1 案を見比べて選べる。
- 型に当てはまらない図（NW 構成図・障害の動作など）は、`diagram` で SVG の絵にして貼れる（絵の中身は PowerPoint で直せない）。
- 自分の PowerPoint テンプレート（`.potx`／`.pptx`）の表紙・章扉・目次・ヘッダー・フッターの上に作れる。

## 前提条件

- Windows
- Python 3.10 以上（`python` が PATH にあること）
- Claude Code
- 推奨: BIZ UDPゴシック（未導入だと、PowerPoint と文字の折り返しがずれることがある）
- 推奨: Claude Code の Playwright MCP（スライド案の選択結果の受け取りに使う。なければ、コピーした回答をチャットに貼り付ける）
- 最終確認: Microsoft PowerPoint（確認用の画像は HTML の撮影で、PowerPoint の実描画ではない）

## 導入方法

Claude Code で次を実行する。

    /plugin marketplace add asama0101/pptx-deck
    /plugin install pptx-deck@pptx-deck-market
    /reload-plugins

`/reload-plugins` のあと、スキルの一覧に `pptx-deck:create` などが出れば導入できている。

### ローカルに落として導入する

リポジトリを手元に clone し、そのフォルダを配布元として登録する（GitHub から直接導入しない場合）。

    git clone https://github.com/asama0101/pptx-deck.git

Claude Code で、clone したフォルダの絶対パスを指定する。

    /plugin marketplace add C:\Users\<ユーザー名>\...\pptx-deck
    /plugin install pptx-deck@pptx-deck-market
    /reload-plugins

導入元は clone したフォルダそのものなので、`git checkout` でブランチを切り替えたり、フォルダを移動・削除したりすると、導入したプラグインの中身も変わる（動かなくなる）。更新は `git pull` のあとに `/plugin marketplace update pptx-deck-market` を実行する。

初回の `/pptx-deck:create` で、Python の専用環境と Chromium（数百 MB）を導入してよいか確認される。承認すると自動で作られる（ネットワークが要る。システムの Python には何も入れない）。

## 使い方

Claude Code で `/pptx-deck:create` を実行するか、「稟議資料を作って」のように頼む。

    /pptx-deck:create 新サーバー導入の稟議資料を作って

1. 開始ページが開くので、入力（ファイルかテキスト）・出力先のフォルダ・成果物の名前を選ぶ。続いて、目的・対象・枚数・配色（`navy`・`green`・`gray` か `#RRGGBB`）・テンプレートの有無を聞かれる。
2. 設計図と原稿ができ、全スライドの案を並べた HTML（`variants.html`）が開く。
3. スライドごとに案を選び、「回答をコピー」を押す。コメントや、画面上での文字の直しもできる。
4. 選んだ案が PPTX になる。

選んだ出力先にできるもの:

    <出力先>/                     開始ページで選んだフォルダ
      <成果物名>.pptx             成果物
      pptx-deck-source/
        <成果物名>/               設計図・原稿・スライドの断片・回答など（直しの元データ）

入口は 5 つ。

| 入口 | 使う場面 |
|---|---|
| `/pptx-deck:create` | 資料を新しく作る |
| `/pptx-deck:revise` | 作った PPTX を直す（型・デザインの選び直し、文言・数字の修正） |
| `/pptx-deck:rebuild` | 元データ（`pptx-deck-source/`）を変えずに PPTX を作り直す |
| `/pptx-deck:review-plan` | 設計図と原稿を HTML で確認する（任意） |
| `/pptx-deck:diagram` | 型に当てはまらない図を絵にする |

`revise`・`rebuild` は、`<出力先>/<成果物名>.pptx` のパスを渡して頼む（その隣の `pptx-deck-source/<成果物名>/` を使う。PPTX を移動・改名すると見つからない。旧配置（`source` フォルダに元データを置く形）は未対応）。

PowerPoint で直した内容は、`revise`・`rebuild` では取り込まれない（作り直すと消える）。直しは `revise` で頼む。既存の PPTX の編集には使えない。

## 設定

| 項目 | 内容 |
|---|---|
| 配色 | `navy`・`green`・`gray`、または基調色 `#RRGGBB`。スライド案の選択画面でも切り替えられる |
| テンプレート | 16:9（13.33×7.5in）の `.potx`／`.pptx`。フォントと配色は固定で、テンプレートの値は使わない |
| フッター | 左下の文言（「社外秘」など）。作成時に伝える |
| 出力形式 | PPTX・HTML（1 ファイル）・両方。スライド案の選択画面で選ぶ |
| `PPTX_DECK_HOME` | 専用環境の置き場を指定する環境変数（通常は不要。プラグインの保存領域が使われる） |

## 困ったとき

| 症状 | 対処 |
|---|---|
| 環境がないと言われる（終了コード 3） | 案内に従い、導入を承認する。状態は `python run.py --data <絶対パス> doctor` で確認できる（`run.py` は `plugins/pptx-deck/` にある） |
| 文字の折り返しが PowerPoint とずれる | BIZ UDPゴシックを導入する |
| `build` が終了コード 4 で止まる | PPTX が手直しされている。残したいなら別名で保存し、作り直すなら `--force` を付ける（手直しは消える） |
| 検査でエラーが出て PPTX ができない | 出力の違反（はみ出し・重なり・文字の小ささなど）を直す。`revise` に頼んでもよい |
| 絵の中の文字を直したい | 絵は画像なので PowerPoint では直せない。`diagram` で描き直す |

## 開発者向け

内部構造・コマンド・テストの方法は [docs/development.md](docs/development.md)。

## ライセンス

MIT。同梱物の出典は [plugins/pptx-deck/NOTICE](plugins/pptx-deck/NOTICE)。
