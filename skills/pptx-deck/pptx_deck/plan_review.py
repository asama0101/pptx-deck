"""設計図（design.md）と原稿（script.md）を、レビューページ用の HTML にする。スライド案のページと同じ操作で承認／要修正を返す。"""
import html as _html
import re
from pathlib import Path

from . import script_lint, variants

_PAGE_HEAD = re.compile(r"^### S(\d{2})\b.*$", re.M)


def parse_design(md: str) -> tuple[str, dict[str, str]]:
    """資料全体（『## ページごと』より前）と、ページごとの Markdown（### SNN …）に分ける。"""
    head, _, tail = md.partition("\n## ページごと")
    overview = re.sub(r"^# .*\n", "", head, count=1).strip()
    pages: dict[str, str] = {}
    ms = list(_PAGE_HEAD.finditer(tail))
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(tail)
        pages[m.group(1)] = tail[m.start():end].strip()
    return overview, pages


def _md_html(text: str) -> str:
    """設計図・原稿の簡易表示（見出し・箇条書き・表・段落）。HTML は必ずエスケープする。"""
    out, in_list, rows = [], False, []

    def flush():
        nonlocal in_list, rows
        if in_list:
            out.append("</ul>")
            in_list = False
        if rows:
            body = [r for r in rows if not re.fullmatch(r"\|[\s\-:|]+\|", r)]
            cells = [[_html.escape(c.strip()) for c in r.strip("|").split("|")] for r in body]
            out.append("<table>" + "".join(
                "<tr>" + "".join(f"<{'th' if i == 0 else 'td'}>{c}</{'th' if i == 0 else 'td'}>" for c in row) + "</tr>"
                for i, row in enumerate(cells)) + "</table>")
            rows = []

    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("|"):
            if in_list:
                flush()
            rows.append(line)
            continue
        if rows:
            flush()
        m = re.match(r"^(\s*)[-*] (.*)$", line)
        if m:
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li style=\"margin-left:{len(m.group(1)) * 6}px\">{_html.escape(m.group(2))}</li>")
            continue
        flush()
        h = re.match(r"^(#{1,4}) (.*)$", line)
        if h:
            out.append(f"<h4>{_html.escape(h.group(2))}</h4>")
        elif line.strip() and not line.startswith("<!--"):
            out.append(f"<p>{_html.escape(line)}</p>")
    flush()
    return "".join(out)


def build_docs(design_md: str, script_md: str) -> tuple[dict[str, str], dict[str, str]]:
    overview, pages = parse_design(design_md)
    docs = {"00": '<h3>資料全体</h3>' + _md_html(overview)}
    titles = {"00": "資料全体"}
    head = script_md.split("\n## S", 1)[0]
    docs["00"] += '<h3>原稿の冒頭（目的・対象・論点）</h3>' + _md_html(head)
    for s in script_lint.parse(script_md):
        nn = s["id"][1:]
        f = s["fields"]
        titles[nn] = (f.get("題") if isinstance(f.get("題"), str) and f.get("題") else s["title"]) or s["id"]
        rows = "".join(
            f"<tr><th>{_html.escape(k)}</th><td>{_html.escape(v if isinstance(v, str) else ' / '.join(v))}</td></tr>"
            for k, v in f.items())
        body = f'<h3>S{nn}　{_html.escape(s["title"])}</h3><h4>原稿</h4><table>{rows}</table>'
        if nn in pages:
            body += "<h4>設計図</h4>" + _md_html(pages[nn])
        else:
            body += "<p><b>設計図にこのスライドのページがありません</b></p>"
        docs[nn] = body
    for nn in sorted(set(pages) - set(docs)):                       # 原稿に無い設計図のページも、不整合として見せる
        first = pages[nn].splitlines()[0]
        titles[nn] = re.sub(r"^###\s*S\d{2}\s*", "", first).strip() or nn
        docs[nn] = "<p><b>原稿にこのスライドがありません</b></p>" + _md_html(pages[nn])
    return docs, titles


def assemble(work: Path, round_no: int | None = None) -> Path:
    work = Path(work)
    docs, titles = build_docs((work / "design.md").read_text(encoding="utf-8"),
                              (work / "script.md").read_text(encoding="utf-8"))
    paths_ = variants.plan_answer_paths(work)
    n = round_no or variants.plan_next_round(work)
    preset = variants.approved_preset([p.read_text(encoding="utf-8") for p in paths_])
    out = work / "plan-review.html"
    frags = {nn: {"A": ""} for nn in docs}
    out.write_text(variants._page(work, frags, f"plan-{n}", docs=docs, titles=titles, preset=preset), encoding="utf-8")
    return out
