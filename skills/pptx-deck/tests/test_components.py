import json
import re
import shutil
from pathlib import Path

import pytest

from pptx_deck import build, check, initdir, measure, paths, template, theme

COMP = paths.ASSETS / "components"
FILES = sorted(COMP.rglob("*.html"))
pytestmark = pytest.mark.skipif(shutil.which("soffice") is None and not Path(
    r"C:\Program Files\LibreOffice\program\soffice.exe").exists(), reason="LibreOffice なし")

# TEMP(Task 6 で外す): 部品庫の作り直しまで emptyBand・sameWord・orphanLine を除外（Task 6 で断片を作り直すときに外す）
TEMP_SKIP_RULES = {"emptyBand", "sameWord", "orphanLine"}

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
    violations = [v for v in violations if v["rule"] not in TEMP_SKIP_RULES]     # TEMP(Task 6 で外す)
    assert violations == [], violations
    # 基調色の文字は白地だけ（薄い面や濃い面の上には載せない）
    accent = theme.derive(cfg["color"]).accent.lstrip("#")
    for e in model[0]["elements"]:
        if e["kind"] == "text":
            for p in e["paras"]:
                for r in p["runs"]:
                    assert not ("text" in r and r["color"] == accent and e["bg"] != "FFFFFF"), (e["idx"], e["bg"])
    out = work / f"_c_{path.stem}.pptx"
    build.build(model, work / cfg["template"], info, theme.derive(cfg["color"]), out,
                base_dir=work, work_name="components")
    assert check.errors(check.check_pptx(out)) == []


def test_source_caption_follows_the_template_area(tmp_path):        # Review Focus 2
    """出典（書くときだけ）は本文領域の下端に付く。領域が標準より狭い（フッターが高い）テンプレートでは、
    出典が領域の内側に上がり、固定座標の本文と重なって検出される（フッターの上に黙って載らない）。"""
    from pptx.util import Emu
    from tests.test_template import STANDARD, _as_pptx
    tpl = _as_pptx(STANDARD, tmp_path / "tall_footer.pptx")
    prs = template.open_template(tpl)
    body = [l for l in prs.slide_layouts if l.name == "本文"][0]
    for ph in body.placeholders:
        if ph.placeholder_format.type == 7:                          # OBJECT（本文の領域）
            ph.height = Emu(round(410 * 9525))                      # 下端 560px
    prs.save(tpl)
    w = tmp_path / "w"
    initdir.init(w, color="navy", template_path=tpl)
    # 部品庫の断片は出典を持たない。出典を書くときの形（SKILL.md）を、判断スライドに足して確かめる
    caption = ('  <div class="pp-text" data-role="caption" data-chrome style="left:64px;top:calc(var(--area-y) + var(--area-h));'
               'width:900px;height:24px">出典: 社内試算（2026年9月）</div></section>')
    src = tmp_path / "decision_with_source.html"
    src.write_text((COMP / "layouts" / "decision.html").read_text(encoding="utf-8").replace("</section>", caption), encoding="utf-8")
    _, _, _, violations = check_fragment(src, w)
    assert any(v["rule"] in ("overlap", "contrast") for v in violations), violations     # 帯に載った出典は、重なりか文字色の指摘になる


@pytest.mark.parametrize("path", FILES, ids=lambda p: f"{p.parent.name}/{p.stem}")
def test_component_header_comment(path):
    head = path.read_text(encoding="utf-8").lstrip()
    assert head.startswith("<!--") and "用途:" in head.split("-->")[0]
    # 16 進の色（#RGB 〜 #RRGGBBAA）の直書きを検出する。数値の書式 "#,##0" は色ではないので対象外
    # 白（#FFFFFF）だけは直書きしてよい。それを除いた残りに 16 進色があれば、var(--…) と同じ行でも検出する
    hard = [l for l in head.splitlines() if "style=" in l
            and re.search(r"#[0-9A-Fa-f]{3,8}\b", re.sub(r"#[Ff]{6}\b", "", l))]
    assert not hard, f"色の直書きがあります（var(--…) を使う）: {hard}"


@pytest.mark.parametrize("path", FILES, ids=lambda p: f"{p.parent.name}/{p.stem}")
def test_component_has_review_notes(path):
    """型庫の断片には、レビューページの見どころ（data-note）が 2 つ以上付いている。属性を壊す文字を含まない。"""
    text = path.read_text(encoding="utf-8")
    notes = re.findall(r'data-note="([^"]*)"', text)
    assert len(set(notes)) >= 2, f"{path.name}: data-note が足りません"
    assert all(n.strip() and "<" not in n and "&quot;" not in n for n in notes)
