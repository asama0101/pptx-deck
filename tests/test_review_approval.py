"""レビューページ（variants.html）の承認バー: 承認・要修正・全部承認・回答のコピーの止め方。

実際に生成したページを Playwright（chromium）で開き、画面の操作と回答 md を確かめる。
"""

# ruff: noqa: S101  # pytest の assert
from pathlib import Path

import pytest
from pptx_deck import variants

CUR = "document.querySelector('#nav button[aria-current=true]').dataset.go"

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

THREE_SLIDES = {
    "01": {"A": PART_FRAG, "B": PART_FRAG},
    "02": {"A": PART_FRAG, "B": PART_FRAG},
    "03": {"A": PART_FRAG, "B": PART_FRAG},
}


@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        b = pw.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def open_page(browser, tmp_path):
    """HTML を tmp_path に書いて chromium で開く。ページはテスト後に閉じる。"""
    pages = []

    def _open(html):
        f = tmp_path / f"p{len(pages)}.html"
        f.write_text(html, encoding="utf-8")
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        pages.append(page)
        page.goto(f.as_uri())
        page.wait_for_timeout(200)  # ページの JS が保存状態を戻すのを待つ
        return page

    yield _open
    for p in pages:
        p.close()


@pytest.fixture
def deck_page(open_page):
    """3 枚（各 2 案）のレビューページを開き、1 枚目の部位バッジをオンにして返す関数。"""

    def _make(frags=None, **kw):
        page = open_page(variants._page(Path("deck"), frags or THREE_SLIDES, "1", **kw))
        page.check(pane("01", ".ptToggle"))
        return page

    return _make


@pytest.fixture
def approve_all_page(deck_page):
    """全部承認の確認用。3 枚目だけ 1 案で、1 枚目は案 A を選んだ状態。"""
    page = deck_page(
        {"01": {"A": PART_FRAG, "B": PART_FRAG}, "02": {"A": PART_FRAG, "B": PART_FRAG}, "03": {"A": PART_FRAG}}
    )
    page.check(pane("01", 'input[value="A"]'))
    return page


def pane(nn, sel=""):
    return f'.pane[data-slide="{nn}"] {sel}'.strip()


def verdict(page, nn):
    return page.evaluate(f"document.querySelector('.pane[data-slide=\"{nn}\"]').dataset.verdict || ''")


def go(page, nn):
    page.click(f'#nav button[data-go="{nn}"]')


def copied_md(page, nn):
    page.click(pane(nn, ".copyBtn"))
    return page.evaluate("window.__answersMd")


def part_comment(page, nn="01", text="出典を足す"):
    page.click(pane(nn, ".pt:has-text('注釈')"))
    page.fill(pane(nn, ".plist textarea"), text)


def has_class(page, selector, cls):
    return page.evaluate(f"document.querySelector('{selector}').classList.contains('{cls}')")


def test_前へ次へのボタンはなく承認で次へ進み左の一覧で移動できる(deck_page):
    page = deck_page()
    assert page.evaluate("document.querySelectorAll('.prev, .next').length") == 0
    page.click(pane("01", ".verdict .ok"))
    assert page.evaluate(CUR) == "02"
    go(page, "03")
    assert page.evaluate(CUR) == "03"


def test_コメントありの要修正は判定が付いて次へ進み回答mdに出る(deck_page):
    page = deck_page()
    page.fill(pane("01", ".cm"), "直して")
    page.click(pane("01", ".verdict .ng"))
    assert page.evaluate(CUR) == "02"
    page.click(pane("02", ".verdict .ok"))
    md = copied_md(page, "03")
    assert "## S01\n- 選択: \n- 判定: 要修正\n- コメント: 直して" in md


def test_部位コメントだけの自動の要修正は動かず一回押すと確定して進む(deck_page):
    page = deck_page()
    part_comment(page)
    assert page.evaluate(CUR) == "01"
    page.click(pane("01", ".verdict .ng"))
    assert verdict(page, "01") == "要修正"
    assert page.evaluate(CUR) == "02"
    page.click(pane("02", ".verdict .ok"))
    md = copied_md(page, "03")
    assert "## S01\n- 選択: \n- 判定: 要修正\n- コメント: \n- 部位: 案 A 注釈 ／ コメント: 出典を足す" in md


def test_確定した要修正はもう一度押すと外れて動かない(deck_page):
    page = deck_page()
    part_comment(page)
    page.click(pane("01", ".verdict .ng"))
    go(page, "01")
    page.click(pane("01", ".verdict .ng"))
    assert verdict(page, "01") == ""
    assert page.evaluate(CUR) == "01"


def test_読み込み直しても自動の要修正は一回で確定する(deck_page):
    page = deck_page()
    part_comment(page)
    page.reload()
    page.wait_for_timeout(200)
    assert verdict(page, "01") == "要修正"
    page.click(pane("01", ".verdict .ng"))
    assert verdict(page, "01") == "要修正"
    assert page.evaluate(CUR) == "02"


