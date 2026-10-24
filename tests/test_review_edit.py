"""レビューページ（variants.html・final-review.html）の編集モード。生成したページを Playwright で開いて確かめる。"""

# ruff: noqa: S101  # pytest の assert
import json
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest
from pptx_deck import fragedit, variants

FRAG = (
    '<section class="slide" data-layout="content" data-variant="{n}｜理由" style="position:relative;width:1280px;'
    'height:720px">'
    '<div class="pp-text" data-role="title" style="position:absolute;left:64px;top:30px;width:900px;height:40px">'
    "題{n}</div>"
    '<div class="pp-text" style="position:absolute;left:64px;top:120px;width:900px;height:200px"><p>一{n}</p><p>'
    "二{n}</p></div>"
    "</section>"
)

# 貼り付け・入力の掃除（sanitizeHtml）の入力と、仕様から決めた期待値（tests/test_fragedit.py の掃除の仕様と同じ）
SANITIZE_CASES = [
    (
        '<b onclick="x()">a</b><script>x()</script><span style="color:var(--accent);position:fixed;font-size:20px">'
        "b</span>"
        '<a href="x">c</a><i>d</i><span class="t-emph evil">e</span><span style="color:rgb(232, 62, 140)">f</span>',
        '<b>a</b><span style="color:var(--accent);font-size:20px">b</span>cd<span class="t-emph">e</span><span '
        'style="color:#E83E8C">f</span>',
    ),
    ("a<br>b<br/>c", "a<br>b<br>c"),
    (
        '<strong>強</strong><span class="t-white b">白</span><span style="font-weight:bold;color:#fff">x</span>',
        '<strong>強</strong><span class="t-white b">白</span><span style="font-weight:bold;color:#fff">x</span>',
    ),
    ("<div>a</div><p>b</p><ul><li>c</li></ul>", "abc"),
    ('<img src="x" onerror="alert(1)">t<style>p{}</style>u', "tu"),
    ("x &amp; y &lt; z &gt; w", "x &amp; y &lt; z &gt; w"),
    (
        '<span style="color:red;font-size:1.5em">r</span><span style="color:rgb(300,0,0)">s</span>',
        "<span>r</span><span>s</span>",
    ),
    # 入れ子の span（中が 1 つの span だけなら 1 つにまとめる。内側の指定が勝つ）
    (
        '<b><span style="font-size:20px"><span style="font-size:21px"><span style="font-size:33px"><span '
        'style="color:#e51010">最高峰</span></span></span></span></b>',
        '<b><span style="font-size:33px;color:#e51010">最高峰</span></b>',
    ),
    (
        '<span class="t-emph b" style="color:#fff;font-size:20px"><span class="t-accent" style="font-weight:400">'
        "x</span></span>",
        '<span class="t-accent" style="font-size:20px;font-weight:400">x</span>',
    ),
    (
        '<span style="font-size:20px">a<span style="font-size:22px">b</span></span><span><a><span class="t-sub">'
        "c</span></a></span>",
        '<span style="font-size:20px">a<span style="font-size:22px">b</span></span><span class="t-sub">c</span>',
    ),
    (
        '<span style="font-size:20px"><span style="font-size:22px">b</span><br></span><span class="t-dark"> <span>'
        "d</span></span>",
        '<span style="font-size:20px"><span style="font-size:22px">b</span><br></span><span class="t-dark"> <span>'
        "d</span></span>",
    ),
]
SANITIZE_IDS = [
    "属性とscriptを除く",
    "brをそろえる",
    "強調と白は残す",
    "ブロック要素は文字だけ",
    "imgとstyleを除く",
    "実体参照は保つ",
    "不正な色とサイズを除く",
    "入れ子のspanを1つにまとめる",
    "クラスと指定を合成",
    "空のspanとaを外す",
    "br入りの入れ子は残す",
]

BIG = '.pane[data-slide="01"] .big '
BAR = '.pane[data-slide="01"] .rv-edit-bar '
THUMB = '.pane[data-slide="01"] .opt[data-k="A"] .stage .pp-text'
# 直した（編集の記録がある）のに判定のないスライドを、画面の操作なしで承認にする（1 案だけのスライドは A を選ぶ）
APPROVE_EDITED = """() => document.querySelectorAll('.pane').forEach(p => {
    if (!Object.keys(p.__rvEd || {}).length) return;
    if (p.dataset.single === '1') {
        if (!p.querySelector('input[type=radio][name^="s"]:checked'))
            p.querySelector('input[type=radio][name^="s"][value="A"]').checked = true;
    } else if (!p.dataset.verdict) p.dataset.verdict = '承認';
})"""
CUR = "document.querySelector('#nav button[aria-current=true]').dataset.go"


# ---- 画面の足場 ----
@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        b = pw.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def open_page(browser, tmp_path):
    """HTML を tmp_path/p.html に書いて chromium で開く。ページはテスト後に閉じる。"""
    pages = []

    def _open(html):
        f = tmp_path / "p.html"
        f.write_text(html, encoding="utf-8")
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        pages.append(page)
        page.goto(f.as_uri())
        settle(page)
        return page

    yield _open
    for p in pages:
        p.close()


