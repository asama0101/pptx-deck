"""絵の往復の履歴: 直す前の版を残し、戻せる。build は履歴を消さない。"""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from tests import _paths  # noqa: F401
from tests._paths import PKG
from pptx_deck import cli, history, paths

SAMPLE = PKG / "assets" / "components" / "pictures" / "traffic-flow.html"


def run(*argv):
    buf, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
        rc = cli.main(list(argv))
    return rc, buf.getvalue(), err.getvalue()


class HistoryTest(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        self.base = Path(self._td.name) / "demo"
        self.assertEqual(run("init", str(self.base), "--color", "navy")[0], 0)
        self.work = paths.resolve_work(self.base)
        self.s = self.work / "slides"
        (self.s / "01-A.html").write_text("v1-01A", encoding="utf-8")
        (self.s / "02-A.html").write_text("v1-02A", encoding="utf-8")

    def test_snapshot_numbers_versions_and_copies_slides(self):
        a = history.snapshot(self.work, "構図を変える前")
        b = history.snapshot(self.work)
        self.assertEqual((a["version"], b["version"]), (1, 2))
        self.assertTrue((self.work / "history" / "001-構図を変える前" / "01-A.html").exists())
        self.assertEqual([v["version"] for v in history.versions(self.work)], [1, 2])

    def test_restore_brings_back_files_and_keeps_the_current_state_as_a_version(self):
        history.snapshot(self.work)                                            # 版 1: v1
        (self.s / "01-A.html").write_text("v2-01A", encoding="utf-8")
        (self.s / "03-A.html").write_text("v2-03A", encoding="utf-8")          # 版 1 には無いファイル
        r = history.restore(self.work, 1)
        self.assertEqual((self.s / "01-A.html").read_text(encoding="utf-8"), "v1-01A")
        self.assertFalse((self.s / "03-A.html").exists())
        self.assertEqual(r["saved_as"], 2)                                     # 戻す前の状態は版 2 に残る
        self.assertEqual((self.work / "history" / "002-before-restore-1" / "03-A.html").read_text(encoding="utf-8"), "v2-03A")
        history.restore(self.work, 2)                                          # 取り消せる
        self.assertEqual((self.s / "03-A.html").read_text(encoding="utf-8"), "v2-03A")

    def test_restore_one_slide_only(self):
        history.snapshot(self.work)
        (self.s / "01-A.html").write_text("v2-01A", encoding="utf-8")
        (self.s / "02-A.html").write_text("v2-02A", encoding="utf-8")
        history.restore(self.work, 1, slide="02")
        self.assertEqual((self.s / "01-A.html").read_text(encoding="utf-8"), "v2-01A")
        self.assertEqual((self.s / "02-A.html").read_text(encoding="utf-8"), "v1-02A")

    def test_unknown_version_and_empty_slides_are_errors(self):
        with self.assertRaises(ValueError):
            history.restore(self.work, 9)
        for f in self.s.glob("*.html"):
            f.unlink()
        with self.assertRaises(ValueError):
            history.snapshot(self.work)

    def test_cli(self):
        rc, out, _ = run("history", str(self.base), "snapshot", "--label", "初回")
        self.assertEqual((rc, json.loads(out)["version"]), (0, 1))
        rc, out, _ = run("history", str(self.base), "list")
        self.assertEqual(json.loads(out)[0]["label"], "初回")
        self.assertEqual(run("history", str(self.base), "restore")[0], 2)      # 版の指定が無い
        self.assertEqual(run("history", str(self.base), "restore", "1")[0], 0)

    def test_build_does_not_remove_history(self):
        for f in self.s.glob("*.html"):
            f.unlink()
        (self.s / "01-A.html").write_text(SAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
        history.snapshot(self.work, "before")
        (self.work / "answers-1.md").write_text("---\n---\n## S01\n- 選択: A\n- 判定: 承認\n- コメント: \n", encoding="utf-8")
        self.assertEqual(run("finalize", str(self.base))[0], 0)
        rc, out, err = run("build", str(self.base))
        self.assertEqual(rc, 0, out + err)
        self.assertTrue((self.work / "history" / "001-before" / "01-A.html").exists())


if __name__ == "__main__":
    unittest.main()
