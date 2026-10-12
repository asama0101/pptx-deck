# pptx-deck 作り直し 実装計画 A（エンジン）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 承認済み原稿の HTML（`final.html`）を、利用者の PowerPoint テンプレートを土台にして、編集可能な .pptx に変換するエンジン（環境構築・テンプレート解析・計測・変換・検査・3 案ページ・最終 HTML の統合）を作る。

**Architecture:** `run.py`（標準ライブラリのみ）が共通の仮想環境の Python で `pptx_deck` パッケージを起動する。HTML は `pp-*` クラスの決められた部品だけで書き、Playwright(Python) が各部品の位置・大きさ・書式を測って dict のモデルにする。モデルを検査し、python-pptx がテンプレートのファイルを土台に開いて、レイアウトの上にネイティブの図形・文字・表・グラフとして書き出す。3 案ページ（`variants.html`）は選択とコメントを `window.__answersMd` に出し、Claude が Playwright MCP で受け取る。

**Tech Stack:** Python 3.14（導入済み）、python-pptx 1.0.2、playwright (Python)、pymupdf、lxml、pytest。LibreOffice（確認用の画像化。導入済み）。

**Spec:** `docs/specs/2026-10-12_1607_pptx-deck-rebuild.md`（承認済み）。この計画は SPEC の受入条件 3〜5・7 とそれを支えるエンジンを作る。受入条件 1・2・6・8（SKILL.md・テンプレート一式・旧スキルの置き換え・README）と通しのサンプル実行は、計画 B（`2026-10-12-pptx-deck-rebuild-library.md`）で作る。計画 B は、この計画の完了後に着手する。

## Global Constraints

すべてのタスクに暗黙に適用する。値は SPEC から写した。

- Windows 専用。フォントは **BIZ UDPゴシック**（PPTX の書式には常にこの名前を書く）。16:9（13.33×7.5in）。HTML 側は 1280×720px（96px = 1in、1px = 0.75pt = 9525 EMU）。
- 本文を画像にしない。画像は、アイコン（SVG）と利用者が渡した写真だけ。
- 実装は Python 一本。仮想環境は `%LOCALAPPDATA%\pptx-deck\venv`。**利用者の承認なしに作らない**（`setup` は `--yes` が必要）。システムの Python に導入しない。
- 位置の計測はスクリプト自身の Playwright で行う。スクリプトから Playwright MCP を呼ばない。
- 利用者のテンプレート（`.potx`／`.pptx`）に従うのは、表紙・裏表紙・ヘッダー・フッターまで。フォントと配色は、常に BIZ UDPゴシックと選んだ配色。
- 配色は無彩色＋基調 1 色＋強調 1 色まで。文字のコントラスト比は 4.5:1 以上（大きい文字は 3:1）。本文 14pt 以上、注記 10pt 以上。
- 体裁の検査は最小限（はみ出し・重なり・文字サイズの下限・コントラスト）。コンサルテイスト自体の検査（出典の有無など）は作らない。
- ファイルの置き場所: スキルの Markdown と同じ場所 = `skills/pptx-deck/`（SKILL.md・テンプレート・コード）。一過性のもの（確認用 PNG、SVG の画像化、LibreOffice の作業）= `tempfile` API による OS の一時フォルダ。成果物と中間成果物 = 実行ディレクトリ直下の `<名前>/`。プロジェクト内やパス直書きで一時ファイルを作らない。
- 旧 `skills/pptx-deck` は参考にとどめ、コードをコピーしない（git 履歴 `c0565aa` に残る）。
- コメントとコミットメッセージは日本語（既存の慣習）。コミットメッセージの末尾に、環境が指定する `Co-Authored-By` / `Claude-Session` の行を付ける。
- テストは仮想環境の Python で実行する。以降 `PY` は `"$LOCALAPPDATA/pptx-deck/venv/Scripts/python.exe"`（Git Bash）を指す。作業ディレクトリは `skills/pptx-deck`。

## Review Focus

SPEC が暗に求めているが、どのタスクの通常のテストにも入りにくい入力と条件。各行のテストは、担当のタスクに入れてある。

1. 利用者のテンプレートが `.potx`（python-pptx がそのままでは開けない）→ 開ける（Task 3）。
2. 16:9 でない／13.33in 幅でないテンプレート → 理由を示して止まる（Task 3）。
3. 背景が暗いテンプレート → 本文の文字色との**コントラスト違反**を検出する（Task 3 で背景色を取り、Task 4・7 で使う）。
4. 裏表紙のレイアウトがないテンプレート → 本文のレイアウトに代え、その旨を `notes` に残す（Task 3・5）。
5. 同名の作業フォルダが既にある → 上書きせず、止まって中身の確認を促す（Task 9）。
6. （Task 4）スライドが 0 枚の HTML、日本語の長いタイトル、`data-overlap` の指定は、それぞれ明確な結果になる。
7. （Task 1）仮想環境が壊れている・ない → 「環境を作ってよいか」の確認に進む。承認なしに作らない。
8. **BIZ UDPゴシックが未導入の PC**（この PC は BIZ UDゴシックのみで、P 付きがない）→ `doctor` が警告し、計測は代替フォントで行う。折り返しの差は、確認用の画像で見る（Task 1）。

---

## ファイル構成

```
skills/pptx-deck/
  run.py                      # 標準ライブラリのみ。venv の Python で pptx_deck を起動する
  requirements.txt            # python-pptx, playwright, pymupdf, lxml
  requirements-dev.txt        # -r requirements.txt, pytest
  pytest.ini
  pptx_deck/
    __init__.py
    __main__.py               # cli.main()
    paths.py                  # 共通 venv・一時フォルダの場所（標準ライブラリのみ）
    env.py                    # 環境の状態確認と作成（標準ライブラリのみ）
    theme.py                  # 配色の導出・プリセット・theme.css
    pptxutil.py               # 単位変換・フォント設定・スライド削除などの小道具
    template.py               # テンプレートを開く・レイアウトを選ぶ・領域を取る・下地を作る
    render.py                 # LibreOffice で PDF → pymupdf で PNG
    measure.js                # ブラウザ内で実行する計測スクリプト
    measure.py                # Playwright で measure.js を実行してモデルを得る
    build.py                  # モデル → PPTX（文字・図形・線・画像・表）
    charts.py                 # モデル → ネイティブのグラフ
    check.py                  # モデルと PPTX の検査
    variants.py               # variants.html の生成・回答の解析・final.html の統合
    initdir.py                # 作業フォルダの初期化
    cli.py                    # サブコマンド
  assets/
    web/base.css              # スライドの枠と pp-* 部品の基本 CSS（計画 B で拡充）
    icons/                    # 計画 B
    template/standard.potx    # 標準テンプレート（Task 3 で生成してコミット）
  tools/make_standard_template.py
  tests/
    conftest.py
    test_env.py  test_theme.py  test_template.py  test_measure.py
    test_build.py  test_charts.py  test_check.py  test_variants.py
    test_initdir.py  test_cli_build.py
```

モデルの形（Task 4 で作り、以降が使う）。座標は px（スライド左上が原点）。

```python
# slide = {"index": int, "layout": str, "bg": "RRGGBB", "elements": [el, ...]}
# el 共通: {"kind": "text|shape|line|image|table|chart", "idx": int,
#           "rect": {"x","y","w","h"}, "role": str|None, "ph": str|None,
#           "bg": "RRGGBB",              # その要素の背後の実効色（コントラスト検査用）
#           "overlap": bool, "chrome": bool}
# text:  "box": {"x","y","w","h"}, "overflow": bool,
#        "paras": [{"align": "left|center|right|justify", "bullet": bool,
#                   "lh": float, "mb": float,
#                   "runs": [{"text","size_px","bold","italic","color"} | {"br": True}]}]
# shape: "shape": "rect|round|ellipse|triangle", "fill": {"hex","a"}|None,
#        "line": {"hex","w"}|None, "radius_px": float
# line:  "fill": {"hex","a"}, "arrow": bool, "reverse": bool
# image: "src": file URL, "alt": str
# table: "table": {"xs": [px...], "rows": [{"h": px, "cells": [
#           {"c0","c1","rowspan","fill","borders":{"l","r","t","b"},"pad":{"l","r","t","b"},
#            "valign","paras"}]}]}
# chart: "chart": {"type","categories","series":[{"name","values"}],
#                  "highlight","fmt","totals"}
```

---

### Task 1: 旧スキルの撤去・足場・環境（run.py と env）

**Files:**
- Delete: `skills/pptx-deck/` 配下の旧ファイルすべて（`git rm -r`）
- Create: `skills/pptx-deck/run.py`, `requirements.txt`, `requirements-dev.txt`, `pytest.ini`
- Create: `skills/pptx-deck/pptx_deck/__init__.py`, `__main__.py`, `paths.py`, `env.py`, `cli.py`
- Create: `skills/pptx-deck/tests/conftest.py`, `tests/test_env.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `paths.home_dir() -> Path`, `paths.venv_dir() -> Path`, `paths.venv_python() -> Path`, `paths.temp_dir(name: str) -> Path`（`tempfile.gettempdir()/pptx-deck/<name>`、作成済み）、`paths.SKILL_DIR`、`paths.ASSETS`
- Produces: `env.status() -> dict`（`{"venv": bool, "modules": {名前: bool}, "chromium": bool}`）、`env.setup(yes: bool) -> int`
- Produces: `python run.py <cmd>`: venv がなければ終了コード 3 と案内（`setup --yes`）を出す。

- [ ] **Step 1: 旧スキルを撤去する**

```bash
cd C:/Users/sioay/OneDrive/github/pptx-deck
git rm -r -q skills/pptx-deck
rm -rf skills/pptx-deck
mkdir -p skills/pptx-deck/pptx_deck skills/pptx-deck/tests skills/pptx-deck/assets/web skills/pptx-deck/assets/template skills/pptx-deck/tools
```

- [ ] **Step 2: 設定ファイルを作る**

`skills/pptx-deck/requirements.txt`:

```
python-pptx==1.0.2
playwright==1.52.0
pymupdf==1.28.2
lxml>=5
```

`skills/pptx-deck/requirements-dev.txt`:

```
-r requirements.txt
pytest>=8
```

`skills/pptx-deck/pytest.ini`:

```ini
[pytest]
testpaths = tests
addopts = -q
```

`.gitignore` に追記:

```
.venv/
.pytest_cache/
```

- [ ] **Step 3: 失敗するテストを書く**

`skills/pptx-deck/tests/conftest.py`:

```python
import sys
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL))


@pytest.fixture
def home(tmp_path, monkeypatch):
    """共通の場所を一時フォルダに差し替える（本物の venv を触らない）。"""
    monkeypatch.setenv("PPTX_DECK_HOME", str(tmp_path / "home"))
    return tmp_path / "home"
```

`skills/pptx-deck/tests/test_env.py`:

```python
import os
import subprocess
import sys
from pathlib import Path

from pptx_deck import env, paths

SKILL = Path(__file__).resolve().parent.parent


def test_home_dir_honors_env(home):
    assert paths.home_dir() == home
    assert paths.venv_python() == home / "venv" / "Scripts" / "python.exe"


def test_temp_dir_is_under_os_temp():
    import tempfile
    d = paths.temp_dir("t1")
    assert d.is_dir()
    assert Path(tempfile.gettempdir()) in d.parents


def test_status_without_venv(home):
    st = env.status()
    assert st["venv"] is False
    assert st["chromium"] is False


def _run(args, home):
    e = {**os.environ, "PPTX_DECK_HOME": str(home)}
    return subprocess.run([sys.executable, str(SKILL / "run.py"), *args],
                          env=e, capture_output=True, text=True, encoding="utf-8")


def test_run_py_without_venv_asks_for_consent(home):
    r = _run(["doctor"], home)
    assert r.returncode == 3
    assert "setup --yes" in r.stdout
    assert not (home / "venv").exists()


def test_setup_without_yes_does_not_create(home):
    r = _run(["setup"], home)
    assert r.returncode == 3
    assert not (home / "venv").exists()
```

- [ ] **Step 4: 失敗を確認する**（パッケージがまだなく、システムの Python で実行する。pytest が無ければ `python -m pip install --user pytest` ではなく、Step 6 の後で venv で実行する）

Run: `cd skills/pptx-deck && python -m pytest tests/test_env.py -x` 
Expected: FAIL（`ModuleNotFoundError: pptx_deck`）。pytest が無い場合は、Step 6 に進む。

- [ ] **Step 5: 実装する**

`skills/pptx-deck/pptx_deck/__init__.py`:

```python
"""pptx-deck: 承認済み HTML から、テンプレートを土台に PPTX を作る。"""
```

`skills/pptx-deck/pptx_deck/__main__.py`:

```python
import sys

from .cli import main

sys.exit(main(sys.argv[1:]))
```

`skills/pptx-deck/pptx_deck/paths.py`:

```python
"""場所の決定。標準ライブラリのみ（run.py から venv なしで使う）。"""
import os
import tempfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
ASSETS = SKILL_DIR / "assets"


def home_dir() -> Path:
    override = os.environ.get("PPTX_DECK_HOME")
    if override:
        return Path(override)
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        raise RuntimeError("LOCALAPPDATA が未設定です（Windows 専用です）")
    return Path(base) / "pptx-deck"


def venv_dir() -> Path:
    return home_dir() / "venv"


def venv_python() -> Path:
    return venv_dir() / "Scripts" / "python.exe"


def temp_dir(name: str) -> Path:
    """OS の一時フォルダ配下の作業場所（確認用 PNG など一過性のもの）。"""
    d = Path(tempfile.gettempdir()) / "pptx-deck" / name
    d.mkdir(parents=True, exist_ok=True)
    return d
```

`skills/pptx-deck/pptx_deck/env.py`:

```python
"""仮想環境の状態確認と作成。標準ライブラリのみ。"""
import subprocess
import sys
import venv

from . import paths

# import 名 → pip 名
MODULES = {"pptx": "python-pptx", "playwright": "playwright", "fitz": "pymupdf", "lxml": "lxml"}

_CHROMIUM_PROBE = (
    "from playwright.sync_api import sync_playwright as s;"
    "p=s().start();import os;print(os.path.exists(p.chromium.executable_path));p.stop()"
)


def _py(code: str) -> subprocess.CompletedProcess:
    return subprocess.run([str(paths.venv_python()), "-c", code],
                          capture_output=True, text=True, timeout=120)


def status() -> dict:
    st = {"venv": paths.venv_python().exists(), "modules": {}, "chromium": False}
    if not st["venv"]:
        st["modules"] = {m: False for m in MODULES}
        return st
    for m in MODULES:
        st["modules"][m] = _py(f"import {m}").returncode == 0
    if st["modules"]["playwright"]:
        r = _py(_CHROMIUM_PROBE)
        st["chromium"] = r.returncode == 0 and r.stdout.strip() == "True"
    return st


def ready(st: dict | None = None) -> bool:
    st = st or status()
    return st["venv"] and all(st["modules"].values()) and st["chromium"]


def setup(yes: bool) -> int:
    target = paths.venv_dir()
    if not yes:
        print(f"仮想環境が必要です。作成先: {target}")
        print("作成内容: python -m venv ＋ requirements.txt の導入 ＋ Playwright の chromium（数百 MB）。")
        print("利用者の承認を得てから `python run.py setup --yes` を実行してください。")
        return 3
    target.parent.mkdir(parents=True, exist_ok=True)
    if not paths.venv_python().exists():
        venv.EnvBuilder(with_pip=True).create(target)
    py = str(paths.venv_python())
    req = str(paths.SKILL_DIR / "requirements.txt")
    for cmd in ([py, "-m", "pip", "install", "-r", req],
                [py, "-m", "playwright", "install", "chromium"]):
        rc = subprocess.call(cmd)
        if rc != 0:
            print(f"失敗: {' '.join(cmd)}", file=sys.stderr)
            return rc
    print("環境を作成しました:", target)
    return 0
```

`skills/pptx-deck/pptx_deck/cli.py`（この時点は doctor のみ。以降のタスクで足す）:

```python
import argparse
import glob
import json
import os
import shutil
import sys

from . import env, paths


def _font_installed() -> bool:
    fonts = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
    return bool(glob.glob(os.path.join(fonts, "BIZ-UDPGothic*")))


def cmd_doctor(args) -> int:
    st = env.status()
    out = {
        "venv": str(paths.venv_dir()),
        "status": st,
        "libreoffice": bool(shutil.which("soffice") or os.path.exists(
            r"C:\Program Files\LibreOffice\program\soffice.exe")),
        "font_biz_udp_gothic": _font_installed(),
    }
    warnings = []
    if not out["libreoffice"]:
        warnings.append("LibreOffice がありません。確認用の画像が作れません。")
    if not out["font_biz_udp_gothic"]:
        warnings.append("BIZ UDPゴシックが未導入です。計測は代替フォントで行うため、折り返しが PowerPoint とずれる場合があります。")
    out["warnings"] = warnings
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if env.ready(st) else 1


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="pptx-deck")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor").set_defaults(fn=cmd_doctor)
    args = ap.parse_args(argv)
    return args.fn(args)
```

`skills/pptx-deck/run.py`:

```python
"""入口。標準ライブラリのみ。共通の仮想環境の Python で pptx_deck を実行する。

  python run.py setup [--yes]   # 仮想環境の作成（--yes は利用者の承認後）
  python run.py <サブコマンド>   # それ以外は venv の Python に渡す
"""
import os
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent
sys.path.insert(0, str(SKILL))

from pptx_deck import env, paths  # noqa: E402  標準ライブラリのみで動く


def main(argv: list[str]) -> int:
    if argv[:1] == ["setup"]:
        return env.setup(yes="--yes" in argv)
    py = paths.venv_python()
    if not py.exists():
        print(f"仮想環境がありません: {paths.venv_dir()}")
        print("利用者に「環境を作ってよいか」を確認し、承認後に `python run.py setup --yes` を実行してください。")
        return 3
    e = {**os.environ, "PYTHONPATH": str(SKILL), "PYTHONUTF8": "1"}
    return subprocess.call([str(py), "-m", "pptx_deck", *argv], env=e)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 6: 利用者の承認を得て、本物の仮想環境を作る**

承認の取り方: 利用者に「`%LOCALAPPDATA%\pptx-deck\venv` に Python の仮想環境と chromium（数百 MB）を導入してよいか」を聞く。承認後:

```bash
cd skills/pptx-deck
python run.py setup --yes
PY="$LOCALAPPDATA/pptx-deck/venv/Scripts/python.exe"
"$PY" -m pip install -r requirements-dev.txt
```

Expected: `環境を作成しました: ...`。`pip install` が Python 3.14 用の wheel がなくて失敗した場合（playwright の依存 greenlet など）は、勝手に別の Python に切り替えず、失敗のログを利用者に示して、使う Python（例: 3.12）を決めてもらう。決まったら `env.setup` が `sys.executable` で venv を作る仕様のため、その Python で `run.py setup --yes` を実行し直す。

