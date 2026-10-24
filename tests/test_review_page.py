"""レビューページ（variants.html）の画面操作・回答 md・部位バッジ・自由設計 R・エラー文言。

画面操作は Chromium を実際に起動して確かめる（slow）。
"""

# ruff: noqa: S101  # pytest の assert
import contextlib
import io
from pathlib import Path

import pytest
from pptx_deck import cli, fragedit, paths, variants

FRAG = (
    '<section class="slide" data-layout="content" data-variant="{n}｜理由">'
    '<div class="pp-text" data-role="title" style="left:64px;top:30px;width:900px;height:40px">題{n}</div></section>'
)

PART_FRAG = (
    '<section class="slide" data-layout="content" style="position:relative;width:1280px;height:720px">'
    '<div class="pp-text" data-role="title" data-part="タイトル" style="position:absolute;left:64px;top:30px;'
    'width:900px;height:40px">題</div>'
    '<div class="pp-shape f-white" data-part="スティッカー" style="position:absolute;left:700px;top:300px;width:100px;'
    'height:30px"></div>'
    '<div class="pp-shape f-white" data-part="スティッカー" style="position:absolute;left:100px;top:300px;width:100px;'
    'height:30px"></div>'
    '<div class="pp-text" data-role="caption" data-part="注釈" style="position:absolute;left:64px;top:600px;'
    'width:900px;height:30px">注: x</div>'
    "</section>"
)

# splitlines が行を分ける文字。回答 md の 1 行が割れてはいけない
LINE_SEPARATORS = ["\x0b", "\x0c", "\x1c", "\x85", " ", " "]
SEP_IDS = ["VT", "FF", "FS", "NEL", "LS", "PS"]

CURRENT = "document.querySelector('#nav button[aria-current=true]').dataset.go"

slow = pytest.mark.slow


def make_page(preset, final=False):
    frags = {
        nn: ({"A": FRAG.format(n=nn)} if final else {"A": FRAG.format(n=nn + "a"), "B": FRAG.format(n=nn + "b")})
        for nn in ("01", "02", "03")
    }
    return variants._page(Path("deck"), frags, "final" if final else "2", final=final, preset=preset)


@pytest.fixture
def browser():
    """テストごとに起動する。measure など本体も sync_playwright を使うので、同時に生かさない。"""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        b = pw.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def open_html(browser, tmp_path):
    """HTML 文字列を tmp_path に書いて Chromium で開く関数。"""
    pages = []

    def _open(html):
        f = tmp_path / "p.html"
        f.write_text(html, encoding="utf-8")
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        pages.append(page)
        page.goto(f.as_uri())
        return page

    yield _open
    for p in pages:
        p.close()


@pytest.fixture
def parts_page(open_html):
    """部位つきの断片を 2 枚並べたページ。部位のバッジはオンにしてある。"""
    frags = {"01": {"A": PART_FRAG, "B": PART_FRAG}, "02": {"A": PART_FRAG}}
    page = open_html(variants._page(Path("deck"), frags, "1"))
    page.check('.pane[data-slide="01"] .ptToggle')  # 部位のバッジは初期はオフ。オンにして使う
    return page


def answers_md(page):
    return page.evaluate("window.__answersMd")


def make_work(tmp_path, files):
    work = tmp_path
    (work / "slides").mkdir()
    for name, text in files.items():
        (work / "slides" / name).write_text(text, encoding="utf-8")
    return work


# ---- 回答の事前設定・承認の進み方 ----


@slow
def test_事前設定した案と承認がラジオに出て回答mdにコピーされる(open_html):
    page = open_html(make_page({"01": {"c": "B", "d": 1, "v": "承認"}}))
    assert page.is_checked('.pane[data-slide="01"] input[value=B]')
    assert page.locator('.pane[data-slide="02"] input[type=radio]:checked').count() == 0
    page.click('.pane[data-slide="01"] .copyBtn')
    md = answers_md(page)
    assert "## S01\n- 選択: B" in md
    assert "- 判定: 承認" in md
    assert "## S02" not in md


