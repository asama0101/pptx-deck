"""配色の切り替え（variants.html）と、finalize・set-color への反映。

画面操作は Chromium を実際に起動して確かめる（slow）。
"""

# ruff: noqa: S101  # pytest の assert
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from pptx_deck import cli, initdir, theme, variants

SPEC = '{"type":"bar","categories":["A","B"],"series":[{"name":"費用","values":[3,5]}]}'
FRAG = (
    '<section class="slide" data-layout="content" data-variant="{n}｜理由" style="position:relative;width:1280px;'
    'height:720px">'
    '<div class="pp-text" data-role="title" style="position:absolute;left:64px;top:30px;width:900px;height:40px;'
    'color:var(--accent)">題{n}</div>'
    '<div class="pp-chart" data-chart=\''
    + SPEC
    + '\' style="position:absolute;left:64px;top:340px;width:900px;height:300px"></div>'
    "</section>"
)
MD_HEAD = "---\nround: 1\n---\n"

NAVY, GREEN, GRAY = "#1F3A5F", "#1E6B52", "#3A3F47"  # theme.PRESETS の値（仕様として固定）

slow = pytest.mark.slow


def cfg(work: Path) -> dict:
    return json.loads((work / "template.json").read_text(encoding="utf-8"))


def color_of(work: Path) -> str:
    return cfg(work)["color"]


# ---- 配色の選択肢 ----


def test_template_jsonがないとき選択肢はプリセット3色で初期値はnavy(tmp_path):
    opts, init = variants._scheme_options(tmp_path)
    assert init == "navy"
    assert list(opts) == ["navy", "green", "gray"]
    assert opts["green"]["accent"] == GREEN


def test_プリセット外の色は末尾の選択肢に足され初期値になる(tmp_path):
    (tmp_path / "template.json").write_text(json.dumps({"color": "#123456"}), encoding="utf-8")
    opts, init = variants._scheme_options(tmp_path)
    assert init == "#123456"
    assert list(opts) == ["navy", "green", "gray", "#123456"]
    assert opts["#123456"]["accent"] == "#123456"


def test_プリセットと同じ色は名前で初期値になり選択肢は増えない(tmp_path):
    (tmp_path / "template.json").write_text(json.dumps({"color": GREEN}), encoding="utf-8")
    opts, init = variants._scheme_options(tmp_path)
    assert init == "green"
    assert list(opts) == ["navy", "green", "gray"]


# ---- 回答の「- 配色:」「- 出力形式:」の解析 ----


@pytest.mark.parametrize(
    ("mds", "expected"),
    [
        ([MD_HEAD + "- 配色: green\n- 出力形式: html\n## S01\n- 選択: A\n"], {"color": "green", "format": "html"}),
        (
            [MD_HEAD + "- 配色: green\n- 出力形式: html\n## S01\n- 選択: A\n", MD_HEAD + "- 配色: #123456\n"],
            {"color": "#123456", "format": "html"},
        ),  # 後の回が配色だけ上書きし、形式は前の回が残る
        ([MD_HEAD], {"color": None, "format": None}),
        ([MD_HEAD + "- 出力形式: xls\n"], {"color": None, "format": None}),  # 未知の形式は無視
    ],
    ids=["1回", "後勝ち", "設定なし", "未知の形式"],
)
def test_parse_settings(mds, expected):
    assert variants.parse_settings(mds) == expected


# ---- set-color / 回答からの反映 ----


@pytest.fixture
def navy_work(tmp_path):
    base = tmp_path / "deck"
    initdir.init(base, color="navy")
    return SimpleNamespace(base=base, work=base / "source")


def test_set_colorはtemplate_jsonとtheme_cssを書き換え不正な色では何も変えない(navy_work):
    work = navy_work.work
    initdir.set_color(work, "green")
    assert color_of(work) == GREEN
    assert f"--accent: {GREEN};" in (work / "theme.css").read_text(encoding="utf-8")
    before = ((work / "template.json").read_text(encoding="utf-8"), (work / "theme.css").read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="zzz"):
        initdir.set_color(work, "zzz")
    assert before == (
        (work / "template.json").read_text(encoding="utf-8"),
        (work / "theme.css").read_text(encoding="utf-8"),
    )


