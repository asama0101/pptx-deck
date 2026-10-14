# pptx-deck 改善 実装計画

> **実装担当（エージェント）へ:** 必須サブスキル: superpowers:subagent-driven-development（推奨）または superpowers:executing-plans で、このプランをタスク単位で実装する。手順はチェックボックス（`- [ ]`）で進捗を管理する。

**Goal:** 承認フローの手間を減らし、LibreOffice なしで動かし、完成した PPTX を同じスキルで再修正でき、プラグインとして導入できるようにする（SPEC の 9 項目）。

**Architecture:** 既存の `pptx_deck`（Python パッケージ）と `run.py`（標準ライブラリのみの入口）を保ったまま、(1) 実行する Python の選択（`env.py`）、(2) 下地画像の廃止と HTML 撮影による確認画像（`template.py`・新 `preview.py`）、(3) レビューページの前回承認の自動選択・承認で次へ（`variants.py` の JS）、(4) 設計図と原稿のレビューページ（新 `plan_review.py`、`variants._page` を再利用）、(5) 作業フォルダを `<名前>/source/` に置く構成と、再生成・指紋・整理（新 `lifecycle.py`、`paths.py`、`cli.py`）を足す。最後にリポジトリを `plugins/pptx-deck/` へ再配置し、スキルを 4 入口に分ける。

**Tech Stack:** Python 3.10 以上（3.14 で確認）、python-pptx 1.0.2、Playwright 1.52.0（Python）、pymupdf 1.28.2、lxml、標準の `unittest`（新しい依存は足さない）、Claude Code プラグイン。

**Spec:** `docs/specs/2026-10-14_2117_pptx-deck-improve.md`（このプランは SPEC の 9 項目と受入条件 1〜13 を実装する）

## Global Constraints

- Windows 専用。コードは `X | None` の型注釈を使う（Python 3.10 以上）。
- 依存は `python-pptx==1.0.2`・`playwright==1.52.0`・`pymupdf==1.28.2`・`lxml>=5` のみ。新しい依存を足さない（テストは `unittest`）。
- LibreOffice・PowerPoint COM を一切呼ばない。`soffice` という文字列がコードに残らない（ドキュメントの「使わない」という説明を除く）。
- 承認なしに仮想環境を作らない。システムの Python には `pip install` しない。
- 削除は、既知の派生ファイル（`variants.html`・`final-review.html`・`plan-review.html`・`final.html`・`theme.css`・`base.css`・`chart-preview.js`・`icons/`・`_template/bg-*.png`）に限る。`source/` にある未知のファイルは消さない。
- コメントとコミットメッセージは日本語。コミットは `feat:`・`fix:`・`refactor:`・`docs:`・`test:` の接頭辞（リポジトリの既存慣習）。コミット本文の末尾に次の 2 行を付ける。
  `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_018NtzbzUvwSVsc4K6awjtC6`
- GitHub への push・外部公開は、利用者の了承を得てから行う（このプランの範囲では push しない）。
- `~/.claude/skills/pptx-deck`（リンク）の取り外しは、導入の確認後に利用者の了承を得てから行う。
- テストの実行コマンド（以下、`$PY`）: `"$LOCALAPPDATA/pptx-deck/venv/Scripts/python.exe" -m unittest discover -s tests -v`（Playwright が要るテストがあるため、venv の Python で実行する）。
- 実行場所はリポジトリのルート（`C:\Users\sioay\OneDrive\github\pptx-deck`）。ブランチは `feat/plugin-and-review-flow`。

## Review Focus

SPEC が暗に前提としているが、タスクのテストが直接は扱わない入力・状態。各行は、担当タスクのテストに入れてある。

1. **旧形式の作業フォルダ**（`source/` がなく `template.json` が直下）で、コマンドが落ちない。`reopen` は「旧形式」と報告する（Task 7・9）。
2. **回答ファイルの並び**: `answers-10.md` が `answers-2.md` より後に来る。`answers-final.md` が最後。`answers-plan-*.md` は混ざらない。回答が 0 件でも落ちない（Task 5）。
3. **テンプレートの背景が画像やグラデーション**: 白で近似し、`init` の `notes` に出す（Task 3）。
4. **手直しした PPTX を `build` が黙って上書きしない**: 指紋が違えば exit 4。`--force` と `--out` で回避できる（Task 8）。
5. **システムの Python の版違い・chromium なし**: venv に回る。どちらもなければ exit 3 で案内する（Task 2）。
6. **整理が未知のファイルを消さない**: `source/` に利用者が置いたファイルは残る（Task 8）。

---

## ファイル構成（タスクで作る・変える物）

| ファイル | 役割 | 区分 |
|---|---|---|
| `tests/_paths.py` | テストから `pptx_deck` を import できるようにする。再配置の前後どちらでも動く | 新規 |
| `tests/test_*.py` | タスクごとのテスト | 新規 |
| `skills/pptx-deck/pptx_deck/env.py` | 実行する Python の選択（`probe`・`missing`・`select_python`）、`setup` | 変更 |
| `skills/pptx-deck/run.py` | 選択した Python で `pptx_deck` を実行する入口 | 変更 |
| `skills/pptx-deck/pptx_deck/template.py` | 下地画像をやめ、レイアウトの背景色を XML から読む | 変更 |
| `skills/pptx-deck/pptx_deck/preview.py` | `final.html` を Chromium で撮って確認用の画像にする | 新規 |
| `skills/pptx-deck/pptx_deck/render.py` | LibreOffice の描画 | 削除 |
| `skills/pptx-deck/pptx_deck/initdir.py` | 作業フォルダ（`source/`）の作成、派生ファイルの書き出し（`write_derived`） | 変更 |
| `skills/pptx-deck/pptx_deck/paths.py` | `resolve_work`・`deck_dir`・`deck_name` | 変更 |
| `skills/pptx-deck/pptx_deck/variants.py` | 回答ファイルの扱い、前回承認の自動選択、承認で次へ、設計図と原稿のページの描画 | 変更 |
| `skills/pptx-deck/pptx_deck/plan_review.py` | `design.md`・`script.md` を読んでレビューページ用の HTML を作る | 新規 |
| `skills/pptx-deck/pptx_deck/lifecycle.py` | 指紋（`build.json`）、整理（`prune`）、`clean`、`reopen` | 新規 |
| `skills/pptx-deck/pptx_deck/cli.py` | サブコマンド（`doctor`・`init`・`build`・`variants`・`finalize`・`review-final`・`review-plan`・`reopen`・`clean`） | 変更 |
| `skills/pptx-deck/SKILL.md` ほか | スキルを 4 入口に分け、参照文書を更新（Task 13） | 変更・新規 |
| `plugins/pptx-deck/…`・`.claude-plugin/marketplace.json` | プラグインとしての再配置（Task 12・14） | 移動・新規 |

---

### Task 1: テストの足場

**Files:**
- Create: `tests/_paths.py`
- Create: `tests/test_paths.py`

**Interfaces:**
- Produces: `tests._paths.PKG`（`pptx_deck` と `run.py` があるフォルダの `Path`）、`tests._paths.REPO`（リポジトリのルート）。import すると `PKG` が `sys.path` に入る。

- [ ] **Step 1: `tests/_paths.py` を書く**

```python
"""テストから pptx_deck を import するための足場。再配置（skills → plugins）の前後どちらでも動く。"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
_PLUGIN = REPO / "plugins" / "pptx-deck"
PKG = _PLUGIN if (_PLUGIN / "pptx_deck").is_dir() else REPO / "skills" / "pptx-deck"
if str(PKG) not in sys.path:
    sys.path.insert(0, str(PKG))
```

- [ ] **Step 2: 失敗するテストを書く（`tests/test_paths.py`）**

```python
import unittest

from tests import _paths


class PkgLocationTest(unittest.TestCase):
    def test_pkg_has_entry_and_package(self):
        self.assertTrue((_paths.PKG / "run.py").is_file())
        self.assertTrue((_paths.PKG / "pptx_deck" / "cli.py").is_file())


if __name__ == "__main__":
    unittest.main()
```

`tests/__init__.py`（空）も作る。

- [ ] **Step 3: 実行して通ることを確認する**

Run: `"$LOCALAPPDATA/pptx-deck/venv/Scripts/python.exe" -m unittest discover -s tests -t . -v`
Expected: `test_pkg_has_entry_and_package ... ok`（`-t .` でリポジトリのルートを基準にするため、`from tests import _paths` が通る）。以降、`$PY` は `-s tests -t .` を付けたこのコマンドを指す。

- [ ] **Step 4: コミット**

```bash
git add tests
git commit -m "test: テストの足場（unittest と import 用の _paths）を追加"
```

---

### Task 2: 実行する Python の選択（項目 9）

**Files:**
- Modify: `skills/pptx-deck/pptx_deck/env.py`
- Modify: `skills/pptx-deck/run.py`
- Modify: `skills/pptx-deck/pptx_deck/cli.py`（`cmd_doctor`・`entry`）
- Test: `tests/test_env_select.py`

**Interfaces:**
- Produces（`pptx_deck.env`）:
  - `REQUIREMENTS: dict[str, str]` — `{"python-pptx": "==1.0.2", "playwright": "==1.52.0", "pymupdf": "==1.28.2", "lxml": ">=5"}`
  - `probe(python: Path) -> dict` — `{"python": [3, 14], "versions": {pkg: str | None}, "chromium": bool}`
  - `missing(info: dict) -> list[str]` — そろっていれば `[]`
  - `@dataclass Selection(kind: str, path: Path | None, system_missing: list[str], venv_missing: list[str])` — `kind` は `"system"`・`"venv"`・`"none"`
  - `select_python(system: Path | None = None) -> Selection`
- Consumes: `paths.venv_python()`、`paths.venv_dir()`（既存）

- [ ] **Step 1: 失敗するテストを書く（`tests/test_env_select.py`）**

```python
import unittest
from pathlib import Path
from unittest import mock

from tests import _paths  # noqa: F401
from pptx_deck import env

GOOD = {"python": [3, 14], "versions": {"python-pptx": "1.0.2", "playwright": "1.52.0", "pymupdf": "1.28.2", "lxml": "5.3.0"}, "chromium": True}


def bad(**over):
    d = {"python": [3, 14], "versions": dict(GOOD["versions"]), "chromium": True}
    d.update(over)
    return d


class MissingTest(unittest.TestCase):
    def test_all_good(self):
        self.assertEqual(env.missing(GOOD), [])

    def test_version_mismatch_is_missing(self):
        info = bad(versions={**GOOD["versions"], "playwright": "1.40.0"})
        self.assertTrue(any("playwright" in m for m in env.missing(info)))

    def test_not_installed_and_no_chromium(self):
        info = bad(versions={**GOOD["versions"], "pymupdf": None}, chromium=False)
        m = env.missing(info)
        self.assertTrue(any("pymupdf" in x for x in m))
        self.assertTrue(any("chromium" in x for x in m))

    def test_old_python(self):
        self.assertTrue(any("Python" in m for m in env.missing(bad(python=[3, 9]))))

    def test_lxml_major_only(self):
        self.assertEqual(env.missing(bad(versions={**GOOD["versions"], "lxml": "6.0.0"})), [])
        self.assertTrue(env.missing(bad(versions={**GOOD["versions"], "lxml": "4.9.0"})))

    def test_requirements_txt_matches(self):
        from tests._paths import PKG
        lines = [l.strip() for l in (PKG / "requirements.txt").read_text(encoding="utf-8").splitlines() if l.strip()]
        self.assertEqual(sorted(lines), sorted(f"{k}{v}" for k, v in env.REQUIREMENTS.items()))


class SelectTest(unittest.TestCase):
    def test_system_first(self):
        with mock.patch.object(env, "probe", return_value=GOOD):
            sel = env.select_python(Path("C:/sys/python.exe"))
        self.assertEqual((sel.kind, sel.path), ("system", Path("C:/sys/python.exe")))

    def test_falls_back_to_venv(self):
        def fake(py):
            return bad(chromium=False) if str(py).startswith("C:") and "sys" in str(py) else GOOD
        with mock.patch.object(env, "probe", side_effect=fake), \
                mock.patch.object(env.paths, "venv_python", return_value=Path("C:/v/python.exe")), \
                mock.patch.object(Path, "exists", return_value=True):
            sel = env.select_python(Path("C:/sys/python.exe"))
        self.assertEqual(sel.kind, "venv")
        self.assertTrue(sel.system_missing)

    def test_none_when_both_unusable(self):
        with mock.patch.object(env, "probe", return_value=bad(chromium=False)), \
                mock.patch.object(env.paths, "venv_python", return_value=Path("C:/nope/python.exe")), \
                mock.patch.object(Path, "exists", return_value=False):
            sel = env.select_python(Path("C:/sys/python.exe"))
        self.assertEqual(sel.kind, "none")
        self.assertIsNone(sel.path)
        self.assertTrue(sel.venv_missing)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 失敗を確認する**

Run: `$PY -k env_select`（`$PY` は Task 1 のコマンド）
Expected: FAIL（`env.REQUIREMENTS` などが未定義）

- [ ] **Step 3: `env.py` を書き換える**

`env.py` の `MODULES`・`_CHROMIUM_PROBE`・`_py`・`venv_healthy`・`status`・`ready` を、次で置き換える（`setup` は残す。`setup` が使う `venv_healthy` は残すので、下に再掲する）。

```python
"""実行する Python の選択（システム優先、なければ venv）と、venv の作成。標準ライブラリのみ。"""
import json
import subprocess
import sys
import venv
from dataclasses import dataclass
from pathlib import Path

from . import paths

# pip 名 → 要求する版。requirements.txt と同じ内容（テストで一致を確かめる）
REQUIREMENTS = {"python-pptx": "==1.0.2", "playwright": "==1.52.0", "pymupdf": "==1.28.2", "lxml": ">=5"}

_PROBE = r'''
import json, os, sys
import importlib.metadata as m
out = {"python": list(sys.version_info[:2]), "versions": {}, "chromium": False}
for pkg in ("python-pptx", "playwright", "pymupdf", "lxml"):
    try:
        out["versions"][pkg] = m.version(pkg)
    except m.PackageNotFoundError:
        out["versions"][pkg] = None
if out["versions"]["playwright"]:
    try:
        from playwright.sync_api import sync_playwright
        p = sync_playwright().start()
        out["chromium"] = os.path.exists(p.chromium.executable_path)
        p.stop()
    except Exception:
        pass
print(json.dumps(out))
'''


