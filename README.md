# pptx-deck

テーマまたは原稿から、PowerPoint で編集できる .pptx を作る Claude Code スキル（プラグイン構成）。Windows 専用。

## できること

- 構成案 → 原稿 → HTML プレビュー → PPTX の順に、承認を取りながら進める。
- 本文を画像にせず、ネイティブの図形・テキスト・チャートで出力する。
- はみ出し・重なり・最小フォントサイズ・コントラスト・AIっぽさ（単調さ・色数・余白など）を自動で検査する。
- LibreOffice があれば、PPTX を画像化して崩れを目視確認する。

## 必要なもの

| 区分 | 内容 |
|---|---|
| 必須 | Node 20 以上、Microsoft Edge、BIZ UDPゴシック（または游ゴシック／メイリオ系） |
| 推奨 | LibreOffice、Python と `pip install pymupdf`（画像化） |

## 使い方

```bash
cd skills/pptx-deck
npm install
node scripts/run.js doctor          # 環境診断
node scripts/run.js init deck-work/sample
node scripts/run.js check deck-work/sample/catalog.html
node scripts/run.js build deck-work/sample/catalog.html deck-work/sample/catalog.pptx --work deck-work/sample
npm test
```

通常は Claude Code から「スライドを作って」と頼む（`skills/pptx-deck/SKILL.md` の手順に従う）。

## 注意

- 画像化は LibreOffice による近似で、PowerPoint の表示と完全には一致しない。最終確認は PowerPoint で行う。
- フォントは同梱しない。BIZ UDPゴシックがない環境では代替フォントになり、折り返しが変わることがある。
- このフォルダを OneDrive の配下に置くと、同期の競合で `.git` が壊れることがある。壊れたときは、リモートから取り直す。
- テンプレ（.pptx/.potx）への流し込み、既存 PPTX の修正は未対応。
- ライセンスは未決定（公開前に決める）。
