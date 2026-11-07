"""文字サイズの項目（fontsize.py）と、theme.css / base.css の変数化。"""

# ruff: noqa: S101  # pytest の assert
import json

import pytest
from pptx_deck import fontsize, initdir, paths

from tests._paths import PKG


def test_defaults():
    cur = fontsize.current({})
    assert cur["title"] == 37
    assert cur["caption"] == 16
    assert cur["chart-scale"] == 1.0


def test_clamp():
    assert fontsize.clamp("body", 10) == 19
    assert fontsize.clamp("body", 99) == 30
    assert fontsize.clamp("chart-scale", 0.5) == 0.84
    assert fontsize.clamp("num-scale", 1.234) == 1.23


def test_parse_line_last_wins_and_drops_unknown():
    text = "- 文字サイズ: title=40 x=3 body=abc\n- 文字サイズ: title=41"
    assert fontsize.parse_line(text) == {"title": 41.0}


def test_format_roundtrip():
    line = fontsize.format_line({"title": 40, "num-scale": 1.1})
    assert fontsize.parse_line(line) == {"title": 40.0, "num-scale": 1.1}
    assert fontsize.format_line({}) == ""


def test_theme_css_has_vars(tmp_path):
    base = tmp_path / "out" / "pptx-deck-source" / "deck"
    initdir.init(base, color="navy")
    work = paths.resolve_work(base)
    css = (work / "theme.css").read_text(encoding="utf-8")
    assert "--fs-title: 37px;" in css
    assert "--fs-cover-sub: 22px;" in css
    assert "--num-scale: 1;" in css

    initdir.set_font_size(work, {"title": 40})
    assert "--fs-title: 40px;" in (work / "theme.css").read_text(encoding="utf-8")
    assert json.loads((work / "template.json").read_text(encoding="utf-8"))["fontsizes"] == {"title": 40}

    initdir.set_font_size(work, {"title": 37})
    assert not json.loads((work / "template.json").read_text(encoding="utf-8")).get("fontsizes")


def test_base_css_reads_vars():
    css = (PKG / "assets" / "web" / "base.css").read_text(encoding="utf-8")
    for token in (
        "font-size: var(--fs-title, 37px)",
        "font-size: var(--fs-lead, 27px)",
        "font-size: var(--fs-body, 19px)",
        "font-size: var(--fs-caption, 16px)",
        "font-size: var(--fs-cover-title, 40px)",
        "font-size: var(--fs-cover-sub, 22px)",
        '[data-role="subhead"]',
        "font-size: var(--fs-subhead, 22px)",
        "calc(44px * var(--num-scale, 1))",
    ):
        assert token in css, token


def test_theme_css_vars_are_inside_balanced_root(tmp_path):
    import re

    base = tmp_path / "out" / "pptx-deck-source" / "deck"
    initdir.init(base, color="navy")
    css = (paths.resolve_work(base) / "theme.css").read_text(encoding="utf-8")
    assert css.count("{") == css.count("}")
    roots = re.findall(r":root\s*\{([^{}]*)\}", css)
    assert roots
    inside = "\n".join(roots)
    for it in fontsize.ITEMS:
        assert f"{it.var}:" in inside
        assert css.count(f"{it.var}:") == 1


@pytest.fixture
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def test_chart_pt():
    from pptx_deck import charts

    assert charts.chart_pt(1.0) == 12
    assert charts.chart_pt(0.84) == 10
    assert charts.chart_pt(1.5) == 18
    assert charts.chart_pt(0.7) == 10


@pytest.mark.slow
def test_build_chart_font_follows_scale(pkg, tmp_path):
    import html
    import json

    from pptx import Presentation
    from pptx_deck import build, template

    from tests._measure import model_of

    base = tmp_path / "out" / "pptx-deck-source" / "deck"
    initdir.init(base, color="navy")
    work = paths.resolve_work(base)
    initdir.set_font_size(work, {"chart-scale": 1.25})
    spec = {"type": "bar", "categories": ["a", "b"], "series": [{"name": "x", "values": [1, 2]}]}
    box = 'style="position:absolute;left:100px;top:150px;width:600px;height:400px"'
    model = model_of(f"<div class=\"pp-chart\" {box} data-chart='{html.escape(json.dumps(spec), quote=True)}'></div>")
    from types import SimpleNamespace

    pal = SimpleNamespace(accent="#00AA55", accent_mid="#55AA88", accent_dark="#005522")
    tpl = pkg / "assets" / "template" / "standard.potx"
    out = build.build(model, tpl, template.analyze(tpl), pal, tmp_path / "o.pptx", base_dir=work)
    chart = [s for s in Presentation(str(out)).slides[0].shapes if s.has_chart][0].chart
    assert chart.font.size.pt == 15


@pytest.mark.slow
def test_preview_uses_scale(browser, pkg):
    import json

    js = (pkg / "assets" / "web" / "chart-preview.js").read_text(encoding="utf-8")
    spec = {"type": "bar", "categories": ["a", "b"], "series": [{"name": "x", "values": [1, 2]}]}
    html = (
        "<html><body><div class='pp-chart' style='position:relative;width:600px;height:400px' "
        f"data-chart='{json.dumps(spec)}'></div></body></html>"
    )

    def sizes(scale):
        page = browser.new_page()
        page.set_content(html)
        page.evaluate(f"document.documentElement.style.setProperty('--chart-scale', '{scale}')")
        page.add_script_tag(content=js)
        page.evaluate("document.querySelectorAll('.pp-chart').forEach(window.__chartPreview)")
        out = page.evaluate("[...document.querySelectorAll('svg text')].map(t => +t.getAttribute('font-size'))")
        page.close()
        return out

    base, big = sizes(1), sizes(1.5)
    assert base
    assert max(big) > max(base)
