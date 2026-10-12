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


def test_preview_uses_fixed_axis(tmp_path):
    """axis の max を指定したプレビューは、棒の高さをその max に対する比で描く（パネル間で長さが比べられる）。"""
    from playwright.sync_api import sync_playwright
    spec = {"type": "bar", "categories": ["A"], "series": [{"name": "x", "values": [300]}], "axis": {"min": 0, "max": 600, "major": 150}}
    html = tmp_path / "p.html"
    html.write_text(
        '<!doctype html><meta charset="utf-8"><style>:root{--accent:#1F3A5F;--accent-mid:#8A9AB0;--accent-dark:#142640;'
        '--emphasis:#B85A0B;--text:#1A1A1A}.pp-chart{position:relative;width:600px;height:364px}</style>'
        f"<div class='pp-chart' data-chart='{json.dumps(spec, ensure_ascii=False)}'></div>"
        f"<script>{JS.read_text(encoding='utf-8')}</script>", encoding="utf-8")
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.goto(html.as_uri())
        h = pg.evaluate("parseFloat(document.querySelector('.pp-chart svg rect').getAttribute('height'))")
        b.close()
    assert h == pytest.approx((364 - 24 - 40) / 2, abs=0.5)        # 描画域の高さ 300px の半分


def test_preview_does_not_touch_measured_classes(tmp_path):
    # プレビューは pp-* クラスを持つ要素を増やさない（計測に混ざらないように）
    # 矢印の向きを決めるために既存の pp-line を読むのは許す（要素は増やさない）
    text = JS.read_text(encoding="utf-8").replace(".pp-chart", "").replace("pp-chart", "").replace(".pp-line[data-arrow]", "")
    assert "pp-" not in text