def probe(python: Path) -> dict:
    """指定した Python に、必要なものがどう入っているか。動かない Python は、すべて未導入として返す。"""
    empty = {"python": [0, 0], "versions": {k: None for k in REQUIREMENTS}, "chromium": False}
    try:
        r = subprocess.run([str(python), "-c", _PROBE], capture_output=True, text=True, timeout=120)
        return json.loads(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 and r.stdout.strip() else empty
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        return empty


def _version_ok(spec: str, ver: str) -> bool:
    if spec.startswith("=="):
        return ver == spec[2:]
    if spec.startswith(">="):
        return int(ver.split(".")[0]) >= int(spec[2:].split(".")[0])      # 主版だけ比べる（lxml>=5）
    return True


def missing(info: dict) -> list[str]:
    out = []
    if tuple(info.get("python", [0, 0])) < (3, 10):
        out.append("Python 3.10 以上が必要です")
    for pkg, spec in REQUIREMENTS.items():
        ver = info["versions"].get(pkg)
        if ver is None:
            out.append(f"{pkg} が未導入です")
        elif not _version_ok(spec, ver):
            out.append(f"{pkg} {ver}（要 {spec}）")
    if not info.get("chromium"):
        out.append("Playwright の chromium が使えません")
    return out


@dataclass
class Selection:
    kind: str                       # "system" | "venv" | "none"
    path: Path | None
    system_missing: list[str]
    venv_missing: list[str]


def select_python(system: Path | None = None) -> Selection:
    """システムの Python に必要なものがそろっていればそれを、なければ venv を使う。どちらも使えなければ none。"""
    system = Path(system or sys.executable)
    sys_miss = missing(probe(system))
    if not sys_miss:
        return Selection("system", system, [], [])
    vpy = paths.venv_python()
    venv_miss = missing(probe(vpy)) if vpy.exists() else ["仮想環境がありません"]
    if not venv_miss:
        return Selection("venv", vpy, sys_miss, [])
    return Selection("none", None, sys_miss, venv_miss)


def venv_healthy() -> bool:
    """venv の python.exe が実際に動くか（基底の Python が消えた venv は、ファイルがあっても動かない）。"""
    try:
        return subprocess.run([str(paths.venv_python()), "-c", "pass"],
                              capture_output=True, timeout=60).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False
```

`setup(yes)` は元のまま（`req = str(paths.SKILL_DIR / "requirements.txt")` を含む）。

- [ ] **Step 4: `run.py` を書き換える**

`main` を次にする（`from pptx_deck import env, paths` はそのまま）。

```python
def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # 子プロセス（PYTHONUTF8=1）と出力の文字コードをそろえる
    if argv[:1] == ["setup"]:
        return env.setup(yes="--yes" in argv)
    sel = env.select_python()
    if sel.kind == "none":
        print("実行できる Python 環境がありません。")
        print("- システムの Python: " + "、".join(sel.system_missing))
        print(f"- 仮想環境（{paths.venv_dir()}）: " + "、".join(sel.venv_missing))
        print(f"利用者に「{paths.venv_dir()} に仮想環境と chromium（数百 MB）を導入してよいか」を確認し、"
              "承認後に `python run.py setup --yes` を実行してください。システムの Python には何も入れません。")
        return 3
    e = {**os.environ, "PYTHONPATH": str(SKILL), "PYTHONUTF8": "1", "PPTX_DECK_PYTHON_KIND": sel.kind}
    return subprocess.call([str(sel.path), "-m", "pptx_deck", *argv], env=e)
```

- [ ] **Step 5: `cli.py` の `cmd_doctor` と `entry` を直す**

`cmd_doctor` の `out = {…}`〜`return …` を次にする（この時点では LibreOffice の項目はまだ残す。Task 4 で消す）。

```python
def cmd_doctor(args) -> int:
    out = {
        "python": {"kind": os.environ.get("PPTX_DECK_PYTHON_KIND", "unknown"), "path": sys.executable},
        "venv": str(paths.venv_dir()),
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
    return 0
```

`entry` の案内文を「仮想環境」固定でなくする。

```python
    except ModuleNotFoundError as e:
        print(f"必要なモジュールがありません: {e.name}")
        print("`python run.py doctor` で使っている Python を確認し、足りなければ利用者の承認後に `python run.py setup --yes` を実行してください。")
        return 3
```

`from . import env, paths` の `env` が未使用になるので、import を `from . import paths` に直す。

- [ ] **Step 6: テストを通す・手動で確認する**

Run: `$PY -k env_select`  → Expected: PASS
Run: `python skills/pptx-deck/run.py doctor`  → Expected: JSON に `"python": {"kind": "system" か "venv", …}` が出る。
Run: `PPTX_DECK_HOME=C:/nonexistent python skills/pptx-deck/run.py doctor`（システムに不足がある環境で）→ Expected: `kind` が `none` なら終了コード 3 と案内文。システム側がそろっていれば `system`。

- [ ] **Step 7: コミット**

```bash
git add tests/test_env_select.py skills/pptx-deck/run.py skills/pptx-deck/pptx_deck/env.py skills/pptx-deck/pptx_deck/cli.py
git commit -m "feat: 実行する Python をシステム優先で選び、足りなければ venv を使う"
```

---

### Task 3: テンプレートの背景色を XML から読む（項目 4 の下地）

**Files:**
- Modify: `skills/pptx-deck/pptx_deck/template.py`（`render_underlays`・`_sample`・`underlay_colors` を置き換え、`layout_css` を変更）
- Test: `tests/test_template_bg.py`

**Interfaces:**
- Produces（`pptx_deck.template`）:
  - `layout_bg_hex(prs, layout_index: int) -> str | None` — 単色の背景なら `"#RRGGBB"`、画像・グラデーションなら `None`
  - `background_colors(path, info: TemplateInfo) -> tuple[dict[str, str], list[str]]` — `({"cover": "#…", "body": "#…", "closing": "#…"}, notes)`。`None` は `#FFFFFF` に近似し、`notes` に理由を入れる
  - `layout_css(info, bg_hex, layout_bg=None) -> str` — 画像（`background-image`）の行を出さない

- [ ] **Step 1: 失敗するテストを書く（`tests/test_template_bg.py`）**

```python
import copy
import unittest

from lxml import etree
from pptx import Presentation

from tests import _paths  # noqa: F401
from pptx_deck import template

A = "http://schemas.openxmlformats.org/drawingml/2006/main"
P = "http://schemas.openxmlformats.org/presentationml/2006/main"


def _set_layout_bg(layout, inner_xml: str):
    cSld = layout._element.find(f"{{{P}}}cSld")
    old = cSld.find(f"{{{P}}}bg")
    if old is not None:
        cSld.remove(old)
    bg = etree.fromstring(f'<p:bg xmlns:p="{P}" xmlns:a="{A}">{inner_xml}</p:bg>')
    cSld.insert(0, bg)


class LayoutBgTest(unittest.TestCase):
    def setUp(self):
        self.prs = Presentation()      # python-pptx の既定テンプレート（マスターの背景は bgRef の bg1 = 白）

    def test_inherits_master_scheme_color(self):
        self.assertEqual(template.layout_bg_hex(self.prs, 0), "#FFFFFF")

    def test_layout_srgb_override(self):
        _set_layout_bg(self.prs.slide_layouts[1], '<p:bgPr><a:solidFill><a:srgbClr val="1F3A5F"/></a:solidFill><a:effectLst/></p:bgPr>')
        self.assertEqual(template.layout_bg_hex(self.prs, 1), "#1F3A5F")

    def test_layout_scheme_color_is_resolved_via_theme(self):
        _set_layout_bg(self.prs.slide_layouts[2], '<p:bgPr><a:solidFill><a:schemeClr val="tx1"/></a:solidFill><a:effectLst/></p:bgPr>')
        got = template.layout_bg_hex(self.prs, 2)
        self.assertRegex(got, r"^#[0-9A-F]{6}$")

    def test_gradient_returns_none(self):
        _set_layout_bg(self.prs.slide_layouts[3], '<p:bgPr><a:gradFill><a:gsLst><a:gs pos="0"><a:srgbClr val="000000"/></a:gs></a:gsLst></a:gradFill><a:effectLst/></p:bgPr>')
        self.assertIsNone(template.layout_bg_hex(self.prs, 3))


class BackgroundColorsTest(unittest.TestCase):
    def test_standard_template(self):
        from tests._paths import PKG
        path = PKG / "assets" / "template" / "standard.potx"
        info = template.analyze(path)
        colors, notes = template.background_colors(path, info)
        self.assertEqual(set(colors), {"cover", "body", "closing"})
        for v in colors.values():
            self.assertRegex(v, r"^#[0-9A-F]{6}$")

    def test_css_has_no_image(self):
        from tests._paths import PKG
        info = template.analyze(PKG / "assets" / "template" / "standard.potx")
        css = template.layout_css(info, "#FFFFFF", {"cover": "#112233", "body": "#FFFFFF", "closing": "#FFFFFF"})
        self.assertNotIn("background-image", css)
        self.assertIn('.slide[data-layout="cover"] { --bg: #112233; }', css)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 失敗を確認する**

Run: `$PY -k template_bg`  → Expected: FAIL（`layout_bg_hex` が未定義）

- [ ] **Step 3: `template.py` を直す**

先頭の `from .render import pptx_to_pngs` と `from . import paths` を削除し、`from pptx.opc.constants import RELATIONSHIP_TYPE as RT` と `from lxml import etree` を足す。`render_underlays`・`_sample`・`underlay_colors` を削除し、次を足す（`layout_css` の手前）。

```python
_NS = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main",
       "p": "http://schemas.openxmlformats.org/presentationml/2006/main"}
_THEME_KEYS = ("dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3", "accent4", "accent5", "accent6", "hlink", "folHlink")


def _theme_colors(master) -> dict[str, str]:
    """テーマの色（dk1・lt1・accent1…）→ 6 桁の 16 進。"""
    root = etree.fromstring(master.part.part_related_by(RT.THEME).blob)
    out = {}
    for key in _THEME_KEYS:
        el = root.find(f".//a:clrScheme/a:{key}", _NS)
        if el is None or len(el) == 0:
            continue
        c = el[0]
        val = c.get("val") if c.tag.endswith("srgbClr") else c.get("lastClr")
        if val:
            out[key] = val.upper()
    return out


def _color_hex(el, theme: dict[str, str], clrmap: dict[str, str]) -> str | None:
    if el.tag.endswith("srgbClr"):
        return el.get("val").upper()
    if el.tag.endswith("schemeClr"):
        key = el.get("val")
        return theme.get(clrmap.get(key, key))
    if el.tag.endswith("sysClr"):
        return (el.get("lastClr") or "FFFFFF").upper()
    return None


def layout_bg_hex(prs, layout_index: int) -> str | None:
    """レイアウト（なければマスター）の背景が単色なら '#RRGGBB'。画像・グラデーション・取れないときは None。"""
    layout = prs.slide_layouts[layout_index]
    master = layout.slide_master
    theme = _theme_colors(master)
    cm = master._element.find("p:clrMap", _NS)
    clrmap = dict(cm.attrib) if cm is not None else {}
    for part in (layout._element, master._element):
        bg = part.find("p:cSld/p:bg", _NS)
        if bg is None:
            continue
        solid = bg.find("p:bgPr/a:solidFill", _NS)
        if solid is not None and len(solid):
            h = _color_hex(solid[0], theme, clrmap)
            return f"#{h}" if h else None
        ref = bg.find("p:bgRef", _NS)
        if ref is not None and len(ref):                 # テーマの背景スタイルの参照。色の指定がある（bg1 など）
            h = _color_hex(ref[0], theme, clrmap)
            return f"#{h}" if h else None
        return None                                      # 画像・グラデーションなど
    return None


def background_colors(path, info: TemplateInfo) -> tuple[dict[str, str], list[str]]:
    """表紙・本文・裏表紙の背景色（HTML の下地）。単色でないレイアウトは白で近似し、notes に理由を返す。"""
    prs = open_template(path)
    idx = {"cover": info.cover, "body": info.body, "closing": info.closing if info.closing is not None else info.body}
    out, notes = {}, []
    for name, i in idx.items():
        h = layout_bg_hex(prs, i)
        if h is None:
            h = "#FFFFFF"
            notes.append(f"{name} の背景が単色ではないため、HTML の下地は白で近似しました（PPTX にはテンプレートの背景が出ます）。")
        out[name] = h
    return out, notes
```

`layout_css` の末尾の `root += (".slide[data-layout=\"cover\"] { background-image: …` の 4 行（`background-image` を出す部分）を削除する。`layout_bg` が渡されたとき `--bg` を出す部分（`for name in ("cover", "closing"): …`）は残す。

- [ ] **Step 4: テストを通す**

Run: `$PY -k template_bg`  → Expected: PASS（4 + 2 テスト）。`test_layout_scheme_color_is_resolved_via_theme` が失敗する場合は、既定テンプレートの `clrMap` に `tx1` が無い（`tx1` → `dk1` の対応が `clrMap` にある）ので、`clrmap.get(key, key)` が `dk1` を返すことを `print(clrmap)` で確かめる。

- [ ] **Step 5: コミット**

```bash
git add tests/test_template_bg.py skills/pptx-deck/pptx_deck/template.py
git commit -m "feat: テンプレートの下地を LibreOffice の画像ではなく背景色（XML）で扱う"
```

---

### Task 4: LibreOffice を外し、確認用の画像を HTML の撮影にする（項目 4）

**Files:**
- Create: `skills/pptx-deck/pptx_deck/preview.py`
- Modify: `skills/pptx-deck/pptx_deck/initdir.py`
- Modify: `skills/pptx-deck/pptx_deck/cli.py`（`cmd_doctor`・`cmd_build`）
- Delete: `skills/pptx-deck/pptx_deck/render.py`
- Test: `tests/test_no_libreoffice.py`

**Interfaces:**
- Produces:
  - `preview.screenshots(html: Path, out_dir: Path) -> list[Path]` — `section.slide` ごとに `slide-NN.png`
  - `initdir.write_derived(work: Path, cfg: dict) -> None` — `theme.css`・`base.css`・`chart-preview.js`・`icons/` を書く（`cfg` は `template.json` の内容: `color`・`template`・`info`・`footer`）。Task 9 の `reopen` も使う
  - `build` の出力 JSON のキー: `ok`・`violations`・`pptx`・`previews`（旧 `pngs`）・`notes`
- Consumes: `template.background_colors`・`template.layout_css`（Task 3）

- [ ] **Step 1: 失敗するテストを書く（`tests/test_no_libreoffice.py`）**

```python
import json
import re
import tempfile
import unittest
from pathlib import Path

from tests import _paths  # noqa: F401
from tests._paths import PKG
from pptx_deck import initdir


class NoLibreOfficeTest(unittest.TestCase):
    def test_no_soffice_in_code(self):
        for f in (PKG / "pptx_deck").glob("*.py"):
            self.assertNotIn("soffice", f.read_text(encoding="utf-8"), f.name)
        self.assertFalse((PKG / "pptx_deck" / "render.py").exists())

    def test_init_makes_solid_background_only(self):
        with tempfile.TemporaryDirectory() as td:
            work = Path(td) / "d"
            initdir.init(work, color="navy")
            src = work / "source" if (work / "source").is_dir() else work     # Task 7 の前後どちらでも通す
            css = (src / "theme.css").read_text(encoding="utf-8")
            self.assertNotIn("background-image", css)
            self.assertRegex(css, r"--bg: #[0-9A-Fa-f]{6}")
            self.assertEqual([p.name for p in (src / "_template").iterdir()], ["template.potx"])
            cfg = json.loads((src / "template.json").read_text(encoding="utf-8"))
            self.assertIn("info", cfg)


class PreviewTest(unittest.TestCase):
    def test_screenshots_one_per_slide(self):
        from pptx_deck import preview
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            html = td / "final.html"
            html.write_text('<!doctype html><meta charset="utf-8"><style>.slide{position:relative;width:1280px;height:720px;background:#fff;margin:0 0 24px}</style>'
                            '<section class="slide">A</section><section class="slide">B</section>', encoding="utf-8")
            out = preview.screenshots(html, td / "out")
            self.assertEqual([p.name for p in out], ["slide-01.png", "slide-02.png"])
            self.assertTrue(all(p.stat().st_size > 0 for p in out))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 失敗を確認する**

Run: `$PY -k no_libreoffice`  → Expected: FAIL（`render.py` が残っている、`preview` が無い）

- [ ] **Step 3: `preview.py` を作る**

```python
"""final.html を Chromium で開き、スライドごとの確認用の画像にする。PPTX の実描画ではない（PowerPoint で最終確認する）。"""
from pathlib import Path


def screenshots(html: Path, out_dir: Path) -> list[Path]:
    from playwright.sync_api import sync_playwright

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out: list[Path] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 720})
            page.goto(Path(html).resolve().as_uri())
            page.evaluate("document.fonts.ready.then(() => true)")
            page.wait_for_timeout(300)                          # chart-preview.js の描画を待つ
            for i, el in enumerate(page.query_selector_all("section.slide"), start=1):
                path = out_dir / f"slide-{i:02d}.png"
                el.screenshot(path=str(path))
                out.append(path)
        finally:
            browser.close()
    return out
