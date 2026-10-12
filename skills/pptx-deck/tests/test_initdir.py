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


@has_soffice
def test_force_warns_about_existing_slides(tmp_path):
    w = tmp_path / "demo"
    (w / "slides").mkdir(parents=True)
    (w / "slides" / "03-C.html").write_text("<section class='slide'></section>", encoding="utf-8")
    r = initdir.init(w, force=True)
    assert any("slides/" in n and "1" in n for n in r["notes"])       # 古い案が混ざることを知らせる
    assert (w / "slides" / "03-C.html").exists()                      # 利用者の作業は消さない


@has_soffice
def test_init_copies_design_template(tmp_path):
    w = tmp_path / "w"
    initdir.init(w, color="navy")
    assert (w / "design.md").exists()
    assert "ガバニングメッセージ" in (w / "design.md").read_text(encoding="utf-8")


@has_soffice
def test_force_keeps_existing_design(tmp_path):
    w = tmp_path / "w"
    w.mkdir()
    (w / "design.md").write_text("利用者の設計図", encoding="utf-8")
    initdir.init(w, force=True)
    assert (w / "design.md").read_text(encoding="utf-8") == "利用者の設計図"   # 利用者の作業は上書きしない


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
