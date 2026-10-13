# 型の選定表（内容の形 → 型）

SKILL.md の 3 章から参照する。スライドの内容の形（要素どうしの関係・数・文の量）から、本体の型の**第 1 候補**と**次点 1・次点 2**を決める表。3 案は「第 1 候補＝A、次点 1＝B、次点 2＝C」の型違いで出す。型の説明と部品は [components.md](components.md)。

この表の規則は、市販のデザインパターン集にある「内容に応じた型の選び方」の考え方を、このリポジトリの部品に合わせて自前の文で書き直したもの。原典の文章・画像は含まない。

## 案の数の決め方

案の数は、候補が何個そろうかで決まる。型の候補が 3 つないときは 2 案で出し、無理に埋めない。同じ型で密度だけ違う案は出さない。

C（3 案目）は、次の順で最初に当てはまるものにする。

1. 表の**次点 2**。
2. 次点 2 が空欄（—）でも、**同じ関係のグループ**（下の表の同じ見出しの行）にある別の型で、内容が入るもの。「入る」の条件は 3 つ: 要素数が収まる、必須の定量データがそろう、本文 14pt 以上を保てる。
3. どちらもなければ、2 案で出す。

B（2 案目）も、次点 1 が内容に合わないときは同じ順で代わりを探す。第 1 候補しか成り立たない（型が一意）なら 1 案にして、承認だけにする。

## 表の見方

- 「予定」を付けた型名は、フェーズ 2 で追加する新規部品の仮の名前。実装が終わるまで、設計図の「型」に書かない（今ある型で代用する）。
- 条件が複数当てはまるときは、上の行の条件を優先する。迷ったら、要素の**関係**（並列・比較・手順…）を先に決め、次に数と文の量で型を絞る。
- 「—」は、その位置に置ける型がないこと。

## 1 関係で決まる型（要素どうしに関係がある）

| 内容の関係 | 条件 | 第 1 候補 | 次点 1 | 次点 2 |
|---|---|---|---|---|
| 並列（同格の項目を並べる） | 項目 2〜3 個・文が短い | `parallel-h` | `side-by-side` | `parallel-grid` |
| | 項目 2〜3 個・文が長い | `parallel-v` | `rating` | `spec` |
| | 項目 4 個以上 | `parallel-grid` | `spec` | `compare` |
| 比較（2 つを突き合わせる） | 現行と計画を体制・数量で並べる | `side-by-side` | `delta` | `before-after-h` |
| | 工程の前後を見せる（5 段以下は上下） | `before-after` | `before-after-h` | `side-by-side` |
| | 工程の前後を見せる（5〜6 段は左右） | `before-after-h` | `before-after` | `side-by-side` |
| | 案を評価軸で選ぶ | `options` | `rating` | `compare` |
| | 前回との差 | `quote-compare` | `quote-bridge` | `delta` |
| 手順（順に進む） | 段階が 5 以下・情報が少ない | `flow-h` | `flow-v` | `swimlane-h` |
| | 段階が多く横に入らない | `flow-v` | `swimlane-v` | `timeline-v` |
| | 担当部門をまたぐ（6 段まで） | `swimlane-h` | `swimlane-v` | `flow-h` |
| | 担当部門をまたぐ（7 段以上） | `swimlane-v` | `swimlane-h` | `flow-v` |
| | 工程×時間の予定 | `gantt` | `roadmap` | `flow-h` |
| | 年度ごとの設備の更改 | `roadmap` | `gantt` | `delta` |
| 時系列（発生順の事象） | 区間の長さで待ちを見せる | `timeline-h` | `timeline-v` | `gantt` |
| | 件数が多く文で読ませる | `timeline-v` | `timeline-h` | — |
| 循環（繰り返す） | 4 段階・指標つき | `cycle` | 四角型サイクル（予定 `cycle-box`） | `flow-h` |
| | 2〜3 要素 | 円型サイクル（予定 `cycle-round`） | `cycle` | — |
| 階層（上下の位置づけ） | 上位ほど少ない・小さい | `pyramid` | `layers` | `tree` |
| | 下位ほど少ない（絞り込む） | `funnel` | `venn` | — |
| | 層×系列の格子で自社の範囲を示す | `layers` | `architecture` | `pyramid` |
| 分解・因果 | 要因を寄与で分解する | `tree` | `cause` | — |
| | 時間の連鎖で原因を追う | `cause` | `tree` | `timeline-h` |
| 重なり・絞り込み | 2 条件の重なりで候補を絞る | `venn` | `positioning` | — |
| 位置づけ | 2 軸で象限に置く | `positioning` | `venn` | — |
| 規模の比較 | 数の大小を面で見せる | `scale` | `bar` | `delta` |
| 式（足す・掛ける） | 要素の積み上げで結果を示す | `formula` | `cost` | `waterfall` |
| 段階（積み上がる） | 段を登って到達点に至る | `steps` | `flow-h` | `pyramid` |
| 包含・相互関係 | 含む／含まれる | `enclosure` | `layers` | `venn` |
| | 互いに影響する | `relation` | `cause` | `architecture` |
| 構成（システム・拠点） | 層で見せる | `architecture` | `topology` | `layers` |
| | 系統（左右）で見せる | `topology` | `architecture` | — |
| 体制 | 責任者→PM→チーム | `org` | `raci` | `tree` |
| | 工程×部門の役割 | `raci` | `org` | `swimlane-v` |

