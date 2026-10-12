# pptx-deck 作り直し 実装計画 B（テンプレート一式・SKILL.md・通しの確認）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 計画 A のエンジンの上に、コンサルテイストのスライドを作るためのテンプレート一式（レイアウト・図解・表・グラフ・アイコン・配色）、原稿の書式と検査、SKILL.md、README を作り、承認の流れを通しで確認して、旧スキルの置き換えを完了する。

**Architecture:** テンプレートは `skills/pptx-deck/assets/components/` の HTML 断片（`<section class="slide">` 1 つ）。Claude が断片をコピーして内容を差し替え、`slides/NN-A.html`〜で 3 案にする。配色は `theme.css` の変数だけで持つ。断片は、全部が `check` に違反なく通り、`build` できることをテストで保証する（基調色を変えても同じ）。グラフのプレビューは `chart-preview.js` の SVG（近似）。

**Tech Stack:** 計画 A と同じ（Python・python-pptx・Playwright・pytest）。HTML/CSS/SVG と、素の JavaScript（プレビュー用）。

**Spec:** `docs/specs/2026-10-12_1607_pptx-deck-rebuild.md`（承認済み）。受入条件 1・2・3・5（利用者のテンプレートでの確認）・6・8 をこの計画で満たす。

**前提:** 計画 A（`2026-10-12-pptx-deck-rebuild-engine.md`）の Task 1〜10 が完了している。

## Global Constraints

すべてのタスクに暗黙に適用する。値は SPEC から写した。

- Windows 専用。BIZ UDPゴシック。16:9（1280×720px = 13.33×7.5in。1px = 0.75pt）。本文を画像にしない。画像はアイコン（SVG）と利用者の写真だけ。
- 配色は無彩色＋基調 1 色＋強調 1 色まで。グラデーション・影・3D は使わない。色は `theme.css` の変数（`var(--accent)` など）だけで指定し、`#RRGGBB` を直書きしない（白 `#FFFFFF` と、下記の固定の灰を除く）。
- 文字: 本文 14pt（約 19px）以上、注記 10pt（14px）以上。コントラスト比 4.5:1 以上（24px 以上は 3:1）。基調色の文字は、白地かつ 24px 以上のときだけ使う（薄い面の上では `var(--text)`）。
- コンサルテイスト: 見出しは結論を言い切る 1 文。1 スライド 1 メッセージ。数字には出典と前提。判断が要るスライドは決めること・期限・推奨。強調色は 1 スライドで 1 点（推奨・承認を求める対象）。密度は高め、余白と整列をそろえる。
- 体裁の検査は最小限（計画 A の `check`）。コンサルテイスト自体の自動検査は作らない。
- スピーカーノートは作らない。
- ファイルの置き場所: テンプレートと手順 = `skills/pptx-deck/`。一過性のもの = `tempfile` の OS の一時フォルダ。成果物と中間成果物 = 実行ディレクトリ直下の `<名前>/`。
- 旧 `skills/pptx-deck` の内容は参考にとどめる（コピーしない）。旧仕様（構成案の承認、判断の枠のルール、橙の役割ルール）は引き継がない。
- コメントとコミットメッセージは日本語。コミットメッセージの末尾に、環境が指定する `Co-Authored-By` / `Claude-Session` の行を付ける。
- テストは仮想環境の Python（`PY="$LOCALAPPDATA/pptx-deck/venv/Scripts/python.exe"`）で、`skills/pptx-deck` を作業ディレクトリにして実行する。

## Review Focus

1. 基調色を変える（明るい黄色 `#FFFF00` など）と、白文字の面・薄い面の文字がコントラスト違反になる → 全断片を 2 つの配色で検査する（Task 1 のテスト基盤）。
2. 利用者のテンプレートでは、本文領域やヘッダー・フッターの位置が標準と違う → 断片は `--area-*`・`--title-*` の変数を使い、固定座標に頼る部分は領域の内側に収める（Task 1・7 で、変換済みの別テンプレートでも通す）。
3. グラフのデータが 1 件・負の値・長い項目名 → プレビューが壊れず、PPTX のグラフも作れる（Task 5）。
4. 原稿（`script.md`）の書き方が崩れている（`## S02` の番号が飛ぶ、見出しがない）→ 検査が全件を列挙して止める（Task 6）。
5. 旧スキルの記述が新スキルに残る → README・SKILL.md から旧仕様の語（`構成案`・`橙`・`deck.html`・`npm`）が消えていることを確認する（Task 7）。
6. 3 案ページで、案が 1 つだけのスライドと 3 案のスライドが混ざる → 計画 A で対応済み。通しの確認（Task 7）で実際に混ぜて確かめる。

---

## ファイル構成

```
skills/pptx-deck/
  SKILL.md                         # Task 6
  assets/
    web/base.css                   # Task 1 で拡充
    web/chart-preview.js           # Task 5
    icons/*.svg                    # Task 2（currentColor の線画 14 種）
    components/
      layouts/  cover.html section.html agenda.html decision.html closing.html
      diagrams/ flow-h.html tree.html matrix.html pyramid.html cycle.html gantt.html
                venn.html before-after.html layers.html compare.html
      tables/   compare.html rating.html cost.html schedule.html
      charts/   bar.html line.html stacked.html waterfall.html pie.html
    sample/script.md               # Task 6（サンプル原稿）
  pptx_deck/script_lint.py         # Task 6
  tests/
    test_components.py             # Task 1（以降の断片を全部検査）
    test_icons.py  test_chart_preview.py  test_script_lint.py
    test_e2e_library.py            # Task 7
README.md                          # Task 7
.claude-plugin/plugin.json         # Task 7
```

## 断片の書き方（共通）

- 1 ファイル = 先頭に HTML コメント（用途・差し替える所・向く内容）＋ `<section class="slide" data-layout="…">` 1 つ。
- 座標は `style="left:…px;top:…px;width:…px;height:…px"`。面（`pp-shape`）と文字（`pp-text`）は兄弟要素にし、文字の中心を含む面が「背後の色」になる（計画 A の `measure.js`）。
- 使えるクラス（Task 1 の `base.css`）: 面 `f-accent f-dark f-mid f-light f-soft f-emph f-white`、角丸 `r`、文字 `t-white t-accent t-emph t-sub center right b`、大きな数字 `num`、罫線 `hr`（`pp-line` と併用）。
- 領域: 本文は標準テンプレートで x 64〜1216、y 150〜640。タイトルは `data-role="title"`（位置は CSS が決める）。出典は `data-role="caption" data-chrome` で、y 640〜664 に置く。
- アイコン: `<img class="pp-image" data-role="icon" src="icons/<名前>-<accent|emphasis|white|gray>.svg" alt="…">`（`init` が色違いを書き出す）。

---

### Task 1: 基本 CSS の拡充・レイアウト断片・断片の検査基盤

**Files:**
- Modify: `skills/pptx-deck/assets/web/base.css`
- Create: `skills/pptx-deck/assets/components/layouts/{cover,section,agenda,decision,closing}.html`
- Test: `skills/pptx-deck/tests/test_components.py`

**Interfaces:**
- Consumes: `initdir.init`, `measure.measure`, `check.check_model`, `build.build`, `template.TemplateInfo`, `theme.derive`
- Produces: `tests/test_components.py` の `check_fragment(path, workdir)`（以降のタスクの断片は、このテストに自動で入る。`assets/components/**/*.html` をすべて検査する）

- [ ] **Step 1: 検査基盤のテストを書く**

`tests/test_components.py`:

```python
import json
import shutil
from pathlib import Path

import pytest

from pptx_deck import build, check, initdir, measure, paths, template, theme

COMP = paths.ASSETS / "components"
FILES = sorted(COMP.rglob("*.html"))
pytestmark = pytest.mark.skipif(shutil.which("soffice") is None and not Path(
    r"C:\Program Files\LibreOffice\program\soffice.exe").exists(), reason="LibreOffice なし")

COLORS = ["navy", "#FFFF00"]            # 暗い基調色と、明るい基調色（Review Focus 1）


@pytest.fixture(scope="session", params=COLORS)
def work(request, tmp_path_factory):
    w = tmp_path_factory.mktemp("lib") / "lib"
    initdir.init(w, color=request.param)
    return w


def wrap(fragment: str) -> str:
    return ('<!doctype html><html lang="ja"><head><meta charset="utf-8">'
            '<link rel="stylesheet" href="theme.css"><link rel="stylesheet" href="base.css">'
            '<script src="chart-preview.js"></script></head><body>' + fragment + "</body></html>")


def check_fragment(path: Path, work: Path):
    cfg = json.loads((work / "template.json").read_text(encoding="utf-8"))
    info = template.TemplateInfo.from_dict(cfg["info"])
    html = work / f"_c_{path.parent.name}_{path.stem}.html"
    html.write_text(wrap(path.read_text(encoding="utf-8")), encoding="utf-8")
    model = measure.measure(html)
    return model, info, cfg, check.check_model(model, info)


def test_there_are_components():
    assert FILES, "assets/components に断片がありません"


@pytest.mark.parametrize("path", FILES, ids=lambda p: f"{p.parent.name}/{p.stem}")
def test_component_is_clean_and_buildable(path, work):
    model, info, cfg, violations = check_fragment(path, work)
    assert len(model) == 1
    assert violations == [], violations
    out = work / f"_c_{path.stem}.pptx"
    build.build(model, work / cfg["template"], info, theme.derive(cfg["color"]), out,
                base_dir=work, work_name="components")
    assert check.errors(check.check_pptx(out)) == []


@pytest.mark.parametrize("path", FILES, ids=lambda p: f"{p.parent.name}/{p.stem}")
def test_component_header_comment(path):
    head = path.read_text(encoding="utf-8").lstrip()
    assert head.startswith("<!--") and "用途:" in head.split("-->")[0]
    assert "#" not in "".join(l for l in head.splitlines() if "style=" in l and "var(" not in l and "rgba" not in l
                              and "#FFFFFF" not in l.upper()), "色の直書きがあります（var(--…) を使う）"
```

注: 最後の assert は「`style=` の行に `#RRGGBB` の直書きがない」ことの粗い確認。`#FFFFFF` と `var(`・`rgba` を含む行は除外する。誤検出する断片が出たら、行を直して `var(--…)` にする（検査を緩めない）。

- [ ] **Step 2: 失敗を確認する**

Run: `"$PY" -m pytest tests/test_components.py`
Expected: FAIL（`assets/components に断片がありません`）

- [ ] **Step 3: base.css を拡充する**

`assets/web/base.css` の `.pp-text { line-height: 1.5; }` の行を次に置き換え、末尾に追記する。

```css
.pp-text { font-size: 20px; line-height: 1.5; color: var(--text); }
```

末尾に追記:

```css
.pp-text li::before { content: "• "; }          /* プレビューの箇条書きの印（PPTX では本物の箇条書き） */

/* 面の色 */
.f-accent { background: var(--accent); }
.f-dark   { background: var(--accent-dark); }
.f-mid    { background: var(--accent-mid); }
.f-light  { background: var(--accent-light); }
.f-soft   { background: var(--bg-soft); }
.f-emph   { background: var(--emphasis); }
.f-white  { background: #FFFFFF; border: 1px solid var(--line); }
.r { border-radius: 10px; }

/* 文字の色・形 */
.t-white  { color: #FFFFFF; }
.t-accent { color: var(--accent); }
.t-emph   { color: var(--emphasis); }
.t-sub    { color: var(--text-sub); }
.center { text-align: center; }
.right  { text-align: right; }
.b      { font-weight: 700; }
.num    { font-size: 44px; font-weight: 700; line-height: 1.2; color: var(--accent); }

/* 罫線（pp-line と併用） */
.hr { background: var(--line); }
```

- [ ] **Step 4: レイアウト断片を書く**

`assets/components/layouts/cover.html`:

```html
<!-- 用途: 表紙。題名・副題は利用者のテンプレートの表紙レイアウトの位置に入る。
     差し替える所: 題名（結論が分かる一文でもよい）・副題・日付と部署。 -->
<section class="slide" data-layout="cover">
  <div class="pp-text" data-ph="title" style="height:120px">クラウド基盤への移行を承認いただきたい</div>
  <div class="pp-text" data-ph="subtitle" style="height:60px">3案の比較と推奨案（B案）</div>
  <div class="pp-text" data-role="caption" style="left:96px;top:520px;width:600px;height:24px">2026年10月　情報システム部</div>
</section>
```

`assets/components/layouts/section.html`:

```html
<!-- 用途: 章扉。この章で答える問いと中身の予告。
     差し替える所: 章番号・見出し（この章の結論）・問い・予告 3 点。 -->
<section class="slide" data-layout="section">
  <div class="pp-text" data-role="title" style="height:44px">現行基盤は2028年に保守が切れ、移行が必要になる</div>
  <div class="pp-text num" style="left:64px;top:200px;width:160px;height:64px">01</div>
  <div class="pp-text" data-role="lead" style="left:64px;top:280px;width:1000px;height:70px">この章で答える問い: なぜ今、移行を決める必要があるのか</div>
  <div class="pp-line hr" style="left:64px;top:370px;width:1152px"></div>
  <div class="pp-text" data-role="body" style="left:64px;top:396px;width:1000px;height:130px"><ul><li>現行基盤の保守期限とリスク</li><li>移行しない場合のコスト</li><li>決定の期限</li></ul></div>
</section>
```

`assets/components/layouts/agenda.html`:

```html
<!-- 用途: 目次。章の番号・名前・一言の中身を行で並べ、罫線で区切る。
     差し替える所: 章の数（3〜4）・名前・説明。 -->
<section class="slide" data-layout="agenda">
  <div class="pp-text" data-role="title" style="height:44px">本日お願いしたいのは、B案の採用と予算の承認である</div>
  <div class="pp-text num" style="left:64px;top:170px;width:100px;height:60px">01</div>
  <div class="pp-text b" data-role="lead" style="left:180px;top:170px;width:900px;height:36px">背景と課題</div>
  <div class="pp-text t-sub" style="left:180px;top:210px;width:900px;height:30px">保守期限と運用負荷</div>
  <div class="pp-line hr" style="left:64px;top:256px;width:1152px"></div>
  <div class="pp-text num" style="left:64px;top:280px;width:100px;height:60px">02</div>
  <div class="pp-text b" data-role="lead" style="left:180px;top:280px;width:900px;height:36px">3案の比較</div>
  <div class="pp-text t-sub" style="left:180px;top:320px;width:900px;height:30px">費用・期間・リスク</div>
  <div class="pp-line hr" style="left:64px;top:366px;width:1152px"></div>
  <div class="pp-text num" style="left:64px;top:390px;width:100px;height:60px">03</div>
  <div class="pp-text b" data-role="lead" style="left:180px;top:390px;width:900px;height:36px">推奨案と計画</div>
  <div class="pp-text t-sub" style="left:180px;top:430px;width:900px;height:30px">B案の進め方と判断のタイミング</div>
  <div class="pp-line hr" style="left:64px;top:476px;width:1152px"></div>
  <div class="pp-text num" style="left:64px;top:500px;width:100px;height:60px">04</div>
  <div class="pp-text b" data-role="lead" style="left:180px;top:500px;width:900px;height:36px">承認のお願い</div>
  <div class="pp-text t-sub" style="left:180px;top:540px;width:900px;height:30px">決めていただくこと</div>
</section>
```

