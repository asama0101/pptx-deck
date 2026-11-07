"""レビューページで直した文字を、スライドの断片（slides/NN-A.html など）へ書き戻す。標準ライブラリだけで動く。
編集できるのは文字（.pp-text・表のセル・グラフのラベル）だけ。
対象の決め方は measure 側の JS（editTargets）と一致させる。"""

import html
import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

from . import history, paths

TEXT_CLASSES = ("t-white", "t-accent", "t-emph", "t-sub", "t-dark", "b")
EDIT_DONE = "- 編集の反映: 済み"
_VOID = {"br", "img", "hr", "input", "meta", "link"}


@dataclass(frozen=True)
class Target:
    kind: str
    start: int
    end: int


class _Node:
    def __init__(self, tag, attrs, tag_start, tag_text, inner_start, parent):
        self.tag, self.attrs, self.parent = tag, attrs, parent
        self.tag_start, self.tag_text = tag_start, tag_text
        self.inner_start, self.inner_end = inner_start, None
        self.children = []

    def classes(self):
        return (self.attrs.get("class") or "").split()

    def has_ancestor(self, pred):
        n = self.parent
        while n is not None:
            if pred(n):
                return True
            n = n.parent
        return False


# 開いている p をブラウザが暗黙に閉じる開始タグ（HTML の仕様どおり）
_CLOSES_P = frozenset(
    [
        "address",
        "article",
        "aside",
        "blockquote",
        "details",
        "div",
        "dl",
        "fieldset",
        "figcaption",
        "figure",
        "footer",
        "form",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "hgroup",
        "hr",
        "main",
        "menu",
        "nav",
        "ol",
        "p",
        "pre",
        "section",
        "table",
        "ul",
    ]
)


class _Tree(HTMLParser):
    """開始・終了タグの文字位置を持つ最小の木。閉じ忘れは入れ子を保って閉じる。"""

    def __init__(self, src):
        super().__init__(convert_charrefs=False)
        self.src = src
        self.lines = [0] + [m.end() for m in re.finditer("\n", src)]
        self.root = _Node("#root", {}, 0, "", 0, None)
        self.stack = [self.root]

    def _pos(self):
        line, col = self.getpos()
        return self.lines[line - 1] + col

    def handle_starttag(self, tag, attrs, selfclose=False):
        pos = self._pos()
        self._implied_close(tag, pos)
        text = self.get_starttag_text()
        n = _Node(tag, {k: (v or "") for k, v in attrs}, pos, text, pos + len(text), self.stack[-1])
        self.stack[-1].children.append(n)
        if tag in _VOID or selfclose:
            n.inner_end = n.inner_start
        else:
            self.stack.append(n)

    def _implied_close(self, tag, pos):
        """ブラウザと同じく、開いている p は p・ブロック要素の開始で、li は同じ一覧の新しい li で暗黙に閉じる。
        間に別の容器（div・td・ul など）があれば閉じない。"""
        if tag in _CLOSES_P:
            target, stop = "p", {"div", "td", "th", "li", "ul", "ol", "table", "section"}
        elif tag == "li":
            target, stop = "li", {"ul", "ol"}
        else:
            return
        for i in range(len(self.stack) - 1, 0, -1):
            t = self.stack[i].tag
            if t == target:
                for n in self.stack[i:]:
                    n.inner_end = pos
                del self.stack[i:]
                return
            if t in stop:
                return

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs, selfclose=True)

    def handle_endtag(self, tag):
        pos = self._pos()
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                for n in self.stack[i:]:
                    n.inner_end = pos
                del self.stack[i:]
                return

    def close(self):
        super().close()
        for n in self.stack[1:]:
            n.inner_end = len(self.src)


def _parse(src):
    t = _Tree(src)
    t.feed(src)
    t.close()
    return t.root


def _walk(n):
    for c in n.children:
        yield c
        yield from _walk(c)


def _containers(root):
    """編集できる文字の容器（文書順）。.pp-picture の中と、容器の中の容器は数えない。"""
    out = []

    def visit(n):
        for c in n.children:
            if "pp-picture" in c.classes():
                continue
            is_cell = c.tag in ("td", "th") and c.has_ancestor(lambda a: "pp-table" in a.classes())
            if "pp-text" in c.classes() or is_cell:
                out.append(c)
            else:
                visit(c)

    visit(root)
    return out


