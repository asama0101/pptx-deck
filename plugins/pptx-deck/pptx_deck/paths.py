"""場所の決定。標準ライブラリのみ（run.py から venv なしで使う）。"""

import hashlib
import json
import os
import tempfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
ASSETS = SKILL_DIR / "assets"


def read_cfg(work) -> dict:
    return json.loads((Path(work) / "template.json").read_text(encoding="utf-8"))


def read_text(path) -> str:
    """利用者が書くファイル（原稿・設計図・回答・メモなど）を読む。
    BOM 付きの UTF-8 も読み、UTF-8 でなければ ValueError にする。"""
    path = Path(path)
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError(f"{path.name} は UTF-8 で保存してください（今の文字コードでは読めません）: {path}") from None


def write_cfg(work, cfg: dict) -> None:
    """同じフォルダの一時ファイルに書いてから置き換える（読む側が途中の JSON を見ないように）。"""
    target = Path(work) / "template.json"
    fd, tmp = tempfile.mkstemp(dir=target.parent, prefix="template-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(cfg, ensure_ascii=False, indent=2))
        Path(tmp).replace(target)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def home_dir() -> Path:
    """専用の仮想環境などの置き場。run.py が `--data`（${CLAUDE_PLUGIN_DATA}）を PPTX_DECK_HOME に入れて渡す。"""
    home = os.environ.get("PPTX_DECK_HOME")
    if not home:
        raise RuntimeError("専用環境の置き場が未指定です（環境変数 PPTX_DECK_HOME か、run.py の --data で指定します）")
    return Path(home)


def venv_dir() -> Path:
    return home_dir() / "venv"


def venv_python() -> Path:
    return venv_dir() / "Scripts" / "python.exe"


def temp_key(name: str, work=None) -> str:
    """一時フォルダの名前。work（作業フォルダ）を渡すと、絶対パスのハッシュを足し、同名の別の作品と混ざらないようにする。"""
    if not name.strip() or name.strip() in (".", "..") or "/" in name or "\\" in name:
        raise ValueError(f"一時フォルダの名前が不正です: {name!r}")  # clean が %TEMP%\pptx-deck 全体を消さないように
    if work is None:
        return name
    return f"{name}-{hashlib.sha1(str(Path(work).resolve()).encode('utf-8'), usedforsecurity=False).hexdigest()[:8]}"


def temp_dir(name: str, work=None) -> Path:
    """OS の一時フォルダ配下の作業場所（確認用 PNG など一過性のもの）。work を渡すと作業フォルダごとに分ける。"""
    d = Path(tempfile.gettempdir()) / "pptx-deck" / temp_key(name, work)
    d.mkdir(parents=True, exist_ok=True)
    return d


def resolve_work(arg) -> Path:
    """コマンドの <名前> を、作業フォルダ（<名前>/source）に解決する。<名前>/source を直接渡してもよい。"""
    base = Path(arg).resolve()
    if base.name == "source":
        return base
    return base / "source"


def deck_dir(work: Path) -> Path:
    return Path(work).parent


def deck_name(work: Path) -> str:
    return deck_dir(work).name