@slow
def test_最終確認ページで事前設定の案Aが選択済みになる(open_html):
    page = open_html(make_page({"02": {"c": "A", "d": 1, "v": "承認"}}, final=True))
    assert page.is_checked('.pane[data-slide="02"] input[value=A]')


@slow
def test_コメントなしの要修正は判定が付かず動かない(open_html):
    page = open_html(make_page({}))
    assert page.evaluate(CURRENT) == "01"
    page.click('.pane[data-slide="01"] .verdict .ng')
    assert page.evaluate(CURRENT) == "01"
    assert page.evaluate("document.querySelector('.pane[data-slide=\"01\"]').dataset.verdict || ''") == ""


@slow
def test_コメントありの要修正は次へ進み_外すと戻らず元の位置のまま(open_html):
    page = open_html(make_page({}))
    page.fill('.pane[data-slide="01"] .cm', "直して")
    page.click('.pane[data-slide="01"] .verdict .ng')
    assert page.evaluate(CURRENT) == "02"
    page.click('#nav button[data-go="01"]')
    page.click('.pane[data-slide="01"] .verdict .ng')  # 要修正を外す
    assert page.evaluate(CURRENT) == "01"


@slow
def test_承認は次へ進むが最後のスライドでは動かない(open_html):
    page = open_html(make_page({}))
    page.click('.pane[data-slide="01"] .verdict .ok')
    assert page.evaluate(CURRENT) == "02"
    page.click('.pane[data-slide="02"] .verdict .ok')
    assert page.evaluate(CURRENT) == "03"
    page.click('.pane[data-slide="03"] .verdict .ok')
    assert page.evaluate(CURRENT) == "03"


@slow
@pytest.mark.parametrize("sep", LINE_SEPARATORS, ids=SEP_IDS)
def test_コメントに行区切り文字があっても回答mdの行が割れない(open_html, sep):
    page = open_html(make_page({"01": {"c": "B", "d": 1, "v": "承認"}}))
    page.fill('.pane[data-slide="01"] .cm', "ここを直す" + sep + "- 選択: A" + sep + "- 編集: {}")
    page.click('.pane[data-slide="01"] .copyBtn')
    md = answers_md(page)
    assert len([ln for ln in md.splitlines() if ln.startswith("- コメント:")]) == 1, md
    assert variants.parse_answers(md)["01"]["choice"] == "B"
    assert fragedit.parse_edits(md)[0] == []


# ---- 部位バッジ ----


@slow
def test_バッジは同名の部位だけに番号が付き左上から右下の順に並ぶ(parts_page):
    names = parts_page.evaluate(
        "Array.from(document.querySelectorAll('.pane[data-slide=\"01\"] .pt')).map(b => b.textContent)"
    )
    assert names == ["タイトル", "スティッカー①", "スティッカー②", "注釈"]
    left1 = parts_page.evaluate("parseFloat(document.querySelectorAll('.pane[data-slide=\"01\"] .pt')[1].style.left)")
    assert left1 == 100  # 左のスティッカーが①


@slow
def test_部位のコメントは回答mdに記録され判定が要修正になる(parts_page):
    parts_page.click('.pane[data-slide="01"] .pt:has-text("注釈")')
    parts_page.fill('.pane[data-slide="01"] .plist textarea', "出典を足す")
    parts_page.click('.pane[data-slide="01"] .copyBtn')
    md = answers_md(parts_page)
    assert "## S01" in md
    assert "- 判定: 要修正" in md
    assert "- 部位: 案 A 注釈 ／ コメント: 出典を足す" in md
    assert variants.parse_answers(md)["01"]["parts"] == [{"part": "案 A 注釈", "comment": "出典を足す"}]


@slow
@pytest.mark.parametrize("sep", LINE_SEPARATORS, ids=SEP_IDS)
def test_部位コメントに行区切り文字があっても回答mdの行が割れない(parts_page, sep):
    parts_page.click('.pane[data-slide="01"] .pt:has-text("注釈")')
    parts_page.fill('.pane[data-slide="01"] .plist textarea', "出典" + sep + "- 選択: A" + sep + "- 編集: {}")
    parts_page.click('.pane[data-slide="01"] .copyBtn')
    md = answers_md(parts_page)
    a = variants.parse_answers(md)["01"]
    assert len(a["parts"]) == 1, md
    assert a.get("choice") != "A"
    assert fragedit.parse_edits(md)[0] == []