`assets/components/layouts/decision.html`:

```html
<!-- 用途: 判断を求めるスライド（結論・承認依頼）。決めること・期限・推奨を上の帯に、理由を 3 列に、
     承認いただく内容を強調色の帯 1 つに置く。強調色はこの帯だけ。
     差し替える所: 帯の 3 項目・理由 3 つ（数字と一言）・承認の文言・出典。 -->
<section class="slide" data-layout="content">
  <div class="pp-text" data-role="title" style="height:44px">B案を採用すれば、現行維持より5年間で5,000万円を削減できる</div>
  <div class="pp-shape f-light r" style="left:64px;top:150px;width:1152px;height:100px"></div>
  <div class="pp-text" data-role="caption" style="left:88px;top:160px;width:340px;height:20px">決めること</div>
  <div class="pp-text b" style="left:88px;top:182px;width:340px;height:60px">移行先の案と予算</div>
  <div class="pp-text" data-role="caption" style="left:480px;top:160px;width:340px;height:20px">期限</div>
  <div class="pp-text b" style="left:480px;top:182px;width:340px;height:60px">11月の経営会議</div>
  <div class="pp-text" data-role="caption" style="left:872px;top:160px;width:320px;height:20px">推奨</div>
  <div class="pp-text b" style="left:872px;top:182px;width:320px;height:60px">B案（段階移行）</div>
  <div class="pp-text num" style="left:64px;top:280px;width:360px;height:56px">▲5,000万円</div>
  <div class="pp-text" style="left:64px;top:340px;width:360px;height:120px">5年間の総費用が、現行維持（保守延長を含む）より少ない</div>
  <div class="pp-text num" style="left:456px;top:280px;width:360px;height:56px">6か月</div>
  <div class="pp-text" style="left:456px;top:340px;width:360px;height:120px">A案の12か月より短く、業務への影響が小さい</div>
  <div class="pp-text num" style="left:848px;top:280px;width:360px;height:56px">1回</div>
  <div class="pp-text" style="left:848px;top:340px;width:360px;height:120px">停止は夜間の1回だけで済む</div>
  <div class="pp-shape f-emph r" style="left:64px;top:500px;width:1152px;height:110px"></div>
  <div class="pp-text t-white b" style="left:88px;top:520px;width:1104px;height:70px;font-size:22px">ご承認いただきたいこと: B案の採用と、初年度予算1.2億円の確保</div>
  <div class="pp-text" data-role="caption" data-chrome style="left:64px;top:640px;width:900px;height:24px">出典: 社内試算（2026年9月）。5年間の総費用、現行比</div>
</section>
```

`assets/components/layouts/closing.html`:

```html
<!-- 用途: 裏表紙（最終スライド）。結びの一文と、次のステップ。位置は利用者のテンプレートの裏表紙レイアウト。
     差し替える所: 結びの一文・次のステップ（2〜3 点）。 -->
<section class="slide" data-layout="closing">
  <div class="pp-text" data-ph="title" style="height:100px">以上、ご承認をお願いします</div>
  <div class="pp-text" data-role="body" style="left:96px;top:430px;width:1000px;height:100px"><ul><li>承認後、11月に詳細設計を開始する</li><li>2027年3月に第1期の移行を完了する</li></ul></div>
</section>
```

- [ ] **Step 5: 基盤のテストを実行する**

Run: `"$PY" -m pytest tests/test_components.py`
Expected: レイアウト 5 枚 × 2 配色 ＋ 見出しコメントの検査がすべて PASS。違反が出たら、メッセージ（`overlap`・`overflow` など）に従って断片の座標・幅・高さを直す（`check` の基準は緩めない）。特に、`decision.html` の「理由」の 3 列（幅 360px で 120px の高さ）に文が収まること、`agenda.html` が `y=540+30=570` で領域の中に収まることを確認する。

- [ ] **Step 6: 目で確認する**

```bash
python run.py init "$TEMP/chk-lib" --color navy
```

`$TEMP/chk-lib/` に `final.html` を作り（5 枚の断片を `wrap` で連結）、`python run.py build` で PPTX と PNG を作る。PNG を Read で開き、見出し・帯・番号・強調の帯が整列し、強調色が `decision` の帯だけに使われていることを確認する。

- [ ] **Step 7: コミット**

```bash
git add skills/pptx-deck
git commit -m "feat: 基本 CSS を拡充し、レイアウト断片 5 種と断片の検査基盤を追加"
```

---

### Task 2: アイコン

**Files:**
- Create: `skills/pptx-deck/assets/icons/{alert,building,check,clock,cloud,coin,document,flag,gear,graph,key,people,server,shield}.svg`
- Test: `skills/pptx-deck/tests/test_icons.py`

**Interfaces:**
- Produces: 14 個の SVG（24×24 の線画。`stroke="currentColor"`）。`init` が `icons/<名前>-<accent|emphasis|white|gray>.svg` を書き出す（計画 A の Task 9）。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_icons.py`:

```python
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from pptx_deck import build, initdir, paths

ICONS = sorted((paths.ASSETS / "icons").glob("*.svg"))
NAMES = {"alert", "building", "check", "clock", "cloud", "coin", "document", "flag", "gear",
         "graph", "key", "people", "server", "shield"}


def test_icon_set():
    assert {p.stem for p in ICONS} == NAMES


@pytest.mark.parametrize("svg", ICONS, ids=lambda p: p.stem)
def test_icon_is_valid_line_art(svg):
    root = ET.parse(svg).getroot()
    assert root.get("viewBox") == "0 0 24 24"
    assert "currentColor" in svg.read_text(encoding="utf-8")


@pytest.mark.parametrize("svg", ICONS, ids=lambda p: p.stem)
def test_icon_rasterizes(svg, tmp_path):
    colored = tmp_path / f"{svg.stem}.svg"
    colored.write_text(svg.read_text(encoding="utf-8").replace("currentColor", "#1F3A5F"), encoding="utf-8")
    png = build.rasterize_svg(colored, 48, "icon-test")
    assert png.exists() and png.stat().st_size > 200


def test_init_writes_four_tones(tmp_path):
    import shutil
    if shutil.which("soffice") is None and not Path(r"C:\Program Files\LibreOffice\program\soffice.exe").exists():
        pytest.skip("LibreOffice なし")
    w = tmp_path / "w"
    initdir.init(w, color="green")
    for tone in ("accent", "emphasis", "white", "gray"):
        assert (w / "icons" / f"shield-{tone}.svg").exists()
    assert "#1E6B52" in (w / "icons" / "shield-accent.svg").read_text(encoding="utf-8")
    assert "currentColor" not in (w / "icons" / "shield-accent.svg").read_text(encoding="utf-8")
```

- [ ] **Step 2: 失敗を確認する**

Run: `"$PY" -m pytest tests/test_icons.py`
Expected: FAIL（アイコンがない）

- [ ] **Step 3: アイコンを書く**

各ファイルは次の形。`<BODY>` を下の表の内容にする（改行・インデントは自由）。

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><BODY></svg>
```

| ファイル | `<BODY>` |
|---|---|
| `alert.svg` | `<path d="M12 3l10 18H2z"/><path d="M12 10v5M12 18v.5"/>` |
| `building.svg` | `<path d="M4 21V5l8-2 8 2v16z"/><path d="M9 9h2M13 9h2M9 13h2M13 13h2M10 21v-4h4v4"/>` |
| `check.svg` | `<circle cx="12" cy="12" r="9"/><path d="M8 12.5l3 3 5-6"/>` |
| `clock.svg` | `<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>` |
| `cloud.svg` | `<path d="M7 18a4 4 0 0 1-.5-7.97A6 6 0 0 1 18 9.5 4.3 4.3 0 0 1 17.5 18z"/>` |
| `coin.svg` | `<circle cx="12" cy="12" r="9"/><path d="M9 9.5c0-1 1.2-1.7 3-1.7s3 .7 3 1.7-1.2 1.5-3 1.9-3 .9-3 1.9 1.2 1.7 3 1.7 3-.7 3-1.7M12 6v1.8M12 16.2V18"/>` |
| `document.svg` | `<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4M9 12h6M9 16h6"/>` |
| `flag.svg` | `<path d="M5 21V4M5 4h12l-2 4 2 4H5"/>` |
| `gear.svg` | `<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M19 5l-2 2M7 17l-2 2"/>` |
| `graph.svg` | `<path d="M4 20V4M4 20h16"/><path d="M8 16v-5M12 16V8M16 16v-8"/>` |
| `key.svg` | `<circle cx="8" cy="15" r="4"/><path d="M11 12l9-9M16 7l3 3M14 9l2 2"/>` |
| `people.svg` | `<circle cx="9" cy="8" r="3"/><circle cx="17" cy="9" r="2.5"/><path d="M3 20c0-3.5 2.7-6 6-6s6 2.5 6 6M15 14.5c3 0 6 1.7 6 5.5"/>` |
| `server.svg` | `<rect x="3" y="4" width="18" height="7" rx="1"/><rect x="3" y="13" width="18" height="7" rx="1"/><path d="M7 7.5h.01M7 16.5h.01"/>` |
| `shield.svg` | `<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M9 12l2 2 4-4"/>` |

- [ ] **Step 4: テストを実行する**

Run: `"$PY" -m pytest tests/test_icons.py`
Expected: すべて PASS。

- [ ] **Step 5: 目で確認する**

14 個を 1 枚の HTML に並べて（`init` 後の `icons/*-accent.svg`）Playwright MCP で開き、それぞれが何のアイコンか判別できることを確認する。判別しにくいものは `<BODY>` を調整する。

- [ ] **Step 6: コミット**

```bash
git add skills/pptx-deck
git commit -m "feat: 線画アイコン 14 種を追加"
```

---

### Task 3: 図解の断片 10 種

**Files:**
- Create: `skills/pptx-deck/assets/components/diagrams/{flow-h,tree,matrix,pyramid,cycle,gantt,venn,before-after,layers,compare}.html`
- Modify: `skills/pptx-deck/pptx_deck/measure.js`（`color(srgb …)` の色を読む）は計画 A で対応済み。確認だけ行う。

**Interfaces:**
- Consumes: Task 1 の基盤（`tests/test_components.py` が自動で拾う）、Task 2 のアイコン（`icons/*-accent.svg` など）、`pp-line` の `data-dir="rev"`（計画 A）

- [ ] **Step 1: 断片を書く**（`diagrams/` の 10 ファイル）

`flow-h.html`（フロー: 横 4 段階。強調は最後の帯 1 点）:

```html
<!-- 用途: 手順・段階を左から右へ。各段階に番号・名前・一言。結論の帯を下に 1 つ。
     差し替える所: 段階の数（3〜4。3 のときは幅を 336px、x を 64/456/848 にする）・名前・説明・結論。 -->
<section class="slide" data-layout="diagram">
  <div class="pp-text" data-role="title" style="height:44px">移行は4つの段階で進め、各段階の終わりに承認を取る</div>
  <div class="pp-shape f-light r" style="left:64px;top:170px;width:240px;height:290px"></div>
  <div class="pp-text num" style="left:84px;top:186px;width:200px;height:56px">01</div>
  <div class="pp-text b" style="left:84px;top:250px;width:200px;height:34px">現状調査</div>
  <div class="pp-text" style="left:84px;top:296px;width:200px;height:150px">資産と依存関係を洗い出す</div>
  <div class="pp-line" data-arrow="end" style="left:308px;top:314px;width:56px;background:var(--accent)"></div>
  <div class="pp-shape f-light r" style="left:368px;top:170px;width:240px;height:290px"></div>
  <div class="pp-text num" style="left:388px;top:186px;width:200px;height:56px">02</div>
  <div class="pp-text b" style="left:388px;top:250px;width:200px;height:34px">設計</div>
  <div class="pp-text" style="left:388px;top:296px;width:200px;height:150px">移行先の構成と手順を決める</div>
  <div class="pp-line" data-arrow="end" style="left:612px;top:314px;width:56px;background:var(--accent)"></div>
  <div class="pp-shape f-light r" style="left:672px;top:170px;width:240px;height:290px"></div>
  <div class="pp-text num" style="left:692px;top:186px;width:200px;height:56px">03</div>
  <div class="pp-text b" style="left:692px;top:250px;width:200px;height:34px">移行</div>
  <div class="pp-text" style="left:692px;top:296px;width:200px;height:150px">夜間に段階的に切り替える</div>
  <div class="pp-line" data-arrow="end" style="left:916px;top:314px;width:56px;background:var(--accent)"></div>
  <div class="pp-shape f-light r" style="left:976px;top:170px;width:240px;height:290px"></div>
  <div class="pp-text num" style="left:996px;top:186px;width:200px;height:56px">04</div>
  <div class="pp-text b" style="left:996px;top:250px;width:200px;height:34px">定着</div>
  <div class="pp-text" style="left:996px;top:296px;width:200px;height:150px">運用を引き継ぎ、旧基盤を停止する</div>
  <div class="pp-shape f-accent r" style="left:64px;top:500px;width:1152px;height:90px"></div>
  <div class="pp-text t-white b" style="left:88px;top:520px;width:1104px;height:50px;font-size:22px">各段階で承認を取るため、問題があれば前の段階に戻せる</div>
  <div class="pp-text" data-role="caption" data-chrome style="left:64px;top:640px;width:900px;height:24px">出典: 移行計画書（2026年9月版）</div>
</section>
```

`tree.html`（ツリー: 1 つの根と 3 つの枝、各枝に内訳）:

