import json
from pathlib import Path

import pytest

from pptx_deck import measure

HEAD = """<!doctype html><html lang="ja"><head><meta charset="utf-8"><style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Yu Gothic','Meiryo',sans-serif}
.slide{position:relative;width:1280px;height:720px;--bg:#FFFFFF;background:#FFFFFF}
.pp-text,.pp-shape,.pp-line,.pp-image,.pp-table,.pp-chart{position:absolute}
</style></head><body>"""


def write(tmp_path, body, name="t.html"):
    p = tmp_path / name
    p.write_text(HEAD + body + "</body></html>", encoding="utf-8")
    return p


def test_zero_slides_is_an_error(tmp_path):
    p = write(tmp_path, "<div>no slide</div>")
    with pytest.raises(ValueError, match="section.slide"):
        measure.measure(p)


def test_text_shape_line(tmp_path):
    p = write(tmp_path, """
<section class="slide" data-layout="content">
  <div class="pp-shape" data-shape="round" style="left:64px;top:150px;width:400px;height:200px;background:#1F3A5F;border-radius:12px"></div>
  <div class="pp-text" data-role="title" style="left:64px;top:40px;width:900px;font-size:28px;font-weight:700;color:#1A1A1A">結論を言い切る見出し</div>
  <div class="pp-text" data-role="body" style="left:80px;top:170px;width:360px;font-size:20px;color:#FFFFFF"><p>一段落目</p><ul><li>箇条A</li><li>箇条B</li></ul></div>
  <div class="pp-line" data-arrow="end" style="left:480px;top:250px;width:100px;height:2px;background:#595959"></div>
</section>""")
    [s] = measure.measure(p)
    assert s["layout"] == "content" and s["bg"] == "FFFFFF"
    kinds = [e["kind"] for e in s["elements"]]
    assert kinds == ["shape", "text", "text", "line"]
    shape, title, body, line = s["elements"]
    assert shape["shape"] == "round" and shape["fill"]["hex"] == "1F3A5F"
    assert shape["rect"] == {"x": 64, "y": 150, "w": 400, "h": 200}
    assert title["role"] == "title" and title["paras"][0]["runs"][0]["text"] == "結論を言い切る見出し"
    assert title["paras"][0]["runs"][0]["size_px"] == 28 and title["paras"][0]["runs"][0]["bold"]
    assert [p["bullet"] for p in body["paras"]] == [False, True, True]
    assert body["bg"] == "1F3A5F"                      # 背後の実効色（コントラスト検査用）
    assert line["arrow"] is True and measure.title_of(s) is title


def test_overflow_flag_and_long_japanese_title(tmp_path):
    long_title = "あ" * 60
    p = write(tmp_path, f"""
<section class="slide" data-layout="content">
  <div class="pp-text" data-role="title" style="left:64px;top:40px;width:300px;height:30px;font-size:28px">{long_title}</div>
</section>""")
    [s] = measure.measure(p)
    t = s["elements"][0]
    assert t["overflow"] is True                       # 枠 30px に収まらない
    assert t["box"]["h"] > 60                          # 複数行に折り返した実測の高さ


def test_data_flags_and_ph(tmp_path):
    p = write(tmp_path, """
<section class="slide" data-layout="cover">
  <div class="pp-text" data-ph="title" style="left:96px;top:250px;width:900px;font-size:40px">表題</div>
  <div class="pp-shape" data-overlap data-chrome style="left:0;top:0;width:10px;height:10px;background:#000"></div>
</section>""")
    [s] = measure.measure(p)
    t, sh = s["elements"]
    assert t["ph"] == "title" and measure.title_of(s) is t
    assert sh["overlap"] is True and sh["chrome"] is True


def test_color_mix_and_reverse_arrow(tmp_path):
    p = write(tmp_path, """
<section class="slide" data-layout="content" style="--acc:#1F3A5F">
  <div class="pp-shape" data-shape="ellipse" data-overlap style="left:100px;top:150px;width:200px;height:200px;background:color-mix(in srgb, var(--acc) 40%, transparent)"></div>
  <div class="pp-line" data-arrow="end" data-dir="rev" style="left:400px;top:250px;width:100px;background:#595959"></div>
</section>""")
    [s] = measure.measure(p)
    sh, ln = s["elements"]
    assert sh["shape"] == "ellipse" and sh["fill"]["hex"] == "1F3A5F" and abs(sh["fill"]["a"] - 0.4) < 0.02
    assert ln["reverse"] is True


def test_dark_slide_background_is_reported(tmp_path):
    p = write(tmp_path, """
<section class="slide" data-layout="content" style="--bg:#101820;background:#101820">
  <div class="pp-text" data-role="body" style="left:64px;top:150px;width:400px;font-size:20px;color:#000000">暗い下地</div>
</section>""")
    [s] = measure.measure(p)
    assert s["bg"] == "101820" and s["elements"][0]["bg"] == "101820"   # Review Focus 3 の元データ


def test_table(tmp_path):
    p = write(tmp_path, """
<section class="slide" data-layout="content">
<table class="pp-table" style="left:64px;top:150px;width:600px;border-collapse:collapse;font-size:20px">
<tr style="height:50px"><td style="width:200px;background:#1F3A5F;color:#fff;padding:8px">項目</td><td colspan="2" style="width:400px;border-bottom:2px solid #BFBFBF;padding:8px">見出し</td></tr>
<tr style="height:50px"><td style="padding:8px">A</td><td style="padding:8px">B</td><td style="padding:8px">C</td></tr>
</table></section>""")
    [s] = measure.measure(p)
    t = s["elements"][0]["table"]
    assert len(t["xs"]) == 4 and len(t["rows"]) == 2
    c = t["rows"][0]["cells"]
    assert (c[0]["c0"], c[0]["c1"]) == (0, 1) and (c[1]["c0"], c[1]["c1"]) == (1, 3)
    assert c[0]["fill"]["hex"] == "1F3A5F" and c[1]["borders"]["b"]["w"] == 2


def test_chart_and_image(tmp_path):
    (tmp_path / "i.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>')
    spec = {"type": "bar", "categories": ["A", "B"], "series": [{"name": "x", "values": [1, 2]}]}
    p = write(tmp_path, f"""
<section class="slide" data-layout="content">
<div class="pp-chart" data-chart='{json.dumps(spec)}' style="left:64px;top:150px;width:500px;height:300px"></div>
<img class="pp-image" data-role="icon" src="i.svg" alt="アイコン" style="left:600px;top:150px;width:40px;height:40px">
</section>""")
    [s] = measure.measure(p)
    ch, im = s["elements"]
    assert ch["chart"]["type"] == "bar"
    assert im["alt"] == "アイコン" and im["src"].startswith("file:///") and im["src"].endswith("i.svg")
