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


# 「フォルダを読み直す」の外部（ブラウザのフォルダ選択）の代わり。window.__pick に
# {name, spec}（spec はファイル名 -> null、フォルダ名 -> 入れ子の spec。"unreadable" はそのフォルダの values() が
# 例外を出す）か {error: 例外名} を入れて使う
NOT_AUTOMATED = "Object.defineProperty(navigator, 'webdriver', {get: () => false});\n"
FAKE_PICKER = (
    NOT_AUTOMATED
    + """
window.__mkdir = function mk(name, spec) {
  return {kind: 'directory', name: name, values: async function* () {
    if (spec === 'unreadable') throw new DOMException('読めません', 'NotAllowedError');
    for (const k of Object.keys(spec)) yield spec[k] === null ? {kind: 'file', name: k} : mk(k, spec[k]);
  }};
};
window.showDirectoryPicker = async function (opts) {
  window.__pickOpts = opts;
  const p = window.__pick;
  if (p.error) throw new DOMException('選択しませんでした', p.error);
  return window.__mkdir(p.name, p.spec);
};
"""
)
NO_PICKER = NOT_AUTOMATED + "window.showDirectoryPicker = undefined;"
LOADED = datetime(2026, 10, 24, 9, 5)


@pytest.fixture
def open_start(browser, work, tmp_path):
    pages = []

    def _open(init=FAKE_PICKER, cwd=None):
        f = start_page.build(cwd or work, tmp_path / "start-page.html")
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        pages.append(page)
        page.clock.set_fixed_time(LOADED)
        page.add_init_script(init)
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
    assert page.inner_text("#reread-hint") == (
        "選んだフォルダの名前だけで作業フォルダか確認します。別の場所の同名フォルダを選ぶと、実在しないパスが並びます"
    )


@slow
def test_ファイルがないときはコピーせず案内を出す(open_start):
    page = open_start()
    page.click("#copy")
    assert page.evaluate("window.__submitted === true") is False
    assert "ファイル" in page.inner_text("#state")


# ---- フォルダを読み直す ----


def _reread(page, name="作業 フォルダ", spec=None, error=None) -> None:
    page.evaluate("p => { window.__pick = p; }", {"name": name, "spec": spec or {}, "error": error})
    page.click("#reread")
    page.wait_for_function("!document.querySelector('#reread').disabled")  # 読み終わるとボタンが戻る


def _open_folder(page, path: Path) -> None:
    """入力のツリーのフォルダを選ぶ（閉じた <details> の中の行も押せるように、DOM で押す）。"""
    page.evaluate(
        "p => [...document.querySelectorAll('#tree-in .row[data-node]')].find(e => e.dataset.node === p).click()",
        str(path),
    )


def _attrs(page, sel: str, attr: str) -> list[str]:
    return page.eval_on_selector_all(sel, f"es => es.map(e => e.getAttribute({json.dumps(attr)}))")


ORIGINAL = {"稟議書 2026.docx": None, "予算案.pdf": None, "成果物": {}}


@slow
def test_読み直すと新しいファイルとフォルダが入力と保存先の両方に出て時刻が変わる(open_start, work):
    page = open_start()
    assert page.inner_text("#read-at") == "読み込み: 09:05"
    page.clock.set_fixed_time(datetime(2026, 10, 24, 9, 30))

    _reread(page, spec={**ORIGINAL, "新規.md": None, "新しい": {"中.txt": None}})

    assert page.evaluate("window.__pickOpts") == {"mode": "read"}
    assert page.inner_text("#read-at") == "読み込み: 09:30"
    assert page.inner_text("#reread-msg") == ""
    assert _attrs(page, "#tree-in .row[data-node]", "data-node") == [
        str(work),
        str(work / "成果物"),
        str(work / "新しい"),
    ]
    assert _attrs(page, "#tree-out input[data-dir]", "data-dir") == [
        str(work),
        str(work / "成果物"),
        str(work / "新しい"),
    ]
    assert _attrs(page, "#files input[data-file]", "data-file") == [
        str(work / f) for f in ("予算案.pdf", "新規.md", "稟議書 2026.docx")
    ]
    _open_folder(page, work / "新しい")
    page.check(_sel("data-file", work / "新しい" / "中.txt"))
    assert _copy(page)["files"] == [str(work / "新しい" / "中.txt")]


