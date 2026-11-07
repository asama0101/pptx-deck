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
    assert q[0] == {
        "id": q[0]["id"],
        "type": "edit",
        "slide": "01",
        "k": "A",
        "d": 1,
        "f": "01-A",
        "part": "注釈",
        "text": "短く",
        "edits": [],
        "retry": False,
        "idx": 3,  # 断片の中の data-part の文書順（タイトル・スティッカー・スティッカー・注釈）
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
    assert ai_page.evaluate("id => window.__aiReply({id: id, ok: true, html: '<p>x</p>'})", old) is False
    assert ai_page.text_content(STATE) == MSG_LOST
    assert ai_page.input_value(f"{ROW} textarea") == "短く"


WATCH = "() => { window.__aiWatchAt = Date.now(); return (window.__aiQueue || []).map(q => q.id); }"  # SKILL.md と同じ


def test_待ち受けの更新はキューのidを返し_応答なしの依頼は消える(ai_page):
    ai_page.clock.install()
    ai_page.evaluate("window.__aiWatchAt = Date.now()")
    _write(ai_page)
    ai_page.click(f"{ROW} .aiAsk")
    rid = ai_page.evaluate("window.__aiQueue[0].id")
    assert ai_page.evaluate(WATCH) == [rid]
    ai_page.clock.run_for(181000)
    assert ai_page.evaluate(WATCH) == []  # ページはこの依頼をあきらめた


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
        "html": NEW_FRAG,
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


def test_aiReplyは受け付けたらtrue_知らないidや処理済みならfalseを返す(ai_page):
    req = _ask(ai_page)
    reply = "r => window.__aiReply(r)"
    assert ai_page.evaluate(reply, {"id": "ai-nothing", "ok": True, "html": NEW_FRAG}) is False
    assert ai_page.evaluate(reply, {"id": req["id"], "ok": True, "html": NEW_FRAG}) is True
    assert ai_page.evaluate(reply, {"id": req["id"], "ok": True, "html": NEW_FRAG}) is False  # 処理済み
    req = _ask(ai_page, part="タイトル")
    assert ai_page.evaluate(reply, {"id": req["id"], "ok": False, "error": "x"}) is True  # 失敗の返事も受け付ける


def _ask_in(page, slide, part="注釈", text="短く"):
    """スライド slide に移って頼み、キューから依頼を取り出して返す。"""
    page.evaluate("window.__aiWatchAt = Date.now()")
    page.click(f'#nav button[data-go="{slide}"]')
    pane = f'.pane[data-slide="{slide}"]'
    page.click(f"{pane} .pt >> text={part}")
    page.fill(f"{pane} .plist li textarea", text)
    page.click(f"{pane} .plist li .aiAsk")
    return page.evaluate("window.__aiQueue.shift()")


@pytest.mark.parametrize("slide", ["01", "02"], ids=["複数案", "単一案"])
def test_okの返答で自動の要修正が外れ_回答をコピーできる(ai_page, slide):
    pane = f'.pane[data-slide="{slide}"]'
    verdict = (
        f"() => {{ const p = document.querySelector('{pane}'); const r = p.querySelector('input[name^=s]:checked');"
        " return [p.dataset.verdict || '', r ? r.value : '', p.dataset.auto || '']; }"
    )
    req = _ask_in(ai_page, slide)
    assert "1" in ai_page.evaluate(verdict)  # 指示を書くと自動の要修正
    _reply(ai_page, id=req["id"], ok=True, html=NEW_FRAG)
    assert ai_page.evaluate(verdict) == ["", "", ""]
    ai_page.click(f"{pane} .approveAll")  # 承認に強制しない（案が決まっているスライドだけが承認になる）
    ai_page.click(f"{pane} .copyBtn")
    assert ai_page.evaluate("window.__submitted") is True, ai_page.text_content(f"{pane} .state")
    assert "判定: 要修正" not in ai_page.evaluate("window.__answersMd")


def test_依頼の保留中は回答をコピーできず案内が出る(ai_page):
    req = _ask(ai_page)
    ai_page.click(f"{PANE} .copyBtn")
    assert not ai_page.evaluate("window.__submitted")
    msg = "S01 は Claude が直している最中です。直り終わってから押してください"
    assert ai_page.text_content(f"{PANE} .state") == msg
    _reply(ai_page, id=req["id"], ok=True, html=NEW_FRAG)
    assert "- 部位:" not in _md(ai_page)
    assert ai_page.evaluate("window.__submitted") is True


def test_ほかのスライドの依頼の保留中もそのスライドへ移って止める(ai_page):
    _ask_in(ai_page, "02")
    ai_page.click('#nav button[data-go="01"]')
    ai_page.click(f"{PANE} .copyBtn")
    assert not ai_page.evaluate("window.__submitted")
    assert ai_page.is_visible('.pane[data-slide="02"]')
    assert "S02 は Claude が直している最中です" in ai_page.text_content('.pane[data-slide="02"] .state')


def test_頼み直す用に覚える指示は頼んだ時点の文(ai_page):
    req = _ask(ai_page, text="短く")
    ai_page.fill(f"{ROW} textarea", "書き換えた")
    _reply(ai_page, id=req["id"], ok=True, html=NEW_FRAG)
    assert ai_page.evaluate("document.querySelector('.pane[data-slide=\"01\"]').__rvAi['01-A'].text") == "短く"


def test_同じ名前の部位は依頼のidxで文書順の位置が分かる(ai_page):
    # PART_FRAG のスティッカーは、文書順で 1 番目が右（left:700）、2 番目が左（left:100）。①② は左から付く
    one = _ask(ai_page, part="スティッカー①")
    assert (one["part"], one["idx"]) == ("スティッカー①", 2)
    _reply(ai_page, id=one["id"], ok=False, error="x")
    ai_page.click(f"{ROW} .aiDel")
    two = _ask(ai_page, part="スティッカー②")
    assert (two["part"], two["idx"]) == ("スティッカー②", 1)
    _reply(ai_page, id=two["id"], ok=False, error="x")
    ai_page.click(f"{ROW} .aiDel")
    assert _ask(ai_page, part="タイトル")["idx"] == 0


def test_返答のあと編集の記録が回答に出ない(ai_page):
    ai_page.check(f"{PANE} .rv-edit-toggle")
    ai_page.evaluate(
        "() => { const e = document.querySelector('.pane[data-slide=\"01\"] .big .stage .pp-text');"
        " e.focus(); e.innerHTML = '打ち換え'; e.blur(); }"
    )
    ai_page.uncheck(f"{PANE} .rv-edit-toggle")  # 編集中は部位のバッジが隠れる。記録は残る
    assert "- 編集: " in _md(ai_page)  # 依頼の保留中は回答をコピーできないので、頼む前に確かめる
    ai_page.evaluate("window.__aiWatchAt = Date.now()")
    ai_page.click(f"{PANE} .pt >> text=注釈")
    ai_page.fill(f"{ROW} textarea", "短く")
    ai_page.click(f"{ROW} .aiAsk")
    req = ai_page.evaluate("window.__aiQueue.shift()")
    assert len(req["edits"]) == 1
    assert req["edits"][0].startswith("- 編集: ")
    assert "打ち換え" in req["edits"][0]
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
    assert q[0] == {
        "id": q[0]["id"],
        "type": "undo",
        "slide": "01",
        "k": "A",
        "d": 1,
        "f": "01-A",
        "part": "",
        "text": "",
        "edits": [],
        "retry": False,
        "idx": -1,
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


def test_頼み直した依頼はretryが真で編集を送らず_通常の依頼はretryが偽(ai_page):
    req = _ask(ai_page)
    assert req["retry"] is False
    _reply(ai_page, id=req["id"], ok=True, html=NEW_FRAG)
    ai_page.check(f"{PANE} .rv-edit-toggle")  # 直した結果の上で文字を打ち換える
    ai_page.evaluate(
        "() => { const e = document.querySelector('.pane[data-slide=\"01\"] .big .stage .pp-text');"
        " e.focus(); e.innerHTML = '打ち換え'; e.blur(); }"
    )
    ai_page.uncheck(f"{PANE} .rv-edit-toggle")
    ai_page.click(f"{AFTER} .aiRetry")
    ai_page.evaluate("window.__aiWatchAt = Date.now()")
    ai_page.click(f"{ROW} .aiAsk")
    again = ai_page.evaluate("window.__aiQueue.shift()")
    assert again["retry"] is True
    assert again["edits"] == []  # 前の AI の結果の上の編集は、頼む前の状態には当てはまらない
    _reply(ai_page, id=again["id"], ok=True, html=NEW_FRAG)
    assert _ask(ai_page, part="タイトル")["retry"] is False  # バッジから開いた行は通常の依頼


def test_再読み込みしても元に戻すが残る(ai_page):
    _fixed(ai_page)
    ai_page.reload()
    assert ai_page.locator(f"{AFTER} .aiUndo").count() == 1
    assert ai_page.locator(f"{AFTER} .aiRetry").count() == 1


def test_再読み込みしても直した断片が出る_元に戻したあとは元の断片(ai_page):
    _fixed(ai_page)
    ai_page.reload()
    assert "新しい題" in ai_page.text_content(f"{PANE} .big .stage")
    assert "新しい題" in ai_page.text_content(f'{PANE} .opt[data-k="A"] .stage')
    assert "新しい題" not in ai_page.text_content(f'{PANE} .opt[data-k="B"] .stage')
    ai_page.evaluate("window.__aiWatchAt = Date.now()")
    ai_page.click(f"{AFTER} .aiUndo")
    _reply(ai_page, id=ai_page.evaluate("window.__aiQueue.shift().id"), ok=True, html=PART_FRAG)
    ai_page.reload()
    assert "新しい題" not in ai_page.text_content(f"{PANE} .big .stage")
    assert ai_page.locator(f"{AFTER} .aiUndo").count() == 0


def test_再読み込みしても直した断片の上の編集が戻る(ai_page):
    _fixed(ai_page)
    ai_page.check(f"{PANE} .rv-edit-toggle")
    ai_page.evaluate(
        "() => { const e = document.querySelector('.pane[data-slide=\"01\"] .big .stage .pp-text');"
        " e.focus(); e.innerHTML = '打ち換え'; e.blur(); }"
    )
    ai_page.reload()
    assert "打ち換え" in ai_page.text_content(f'{PANE} .opt[data-k="A"] .stage')
    assert "新しい題" not in ai_page.text_content(f'{PANE} .opt[data-k="A"] .stage')


# ---- 依頼中は、その断片だけ編集モードで直せない ----
TOGGLE = f"{PANE} .rv-edit-toggle"
BIG_EDITABLE = '.big [contenteditable="true"]'


def _editable(page, slide="01"):
    return page.locator(f'.pane[data-slide="{slide}"] {BIG_EDITABLE}').count()


def test_依頼中もスイッチは押せ_依頼中の断片だけ編集できない(ai_page):
    req = _ask(ai_page)
    assert ai_page.is_enabled(TOGGLE)
    ai_page.check(TOGGLE)
    assert _editable(ai_page) == 0  # 01-A は依頼中
    ai_page.click(f'{PANE} .opt[data-k="B"] .thumb')
    assert _editable(ai_page) > 0  # 同じスライドのほかの断片（01-B）は直せる
    ai_page.wait_for_timeout(1500)  # 毎秒の再描画で、編集モードが切れない
    assert ai_page.is_checked(TOGGLE)
    assert _editable(ai_page) > 0
    ai_page.click('#nav button[data-go="02"]')
    assert _editable(ai_page, "02") > 0  # ほかのスライドも直せる
    ai_page.click('#nav button[data-go="01"]')
    ai_page.click(f'{PANE} .opt[data-k="A"] .thumb')
    assert _editable(ai_page) == 0
    _reply(ai_page, id=req["id"], ok=True, html=NEW_FRAG)
    assert _editable(ai_page) > 0  # 終わると直せる
    ai_page.evaluate("window.__aiWatchAt = Date.now()")
    ai_page.click(f"{AFTER} .aiUndo")
    assert _editable(ai_page) == 0  # 元に戻すの依頼中も同じ
    _reply(ai_page, id=ai_page.evaluate("window.__aiQueue.shift().id"), ok=False, error="x")
    assert _editable(ai_page) > 0  # 失敗の返事でも直せるように戻る


def test_依頼を出すと編集中の断片はその場で直せなくなり_遅れた確定も記録しない(ai_page):
    ai_page.evaluate("window.__aiWatchAt = Date.now()")
    ai_page.click(f"{PANE} .pt >> text=注釈")
    ai_page.fill(f"{ROW} textarea", "短く")
    ai_page.check(TOGGLE)
    assert _editable(ai_page) > 0
    ai_page.evaluate(f"window.__el = document.querySelector('{PANE} {BIG_EDITABLE}')")
    ai_page.click(f"{ROW} .aiAsk")
    req = ai_page.evaluate("window.__aiQueue.shift()")
    assert _editable(ai_page) == 0
    assert ai_page.is_checked(TOGGLE)  # 編集モードはオンのまま
    ai_page.evaluate(
        "() => { window.__el.innerHTML = '遅れた打ち換え'; window.__el.dispatchEvent(new Event('blur')); }"
    )
    assert ai_page.evaluate("Object.keys(document.querySelector('.pane[data-slide=\"01\"]').__rvEd || {})") == []
    _reply(ai_page, id=req["id"], ok=True, html=NEW_FRAG)
    assert _editable(ai_page) > 0


def test_待ち受けが切れて応答なしになると依頼中の断片はまた直せる(ai_page):
    ai_page.clock.install()
    _ask(ai_page)  # 編集中は部位のバッジが隠れるので、先に頼む
    ai_page.check(TOGGLE)
    assert _editable(ai_page) == 0
    ai_page.clock.run_for(181000)
    assert _editable(ai_page) > 0


def test_元に戻すだけが待つ状態で待ち受けが切れると案内は元に戻す向け(ai_page):
    _fixed(ai_page)
    ai_page.evaluate("() => { window.__aiWatchAt = 0; window.__rvAiRefresh(); }")
    assert ai_page.text_content(STATE) == "元に戻すには Claude の待ち受けが必要です"


# ---- 通し（実際の Claude 抜き） ----
def test_頼む_返答_元に戻す_頼み直すが通しで動く(ai_page):
    orig = ai_page.evaluate(ORIG_STAGE)
    # 頼む → 返答で断片が置き換わる
    req = _ask(ai_page, text="もっと短く")
    assert req["type"] == "edit"
    assert req["text"] == "もっと短く"
    _reply(ai_page, id=req["id"], ok=True, html=NEW_FRAG)
    assert "新しい題" in ai_page.text_content(f"{PANE} .big .stage")
    assert ai_page.locator(f"{AFTER} .aiUndo").count() == 1
    assert ai_page.locator(f"{AFTER} .aiRetry").count() == 1
    # 元に戻す → undo の依頼 → 元の全文で返答すると戻る
    ai_page.click(f"{AFTER} .aiUndo")
    undo = ai_page.evaluate("window.__aiQueue.shift()")
    assert undo["type"] == "undo"
    _reply(ai_page, id=undo["id"], ok=True, html=PART_FRAG)
    assert "新しい題" not in ai_page.text_content(f"{PANE} .big .stage")
    assert ai_page.evaluate(ORIG_STAGE) == orig
    assert ai_page.locator(f"{AFTER} button").count() == 0
    # もう一度直し、頼み直す → 前の指示が残って行が開き、もう一度頼める
    req = _ask(ai_page, text="もっと短く")
    _reply(ai_page, id=req["id"], ok=True, html=NEW_FRAG)
    ai_page.click(f"{AFTER} .aiRetry")
    assert ai_page.input_value(f"{ROW} textarea") == "もっと短く"
    ai_page.click(f"{ROW} .aiAsk")
    again = ai_page.evaluate("window.__aiQueue.shift()")
    assert again["type"] == "edit"
    assert again["retry"] is True  # Claude は前の AI の結果を戻してから直し直す
    assert again["text"] == "もっと短く"
    assert again["id"] not in (req["id"], undo["id"])
    # 返答が来れば、AI への指示は部位のコメントとして回答 md に出ない
    _reply(ai_page, id=again["id"], ok=True, html=NEW_FRAG)
    assert "- 部位:" not in _md(ai_page)


def test_htmlの無いokの返答は適用されないのでfalseを返し依頼は消える(ai_page):
    req = _ask(ai_page)
    assert ai_page.evaluate("r => window.__aiReply(r)", {"id": req["id"], "ok": True}) is False
    assert ai_page.text_content(f"{PANE} .big .stage").count("題") == 1
    assert "新しい題" not in ai_page.text_content(f"{PANE} .big .stage")
    assert ai_page.is_enabled(f"{ROW} .aiAsk")  # 依頼は落ちている
    assert ai_page.evaluate("r => window.__aiReply(r)", {"id": req["id"], "ok": True, "html": NEW_FRAG}) is False


def test_保存の容量超過では全文を落として再保存し_判定とコメントは残る(open_html):
    frags = {"01": {"A": PART_FRAG, "B": PART_FRAG}, "02": {"A": PART_FRAG}}
    page = open_html(variants._page(Path("deck"), frags, "1"))
    page.check('.pane[data-slide="01"] .ptToggle')
    page.evaluate(
        "() => { const o = Storage.prototype.setItem; Storage.prototype.setItem = function (k, v) {"
        " if (v.length > 4000) throw new DOMException('quota', 'QuotaExceededError'); return o.call(this, k, v); }; }"
    )
    page.fill(f"{PANE} .cm", "全体のコメント")
    _reply_ok = _ask(page)
    _reply(page, id=_reply_ok["id"], ok=True, html=NEW_FRAG + "<!--" + "x" * 5000 + "-->")
    assert page.evaluate("window.__rvStoreDegraded") is True
    saved = page.evaluate(
        "() => JSON.parse(sessionStorage.getItem("
        "Object.keys(sessionStorage).find(k => k.startsWith('pptxdeck-review-'))))"
    )
    s = saved["01"]
    assert s["t"] == "全体のコメント"
    assert s["ai"]["01-A"]["part"] == "注釈"
    assert "html" not in s["ai"]["01-A"]
    assert page.evaluate("typeof document.querySelector('.pane[data-slide=\"01\"]').__rvAi['01-A'].html") == "string"
    page.reload()  # html の無い ai でも再読み込みは壊れない
    assert page.input_value(f"{PANE} .cm") == "全体のコメント"
    assert page.locator(f"{AFTER} .aiUndo").count() == 1
