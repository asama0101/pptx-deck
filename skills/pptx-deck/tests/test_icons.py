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
