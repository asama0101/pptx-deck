"""グラフ指定 → PowerPoint のネイティブグラフ。色は配色（Palette）から取る。"""
from lxml import etree
from pptx.chart.data import CategoryChartData
from pptx.oxml.ns import qn
from pptx.enum.chart import XL_CHART_TYPE as C, XL_LEGEND_POSITION
from pptx.util import Pt

from .pptxutil import FONT, emu, rgb

TYPES = {"bar": C.COLUMN_CLUSTERED, "barh": C.BAR_CLUSTERED, "line": C.LINE_MARKERS, "pie": C.PIE,
         "stacked": C.COLUMN_STACKED, "stacked100": C.COLUMN_STACKED_100, "waterfall": C.COLUMN_STACKED}
FONT_PT = 12


def waterfall_series(values, totals):
    n = len(values)
    totals = set(totals if totals is not None else [0, n - 1])
    base, up, down, tot = [], [], [], []
    run = 0
    for i, v in enumerate(values):
        if i in totals:
            base.append(0); up.append(0); down.append(0); tot.append(v)
            run = v
        elif v >= 0:
            base.append(run); up.append(v); down.append(0); tot.append(0)
            run += v
        else:
            run += v
            if run < 0:
                raise ValueError(f"累計が 0 未満になります（{i + 1} 番目）。値を確認してください")
            base.append(run); up.append(0); down.append(-v); tot.append(0)
    return {"base": base, "up": up, "down": down, "total": tot}


def _series_colors(p):
    return [p.accent, p.accent_mid, "#8C8C8C", p.accent_dark, "#BFBFBF"]


def _fill(series, hex6):
    series.format.fill.solid()
    series.format.fill.fore_color.rgb = rgb(hex6)


def add_chart(slide, el, palette):
    spec, r = el["chart"], el["rect"]
    t = spec["type"]
    if t not in TYPES:
        raise ValueError(f"未対応のグラフ型: {t}（{', '.join(TYPES)}）")
    cd = CategoryChartData()
    cd.categories = spec["categories"]
    if t == "waterfall":
        w = waterfall_series(spec["series"][0]["values"], spec.get("totals"))
        for name, key in (("基準", "base"), ("増加", "up"), ("減少", "down"), ("合計", "total")):
            cd.add_series(name, w[key])
    else:
        for s in spec["series"]:
            cd.add_series(s["name"], s["values"])
    gf = slide.shapes.add_chart(TYPES[t], emu(r["x"]), emu(r["y"]), emu(r["w"]), emu(r["h"]), cd)
    chart = gf.chart
    chart.font.size = Pt(FONT_PT)
    chart.font.name = FONT
    latin = chart.font._element.find(qn("a:latin"))
    ea = etree.Element(qn("a:ea"))
    ea.set("typeface", FONT)
    latin.addnext(ea)             # 日本語は a:ea の書体で描かれる
    colors = _series_colors(palette)
    fmt = spec.get("fmt", "#,##0")
    plot = chart.plots[0]
    chart.has_title = False

    if t == "pie":
        ser = plot.series[0]
        cycle = [palette.accent, palette.accent_mid, "#8C8C8C", palette.accent_dark, "#BFBFBF"]
        for i in range(len(spec["categories"])):
            pt = ser.points[i]
            pt.format.fill.solid()
            pt.format.fill.fore_color.rgb = rgb(palette.emphasis if spec.get("highlight") == i else cycle[i % 5])
        plot.has_data_labels = True
        plot.data_labels.number_format = fmt
        plot.data_labels.number_format_is_linked = False
        chart.has_legend = True
        chart.legend.position = XL_LEGEND_POSITION.BOTTOM
        chart.legend.include_in_layout = False
        return

    value_axis = chart.value_axis
    value_axis.has_major_gridlines = False
    value_axis.tick_labels.font.size = Pt(FONT_PT)
    chart.category_axis.tick_labels.font.size = Pt(FONT_PT)
    plot.gap_width = 60

    if t == "waterfall":
        plot.overlap = 100
        s_base, s_up, s_down, s_tot = plot.series
        s_base.format.fill.background()
        _fill(s_up, palette.accent)
        _fill(s_down, "#404040")
        _fill(s_tot, "#767676")
        s_base.data_labels.show_value = False
        for s in (s_up, s_down, s_tot):
            dl = s.data_labels
            dl.show_value = True
            dl.number_format = fmt + ";-" + fmt + ";;"
            dl.number_format_is_linked = False
            dl.font.size = Pt(FONT_PT)
            dl.font.color.rgb = rgb("#FFFFFF")  # 棒はいずれも濃色。白でコントラスト 4.5:1 以上
        chart.has_legend = False
        return

    for i, ser in enumerate(plot.series):
        if t == "line":
            ser.format.line.color.rgb = rgb(colors[i % 5])
            ser.format.line.width = Pt(2.5)
            ser.smooth = False
        else:
            _fill(ser, colors[i % 5])
    if t in ("bar", "barh") and spec.get("highlight") is not None:
        pt = plot.series[0].points[spec["highlight"]]
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = rgb(palette.emphasis)
    if t.startswith("stacked"):
        plot.overlap = 100
    plot.has_data_labels = True
    plot.data_labels.number_format = fmt
    plot.data_labels.number_format_is_linked = False
    plot.data_labels.font.size = Pt(FONT_PT)
    multi = len(plot.series) > 1
    chart.has_legend = multi
    if multi:
        chart.legend.position = XL_LEGEND_POSITION.BOTTOM
        chart.legend.include_in_layout = False