- [ ] **Step 7: テストを実行する**

Run: `"$PY" -m pytest tests/test_env.py`
Expected: 5 passed。続けて `python run.py doctor` が JSON を出し、`font_biz_udp_gothic` が `false` なら警告が出る（この PC は P 付きが未導入）。

- [ ] **Step 8: コミット**

```bash
git add -A
git commit -m "feat: 旧 pptx-deck を撤去し、新スキルの足場と共通 venv の確認・作成を追加"
```

---

### Task 2: 配色（theme）

**Files:**
- Create: `skills/pptx-deck/pptx_deck/theme.py`
- Test: `skills/pptx-deck/tests/test_theme.py`

**Interfaces:**
- Produces: `theme.PRESETS: dict[str, str]`、`theme.resolve(arg: str) -> str`（プリセット名または `#RRGGBB` → 大文字の `#RRGGBB`。不正は `ValueError`）、`theme.contrast(a: str, b: str) -> float`（`#RRGGBB` 同士）、`theme.mix(a, b, t) -> str`、`theme.derive(base: str) -> Palette`、`theme.theme_css(p: Palette) -> str`
- `Palette`（frozen dataclass、値はすべて `#RRGGBB`）: `accent, accent_dark, accent_mid, accent_light, emphasis, text, text_sub, line, bg_soft`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_theme.py`:

```python
import pytest

from pptx_deck import theme


def test_contrast_black_white():
    assert theme.contrast("#000000", "#FFFFFF") == pytest.approx(21.0, abs=0.01)


def test_resolve_preset_and_hex():
    assert theme.resolve("navy") == "#1F3A5F"
    assert theme.resolve("#1e6b52") == "#1E6B52"


@pytest.mark.parametrize("bad", ["1E6B52", "#12345", "red", "#GGGGGG"])
def test_resolve_rejects_bad(bad):
    with pytest.raises(ValueError):
        theme.resolve(bad)


@pytest.mark.parametrize("base", ["#FFFF00", "#1F3A5F", "#FFFFFF", "#00FF88", "#808080"])
def test_derived_accent_is_readable_on_white(base):
    p = theme.derive(base)
    assert theme.contrast(p.accent, "#FFFFFF") >= 4.5
    assert theme.contrast(p.emphasis, "#FFFFFF") >= 4.5
    assert theme.contrast(p.text, "#FFFFFF") >= 7


def test_emphasis_is_a_different_hue():
    for name, hexv in theme.PRESETS.items():
        p = theme.derive(hexv)
        assert theme.hue_distance(p.accent, p.emphasis) >= 60 or theme.is_gray(p.accent), name


def test_gray_base_gets_orange_emphasis():
    assert theme.derive("#3A3F47").emphasis == "#B85A0B"


def test_lighter_tones_are_ordered():
    p = theme.derive("#1F3A5F")
    L = theme.luminance
    assert L(p.accent_dark) < L(p.accent) < L(p.accent_mid) < L(p.accent_light)


def test_theme_css_defines_variables():
    css = theme.theme_css(theme.derive("#1F3A5F"))
    for var in ("--accent", "--accent-dark", "--accent-mid", "--accent-light",
                "--emphasis", "--text", "--text-sub", "--line", "--bg-soft"):
        assert var + ":" in css
```

- [ ] **Step 2: 失敗を確認する**

Run: `"$PY" -m pytest tests/test_theme.py`
Expected: FAIL（`cannot import name 'theme'`）

- [ ] **Step 3: 実装する**

`pptx_deck/theme.py`:

```python
"""配色。基調色 1 つから、薄色・濃色・強調色を導く。色は #RRGGBB（大文字）。"""
import colorsys
import re
from dataclasses import dataclass

PRESETS = {"navy": "#1F3A5F", "green": "#1E6B52", "gray": "#3A3F47"}
_EMPHASIS = ["#B85A0B", "#0B6E99", "#7A3E9D", "#1E7A4A"]
_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


@dataclass(frozen=True)
class Palette:
    accent: str
    accent_dark: str
    accent_mid: str
    accent_light: str
    emphasis: str
    text: str
    text_sub: str
    line: str
    bg_soft: str


def _rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _hex(rgb) -> str:
    return "#%02X%02X%02X" % tuple(round(c) for c in rgb)


def mix(a: str, b: str, t: float) -> str:
    return _hex(tuple(x + (y - x) * t for x, y in zip(_rgb(a), _rgb(b))))