def settle(page):
    page.wait_for_timeout(200)  # ページの JS が保存状態を戻すのを待つ


def make_page(preset=None, designs=None, tweak=None):
    frags = {nn: {"A": FRAG.format(n=nn + "a"), "B": FRAG.format(n=nn + "b")} for nn in ("01", "02")}
    if tweak:
        frags["01"]["A"] = tweak(frags["01"]["A"])
    return variants._page(Path("deck"), frags, "2", preset=preset or {}, designs=designs)


def copy_md(page, nn="01", approve=True):
    """回答をコピーして md を返す（止まったときは None）。approve が真なら、直したのに判定のないスライドを先に承認にする
    （判定がないとコピーが止まるため。編集の記録を読むテストで使う）。"""
    if approve:
        page.evaluate(APPROVE_EDITED)
    page.click(f'.pane[data-slide="{nn}"] .copyBtn')
    return page.evaluate("window.__answersMd")


def edit(page, sel, html):
    page.evaluate(
        "([s, h]) => { const e = document.querySelector(s); e.focus(); e.innerHTML = h; e.blur(); }", [sel, html]
    )


def edit_lines(md):
    return [json.loads(ln.split(": ", 1)[1]) for ln in md.splitlines() if ln.startswith("- 編集: ")]


def go(page, nn):
    page.click(f'#nav button[data-go="{nn}"]')


# ---- ツールバー操作の足場 ----
@pytest.fixture
def toolbar_page(open_page):
    """題を指定の HTML にした 1 案だけのページを開き、編集モードをオンにして返す関数。"""

    def _make(title):
        frags = {"01": {"A": FRAG.format(n="01a").replace("題01a", title)}}
        page = open_page(variants._page(Path("deck"), frags, "2"))
        page.evaluate("setEditing(true)")
        return page

    return _make


def select(page, txt):
    """大きな 1 案の題で、文字 txt（複数の文字ノードにまたがってよい）を選ぶ。"""
    page.evaluate(
        """([s, txt]) => {
        const e = document.querySelector(s); e.focus();
        const i = e.textContent.indexOf(txt), j = i + txt.length,
            w = document.createTreeWalker(e, NodeFilter.SHOW_TEXT);
        const r = document.createRange(); let n, at = 0, a = false;
        while ((n = w.nextNode())) {
            const end = at + n.data.length;
            if (!a && i < end) { r.setStart(n, i - at); a = true; }
            if (a && j <= end) { r.setEnd(n, j - at); break; }
            at = end;
        }
        const sel = getSelection(); sel.removeAllRanges(); sel.addRange(r);
    }""",
        [BIG + ".pp-text", txt],
    )
    page.wait_for_timeout(50)  # selectionchange を待つ


def after(page):
    """今の題の編集後の HTML（記録がなければ None）。"""
    page.evaluate("window.__answersMd = null")  # 出す行がないと、前の内容が残るため
    got = edit_lines(copy_md(page) or "")
    return got[0]["after"] if got else None


def press(page, ed, v=None, times=1):
    sel = BAR + f'[data-ed="{ed}"]' + (f'[data-v="{v}"]' if v else "")
    for _ in range(times):
        page.click(sel)


def custom_color(page, v):
    page.evaluate(
        "([s, v]) => { const c = document.querySelector(s); c.value = v; c.dispatchEvent(new Event('change')); }",
        [BAR + ".rv-ed-color", v],
    )


class _Nest(HTMLParser):
    """span の入れ子で、同じ指定（font-size・色）が重なった深さの最大と、空の要素の数を数える。"""

    def __init__(self):
        super().__init__()
        self.stack, self.deep, self.empty, self.last = [], {"size": 0, "color": 0}, 0, None

    def handle_starttag(self, tag, attrs):
        if tag == "br":
            return
        d = dict(attrs)
        st, cls = d.get("style") or "", (d.get("class") or "").split()
        props = set()
        if "font-size" in st:
            props.add("size")
        if "color" in st or any(c.startswith("t-") for c in cls):
            props.add("color")
        self.stack.append(props)
        for k in self.deep:
            self.deep[k] = max(self.deep[k], sum(k in p for p in self.stack))
        self.last = tag

    def handle_endtag(self, tag):
        if tag == "br":
            return
        if self.last == tag:
            self.empty += 1
        self.stack.pop()
        self.last = None

    def handle_data(self, data):
        self.last = None


def nest(html):
    p = _Nest()
    p.feed(html)
    return p


