"""fragedit: 画面での編集を断片 HTML へ文字列の切り貼りで戻す。"""

# ruff: noqa: S101  # pytest の assert
import pytest
from pptx_deck import fragedit


def cuts(src):
    return [src[t.start : t.end] for t in fragedit.targets(src)]


# ---- 対象の決め方 ----


def test_文字と表のセルを出現順に対象にし図形は対象にしない():
    src = (
        '<section class="slide"><div class="pp-text">題<b>1</b></div>'
        '<table class="pp-table"><tr><td><p>a</p><p>b</p></td><th>c</th></tr></table>'
        '<div class="pp-shape"></div></section>'
    )
    assert cuts(src) == ["題<b>1</b>", "a", "b", "c"]


def test_絵の中の文字は対象にしない():
    assert fragedit.targets('<div class="pp-picture"><svg><text class="pp-text">x</text></svg></div>') == []


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        (
            '<div class="pp-text"><ul><li>a<br>b</li><li>c</ul></div><div class="pp-text">x<br>y',
            ["a<br>b", "c", "x<br>y"],
        ),
        ('<div class="pp-text"><p>一<p>二</div>', ["一", "二"]),
        ('<div class="pp-text"><ul><li>あ<li>い</ul></div>', ["あ", "い"]),
        # 入れ子の ul の li は外側の li を閉じない（容器の中の容器は数えないので対象は外側の 1 つ）
        ('<div class="pp-text"><ul><li>あ<ul><li>い</li></ul></li></ul></div>', ["あ<ul><li>い</li></ul>"]),
    ],
    ids=["箇条書きと閉じ忘れとvoid要素", "閉じないpは暗黙に閉じる", "閉じないliは暗黙に閉じる", "入れ子のliは外側だけ"],
)
def test_閉じタグの省略を補って対象を切り出す(src, expected):
    assert cuts(src) == expected


@pytest.mark.parametrize(
    ("t", "after", "expected"),
    [
        ("t1", "二を直した", '<div class="pp-text"><p>一<p>二を直した</div>'),
        ("t0", "一を直した", '<div class="pp-text"><p>一を直した<p>二</div>'),
    ],
    ids=["後ろのp", "前のp"],
)
def test_閉じないpを直しても隣は変わらない(t, after, expected):
    src = '<div class="pp-text"><p>一<p>二</div>'
    assert fragedit.apply_edit(src, {"t": t, "after": after}) == expected


def test_同梱の部品断片はすべて解析できる(pkg):
    total = 0
    for f in sorted((pkg / "assets" / "components").rglob("*.html")):
        for t in fragedit.targets(f.read_text(encoding="utf-8")):
            assert t.start <= t.end, f
            total += 1
    assert total > 0


# ---- インライン書式の浄化 ----


def test_許可した書式だけを残す():
    got = fragedit.sanitize_inline(
        '<b onclick="x()">a</b><script>x()</script><span style="color:var(--accent);position:fixed;font-size:20px">'
        "b</span>"
        '<a href="x">c</a><i>d</i><span class="t-emph evil">e</span><span style="color:rgb(232, 62, 140)">f</span>'
    )
    assert got == (
        '<b>a</b><span style="color:var(--accent);font-size:20px">b</span>cd'
        '<span class="t-emph">e</span><span style="color:#E83E8C">f</span>'
    )


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        # 編集モードの「＋」を繰り返して入れ子になった span（実際の記録）は、内側の指定が勝つ 1 つにまとめる
        (
            '<b><span style="font-size:20px"><span style="font-size:21px"><span style="font-size:33px">'
            '<span style="color:#e51010">最高峰</span></span></span></span></b>',
            '<b><span style="font-size:33px;color:#e51010">最高峰</span></b>',
        ),
        (
            '<span class="t-emph b" style="color:#fff;font-size:20px"><span class="t-accent" style="font-weight:400">'
            "x</span></span>",
            '<span class="t-accent" style="font-size:20px;font-weight:400">x</span>',
        ),
        # 中に文字が並ぶ入れ子はまとめない
        (
            '<span style="font-size:20px">a<span style="font-size:22px">b</span></span>',
            '<span style="font-size:20px">a<span style="font-size:22px">b</span></span>',
        ),
    ],
    ids=["繰り返し入れ子", "クラスと指定の入れ子", "文字が並ぶ入れ子は残す"],
)
def test_入れ子のspanをまとめる(src, expected):
    assert fragedit.sanitize_inline(src) == expected


# ---- 1 件の反映 ----


def test_対象だけが変わる():
    src = '<div class="pp-text">旧</div>\n<div class="pp-text">残</div>'
    assert (
        fragedit.apply_edit(src, {"t": "t0", "after": "新<br>題"})
        == '<div class="pp-text">新<br>題</div>\n<div class="pp-text">残</div>'
    )


def test_空に直せて実体参照はそのまま入る():
    assert (
        fragedit.apply_edit('<div class="pp-text">旧</div>', {"t": "t0", "after": ""}) == '<div class="pp-text"></div>'
    )
    assert (
        fragedit.apply_edit('<div class="pp-text">旧</div>', {"t": "t0", "after": "&lt;&amp;"})
        == '<div class="pp-text">&lt;&amp;</div>'
    )


def test_存在しない対象はValueErrorにする():
    with pytest.raises(ValueError, match="t7"):
        fragedit.apply_edit('<div class="pp-text">x</div>', {"t": "t7", "after": "y"})


CHART = (
    '<div class="pp-chart" data-chart=\'{"type":"bar","categories":["A","B"],'
    '"series":[{"name":"費用","values":[1,2]}]}\'></div>'
)


