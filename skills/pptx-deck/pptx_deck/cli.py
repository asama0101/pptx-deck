import argparse
import glob
import json
import os
import shutil
import sys
from pathlib import Path

from . import env, paths


def _font_installed() -> bool:
    fonts = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
    return bool(glob.glob(os.path.join(fonts, "BIZ-UDPGothic*")))


def cmd_doctor(args) -> int:
    st = env.status()
    out = {
        "venv": str(paths.venv_dir()),
        "status": st,
        "libreoffice": bool(shutil.which("soffice") or os.path.exists(
            r"C:\Program Files\LibreOffice\program\soffice.exe")),
        "font_biz_udp_gothic": _font_installed(),
    }
    warnings = []
    if not out["libreoffice"]:
        warnings.append("LibreOffice がありません。確認用の画像が作れません。")
    if not out["font_biz_udp_gothic"]:
        warnings.append("BIZ UDPゴシックが未導入です。計測は代替フォントで行うため、折り返しが PowerPoint とずれる場合があります。")
    out["warnings"] = warnings
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if env.ready(st) else 1


def cmd_init(args) -> int:
    from . import initdir
    try:
        r = initdir.init(Path(args.workdir), color=args.color, template_path=args.template, force=args.force)
    except (FileExistsError, ValueError) as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 2
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="pptx-deck")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor").set_defaults(fn=cmd_doctor)
    p = sub.add_parser("init")
    p.add_argument("workdir")
    p.add_argument("--color", default="navy", help="プリセット名（navy|green|gray）または #RRGGBB")
    p.add_argument("--template", default=None, help="利用者の .potx / .pptx")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_init)
    args = ap.parse_args(argv)
    return args.fn(args)