# ---- 編集の記録 ----
def test_グラフのラベルは編集モードのときだけ直せて記録は元に戻すと消える(open_page, pkg, tmp_path):
    spec = (
        '{"type":"bar","categories":["A案","C案"],"series":[{"name":"費用","values":[3,5]},'
        '{"name":"運用","values":[1,2]}]}'
    )
    chart = (
        '<div class="pp-chart" data-chart=\'' + spec + "' "
        'style="position:absolute;left:64px;top:340px;width:900px;height:300px"></div>'
    )
    frag = FRAG.format(n="01a").replace("</section>", chart + "</section>")
    (tmp_path / "chart-preview.js").write_text(
        (pkg / "assets" / "web" / "chart-preview.js").read_text(encoding="utf-8"), encoding="utf-8"
    )
    page = open_page(variants._page(Path("deck"), {"01": {"A": frag}}, "2"))
    panel = ".rv-chart-panel"
    page.click(BIG + ".pp-chart")  # 編集モードでなければ何も出ない
    assert page.locator(panel).count() == 0
    page.evaluate("setEditing(true)")
    page.click(BIG + ".pp-chart")
    assert page.locator(panel).count() == 1
    assert page.locator(panel + " input").count() == 4  # カテゴリ 2 ＋ 系列 2（数値の欄はない）
    assert page.locator(panel + " input[type=number]").count() == 0
    page.fill(panel + ' input[data-t="c0.cat1"]', "B案")

    def texts(sel):
        return page.evaluate("s => Array.from(document.querySelectorAll(s + ' svg text')).map(e => e.textContent)", sel)

    assert "B案" in texts(BIG + ".pp-chart")
    thumb = '.pane[data-slide="01"] .opt[data-k="A"] .stage .pp-chart'
    assert "B案" in json.loads(page.get_attribute(thumb, "data-chart"))["categories"]
    assert "B案" in texts(thumb)
    page.fill(panel + ' input[data-t="c0.ser0"]', "総費用")
    page.fill('.pane[data-slide="01"] .cm', "x")
    # ボタンだと次へ進んで編集パネルが閉じるので、判定だけ直接付ける（1 案だけのスライドの要修正は FIX）
    page.evaluate("document.querySelector('.pane[data-slide=\"01\"] input[value=FIX]').checked = true")
    got = edit_lines(copy_md(page))
    assert [(e["t"], e["before"], e["after"]) for e in got] == [
        ("c0.cat1", "C案", "B案"),
        ("c0.ser0", "費用", "総費用"),
    ]
    assert '"t":"c0.cat1"' in copy_md(page)
    page.fill(panel + ' input[data-t="c0.cat1"]', "C案")  # 元に戻すと記録が消える
    assert [e["t"] for e in edit_lines(copy_md(page))] == ["c0.ser0"]
    page.evaluate("setEditing(false)")
    assert page.is_visible(panel) is False


def test_編集モードは初期オフで回答mdは編集前と1バイトも変わらない(open_page):
    page = open_page(make_page({"01": {"c": "B", "d": 1, "v": "承認"}}))
    count = "document.querySelectorAll('[contenteditable]').length"
    assert page.evaluate(count) == 0
    assert page.is_checked('.pane[data-slide="01"] .rv-edit-toggle') is False
    assert page.is_visible('.pane[data-slide="01"] .rv-edit-bar') is False
    page.click('.pane[data-slide="01"] .opt[data-k="A"] .thumb')  # 編集モードでなければ、サムネを押すと大きく見るだけ
    assert page.evaluate("document.querySelector('.pane[data-slide=\"01\"] .opt.view').dataset.k") == "A"
    assert page.evaluate(count) == 0
    md = copy_md(page)
    assert md == "---\ndeck: deck\nround: 2\n---\n## S01\n- 選択: B\n- 判定: 承認\n- コメント: \n"
    for key in ("- 編集:", "- 配色:", "- 出力形式:"):
        assert key not in md
    page.check('.pane[data-slide="01"] .rv-edit-toggle')
    assert page.evaluate(count) > 0
    assert page.is_visible('.pane[data-slide="01"] .rv-edit-bar') is True
    page.uncheck('.pane[data-slide="01"] .rv-edit-toggle')
    assert page.evaluate(count) == 0  # オフに戻すと、編集の属性は残らない


def test_直した文字は記録されサムネ・別スライド・開き直しに引き継がれ元に戻すと消える(open_page):
    page = open_page(make_page())
    page.evaluate("setEditing(true)")
    assert page.evaluate("document.querySelector('.rv').classList.contains('editing')") is True
    edit(page, BIG + ".pp-text", "新<b>題</b>")
    assert page.inner_html(THUMB) == "新<b>題</b>"  # サムネの断片にも書く
    go(page, "02")
    go(page, "01")
    assert page.inner_html(BIG + ".pp-text") == "新<b>題</b>"  # 別のスライドに移って戻っても残る
    assert copy_md(page, approve=False) is None  # 直しただけ（判定なし）では、コピーが止まる
    md = copy_md(page)
    assert "## S01\n- 選択: \n" in md  # 直しただけのスライドは、案を選んだことにしない
    assert '- 編集: {"f":"01-A","t":"t0","before":"題01a","after":"新<b>題</b>"}' in md
    assert "## S02" not in md
    edits, problems = fragedit.parse_edits(md)
    assert problems == []
    assert [(e["slide"], e["f"], e["t"], e["after"]) for e in edits] == [("01", "01-A", "t0", "新<b>題</b>")]
    page.reload()
    settle(page)
    assert page.inner_html(THUMB) == "新<b>題</b>"  # 同じタブで開き直しても残る
    assert len(edit_lines(copy_md(page))) == 1
    page.evaluate("setEditing(true)")
    edit(page, BIG + ".pp-text", "題01a")  # 元に戻したら、記録を消す
    md_after_undo = page.evaluate(
        "document.querySelector('.pane[data-slide=\"01\"] .cm').value = 'x', "
        "document.querySelector('.pane[data-slide=\"01\"] .verdict .ng').click(), "
        "document.querySelector('#nav button[data-go=\"01\"]').click(), "
        "document.querySelector('.pane[data-slide=\"01\"] .copyBtn').click(), window.__answersMd"
    )
    assert "## S01\n- 選択: \n- 判定: 要修正\n- コメント: x\n" in md_after_undo
    assert "- 編集:" not in md_after_undo