```html
<!-- 用途: 分解・内訳・組織。根 → 3 つの枝 → 各枝の内訳。罫線は直角。
     差し替える所: 根・枝の名前・内訳（各 2〜3 行）。 -->
<section class="slide" data-layout="diagram">
  <div class="pp-text" data-role="title" style="height:44px">総費用は、構築・運用・移行の3つに分けて管理できる</div>
  <div class="pp-shape f-accent r" style="left:480px;top:160px;width:320px;height:64px"></div>
  <div class="pp-text t-white b center" style="left:496px;top:174px;width:288px;height:36px;font-size:22px">5年間の総費用</div>
  <div class="pp-line hr" style="left:639px;top:224px;width:2px;height:32px"></div>
  <div class="pp-line hr" style="left:224px;top:256px;width:832px"></div>
  <div class="pp-line hr" style="left:223px;top:256px;width:2px;height:36px"></div>
  <div class="pp-line hr" style="left:639px;top:256px;width:2px;height:36px"></div>
  <div class="pp-line hr" style="left:1055px;top:256px;width:2px;height:36px"></div>
  <div class="pp-shape f-light r" style="left:64px;top:292px;width:320px;height:64px"></div>
  <div class="pp-text b center" style="left:80px;top:306px;width:288px;height:36px">構築費</div>
  <div class="pp-shape f-light r" style="left:480px;top:292px;width:320px;height:64px"></div>
  <div class="pp-text b center" style="left:496px;top:306px;width:288px;height:36px">運用費</div>
  <div class="pp-shape f-light r" style="left:896px;top:292px;width:320px;height:64px"></div>
  <div class="pp-text b center" style="left:912px;top:306px;width:288px;height:36px">移行費</div>
  <div class="pp-shape f-white r" style="left:64px;top:372px;width:320px;height:200px"></div>
  <div class="pp-text" style="left:84px;top:388px;width:280px;height:170px"><ul><li>設計: 2,000万円</li><li>機器: 5,500万円</li><li>設定: 1,500万円</li></ul></div>
  <div class="pp-shape f-white r" style="left:480px;top:372px;width:320px;height:200px"></div>
  <div class="pp-text" style="left:500px;top:388px;width:280px;height:170px"><ul><li>保守: 3,000万円</li><li>監視: 1,200万円</li><li>人件費: 1,800万円</li></ul></div>
  <div class="pp-shape f-white r" style="left:896px;top:372px;width:320px;height:200px"></div>
  <div class="pp-text" style="left:916px;top:388px;width:280px;height:170px"><ul><li>データ移行: 900万円</li><li>試験: 600万円</li><li>教育: 500万円</li></ul></div>
  <div class="pp-text" data-role="caption" data-chrome style="left:64px;top:640px;width:900px;height:24px">出典: 見積書（2026年9月）。金額は5年間の合計</div>
</section>
```

`matrix.html`（2×2 マトリクス: 右上が推奨）:

```html
<!-- 用途: 2 軸で案を分類する。右上（効果が高く、負担が小さい）を推奨の象限にする。
     差し替える所: 軸の名前・各象限の見出しと一言・案の位置。 -->
<section class="slide" data-layout="diagram">
  <div class="pp-text" data-role="title" style="height:44px">効果が高く負担が小さい案は、B案だけである</div>
  <div class="pp-text t-sub right" style="left:64px;top:170px;width:120px;height:30px">効果 高</div>
  <div class="pp-text t-sub right" style="left:64px;top:560px;width:120px;height:30px">効果 低</div>
  <div class="pp-shape f-soft r" style="left:200px;top:160px;width:480px;height:212px"></div>
  <div class="pp-text b" style="left:224px;top:176px;width:432px;height:34px">効果は高いが、負担も大きい</div>
  <div class="pp-text" style="left:224px;top:216px;width:432px;height:140px">A案: 全面刷新。12か月、2.5億円</div>
  <div class="pp-shape f-accent r" style="left:696px;top:160px;width:480px;height:212px"></div>
  <div class="pp-text t-white b" style="left:720px;top:176px;width:432px;height:34px">効果が高く、負担が小さい</div>
  <div class="pp-text t-white" style="left:720px;top:216px;width:432px;height:140px">B案: 段階移行。6か月、1.7億円</div>
  <div class="pp-shape f-soft r" style="left:200px;top:388px;width:480px;height:212px"></div>
  <div class="pp-text b" style="left:224px;top:404px;width:432px;height:34px">効果が低く、負担も大きい</div>
  <div class="pp-text" style="left:224px;top:444px;width:432px;height:140px">該当なし</div>
  <div class="pp-shape f-soft r" style="left:696px;top:388px;width:480px;height:212px"></div>
  <div class="pp-text b" style="left:720px;top:404px;width:432px;height:34px">負担は小さいが、効果も低い</div>
  <div class="pp-text" style="left:720px;top:444px;width:432px;height:140px">C案: 現状維持。保守延長を含め2.2億円、リスクが残る</div>
  <div class="pp-text t-sub" style="left:200px;top:608px;width:400px;height:30px">負担 大</div>
  <div class="pp-text t-sub right" style="left:776px;top:608px;width:400px;height:30px">負担 小</div>
</section>
```

`pyramid.html`（ピラミッド: 4 層、頂点が最重要）:

```html
<!-- 用途: 階層・優先度・段階。上ほど重要。層の幅は中央をそろえて 160/320/480/640px。右に各層の説明。
     差し替える所: 層の名前（短く）・説明。 -->
<section class="slide" data-layout="diagram">
  <div class="pp-text" data-role="title" style="height:44px">判断の土台は、事実・影響・選択肢・推奨の順に積み上がる</div>
  <div class="pp-shape f-dark" style="left:320px;top:170px;width:160px;height:100px"></div>
  <div class="pp-text t-white b center" style="left:330px;top:206px;width:140px;height:30px">推奨</div>
  <div class="pp-shape f-accent" style="left:240px;top:280px;width:320px;height:100px"></div>
  <div class="pp-text t-white b center" style="left:250px;top:316px;width:300px;height:30px">選択肢</div>
  <div class="pp-shape f-mid" style="left:160px;top:390px;width:480px;height:100px"></div>
  <div class="pp-text b center" style="left:170px;top:426px;width:460px;height:30px">影響</div>
  <div class="pp-shape f-light" style="left:80px;top:500px;width:640px;height:100px"></div>
  <div class="pp-text b center" style="left:90px;top:536px;width:620px;height:30px">事実</div>
  <div class="pp-text" style="left:760px;top:196px;width:456px;height:56px">B案を採用する</div>
  <div class="pp-text" style="left:760px;top:306px;width:456px;height:56px">3案を費用・期間・リスクで比べる</div>
  <div class="pp-text" style="left:760px;top:416px;width:456px;height:56px">停止時間と業務への影響を測る</div>
  <div class="pp-text" style="left:760px;top:526px;width:456px;height:56px">保守期限・現行費用・利用状況</div>
</section>
```

`cycle.html`（サイクル: 4 段階の循環。矢印は `data-dir="rev"` で逆向き）:

```html
<!-- 用途: 繰り返しの運用（計画 → 実行 → 評価 → 改善）。左上から時計回り。戻る矢印は data-dir="rev"。
     差し替える所: 4 つの名前・説明・中央の一言。 -->
<section class="slide" data-layout="diagram">
  <div class="pp-text" data-role="title" style="height:44px">運用は、四半期ごとの見直しで継続的に改善する</div>
  <div class="pp-shape f-light r" style="left:240px;top:170px;width:360px;height:140px"></div>
  <div class="pp-text b" style="left:264px;top:184px;width:312px;height:34px">1 計画</div>
  <div class="pp-text" style="left:264px;top:224px;width:312px;height:76px">目標と指標を決める</div>
  <div class="pp-shape f-light r" style="left:680px;top:170px;width:360px;height:140px"></div>
  <div class="pp-text b" style="left:704px;top:184px;width:312px;height:34px">2 実行</div>
  <div class="pp-text" style="left:704px;top:224px;width:312px;height:76px">計画どおりに運用する</div>
  <div class="pp-shape f-light r" style="left:680px;top:450px;width:360px;height:140px"></div>
  <div class="pp-text b" style="left:704px;top:464px;width:312px;height:34px">3 評価</div>
  <div class="pp-text" style="left:704px;top:504px;width:312px;height:76px">指標と費用を確かめる</div>
  <div class="pp-shape f-light r" style="left:240px;top:450px;width:360px;height:140px"></div>
  <div class="pp-text b" style="left:264px;top:464px;width:312px;height:34px">4 改善</div>
  <div class="pp-text" style="left:264px;top:504px;width:312px;height:76px">原因を直し、次の計画に反映する</div>
  <div class="pp-line" data-arrow="end" style="left:604px;top:239px;width:72px;background:var(--accent)"></div>
  <div class="pp-line" data-arrow="end" style="left:859px;top:314px;width:2px;height:132px;background:var(--accent)"></div>
  <div class="pp-line" data-arrow="end" data-dir="rev" style="left:604px;top:519px;width:72px;background:var(--accent)"></div>
  <div class="pp-line" data-arrow="end" data-dir="rev" style="left:419px;top:314px;width:2px;height:132px;background:var(--accent)"></div>
  <div class="pp-text center t-sub" style="left:440px;top:370px;width:400px;height:30px">四半期ごとに1周</div>
</section>
```

`gantt.html`（ガント: 6 か月・5 工程・承認の判断点は強調色の ◆ を 1 つ）:

```html
<!-- 用途: 計画・スケジュール。月の列（148px × 6）に工程の棒を置く。承認を求める判断点は ◆（強調色）で 1 つだけ。
     差し替える所: 月・工程名・棒の位置（left = 320 + 148 × 開始月、width = 148 × 月数）・◆ の位置。 -->
<section class="slide" data-layout="diagram">
  <div class="pp-text" data-role="title" style="height:44px">6か月で移行を完了し、第3月に最終判断を行う</div>
  <div class="pp-shape f-soft" style="left:320px;top:160px;width:888px;height:36px"></div>
  <div class="pp-text center b" style="left:320px;top:166px;width:148px;height:26px">11月</div>
  <div class="pp-text center b" style="left:468px;top:166px;width:148px;height:26px">12月</div>
  <div class="pp-text center b" style="left:616px;top:166px;width:148px;height:26px">1月</div>
  <div class="pp-text center b" style="left:764px;top:166px;width:148px;height:26px">2月</div>
  <div class="pp-text center b" style="left:912px;top:166px;width:148px;height:26px">3月</div>
  <div class="pp-text center b" style="left:1060px;top:166px;width:148px;height:26px">4月</div>
  <div class="pp-text b" style="left:64px;top:216px;width:240px;height:36px">現状調査</div>
  <div class="pp-shape f-accent r" style="left:320px;top:218px;width:296px;height:32px"></div>
  <div class="pp-line hr" style="left:64px;top:266px;width:1144px"></div>
  <div class="pp-text b" style="left:64px;top:282px;width:240px;height:36px">設計</div>
  <div class="pp-shape f-accent r" style="left:468px;top:284px;width:296px;height:32px"></div>
  <div class="pp-line hr" style="left:64px;top:332px;width:1144px"></div>
  <div class="pp-text b" style="left:64px;top:348px;width:240px;height:36px">環境構築</div>
  <div class="pp-shape f-mid" style="left:616px;top:350px;width:296px;height:32px"></div>
  <div class="pp-line hr" style="left:64px;top:398px;width:1144px"></div>
  <div class="pp-text b" style="left:64px;top:414px;width:240px;height:36px">データ移行</div>
  <div class="pp-shape f-accent r" style="left:764px;top:416px;width:296px;height:32px"></div>
  <div class="pp-line hr" style="left:64px;top:464px;width:1144px"></div>
  <div class="pp-text b" style="left:64px;top:480px;width:240px;height:36px">試験・定着</div>
  <div class="pp-shape f-mid" style="left:912px;top:482px;width:296px;height:32px"></div>
  <div class="pp-text t-emph b center" style="left:900px;top:536px;width:40px;height:34px;font-size:24px">◆</div>
  <div class="pp-text" style="left:944px;top:536px;width:264px;height:34px">3月: 最終判断</div>
  <div class="pp-text" data-role="caption" data-chrome style="left:64px;top:640px;width:900px;height:24px">出典: 移行計画書（2026年9月版）。◆は承認を求める判断点</div>
</section>
```

`venn.html`（ベン図: 2 つの円。重なりが主役）:

```html
<!-- 用途: 2 つの集合の重なり（共通点・両立する条件）。重なりの文言だけを太字にする。
     円は半透明（color-mix）。重なる要素には data-overlap を両方に付ける。
     差し替える所: 2 つの集合の名前・それぞれだけの特徴・重なり・右の説明。 -->
<section class="slide" data-layout="diagram">
  <div class="pp-text" data-role="title" style="height:44px">必要な要件を満たす案は、2つの条件が重なるB案だけである</div>
  <div class="pp-shape" data-shape="ellipse" data-overlap style="left:80px;top:170px;width:400px;height:400px;background:color-mix(in srgb, var(--accent) 35%, transparent)"></div>
  <div class="pp-shape" data-shape="ellipse" data-overlap style="left:340px;top:170px;width:400px;height:400px;background:color-mix(in srgb, var(--accent-dark) 35%, transparent)"></div>
  <div class="pp-text b center" style="left:100px;top:230px;width:220px;height:34px">費用が低い</div>
  <div class="pp-text center" style="left:100px;top:290px;width:220px;height:100px">C案、B案</div>
  <div class="pp-text b center" style="left:500px;top:230px;width:220px;height:34px">期間が短い</div>
  <div class="pp-text center" style="left:500px;top:290px;width:220px;height:100px">A案、B案</div>
  <div class="pp-text b center" style="left:340px;top:330px;width:140px;height:60px">B案</div>
  <div class="pp-text b" style="left:800px;top:196px;width:416px;height:34px">読み方</div>
  <div class="pp-text" style="left:800px;top:240px;width:416px;height:200px"><ul><li>左: 総費用が現行以下</li><li>右: 12か月以内に完了</li><li>重なり: 両方を満たす案</li></ul></div>
</section>
```

`before-after.html`（ビフォーアフター: 左が現状、右が導入後、下に結論の帯）:

```html
<!-- 用途: 導入前後・現状と目標の比較。項目ごとに「前の値 → 後の値」。後の値だけ基調色の大きな数字。
     差し替える所: 項目名・前後の値・結論。 -->
<section class="slide" data-layout="diagram">
  <div class="pp-text" data-role="title" style="height:44px">導入後は、障害対応が月40時間から8時間に減る</div>
  <div class="pp-shape f-soft r" style="left:64px;top:160px;width:520px;height:400px"></div>
  <div class="pp-text b" style="left:88px;top:176px;width:472px;height:34px">現状</div>
  <div class="pp-text" data-role="caption" style="left:88px;top:230px;width:472px;height:22px">障害対応（月）</div>
  <div class="pp-text" data-role="display" style="left:88px;top:256px;width:472px;height:56px">40時間</div>
  <div class="pp-text" data-role="caption" style="left:88px;top:336px;width:472px;height:22px">停止回数（年）</div>
  <div class="pp-text" data-role="display" style="left:88px;top:362px;width:472px;height:56px">6回</div>
  <div class="pp-text" data-role="caption" style="left:88px;top:442px;width:472px;height:22px">運用費（年）</div>
  <div class="pp-text" data-role="display" style="left:88px;top:468px;width:472px;height:56px">4,200万円</div>
  <div class="pp-line" data-arrow="end" style="left:596px;top:360px;width:88px;background:var(--accent)"></div>
  <div class="pp-shape f-light r" style="left:696px;top:160px;width:520px;height:400px"></div>
  <div class="pp-text b" style="left:720px;top:176px;width:472px;height:34px">導入後</div>
  <div class="pp-text" data-role="caption" style="left:720px;top:230px;width:472px;height:22px">障害対応（月）</div>
  <div class="pp-text num" style="left:720px;top:256px;width:472px;height:56px">8時間</div>
  <div class="pp-text" data-role="caption" style="left:720px;top:336px;width:472px;height:22px">停止回数（年）</div>
  <div class="pp-text num" style="left:720px;top:362px;width:472px;height:56px">1回</div>
  <div class="pp-text" data-role="caption" style="left:720px;top:442px;width:472px;height:22px">運用費（年）</div>
  <div class="pp-text num" style="left:720px;top:468px;width:472px;height:56px">2,900万円</div>
  <div class="pp-text" data-role="caption" data-chrome style="left:64px;top:640px;width:900px;height:24px">出典: 社内運用実績（2025年度）と見積り。導入後は試算値</div>
</section>
```

