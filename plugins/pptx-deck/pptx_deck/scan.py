"""開始ページの事前スキャン（入力ファイルと出力先の候補）と、最近使った場所の記録。"""

import json
import stat
from pathlib import Path

from . import paths

MAX_DEPTH = 3  # 場所そのものを 0、直下を 1 とした、辿るフォルダの深さの上限
MAX_ENTRIES = 200  # 1 フォルダで拾うフォルダ・ファイルの件数
MAX_RECENT = 10
EXTS = {".docx", ".pdf", ".pptx", ".md", ".txt"}
SKIP_DIRS = {paths.SOURCE_PARENT, ".git", "node_modules"}


def _hidden(p: Path) -> bool:
    if p.name.startswith((".", "~$")):  # ~$ は Office の作業中のロックファイル
        return True
    try:
        st = p.lstat()
    except OSError:
        return True  # 属性が読めないものは出さない（一覧は補助で、パス欄から指定できる）
    return bool(getattr(st, "st_file_attributes", 0) & (stat.FILE_ATTRIBUTE_HIDDEN | stat.FILE_ATTRIBUTE_SYSTEM))


def _tree(path: Path, name: str, depth: int) -> dict:
    node = {"name": name, "path": str(path), "dirs": [], "files": []}
    try:
        entries = sorted(path.iterdir(), key=lambda p: p.name.lower())
    except OSError:
        return node  # 読めないフォルダ（権限・消えた）は中身なしで出す
    count = 0
    for p in entries:
        if count >= MAX_ENTRIES:
            break
        if _hidden(p) or p.is_symlink() or p.is_junction():
            continue
        if p.is_dir():
            if p.name in SKIP_DIRS or depth >= MAX_DEPTH:  # 深さの上限のフォルダは、ファイルだけ拾う
                continue
            node["dirs"].append(_tree(p, p.name, depth + 1))
        elif p.suffix.lower() in EXTS:
            node["files"].append(str(p))
        else:
            continue
        count += 1
    return node


def scan(cwd: Path, home: Path | None = None) -> dict:
    """作業フォルダ・ドキュメント・デスクトップ・ダウンロード・最近使った場所（存在するものだけ）を辿る。"""
    home = Path.home() if home is None else home
    places = []
    for label, p in (
        ("作業フォルダ", cwd),
        ("ドキュメント", home / "Documents"),
        ("デスクトップ", home / "Desktop"),
        ("ダウンロード", home / "Downloads"),
    ):
        if p.is_dir():
            places.append({"label": label, "path": str(p), "tree": _tree(p, label, 0)})
    recent = [Path(d) for d in load_recent() if Path(d).is_dir()]
    if recent:
        tree = {"name": "最近使った場所", "path": "", "dirs": [_tree(d, str(d), 1) for d in recent], "files": []}
        places.append({"label": "最近使った場所", "path": "", "tree": tree})
    return {"cwd": str(cwd), "places": places}


def _recent_file() -> Path | None:
    try:
        return paths.home_dir() / "recent.json"
    except RuntimeError:
        return None  # 置き場（PPTX_DECK_HOME）がなければ記録しない


def load_recent() -> list[str]:
    f = _recent_file()
    if f is None or not f.is_file():
        return []
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []  # 壊れた記録は空として扱う（次の remember_recent で書き直す）
    return [d for d in data if isinstance(d, str)] if isinstance(data, list) else []


def remember_recent(dirs: list[str]) -> None:
    """dirs を新しい順として先頭に足し、重複を除いて MAX_RECENT 件まで残す。"""
    f = _recent_file()
    if f is None:
        return
    merged: list[str] = []
    for d in [*dirs, *load_recent()]:
        if d.lower() not in (m.lower() for m in merged):
            merged.append(d)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(merged[:MAX_RECENT], ensure_ascii=False, indent=2), encoding="utf-8")
