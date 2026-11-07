"""案の選択ページの「文字サイズ」欄（Chromium を起動するので slow）。"""

# ruff: noqa: S101  # pytest の assert
import pytest
from pptx_deck import fontsize, initdir, variants

pytestmark = pytest.mark.slow

FRAG = (
    '<section class="slide" data-layout="content" data-variant="{n}｜理由" style="position:relative;width:1280px;'
    'height:720px">'
    '<div class="pp-text" data-role="title" style="position:absolute;left:64px;top:30px;width:900px;height:60px">'
    "題{n}</div></section>"
)
BIG = '.pane[data-slide="01"] .big [data-role="title"]'


@pytest.fixture
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        b = pw.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def work(tmp_path):
    w = tmp_path / "out" / "pptx-deck-source" / "deck"
    initdir.init(w, color="navy")
    for nn in ("01", "02"):
        for k in ("A", "B"):
            (w / "slides" / f"{nn}-{k}.html").write_text(FRAG.replace("{n}", nn + k), encoding="utf-8")
    return w


@pytest.fixture
def open_page(browser, work):
    pages = []

    def _open():
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        pages.append(page)
        page.goto(variants.assemble(work, 1).as_uri())
        return page

    yield _open
    for p in pages:
        p.close()


def answers(page):
    """スライド 1 を要修正にして回答を書き出す。"""
    page.fill('.pane[data-slide="01"] .cm', "x")
    page.click('.pane[data-slide="01"] .verdict .ng')
    page.click('#nav button[data-go="01"]')
    page.evaluate("window.__answersMd = ''")
    page.click('.pane[data-slide="01"] .copyBtn')
    return page.evaluate("window.__answersMd")


def test_panel_present(open_page):
    page = open_page()
    assert page.locator("input[data-fs]").count() == len(fontsize.ITEMS)
    assert page.input_value('input[data-fs="title"]') == "37"
    assert page.input_value('input[data-fs="num-scale"]') == "1"


def test_change_applies_live(open_page):
    page = open_page()
    page.locator("details.rv-fs > summary").click()
    page.fill('input[data-fs="title"]', "45")
    assert page.evaluate("s => getComputedStyle(document.querySelector(s)).fontSize", BIG) == "45px"


def test_clamped_in_page(open_page):
    page = open_page()
    page.locator("details.rv-fs > summary").click()
    page.fill('input[data-fs="body"]', "5")
    page.press('input[data-fs="body"]', "Tab")
    assert page.input_value('input[data-fs="body"]') == "19"


def test_answer_line_only_when_changed(open_page):
    page = open_page()
    assert "文字サイズ" not in answers(page)
    page.locator("details.rv-fs > summary").click()
    page.fill('input[data-fs="title"]', "45")
    page.fill('input[data-fs="num-scale"]', "1.2")
    page.click('.pane[data-slide="01"] .copyBtn')
    assert "- 文字サイズ: title=45 num-scale=1.2\n" in page.evaluate("window.__answersMd")


def test_reset_button(open_page):
    page = open_page()
    page.locator("details.rv-fs > summary").click()
    page.fill('input[data-fs="title"]', "45")
    page.click(".rv-fs-reset")
    assert page.input_value('input[data-fs="title"]') == "37"
    assert page.evaluate("s => getComputedStyle(document.querySelector(s)).fontSize", BIG) == "37px"
    assert "文字サイズ" not in answers(page)


def test_initial_from_cfg(work, open_page):
    initdir.set_font_size(work, {"title": 40})
    page = open_page()
    assert page.input_value('input[data-fs="title"]') == "40"
    assert "文字サイズ" not in answers(page)