def test_回答の配色は同じ色なら何もせずPPTXがあれば見送り無ければ反映する(navy_work):
    base, work = navy_work.base, navy_work.work
    assert cli._apply_color_from_answers(work, [MD_HEAD]) == "none"
    assert cli._apply_color_from_answers(work, [MD_HEAD + "- 配色: navy\n"]) == "none"
    (base / "deck.pptx").write_bytes(b"dummy")
    assert cli._apply_color_from_answers(work, [MD_HEAD + "- 配色: green\n"]) == "skipped_pptx"
    assert color_of(work) == NAVY
    (base / "deck.pptx").unlink()
    assert cli._apply_color_from_answers(work, [MD_HEAD + "- 配色: green\n"]) == "applied"
    assert color_of(work) == GREEN


def test_PPTXがあるときの見送りは同じ色では繰り返さず新しい色は案内しPPTX削除後に反映する(navy_work):
    base, work = navy_work.base, navy_work.work
    green = [MD_HEAD + "- 配色: green\n"]
    (base / "deck.pptx").write_bytes(b"dummy")
    assert cli._apply_color_from_answers(work, green) == "skipped_pptx"
    assert cli._apply_color_from_answers(work, green) == "none"  # 同じ警告を繰り返さない
    gray = green + [MD_HEAD + "- 配色: gray\n"]
    assert cli._apply_color_from_answers(work, gray) == "skipped_pptx"  # 新しい色は案内する
    (base / "deck.pptx").unlink()
    assert cli._apply_color_from_answers(work, gray) == "applied"
    assert color_of(work) == GRAY


def test_反映済みの回答の色はset_colorのあとに再適用されず回答が変われば反映される(navy_work):
    work = navy_work.work
    green = [MD_HEAD + "- 配色: green\n"]
    assert cli._apply_color_from_answers(work, green) == "applied"
    initdir.set_color(work, "gray")
    assert cli._apply_color_from_answers(work, green) == "none"  # 同じ回答値は再適用しない
    assert color_of(work) == GRAY
    navy = green + [MD_HEAD + "- 配色: navy\n"]
    assert cli._apply_color_from_answers(work, navy) == "applied"  # 回答の値が変われば反映する
    assert color_of(work) == NAVY
    assert cfg(work)["answers_color"] == NAVY


def test_init_forceは反映済みの回答の色の記録を残す(navy_work):
    base, work = navy_work.base, navy_work.work
    green = [MD_HEAD + "- 配色: green\n"]
    assert cli._apply_color_from_answers(work, green) == "applied"
    initdir.set_color(work, "gray")
    initdir.init(base, force=True)
    assert cfg(work)["answers_color"] == GREEN
    assert cli._apply_color_from_answers(work, green) == "none"
    assert color_of(work) == GRAY


# ---- finalize を通した回答の配色と set-color の前後関係 ----


@pytest.fixture
def deck(navy_work):
    """断片 1 枚と navy の作業フォルダ。finalize・回答の書き出し・色の読み取りを持つ。"""
    base, work = navy_work.base, navy_work.work
    (work / "slides" / "01-A.html").write_text('<div class="pp-text">x</div>', encoding="utf-8")

    def answers(n, color=None):
        md = f"---\nround: {n}\n---\n" + (f"- 配色: {color}\n" if color else "") + "## S01\n- 選択: A\n- 判定: 承認\n"
        (work / f"answers-{n}.md").write_text(md, encoding="utf-8")

    def page_init(round_no):
        html = variants.assemble(work, round_no).read_text(encoding="utf-8")
        return html.split('class="rv-scheme" data-init="', 1)[1].split('"', 1)[0]

    return SimpleNamespace(base=base, work=work, answers=answers, page_init=page_init)