def _blocks(c):
    out = []
    for ch in c.children:
        if ch.tag == "p":
            out.append(ch)
        elif ch.tag in ("ul", "ol"):
            out.extend(li for li in ch.children if li.tag == "li")
    return out


def _text_nodes(root):
    nodes = []
    for c in _containers(root):
        nodes.extend(_blocks(c) or [c])
    return nodes


def _charts(root):
    out = []

    def visit(n):
        for c in n.children:
            if "pp-picture" in c.classes():
                continue
            if "pp-chart" in c.classes():
                out.append(c)
            visit(c)

    visit(root)
    return out


def targets(src: str) -> list[Target]:
    """編集できる文字の対象を文書順に返す。start/end は元の文字列での内側の HTML の位置。"""
    return [Target("text", n.inner_start, n.inner_end) for n in _text_nodes(_parse(src))]


# ---- サニタイズ ----

_HEX = re.compile(r"^#[0-9a-fA-F]{3,8}$")
_RGB = re.compile(r"^rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*(?:,\s*[\d.]+\s*)?\)$")
_VAR = re.compile(r"^var\(--[A-Za-z0-9_-]+\)$")
_PX = re.compile(r"^\d+px$")


def _color(v):
    v = v.strip()
    if _HEX.match(v) or _VAR.match(v):
        return v
    m = _RGB.match(v)
    if m and all(int(x) <= 255 for x in m.groups()):
        r, g, b = (int(x) for x in m.groups())
        return f"#{r:02X}{g:02X}{b:02X}"
    return None


def _style(value):
    out = []
    for decl in value.split(";"):
        if ":" not in decl:
            continue
        k, v = (s.strip() for s in decl.split(":", 1))
        k = k.lower()
        if k == "color":
            v = _color(v)
        elif k == "font-size":
            v = v if _PX.match(v) else None
        elif k == "font-weight":
            v = v if v in ("700", "400", "bold") else None
        else:
            v = None
        if v:
            out.append(f"{k}:{v}")
    return ";".join(out)


class _Clean(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.out, self.open, self.skip = [], [], None

    def handle_starttag(self, tag, attrs):
        if self.skip:
            return
        if tag in ("script", "style"):
            self.skip = tag
        elif tag == "br":
            self.out.append("<br>")
        elif tag in ("b", "strong", "span"):
            a = ""
            if tag == "span":
                d = dict(attrs)
                cls = [c for c in (d.get("class") or "").split() if c in TEXT_CLASSES]
                if cls:
                    a += f' class="{" ".join(cls)}"'
                st = _style(d.get("style") or "")
                if st:
                    a += f' style="{st}"'
            self.out.append(f"<{tag}{a}>")
            self.open.append(tag)

    def handle_startendtag(self, tag, attrs):
        if self.skip:
            return
        if tag == "br":
            self.out.append("<br>")
        elif tag in ("b", "strong", "span"):
            self.handle_starttag(tag, attrs)
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if self.skip:
            if tag == self.skip:
                self.skip = None
            return
        if tag in self.open:
            while self.open:
                t = self.open.pop()
                self.out.append(f"</{t}>")
                if t == tag:
                    break

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data.replace("&", "&amp;").replace("<", "&lt;"))

    def handle_entityref(self, name):
        if not self.skip:
            self.out.append(f"&{name};")

    def handle_charref(self, name):
        if not self.skip:
            self.out.append(f"&#{name};")


_COLOR_CLASSES = TEXT_CLASSES[:5]
_TOKEN = re.compile(r"(<[^>]*>)")
_SPAN = re.compile(r'^<span(?: class="([^"]*)")?(?: style="([^"]*)")?>$')


def _decls(style):
    return [tuple(s.strip() for s in d.split(":", 1)) for d in style.split(";") if ":" in d]