`layers.html`（階層・レイヤー: 4 層を縦に重ねる）:

```html
<!-- 用途: システム構成・責任範囲の階層。左に層の名前（色面）、右に中身。上から利用者 → 業務 → 基盤 → 設備。
     差し替える所: 層の名前・中身。 -->
<section class="slide" data-layout="diagram">
  <div class="pp-text" data-role="title" style="height:44px">移行するのは基盤の層だけで、業務アプリは変更しない</div>
  <div class="pp-shape f-soft r" style="left:64px;top:160px;width:220px;height:88px"></div>
  <div class="pp-text b center" style="left:74px;top:190px;width:200px;height:30px">利用者</div>
  <div class="pp-shape f-soft r" style="left:296px;top:160px;width:920px;height:88px"></div>
  <div class="pp-text" style="left:320px;top:184px;width:872px;height:44px">社内の約800人。利用方法は変わらない</div>
  <div class="pp-shape f-soft r" style="left:64px;top:262px;width:220px;height:88px"></div>
  <div class="pp-text b center" style="left:74px;top:292px;width:200px;height:30px">業務アプリ</div>
  <div class="pp-shape f-soft r" style="left:296px;top:262px;width:920px;height:88px"></div>
  <div class="pp-text" style="left:320px;top:286px;width:872px;height:44px">販売管理・会計など12システム。変更なし</div>
  <div class="pp-shape f-accent r" style="left:64px;top:364px;width:220px;height:88px"></div>
  <div class="pp-text t-white b center" style="left:74px;top:394px;width:200px;height:30px">基盤</div>
  <div class="pp-shape f-light r" style="left:296px;top:364px;width:920px;height:88px"></div>
  <div class="pp-text b" style="left:320px;top:388px;width:872px;height:44px">サーバー・ストレージ・ネットワーク。今回の移行対象</div>
  <div class="pp-shape f-soft r" style="left:64px;top:466px;width:220px;height:88px"></div>
  <div class="pp-text b center" style="left:74px;top:496px;width:200px;height:30px">設備</div>
  <div class="pp-shape f-soft r" style="left:296px;top:466px;width:920px;height:88px"></div>
  <div class="pp-text" style="left:320px;top:490px;width:872px;height:44px">データセンター。契約を更新し、そのまま使う</div>
</section>
```

`compare.html`（項目比較: 3 案を縦の列で。推奨は強調色の見出し 1 つ）:

```html
<!-- 用途: 3 案の比較。各案に見出し・大きな数字・要点。推奨案の見出しだけ強調色。
     差し替える所: 案の名前・数字・要点・推奨の案（強調色にする列）。 -->
<section class="slide" data-layout="diagram">
  <div class="pp-text" data-role="title" style="height:44px">3案のうち、費用と期間のバランスが取れているのはB案である</div>
  <div class="pp-shape f-dark r" style="left:64px;top:160px;width:368px;height:64px"></div>
  <div class="pp-text t-white b center" style="left:80px;top:174px;width:336px;height:36px;font-size:22px">A案: 全面刷新</div>
  <div class="pp-shape f-white r" style="left:64px;top:232px;width:368px;height:360px"></div>
  <div class="pp-text num" style="left:84px;top:248px;width:328px;height:56px">2.5億円</div>
  <div class="pp-text" style="left:84px;top:316px;width:328px;height:260px"><ul><li>期間: 12か月</li><li>停止: 3回</li><li>リスク: 大</li></ul></div>
  <div class="pp-shape f-emph r" style="left:456px;top:160px;width:368px;height:64px"></div>
  <div class="pp-text t-white b center" style="left:472px;top:174px;width:336px;height:36px;font-size:22px">B案: 段階移行（推奨）</div>
  <div class="pp-shape f-white r" style="left:456px;top:232px;width:368px;height:360px"></div>
  <div class="pp-text num" style="left:476px;top:248px;width:328px;height:56px">1.7億円</div>
  <div class="pp-text" style="left:476px;top:316px;width:328px;height:260px"><ul><li>期間: 6か月</li><li>停止: 1回</li><li>リスク: 中</li></ul></div>
  <div class="pp-shape f-dark r" style="left:848px;top:160px;width:368px;height:64px"></div>
  <div class="pp-text t-white b center" style="left:864px;top:174px;width:336px;height:36px;font-size:22px">C案: 現状維持</div>
  <div class="pp-shape f-white r" style="left:848px;top:232px;width:368px;height:360px"></div>
  <div class="pp-text num" style="left:868px;top:248px;width:328px;height:56px">2.2億円</div>
  <div class="pp-text" style="left:868px;top:316px;width:328px;height:260px"><ul><li>期間: なし</li><li>停止: なし</li><li>リスク: 保守延長が必要</li></ul></div>
  <div class="pp-text" data-role="caption" data-chrome style="left:64px;top:640px;width:900px;height:24px">出典: 見積書（2026年9月）。費用は5年間の総額</div>
</section>
```

- [ ] **Step 2: テストを実行する**

Run: `"$PY" -m pytest tests/test_components.py -k diagrams`
Expected: 10 枚 × 2 配色がすべて PASS。落ちたら、メッセージに従って断片を直す。よくあるもの:
- `venn`: 円と円・文字と円の `overlap`。円には `data-overlap` が付いている。文字が円の外枠（rect）に完全に含まれていない場合は、`left/width` を円の内側に収める。
- `cycle`・`flow-h`: 矢印は `pp-line`（重なり検査の対象外）。
- 明るい黄色（`#FFFF00`）の配色で、`t-white` の面の `contrast` が落ちる場合は、`theme.derive` が基調色を暗くする（計画 A の Task 2）ので落ちないはず。落ちたら `derive` の不具合として計画 A に戻る。
- `before-after`: `data-role="display"` は 40px 太字で `var(--text)`。

- [ ] **Step 3: 目で確認する**

`final.html` に 10 枚の断片を連結して `build` し、PNG を Read で開く。確認点: ① 矢印が正しい向き（`cycle` の戻りが逆向き）② `venn` の円が半透明で重なりが見える（PPTX で透過が効いている。LibreOffice の画像で確認）③ `gantt` の棒と ◆ が列に合っている ④ 強調色が 1 スライドに 1 点。

- [ ] **Step 4: コミット**

```bash
git add skills/pptx-deck
git commit -m "feat: 図解の断片 10 種（フロー・ツリー・マトリクス・ピラミッド・サイクル・ガント・ベン図・ビフォーアフター・階層・項目比較）を追加"
```

---

### Task 4: 表の断片 4 種

**Files:**
- Create: `skills/pptx-deck/assets/components/tables/{compare,rating,cost,schedule}.html`

**Interfaces:**
- Consumes: Task 1 の基盤。表は `<table class="pp-table">`。セルの文字は `td`／`th` の直下（`<p>` を使わない）。行は罫線（`border-bottom`）で区切り、縦線は引かない。

- [ ] **Step 1: 断片を書く**

`compare.html`（比較表: 項目 × 3 案。推奨の列の見出しだけ強調色）:

```html
<!-- 用途: 3 案の比較表。項目を行、案を列にする。推奨案の列見出しだけ強調色。罫線は行の区切りだけ。
     差し替える所: 項目・案の名前・値・推奨の列。行数は 5〜6 まで。 -->
<section class="slide" data-layout="table">
  <div class="pp-text" data-role="title" style="height:44px">B案は、費用・期間・リスクの3項目で最も釣り合っている</div>
  <table class="pp-table" style="left:64px;top:160px;width:1152px;font-size:20px">
    <tr style="height:56px">
      <td style="width:252px;padding:12px 16px;background:var(--bg-soft);font-weight:700">項目</td>
      <td style="width:300px;padding:12px 16px;background:var(--accent-dark);color:#FFFFFF;font-weight:700">A案: 全面刷新</td>
      <td style="width:300px;padding:12px 16px;background:var(--emphasis);color:#FFFFFF;font-weight:700">B案: 段階移行（推奨）</td>
      <td style="width:300px;padding:12px 16px;background:var(--accent-dark);color:#FFFFFF;font-weight:700">C案: 現状維持</td>
    </tr>
    <tr style="height:56px">
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);font-weight:700">総費用（5年）</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line)">2.5億円</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);font-weight:700">1.7億円</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line)">2.2億円（保守延長を含む）</td>
    </tr>
    <tr style="height:56px">
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);font-weight:700">期間</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line)">12か月</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);font-weight:700">6か月</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line)">なし</td>
    </tr>
    <tr style="height:56px">
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);font-weight:700">業務停止</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line)">3回</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);font-weight:700">1回（夜間）</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line)">保守切れで長期停止の恐れ</td>
    </tr>
    <tr style="height:56px">
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);font-weight:700">主なリスク</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line)">工期の遅れ</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);font-weight:700">段階間の整合</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line)">2028年に保守が切れる</td>
    </tr>
  </table>
  <div class="pp-text" data-role="caption" data-chrome style="left:64px;top:640px;width:900px;height:24px">出典: 見積書（2026年9月）。費用は5年間の総額</div>
</section>
```

`rating.html`（評価表: 記号 ◎○△。記号は 24px 以上の大きさ）:

```html
<!-- 用途: 評価軸 × 案の評価表。◎（優れる）○（良い）△（劣る）を使う。凡例を下に置く。
     差し替える所: 評価軸・案・記号・総合の行。 -->
<section class="slide" data-layout="table">
  <div class="pp-text" data-role="title" style="height:44px">5つの評価軸のうち4つで、B案が上位である</div>
  <table class="pp-table" style="left:64px;top:160px;width:1152px;font-size:20px">
    <tr style="height:56px">
      <td style="width:372px;padding:12px 16px;background:var(--bg-soft);font-weight:700">評価軸</td>
      <td style="width:260px;padding:12px 16px;background:var(--accent-dark);color:#FFFFFF;font-weight:700;text-align:center">A案</td>
      <td style="width:260px;padding:12px 16px;background:var(--emphasis);color:#FFFFFF;font-weight:700;text-align:center">B案（推奨）</td>
      <td style="width:260px;padding:12px 16px;background:var(--accent-dark);color:#FFFFFF;font-weight:700;text-align:center">C案</td>
    </tr>
    <tr style="height:56px">
      <td style="padding:12px 16px;border-bottom:1px solid var(--line)">費用</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);text-align:center;font-size:24px">△</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);text-align:center;font-size:24px;font-weight:700">○</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);text-align:center;font-size:24px">◎</td>
    </tr>
    <tr style="height:56px">
      <td style="padding:12px 16px;border-bottom:1px solid var(--line)">期間</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);text-align:center;font-size:24px">△</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);text-align:center;font-size:24px;font-weight:700">◎</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);text-align:center;font-size:24px">◎</td>
    </tr>
    <tr style="height:56px">
      <td style="padding:12px 16px;border-bottom:1px solid var(--line)">業務への影響</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);text-align:center;font-size:24px">△</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);text-align:center;font-size:24px;font-weight:700">◎</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);text-align:center;font-size:24px">△</td>
    </tr>
    <tr style="height:56px">
      <td style="padding:12px 16px;border-bottom:1px solid var(--line)">将来の拡張性</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);text-align:center;font-size:24px">◎</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);text-align:center;font-size:24px;font-weight:700">○</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);text-align:center;font-size:24px">△</td>
    </tr>
    <tr style="height:56px">
      <td style="padding:12px 16px;font-weight:700">総合</td>
      <td style="padding:12px 16px;text-align:center;font-size:24px">○</td>
      <td style="padding:12px 16px;text-align:center;font-size:24px;font-weight:700">◎</td>
      <td style="padding:12px 16px;text-align:center;font-size:24px">△</td>
    </tr>
  </table>
  <div class="pp-text" data-role="caption" style="left:64px;top:560px;width:900px;height:24px">◎ 優れる　○ 良い　△ 劣る</div>
  <div class="pp-text" data-role="caption" data-chrome style="left:64px;top:640px;width:900px;height:24px">出典: 評価会議の採点（2026年9月、5名の平均）</div>
</section>
```

`cost.html`（費用表: 数字は右寄せ、合計行は太字で上に太い罫線）:

```html
<!-- 用途: 費用の内訳。数字は右寄せで桁をそろえ、単位は見出しに書く。合計の行は太字で、上に太い罫線。
     差し替える所: 費目・年度・金額・合計。 -->
<section class="slide" data-layout="table">
  <div class="pp-text" data-role="title" style="height:44px">B案の総費用は5年間で1.7億円、初年度に約7割が集中する</div>
  <table class="pp-table" style="left:64px;top:160px;width:1152px;font-size:20px">
    <tr style="height:56px">
      <td style="width:352px;padding:12px 16px;background:var(--bg-soft);font-weight:700">費目（万円）</td>
      <td style="width:160px;padding:12px 16px;background:var(--bg-soft);font-weight:700;text-align:right">2027年度</td>
      <td style="width:160px;padding:12px 16px;background:var(--bg-soft);font-weight:700;text-align:right">2028年度</td>
      <td style="width:160px;padding:12px 16px;background:var(--bg-soft);font-weight:700;text-align:right">2029年度</td>
      <td style="width:160px;padding:12px 16px;background:var(--bg-soft);font-weight:700;text-align:right">2030年度</td>
      <td style="width:160px;padding:12px 16px;background:var(--bg-soft);font-weight:700;text-align:right">2031年度</td>
    </tr>
    <tr style="height:56px">
      <td style="padding:12px 16px;border-bottom:1px solid var(--line)">構築</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);text-align:right">9,000</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);text-align:right">0</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);text-align:right">0</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);text-align:right">0</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);text-align:right">0</td>
    </tr>
    <tr style="height:56px">
      <td style="padding:12px 16px;border-bottom:1px solid var(--line)">運用</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);text-align:right">1,200</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);text-align:right">1,200</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);text-align:right">1,200</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);text-align:right">1,200</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);text-align:right">1,200</td>
    </tr>
    <tr style="height:56px">
      <td style="padding:12px 16px;border-bottom:1px solid var(--line)">移行</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);text-align:right">2,000</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);text-align:right">0</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);text-align:right">0</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);text-align:right">0</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);text-align:right">0</td>
    </tr>
    <tr style="height:56px">
      <td style="padding:12px 16px;border-top:3px solid var(--text);font-weight:700">合計</td>
      <td style="padding:12px 16px;border-top:3px solid var(--text);font-weight:700;text-align:right">12,200</td>
      <td style="padding:12px 16px;border-top:3px solid var(--text);font-weight:700;text-align:right">1,200</td>
      <td style="padding:12px 16px;border-top:3px solid var(--text);font-weight:700;text-align:right">1,200</td>
      <td style="padding:12px 16px;border-top:3px solid var(--text);font-weight:700;text-align:right">1,200</td>
      <td style="padding:12px 16px;border-top:3px solid var(--text);font-weight:700;text-align:right">1,200</td>
    </tr>
  </table>
  <div class="pp-text" data-role="caption" data-chrome style="left:64px;top:640px;width:900px;height:24px">出典: 見積書（2026年9月）。単位は万円、税抜</div>
</section>
```

