"""絵の往復の履歴。直す前の slides/*.html を source/history/NNN[-ラベル]/ に残し、前の版へ戻せるようにする。
build は history/ を消さない（lifecycle.prune は既知の派生ファイルだけを消す）。"""
import re
import shutil
from pathlib import Path

HISTORY = "history"
_VER = re.compile(r"^(\d{3})(?:-(.*))?$")


def _dir(work: Path) -> Path:
    return Path(work) / HISTORY


def _slides(work: Path) -> Path:
    return Path(work) / "slides"


def versions(work: Path) -> list[dict]:
    """版の一覧（古い順）。"""
    out = []
    d = _dir(work)
    if d.is_dir():
        for p in sorted(d.iterdir()):
            m = _VER.match(p.name)
            if p.is_dir() and m:
                out.append({"version": int(m.group(1)), "label": m.group(2) or "", "path": str(p),
                            "files": sorted(f.name for f in p.glob("*.html"))})
    return out


def _label(label: str) -> str:
    label = re.sub(r"[\\/:*?\"<>|\s]+", "-", (label or "").strip()).strip("-")
    return label[:40]


def snapshot(work: Path, label: str = "") -> dict:
    """slides/*.html をそのまま新しい版として残す。直す前に呼ぶ。"""
    work = Path(work)
    src = _slides(work)
    files = sorted(src.glob("*.html")) if src.is_dir() else []
    if not files:
        raise ValueError(f"{src} に断片（*.html）がありません")
    vs = versions(work)
    n = (vs[-1]["version"] + 1) if vs else 1
    lab = _label(label)
    dest = _dir(work) / (f"{n:03d}-{lab}" if lab else f"{n:03d}")
    dest.mkdir(parents=True)
    for f in files:
        shutil.copyfile(f, dest / f.name)
    return {"version": n, "label": lab, "path": str(dest), "files": [f.name for f in files]}


def restore(work: Path, version: int, slide: str | None = None) -> dict:
    """指定した版の断片を slides/ に戻す。戻す前の状態も新しい版として残すので、取り消せる。
    slide（例 "02"）を渡すと、そのスライドの断片（02-A.html・02-B-d2.html など）だけを戻す。"""
    work = Path(work)
    target = next((v for v in versions(work) if v["version"] == version), None)
    if target is None:
        raise ValueError(f"版 {version} がありません（{', '.join(str(v['version']) for v in versions(work)) or 'なし'}）")
    saved = snapshot(work, f"before-restore-{version}")
    src, dst = Path(target["path"]), _slides(work)
    pick = (lambda name: name.startswith(f"{slide}-")) if slide else (lambda name: True)
    removed = []
    for f in sorted(dst.glob("*.html")):
        if pick(f.name):
            f.unlink()
            removed.append(f.name)
    restored = []
    for f in sorted(src.glob("*.html")):
        if pick(f.name):
            shutil.copyfile(f, dst / f.name)
            restored.append(f.name)
    return {"restored_version": version, "saved_as": saved["version"], "restored": restored, "removed": removed}
