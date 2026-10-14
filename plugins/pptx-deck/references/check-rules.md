# 検査の rule と直し方

SKILL.md の 5 章から参照する。`build`・`check` の出力 JSON の `violations` に出る `rule` ごとの直し方。内容（文言・数字）は変えず、配置・サイズ・色で直す。

| rule | 直し方 |
|---|---|
| `overflow` | 文字の枠を広げるか、文章を減らす |
| `overlap` | 位置をずらす。意図的なら両方に `data-overlap` |
| `keepout` | テンプレートのヘッダー・フッターの領域（y 676 以降が標準）を避ける |
| `fontMin` | 本文 14pt（19px）・注記 10pt（14px）以上にする |
| `contrast` | 文字色か面の色を変える（基調色の文字は白地で 24px 以上） |
| `imageAlt`・`bodyImage` | `alt`（絵は `data-alt`）を付ける／本文を画像にしない（絵は `pp-picture`） |
| `pictureSvg` | `pp-picture` の中に `<svg>` を入れる |
| `pictureOverflow` | 絵の中の文字が絵の外にはみ出している。文字の位置・長さを直す（`viewBox` と絵の大きさが違うと、はみ出して見えることがある） |
| `fontMin`（絵の中の文字） | 絵の中の文字が 14pt（約 19px）未満。`font-size` と `viewBox` の拡大率を確かめる。収まらないときは図を 2 枚に分けるか、番号だけを絵に置いて説明を凡例に出す |
| `titleMissing` | `data-role="title"`（表紙・裏表紙は `data-ph="title"`）を付ける |
| `dash`（警告） | ダッシュ（—）を消し、接続語か読点で書き直す |
| `sameWord`（警告） | 同じ文言（6 字以上）を 1 枚に 2 度書かない。軸・見出しにくくり出すか、片方を消す |
| `orphanLine`（警告） | 最終行が 1〜2 字だけ。文字の枠の幅を変えるか、文を詰める |
| `pictureColor`（警告） | 絵の中の色がテーマの変数以外。`sv-f-*`・`sv-s-*` のクラスか `var(--accent)` などにする（利用者の画像の中の色は対象外） |
| `pictureTextOverlap`（警告） | 絵の中の文字どうしが重なっている。位置をずらすか、番号だけにして凡例に逃がす |
| `emptyBand`（警告） | 本体が本文領域の下端より 120px 以上手前で終わっている。図や表を下へ広げるか、間隔を配り直す |

警告（`severity: warning`）は `ok` を false にしないが、5.1 で 0 件にする。`build` の前に見るときは `python "${CLAUDE_PLUGIN_ROOT}/run.py" check "<名前>/source/final.html"`（確認用の画像 `previews` は `final.html` の撮影で、PPTX の実描画ではない）。