`schedule.html`（スケジュール表: 工程 × 月。実施の月は薄い面、判断点は ◆）:

```html
<!-- 用途: 工程 × 月の予定表。実施の月を薄い面で塗り、承認の判断点だけ ◆（強調色）にする。
     差し替える所: 工程・月・塗る月・◆ の位置。 -->
<section class="slide" data-layout="table">
  <div class="pp-text" data-role="title" style="height:44px">工程は6か月に収まり、承認は第3月の1回だけである</div>
  <table class="pp-table" style="left:64px;top:160px;width:1152px;font-size:20px">
    <tr style="height:56px">
      <td style="width:312px;padding:12px 16px;background:var(--bg-soft);font-weight:700">工程</td>
      <td style="width:140px;padding:12px 16px;background:var(--bg-soft);font-weight:700;text-align:center">11月</td>
      <td style="width:140px;padding:12px 16px;background:var(--bg-soft);font-weight:700;text-align:center">12月</td>
      <td style="width:140px;padding:12px 16px;background:var(--bg-soft);font-weight:700;text-align:center">1月</td>
      <td style="width:140px;padding:12px 16px;background:var(--bg-soft);font-weight:700;text-align:center">2月</td>
      <td style="width:140px;padding:12px 16px;background:var(--bg-soft);font-weight:700;text-align:center">3月</td>
      <td style="width:140px;padding:12px 16px;background:var(--bg-soft);font-weight:700;text-align:center">4月</td>
    </tr>
    <tr style="height:56px">
      <td style="padding:12px 16px;border-bottom:1px solid var(--line)">現状調査</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);background:var(--accent-mid)"></td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);background:var(--accent-mid)"></td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line)"></td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line)"></td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line)"></td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line)"></td>
    </tr>
    <tr style="height:56px">
      <td style="padding:12px 16px;border-bottom:1px solid var(--line)">設計・構築</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line)"></td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);background:var(--accent-mid)"></td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);background:var(--accent-mid)"></td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line)"></td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line)"></td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line)"></td>
    </tr>
    <tr style="height:56px">
      <td style="padding:12px 16px;border-bottom:1px solid var(--line)">データ移行</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line)"></td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line)"></td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line)"></td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);background:var(--accent-mid)"></td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);background:var(--accent-mid)"></td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line)"></td>
    </tr>
    <tr style="height:56px">
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);font-weight:700">最終判断（承認）</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line)"></td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line)"></td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line)"></td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line)"></td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line);text-align:center;color:var(--emphasis);font-size:24px;font-weight:700">◆</td>
      <td style="padding:12px 16px;border-bottom:1px solid var(--line)"></td>
    </tr>
    <tr style="height:56px">
      <td style="padding:12px 16px">試験・定着</td>
      <td style="padding:12px 16px"></td>
      <td style="padding:12px 16px"></td>
      <td style="padding:12px 16px"></td>
      <td style="padding:12px 16px"></td>
      <td style="padding:12px 16px;background:var(--accent-mid)"></td>
      <td style="padding:12px 16px;background:var(--accent-mid)"></td>
    </tr>
  </table>
  <div class="pp-text" data-role="caption" data-chrome style="left:64px;top:640px;width:900px;height:24px">出典: 移行計画書（2026年9月版）。◆は承認を求める判断点</div>
</section>
```

- [ ] **Step 2: テストを実行する**

Run: `"$PY" -m pytest tests/test_components.py -k tables`
Expected: 4 枚 × 2 配色が PASS。落ちたときの典型: ① 空セルの `paras` が空配列（`runsOf` が空）→ `build.add_table` の `fill_text_frame` は空の段落でも動く（何も追加しない）が、`cell.text_frame` に空の段落が 1 つ残るのは正常 ② 明るい黄色の配色で、`th` 相当のセル（`color:#FFFFFF` on `var(--emphasis)`）の `contrast` が落ちる場合は、`emphasis` の候補が白に対して 4.5:1 以上（計画 A の Task 2）なので落ちないはず ③ 表の `table_height` が領域を超える場合は、行数か `height` を減らす。

- [ ] **Step 3: 目で確認する**

PNG を Read で開く。確認点: ① 縦線がなく、行の罫線だけがある ② 合計行の上に太い罫線 ③ 数字が右寄せで桁がそろう ④ 推奨列の見出しだけが強調色 ⑤ PowerPoint の表として編集できる（`python-pptx` で `has_table` を確認済みのテストが Task 5（計画 A）にある）。

- [ ] **Step 4: コミット**

```bash
git add skills/pptx-deck
git commit -m "feat: 表の断片 4 種（比較・評価・費用・スケジュール）を追加"
```

---

### Task 5: グラフの断片 5 種とブラウザ用プレビュー

**Files:**
- Create: `skills/pptx-deck/assets/web/chart-preview.js`
- Create: `skills/pptx-deck/assets/components/charts/{bar,line,stacked,waterfall,pie}.html`
- Test: `skills/pptx-deck/tests/test_chart_preview.py`

**Interfaces:**
- Consumes: `data-chart`（計画 A の Task 6 のグラフ指定）。`init` が `chart-preview.js` を作業フォルダに写す（計画 A の Task 9）。
- Produces: `chart-preview.js` は、`DOMContentLoaded` で `.pp-chart` ごとに `<svg>` を差し込む（PowerPoint のグラフの近似）。`window.__chartPreview(el)` を公開する（テスト用）。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_chart_preview.py`:

```python
import json
from pathlib import Path

import pytest

from pptx_deck import paths

JS = paths.ASSETS / "web" / "chart-preview.js"

SPECS = {
    "bar": {"type": "bar", "categories": ["現行", "A案", "B案"], "series": [{"name": "費用", "values": [120, 90, 60]}], "highlight": 2},
    "barh": {"type": "barh", "categories": ["現行", "A案"], "series": [{"name": "費用", "values": [120, 90]}]},
    "line": {"type": "line", "categories": ["1月", "2月", "3月"], "series": [{"name": "A", "values": [1, 3, 2]}, {"name": "B", "values": [2, 2, 4]}]},
    "stacked": {"type": "stacked", "categories": ["2027", "2028"], "series": [{"name": "構築", "values": [9, 0]}, {"name": "運用", "values": [3, 3]}]},
    "stacked100": {"type": "stacked100", "categories": ["A", "B"], "series": [{"name": "x", "values": [1, 3]}, {"name": "y", "values": [3, 1]}]},
    "waterfall": {"type": "waterfall", "categories": ["現行", "削減", "追加", "B案"], "series": [{"name": "費用", "values": [120, -40, 10, 90]}], "totals": [0, 3]},
    "pie": {"type": "pie", "categories": ["構築", "運用", "移行"], "series": [{"name": "比率", "values": [50, 30, 20]}], "highlight": 0},
    "one_point": {"type": "bar", "categories": ["A"], "series": [{"name": "x", "values": [5]}]},
    "negative": {"type": "bar", "categories": ["A", "B"], "series": [{"name": "x", "values": [-5, 3]}]},
    "long_label": {"type": "bar", "categories": ["とても長い項目名がここに入る場合"], "series": [{"name": "x", "values": [5]}]},
}


@pytest.mark.parametrize("name", SPECS)
def test_preview_draws_svg_without_errors(name, tmp_path):
    from playwright.sync_api import sync_playwright
    html = tmp_path / "p.html"
    html.write_text(
        '<!doctype html><meta charset="utf-8"><style>:root{--accent:#1F3A5F;--accent-mid:#8A9AB0;--accent-dark:#142640;'
        '--emphasis:#B85A0B;--text:#1A1A1A}.pp-chart{position:relative;width:600px;height:360px}</style>'
        f"<div class='pp-chart' data-chart='{json.dumps(SPECS[name], ensure_ascii=False)}'></div>"
        f"<script>{JS.read_text(encoding='utf-8')}</script>", encoding="utf-8")
    errors = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(html.as_uri())
        n_rect = pg.evaluate("document.querySelectorAll('.pp-chart svg rect, .pp-chart svg path, .pp-chart svg polyline').length")
        b.close()
    assert errors == []
    assert n_rect >= 1


def test_preview_does_not_touch_measured_classes(tmp_path):
    # プレビューは pp-* クラスを持つ要素を増やさない（計測に混ざらないように）
    assert "pp-" not in JS.read_text(encoding="utf-8").replace(".pp-chart", "").replace("pp-chart", "")
```

- [ ] **Step 2: 失敗を確認する**

Run: `"$PY" -m pytest tests/test_chart_preview.py`
Expected: FAIL（`chart-preview.js` がない）

- [ ] **Step 3: プレビューを書く**

`assets/web/chart-preview.js`（PowerPoint のグラフの近似。色は CSS 変数から取る）:

```javascript
/* グラフのブラウザ用プレビュー（近似）。実際のグラフは PowerPoint のネイティブグラフで出る。 */
(function () {
  var NS = 'http://www.w3.org/2000/svg';
  var css = function (n) { return getComputedStyle(document.documentElement).getPropertyValue(n).trim() || '#333'; };
  var el = function (t, a, p) {
    var e = document.createElementNS(NS, t);
    for (var k in a) e.setAttribute(k, a[k]);
    if (p) p.appendChild(e);
    return e;
  };
  var txt = function (p, x, y, s, o) {
    o = o || {};
    var t = el('text', { x: x, y: y, 'font-size': o.size || 14, 'text-anchor': o.anchor || 'middle',
      fill: o.fill || css('--text'), 'font-weight': o.bold ? 700 : 400 }, p);
    t.textContent = s;
    return t;
  };
  var nice = function (v) {
    if (v <= 0) return 1;
    var p = Math.pow(10, Math.floor(Math.log10(v))), m = v / p;
    return (m <= 1 ? 1 : m <= 2 ? 2 : m <= 5 ? 5 : 10) * p;
  };
  var fmt = function (v) { return Math.round(v * 10) / 10 + ''; };
  var palette = function () {
    return [css('--accent'), css('--accent-mid'), '#8C8C8C', css('--accent-dark'), '#BFBFBF'];
  };

  function stacks(spec) {
    var n = spec.categories.length, S = spec.series;
    if (spec.type === 'waterfall') {
      var vals = S[0].values, tot = {}, run = 0;
      (spec.totals || [0, n - 1]).forEach(function (i) { tot[i] = 1; });
      return vals.map(function (v, i) {
        if (tot[i]) { run = v; return [{ lo: 0, hi: v, v: v, color: '#767676' }]; }
        if (v >= 0) { var a = [{ lo: run, hi: run + v, v: v, color: css('--accent') }]; run += v; return a; }
        var b = [{ lo: run + v, hi: run, v: -v, color: '#404040' }]; run += v; return b;
      });
    }
    var pal = palette(), stacked = spec.type.indexOf('stacked') === 0;
    return spec.categories.map(function (_, i) {
      if (!stacked) return S.map(function (s, j) {
        var hl = j === 0 && spec.highlight === i;
        return { lo: 0, hi: s.values[i], v: s.values[i], j: j, n: S.length, color: hl ? css('--emphasis') : pal[j % 5] };
      });
      var acc = 0, d = spec.type === 'stacked100' ? S.reduce(function (a, s) { return a + s.values[i]; }, 0) / 100 || 1 : 1;
      return S.map(function (s, j) {
        var v = s.values[i] / d, r = { lo: acc, hi: acc + v, v: s.values[i], color: pal[j % 5] };
        acc += v; return r;
      });
    });
  }

  function legend(svg, spec, W, H) {
    if (spec.series.length < 2 || spec.type === 'waterfall') return;
    var pal = palette(), x = 56;
    spec.series.forEach(function (s, j) {
      el('rect', { x: x, y: H - 18, width: 12, height: 12, fill: pal[j % 5] }, svg);
      txt(svg, x + 18, H - 7, s.name, { anchor: 'start', size: 13 });
      x += 30 + s.name.length * 14;
    });
  }

  function columns(svg, spec, W, H, horizontal) {
    var L = 56, R = 16, T = 24, B = spec.series.length > 1 && spec.type !== 'waterfall' ? 56 : 40;
    var pw = W - L - R, ph = H - T - B, st = stacks(spec);
    var lo = 0, hi = 0;
    st.forEach(function (c) { c.forEach(function (b) { lo = Math.min(lo, b.lo, b.hi); hi = Math.max(hi, b.lo, b.hi); }); });
    hi = spec.type === 'stacked100' ? 100 : nice(hi);
    var range = hi - lo || 1, n = st.length, slot = (horizontal ? ph : pw) / n;
    var pos = function (v) { return (v - lo) / range * (horizontal ? pw : ph); };
    el('line', horizontal ? { x1: L + pos(0), y1: T, x2: L + pos(0), y2: T + ph, stroke: '#BFBFBF' }
      : { x1: L, y1: T + ph - pos(0), x2: L + pw, y2: T + ph - pos(0), stroke: '#BFBFBF' }, svg);
    st.forEach(function (c, i) {
      c.forEach(function (b) {
        var k = b.n || 1, w = slot * 0.62 / k, off = slot * 0.19 + (b.j || 0) * w;
        var a = pos(Math.min(b.lo, b.hi)), len = Math.abs(pos(b.hi) - pos(b.lo));
        if (horizontal) el('rect', { x: L + a, y: T + i * slot + off, width: len, height: w, fill: b.color }, svg);
        else el('rect', { x: L + i * slot + off, y: T + ph - a - len, width: w, height: len, fill: b.color }, svg);
        if (horizontal) txt(svg, L + a + len + 6, T + i * slot + off + w / 2 + 5, fmt(b.v), { anchor: 'start', size: 13 });
        else txt(svg, L + i * slot + off + w / 2, T + ph - a - len - 6, fmt(b.v), { size: 13 });
      });
      var label = spec.categories[i];
      if (horizontal) txt(svg, L - 8, T + i * slot + slot / 2 + 5, label, { anchor: 'end', size: 13 });
      else txt(svg, L + i * slot + slot / 2, T + ph + 20, label.length > 8 ? label.slice(0, 7) + '…' : label, { size: 13 });
    });
    legend(svg, spec, W, H);
  }

  function line(svg, spec, W, H) {
    var L = 56, R = 16, T = 24, B = spec.series.length > 1 ? 56 : 40, pw = W - L - R, ph = H - T - B, pal = palette();
    var all = [].concat.apply([], spec.series.map(function (s) { return s.values; }));
    var lo = Math.min(0, Math.min.apply(null, all)), hi = nice(Math.max.apply(null, all)), range = hi - lo || 1;
    var n = spec.categories.length, step = n > 1 ? pw / (n - 1) : 0;
    spec.series.forEach(function (s, j) {
      var pts = s.values.map(function (v, i) { return (L + (n > 1 ? i * step : pw / 2)) + ',' + (T + ph - (v - lo) / range * ph); });
      el('polyline', { points: pts.join(' '), fill: 'none', stroke: pal[j % 5], 'stroke-width': 3 }, svg);
      s.values.forEach(function (v, i) { el('circle', { cx: L + (n > 1 ? i * step : pw / 2), cy: T + ph - (v - lo) / range * ph, r: 4, fill: pal[j % 5] }, svg); });
    });
    spec.categories.forEach(function (c, i) { txt(svg, L + (n > 1 ? i * step : pw / 2), T + ph + 20, c, { size: 13 }); });
    legend(svg, spec, W, H);
  }

  function pie(svg, spec, W, H) {
    var cx = W / 2, cy = H / 2 - 10, r = Math.min(W, H) / 2 - 40, v = spec.series[0].values;
    var sum = v.reduce(function (a, b) { return a + b; }, 0) || 1, a0 = -Math.PI / 2, pal = palette();
    v.forEach(function (x, i) {
      var a1 = a0 + x / sum * Math.PI * 2, large = a1 - a0 > Math.PI ? 1 : 0;
      var d = 'M' + cx + ',' + cy + ' L' + (cx + r * Math.cos(a0)) + ',' + (cy + r * Math.sin(a0)) +
        ' A' + r + ',' + r + ' 0 ' + large + ' 1 ' + (cx + r * Math.cos(a1)) + ',' + (cy + r * Math.sin(a1)) + ' Z';
      el('path', { d: d, fill: spec.highlight === i ? css('--emphasis') : pal[i % 5], stroke: '#fff', 'stroke-width': 2 }, svg);
      var am = (a0 + a1) / 2;
      txt(svg, cx + r * 0.62 * Math.cos(am), cy + r * 0.62 * Math.sin(am) + 5, fmt(x), { size: 14, fill: '#fff', bold: true });
      a0 = a1;
    });
    var x = 40;
    spec.categories.forEach(function (c, i) {
      el('rect', { x: x, y: H - 18, width: 12, height: 12, fill: pal[i % 5] }, svg);
      txt(svg, x + 18, H - 7, c, { anchor: 'start', size: 13 });
      x += 30 + c.length * 14;
    });
  }

  function draw(host) {
    var spec = JSON.parse(host.dataset.chart);
    host.querySelectorAll('svg').forEach(function (s) { s.remove(); });
    var W = host.clientWidth || 600, H = host.clientHeight || 360;
    var svg = el('svg', { width: W, height: H, viewBox: '0 0 ' + W + ' ' + H, style: 'position:absolute;left:0;top:0' }, host);
    svg.setAttribute('font-family', "'BIZ UDPGothic','Yu Gothic','Meiryo',sans-serif");
    if (spec.type === 'line') line(svg, spec, W, H);
    else if (spec.type === 'pie') pie(svg, spec, W, H);
    else columns(svg, spec, W, H, spec.type === 'barh');
  }

  window.__chartPreview = draw;
  var run = function () { document.querySelectorAll('.pp-chart').forEach(draw); };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run); else run();
})();
```

注: テストの `test_preview_does_not_touch_measured_classes` は、JS が `pp-chart` 以外の `pp-` クラスを持つ要素を作らないことの確認。`<svg>` 内の要素は `pp-*` クラスを持たないので計測に混ざらない。`stacks` の一部の定義が長いため、テストが落ちたら、ブラウザのコンソールのエラーを `pageerror` の内容から読んで直す。

- [ ] **Step 4: グラフの断片を書く**

右側に所見を置く共通の形。数字には出典を付ける。

`charts/bar.html`:

```html
<!-- 用途: 案どうし・期間どうしの量の比較（縦棒）。注目する 1 本だけ強調色（highlight は 0 始まりの番号）。
     差し替える所: data-chart の categories / series / highlight・右の所見・出典。 -->