def test_自動の要修正から承認に変えると印が消え手で付けた要修正はもう一度で外れる(deck_page):
    page = deck_page()
    part_comment(page)
    page.click(pane("01", ".verdict .ok"))
    go(page, "01")
    page.click(pane("01", ".verdict .ng"))
    go(page, "01")
    page.click(pane("01", ".verdict .ng"))
    assert verdict(page, "01") == ""


def test_コメントだけで判定のないスライドがあると回答のコピーが止まりそのスライドへ戻る(deck_page):
    page = deck_page()
    page.click(pane("01", ".verdict .ng"))
    page.fill(pane("01", ".cm"), "直してほしい")
    go(page, "02")
    page.click(pane("02", ".verdict .ok"))
    assert copied_md(page, "03") is None
    assert page.evaluate("!!window.__submitted") is False
    assert page.evaluate(CUR) == "01"
    st = pane("01", ".state")
    assert "S01 にコメントがありますが、承認か要修正が押されていません" in page.inner_text(st)
    assert has_class(page, st, "rv-warn")


def test_部位コメントだけで判定のないスライドがあると回答のコピーが止まる(deck_page):
    page = deck_page()
    part_comment(page)
    page.click(pane("01", ".clear"))
    page.click(pane("01", ".copyBtn"))
    assert page.evaluate("!!window.__submitted") is False
    assert "承認か要修正が押されていません" in page.inner_text(pane("01", ".state"))


def test_案内は判定を付けるか別のスライドへ移って戻ると消える(deck_page):
    page = deck_page()
    st = pane("01", ".state")
    page.click(pane("01", ".verdict .ng"))
    assert "修正事項" in page.inner_text(st)
    assert has_class(page, st, "rv-warn")
    go(page, "02")
    go(page, "01")
    assert page.inner_text(st) == ""
    page.click(pane("01", ".verdict .ng"))
    page.fill(pane("01", ".cm"), "直して")
    page.click(pane("01", ".verdict .ng"))
    assert page.evaluate(CUR) == "02"
    assert page.evaluate(f"document.querySelector('{st}').textContent") == ""


def test_承認のあとに案のラジオを外すと判定も外れ回答mdに承認が出ない(deck_page):
    page = deck_page()
    page.click(pane("01", 'input[value="A"]'))
    page.click(pane("01", ".verdict .ok"))
    assert verdict(page, "01") == "承認"
    go(page, "01")
    page.click(pane("01", 'input[value="A"]'))
    assert verdict(page, "01") == ""
    page.click(pane("01", ".copyBtn"))
    assert "判定: 承認" not in (page.evaluate("window.__answersMd") or "")


def test_要修正のあとに案のラジオを外しても要修正は残り回答mdに出る(deck_page):
    page = deck_page()
    page.click(pane("01", 'input[value="A"]'))
    page.fill(pane("01", ".cm"), "直して")
    page.click(pane("01", ".verdict .ng"))
    go(page, "01")
    page.click(pane("01", 'input[value="A"]'))
    assert verdict(page, "01") == "要修正"
    page.click(pane("01", ".copyBtn"))
    assert "判定: 要修正" in (page.evaluate("window.__answersMd") or "")


def test_コメント欄の案内文は要修正のとき必須と書く(deck_page):
    page = deck_page()
    assert page.get_attribute(pane("01", ".cm"), "placeholder") == "どうしてほしいか（要修正のときは必須）"


def test_コメントなしの要修正は判定が付かず動かずコメント欄に移る(deck_page):
    page = deck_page()
    page.click(pane("01", ".verdict .ng"))
    assert page.evaluate(CUR) == "01"
    assert verdict(page, "01") == ""
    assert page.evaluate("document.activeElement.matches('.pane[data-slide=\"01\"] .cm')") is True
    assert "修正事項" in page.inner_text(pane("01", ".state"))


def test_部位コメントの自動の要修正は次へ進まない(deck_page):
    page = deck_page()
    part_comment(page)
    assert verdict(page, "01") == "要修正"
    assert page.evaluate(CUR) == "01"


def test_最後のスライドの要修正は判定が付いて動かない(deck_page):
    page = deck_page()
    go(page, "03")
    page.fill(pane("03", ".cm"), "直して")
    page.click(pane("03", ".verdict .ng"))
    assert verdict(page, "03") == "要修正"
    assert page.evaluate(CUR) == "03"


def test_1案だけの最終ページでもコメントがあるときだけ要修正のラジオが付く(deck_page):
    page = deck_page({"01": {"A": PART_FRAG}, "02": {"A": PART_FRAG}}, final=True)
    fix = "document.querySelector('.pane[data-slide=\"01\"] input[value=FIX]').checked"
    page.click(pane("01", ".verdict .ng"))
    assert page.evaluate(fix) is False
    assert page.evaluate(CUR) == "01"
    page.fill(pane("01", ".cm"), "直して")
    page.click(pane("01", ".verdict .ng"))
    assert page.evaluate(fix) is True
    assert page.evaluate(CUR) == "02"


