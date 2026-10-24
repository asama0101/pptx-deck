"""build の出力先（--out・上書きの確認・書き込めない出力先・記録のない PPTX）。

測定・検査・PPTX の書き出しは実物を通す（ブラウザを使う分は slow）。
「測定の前に止まる」ことは、Playwright を読み込めなくして（no_browser）、測定まで進めば別の失敗になる形で確かめる。
"""

# ruff: noqa: S101  # pytest の assert
import json
import shutil
import stat
import sys
import tempfile
from pathlib import Path

import pytest
from pptx import Presentation
from pptx_deck import cli, paths

PKG = Path(__file__).resolve().parent.parent / "plugins" / "pptx-deck"


@pytest.fixture(scope="module")
def pristine_deck(tmp_path_factory) -> Path:
    """init → variants → 回答 → finalize まで進めた作品（final.html つき）。
    どのテストも変更しない（コピーして使う）。"""
    base = tmp_path_factory.mktemp("pristine") / "deck"
    assert cli.main(["init", str(base), "--color", "navy"]) == 0
    work = paths.resolve_work(base)
    shutil.copyfile(PKG / "assets" / "components" / "layouts" / "cover.html", work / "slides" / "01-A.html")
    assert cli.main(["variants", str(base)]) == 0
    (work / "answers-1.md").write_text(
        "---\ndeck: deck\nround: 1\n---\n## S01\n- 選択: A\n- 判定: 承認\n- コメント: \n", encoding="utf-8"
    )
    assert cli.main(["finalize", str(base)]) == 0
    assert (work / "final.html").is_file()
    return base


@pytest.fixture
def work(pristine_deck, tmp_path) -> Path:
    """final.html まで進んだ作品（作業フォルダ）。テストごとのコピー。"""
    base = tmp_path / "deck"
    shutil.copytree(pristine_deck, base)
    return paths.resolve_work(base)


@pytest.fixture
def temp_root(tmp_path, monkeypatch):
    """確認用の画像の置き場（OS の一時フォルダ）を tmp_path の下に向ける。"""
    root = tmp_path / "os-temp"
    root.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(root))
    return root


@pytest.fixture
def no_browser(monkeypatch):
    """Playwright を読み込めなくする。測定（ブラウザの起動）まで進んだら ModuleNotFoundError で落ちる。"""
    monkeypatch.setitem(sys.modules, "playwright", None)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", None)


def build(work, out, capsys, force=False):
    """cmd_build を実物のまま呼ぶ。(終了コード, stdout, stderr)。"""
    argv = ["build", str(work), "--out", str(out)] + (["--force"] if force else [])
    capsys.readouterr()
    rc = cli.main(argv)
    cap = capsys.readouterr()
    return rc, cap.out, cap.err


def _slide_count(pptx: Path) -> int:
    return len(Presentation(str(pptx)).slides)


# ---- --out の上書き ----


def test_既存の出力先は_force_なしで終了コード4で止まり中身を変えない(work, tmp_path, temp_root, no_browser, capsys):
    out = tmp_path / "other.pptx"
    out.write_bytes(b"old")
    rc, stdout, err = build(work, out, capsys)
    assert rc == 4
    assert "--force" in err
    assert out.read_bytes() == b"old"
    assert stdout == ""  # 測定・書き出しまで進んでいない（進めば結果の JSON が出る）


@pytest.mark.slow
def test_force_付きなら既存の出力先を新しい_pptx_で上書きする(work, tmp_path, temp_root, capsys):
    out = tmp_path / "other.pptx"
    out.write_bytes(b"old")
    rc, stdout, _ = build(work, out, capsys, force=True)
    assert rc == 0
    assert json.loads(stdout)["pptx"] == str(out)
    assert _slide_count(out) == 1


@pytest.mark.slow
def test_出力先が無ければ親フォルダを作って_pptx_を出す(work, tmp_path, temp_root, capsys):
    out = tmp_path / "sub" / "new.pptx"
    rc, _, _ = build(work, out, capsys)
    assert rc == 0
    assert _slide_count(out) == 1


# ---- 記録のない PPTX ----


def test_記録のない既定の_pptx_は_force_なしで終了コード4で止まり中身を変えない(work, temp_root, no_browser, capsys):
    out = paths.deck_dir(work) / "deck.pptx"
    out.write_bytes(b"original")  # build.json がない
    rc, stdout, err = build(work, out, capsys)
    assert rc == 4
    assert "記録のない" in err
    assert "--force" in err
    assert out.read_bytes() == b"original"
    assert stdout == ""


@pytest.mark.slow
def test_記録のない既定の_pptx_も_force_なら上書きされる(work, temp_root, capsys):
    out = paths.deck_dir(work) / "deck.pptx"
    out.write_bytes(b"original")
    rc, _, _ = build(work, out, capsys, force=True)
    assert rc == 0
    assert _slide_count(out) == 1


def test_壊れた_build_json_は記録なしとして_force_なしで終了コード4で止まる(work, temp_root, no_browser, capsys):
    out = paths.deck_dir(work) / "deck.pptx"
    out.write_bytes(b"original")
    (work / "build.json").write_text("{壊れた", encoding="utf-8")
    rc, _, err = build(work, out, capsys)
    assert rc == 4
    assert "記録のない" in err
    assert out.read_bytes() == b"original"


@pytest.mark.slow
def test_初回のビルドは_pptx_が無ければ止まらず出力と_build_json_を残す(work, temp_root, capsys):
    out = paths.deck_dir(work) / "deck.pptx"
    assert not out.exists()
    rc, _, _ = build(work, out, capsys)
    assert rc == 0
    assert _slide_count(out) == 1
    assert json.loads((work / "build.json").read_text(encoding="utf-8"))["sha256"]


def test_reopen_は記録のない_pptx_を_force_なしで終了コード4で止め_force_なら進む(work, capsys):
    pptx = paths.deck_dir(work) / "deck.pptx"
    pptx.write_bytes(b"original")
    capsys.readouterr()
    assert cli.main(["reopen", str(work)]) == 4
    assert json.loads(capsys.readouterr().out)["status"] == "unrecorded"
    assert cli.main(["reopen", str(work), "--force"]) == 0
    assert pptx.read_bytes() == b"original"  # reopen は PPTX を変えない


# ---- 書き込めない出力先 ----


def test_書き込めない出力先は測定の前に終了コード2で止まり中身を変えない(work, tmp_path, temp_root, no_browser, capsys):
    out = tmp_path / "locked.pptx"
    out.write_bytes(b"old")
    out.chmod(stat.S_IREAD)  # 読み取り専用（PowerPoint で開いている状態の代わり）
    try:
        rc, stdout, err = build(work, out, capsys, force=True)
    finally:
        out.chmod(stat.S_IWRITE | stat.S_IREAD)
    assert rc == 2
    assert "PowerPoint" in err
    assert stdout == ""
    assert out.read_bytes() == b"old"


def test_書き込み確認は既存の出力先の中身を変えない(tmp_path):
    out = tmp_path / "keep.pptx"
    out.write_bytes(b"old")
    assert cli._check_writable(out) is None
    assert out.read_bytes() == b"old"


def test_書き込み確認は無い出力先を作らず親フォルダだけ用意する(tmp_path):
    out = tmp_path / "sub" / "x.pptx"
    assert cli._check_writable(out) is None
    assert not out.exists()
    assert out.parent.is_dir()
    assert list(out.parent.iterdir()) == []  # 確認用の一時ファイルも残さない
