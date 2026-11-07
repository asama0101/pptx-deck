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


ROW = '.pane[data-slide="01"] .plist li'
STATE = '.pane[data-slide="01"] .aiState'
MSG_IDLE = "いま Claude が待ち受けていません。指示を回答に入れて送ると、あとで直します"
MSG_BUSY = "Claude が直しています…"
MSG_LOST = "応答がありません。指示を部位のコメントに移しました"


def _write(page, text="短く"):
    """注釈のバッジを押し、行の欄に指示を書く。"""
    page.click('.pane[data-slide="01"] .pt >> text=注釈')
    page.fill(f"{ROW} textarea", text)


def test_待ち受け中でないと頼むは押せず案内が出る(ai_page):
    _write(ai_page)
    assert ai_page.is_disabled(f"{ROW} .aiAsk")
    assert ai_page.text_content(STATE) == MSG_IDLE


def test_頼むとキューに依頼が積まれる(ai_page):
    ai_page.evaluate("window.__aiWatchAt = Date.now()")
    _write(ai_page)
    ai_page.click(f"{ROW} .aiAsk")
    q = ai_page.evaluate("window.__aiQueue")
    assert len(q) == 1
    assert {k: q[0][k] for k in ("type", "slide", "k", "d", "f", "part", "text", "edits")} == {
        "type": "edit",
        "slide": "01",
        "k": "A",
        "d": 1,
        "f": "01-A",
        "part": "注釈",
        "text": "短く",
        "edits": [],
    }
    assert q[0]["id"].startswith("ai-")
    assert ai_page.text_content(STATE) == MSG_BUSY


def test_処理が終わるまで同じ断片の頼むは押せない(ai_page):
    ai_page.evaluate("window.__aiWatchAt = Date.now()")
    _write(ai_page)
    assert ai_page.is_enabled(f"{ROW} .aiAsk")
    ai_page.click(f"{ROW} .aiAsk")
    assert ai_page.is_disabled(f"{ROW} .aiAsk")


def test_180秒返答がないと応答なしになり指示が部位のコメントに残る(ai_page):
    ai_page.clock.install()
    ai_page.evaluate("window.__aiWatchAt = Date.now()")
    _write(ai_page)
    ai_page.click(f"{ROW} .aiAsk")
    old = ai_page.evaluate("window.__aiQueue[0].id")
    ai_page.clock.run_for(181000)
    assert ai_page.text_content(STATE) == MSG_LOST
    assert ai_page.input_value(f"{ROW} textarea") == "短く"
    assert ai_page.evaluate("window.__aiQueue.length") == 0
    ai_page.click('.pane[data-slide="01"] .copyBtn')
    assert "- 部位: 案 A 注釈 ／ コメント: 短く" in ai_page.input_value('.pane[data-slide="01"] .copybox') or (
        "- 部位: 案 A 注釈 ／ コメント: 短く" in ai_page.evaluate("window.__answersMd")
    )
    ai_page.evaluate("id => window.__aiReply({id: id, ok: true, html: '<p>x</p>'})", old)
    assert ai_page.text_content(STATE) == MSG_LOST
    assert ai_page.input_value(f"{ROW} textarea") == "短く"


# ---- 返答を受け取って画面を置き換える ----
PANE = '.pane[data-slide="01"]'
NEW_FRAG = PART_FRAG.replace(">題<", ">新しい題<")


def _ask(page, part="注釈", text="短く"):
    """待ち受け中にして、部位の行に指示を書いて頼み、キューから依頼を取り出して返す。"""
    page.evaluate("window.__aiWatchAt = Date.now()")
    page.click(f"{PANE} .pt >> text={part}")
    page.fill(f"{ROW} textarea", text)
    page.click(f"{ROW} .aiAsk")
    return page.evaluate("window.__aiQueue.shift()")


def _reply(page, **r):
    page.evaluate("r => window.__aiReply(r)", r)


def _md(page):
    """01 を A の承認にして回答 md を出す（編集の記録は判定がないと出せないため）。"""
    page.evaluate(
        "() => { const p = document.querySelector('.pane[data-slide=\"01\"]'); p.dataset.verdict = '承認';"
        " p.querySelector('input[name^=s][value=A]').checked = true; window.__answersMd = null; }"
    )
    page.click(f"{PANE} .copyBtn")
    return page.evaluate("window.__answersMd")


def test_okの返答で断片が置き換わり大きな表示も変わる(ai_page):
    req = _ask(ai_page)
    _reply(ai_page, id=req["id"], ok=True, html=NEW_FRAG)
    assert "新しい題" in ai_page.text_content(f"{PANE} .big .stage")
    assert "新しい題" in ai_page.text_content(f'{PANE} .opt[data-k="A"] .stage')
    assert "新しい題" not in ai_page.text_content(f'{PANE} .opt[data-k="B"] .stage')  # 別の案は変わらない


def test_okの返答で指示は欄からも回答mdからも消え内容は覚えておく(ai_page):
    req = _ask(ai_page, text="短く")
    _reply(ai_page, id=req["id"], ok=True, html=NEW_FRAG)
    assert ai_page.locator(ROW).count() == 0
    assert ai_page.evaluate("document.querySelector('.pane[data-slide=\"01\"] .aiAfter') !== null")
    assert ai_page.evaluate("document.querySelector('.pane[data-slide=\"01\"]').__rvAi['01-A']") == {
        "f": "01-A",
        "part": "注釈",
        "text": "短く",
    }
    assert "- 部位:" not in _md(ai_page)
    assert ai_page.evaluate("window.__aiQueue.length") == 0