@pytest.fixture
def finalize(deck, capsys):
    """finalize を実行して終了コード 0 を確かめ、標準エラー出力を返す関数。"""

    def _run():
        capsys.readouterr()
        rc = cli.main(["finalize", str(deck.base)])
        captured = capsys.readouterr()
        assert rc == 0, captured.err
        return captured.err

    return _run


@pytest.fixture
def green_then_navy(deck, finalize):
    """回答 1 の green を finalize で反映したあと、set-color で navy に戻した状態。"""
    deck.answers(1, "green")
    finalize()
    assert color_of(deck.work) == GREEN
    initdir.set_color(deck.work, "navy")


def test_set_colorの色は再finalizeでも残る(deck, finalize, green_then_navy):
    finalize()
    assert color_of(deck.work) == NAVY


def test_反映済みの色を2回目の回答で選び直すと反映される(deck, finalize, green_then_navy):
    assert deck.page_init(2) == "navy"  # ページは現在の色で開く
    deck.answers(2, "green")  # 利用者がページで green を選び直した
    finalize()
    assert color_of(deck.work) == GREEN


def test_2回目の回答で配色に触れなければset_colorの色が残る(deck, finalize, green_then_navy):
    deck.answers(2)
    finalize()
    assert color_of(deck.work) == NAVY


def test_PPTXがあるときの警告は1回だけでPPTX削除後のfinalizeで反映される(deck, finalize):
    (deck.base / "deck.pptx").write_bytes(b"dummy")
    deck.answers(1, "green")
    assert "PPTX が作成済み" in finalize()
    assert "PPTX が作成済み" not in finalize()  # 同じ警告は繰り返さない
    assert color_of(deck.work) == NAVY
    (deck.base / "deck.pptx").unlink()
    finalize()
    assert color_of(deck.work) == GREEN


def test_新しい回答の色を反映したあとのset_colorは戻されない(deck, finalize, green_then_navy):
    deck.answers(2, "green")
    finalize()
    assert color_of(deck.work) == GREEN
    initdir.set_color(deck.work, "navy")
    finalize()  # answers-2 の green は反映済み。set-color を戻さない
    assert color_of(deck.work) == NAVY


def test_3回目のページは未反映の2回目の選択を引き継ぐ(deck, finalize, green_then_navy):
    deck.answers(2, "green")  # まだ finalize していない回の選択
    assert deck.page_init(3) == "green"  # 触らなければ finalize で green になるので、ページも green で開く
    deck.answers(3)
    finalize()
    assert color_of(deck.work) == GREEN


def test_init_forceのあとも回答の色の出どころが残り2回目の選択が反映される(deck, finalize, green_then_navy):
    initdir.init(deck.base, force=True)
    deck.answers(2, "green")
    finalize()
    assert color_of(deck.work) == GREEN


# ---- ページの配色セレクタ（Chromium） ----


