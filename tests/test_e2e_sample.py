"""init → variants → finalize → build → reopen を、LibreOffice を呼ばずに通す。部品の見本（assets/components）を案に使う。"""
import contextlib
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests import _paths  # noqa: F401
from tests._paths import PKG
from pptx_deck import cli, lifecycle, paths

COMP = PKG / "assets" / "components"


def run(*argv):
    buf, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
        rc = cli.main(list(argv))
    return rc, buf.getvalue(), err.getvalue()


class E2ETest(unittest.TestCase):
    def test_full_flow_without_libreoffice(self):
        calls = []
        real_run, real_popen = subprocess.run, subprocess.Popen

        def spy_run(cmd, *a, **k):
            calls.append(str(cmd[0] if isinstance(cmd, (list, tuple)) else cmd))
            return real_run(cmd, *a, **k)

        def spy_popen(cmd, *a, **k):
            calls.append(str(cmd[0] if isinstance(cmd, (list, tuple)) else cmd))
            return real_popen(cmd, *a, **k)

        with tempfile.TemporaryDirectory() as td, \
                mock.patch("subprocess.run", spy_run), mock.patch("subprocess.Popen", spy_popen):
            base = Path(td) / "demo"
            self.assertEqual(run("init", str(base), "--color", "navy")[0], 0)
            work = paths.resolve_work(base)
            slides = work / "slides"
            shutil.copyfile(COMP / "layouts" / "cover.html", slides / "01-A.html")
            shutil.copyfile(COMP / "diagrams" / "flow-h.html", slides / "02-A.html")
            shutil.copyfile(COMP / "diagrams" / "flow-v.html", slides / "02-B.html")
            shutil.copyfile(COMP / "charts" / "bar.html", slides / "03-A.html")

            self.assertEqual(run("variants", str(base))[0], 0)
            self.assertTrue((work / "variants.html").exists())
            (work / "answers-1.md").write_text(
                "---\ndeck: demo\nround: 1\n---\n"
                "## S01\n- 選択: A\n- 判定: 承認\n- コメント: \n"
                "## S02\n- 選択: B\n- 判定: 承認\n- コメント: \n"
                "## S03\n- 選択: A\n- 判定: 承認\n- コメント: \n", encoding="utf-8")
            # --answers を省略 → answers-*.md を自動で使う
            self.assertEqual(run("finalize", str(base))[0], 0)
            rc, out, _ = run("build", str(base))
            self.assertEqual(rc, 0, out)
            result = json.loads(out)
            pptx = base / "demo.pptx"
            self.assertTrue(pptx.exists())
            self.assertIn("final.html", result["removed"])
            self.assertEqual(sorted(p.name for p in base.iterdir()), ["demo.pptx", "source"])
            self.assertFalse((work / "theme.css").exists())
            self.assertTrue((work / "build.json").exists())
            self.assertTrue(result["previews"])

            rc, out, _ = run("reopen", str(base))
            self.assertEqual((rc, json.loads(out)["status"]), (0, "ok"))
            self.assertTrue((work / "theme.css").exists())
            # 2 回目: 前回承認が選択済みで開く
            self.assertEqual(run("variants", str(base))[0], 0)
            html = (work / "variants.html").read_text(encoding="utf-8")
            self.assertIn('"01": {"c": "A"', html)

            lifecycle.prune(work)
            # PowerPoint で手直しした想定
            pptx.write_bytes(pptx.read_bytes() + b"x")
            self.assertEqual(run("reopen", str(base))[0], 4)
            self.assertEqual(run("reopen", str(base), "--force")[0], 0)
            self.assertEqual(run("finalize", str(base))[0], 0)
            # 手直し済みの PPTX を黙って上書きしない
            rc, _, err = run("build", str(base))
            self.assertEqual(rc, 4, err)
            self.assertEqual(run("build", str(base), "--force")[0], 0)
            self.assertEqual(run("clean", str(base))[0], 0)

        self.assertFalse(
            [c for c in calls if "soffice" in c.lower() or "libreoffice" in c.lower()], calls)

    def test_final_answers_do_not_change_choice_then_build(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "demo"
            self.assertEqual(run("init", str(base), "--color", "navy")[0], 0)
            work = paths.resolve_work(base)
            shutil.copyfile(COMP / "layouts" / "cover.html", work / "slides" / "01-A.html")
            shutil.copyfile(COMP / "diagrams" / "flow-h.html", work / "slides" / "02-A.html")
            shutil.copyfile(COMP / "diagrams" / "flow-v.html", work / "slides" / "02-B.html")
            (work / "answers-1.md").write_text(
                "---\n---\n## S01\n- 選択: A\n- 判定: 承認\n- コメント: \n"
                "## S02\n- 選択: B\n- 判定: 承認\n- コメント: \n", encoding="utf-8")
            (work / "answers-final.md").write_text(
                "---\n---\n## S01\n- 選択: A\n- 判定: 承認\n- コメント: \n"
                "## S02\n- 選択: A\n- 判定: 承認\n- コメント: \n", encoding="utf-8")
            self.assertEqual(run("finalize", str(base))[0], 0)
            body = (work / "final.html").read_text(encoding="utf-8")
            self.assertIn((COMP / "diagrams" / "flow-v.html").read_text(encoding="utf-8"), body)
            self.assertEqual(run("build", str(base))[0], 0)
            # revise (a): 2 回目の回答で S02 を A に変える。古い answers-final.md（A）とは無関係に answers-2.md が効く
            self.assertEqual(run("reopen", str(base))[0], 0)
            (work / "answers-2.md").write_text(
                "---\n---\n## S02\n- 選択: A\n- 判定: 承認\n- コメント: \n", encoding="utf-8")
            (work / "answers-final.md").write_text(
                "---\n---\n## S02\n- 選択: B\n- 判定: 承認\n- コメント: \n", encoding="utf-8")
            self.assertEqual(run("finalize", str(base))[0], 0)
            body = (work / "final.html").read_text(encoding="utf-8")
            self.assertIn((COMP / "diagrams" / "flow-h.html").read_text(encoding="utf-8"), body)
            self.assertNotIn((COMP / "diagrams" / "flow-v.html").read_text(encoding="utf-8"), body)


if __name__ == "__main__":
    unittest.main()