def test_断片が変わって作り直したページは古い編集・判定・コメントを引き継がない(open_page, tmp_path):
    page = open_page(make_page())  # 同じ deck・round でも、内容が変われば保存先（sessionStorage）は別
    page.evaluate("setEditing(true)")
    edit(page, BIG + ".pp-text", "題を直した")
    page.fill('.pane[data-slide="01"] .cm', "x")
    page.click('.pane[data-slide="01"] .verdict .ng')
    go(page, "01")
    assert len(edit_lines(copy_md(page))) == 1
    page.reload()
    settle(page)  # 同じ内容の開き直しは、状態を引き継ぐ
    go(page, "01")
    assert page.input_value('.pane[data-slide="01"] .cm') == "x"
    assert len(edit_lines(copy_md(page))) == 1
    regen = make_page(
        tweak=lambda f: f.replace("<p>一01a</p>", "<p>新規01a</p><p>一01a</p>")
    )  # 断片を 1 か所変えて作り直す（保存キーのハッシュも変わる）
    (tmp_path / "p.html").write_text(regen, encoding="utf-8")
    page.reload()
    settle(page)
    go(page, "01")
    assert page.inner_html('.pane[data-slide="01"] .opt[data-k="A"] .stage .pp-text') == "題01a"  # 古い編集は復元しない
    assert page.input_value('.pane[data-slide="01"] .cm') == ""  # 判定・コメントも空
    assert page.evaluate("document.querySelector('.pane[data-slide=\"01\"]').dataset.verdict || null") is None
    assert "- 編集:" not in (copy_md(page, approve=False) or "")


def test_案とデザインごとに別の断片へ編集が記録され混ざらない(open_page):
    designs = {"01": {"A": {1: FRAG.format(n="01a"), 2: FRAG.format(n="01a2")}, "B": {1: FRAG.format(n="01b")}}}
    page = open_page(make_page(designs=designs))
    assert page.evaluate(
        "Array.from(document.querySelectorAll('.pane[data-slide=\"01\"] [data-f]')).map(e => e.dataset.f)"
    ) == ["01-A", "01-B", "01-A", "01-A-d2"]  # デザイン 1 の断片は NN-K（NN-K-d1 という断片はない）
    page.evaluate("setEditing(true)")
    edit(page, BIG + ".pp-text", "A の題")
    page.click('.pane[data-slide="01"] .opt[data-k="B"] .thumb')
    edit(page, BIG + "p:nth-of-type(2)", "B の二")
    page.click('.pane[data-slide="01"] .opt[data-k="A"] .thumb')
    page.click('.pane[data-slide="01"] .dopt[data-d="2"] .thumb')
    edit(page, BIG + ".pp-text", "A2 の題")
    assert page.inner_html('.pane[data-slide="01"] .opt[data-k="B"] .stage .pp-text') == "題01b"
    assert (
        page.inner_html('.pane[data-slide="01"] .dopt[data-d="1"] .stage .pp-text') == "A の題"
    )  # 同じ断片のサムネはそろえる
    got = [(e["f"], e["t"], e["after"]) for e in edit_lines(copy_md(page))]
    assert sorted(got) == [("01-A", "t0", "A の題"), ("01-A-d2", "t0", "A2 の題"), ("01-B", "t2", "B の二")]


def test_最終ページは選ばれた断片のidで編集を記録する(open_page):
    frags = {"01": {"A": FRAG.format(n="01b2")}, "02": {"A": FRAG.format(n="02a")}}
    page = open_page(variants._page(Path("deck"), frags, "final", final=True, ids={"01": "01-B-d2", "02": "02-A"}))
    page.check('.pane[data-slide="01"] .rv-edit-toggle')
    edit(page, BIG + ".pp-text", "最終で直す")
    assert [(e["f"], e["after"]) for e in edit_lines(copy_md(page))] == [("01-B-d2", "最終で直す")]


@pytest.mark.parametrize(("raw", "expected"), SANITIZE_CASES, ids=SANITIZE_IDS)
def test_貼り付けや入力のマークアップは掃除され期待の形になる(open_page, raw, expected):
    page = open_page(make_page())
    assert page.evaluate("s => sanitizeHtml(s)", raw) == expected


