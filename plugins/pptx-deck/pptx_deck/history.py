"""絵の往復の履歴。直す前の slides/*.html を <元データ>/history/NNN/ に残し
（ラベルは中の label.txt。古い NNN-ラベル/ の名前も読める）、前の版へ戻せるようにする。
build は history/ を消さない（lifecycle.prune は既知の派生ファイルだけを消す）。"""

import contextlib
import re
import shutil
from pathlib import Path

HISTORY = "history"
_LABEL_FILE = "label.txt"
_VER = re.compile(r"^(\d{3,})(?:-(.*))?$")


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
                label = m.group(2) or ""
                with contextlib.suppress(OSError):
                    label = (p / _LABEL_FILE).read_text(encoding="utf-8")
                out.append(
                    {
                        "version": int(m.group(1)),
                        "label": label,
                        "path": str(p),
                        "files": sorted(f.name for f in p.glob("*.html")),
                    }
                )
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
    n = max((v["version"] for v in vs), default=0) + 1
    lab = _label(label)
    _dir(work).mkdir(parents=True, exist_ok=True)
    while True:  # 並行する snapshot と番号が重なったら、取れるまで 1 つずつ上げる
        dest = _dir(work) / f"{n:03d}"
        try:
            dest.mkdir(exist_ok=False)
            break
        except FileExistsError:
            n += 1
    if lab:
        (dest / _LABEL_FILE).write_text(lab, encoding="utf-8")
    for f in files:
        shutil.copyfile(f, dest / f.name)
    return {"version": n, "label": lab, "path": str(dest), "files": [f.name for f in files]}


def restore(work: Path, version: int, slide: str | None = None) -> dict:
    """指定した版の断片を slides/ に戻す。戻す前の状態も新しい版として残すので、取り消せる。
    slide（例 "02"）を渡すと、そのスライドの断片（02-A.html・02-B-d2.html など）だけを戻す。"""
    work = Path(work)
    target = next((v for v in versions(work) if v["version"] == version), None)
    if target is None:
        raise ValueError(
            f"版 {version} がありません（{', '.join(str(v['version']) for v in versions(work)) or 'なし'}）"
        )
    if slide is not None:  # 戻す前の版を作る前に確かめる（不正な指定で版だけ増やさない）
        if not re.fullmatch(r"\d{2}", slide):
            raise ValueError(f"スライド番号は 2 桁の数字で指定してください（例 02）: {slide!r}")
        if not any(n.startswith(f"{slide}-") for n in target["files"]):
            raise ValueError(f"版 {version} にスライド {slide} の断片（{slide}-*.html）がありません")
    saved = snapshot(work, f"before-restore-{version}")
    src, dst = Path(target["path"]), _slides(work)
    pick = (lambda name: name.startswith(f"{slide}-")) if slide is not None else (lambda name: True)
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
    for name in (
        "final.html",
        "final-review.html",
    ):  # 戻す前の内容のままの統合結果で build しないよう消す（apply-edits と同じ）
        (work / name).unlink(missing_ok=True)
    return {"restored_version": version, "saved_as": saved["version"], "restored": restored, "removed": removed}


FRAGMENT = re.compile(r"^\d{2}-[A-Z](?:-d[23])?$")


def _check_fragment(work: Path, fragment: str) -> None:
    if not FRAGMENT.fullmatch(fragment):
        raise ValueError(f"断片名の形が違います（例 02-A、02-A-d2）: {fragment!r}")
    if not (_slides(work) / f"{fragment}.html").is_file():
        raise ValueError(f"{_slides(work) / (fragment + '.html')} がありません")


def snapshot_fragment(work: Path, fragment: str, keep: int = 5) -> dict:
    """AI に頼む前の slides/ を、ラベル ai-edit-<断片名> の版として残す。
    同じラベルの版が keep を超えたら、古い順に消す（ほかのラベルの版は消さない）。"""
    work = Path(work)
    _check_fragment(work, fragment)
    saved = snapshot(work, f"ai-edit-{fragment}")
    same = [v for v in versions(work) if v["label"] == saved["label"]]
    for v in same[: max(len(same) - keep, 0)]:
        shutil.rmtree(v["path"])
    return saved


def restore_fragment(work: Path, version: int, fragment: str) -> dict:
    """指定した版の <断片名>.html だけを slides/ に戻す。戻す前の状態も新しい版として残す。"""
    work = Path(work)
    target = next((v for v in versions(work) if v["version"] == version), None)
    if target is None:
        raise ValueError(
            f"版 {version} がありません（{', '.join(str(v['version']) for v in versions(work)) or 'なし'}）"
        )
    if not FRAGMENT.fullmatch(fragment):
        raise ValueError(f"断片名の形が違います（例 02-A、02-A-d2）: {fragment!r}")
    name = f"{fragment}.html"
    if name not in target["files"]:  # 戻す前の版を作る前に確かめる
        raise ValueError(f"版 {version} に断片 {name} がありません")
    saved = snapshot(work, f"before-restore-{version}-{fragment}")
    shutil.copyfile(Path(target["path"]) / name, _slides(work) / name)
    for final in ("final.html", "final-review.html"):  # restore と同じ。古い統合結果で build しない
        (work / final).unlink(missing_ok=True)
    return {"restored_version": version, "saved_as": saved["version"], "restored": [name]}


def latest_ai_edit(work: Path, fragment: str) -> dict | None:
    """ラベル ai-edit-<断片名> の最新の版。なければ None。"""
    same = [v for v in versions(work) if v["label"] == f"ai-edit-{fragment}"]
    return same[-1] if same else None
