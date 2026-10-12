# pptx-deck

テーマまたは原稿から、PowerPoint で編集できる .pptx を作る Claude Code スキル（プラグイン構成）。Windows 専用。

## 概要

「スライドを作って」と頼むと、Claude が構成案 → 原稿 → HTML プレビュー → PPTX の順に、承認を取りながら進める。HTML で体裁を検査して合格させてから PPTX にするので、はみ出し・重なり・AI っぽい単調さを、出力前に潰せる。

- 本文を画像にせず、ネイティブの図形・テキスト・チャートで出力する（PowerPoint で編集できる）。
- 13.33×7.5in（16:9）、BIZ UDPゴシック、無彩色＋基調のアクセント（青など）＋強調色 1 色（橙）。コンサル資料風（判断の枠、玉・棒・四角の記号、アイコン、章タグ、結論の帯）。橙は推奨・承認を求める案だけ。
- 既存 PPTX の修正と、テンプレ（.pptx/.potx）への流し込みには使わない。

## 進め方

| 段階 | 内容 | 承認 |
|---|---|---|
| 1. 入力の確認 | テーマのみか原稿ありか。対象者・目的・枚数を確認し、伝えたい性質から**トーン（アクセント色）**を決める | |
| 2. 構成案 | スライド一覧と各スライドで言い切るメッセージ（テーマのみの場合だけ） | 承認 |
| 3. 原稿 | 見出し・本文・図解/グラフの型と理由・ノート。2 枚目は必ずサマリ。論理・抜け漏れ・読み手の視点で内容レビューしてから示す | 承認①（内容を凍結） |
| 4. HTML プレビュー | `deck.html` を書き、`check` に合格させてからブラウザで見せる | 承認② |
| 5. PPTX 出力 | `build` で PPTX を出し、出力後検査と画像化を行う | |
| 6. 報告 | 検査結果と目視所見を伝える。PowerPoint での最終確認を勧める | |

作業物（構成案・原稿・HTML・PPTX）は `deck-work/<名前>/` にまとまり、途中から再開できる。確認用の画像（`render/`）と検査結果（`report.json`）は、OS の一時フォルダの `pptx-deck/<作業名>/` に出る（`build` の出力の `tempDir`・`reportPath` に場所が出る。消すのは OS の掃除に任せる）。

## 自動検査

`check`（HTML）と `build`（PPTX 出力後）が、JSON で違反と次の一手（`suggestion`）を返す。`error` は不合格、`warning` は合否に影響しない。

| 分類 | 主な検査 |
|---|---|
| 幾何 | 安全余白、はみ出し、重なり、折り返しの安定（`wrapStable`）、タイトル位置 |
| 文字 | 最小フォントサイズ、タイトルと本文の差（4pt 以上）、コントラスト比 4.5:1 以上 |
| AI っぽさ | 同じ大きさのカードの横並び（`cardRow`）、同一レイアウトの連続、色数（基調＋強調色の 2 色まで）、余白の使用率 |
| 内容の見せ方 | 数字の比較はグラフにする（`numberCompare`）、内訳は積み上げ（`chartBreakdown`）、差額は注記（`chartDiff`）、効果を謳うなら before/after（`effectBeforeAfter`） |
| 視線設計 | 矢印は強調対象にだけ向ける（`arrowTarget`）、強調は 1 点に絞る（`isolation`。基調色と強調色の合計）、右下を空けない（`zFlow`）、アクセント色が伝えたい性質に合う（`colorTone`）、橙は推奨・承認を求める案だけ（`accent2Reco`、警告） |
| 出典 | 数字があるスライドには出典を書く（`sourceMissing`、警告） |

違反は自動修正（余白縮小 → 行間 → フォント縮小、最大 3 回）で直し、それでも収まらないときはスライド分割案・文章の削減案を示して承認を得る。

## 作れるもの

- **レイアウト**: `cover`・`section`・`content`・`diagram`・`chart`・`closing`。
- **図解**（`design/diagrams.html` に見本 18 枚）: ツリー、ピラミッド、フロー（横・縦）、サイクル、ビフォーアフター（横・縦）、地図（日本全国 47 都道府県の輪郭）、相関図、マトリクス、ベン図、数式、項目比較、TAM-SAM-SOM、階層・レイヤー、トライアングル、階段、ガントチャート。矩形・角丸矩形・円・三角形・直線矢印（水平・垂直・斜め）・テキストで描く。半透明の円も使える（ベン図）。輪郭の多角形（フリーフォーム）も使える（地図）。立体は平面の重ねで表す。六角形が要る図（ハニカム）は作れない。
- **チャート**（`design/charts.html` に見本）: `bar`・`barh`・`line`（複数系列も可）・`pie`・`stacked`・`stackedh`・`stacked100`・`area`・`cumulative`・`waterfall`。データの関係から型を選ぶ。注目データだけアクセント色、他は無彩色。
- **コンサル資料風の部品**（`design/consulting.html`・`design/planning.html` に見本）: 円形の面に置く線画アイコン（22 種、`references/icons/`）、章タグ・見出し下の細線・出典・ページ番号・結論の帯、判断の枠（決めること・期限・推奨）、玉・棒・四角・◆の記号による比較、月軸＋判断ポイントの行のガント、複数系列の折れ線、目次つきの表紙。検証計画書向けに、3 層の構成図、試験工程、ゲージによる判定基準。表（行×列）と、図の横の説明パネルは使わない。
- **トーン**: `trust`・`growth`・`alert`・`energy`・`premium`・`neutral`。`data-tone` に宣言し、アクセント色の色相と合わないと不合格にする。強調色（`--accent2`、既定は橙）は「推奨・承認を求める案」だけに使う（期限・リスクは基調色の濃色や太線で示す）。
- 設計の考え方は `skills/pptx-deck/references/design-guide.md`（視線設計と色彩心理、グラフ・図解の選び方、効果と内訳・差額の見せ方）。