## 2 関係がない型（数値・一覧・事例）

| 内容 | 条件 | 第 1 候補 | 次点 1 | 次点 2 |
|---|---|---|---|---|
| グラフ | 伸び・増減を比べる | `bar` | `waterfall` | `line` |
| | 項目の大小を比べる | `data-chart` の横棒 | `bar` | `effort-bar` |
| | 割合 | `data-chart` の `pie` | `stacked` | `bar` |
| | 時間の推移 | `line` | `bar` | `stacked` |
| | 積み上げ・内訳 | `stacked` | `waterfall` | `data-chart` の `pie` |
| | 増減の差し引き | `waterfall` | `quote-bridge` | `bar` |
| | 所見が長文 | 各グラフの `-note` 版（`bar-note`・`line-note`・`stacked-note`・`waterfall-note`） | 吹き出し版の各グラフ | — |
| | 工数を棒で比べる | `effort-bar` | `effort` | `bar` |
| 事例・実績・紹介 | 会社概要 | 会社概要（予定 `company`） | `summary` | `org` |
| | メンバー紹介 | メンバー（予定 `members`） | `org` | `raci` |
| | 理念（MVV） | 理念（予定 `mvv`） | `pyramid` | `layers` |
| | 導入実績 | 導入実績（予定 `track-record`） | `result` | `bar` |
| | 沿革 | `timeline-h` | `timeline-v` | — |
| | 画面・キャプチャの解説 | キャプチャ（予定 `screenshot`） | `architecture` | — |
| | Q&A | Q&A（予定 `qa`） | `rating` | `issues` |
| | 名言・要旨の引用 | 引用（予定 `quote-phrase`） | `summary` | — |
| | 料金プラン | 料金（予定 `pricing`） | `options` | `cost` |
| | 事例 | 事例（予定 `case`） | `before-after` | `result` |

### 表の使い分け

表は 15 種あり、内容が決まるとほぼ型が決まる。

| 内容 | 第 1 候補 | 次点 1 | 次点 2 |
|---|---|---|---|
| 論点｜決定｜根拠の一覧 | `compare` | `rating` | `options` |
| 事実→含意を 2 段で論証 | `rating` | `compare` | `risk` |
| 案の評価（○△×） | `options` | `rating` | `compare` |
| リスク | `risk` | `issues` | `rating` |
| 費用（費目×年度） | `cost` | `quote` | `delta` |
| 見積 | `quote` | `quote-compare` | `cost` |
| 前回との比較 | `quote-compare` | `quote-bridge` | `delta` |
| 工数 | `effort` | `effort-bar` | `delta` |
| 検証項目・機能・要件 | `spec` | `result` | `raci` |
| 判定結果 | `result` | `spec` | `issues` |
| 課題・不具合 | `issues` | `actions` | `risk` |
| 再発防止策 | `actions` | `issues` | `risk` |
| 設備増減 | `delta` | `side-by-side` | `site-matrix` |
| 拠点種別×設備の台数 | `site-matrix` | `delta` | `roadmap` |
| 工程×部門の役割 | `raci` | `org` | `swimlane-v` |

## 3 ページの項目で決まる型（型が一意）

| 内容 | 型 | 案の数 |
|---|---|---|
| 表紙 | `cover` | 1 案（承認のみ） |
| 章扉 | `section` | 1 案 |
| 目次 | `agenda` | 1 案 |
| 数字サマリ | `summary` | 1 案 |
| クロージング決定 | `decision` | 1 案（決定事項はサマリと同じ番号で固定） |
| 裏表紙 | `closing` | 1 案 |
| 障害概要 | `incident` | 1 案（障害報告の冒頭） |

## 4 使い方

1. スライドの主張から、**関係**を 1 つ決める（並列・比較・手順・時系列・循環・階層・分解・位置づけ・数値・一覧・ページ項目）。
2. 該当する行を探し、条件（数・文の量）で第 1 候補・次点 1・次点 2 を取る。
3. A に第 1 候補、B に次点 1、C に次点 2 を置く。空欄（—）や内容が入らない型は、上の「案の数の決め方」に従って、同じグループの別の型で補うか、2 案で出す。
4. 設計図の台帳に、第 1 候補・次点と「選んだ理由」（どの行のどの条件に当たったか）を書く。
5. 内容（文言・数字）は案の間で同じにする。変えるのは型だけ。
