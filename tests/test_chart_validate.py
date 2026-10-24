"""グラフ指定と画像の src を check_model がエラーにする（build が途中で例外にならない）。stacked100 は廃止。"""

# ruff: noqa: S101  # pytest の assert
import html
import json
import os
import re
import subprocess
import sys

import pytest
from pptx_deck import charts, check, initdir, measure, paths, template

from tests._measure import model_of
from tests._paths import PKG

pytestmark = pytest.mark.slow  # ブラウザ（Chromium）で測る

BOX = 'style="position:absolute;left:80px;top:120px;width:600px;height:360px"'
IMG_STYLE = 'style="position:absolute;left:80px;top:120px;width:100px;height:100px"'


def _spec(**kw):
    s = {"type": "bar", "categories": ["a", "b", "c"], "series": [{"name": "s", "values": [1, 2, 3]}]}
    s.update(kw)
    return s


def _chart_model(spec):
    return model_of(f"<div class=\"pp-chart\" {BOX} data-chart='{html.escape(json.dumps(spec), quote=True)}'></div>")


def _info():
    return template.analyze(paths.ASSETS / "template" / "standard.potx")


def _rules(model, rule):
    return [v for v in check.check_model(model, _info()) if v["rule"] == rule]


BAD_SPECS = {
    "area": (_spec(type="area"), "未対応のグラフ型: area"),
    "stacked100": (_spec(type="stacked100"), "未対応のグラフ型: stacked100"),
    "highlight": (_spec(highlight=5), "highlight 5 が範囲外です（0 〜 2）"),
    "axis": (_spec(axis={"min": 3, "max": 3}), "axis の min は max より小さくしてください（min=3, max=3）"),
    "waterfall": (
        _spec(type="waterfall", series=[{"name": "s", "values": [10, -20, 5]}]),
        "累計が 0 未満になります（2 番目）",
    ),
    "categories": (_spec(categories=[]), "categories（カテゴリ）が空です"),
    "series": (_spec(series=[]), "series（系列）が空です"),
    "長さ違い": (_spec(series=[{"name": "s", "values": [1, 2]}]), "カテゴリ数（3）と同じ長さの数値の配列"),
    "None": (_spec(series=[{"name": "s", "values": [1, None, 3]}]), "カテゴリ数（3）と同じ長さの数値の配列"),
    "文字列": (_spec(series=[{"name": "s", "values": [1, "2", 3]}]), "カテゴリ数（3）と同じ長さの数値の配列"),
    "bool": (_spec(series=[{"name": "s", "values": [1, True, 3]}]), "カテゴリ数（3）と同じ長さの数値の配列"),
    "waterfall2系列": (
        _spec(type="waterfall", series=[{"name": "s", "values": [10, 5, 3]}, {"name": "t", "values": [1, 2, 3]}]),
        "waterfall の series は 1 つだけです",
    ),
}


@pytest.mark.parametrize("t", ["bar", "barh", "line", "pie", "stacked"])
def test_正常な指定は問題なしを返す(t):
    assert charts.validate(_spec(type=t)) == []


def test_正常なウォーターフォールは問題なしを返す():
    assert charts.validate(_spec(type="waterfall", series=[{"name": "s", "values": [10, 5, -3]}])) == []


@pytest.mark.parametrize(("spec", "msg"), BAD_SPECS.values(), ids=BAD_SPECS.keys())
def test_不正な指定は_validate_が1件の文で理由を返す(spec, msg):
    got = charts.validate(spec)
    assert len(got) == 1
    assert msg in got[0]


@pytest.mark.slow
@pytest.mark.parametrize(("spec", "msg"), BAD_SPECS.values(), ids=BAD_SPECS.keys())
def test_不正な指定は_check_model_が_chartSpec_のエラーを1件出す(spec, msg):
    vs = _rules(_chart_model(spec), "chartSpec")
    assert len(vs) == 1
    assert vs[0]["severity"] == "error"
    assert msg in vs[0]["message"]


