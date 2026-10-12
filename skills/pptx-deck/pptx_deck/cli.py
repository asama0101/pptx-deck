import argparse
import glob
import json
import os
import shutil
import sys
from pathlib import Path

from . import env, paths


def _has_font(registered: list[str], family: str) -> bool:
    return any(family in name for name in registered)


def _registered_fonts() -> list[str]:
    """レジストリの登録名（全員向け・利用者向け）。TTC 内のファミリも登録名に並ぶ。"""
    import winreg
    names: list[str] = []
    for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(root, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts") as k:
                i = 0
                while True:
                    names.append(winreg.EnumValue(k, i)[0])
                    i += 1
        except OSError:
            pass
    return names


def _font_installed() -> bool:
    return _has_font(_registered_fonts(), "BIZ UDPGothic")


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


def _load_cfg(work: Path):
    from . import template, theme
    cfg = json.loads((work / "template.json").read_text(encoding="utf-8"))
    return cfg, template.TemplateInfo.from_dict(cfg["info"]), theme.derive(cfg["color"])


def cmd_check(args) -> int:
    from . import check, measure
    html = Path(args.html)
    work = Path(args.workdir) if args.workdir else html.parent
    _, info, _ = _load_cfg(work)
    violations = check.check_model(measure.measure(html), info)
    print(json.dumps(violations, ensure_ascii=False, indent=2))
    return 1 if check.errors(violations) else 0


def cmd_build(args) -> int:
    from . import build, check, measure, render
    work = Path(args.workdir).resolve()
    name = work.name
    cfg, info, palette = _load_cfg(work)
    html = work / "final.html"
    if not html.exists():
        print("エラー: final.html がありません（先に finalize を実行してください）", file=sys.stderr)
        return 2
    model = measure.measure(html)
    violations = check.check_model(model, info)
    result = {"ok": False, "violations": violations, "pptx": None, "pngs": [], "notes": list(info.notes)}
    if check.errors(violations):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1
    out = work / f"{name}.pptx"
    footer = args.footer if args.footer is not None else cfg.get("footer")
    build.build(model, work / cfg["template"], info, palette, out, base_dir=work, footer=footer, work_name=name)
    violations += check.check_pptx(out)
    result["violations"] = violations
    result["pptx"] = str(out)
    try:
        result["pngs"] = [str(p) for p in render.pptx_to_pngs(out, paths.temp_dir(name) / "render")]
    except RuntimeError as e:
        result["notes"].append(str(e))
    result["ok"] = not check.errors(violations)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


def cmd_variants(args) -> int:
    from . import variants
    print(variants.assemble(Path(args.workdir), round_no=args.round))
    return 0


def cmd_finalize(args) -> int:
    from . import variants
    md = Path(args.answers).read_text(encoding="utf-8")
    try:
        print(variants.finalize(Path(args.workdir), md, allow_comments=args.allow_comments))
    except ValueError as e:
        print(f"エラー:\n{e}", file=sys.stderr)
        return 2
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
    p = sub.add_parser("check")
    p.add_argument("html")
    p.add_argument("--workdir", default=None)
    p.set_defaults(fn=cmd_check)
    p = sub.add_parser("build")
    p.add_argument("workdir")
    p.add_argument("--footer", default=None)
    p.set_defaults(fn=cmd_build)
    p = sub.add_parser("variants")
    p.add_argument("workdir")
    p.add_argument("--round", type=int, default=1)
    p.set_defaults(fn=cmd_variants)
    p = sub.add_parser("finalize")
    p.add_argument("workdir")
    p.add_argument("--answers", required=True)
    p.add_argument("--allow-comments", action="store_true")
    p.set_defaults(fn=cmd_finalize)
    args = ap.parse_args(argv)
    return args.fn(args)
