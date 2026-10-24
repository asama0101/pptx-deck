"""init --force は、明示しなかった色・フッター・テンプレートを保つ。"""

# ruff: noqa: S101  # pytest の assert
import json
import zipfile
from pathlib import Path

import pytest
from pptx_deck import cli, initdir, paths

NAVY, GREEN = "#1F3A5F", "#1E6B52"


def _custom_template(dst: Path) -> Path:
    """標準テンプレートに余分なエントリを足して、標準とバイト列が違うテンプレートを作る。"""
    src = paths.ASSETS / "template" / "standard.potx"
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            zout.writestr(item, zin.read(item.filename))
        zout.writestr("docProps/marker.txt", "custom")
    return dst


def _cfg(work: Path) -> dict:
    return json.loads((work / "template.json").read_text(encoding="utf-8"))


@pytest.fixture
def deck(tmp_path):
    """緑・独自テンプレート・フッターつきで init した作業フォルダ。(base, work, 独自テンプレートのバイト列)"""
    base = tmp_path / "deck"
    tpl = _custom_template(tmp_path / "other.potx")
    initdir.init(base, color="green", template_path=tpl, footer="© 2026 A")
    work = paths.resolve_work(base)
    tbytes = tpl.read_bytes()
    assert tbytes != (paths.ASSETS / "template" / "standard.potx").read_bytes()
    assert (work / _cfg(work)["template"]).read_bytes() == tbytes
    return base, work, tbytes


def test_forceだけなら色_フッター_テンプレートを保つ(deck):
    base, work, tbytes = deck
    initdir.init(base, force=True)
    after = _cfg(work)
    assert after["color"] == GREEN
    assert after["footer"] == "© 2026 A"
    assert (work / after["template"]).read_bytes() == tbytes


def test_CLIのforceだけなら色_フッター_テンプレートを保つ(deck):
    base, work, tbytes = deck
    assert cli.main(["init", str(base), "--force"]) == 0
    after = _cfg(work)
    assert after["color"] == GREEN
    assert after["footer"] == "© 2026 A"
    assert (work / after["template"]).read_bytes() == tbytes


def test_forceと色を指定したら色だけ変わる(deck):
    base, work, tbytes = deck
    initdir.init(base, color="navy", force=True)
    after = _cfg(work)
    assert after["color"] == NAVY
    assert after["footer"] == "© 2026 A"
    assert (work / after["template"]).read_bytes() == tbytes


def test_新規のinitは既定値_標準テンプレート_フッターなし(tmp_path):
    base = tmp_path / "deck"
    initdir.init(base)
    work = paths.resolve_work(base)
    cfg = _cfg(work)
    assert cfg["color"] == NAVY
    assert cfg["footer"] is None
    assert (work / cfg["template"]).read_bytes() == (paths.ASSETS / "template" / "standard.potx").read_bytes()