def _merge_spans(s):
    """中が span 1 つだけの span を 1 つにまとめる（内側の指定が勝つ）。s は _Clean を通した形。
    reviewext の mergeSpans と同じ規則
    （色は文字色のクラスか color、太さは b クラスか font-weight を 1 つの指定とみなす）。"""
    root = ["#root", [], [], []]
    stack = [root]
    for tok in _TOKEN.split(s):
        if not tok:
            continue
        if tok.startswith("</"):
            stack.pop()
            continue
        m = _SPAN.match(tok)
        if m or tok in ("<b>", "<strong>"):
            n = ["span", (m.group(1) or "").split(), _decls(m.group(2) or ""), []] if m else [tok[1:-1], [], [], []]
            stack[-1][3].append(n)
            stack.append(n)
        else:
            stack[-1][3].append(tok)  # 文字と <br>

    def out(n):
        if isinstance(n, str):
            return n
        tag, cls, decls, kids = n
        while tag == "span" and len(kids) == 1 and not isinstance(kids[0], str) and kids[0][0] == "span":
            _, kc, kd, kk = kids[0]
            keys = [k for k, _v in kd]
            col = "color" in keys or any(c in _COLOR_CLASSES for c in kc)
            wt = "b" in kc or "font-weight" in keys
            cls = [c for c in cls if not (col and c in _COLOR_CLASSES) and not (wt and c == "b")]
            cls += [c for c in kc if c not in cls]
            decls = [
                (k, v)
                for k, v in decls
                if k not in keys and not (col and k == "color") and not (wt and k == "font-weight")
            ] + kd
            kids = kk
        a = (f' class="{" ".join(cls)}"' if cls else "") + (
            f' style="{";".join(f"{k}:{v}" for k, v in decls)}"' if decls else ""
        )
        return f"<{tag}{a}>" + "".join(out(k) for k in kids) + f"</{tag}>"

    return "".join(out(k) for k in root[3])


def sanitize_inline(html_text: str) -> str:
    """b・strong・span（許した class と style だけ）・br 以外を外し、入れ子の span をまとめる。"""
    p = _Clean()
    p.feed(html_text)
    p.close()
    while p.open:
        p.out.append(f"</{p.open.pop()}>")
    return _merge_spans("".join(p.out))


# ---- 差し込み ----

_ID = re.compile(r"^(?:t(\d+)|c(\d+)\.(cat|ser)(\d+))$")
_ATTR = re.compile(r"""data-chart\s*=\s*(?:'([^']*)'|"([^"]*)")""", re.I)


def _plain_text(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]*>", "", s))


def _plain(s: str) -> str:
    """タグを除き、実体参照を戻し、空白をすべて除いた文字。
    before との照合に使う（タグ・空白・実体参照の違いを吸収する）。"""
    return re.sub(r"\s+", "", _plain_text(s))