def test_要修正のコメントを消すと回答のコピーが止まり修正事項がないと案内する(deck_page):
    page = deck_page()
    page.fill(pane("01", ".cm"), "直して")
    page.click(pane("01", ".verdict .ng"))
    go(page, "01")
    page.fill(pane("01", ".cm"), "")
    go(page, "03")
    page.click(pane("03", ".copyBtn"))
    assert page.evaluate("!!window.__submitted") is False
    assert page.evaluate(CUR) == "01"
    assert "修正事項がありません" in page.inner_text(pane("01", ".state"))


def test_全部承認は案が決まった判定なしのスライドを承認し要修正は数えず進まない(approve_all_page):
    page = approve_all_page
    go(page, "02")
    page.fill(pane("02", ".cm"), "x")
    page.click(pane("02", ".verdict .ng"))
    page.click(pane("03", ".approveAll"))
    assert verdict(page, "01") == "承認"
    assert verdict(page, "02") == "要修正"
    assert page.evaluate("document.querySelector('.pane[data-slide=\"03\"] input[value=A]').checked") is True
    assert page.evaluate(CUR) == "03"
    st = pane("03", ".state")
    assert "承認 2 枚" in page.inner_text(st)
    assert has_class(page, st, "rv-warn") is False


def test_全部承認はコメントのあるスライドを残し案内に未選択とコメントの枚数を出す(approve_all_page):
    page = approve_all_page
    page.fill(pane("01", ".cm"), "ここ直して")
    page.click(pane("01", ".approveAll"))
    assert verdict(page, "01") == ""
    assert page.evaluate("document.querySelector('.pane[data-slide=\"03\"] input[value=A]').checked") is True
    st = page.inner_text(pane("01", ".state"))
    assert "承認 1 枚" in st
    assert "案が未選択の 1 枚" in st
    assert "コメントのある 1 枚" in st


def test_全部承認のあと別のスライドの古い案内は残らない(approve_all_page):
    page = approve_all_page
    go(page, "02")
    page.click(pane("02", ".verdict .ng"))
    assert "修正事項" in page.inner_text(pane("02", ".state"))
    go(page, "03")
    page.click(pane("03", ".approveAll"))
    assert "承認 2 枚" in page.inner_text(pane("03", ".state"))
    go(page, "02")
    assert page.inner_text(pane("02", ".state")) == ""


def test_全部承認は案が未選択のスライドを承認せず次へも進まない(approve_all_page):
    page = approve_all_page
    go(page, "02")
    page.click(pane("02", ".approveAll"))
    assert verdict(page, "01") == "承認"
    assert verdict(page, "02") == ""
    assert page.evaluate("document.querySelector('.pane[data-slide=\"03\"] input[value=A]').checked") is True
    st = page.inner_text(pane("02", ".state"))
    assert "承認 2 枚" in st
    assert "1 枚" in st
    assert page.evaluate(CUR) == "02"


def test_全部承認の回答mdは一枚ずつ承認したときと同じ(deck_page):
    frags = {"01": {"A": PART_FRAG, "B": PART_FRAG}, "02": {"A": PART_FRAG, "B": PART_FRAG}, "03": {"A": PART_FRAG}}
    expected = (
        "---\ndeck: \nround: 1\n---\n## S01\n- 選択: A\n- 判定: 承認\n- コメント: \n"
        "## S03\n- 選択: A\n- 判定: 承認\n- コメント: \n"
    )

    all_at_once = deck_page(frags)
    all_at_once.check(pane("01", 'input[value="A"]'))
    all_at_once.click(pane("01", ".approveAll"))
    md_all = copied_md(all_at_once, "01")

    one_by_one = deck_page(frags)
    one_by_one.check(pane("01", 'input[value="A"]'))
    one_by_one.click(pane("01", ".verdict .ok"))
    go(one_by_one, "03")
    one_by_one.click(pane("03", ".verdict .ok"))
    md_one = copied_md(one_by_one, "03")

    assert md_all == expected
    assert md_one == expected


def test_何も触らずに回答をコピーすると送られず案内を警告色で出す(deck_page):
    page = deck_page()
    page.click(pane("01", ".copyBtn"))
    assert page.evaluate("!!window.__submitted") is False
    assert "承認か要修正を選んだスライドがありません" in page.inner_text(pane("01", ".state"))
    assert has_class(page, pane("01", ".state"), "rv-warn")


def test_資料全体の確認はあっても任意の案内で回答をコピーのボタンは出る():
    html = variants._page(Path("deck"), {"00": {"A": ""}}, "1", docs={"00": "<p>x</p>"})
    assert "承認する前に" not in html
    assert "資料全体と、スライドごとの設計と原稿を確認します。" in html
    assert "回答をコピー" in html
