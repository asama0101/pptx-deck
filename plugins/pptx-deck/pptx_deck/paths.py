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
    if not name.strip() or name.strip() in (".", "..") or "/" in name or "\\" in name:
        raise ValueError(f"一時フォルダの名前が不正です: {name!r}")     # clean が %TEMP%\pptx-deck 全体を消さないように
    d = Path(tempfile.gettempdir()) / "pptx-deck" / name
    d.mkdir(parents=True, exist_ok=True)
    return d


def resolve_work(arg) -> Path:
    """コマンドの <名前> を、作業フォルダ（<名前>/source）に解決する。旧形式（template.json が直下）はそのフォルダ。"""
    base = Path(arg).resolve()
    src = base / "source"
    if src.is_dir():
        return src
    if (base / "template.json").exists():
        return base
    return src


def is_legacy(work: Path) -> bool:
    return Path(work).name != "source"


def deck_dir(work: Path) -> Path:
    work = Path(work)
    return work if is_legacy(work) else work.parent


def deck_name(work: Path) -> str:
    return deck_dir(work).name
