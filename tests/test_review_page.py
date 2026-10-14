import tempfile
import unittest
from pathlib import Path

from tests import _paths  # noqa: F401
from pptx_deck import variants

FRAG = ('<section class="slide" data-layout="content" data-variant="{n}｜理由">'
        '<div class="pp-text" data-role="title" style="left:64px;top:30px;width:900px;height:40px">題{n}</div></section>')


def make_page(preset, final=False):
    frags = {nn: ({"A": FRAG.format(n=nn)} if final else {"A": FRAG.format(n=nn + "a"), "B": FRAG.format(n=nn + "b")})
             for nn in ("01", "02", "03")}
    return variants._page(Path("deck"), frags, "final" if final else "2", final=final, preset=preset)


class PageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls._pw = sync_playwright().start()
        cls.browser = cls._pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls._pw.stop()

    def open(self, html, td):
        f = Path(td) / "p.html"
        f.write_text(html, encoding="utf-8")
        page = self.browser.new_page(viewport={"width": 1400, "height": 900})
        page.goto(f.as_uri())
        page.wait_for_timeout(200)
        return page

    def test_preset_is_selected_and_copied(self):
        with tempfile.TemporaryDirectory() as td:
            page = self.open(make_page({"01": {"c": "B", "d": 1, "v": "承認"}}), td)
            self.assertEqual(page.evaluate("document.querySelector('.pane[data-slide=\"01\"] input[value=B]').checked"), True)
            self.assertEqual(page.evaluate("document.querySelector('.pane[data-slide=\"02\"] input[type=radio]:checked') === null"), True)
            page.click(".pane[data-slide=\"01\"] .copyBtn")
            md = page.evaluate("window.__answersMd")
            self.assertIn("## S01\n- 選択: B", md)
            self.assertIn("- 判定: 承認", md)
            self.assertNotIn("## S02", md)

    def test_final_preset_marks_approved(self):
        with tempfile.TemporaryDirectory() as td:
            page = self.open(make_page({"02": {"c": "A", "d": 1, "v": "承認"}}, final=True), td)
            self.assertEqual(page.evaluate("document.querySelector('.pane[data-slide=\"02\"] input[value=A]').checked"), True)

    def test_approve_moves_to_next_but_not_fix_or_last(self):
        with tempfile.TemporaryDirectory() as td:
            page = self.open(make_page({}), td)
            cur = "document.querySelector('#nav button[aria-current=true]').dataset.go"
            self.assertEqual(page.evaluate(cur), "01")
            page.click(".pane[data-slide=\"01\"] .verdict .ng")           # 要修正
            self.assertEqual(page.evaluate(cur), "01")
            page.click(".pane[data-slide=\"01\"] .verdict .ng")           # 外す
            page.click(".pane[data-slide=\"01\"] .verdict .ok")           # 承認
            self.assertEqual(page.evaluate(cur), "02")
            page.click(".pane[data-slide=\"02\"] .verdict .ok")
            page.click(".pane[data-slide=\"03\"] .verdict .ok")           # 最後は動かない
            self.assertEqual(page.evaluate(cur), "03")


if __name__ == "__main__":
    unittest.main()