## 必要なもの

| 区分 | 内容 |
|---|---|
| 必須 | Node 20 以上、Microsoft Edge、BIZ UDPゴシック（または游ゴシック／メイリオ系） |
| 推奨 | LibreOffice、Python と `pip install pymupdf`（画像化） |

## 使い方

通常は Claude Code から「スライドを作って」「資料を作って」と頼む（`skills/pptx-deck/SKILL.md` の手順に従う）。コマンドを直接使うときは次のとおり。

```bash
cd skills/pptx-deck
npm install
node scripts/run.js doctor                 # 環境診断
node scripts/run.js init deck-work/sample  # 作業フォルダに base.css・chart-preview.js・アイコンをコピー
node scripts/run.js icons deck-work/sample # base.css の色でアイコンを作り直す
node scripts/run.js check design/catalog.html            # 見本は design/ を直接使う
node scripts/run.js build design/catalog.html deck-work/sample/catalog.pptx --work deck-work/sample  # 画像・検査結果は一時フォルダへ
node scripts/run.js verify deck-work/sample/catalog.pptx           # PPTX だけを検査
node scripts/run.js render deck-work/sample/catalog.pptx <出力フォルダ>  # 画像化
npm test
```

| コマンド | 役割 |
|---|---|
| `doctor` | Node・Edge・フォント・LibreOffice・pymupdf の診断 |
| `init` | 作業フォルダの作成と、CSS・プレビュー用 JS・アイコン（`icons/`）の書き出し（見本 5 種は `design/` を直接参照） |
| `icons` | 作業フォルダの `base.css` の `--accent`・`--accent2` の色で、アイコンを作り直す |
| `check` | HTML の計測と検査（`--attempt N` で自動修正の回数を渡す） |
| `build` | HTML → PPTX、出力後検査、画像化（画像と `report.json` は OS の一時フォルダへ） |
| `verify` | 既存 PPTX の検査 |
| `render` | PPTX を LibreOffice で PNG にする |

## 構成

```
.claude-plugin/plugin.json      プラグイン定義
skills/pptx-deck/
  SKILL.md                      Claude への手順書
  references/design-guide.md    設計ガイド
  references/icons/             線画アイコン（SVG、22 種）
  design/                       base.css と見本（catalog・diagrams・charts・consulting・planning）、japan-map.json（日本地図の輪郭）
  scripts/                      run.js（CLI）、measure・build・render、rules/（検査）、tools/（日本地図の輪郭データの生成）
  config/thresholds.json        検査のしきい値
  samples/                      受入サンプルと expected.json
  tests/                        npm test
docs/specs/                     仕様（SPEC）
```

## 注意

- 画像化は LibreOffice による近似で、PowerPoint の表示と完全には一致しない。最終確認は PowerPoint で行う。
- チャートの HTML プレビューも近似。
- フォントは同梱しない。BIZ UDPゴシックがない環境では代替フォントになり、折り返しが変わることがある。
- このフォルダを OneDrive の配下に置くと、同期の競合で `.git` が壊れることがある。壊れたときは、リモートから取り直す。
- PPTX の検証は、XML の整形式、`[Content_Types].xml`、チャートの軸 ID の宣言に絞っている（スキーマ(XSD)検証はしない）。
- 写真素材は自動で集めない。画像は利用者が渡したものと、同梱のアイコン（SVG）だけ。
- アイコンは `icons/<名前>.svg`（基調色）・`-o`（強調色）・`-w`（白）。配色を変えたら `icons` コマンドで作り直す。
- 第 2 軸・3D のチャートは使わない。ウォーターフォールは、背景色の土台を積み上げた編集可能なネイティブチャートで、値は計算した位置のテキストボックスで置く（累計の棒と同じ方式）。
- テンプレ（.pptx/.potx）への流し込み、既存 PPTX の修正は未対応。
- 日本地図の輪郭（`skills/pptx-deck/design/japan-map.json`）は、Natural Earth（パブリックドメイン。https://www.naturalearthdata.com/ ）の admin-1 を `scripts/tools/gen-japan-map.js` で簡略化したもの。
- ライセンスは MIT（`LICENSE`）。フォントは同梱していない。依存（pptxgenjs=MIT、playwright=Apache-2.0、jszip、fast-xml-parser=MIT）はそれぞれのライセンスに従う。
