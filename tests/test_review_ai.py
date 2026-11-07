"""レビューページの「AI に頼む」（切り替え・バッジ・部位の行）。

画面操作は Chromium を実際に起動して確かめる（slow）。
"""

# ruff: noqa: S101  # pytest の assert
from pathlib import Path

import pytest
from pptx_deck import variants

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


@pytest.fixture
def browser():
    """テストごとに起動する。"""
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
def ai_page(open_html):
    """部位つきの断片を 2 枚並べたページ。「AI に頼む」はオンにしてある。"""
    frags = {"01": {"A": PART_FRAG, "B": PART_FRAG}, "02": {"A": PART_FRAG}}
    page = open_html(variants._page(Path("deck"), frags, "1"))
    page.check('.pane[data-slide="01"] .ptToggle')  # 初期はオフ。オンにして使う
    return page


def test_切り替えは見どころとAIに頼むの2つ(ai_page):
    labels = ai_page.evaluate(
        "Array.from(document.querySelectorAll('.pane[data-slide=\"01\"] .tgl label')).map(l => l.textContent.trim())"
    )
    assert labels == ["見どころ", "AI に頼む"]


def test_バッジは紫で部位名を含む(ai_page):
    texts = ai_page.evaluate(
        "Array.from(document.querySelectorAll('.pane[data-slide=\"01\"] .pt')).map(b => b.textContent)"
    )
    assert texts == [
        "✦ AI に頼む：タイトル",
        "✦ AI に頼む：スティッカー①",
        "✦ AI に頼む：スティッカー②",
        "✦ AI に頼む：注釈",
    ]
    bg = ai_page.evaluate("getComputedStyle(document.querySelector('.pane[data-slide=\"01\"] .pt')).backgroundColor")
    assert bg == "rgb(106, 63, 181)"
