"""answers-final.md（最終確認の回答）は、finalize / review-final の案の決定に使わない。"""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from tests import _paths  # noqa: F401
from pptx_deck import cli, paths, variants

FINAL_OK = "---\n---\n## S01\n- 選択: A\n- 判定: 承認\n- コメント: \n## S02\n- 選択: A\n- 判定: 承認\n- コメント: \n"
FINAL_FIX = "---\n---\n## S01\n- 選択: A\n- 判定: 承認\n- コメント: \n## S02\n- 選択: FIX\n- 判定: 要修正\n- コメント: 直す\n"
ANS1 = ("---\n---\n## S01\n- 選択: B\n- デザイン: 2\n- 判定: 承認\n- コメント: \n"
        "## S02\n- 選択: A\n- 判定: 承認\n- コメント: \n")


def run(*argv):
    buf, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
        rc = cli.main(list(argv))
    return rc, buf.getvalue(), err.getvalue()


def make(td):
    base = Path(td) / "demo"
    assert run("init", str(base), "--color", "navy")[0] == 0
    work = paths.resolve_work(base)
    s = work / "slides"
    (s / "01-A.html").write_text("<section>MARK-1A</section>", encoding="utf-8")
    (s / "01-B.html").write_text("<section>MARK-1B</section>", encoding="utf-8")
    (s / "01-B-d2.html").write_text("<section>MARK-1B2</section>", encoding="utf-8")
    (s / "02-A.html").write_text("<section>MARK-2A</section>", encoding="utf-8")
    (work / "answers-1.md").write_text(ANS1, encoding="utf-8")
    return base, work


class FinalAnswersTest(unittest.TestCase):
    def test_final_approval_does_not_override_choice(self):
        with tempfile.TemporaryDirectory() as td:
            base, work = make(td)
            (work / "answers-final.md").write_text(FINAL_OK, encoding="utf-8")
            self.assertEqual(run("finalize", str(base))[0], 0)
            html = (work / "final.html").read_text(encoding="utf-8")
            self.assertIn("MARK-1B2", html)
            self.assertNotIn("MARK-1A", html)

    def test_final_fix_does_not_block_finalize(self):
        with tempfile.TemporaryDirectory() as td:
            base, work = make(td)
            (work / "answers-final.md").write_text(FINAL_FIX, encoding="utf-8")
            rc, _, err = run("finalize", str(base))
            self.assertEqual(rc, 0, err)
            rc, _, err = run("review-final", str(base))
            self.assertEqual(rc, 0, err)

    def test_answer_paths_include_final_flag(self):
        with tempfile.TemporaryDirectory() as td:
            base, work = make(td)
            (work / "answers-final.md").write_text(FINAL_OK, encoding="utf-8")
            self.assertEqual([p.name for p in variants.answer_paths(work)], ["answers-1.md", "answers-final.md"])
            self.assertEqual([p.name for p in variants.answer_paths(work, include_final=False)], ["answers-1.md"])

    def test_preset_uses_previous_final_approval_only_for_preselection(self):
        with tempfile.TemporaryDirectory() as td:
            base, work = make(td)
            (work / "answers-final.md").write_text(FINAL_FIX, encoding="utf-8")
            self.assertEqual(run("finalize", str(base))[0], 0)
            page = (work / "final-review.html").read_text(encoding="utf-8")
            self.assertIn('"01": {"c": "A"', page)        # 前回の最終確認で承認した S01 は選択済み
            self.assertNotIn('"02": {"c"', page)           # 要修正の S02 は選択済みにしない

    def test_revise_later_round_wins_over_stale_final(self):
        with tempfile.TemporaryDirectory() as td:
            base, work = make(td)
            (work / "answers-final.md").write_text(FINAL_OK, encoding="utf-8")
            (work / "answers-2.md").write_text(
                "---\n---\n## S01\n- 選択: B\n- デザイン: 1\n- 判定: 承認\n- コメント: \n", encoding="utf-8")
            self.assertEqual(run("finalize", str(base))[0], 0)
            html = (work / "final.html").read_text(encoding="utf-8")
            self.assertIn("MARK-1B</section>", html)
            self.assertNotIn("MARK-1B2", html)
            self.assertNotIn("MARK-1A", html)


if __name__ == "__main__":
    unittest.main()
