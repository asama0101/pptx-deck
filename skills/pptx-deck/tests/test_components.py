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
