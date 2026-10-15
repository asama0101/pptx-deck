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


PART_FRAG = ('<section class="slide" data-layout="content" style="position:relative;width:1280px;height:720px">'
             '<div class="pp-text" data-role="title" data-part="タイトル" style="position:absolute;left:64px;top:30px;width:900px;height:40px">題</div>'
             '<div class="pp-shape f-white" data-part="スティッカー" style="position:absolute;left:700px;top:300px;width:100px;height:30px"></div>'
             '<div class="pp-shape f-white" data-part="スティッカー" style="position:absolute;left:100px;top:300px;width:100px;height:30px"></div>'
             '<div class="pp-text" data-role="caption" data-part="注釈" style="position:absolute;left:64px;top:600px;width:900px;height:30px">注: x</div>'
             '</section>')


class PartBadgeTest(unittest.TestCase):
    setUpClass = classmethod(PageTest.setUpClass.__func__)
    tearDownClass = classmethod(PageTest.tearDownClass.__func__)
    open = PageTest.open
    def page_with_parts(self, td):
        frags = {"01": {"A": PART_FRAG, "B": PART_FRAG}, "02": {"A": PART_FRAG}}
        return self.open(variants._page(Path("deck"), frags, "1"), td)

    def test_badges_numbered_top_left_to_bottom_right(self):
        with tempfile.TemporaryDirectory() as td:
            page = self.page_with_parts(td)
            names = page.evaluate("Array.from(document.querySelectorAll('.pane[data-slide=\"01\"] .pt')).map(b => b.textContent)")
            # 同じ部位が複数あるものだけに番号を付け、左上から右下の順（左のスティッカーが①）
            self.assertEqual(names, ["タイトル", "スティッカー①", "スティッカー②", "注釈"])
            left1 = page.evaluate("parseFloat(document.querySelectorAll('.pane[data-slide=\"01\"] .pt')[1].style.left)")
            self.assertEqual(left1, 100)

    def test_part_comment_is_recorded_and_sets_fix(self):
        with tempfile.TemporaryDirectory() as td:
            page = self.page_with_parts(td)
            page.click(".pane[data-slide=\"01\"] .pt:has-text('注釈')")
            page.fill(".pane[data-slide=\"01\"] .plist textarea", "出典を足す")
            page.click(".pane[data-slide=\"01\"] .copyBtn")
            md = page.evaluate("window.__answersMd")
            self.assertIn("## S01", md)
            self.assertIn("- 判定: 要修正", md)
            self.assertIn("- 部位: 案 A 注釈 ／ コメント: 出典を足す", md)
            a = variants.parse_answers(md)["01"]
            self.assertEqual(a["parts"], [{"part": "案 A 注釈", "comment": "出典を足す"}])

    def test_single_slide_part_label_has_no_variant(self):
        with tempfile.TemporaryDirectory() as td:
            page = self.page_with_parts(td)
            page.click("#nav button[data-go=\"02\"]")
            page.click(".pane[data-slide=\"02\"] .pt:has-text('タイトル')")
            page.fill(".pane[data-slide=\"02\"] .plist textarea", "短く")
            page.click(".pane[data-slide=\"02\"] .copyBtn")
            self.assertIn("- 部位: タイトル ／ コメント: 短く", page.evaluate("window.__answersMd"))

    def test_empty_part_row_is_not_recorded(self):
        with tempfile.TemporaryDirectory() as td:
            page = self.page_with_parts(td)
            page.click(".pane[data-slide=\"01\"] .pt:has-text('注釈')")        # 行は開くが、何も書かない
            page.click(".pane[data-slide=\"01\"] .verdict .ok")           # 承認すると次のスライドへ進む
            page.click(".pane[data-slide=\"02\"] .copyBtn")
            self.assertNotIn("部位:", page.evaluate("window.__answersMd"))


class PartAnswersTest(unittest.TestCase):
    MD = "## S01\n- 選択: A\n- 判定: 要修正\n- コメント: 全体\n- 部位: スティッカー② ／ コメント: 文言を短く\n"

    def test_part_comment_counts_as_unreflected_comment(self):
        with tempfile.TemporaryDirectory() as td:
            work = Path(td)
            (work / "slides").mkdir()
            (work / "slides" / "01-A.html").write_text(FRAG.format(n="01"), encoding="utf-8")
            md = "## S01\n- 選択: A\n- 判定: 承認\n- コメント: \n- 部位: 注釈 ／ コメント: 出典を足す\n"
            with self.assertRaises(ValueError) as cm:
                variants.finalize(work, md)
            self.assertIn("注釈", str(cm.exception))

    def test_comment_text_and_preset(self):
        a = variants.parse_answers(self.MD)["01"]
        self.assertEqual(variants.comment_text(a), "全体 【スティッカー②】文言を短く")
        md_ok = "## S01\n- 選択: A\n- 判定: 承認\n- コメント: \n- 部位: 注釈 ／ コメント: 直す\n"
        self.assertEqual(variants.approved_preset([md_ok]), {})


class FreeDesignTest(unittest.TestCase):
    def work(self, td, files):
        work = Path(td)
        (work / "slides").mkdir()
        for name, text in files.items():
            (work / "slides" / name).write_text(text, encoding="utf-8")
        return work

    def test_r_is_collected_and_finalized(self):
        with tempfile.TemporaryDirectory() as td:
            work = self.work(td, {"01-A.html": FRAG.format(n="a"), "01-B.html": FRAG.format(n="b"), "01-R.html": FRAG.format(n="r")})
            self.assertEqual(sorted(variants.collect(work)["01"]), ["A", "B", "R"])
            page = variants._page(work, variants.collect(work), "1", designs=variants.collect_designs(work))
            self.assertIn("案 R（自由設計）", page)
            self.assertNotIn('class="dgroup" data-k="R"', page)           # R にはデザイン 1〜3 の選択がない
            out = variants.finalize(work, "## S01\n- 選択: R\n- 判定: 承認\n- コメント: \n")
            self.assertIn("題r", out.read_text(encoding="utf-8"))

    def test_r_rejects_design_variants_and_pictures(self):
        with tempfile.TemporaryDirectory() as td:
            work = self.work(td, {"01-A.html": FRAG.format(n="a"), "01-R.html": FRAG.format(n="r"), "01-R-d2.html": FRAG.format(n="r2")})
            with self.assertRaises(ValueError) as cm:
                variants.collect_designs(work)
            self.assertIn("デザイン 2・3", str(cm.exception))
        with tempfile.TemporaryDirectory() as td:
            work = self.work(td, {"01-A.html": FRAG.format(n="a"), "01-R.html": FRAG.format(n="r") + '<div class="pp-picture"></div>'})
            with self.assertRaises(ValueError) as cm:
                variants.collect_designs(work)
            self.assertIn("pp-picture", str(cm.exception))
