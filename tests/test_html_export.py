"""export-html: final.html を 1 枚の自己完結 HTML にする。"""

# ruff: noqa: S101  # pytest の assert
import base64
import re
import shutil
from pathlib import Path

import pytest
from pptx_deck import cli, htmlexport, initdir, paths, variants

FRAGS = ["charts/bar.html", "diagrams/parallel-d2.html", "tables/actions-d2.html"]
BAR_RECT = '<rect x="8" y="8" width="720" height="350" rx="6" class="sv-f-white sv-s-line" stroke-width="2"/>'
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


@pytest.fixture
def make(tmp_path, pkg):
    """init した作業フォルダに、断片を並べた final.html を置く。(base, work) を返す。"""

    def _make(frags=FRAGS):
        base = tmp_path / "demo"
        initdir.init(base, color="navy")
        work = paths.resolve_work(base)
        body = "\n".join((pkg / "assets" / "components" / f).read_text(encoding="utf-8") for f in frags)
        (work / "final.html").write_text(
            variants.HEAD.format(title="demo", extra="") + body + "</body></html>", encoding="utf-8"
        )
        return base, work

    return _make


@pytest.fixture
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def run(capsys, *argv):
    rc = cli.main(list(argv))
    cap = capsys.readouterr()
    return rc, cap.out, cap.err


def edit_final(work, old, new):
    fin = work / "final.html"
    t = fin.read_text(encoding="utf-8")
    assert old in t
    fin.write_text(t.replace(old, new, 1), encoding="utf-8")


def external_img_refs(html):
    body = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    return re.findall(r'<(?:image|img)\b[^>]*?\b(?:xlink:)?(?:href|src)="(?!data:)[^"]*"', body)


def open_offline(browser, html_path, tmp_path, selector):
    """出力 HTML を、元の作業フォルダと無関係な場所へ写して開く。失敗した要求と、要素が出たかを返す。"""
    empty = tmp_path / "empty"
    empty.mkdir()
    dst = empty / "out.html"
    shutil.copy(html_path, dst)
    failed = []
    page = browser.new_page()
    page.on("requestfailed", lambda q: failed.append(q.url))
    page.goto(dst.as_uri())
    page.wait_for_selector(selector)
    return page, failed


def test_外部参照が残らず1枚で完結する(make):
    _, work = make()
    html = htmlexport.build_html(work)
    for s in ('href="theme.css"', 'href="base.css"', 'src="icons/', 'src="chart-preview.js"'):
        assert s not in html
    assert "data:image/svg+xml" in html
    assert len(re.findall(r"</script>", html)) == len(re.findall(r"<script", html))


def test_スライドを順に積み編集UIを含まない(make):
    _, work = make()
    html = htmlexport.build_html(work)
    assert len(re.findall(r'<section class="slide"', html)) == 3
    assert len(re.findall(r'<div class="frame">', html)) == 3
    assert "contenteditable" not in html
    assert "<select" not in html
    assert "近似" in html


def test_final_htmlがなければValueError(tmp_path):
    base = tmp_path / "demo"
    initdir.init(base, color="navy")
    with pytest.raises(ValueError, match="final.html"):
        htmlexport.build_html(paths.resolve_work(base))


def test_画像が見つからなければmissingに載せ参照はそのまま残す(make):
    _, work = make()
    shutil.rmtree(work / "icons")
    r = htmlexport.export(work)
    assert r["missing"] == ["icons/clock-accent.svg", "icons/coin-accent.svg", "icons/shield-accent.svg"]
    assert 'src="icons/' in Path(r["html"]).read_text(encoding="utf-8")


def test_export_htmlコマンドは作品名のhtmlを書く(make, capsys):
    base, _ = make()
    rc, out, err = run(capsys, "export-html", str(base))
    assert rc == 0, err
    html = (base / "demo.html").read_text(encoding="utf-8")
    assert html.count('<section class="slide"') == 3
    assert '"missing": []' in out


def test_export_htmlのpruneはfinal_htmlを消す(make, capsys):
    base, work = make()
    assert run(capsys, "export-html", str(base), "--prune")[0] == 0
    assert not (work / "final.html").exists()
    assert (base / "demo.html").is_file()


@pytest.mark.slow
def test_グラフが外部ファイルなしでオフラインで描かれる(make, tmp_path, browser):
    _, work = make()
    r = htmlexport.export(work)
    page, failed = open_offline(browser, r["html"], tmp_path, ".pp-chart svg")
    imgs = page.eval_on_selector_all("img", "e=>e.map(i=>i.naturalWidth)")
    assert failed == []
    assert imgs
    assert all(w > 0 for w in imgs)


@pytest.mark.slow
def test_絵の画像参照が埋め込まれオフラインで開ける(make, tmp_path, browser):
    _, work = make(["pictures/annotate.html"])
    (work / "material").mkdir()
    (work / "material" / "x.png").write_bytes(PNG)
    edit_final(
        work,
        BAR_RECT,
        '<image href="material/x.png" x="8" y="8" width="720" height="350"/>'
        '<image xlink:href="material/x.png" x="8" y="8" width="10" height="10"/>',
    )
    r = htmlexport.export(work)
    assert r["missing"] == []
    out = Path(r["html"]).read_text(encoding="utf-8")
    assert "material/x.png" not in out
    assert external_img_refs(out) == []
    page, failed = open_offline(browser, r["html"], tmp_path, ".pp-picture svg")
    assert failed == []


def img_export(make, tag, files=()):
    _, work = make(["charts/bar.html"])
    for name in files:
        f = work / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"\x89PNG")
    edit_final(work, "</section>", tag + "</section>")
    r = htmlexport.export(work)
    return r, Path(r["html"]).read_text(encoding="utf-8")


def test_単一引用符のsrcも埋め込む(make):
    r, out = img_export(make, "<img class='pp-image' alt='a' src='material/logo.png'>", ["material/logo.png"])
    assert r["missing"] == []
    assert "data:image/png;base64," in out
    assert "material/logo.png" not in out


def test_単一引用符のsrcが無ければmissingに載せる(make):
    r, _ = img_export(make, "<img class='pp-image' alt='a' src='material/none.png'>")
    assert r["missing"] == ["material/none.png"]


def test_パーセントエンコードのsrcを復号して埋め込む(make):
    r, out = img_export(make, '<img class="pp-image" alt="a" src="material/%E5%9B%B3%201.png">', ["material/図 1.png"])
    assert r["missing"] == []
    assert "data:image/png;base64," in out


def test_パーセントエンコードのsrcが無ければ元の綴りでmissingに載せる(make):
    r, _ = img_export(make, '<img class="pp-image" alt="a" src="material/%E5%9B%B3.png">')
    assert r["missing"] == ["material/%E5%9B%B3.png"]


def test_絵の画像参照が無ければmissingに載せる(make):
    _, work = make(["pictures/annotate.html"])
    edit_final(work, BAR_RECT, '<image href="material/none.png" x="8" y="8" width="720" height="350"/>')
    assert htmlexport.export(work)["missing"] == ["material/none.png"]
