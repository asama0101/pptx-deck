"""絵の提案と構造の確認: 計画の検証・ページ・回答の解析と凍結の判定。"""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from tests import _paths
from pptx_deck import cli, paths, picture_plan as pp

PLAN = {
    "title": "絵の提案", "intro": "確認してください",
    "proposals": [
        {"id": "P1", "title": "S05 通信経路", "reason": "経路の順番を見せるため", "summary": "利用者から DB まで 5 経路",
         "items": [{"id": "P1-1", "kind": "要素", "text": "FW"}, {"id": "P1-2", "kind": "順序", "text": "FW → LB"},
                   {"id": "P1-3", "kind": "強調", "text": "Web から DB への直接接続"}]},
        {"id": "P2", "title": "S06 自己紹介", "asked": True, "summary": "経歴 3 点",
         "items": [{"id": "P2-1", "kind": "要素", "text": "経歴"}]},
        {"id": "P3", "title": "S07 体制", "reason": "階層を見せるため", "summary": "3 層", "items": [{"id": "P3-1", "kind": "要素", "text": "PM"}]},
    ],
}


def run(*argv):
    buf, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
        rc = cli.main(list(argv))
    return rc, buf.getvalue(), err.getvalue()


class AnswersTest(unittest.TestCase):
    MD1 = ("---\npicture-plan: demo\nround: 1\n---\n"
           "## P1\n- 提案: する\n- 項目 P1-1: OK\n- 項目 P1-2: 修正｜LB は FW の後\n- 項目 P1-3: OK\n- コメント: \n"
           "## P2\n- 提案: 依頼済み\n- 項目 P2-1: OK\n- コメント: \n"
           "## P3\n- 提案: しない\n- コメント: 文章のままでよい\n")

    def test_parse(self):
        a = pp.parse_answers(self.MD1)
        self.assertEqual(a["P1"]["proposal"], "する")
        self.assertEqual(a["P1"]["items"]["P1-2"], ("修正", "LB は FW の後"))
        self.assertEqual(a["P1"]["items"]["P1-1"], ("OK", ""))
        self.assertEqual(a["P3"]["comment"], "文章のままでよい")

    def test_resolve_lists_fixes_and_is_not_frozen(self):
        r = pp.resolve(PLAN, pp.merge_answers([self.MD1]))
        self.assertEqual((r["draw"], r["skip"]), (["P1", "P2"], ["P3"]))
        self.assertEqual(r["fixes"], [{"id": "P1-2", "text": "FW → LB", "comment": "LB は FW の後"}])
        self.assertFalse(r["frozen"])

    def test_later_round_overrides_and_freezes(self):
        md2 = "---\nround: 2\n---\n## P1\n- 項目 P1-2: OK\n"
        r = pp.resolve(PLAN, pp.merge_answers([self.MD1, md2]))
        self.assertEqual(r["fixes"], [])
        self.assertTrue(r["frozen"], r)

    def test_unanswered_is_pending(self):
        r = pp.resolve(PLAN, {})
        self.assertIn("P1 提案", r["pending"])
        self.assertIn("P3 提案", r["pending"])
        self.assertNotIn("P2 提案", r["pending"])                 # 依頼済みは、提案の回答が要らない
        self.assertFalse(r["frozen"])