@slow
def test_読み直しで消えたファイルのチェックは外れ残ったファイルと保存先の選択は保たれる(open_start, work):
    page = open_start()
    page.check(_sel("data-file", work / "予算案.pdf"))
    page.check(_sel("data-file", work / "稟議書 2026.docx"))
    page.check(_sel("data-dir", work / "成果物"))

    _reread(page, spec={"稟議書 2026.docx": None, "成果物": {}})

    assert page.inner_text("#reread-msg") == ""  # 保存先は残っているので通知しない
    assert page.is_checked(_sel("data-file", work / "稟議書 2026.docx"))
    assert page.inner_text("#chosen-files") == str(work / "稟議書 2026.docx")
    r = _copy(page)
    assert r["files"] == [str(work / "稟議書 2026.docx")]
    assert r["out_dir"] == str(work / "成果物")


@slow
def test_読み直しても開いていたフォルダが残っていればその一覧を出す(open_start, work):
    page = open_start()
    _open_folder(page, work / "成果物")

    _reread(page, spec={**ORIGINAL, "成果物": {"追加.md": None}})

    assert page.inner_text("#folder-h") == str(work / "成果物")
    assert _attrs(page, "#files input[data-file]", "data-file") == [str(work / "成果物" / "追加.md")]


@slow
def test_読み直しで選んでいた保存先とフォルダが消えたら作業フォルダに戻る(open_start, work):
    page = open_start()
    page.check(_sel("data-file", work / "予算案.pdf"))
    _open_folder(page, work / "成果物")  # 右の一覧を 成果物 にする（予算案.pdf のチェックは残る）
    page.check(_sel("data-dir", work / "成果物"))

    _reread(page, spec={"予算案.pdf": None})

    assert page.inner_text("#reread-msg") == "選んでいた保存先が見つからないため、作業フォルダに戻しました"
    assert page.inner_text("#folder-h") == str(work)
    assert page.is_checked(_sel("data-dir", work))
    r = _copy(page)
    assert (r["files"], r["out_dir"]) == ([str(work / "予算案.pdf")], str(work))

    _reread(page, error="AbortError")  # 次の操作（取り消しでも）で前の通知は消える
    assert page.inner_text("#reread-msg") == ""


@slow
def test_違う名前のフォルダを選ぶと警告を出して一覧を変えない(open_start, work):
    page = open_start()
    page.check(_sel("data-file", work / "予算案.pdf"))

    _reread(page, name="別のフォルダ", spec={"x.md": None})

    msg = page.locator("#reread-msg")
    assert (
        msg.inner_text()
        == "選んだフォルダ名（別のフォルダ）が作業フォルダ（作業 フォルダ）と違います。作業フォルダを選んでください"
    )
    assert "sp-warn" in msg.get_attribute("class")
    assert _attrs(page, "#files input[data-file]", "data-file") == [
        str(work / "予算案.pdf"),
        str(work / "稟議書 2026.docx"),
    ]
    assert page.is_checked(_sel("data-file", work / "予算案.pdf"))
    assert page.inner_text("#read-at") == "読み込み: 09:05"

    _reread(page, error="AbortError")  # 取り消しても、前の警告は残さない
    assert page.inner_text("#reread-msg") == ""


@slow
def test_作業フォルダそのものが読めないときは警告を出して一覧を変えない(open_start, work):
    page = open_start()
    page.check(_sel("data-file", work / "予算案.pdf"))

    _reread(page, spec="unreadable")

    msg = page.locator("#reread-msg")
    assert msg.inner_text() == "フォルダを読み直せませんでした（NotAllowedError）"
    assert "sp-warn" in msg.get_attribute("class")
    assert _attrs(page, "#files input[data-file]", "data-file") == [
        str(work / "予算案.pdf"),
        str(work / "稟議書 2026.docx"),
    ]
    assert page.is_checked(_sel("data-file", work / "予算案.pdf"))
    assert page.inner_text("#read-at") == "読み込み: 09:05"


@slow
def test_読めないサブフォルダは中身なしで出し警告しない(open_start, work):
    page = open_start()

    _reread(page, spec={"a.md": None, "読めない": "unreadable"})

    assert page.inner_text("#reread-msg") == ""
    assert _attrs(page, "#tree-in .row[data-node]", "data-node") == [str(work), str(work / "読めない")]
    assert _attrs(page, "#files input[data-file]", "data-file") == [str(work / "a.md")]


