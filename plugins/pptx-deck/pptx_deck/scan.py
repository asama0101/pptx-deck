"""開始ページの事前スキャン（作業フォルダの中の、入力ファイルと保存先の候補）。

辿る規則（深さ・件数・拡張子・除外）は、開始ページの「フォルダを読み直す」（start-page.html の JS）と一致させる。
"""

import stat
from pathlib import Path

from . import paths

MAX_DEPTH = 3  # 場所そのものを 0、直下を 1 とした、辿るフォルダの深さの上限
MAX_ENTRIES = 200  # 1 フォルダで拾うフォルダ・ファイルの件数
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


def scan(cwd: Path) -> dict:
    """作業フォルダだけを辿る。ほかの場所は、開始ページのパス欄に手動で書く。"""
    return {
        "cwd": str(cwd),
        "places": [{"label": "作業フォルダ", "path": str(cwd), "tree": _tree(cwd, "作業フォルダ", 0)}],
    }
