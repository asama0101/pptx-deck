"""下書きの確認。slides/ の断片を、回答（案の選択）を待たずに 1 つの一時 HTML（draft-*.html）に束ねて、
確認用の画像と検査の結果を返す。
絵の往復（描く → 見る → 直す）で、直すたびに使う。
finalize・build の代わりではない（PPTX は出さない。派生ファイルも消さない）。"""

import html as _html
import tempfile
from pathlib import Path

from . import paths, variants


def assemble(work: Path, pick: str = "A", slides: list[str] | None = None) -> tuple[Path, list[str]]:
    """slides/ の断片を束ねて一時の draft-*.html にする（呼び出し側が消す）。
    各スライドは pick の案（なければ最初の案）のデザイン 1。
    slides（例 ["02", "03"]）を渡すと、そのスライドだけ。戻り値は（一時 HTML のパス, 含めたスライド番号）。"""
    work = Path(work)
    designs = variants.collect_designs(work)
    nns = sorted(designs)
    if slides:
        slides = [s.zfill(2) for s in slides]
        missing = [s for s in slides if s not in designs]
        if missing:
            raise ValueError(f"slides/ に {', '.join(missing)} の断片がありません")
        nns = sorted(slides)
    body = []
    for nn in nns:
        opts = designs[nn]
        key = pick if pick in opts else sorted(opts)[0]
        body.append(opts[key][1])
    # 実行ごとに一意な名前にする（連続・並走しても互いを上書きしない）。base.css 等の相対参照のため work の中に置く
    with tempfile.NamedTemporaryFile(
        "w", dir=work, prefix="draft-", suffix=".html", delete=False, encoding="utf-8"
    ) as f:
        f.write(
            variants.HEAD.format(title=_html.escape(paths.deck_name(work)), extra="")
            + "\n".join(body)
            + "</body></html>"
        )
    return Path(f.name), nns