def test_add_chart_は未対応型で従来の文言の例外にする():
    with pytest.raises(ValueError, match="未対応のグラフ型"):
        charts.add_chart(None, {"chart": _spec(type="area"), "rect": {}}, None)


@pytest.mark.slow
def test_正常なグラフは_chartSpec_を出さない():
    assert _rules(_chart_model(_spec(highlight=2)), "chartSpec") == []


@pytest.mark.slow
@pytest.mark.parametrize(
    "src", ["https://example.com/a.png", "file:///nonexistent/zzz.png"], ids=["外部_URL", "存在しないファイル"]
)
def test_使えない画像の_src_は_imageSrc_エラーになる(src):
    m = model_of(f'<img class="pp-image" alt="a" src="{src}" {IMG_STYLE}>')
    vs = _rules(m, "imageSrc")
    assert len(vs) == 1
    assert vs[0]["severity"] == "error"


@pytest.mark.slow
def test_存在する画像は_imageSrc_を出さない(tmp_path):
    p = tmp_path / "a.png"
    p.write_bytes(b"x")
    m = model_of(f'<img class="pp-image" alt="a" src="{p.as_uri()}" {IMG_STYLE}>')
    assert _rules(m, "imageSrc") == []


@pytest.mark.slow
def test_不正なグラフ指定でも_build_は_traceback_を出さず_chartSpec_を報告して止まる(tmp_path):
    base = tmp_path / "deck"
    initdir.init(base, color="navy", template_path=None, force=False, footer=None)
    work = paths.resolve_work(base)
    sec = (
        '<section class="slide" data-layout="content"><div class="pp-text" data-role="title" '
        'style="position:absolute;left:80px;top:40px;width:600px;height:50px">題</div>'
        f"<div class=\"pp-chart\" {BOX} data-chart='{json.dumps(_spec(type='area'))}'></div></section>"
    )
    (work / "final.html").write_text(
        '<!doctype html><html lang="ja"><head><meta charset="utf-8"><link rel="stylesheet" href="theme.css">'
        f'<link rel="stylesheet" href="base.css"></head><body>{sec}</body></html>',
        encoding="utf-8",
    )
    r = subprocess.run(  # noqa: S603  # 自分の入口を sys.executable で起動する（外部入力なし）
        [sys.executable, "-m", "pptx_deck", "build", str(base)],
        cwd=PKG,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    assert r.returncode == 1, r.stderr
    assert "Traceback" not in r.stderr
    assert "chartSpec" in r.stdout
    assert not (base / "deck.pptx").exists()


@pytest.mark.slow
def test_部品見本の全スライドで_chartSpec_と_imageSrc_の誤検出がない(tmp_path):
    comp = PKG / "assets" / "components"
    sec = re.compile(r"<section\b.*?</section>", re.S)
    secs = []
    for f in sorted(comp.rglob("*.html")):
        m = sec.search(re.sub(r"<!--.*?-->", "", f.read_text(encoding="utf-8"), flags=re.S))
        if m:
            secs.append((f.relative_to(comp).as_posix(), m.group(0)))
    assert len(secs) >= 150
    base = tmp_path / "deck"
    initdir.init(base, color="navy", template_path=None, force=False, footer=None)
    work = paths.resolve_work(base)
    info = template.TemplateInfo.from_dict(json.loads((work / "template.json").read_text(encoding="utf-8"))["info"])
    doc = (
        '<!doctype html><html lang="ja"><head><meta charset="utf-8">'
        '<link rel="stylesheet" href="theme.css"><link rel="stylesheet" href="base.css"></head><body>'
        + "\n".join(s for _, s in secs)
        + "</body></html>"
    )
    (work / "final.html").write_text(doc, encoding="utf-8")
    model = measure.measure(work / "final.html")
    bad = [
        (secs[v["slide"] - 1][0], v["message"])
        for v in check.check_model(model, info)
        if v["rule"] in ("chartSpec", "imageSrc")
    ]
    assert bad == []