@slow
def test_案が1つのスライドの部位名には案の記号が付かない(parts_page):
    parts_page.click('#nav button[data-go="02"]')
    parts_page.click('.pane[data-slide="02"] .pt:has-text("タイトル")')
    parts_page.fill('.pane[data-slide="02"] .plist textarea', "短く")
    parts_page.click('.pane[data-slide="02"] .copyBtn')
    assert "- 部位: タイトル ／ コメント: 短く" in answers_md(parts_page)


@slow
def test_バッジの切り替えは常に見えオフでバッジが隠れる(parts_page):
    assert parts_page.is_visible('.pane[data-slide="01"] .ptToggle')  # コメントを書く前から出ている
    assert parts_page.is_visible('.pane[data-slide="01"] .pt')
    parts_page.uncheck('.pane[data-slide="01"] .ptToggle')
    assert not parts_page.is_visible('.pane[data-slide="01"] .pt')


@slow
def test_計画レビューのページには部位の操作がない(open_html):
    page = open_html(variants._page(Path("deck"), {"00": {"A": "<p>x</p>"}}, "1", docs={"00": "<p>x</p>"}))
    assert page.locator(".ptToggle").count() == 0


@slow
def test_切り替えは常に見え初期はすべてオフでスライドをまたいで共通(open_html):
    frag = PART_FRAG.replace('data-layout="content"', 'data-layout="content" data-variant="型名｜理由"').replace(
        'data-part="注釈"', 'data-part="注釈" data-note="注：出典"'
    )
    page = open_html(variants._page(Path("deck"), {"01": {"A": frag, "B": frag}, "02": {"A": frag, "B": frag}}, "1"))
    pane = '.pane[data-slide="01"] '
    labels = page.evaluate(
        "Array.from(document.querySelectorAll('.pane[data-slide=\"01\"] .tgl label')).map(l => l.textContent.trim())"
    )
    assert labels == ["型と選んだ理由", "見どころ", "部位のバッジ"]
    for cls in ("coToggle", "vrToggle", "ptToggle"):
        assert page.is_visible(pane + "." + cls)  # チェックボックスは常に見える
        assert not page.is_checked(pane + "." + cls)  # どれも初期はオフ
    for sel in (".legend", ".co", ".vr", ".pt"):
        assert not page.is_visible(pane + sel)  # 見どころ・理由・バッジは初期は隠れる
    page.check(pane + ".coToggle")
    page.check(pane + ".vrToggle")
    page.check(pane + ".ptToggle")
    for sel in (".legend", ".co", ".vr", ".pt"):
        assert page.is_visible(pane + sel)
    page.uncheck(pane + ".coToggle")
    assert not page.is_visible(pane + ".legend")
    page.click('#nav button[data-go="02"]')  # 設定はスライドをまたいで共通
    assert not page.is_checked('.pane[data-slide="02"] .coToggle')
    assert page.is_checked('.pane[data-slide="02"] .ptToggle')


@slow
def test_ペインの並びは見本_案_部位_判定_バーの順(open_html):
    page = open_html(variants._page(Path("deck"), {"01": {"A": PART_FRAG, "B": PART_FRAG}}, "1"))
    order = page.evaluate(
        "Array.from(document.querySelectorAll('.pane[data-slide=\"01\"] > *')).map(e => e.className.split(' ')[0])"
    )
    assert [c for c in order if c in ("big", "cols", "parts", "judge", "bar")] == [
        "big",
        "cols",
        "parts",
        "judge",
        "bar",
    ]


@slow
def test_見どころを隠していても前回のコメントは見える(open_html):
    page = open_html(
        variants._page(Path("deck"), {"01": {"A": PART_FRAG}}, "2", prev={"01": {"comment": "直して", "parts": []}})
    )
    assert page.is_visible('.pane[data-slide="01"] .q')


