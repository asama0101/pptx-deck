"""入口。標準ライブラリのみ。共通の仮想環境の Python で pptx_deck を実行する。

  python run.py setup [--yes]   # 仮想環境の作成（--yes は利用者の承認後）
  python run.py <サブコマンド>   # それ以外は venv の Python に渡す
"""
import os
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent
sys.path.insert(0, str(SKILL))

from pptx_deck import env, paths  # noqa: E402  標準ライブラリのみで動く


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # 子プロセス（PYTHONUTF8=1）と出力の文字コードをそろえる
    if argv[:1] == ["setup"]:
        return env.setup(yes="--yes" in argv)
    py = paths.venv_python()
    if not py.exists():
        print(f"仮想環境がありません: {paths.venv_dir()}")
        print("利用者に「環境を作ってよいか」を確認し、承認後に `python run.py setup --yes` を実行してください。")
        return 3
    e = {**os.environ, "PYTHONPATH": str(SKILL), "PYTHONUTF8": "1"}
    return subprocess.call([str(py), "-m", "pptx_deck", *argv], env=e)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
