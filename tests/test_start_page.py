"""開始ページ（start-page.html）: 埋め込むデータと、画面の選択から出る回答 md。

画面操作は Chromium を実際に起動して確かめる（slow）。
"""

# ruff: noqa: S101  # pytest の assert
import json
import re
import tempfile
from datetime import datetime
from pathlib import Path

import pytest
from pptx_deck import cli, intake, start_page

slow = pytest.mark.slow
BODY = "一行目\n\n## 見出し\n- 名前: 上書き\n二行目"  # 本文の見出し・箇条書きも本文のまま
_DATA = re.compile(r"var DATA = (.*?);\n", re.DOTALL)


def _embedded(html: str) -> dict:
    return json.loads(_DATA.search(html).group(1))


@pytest.fixture
def temp_root(tmp_path, monkeypatch):
    """OS の一時フォルダを tmp_path の下に向ける（開始ページを本物の一時フォルダに書かない）。"""
    root = tmp_path / "os-temp"
    root.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(root))
    return root


def test_埋め込んだデータが_JSON_として読め_閉じタグで壊れない():
    data = {"cwd": r"C:\x</script><script>alert(1)</script>", "places": []}
    html = start_page.render(data)
    template = (start_page.TEMPLATE).read_text(encoding="utf-8")
    assert html.count("</script>") == template.count("</script>")  # データの中の閉じタグで script が切れない
    assert _embedded(html) == data


def test_build_は作業フォルダの一覧を埋め込んで書き出す(tmp_path):
    cwd = tmp_path / "作業 フォルダ"
    (cwd / "資料").mkdir(parents=True)
    (cwd / "資料" / "稟議書.docx").write_text("x", encoding="utf-8")

    out = start_page.build(cwd, tmp_path / "page.html")

    assert out == tmp_path / "page.html"
    data = _embedded(out.read_text(encoding="utf-8"))
    assert data["cwd"] == str(cwd)
    assert [(p["label"], p["path"]) for p in data["places"]] == [("作業フォルダ", str(cwd))]
    assert data["places"][0]["tree"]["dirs"][0]["files"] == [str(cwd / "資料" / "稟議書.docx")]


def test_cli_start_page_はページのパスを1行で出す(tmp_path, temp_root, monkeypatch, capsys):
    cwd = tmp_path / "作業"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    assert cli.main(["start-page"]) == 0
    out = capsys.readouterr().out
    assert out.count("\n") == 1
    page = Path(out.strip())
    assert page.name == "start-page.html"
    assert page.is_relative_to(temp_root)
    assert _embedded(page.read_text(encoding="utf-8"))["cwd"] == str(cwd)


def test_start_page_は呼ぶたびに別のパスに作る(tmp_path, temp_root):
    assert start_page.build(tmp_path) != start_page.build(tmp_path)


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
def work(tmp_path):
    """作業フォルダ（日本語・空白入り）に、ファイルと保存先の候補のフォルダを置く。"""
    cwd = tmp_path / "作業 フォルダ"
    for f in ("稟議書 2026.docx", "予算案.pdf"):
        (cwd / f).parent.mkdir(parents=True, exist_ok=True)
        (cwd / f).write_text("x", encoding="utf-8")
    (cwd / "成果物").mkdir()
    return cwd


LOADED = datetime(2026, 10, 24, 9, 5)


@pytest.fixture
def open_start(browser, work, tmp_path):
    pages = []

    def _open():
        f = start_page.build(work, tmp_path / "start-page.html")
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        pages.append(page)
        page.clock.set_fixed_time(LOADED)
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
    page.fill("#text", BODY)
    page.fill("#name", "メモ")

    r = _copy(page)

    assert (r["kind"], r["files"], r["text"], r["name"]) == ("text", [], BODY, "メモ")


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
def test_画面の表示は保存先と呼び_旧称を使わない(open_start):
    page = open_start()
    shown = page.inner_text("main") + "".join(_attrs(page, "[placeholder]", "placeholder")) + page.title()
    assert "出力先" not in shown
    assert page.inner_text("#h-out") == "保存先フォルダ"
    assert "パス欄に手動でパスを書く" in page.get_attribute("#path-out", "placeholder")
    assert (
        page.inner_text("#reread-hint")
        == "押すと Claude が作業フォルダを読み直し、開始ページを開き直します（選んだ内容は消えます）"
    )


@slow
def test_ファイルがないときはコピーせず案内を出す(open_start):
    page = open_start()
    page.click("#copy")
    assert page.evaluate("window.__submitted === true") is False
    assert "ファイル" in page.inner_text("#state")


# ---- フォルダを読み直す ----


def _attrs(page, sel: str, attr: str) -> list[str]:
    return page.eval_on_selector_all(sel, f"es => es.map(e => e.getAttribute({json.dumps(attr)}))")


@slow
def test_読み込みの時刻を出す(open_start):
    assert open_start().inner_text("#read-at") == "読み込み: 09:05"


@slow
def test_読み直すと_Claudeにページの作り直しを頼む(open_start):
    page = open_start()
    assert page.inner_text("#reread") == "フォルダを読み直す"
    assert page.evaluate("window.__regenerate") is None
    page.click("#reread")
    assert page.evaluate("window.__regenerate") is True
    assert "開始ページの作り直しを頼みました" in page.inner_text("#reread-msg")
    assert not page.is_disabled("#reread")  # 頼みが届かなかったときに、もう一度押せる
    assert page.evaluate("window.__submitted") is None  # 回答ではない