def test_貼り付けた危険なマークアップは文字だけになり実行されない(open_page):
    page = open_page(make_page())
    page.evaluate("setEditing(true)")
    page.evaluate(
        """s => {
        const e = document.querySelector(s); e.focus();
        const r = document.createRange(); r.selectNodeContents(e);
        const sel = getSelection(); sel.removeAllRanges(); sel.addRange(r);
        const dt = new DataTransfer();
        dt.setData('text/html',
            '<img src=x onerror="window.__bad=1"><script>window.__bad=1</script><b style="position:fixed">貼った</b>');
        dt.setData('text/plain', '貼った文字');
        e.dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true}));
        e.blur();
    }""",
        BIG + ".pp-text",
    )
    assert edit_lines(copy_md(page))[0]["after"] == "貼った文字"
    assert page.evaluate("window.__bad") is None


def test_キーボード入力と太字と色のツールバーが記録に反映される(open_page):
    page = open_page(make_page())
    page.check('.pane[data-slide="01"] .rv-edit-toggle')
    page.click(BIG + ".pp-text")
    page.keyboard.press("End")
    page.keyboard.type("X")
    page.keyboard.press("Enter")
    page.keyboard.type("Y")
    page.keyboard.press("Control+A")
    page.click(BAR + '[data-ed="bold"]')
    page.click(BAR + '[data-ed="cls"][data-v="t-emph"]')
    page.keyboard.press("Escape")
    got = edit_lines(copy_md(page))[0]["after"]
    assert got == '<b><span class="t-emph">題01aX<br>Y</span></b>'
    assert fragedit.sanitize_inline(got) == got  # 掃除済みの形でそのまま戻せる


# ---- ツールバーを何度押しても、同じ指定の span を入れ子にしない ----
def test_サイズを何度押しても一つのspanが更新されるだけ(toolbar_page):
    page = toolbar_page("前<b>最高峰のアクション</b>後")
    select(page, "アクション")
    press(page, "size", "2")
    first = int(re.search(r"font-size:(\d+)px", after(page)).group(1))
    press(page, "size", "2", times=13)
    press(page, "size", "-2")
    got = after(page)
    assert got == f'前<b>最高峰の<span style="font-size:{first + 24}px">アクション</span></b>後'
    assert fragedit.sanitize_inline(got) == got
    page.keyboard.press("Escape")
    assert after(page) == got


def test_色を何度選んでも一つのspanが更新されるだけ(toolbar_page):
    page = toolbar_page("前<b>最高峰のアクション</b>後")
    select(page, "アクション")
    for v in ("t-emph", "t-accent", "t-dark"):
        press(page, "cls", v)
    assert after(page) == '前<b>最高峰の<span class="t-dark">アクション</span></b>後'
    custom_color(page, "#e51010")
    custom_color(page, "#00aa00")
    assert after(page) == '前<b>最高峰の<span style="color:#00aa00">アクション</span></b>後'
    press(page, "cls", "t-sub")
    assert after(page) == '前<b>最高峰の<span class="t-sub">アクション</span></b>後'


def test_サイズと色を交互に繰り返しても入れ子も空要素もできない(toolbar_page):
    page = toolbar_page("前<b>最高峰のアクション</b>後")
    select(page, "アクション")
    for _ in range(3):
        press(page, "size", "2")
        press(page, "cls", "t-emph")
        custom_color(page, "#e51010")
    got = after(page)
    n = nest(got)
    assert n.deep == {"size": 1, "color": 1}, got
    assert got.count("font-size") == 1, got
    assert "color:#e51010" in got
    assert "t-emph" not in got
    assert n.empty == 0, got


def test_太字を二回押すと元に戻り記録も消える(toolbar_page):
    page = toolbar_page("前文字後")
    select(page, "文字")
    press(page, "bold")
    assert after(page) == "前<b>文字</b>後"
    press(page, "bold")
    assert after(page) is None  # 元に戻ったので、記録は消える
    assert page.inner_html(BIG + ".pp-text") == "前文字後"
    press(page, "bold")
    press(page, "size", "2")
    press(page, "bold")
    got = after(page)
    assert "<b>" not in got
    assert "font-size" in got
    assert nest(got).empty == 0, got


def test_既存のspanの中身を選んだときはそのspanを直しまるごと選んだときは包む(toolbar_page):
    page = toolbar_page('前<span style="font-size:20px">中</span>後')
    select(page, "中")  # span の中身ちょうど → その span を直す
    press(page, "size", "2")
    assert after(page) == '前<span style="font-size:22px">中</span>後'
    select(page, "前中後")  # span をまるごと含む → 中の指定を外して包む
    page.fill(BAR + ".rv-ed-size", "30")
    page.dispatch_event(BAR + ".rv-ed-size", "change")
    assert after(page) == '<span style="font-size:30px">前中後</span>'


def test_spanの一部だけ選ぶとspanを分けて入れ子にしない(toolbar_page):
    page = toolbar_page('<span class="t-emph" style="font-size:20px">ab<b>cd</b>ef</span>gh')
    select(page, "c")  # span の中の一部 → span を分ける
    press(page, "size", "2", times=2)
    got = after(page)
    assert got == (
        '<span class="t-emph" style="font-size:20px">ab</span>'
        '<span class="t-emph" style="font-size:24px"><b>c</b></span>'
        '<span class="t-emph" style="font-size:20px"><b>d</b>ef</span>gh'
    )
    n = nest(got)
    assert (n.deep["size"], n.empty) == (1, 0), got
    select(page, "fg")  # span の外にまたがる
    press(page, "size", "-2", times=2)
    got = after(page)
    n = nest(got)
    assert (n.deep["size"], n.empty) == (1, 0), got
    assert re.sub(r"<[^>]+>", "", got) == "abcdefgh"


