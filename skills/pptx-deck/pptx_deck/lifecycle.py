"""PPTX の指紋（build.json）、派生ファイルの整理、一時ファイルの削除。削除は既知の派生ファイルに限る。"""
import datetime
import hashlib
import json
import shutil
from pathlib import Path

from . import paths

DERIVED_FILES = ("variants.html", "final-review.html", "plan-review.html", "final.html",
                 "theme.css", "base.css", "chart-preview.js")
DERIVED_DIRS = ("icons",)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def record_build(work: Path, pptx: Path) -> None:
    data = {"pptx": Path(pptx).name, "sha256": sha256_of(pptx),
            "built_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds")}
    (Path(work) / "build.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def fingerprint_status(work: Path, pptx: Path) -> str:
    if not Path(pptx).exists():
        return "missing"
    rec = Path(work) / "build.json"
    if not rec.exists():
        return "unrecorded"
    try:
        saved = json.loads(rec.read_text(encoding="utf-8")).get("sha256")
    except (OSError, ValueError):
        return "unrecorded"
    return "unchanged" if saved == sha256_of(pptx) else "modified"


def prune(work: Path) -> list[str]:
    """再生成できる派生ファイルだけを消す。source/ の元データと、未知のファイルは消さない。消した相対パスを返す。"""
    work = Path(work)
    removed: list[str] = []
    for name in DERIVED_FILES:
        p = work / name
        if p.is_file():
            p.unlink()
            removed.append(name)
    for name in DERIVED_DIRS:
        p = work / name
        if p.is_dir():
            shutil.rmtree(p)
            removed.append(name)
    tdir = work / "_template"
    if tdir.is_dir():
        for p in sorted(tdir.glob("bg-*.png")):
            p.unlink()
            removed.append(f"_template/{p.name}")
    return removed


def clean_temp(name: str) -> bool:
    d = paths.temp_dir(name)           # 作ってから消す（存在しなくても安全）
    shutil.rmtree(d, ignore_errors=True)
    return True
