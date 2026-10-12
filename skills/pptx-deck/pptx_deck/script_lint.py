"""原稿（script.md）の書式を検査する。内容の良し悪しは見ない。"""
import re

from . import theme

LAYOUTS = {"cover", "section", "agenda", "content", "diagram", "table", "chart", "closing"}
_SLIDE = re.compile(r"^## (S\d{2})\s*(.*)$")
_NEAR_MISS = re.compile(r"^#{2,3}\s*[Ss]\d+")
_FIELD = re.compile(r"^- ([^:：]+)[:：]\s*(.*)$")
_ITEM = re.compile(r"^\s+- (.*)$")


def parse(md: str) -> list[dict]:
    slides, cur, field = [], None, None
    for line in md.splitlines():
        m = _SLIDE.match(line)
        if m:
            cur = {"id": m.group(1), "title": m.group(2).strip(), "fields": {}}
            slides.append(cur)
            field = None
            continue
        if cur is None:
            continue
        f = _FIELD.match(line)
        if f:
            field = f.group(1).strip()
            cur["fields"][field] = f.group(2).strip() if f.group(2).strip() else []
            continue
        it = _ITEM.match(line)
        if it and field is not None:
            if not isinstance(cur["fields"][field], list):
                cur["fields"][field] = [cur["fields"][field]]
            cur["fields"][field].append(it.group(1).strip())
    return slides


def _header_color(md: str):
    for line in md.splitlines():
        if line.startswith("## "):
            break
        m = _FIELD.match(line)
        if m and m.group(1).strip() == "配色":
            return m.group(2).strip()
    return None


def lint(md: str) -> list[str]:
    slides = parse(md)
    if not slides:
        return ["スライド（## S01 …）がありません"]
    out = []
    for line in md.splitlines():     # 見出しの書き損じ（## S1・### S02・##S02・## s02）は、前のスライドに混ざるので先に知らせる
        if _NEAR_MISS.match(line) and not _SLIDE.match(line):
            out.append(f"見出しの書式が不正です: {line.strip()!r}（`## S01 名前` の形にしてください）")
    color = _header_color(md)
    if color:
        try:
            theme.resolve(color)
        except ValueError as e:
            out.append(f"配色: {e}")
    for i, s in enumerate(slides, start=1):
        sid, f = s["id"], s["fields"]
        if sid != f"S{i:02d}":
            out.append(f"{sid}: 番号が連番ではありません（{i} 番目は S{i:02d}）")
        layout = f.get("layout")
        if layout not in LAYOUTS:
            out.append(f"{sid}: layout が不正です: {layout!r}（{', '.join(sorted(LAYOUTS))}）")
        if i == 1 and layout != "cover":
            out.append(f"{sid}: 最初のスライドは表紙（layout: cover）にしてください")
        if not f.get("見出し"):
            out.append(f"{sid}: 見出しがありません")
        if layout not in ("cover", "closing") and not f.get("章名"):
            out.append(f"{sid}: 章名（そのスライドが答える問い）がありません")
        if layout not in ("cover", "closing", "agenda") and not (f.get("本文") or f.get("図表")):
            out.append(f"{sid}: 本文か図表のどちらかが必要です")
        if layout in ("diagram", "table", "chart") and not f.get("図表"):
            out.append(f"{sid}: layout が {layout} のときは図表（型と理由）が必要です")
    return out
