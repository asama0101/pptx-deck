import json
import re
import tempfile
import unittest
from pathlib import Path

from tests import _paths  # noqa: F401
from tests._paths import PKG
from pptx_deck import initdir


class NoLibreOfficeTest(unittest.TestCase):
    def test_no_soffice_in_code(self):
        for f in (PKG / "pptx_deck").glob("*.py"):
            self.assertNotIn("soffice", f.read_text(encoding="utf-8"), f.name)
        self.assertFalse((PKG / "pptx_deck" / "render.py").exists())

    def test_init_makes_solid_background_only(self):
        with tempfile.TemporaryDirectory() as td:
            work = Path(td) / "d"
            initdir.init(work, color="navy")
            src = work / "source" if (work / "source").is_dir() else work     # Task 7 の前後どちらでも通す
            css = (src / "theme.css").read_text(encoding="utf-8")
            self.assertNotIn("background-image", css)
            self.assertRegex(css, r"--bg: #[0-9A-Fa-f]{6}")
            self.assertEqual([p.name for p in (src / "_template").iterdir()], ["template.potx"])
            cfg = json.loads((src / "template.json").read_text(encoding="utf-8"))
            self.assertIn("info", cfg)


class PreviewTest(unittest.TestCase):
    def test_screenshots_one_per_slide(self):
        from pptx_deck import preview
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            html = td / "final.html"
            html.write_text('<!doctype html><meta charset="utf-8"><style>.slide{position:relative;width:1280px;height:720px;background:#fff;margin:0 0 24px}</style>'
                            '<section class="slide">A</section><section class="slide">B</section>', encoding="utf-8")
            out = preview.screenshots(html, td / "out")
            self.assertEqual([p.name for p in out], ["slide-01.png", "slide-02.png"])
            self.assertTrue(all(p.stat().st_size > 0 for p in out))


if __name__ == "__main__":
    unittest.main()