@slow
def test_フォルダ名の大文字小文字の違いは同じフォルダとして読み直す(open_start, tmp_path):
    cwd = tmp_path / "Deck Work"
    cwd.mkdir()
    page = open_start(cwd=cwd)

    _reread(page, name="deck WORK", spec={"a.md": None})

    assert page.inner_text("#reread-msg") == ""
    assert _attrs(page, "#files input[data-file]", "data-file") == [str(cwd / "a.md")]


@slow
@pytest.mark.parametrize(
    ("error", "msg"),
    [("AbortError", ""), ("NotAllowedError", "フォルダを読み直せませんでした（NotAllowedError）")],
    ids=["取り消しは何も出さない", "ほかの失敗は案内を出す"],
)
def test_フォルダの選択が失敗しても一覧を変えずページは動く(open_start, work, error, msg):
    page = open_start()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.check(_sel("data-file", work / "予算案.pdf"))

    _reread(page, error=error)

    assert errors == []
    assert page.inner_text("#reread-msg") == msg
    assert page.inner_text("#read-at") == "読み込み: 09:05"
    assert _attrs(page, "#files input[data-file]", "data-file") == [
        str(work / "予算案.pdf"),
        str(work / "稟議書 2026.docx"),
    ]
    assert _copy(page)["files"] == [str(work / "予算案.pdf")]


@slow
def test_フォルダ選択がないブラウザではボタンを無効にして案内を出す(open_start):
    page = open_start(init=NO_PICKER)
    assert page.is_disabled("#reread")
    assert (
        page.inner_text("#reread-msg")
        == "このブラウザでは使えません（Chrome か Edge で開くか、ページを作り直してください）"
    )
    assert page.inner_text("#read-at") == "読み込み: 09:05"


@slow
def test_自動操作のブラウザでは読み直しの代わりにページの作り直しをClaudeに頼む(open_start):
    # Playwright が起動したブラウザは navigator.webdriver が true（Claude 操作用のブラウザと同じ）
    page = open_start(init="window.showDirectoryPicker = () => { window.__picked = true; };")
    assert page.inner_text("#reread") == "フォルダを読み直す"
    assert page.evaluate("window.__regenerate") is None
    page.click("#reread")
    assert page.evaluate("window.__regenerate") is True
    assert "開始ページの作り直しを頼みました" in page.inner_text("#reread-msg")
    assert page.evaluate("window.__picked") is None  # フォルダ選択は開かない
    assert not page.is_disabled("#reread")  # 頼みが届かなかったときに、もう一度押せる
    assert page.evaluate("window.__submitted") is None  # 回答ではない


@slow
def test_読み直しでも隠し_ロック_除外のフォルダと対象外の拡張子は出ない(open_start, work):
    page = open_start()
    spec = {
        ".hidden": {"a.md": None},
        ".h.md": None,
        "~$a.docx": None,
        ".git": {"y.md": None},
        "node_modules": {"y.md": None},
        "pptx-deck-source": {"deck": {"script.md": None}},
        "f.xlsx": None,
        "g.png": None,
        "e.TXT": None,
        "B.PDF": None,
        "a.md": None,
        "資料": {"x.docx": None},
    }

    _reread(page, spec=spec)

    assert _attrs(page, "#tree-in .row[data-node]", "data-node") == [str(work), str(work / "資料")]
    assert _attrs(page, "#files input[data-file]", "data-file") == [str(work / f) for f in ("a.md", "B.PDF", "e.TXT")]


@slow
def test_読み直しでも深さと件数の上限は_scan_と同じ(open_start, work):
    page = open_start()
    spec = {
        "a": {"b": {"c": {"c.md": None, "d": {"d.md": None}}}},
        "many": {f"{i:03}.md": None for i in reversed(range(205))},
    }

    _reread(page, spec=spec)

    c = work / "a" / "b" / "c"
    assert _attrs(page, "#tree-in .row[data-node]", "data-node") == [
        str(work),
        str(work / "a"),
        str(work / "a" / "b"),
        str(c),
        str(work / "many"),
    ]  # 深さ 4 の d は辿らない
    _open_folder(page, c)
    assert _attrs(page, "#files input[data-file]", "data-file") == [str(c / "c.md")]
    _open_folder(page, work / "many")
    files = _attrs(page, "#files input[data-file]", "data-file")
    assert (len(files), files[0], files[-1]) == (200, str(work / "many" / "000.md"), str(work / "many" / "199.md"))