def test_ngの返答では断片は変わらず理由が出る(ai_page):
    req = _ask(ai_page)
    _reply(ai_page, id=req["id"], ok=False, error="検査の違反: overlap")
    assert "新しい題" not in ai_page.text_content(f"{PANE} .big .stage")
    assert ai_page.text_content(f"{PANE} .big .stage").count("題") == 1
    assert ai_page.text_content(STATE) == "検査の違反: overlap"
    assert ai_page.is_enabled(f"{ROW} .aiAsk")
    assert ai_page.input_value(f"{ROW} textarea") == "短く"  # 指示は残る（頼み直す・回答で送る）


def test_idが合わない返答は無視する(ai_page):
    _ask(ai_page)
    _reply(ai_page, id="ai-nothing", ok=True, html=NEW_FRAG)
    assert "新しい題" not in ai_page.text_content(f"{PANE} .big .stage")
    assert ai_page.is_disabled(f"{ROW} .aiAsk")  # 依頼はまだ保留中


def test_返答のあと編集の記録が回答に出ない(ai_page):
    ai_page.check(f"{PANE} .rv-edit-toggle")
    ai_page.evaluate(
        "() => { const e = document.querySelector('.pane[data-slide=\"01\"] .big .stage .pp-text');"
        " e.focus(); e.innerHTML = '打ち換え'; e.blur(); }"
    )
    ai_page.uncheck(f"{PANE} .rv-edit-toggle")  # 編集中は部位のバッジが隠れる。記録は残る
    ai_page.evaluate("window.__aiWatchAt = Date.now()")
    ai_page.click(f"{PANE} .pt >> text=注釈")
    ai_page.fill(f"{ROW} textarea", "短く")
    ai_page.click(f"{ROW} .aiAsk")
    req = ai_page.evaluate("window.__aiQueue.shift()")
    assert len(req["edits"]) == 1
    assert req["edits"][0].startswith("- 編集: ")
    assert "打ち換え" in req["edits"][0]
    assert "- 編集: " in _md(ai_page)
    _reply(ai_page, id=req["id"], ok=True, html=NEW_FRAG)
    assert "- 編集: " not in _md(ai_page)
    assert ai_page.evaluate("Object.keys(document.querySelector('.pane[data-slide=\"01\"]').__rvOrig || {})") == []


def test_依頼のidはページを開き直しても重ならない(ai_page):
    req = _ask(ai_page)
    assert req["id"] != "ai-1"
    assert req["id"].startswith("ai-")


# ---- 元に戻す・頼み直す・再読み込み ----
AFTER = f"{PANE} .aiAfter"
ORIG_STAGE = 'document.querySelector(\'.pane[data-slide="01"] .opt[data-k="A"] .stage\').innerHTML'


def _fixed(page, text="短く"):
    """頼んで、直った状態にする。"""
    req = _ask(page, text=text)
    _reply(page, id=req["id"], ok=True, html=NEW_FRAG)


def test_直ったあとに元に戻すと頼み直すが出る(ai_page):
    assert ai_page.locator(f"{AFTER} button").count() == 0
    _fixed(ai_page)
    assert ai_page.locator(f"{AFTER} .aiUndo").count() == 1
    assert ai_page.locator(f"{AFTER} .aiRetry").count() == 1


def test_元に戻すはundoの依頼を積み返答で断片が戻る(ai_page):
    orig = ai_page.evaluate(ORIG_STAGE)
    _fixed(ai_page)
    ai_page.click(f"{AFTER} .aiUndo")
    q = ai_page.evaluate("window.__aiQueue")
    assert len(q) == 1
    assert {k: q[0][k] for k in ("type", "slide", "k", "d", "f", "part", "text", "edits")} == {
        "type": "undo",
        "slide": "01",
        "k": "A",
        "d": 1,
        "f": "01-A",
        "part": "",
        "text": "",
        "edits": [],
    }
    assert q[0]["id"].startswith("ai-")
    _reply(ai_page, id=q[0]["id"], ok=True, html=PART_FRAG)
    assert "新しい題" not in ai_page.text_content(f"{PANE} .big .stage")
    assert "新しい題" not in ai_page.text_content(f'{PANE} .opt[data-k="A"] .stage')
    assert ai_page.evaluate(ORIG_STAGE) == orig
    assert ai_page.locator(f"{AFTER} button").count() == 0


def test_元に戻すが応答なしでも指示は部位の行に移らない(ai_page):
    ai_page.clock.install()
    _fixed(ai_page)
    ai_page.click(f"{AFTER} .aiUndo")
    ai_page.clock.run_for(181000)
    assert "応答がありません" in ai_page.text_content(STATE)
    assert MSG_LOST not in ai_page.text_content(STATE)
    assert ai_page.locator(ROW).count() == 0
    assert ai_page.evaluate("window.__aiQueue.length") == 0
    assert ai_page.locator(f"{AFTER} .aiUndo").count() == 1


def test_頼み直すは前の指示を残して開く(ai_page):
    _fixed(ai_page, text="短く")
    ai_page.click(f"{AFTER} .aiRetry")
    assert ai_page.input_value(f"{ROW} textarea") == "短く"
    assert ai_page.evaluate("document.activeElement.tagName") == "TEXTAREA"
    assert ai_page.is_enabled(f"{ROW} .aiAsk")
    assert ai_page.locator(f"{AFTER} .aiUndo").count() == 1


def test_再読み込みしても元に戻すが残る(ai_page):
    _fixed(ai_page)
    ai_page.reload()
    assert ai_page.locator(f"{AFTER} .aiUndo").count() == 1
    assert ai_page.locator(f"{AFTER} .aiRetry").count() == 1