```

- [ ] **Step 4: `initdir.py` を直す**

`init` の `render_underlays`〜`write_text(theme.css…)` の部分と、`base.css`・`chart-preview.js`・`icons/` の書き出しを `write_derived` にまとめ、`init` から呼ぶ。`init` 全体を次にする。

```python
def write_derived(work: Path, cfg: dict) -> list[str]:
    """template.json の内容から、再生成できるファイル（theme.css・base.css・chart-preview.js・icons/）を書く。notes を返す。"""
    work = Path(work)
    palette = theme.derive(cfg["color"])
    info = template.TemplateInfo.from_dict(cfg["info"])
    colors, notes = template.background_colors(work / cfg["template"], info)
    (work / "theme.css").write_text(theme.theme_css(palette) + template.layout_css(info, colors["body"], colors),
                                    encoding="utf-8")
    shutil.copyfile(paths.ASSETS / "web" / "base.css", work / "base.css")
    preview = paths.ASSETS / "web" / "chart-preview.js"
    if preview.exists():
        shutil.copyfile(preview, work / "chart-preview.js")
    _write_icons(work / "icons", palette)
    return notes


def init(workdir, color: str = "navy", template_path=None, force: bool = False, footer: str | None = None) -> dict:
    work = Path(workdir)
    base = theme.resolve(color)                                   # 不正なら何も作らずに失敗
    src = Path(template_path) if template_path else paths.ASSETS / "template" / "standard.potx"
    info = template.analyze(src)                                  # 非 16:9 などもここで失敗
    if work.exists() and any(work.iterdir()) and not force:
        raise FileExistsError(f"{work} は空ではありません。中身を確認し、上書きしてよければ --force を付けてください")
    work.mkdir(parents=True, exist_ok=True)
    tdir = work / "_template"
    tdir.mkdir(exist_ok=True)
    dst = tdir / f"template{src.suffix.lower()}"
    shutil.copyfile(src, dst)
    cfg = {"color": base, "template": f"_template/{dst.name}", "info": info.to_dict(), "footer": footer}
    (work / "template.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    notes = list(info.notes) + write_derived(work, cfg)
    design = work / "design.md"
    if not design.exists():        # 設計図の雛形。--force でも利用者が書いた設計図は上書きしない
        shutil.copyfile(paths.ASSETS / "sample" / "design.md", design)
    (work / "slides").mkdir(exist_ok=True)
    stale = [p for p in (work / "slides").iterdir()]
    if stale:      # 消さない。古い案が variants に混ざるので、利用者に確認してもらう
        notes.append(f"slides/ に既存のファイルが {len(stale)} 個あります。前の作業の案が混ざるので、不要なら削除してください")
    return {"workdir": str(work), "color": base, "template": str(dst), "notes": notes}
```

`template.json` に書く `info` は `info.to_dict()`（従来どおり）。`from . import paths, template, theme` はそのまま。

- [ ] **Step 5: `cli.py` を直す**

`cmd_doctor` から LibreOffice の項目と警告を削除し（`shutil`・`os` が不要になれば import も整理）、`cmd_build` の画像部分を置き換える。

```python
    # cmd_build の画像作成部分（pngs → previews）
    try:
        result["previews"] = [str(p) for p in preview.screenshots(html, paths.temp_dir(name) / "preview")]
    except Exception as e:        # PPTX は出ている。確認用の画像だけ作れなかったことを知らせる
        result["notes"].append(f"確認用の画像を作れませんでした: {e}")
```

`result = {"ok": False, "violations": violations, "pptx": None, "previews": [], "notes": list(info.notes)}` に変え、`from . import build, check, measure, preview` に直し、`subprocess` の import が不要になれば削除する。`git rm skills/pptx-deck/pptx_deck/render.py`。

- [ ] **Step 6: テストを通す・手動で確認する**

Run: `$PY -k no_libreoffice`  → Expected: PASS
Run: `python skills/pptx-deck/run.py doctor`  → Expected: JSON に `libreoffice` のキーがなく、`warnings` に LibreOffice が出ない。

- [ ] **Step 7: コミット**

```bash
git add -A tests skills/pptx-deck
git commit -m "feat: LibreOffice を廃止し、確認用の画像を final.html の撮影にする"
```

---

### Task 5: 回答ファイルの扱い（並び・次の回・前回承認の抽出）

**Files:**
- Modify: `skills/pptx-deck/pptx_deck/variants.py`（関数の追加のみ）
- Modify: `skills/pptx-deck/pptx_deck/cli.py`（`variants --round` の既定、`finalize`/`review-final` の `--answers` を省略可に）
- Test: `tests/test_answers.py`

**Interfaces:**
- Produces（`pptx_deck.variants`）:
  - `answer_paths(work: Path, upto: int | None = None) -> list[Path]` — `answers-N.md`（N は数字）と `answers-final.md` を、数字の昇順 → `final` の順に。`answers-plan-*.md` は含めない。`upto` は N の上限（`final` は `upto` が None のときだけ含める）
  - `plan_answer_paths(work: Path) -> list[Path]` — `answers-plan-N.md` を数字の昇順に
  - `next_round(work: Path) -> int` — 既存の `answers-N.md` の最大 N + 1（なければ 1）
  - `approved_preset(mds: list[str]) -> dict[str, dict]` — 最新の判定が承認で、コメントが空のスライドだけ。`{"03": {"c": "B", "d": 2, "v": "承認"}}`

- [ ] **Step 1: 失敗するテストを書く（`tests/test_answers.py`）**

```python
import tempfile
import unittest
from pathlib import Path

from tests import _paths  # noqa: F401
from pptx_deck import variants


def touch(d: Path, *names):
    for n in names:
        (d / n).write_text("---\n---\n", encoding="utf-8")


class AnswerPathsTest(unittest.TestCase):
    def test_numeric_order_and_final_last(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            touch(d, "answers-10.md", "answers-2.md", "answers-1.md", "answers-final.md", "answers-plan-1.md", "other.md")
            self.assertEqual([p.name for p in variants.answer_paths(d)],
                             ["answers-1.md", "answers-2.md", "answers-10.md", "answers-final.md"])
            self.assertEqual([p.name for p in variants.answer_paths(d, upto=2)], ["answers-1.md", "answers-2.md"])
            self.assertEqual([p.name for p in variants.plan_answer_paths(d)], ["answers-plan-1.md"])
            self.assertEqual(variants.next_round(d), 11)

    def test_empty(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            self.assertEqual(variants.answer_paths(d), [])
            self.assertEqual(variants.next_round(d), 1)


MD1 = "---\n---\n## S01\n- 選択: B\n- デザイン: 2\n- 判定: 承認\n- コメント: \n## S02\n- 選択: A\n- 判定: 承認\n- コメント: 直して\n## S03\n- 選択: \n- 判定: 要修正\n- コメント: 違う\n"
MD2 = "---\n---\n## S03\n- 選択: A\n- 判定: 承認\n- コメント: \n## S01\n- 選択: \n- 判定: 要修正\n- コメント: \n"


class PresetTest(unittest.TestCase):
    def test_latest_verdict_wins_and_comments_block(self):
        self.assertEqual(variants.approved_preset([MD1]), {"01": {"c": "B", "d": 2, "v": "承認"}})
        got = variants.approved_preset([MD1, MD2])
        self.assertEqual(got, {"03": {"c": "A", "d": 1, "v": "承認"}})     # S01 は後の回で要修正、S02 はコメントあり

    def test_old_answers_without_verdict_count_as_approved(self):
        md = "---\n---\n## S04\n- 選択: C\n- コメント: \n"
        self.assertEqual(variants.approved_preset([md]), {"04": {"c": "C", "d": 1, "v": "承認"}})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 失敗を確認する**

Run: `$PY -k test_answers`  → Expected: FAIL（関数が未定義）

- [ ] **Step 3: `variants.py` に関数を足す（`merge_answers` の後ろ）**

```python
_ANS_FILE = re.compile(r"^answers-(\d+|final)\.md$")
_PLAN_FILE = re.compile(r"^answers-plan-(\d+)\.md$")


def answer_paths(work: Path, upto: int | None = None) -> list[Path]:
    """answers-N.md（N は数字）を昇順に、最後に answers-final.md。answers-plan-*.md は含めない。"""
    found: list[tuple[int, Path]] = []
    for f in Path(work).glob("answers-*.md"):
        m = _ANS_FILE.match(f.name)
        if not m:
            continue
        n = int(m.group(1)) if m.group(1).isdigit() else 10 ** 9
        if upto is not None and n > upto:
            continue
        found.append((n, f))
    return [f for _, f in sorted(found)]


def plan_answer_paths(work: Path) -> list[Path]:
    found = [(int(m.group(1)), f) for f in Path(work).glob("answers-plan-*.md") if (m := _PLAN_FILE.match(f.name))]
    return [f for _, f in sorted(found)]


def next_round(work: Path) -> int:
    nums = [int(m.group(1)) for f in Path(work).glob("answers-*.md") if (m := _ANS_FILE.match(f.name)) and m.group(1).isdigit()]
    return max(nums, default=0) + 1


def approved_preset(mds: list[str]) -> dict[str, dict]:
    """回の順に重ねて、最新の判定が承認でコメントが空のスライドだけ返す（再提示の画面で選択済みにする）。"""
    cur: dict[str, dict] = {}
    for md in mds:
        for nn, a in parse_answers(md).items():
            verdict = a.get("verdict", "")
            if not verdict and not a["choice"]:
                continue
            prev = cur.get(nn, {})
            cur[nn] = {"c": a["choice"] or prev.get("c", ""), "d": a.get("design", prev.get("d", 1)),
                       "v": verdict or "承認", "m": a["comment"]}
    return {nn: {"c": x["c"], "d": x["d"], "v": x["v"]}
            for nn, x in cur.items() if x["v"] == "承認" and x["c"] and not x["m"]}
```

- [ ] **Step 4: `cli.py` の引数を直す**

`variants` の `--round` を `default=None` にし、`cmd_variants` を次にする。`finalize`・`review-final` の `--answers` は `required` を外し、省略時は `answer_paths(work)` を使う。

```python
def cmd_variants(args) -> int:
    from . import variants
    work = Path(args.workdir)
    print(variants.assemble(work, round_no=args.round or variants.next_round(work)))
    return 0


def _answers_mds(work: Path, given: list[str] | None) -> list[str]:
    from . import variants
    files = [Path(p) for p in given] if given else variants.answer_paths(work)
    return [f.read_text(encoding="utf-8") for f in files]
```

`cmd_finalize`・`cmd_review_final` の `mds = […]` を `mds = _answers_mds(Path(args.workdir), args.answers)` にする。argparse は `p.add_argument("--answers", action="append", default=None, help=…)`（`required=True` を削除）。

- [ ] **Step 5: テストを通す・コミット**

Run: `$PY -k test_answers`  → Expected: PASS

```bash
git add tests/test_answers.py skills/pptx-deck/pptx_deck/variants.py skills/pptx-deck/pptx_deck/cli.py
git commit -m "feat: 回答ファイルの並び・次の回・前回承認の抽出を足し、finalize の --answers を省略可にする"
```

---

### Task 6: レビューページ — 前回承認の自動選択と、承認で次へ（項目 1・2）

**Files:**
- Modify: `skills/pptx-deck/pptx_deck/variants.py`（`_page` の引数 `preset`、`_SCRIPT`、`assemble`、`review_final`）
- Test: `tests/test_review_page.py`

**Interfaces:**
- Consumes: `variants.approved_preset`・`variants.answer_paths`（Task 5）
- Produces: `variants._page(work, frags, round_label, final=False, prev=None, notes=None, designs=None, preset=None)`。`preset` は `approved_preset` の戻り値。ページの JS は `window.__PRESET__` ではなく埋め込み定数 `PRESET` を使う。

- [ ] **Step 1: 失敗するテストを書く（`tests/test_review_page.py`）**

```python
import tempfile
import unittest
from pathlib import Path

from tests import _paths  # noqa: F401
from pptx_deck import variants

FRAG = ('<section class="slide" data-layout="content" data-variant="{n}｜理由">'
        '<div class="pp-text" data-role="title" style="left:64px;top:30px;width:900px;height:40px">題{n}</div></section>')


def make_page(preset, final=False):
    frags = {nn: ({"A": FRAG.format(n=nn)} if final else {"A": FRAG.format(n=nn + "a"), "B": FRAG.format(n=nn + "b")})
             for nn in ("01", "02", "03")}
    return variants._page(Path("deck"), frags, "final" if final else "2", final=final, preset=preset)


class PageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls._pw = sync_playwright().start()
        cls.browser = cls._pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls._pw.stop()

    def open(self, html, td):
        f = Path(td) / "p.html"
        f.write_text(html, encoding="utf-8")
        page = self.browser.new_page(viewport={"width": 1400, "height": 900})
        page.goto(f.as_uri())
        page.wait_for_timeout(200)
        return page

    def test_preset_is_selected_and_copied(self):
        with tempfile.TemporaryDirectory() as td:
            page = self.open(make_page({"01": {"c": "B", "d": 1, "v": "承認"}}), td)
            self.assertEqual(page.evaluate("document.querySelector('.pane[data-slide=\"01\"] input[value=B]').checked"), True)
            self.assertEqual(page.evaluate("document.querySelector('.pane[data-slide=\"02\"] input[type=radio]:checked') === null"), True)
            page.click(".pane[data-slide=\"01\"] .copyBtn")
            md = page.evaluate("window.__answersMd")
            self.assertIn("## S01\n- 選択: B", md)
            self.assertIn("- 判定: 承認", md)
            self.assertNotIn("## S02", md)

    def test_final_preset_marks_approved(self):
        with tempfile.TemporaryDirectory() as td:
            page = self.open(make_page({"02": {"c": "A", "d": 1, "v": "承認"}}, final=True), td)
            self.assertEqual(page.evaluate("document.querySelector('.pane[data-slide=\"02\"] input[value=A]').checked"), True)

    def test_approve_moves_to_next_but_not_fix_or_last(self):
        with tempfile.TemporaryDirectory() as td:
            page = self.open(make_page({}), td)
            cur = "document.querySelector('#nav button[aria-current=true]').dataset.go"
            self.assertEqual(page.evaluate(cur), "01")
            page.click(".pane[data-slide=\"01\"] .verdict .ng")           # 要修正
            self.assertEqual(page.evaluate(cur), "01")
            page.click(".pane[data-slide=\"01\"] .verdict .ng")           # 外す
            page.click(".pane[data-slide=\"01\"] .verdict .ok")           # 承認
            self.assertEqual(page.evaluate(cur), "02")
            page.click(".pane[data-slide=\"02\"] .verdict .ok")
            page.click(".pane[data-slide=\"03\"] .verdict .ok")           # 最後は動かない
            self.assertEqual(page.evaluate(cur), "03")


if __name__ == "__main__":
    unittest.main()
```


- [ ] **Step 2: 失敗を確認する**

Run: `$PY -k review_page`  → Expected: FAIL（`_page()` が `preset` を受けない）

- [ ] **Step 3: `_page`・`_SCRIPT` を直す**

(a) `_page` のシグネチャに `preset: dict | None = None` を足し、末尾の `parts.append(_SCRIPT.replace(…))` を次にする。

```python
    preset_js = json.dumps(preset or {}, ensure_ascii=False).replace("</", "<\\/")
    parts.append(_SCRIPT.replace("__DECK__", deck_js).replace("__ROUND__", round_label).replace("__PRESET__", preset_js))
```

(b) `_SCRIPT` の先頭 `var panes = …` の行の後に `var PRESET = __PRESET__;` を足す。

(c) `restore()` の後に `applyPreset` を足す。

```js
  // 前回承認したスライドを選択済みにする。同じタブで入力の途中なら、その入力を優先する
  function applyPreset() {
    if (Object.keys(load()).length) return;
    panes.forEach(function (p) {
      var a = PRESET[p.dataset.slide]; if (!a) return;
      var single = p.dataset.single === '1';
      var r = $('input[type=radio][name^="s"][value="' + (single ? 'A' : a.c) + '"]', p);
      if (!r) return;                                           // 案がなくなっていれば引き継がない
      r.checked = true;
      if (!single) {
        p.dataset.verdict = '承認';
        if (a.d > 1) { var x = $('.dgroup[data-k="' + a.c + '"] input[value="' + a.d + '"]', p); if (x) x.checked = true; }
      }
    });
  }
```

(d) `setVerdict` の末尾 `refresh(); store(snapshot());` の後に次を足す。

```js
    if (v === '承認' && cur < panes.length - 1) go(cur + 1);       // 承認したら次のスライドへ（要修正と最後は動かない）
```

(e) `start()` を次にする。

```js
  function start() {
    restore();
    applyPreset();
    $$('input[type=radio][name^="s"]:checked').forEach(function (x) { x.dataset.was = '1'; });
    refresh(); store(snapshot()); go(0);
  }
```

- [ ] **Step 4: `assemble`・`review_final` から preset を渡す**

```python
# assemble の _page 呼び出し
preset = approved_preset([f.read_text(encoding="utf-8") for f in answer_paths(work, upto=round_no - 1)]) if round_no > 1 else {}
out.write_text(_page(work, frags, str(round_no), prev=prev, notes=notes, designs=designs, preset=preset), encoding="utf-8")

# review_final の _page 呼び出し（answers_md は str か list[str]）
mds = [answers_md] if isinstance(answers_md, str) else list(answers_md)
out.write_text(_page(work, one, "final", final=True, preset=approved_preset(mds)), encoding="utf-8")
```

- [ ] **Step 5: テストを通す・コミット**

Run: `$PY -k review_page`  → Expected: PASS（3 テスト）。`test_approve_moves_to_next…` が失敗する場合は、`#nav button[aria-current=true]` のセレクタが属性値の文字列 `"true"` に一致するか（`setAttribute('aria-current', j === cur)` は `"true"`/`"false"` を入れる）を確かめる。

```bash
git add tests/test_review_page.py skills/pptx-deck/pptx_deck/variants.py
git commit -m "feat: レビューページで前回承認を選択済みにし、承認で次のスライドへ移る"
```

---

### Task 7: 作業フォルダを `<名前>/source/` にする（項目 6 の構成）

**Files:**
- Modify: `skills/pptx-deck/pptx_deck/paths.py`
- Modify: `skills/pptx-deck/pptx_deck/cli.py`（全コマンドで `resolve_work`）
- Modify: `skills/pptx-deck/pptx_deck/variants.py`（`work.name` → `paths.deck_name(work)`）
- Test: `tests/test_workdir.py`

**Interfaces:**
- Produces（`pptx_deck.paths`）:
  - `resolve_work(arg) -> Path` — `<arg>/source/` があればそれ。なく、`<arg>/template.json` があれば旧形式として `<arg>`。どちらもなければ新規用に `<arg>/source`
  - `deck_dir(work: Path) -> Path` — `work.name == "source"` なら親、旧形式なら `work`
  - `deck_name(work: Path) -> str` — `deck_dir(work).name`
  - `is_legacy(work: Path) -> bool`
- `initdir.init(workdir, …)` は引数に `<名前>` を取り、`resolve_work` の結果（`<名前>/source`）に作る

- [ ] **Step 1: 失敗するテストを書く（`tests/test_workdir.py`）**

```python
import tempfile
import unittest
from pathlib import Path

from tests import _paths  # noqa: F401
from pptx_deck import initdir, paths


class ResolveTest(unittest.TestCase):
    def test_new_layout(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "deck"
            self.assertEqual(paths.resolve_work(base), (base / "source").resolve())
            (base / "source").mkdir(parents=True)
            self.assertEqual(paths.resolve_work(base), (base / "source").resolve())
            self.assertEqual(paths.deck_dir(base / "source"), base)
            self.assertEqual(paths.deck_name(base / "source"), "deck")
            self.assertFalse(paths.is_legacy(base / "source"))

    def test_legacy_layout(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "old"
            base.mkdir()
            (base / "template.json").write_text("{}", encoding="utf-8")
            w = paths.resolve_work(base)
            self.assertEqual(w, base.resolve())
            self.assertTrue(paths.is_legacy(w))
            self.assertEqual(paths.deck_name(w), "old")


class InitLayoutTest(unittest.TestCase):
    def test_init_creates_source(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "deck"
            r = initdir.init(base, color="navy")
            self.assertTrue((base / "source" / "template.json").is_file())
            self.assertFalse((base / "template.json").exists())
            self.assertTrue(r["workdir"].endswith("source"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 失敗を確認する**

Run: `$PY -k workdir`  → Expected: FAIL（`paths.resolve_work` が未定義）

- [ ] **Step 3: `paths.py` に足す**

```python
def resolve_work(arg) -> Path:
    """コマンドの <名前> を、作業フォルダ（<名前>/source）に解決する。旧形式（template.json が直下）はそのフォルダ。"""
    base = Path(arg).resolve()
    src = base / "source"
    if src.is_dir():
        return src
    if (base / "template.json").exists():
        return base
    return src


def is_legacy(work: Path) -> bool:
    return Path(work).name != "source"


def deck_dir(work: Path) -> Path:
    work = Path(work)
    return work if is_legacy(work) else work.parent


def deck_name(work: Path) -> str:
    return deck_dir(work).name
```

`temp_dir(name)` はそのまま（呼び出し側が `deck_name(work)` を渡す）。

- [ ] **Step 4: `initdir.init` を直す**

先頭を次にする（残りは Task 4 のとおり）。

```python
def init(workdir, color: str = "navy", template_path=None, force: bool = False, footer: str | None = None) -> dict:
    work = paths.resolve_work(workdir)
    base = theme.resolve(color)
    …
```

- [ ] **Step 5: `cli.py` と `variants.py` を直す**

`cli.py`: `cmd_init` は `initdir.init(Path(args.workdir), …)` のまま（`init` 内で解決する）。それ以外の、`Path(args.workdir)` を使う箇所（`cmd_build`・`cmd_variants`・`cmd_finalize`・`cmd_review_final`・`_answers_mds` を呼ぶ側・`cmd_check` の `workdir`）を `paths.resolve_work(args.workdir)` に置き換える。`cmd_build` の出力先と名前を次にする。

```python
    work = paths.resolve_work(args.workdir)
    name = paths.deck_name(work)
    …
    out = paths.deck_dir(work) / f"{name}.pptx"
```

`variants.py`: `from . import paths` を足し、`_page` の `json.dumps(work.name …)` と `finalize` の `_html.escape(work.name)` を `paths.deck_name(work)` に直す。`_page` の第 1 引数 `work` は `Path` なので、テスト（Task 6）の `Path("deck")` は `deck_name` が `deck`（`source` ではないので旧形式扱いで `deck`）を返す。

- [ ] **Step 6: テストを通す・コミット**

Run: `$PY`（全テスト）  → Expected: すべて PASS（Task 4 の `test_init_makes_solid_background_only` は `source/` を見つけて通る）

```bash
git add tests/test_workdir.py skills/pptx-deck/pptx_deck
git commit -m "feat: 作業フォルダを <名前>/source/ にし、旧形式も読めるようにする"
```

---

### Task 8: 指紋・整理・上書きの確認（項目 6、受入条件 7・8）

**Files:**
- Create: `skills/pptx-deck/pptx_deck/lifecycle.py`
- Modify: `skills/pptx-deck/pptx_deck/cli.py`（`cmd_build` を全面的に置き換え、`clean` を追加）
- Test: `tests/test_lifecycle.py`

**Interfaces:**
- Produces（`pptx_deck.lifecycle`）:
  - `DERIVED_FILES: tuple[str, ...]` — `("variants.html", "final-review.html", "plan-review.html", "final.html", "theme.css", "base.css", "chart-preview.js")`
  - `sha256_of(path: Path) -> str`
  - `record_build(work: Path, pptx: Path) -> None` — `work/build.json` に `{"pptx", "sha256", "built_at"}`
  - `fingerprint_status(work: Path, pptx: Path) -> str` — `"missing"`（PPTX なし）・`"unrecorded"`（記録なし）・`"unchanged"`・`"modified"`
  - `prune(work: Path) -> list[str]` — 既知の派生ファイルだけを消し、消した相対パスを返す
  - `clean_temp(name: str) -> bool` — `%TEMP%\pptx-deck\<name>` を消す
- `build` の出力 JSON に `removed: list[str]` を足す。終了コード 4 は「PPTX が前回のビルド後に変更されている」。

- [ ] **Step 1: 失敗するテストを書く（`tests/test_lifecycle.py`）**

```python
import json
import tempfile
import unittest
from pathlib import Path

from tests import _paths  # noqa: F401
from pptx_deck import lifecycle


class FingerprintTest(unittest.TestCase):
    def test_status_transitions(self):
        with tempfile.TemporaryDirectory() as td:
            work = Path(td) / "source"
            work.mkdir()
            pptx = Path(td) / "deck.pptx"
            self.assertEqual(lifecycle.fingerprint_status(work, pptx), "missing")
            pptx.write_bytes(b"v1")
            self.assertEqual(lifecycle.fingerprint_status(work, pptx), "unrecorded")
            lifecycle.record_build(work, pptx)
            self.assertEqual(lifecycle.fingerprint_status(work, pptx), "unchanged")
            pptx.write_bytes(b"v1-edited")
            self.assertEqual(lifecycle.fingerprint_status(work, pptx), "modified")
            self.assertEqual(json.loads((work / "build.json").read_text(encoding="utf-8"))["pptx"], "deck.pptx")


class PruneTest(unittest.TestCase):
    def test_removes_only_known_derived(self):
        with tempfile.TemporaryDirectory() as td:
            w = Path(td)
            for n in lifecycle.DERIVED_FILES:
                (w / n).write_text("x", encoding="utf-8")
            (w / "icons").mkdir()
            (w / "icons" / "a.svg").write_text("x", encoding="utf-8")
            (w / "_template").mkdir()
            (w / "_template" / "template.potx").write_bytes(b"t")
            (w / "_template" / "bg-body.png").write_bytes(b"p")
            for keep in ("design.md", "script.md", "template.json", "build.json", "answers-1.md", "round-2-notes.md", "素材メモ.md"):
                (w / keep).write_text("k", encoding="utf-8")
            (w / "slides").mkdir()
            (w / "slides" / "01-A.html").write_text("s", encoding="utf-8")
            removed = lifecycle.prune(w)
            self.assertIn("final.html", removed)
            self.assertIn("icons", removed)
            self.assertIn("_template/bg-body.png", removed)
            left = sorted(p.name for p in w.iterdir())
            self.assertEqual(left, sorted(["_template", "answers-1.md", "build.json", "design.md", "round-2-notes.md", "script.md", "slides", "template.json", "素材メモ.md"]))
            self.assertEqual([p.name for p in (w / "_template").iterdir()], ["template.potx"])

    def test_prune_empty_dir_is_safe(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(lifecycle.prune(Path(td)), [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 失敗を確認する**

Run: `$PY -k lifecycle`  → Expected: FAIL（`lifecycle` が無い）

- [ ] **Step 3: `lifecycle.py` を作る**

```python
"""PPTX の指紋（build.json）、派生ファイルの整理、一時ファイルの削除。削除は既知の派生ファイルに限る。"""
import datetime
import hashlib
import json
import shutil
from pathlib import Path

from . import paths

DERIVED_FILES = ("variants.html", "final-review.html", "plan-review.html", "final.html",
                 "theme.css", "base.css", "chart-preview.js")
DERIVED_DIRS = ("icons",)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def record_build(work: Path, pptx: Path) -> None:
    data = {"pptx": Path(pptx).name, "sha256": sha256_of(pptx),
            "built_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds")}
    (Path(work) / "build.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def fingerprint_status(work: Path, pptx: Path) -> str:
    if not Path(pptx).exists():
        return "missing"
    rec = Path(work) / "build.json"
    if not rec.exists():
        return "unrecorded"
    try:
        saved = json.loads(rec.read_text(encoding="utf-8")).get("sha256")
    except (OSError, ValueError):
        return "unrecorded"
    return "unchanged" if saved == sha256_of(pptx) else "modified"


def prune(work: Path) -> list[str]:
    """再生成できる派生ファイルだけを消す。source/ の元データと、未知のファイルは消さない。消した相対パスを返す。"""
    work = Path(work)
    removed: list[str] = []
    for name in DERIVED_FILES:
        p = work / name
        if p.is_file():
            p.unlink()
            removed.append(name)
    for name in DERIVED_DIRS:
        p = work / name
        if p.is_dir():
            shutil.rmtree(p)
            removed.append(name)
    tdir = work / "_template"
    if tdir.is_dir():
        for p in sorted(tdir.glob("bg-*.png")):
            p.unlink()
            removed.append(f"_template/{p.name}")
    return removed


def clean_temp(name: str) -> bool:
    d = paths.temp_dir(name)           # 作ってから消す（存在しなくても安全）
    shutil.rmtree(d, ignore_errors=True)
    return True
```

- [ ] **Step 4: `cmd_build` を全面的に置き換え、`clean` を足す（`cli.py`）**

```python
def cmd_build(args) -> int:
    from . import build, check, lifecycle, measure, preview
    work = paths.resolve_work(args.workdir)
    name = paths.deck_name(work)
    cfg, info, palette = _load_cfg(work)
    html = work / "final.html"
    if not html.exists():
        print("エラー: final.html がありません（先に finalize を実行してください）", file=sys.stderr)
        return 2
    default_out = paths.deck_dir(work) / f"{name}.pptx"
    out = Path(args.out).resolve() if args.out else default_out
    if out == default_out and not args.force:
        st = lifecycle.fingerprint_status(work, out)
        if st == "modified":
            print(f"エラー: {out.name} は前回のビルドのあとに変更されています。作り直すと PowerPoint での手直しが消えます。"
                  "上書きしてよければ --force、別の名前で出すなら --out <パス> を付けてください。", file=sys.stderr)
            return 4
    model = measure.measure(html)
    violations = check.check_model(model, info)
    result = {"ok": False, "violations": violations, "pptx": None, "previews": [], "removed": [], "notes": list(info.notes)}
    if check.errors(violations):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1
    footer = args.footer if args.footer is not None else cfg.get("footer")
    build.build(model, work / cfg["template"], info, palette, out, base_dir=work, footer=footer, work_name=name)
    violations += check.check_pptx(out)
    result["violations"] = violations
    result["pptx"] = str(out)
    try:
        result["previews"] = [str(p) for p in preview.screenshots(html, paths.temp_dir(name) / "preview")]
    except Exception as e:        # PPTX は出ている。確認用の画像だけ作れなかったことを知らせる
        result["notes"].append(f"確認用の画像を作れませんでした: {e}")
    result["ok"] = not check.errors(violations)
    if result["ok"]:
        if out == default_out:
            lifecycle.record_build(work, out)
        result["removed"] = lifecycle.prune(work)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


def cmd_clean(args) -> int:
    from . import lifecycle
    work = paths.resolve_work(args.workdir)
    name = paths.deck_name(work)
    target = str(paths.temp_dir(name))          # 先にパスを求める（temp_dir は作って返す）
    lifecycle.clean_temp(name)
    print(json.dumps({"cleaned": target}, ensure_ascii=False))
    return 0
```

`main` のパーサに追加する。

```python
    p = sub.add_parser("build")
    p.add_argument("workdir")
    p.add_argument("--footer", default=None)
    p.add_argument("--out", default=None, help="PPTX の出力先（省略すると <名前>/<名前>.pptx）")
    p.add_argument("--force", action="store_true", help="前回のビルド後に変更された PPTX も上書きする")
    p.set_defaults(fn=cmd_build)
    p = sub.add_parser("clean")
    p.add_argument("workdir")
    p.set_defaults(fn=cmd_clean)
```


**実装判断（SPEC の項目 6 からの差分）:** SPEC は `%TEMP%\pptx-deck\<名前>\` を `build` 成功時に削除するとしているが、確認用の画像（`previews`）は `build` の直後に見るものなので、`build` では消さず、見終わった後に `clean` で消す。`SKILL.md` の手順に入れる（Task 13）。

- [ ] **Step 5: テストを通す・コミット**

Run: `$PY -k lifecycle`  → Expected: PASS
Run: `$PY`  → Expected: すべて PASS

```bash
git add tests/test_lifecycle.py skills/pptx-deck/pptx_deck/lifecycle.py skills/pptx-deck/pptx_deck/cli.py
git commit -m "feat: PPTX の指紋・派生ファイルの整理・上書きの確認と clean コマンドを追加"
```

---

### Task 9: `reopen`（派生ファイルの再生成と指紋の確認）

**Files:**
- Modify: `skills/pptx-deck/pptx_deck/lifecycle.py`（`reopen` を追加）
- Modify: `skills/pptx-deck/pptx_deck/cli.py`（`cmd_reopen`）
- Test: `tests/test_reopen.py`

**Interfaces:**
- Consumes: `initdir.write_derived`（Task 4）、`lifecycle.fingerprint_status`（Task 8）、`variants.answer_paths`・`variants.next_round`（Task 5）、`paths.resolve_work`・`paths.is_legacy`（Task 7）
- Produces: `lifecycle.reopen(work: Path) -> dict` — `{"status": "ok"|"modified"|"unrecorded"|"missing_pptx", "legacy": bool, "source": str, "pptx": str, "answers": [str], "next_round": int, "slides": int, "notes": [str]}`。`pptx_deck reopen <名前> [--force]` は `modified` のとき終了コード 4（`--force` なら 0）。

- [ ] **Step 1: 失敗するテストを書く（`tests/test_reopen.py`）**

```python
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tests import _paths  # noqa: F401
from pptx_deck import initdir, lifecycle, paths


def fresh(td) -> Path:
    base = Path(td) / "deck"
    initdir.init(base, color="navy")
    work = paths.resolve_work(base)
    (work / "slides" / "01-A.html").write_text("<section class='slide'></section>", encoding="utf-8")
    (work / "answers-1.md").write_text("---\n---\n", encoding="utf-8")
    (work / "answers-final.md").write_text("---\n---\n", encoding="utf-8")
    lifecycle.prune(work)               # build 後の状態にする
    return work


class ReopenTest(unittest.TestCase):
    def test_regenerates_derived_files(self):
        with tempfile.TemporaryDirectory() as td:
            work = fresh(td)
            self.assertFalse((work / "theme.css").exists())
            pptx = paths.deck_dir(work) / "deck.pptx"
            pptx.write_bytes(b"v1")
            lifecycle.record_build(work, pptx)
            r = lifecycle.reopen(work)
            self.assertEqual(r["status"], "ok")
            self.assertTrue((work / "theme.css").exists() and (work / "base.css").exists() and (work / "icons").is_dir())
            self.assertEqual([Path(a).name for a in r["answers"]], ["answers-1.md", "answers-final.md"])
            self.assertEqual(r["next_round"], 2)
            self.assertEqual(r["slides"], 1)

    def test_modified_pptx_is_reported(self):
        with tempfile.TemporaryDirectory() as td:
            work = fresh(td)
            pptx = paths.deck_dir(work) / "deck.pptx"
            pptx.write_bytes(b"v1")
            lifecycle.record_build(work, pptx)
            pptx.write_bytes(b"v1 + 手直し")
            self.assertEqual(lifecycle.reopen(work)["status"], "modified")

    def test_missing_pptx(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(lifecycle.reopen(fresh(td))["status"], "missing_pptx")

    def test_legacy_folder(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "old"
            initdir.init(base, color="navy")
            legacy = Path(td) / "legacy"
            shutil.copytree(base / "source", legacy)           # source/ の中身を直下に置いた旧形式
            r = lifecycle.reopen(paths.resolve_work(legacy))
            self.assertTrue(r["legacy"])
            self.assertTrue(any("旧形式" in n for n in r["notes"]))


if __name__ == "__main__":
    unittest.main()
```


- [ ] **Step 2: 失敗を確認する**

Run: `$PY -k reopen`  → Expected: FAIL（`lifecycle.reopen` が未定義）

- [ ] **Step 3: `lifecycle.reopen` を書く**

```python
def reopen(work: Path) -> dict:
    """完成した作品を再修正するための準備。派生ファイルを template.json から再生成し、PPTX の指紋を確かめる。"""
    from . import initdir, variants

    work = Path(work)
    cfg = json.loads((work / "template.json").read_text(encoding="utf-8"))
    notes = list(initdir.write_derived(work, cfg))
    legacy = paths.is_legacy(work)
    if legacy:
        notes.append("旧形式の作業フォルダです（source/ がありません）。このまま扱えますが、新しい作品は source/ に作ります。")
    pptx = paths.deck_dir(work) / f"{paths.deck_name(work)}.pptx"
    st = fingerprint_status(work, pptx)
    status = {"unchanged": "ok", "modified": "modified", "missing": "missing_pptx", "unrecorded": "unrecorded"}[st]
    if status == "modified":
        notes.append("PPTX は前回のビルドのあとに変更されています。作り直すと PowerPoint での手直しが消えます。")
    slides = len({m.group(1) for f in (work / "slides").glob("*.html") if (m := variants.FRAG.match(f.name))}) if (work / "slides").is_dir() else 0
    return {"status": status, "legacy": legacy, "source": str(work), "pptx": str(pptx),
            "answers": [str(p) for p in variants.answer_paths(work)], "next_round": variants.next_round(work),
            "slides": slides, "notes": notes}
```

- [ ] **Step 4: `cli.py` に `reopen` を足す**

```python
def cmd_reopen(args) -> int:
    from . import lifecycle
    work = paths.resolve_work(args.workdir)
    if not (work / "template.json").exists():
        print(f"エラー: {work} に template.json がありません（作品の source/ が見つかりません）", file=sys.stderr)
        return 2
    r = lifecycle.reopen(work)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 4 if r["status"] == "modified" and not args.force else 0
```

```python
    p = sub.add_parser("reopen")
    p.add_argument("workdir")
    p.add_argument("--force", action="store_true", help="PPTX が変更されていても続ける（手直しは消える）")
    p.set_defaults(fn=cmd_reopen)
```

- [ ] **Step 5: テストを通す・コミット**

Run: `$PY -k reopen`  → Expected: PASS
Run: `$PY`  → Expected: すべて PASS

```bash
git add tests/test_reopen.py skills/pptx-deck/pptx_deck
git commit -m "feat: reopen で派生ファイルを再生成し、PPTX の変更を検知する"
```

---

### Task 10: 設計図と原稿のレビューページ（項目 7）

**Files:**
- Create: `skills/pptx-deck/pptx_deck/plan_review.py`
- Modify: `skills/pptx-deck/pptx_deck/variants.py`（`_page` に `docs` を足し、`_STYLE`・`_SCRIPT` を小さく直す）
- Modify: `skills/pptx-deck/pptx_deck/cli.py`（`review-plan`）
- Test: `tests/test_plan_review.py`

**Interfaces:**
- Produces（`pptx_deck.plan_review`）:
  - `parse_design(md: str) -> tuple[str, dict[str, str]]` — `(資料全体の Markdown, {"04": "…ページの Markdown"})`。資料全体は `## ページごと` より前の本文
  - `build_docs(design_md: str, script_md: str) -> tuple[dict[str, str], dict[str, str]]` — `({"00": 資料全体の HTML, "01": …}, {"00": "資料全体", "01": "表紙", …})`（HTML とナビ用の題）
  - `assemble(work: Path, round_no: int | None = None) -> Path` — `plan-review.html` を作る。回答は `answers-plan-N.md`
- `variants._page(…, docs: dict[str, str] | None = None, titles: dict[str, str] | None = None)` — `docs` があるとき、各ペインの大きな画面を、サムネではなく読める文書の枠（`.doc`）にする。ペインに `data-doc="1"` を付ける。

- [ ] **Step 1: 失敗するテストを書く（`tests/test_plan_review.py`）**

```python
import tempfile
import unittest
from pathlib import Path

from tests import _paths  # noqa: F401
from tests._paths import PKG
from pptx_deck import plan_review

DESIGN = (PKG / "assets" / "sample" / "design.md").read_text(encoding="utf-8")
SCRIPT = (PKG / "assets" / "sample" / "script.md").read_text(encoding="utf-8")


class ParseTest(unittest.TestCase):
    def test_parse_design(self):
        overview, pages = plan_review.parse_design(DESIGN)
        self.assertIn("ガバニングメッセージ", overview)
        self.assertIn("台帳", overview)
        self.assertEqual(sorted(pages), ["04"])
        self.assertIn("レイアウト記述", pages["04"])

    def test_build_docs_covers_every_script_slide_plus_overview(self):
        docs, titles = plan_review.build_docs(DESIGN, SCRIPT)
        self.assertEqual(sorted(docs)[0], "00")
        self.assertEqual(len(docs), 11 + 1)                       # 見本の原稿は 11 枚 + 資料全体
        self.assertEqual(titles["00"], "資料全体")
        self.assertIn("削減で生む原資が成長投資を支えるため", docs["02"])      # 見出し（リード文）が出る
        self.assertIn("レイアウト記述", docs["04"])                  # 設計図のページ記述が合流する


class AssembleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls._pw = sync_playwright().start()
        cls.browser = cls._pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls._pw.stop()

    def test_page_works_like_review_pages(self):
        with tempfile.TemporaryDirectory() as td:
            work = Path(td) / "deck" / "source"
            work.mkdir(parents=True)
            (work / "design.md").write_text(DESIGN, encoding="utf-8")
            (work / "script.md").write_text(SCRIPT, encoding="utf-8")
            (work / "answers-plan-1.md").write_text("---\n---\n## S02\n- 選択: A\n- 判定: 承認\n- コメント: \n", encoding="utf-8")
            out = plan_review.assemble(work, round_no=2)
            self.assertEqual(out.name, "plan-review.html")
            page = self.browser.new_page(viewport={"width": 1400, "height": 900})
            page.goto(out.as_uri())
            page.wait_for_timeout(200)
            self.assertEqual(page.evaluate("document.querySelectorAll('.pane').length"), 12)
            self.assertEqual(page.evaluate("document.querySelector('.pane[data-slide=\"02\"] input[value=A]').checked"), True)   # 前回承認
            page.click(".pane[data-slide=\"00\"] .verdict .ok")                                                              # 承認で次へ
            self.assertEqual(page.evaluate("document.querySelector('#nav button[aria-current=true]').dataset.go"), "01")
            page.click(".pane[data-slide=\"01\"] .copyBtn")
            md = page.evaluate("window.__answersMd")
            self.assertIn("round: plan-2", md)
            self.assertIn("## S00", md)
            self.assertIn("## S02", md)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 失敗を確認する**

Run: `$PY -k plan_review`  → Expected: FAIL（`plan_review` が無い）

- [ ] **Step 3: `plan_review.py` を作る**

```python
"""設計図（design.md）と原稿（script.md）を、レビューページ用の HTML にする。スライド案のページと同じ操作で承認／要修正を返す。"""
import html as _html
import re
from pathlib import Path

from . import script_lint, variants

_PAGE_HEAD = re.compile(r"^### S(\d{2})\b.*$", re.M)


def parse_design(md: str) -> tuple[str, dict[str, str]]:
    """資料全体（『## ページごと』より前）と、ページごとの Markdown（### SNN …）に分ける。"""
    head, _, tail = md.partition("\n## ページごと")
    overview = re.sub(r"^# .*\n", "", head, count=1).strip()
    pages: dict[str, str] = {}
    ms = list(_PAGE_HEAD.finditer(tail))
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(tail)
        pages[m.group(1)] = tail[m.start():end].strip()
    return overview, pages


def _md_html(text: str) -> str:
    """設計図・原稿の簡易表示（見出し・箇条書き・表・段落）。HTML は必ずエスケープする。"""
    out, in_list, rows = [], False, []

    def flush():
        nonlocal in_list, rows
        if in_list:
            out.append("</ul>")
            in_list = False
        if rows:
            body = [r for r in rows if not re.fullmatch(r"\|[\s\-:|]+\|", r)]
            cells = [[_html.escape(c.strip()) for c in r.strip("|").split("|")] for r in body]
            out.append("<table>" + "".join(
                "<tr>" + "".join(f"<{'th' if i == 0 else 'td'}>{c}</{'th' if i == 0 else 'td'}>" for c in row) + "</tr>"
                for i, row in enumerate(cells)) + "</table>")
            rows = []

    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("|"):
            if in_list:
                flush()
            rows.append(line)
            continue
        if rows:
            flush()
        m = re.match(r"^(\s*)[-*] (.*)$", line)
        if m:
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li style=\"margin-left:{len(m.group(1)) * 6}px\">{_html.escape(m.group(2))}</li>")
            continue
        flush()
        h = re.match(r"^(#{1,4}) (.*)$", line)
        if h:
            out.append(f"<h4>{_html.escape(h.group(2))}</h4>")
        elif line.strip() and not line.startswith("<!--"):
            out.append(f"<p>{_html.escape(line)}</p>")
    flush()
    return "".join(out)


def build_docs(design_md: str, script_md: str) -> tuple[dict[str, str], dict[str, str]]:
    overview, pages = parse_design(design_md)
    docs = {"00": '<h3>資料全体</h3>' + _md_html(overview)}
    titles = {"00": "資料全体"}
    head = script_md.split("\n## S", 1)[0]
    docs["00"] += '<h3>原稿の冒頭（目的・対象・論点）</h3>' + _md_html(head)
    for s in script_lint.parse(script_md):
        nn = s["id"][1:]
        f = s["fields"]
        titles[nn] = (f.get("題") if isinstance(f.get("題"), str) and f.get("題") else s["title"]) or s["id"]
        rows = "".join(
            f"<tr><th>{_html.escape(k)}</th><td>{_html.escape(v if isinstance(v, str) else ' / '.join(v))}</td></tr>"
            for k, v in f.items())
        body = f'<h3>S{nn}　{_html.escape(s["title"])}</h3><h4>原稿</h4><table>{rows}</table>'
        if nn in pages:
            body += "<h4>設計図</h4>" + _md_html(pages[nn])
        docs[nn] = body
    return docs, titles


def assemble(work: Path, round_no: int | None = None) -> Path:
    work = Path(work)
    docs, titles = build_docs((work / "design.md").read_text(encoding="utf-8"),
                              (work / "script.md").read_text(encoding="utf-8"))
    paths_ = variants.plan_answer_paths(work)
    n = round_no or (len(paths_) + 1)
    preset = variants.approved_preset([p.read_text(encoding="utf-8") for p in paths_])
    out = work / "plan-review.html"
    frags = {nn: {"A": ""} for nn in docs}
    out.write_text(variants._page(work, frags, f"plan-{n}", docs=docs, titles=titles, preset=preset), encoding="utf-8")
    return out
```

- [ ] **Step 4: `variants._page` を `docs` に対応させる**

(a) シグネチャに `docs: dict[str, str] | None = None, titles: dict[str, str] | None = None` を足す。
(b) `title`・`lead` を `docs` のとき切り替える。

```python
    if docs is not None:
        title = "設計図と原稿の確認"
        lead = ("承認する前に、資料全体と、スライドごとの設計と原稿を確認します。1 枚ずつ見て「承認」か「要修正」を選び、"
                "直したい点があればコメントに書いて、最後に判断欄の右端の「回答をコピー」を押してください。")
```

(c) ナビとペインの組み立てで、`t = _title_of(…)` を `t = (titles or {}).get(nn) or _title_of(opts[letters[0]])` にし、`single = final or len(letters) == 1 or docs is not None`、ペインの先頭を次にする。

```python
        doc_attr = ' data-doc="1"' if docs is not None else ""
        p = [f'<section class="pane" data-slide="{nn}" data-single="{1 if single else 0}"{doc_attr} hidden>',
             f'<div class="top"><h2>{"S" + nn if nn != "00" else ""}　{esc(t)}</h2></div>',
             (f'<div class="doc">{docs[nn]}</div>' if docs is not None
              else '<div class="big"><div class="thumb"><div class="stage"></div></div></div>'),
             '<div class="cols"' + (' hidden' if docs is not None else '') + '>']
```

(d) `docs` のとき `opts` の中身（サムネ）が空文字の断片でも壊れないよう、`<div class="opt" …>` 内の `.thumb` はそのまま出す（JS が `$('.thumb', o)` を要求するため）。`single` なので `.opts.single` で非表示になる。ラジオは「採用」「要修正」（A / FIX）で、既存の単一案の分岐が使われる。

(e) `_STYLE` の末尾（`</style>` の前）に足す。

```css
.rv .doc{background:#fff;color:#1a1a1a;padding:18px 22px;border:1px solid var(--line);font-size:14px;line-height:1.7;max-height:68vh;overflow:auto}
.rv .doc h3{font-size:17px;margin:4px 0 8px}.rv .doc h4{font-size:14px;margin:14px 0 4px;color:#33496B}
.rv .doc p{margin:2px 0}.rv .doc ul{margin:2px 0 2px 18px;list-style:disc}.rv .doc li{margin:1px 0}
.rv .doc table{border-collapse:collapse;margin:6px 0;width:100%}.rv .doc th,.rv .doc td{border:1px solid #c9d2e0;padding:4px 8px;text-align:left;vertical-align:top}.rv .doc th{background:#eef2f8;white-space:nowrap}
```

(f) `_SCRIPT` の `showBig` の先頭に足す（文書のペインは、大きな画面の描画をしない）。

```js
    if (p.dataset.doc === '1') { p.dataset.view = k; fit(); return; }
```

`viewKey(p)` は `$('.opt', p).dataset.k` を使うので、`frags = {nn: {"A": ""}}` の `A` が `data-k="A"` で出る。

- [ ] **Step 5: `cli.py` に `review-plan` を足す**

```python
def cmd_review_plan(args) -> int:
    from . import plan_review
    work = paths.resolve_work(args.workdir)
    for need in ("design.md", "script.md"):
        if not (work / need).exists():
            print(f"エラー: {work / need} がありません", file=sys.stderr)
            return 2
    print(plan_review.assemble(work, round_no=args.round))
    return 0
```

```python
    p = sub.add_parser("review-plan")
    p.add_argument("workdir")
    p.add_argument("--round", type=int, default=None)
    p.set_defaults(fn=cmd_review_plan)
```

- [ ] **Step 6: テストを通す・コミット**

Run: `$PY -k plan_review`  → Expected: PASS（3 テスト）。`test_build_docs…` の `len(docs) == 12` が合わないときは、見本の `script.md` の `## S01`〜`## S11` の数を `grep -c '^## S' skills/pptx-deck/assets/sample/script.md` で確かめて、期待値を実際の枚数 + 1 に直す。
Run: `$PY`  → Expected: すべて PASS

```bash
git add tests/test_plan_review.py skills/pptx-deck/pptx_deck
git commit -m "feat: 設計図と原稿を HTML で確認する review-plan を追加"
```

---

### Task 11: 通しの検証（受入条件 13）

**Files:**
- Create: `tests/test_e2e_sample.py`
- Modify: `docs/verification.md`（新規。手順書。実行方法とチェック項目）

**Interfaces:**
- Consumes: Task 2〜10 のすべて。`pptx_deck.cli.main(argv)`（`argv` の先頭は サブコマンド）

- [ ] **Step 1: テストを書く（`tests/test_e2e_sample.py`）**

```python
"""init → variants → finalize → build → reopen を、LibreOffice を呼ばずに通す。部品の見本（assets/components）を案に使う。"""
import contextlib
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests import _paths  # noqa: F401
from tests._paths import PKG
from pptx_deck import cli, lifecycle, paths

COMP = PKG / "assets" / "components"


def run(*argv):
    buf, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
        rc = cli.main(list(argv))
    return rc, buf.getvalue(), err.getvalue()


class E2ETest(unittest.TestCase):
    def test_full_flow_without_libreoffice(self):
        calls = []
        real_run, real_popen = subprocess.run, subprocess.Popen

        def spy_run(cmd, *a, **k):
            calls.append(str(cmd[0] if isinstance(cmd, (list, tuple)) else cmd))
            return real_run(cmd, *a, **k)

        def spy_popen(cmd, *a, **k):
            calls.append(str(cmd[0] if isinstance(cmd, (list, tuple)) else cmd))
            return real_popen(cmd, *a, **k)

        with tempfile.TemporaryDirectory() as td, mock.patch("subprocess.run", spy_run), mock.patch("subprocess.Popen", spy_popen):
            base = Path(td) / "demo"
            self.assertEqual(run("init", str(base), "--color", "navy")[0], 0)
            work = paths.resolve_work(base)
            slides = work / "slides"
            shutil.copyfile(COMP / "layouts" / "cover.html", slides / "01-A.html")
            shutil.copyfile(COMP / "diagrams" / "flow-h.html", slides / "02-A.html")
            shutil.copyfile(COMP / "diagrams" / "flow-v.html", slides / "02-B.html")
            shutil.copyfile(COMP / "charts" / "bar.html", slides / "03-A.html")

            self.assertEqual(run("variants", str(base))[0], 0)
            self.assertTrue((work / "variants.html").exists())
            (work / "answers-1.md").write_text(
                "---\ndeck: demo\nround: 1\n---\n## S01\n- 選択: A\n- 判定: 承認\n- コメント: \n"
                "## S02\n- 選択: B\n- 判定: 承認\n- コメント: \n## S03\n- 選択: A\n- 判定: 承認\n- コメント: \n", encoding="utf-8")
            self.assertEqual(run("finalize", str(base))[0], 0)                      # --answers を省略 → answers-*.md を自動で使う
            rc, out, _ = run("build", str(base))
            self.assertEqual(rc, 0, out)
            result = json.loads(out)
            pptx = base / "demo.pptx"
            self.assertTrue(pptx.exists())
            self.assertIn("final.html", result["removed"])
            self.assertEqual(sorted(p.name for p in base.iterdir()), ["demo.pptx", "source"])
            self.assertFalse((work / "theme.css").exists())
            self.assertTrue((work / "build.json").exists())
            self.assertTrue(result["previews"])

            rc, out, _ = run("reopen", str(base))
            self.assertEqual((rc, json.loads(out)["status"]), (0, "ok"))
            self.assertTrue((work / "theme.css").exists())
            self.assertEqual(run("variants", str(base))[0], 0)                      # 2 回目: 前回承認が選択済みで開く
            html = (work / "variants.html").read_text(encoding="utf-8")
            self.assertIn('"01": {"c": "A"', html)

            lifecycle.prune(work)
            pptx.write_bytes(pptx.read_bytes() + b"x")                              # PowerPoint で手直しした想定
            self.assertEqual(run("reopen", str(base))[0], 4)
            self.assertEqual(run("reopen", str(base), "--force")[0], 0)
            self.assertEqual(run("finalize", str(base))[0], 0)
            rc, _, err = run("build", str(base))
            self.assertEqual(rc, 4, err)                                            # 手直し済みの PPTX を黙って上書きしない
            self.assertEqual(run("build", str(base), "--force")[0], 0)
            self.assertEqual(run("clean", str(base))[0], 0)

        self.assertFalse([c for c in calls if "soffice" in c.lower() or "libreoffice" in c.lower()], calls)


if __name__ == "__main__":
    unittest.main()
```


- [ ] **Step 2: 実行して、失敗した箇所を直す**

Run: `$PY -k e2e`
Expected: PASS。失敗しうる箇所と対処:
- 部品の見本が `check` の違反を出して `build` が `ok: false` になる場合: `python skills/pptx-deck/run.py check <work>/final.html` で `rule` を確認し、見本の断片を 1 つ別の型（`assets/components/` の別の 1 本）に差し替える。見本が違反を出すなら、それは別の不具合なので、テストの案を差し替えるのみにして、見本は直さない（範囲外）。
- `'"01": {"c": "A"'` が HTML に見つからない場合: `json.dumps` の区切りが `, ` か `,` か、キーの順（`c`・`d`・`v`）を `variants.html` の中身で確かめて、期待文字列を実際の出力に合わせる。

- [ ] **Step 3: 手順書 `docs/verification.md` を書く**

内容: (1) 実行コマンド `"$LOCALAPPDATA/pptx-deck/venv/Scripts/python.exe" -m unittest discover -s tests -t . -v`、(2) 何を確かめるか（SPEC の受入条件 1〜13 の対応表: 1・2 → `test_review_page`、3 → SKILL.md の文面、4・5 → `test_no_libreoffice`・`test_template_bg`、6〜8 → `test_e2e_sample`・`test_reopen`・`test_lifecycle`、9 → `test_plan_review`、10 → `grep -ri libreoffice`、11 → Task 14、12 → `test_env_select`、13 → このファイル）、(3) 人が見る項目（PowerPoint で開いて崩れの確認、Playwright MCP でのレビューページの操作）。

- [ ] **Step 4: コミット**

```bash
git add tests/test_e2e_sample.py docs/verification.md
git commit -m "test: LibreOffice なしの通し検証（init から reopen まで）と手順書を追加"
```

---

### Task 12: `plugins/pptx-deck/` へ再配置（項目 8 の構成）

**Files:**
- Move: `skills/pptx-deck/{run.py,requirements.txt,pptx_deck,assets,references}` → `plugins/pptx-deck/`
- Move: `skills/pptx-deck/SKILL.md` → `plugins/pptx-deck/skills/create/SKILL.md`
- Move: `.claude-plugin/plugin.json` → `plugins/pptx-deck/.claude-plugin/plugin.json`
- Modify: `tests/_paths.py`（変更なし。`plugins/pptx-deck/pptx_deck` があれば自動でそちらを使う）

**注意（利用者への事前連絡）:** この移動で、`~/.claude/skills/pptx-deck`（リンク）の先がなくなり、`/pptx-deck` スキルがいまのセッションでは呼べなくなる。リンクは取り外さない（SPEC: 導入の確認後に了承を得て外す）。以降の確認は `claude --plugin-dir plugins/pptx-deck` で行う。移動の前に、利用者にこの点を伝えて了承を得る（AskUserQuestion）。

- [ ] **Step 1: 全テストが通ることを確認する（移動前の基準）**

Run: `$PY`  → Expected: すべて PASS

- [ ] **Step 2: 移動する**

```bash
mkdir -p plugins/pptx-deck/.claude-plugin plugins/pptx-deck/skills/create
git mv skills/pptx-deck/pptx_deck plugins/pptx-deck/pptx_deck
git mv skills/pptx-deck/assets plugins/pptx-deck/assets
git mv skills/pptx-deck/references plugins/pptx-deck/references
git mv skills/pptx-deck/run.py plugins/pptx-deck/run.py
git mv skills/pptx-deck/requirements.txt plugins/pptx-deck/requirements.txt
git mv skills/pptx-deck/SKILL.md plugins/pptx-deck/skills/create/SKILL.md
git mv .claude-plugin/plugin.json plugins/pptx-deck/.claude-plugin/plugin.json
```

`skills/` が空になれば削除する（`rmdir skills/pptx-deck skills`）。

- [ ] **Step 3: テストを通す**

Run: `$PY`  → Expected: すべて PASS（`tests/_paths.py` が `plugins/pptx-deck` を見つけて使う）。`paths.SKILL_DIR`（`pptx_deck` の親）は `plugins/pptx-deck` になり、`ASSETS` もそこを指す。

- [ ] **Step 4: コミット**

```bash
git add -A
git commit -m "refactor: リポジトリをプラグイン構成（plugins/pptx-deck）に再配置する"
```

---

### Task 13: スキルを 4 入口に分け、ドキュメントを更新する（項目 3・8）

**Files:**
- Modify: `plugins/pptx-deck/skills/create/SKILL.md`
- Create: `plugins/pptx-deck/skills/revise/SKILL.md`
- Create: `plugins/pptx-deck/skills/rebuild/SKILL.md`
- Create: `plugins/pptx-deck/skills/review-plan/SKILL.md`
- Modify: `plugins/pptx-deck/references/review-flow.md`・`check-rules.md`・`html-rules.md`（LibreOffice・`pngs` の記述）
- Modify: `README.md`
- Test: `tests/test_docs.py`

**Interfaces:**
- Consumes: Task 2〜10 のコマンド（`doctor`・`init`・`variants`・`finalize`・`review-final`・`review-plan`・`reopen`・`build`・`clean`）

- [ ] **Step 1: 失敗するテストを書く（`tests/test_docs.py`）**

```python
import re
import unittest

from tests import _paths  # noqa: F401
from tests._paths import PKG, REPO


class DocsTest(unittest.TestCase):
    def test_four_skills_with_frontmatter(self):
        for name in ("create", "revise", "rebuild", "review-plan"):
            text = (PKG / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
            m = re.match(r"^---\nname: (.+)\ndescription: (.+)\n(?:compatibility: .+\n)?---\n", text)
            self.assertIsNotNone(m, name)
            self.assertEqual(m.group(1).strip(), name)

    def test_no_hardcoded_skill_paths(self):
        for f in (PKG / "skills").rglob("SKILL.md"):
            t = f.read_text(encoding="utf-8")
            self.assertNotIn("C:/Users", t, f)
            self.assertNotIn("${CLAUDE_SKILL_DIR}", t, f)
            self.assertIn("${CLAUDE_PLUGIN_ROOT}", t, f)

    def test_no_libreoffice_as_dependency(self):
        for f in [REPO / "README.md", *PKG.rglob("*.md")]:
            for line in f.read_text(encoding="utf-8").splitlines():
                if re.search(r"LibreOffice|soffice", line):
                    self.assertRegex(line, r"使わ|使用しな|不要|なし|廃止", f"{f}: {line}")

    def test_wait_cap_documented(self):
        for f in (PKG / "skills" / "create" / "SKILL.md", PKG / "references" / "review-flow.md"):
            t = f.read_text(encoding="utf-8")
            self.assertIn("18 回", t, f)
            self.assertRegex(t, r"続行方法.*質問|質問.*続行方法", f)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 失敗を確認する**

Run: `$PY -k test_docs`  → Expected: FAIL

- [ ] **Step 3: `create/SKILL.md` を直す**

次の置き換えを行う（`plugins/pptx-deck/skills/create/SKILL.md`）。ほかの本文（2〜4 章の規則、型の選び方、HTML の書き方）は変えない。

1. frontmatter を次にする。

```
---
name: create
description: テーマ・素材・原稿から、コンサルテイストの承認資料（稟議・提案・計画）を新しく作る。設計図と原稿(Markdown)の承認 → HTML スライド案（各 3 案）の選択 → 最終 HTML の承認 → 編集可能な PowerPoint(.pptx) の順に進める。利用者の PPTX テンプレート（表紙・裏表紙・ヘッダー・フッター）に従える。「スライドを作って」「資料を作って」「PowerPoint を作って」「稟議資料」「提案資料」「デッキ」と頼まれたときに使う。作った PPTX の直しには revise、設計図と原稿の確認だけなら review-plan を使う。既存の PPTX の編集には使わない。Windows 専用。
compatibility: Windows 専用。Python 3.10 以上と Claude Code。システムの Python に python-pptx・Playwright・chromium がそろっていればそれを使い、なければ仮想環境を承認を得て作る。スライド案の選択に Playwright MCP が必要（ないときは回答を貼り付ける）。LibreOffice は使わない。
---
```

2. 冒頭の説明段落を次にする。

```
`${CLAUDE_PLUGIN_ROOT}` は、このプラグインのフォルダ（Claude Code が実パスに置き換える）。コマンドはすべて `python "${CLAUDE_PLUGIN_ROOT}/run.py" …`。`<名前>` は作品の名前（実行したディレクトリ直下の `<名前>/`）。作業ファイルは `<名前>/source/` に作り、PPTX は `<名前>/<名前>.pptx` に出る。
```

3. 本文中の `${CLAUDE_SKILL_DIR}` をすべて `${CLAUDE_PLUGIN_ROOT}` に置き換える（`grep -n CLAUDE_SKILL_DIR` が 0 件になるまで）。

4. 「0. 初回だけ（環境）」を次にする。

```
## 0. 初回だけ（環境）

1. `python "${CLAUDE_PLUGIN_ROOT}/run.py" doctor` を実行する。終了コード 3 のときは、システムの Python にも仮想環境にも必要なものがそろっていない。**利用者に「`%LOCALAPPDATA%\pptx-deck\venv` に Python の仮想環境と chromium（数百 MB）を導入してよいか」を確認する**。承認が出るまで作らない。システムの Python には何も入れない。
2. 承認後、`python "${CLAUDE_PLUGIN_ROOT}/run.py" setup --yes`。
3. `doctor` の `python.kind`（`system` か `venv`）と `warnings`（BIZ UDPゴシック未導入など）を利用者に伝える。
```

5. 「1. 流れ」の表の 原稿 の行の承認欄を `① 設計図と原稿を HTML で承認（review-plan。内容を凍結）` にし、本文の「⑴ 設計図と原稿を一緒にチャットで示して承認を求める」の箇所（2.3 の末尾）を次に置き換える。

```
空になり、5.1 のヘッド・論理の確認を済ませてから、`python "${CLAUDE_PLUGIN_ROOT}/run.py" review-plan "<名前>"` で `plan-review.html` を作り、Playwright MCP の `browser_navigate` で開いて、「資料全体とスライドごとの設計・原稿を見て、『承認』か『要修正』を選び、『回答をコピー』を押してください」と伝える。待ち方と回答の保存は 3 章の手順 4・5 と同じ（保存先は `<名前>/source/answers-plan-N.md`）。要修正があれば、コメントに沿って設計図と原稿を直し、`review-plan` を出し直す（前回承認したスライドは選択済みで開く）。承認後は、承認なしに内容を変えない。
```

6. 3 章の手順 4 の末尾（「ユーザーがターミナルに入力したときは…」の直前）に次を足す。

```
18 回（約 30 分）を超えても送信されないときは、待ちをやめて、続行方法（もう一度待つ／回答を貼り付けて渡す／中止）を利用者に質問して止まる。
```

7. 1.2 の作業フォルダの表を次に置き換える。

```
| 置き場所 | ファイル |
|---|---|
| プラグイン `${CLAUDE_PLUGIN_ROOT}`（読み取り専用） | `skills/`、`assets/`（`components/` の断片、`web/`、`icons/`、`template/`）、`references/`、コード |
| `<名前>/` | `<名前>.pptx`（成果物）と `source/` |
| `<名前>/source/` | `design.md`（`init` が雛形を置く）、`script.md`、`slides/NN-X.html`、`answers-*.md`、`template.json`、`_template/template.<拡張子>`、`build.json`。作業中だけ `variants.html`・`plan-review.html`・`final.html`・`final-review.html`・`theme.css`・`base.css`・`chart-preview.js`・`icons/` |
| OS の一時フォルダ `%TEMP%\pptx-deck\<名前>\` | 確認用の画像（`preview/`）、SVG の画像化 |
```

8. 5 章（PPTX の出力）の「`ok` が true なら…」の段落を次に置き換える。

```
`ok` が true なら、`previews`（確認用の画像。`final.html` を Chromium で撮ったもので、PPTX の実描画ではない）を開いて崩れを確認し、所見を伝える。**PowerPoint で開いて最終確認することを必ず勧める**。確認が済んだら `python "${CLAUDE_PLUGIN_ROOT}/run.py" clean "<名前>"` で一時の画像を消す。成果物は `<名前>/<名前>.pptx`。`build` は成功すると、再生成できる派生ファイルを `source/` から自動で消す（`removed` に一覧が出る）。元データ（`design.md`・`script.md`・`slides/`・`answers-*.md`・`template.json` など）は残るので、あとで `revise` で直せる。
```

9. 5 章の `build` の説明の終了コード 4 を足す: 「終了コード 4 は、PPTX が前回のビルド後に変更されている（手直しが消える）。利用者に確認し、`--force`（上書き）か `--out <パス>`（別名）を選んでもらう」。

- [ ] **Step 4: 3 つの新しい SKILL.md を書く**

`plugins/pptx-deck/skills/revise/SKILL.md`:

```markdown
---
name: revise
description: このプラグインで作った PPTX を、あとから直す。型・デザインを選び直す、または文言・数字だけを直して、PPTX を作り直す。「作った資料を直したい」「スライドの文言を変えたい」「デザインを選び直したい」と頼まれたときに使う。PowerPoint で手直しした内容は取り込まない（作り直すと消える）。Windows 専用。
compatibility: Windows 専用。create と同じ環境。作品の source/ フォルダが必要。
---

# pptx-deck revise

`${CLAUDE_PLUGIN_ROOT}` はこのプラグインのフォルダ。コマンドは `python "${CLAUDE_PLUGIN_ROOT}/run.py" …`。`<名前>` は作品の名前（`<名前>/<名前>.pptx` と `<名前>/source/` があるフォルダ）。

## 手順

1. `python "${CLAUDE_PLUGIN_ROOT}/run.py" reopen "<名前>"`。出力の `status` を見る。
   - `ok`: 続ける。
   - `modified`（終了コード 4）: PPTX が前回のビルドのあとに変更されている。作り直すと PowerPoint での手直しが消えると利用者に伝え、「上書きして続ける（`--force`）」か「別名で保存する（`build --out <パス>`）」かを選んでもらう。選ぶまで進めない。
   - `missing_pptx`・`unrecorded`: PPTX がない、または記録がない。そのまま続けてよいと伝える。
   - `legacy: true`: 旧形式のフォルダ。そのまま扱えると伝える。
2. 利用者に直し方を選んでもらう。
   - **(a) 型・デザインを選び直す**: `python "${CLAUDE_PLUGIN_ROOT}/run.py" variants "<名前>"` で `variants.html` を作り（前回承認したスライドは選択済み）、create の 3 章の手順 3〜6 と同じ手順で、選んでもらう。直したいスライドだけ、案を選び直して承認する。
   - **(b) 文言・数字だけ直す**: 直す内容を聞き、`source/slides/NN-X.html`（選ばれている案）と `source/script.md` の該当箇所を直す。数字を作らない（素材に無い数字は「xx」）。直したスライドは `source/round-N-notes.md` に「NN: 直した内容」と書く。
3. `python "${CLAUDE_PLUGIN_ROOT}/run.py" finalize "<名前>"`（回答は `source/answers-*.md` を回の順に自動で使う）。`final-review.html` を開いて、create の 3 章の手順 8 と同じ手順で承認を得る（保存先は `source/answers-final.md` を上書き）。
4. `python "${CLAUDE_PLUGIN_ROOT}/run.py" build "<名前>"`。`ok` が false なら `violations` を読んで `source/slides/` を直し、3 に戻る。
5. `previews` を開いて崩れを確認し、**PowerPoint で開いて最終確認することを勧める**。済んだら `clean "<名前>"`。

## 守ること

- 利用者が直すと言った内容以外は変えない。
- 回答を待つときは create の手順 4 に従う。18 回（約 30 分）を超えたら続行方法を質問して止まる。
- 仮想環境は、承認なしに作らない。
```

`plugins/pptx-deck/skills/rebuild/SKILL.md`:

```markdown
---
name: rebuild
description: このプラグインで作った作品の PPTX を、元データ（source/）を変えずに作り直す。スキルや環境を更新したあとに作り直したいとき、PPTX を失くしたときに使う。内容を直すときは revise を使う。Windows 専用。
compatibility: Windows 専用。create と同じ環境。作品の source/ フォルダが必要。
---

# pptx-deck rebuild

`${CLAUDE_PLUGIN_ROOT}` はこのプラグインのフォルダ。コマンドは `python "${CLAUDE_PLUGIN_ROOT}/run.py" …`。`<名前>` は作品の名前。

承認は要らない（内容を変えないため）。

## 手順

1. `python "${CLAUDE_PLUGIN_ROOT}/run.py" reopen "<名前>"`。`status` が `modified`（終了コード 4）のときは、作り直すと PowerPoint での手直しが消えると伝え、「上書き（`--force`）」か「別名（`build --out <パス>`）」かを選んでもらう。
2. `python "${CLAUDE_PLUGIN_ROOT}/run.py" finalize "<名前>"`（`source/answers-*.md` から `final.html` を作る）。「案が決まっていません」などのエラーが出たら、回答が足りない。止まって利用者に伝え、revise を勧める。
3. `python "${CLAUDE_PLUGIN_ROOT}/run.py" build "<名前>"`（上書きを選んだときは `--force`、別名のときは `--out <パス>`）。`ok` が false なら `violations` を伝えて止まる（直すのは revise）。
4. `previews` を開いて崩れを確認し、PowerPoint で開いて最終確認することを勧める。済んだら `clean "<名前>"`。

## 守ること

- 内容（文言・数字・案の選択）を変えない。
- 仮想環境は、承認なしに作らない。
```

`plugins/pptx-deck/skills/review-plan/SKILL.md`:

```markdown
---
name: review-plan
description: 設計図（design.md）と原稿（script.md）を HTML のレビューページで確認し、承認／要修正とコメントを受け取る。create の承認①として呼ばれるほか、「設計図と原稿を確認したい」と頼まれたときに単独でも使う。Windows 専用。
compatibility: Windows 専用。create と同じ環境。Playwright MCP が必要（ないときは回答を貼り付ける）。
---

# pptx-deck review-plan

`${CLAUDE_PLUGIN_ROOT}` はこのプラグインのフォルダ。コマンドは `python "${CLAUDE_PLUGIN_ROOT}/run.py" …`。`<名前>` は作品の名前。

## 手順

1. `python "${CLAUDE_PLUGIN_ROOT}/run.py" lint-script "<名前>/source/script.md"` が空であることを確かめる。
2. `python "${CLAUDE_PLUGIN_ROOT}/run.py" review-plan "<名前>"` → `<名前>/source/plan-review.html`。Playwright MCP の `browser_navigate` で `file:///C:/…/plan-review.html` を開き、「資料全体とスライドごとの設計・原稿を見て、『承認』か『要修正』を選び、『回答をコピー』を押してください。直したい点はコメントに書いてください」と伝える。`browser_resize` で窓の大きさを変えない。
3. 回答を待つ。`browser_evaluate` で次を実行し、送信されるか約 100 秒たつまでブロックして結果を返す。`submitted` が false なら同じ呼び出しを繰り返す（合計約 30 分、18 回まで）。18 回を超えても送信されないときは、続行方法（もう一度待つ／回答を貼り付けて渡す／中止）を利用者に質問して止まる。ユーザーがターミナルに入力したときは待ちをやめて、その内容に従う。

   `() => new Promise(res => { const t0 = Date.now(); const id = setInterval(() => { if (window.__submitted || Date.now() - t0 > 100000) { clearInterval(id); res({ submitted: !!window.__submitted, md: window.__answersMd }); } }, 500); })`

4. `submitted` が true なら、`md` を `<名前>/source/answers-plan-N.md` に書く（N は何回目か）。貼り付けられた md も同じように書く。
5. 要修正またはコメントがあるスライドは、設計図と原稿を直して 2 から出し直す（前回承認したスライドは選択済みで開く）。全部承認されたら、内容を凍結する（以降、承認なしに変えない）。

## 守ること

- 承認後は、承認なしに設計図と原稿の内容を変えない。
```

- [ ] **Step 5: 参照文書と README を更新する**

- `references/review-flow.md`: 手順 4 の末尾に Step 3-6 と同じ「18 回…続行方法を質問して止まる」を足す。手順 3 に `plan-review.html` の言及を足す。`pngs` を `previews` に直す。
- `references/check-rules.md`・`html-rules.md`: `grep -n "LibreOffice\|pngs\|画像" …` で出た箇所を、「確認用の画像は `final.html` の撮影（PPTX の実描画ではない）」に合わせて直す。
- `README.md`: (1) 依存関係の表の LibreOffice の行を削除し、「必須: システムの Python に python-pptx・playwright・pymupdf・lxml・chromium がそろっていればそれを使う。なければ `%LOCALAPPDATA%\pptx-deck\venv` に承認後に作る」に直す。Playwright MCP の行に「プラグインには同梱しない。ないときは回答を貼り付ける」と書く。「最終確認」の行を「確認用の画像は HTML の撮影で、PPTX の実描画ではない。PowerPoint で開いて最終確認する」にする。(2) 使い方に 4 入口（`/pptx-deck:create`・`:revise`・`:rebuild`・`:review-plan`）と、完成後のフォルダ構成（`<名前>.pptx` と `source/`）を書く。(3) 76 行目付近の `部品見本.html` の説明の「画像は LibreOffice の描画」を、実際の作り方に合わせて直す（次の Step）。
- `部品見本.html` の作り方の確認: `grep -rn "部品見本" --include=*.py --include=*.md --include=*.json .` で、生成するスクリプトがあるかを調べる。スクリプトがなければ、README の記述を「`assets/components/` の各断片を `preview.screenshots` と同じ方法で撮った画像を並べた一覧。作り直す手順は未整備」に改め、**`部品見本.html` 自体は作り直さない**（範囲外。未確認として報告に残す）。

- [ ] **Step 6: テストを通す・コミット**

Run: `$PY -k test_docs`  → Expected: PASS
Run: `$PY`  → Expected: すべて PASS

```bash
git add -A
git commit -m "docs: スキルを create・revise・rebuild・review-plan に分け、LibreOffice と待ち受けの記述を更新する"
```

---

### Task 14: プラグインの定義と導入の確認（項目 8、受入条件 10・11）

**Files:**
- Modify: `plugins/pptx-deck/.claude-plugin/plugin.json`（version を `0.3.0`、`author` と `description` を更新）
- Create: `.claude-plugin/marketplace.json`
- Modify: `README.md`（導入手順）

**Interfaces:**
- Consumes: Task 12・13 の構成

- [ ] **Step 1: `plugin.json` を書き換える**

```json
{
  "name": "pptx-deck",
  "version": "0.3.0",
  "description": "ビジネス上の承認文書をコンサルテイストで作る。設計図と原稿の承認 → スライド案（各 3 案）の選択 → 最終 HTML → 編集可能な PPTX。作った PPTX の再修正・再生成にも対応。利用者のテンプレートに従える。Windows 専用。",
  "author": { "name": "asama0101" },
  "license": "MIT"
}
```

- [ ] **Step 2: `.claude-plugin/marketplace.json` を書く**

```json
{
  "name": "pptx-deck-market",
  "owner": { "name": "asama0101" },
  "plugins": [
    {
      "name": "pptx-deck",
      "source": "./plugins/pptx-deck",
      "description": "ビジネス上の承認文書をコンサルテイストで作り、PPTX を再修正・再生成できる。Windows 専用。"
    }
  ]
}
```

- [ ] **Step 3: 検証する**

Run: `claude plugin validate plugins/pptx-deck`
Expected: エラーなし。警告が出たら内容を読み、`--strict` でも通るように直す（`name` の不一致、パスが `./` で始まっていない等）。
Run: `claude plugin validate .`（マーケットプレイスの定義の検証。サブコマンドの引数が違う場合は `claude plugin validate --help` で確かめる）
Expected: エラーなし。

- [ ] **Step 4: ローカルで導入して動かす（外部への公開なし）**

Run（別のターミナルで）: `claude --plugin-dir plugins/pptx-deck`
確認: セッション内で `/pptx-deck:create`・`:revise`・`:rebuild`・`:review-plan` が候補に出る。`/pptx-deck:rebuild` を、テスト用の作品（`tests/test_e2e_sample.py` と同じ手順で一時フォルダに作ったもの）で呼び、`${CLAUDE_PLUGIN_ROOT}` がコマンドの中で実パスに展開されて `run.py` が動くことを確かめる。展開されない場合は、SPEC のリスク「`${CLAUDE_PLUGIN_ROOT}` の展開」に該当する。**止まって利用者に相談する**（SKILL.md のパスの書き方を変える判断は SPEC に戻る）。

- [ ] **Step 5: README に導入手順を書く**

```markdown
## 導入

プラグインとして導入する（GitHub に公開した後）:

    /plugin marketplace add asama0101/pptx-deck
    /plugin install pptx-deck@pptx-deck-market

開発中にローカルで試す: `claude --plugin-dir plugins/pptx-deck`（変更は `/reload-plugins` で反映）。

Playwright MCP はプラグインに含まれない。案の選択と回答の受け取りに使うので、Claude Code に別に設定する（ない場合は、回答を貼り付けて渡す）。
```

- [ ] **Step 6: 最終確認（受入条件のチェック）**

Run: `$PY`  → Expected: すべて PASS
Run: `grep -rniE "libreoffice|soffice" plugins README.md docs/verification.md | grep -vE "使わ|使用しな|不要|なし|廃止"` → Expected: 出力なし（受入条件 10）
Run: `git status --short`  → Expected: 変更なし（`cloud-ringi` の残りや一時ファイルが無い）

- [ ] **Step 7: コミット**

```bash
git add -A
git commit -m "feat: プラグインの定義（plugin.json 0.3.0・marketplace.json）と導入手順を追加する"
```

- [ ] **Step 8: 利用者に報告し、了承を取る**

報告する内容: (1) 受入条件 1〜13 の達成状況（人が見る項目: PowerPoint での確認、Playwright MCP でのレビューページの操作は「未実施」と明記）、(2) `~/.claude/skills/pptx-deck`（リンク）の取り外しの了承の確認（導入が確認できてから）、(3) GitHub への push の了承の確認（マーケットプレイスからの導入に必要）、(4) `部品見本.html` の作り直しが未整備であること。**了承なしに push・リンクの取り外しを行わない。**

---

## 自己レビュー

**SPEC の網羅:**

| SPEC | タスク |
|---|---|
| 1 前回承認の自動選択 | Task 5（抽出）・6（画面） |
| 2 承認で次へ | Task 6 |
| 3 自動確認の維持と上限後の質問 | Task 13（SKILL.md・review-flow.md・review-plan） |
| 4 LibreOffice 廃止 | Task 3（背景色）・4（撮影・doctor・render.py 削除） |
| 5 再修正（reopen・2 パターン） | Task 9（reopen）・13（revise の手順） |
| 6 整理・source/ 構成 | Task 7（構成）・8（指紋・整理・clean） |
| 7 設計図と原稿の HTML | Task 10 |
| 8 プラグイン化 | Task 12（再配置）・13（4 入口）・14（定義・導入） |
| 9 Python の選択 | Task 2 |
| 受入条件 13（通しの検証） | Task 11 |

**SPEC からの意図的な差分（実装判断）:** (1) `%TEMP%\pptx-deck\<名前>\` の削除は、確認用の画像を見る前に消さないよう、`build` ではなく `clean` で行う（Task 8）。(2) 設計図と原稿のレビューページは、資料全体を `S00` として先頭に足す（Task 10）。これらを実装後の報告に入れる。

**プレースホルダー検査:** 各コード手順は実コードを含む。テストコード内の「実装時に直す」という注記は残していない。

**型・名前の一貫性:** `approved_preset`（Task 5）→ Task 6・10 が使用、`answer_paths`・`plan_answer_paths`・`next_round`（Task 5）→ Task 6・9・10、`write_derived`（Task 4）→ Task 9、`fingerprint_status`・`record_build`・`prune`・`clean_temp`（Task 8）→ Task 9・11、`resolve_work`・`deck_dir`・`deck_name`・`is_legacy`（Task 7）→ Task 8〜11。`build` の出力キーは `previews`・`removed`（Task 4・8）で、Task 11・13 が同じ名前を使う。

**Review Focus の対応:** 1 旧形式 → Task 7・9 のテスト、2 回答の並び → Task 5、3 背景が単色でない → Task 3、4 手直しの上書き → Task 8・11、5 版違い・chromium なし → Task 2、6 未知のファイル → Task 8。
