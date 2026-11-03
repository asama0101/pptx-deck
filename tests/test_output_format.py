"""最終成果物の形式の選択（variants.html）と、output-format コマンド。"""

# ruff: noqa: S101  # pytest の assert
import pytest
from pptx_deck import cli, variants

FRAG = (
    '<section class="slide" data-layout="content" data-variant="{n}｜理由" style="position:relative;width:1280px;'
    'height:720px">'
    '<div class="pp-text" data-role="title" style="position:absolute;left:64px;top:30px;width:900px;height:40px">'
    "題{n}</div>"
    "</section>"
)
MD_HEAD = "---\nround: 1\n---\n"


@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        b = pw.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def prepare(browser, tmp_path):
    """レビューページ（variants._page）を作ってブラウザで開く。out_format は前の回から引き継いだ形式。"""
    pages = []

    def _prepare(out_format="pptx"):
        frags = {nn: {"A": FRAG.replace("{n}", nn + "a"), "B": FRAG.replace("{n}", nn + "b")} for nn in ("01", "02")}
        f = tmp_path / "p.html"
        f.write_text(variants._page(tmp_path / "deck", frags, "1", out_format=out_format), encoding="utf-8")
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        pages.append(page)
        page.goto(f.as_uri())
        page.wait_for_timeout(200)
        return page

    yield _prepare
    for p in pages:
        p.close()


def copy_answers(page):
    """スライド 01 を要修正にして（コメントが要る）「回答をコピー」を押し、コピーされた回答 md を返す。"""
    if page.get_attribute('.pane[data-slide="01"] .verdict .ng', "aria-pressed") != "true":
        page.fill('.pane[data-slide="01"] .cm', "x")  # 要修正は修正事項が要る。付けると次へ進むので戻る
        page.click('.pane[data-slide="01"] .verdict .ng')
        page.click('#nav button[data-go="01"]')
    page.evaluate("window.__answersMd = ''")
    page.click('.pane[data-slide="01"] .copyBtn')
    return page.evaluate("window.__answersMd")


@pytest.mark.slow
def test_既定の形式_pptx_では_回答に出力形式の行を出さない(prepare):
    page = prepare()
    assert page.input_value("#rvFormat") == "pptx"
    assert page.eval_on_selector_all("#rvFormat option", "e => e.map(o => o.value)") == ["pptx", "html", "both"]
    assert "- 出力形式:" not in copy_answers(page)


@pytest.mark.slow
def test_形式を変えると回答に出力形式の行が出て_元に戻すと消える(prepare):
    page = prepare()
    page.select_option("#rvFormat", "html")
    assert "---\n- 出力形式: html\n## S01" in copy_answers(page)
    page.select_option("#rvFormat", "pptx")
    assert "- 出力形式:" not in copy_answers(page)


@pytest.mark.slow
def test_前の回の形式を引き継ぎ_触らなければ行を出さず_初期値へ戻した選択は残す(prepare):
    page = prepare("html")
    assert page.input_value("#rvFormat") == "html"
    assert "- 出力形式:" not in copy_answers(page)  # 触らなければ行は出ない（前の回の行が有効）
    page.select_option("#rvFormat", "pptx")
    md = copy_answers(page)
    assert "---\n- 出力形式: pptx\n## S01" in md  # 初期値へ戻した選択も残す
    assert variants.parse_settings([MD_HEAD + "- 出力形式: html\n", md])["format"] == "pptx"


def test_assemble_は前の回の出力形式を次のページの初期値に引き継ぐ(tmp_path):
    work = tmp_path / "out" / "pptx-deck-source" / "deck"
    (work / "slides").mkdir(parents=True)
    (work / "slides" / "01-A.html").write_text(FRAG.replace("{n}", "a"), encoding="utf-8")
    (work / "answers-1.md").write_text(MD_HEAD + "- 出力形式: both\n", encoding="utf-8")
    html = variants.assemble(work, 2).read_text(encoding="utf-8")
    assert 'data-init="both"' in html


def test_出力形式の既定は_pptx(tmp_path):
    assert variants.output_format(tmp_path) == "pptx"
    (tmp_path / "answers-1.md").write_text(MD_HEAD + "## S01\n- 選択: A\n", encoding="utf-8")
    assert variants.output_format(tmp_path) == "pptx"


def test_出力形式は最終確認も含め_後の回が勝つ(tmp_path):
    (tmp_path / "answers-1.md").write_text(MD_HEAD + "- 出力形式: html\n", encoding="utf-8")
    assert variants.output_format(tmp_path) == "html"
    (tmp_path / "answers-final.md").write_text(MD_HEAD + "- 出力形式: both\n", encoding="utf-8")
    assert variants.output_format(tmp_path) == "both"


def test_output_format_コマンドは形式を1行で出力する(tmp_path, capsys):
    work = tmp_path / "out" / "pptx-deck-source" / "deck"
    work.mkdir(parents=True)
    (work / "answers-1.md").write_text(MD_HEAD + "- 出力形式: html\n", encoding="utf-8")
    code = cli.main(["output-format", str(work)])
    assert code == 0
    assert capsys.readouterr().out == "html\n"