<section class="slide" data-layout="chart">
  <div class="pp-text" data-role="title" style="height:44px">B案の総費用は1.7億円で、A案より8,000万円低い</div>
  <div class="pp-chart" data-chart='{"type":"bar","categories":["現行維持（C案）","A案","B案"],"series":[{"name":"総費用（万円）","values":[22000,25000,17000]}],"highlight":2,"fmt":"#,##0"}' style="left:64px;top:160px;width:720px;height:440px"></div>
  <div class="pp-text b" style="left:830px;top:176px;width:386px;height:34px">読み取れること</div>
  <div class="pp-text" style="left:830px;top:222px;width:386px;height:300px"><ul><li>A案は最も高く、2.5億円</li><li>B案は1.7億円で、A案より8,000万円低い</li><li>C案は保守延長を含めて2.2億円</li></ul></div>
  <div class="pp-text" data-role="caption" data-chrome style="left:64px;top:640px;width:900px;height:24px">出典: 見積書（2026年9月）。5年間の総額</div>
</section>
```

`charts/line.html`:

```html
<!-- 用途: 時間の推移（折れ線）。系列は 2〜3 本まで。注目する系列を先頭にする。
     差し替える所: data-chart・右の所見・出典。 -->
<section class="slide" data-layout="chart">
  <div class="pp-text" data-role="title" style="height:44px">障害対応の時間は、導入後6か月で月40時間から8時間に下がる見込み</div>
  <div class="pp-chart" data-chart='{"type":"line","categories":["1月","2月","3月","4月","5月","6月"],"series":[{"name":"導入後（見込み）","values":[40,30,20,12,9,8]},{"name":"現状","values":[40,41,39,40,42,40]}],"fmt":"#,##0"}' style="left:64px;top:160px;width:720px;height:440px"></div>
  <div class="pp-text b" style="left:830px;top:176px;width:386px;height:34px">読み取れること</div>
  <div class="pp-text" style="left:830px;top:222px;width:386px;height:300px"><ul><li>現状は月40時間前後で横ばい</li><li>導入後は3月から下がり始める</li><li>6月には8時間に収まる</li></ul></div>
  <div class="pp-text" data-role="caption" data-chrome style="left:64px;top:640px;width:900px;height:24px">出典: 社内運用実績（現状）、事業部の試算（導入後）。単位は時間／月</div>
</section>
```

`charts/stacked.html`:

```html
<!-- 用途: 内訳の推移（積み上げ棒）。系列は 3 本まで。合計の数字は右の所見に書く。
     差し替える所: data-chart・右の所見・出典。 -->
<section class="slide" data-layout="chart">
  <div class="pp-text" data-role="title" style="height:44px">費用は初年度に集中し、2年目以降は運用費だけになる</div>
  <div class="pp-chart" data-chart='{"type":"stacked","categories":["2027","2028","2029","2030","2031"],"series":[{"name":"構築","values":[9000,0,0,0,0]},{"name":"移行","values":[2000,0,0,0,0]},{"name":"運用","values":[1200,1200,1200,1200,1200]}],"fmt":"#,##0"}' style="left:64px;top:160px;width:720px;height:440px"></div>
  <div class="pp-text b" style="left:830px;top:176px;width:386px;height:34px">読み取れること</div>
  <div class="pp-text" style="left:830px;top:222px;width:386px;height:300px"><ul><li>初年度は1.22億円で、5年間の72%</li><li>2年目以降は年1,200万円で一定</li><li>構築費が最大の項目</li></ul></div>
  <div class="pp-text" data-role="caption" data-chrome style="left:64px;top:640px;width:900px;height:24px">出典: 見積書（2026年9月）。単位は万円、年度</div>
</section>
```

`charts/waterfall.html`:

```html
<!-- 用途: 差額の内訳（ウォーターフォール）。最初と最後が合計、間が増減。totals は合計にする位置（0 始まり）。
     減少は濃い灰、増加は基調色、合計は灰。差し替える所: data-chart・右の所見・出典。 -->
<section class="slide" data-layout="chart">
  <div class="pp-text" data-role="title" style="height:44px">年間の運用費は、保守費の削減で4,200万円から2,900万円に下がる</div>
  <div class="pp-chart" data-chart='{"type":"waterfall","categories":["現状","保守費","電力費","監視費","導入後"],"series":[{"name":"運用費","values":[4200,-900,-300,-100,2900]}],"totals":[0,4],"fmt":"#,##0"}' style="left:64px;top:160px;width:720px;height:440px"></div>
  <div class="pp-text b" style="left:830px;top:176px;width:386px;height:34px">読み取れること</div>
  <div class="pp-text" style="left:830px;top:222px;width:386px;height:300px"><ul><li>差額は▲1,300万円</li><li>保守費の削減が最大で▲900万円</li><li>電力費・監視費は小さい</li></ul></div>
  <div class="pp-text" data-role="caption" data-chrome style="left:64px;top:640px;width:900px;height:24px">出典: 社内運用実績と見積り。単位は万円／年</div>
</section>
```

`charts/pie.html`:

```html
<!-- 用途: 全体に占める割合（円）。項目は 4 つまで。注目する 1 つだけ強調色。
     差し替える所: data-chart・右の所見・出典。 -->
<section class="slide" data-layout="chart">
  <div class="pp-text" data-role="title" style="height:44px">総費用の約5割は構築費で、残りを運用と移行が分け合う</div>
  <div class="pp-chart" data-chart='{"type":"pie","categories":["構築","運用","移行"],"series":[{"name":"割合","values":[9000,6000,2000]}],"highlight":0,"fmt":"#,##0"}' style="left:64px;top:160px;width:720px;height:440px"></div>
  <div class="pp-text b" style="left:830px;top:176px;width:386px;height:34px">読み取れること</div>
  <div class="pp-text" style="left:830px;top:222px;width:386px;height:300px"><ul><li>構築費が最大で、9,000万円</li><li>運用費は5年間で6,000万円</li><li>移行費は2,000万円</li></ul></div>
  <div class="pp-text" data-role="caption" data-chrome style="left:64px;top:640px;width:900px;height:24px">出典: 見積書（2026年9月）。単位は万円</div>
</section>
```

断片の数字は、1 つのデッキの例として整合させてある（A案 2.5億円・B案 1.7億円・C案 2.2億円（保守延長を含む）、B案の内訳は構築 9,000＋運用 6,000＋移行 2,000＝17,000万円、初年度 12,200万円）。断片を直したときは、他の断片と矛盾しないか確認する。

- [ ] **Step 5: テストを実行する**

Run: `"$PY" -m pytest tests/test_chart_preview.py tests/test_components.py -k "chart or preview"`
Expected: すべて PASS。

- [ ] **Step 6: 目で確認する**

Playwright MCP で `init` した作業フォルダの `final.html`（5 枚の断片を連結）を開き、プレビューのグラフを目視する。次に `build` した PPTX の PNG（LibreOffice の画像）と並べて、棒の高さ・強調色・ウォーターフォールの階段・値ラベルが大きくずれていないことを確認する。ずれはプレビューが近似であることを SKILL.md に書く（Task 6）。

- [ ] **Step 7: コミット**

```bash
git add skills/pptx-deck
git commit -m "feat: グラフの断片 5 種とブラウザ用プレビューを追加"
```

---

### Task 6: 原稿の書式と検査・SKILL.md

**Files:**
- Create: `skills/pptx-deck/pptx_deck/script_lint.py`, `assets/sample/script.md`, `SKILL.md`
- Modify: `skills/pptx-deck/pptx_deck/cli.py`（`lint-script` を追加）
- Test: `skills/pptx-deck/tests/test_script_lint.py`

**Interfaces:**
- Produces: `script_lint.parse(md: str) -> list[dict]`（`{"id": "S01", "title": str, "fields": {名前: 文字列 | list[str]}}`）、`script_lint.lint(md: str) -> list[str]`（問題の全件。空なら合格）
- CLI: `lint-script <script.md>`: 問題を 1 行ずつ出し、あれば終了コード 1。

原稿の書式（`script.md`）:

```
# <デッキ名>
- 目的: …
- 対象: …
- 配色: navy | green | gray | #RRGGBB

## S01 表紙
- layout: cover
- 見出し: …
- 副題: …

## S02 背景
- layout: content
- 章名: なぜ今、移行を決める必要があるのか
- 見出し: 現行基盤は2028年に保守が切れる
- 本文:
  - 保守期限は2028年3月
  - …
- 図表: 図解/before-after — 現状と導入後を並べて見せるため
- 出典: 社内資料（2026年9月）
- 判断の枠: 決めること=…／期限=…／推奨=…
```

規則: ① `## S` の番号は 01 から連番 ② `layout` は `cover|section|agenda|content|diagram|table|chart|closing` ③ 全スライドに `見出し` ④ `cover`・`closing` 以外に `章名`、`cover`・`closing`・`agenda` 以外に `本文` か `図表` ⑤ `layout` が `diagram|table|chart` なら `図表` ⑥ 最初は `cover`（警告ではなく問題として扱う）⑦ 配色の値は有効な指定。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_script_lint.py`:

