"""絵（pp-picture）: SVG を Chromium で PNG にして PPTX に貼る・検査する。"""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from tests import _paths  # noqa: F401
from tests._paths import PKG
from pptx_deck import cli, paths

SAMPLE = PKG / "assets" / "components" / "pictures" / "traffic-flow.html"


def run(*argv):
    buf, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
        rc = cli.main(list(argv))
    return rc, buf.getvalue(), err.getvalue()


def make_work(base: Path, fragment: str) -> Path:
    """init → 断片を 01-A に置く → finalize。final.html のある作業フォルダを返す。"""
    assert run("init", str(base), "--color", "navy")[0] == 0
    work = paths.resolve_work(base)
    (work / "slides" / "01-A.html").write_text(fragment, encoding="utf-8")
    (work / "answers-1.md").write_text("---\n---\n## S01\n- 選択: A\n- 判定: 承認\n- コメント: \n", encoding="utf-8")
    assert run("finalize", str(base))[0] == 0
    return work


def rules_of(work: Path):
    rc, out, _ = run("check", str(work / "final.html"))
    return rc, {(v["rule"], v["severity"]) for v in json.loads(out)}


class PictureBuildTest(unittest.TestCase):
    def test_sample_builds_and_places_a_transparent_3x_png(self):
        from pptx import Presentation
        from PIL import Image
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "demo"
            make_work(base, SAMPLE.read_text(encoding="utf-8"))
            rc, out, err = run("build", str(base))
            self.assertEqual(rc, 0, out + err)
            result = json.loads(out)
            self.assertTrue(result["ok"], result["violations"])
            self.assertEqual(result["violations"], [])
            prs = Presentation(str(base / "demo.pptx"))
            pics = [s for s in prs.slides[0].shapes if s.shape_type == 13]
            self.assertEqual(len(pics), 1)
            pic = pics[0]
            self.assertEqual(pic.name, "pp-picture")
            self.assertEqual((pic.left / 9525, pic.top / 9525, pic.width / 9525, pic.height / 9525), (64, 224, 1152, 366))
            self.assertIn("想定外", pic._element.nvPicPr.cNvPr.get("descr"))
            im = Image.open(__import__("io").BytesIO(pic.image.blob))
            self.assertEqual(im.size, (1152 * 3, 366 * 3))           # 3 倍の解像度
            self.assertEqual(im.mode, "RGBA")
            self.assertEqual(im.getpixel((0, 0))[3], 0)               # 透過（下地・ほかの部品が写り込まない）
            # 題・リード文・注は、編集できる文字のまま
            texts = [s.text_frame.text for s in prs.slides[0].shapes if s.has_text_frame]
            self.assertTrue(any("通信経路" in t for t in texts))
            self.assertTrue(any("遮断が必要" in t for t in texts))