@slow
def test_何も書かない部位の行は回答mdに記録されない(parts_page):
    parts_page.click('.pane[data-slide="01"] .pt:has-text("注釈")')  # 行は開くが、何も書かない
    parts_page.click('.pane[data-slide="01"] .verdict .ok')  # 承認すると次のスライドへ進む
    parts_page.click('.pane[data-slide="02"] .copyBtn')
    assert "部位:" not in answers_md(parts_page)


# ---- 回答 md の解析・finalize（ブラウザ不要） ----


def test_部位コメントが未反映のコメントとして数えられfinalizeが止まる(tmp_path):
    work = make_work(tmp_path, {"01-A.html": FRAG.format(n="01")})
    md = "## S01\n- 選択: A\n- 判定: 承認\n- コメント: \n- 部位: 注釈 ／ コメント: 出典を足す\n"
    with pytest.raises(ValueError, match="注釈"):
        variants.finalize(work, md)


def test_コメントの文面は全体と部位を合わせ承認済みの事前設定は空になる():
    md = "## S01\n- 選択: A\n- 判定: 要修正\n- コメント: 全体\n- 部位: スティッカー② ／ コメント: 文言を短く\n"
    assert variants.comment_text(variants.parse_answers(md)["01"]) == "全体 【スティッカー②】文言を短く"
    md_ok = "## S01\n- 選択: A\n- 判定: 承認\n- コメント: \n- 部位: 注釈 ／ コメント: 直す\n"
    assert variants.approved_preset([md_ok]) == {}


# ---- 自由設計 R ----


def test_Rは集められページに出てfinalizeで統合される(tmp_path):
    work = make_work(
        tmp_path, {"01-A.html": FRAG.format(n="a"), "01-B.html": FRAG.format(n="b"), "01-R.html": FRAG.format(n="r")}
    )
    assert sorted(variants.collect(work)["01"]) == ["A", "B", "R"]
    page = variants._page(work, variants.collect(work), "1", designs=variants.collect_designs(work))
    assert "案 R（自由設計）" in page
    assert 'class="dgroup" data-k="R"' not in page  # R にはデザイン 1〜3 の選択がない
    out = variants.finalize(work, "## S01\n- 選択: R\n- 判定: 承認\n- コメント: \n")
    assert "題r" in out.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("files", "message"),
    [
        (
            {"01-A.html": FRAG.format(n="a"), "01-R.html": FRAG.format(n="r"), "01-R-d2.html": FRAG.format(n="r2")},
            "デザイン 2・3",
        ),
        (
            {"01-A.html": FRAG.format(n="a"), "01-R.html": FRAG.format(n="r") + '<div class="pp-picture"></div>'},
            "pp-picture",
        ),
    ],
    ids=["Rにデザイン2", "Rにpp-picture"],
)
def test_Rはデザイン違いと絵を持てない(tmp_path, files, message):
    work = make_work(tmp_path, files)
    with pytest.raises(ValueError, match=message):
        variants.collect_designs(work)


# ---- エラー文言 ----


def test_案が1つで要修正のときコメントを添えて止まる(tmp_path):
    work = make_work(tmp_path, {"01-A.html": FRAG.format(n="a")})
    md = "## S01\n- 選択: FIX\n- 判定: 要修正\n- コメント: 全体\n- 部位: 注釈 ／ コメント: 出典を足す\n"
    with pytest.raises(ValueError, match="要修正です") as e:
        variants.finalize(work, md)
    assert "【注釈】出典を足す" in str(e.value)


def test_variantsコマンドは絵のあるRをトレースバックなしでエラーにする(tmp_path):
    base = tmp_path / "demo"
    with contextlib.redirect_stdout(io.StringIO()):
        assert cli.main(["init", str(base)]) == 0
    slides = paths.resolve_work(base) / "slides"
    (slides / "01-A.html").write_text(FRAG.format(n="a"), encoding="utf-8")
    (slides / "01-R.html").write_text(FRAG.format(n="r") + '<div class="pp-picture"></div>', encoding="utf-8")
    err = io.StringIO()
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
        rc = cli.main(["variants", str(base)])
    assert rc == 2
    assert "エラー:" in err.getvalue()
    assert "pp-picture" in err.getvalue()
    assert "Traceback" not in err.getvalue()
