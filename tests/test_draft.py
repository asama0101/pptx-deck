"""下書きの確認（draft）: 回答を待たずに断片を束ね、確認用の画像と検査の結果を返す。PPTX は出さない。"""
import contextlib
import io
import json
import re
import tempfile
import unittest
from pathlib import Path

from tests import _paths  # noqa: F401
from tests._paths import PKG
from pptx_deck import cli, lifecycle, paths

PICTURES = PKG / "assets" / "components" / "pictures"


def run(*argv):
    buf, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
        rc = cli.main(list(argv))
    return rc, buf.getvalue(), err.getvalue()


class DraftTest(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        self.base = Path(self._td.name) / "demo"
        self.assertEqual(run("init", str(self.base), "--color", "navy")[0], 0)
        self.work = paths.resolve_work(self.base)
        for nn, n in (("01", "failure"), ("02", "network")):
            (self.work / "slides" / f"{nn}-A.html").write_text((PICTURES / f"{n}.html").read_text(encoding="utf-8"), encoding="utf-8")
        (self.work / "slides" / "02-B.html").write_text(
            (PICTURES / "self-intro.html").read_text(encoding="utf-8"), encoding="utf-8")

    def test_returns_previews_and_violations_without_building(self):
        rc, out, err = run("draft", str(self.base))
        self.assertEqual(rc, 0, out + err)
        r = json.loads(out)
        self.assertEqual((r["ok"], r["slides"], r["violations"]), (True, ["01", "02"], []))
        self.assertEqual(len(r["previews"]), 2)
        for p in r["previews"]:
            self.assertTrue(Path(p).exists())
        self.assertFalse((self.work / "final.html").exists())
        self.assertFalse(list(self.base.glob("*.pptx")))
        self.assertTrue((self.work / "draft.html").exists())
        self.assertIn("draft.html", lifecycle.prune(self.work))                   # 派生ファイルとして、build が片づける

    def test_slide_and_pick_options(self):
        rc, out, _ = run("draft", str(self.base), "--slide", "02", "--pick", "B")
        r = json.loads(out)
        self.assertEqual((rc, r["slides"], len(r["previews"])), (0, ["02"], 1))
        self.assertIn("自己紹介", (self.work / "draft.html").read_text(encoding="utf-8"))   # 02-B（自己紹介）が入る
        self.assertEqual(run("draft", str(self.base), "--slide", "09")[0], 2)

    def test_violation_is_reported_with_exit_code_1(self):
        f = self.work / "slides" / "01-A.html"
        f.write_text(re.sub(r' data-alt="[^"]*"', "", f.read_text(encoding="utf-8")), encoding="utf-8")
        rc, out, _ = run("draft", str(self.base))
        r = json.loads(out)
        self.assertEqual((rc, r["ok"]), (1, False))
        self.assertIn("imageAlt", {v["rule"] for v in r["violations"]})
        self.assertEqual(len(r["previews"]), 2)                                  # 画像は出す（直す手がかり）


if __name__ == "__main__":
    unittest.main()
