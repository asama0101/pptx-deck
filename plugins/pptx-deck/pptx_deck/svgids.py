"""絵（pp-picture）の SVG の id を、絵ごとに一意にする。

`<symbol id="i-server">`・`<marker id="m-acc">` のような定義は、どの絵にも同じ名前で写して使う。ところが 1 つの HTML（final.html・確認ページ）に絵が
2 枚以上あると、`<use href="#i-server">` や `marker-end="url(#m-acc)"` は、文書の中で最初に見つかった定義（前のスライドの絵）を参照してしまう。
絵を 1 枚ずつ撮るときは前のスライドが隠れているので、アイコンや矢じりが消える。そこで、断片を束ねるときに、絵の中の id と参照へ接頭辞を付ける。
断片のファイル（source/slides/）は書き換えない。"""
import re

_PICTURE = re.compile(r'(<div\b[^>]*\bclass="[^"]*\bpp-picture\b[^"]*"[^>]*>)(.*?)(</div>)', re.S)
_ID = re.compile(r'\bid="([^"]+)"')


def uniquify(fragment: str, prefix: str) -> str:
    """断片の中の各 pp-picture について、<svg> の中の id（と href="#…"・url(#…) の参照）に prefix を付ける。"""
    def one(m: "re.Match[str]") -> str:
        head, body, tail = m.group(1), m.group(2), m.group(3)
        ids = set(_ID.findall(body))
        if not ids:
            return m.group(0)
        for i in sorted(ids, key=len, reverse=True):          # 長い id から（i-server と i-server2 の取り違えを避ける）
            e = re.escape(i)
            body = re.sub(rf'\bid="{e}"', f'id="{prefix}{i}"', body)
            body = re.sub(rf'(href="#){e}(")', rf'\g<1>{prefix}{i}\g<2>', body)
            body = re.sub(rf'url\(#{e}\)', f'url(#{prefix}{i})', body)
        return head + body + tail

    return _PICTURE.sub(one, fragment)