class PictureCheckTest(unittest.TestCase):
    def check(self, mutate):
        frag = mutate(SAMPLE.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as td:
            return rules_of(make_work(Path(td) / "demo", frag))

    def test_sample_is_clean(self):
        self.assertEqual(self.check(lambda s: s), (0, set()))

    def test_alt_is_required(self):
        import re
        rc, rules = self.check(lambda s: re.sub(r' data-alt="[^"]*"', "", s))
        self.assertEqual(rc, 1)
        self.assertIn(("imageAlt", "error"), rules)

    def test_svg_is_required(self):
        import re
        rc, rules = self.check(lambda s: re.sub(r"<svg.*</svg>", "", s, flags=re.S))
        self.assertEqual(rc, 1)
        self.assertIn(("pictureSvg", "error"), rules)

    def test_literal_colors_are_warned(self):
        rc, rules = self.check(lambda s: s.replace('<text x="22" y="36"', '<rect x="1" y="1" width="9" height="9" fill="#ff0000"/><text x="22" y="36"'))
        self.assertEqual(rc, 0)                                       # 警告。ビルドは止めない
        self.assertIn(("pictureColor", "warning"), rules)

    def test_var_and_class_colors_are_not_warned(self):
        rc, rules = self.check(lambda s: s.replace('<text x="22" y="36"', '<rect x="1" y="1" width="9" height="9" style="fill:var(--accent)"/><text x="22" y="36"'))
        self.assertNotIn(("pictureColor", "warning"), rules)

    def test_small_text_is_an_error(self):
        rc, rules = self.check(lambda s: s.replace('<text x="94" y="236" text-anchor="middle">', '<text x="94" y="236" text-anchor="middle" font-size="14">'))
        self.assertEqual(rc, 1)
        self.assertIn(("fontMin", "error"), rules)

    def test_viewbox_scale_is_taken_into_account(self):
        # viewBox を半分にすると描画は 2 倍。20 のままでも 40px になり、検査に通る。viewBox を倍にすると 10px になり落ちる
        rc, rules = self.check(lambda s: s.replace('viewBox="0 0 1152 366"', 'viewBox="0 0 2304 732"'))
        self.assertIn(("fontMin", "error"), rules)

    def test_text_outside_the_picture_is_an_error(self):
        rc, rules = self.check(lambda s: s.replace('<text x="22" y="36"', '<text x="1100" y="36"'))
        self.assertEqual(rc, 1)
        self.assertIn(("pictureOverflow", "error"), rules)

    def test_overlapping_texts_inside_are_warned(self):
        rc, rules = self.check(lambda s: s.replace('<text x="244" y="36" font-weight="700">DMZ</text>', '<text x="244" y="36" font-weight="700">DMZ</text><text x="250" y="38">DMZ2</text>'))
        self.assertIn(("pictureTextOverlap", "warning"), rules)

    def test_overlap_with_other_parts_is_still_checked(self):
        extra = '<div class="pp-text" style="left:100px;top:300px;width:300px;height:40px">重なる文字</div>\n</section>'
        rc, rules = self.check(lambda s: s.replace("</section>", extra))
        self.assertEqual(rc, 1)
        self.assertIn(("overlap", "error"), rules)

    def test_overlap_inside_the_picture_is_not_checked(self):
        # 絵の内部（矢印・番号・吹き出しの重なり）は、重なりの検査の対象外
        rc, rules = self.check(lambda s: s.replace("</svg>", '<rect x="100" y="100" width="300" height="100" class="sv-f-light"/><rect x="150" y="120" width="300" height="100" class="sv-f-mid"/></svg>'))
        self.assertNotIn(("overlap", "error"), rules)


class PictureAssetsTest(unittest.TestCase):
    def test_parts_svg_is_valid_and_uses_only_theme_classes(self):
        import re
        import xml.etree.ElementTree as ET
        text = (PKG / "assets" / "pictures" / "parts.svg").read_text(encoding="utf-8")
        root = ET.fromstring(text)
        ids = {e.get("id") for e in root.iter() if e.get("id")}
        for need in ("i-user", "i-pc", "i-server", "i-db", "i-router", "i-switch", "i-fw", "i-lb",
                     "i-cloud", "i-internet", "i-alert", "i-doc", "m-acc", "m-emph"):
            self.assertIn(need, ids)
        self.assertEqual(re.findall(r'(?:fill|stroke)="(?!none)[^"]*"', text), [])      # 色はクラスだけ

    def test_sample_symbols_match_the_parts_library(self):
        import re
        parts = (PKG / "assets" / "pictures" / "parts.svg").read_text(encoding="utf-8")
        sample = SAMPLE.read_text(encoding="utf-8")
        for sid in re.findall(r'<symbol id="([^"]+)"', sample):
            self.assertIn(f'<symbol id="{sid}"', parts)
            a = re.search(rf'<symbol id="{sid}".*?</symbol>', sample, re.S).group(0)
            b = re.search(rf'<symbol id="{sid}".*?</symbol>', parts, re.S).group(0)
            self.assertEqual(re.sub(r"\s+", "", a), re.sub(r"\s+", "", b), sid)


if __name__ == "__main__":
    unittest.main()