def luminance(h: str) -> float:
    def f(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (f(c) for c in _rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _hls(h: str):
    r, g, b = (c / 255 for c in _rgb(h))
    return colorsys.rgb_to_hls(r, g, b)


def is_gray(h: str) -> bool:
    _, l, s = _hls(h)
    return s < 0.15 or l > 0.97 or l < 0.03


def hue_distance(a: str, b: str) -> float:
    d = abs(_hls(a)[0] * 360 - _hls(b)[0] * 360) % 360
    return min(d, 360 - d)


def resolve(arg: str) -> str:
    if arg in PRESETS:
        return PRESETS[arg]
    if not _HEX.match(arg):
        raise ValueError(f"色はプリセット名（{', '.join(PRESETS)}）か #RRGGBB で指定してください: {arg}")
    return arg.upper()


def derive(base: str) -> Palette:
    accent = resolve(base)
    while contrast(accent, "#FFFFFF") < 4.5:
        accent = mix(accent, "#000000", 0.1)
    if is_gray(accent):
        emphasis = _EMPHASIS[0]
    else:
        emphasis = next((c for c in _EMPHASIS
                         if hue_distance(c, accent) >= 60 and contrast(c, "#FFFFFF") >= 4.5),
                        "#404040")
    return Palette(
        accent=accent,
        accent_dark=mix(accent, "#000000", 0.35),
        accent_mid=mix(accent, "#FFFFFF", 0.45),
        accent_light=mix(accent, "#FFFFFF", 0.88),
        emphasis=emphasis,
        text="#1A1A1A",
        text_sub="#595959",
        line="#BFBFBF",
        bg_soft="#F2F2F2",
    )


def theme_css(p: Palette) -> str:
    rows = [("accent", p.accent), ("accent-dark", p.accent_dark), ("accent-mid", p.accent_mid),
            ("accent-light", p.accent_light), ("emphasis", p.emphasis), ("text", p.text),
            ("text-sub", p.text_sub), ("line", p.line), ("bg-soft", p.bg_soft)]
    body = "".join(f"  --{k}: {v};\n" for k, v in rows)
    return f":root {{\n{body}}}\n"
```

- [ ] **Step 4: テストを実行する**

Run: `"$PY" -m pytest tests/test_theme.py`
Expected: すべて PASS。`#808080` の `is_gray` 判定、`#FFFFFF` の accent が暗くなって 4.5:1 になること（ループ）を確認。

- [ ] **Step 5: コミット**

```bash
git add skills/pptx-deck/pptx_deck/theme.py skills/pptx-deck/tests/test_theme.py
git commit -m "feat: 基調色から配色を導く theme を追加"
```

---

### Task 3: テンプレートの解析と標準テンプレート・画像化

**Files:**
- Create: `skills/pptx-deck/pptx_deck/pptxutil.py`, `render.py`, `template.py`
- Create: `skills/pptx-deck/tools/make_standard_template.py`
- Create（生成物をコミット）: `skills/pptx-deck/assets/template/standard.potx`
- Test: `skills/pptx-deck/tests/test_template.py`

**Interfaces:**
- Consumes: `paths.temp_dir`
- Produces: `pptxutil.PX = 9525`、`pptxutil.FONT = "BIZ UDPゴシック"`、`pptxutil.emu(px) -> Emu`、`pptxutil.drop_all_slides(prs)`
- Produces: `render.find_soffice() -> str`、`render.pptx_to_pngs(pptx: Path, out_dir: Path, width_px: int = 1280, stem: str = "slide") -> list[Path]`
- Produces: `template.Rect`（`x, y, w, h: float`、`to_dict()`/`from_dict()`）、`template.TemplateInfo`（`cover: int`, `body: int`, `closing: int | None`, `area: Rect`, `title: Rect`, `cover_title: Rect`, `cover_subtitle: Rect | None`, `closing_title: Rect`（裏表紙の題の位置。裏表紙がなければ本文のタイトルの位置）, `keepout: list[Rect]`, `notes: list[str]`、`to_dict()`/`from_dict()`）、`template.open_template(path) -> Presentation`、`template.analyze(path) -> TemplateInfo`、`template.render_underlays(path, info, out_dir: Path) -> str`（`bg-cover.png`・`bg-body.png`・`bg-closing.png` を `out_dir` に書き、本文の下地色 `#RRGGBB` を返す）、`template.layout_css(info, bg_hex) -> str`

- [ ] **Step 1: 小道具と画像化を書く**

`pptx_deck/pptxutil.py`:

```python
from pptx.dml.color import RGBColor
from pptx.oxml.ns import qn
from pptx.util import Emu, Pt

PX = 9525
FONT = "BIZ UDPゴシック"
SLIDE_W_EMU = 12192000  # 13.333in
SLIDE_H_EMU = 6858000   # 7.5in


def emu(px: float) -> Emu:
    return Emu(round(px * PX))


def rgb(hex6: str) -> RGBColor:
    return RGBColor.from_string(hex6.lstrip("#").upper())


def drop_all_slides(prs) -> None:
    """テンプレートの既存スライドをすべて外す（マスターとレイアウトは残す）。"""
    lst = prs.slides._sldIdLst
    for sld in list(lst):
        prs.part.drop_rel(sld.rId)
        lst.remove(sld)


def set_run_font(run, size_px: float, bold: bool, italic: bool, color_hex: str) -> None:
    f = run.font
    f.size = Pt(round(size_px * 0.75 * 2) / 2)  # 0.5pt 刻み
    f.bold = bold
    f.italic = italic
    f.color.rgb = rgb(color_hex)
    f.name = FONT  # a:latin
    rPr = run._r.get_or_add_rPr()
    latin = rPr.find(qn("a:latin"))
    ea = rPr.find(qn("a:ea"))
    if ea is None:
        from lxml import etree
        ea = etree.Element(qn("a:ea"))
        latin.addnext(ea)
    ea.set("typeface", FONT)
```

`pptx_deck/render.py`:

```python
"""PPTX → PDF（LibreOffice）→ PNG（pymupdf）。一時ファイルは tempfile で作る。"""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def find_soffice() -> str:
    found = shutil.which("soffice")
    if found:
        return found
    for p in (r"C:\Program Files\LibreOffice\program\soffice.exe",
              r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"):
        if os.path.exists(p):
            return p
    raise RuntimeError("LibreOffice が見つかりません（確認用の画像が作れません）")


def pptx_to_pngs(pptx: Path, out_dir: Path, width_px: int = 1280, stem: str = "slide") -> list[Path]:
    import fitz  # pymupdf

    soffice = find_soffice()
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pptx-deck-so-") as td:
        profile = Path(td) / "profile"
        cmd = [soffice, f"-env:UserInstallation={profile.as_uri()}", "--headless",
               "--convert-to", "pdf", "--outdir", td, str(pptx)]
        subprocess.run(cmd, check=True, capture_output=True, timeout=300)
        pdf = Path(td) / (Path(pptx).stem + ".pdf")
        doc = fitz.open(str(pdf))
        paths = []
        for i, page in enumerate(doc):
            zoom = width_px / page.rect.width
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            p = out_dir / f"{stem}-{i + 1:02d}.png"
            pix.save(str(p))
            paths.append(p)
        doc.close()
    return paths
```

- [ ] **Step 2: 標準テンプレートの生成スクリプトを書く**

`tools/make_standard_template.py`:

```python
"""標準テンプレート assets/template/standard.potx を生成する。再生成は:
   python -m tools.make_standard_template  （venv の Python、skills/pptx-deck で実行）
レイアウトは 表紙・本文・裏表紙 の 3 つ。装飾は無彩色の細線だけ（どの配色にも合う）。"""
import io
import zipfile
from pathlib import Path

from pptx import Presentation
from pptx.enum.shapes import PP_PLACEHOLDER as T
from pptx.oxml import parse_xml

PX = 9525
OUT = Path(__file__).resolve().parent.parent / "assets" / "template" / "standard.potx"
NS = ('xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
      'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"')

FOOT = {T.DATE: (800, 676, 300, 28), T.FOOTER: (64, 676, 700, 28), T.SLIDE_NUMBER: (1136, 676, 80, 28)}
GEOM = {
    "表紙": {T.CENTER_TITLE: (96, 250, 1088, 120), T.SUBTITLE: (96, 390, 1088, 60), **FOOT},
    "本文": {T.TITLE: (64, 40, 1152, 80), T.OBJECT: (64, 150, 1152, 490), **FOOT},
    "裏表紙": {T.TITLE: (96, 300, 1088, 100), **FOOT},
}
# レイアウト名 → (線の始点 x, y, 長さ)
LINES = {"表紙": (96, 236, 120), "本文": (64, 668, 1152), "裏表紙": (96, 286, 120)}


def _line_xml(shape_id, x, y, length):
    return parse_xml(
        f'<p:cxnSp {NS}><p:nvCxnSpPr><p:cNvPr id="{shape_id}" name="罫線"/><p:cNvCxnSpPr/>'
        f'<p:nvPr userDrawn="1"/></p:nvCxnSpPr><p:spPr><a:xfrm><a:off x="{x * PX}" y="{y * PX}"/>'
        f'<a:ext cx="{length * PX}" cy="0"/></a:xfrm><a:prstGeom prst="line"><a:avLst/></a:prstGeom>'
        f'<a:ln w="9525"><a:solidFill><a:srgbClr val="BFBFBF"/></a:solidFill></a:ln></p:spPr></p:cxnSp>')


def _place(shape, geom):
    x, y, w, h = geom
    shape.left, shape.top, shape.width, shape.height = (round(v * PX) for v in (x, y, w, h))


def make(out: Path = OUT) -> Path:
    prs = Presentation()
    prs.slide_width, prs.slide_height = 12192000, 6858000
    for ph in prs.slide_master.placeholders:
        t = ph.placeholder_format.type
        g = {T.TITLE: (64, 40, 1152, 80), T.BODY: (64, 150, 1152, 490), **FOOT}.get(t)
        if g:
            _place(ph, g)
    layouts = list(prs.slide_layouts)
    keep = {0: "表紙", 1: "本文", 5: "裏表紙"}  # 既定テンプレートの Title Slide / Title and Content / Title Only
    kept = {name: layouts[i] for i, name in keep.items()}
    for i, lay in enumerate(layouts):
        if i not in keep:
            prs.slide_layouts.remove(lay)
    for name, lay in kept.items():
        lay._element.cSld.set("name", name)
        for ph in lay.placeholders:
            g = GEOM[name].get(ph.placeholder_format.type)
            if g:
                _place(ph, g)
        x, y, length = LINES[name]
        lay.shapes._spTree.append(_line_xml(900, x, y, length))
    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(buf) as zin, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "[Content_Types].xml":
                data = data.replace(b"presentationml.presentation.main+xml",
                                    b"presentationml.template.main+xml")
            zout.writestr(item, data)
    return out


if __name__ == "__main__":
    print(make())
```

- [ ] **Step 3: 失敗するテストを書く**

`tests/test_template.py`:

```python
import io
import shutil
import zipfile
from pathlib import Path

import pytest
from pptx import Presentation
from pptx.util import Emu

from pptx_deck import paths, render, template
from pptx_deck.pptxutil import SLIDE_W_EMU

STANDARD = paths.ASSETS / "template" / "standard.potx"
has_soffice = pytest.mark.skipif(shutil.which("soffice") is None and not Path(
    r"C:\Program Files\LibreOffice\program\soffice.exe").exists(), reason="LibreOffice なし")


def _as_pptx(potx: Path, dst: Path, rename=None, drop=None) -> Path:
    """標準テンプレートから、利用者が持ってきそうな .pptx を作る（content-type を戻す）。"""
    buf = io.BytesIO()
    with zipfile.ZipFile(potx) as zin, zipfile.ZipFile(buf, "w") as zout:
        for it in zin.infolist():
            d = zin.read(it.filename)
            if it.filename == "[Content_Types].xml":
                d = d.replace(b"presentationml.template.main+xml", b"presentationml.presentation.main+xml")
            zout.writestr(it, d)
    buf.seek(0)
    prs = Presentation(buf)
    for lay in prs.slide_layouts:
        if rename and lay.name in rename:
            lay._element.cSld.set("name", rename[lay.name])
    if drop:
        for lay in list(prs.slide_layouts):
            if lay.name == drop:
                prs.slide_layouts.remove(lay)
    prs.save(dst)
    return dst


def test_standard_template_exists_and_opens_as_potx():
    assert STANDARD.exists()
    prs = template.open_template(STANDARD)  # .potx を開ける（Review Focus 1）
    assert [l.name for l in prs.slide_layouts] == ["表紙", "本文", "裏表紙"]


def test_analyze_standard():
    info = template.analyze(STANDARD)
    assert (info.cover, info.body, info.closing) == (0, 1, 2)
    assert info.area.to_dict() == {"x": 64, "y": 150, "w": 1152, "h": 490}
    assert info.title.y == 40
    assert any(r.y >= 670 for r in info.keepout)       # フッター・ページ番号の領域
    assert info.cover_subtitle is not None
    assert info.closing_title.y == 300                  # 裏表紙の題の位置（プレビューと PPTX をそろえる）
    assert info.notes == []


def test_analyze_pptx_with_english_names(tmp_path):
    p = _as_pptx(STANDARD, tmp_path / "u.pptx",
                 rename={"表紙": "Title Slide", "本文": "Title and Content", "裏表紙": "Closing"})
    info = template.analyze(p)
    assert (info.cover, info.body, info.closing) == (0, 1, 2)


def test_missing_closing_falls_back_with_note(tmp_path):
    p = _as_pptx(STANDARD, tmp_path / "u.pptx", drop="裏表紙")
    info = template.analyze(p)
    assert info.closing is None                         # Review Focus 4
    assert any("裏表紙" in n for n in info.notes)
    assert info.closing_title == info.title             # 本文のレイアウトで代えるので、題は本文の位置


def test_non_169_template_is_rejected(tmp_path):
    prs = Presentation()  # 既定は 4:3（10in × 7.5in）
    src = tmp_path / "old.pptx"
    prs.save(src)
    with pytest.raises(ValueError, match="13.33"):      # Review Focus 2
        template.analyze(src)


def test_info_roundtrip():
    info = template.analyze(STANDARD)
    assert template.TemplateInfo.from_dict(info.to_dict()) == info


def test_layout_css_has_area_and_backgrounds():
    info = template.analyze(STANDARD)
    css = template.layout_css(info, "#FFFFFF")
    for token in ("--area-x: 64px", "--title-y: 40px", "--cover-title-x: 96px", "--closing-title-y: 300px",
                  "_template/bg-cover.png", "_template/bg-body.png", "--bg: #FFFFFF"):
        assert token in css


@has_soffice
def test_render_underlays(tmp_path):
    info = template.analyze(STANDARD)
    bg = template.render_underlays(STANDARD, info, tmp_path)
    for name in ("bg-cover.png", "bg-body.png", "bg-closing.png"):
        assert (tmp_path / name).exists()
    assert bg == "#FFFFFF"                              # 標準テンプレートの本文は白


@has_soffice
def test_pptx_to_pngs_uses_os_temp_and_returns_files(tmp_path):
    prs = template.open_template(STANDARD)
    prs.slides.add_slide(prs.slide_layouts[1])
    src = tmp_path / "x.pptx"
    prs.save(src)
    pngs = render.pptx_to_pngs(src, tmp_path / "out", width_px=640)
    assert len(pngs) == 1 and pngs[0].exists()
```

- [ ] **Step 4: 標準テンプレートを生成し、テストの失敗を確認する**

```bash
"$PY" -m tools.make_standard_template
"$PY" -m pytest tests/test_template.py
```

Expected: 生成は `.../standard.potx` を表示。pytest は `template` が未実装で FAIL。

- [ ] **Step 5: 実装する**

`pptx_deck/template.py`:

```python
"""利用者（または標準）のテンプレートを開いて、使うレイアウトと領域を決める。"""
import io
import re
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

from pptx import Presentation
from pptx.enum.shapes import PP_PLACEHOLDER as T

from . import paths
from .pptxutil import PX, SLIDE_H_EMU, SLIDE_W_EMU, drop_all_slides
from .render import pptx_to_pngs

_COVER = re.compile(r"(title slide|(?<!裏)表紙|cover|タイトル ?スライド)", re.I)
_CLOSING = re.compile(r"(裏表紙|closing|\bend\b|thank|結び)", re.I)
_BODY = re.compile(r"(title and content|本文|body|タイトルとコンテンツ|content)", re.I)


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    w: float
    h: float

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Rect":
        return Rect(**d)


@dataclass(frozen=True)
class TemplateInfo:
    cover: int
    body: int
    closing: int | None
    area: Rect
    title: Rect
    cover_title: Rect
    cover_subtitle: Rect | None
    closing_title: Rect
    keepout: tuple[Rect, ...] = ()
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "cover": self.cover, "body": self.body, "closing": self.closing,
            "area": self.area.to_dict(), "title": self.title.to_dict(),
            "cover_title": self.cover_title.to_dict(),
            "cover_subtitle": self.cover_subtitle.to_dict() if self.cover_subtitle else None,
            "closing_title": self.closing_title.to_dict(),
            "keepout": [r.to_dict() for r in self.keepout], "notes": list(self.notes),
        }

    @staticmethod
    def from_dict(d: dict) -> "TemplateInfo":
        sub = d["cover_subtitle"]
        return TemplateInfo(
            cover=d["cover"], body=d["body"], closing=d["closing"],
            area=Rect.from_dict(d["area"]), title=Rect.from_dict(d["title"]),
            cover_title=Rect.from_dict(d["cover_title"]),
            cover_subtitle=Rect.from_dict(sub) if sub else None,
            closing_title=Rect.from_dict(d["closing_title"]),
            keepout=tuple(Rect.from_dict(r) for r in d["keepout"]), notes=tuple(d["notes"]))


def open_template(path) -> Presentation:
    """.pptx / .potx を開く。.potx は content-type を .pptx 相当に直して開く。"""
    path = Path(path)
    if path.suffix.lower() == ".potx":
        buf = io.BytesIO()
        with zipfile.ZipFile(path) as zin, zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
            for it in zin.infolist():
                data = zin.read(it.filename)
                if it.filename == "[Content_Types].xml":
                    data = data.replace(b"presentationml.template.main+xml",
                                        b"presentationml.presentation.main+xml")
                zout.writestr(it, data)
        buf.seek(0)
        prs = Presentation(buf)
    else:
        prs = Presentation(str(path))
    if abs(prs.slide_width - SLIDE_W_EMU) > SLIDE_W_EMU * 0.01 or \
            abs(prs.slide_height - SLIDE_H_EMU) > SLIDE_H_EMU * 0.01:
        raise ValueError(
            "テンプレートは 13.33×7.5in（16:9）のみ対応です。"
            f"実際: {prs.slide_width / 914400:.2f}×{prs.slide_height / 914400:.2f}in")
    return prs


def _rect(shape) -> Rect:
    return Rect(shape.left / PX, shape.top / PX, shape.width / PX, shape.height / PX)


def _phs(layout, *types):
    return [p for p in layout.placeholders if p.placeholder_format.type in types]


def _pick(prs, name_re, pred=None):
    for i, lay in enumerate(prs.slide_layouts):
        if name_re.search(lay.name):
            return i
    if pred:
        for i, lay in enumerate(prs.slide_layouts):
            if pred(lay):
                return i
    return None


def analyze(path) -> TemplateInfo:
    prs = open_template(path)
    L = list(prs.slide_layouts)
    notes = []
    body = _pick(prs, _BODY, lambda l: _phs(l, T.TITLE) and _phs(l, T.BODY, T.OBJECT))
    if body is None:
        raise ValueError("本文に使えるレイアウト（タイトルと本文の領域があるもの）がありません")
    cover = _pick(prs, _COVER, lambda l: bool(_phs(l, T.CENTER_TITLE)))
    if cover is None:
        cover = body
        notes.append("表紙のレイアウトが見つかりません。本文のレイアウトで代えます。")
    closing = _pick(prs, _CLOSING)
    if closing is None:
        notes.append("裏表紙のレイアウトが見つかりません。本文のレイアウトで代えます。")
    b, c = L[body], L[cover]
    cl_titles = _phs(L[closing], T.TITLE, T.CENTER_TITLE) if closing is not None else []
    areas = _phs(b, T.BODY, T.OBJECT)
    area = _rect(areas[0]) if areas else Rect(64, 150, 1152, 490)
    title = _rect(_phs(b, T.TITLE)[0])
    ct = _phs(c, T.CENTER_TITLE, T.TITLE)
    cs = _phs(c, T.SUBTITLE)
    keepout = tuple(_rect(p) for p in _phs(b, T.SLIDE_NUMBER, T.FOOTER, T.DATE))
    return TemplateInfo(
        cover=cover, body=body, closing=closing, area=area, title=title,
        cover_title=_rect(ct[0]) if ct else title,
        cover_subtitle=_rect(cs[0]) if cs else None,
        closing_title=_rect(cl_titles[0]) if cl_titles else title,
        keepout=keepout, notes=tuple(notes))


def render_underlays(path, info: TemplateInfo, out_dir: Path) -> str:
    """表紙・本文・裏表紙の下地（背景・ロゴ・ヘッダー・フッター）を画像にする。本文の下地色を返す。"""
    import fitz

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    prs = open_template(path)
    drop_all_slides(prs)
    order = [("cover", info.cover), ("body", info.body)]
    if info.closing is not None:
        order.append(("closing", info.closing))
    for _, idx in order:
        prs.slides.add_slide(prs.slide_layouts[idx])
    work = paths.temp_dir("underlay")
    src = work / "underlay.pptx"
    prs.save(str(src))
    pngs = pptx_to_pngs(src, work / "png", stem="u")
    for (name, _), png in zip(order, pngs):
        (out_dir / f"bg-{name}.png").write_bytes(png.read_bytes())
    if info.closing is None:
        (out_dir / "bg-closing.png").write_bytes((out_dir / "bg-body.png").read_bytes())
    pix = fitz.Pixmap(str(out_dir / "bg-body.png"))
    px = min(int(info.area.x) + 8, pix.width - 1)
    py = min(int(info.area.y) + 8, pix.height - 1)
    r, g, b = pix.pixel(px, py)[:3]
    return "#%02X%02X%02X" % (r, g, b)


def layout_css(info: TemplateInfo, bg_hex: str) -> str:
    def v(prefix, r: Rect):
        return (f"  --{prefix}-x: {r.x:g}px;\n  --{prefix}-y: {r.y:g}px;\n"
                f"  --{prefix}-w: {r.w:g}px;\n  --{prefix}-h: {r.h:g}px;\n")
    root = f":root {{\n  --bg: {bg_hex};\n" + v("area", info.area) + v("title", info.title) \
        + v("cover-title", info.cover_title) + v("closing-title", info.closing_title)
    if info.cover_subtitle:
        root += v("cover-subtitle", info.cover_subtitle)
    root += "}\n"
    root += (".slide[data-layout=\"cover\"] { background-image: url(_template/bg-cover.png); }\n"
             ".slide[data-layout=\"closing\"] { background-image: url(_template/bg-closing.png); }\n"
             ".slide:not([data-layout=\"cover\"]):not([data-layout=\"closing\"]) "
             "{ background-image: url(_template/bg-body.png); }\n")
    return root
```

- [ ] **Step 6: テストを実行する**

Run: `"$PY" -m pytest tests/test_template.py`
Expected: すべて PASS（LibreOffice のテストを含む）。`test_standard_template_exists_and_opens_as_potx` が失敗する場合は、`make_standard_template.py` のレイアウト削除（`prs.slide_layouts.remove`）と名前の設定を見直す。

- [ ] **Step 7: 標準テンプレートの見た目を確認する**

```bash
"$PY" -c "from pptx_deck import template, paths; i=template.analyze(paths.ASSETS/'template'/'standard.potx'); print(template.render_underlays(paths.ASSETS/'template'/'standard.potx', i, paths.temp_dir('chk')))"
```

出力された色が `#FFFFFF` で、`%TEMP%\pptx-deck\chk\` ではなく、`bg-*.png` が渡した `out_dir`（ここでは `paths.temp_dir('chk')`）にあることを確認し、`bg-body.png` を Read で開いて、下端に細い罫線があることを目で確認する。

- [ ] **Step 8: コミット**

```bash
git add skills/pptx-deck
git commit -m "feat: テンプレートの解析（.potx/.pptx）・標準テンプレート・下地の画像化を追加"
```

---

### Task 4: 計測（measure）

**Files:**
- Create: `skills/pptx-deck/pptx_deck/measure.js`, `measure.py`
- Test: `skills/pptx-deck/tests/test_measure.py`

**Interfaces:**
- Produces: `measure.measure(html: Path) -> list[dict]`（上記「モデルの形」のスライドの配列。`section.slide` が 0 枚なら `ValueError`）、`measure.title_of(slide: dict) -> dict | None`
- HTML の約束（計画 B が使う）: 1 枚 = `<section class="slide" data-layout="…">`（1280×720px）。部品は `pp-text`・`pp-shape`・`pp-line`・`pp-image`・`pp-table`・`pp-chart`。`.pp-text` は直下に `<p>`／`<ul><li>`／インラインだけを持つ。表は `<table class="pp-table">`。`data-role`・`data-ph`（`title|subtitle`）・`data-shape`・`data-arrow="end"`・`data-overlap`・`data-chrome`・`data-chart`（JSON）を読む。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_measure.py`:

```python
import json
from pathlib import Path

import pytest

from pptx_deck import measure

HEAD = """<!doctype html><html lang="ja"><head><meta charset="utf-8"><style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Yu Gothic','Meiryo',sans-serif}
.slide{position:relative;width:1280px;height:720px;--bg:#FFFFFF;background:#FFFFFF}
.pp-text,.pp-shape,.pp-line,.pp-image,.pp-table,.pp-chart{position:absolute}
</style></head><body>"""


def write(tmp_path, body, name="t.html"):
    p = tmp_path / name
    p.write_text(HEAD + body + "</body></html>", encoding="utf-8")
    return p


def test_zero_slides_is_an_error(tmp_path):
    p = write(tmp_path, "<div>no slide</div>")
    with pytest.raises(ValueError, match="section.slide"):
        measure.measure(p)


def test_text_shape_line(tmp_path):
    p = write(tmp_path, """
<section class="slide" data-layout="content">
  <div class="pp-shape" data-shape="round" style="left:64px;top:150px;width:400px;height:200px;background:#1F3A5F;border-radius:12px"></div>
  <div class="pp-text" data-role="title" style="left:64px;top:40px;width:900px;font-size:28px;font-weight:700;color:#1A1A1A">結論を言い切る見出し</div>
  <div class="pp-text" data-role="body" style="left:80px;top:170px;width:360px;font-size:20px;color:#FFFFFF"><p>一段落目</p><ul><li>箇条A</li><li>箇条B</li></ul></div>
  <div class="pp-line" data-arrow="end" style="left:480px;top:250px;width:100px;height:2px;background:#595959"></div>
</section>""")
    [s] = measure.measure(p)
    assert s["layout"] == "content" and s["bg"] == "FFFFFF"
    kinds = [e["kind"] for e in s["elements"]]
    assert kinds == ["shape", "text", "text", "line"]
    shape, title, body, line = s["elements"]
    assert shape["shape"] == "round" and shape["fill"]["hex"] == "1F3A5F"
    assert shape["rect"] == {"x": 64, "y": 150, "w": 400, "h": 200}
    assert title["role"] == "title" and title["paras"][0]["runs"][0]["text"] == "結論を言い切る見出し"
    assert title["paras"][0]["runs"][0]["size_px"] == 28 and title["paras"][0]["runs"][0]["bold"]
    assert [p["bullet"] for p in body["paras"]] == [False, True, True]
    assert body["bg"] == "1F3A5F"                      # 背後の実効色（コントラスト検査用）
    assert line["arrow"] is True and measure.title_of(s) is title


def test_overflow_flag_and_long_japanese_title(tmp_path):
    long_title = "あ" * 60
    p = write(tmp_path, f"""
<section class="slide" data-layout="content">
  <div class="pp-text" data-role="title" style="left:64px;top:40px;width:300px;height:30px;font-size:28px">{long_title}</div>
</section>""")
    [s] = measure.measure(p)
    t = s["elements"][0]
    assert t["overflow"] is True                       # 枠 30px に収まらない
    assert t["box"]["h"] > 60                          # 複数行に折り返した実測の高さ


def test_data_flags_and_ph(tmp_path):
    p = write(tmp_path, """
<section class="slide" data-layout="cover">
  <div class="pp-text" data-ph="title" style="left:96px;top:250px;width:900px;font-size:40px">表題</div>
  <div class="pp-shape" data-overlap data-chrome style="left:0;top:0;width:10px;height:10px;background:#000"></div>
</section>""")
    [s] = measure.measure(p)
    t, sh = s["elements"]
    assert t["ph"] == "title" and measure.title_of(s) is t
    assert sh["overlap"] is True and sh["chrome"] is True


def test_color_mix_and_reverse_arrow(tmp_path):
    p = write(tmp_path, """
<section class="slide" data-layout="content" style="--acc:#1F3A5F">
  <div class="pp-shape" data-shape="ellipse" data-overlap style="left:100px;top:150px;width:200px;height:200px;background:color-mix(in srgb, var(--acc) 40%, transparent)"></div>
  <div class="pp-line" data-arrow="end" data-dir="rev" style="left:400px;top:250px;width:100px;background:#595959"></div>
</section>""")
    [s] = measure.measure(p)
    sh, ln = s["elements"]
    assert sh["shape"] == "ellipse" and sh["fill"]["hex"] == "1F3A5F" and abs(sh["fill"]["a"] - 0.4) < 0.02
    assert ln["reverse"] is True


def test_dark_slide_background_is_reported(tmp_path):
    p = write(tmp_path, """
<section class="slide" data-layout="content" style="--bg:#101820;background:#101820">
  <div class="pp-text" data-role="body" style="left:64px;top:150px;width:400px;font-size:20px;color:#000000">暗い下地</div>
</section>""")
    [s] = measure.measure(p)
    assert s["bg"] == "101820" and s["elements"][0]["bg"] == "101820"   # Review Focus 3 の元データ


def test_table(tmp_path):
    p = write(tmp_path, """
<section class="slide" data-layout="content">
<table class="pp-table" style="left:64px;top:150px;width:600px;border-collapse:collapse;font-size:20px">
<tr style="height:50px"><td style="width:200px;background:#1F3A5F;color:#fff;padding:8px">項目</td><td colspan="2" style="width:400px;border-bottom:2px solid #BFBFBF;padding:8px">見出し</td></tr>
<tr style="height:50px"><td style="padding:8px">A</td><td style="padding:8px">B</td><td style="padding:8px">C</td></tr>
</table></section>""")
    [s] = measure.measure(p)
    t = s["elements"][0]["table"]
    assert len(t["xs"]) == 4 and len(t["rows"]) == 2
    c = t["rows"][0]["cells"]
    assert (c[0]["c0"], c[0]["c1"]) == (0, 1) and (c[1]["c0"], c[1]["c1"]) == (1, 3)
    assert c[0]["fill"]["hex"] == "1F3A5F" and c[1]["borders"]["b"]["w"] == 2


def test_chart_and_image(tmp_path):
    (tmp_path / "i.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>')
    spec = {"type": "bar", "categories": ["A", "B"], "series": [{"name": "x", "values": [1, 2]}]}
    p = write(tmp_path, f"""
<section class="slide" data-layout="content">
<div class="pp-chart" data-chart='{json.dumps(spec)}' style="left:64px;top:150px;width:500px;height:300px"></div>
<img class="pp-image" data-role="icon" src="i.svg" alt="アイコン" style="left:600px;top:150px;width:40px;height:40px">
</section>""")
    [s] = measure.measure(p)
    ch, im = s["elements"]
    assert ch["chart"]["type"] == "bar"
    assert im["alt"] == "アイコン" and im["src"].startswith("file:///") and im["src"].endswith("i.svg")
```

- [ ] **Step 2: 失敗を確認する**

Run: `"$PY" -m pytest tests/test_measure.py`
Expected: FAIL（`measure` が未実装）

- [ ] **Step 3: 計測スクリプトを書く**

`pptx_deck/measure.js`（`page.evaluate` で実行する関数式。戻り値はスライドの配列）:

```javascript
() => {
  const px = (v) => parseFloat(v) || 0;
  const hex2 = (n) => Math.round(n).toString(16).padStart(2, '0').toUpperCase();
  const parseColor = (c) => {
    c = c || '';
    let m = /rgba?\(([^)]+)\)/.exec(c);
    if (m) {
      const [r, g, b, a = 1] = m[1].split(/[ ,\/]+/).filter(Boolean).map(Number);
      return { hex: hex2(r) + hex2(g) + hex2(b), a };
    }
    m = /color\(srgb ([^)]+)\)/.exec(c);       // color-mix() の結果は color(srgb r g b / a) で返る
    if (m) {
      const [r, g, b, a = 1] = m[1].split(/[ \/]+/).filter(Boolean).map(Number);
      return { hex: hex2(r * 255) + hex2(g * 255) + hex2(b * 255), a };
    }
    return null;
  };
  const slides = [...document.querySelectorAll('section.slide')];

  return slides.map((slide, si) => {
    const sr = slide.getBoundingClientRect();
    const rel = (r) => ({ x: r.left - sr.left, y: r.top - sr.top, w: r.width, h: r.height });
    const bgVar = getComputedStyle(slide).getPropertyValue('--bg').trim();
    const slideBg = (bgVar || '#FFFFFF').replace('#', '').toUpperCase();
    const slideRgb = [0, 2, 4].map((i) => parseInt(slideBg.slice(i, i + 2), 16));

    // 背後の実効色: スライドの下地に、DOM 順で前にある塗りつぶし済みの面（pp-shape）のうち、
    // 対象の中心を含むものを順に重ねる。面と文字が兄弟要素でも、親子でも同じ結果になる。
    const els = [...slide.querySelectorAll('.pp-text,.pp-shape,.pp-line,.pp-image,.pp-table,.pp-chart')];
    const fills = els.map((e, i) => {
      if (!e.classList.contains('pp-shape')) return null;
      const f = parseColor(getComputedStyle(e).backgroundColor);
      return f && f.a > 0 ? { i, f, r: rel(e.getBoundingClientRect()) } : null;
    }).filter(Boolean);
    const effBg = (r, idx) => {
      const cx = r.x + r.w / 2, cy = r.y + r.h / 2;
      let base = slideRgb.slice();
      for (const s of fills) {
        if (s.i >= idx) break;
        if (cx < s.r.x || cx > s.r.x + s.r.w || cy < s.r.y || cy > s.r.y + s.r.h) continue;
        const rgb = [0, 2, 4].map((k) => parseInt(s.f.hex.slice(k, k + 2), 16));
        base = base.map((v, k) => v * (1 - s.f.a) + rgb[k] * s.f.a);
      }
      return base.map(hex2).join('');
    };

    const runsOf = (block) => {
      const runs = [];
      const walk = (node) => {
        if (node.nodeType === 3) {
          const t = node.textContent.replace(/\s+/g, ' ');
          if (!t.trim() && !runs.length) return;
          const cs = getComputedStyle(node.parentElement);
          runs.push({
            text: t, size_px: px(cs.fontSize), bold: parseInt(cs.fontWeight) >= 600,
            italic: cs.fontStyle === 'italic', color: (parseColor(cs.color) || { hex: '000000' }).hex,
          });
        } else if (node.nodeType === 1) {
          if (node.tagName === 'BR') { runs.push({ br: true }); return; }
          if (node.tagName === 'UL' || node.tagName === 'OL') return;
          node.childNodes.forEach(walk);
        }
      };
      block.childNodes.forEach(walk);
      const first = runs.find((r) => r.text !== undefined);
      if (first) first.text = first.text.replace(/^\s+/, '');
      const last = [...runs].reverse().find((r) => r.text !== undefined);
      if (last) last.text = last.text.replace(/\s+$/, '');
      return runs.filter((r) => r.br || r.text);
    };

    const alignOf = (cs) => {
      const a = cs.textAlign;
      return a === 'center' || a === 'right' || a === 'justify' ? a : a === 'end' ? 'right' : 'left';
    };

    const parasOf = (el) => {
      let blocks = [...el.querySelectorAll(':scope > p, :scope > ul > li, :scope > ol > li')];
      if (!blocks.length) blocks = [el];
      return blocks.map((b) => {
        const cs = getComputedStyle(b);
        const fs = px(cs.fontSize);
        const lh = cs.lineHeight === 'normal' ? 1.2 : px(cs.lineHeight) / fs;
        return {
          align: alignOf(cs), bullet: b.tagName === 'LI', lh, mb: px(cs.marginBottom),
          runs: runsOf(b),
        };
      }).filter((p) => p.runs.length);
    };

    const base = (el, kind, idx) => {
      const r = rel(el.getBoundingClientRect());
      return {
        kind, idx, rect: r, role: el.dataset.role || null, ph: el.dataset.ph || null,
        bg: effBg(r, idx), overlap: el.dataset.overlap !== undefined, chrome: el.dataset.chrome !== undefined,
      };
    };

    const borderOf = (cs, side) => {
      const w = px(cs['border' + side + 'Width']);
      const c = parseColor(cs['border' + side + 'Color']);
      return w > 0 && cs['border' + side + 'Style'] !== 'none' && c && c.a > 0 ? { hex: c.hex, w } : null;
    };

    const elements = els.map((el, idx) => {
      const cs = getComputedStyle(el);
      if (el.classList.contains('pp-text')) {
        const e = base(el, 'text', idx);
        const range = document.createRange();
        range.selectNodeContents(el);
        const cr = range.getBoundingClientRect();
        const crr = rel(cr);
        const padL = px(cs.paddingLeft), padR = px(cs.paddingRight);
        e.box = { x: e.rect.x + padL, y: crr.y, w: e.rect.w - padL - padR, h: crr.h };
        e.overflow = crr.y + crr.h > e.rect.y + e.rect.h + 2 || crr.x + crr.w > e.rect.x + e.rect.w + 2;
        e.paras = parasOf(el);
        return e;
      }
      if (el.classList.contains('pp-shape')) {
        const e = base(el, 'shape', idx);
        const f = parseColor(cs.backgroundColor);
        const radius = px(cs.borderTopLeftRadius);
        e.shape = el.dataset.shape || (radius > 0 ? 'round' : 'rect');
        e.fill = f && f.a > 0 ? f : null;
        e.line = borderOf(cs, 'Top');
        e.radius_px = radius;
        return e;
      }
      if (el.classList.contains('pp-line')) {
        const e = base(el, 'line', idx);
        e.fill = parseColor(cs.backgroundColor) || { hex: '000000', a: 1 };
        e.arrow = el.dataset.arrow === 'end';
        e.reverse = el.dataset.dir === 'rev';      // 矢印を逆向き（右→左、下→上）にする
        return e;
      }
      if (el.classList.contains('pp-image')) {
        const e = base(el, 'image', idx);
        e.src = el.currentSrc || el.getAttribute('src') || '';
        e.alt = el.getAttribute('alt') || '';
        return e;
      }
      if (el.classList.contains('pp-chart')) {
        const e = base(el, 'chart', idx);
        e.chart = JSON.parse(el.dataset.chart);
        return e;
      }
      // pp-table
      const e = base(el, 'table', idx);
      const cells = [...el.querySelectorAll('td,th')].map((c) => rel(c.getBoundingClientRect()));
      const xs = [...new Set(cells.flatMap((c) => [Math.round(c.x), Math.round(c.x + c.w)]))].sort((a, b) => a - b);
      const rows = [...el.rows].map((tr) => ({
        h: tr.getBoundingClientRect().height,
        cells: [...tr.cells].map((td) => {
          const r = rel(td.getBoundingClientRect());
          const tcs = getComputedStyle(td);
          const f = parseColor(tcs.backgroundColor);
          const c0 = xs.indexOf(Math.round(r.x));
          const c1 = xs.indexOf(Math.round(r.x + r.w));
          return {
            c0, c1, rowspan: td.rowSpan || 1,
            fill: f && f.a > 0 ? f : null,
            borders: { l: borderOf(tcs, 'Left'), r: borderOf(tcs, 'Right'), t: borderOf(tcs, 'Top'), b: borderOf(tcs, 'Bottom') },
            pad: { l: px(tcs.paddingLeft), r: px(tcs.paddingRight), t: px(tcs.paddingTop), b: px(tcs.paddingBottom) },
            valign: tcs.verticalAlign === 'top' || tcs.verticalAlign === 'bottom' ? tcs.verticalAlign : 'middle',
            paras: parasOf(td), bg: effBg(r, idx),
          };
        }),
      }));
      e.table = { xs, rows };
      return e;
    });
    return { index: si + 1, layout: slide.dataset.layout || 'content', bg: slideBg, elements };
  });
}
```

`pptx_deck/measure.py`:

```python
"""final.html を Playwright(Python) で開き、部品の位置・大きさ・書式をモデルにする。"""
from pathlib import Path


def measure(html: Path) -> list[dict]:
    from playwright.sync_api import sync_playwright

    js = (Path(__file__).parent / "measure.js").read_text(encoding="utf-8")
    html = Path(html).resolve()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 720})
            page.goto(html.as_uri())
            page.evaluate("document.fonts.ready.then(() => true)")
            slides = page.evaluate(js)
        finally:
            browser.close()
    if not slides:
        raise ValueError(f"{html.name} に section.slide がありません")
    return slides


def title_of(slide: dict) -> dict | None:
    for e in slide["elements"]:
        if e["kind"] == "text" and (e.get("role") == "title" or e.get("ph") == "title"):
            return e
    return None
```

- [ ] **Step 4: テストを実行する**

Run: `"$PY" -m pytest tests/test_measure.py`
Expected: すべて PASS。`test_table` で `xs` の長さが合わないときは、`Math.round` の丸めで境界が 1px ずれていることが多い。`test_overflow_flag_and_long_japanese_title` が失敗するときは、`range.getBoundingClientRect()` が枠の外に出ていること（`overflow: visible`）を確認する。

- [ ] **Step 5: コミット**

```bash
git add skills/pptx-deck/pptx_deck/measure.js skills/pptx-deck/pptx_deck/measure.py skills/pptx-deck/tests/test_measure.py
git commit -m "feat: ブラウザで部品の位置と書式を測るモデル化（measure）を追加"
```

---

### Task 5: 変換の中核（文字・図形・線・画像・表・テンプレートのプレースホルダー）

**Files:**
- Create: `skills/pptx-deck/pptx_deck/build.py`
- Test: `skills/pptx-deck/tests/test_build.py`

**Interfaces:**
- Consumes: `template.open_template`, `template.TemplateInfo`, `pptxutil.*`, `theme.Palette`, `charts.add_chart`（Task 6。この Task では `kind == "chart"` を `NotImplementedError` にし、Task 6 で差し替える）
- Produces: `build.build(model: list[dict], template_path, info: TemplateInfo, palette: Palette, out: Path, base_dir: Path, footer: str | None = None, work_name: str = "build") -> Path`
- 動作: テンプレートを開き、既存スライドを外す。`layout` が `cover` → 表紙、`closing` → 裏表紙（なければ本文）、他 → 本文のレイアウトで `add_slide` する。title／subtitle の `ph` と、本文の `role="title"` は、レイアウトのプレースホルダーに入れる（本文のタイトルは、測った位置・書式に上書き）。使わないプレースホルダーは外し、レイアウトのスライド番号・フッターのプレースホルダーをスライドに写す。ほかの要素は DOM の順に追加する。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_build.py`:

```python
from pathlib import Path

import pytest
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE, PP_PLACEHOLDER as T
from pptx.util import Emu

from pptx_deck import build, paths, template, theme
from pptx_deck.pptxutil import FONT

STANDARD = paths.ASSETS / "template" / "standard.potx"
PAL = theme.derive("#1F3A5F")


def run(model, tmp_path, tpl=STANDARD, footer=None):
    info = template.analyze(tpl)
    out = tmp_path / "o.pptx"
    build.build(model, tpl, info, PAL, out, base_dir=tmp_path, footer=footer, work_name="t")
    return Presentation(out), info


def text_el(idx, x, y, w, h, text, role="body", size=20, color="1A1A1A", bold=False, ph=None, **kw):
    return {"kind": "text", "idx": idx, "rect": {"x": x, "y": y, "w": w, "h": h}, "role": role, "ph": ph,
            "bg": "FFFFFF", "overlap": False, "chrome": False, "overflow": False,
            "box": {"x": x, "y": y, "w": w, "h": h},
            "paras": [{"align": kw.get("align", "left"), "bullet": kw.get("bullet", False), "lh": 1.4, "mb": 0,
                       "runs": [{"text": text, "size_px": size, "bold": bold, "italic": False, "color": color}]}]}


def slide(layout, elements, index=1):
    return {"index": index, "layout": layout, "bg": "FFFFFF", "elements": elements}


def shape_el(idx, x, y, w, h, kind="rect", fill="1F3A5F", a=1, radius=0, line=None):
    return {"kind": "shape", "idx": idx, "rect": {"x": x, "y": y, "w": w, "h": h}, "role": None, "ph": None,
            "bg": "FFFFFF", "overlap": False, "chrome": False, "shape": kind,
            "fill": {"hex": fill, "a": a} if fill else None, "line": line, "radius_px": radius}


def test_layouts_follow_data_layout(tmp_path):
    model = [slide("cover", [text_el(0, 96, 250, 900, 60, "表題", role=None, size=40, ph="title")], 1),
             slide("content", [text_el(0, 64, 40, 900, 40, "見出し", role="title", size=28)], 2),
             slide("closing", [text_el(0, 96, 300, 900, 60, "以上", role=None, size=36, ph="title")], 3)]
    prs, info = run(model, tmp_path)
    assert [s.slide_layout.name for s in prs.slides] == ["表紙", "本文", "裏表紙"]
    assert [s.shapes.title.text_frame.text for s in prs.slides] == ["表題", "見出し", "以上"]


def test_user_template_slides_are_dropped_and_potx_footer_kept(tmp_path):
    prs, _ = run([slide("content", [text_el(0, 64, 40, 900, 40, "見出し", role="title", size=28)])], tmp_path)
    s = prs.slides[0]
    types = [p.placeholder_format.type for p in s.placeholders]
    assert T.TITLE in types and T.SLIDE_NUMBER in types       # ページ番号はテンプレートのものを写す
    assert T.OBJECT not in types                               # 使わない本文領域は外す
    assert len(prs.slides) == 1


def test_missing_closing_uses_body(tmp_path):
    from tests.test_template import _as_pptx
    tpl = _as_pptx(STANDARD, tmp_path / "u.pptx", drop="裏表紙")
    model = [slide("closing", [text_el(0, 96, 300, 900, 60, "以上", role=None, size=36, ph="title")])]
    prs, info = run(model, tmp_path, tpl=tpl)
    assert info.closing is None and prs.slides[0].slide_layout.name == "本文"   # Review Focus 4


def test_title_placeholder_gets_measured_geometry_and_font(tmp_path):
    model = [slide("content", [text_el(0, 70, 44, 800, 40, "見出し", role="title", size=28, bold=True)])]
    prs, _ = run(model, tmp_path)
    t = prs.slides[0].shapes.title
    assert (t.left, t.top, t.width) == (70 * 9525, 44 * 9525, 800 * 9525)
    r = t.text_frame.paragraphs[0].runs[0]
    assert r.font.size.pt == 21 and r.font.bold and r.font.name == FONT
    assert r._r.rPr.find("{http://schemas.openxmlformats.org/drawingml/2006/main}ea").get("typeface") == FONT


def test_textbox_bullets_and_runs(tmp_path):
    el = text_el(0, 80, 170, 360, 100, "x")
    el["paras"] = [
        {"align": "left", "bullet": True, "lh": 1.4, "mb": 6,
         "runs": [{"text": "太字", "size_px": 20, "bold": True, "italic": False, "color": "1F3A5F"},
                  {"br": True},
                  {"text": "続き", "size_px": 20, "bold": False, "italic": False, "color": "1A1A1A"}]}]
    prs, _ = run([slide("content", [text_el(0, 64, 40, 900, 40, "見出し", role="title", size=28), el])], tmp_path)
    tb = [s for s in prs.slides[0].shapes if not s.is_placeholder][0]
    assert tb.text_frame.word_wrap is True
    p = tb.text_frame.paragraphs[0]
    assert "buChar" in p._p.xml and [r.text for r in p.runs] == ["太字", "続き"]
    assert p.runs[0].font.bold is True


def test_shapes_fill_alpha_radius(tmp_path):
    els = [text_el(0, 64, 40, 900, 40, "見出し", role="title", size=28),
           shape_el(1, 64, 150, 300, 100, "round", radius=20),
           shape_el(2, 400, 150, 100, 100, "ellipse", fill="B85A0B", a=0.5),
           shape_el(3, 520, 150, 100, 100, "triangle", fill=None, line={"hex": "595959", "w": 2})]
    prs, _ = run([slide("content", els)], tmp_path)
    shapes = [s for s in prs.slides[0].shapes if not s.is_placeholder]
    assert shapes[0].auto_shape_type == MSO_SHAPE.ROUNDED_RECTANGLE
    assert abs(shapes[0].adjustments[0] - 0.2) < 0.01
    assert shapes[1].auto_shape_type == MSO_SHAPE.OVAL and 'a:alpha val="50000"' in shapes[1]._element.xml.replace("'", '"')
    assert shapes[2].auto_shape_type == MSO_SHAPE.ISOSCELES_TRIANGLE and shapes[2].fill.type is not None


def test_line_arrow(tmp_path):
    ln = {"kind": "line", "idx": 1, "rect": {"x": 100, "y": 300, "w": 200, "h": 2}, "role": None, "ph": None,
          "bg": "FFFFFF", "overlap": False, "chrome": False, "fill": {"hex": "595959", "a": 1}, "arrow": True}
    prs, _ = run([slide("content", [text_el(0, 64, 40, 900, 40, "見出し", role="title", size=28), ln])], tmp_path)
    cx = [s for s in prs.slides[0].shapes if s.shape_type is not None and "Connector" in type(s).__name__][0]
    assert "tailEnd" in cx._element.xml and cx.begin_x == 100 * 9525 and cx.end_x == 300 * 9525


def test_line_arrow_reverse_swaps_ends(tmp_path):
    ln = {"kind": "line", "idx": 1, "rect": {"x": 100, "y": 300, "w": 200, "h": 2}, "role": None, "ph": None,
          "bg": "FFFFFF", "overlap": False, "chrome": False, "fill": {"hex": "595959", "a": 1}, "arrow": True,
          "reverse": True}
    prs, _ = run([slide("content", [text_el(0, 64, 40, 900, 40, "見出し", role="title", size=28), ln])], tmp_path)
    cx = [s for s in prs.slides[0].shapes if "Connector" in type(s).__name__][0]
    assert cx.begin_x == 300 * 9525 and cx.end_x == 100 * 9525          # 右から左へ向く


def test_icon_svg_becomes_picture_with_alt(tmp_path):
    svg = tmp_path / "i.svg"
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">'
                   '<circle cx="12" cy="12" r="8" fill="none" stroke="#1F3A5F" stroke-width="2"/></svg>')
    im = {"kind": "image", "idx": 1, "rect": {"x": 100, "y": 200, "w": 48, "h": 48}, "role": "icon", "ph": None,
          "bg": "FFFFFF", "overlap": False, "chrome": False, "src": svg.as_uri(), "alt": "丸のアイコン"}
    prs, _ = run([slide("content", [text_el(0, 64, 40, 900, 40, "見出し", role="title", size=28), im])], tmp_path)
    pic = [s for s in prs.slides[0].shapes if s.shape_type == 13][0]
    assert pic._element.nvPicPr.cNvPr.get("descr") == "丸のアイコン"


def test_table_merge_fill_borders(tmp_path):
    def cell(c0, c1, text, fill=None, b=None, rowspan=1):
        return {"c0": c0, "c1": c1, "rowspan": rowspan, "fill": {"hex": fill, "a": 1} if fill else None,
                "borders": {"l": None, "r": None, "t": None, "b": b}, "pad": {"l": 8, "r": 8, "t": 8, "b": 8},
                "valign": "middle", "bg": "FFFFFF",
                "paras": [{"align": "left", "bullet": False, "lh": 1.4, "mb": 0,
                           "runs": [{"text": text, "size_px": 20, "bold": False, "italic": False, "color": "1A1A1A"}]}]}
    tbl = {"kind": "table", "idx": 1, "rect": {"x": 64, "y": 150, "w": 600, "h": 100}, "role": None, "ph": None,
           "bg": "FFFFFF", "overlap": False, "chrome": False,
           "table": {"xs": [64, 264, 464, 664], "rows": [
               {"h": 50, "cells": [cell(0, 1, "項目", fill="1F3A5F"), cell(1, 3, "見出し", b={"hex": "BFBFBF", "w": 2})]},
               {"h": 50, "cells": [cell(0, 1, "A"), cell(1, 2, "B"), cell(2, 3, "C")]}]}}
    prs, _ = run([slide("content", [text_el(0, 64, 40, 900, 40, "見出し", role="title", size=28), tbl])], tmp_path)
    gf = [s for s in prs.slides[0].shapes if s.has_table][0]
    t = gf.table
    assert len(t.columns) == 3 and len(t.rows) == 2
    assert t.cell(0, 1).is_merge_origin and t.cell(0, 1).span_width == 2
    assert t.cell(0, 0).text == "項目" and t.cell(1, 2).text == "C"
    assert "lnB" in t.cell(0, 1)._tc.xml


def test_footer_text_override(tmp_path):
    prs, _ = run([slide("content", [text_el(0, 64, 40, 900, 40, "見出し", role="title", size=28)])],
                 tmp_path, footer="社外秘")
    ft = [p for p in prs.slides[0].placeholders if p.placeholder_format.type == T.FOOTER][0]
    assert ft.text_frame.text == "社外秘"


def test_chart_not_yet_supported_is_explicit(tmp_path):
    ch = {"kind": "chart", "idx": 1, "rect": {"x": 64, "y": 150, "w": 500, "h": 300}, "role": None, "ph": None,
          "bg": "FFFFFF", "overlap": False, "chrome": False,
          "chart": {"type": "bar", "categories": ["A"], "series": [{"name": "x", "values": [1]}]}}
    with pytest.raises(NotImplementedError):
        run([slide("content", [text_el(0, 64, 40, 900, 40, "見出し", role="title", size=28), ch])], tmp_path)
```

テストが `tests.test_template` から import するため、`tests/__init__.py`（空）を作る。

- [ ] **Step 2: 失敗を確認する**

Run: `touch tests/__init__.py; "$PY" -m pytest tests/test_build.py`
Expected: FAIL（`build` が未実装）

- [ ] **Step 3: 実装する**

`pptx_deck/build.py`:

```python
"""モデル → PPTX。テンプレートのファイルを土台に、レイアウトの上へ書き出す。"""
import copy
import re
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

from lxml import etree
from pptx.enum.dml import MSO_LINE
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE, PP_PLACEHOLDER as T
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Pt

from . import paths, template
from .pptxutil import drop_all_slides, emu, rgb, set_run_font

ALIGN = {"left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER, "right": PP_ALIGN.RIGHT, "justify": PP_ALIGN.JUSTIFY}
SHAPES = {"rect": MSO_SHAPE.RECTANGLE, "round": MSO_SHAPE.ROUNDED_RECTANGLE,
          "ellipse": MSO_SHAPE.OVAL, "triangle": MSO_SHAPE.ISOSCELES_TRIANGLE}
VALIGN = {"top": MSO_ANCHOR.TOP, "middle": MSO_ANCHOR.MIDDLE, "bottom": MSO_ANCHOR.BOTTOM}


def url_to_path(url: str, base_dir: Path) -> Path:
    if url.startswith("file:"):
        return Path(url2pathname(urlparse(url).path))
    return (base_dir / url).resolve()


# ---- 文字 ----
def _bullet(p, size_px):
    pPr = p._p.get_or_add_pPr()
    indent = round(size_px * 9525)
    pPr.set("marL", str(indent))
    pPr.set("indent", str(-indent))
    for tag in ("a:buNone", "a:buChar", "a:buAutoNum"):
        for el in pPr.findall(qn(tag)):
            pPr.remove(el)
    etree.SubElement(pPr, qn("a:buChar")).set("char", "•")


def fill_text_frame(tf, paras, anchor=MSO_ANCHOR.TOP):
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    first = True
    for para in paras:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.alignment = ALIGN[para["align"]]
        size = next((r["size_px"] for r in para["runs"] if "text" in r), 20)
        p.line_spacing = max(0.9, round(para["lh"] / 1.2, 2))
        if para.get("mb"):
            p.space_after = Pt(round(para["mb"] * 0.75, 1))
        if para["bullet"]:
            _bullet(p, size)
        for run in para["runs"]:
            if run.get("br"):
                p.add_line_break()
                continue
            r = p.add_run()
            r.text = run["text"]
            set_run_font(r, run["size_px"], run["bold"], run["italic"], run["color"])


def _place(shape, rect):
    shape.left, shape.top = emu(rect["x"]), emu(rect["y"])
    shape.width, shape.height = emu(rect["w"]), emu(rect["h"])


def add_textbox(slide, el):
    b = el["box"]
    tb = slide.shapes.add_textbox(emu(b["x"]), emu(b["y"]), emu(b["w"] + 2), emu(max(b["h"], 1)))
    fill_text_frame(tb.text_frame, el["paras"])


# ---- 図形・線・画像 ----
def add_shape(slide, el):
    r = el["rect"]
    shp = slide.shapes.add_shape(SHAPES[el["shape"]], emu(r["x"]), emu(r["y"]), emu(r["w"]), emu(r["h"]))
    if el["shape"] == "round" and el["radius_px"]:
        shp.adjustments[0] = min(0.5, el["radius_px"] / min(r["w"], r["h"]))
    if el["fill"]:
        shp.fill.solid()
        shp.fill.fore_color.rgb = rgb(el["fill"]["hex"])
        if el["fill"]["a"] < 1:
            clr = shp.fill._xPr.find(qn("a:solidFill"))[0]
            etree.SubElement(clr, qn("a:alpha")).set("val", str(int(el["fill"]["a"] * 100000)))
    else:
        shp.fill.background()
    if el["line"]:
        shp.line.color.rgb = rgb(el["line"]["hex"])
        shp.line.width = Pt(el["line"]["w"] * 0.75)
    else:
        shp.line.fill.background()
    shp.shadow.inherit = False


def add_line(slide, el):
    r = el["rect"]
    horizontal = r["w"] >= r["h"]
    if horizontal:
        x1, y1, x2, y2, th = r["x"], r["y"] + r["h"] / 2, r["x"] + r["w"], r["y"] + r["h"] / 2, r["h"]
    else:
        x1, y1, x2, y2, th = r["x"] + r["w"] / 2, r["y"], r["x"] + r["w"] / 2, r["y"] + r["h"], r["w"]
    if el.get("reverse"):
        x1, y1, x2, y2 = x2, y2, x1, y1
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, emu(x1), emu(y1), emu(x2), emu(y2))
    c.line.color.rgb = rgb(el["fill"]["hex"])
    c.line.width = Pt(max(0.75, th * 0.75))
    if el["arrow"]:
        etree.SubElement(c.line._get_or_add_ln(), qn("a:tailEnd")).set("type", "triangle")


def rasterize_svg(svg: Path, width_px: float, work_name: str) -> Path:
    import fitz
    out_dir = paths.temp_dir(work_name) / "raster"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / (svg.stem + ".png")
    doc = fitz.open(str(svg))
    page = doc[0]
    zoom = max(1.0, width_px * 3 / page.rect.width)
    page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=True).save(str(out))
    doc.close()
    return out