@pytest.fixture
def browser():
    """テストごとに起動する。measure など本体も sync_playwright を使うので、同時に生かさない。"""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        b = pw.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def scheme_page(browser, tmp_path):
    """配色セレクタつきのページを開く関数。selected は前の回から引き継いだ選択。None で scheme なし。"""
    pages = []

    def _open(scheme="navy", selected=None):
        frags = {nn: {"A": FRAG.replace("{n}", nn + "a"), "B": FRAG.replace("{n}", nn + "b")} for nn in ("01", "02")}
        sch = None
        if scheme:
            opts = variants._scheme_options(tmp_path)[0]  # template.json なし → プリセット 3 色
            sch = (opts, scheme) if not selected else (opts, scheme, selected)
        (tmp_path / "theme.css").write_text(theme.theme_css(theme.derive("navy")), encoding="utf-8")
        (tmp_path / "chart-preview.js").write_text(
            (Path(variants.__file__).parent.parent / "assets" / "web" / "chart-preview.js").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        (tmp_path / "p.html").write_text(
            variants._page(Path("demo") / "source", frags, "1", scheme=sch), encoding="utf-8"
        )
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        pages.append(page)
        page.goto((tmp_path / "p.html").as_uri())
        return page

    yield _open
    for p in pages:
        p.close()


ACCENT = "getComputedStyle(document.documentElement).getPropertyValue('--accent').trim().toUpperCase()"


def copy_md(page):
    """スライド 1 を要修正にして（要修正は修正事項が要る。付けると次へ進むので戻る）回答を書き出す。"""
    if page.get_attribute('.pane[data-slide="01"] .verdict .ng', "aria-pressed") != "true":
        page.fill('.pane[data-slide="01"] .cm', "x")
        page.click('.pane[data-slide="01"] .verdict .ng')
        page.click('#nav button[data-go="01"]')
    page.evaluate("window.__answersMd = ''")
    page.click('.pane[data-slide="01"] .copyBtn')
    return page.evaluate("window.__answersMd")


@slow
def test_配色を切り替えるとスライドの色とグラフの塗りが変わる(scheme_page):
    page = scheme_page()
    big = '.pane[data-slide="01"] .big '

    def fills():
        return page.evaluate(
            "s => Array.from(document.querySelectorAll(s + ' svg [fill]')).map(e => "
            "e.getAttribute('fill').toUpperCase())",
            big + ".pp-chart",
        )

    assert page.evaluate(ACCENT) == NAVY
    before = fills()
    page.select_option(".rv-scheme", "green")
    assert page.evaluate(ACCENT) == GREEN
    assert (
        page.evaluate("s => getComputedStyle(document.querySelector(s + ' .pp-text')).color", big) == "rgb(30, 107, 82)"
    )
    after = fills()
    assert after != before
    assert GREEN in after


@slow
def test_回答mdに配色の行が出るのは初期値から変えたときだけ(scheme_page):
    page = scheme_page()
    sel = '.pane[data-slide="01"]'
    page.fill(sel + " .cm", "x")
    page.click(sel + " .verdict .ng")
    page.click('#nav button[data-go="01"]')
    page.click(sel + " .copyBtn")
    assert "- 配色:" not in page.evaluate("window.__answersMd")
    page.select_option(".rv-scheme", "green")
    page.click(sel + " .copyBtn")
    assert "---\n- 配色: green\n## S01" in page.evaluate("window.__answersMd")
    page.select_option(".rv-scheme", "navy")
    page.click(sel + " .copyBtn")
    assert "- 配色:" not in page.evaluate("window.__answersMd")


@slow
def test_引き継いだ選択で開き初期値へ戻すと行が出て後の回が勝つ(scheme_page, tmp_path):
    page = scheme_page(selected="green")
    assert page.input_value(".rv-scheme") == "green"
    assert page.evaluate(ACCENT) == GREEN
    assert "- 配色:" not in copy_md(page)  # 触らなければ行は出ない（前の回の行が有効）
    page.select_option(".rv-scheme", "navy")
    md = copy_md(page)
    assert "---\n- 配色: navy\n## S01" in md
    r1 = MD_HEAD + "- 配色: green\n"
    assert variants.parse_settings([r1, md])["color"] == "navy"
    base = tmp_path / "deck"
    initdir.init(base, color="navy")
    assert cli._apply_color_from_answers(base / "source", [r1, md]) == "none"


@slow
def test_1回目で触れなかった回答mdは配色の行を含まない完全な文面(scheme_page):
    md = copy_md(scheme_page())
    assert md == "---\ndeck: demo\nround: 1\n---\n## S01\n- 選択: \n- 判定: 要修正\n- コメント: x\n"


@slow
def test_scheme指定がなければ配色のセレクタは出ない(scheme_page):
    page = scheme_page(scheme=None)
    assert page.locator(".rv-scheme").count() == 0