```python
from pptx_deck import script_lint

OK = """# クラウド移行
- 目的: 承認を得る
- 対象: 経営会議
- 配色: navy

## S01 表紙
- layout: cover
- 見出し: クラウド基盤への移行を承認いただきたい
- 副題: 3案の比較

## S02 背景
- layout: content
- 章名: なぜ今、移行を決める必要があるのか
- 見出し: 現行基盤は2028年に保守が切れる
- 本文:
  - 保守期限は2028年3月
  - 運用負荷が年々増えている
- 出典: 社内資料（2026年9月）

## S03 比較
- layout: table
- 章名: 3案のどれを選ぶか
- 見出し: B案は3項目で最も釣り合っている
- 図表: 表/compare — 3案を項目ごとに並べるため
"""


def test_parse():
    s = script_lint.parse(OK)
    assert [x["id"] for x in s] == ["S01", "S02", "S03"]
    assert s[1]["fields"]["本文"] == ["保守期限は2028年3月", "運用負荷が年々増えている"]
    assert s[1]["fields"]["見出し"] == "現行基盤は2028年に保守が切れる"


def test_ok_has_no_problems():
    assert script_lint.lint(OK) == []


def test_lists_every_problem_at_once():           # Review Focus 4
    bad = OK.replace("## S02", "## S04").replace("- 見出し: B案は3項目で最も釣り合っている\n", "") \
            .replace("- layout: cover", "- layout: banner")
    got = "\n".join(script_lint.lint(bad))
    assert "S04" in got and "連番" in got
    assert "S03" in got and "見出し" in got
    assert "banner" in got


def test_first_must_be_cover():
    md = OK.replace("- layout: cover", "- layout: content")
    assert any("表紙" in p for p in script_lint.lint(md))


def test_diagram_needs_figure_field():
    md = OK.replace("- 図表: 表/compare — 3案を項目ごとに並べるため\n", "- 本文:\n  - 要点\n")
    assert any("図表" in p for p in script_lint.lint(md))


def test_bad_color():
    assert any("配色" in p for p in script_lint.lint(OK.replace("- 配色: navy", "- 配色: red")))


def test_empty_script():
    assert script_lint.lint("") == ["スライド（## S01 …）がありません"]
```

- [ ] **Step 2: 失敗を確認する**

Run: `"$PY" -m pytest tests/test_script_lint.py`
Expected: FAIL

- [ ] **Step 3: 実装する**

`pptx_deck/script_lint.py`:

```python
"""原稿（script.md）の書式を検査する。内容の良し悪しは見ない。"""
import re

from . import theme

LAYOUTS = {"cover", "section", "agenda", "content", "diagram", "table", "chart", "closing"}
_SLIDE = re.compile(r"^## (S\d{2})\s*(.*)$")
_FIELD = re.compile(r"^- ([^:：]+)[:：]\s*(.*)$")
_ITEM = re.compile(r"^\s+- (.*)$")


def parse(md: str) -> list[dict]:
    slides, cur, field = [], None, None
    for line in md.splitlines():
        m = _SLIDE.match(line)
        if m:
            cur = {"id": m.group(1), "title": m.group(2).strip(), "fields": {}}
            slides.append(cur)
            field = None
            continue
        if cur is None:
            continue
        f = _FIELD.match(line)
        if f:
            field = f.group(1).strip()
            cur["fields"][field] = f.group(2).strip() if f.group(2).strip() else []
            continue
        it = _ITEM.match(line)
        if it and field is not None:
            if not isinstance(cur["fields"][field], list):
                cur["fields"][field] = [cur["fields"][field]]
            cur["fields"][field].append(it.group(1).strip())
    return slides


def _header_color(md: str):
    for line in md.splitlines():
        if line.startswith("## "):
            break
        m = _FIELD.match(line)
        if m and m.group(1).strip() == "配色":
            return m.group(2).strip()
    return None


def lint(md: str) -> list[str]:
    slides = parse(md)
    if not slides:
        return ["スライド（## S01 …）がありません"]
    out = []
    color = _header_color(md)
    if color:
        try:
            theme.resolve(color)
        except ValueError as e:
            out.append(f"配色: {e}")
    for i, s in enumerate(slides, start=1):
        sid, f = s["id"], s["fields"]
        if sid != f"S{i:02d}":
            out.append(f"{sid}: 番号が連番ではありません（{i} 番目は S{i:02d}）")
        layout = f.get("layout")
        if layout not in LAYOUTS:
            out.append(f"{sid}: layout が不正です: {layout!r}（{', '.join(sorted(LAYOUTS))}）")
        if i == 1 and layout != "cover":
            out.append(f"{sid}: 最初のスライドは表紙（layout: cover）にしてください")
        if not f.get("見出し"):
            out.append(f"{sid}: 見出しがありません")
        if layout not in ("cover", "closing") and not f.get("章名"):
            out.append(f"{sid}: 章名（そのスライドが答える問い）がありません")
        if layout not in ("cover", "closing", "agenda") and not (f.get("本文") or f.get("図表")):
            out.append(f"{sid}: 本文か図表のどちらかが必要です")
        if layout in ("diagram", "table", "chart") and not f.get("図表"):
            out.append(f"{sid}: layout が {layout} のときは図表（型と理由）が必要です")
    return out
```

`pptx_deck/cli.py` に追加:

```python
def cmd_lint_script(args) -> int:
    from . import script_lint
    problems = script_lint.lint(Path(args.script).read_text(encoding="utf-8"))
    for p in problems:
        print(p)
    return 1 if problems else 0
```

`main` の登録部に追加:

```python
    p = sub.add_parser("lint-script")
    p.add_argument("script")
    p.set_defaults(fn=cmd_lint_script)
```

- [ ] **Step 4: サンプル原稿を書く**

`assets/sample/script.md`（10 枚。通しの確認と、書き方の手本に使う。数字は例）:

```markdown
# クラウド基盤移行の承認依頼
- 目的: 経営会議で、移行先の案と予算を承認してもらう
- 対象: 経営会議（10名）
- 配色: navy

## S01 表紙
- layout: cover
- 見出し: クラウド基盤への移行を承認いただきたい
- 副題: 3案の比較と推奨案（B案）

## S02 目次
- layout: agenda
- 章名: 本日のお願いと流れ
- 見出し: 本日お願いしたいのは、B案の採用と初年度予算の承認である

## S03 背景
- layout: section
- 章名: なぜ今、移行を決める必要があるのか
- 見出し: 現行基盤は2028年に保守が切れ、移行が必要になる
- 本文:
  - 現行基盤の保守期限
  - 移行しない場合のコスト
  - 決定の期限

## S04 段階
- layout: diagram
- 章名: どう進めるのか
- 見出し: 移行は4つの段階で進め、各段階の終わりに承認を取る
- 図表: 図解/flow-h — 手順を順に示し、各段階の承認を見せるため
- 出典: 移行計画書（2026年9月版）

## S05 比較表
- layout: table
- 章名: 3案のどれを選ぶか
- 見出し: B案は、費用・期間・リスクの3項目で最も釣り合っている
- 図表: 表/compare — 3案を項目ごとに並べて比べるため
- 出典: 見積書（2026年9月）

## S06 費用
- layout: chart
- 章名: 費用はどれだけ違うのか
- 見出し: B案の総費用は1.7億円で、A案より8,000万円低い
- 図表: グラフ/bar — 3案の量を比べ、B案だけを強調するため
- 出典: 見積書（2026年9月）。5年間の総額

## S07 効果
- layout: diagram
- 章名: 導入すると何が変わるのか
- 見出し: 導入後は、障害対応が月40時間から8時間に減る
- 図表: 図解/before-after — 前後の値を並べて見せるため
- 出典: 社内運用実績と見積り

## S08 計画
- layout: diagram
- 章名: いつ、何を決めるのか
- 見出し: 6か月で移行を完了し、第3月に最終判断を行う
- 図表: 図解/gantt — 工程と判断点を月の軸に並べるため
- 出典: 移行計画書（2026年9月版）

## S09 承認依頼
- layout: content
- 章名: 何を承認してほしいのか
- 見出し: B案を採用すれば、現行維持より5年間で5,000万円を削減できる
- 図表: 判断の枠/decision — 決めること・期限・推奨と理由を1枚に置くため
- 出典: 社内試算（2026年9月）
- 判断の枠: 決めること=移行先の案と予算／期限=11月の経営会議／推奨=B案

## S10 結び
- layout: closing
- 見出し: 以上、ご承認をお願いします
- 本文:
  - 承認後、11月に詳細設計を開始する
  - 2027年3月に第1期の移行を完了する
```

注: `S09` の `layout: content` は、`lint` の「本文か図表」の規則を `図表` で満たす。`lint` がこのサンプルで空を返すことを Step 5 のテストに追加する。

テストに追加（`tests/test_script_lint.py` の末尾）:

```python
def test_sample_script_is_valid():
    from pptx_deck import paths
    md = (paths.ASSETS / "sample" / "script.md").read_text(encoding="utf-8")
    assert script_lint.lint(md) == []
    assert len(script_lint.parse(md)) == 10
```

- [ ] **Step 5: テストを実行する**

Run: `"$PY" -m pytest tests/test_script_lint.py`
Expected: すべて PASS。

- [ ] **Step 6: SKILL.md を書く**

`skills/pptx-deck/SKILL.md`:

````markdown
---
name: pptx-deck
description: テーマ・素材・原稿から、コンサルテイストの承認資料（稟議・提案・計画）を作る。原稿(Markdown)の承認 → HTML スライド案（各 3 案）の選択 → 最終 HTML の承認 → 編集可能な PowerPoint(.pptx) の順に進める。利用者の PPTX テンプレート（表紙・裏表紙・ヘッダー・フッター）に従える。「スライドを作って」「資料を作って」「PowerPoint を作って」「稟議資料」「提案資料」「デッキ」と頼まれたときに使う。既存 PPTX の編集には使わない。Windows 専用。
---

# pptx-deck

ビジネス上の承認文書を、コンサル資料のテイストで作る。本文を画像にせず、PowerPoint で編集できる .pptx を出す。13.33×7.5in（16:9）、BIZ UDPゴシック、無彩色＋基調 1 色＋強調 1 色。

以降の `<skill>` は、この SKILL.md があるフォルダ。コマンドはすべて `python "<skill>/run.py" …`。`<名前>` は作業フォルダ名（実行したディレクトリ直下に作る）。

## 0. 初回だけ（環境）

1. `python "<skill>/run.py" doctor` を実行する。`venv` がない（終了コード 3）または `status` に不足があるときは、**利用者に「`%LOCALAPPDATA%\pptx-deck\venv` に Python の仮想環境と chromium（数百 MB）を導入してよいか」を確認する**。承認が出るまで作らない。
2. 承認後、`python "<skill>/run.py" setup --yes`。
3. `doctor` の `warnings` を利用者に伝える（BIZ UDPゴシック未導入、LibreOffice なしなど）。

## 1. 流れ（承認は 3 回）

| 段階 | やること | 承認 |
|---|---|---|
| 入力 | 下の「1.1 入力で聞くこと」 | |
| 原稿 | `<名前>/script.md` を書く。`lint-script` が空になるまで直す | ① チャットで承認（内容を凍結） |
| スライド案 | 全スライドの 3 案を `slides/NN-A.html`〜に書き、`variants` で 1 つの HTML にする | ② HTML 上で選択＋コメント |
| 最終 HTML | 選ばれた案を `finalize` で統合し、ブラウザで全体を見せる | ③ チャットで承認 |
| PPTX | `build` で書き出し、検査と確認用の画像で崩れを確認する | |

### 1.1 入力で聞くこと
- 入口: テーマのみ／素材（メモ・文書・データ）／既存の Markdown 原稿。足りない前提（対象者・目的・枚数・期限）は先に質問する。外れたときの手戻りが大きいものは推測しない。
- 配色: プリセット（`navy`・`green`・`gray`）か、基調色 `#RRGGBB`。指定がなければ `navy`。
- 利用者の PowerPoint テンプレートの有無（`.potx` または `.pptx` のパス）。あれば、**表紙・裏表紙・ヘッダー・フッター**がそれに従う。フォントと配色は、テンプレートにかかわらず BIZ UDPゴシックと選んだ配色。16:9（13.33×7.5in）以外のテンプレートは使えない。
- フッターの文言（社外秘など）があれば `build --footer`。

### 1.2 作業フォルダ
`python "<skill>/run.py" init "<名前>" --color <プリセット|#RRGGBB> [--template "<パス>"]`。同名のフォルダが空でないときは止まる。**中身を利用者に見せて、上書きしてよいと言われたときだけ `--force`**。`init` の出力の `notes`（テンプレートの代替レイアウト）は利用者に伝える。

| 置き場所 | ファイル |
|---|---|
| スキル `<skill>/`（読み取り専用） | `SKILL.md`、`assets/`（`components/` の断片、`web/`、`icons/`、`template/`）、コード |
| 作業フォルダ `<名前>/` | `script.md`、`slides/NN-X.html`、`variants.html`、`final.html`、`<名前>.pptx`、`theme.css`・`base.css`・`icons/`・`_template/`（`init` が作る） |
| OS の一時フォルダ `%TEMP%\pptx-deck\<名前>\` | 確認用の PNG（`render/`）、SVG の画像化 |

## 2. 原稿（script.md）

書式は `assets/sample/script.md`（10 枚）に従う。スライドごとに次を書く。

- `layout`（`cover|section|agenda|content|diagram|table|chart|closing`）、`見出し`（**結論を言い切る 1 文**）、`章名`（そのスライドが答える問い）、`本文`、`図表`（型と選んだ理由を 1 行）、`出典`、判断が要るスライドは `判断の枠`（決めること・期限・推奨）。
- 1 スライド 1 メッセージ。結論 → 根拠の順。数字には出典と前提を書く。スピーカーノートは作らない。
- 書いたら `python "<skill>/run.py" lint-script "<名前>/script.md"`。問題は全件出る。空になってからチャットで承認を求める。承認後は、承認なしに内容を変えない。

## 3. スライド案（3 案）

1. `assets/components/` の断片から、内容に合う型を選ぶ（下の一覧）。断片をコピーして、内容と数字を差し替え、`<名前>/slides/NN-A.html` に書く。
2. **3 案は、同じ型のまま配置・強調・密度を変える**（A: 標準／B: 強調や大きな数字を前に出す／C: 情報量を増やして密度を上げる）。基本として、**図と表を多用して説明する**。内容（文言と数字）は 3 案で同じ。
3. `python "<skill>/run.py" variants "<名前>"` → `<名前>/variants.html`。Playwright MCP の `browser_navigate` で `file:///C:/.../variants.html` を開き、「各スライドの案を選び、直したい点はコメントに書いて、『送信』を押してください」と伝える。
4. 送信を待つ（ユーザーに「完了」と入力させない）。`browser_evaluate` で次を実行し、送信されるか約 100 秒たつまでブロックして結果を返す。`submitted` が false なら同じ呼び出しを繰り返す（合計約 30 分、18 回まで）。ユーザーがターミナルに入力したときは待ちをやめて、その内容に従う。

   `() => new Promise(res => { const t0 = Date.now(); const id = setInterval(() => { if (window.__submitted || Date.now() - t0 > 100000) { clearInterval(id); res({ submitted: !!window.__submitted, md: window.__answersMd }); } }, 500); })`

5. `submitted` が true なら、`md` を `<名前>/answers-N.md` に書く（N は何回目か）。
6. **コメントがあるスライドだけ**、選ばれた案を直して 1 案にし（`NN-A.html` を上書き、`NN-B/C` は削除）、`variants --round N+1` で再提示する（「採用／要修正」の選択になる）。別案の希望があるときだけ 3 案に戻す。コメントが未反映のうちは `finalize` が止まる。
7. すべて決まったら `python "<skill>/run.py" finalize "<名前>" --answers "<名前>/answers-N.md"` → `final.html`。