def add_image(slide, el, base_dir, work_name):
    r = el["rect"]
    src = url_to_path(el["src"], base_dir)
    if src.suffix.lower() == ".svg":
        src = rasterize_svg(src, r["w"], work_name)
    pic = slide.shapes.add_picture(str(src), emu(r["x"]), emu(r["y"]), emu(r["w"]), emu(r["h"]))
    pic._element.nvPicPr.cNvPr.set("descr", el["alt"])


# ---- 表 ----
def _border(tcPr, tag, spec):
    for old in tcPr.findall(qn(tag)):
        tcPr.remove(old)
    ln = etree.Element(qn(tag))
    if spec:
        ln.set("w", str(int(spec["w"] * 0.75 * 12700)))
        fill = etree.SubElement(ln, qn("a:solidFill"))
        etree.SubElement(fill, qn("a:srgbClr")).set("val", spec["hex"])
    else:
        ln.set("w", "0")
        etree.SubElement(ln, qn("a:noFill"))
    return ln


def add_table(slide, el):
    t, r = el["table"], el["rect"]
    xs, rows = t["xs"], t["rows"]
    ncols = len(xs) - 1
    gf = slide.shapes.add_table(len(rows), ncols, emu(r["x"]), emu(r["y"]), emu(r["w"]), emu(r["h"]))
    tbl = gf.table
    tblPr = tbl._tbl.tblPr
    tblPr.set("firstRow", "0")
    tblPr.set("bandRow", "0")
    sid = tblPr.find(qn("a:tableStyleId"))
    if sid is not None:
        tblPr.remove(sid)
    for i in range(ncols):
        tbl.columns[i].width = emu(xs[i + 1] - xs[i])
    for j, row in enumerate(rows):
        tbl.rows[j].height = emu(row["h"])
    for j, row in enumerate(rows):
        for c in row["cells"]:
            cell = tbl.cell(j, c["c0"])
            if c["c1"] - c["c0"] > 1 or c["rowspan"] > 1:
                cell.merge(tbl.cell(j + c["rowspan"] - 1, c["c1"] - 1))
            cell.margin_left, cell.margin_right = emu(c["pad"]["l"]), emu(c["pad"]["r"])
            cell.margin_top, cell.margin_bottom = emu(c["pad"]["t"]), emu(c["pad"]["b"])
            cell.vertical_anchor = VALIGN[c["valign"]]
            if c["fill"]:
                cell.fill.solid()
                cell.fill.fore_color.rgb = rgb(c["fill"]["hex"])
            else:
                cell.fill.background()
            fill_text_frame(cell.text_frame, c["paras"], anchor=VALIGN[c["valign"]])
            cell.margin_left, cell.margin_right = emu(c["pad"]["l"]), emu(c["pad"]["r"])
            cell.margin_top, cell.margin_bottom = emu(c["pad"]["t"]), emu(c["pad"]["b"])
            tcPr = cell._tc.get_or_add_tcPr()
            for i, (tag, side) in enumerate((("a:lnL", "l"), ("a:lnR", "r"), ("a:lnT", "t"), ("a:lnB", "b"))):
                tcPr.insert(i, _border(tcPr, tag, c["borders"][side]))


