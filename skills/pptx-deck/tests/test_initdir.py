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
        initdir.init(tmp_path / "x", template_path=bad)
    assert not (tmp_path / "x").exists()


def test_base_css_contract():
    css = (paths.ASSETS / "web" / "base.css").read_text(encoding="utf-8")
    for token in ("1280px", "720px", "position: absolute", "var(--title-x)", "var(--cover-title-x)", "var(--closing-title-x)",
                  "BIZ UDPGothic", "var(--area-x)"):
        assert token in css
