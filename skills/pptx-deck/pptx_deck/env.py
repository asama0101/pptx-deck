"""実行する Python の選択（システム優先、なければ venv）と、venv の作成。標準ライブラリのみ。"""
import json
import subprocess
import sys
import venv
from dataclasses import dataclass
from pathlib import Path

from . import paths

# pip 名 → 要求する版。requirements.txt と同じ内容（テストで一致を確かめる）
REQUIREMENTS = {"python-pptx": "==1.0.2", "playwright": "==1.52.0", "pymupdf": "==1.28.2", "lxml": ">=5"}

_PROBE = r'''
import json, os, sys
import importlib.metadata as m
out = {"python": list(sys.version_info[:2]), "versions": {}, "chromium": False}
for pkg in ("python-pptx", "playwright", "pymupdf", "lxml"):
    try:
        out["versions"][pkg] = m.version(pkg)
    except m.PackageNotFoundError:
        out["versions"][pkg] = None
if out["versions"]["playwright"]:
    try:
        from playwright.sync_api import sync_playwright
        p = sync_playwright().start()
        out["chromium"] = os.path.exists(p.chromium.executable_path)
        p.stop()
    except Exception:
        pass
print(json.dumps(out))
'''


def probe(python: Path) -> dict:
    """指定した Python に、必要なものがどう入っているか。動かない Python は、すべて未導入として返す。"""
    empty = {"python": [0, 0], "versions": {k: None for k in REQUIREMENTS}, "chromium": False}
    try:
        r = subprocess.run([str(python), "-c", _PROBE], capture_output=True, text=True, timeout=120)
        return json.loads(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 and r.stdout.strip() else empty
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        return empty


def _version_ok(spec: str, ver: str) -> bool:
    if spec.startswith("=="):
        return ver == spec[2:]
    if spec.startswith(">="):
        return int(ver.split(".")[0]) >= int(spec[2:].split(".")[0])      # 主版だけ比べる（lxml>=5）
    return True


def missing(info: dict) -> list[str]:
    out = []
    if tuple(info.get("python", [0, 0])) < (3, 10):
        out.append("Python 3.10 以上が必要です")
    for pkg, spec in REQUIREMENTS.items():
        ver = info["versions"].get(pkg)
        if ver is None:
            out.append(f"{pkg} が未導入です")
        elif not _version_ok(spec, ver):
            out.append(f"{pkg} {ver}（要 {spec}）")
    if not info.get("chromium"):
        out.append("Playwright の chromium が使えません")
    return out


@dataclass
class Selection:
    kind: str                       # "system" | "venv" | "none"
    path: Path | None
    system_missing: list[str]
    venv_missing: list[str]


def select_python(system: Path | None = None) -> Selection:
    """システムの Python に必要なものがそろっていればそれを、なければ venv を使う。どちらも使えなければ none。"""
    system = Path(system or sys.executable)
    sys_miss = missing(probe(system))
    if not sys_miss:
        return Selection("system", system, [], [])
    vpy = paths.venv_python()
    venv_miss = missing(probe(vpy)) if vpy.exists() else ["仮想環境がありません"]
    if not venv_miss:
        return Selection("venv", vpy, sys_miss, [])
    return Selection("none", None, sys_miss, venv_miss)


def venv_healthy() -> bool:
    """venv の python.exe が実際に動くか（基底の Python が消えた venv は、ファイルがあっても動かない）。"""
    try:
        return subprocess.run([str(paths.venv_python()), "-c", "pass"],
                              capture_output=True, timeout=60).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def setup(yes: bool) -> int:
    target = paths.venv_dir()
    if not yes:
        print(f"仮想環境が必要です。作成先: {target}")
        print("作成内容: python -m venv ＋ requirements.txt の導入 ＋ Playwright の chromium（数百 MB）。")
        print("利用者の承認を得てから `python run.py setup --yes` を実行してください。")
        return 3
    target.parent.mkdir(parents=True, exist_ok=True)
    if not paths.venv_python().exists():
        venv.EnvBuilder(with_pip=True).create(target)
    elif not venv_healthy():                 # 動かない venv は作り直す（承認済みの場所 %LOCALAPPDATA%\pptx-deck\venv だけ）
        print(f"仮想環境が壊れています。作り直します: {target}")
        venv.EnvBuilder(with_pip=True, clear=True).create(target)
    py = str(paths.venv_python())
    req = str(paths.SKILL_DIR / "requirements.txt")
    for cmd in ([py, "-m", "pip", "install", "-r", req],
                [py, "-m", "playwright", "install", "chromium"]):
        rc = subprocess.call(cmd)
        if rc != 0:
            print(f"失敗: {' '.join(cmd)}", file=sys.stderr)
            return rc
    print("環境を作成しました:", target)
    return 0
