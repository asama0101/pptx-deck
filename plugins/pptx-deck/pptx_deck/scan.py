"""開始ページの事前スキャン（入力ファイルと出力先の候補）と、最近使った場所の記録。"""

import json
import os
import stat
from pathlib import Path

from . import paths

MAX_DEPTH = 3  # 場所そのものを 0、直下を 1 とした、辿るフォルダの深さの上限
MAX_ENTRIES = 200  # 1 フォルダで拾うフォルダ・ファイルの件数
MAX_RECENT = 10
EXTS = {".docx", ".pdf", ".pptx", ".md", ".txt"}
SKIP_DIRS = {paths.SOURCE_PARENT, ".git", "node_modules"}


_LINK_TAGS = {getattr(stat, "IO_REPARSE_TAG_MOUNT_POINT", -1), getattr(stat, "IO_REPARSE_TAG_SYMLINK", -1)}


def _skip(p: Path) -> bool:
    """辿らない・出さないもの: 隠し・システム属性、Office のロックファイル、シンボリックリンクとジャンクション。
    ジャンクションは lstat の再解析タグで見る（Path.is_junction は Python 3.12 から）。OneDrive のクラウドの
    ファイルも再解析ポイントなので、属性ではなくタグで、リンクとジャンクションだけを除く。"""
    if p.name.startswith((".", "~$")):  # ~$ は Office の作業中のロックファイル
        return True
    try:
        st = p.lstat()
    except OSError:
        return True  # 属性が読めないものは出さない（一覧は補助で、パス欄から指定できる）
    if stat.S_ISLNK(st.st_mode) or getattr(st, "st_reparse_tag", 0) in _LINK_TAGS:
        return True
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
        if _skip(p):
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


_SHELL_FOLDERS = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
# (ラベル, home 下の英語名, レジストリの値名)
_KNOWN = (
    ("ドキュメント", "Documents", "Personal"),
    ("デスクトップ", "Desktop", "Desktop"),
    ("ダウンロード", "Downloads", "{374DE290-123F-4565-9164-39C4925E467B}"),
)


def _registry_value(name: str) -> str | None:
    """User Shell Folders の値を読む。読めなければ None（Windows 以外では winreg がない）。"""
    try:
        import winreg  # noqa: PLC0415  # Windows 以外でも import できるように遅延させる

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _SHELL_FOLDERS) as k:
            v, _ = winreg.QueryValueEx(k, name)
    except (ImportError, OSError):
        return None
    return v if isinstance(v, str) else None


def _known_dir(home: Path | None, english: str, value: str) -> Path:
    """既知のフォルダ。home を渡さないときは、OneDrive などでの移動先をレジストリから引く（実在するものだけ）。"""
    if home is not None:
        return home / english
    raw = _registry_value(value)
    if raw:
        p = Path(os.path.expandvars(raw))
        if p.is_absolute() and p.is_dir():
            return p
    return Path.home() / english


def scan(cwd: Path, home: Path | None = None) -> dict:
    """作業フォルダ・ドキュメント・デスクトップ・ダウンロード・最近使った場所（存在するものだけ）を辿る。
    home を渡すと、レジストリを読まずに home の下の英語名のフォルダを使う（テスト用）。"""
    places = []
    for label, p in (("作業フォルダ", cwd), *((lb, _known_dir(home, en, v)) for lb, en, v in _KNOWN)):
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