# ---- リセット: 編集対象の文章を元の内容に戻し、編集の記録を消す ----
def decorate(page):
    """題を、文面変更・太字・サイズ・色で直す（キーボード入力と、ツールバーの操作）。"""
    page.click(BIG + ".pp-text")
    page.keyboard.press("End")
    page.keyboard.type("追記")
    select(page, "追記")
    press(page, "bold")
    press(page, "size", "2")
    press(page, "cls", "t-emph")


def test_リセットで題が元に戻りサムネ・大きな案・記録が消え編集モードは続く(toolbar_page):
    page = toolbar_page("前文字後")
    decorate(page)
    edited = after(page)
    assert edited.startswith("前文字後<b>")
    assert "追記" in edited
    assert "t-emph" in edited
    assert "font-size" in edited
    assert page.inner_html(THUMB) == edited
    page.click(BAR + '[data-ed="reset"]')
    assert page.inner_html(THUMB) == "前文字後"  # サムネの断片
    assert page.inner_html(BIG + ".pp-text") == "前文字後"  # 大きな 1 案
    assert after(page) is None
    assert "- 編集:" not in page.evaluate("window.__answersMd || ''")
    assert page.evaluate("document.querySelector('.rv').classList.contains('editing')") is True  # 編集モードは続く
    assert page.get_attribute(BIG + ".pp-text", "contenteditable") == "true"


def test_フォーカスが外れても選んでいた対象をリセットで戻せる(toolbar_page):
    page = toolbar_page("前文字後")
    select(page, "文字")
    press(page, "bold")
    page.keyboard.press("Escape")
    assert page.inner_html(THUMB) == "前<b>文字</b>後"
    page.click(BAR + '[data-ed="reset"]')
    assert page.inner_html(THUMB) == "前文字後"
    assert page.inner_html(BIG + ".pp-text") == "前文字後"
    assert after(page) is None


def test_表のセルをリセットすると押したセルだけ元に戻り他のセルは変わらない(open_page):
    table = (
        '<div class="pp-table" style="position:absolute;left:64px;top:120px;width:600px;height:100px">'
        "<table><tr><td>セル甲</td><td>セル乙</td></tr></table></div>"
    )
    frag = FRAG.format(n="01a").replace("</section>", table + "</section>")
    page = open_page(variants._page(Path("deck"), {"01": {"A": frag}}, "2"))
    page.evaluate("setEditing(true)")
    cell = BIG + "td:nth-of-type(2)"
    thumb = '.pane[data-slide="01"] .opt[data-k="A"] .stage td:nth-of-type(2)'
    page.click(cell)
    page.keyboard.press("End")
    page.keyboard.type("追記")
    page.evaluate("document.activeElement.blur()")
    page.click(cell)  # もう一度フォーカスして選ぶ
    page.keyboard.press("Control+A")
    press(page, "bold")
    assert page.inner_html(thumb) == "<b>セル乙追記</b>"
    page.click(BAR + '[data-ed="reset"]')
    assert page.inner_html(thumb) == "セル乙"
    assert page.inner_html(cell) == "セル乙"
    assert page.inner_html(BIG + "td:nth-of-type(1)") == "セル甲"
    assert after(page) is None


def test_リセットした内容は読み込み直しても復元されない(toolbar_page):
    page = toolbar_page("前文字後")
    decorate(page)
    page.click(BAR + '[data-ed="reset"]')
    page.reload()
    settle(page)
    assert page.inner_html(THUMB) == "前文字後"
    assert after(page) is None


def test_対象を選んでいないリセットは何もせず他の編集の記録も変えない(toolbar_page):
    page = toolbar_page("前文字後")
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.click(BAR + '[data-ed="reset"]')  # 何も選んでいない
    assert errors == []
    assert after(page) is None
    assert page.inner_html(THUMB) == "前文字後"
    edit(page, BIG + ".pp-text", "直した")  # 別の編集があっても、対象がなければ記録は変わらない
    page.evaluate("setEditing(false), setEditing(true)")  # 選んでいた範囲は編集モードを切ると消える
    page.click(BAR + '[data-ed="reset"]')
    assert errors == []
    assert after(page) == "直した"
    assert page.inner_html(THUMB) == "直した"


def test_隠れたスライドの編集は別スライドのリセットで戻らない(open_page):
    page = open_page(make_page())
    page.evaluate("setEditing(true)")
    page.click(BIG + ".pp-text")
    page.keyboard.press("Control+A")
    press(page, "bold")
    assert page.inner_html(THUMB) == "<b>題01a</b>"
    page.click('.pane[data-slide="01"] .verdict .ok')  # 承認で 02 へ（01 は隠れる）
    page.click('.pane[data-slide="02"] .rv-edit-bar [data-ed="reset"]')  # 02 のリセットは、隠れた 01 に効かない
    assert page.inner_html(THUMB) == "<b>題01a</b>"
    assert '"after":"<b>題01a</b>"' in copy_md(page, "02")


