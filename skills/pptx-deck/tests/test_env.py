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
