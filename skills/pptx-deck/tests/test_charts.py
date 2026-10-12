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
    # 強調しない点は系列の塗り（基調色）のまま。点ごとの塗りは強調した点にだけ付く
    assert str(ch.plots[0].series[0].format.fill.fore_color.rgb) == PAL.accent.lstrip("#")


def test_axis_sets_min_max_and_major_unit(tmp_path):
    # 小グラフを並べるときは、軸の最大・最小・目盛を全パネルで揃える（"axis" で指定する）
    ch = built({**BASE, "type": "bar", "axis": {"min": 0, "max": 600, "major": 150}}, tmp_path)
    ax = ch.value_axis
    assert (ax.minimum_scale, ax.maximum_scale, ax.major_unit) == (0, 600, 150)


def test_axis_is_automatic_without_spec(tmp_path):
    ax = built({**BASE, "type": "bar"}, tmp_path).value_axis
    assert ax.minimum_scale is None and ax.maximum_scale is None and ax.major_unit is None


def test_fonts_are_at_least_10pt_and_biz(tmp_path):
    ch = built({**BASE, "type": "bar"}, tmp_path)
    assert ch.font.size.pt >= 10 and ch.font.name == "BIZ UDPゴシック"


def test_chart_font_sets_east_asian_face(tmp_path):
    ch = built({**BASE, "type": "bar"}, tmp_path)
    # 日本語の文字は a:ea の書体で描かれる。a:latin だけだとテーマの書体に落ちる
    assert 'a:ea typeface="BIZ UDPゴシック"' in ch._chartSpace.xml.replace("'", '"')


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


def test_waterfall_labels_are_readable_on_their_bars(tmp_path):
    ch = built({"type": "waterfall", "categories": ["前", "増", "減", "後"],
                "series": [{"name": "金額", "values": [100, 20, -30, 90]}], "totals": [0, 3]}, tmp_path)
    s = ch.plots[0].series
    fills = [PAL.accent, "#404040", "#767676"]
    for ser, fill in zip(list(s)[1:], fills):
        label = str(ser.data_labels.font.color.rgb)
        assert theme.contrast("#" + label, fill) >= 4.5


def test_waterfall_small_step_label_moves_out_of_the_thin_bar(tmp_path):
    ch = built({"type": "waterfall", "categories": ["現状", "保守費", "電力費", "監視費", "導入後"],
                "series": [{"name": "運用費", "values": [4200, -900, -300, -100, 2900]}], "totals": [0, 4]}, tmp_path)
    s = list(ch.plots[0].series)
    # 棒の高さが軸の 6% 未満の増減は、棒の中ではなく、基準の系列に黒字で値を出す
    lbl = s[0].points[3].data_label
    assert lbl.has_text_frame and lbl.text_frame.text == "100"
    run_font = lbl.text_frame.paragraphs[0].runs[0].font           # リッチテキストの文字色は run に付く
    assert theme.contrast("#" + str(run_font.color.rgb), "#FFFFFF") >= 4.5
    assert not s[0].points[1].data_label.has_text_frame            # 大きな棒は棒の中のラベルのまま
    assert "[>=" in s[2].data_labels.number_format                  # 小さい値は棒の中のラベルを出さない


def test_waterfall_large_values_do_not_use_scientific_notation(tmp_path):
    # 円単位の大きな値でも、数値書式に 1.02e+07 のような指数表記を入れない（PowerPoint が解釈できない）
    ch = built({"type": "waterfall", "categories": ["現状", "保守費", "電力費", "導入後"],
                "series": [{"name": "運用費", "values": [170000000, -9000000, -1000000, 160000000]}],
                "totals": [0, 3], "fmt": "0"}, tmp_path)
    s = list(ch.plots[0].series)
    assert "e+" not in s[1].data_labels.number_format
    assert "e+" not in s[0].points[2].data_label.text_frame.text and s[0].points[2].data_label.text_frame.text == "1000000"


def test_unknown_type_is_an_error(tmp_path):
    with pytest.raises(ValueError, match="radar"):
        built({**BASE, "type": "radar"}, tmp_path)