def test_隠れたスライドの選択には別スライドのツールバーが効かず選んだスライドにだけ効く(open_page):
    def bar(nn):
        return f'.pane[data-slide="{nn}"] .rv-edit-bar '

    def thumb(nn):
        return f'.pane[data-slide="{nn}"] .opt[data-k="A"] .stage .pp-text'

    def select_all(nn):
        page.click(f'.pane[data-slide="{nn}"] .big .pp-text')
        page.keyboard.press("Control+A")
        page.wait_for_timeout(50)  # selectionchange を待つ

    def every_action(nn):
        page.click(bar(nn) + '[data-ed="bold"]')
        page.click(bar(nn) + '[data-ed="cls"][data-v="t-emph"]')
        page.evaluate(
            "s => { const c = document.querySelector(s); c.value = '#e51010'; c.dispatchEvent(new Event('change')); }",
            bar(nn) + ".rv-ed-color",
        )
        page.click(bar(nn) + '[data-ed="size"][data-v="2"]')
        page.fill(bar(nn) + ".rv-ed-size", "30")
        page.dispatch_event(bar(nn) + ".rv-ed-size", "change")

    def edits():
        page.evaluate("window.__answersMd = null")
        return edit_lines(copy_md(page, "02") or "")

    page = open_page(make_page())
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.evaluate("setEditing(true)")
    select_all("01")
    page.click('.pane[data-slide="01"] .verdict .ok')  # 承認で 02 へ（01 は隠れる）
    every_action("02")  # 02 のツールバーは、隠れた 01 の選択に効かない
    assert page.inner_html(thumb("01")) == "題01a"
    assert page.inner_html(BIG + ".pp-text") == "題01a"
    assert page.inner_html(thumb("02")) == "題02a"
    assert edits() == []
    select_all("02")  # 02 で選べば、02 の対象に効く
    page.click(bar("02") + '[data-ed="bold"]')
    assert page.inner_html(thumb("02")) == "<b>題02a</b>"
    assert page.inner_html(thumb("01")) == "題01a"
    assert [e["after"] for e in edits()] == ["<b>題02a</b>"]
    go(page, "01")  # 01 へ戻って選べば、01 に効く
    select_all("01")
    page.click(bar("01") + '[data-ed="bold"]')
    assert page.inner_html(thumb("01")) == "<b>題01a</b>"
    go(page, "02")  # 02 へ移っただけ（選んでいない）なら、02 のツールバーは何もしない
    every_action("02")
    assert page.inner_html(thumb("01")) == "<b>題01a</b>"
    assert page.inner_html(thumb("02")) == "<b>題02a</b>"
    assert sorted(e["after"] for e in edits()) == ["<b>題01a</b>", "<b>題02a</b>"]
    assert errors == []


def test_全消去ボタンはなくリセットボタンだけがある(toolbar_page):
    page = toolbar_page("前文字後")
    assert page.locator('[data-ed="clear"]').count() == 0
    assert page.locator(BAR + '[data-ed="reset"]').count() == 1
    assert page.inner_text(BAR + '[data-ed="reset"]') == "リセット"
    assert "解除" not in page.inner_text(BAR)


# ---- 編集対象の決め方は JS（editTargets）と Python（fragedit.targets）で一致させる ----
EXTRA_TARGET_SOURCES = [
    '<div class="pp-text"><p>一<p>二</div>',  # 閉じ忘れの p・li は暗黙に閉じる
    '<div class="pp-text"><ul><li>あ<li>い</ul></div>',
    '<table class="pp-table"><tr><td><p>a<p>b</td><td>c</td></tr></table>',
    '<div class="pp-text"><p>a<ul><li>b</ul><p>c</div>',  # p は ul・div・h2 などの開始でも暗黙に閉じる
    '<div class="pp-text"><p>a<div>b</div><p>c</div>',
    '<div class="pp-text"><p>a<h2>b</h2><p>c<blockquote>d</blockquote></div>',
    '<table class="pp-table"><tr><td><p>a<ul><li>b</ul></td><td>c</td></tr></table>',
]


def test_編集対象はJSとPythonで部品の全見本と閉じ忘れの断片で一致する(open_page, pkg):
    files = sorted((pkg / "assets" / "components").rglob("*.html"))
    assert len(files) > 100  # 見本を拾えていること
    srcs = [f.read_text(encoding="utf-8") for f in files] + EXTRA_TARGET_SOURCES
    names = [f.name for f in files] + [f"(閉じ忘れ{i})" for i in range(len(EXTRA_TARGET_SOURCES))]
    py = [[s[t.start : t.end] for t in fragedit.targets(s)] for s in srcs]
    page = open_page(make_page())
    got = page.evaluate(
        """([srcs, py]) => srcs.map((s, i) => {
        const d = document.createElement('div'); d.innerHTML = s;
        const norm = h => { const n = document.createElement('div'); n.innerHTML = h; return n.innerHTML; };
        return [editTargets(d).map(e => e.innerHTML), py[i].map(norm)];
    })""",
        [srcs, py],
    )
    for name, (js, want) in zip(names, got, strict=True):
        assert js == want, name
    # 閉じ忘れの断片の対象は、暗黙に閉じた段落・項目・セルの文字（div・blockquote の中身は対象外）
    assert [js for js, _ in got[len(files) :]] == [
        ["一", "二"],
        ["あ", "い"],
        ["a", "b", "c"],
        ["a", "b", "c"],
        ["a", "c"],
        ["a", "c"],
        ["a", "b", "c"],
    ]