# ---- スライド ----
def _next_id(slide) -> int:
    ids = [int(x) for x in slide.shapes._spTree.xpath("//p:cNvPr/@id")]
    return max(ids + [1]) + 1


def _clone_footer_placeholders(slide, layout, footer):
    for ph in layout.placeholders:
        if ph.placeholder_format.type not in (T.SLIDE_NUMBER, T.FOOTER):
            continue
        el = copy.deepcopy(ph._element)
        el.xpath(".//p:cNvPr")[0].set("id", str(_next_id(slide)))
        slide.shapes._spTree.append(el)
        if footer is not None and ph.placeholder_format.type == T.FOOTER:
            ts = el.xpath(".//a:t")
            if ts:
                ts[0].text = footer
                for extra in ts[1:]:
                    extra.text = ""
            else:
                p = el.xpath(".//a:p")[0]
                r = etree.SubElement(p, qn("a:r"))
                etree.SubElement(r, qn("a:t")).text = footer


def _layout_index(info, name):
    if name == "cover":
        return info.cover
    if name == "closing":
        return info.closing if info.closing is not None else info.body
    return info.body


def build(model, template_path, info, palette, out: Path, base_dir: Path,
          footer: str | None = None, work_name: str = "build") -> Path:
    from . import charts

    prs = template.open_template(template_path)
    drop_all_slides(prs)
    for s in model:
        layout = prs.slide_layouts[_layout_index(info, s["layout"])]
        slide = prs.slides.add_slide(layout)
        used = set()
        elements = s["elements"]
        # タイトル・副題はレイアウトのプレースホルダーへ
        for el in elements:
            if el["kind"] != "text":
                continue
            is_title = el.get("ph") == "title" or (el.get("role") == "title" and s["layout"] not in ("cover", "closing"))
            is_sub = el.get("ph") == "subtitle"
            if is_title and slide.shapes.title is not None and "title" not in used:
                ph = slide.shapes.title
                if el.get("ph") is None:        # 本文のタイトルは、測った位置に上書きする
                    _place(ph, el["box"])
                fill_text_frame(ph.text_frame, el["paras"])
                used.add("title")
                el["_done"] = True
            elif is_sub:
                subs = [p for p in slide.placeholders if p.placeholder_format.type == T.SUBTITLE]
                if subs:
                    fill_text_frame(subs[0].text_frame, el["paras"])
                    used.add("sub")
                    el["_done"] = True
        for ph in list(slide.placeholders):
            keep = (ph.placeholder_format.type in (T.TITLE, T.CENTER_TITLE) and "title" in used) or \
                   (ph.placeholder_format.type == T.SUBTITLE and "sub" in used)
            if not keep:
                ph._element.getparent().remove(ph._element)
        _clone_footer_placeholders(slide, layout, footer)
        for el in elements:
            if el.pop("_done", False):
                continue
            k = el["kind"]
            if k == "text":
                add_textbox(slide, el)
            elif k == "shape":
                add_shape(slide, el)
            elif k == "line":
                add_line(slide, el)
            elif k == "image":
                add_image(slide, el, base_dir, work_name)
            elif k == "table":
                add_table(slide, el)
            elif k == "chart":
                charts.add_chart(slide, el, palette)
            else:
                raise ValueError(f"未対応の要素: {k}")
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out))
    return out
```

`pptx_deck/charts.py`（Task 6 で本実装。この時点は明示的に失敗させる）:

```python
def add_chart(slide, el, palette):
    raise NotImplementedError("グラフは Task 6 で実装する")
```

- [ ] **Step 4: テストを実行する**

Run: `"$PY" -m pytest tests/test_build.py`
Expected: すべて PASS。失敗しやすい点: ① 表の `cell.merge` の範囲（`c1 - 1` が最終列）② `_clone_footer_placeholders` の `p:cNvPr` 検索（名前空間は lxml の `xpath` が python-pptx の要素で解決される）③ 本文タイトルの `slide.shapes.title`（`add_slide` 後にタイトルのプレースホルダーが存在する前提。標準テンプレートの「本文」は TITLE を持つ）。

- [ ] **Step 5: 目で確認する**

```bash
"$PY" - <<'EOF'
from pathlib import Path
from tests.test_build import *
import tempfile
t = Path(tempfile.mkdtemp(prefix="pptx-deck-chk-"))
model = [slide("cover", [text_el(0, 96, 250, 900, 60, "表題テスト", role=None, size=40, ph="title")], 1),
         slide("content", [text_el(0, 64, 40, 900, 40, "見出しがここに入る", role="title", size=28, bold=True),
                           shape_el(1, 64, 150, 300, 100, "round", radius=20)], 2)]
prs, _ = run(model, t)
from pptx_deck import render
print(render.pptx_to_pngs(t / "o.pptx", t / "png"))
EOF
```

出力された PNG を Read で開き、表紙の題・本文の見出し・角丸の面・下端の罫線とページ番号が出ていることを確認する。

- [ ] **Step 6: コミット**

```bash
git add skills/pptx-deck
git commit -m "feat: モデルをテンプレート土台の PPTX に書き出す変換（文字・図形・線・画像・表）を追加"
```

---

### Task 6: ネイティブのグラフ

**Files:**
- Modify: `skills/pptx-deck/pptx_deck/charts.py`（全面置換）
- Test: `skills/pptx-deck/tests/test_charts.py`

**Interfaces:**
- Consumes: `theme.Palette`, `pptxutil.emu/rgb/FONT`
- Produces: `charts.add_chart(slide, el: dict, palette) -> None`、`charts.waterfall_series(values: list[float], totals: list[int]) -> dict`
- グラフ指定（`el["chart"]`）: `{"type": "bar|barh|line|pie|stacked|stacked100|waterfall", "categories": [...], "series": [{"name","values"}], "highlight": int|None, "fmt": "#,##0", "totals": [int]}`。`highlight` は系列 0 の強調する点の番号（強調色）。`waterfall` は `series[0].values` を増減とし、`totals`（省略時は先頭と末尾）の位置は合計の値。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_charts.py`:

