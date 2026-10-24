"""開始ページ（start-page.html）: 埋め込むデータと、画面の選択から出る回答 md。

画面操作は Chromium を実際に起動して確かめる（slow）。
"""

# ruff: noqa: S101  # pytest の assert
import json
import re
from pathlib import Path

import pytest
from pptx_deck import cli, intake, start_page

slow = pytest.mark.slow
_DATA = re.compile(r"var DATA = (.*?);\n", re.DOTALL)


def _embedded(html: str) -> dict:
    return json.loads(_DATA.search(html).group(1))


@pytest.fixture
def home(monkeypatch, tmp_path):
    """最近使った場所の記録を、空の置き場にする（本物の置き場を読み書きしない）。"""
    h = tmp_path / "pptx-home"
    h.mkdir()
    monkeypatch.setenv("PPTX_DECK_HOME", str(h))
    return h


def test_埋め込んだデータが_JSON_として読め_閉じタグで壊れない():
    data = {"cwd": r"C:\x</script><script>alert(1)</script>", "places": []}
    html = start_page.render(data)
    template = (start_page.TEMPLATE).read_text(encoding="utf-8")
    assert html.count("</script>") == template.count("</script>")  # データの中の閉じタグで script が切れない
    assert _embedded(html) == data


def test_build_は作業フォルダの一覧を埋め込んで書き出す(tmp_path, home):
    cwd = tmp_path / "作業 フォルダ"
    (cwd / "資料").mkdir(parents=True)
    (cwd / "資料" / "稟議書.docx").write_text("x", encoding="utf-8")

    out = start_page.build(cwd, tmp_path / "page.html")

    assert out == tmp_path / "page.html"
    data = _embedded(out.read_text(encoding="utf-8"))
    assert data["cwd"] == str(cwd)
    assert data["places"][0]["tree"]["dirs"][0]["files"] == [str(cwd / "資料" / "稟議書.docx")]


def test_cli_start_page_はページのパスを1行で出す(tmp_path, home, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert cli.main(["start-page"]) == 0
    out = capsys.readouterr().out
    assert out.count("\n") == 1
    page = Path(out.strip())
    assert page.name == "start-page.html"
    assert _embedded(page.read_text(encoding="utf-8"))["cwd"] == str(tmp_path)


# ---- 画面の操作 ----


@pytest.fixture
def browser():
    """テストごとに起動する。measure など本体も sync_playwright を使うので、同時に生かさない。"""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        b = pw.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def work(tmp_path, home):
    """作業フォルダ（日本語・空白入り）に、ファイルと出力先の候補のフォルダを置く。"""
    cwd = tmp_path / "作業 フォルダ"
    for f in ("稟議書 2026.docx", "予算案.pdf"):
        (cwd / f).parent.mkdir(parents=True, exist_ok=True)
        (cwd / f).write_text("x", encoding="utf-8")
    (cwd / "成果物").mkdir()
    return cwd


@pytest.fixture
def open_start(browser, work, tmp_path):
    pages = []

    def _open():
        f = start_page.build(work, tmp_path / "start-page.html")
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        pages.append(page)
        page.goto(f.as_uri())
        return page

    yield _open
    for p in pages:
        p.close()


def _copy(page) -> dict:
    page.click("#copy")
    assert page.evaluate("window.__submitted") is True
    return intake.parse(page.evaluate("window.__answersMd"))


def _sel(attr: str, path: Path) -> str:
    return f"input[{attr}={json.dumps(str(path), ensure_ascii=False)}]"  # CSS の文字列では \\ が \ になる


@slow
def test_ファイルの選択とパス欄の追記が両方出る(open_start, work):
    page = open_start()
    page.check(_sel("data-file", work / "予算案.pdf"))
    page.check(_sel("data-file", work / "稟議書 2026.docx"))
    page.fill("#path-files", "C:\\外\\追加 1.docx\n\n  C:\\外\\追加2.md  \n")
    page.fill("#name", "稟議 書")

    r = _copy(page)

    assert r["kind"] == "file"
    assert r["files"] == [  # 選んだ順、続けてパス欄
        str(work / "予算案.pdf"),
        str(work / "稟議書 2026.docx"),
        "C:\\外\\追加 1.docx",
        "C:\\外\\追加2.md",
    ]
    assert r["name"] == "稟議 書"
    assert r["out_dir"] == str(work)  # 既定は作業フォルダ


@slow
def test_テキスト種別は本文と名前が出てファイルは出ない(open_start, work):
    page = open_start()
    page.check(_sel("data-file", work / "予算案.pdf"))
    page.check("input[name=kind][value=text]")
    page.fill("#text", "一行目\n\n二行目")
    page.fill("#name", "メモ")

    r = _copy(page)

    assert (r["kind"], r["files"], r["text"], r["name"]) == ("text", [], "一行目\n\n二行目", "メモ")


@slow
def test_出力先は選択よりパス欄を優先する(open_start, work):
    page = open_start()
    page.check(_sel("data-file", work / "予算案.pdf"))
    page.check(_sel("data-dir", work / "成果物"))
    assert _copy(page)["out_dir"] == str(work / "成果物")

    page.fill("#path-out", "D:\\出力 先")
    assert _copy(page)["out_dir"] == "D:\\出力 先"


@slow
def test_引用符付きのパス欄も_intake_parse_で外れる(open_start, work):
    page = open_start()
    page.fill("#path-files", '"C:\\a b\\資料.docx"')
    page.fill("#path-out", '"C:\\out dir"')

    r = _copy(page)

    assert r["files"] == ["C:\\a b\\資料.docx"]
    assert r["out_dir"] == "C:\\out dir"
    assert r["name"] == ""


@slow
def test_ファイルがないときはコピーせず案内を出す(open_start):
    page = open_start()
    page.click("#copy")
    assert page.evaluate("window.__submitted === true") is False
    assert "ファイル" in page.inner_text("#state")