def test_グラフの分類名と系列名を直せる():
    got = fragedit.apply_edit(CHART, {"t": "c0.cat1", "after": "B'案"})
    assert got == CHART.replace('"B"', '"B&#39;案"')
    got = fragedit.apply_edit(CHART, {"t": "c0.ser0", "after": "総額"})
    assert got == CHART.replace('"費用"', '"総額"')


def test_二重引用符の属性のグラフでは引用符をエスケープする():
    src = '<div class="pp-chart" data-chart="{&quot;categories&quot;:[&quot;A&quot;],&quot;series&quot;:[]}"></div>'
    got = fragedit.apply_edit(src, {"t": "c0.cat0", "after": 'x"y'})
    assert (
        got == '<div class="pp-chart" data-chart="{&quot;categories&quot;:[&quot;x\\&quot;y&quot;],'
        '&quot;series&quot;:[]}"></div>'
    )


# ---- before の照合 ----


def edit_text(inner, before, after="新"):
    return fragedit.apply_edit(f'<div class="pp-text">{inner}</div>', {"t": "t0", "before": before, "after": after})


def test_beforeと現在の文字が違えば両方を示してValueErrorにする():
    with pytest.raises(ValueError, match="現在の文") as e:
        edit_text("現在の文", "別の文")
    assert "別の文" in str(e.value)
    assert "現在の文" in str(e.value)


@pytest.mark.parametrize(
    ("inner", "before"),
    [
        ("A &amp; B<br>C", "A & B<br>C"),
        ("1 &lt; 2", "1 &lt; 2"),
        ("<b>太</b>字", "太字"),
        ('<span class="t-accent">色</span>\n付き', "色 付き"),
        ("a\n  b", "a b"),
    ],
    ids=["実体参照", "lt", "タグ", "空白とタグ", "改行と空白"],
)
def test_タグ_空白_実体参照の違いは不一致にしない(inner, before):
    assert edit_text(inner, before) == '<div class="pp-text">新</div>'


def test_beforeがなければ照合しない():
    assert (
        fragedit.apply_edit('<div class="pp-text">旧</div>', {"t": "t0", "after": "新"})
        == '<div class="pp-text">新</div>'
    )


def test_グラフのラベルもbeforeと一致すれば直せ違えば断る():
    src = (
        '<div class="pp-chart" data-chart=\'{"categories":["A","B"],"series":[{"name":"費用","values":[1,2]}]}\'></div>'
    )
    assert fragedit.apply_edit(src, {"t": "c0.cat1", "before": "B", "after": "X"}) == src.replace('"B"', '"X"')
    assert fragedit.apply_edit(src, {"t": "c0.ser0", "before": "費用", "after": "X"}) == src.replace('"費用"', '"X"')
    with pytest.raises(ValueError, match="Z"):
        fragedit.apply_edit(src, {"t": "c0.cat1", "before": "Z", "after": "X"})


def test_回答の編集でbeforeが違えば反映せずskippedに載せ断片を残す(tmp_path):
    (tmp_path / "slides").mkdir()
    (tmp_path / "slides" / "01-A.html").write_text('<div class="pp-text">変わった</div>\n', encoding="utf-8")
    ans = tmp_path / "answers-1.md"
    ans.write_text('## S01\n- 編集: {"f":"01-A","t":"t0","before":"元","after":"新"}\n', encoding="utf-8")
    r = fragedit.apply_answers(tmp_path, ans)
    assert r["applied"] == []
    assert len(r["skipped"]) == 1
    assert "元の文字" in r["skipped"][0]["reason"]
    assert (tmp_path / "slides" / "01-A.html").read_text(encoding="utf-8") == '<div class="pp-text">変わった</div>\n'


# ---- 回答 md の解析と反映 ----

MD = """# 回答
## S01
- 編集: {"f":"01-A","t":"t0","before":"旧A","after":"新A"}
- 編集: {"f":"01-B","t":"t0","before":"旧B","after":"新B"}
- 編集: {"f":"01-A","t":"t9","before":"","after":"範囲外"}
- 編集: {壊れている
"""


def test_回答mdの編集行を解析し壊れた行をproblemsに載せる():
    edits, problems = fragedit.parse_edits(MD)
    assert edits == [
        {"slide": "01", "f": "01-A", "t": "t0", "before": "旧A", "after": "新A"},
        {"slide": "01", "f": "01-B", "t": "t0", "before": "旧B", "after": "新B"},
        {"slide": "01", "f": "01-A", "t": "t9", "before": "", "after": "範囲外"},
    ]
    assert len(problems) == 1
    assert fragedit.has_unapplied(MD) is True


def test_回答の編集を断片へ反映し版を残してfinal_htmlを消す(tmp_path):
    (tmp_path / "slides").mkdir()
    for n, v in (("01-A", "旧A"), ("01-B", "旧B")):
        (tmp_path / "slides" / f"{n}.html").write_text(f'<div class="pp-text">{v}</div>\n', encoding="utf-8")
    (tmp_path / "final.html").write_text("x", encoding="utf-8")
    ans = tmp_path / "answers-1.md"
    ans.write_text(MD, encoding="utf-8")
    r = fragedit.apply_answers(tmp_path, ans)
    assert len(r["applied"]) == 2
    assert len(r["skipped"]) == 2  # 範囲外の対象と壊れた行
    assert r["snapshot"] == 1
    assert (tmp_path / "slides" / "01-A.html").read_text(encoding="utf-8") == '<div class="pp-text">新A</div>\n'
    assert (tmp_path / "slides" / "01-B.html").read_text(encoding="utf-8") == '<div class="pp-text">新B</div>\n'
    assert "旧A" in (tmp_path / "history" / "001" / "01-A.html").read_text(encoding="utf-8")
    assert not (tmp_path / "final.html").exists()
    assert fragedit.has_unapplied(ans.read_text(encoding="utf-8")) is False
