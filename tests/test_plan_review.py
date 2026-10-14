import tempfile
import unittest
from pathlib import Path

from tests import _paths  # noqa: F401
from tests._paths import PKG
from pptx_deck import plan_review

DESIGN = (PKG / "assets" / "sample" / "design.md").read_text(encoding="utf-8")
SCRIPT = (PKG / "assets" / "sample" / "script.md").read_text(encoding="utf-8")


class ParseTest(unittest.TestCase):
    def test_parse_design(self):
        overview, pages = plan_review.parse_design(DESIGN)
        self.assertIn("ガバニングメッセージ", overview)
        self.assertIn("台帳", overview)
        self.assertEqual(sorted(pages), ["04"])
        self.assertIn("レイアウト記述", pages["04"])

    def test_build_docs_covers_every_script_slide_plus_overview(self):
        docs, titles = plan_review.build_docs(DESIGN, SCRIPT)
        self.assertEqual(sorted(docs)[0], "00")
        self.assertEqual(len(docs), 11 + 1)                       # 見本の原稿は 11 枚 + 資料全体
        self.assertEqual(titles["00"], "資料全体")
        self.assertIn("削減で生む原資が成長投資を支えるため", docs["02"])      # 見出し（リード文）が出る
        self.assertIn("レイアウト記述", docs["04"])                  # 設計図のページ記述が合流する


class AssembleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls._pw = sync_playwright().start()
        cls.browser = cls._pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls._pw.stop()

    def test_page_works_like_review_pages(self):
        with tempfile.TemporaryDirectory() as td:
            work = Path(td) / "deck" / "source"
            work.mkdir(parents=True)
            (work / "design.md").write_text(DESIGN, encoding="utf-8")
            (work / "script.md").write_text(SCRIPT, encoding="utf-8")
            (work / "answers-plan-1.md").write_text("---\n---\n## S02\n- 選択: A\n- 判定: 承認\n- コメント: \n", encoding="utf-8")
            out = plan_review.assemble(work, round_no=2)
            self.assertEqual(out.name, "plan-review.html")
            page = self.browser.new_page(viewport={"width": 1400, "height": 900})
            page.goto(out.as_uri())
            page.wait_for_timeout(200)
            self.assertEqual(page.evaluate("document.querySelectorAll('.pane').length"), 12)
            self.assertEqual(page.evaluate("document.querySelector('.pane[data-slide=\"02\"] input[value=A]').checked"), True)   # 前回承認
            page.click(".pane[data-slide=\"00\"] .verdict .ok")                                                              # 承認で次へ
            self.assertEqual(page.evaluate("document.querySelector('#nav button[aria-current=true]').dataset.go"), "01")
            page.click(".pane[data-slide=\"01\"] .copyBtn")
            md = page.evaluate("window.__answersMd")
            self.assertIn("round: plan-2", md)
            self.assertIn("## S00", md)
            self.assertIn("## S02", md)


if __name__ == "__main__":
    unittest.main()
