import os
import subprocess
import sys
from pathlib import Path

from pptx_deck import env, paths

SKILL = Path(__file__).resolve().parent.parent


def test_home_dir_honors_env(home):
    assert paths.home_dir() == home
    assert paths.venv_python() == home / "venv" / "Scripts" / "python.exe"


def test_temp_dir_is_under_os_temp():
    import tempfile
    d = paths.temp_dir("t1")
    assert d.is_dir()
    assert Path(tempfile.gettempdir()) in d.parents


def test_status_without_venv(home):
    st = env.status()
    assert st["venv"] is False
    assert st["chromium"] is False


def test_font_match_uses_registered_names_not_file_names():
    from pptx_deck import cli
    # BIZ UDPGothic は BIZ-UDGothicR.ttc に同梱される。ファイル名ではなく登録名で判定する
    assert cli._has_font(["Arial (TrueType)", "BIZ UDGothic & BIZ UDPGothic (TrueType)"], "BIZ UDPGothic")
    assert not cli._has_font(["BIZ UDGothic (TrueType)", "Yu Gothic (TrueType)"], "BIZ UDPGothic")


def test_venv_health_detects_a_broken_interpreter(home, monkeypatch):
    py = paths.venv_python()
    py.parent.mkdir(parents=True)
    py.write_bytes(b"not an executable")                  # python.exe はあるが動かない（基底の Python が消えた等）
    assert env.venv_healthy() is False
    monkeypatch.setattr(paths, "venv_python", lambda: Path(sys.executable))
    assert env.venv_healthy() is True


def test_missing_module_gives_guidance_not_traceback(capsys, monkeypatch):
    from pptx_deck import cli

    def boom(argv):
        raise ModuleNotFoundError("No module named 'pptx'", name="pptx")
    monkeypatch.setattr(cli, "main", boom)
    assert cli.entry(["build", "x"]) == 3
    out = capsys.readouterr().out
    assert "setup --yes" in out and "pptx" in out


def _run(args, home):
    e = {**os.environ, "PPTX_DECK_HOME": str(home)}
    return subprocess.run([sys.executable, str(SKILL / "run.py"), *args],
                          env=e, capture_output=True, text=True, encoding="utf-8")


def test_run_py_without_venv_asks_for_consent(home):
    r = _run(["doctor"], home)
    assert r.returncode == 3
    assert "setup --yes" in r.stdout
    assert not (home / "venv").exists()


def test_setup_without_yes_does_not_create(home):
    r = _run(["setup"], home)
    assert r.returncode == 3
    assert not (home / "venv").exists()
