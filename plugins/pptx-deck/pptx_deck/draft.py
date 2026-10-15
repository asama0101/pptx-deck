"""下書きの確認。slides/ の断片を、回答（案の選択）を待たずに 1 つの HTML（draft.html）に束ねて、確認用の画像と検査の結果を返す。
絵の往復（描く → 見る → 直す）で、直すたびに使う。finalize・build の代わりではない（PPTX は出さない。派生ファイルも消さない）。"""
import html as _html
from pathlib import Path

from . import paths, variants


def assemble(work: Path, pick: str = "A", slides: list[str] | None = None) -> tuple[Path, list[str]]:
    """slides/ の断片を束ねて draft.html にする。各スライドは pick の案（なければ最初の案）のデザイン 1。
    slides（例 ["02", "03"]）を渡すと、そのスライドだけ。戻り値は（draft.html のパス, 含めたスライド番号）。"""
    work = Path(work)
    designs = variants.collect_designs(work)
    nns = sorted(designs)
    if slides:
        missing = [s for s in slides if s not in designs]
        if missing:
            raise ValueError(f"slides/ に {', '.join(missing)} の断片がありません")
        nns = sorted(slides)
    body = []
    for nn in nns:
        opts = designs[nn]
        key = pick if pick in opts else sorted(opts)[0]
        body.append(opts[key][1])
    out = work / "draft.html"
    out.write_text(variants.HEAD.format(title=_html.escape(paths.deck_name(work)), extra="") + "\n".join(body) + "</body></html>",
                   encoding="utf-8")
    return out, nns