```python
import pytest
from pptx import Presentation
from pptx.enum.chart import XL_CHART_TYPE as C

from pptx_deck import charts, paths, template, theme
from pptx_deck.build import build
from tests.test_build import slide, text_el

STANDARD = paths.ASSETS / "template" / "standard.potx"
PAL = theme.derive("#1F3A5F")


def chart_el(spec):
    return {"kind": "chart", "idx": 1, "rect": {"x": 64, "y": 150, "w": 600, "h": 360}, "role": None, "ph": None,
            "bg": "FFFFFF", "overlap": False, "chrome": False, "chart": spec}


def built(spec, tmp_path):
    info = template.analyze(STANDARD)
    m = [slide("content", [text_el(0, 64, 40, 900, 40, "見出し", role="title", size=28), chart_el(spec)])]
    out = tmp_path / "c.pptx"
    build(m, STANDARD, info, PAL, out, base_dir=tmp_path)
    shapes = [s for s in Presentation(out).slides[0].shapes if s.has_chart]
    assert len(shapes) == 1
    return shapes[0].chart


BASE = {"categories": ["2024", "2025", "2026"], "series": [{"name": "費用", "values": [120, 90, 60]}]}


@pytest.mark.parametrize("t,expected", [
    ("bar", C.COLUMN_CLUSTERED), ("barh", C.BAR_CLUSTERED), ("line", C.LINE_MARKERS),
    ("stacked", C.COLUMN_STACKED), ("stacked100", C.COLUMN_STACKED_100)])
def test_chart_types(t, expected, tmp_path):
    spec = {**BASE, "type": t}
    if t.startswith("stacked"):
        spec["series"] = [{"name": "A", "values": [1, 2, 3]}, {"name": "B", "values": [3, 2, 1]}]
    ch = built(spec, tmp_path)
    assert ch.chart_type == expected


def test_pie(tmp_path):
    ch = built({"type": "pie", "categories": ["A", "B", "C"], "series": [{"name": "比率", "values": [50, 30, 20]}]}, tmp_path)
    assert ch.chart_type == C.PIE


def test_bar_highlight_uses_emphasis_color(tmp_path):
    ch = built({**BASE, "type": "bar", "highlight": 2}, tmp_path)
    pt = ch.plots[0].series[0].points[2]
    assert str(pt.format.fill.fore_color.rgb) == PAL.emphasis.lstrip("#")
    other = ch.plots[0].series[0].points[0]
    assert str(other.format.fill.fore_color.rgb) == PAL.accent.lstrip("#")


def test_fonts_are_at_least_10pt_and_biz(tmp_path):
    ch = built({**BASE, "type": "bar"}, tmp_path)
    assert ch.font.size.pt >= 10 and ch.font.name == "BIZ UDPゴシック"


def test_waterfall_series():
    d = charts.waterfall_series([100, 20, -30, 90], [0, 3])
    assert d["base"] == [0, 100, 90, 0] and d["up"] == [0, 20, 0, 0]
    assert d["down"] == [0, 0, 30, 0] and d["total"] == [100, 0, 0, 90]


def test_waterfall_default_totals_first_and_last():
    d = charts.waterfall_series([100, -40, 60], None)
    assert d["total"] == [100, 0, 60]


def test_waterfall_negative_running_total_is_an_error():
    with pytest.raises(ValueError, match="0 未満"):
        charts.waterfall_series([10, -30, 5], [0, 2])


def test_waterfall_chart_has_four_series_and_hidden_base(tmp_path):
    ch = built({"type": "waterfall", "categories": ["前", "増", "減", "後"],
                "series": [{"name": "金額", "values": [100, 20, -30, 90]}], "totals": [0, 3]}, tmp_path)
    s = ch.plots[0].series
    assert [x.name for x in s] == ["基準", "増加", "減少", "合計"] and len(s) == 4
    assert s[0].format.fill.type == 5          # MSO_FILL.BACKGROUND（塗りなし）


def test_unknown_type_is_an_error(tmp_path):
    with pytest.raises(ValueError, match="radar"):
        built({**BASE, "type": "radar"}, tmp_path)
```

- [ ] **Step 2: 失敗を確認する**

Run: `"$PY" -m pytest tests/test_charts.py`
Expected: FAIL（`NotImplementedError`）

- [ ] **Step 3: 実装する**

`pptx_deck/charts.py`:

```python
"""グラフ指定 → PowerPoint のネイティブグラフ。色は配色（Palette）から取る。"""
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE as C, XL_LEGEND_POSITION
from pptx.util import Pt

from .pptxutil import FONT, emu, rgb

TYPES = {"bar": C.COLUMN_CLUSTERED, "barh": C.BAR_CLUSTERED, "line": C.LINE_MARKERS, "pie": C.PIE,
         "stacked": C.COLUMN_STACKED, "stacked100": C.COLUMN_STACKED_100, "waterfall": C.COLUMN_STACKED}
FONT_PT = 12


def waterfall_series(values, totals):
    n = len(values)
    totals = set(totals if totals is not None else [0, n - 1])
    base, up, down, tot = [], [], [], []
    run = 0
    for i, v in enumerate(values):
        if i in totals:
            base.append(0); up.append(0); down.append(0); tot.append(v)
            run = v
        elif v >= 0:
            base.append(run); up.append(v); down.append(0); tot.append(0)
            run += v
        else:
            run += v
            if run < 0:
                raise ValueError(f"累計が 0 未満になります（{i + 1} 番目）。値を確認してください")
            base.append(run); up.append(0); down.append(-v); tot.append(0)
    return {"base": base, "up": up, "down": down, "total": tot}


def _series_colors(p):
    return [p.accent, p.accent_mid, "#8C8C8C", p.accent_dark, "#BFBFBF"]


def _fill(series, hex6):
    series.format.fill.solid()
    series.format.fill.fore_color.rgb = rgb(hex6)


def add_chart(slide, el, palette):
    spec, r = el["chart"], el["rect"]
    t = spec["type"]
    if t not in TYPES:
        raise ValueError(f"未対応のグラフ型: {t}（{', '.join(TYPES)}）")
    cd = CategoryChartData()
    cd.categories = spec["categories"]
    if t == "waterfall":
        w = waterfall_series(spec["series"][0]["values"], spec.get("totals"))
        for name, key in (("基準", "base"), ("増加", "up"), ("減少", "down"), ("合計", "total")):
            cd.add_series(name, w[key])
    else:
        for s in spec["series"]:
            cd.add_series(s["name"], s["values"])
    gf = slide.shapes.add_chart(TYPES[t], emu(r["x"]), emu(r["y"]), emu(r["w"]), emu(r["h"]), cd)
    chart = gf.chart
    chart.font.size = Pt(FONT_PT)
    chart.font.name = FONT
    colors = _series_colors(palette)
    fmt = spec.get("fmt", "#,##0")
    plot = chart.plots[0]
    chart.has_title = False

    if t == "pie":
        ser = plot.series[0]
        cycle = [palette.accent, palette.accent_mid, "#8C8C8C", palette.accent_dark, "#BFBFBF"]
        for i in range(len(spec["categories"])):
            pt = ser.points[i]
            pt.format.fill.solid()
            pt.format.fill.fore_color.rgb = rgb(palette.emphasis if spec.get("highlight") == i else cycle[i % 5])
        plot.has_data_labels = True
        plot.data_labels.number_format = fmt
        plot.data_labels.number_format_is_linked = False
        chart.has_legend = True
        chart.legend.position = XL_LEGEND_POSITION.BOTTOM
        chart.legend.include_in_layout = False
        return

    value_axis = chart.value_axis
    value_axis.has_major_gridlines = False
    value_axis.tick_labels.font.size = Pt(FONT_PT)
    chart.category_axis.tick_labels.font.size = Pt(FONT_PT)
    plot.gap_width = 60

    if t == "waterfall":
        plot.overlap = 100
        s_base, s_up, s_down, s_tot = plot.series
        s_base.format.fill.background()
        _fill(s_up, palette.accent)
        _fill(s_down, "#404040")
        _fill(s_tot, "#767676")
        s_base.data_labels.show_value = False
        for s in (s_up, s_down, s_tot):
            dl = s.data_labels
            dl.show_value = True
            dl.number_format = fmt + ";-" + fmt + ";;"
            dl.number_format_is_linked = False
            dl.font.size = Pt(FONT_PT)
        chart.has_legend = False
        return

    for i, ser in enumerate(plot.series):
        if t == "line":
            ser.format.line.color.rgb = rgb(colors[i % 5])
            ser.format.line.width = Pt(2.5)
            ser.smooth = False
        else:
            _fill(ser, colors[i % 5])
    if t in ("bar", "barh") and spec.get("highlight") is not None:
        pt = plot.series[0].points[spec["highlight"]]
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = rgb(palette.emphasis)
    if t.startswith("stacked"):
        plot.overlap = 100
    plot.has_data_labels = True
    plot.data_labels.number_format = fmt
    plot.data_labels.number_format_is_linked = False
    plot.data_labels.font.size = Pt(FONT_PT)
    multi = len(plot.series) > 1
    chart.has_legend = multi
    if multi:
        chart.legend.position = XL_LEGEND_POSITION.BOTTOM
        chart.legend.include_in_layout = False
```

- [ ] **Step 4: テストを実行する**

Run: `"$PY" -m pytest tests/test_charts.py tests/test_build.py`
Expected: すべて PASS。`test_chart_not_yet_supported_is_explicit`（Task 5）は期待が変わるため、**この Step で削除**する（グラフは対応済み）。`s[0].format.fill.type == 5` は `MSO_FILL.BACKGROUND` の値。違う場合は `from pptx.enum.dml import MSO_FILL` で比較に直す。

- [ ] **Step 5: 目で確認する**

Task 5 Step 5 と同じ方法で、`waterfall` と `bar`（highlight あり）を 1 枚ずつ PNG にして、棒の強調色・合計の灰・値ラベルが出ていることを確認する。

- [ ] **Step 6: コミット**

```bash
git add skills/pptx-deck
git commit -m "feat: ネイティブのグラフ（棒・横棒・折れ線・円・積み上げ・ウォーターフォール）を追加"
```

---

### Task 7: 検査（check）

**Files:**
- Create: `skills/pptx-deck/pptx_deck/check.py`
- Test: `skills/pptx-deck/tests/test_check.py`

**Interfaces:**
- Consumes: `theme.contrast`, `template.TemplateInfo`
- Produces: `check.check_model(model: list[dict], info: TemplateInfo) -> list[dict]`、`check.check_pptx(path: Path) -> list[dict]`、`check.errors(violations) -> list[dict]`
- 違反の形: `{"rule": str, "slide": int, "message": str, "severity": "error"}`。規則名: `overflow`・`outOfSlide`・`keepout`・`overlap`・`fontMin`・`contrast`・`imageAlt`・`bodyImage`・`titleMissing`（モデル）、`pptxBounds`・`pptxFontMin`・`pptxPicture`（PPTX）。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_check.py`:

```python
from pathlib import Path

from pptx import Presentation
from pptx.util import Pt

from pptx_deck import check, paths, template
from tests.test_build import shape_el, slide, text_el

INFO = template.analyze(paths.ASSETS / "template" / "standard.potx")
TITLE = text_el(0, 64, 40, 900, 40, "見出し", role="title", size=28)


def rules(model):
    return sorted({v["rule"] for v in check.check_model(model, INFO)})


def test_clean_slide_passes():
    assert check.check_model([slide("content", [TITLE, text_el(1, 64, 160, 500, 40, "本文", size=20)])], INFO) == []


def test_overflow_flag():
    t = text_el(1, 64, 160, 500, 40, "本文", size=20)
    t["overflow"] = True
    assert "overflow" in rules([slide("content", [TITLE, t])])


def test_out_of_slide():
    assert "outOfSlide" in rules([slide("content", [TITLE, text_el(1, 1200, 160, 200, 40, "はみ出し")])])


def test_keepout_footer_zone():
    assert "keepout" in rules([slide("content", [TITLE, text_el(1, 64, 680, 500, 30, "フッター領域")])])


def test_chrome_elements_skip_keepout():
    c = text_el(1, 64, 680, 500, 30, "出典")
    c["chrome"] = True
    assert "keepout" not in rules([slide("content", [TITLE, c])])


def test_partial_text_overlap_is_error():
    a = text_el(1, 64, 160, 400, 60, "A")
    b = text_el(2, 300, 190, 400, 60, "B")
    assert "overlap" in rules([slide("content", [TITLE, a, b])])


def test_text_inside_shape_is_fine():
    sh = shape_el(1, 64, 150, 400, 120)
    t = text_el(2, 80, 170, 360, 40, "面の中", color="FFFFFF")
    t["bg"] = "1F3A5F"
    assert rules([slide("content", [TITLE, sh, t])]) == []


def test_text_crossing_shape_edge_is_error():
    sh = shape_el(1, 64, 150, 200, 100)
    t = text_el(2, 200, 170, 300, 40, "はみ出す")
    assert "overlap" in rules([slide("content", [TITLE, sh, t])])


def test_data_overlap_allows_it():
    a = text_el(1, 64, 160, 400, 60, "A")
    b = text_el(2, 300, 190, 400, 60, "B")
    a["overlap"] = b["overlap"] = True
    assert "overlap" not in rules([slide("content", [TITLE, a, b])])


def test_font_min_by_role():
    assert "fontMin" in rules([slide("content", [TITLE, text_el(1, 64, 160, 500, 40, "小さい", size=16)])])   # 12pt
    assert "fontMin" not in rules([slide("content", [TITLE, text_el(1, 64, 160, 500, 40, "注記", role="caption", size=14)])])
    assert "fontMin" in rules([slide("content", [TITLE, text_el(1, 64, 160, 500, 40, "注記", role="caption", size=12)])])  # 9pt


def test_contrast_on_dark_template_background():          # Review Focus 3
    t = text_el(1, 64, 160, 500, 40, "暗い下地に黒文字", color="000000")
    t["bg"] = "101820"
    assert "contrast" in rules([slide("content", [TITLE, t])])


def test_large_text_needs_only_3_to_1():
    t = text_el(1, 64, 160, 500, 60, "大きい文字", size=36, color="8A8A8A")
    assert "contrast" not in rules([slide("content", [TITLE, t])])


def test_image_alt_and_body_image():
    im = {"kind": "image", "idx": 1, "rect": {"x": 64, "y": 150, "w": 900, "h": 450}, "role": None, "ph": None,
          "bg": "FFFFFF", "overlap": False, "chrome": False, "src": "x.png", "alt": ""}
    got = rules([slide("content", [TITLE, im])])
    assert "imageAlt" in got and "bodyImage" in got
    im2 = {**im, "role": "icon", "alt": "アイコン", "rect": {"x": 64, "y": 150, "w": 48, "h": 48}}
    assert rules([slide("content", [TITLE, im2])]) == []


def test_title_missing_except_closing():
    assert "titleMissing" in rules([slide("content", [text_el(1, 64, 160, 500, 40, "本文")])])
    cover = text_el(0, 96, 250, 900, 60, "表題", role=None, size=40, ph="title")
    assert "titleMissing" not in rules([slide("cover", [cover])])


def test_check_pptx(tmp_path):
    prs = Presentation()
    prs.slide_width, prs.slide_height = 12192000, 6858000
    s = prs.slides.add_slide(prs.slide_layouts[6])
    tb = s.shapes.add_textbox(12000000, 100000, 600000, 300000)     # 右にはみ出す
    r = tb.text_frame.paragraphs[0].add_run()
    r.text = "小さい"
    r.font.size = Pt(8)
    out = tmp_path / "x.pptx"
    prs.save(out)
    got = {v["rule"] for v in check.check_pptx(out)}
    assert {"pptxBounds", "pptxFontMin"} <= got


def test_errors_filter():
    vs = [{"rule": "a", "slide": 1, "message": "m", "severity": "error"},
          {"rule": "b", "slide": 1, "message": "m", "severity": "warning"}]
    assert [v["rule"] for v in check.errors(vs)] == ["a"]
```

- [ ] **Step 2: 失敗を確認する**

Run: `"$PY" -m pytest tests/test_check.py`
Expected: FAIL（`check` が未実装）

- [ ] **Step 3: 実装する**

`pptx_deck/check.py`:

```python
"""体裁の検査（最小限）: はみ出し・重なり・文字サイズの下限・コントラスト・画像の使い方。"""
from pathlib import Path

from . import theme
from .template import TemplateInfo

SLIDE_W, SLIDE_H = 1280, 720
MIN_PT_DEFAULT, MIN_PT_SMALL = 14, 10          # 本文 / 注記（role=caption|chrome）
LARGE_PX = 24                                  # 24px(18pt) 以上は大きい文字（3:1）
BODY_IMAGE_RATIO = 0.4
OVERLAP_MIN_AREA = 4


def _v(rule, slide, message, severity="error"):
    return {"rule": rule, "slide": slide, "message": message, "severity": severity}


def errors(violations):
    return [v for v in violations if v["severity"] == "error"]


def _r(el):
    return el.get("box") if el["kind"] == "text" else el["rect"]


def _inter(a, b):
    ix = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
    iy = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
    return ix * iy if ix > 0 and iy > 0 else 0


def _contains(a, b, tol=2):
    return (a["x"] - tol <= b["x"] and a["y"] - tol <= b["y"]
            and a["x"] + a["w"] + tol >= b["x"] + b["w"] and a["y"] + a["h"] + tol >= b["y"] + b["h"])


def check_model(model, info: TemplateInfo):
    out = []
    keepout = [r.to_dict() for r in info.keepout]
    for s in model:
        n = s["index"]
        els = s["elements"]
        has_title = any(e["kind"] == "text" and (e.get("role") == "title" or e.get("ph") == "title") for e in els)
        if not has_title and s["layout"] != "closing":
            out.append(_v("titleMissing", n, "タイトル（data-role=\"title\" または data-ph=\"title\"）がありません"))
        for e in els:
            k, rect = e["kind"], _r(e)
            label = f"{k}#{e['idx']}"
            if k == "text":
                if e.get("overflow"):
                    out.append(_v("overflow", n, f"{label}: 文字が枠からはみ出しています。幅・高さを広げるか文章を減らしてください"))
                for p in e["paras"]:
                    for run in p["runs"]:
                        if "text" not in run:
                            continue
                        pt = run["size_px"] * 0.75
                        small = e.get("role") in ("caption", "chrome") or e.get("chrome")
                        floor = MIN_PT_SMALL if small else MIN_PT_DEFAULT
                        if pt < floor:
                            out.append(_v("fontMin", n, f"{label}: {pt:g}pt は下限 {floor}pt 未満です"))
                        need = 3.0 if run["size_px"] >= LARGE_PX else 4.5
                        ratio = theme.contrast("#" + run["color"], "#" + e["bg"])
                        if ratio < need:
                            out.append(_v("contrast", n, f"{label}: 文字色 #{run['color']} と背景 #{e['bg']} のコントラスト比 {ratio:.1f} が {need} 未満です"))
            if k == "table":
                for row in e["table"]["rows"]:
                    for c in row["cells"]:
                        for p in c["paras"]:
                            for run in p["runs"]:
                                if "text" in run and run["size_px"] * 0.75 < MIN_PT_DEFAULT:
                                    out.append(_v("fontMin", n, f"{label}: 表の文字 {run['size_px'] * 0.75:g}pt は下限 {MIN_PT_DEFAULT}pt 未満です"))
                                bg = c["fill"]["hex"] if c["fill"] else c["bg"]
                                need = 3.0 if run.get("size_px", 0) >= LARGE_PX else 4.5
                                if "text" in run and theme.contrast("#" + run["color"], "#" + bg) < need:
                                    out.append(_v("contrast", n, f"{label}: 表の文字色 #{run['color']} と背景 #{bg} のコントラスト比が {need} 未満です"))
            if k == "image":
                if not e.get("alt"):
                    out.append(_v("imageAlt", n, f"{label}: alt がありません"))
                area = rect["w"] * rect["h"]
                if e.get("role") not in ("icon", "logo", "photo") or area > SLIDE_W * SLIDE_H * BODY_IMAGE_RATIO:
                    out.append(_v("bodyImage", n, f"{label}: 本文を画像にしないでください（画像はアイコン・ロゴ・利用者の写真だけ）"))
            if rect["x"] < -1 or rect["y"] < -1 or rect["x"] + rect["w"] > SLIDE_W + 1 or rect["y"] + rect["h"] > SLIDE_H + 1:
                out.append(_v("outOfSlide", n, f"{label}: スライドの外にはみ出しています"))
            if not e.get("chrome") and not e.get("ph") and k != "line":
                for z in keepout:
                    if _inter(rect, z) > OVERLAP_MIN_AREA:
                        out.append(_v("keepout", n, f"{label}: テンプレートのヘッダー・フッター領域に入っています"))
                        break
        # 重なり
        cand = [e for e in els if e["kind"] in ("text", "shape", "image", "table", "chart")
                and not (e["kind"] == "text" and not e["paras"])]
        for i, a in enumerate(cand):
            for b in cand[i + 1:]:
                if a["overlap"] or b["overlap"]:
                    continue
                ra, rb = _r(a), _r(b)
                if _inter(ra, rb) <= OVERLAP_MIN_AREA:
                    continue
                if (a["kind"] == "shape" and _contains(ra, rb)) or (b["kind"] == "shape" and _contains(rb, ra)):
                    continue
                out.append(_v("overlap", n, f"{a['kind']}#{a['idx']} と {b['kind']}#{b['idx']} が重なっています（意図的なら data-overlap を両方に付ける）"))
    return out


