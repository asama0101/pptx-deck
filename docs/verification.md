# 検証手順書

pptx-deck の改修（プラグイン化・レビュー流れ・LibreOffice 非依存）を確かめる手順。自動テストと、人が見る項目に分ける。

## 1. 自動テストの実行

リポジトリのルートで実行する。

```bash
"$LOCALAPPDATA/pptx-deck/venv/Scripts/python.exe" -m unittest discover -s tests -t . -v
```

通しの検証だけを回すときは `-k e2e` を付ける。

```bash
"$LOCALAPPDATA/pptx-deck/venv/Scripts/python.exe" -m unittest discover -s tests -t . -v -k e2e
```

`tests/test_e2e_sample.py` は `init` → `variants` → `finalize` → `build` → `reopen` → `clean` を通し、LibreOffice（soffice）を一度も呼ばないことを確かめる。案には `assets/components` の部品の見本を使う。

## 2. SPEC の受入条件との対応

| 受入条件 | 確かめ方 |
|---|---|
| 1・2 | `tests/test_review_page.py` |
| 3 | `skills/pptx-deck/SKILL.md` の文面を読む |
| 4・5 | `tests/test_no_libreoffice.py`、`tests/test_template_bg.py` |
| 6〜8 | `tests/test_e2e_sample.py`、`tests/test_reopen.py`、`tests/test_lifecycle.py` |
| 9 | `tests/test_plan_review.py` |
| 10 | `grep -ri libreoffice`（コードに LibreOffice への依存が残っていないこと） |
| 11 | Task 14 で確認する |
| 12 | `tests/test_env_select.py` |
| 13 | このファイル（自動テストの実行と、下記の人が見る項目） |

## 3. 人が見る項目

自動テストでは確かめられないため、次を目で確認する。

### 3.1 PowerPoint で開いて崩れを確認する

1. 部品の見本などで `build` した `.pptx` を PowerPoint で開く。
2. 文字のはみ出し、図形のずれ、グラフの欠け、テンプレート（表紙・裏表紙・ヘッダー・フッター）の反映を確認する。
3. 編集できること（図形・表・グラフを選んで直せること）を確認する。
4. 手直しして保存した後、`reopen` が手直しを検知して止まる（終了コード 4）ことを確認する。`--force` で続行できることも確認する。

### 3.2 Playwright MCP でレビューページを操作する

1. `variants` で作った `variants.html` と、`review-plan` で作った設計図の確認ページを開く。
2. 各スライドの案の選択、判定（承認・修正）、コメント入力ができることを確認する。
3. 回答を書き出し、`answers-*.md` として保存できることを確認する。
4. 2 回目の `variants` で、前回承認した案が選択済みで開くことを確認する。
5. 原稿と設計図の不整合が、確認ページ上で見えることを確認する。
