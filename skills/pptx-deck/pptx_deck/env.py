"""仮想環境の状態確認と作成。標準ライブラリのみ。"""
import subprocess
import sys
import venv

from . import paths

# import 名 → pip 名
MODULES = {"pptx": "python-pptx", "playwright": "playwright", "fitz": "pymupdf", "lxml": "lxml"}

_CHROMIUM_PROBE = (
    "from playwright.sync_api import sync_playwright as s;"
    "p=s().start();import os;print(os.path.exists(p.chromium.executable_path));p.stop()"
)


def _py(code: str) -> subprocess.CompletedProcess:
    return subprocess.run([str(paths.venv_python()), "-c", code],
                          capture_output=True, text=True, timeout=120)


def venv_healthy() -> bool:
    """venv の python.exe が実際に動くか（基底の Python が消えた venv は、ファイルがあっても動かない）。"""
    try:
        return subprocess.run([str(paths.venv_python()), "-c", "pass"],
                              capture_output=True, timeout=60).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def status() -> dict:
    st = {"venv": paths.venv_python().exists(), "modules": {}, "chromium": False}
    if not st["venv"]:
        st["modules"] = {m: False for m in MODULES}
        return st
    for m in MODULES:
        st["modules"][m] = _py(f"import {m}").returncode == 0
    if st["modules"]["playwright"]:
        r = _py(_CHROMIUM_PROBE)
        st["chromium"] = r.returncode == 0 and r.stdout.strip() == "True"
    return st


def ready(st: dict | None = None) -> bool:
    st = st or status()
    return st["venv"] and all(st["modules"].values()) and st["chromium"]


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
