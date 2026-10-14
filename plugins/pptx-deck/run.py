"""入口。標準ライブラリのみ。システムの Python（なければ共通の仮想環境）で pptx_deck を実行する。

  python run.py setup [--yes]   # 仮想環境の作成（--yes は利用者の承認後）
  python run.py <サブコマンド>   # それ以外は選んだ Python に渡す
"""
import json
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
    sel = env.select_python()
    if sel.kind == "none":
        print("実行できる Python 環境がありません。")
        print("- システムの Python: " + "、".join(sel.system_missing))
        print(f"- 仮想環境（{paths.venv_dir()}）: " + "、".join(sel.venv_missing))
        print(f"利用者に「{paths.venv_dir()} に仮想環境と chromium（数百 MB）を導入してよいか」を確認し、"
              "承認後に `python run.py setup --yes` を実行してください。システムの Python には何も入れません。")
        return 3
    e = {**os.environ, "PYTHONPATH": str(SKILL), "PYTHONUTF8": "1", "PPTX_DECK_PYTHON_KIND": sel.kind,
         "PPTX_DECK_SYSTEM_MISSING": json.dumps(sel.system_missing, ensure_ascii=False)}
    return subprocess.call([str(sel.path), "-m", "pptx_deck", *argv], env=e)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