def _snip(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= 30 else s[:30] + "…"


def _mismatch(t, before, now):
    return ValueError(
        f"元の文字が違います（{t}。期待: {_snip(before)!r} ／ 現在: {_snip(now)!r}）。断片が回答のあとで変わっています"
    )


def _chart_edit(src, node, kind, j, after, before=None):
    m = _ATTR.search(node.tag_text)
    if not m:
        raise ValueError("data-chart がありません")
    q = "'" if m.group(1) is not None else '"'
    g = 1 if q == "'" else 2
    try:
        data = json.loads(html.unescape(m.group(g)))
        items = data["categories" if kind == "cat" else "series"]
        now = str(items[j] if kind == "cat" else items[j]["name"])
        if before is None or re.sub(r"\s+", "", before) == re.sub(r"\s+", "", now):
            if kind == "cat":
                items[j] = after
            else:
                items[j]["name"] = after
            now = None
    except (ValueError, KeyError, IndexError, TypeError) as e:
        raise ValueError(f"グラフのラベル {kind}{j} を書き換えられません") from e
    if now is not None:
        raise _mismatch(f"{kind}{j}", before, now)
    val = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("&", "&amp;")
    val = val.replace(q, "&#39;" if q == "'" else "&quot;")
    s = node.tag_start + m.start(g)
    e = node.tag_start + m.end(g)
    return src[:s] + val + src[e:]


def apply_edit(src: str, edit: dict) -> str:
    """edit = {"t": "t3" | "c0.cat2" | "c0.ser1", "after": str}。
    編集する要素（グラフは data-chart の値）の外は 1 バイトも変えない。
    data-chart の値だけは、JSON を読み直して compact（separators=(",", ":")）に書き直す。"""
    m = _ID.match(str(edit.get("t", "")))
    if not m:
        raise ValueError(f"対象の指定が読めません: {edit.get('t')!r}")
    after = edit.get("after")
    if not isinstance(after, str):
        raise ValueError("after が文字列ではありません")
    root = _parse(src)
    if m.group(1) is not None:
        nodes = _text_nodes(root)
        i = int(m.group(1))
        if i >= len(nodes):
            raise ValueError(f"対象 t{i} がありません（{len(nodes)} 件）")
        n = nodes[i]
        before = edit.get("before")
        if isinstance(before, str) and _plain(before) != _plain(src[n.inner_start : n.inner_end]):
            raise _mismatch(f"t{i}", before, _plain_text(src[n.inner_start : n.inner_end]))
        return src[: n.inner_start] + sanitize_inline(after) + src[n.inner_end :]
    charts = _charts(root)
    i = int(m.group(2))
    if i >= len(charts):
        raise ValueError(f"グラフ c{i} がありません（{len(charts)} 件）")
    return _chart_edit(
        src,
        charts[i],
        m.group(3),
        int(m.group(4)),
        after,
        edit.get("before") if isinstance(edit.get("before"), str) else None,
    )


# ---- 回答 md ----

_SLIDE = re.compile(r"^##\s+S(\d+)\b")
_EDIT = re.compile(r"^-\s*編集\s*[:：]\s*(.*)$")


def parse_edits(md: str) -> tuple[list[dict], list[str]]:
    """「## S01」の節の下の「- 編集: {json}」を読む。読めなかった行は problems に説明を入れる。"""
    edits, problems, slide = [], [], None
    for no, line in enumerate(md.splitlines(), 1):
        line = line.strip()
        m = _SLIDE.match(line)
        if m:
            slide = m.group(1)
            continue
        if line.startswith("## "):
            slide = None
            continue
        m = _EDIT.match(line)
        if not m:
            continue
        try:
            d = json.loads(m.group(1))
            if not isinstance(d, dict) or not all(isinstance(d.get(k), str) for k in ("f", "t", "after")):
                raise ValueError("f・t・after が要ります")
        except ValueError as e:
            problems.append(f"{no} 行目: 編集の行が読めません（{e}）")
            continue
        if slide is None:
            problems.append(f"{no} 行目: スライドの節（## S01）の外にあります")
            continue
        edits.append(
            {
                "slide": slide,
                "f": d["f"],
                "t": d["t"],
                "before": d["before"] if isinstance(d.get("before"), str) else None,
                "after": d["after"],
            }
        )
    return edits, problems


def has_unapplied(md: str) -> bool:
    lines = [ln.strip() for ln in md.splitlines()]
    return EDIT_DONE not in lines and any(_EDIT.match(ln) for ln in lines)


_FRAG = re.compile(r"^[0-9A-Za-z._-]+$")


def _mark_done(answers_file: Path, md: str) -> None:
    with answers_file.open("ab") as fh:
        fh.write((("" if md.endswith("\n") else "\n") + EDIT_DONE + "\n").encode("utf-8"))


def apply_answers(work: Path, answers_file: Path) -> dict:
    """回答 md の編集を断片へ反映する。先に history へ元の断片を残す。壊れた編集は skipped に入れて続ける。

    「- 編集の反映: 済み」は、編集の行が 1 つでもあれば（読めない行だけでも、全部が skipped でも）必ず足す。
    skipped は呼び出し側（apply-edits）が stderr に出して終了コード 1 にする。知らせたあとは guard を外し、
    利用者が止まり続けないようにする（読めなかった・飛ばした編集は、直して再実行するか手で直す）。"""
    work, answers_file = Path(work), Path(answers_file)
    md = paths.read_text(answers_file)
    edits, problems = parse_edits(md)
    applied, skipped = [], [{"f": "", "t": "", "reason": p} for p in problems]
    if not edits:
        if skipped:
            _mark_done(answers_file, md)
        return {"applied": applied, "skipped": skipped, "snapshot": None}
    snap = history.snapshot(work, "before-apply-edits")
    by_f = {}
    for e in edits:
        by_f.setdefault(e["f"], []).append(e)
    for f, es in by_f.items():
        path = work / "slides" / f"{f}.html"
        if not _FRAG.match(f) or not path.is_file():
            skipped += [{"f": f, "t": e["t"], "reason": f"断片 {f} がありません"} for e in es]
            continue
        text = path.read_bytes().decode("utf-8")
        for e in es:
            try:
                text = apply_edit(text, e)
                applied.append({"f": f, "t": e["t"]})
            except ValueError as ex:
                skipped.append({"f": f, "t": e["t"], "reason": str(ex)})
        path.write_bytes(text.encode("utf-8"))
    for name in ("final.html", "final-review.html"):
        (work / name).unlink(missing_ok=True)
    _mark_done(answers_file, md)
    return {"applied": applied, "skipped": skipped, "snapshot": snap["version"]}
