"""要修正のまま再読み込みしても、大きな表示が空にならない（Chromium を起動するので slow）。

「要修正」のラジオ（値 FIX）は案ではない。復元された FIX を表示する案のキーに使うと、大きな表示が真っ白になる。
"""

# ruff: noqa: S101  # pytest の assert
import pytest
from pptx_deck import initdir, variants

pytestmark = pytest.mark.slow

FRAG = (
    '<section class="slide" data-layout="content" data-variant="{n}｜理由" style="position:relative;width:1280px;'
    'height:720px">'
    '<div class="pp-text" data-role="title" style="position:absolute;left:64px;top:30px;width:900px;height:60px">'
    "題{n}</div></section>"
)
PANE = '.pane[data-slide="01"]'


@pytest.fixture
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        b = pw.chromium.launch()
        yield b
        b.close()


def make_work(tmp_path, cases):
    w = tmp_path / "out" / "pptx-deck-source" / "deck"
    initdir.init(w, color="navy")
    for k in cases:
        (w / "slides" / f"01-{k}.html").write_text(FRAG.replace("{n}", "01" + k), encoding="utf-8")
    return w


def big_title(page):
    return page.evaluate(f"""() => {{ const t = document.querySelector('{PANE} .big [data-role="title"]');
      return t ? t.textContent : null; }}""")


def test_big_view_survives_reload_with_fix_selected(browser, tmp_path):
    """FIX のラジオがあるのは、案が 1 つのスライド（採用／要修正）と最終確認のページだけ。"""
    work = make_work(tmp_path, ("A",))
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    page.goto(variants.assemble(work, 1).as_uri())
    assert big_title(page) == "題01A"
    page.fill(f"{PANE} .cm", "直したい")
    page.click(f"{PANE} .verdict .ng")  # 要修正: ラジオは FIX になる
    assert page.evaluate(f"document.querySelector('{PANE} input[type=radio][value=FIX]').checked")
    page.reload()
    assert page.evaluate(f"document.querySelector('{PANE} input[type=radio][value=FIX]').checked")  # 復元された
    assert big_title(page) == "題01A"
    page.close()
