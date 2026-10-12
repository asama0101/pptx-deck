"""場所の決定。標準ライブラリのみ（run.py から venv なしで使う）。"""
import os
import tempfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
ASSETS = SKILL_DIR / "assets"


def home_dir() -> Path:
    override = os.environ.get("PPTX_DECK_HOME")
    if override:
        return Path(override)
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        raise RuntimeError("LOCALAPPDATA が未設定です（Windows 専用です）")
    return Path(base) / "pptx-deck"


def venv_dir() -> Path:
    return home_dir() / "venv"


def venv_python() -> Path:
    return venv_dir() / "Scripts" / "python.exe"


def temp_dir(name: str) -> Path:
    """OS の一時フォルダ配下の作業場所（確認用 PNG など一過性のもの）。"""
    d = Path(tempfile.gettempdir()) / "pptx-deck" / name
    d.mkdir(parents=True, exist_ok=True)
    return d