class PlanFileTest(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        self.base = Path(self._td.name) / "demo"
        self.assertEqual(run("init", str(self.base), "--color", "navy")[0], 0)
        self.work = paths.resolve_work(self.base)

    def write(self, plan):
        (self.work / "picture-plan.json").write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")

    def test_missing_or_invalid_plan_is_an_error(self):
        self.assertEqual(run("review-picture", str(self.base))[0], 2)
        bad = json.loads(json.dumps(PLAN))
        bad["proposals"][0]["items"][0]["id"] = "X-1"
        self.write(bad)
        rc, _, err = run("review-picture", str(self.base))
        self.assertEqual(rc, 2)
        self.assertIn("P1-1", err)
        self.write({"proposals": []})
        self.assertEqual(run("review-picture", str(self.base))[0], 2)

    def test_page_escapes_html_and_hides_the_proposal_for_asked(self):
        plan = json.loads(json.dumps(PLAN))
        plan["proposals"][0]["items"][0]["text"] = "<script>alert(1)</script>"
        self.write(plan)
        self.assertEqual(run("review-picture", str(self.base))[0], 0)
        html = (self.work / "picture-review.html").read_text(encoding="utf-8")
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;alert(1)", html)
        self.assertEqual(html.count('name="prop-P1"'), 2)
        self.assertNotIn('name="prop-P2"', html)                  # 依頼済みは、提案の欄を省く

    def test_status_command_exit_code(self):
        self.write(PLAN)
        (self.work / "answers-picture-1.md").write_text(AnswersTest.MD1, encoding="utf-8")
        rc, out, _ = run("picture-status", str(self.base))
        self.assertEqual(rc, 1)
        self.assertEqual(json.loads(out)["fixes"][0]["id"], "P1-2")
        (self.work / "answers-picture-2.md").write_text("---\n---\n## P1\n- 項目 P1-2: OK\n", encoding="utf-8")
        self.assertEqual(run("picture-status", str(self.base))[0], 0)
        self.assertEqual(pp.next_round(self.work), 3)

    def test_page_click_through_returns_answers_md(self):
        from playwright.sync_api import sync_playwright
        self.write(PLAN)
        self.assertEqual(run("review-picture", str(self.base))[0], 0)
        url = (self.work / "picture-review.html").resolve().as_uri()
        with sync_playwright() as p:
            b = p.chromium.launch()
            try:
                page = b.new_page()
                page.goto(url)
                # 未選択のまま押すと、送信されず、足りない所が出る
                page.click("#copy")
                self.assertFalse(page.evaluate("!!window.__submitted"))
                self.assertIn("P1", page.inner_text("#state"))
                page.click('input[name="prop-P1"][value="する"]')
                page.click('input[name="prop-P3"][value="しない"]')
                for i in ("P1-1", "P1-3", "P2-1"):
                    page.click(f'li[data-i="{i}"] button[data-v="OK"]')
                page.click('li[data-i="P1-2"] button[data-v="修正"]')
                page.fill('li[data-i="P1-2"] .cm', "LB は FW の後")
                page.click("#copy")
                self.assertTrue(page.evaluate("!!window.__submitted"))
                md = page.evaluate("window.__answersMd")
            finally:
                b.close()
        a = pp.parse_answers(md)
        self.assertEqual(a["P1"]["items"]["P1-2"], ("修正", "LB は FW の後"))
        self.assertEqual(a["P2"]["proposal"], "依頼済み")
        self.assertEqual(a["P3"]["proposal"], "しない")
        self.assertNotIn("P3-1", a["P3"]["items"])                 # 「しない」の提案は、項目を聞かない
        r = pp.resolve(PLAN, pp.merge_answers([md]))
        self.assertEqual([f["id"] for f in r["fixes"]], ["P1-2"])


class SampleFlowTest(unittest.TestCase):
    """見本の素材（assets/sample/picture/）から、提案・構造の確認 → 凍結 → 描く → PPTX まで通す。"""
    SAMPLE = _paths.PKG / "assets" / "sample" / "picture"
    PICTURES = _paths.PKG / "assets" / "components" / "pictures"

    def test_sample_inputs_exist(self):
        for n in ("incident-report.md", "self-intro-hearing.md", "network-memo.md", "picture-plan.example.json"):
            self.assertTrue((self.SAMPLE / n).is_file(), n)

    def test_from_the_sample_plan_to_a_pptx(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "demo"
            self.assertEqual(run("init", str(base), "--color", "navy")[0], 0)
            work = paths.resolve_work(base)
            (work / "picture-plan.json").write_text((self.SAMPLE / "picture-plan.example.json").read_text(encoding="utf-8"), encoding="utf-8")
            self.assertEqual(run("review-picture", str(base))[0], 0)
            # 1 回目: P1 は「する」で、1 項目だけ修正。P2 は「しない」
            md1 = ("---\npicture-plan: demo\nround: 1\n---\n"
                   "## P1\n- 提案: する\n- 項目 P1-1: OK\n- 項目 P1-2: 修正｜4 番目は「応答なしのエラー」と書く\n- 項目 P1-3: OK\n- 項目 P1-4: OK\n- コメント: \n"
                   "## P2\n- 提案: しない\n- コメント: \n")
            (work / "answers-picture-1.md").write_text(md1, encoding="utf-8")
            rc, out, _ = run("picture-status", str(base))
            self.assertEqual(rc, 1)
            self.assertEqual([f["id"] for f in json.loads(out)["fixes"]], ["P1-2"])
            # 2 回目: 直して OK。P2 を「する」に変える（後の回答が前を上書きする）
            md2 = ("---\npicture-plan: demo\nround: 2\n---\n## P1\n- 提案: する\n- 項目 P1-2: OK\n- コメント: \n"
                   "## P2\n- 提案: する\n" + "".join(f"- 項目 P2-{i}: OK\n" for i in (1, 2, 3, 4)) + "- コメント: \n")
            (work / "answers-picture-2.md").write_text(md2, encoding="utf-8")
            rc, out, _ = run("picture-status", str(base))
            r = json.loads(out)
            self.assertEqual((rc, r["draw"], r["frozen"]), (0, ["P1", "P2"], True), out)
            # 凍結した構造を描く（見本をそのまま使う）→ 下書きの確認 → 最終 → PPTX
            for nn, n in (("01", "failure"), ("02", "traffic-flow")):
                (work / "slides" / f"{nn}-A.html").write_text((self.PICTURES / f"{n}.html").read_text(encoding="utf-8"), encoding="utf-8")
            self.assertEqual(run("draft", str(base))[0], 0)
            (work / "answers-1.md").write_text("---\n---\n## S01\n- 選択: A\n## S02\n- 選択: A\n", encoding="utf-8")
            self.assertEqual(run("finalize", str(base))[0], 0)
            rc, out, err = run("build", str(base))
            self.assertEqual(rc, 0, out + err)
            self.assertEqual(json.loads(out)["violations"], [])
            self.assertTrue((base / "demo.pptx").exists())


if __name__ == "__main__":
    unittest.main()
