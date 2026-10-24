"""束 F4: file: URL → パスの変換が UNC のホストを保つ（check と build で共通）、data-chart の破損、svg の id 接頭辞。"""

# ruff: noqa: S101  # pytest の assert
from pathlib import Path

import pytest
from pptx_deck import build, check, paths, pptxutil, svgids, template

from tests._measure import model_of

pytestmark = pytest.mark.slow  # ブラウザ（Chromium）で測る


def test_check_と_pptxutil_は同じ変換関数を共有する():
    assert check.file_url_to_path is pptxutil.file_url_to_path


CONVERTERS = {
    "pptxutil": pptxutil.file_url_to_path,
    "check": check.file_url_to_path,
    "build": lambda url: build.url_to_path(url, Path()),
}


@pytest.mark.parametrize("which", list(CONVERTERS), ids=list(CONVERTERS))
@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("file://nas/share/a.png", "\\\\nas\\share\\a.png"),
        ("file:///C:/x/a%20b.png", "C:\\x\\a b.png"),
    ],
    ids=["UNC_ホストを保つ", "ドライブとパーセント"],
)
def test_file_URL_をパスにする(which, url, expected):
    assert str(CONVERTERS[which](url)) == expected


CHART_BOX = 'style="position:absolute;left:80px;top:120px;width:600px;height:360px"'
SERIES_OK = '"series":[{"name":"s","values":[1]}]'


def _chart_spec_violations(data_chart):
    info = template.analyze(paths.ASSETS / "template" / "standard.potx")
    m = model_of(f"<div class=\"pp-chart\" {CHART_BOX} data-chart='{data_chart}'></div>")
    return [v for v in check.check_model(m, info) if v["rule"] == "chartSpec"]


@pytest.mark.parametrize(
    ("data_chart", "messages"),
    [
        ('{"type":"bar",}', ["chart#0: グラフの指定（data-chart）が JSON として読めません"]),
        (
            '{"type":"bar","categories":["a"],"series":["x"]}',
            ["chart#0: series の各要素は {name, values} のオブジェクトで指定してください"],
        ),
        ("[1,2]", ["chart#0: グラフの指定（data-chart）がオブジェクトではありません"]),
        ('{"type":"bar"}', ["chart#0: categories（カテゴリ）が空です", "chart#0: series（系列）が空です"]),
        ('{"type":"bar","categories":["a"],"series":"x"}', ["chart#0: categories と series は配列で指定してください"]),
        (
            '{"type":"bar","categories":["a"],' + SERIES_OK + ',"axis":5}',
            ["chart#0: axis はオブジェクトで指定してください"],
        ),
    ],
    ids=[
        "JSON構文エラー",
        "seriesの要素が辞書でない",
        "仕様が辞書でない",
        "必須キーなし",
        "seriesが配列でない",
        "axisが辞書でない",
    ],
)
def test_data_chart_が壊れていても_chartSpec_の違反になる(data_chart, messages):
    vs = _chart_spec_violations(data_chart)
    assert len(vs) == len(messages)
    for v, msg in zip(vs, messages, strict=True):
        assert v["message"].startswith(msg)
        assert v["severity"] == "error"
        assert v["slide"] == 1


def test_単一引用符の_id_と_href_にも接頭辞を付ける():
    frag = (
        "<div class=\"pp-picture\"><svg><defs><symbol id='i-a'/></defs>"
        "<use href='#i-a'/><use xlink:href=\"#i-a\"/></svg></div>"
    )
    assert svgids.uniquify(frag, "p-") == (
        "<div class=\"pp-picture\"><svg><defs><symbol id='p-i-a'/></defs>"
        "<use href='#p-i-a'/><use xlink:href=\"#p-i-a\"/></svg></div>"
    )


def test_url_の4つの書き方すべてに接頭辞を付ける():
    frag = (
        '<div class="pp-picture"><svg><defs><marker id="m"/></defs>'
        '<path marker-end="url(\'#m\')"/><path marker-end=\'url("#m")\'/><path marker-end="url(#m)"/>'
        '<path style="fill:url( #m )"/></svg></div>'
    )
    assert svgids.uniquify(frag, "p-") == (
        '<div class="pp-picture"><svg><defs><marker id="p-m"/></defs>'
        '<path marker-end="url(\'#p-m\')"/><path marker-end=\'url("#p-m")\'/><path marker-end="url(#p-m)"/>'
        '<path style="fill:url( #p-m )"/></svg></div>'
    )