# ---- 編集したのに判定がないスライドがあると、回答のコピーを止める ----
def blocked_state(page, nn, at):
    """nn でコピーを押すと止まり、at のスライドへ移って案内（橙の .rv-warn）が出る。"""
    assert copy_md(page, nn, approve=False) is None
    assert page.evaluate("!!window.__submitted") is False
    assert page.evaluate(CUR) == at
    st = f'.pane[data-slide="{at}"] .state'
    assert f"S{at} は文字を直していますが、承認か要修正が押されていません" in page.inner_text(st)
    assert page.evaluate(f"document.querySelector('{st}').classList.contains('rv-warn')") is True


def test_文字を直して判定のないスライドがあるとコピーが止まり承認すれば出せる(open_page):
    page = open_page(make_page())
    page.evaluate("setEditing(true)")
    page.click('.pane[data-slide="01"] .verdict .ok')  # 01 を承認して 02 へ
    edit(page, '.pane[data-slide="02"] .big .pp-text', "直した題")  # 02 は直しただけ
    go(page, "01")
    blocked_state(page, "01", "02")  # 02 へ移って知らせる
    page.click('.pane[data-slide="02"] .verdict .ok')
    md = copy_md(page, "02", approve=False)
    assert (
        "## S02\n- 選択: A\n- 判定: 承認\n- コメント: \n"
        '- 編集: {"f":"02-A","t":"t0","before":"題02a","after":"直した題"}'
    ) in md
    assert page.evaluate("window.__submitted") is True


def test_要修正のスライドで文字を直していてもコピーできる(open_page):
    page = open_page(make_page())
    page.evaluate("setEditing(true)")
    edit(page, BIG + ".pp-text", "直した題")
    page.fill('.pane[data-slide="01"] .cm', "数字を確かめる")
    page.click('.pane[data-slide="01"] .verdict .ng')  # 要修正（コメントあり）で 02 へ
    md = copy_md(page, "02", approve=False)
    assert "## S01\n- 選択: \n- 判定: 要修正\n- コメント: 数字を確かめる\n- 編集: " in md
    assert "## S02" not in md


def test_リセットで編集の記録を消したスライドはコピーを止めない(open_page):
    page = open_page(make_page())
    page.evaluate("setEditing(true)")
    page.click(BIG + ".pp-text")
    page.keyboard.press("Control+A")
    page.click(BAR + '[data-ed="bold"]')
    page.click(BAR + '[data-ed="reset"]')  # 元に戻すと記録は消える
    assert copy_md(page, "01", approve=False) is None
    state = page.inner_text('.pane[data-slide="01"] .state')
    assert "承認か要修正を選んだスライドがありません" in state  # 直しの止め方ではなく、これまでの案内
    assert "文字を直して" not in state
    go(page, "02")
    page.click('.pane[data-slide="02"] .verdict .ok')
    md = copy_md(page, "02", approve=False)
    assert "## S01" not in md
    assert "- 編集:" not in md


def test_最終ページでも文字を直して判定のないスライドがあるとコピーが止まる(open_page):
    frags = {"01": {"A": FRAG.format(n="01a")}, "02": {"A": FRAG.format(n="02a")}}
    page = open_page(variants._page(Path("deck"), frags, "final", final=True, ids={"01": "01-A", "02": "02-A"}))
    page.check('.pane[data-slide="01"] .rv-edit-toggle')
    edit(page, BIG + ".pp-text", "最終で直す")
    go(page, "02")
    page.click('.pane[data-slide="02"] .verdict .ok')
    blocked_state(page, "02", "01")
    page.click('.pane[data-slide="01"] .verdict .ok')  # 承認で 02 へ
    md = copy_md(page, "02", approve=False)
    assert '## S01\n- 選択: A\n- 判定: 承認\n- コメント: \n- 編集: {"f":"01-A"' in md


# ---- 選ばれた断片の印（review_final） ----
def test_最終レビューは回答で選ばれた案とデザインの断片に印を付ける(tmp_path):
    work = tmp_path
    (work / "slides").mkdir()
    for name in ("01-A", "01-B", "01-B-d2", "02-A"):
        (work / "slides" / f"{name}.html").write_text(FRAG.format(n=name), encoding="utf-8")
    md = "## S01\n- 選択: B\n- デザイン: 2\n- 判定: 承認\n- コメント: \n## S02\n- 選択: A\n- 判定: 承認\n- コメント: \n"
    html = variants.review_final(work, md).read_text(encoding="utf-8")
    assert 'data-f="01-B-d2"' in html
    assert 'data-f="02-A"' in html
    assert 'data-f="01-A"' not in html