def check_pptx(path: Path):
    from pptx import Presentation

    prs = Presentation(str(path))
    W, H = prs.slide_width, prs.slide_height
    tol = 9525
    out = []
    for i, s in enumerate(prs.slides, start=1):
        for sh in s.shapes:
            if sh.left is None:
                continue
            if sh.left < -tol or sh.top < -tol or sh.left + sh.width > W + tol or sh.top + sh.height > H + tol:
                out.append(_v("pptxBounds", i, f"{sh.name}: スライドの外にはみ出しています"))
            if sh.shape_type == 13 and sh.width * sh.height > W * H * BODY_IMAGE_RATIO:
                out.append(_v("pptxPicture", i, f"{sh.name}: 大きな画像があります（本文を画像にしない）"))
            if sh.has_text_frame:
                for p in sh.text_frame.paragraphs:
                    for r in p.runs:
                        if r.font.size is not None and r.font.size.pt < MIN_PT_SMALL:
                            out.append(_v("pptxFontMin", i, f"{sh.name}: {r.font.size.pt:g}pt は下限 {MIN_PT_SMALL}pt 未満です"))
    return out
```

- [ ] **Step 4: テストを実行する**

Run: `"$PY" -m pytest tests/test_check.py`
Expected: すべて PASS。`test_text_inside_shape_is_fine` が失敗する場合は、`text_el` の既定 `bg="FFFFFF"` と色 `FFFFFF` のコントラストを疑う（テスト側で `t["bg"] = "1F3A5F"` を設定済み）。

- [ ] **Step 5: コミット**

```bash
git add skills/pptx-deck
git commit -m "feat: はみ出し・重なり・文字サイズ・コントラストの最小限の検査を追加"
```

---

### Task 8: 3 案ページと最終 HTML の統合（variants）

**Files:**
- Create: `skills/pptx-deck/pptx_deck/variants.py`
- Test: `skills/pptx-deck/tests/test_variants.py`

**Interfaces:**
- Produces: `variants.collect(work: Path) -> dict[str, dict[str, str]]`（`work/slides/NN-X.html` の NN → 案の記号 → HTML）、`variants.assemble(work: Path, round_no: int = 1) -> Path`（`work/variants.html` を書く）、`variants.parse_answers(md: str) -> dict[str, dict]`（`{"01": {"choice": "B", "comment": "…"}}`）、`variants.finalize(work: Path, answers_md: str, allow_comments: bool = False) -> Path`（`work/final.html` を書く。選択が欠けている／`FIX`／コメントが未反映なら `ValueError` に全件を列挙）
- 約束: 断片は `work/slides/NN-X.html`（NN は 2 桁、X は A〜Z）。中身は `<section class="slide" …>…</section>` 1 つ。`variants.html`・`final.html` は `theme.css`・`base.css`・`chart-preview.js` を相対パスで読む。`variants.html` は、送信で `window.__answersMd`（Markdown）と `window.__submitted = true` を設定する。回答の形式: `## S01` / `- 選択: B` / `- コメント: …`。案が 1 つだけのスライドは「採用（A）／要修正（FIX）」の選択になる。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_variants.py`:

```python
import pytest

from pptx_deck import variants


def frag(text):
    return f'<section class="slide" data-layout="content"><div class="pp-text" data-role="title">{text}</div></section>'


def make(work, spec):
    d = work / "slides"
    d.mkdir(parents=True)
    for name, text in spec.items():
        (d / f"{name}.html").write_text(frag(text), encoding="utf-8")


def test_collect_groups_by_number(tmp_path):
    make(tmp_path, {"01-A": "a1", "01-B": "b1", "02-A": "a2", "readme": "x"})
    got = variants.collect(tmp_path)
    assert sorted(got) == ["01", "02"] and sorted(got["01"]) == ["A", "B"]


def test_collect_requires_slides(tmp_path):
    with pytest.raises(ValueError, match="slides"):
        variants.collect(tmp_path)


def test_assemble_has_choices_and_submit_hook(tmp_path):
    make(tmp_path, {"01-A": "a1", "01-B": "b1", "01-C": "c1", "02-A": "a2"})
    html = variants.assemble(tmp_path, round_no=2).read_text(encoding="utf-8")
    assert html.count('type="radio"') == 3 + 2            # 3 案 ＋ 1 案（採用／要修正）
    assert 'value="FIX"' in html and 'value="C"' in html
    assert "window.__answersMd" in html and "window.__submitted" in html
    assert "round: 2" in html
    assert 'href="theme.css"' in html and 'href="base.css"' in html
    assert "a1" in html and "c1" in html


def test_parse_answers():
    md = "---\ndeck: x\nround: 1\n---\n## S01\n- 選択: B\n- コメント: 色を濃く\n## S02\n- 選択: A\n- コメント: \n"
    assert variants.parse_answers(md) == {"01": {"choice": "B", "comment": "色を濃く"},
                                          "02": {"choice": "A", "comment": ""}}


ANS_OK = "## S01\n- 選択: B\n- コメント: \n## S02\n- 選択: A\n- コメント: \n"


def test_finalize_picks_selected_in_order(tmp_path):
    make(tmp_path, {"01-A": "a1", "01-B": "b1", "02-A": "a2"})
    out = variants.finalize(tmp_path, ANS_OK).read_text(encoding="utf-8")
    assert "b1" in out and "a1" not in out and out.index("b1") < out.index("a2")
    assert 'href="theme.css"' in out and out.count("<section") == 2


def test_finalize_lists_every_problem(tmp_path):
    make(tmp_path, {"01-A": "a1", "01-B": "b1", "02-A": "a2", "03-A": "a3"})
    md = "## S01\n- 選択: B\n- コメント: 色を変えて\n## S02\n- 選択: FIX\n- コメント: 直して\n"
    with pytest.raises(ValueError) as e:
        variants.finalize(tmp_path, md)
    msg = str(e.value)
    assert "S01" in msg and "色を変えて" in msg and "S02" in msg and "S03" in msg
    assert not (tmp_path / "final.html").exists()


def test_finalize_can_ignore_comments(tmp_path):
    make(tmp_path, {"01-A": "a1", "01-B": "b1", "02-A": "a2"})
    md = "## S01\n- 選択: B\n- コメント: メモ\n## S02\n- 選択: A\n- コメント: \n"
    assert variants.finalize(tmp_path, md, allow_comments=True).exists()
```

- [ ] **Step 2: 失敗を確認する**

Run: `"$PY" -m pytest tests/test_variants.py`
Expected: FAIL（`variants` が未実装）

- [ ] **Step 3: 実装する**

`pptx_deck/variants.py`:

```python
"""3 案ページ（variants.html）の生成、回答の解析、最終 HTML（final.html）の統合。"""
import html as _html
import re
from pathlib import Path

FRAG = re.compile(r"^(\d{2})-([A-Z])\.html$")
HEAD = ('<!doctype html><html lang="ja"><head><meta charset="utf-8"><title>{title}</title>'
        '<link rel="stylesheet" href="theme.css"><link rel="stylesheet" href="base.css">'
        '<script src="chart-preview.js" defer></script>{extra}</head><body>')

_STYLE = """<style>
body{font-family:'BIZ UDPGothic','Yu Gothic','Meiryo',sans-serif;margin:0;padding:24px;background:#E5E5E5}
.wrap{max-width:1700px;margin:0 auto}
h1{font-size:22px;margin:0 0 4px}.lead{color:#595959;margin:0 0 24px}
.sl{background:#fff;border:1px solid #BFBFBF;border-radius:8px;padding:16px;margin:0 0 20px}
.sl h2{font-size:18px;margin:0 0 12px}
.row{display:flex;gap:16px;flex-wrap:wrap;align-items:flex-start}
.opt{display:flex;flex-direction:column;gap:6px}
.opt label{font-weight:700;display:flex;gap:6px;align-items:center;cursor:pointer}
.thumb{width:512px;height:288px;overflow:hidden;border:1px solid #BFBFBF;position:relative}
.thumb .scaled{width:1280px;height:720px;transform:scale(.4);transform-origin:0 0}
.thumb .slide{margin:0}
textarea{width:100%;box-sizing:border-box;height:56px;margin-top:12px;font:inherit;padding:6px}
.bar{position:sticky;bottom:0;background:#fff;border-top:1px solid #BFBFBF;padding:12px 24px;display:flex;gap:16px;align-items:center}
button{font:inherit;font-weight:700;padding:8px 24px;border:0;border-radius:6px;background:#1F3A5F;color:#fff;cursor:pointer}
#state{color:#1E6B52;font-weight:700}
</style>"""

_SCRIPT = """<script>
document.getElementById('submit').onclick = function () {
  var lines = ['---', 'deck: __DECK__', 'round: __ROUND__', '---'];
  document.querySelectorAll('[data-slide]').forEach(function (sec) {
    var sel = sec.querySelector('input[type=radio]:checked');
    var c = sec.querySelector('textarea').value.replace(/\\r?\\n/g, ' ');
    lines.push('## S' + sec.dataset.slide, '- 選択: ' + (sel ? sel.value : ''), '- コメント: ' + c);
  });
  window.__answersMd = lines.join('\\n') + '\\n';
  window.__submitted = true;
  document.getElementById('state').textContent = '送信しました。Claude に戻ってください。';
};
</script>"""


def collect(work: Path) -> dict[str, dict[str, str]]:
    d = Path(work) / "slides"
    if not d.is_dir():
        raise ValueError(f"{d} がありません（slides/NN-A.html の形で案を置いてください）")
    out: dict[str, dict[str, str]] = {}
    for f in sorted(d.iterdir()):
        m = FRAG.match(f.name)
        if m:
            out.setdefault(m.group(1), {})[m.group(2)] = f.read_text(encoding="utf-8")
    if not out:
        raise ValueError(f"{d} に NN-A.html の形のファイルがありません")
    return out


def assemble(work: Path, round_no: int = 1) -> Path:
    work = Path(work)
    frags = collect(work)
    parts = [HEAD.format(title="スライド案の選択", extra=_STYLE),
             '<div class="wrap"><h1>スライド案の選択</h1>'
             f'<p class="lead">ラウンド {round_no}。各スライドの案を選び、直したい点があればコメントに書いて、最後に「送信」を押してください。</p>']
    for nn, opts in frags.items():
        parts.append(f'<div class="sl" data-slide="{nn}"><h2>S{nn}</h2><div class="row">')
        letters = sorted(opts)
        choices = [(k, f"案 {k}") for k in letters] if len(letters) > 1 else [("A", "採用"), ("FIX", "要修正")]
        for k in letters:
            parts.append(f'<div class="opt"><div class="thumb"><div class="scaled">{opts[k]}</div></div>')
            if len(letters) > 1:
                parts.append(f'<label><input type="radio" name="s{nn}" value="{k}"> 案 {k}</label>')
            else:
                parts.append(f'<label><input type="radio" name="s{nn}" value="A"> 採用</label>'
                             f'<label><input type="radio" name="s{nn}" value="FIX"> 要修正</label>')
            parts.append("</div>")
        parts.append('</div><textarea placeholder="どうしてほしいか（任意）"></textarea></div>')
    parts.append('</div><div class="bar"><button id="submit">送信</button><span id="state"></span></div>')
    parts.append(_SCRIPT.replace("__DECK__", _html.escape(work.name)).replace("__ROUND__", str(round_no)))
    parts.append("</body></html>")
    out = work / "variants.html"
    out.write_text("".join(parts), encoding="utf-8")
    return out


def parse_answers(md: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    cur = None
    for line in md.splitlines():
        m = re.match(r"^## S(\d{2})\s*$", line)
        if m:
            cur = m.group(1)
            out[cur] = {"choice": "", "comment": ""}
        elif cur and line.startswith("- 選択:"):
            out[cur]["choice"] = line.split(":", 1)[1].strip()
        elif cur and line.startswith("- コメント:"):
            out[cur]["comment"] = line.split(":", 1)[1].strip()
    return out


def finalize(work: Path, answers_md: str, allow_comments: bool = False) -> Path:
    work = Path(work)
    frags = collect(work)
    ans = parse_answers(answers_md)
    problems = []
    for nn in sorted(frags):
        a = ans.get(nn)
        if not a or a["choice"] not in frags[nn]:
            got = a["choice"] if a and a["choice"] else "未回答"
            problems.append(f"S{nn}: 案が決まっていません（回答: {got}）")
        elif a["comment"] and not allow_comments:
            problems.append(f"S{nn}: コメントが未反映です: {a['comment']}")
    if problems:
        raise ValueError("\n".join(problems))
    body = "\n".join(frags[nn][ans[nn]["choice"]] for nn in sorted(frags))
    out = work / "final.html"
    out.write_text(HEAD.format(title=work.name, extra="") + body + "</body></html>", encoding="utf-8")
    return out
```

- [ ] **Step 4: テストを実行する**

Run: `"$PY" -m pytest tests/test_variants.py`
Expected: すべて PASS。

- [ ] **Step 5: ブラウザで送信を確認する（手動）**

```bash
"$PY" - <<'EOF'
import tempfile
from pathlib import Path
from pptx_deck import variants
from tests.test_variants import make
w = Path(tempfile.mkdtemp(prefix="pptx-deck-chk-")) / "demo"
make(w, {"01-A": "案A", "01-B": "案B", "02-A": "単独"})
(w / "theme.css").write_text(""); (w / "base.css").write_text("")
print(variants.assemble(w))
EOF
```

出力されたパスを Playwright MCP の `browser_navigate` で開き、ラジオを選んで「送信」を押し、`browser_evaluate` で `() => ({s: window.__submitted, md: window.__answersMd})` を実行して、`## S01` / `- 選択: …` が出ていることを確認する。

- [ ] **Step 6: コミット**

```bash
git add skills/pptx-deck
git commit -m "feat: 3 案ページの生成・回答の解析・最終 HTML の統合を追加"
```

---

### Task 9: 作業フォルダの初期化（init）と基本 CSS

**Files:**
- Create: `skills/pptx-deck/pptx_deck/initdir.py`, `assets/web/base.css`
- Modify: `skills/pptx-deck/pptx_deck/cli.py`（`init` を追加）
- Test: `skills/pptx-deck/tests/test_initdir.py`

**Interfaces:**
- Consumes: `theme.resolve/derive/theme_css`, `template.analyze/render_underlays/layout_css`, `paths.ASSETS`
- Produces: `initdir.init(workdir: Path, color: str = "navy", template: Path | None = None, force: bool = False) -> dict`（`{"workdir","color","template","notes"}`）
- 作業フォルダの中身: `theme.css`（配色＋テンプレート領域＋下地）、`base.css`、`chart-preview.js`（あれば）、`icons/`（色違いの SVG。あれば）、`_template/`（`template.<ext>`・`bg-*.png`）、`slides/`（空）、`template.json`（`{"color","template","info","footer"}`）
- `base.css` の約束（計画 B が拡充する）: `.slide` は 1280×720、`.pp-*` は `position:absolute`、`[data-role=title]` は `--title-*` の位置、`[data-ph=title]`・`[data-ph=subtitle]` は `--cover-*` の位置、フォントは `'BIZ UDPGothic','BIZ UDPゴシック','BIZ UDGothic','Yu Gothic','Meiryo'`。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_initdir.py`:

```python
import json
import shutil
from pathlib import Path

import pytest

from pptx_deck import initdir, paths

has_soffice = pytest.mark.skipif(shutil.which("soffice") is None and not Path(
    r"C:\Program Files\LibreOffice\program\soffice.exe").exists(), reason="LibreOffice なし")


@has_soffice
def test_init_writes_everything(tmp_path):
    w = tmp_path / "demo"
    r = initdir.init(w, color="green")
    assert r["color"] == "#1E6B52"
    for rel in ("theme.css", "base.css", "template.json", "slides", "_template/bg-cover.png",
                "_template/bg-body.png", "_template/bg-closing.png", "_template/template.potx"):
        assert (w / rel).exists(), rel
    css = (w / "theme.css").read_text(encoding="utf-8")
    assert "--accent: #1E6B52" in css and "--area-x: 64px" in css and "--bg: #FFFFFF" in css
    cfg = json.loads((w / "template.json").read_text(encoding="utf-8"))
    assert cfg["color"] == "#1E6B52" and cfg["template"] == "_template/template.potx"
    assert cfg["info"]["body"] == 1


def test_init_refuses_non_empty_dir(tmp_path):                # Review Focus 5
    w = tmp_path / "demo"
    w.mkdir()
    (w / "script.md").write_text("原稿", encoding="utf-8")
    with pytest.raises(FileExistsError, match="--force"):
        initdir.init(w)
    assert (w / "script.md").read_text(encoding="utf-8") == "原稿"      # 触っていない


def test_init_rejects_bad_color(tmp_path):
    with pytest.raises(ValueError):
        initdir.init(tmp_path / "x", color="red")
    assert not (tmp_path / "x").exists()


def test_init_rejects_non_169_template_before_writing(tmp_path):
    from pptx import Presentation
    bad = tmp_path / "old.pptx"
    Presentation().save(bad)
    with pytest.raises(ValueError, match="13.33"):
        initdir.init(tmp_path / "x", template=bad)
    assert not (tmp_path / "x").exists()


def test_base_css_contract():
    css = (paths.ASSETS / "web" / "base.css").read_text(encoding="utf-8")
    for token in ("1280px", "720px", "position: absolute", "var(--title-x)", "var(--cover-title-x)", "var(--closing-title-x)",
                  "BIZ UDPGothic", "var(--area-x)"):
        assert token in css
