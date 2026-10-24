"""final.html を、1 枚で完結する閲覧・共有用の HTML にする（編集 UI なし）。"""

import base64
import re
from pathlib import Path
from urllib.parse import unquote

from . import paths

_MIME = {
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}
_LINK = re.compile(r'<link rel="stylesheet" href="(theme|base)\.css">')
_SCRIPT = '<script src="chart-preview.js" defer></script>'
_IMG_SRC = re.compile(
    r"""(<img\b[^>]*?(?<![\w-])src=(["']))((?:(?!\2)[^>])+)(\2)"""
)  # data-src= は対象外。引用符は " と ' の両方
_COMMENT_OR_IMAGE = re.compile(r"<!--.*?-->|<image\b[^>]*>", re.S)  # コメントの中の例は読み飛ばす
_HREF = re.compile(r"""(\s(?:xlink:)?href=(["']))((?:(?!\2)[^>])+)(\2)""")
_SLIDE = '<section class="slide"'
_SECTION = re.compile(r"<section\b|</section\s*>")

_CSS = """<style>
body{background:#E5E5E5;margin:0;padding:16px 0}
.frame{width:calc(1280px*var(--s,1));height:calc(720px*var(--s,1));margin:0 auto 24px;overflow:hidden}
.frame>.slide{margin:0;transform:scale(var(--s,1));transform-origin:0 0}
.note{width:calc(1280px*var(--s,1));margin:0 auto;font:13px/1.6 sans-serif;color:#555}
</style>"""
_FIT = (
    "<script>(function(){function f(){document.documentElement.style.setProperty('--s',"
    "Math.min(1,(innerWidth-32)/1280))}f();addEventListener('resize',f)})()</script>"
)
_NOTE = '<p class="note">グラフはブラウザ用の近似で、PowerPoint のグラフと軸・桁区切りが異なる場合があります。</p>'


def _data_uri(work: Path, src: str, missing: list) -> str | None:
    if re.match(r"^(data:|https?:|//|/)", src):
        return None
    f = work / unquote(src)  # ブラウザと build は %E5… を解いて探す
    mime = _MIME.get(f.suffix.lower())
    if mime is None or not f.is_file():
        missing.append(src)
        return None
    return f"data:{mime};base64," + base64.b64encode(f.read_bytes()).decode("ascii")


def _build(work: Path, missing: list) -> str:
    src = work / "final.html"
    if not src.exists():
        raise ValueError("final.html がありません（先に finalize を実行してください）")
    html = src.read_text(encoding="utf-8")
    html = _LINK.sub(lambda m: "<style>" + (work / f"{m.group(1)}.css").read_text(encoding="utf-8") + "</style>", html)
    js = (work / "chart-preview.js").read_text(encoding="utf-8").replace("</script", r"<\/script")
    html = html.replace(_SCRIPT, "<script>" + js + "</script>")

    def img(m):
        uri = _data_uri(work, m.group(3), missing)
        return m.group(1) + (uri or m.group(3)) + m.group(4)

    html = _IMG_SRC.sub(img, html)

    def image_tag(m):  # 絵（pp-picture）の SVG の中の <image href / xlink:href>。#id・data:・http は触らない
        tag = m.group(0)
        if tag.startswith("<!--"):
            return tag
        return _HREF.sub(
            lambda h: (
                h.group(1) + (_data_uri(work, h.group(3), missing) or h.group(3)) + h.group(4)
                if not h.group(3).startswith("#")
                else h.group(0)
            ),
            tag,
        )

    html = _COMMENT_OR_IMAGE.sub(image_tag, html)

    head, sep, rest = html.partition("<body>")
    tail = "</body></html>"
    if tail in rest:
        rest = rest[: rest.rindex(tail)]
    parts, pos = [], 0
    while True:  # 各スライドと、直後の空白だけを枠に入れる（そのあとの要素は枠の外）
        start = rest.find(_SLIDE, pos)
        if start < 0:
            break
        end = _slide_end(rest, start)
        if end is None:
            break
        end += len(rest[end:]) - len(rest[end:].lstrip())
        parts.append(rest[pos:start])
        parts.append(f'<div class="frame">{rest[start:end]}</div>')
        pos = end
    body = "".join(parts) + rest[pos:]
    return head.replace("</head>", _CSS + "</head>") + sep + body + _NOTE + _FIT + tail


def _slide_end(text: str, start: int) -> int | None:
    """start の <section class="slide" に対応する </section> の終わり（入れ子の section を数える）。"""
    depth = 0
    for t in _SECTION.finditer(text, start):
        depth += -1 if t.group(0).startswith("</") else 1
        if depth == 0:
            return t.end()
    return None


def build_html(work: Path) -> str:
    return _build(Path(work), [])


def export(work: Path, out: Path | None = None) -> dict:
    work = Path(work)
    missing: list = []
    html = _build(work, missing)
    out = Path(out) if out else paths.deck_dir(work) / f"{paths.deck_name(work)}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8", newline="\n")
    return {"html": str(out), "missing": sorted(set(missing))}
