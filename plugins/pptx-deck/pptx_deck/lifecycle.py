"""PPTX の指紋（build.json）、派生ファイルの整理、一時ファイルの削除。削除は既知の派生ファイルに限る。"""

import datetime
import hashlib
import json
import shutil
import time
from pathlib import Path

from . import paths

DERIVED_FILES = (
    "variants.html",
    "final-review.html",
    "plan-review.html",
    "picture-review.html",
    "draft.html",
    "final.html",
    "theme.css",
    "base.css",
    "chart-preview.js",
)
DERIVED_DIRS = ("icons",)
DRAFT_KEEP_SEC = 600


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def record_build(work: Path, pptx: Path) -> None:
    data = {
        "pptx": Path(pptx).name,
        "sha256": sha256_of(pptx),
        "built_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
    }
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
    now = time.time()
    for p in sorted(work.glob("draft-*.html")):
        # 作ってから 10 分以内のものは、同じ作業フォルダで別の draft が測っている最中かもしれないので残す
        if p.is_file() and now - p.stat().st_mtime >= DRAFT_KEEP_SEC:
            p.unlink()
            removed.append(p.name)
    return removed


def clean_temp(name: str, work=None) -> bool:
    d = paths.temp_dir(name, work)  # 作ってから消す（存在しなくても安全）
    shutil.rmtree(d, ignore_errors=True)
    return True


def ensure_derived(work: Path) -> bool:
    """build や確認ページが使う派生ファイルが欠けていれば、template.json から再生成する。再生成したら True。"""
    from . import initdir

    work = Path(work)
    if all((work / n).exists() for n in ("theme.css", "base.css", "chart-preview.js", "icons")):
        return False
    cfg = paths.read_cfg(work)
    initdir.write_derived(work, cfg)
    return True


def reopen(work: Path) -> dict:
    """完成した作品を再修正するための準備。派生ファイルを template.json から再生成し、PPTX の指紋を確かめる。"""
    from . import initdir, variants

    work = Path(work)
    cfg = paths.read_cfg(work)
    notes = list(initdir.write_derived(work, cfg))
    pptx = paths.deck_dir(work) / f"{paths.deck_name(work)}.pptx"
    st = fingerprint_status(work, pptx)
    status = {"unchanged": "ok", "modified": "modified", "missing": "missing_pptx", "unrecorded": "unrecorded"}[st]
    if status == "modified":
        notes.append("PPTX は前回のビルドのあとに変更されています。作り直すと PowerPoint での手直しが消えます。")
    elif status == "unrecorded":
        notes.append("PPTX に build.json の記録がありません。元の資料かもしれず、作り直すと消えます。")
    slides = (
        len({m.group(1) for f in (work / "slides").glob("*.html") if (m := variants.FRAG.match(f.name))})
        if (work / "slides").is_dir()
        else 0
    )
    return {
        "status": status,
        "source": str(work),
        "pptx": str(pptx),
        "answers": [str(p) for p in variants.answer_paths(work)],
        "next_round": variants.next_round(work),
        "slides": slides,
        "notes": notes,
    }
