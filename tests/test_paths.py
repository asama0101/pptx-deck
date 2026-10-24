# ruff: noqa: S101  # pytest の assert
import sys
import tempfile

import pytest
from pptx_deck import cli, paths


@pytest.fixture
def temp_root(tmp_path, monkeypatch):
    """OS の一時フォルダを tmp_path の下に向ける（確認用の画像の置き場を、実際の一時フォルダに作らない）。"""
    root = tmp_path / "os-temp"
    root.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(root))
    return root


def test_プラグイン本体に入口と_pptx_deck_パッケージがある(pkg):
    assert (pkg / "run.py").is_file()
    assert (pkg / "pptx_deck" / "cli.py").is_file()


def test_home_dir_は環境変数_PPTX_DECK_HOME_を返す(monkeypatch):
    monkeypatch.setenv("PPTX_DECK_HOME", r"C:\x\home")
    assert str(paths.home_dir()) == r"C:\x\home"


def test_環境変数がないと_home_dir_は_RuntimeError_で止まり_LOCALAPPDATA_へ戻らない(monkeypatch, tmp_path):
    monkeypatch.delenv("PPTX_DECK_HOME", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))  # フォールバックしないことを確かめるため残す
    with pytest.raises(RuntimeError, match="PPTX_DECK_HOME"):
        paths.home_dir()


def test_venv_の_python_は置き場の下の_venv_Scripts_python_exe(monkeypatch):
    monkeypatch.setenv("PPTX_DECK_HOME", r"C:\x\home")
    assert str(paths.venv_python()) == r"C:\x\home\venv\Scripts\python.exe"


@pytest.mark.parametrize(
    "bad",
    ["", "  ", ".", "..", "a/b", r"a\b"],
    ids=["空", "空白のみ", "ドット1つ", "ドット2つ", "スラッシュ", "バックスラッシュ"],
)
def test_不正な名前の一時フォルダは_ValueError_で拒否される(bad, temp_root):
    with pytest.raises(ValueError, match="一時フォルダの名前が不正です"):
        paths.temp_dir(bad)
    assert list(temp_root.iterdir()) == []  # 拒否したときは何も作らない


def test_clean_は空の作品名なら終了コード2で止まり何も消さない(temp_root, tmp_path, capsys):
    (temp_root / "pptx-deck").mkdir()
    (temp_root / "pptx-deck" / "keep.txt").write_text("x", encoding="utf-8")
    rc = cli.main(["clean", tmp_path.anchor])  # ドライブ直下は作品名が空になる
    assert rc == 2
    assert "エラー" in capsys.readouterr().err
    assert (temp_root / "pptx-deck" / "keep.txt").read_text(encoding="utf-8") == "x"


def test_build_は空の作品名なら終了コード2で止まり測定しない(tmp_path, monkeypatch, capsys, temp_root):
    # 空の作品名は、実際にはドライブ直下の作品でしか起きない。そこへ作品を作れないので、作品名の決定だけを差し替える
    assert cli.main(["init", str(tmp_path / "demo"), "--color", "navy"]) == 0
    capsys.readouterr()
    monkeypatch.setattr(paths, "deck_name", lambda work: "")
    monkeypatch.setitem(sys.modules, "playwright", None)  # 測定まで進めば ModuleNotFoundError になる
    monkeypatch.setitem(sys.modules, "playwright.sync_api", None)
    rc = cli.main(["build", str(tmp_path / "demo")])
    cap = capsys.readouterr()
    assert rc == 2
    assert "エラー" in cap.err
    assert cap.out == ""
