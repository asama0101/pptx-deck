"""下書きの確認（draft）: 回答を待たずに断片を束ね、確認用の画像と検査の結果を返す。PPTX は出さない。"""

# ruff: noqa: S101  # pytest の assert
import json
import os
import re
import time
from pathlib import Path

import pytest
from pptx_deck import cli, draft, paths

pytestmark = pytest.mark.slow  # 実際にブラウザでスライドを撮る


@pytest.fixture(autouse=True)
def _temp_in_tmp_path(tmp_path, monkeypatch):
    """確認用の画像の置き場（OS の一時フォルダ）を tmp_path の下に向ける。"""
    d = tmp_path / "os-temp"
    d.mkdir()
    monkeypatch.setattr("tempfile.tempdir", str(d))


@pytest.fixture
def deck(pkg, tmp_path):
    """init 済みで、01-A（故障の絵）・02-A（構成図）・02-B（自己紹介）の断片を置いた作品。(base, work)"""
    pictures = pkg / "assets" / "components" / "pictures"
    base = tmp_path / "demo"
    assert cli.main(["init", str(base), "--color", "navy"]) == 0
    work = paths.resolve_work(base)
    for name, src in (("01-A", "failure"), ("02-A", "network"), ("02-B", "self-intro")):
        (work / "slides" / f"{name}.html").write_text(
            (pictures / f"{src}.html").read_text(encoding="utf-8"), encoding="utf-8"
        )
    return base, work


def run(capsys, *argv):
    capsys.readouterr()
    rc = cli.main(list(argv))
    cap = capsys.readouterr()
    return rc, cap.out, cap.err


def test_PPTXを作らずに確認用の画像と検査結果を返す(deck, capsys):
    base, work = deck
    rc, out, err = run(capsys, "draft", str(base))
    assert rc == 0, out + err
    r = json.loads(out)
    assert (r["ok"], r["slides"], r["violations"]) == (True, ["01", "02"], [])
    assert len(r["previews"]) == 2
    for p in r["previews"]:
        assert Path(p).read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert not (work / "final.html").exists()
    assert list(base.glob("*.pptx")) == []
    assert list(work.glob("draft*.html")) == []  # 一時の HTML は残さない


def test_slideで対象を絞りpickで案を選ぶ(deck, capsys):
    base, work = deck
    rc, out, _ = run(capsys, "draft", str(base), "--slide", "02", "--pick", "B")
    r = json.loads(out)
    assert (rc, r["slides"], len(r["previews"])) == (0, ["02"], 1)
    html, _ = draft.assemble(work, pick="B", slides=["02"])
    try:
        assert html.parent == work
        assert re.match(r"^draft-.*\.html$", html.name)
        assert "自己紹介" in html.read_text(encoding="utf-8")  # 02-B（自己紹介）が入る
        assert "自己紹介" not in draft.assemble(work, pick="A", slides=["02"])[0].read_text(encoding="utf-8")
    finally:
        for f in work.glob("draft-*.html"):
            f.unlink()


def test_存在しないスライド番号は終了コード2(deck, capsys):
    base, _ = deck
    assert run(capsys, "draft", str(base), "--slide", "09")[0] == 2


def test_続けて実行しても確認用の画像は互いを上書きしない(deck, capsys):
    base, work = deck
    r1 = json.loads(run(capsys, "draft", str(base), "--slide", "01")[1])
    r2 = json.loads(run(capsys, "draft", str(base), "--slide", "02")[1])
    assert Path(r1["previews"][0]).exists()  # 2 回目のあとも残る
    assert Path(r1["previews"][0]).parent != Path(r2["previews"][0]).parent
    assert list(work.glob("draft*.html")) == []


def test_2日前の実行フォルダは次の実行で掃除される(deck, capsys):
    base, _ = deck
    r = json.loads(run(capsys, "draft", str(base), "--slide", "01")[1])
    first = Path(r["previews"][0]).parent
    old = time.time() - 2 * 86400
    os.utime(first, (old, old))
    r2 = json.loads(run(capsys, "draft", str(base), "--slide", "02")[1])
    assert not first.exists()
    assert Path(r2["previews"][0]).exists()


def test_違反があれば終了コード1で報告し_画像は出す(deck, capsys):
    base, work = deck
    f = work / "slides" / "01-A.html"
    f.write_text(re.sub(r' data-alt="[^"]*"', "", f.read_text(encoding="utf-8")), encoding="utf-8")
    rc, out, _ = run(capsys, "draft", str(base))
    r = json.loads(out)
    assert (rc, r["ok"]) == (1, False)
    assert "imageAlt" in {v["rule"] for v in r["violations"]}
    assert len(r["previews"]) == 2  # 画像は出す（直す手がかり）
