"""作業フォルダ（実行ディレクトリ直下の <名前>/）の初期化。"""
import json
import shutil
from pathlib import Path

from . import paths, template, theme

ICON_TONES = ("accent", "emphasis", "white", "gray")


def _write_icons(dst: Path, p: theme.Palette):
    src = paths.ASSETS / "icons"
    if not src.is_dir():
        return
    colors = {"accent": p.accent, "emphasis": p.emphasis, "white": "#FFFFFF", "gray": p.text_sub}
    dst.mkdir(parents=True, exist_ok=True)
    for svg in sorted(src.glob("*.svg")):
        text = svg.read_text(encoding="utf-8")
        for tone in ICON_TONES:
            (dst / f"{svg.stem}-{tone}.svg").write_text(text.replace("currentColor", colors[tone]), encoding="utf-8")


def init(workdir, color: str = "navy", template_path=None, force: bool = False) -> dict:
    work = Path(workdir)
    base = theme.resolve(color)                                   # 不正なら何も作らずに失敗
    palette = theme.derive(base)
    src = Path(template_path) if template_path else paths.ASSETS / "template" / "standard.potx"
    info = template.analyze(src)                                  # 非 16:9 などもここで失敗
    if work.exists() and any(work.iterdir()) and not force:
        raise FileExistsError(f"{work} は空ではありません。中身を確認し、上書きしてよければ --force を付けてください")
    work.mkdir(parents=True, exist_ok=True)
    tdir = work / "_template"
    tdir.mkdir(exist_ok=True)
    dst = tdir / f"template{src.suffix.lower()}"
    shutil.copyfile(src, dst)
    bg = template.render_underlays(dst, info, tdir)
    (work / "theme.css").write_text(theme.theme_css(palette) + template.layout_css(info, bg), encoding="utf-8")
    shutil.copyfile(paths.ASSETS / "web" / "base.css", work / "base.css")
    preview = paths.ASSETS / "web" / "chart-preview.js"
    if preview.exists():
        shutil.copyfile(preview, work / "chart-preview.js")
    _write_icons(work / "icons", palette)
    (work / "slides").mkdir(exist_ok=True)
    (work / "template.json").write_text(json.dumps({
        "color": base, "template": f"_template/{dst.name}", "info": info.to_dict(), "footer": None,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"workdir": str(work), "color": base, "template": str(dst), "notes": list(info.notes)}