```

- [ ] **Step 2: 失敗を確認する**

Run: `"$PY" -m pytest tests/test_initdir.py`
Expected: FAIL（`initdir` が未実装）

- [ ] **Step 3: base.css を書く**

`assets/web/base.css`:

```css
/* pptx-deck 基本 CSS。1 スライド = 1280×720px（13.33×7.5in）。1px = 0.75pt。 */
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: #E5E5E5; padding: 24px 0; color: var(--text);
  font-family: 'BIZ UDPGothic', 'BIZ UDPゴシック', 'BIZ UDGothic', 'Yu Gothic', 'Meiryo', sans-serif;
}
.slide {
  position: relative; width: 1280px; height: 720px; margin: 0 auto 24px; overflow: hidden;
  background-color: var(--bg); background-size: 1280px 720px; background-repeat: no-repeat;
}
.pp-text, .pp-shape, .pp-line, .pp-image, .pp-table, .pp-chart { position: absolute; }
.pp-text { line-height: 1.5; }
.pp-text ul { list-style: none; }
.pp-text li { margin-bottom: 6px; }
.pp-line { height: 2px; }
table.pp-table { border-collapse: collapse; }

/* 役割ごとの文字（px。pt = px × 0.75） */
[data-role="title"]   { font-size: 28px; font-weight: 700; line-height: 1.35; color: var(--text); }
[data-role="lead"]    { font-size: 22px; color: var(--text); }
[data-role="body"]    { font-size: 20px; color: var(--text); }
[data-role="caption"] { font-size: 14px; color: var(--text-sub); }
[data-role="display"] { font-size: 40px; font-weight: 700; color: var(--text); }

/* テンプレートの位置に合わせる（theme.css の変数） */
[data-role="title"]:not([data-ph]) { left: var(--title-x); top: var(--title-y); width: var(--title-w); }
[data-ph="title"]    { left: var(--cover-title-x); top: var(--cover-title-y); width: var(--cover-title-w);
                       font-size: 40px; font-weight: 700; color: var(--text); }
.slide[data-layout="closing"] [data-ph="title"] { left: var(--closing-title-x); top: var(--closing-title-y); width: var(--closing-title-w); }
[data-ph="subtitle"] { left: var(--cover-subtitle-x); top: var(--cover-subtitle-y); width: var(--cover-subtitle-w);
                       font-size: 22px; color: var(--text-sub); }
.area { position: absolute; left: var(--area-x); top: var(--area-y); width: var(--area-w); height: var(--area-h); }
```

- [ ] **Step 4: 実装する**

`pptx_deck/initdir.py`:

```python
"""作業フォルダ（実行ディレクトリ直下の <名前>/）の初期化。"""
import json
import shutil
from pathlib import Path

from . import paths, template, theme

ICON_TONES = ("accent", "emphasis", "white", "gray")


def _write_icons(dst: Path, p: theme.Palette):
    src = paths.ASSETS / "icons"
    if not src.is_dir():
        return
    colors = {"accent": p.accent, "emphasis": p.emphasis, "white": "#FFFFFF", "gray": p.text_sub}
    dst.mkdir(parents=True, exist_ok=True)
    for svg in sorted(src.glob("*.svg")):
        text = svg.read_text(encoding="utf-8")
        for tone in ICON_TONES:
            (dst / f"{svg.stem}-{tone}.svg").write_text(text.replace("currentColor", colors[tone]), encoding="utf-8")


def init(workdir, color: str = "navy", template_path=None, force: bool = False) -> dict:
    work = Path(workdir)
    base = theme.resolve(color)                                   # 不正なら何も作らずに失敗
    palette = theme.derive(base)
    src = Path(template_path) if template_path else paths.ASSETS / "template" / "standard.potx"
    info = template.analyze(src)                                  # 非 16:9 などもここで失敗
    if work.exists() and any(work.iterdir()) and not force:
        raise FileExistsError(f"{work} は空ではありません。中身を確認し、上書きしてよければ --force を付けてください")
    work.mkdir(parents=True, exist_ok=True)
    tdir = work / "_template"
    tdir.mkdir(exist_ok=True)
    dst = tdir / f"template{src.suffix.lower()}"
    shutil.copyfile(src, dst)
    bg = template.render_underlays(dst, info, tdir)
    (work / "theme.css").write_text(theme.theme_css(palette) + template.layout_css(info, bg), encoding="utf-8")
    shutil.copyfile(paths.ASSETS / "web" / "base.css", work / "base.css")
    preview = paths.ASSETS / "web" / "chart-preview.js"
    if preview.exists():
        shutil.copyfile(preview, work / "chart-preview.js")
    _write_icons(work / "icons", palette)
    (work / "slides").mkdir(exist_ok=True)
    (work / "template.json").write_text(json.dumps({
        "color": base, "template": f"_template/{dst.name}", "info": info.to_dict(), "footer": None,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"workdir": str(work), "color": base, "template": str(dst), "notes": list(info.notes)}
```

`pptx_deck/cli.py` に `init` を追加（`import` と `main` を差し替え）:

```python
from pathlib import Path

def cmd_init(args) -> int:
    from . import initdir
    try:
        r = initdir.init(Path(args.workdir), color=args.color, template_path=args.template, force=args.force)
    except (FileExistsError, ValueError) as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 2
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0
```

`main` の登録部に追加:

```python
    p = sub.add_parser("init")
    p.add_argument("workdir")
    p.add_argument("--color", default="navy", help="プリセット名（navy|green|gray）または #RRGGBB")
    p.add_argument("--template", default=None, help="利用者の .potx / .pptx")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_init)
```

- [ ] **Step 5: テストを実行する**

Run: `"$PY" -m pytest tests/test_initdir.py`
Expected: すべて PASS。

- [ ] **Step 6: コミット**

```bash
git add skills/pptx-deck
git commit -m "feat: 作業フォルダの初期化（配色・テンプレート領域・下地）と基本 CSS を追加"
```

---

### Task 10: `build` / `check` / `variants` / `finalize` コマンドと通しの確認

**Files:**
- Modify: `skills/pptx-deck/pptx_deck/cli.py`
- Test: `skills/pptx-deck/tests/test_cli_build.py`

**Interfaces:**
- Consumes: Task 1〜9 のすべて
- Produces（CLI。`python run.py …`）:
  - `check <html>`: 標準出力に違反の JSON、`error` があれば終了コード 1
  - `build <workdir> [--footer 文言]`: `<workdir>/final.html` → 計測 → 検査 → `<workdir>/<名前>.pptx` → 出力後検査 → 確認用 PNG を OS の一時フォルダ（`paths.temp_dir(<名前>)/render`）に出す。出力 JSON: `{"ok": bool, "violations": [...], "pptx": str, "pngs": [...], "notes": [...]}`。検査に `error` があれば PPTX を作らず終了コード 1
  - `variants <workdir> [--round N]`: `variants.html` を作り、パスを出す
  - `finalize <workdir> --answers <md> [--allow-comments]`: `final.html` を作る。問題があれば全件を出して終了コード 2

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_cli_build.py`（通しの確認。LibreOffice があれば画像も確認）:

```python
import json
import shutil
from pathlib import Path

import pytest
from pptx import Presentation

from pptx_deck import cli, initdir, variants

has_soffice = pytest.mark.skipif(shutil.which("soffice") is None and not Path(
    r"C:\Program Files\LibreOffice\program\soffice.exe").exists(), reason="LibreOffice なし")

COVER = """<section class="slide" data-layout="cover">
<div class="pp-text" data-ph="title">クラウド移行の承認依頼</div>
<div class="pp-text" data-ph="subtitle">2026年10月 情報システム部</div></section>"""

CONTENT = """<section class="slide" data-layout="content">
<div class="pp-text" data-role="title" style="height:44px">B案を採用し、年間5,800万円を削減する</div>
<div class="pp-shape" style="left:64px;top:160px;width:540px;height:300px;background:var(--accent-light)"></div>
<div class="pp-text" data-role="body" style="left:88px;top:184px;width:492px"><ul><li>初期費用は3案で最小</li><li>運用は既存チームで可能</li></ul></div>
<div class="pp-chart" data-chart='{"type":"bar","categories":["現行","B案"],"series":[{"name":"費用","values":[120,62]}],"highlight":1}' style="left:660px;top:160px;width:540px;height:300px"></div>
<div class="pp-text" data-role="caption" data-chrome style="left:64px;top:640px;width:700px;height:24px">出典: 社内試算（2026年9月）</div>
</section>"""


def prepare(tmp_path, content=CONTENT):
    w = tmp_path / "demo"
    initdir.init(w, color="navy")
    (w / "slides").mkdir(exist_ok=True)
    (w / "slides" / "01-A.html").write_text(COVER, encoding="utf-8")
    (w / "slides" / "02-A.html").write_text(content, encoding="utf-8")
    (w / "slides" / "02-B.html").write_text(content.replace("B案を採用", "B案を採る"), encoding="utf-8")
    return w


@has_soffice
def test_end_to_end(tmp_path, capsys):
    w = prepare(tmp_path)
    assert cli.main(["variants", str(w)]) == 0
    assert (w / "variants.html").exists()
    ans = tmp_path / "ans.md"
    ans.write_text("## S01\n- 選択: A\n- コメント: \n## S02\n- 選択: B\n- コメント: \n", encoding="utf-8")
    assert cli.main(["finalize", str(w), "--answers", str(ans)]) == 0
    capsys.readouterr()
    assert cli.main(["build", str(w)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True and out["violations"] == []
    prs = Presentation(w / "demo.pptx")
    assert [s.slide_layout.name for s in prs.slides] == ["表紙", "本文"]
    assert prs.slides[1].shapes.title.text_frame.text.startswith("B案を採る")
    assert any(s.has_chart for s in prs.slides[1].shapes)
    assert len(out["pngs"]) == 2 and all(Path(p).exists() for p in out["pngs"])
    assert str(w) not in out["pngs"][0]                       # 確認用の画像は作業フォルダに出さない


def test_build_stops_on_errors_and_writes_no_pptx(tmp_path, capsys):
    bad = CONTENT.replace('style="left:88px;top:184px;width:492px"', 'style="left:88px;top:184px;width:492px;font-size:14px"')
    w = prepare(tmp_path, content=bad)
    ans = tmp_path / "ans.md"
    ans.write_text("## S01\n- 選択: A\n- コメント: \n## S02\n- 選択: A\n- コメント: \n", encoding="utf-8")
    cli.main(["finalize", str(w), "--answers", str(ans)])
    capsys.readouterr()
    assert cli.main(["build", str(w)]) == 1
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is False and any(v["rule"] == "fontMin" for v in out["violations"])
    assert not (w / "demo.pptx").exists()


def test_finalize_reports_all_problems(tmp_path, capsys):
    w = prepare(tmp_path)
    ans = tmp_path / "ans.md"
    ans.write_text("## S01\n- 選択: A\n- コメント: 直して\n", encoding="utf-8")
    assert cli.main(["finalize", str(w), "--answers", str(ans)]) == 2
    err = capsys.readouterr().err
    assert "S01" in err and "S02" in err


def test_check_command(tmp_path, capsys):
    w = prepare(tmp_path)
    ans = tmp_path / "ans.md"
    ans.write_text("## S01\n- 選択: A\n- コメント: \n## S02\n- 選択: A\n- コメント: \n", encoding="utf-8")
    cli.main(["finalize", str(w), "--answers", str(ans)])
    capsys.readouterr()
    assert cli.main(["check", str(w / "final.html"), "--workdir", str(w)]) == 0
    assert json.loads(capsys.readouterr().out) == []
```

- [ ] **Step 2: 失敗を確認する**

Run: `"$PY" -m pytest tests/test_cli_build.py`
Expected: FAIL（サブコマンドが未実装）

- [ ] **Step 3: 実装する**

`pptx_deck/cli.py` に追加（`cmd_init` の近く）:

```python
def _load_cfg(work: Path):
    from . import template, theme
    cfg = json.loads((work / "template.json").read_text(encoding="utf-8"))
    return cfg, template.TemplateInfo.from_dict(cfg["info"]), theme.derive(cfg["color"])


def cmd_check(args) -> int:
    from . import check, measure
    html = Path(args.html)
    work = Path(args.workdir) if args.workdir else html.parent
    _, info, _ = _load_cfg(work)
    violations = check.check_model(measure.measure(html), info)
    print(json.dumps(violations, ensure_ascii=False, indent=2))
    return 1 if check.errors(violations) else 0


def cmd_build(args) -> int:
    from . import build, check, measure, render
    work = Path(args.workdir).resolve()
    name = work.name
    cfg, info, palette = _load_cfg(work)
    html = work / "final.html"
    if not html.exists():
        print("エラー: final.html がありません（先に finalize を実行してください）", file=sys.stderr)
        return 2
    model = measure.measure(html)
    violations = check.check_model(model, info)
    result = {"ok": False, "violations": violations, "pptx": None, "pngs": [], "notes": list(info.notes)}
    if check.errors(violations):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1
    out = work / f"{name}.pptx"
    footer = args.footer if args.footer is not None else cfg.get("footer")
    build.build(model, work / cfg["template"], info, palette, out, base_dir=work, footer=footer, work_name=name)
    violations += check.check_pptx(out)
    result["violations"] = violations
    result["pptx"] = str(out)
    try:
        result["pngs"] = [str(p) for p in render.pptx_to_pngs(out, paths.temp_dir(name) / "render")]
    except RuntimeError as e:
        result["notes"].append(str(e))
    result["ok"] = not check.errors(violations)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


def cmd_variants(args) -> int:
    from . import variants
    print(variants.assemble(Path(args.workdir), round_no=args.round))
    return 0


def cmd_finalize(args) -> int:
    from . import variants
    md = Path(args.answers).read_text(encoding="utf-8")
    try:
        print(variants.finalize(Path(args.workdir), md, allow_comments=args.allow_comments))
    except ValueError as e:
        print(f"エラー:\n{e}", file=sys.stderr)
        return 2
    return 0
```

`main` の登録部に追加:

```python
    p = sub.add_parser("check")
    p.add_argument("html")
    p.add_argument("--workdir", default=None)
    p.set_defaults(fn=cmd_check)
    p = sub.add_parser("build")
    p.add_argument("workdir")
    p.add_argument("--footer", default=None)
    p.set_defaults(fn=cmd_build)
    p = sub.add_parser("variants")
    p.add_argument("workdir")
    p.add_argument("--round", type=int, default=1)
    p.set_defaults(fn=cmd_variants)
    p = sub.add_parser("finalize")
    p.add_argument("workdir")
    p.add_argument("--answers", required=True)
    p.add_argument("--allow-comments", action="store_true")
    p.set_defaults(fn=cmd_finalize)
```

- [ ] **Step 4: テストを実行する**

Run: `"$PY" -m pytest tests/test_cli_build.py`
Expected: すべて PASS。`test_end_to_end` が検査で落ちるときは、出力 JSON の `violations` を読む。多いのは ① 見出しの高さ指定（`height:44px`）と折り返し（`overflow`）② 出典（`data-chrome`）が下端のフッター領域に入る場合の `keepout`（`data-chrome` は除外される）③ グラフの中のテキストは検査対象外。

- [ ] **Step 5: 全テストと目視確認**

```bash
"$PY" -m pytest
python run.py doctor
```

Expected: 全テスト PASS。次に、通しのテストで出る PNG（`%TEMP%\pptx-deck\demo\render\`）を Read で開き、(a) 表紙のタイトル・副題がテンプレートの位置にある、(b) 本文の見出し・面・グラフ・出典が重ならず、下端に罫線とページ番号がある、を確認する。差が大きい場合（折り返し位置の違い）は、`font_biz_udp_gothic` が false（代替フォントで計測）が原因の可能性があるため、その旨を記録する。

- [ ] **Step 6: 利用者のテンプレートでの確認（手動）**

利用者に、実際に使う会社テンプレート（`.potx` と `.pptx` を各 1 本）のパスを聞く。

```bash
python run.py init "$TEMP/chk-tpl" --template "<利用者のテンプレート>" --color navy
```

`init` の出力の `notes`（代替になったレイアウト）を利用者に伝え、`_template/bg-body.png`・`bg-cover.png` を Read で開いて、会社のロゴ・ヘッダー・フッターが下地に出ていることを確認する。受入条件 5 の確認はここで行う（テンプレートが手元になければ、`tests/test_template.py` の変換済み `.pptx` を代わりに使い、利用者の実物での確認は計画 B の通しで行う）。

- [ ] **Step 7: コミット**

```bash
git add skills/pptx-deck
git commit -m "feat: check・build・variants・finalize コマンドを追加し、通しで PPTX を出力できるようにする"
```

---

## 計画 A の完了条件

- `"$PY" -m pytest` がすべて通る。
- `python run.py init <名前> --color navy` → 断片 `slides/NN-X.html` → `variants` → （HTML で選択）→ `finalize` → `build` が通り、`<名前>/<名前>.pptx` と確認用 PNG（OS の一時フォルダ）が出る。
- 利用者のテンプレートを `--template` で指定でき、表紙・裏表紙・ヘッダー・フッターがテンプレートのマスターに従う（標準テンプレートと変換済み `.pptx` で確認済み）。
- 計画 B（テンプレート一式・SKILL.md・通しのサンプル・README・旧スキルの置き換えの仕上げ）に進める。

## 自己レビュー（作成時）

- **SPEC の対応**: 流れ 3〜5 → Task 8・10。変換方式 → Task 4・5・6。テンプレートへの従い方 → Task 3・5（`.potx`・`.pptx`、表紙・裏表紙・ヘッダー・フッター、フォント・配色は常に固定）。実行環境（venv・承認・MCP を使わない計測）→ Task 1・4。体裁の検査 → Task 7。置き場所 → Task 1・9・10（確認用 PNG は `tempfile`、成果物は作業フォルダ）。受入条件 1・2・6・8 は計画 B。
- **型の整合**: `TemplateInfo.to_dict/from_dict`（Task 3）を Task 9・10 の `template.json` が使う。`build.build` の引数（`model, template_path, info, palette, out, base_dir, footer, work_name`）は Task 5 の定義と Task 6・10 の呼び出しで一致。`charts.add_chart(slide, el, palette)` は Task 5 の呼び出しと Task 6 の定義で一致。`check.check_model(model, info)` は Task 7・10 で一致。
- **SPEC との差**: SPEC の置き場所の表は「テンプレートの下地画像」を一時フォルダに置くとしたが、HTML が相対パスで読むため、この計画では**作業フォルダの `_template/`** に置く（再生成できる、確認用 PNG とは別物）。確認用 PNG・SVG の画像化・LibreOffice の作業は一時フォルダのまま。この差は利用者に伝える。