### 型の一覧（`assets/components/`）
- レイアウト: `cover`（表紙）・`section`（章扉）・`agenda`（目次）・`decision`（判断・承認依頼）・`closing`（裏表紙）
- 図解: `flow-h`（手順）・`tree`（分解）・`matrix`（2×2）・`pyramid`（階層・優先度）・`cycle`（循環）・`gantt`（計画）・`venn`（重なり）・`before-after`（前後）・`layers`（構成）・`compare`（3 案の比較）
- 表: `compare`（比較）・`rating`（◎○△）・`cost`（費用）・`schedule`（予定）
- グラフ: `bar`・`line`・`stacked`・`waterfall`・`pie`（`data-chart` の書き方は断片のコメントと下記）
- 内容に合う型がなければ、断片の部品（下記）で組む。新しい型を作ったら、`assets/components/` に足して `tests/test_components.py` を通す。

## 4. HTML の書き方

- 1 枚 = `<section class="slide" data-layout="…">`（1280×720px）。部品は `pp-text`・`pp-shape`・`pp-line`・`pp-image`・`pp-table`・`pp-chart` だけ。**これ以外のクラスの文字や図は PPTX に出ない**。
- 位置は `style="left;top;width;height"`（px）。文字には必ず幅を付ける。面と文字は兄弟要素にし、文字の中心を含む面が背景色になる。
- 文字: `data-role` = `title|lead|body|caption|display`。表紙・裏表紙の題と副題は `data-ph="title|subtitle"`（位置はテンプレート）。箇条書きは `<div class="pp-text"><ul><li>`。
- 色は `var(--accent)` などの変数だけ。基調色の文字は白地かつ 24px 以上のときだけ。**強調色（`f-emph`・`t-emph`）は 1 スライドに 1 点**（推奨・承認を求める対象）。
- 本文 14pt（約 19px）以上、注記 10pt（14px）以上。出典は `data-role="caption" data-chrome`、y 640〜664。
- 画像はアイコン（`icons/<名前>-<accent|emphasis|white|gray>.svg`、`alt` 必須）と利用者の写真だけ。
- 重ねる図（ベン図など）は、重なる要素の両方に `data-overlap`。
- グラフ: `data-chart='{"type":"bar|barh|line|pie|stacked|stacked100|waterfall","categories":[…],"series":[{"name":"…","values":[…]}],"highlight":番号,"fmt":"#,##0","totals":[…]}'`。ブラウザのプレビューは近似で、実際は PowerPoint のグラフになる。

## 5. PPTX の出力

`python "<skill>/run.py" build "<名前>" [--footer "文言"]`。出力 JSON の `ok` が false なら、`violations` を読んで `slides/` の断片を直し、`finalize` からやり直す（内容は変えない。直すのは配置・サイズ・色）。直しが原稿の変更（文章を減らす、スライドを分ける）を伴うときは、案を示して利用者の承認を得る。

`ok` が true なら、`pngs`（確認用の画像。LibreOffice の描画）を開いて崩れを確認し、所見を伝える。PowerPoint で開いて最終確認することを勧める。成果物は `<名前>/<名前>.pptx`。

| rule | 直し方 |
|---|---|
| `overflow` | 文字の枠を広げるか、文章を減らす |
| `overlap` | 位置をずらす。意図的なら両方に `data-overlap` |
| `keepout` | テンプレートのヘッダー・フッターの領域（y 676 以降が標準）を避ける |
| `fontMin` | 本文 14pt（19px）・注記 10pt（14px）以上にする |
| `contrast` | 文字色か面の色を変える（基調色の文字は白地で 24px 以上） |
| `imageAlt`・`bodyImage` | `alt` を付ける／本文を画像にしない |
| `titleMissing` | `data-role="title"`（表紙・裏表紙は `data-ph="title"`）を付ける |

## 6. 守ること

- 原稿の承認後は、承認なしで内容を変えない。
- 仮想環境は、承認なしに作らない。既存の作業フォルダは、中身を見せて承認を得てから上書きする。
- エラーが出たら、原因と対処を示して止まる。推測で別の方法に切り替えない。
- スクリプトは Playwright MCP を使わない。MCP は、案の選択の受け取りと画面確認だけに使う。
````

- [ ] **Step 7: SKILL.md の記述を検証する**

```bash
python run.py lint-script assets/sample/script.md
```

Expected: 何も出力されず、終了コード 0。`SKILL.md` に書いたコマンド名（`doctor`・`setup`・`init`・`lint-script`・`variants`・`finalize`・`build`）が `python run.py --help` のサブコマンドと一致していることを目で確認する（`check` は補助なので SKILL.md には載せない）。旧スキルの語が残っていないこと:

```bash
grep -n -E "構成案|橙|deck\.html|npm|node " SKILL.md || echo "旧仕様の語なし"
```

- [ ] **Step 8: コミット**

```bash
git add skills/pptx-deck
git commit -m "feat: 原稿の書式と検査（lint-script）・サンプル原稿・SKILL.md を追加"
```

---

### Task 7: 通しの確認・README・プラグイン情報・旧スキルの置き換えの仕上げ

**Files:**
- Create: `skills/pptx-deck/tests/test_e2e_library.py`
- Modify: `README.md`（全面書き換え）, `.claude-plugin/plugin.json`

**Interfaces:**
- Consumes: Task 1〜6 のすべて、計画 A の CLI

- [ ] **Step 1: 全断片を 1 つのデッキにする通しのテストを書く**

`tests/test_e2e_library.py`:

```python
import json
import shutil
from pathlib import Path

import pytest
from pptx import Presentation

from pptx_deck import cli, initdir, paths
from tests.test_template import STANDARD, _as_pptx

pytestmark = pytest.mark.skipif(shutil.which("soffice") is None and not Path(
    r"C:\Program Files\LibreOffice\program\soffice.exe").exists(), reason="LibreOffice なし")

COMP = paths.ASSETS / "components"
ORDER = ["layouts/cover", "layouts/agenda", "layouts/section", "diagrams/flow-h", "tables/compare",
         "charts/bar", "diagrams/before-after", "diagrams/gantt", "layouts/decision", "layouts/closing"]


def make_deck(work: Path, names):
    slides = work / "slides"
    for i, n in enumerate(names, start=1):
        (slides / f"{i:02d}-A.html").write_text((COMP / f"{n}.html").read_text(encoding="utf-8"), encoding="utf-8")
    ans = "".join(f"## S{i:02d}\n- 選択: A\n- コメント: \n" for i in range(1, len(names) + 1))
    (work / "ans.md").write_text(ans, encoding="utf-8")
    assert cli.main(["variants", str(work)]) == 0
    assert cli.main(["finalize", str(work), "--answers", str(work / "ans.md")]) == 0


@pytest.mark.parametrize("template_kind", ["standard", "user_pptx"])
def test_full_deck_builds(tmp_path, capsys, template_kind):
    w = tmp_path / "deck"
    tpl = None
    if template_kind == "user_pptx":
        tpl = _as_pptx(STANDARD, tmp_path / "company.pptx",
                       rename={"表紙": "Title Slide", "本文": "Title and Content", "裏表紙": "Closing"})
    initdir.init(w, color="green", template_path=tpl)
    make_deck(w, ORDER)
    capsys.readouterr()
    assert cli.main(["build", str(w), "--footer", "社外秘"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True and out["violations"] == []
    prs = Presentation(w / "deck.pptx")
    assert len(prs.slides) == 10
    assert prs.slides[0].slide_layout.name in ("表紙", "Title Slide")
    assert prs.slides[-1].slide_layout.name in ("裏表紙", "Closing")
    assert any(s.has_chart for s in prs.slides[5].shapes) and any(s.has_table for s in prs.slides[4].shapes)
    footers = [p.text_frame.text for s in prs.slides for p in s.placeholders if "Footer" in p.name]
    assert footers and all(t == "社外秘" for t in footers)
    assert len(out["pngs"]) == 10


def test_no_picture_of_body_text(tmp_path, capsys):
    """本文を画像にしていない: 画像はアイコン等の小さなものだけ（SPEC 受入条件 4）。"""
    w = tmp_path / "deck"
    initdir.init(w, color="navy")
    make_deck(w, ["layouts/decision", "diagrams/compare", "charts/waterfall"])
    capsys.readouterr()
    assert cli.main(["build", str(w)]) == 0
    prs = Presentation(w / "deck.pptx")
    for s in prs.slides:
        for sh in s.shapes:
            if sh.shape_type == 13:
                assert sh.width * sh.height < prs.slide_width * prs.slide_height * 0.05
```

- [ ] **Step 2: 通しのテストと全テストを実行する**

Run: `"$PY" -m pytest tests/test_e2e_library.py && "$PY" -m pytest`
Expected: すべて PASS。落ちたら、出力 JSON の `violations` を読み、断片（Task 1〜5）を直す。`user_pptx` の場合に `keepout`・`outOfSlide` が出るなら、断片の座標が標準テンプレートに依存している可能性が高い（Review Focus 2）。その場合は、利用者のテンプレートで領域が違う場合の扱いを SKILL.md に書き足す（領域が狭いテンプレートでは、`--area-*` の変数に合わせて断片の座標を調整する）。

- [ ] **Step 3: 実際の承認の流れを、サンプル原稿で通す（手動）**

この Step は、人の操作と Playwright MCP を含む通しの確認。**SKILL.md に書いたとおり**に、`assets/sample/script.md` を原稿として実行する。

1. 利用者に「サンプル原稿で通しの確認をします。環境（`doctor`）と、使うテンプレート（あれば会社のもの）を教えてください」と伝える。
2. `init` → 全 10 枚の `slides/NN-A/B/C.html`（3 案。同じ型のまま配置・強調・密度を変える）を断片から作る → `variants` → Playwright MCP で開く → 送信を待つ（SKILL.md の `browser_evaluate`）→ 回答を `answers-1.md` に書く。
3. 利用者に、**わざと 1 枚にコメントを付けて**もらう（コメントの反映 → 1 案での再提示 → `finalize` が通る流れを確認するため）。
4. `finalize` → `final.html` を Playwright MCP で開いて全体を見せる → チャットで承認を得る → `build`。
5. `ok: true`、`pngs` の確認、`<名前>.pptx` を PowerPoint で開いて、表紙・裏表紙・ヘッダー・フッターがテンプレートに従っていること、グラフ・表が編集できること、本文が画像でないことを、利用者に確認してもらう。
6. 結果（所見、直した点）を利用者に報告する。この通しで見つかった問題は、SKILL.md か断片に反映して、テストを足す。

- [ ] **Step 4: README.md を書き換える**

`README.md`（全面）:

````markdown
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
````

- [ ] **Step 5: プラグイン情報を更新する**

`.claude-plugin/plugin.json`:

```json
{
  "name": "pptx-deck",
  "version": "0.2.0",
  "description": "ビジネス上の承認文書をコンサルテイストで作る。原稿の承認 → スライド案（各 3 案）の選択 → 最終 HTML → 編集可能な PPTX。利用者のテンプレートに従える。Windows 専用。",
  "license": "MIT"
}
```

- [ ] **Step 6: 旧仕様の語が残っていないことを確認する**（Review Focus 5）

```bash
cd C:/Users/sioay/OneDrive/github/pptx-deck
grep -rn -E "構成案|橙|deck\.html|npm |node_modules|pptxgenjs" README.md skills/pptx-deck/SKILL.md skills/pptx-deck/assets .claude-plugin || echo "旧仕様の語なし"
```

Expected: `旧仕様の語なし`。出たら、該当箇所を新仕様に直す（`SKILL.md` の「強調色（`f-emph`）」の説明に「橙」と書いていないこと）。

- [ ] **Step 7: 全テストを実行する**

Run: `cd skills/pptx-deck && "$PY" -m pytest`
Expected: すべて PASS。テスト数と所要時間を記録する。

- [ ] **Step 8: コミット**

```bash
cd C:/Users/sioay/OneDrive/github/pptx-deck
git add -A
git commit -m "feat: 通しのテスト・README・プラグイン情報を新仕様に更新し、旧スキルの置き換えを完了"
```

- [ ] **Step 9: 利用者のインストール先の更新を提案する**

`~/.claude/skills/pptx-deck`（`C:\Users\sioay\.claude\skills\pptx-deck`）は、リポジトリとは別の**旧スキルのコピー**（`node_modules` を含む）。置き換えは削除を伴うため、**利用者に確認する**。確認の文面: 「`~/.claude/skills/pptx-deck`（旧スキルのコピー）を、新スキルに置き換えてよいですか。中身は `SKILL.md`・`design/`・`scripts/`・`node_modules/` などで、旧スキルは git の履歴（`c0565aa`）に残っています」。承認されたら、中身を一覧で見せてから削除し、リポジトリの `skills/pptx-deck` へのリンク（`grill-form` と同じシンボリックリンク）または複製を作る。承認が出なければ、何もせず、手順だけを伝える。

---

## 計画 B の完了条件

- `"$PY" -m pytest` がすべて通る（断片 24 種 × 2 配色、アイコン、グラフのプレビュー、原稿の検査、通しの 2 テンプレート）。
- `assets/sample/script.md` を原稿にして、承認の流れ（原稿 → 3 案の選択 → コメントの反映 → 最終 HTML → PPTX）が人の操作で最後まで通った（Task 7 Step 3）。
- 利用者のテンプレート（標準・変換済み `.pptx`、可能なら会社のもの）で、表紙・裏表紙・ヘッダー・フッターが従っている。
- `README.md`・`SKILL.md`・`plugin.json` に旧仕様の語が残っていない。
- 旧 `skills/pptx-deck` が新スキルに置き換わっている（リポジトリ）。インストール先のコピーは、利用者の承認に従う。

## 自己レビュー（作成時）

- **SPEC の対応**: 受入条件 1（SKILL.md）→ Task 6。2（テンプレート一式・配色の反映）→ Task 1〜5（配色は 2 配色で全断片を検査）。3（サンプル原稿の通し）→ Task 7 Step 3。4・5 は計画 A と Task 7 の通しのテスト。6（旧スキルの置き換え）→ 計画 A Task 1 と Task 7 Step 6・9。7（README）→ Task 7。8（仮想環境）→ 計画 A Task 1 と SKILL.md の 0 章。
- **断片の数字**: 1 つのデッキの例として整合させた（Task 5 の注記）。実装者は、断片を直したら他との矛盾を確認する。
- **型・名前の整合**: `data-dir="rev"`（`cycle.html`）は計画 A の Task 4・5 で対応する。`color-mix`（`venn.html`）は計画 A の `measure.js` の `parseColor` が `color(srgb …)` を読むことに依存する。`closing` の題の位置は `--closing-title-*`（計画 A の Task 3・9）に依存する。
- **計画 A への依存の追加**: 上の 3 点は、計画 A の該当タスクに反映済み。
