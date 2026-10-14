import argparse
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests import _paths  # noqa: F401
from pptx_deck import cli, initdir, lifecycle, paths


def fresh(td) -> Path:
    base = Path(td) / "deck"
    initdir.init(base, color="navy")
    work = paths.resolve_work(base)
    (work / "slides" / "01-A.html").write_text("<section class='slide'></section>", encoding="utf-8")
    (work / "answers-1.md").write_text("---\n---\n", encoding="utf-8")
    (work / "answers-final.md").write_text("---\n---\n", encoding="utf-8")
    lifecycle.prune(work)               # build 後の状態にする
    return work


class ReopenTest(unittest.TestCase):
    def test_regenerates_derived_files(self):
        with tempfile.TemporaryDirectory() as td:
            work = fresh(td)
            self.assertFalse((work / "theme.css").exists())
            pptx = paths.deck_dir(work) / "deck.pptx"
            pptx.write_bytes(b"v1")
            lifecycle.record_build(work, pptx)
            r = lifecycle.reopen(work)
            self.assertEqual(r["status"], "ok")
            self.assertTrue((work / "theme.css").exists() and (work / "base.css").exists() and (work / "icons").is_dir())
            self.assertEqual([Path(a).name for a in r["answers"]], ["answers-1.md", "answers-final.md"])
            self.assertEqual(r["next_round"], 2)
            self.assertEqual(r["slides"], 1)

    def test_modified_pptx_is_reported(self):
        with tempfile.TemporaryDirectory() as td:
            work = fresh(td)
            pptx = paths.deck_dir(work) / "deck.pptx"
            pptx.write_bytes(b"v1")
            lifecycle.record_build(work, pptx)
            pptx.write_bytes("v1 + 手直し".encode("utf-8"))
            self.assertEqual(lifecycle.reopen(work)["status"], "modified")

    def test_missing_pptx(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(lifecycle.reopen(fresh(td))["status"], "missing_pptx")


class EnsureDerivedTest(unittest.TestCase):
    def test_regenerates_after_prune_then_noop(self):
        with tempfile.TemporaryDirectory() as td:
            work = fresh(td)
            self.assertTrue(lifecycle.ensure_derived(work))
            self.assertTrue((work / "theme.css").exists() and (work / "base.css").exists() and (work / "icons").is_dir())
            self.assertFalse(lifecycle.ensure_derived(work))


class BuildRecordsFingerprintTest(unittest.TestCase):
    def test_build_json_written_even_when_check_pptx_flags_error(self):
        with tempfile.TemporaryDirectory() as td:
            work = fresh(td)
            (work / "final.html").write_text("<html></html>", encoding="utf-8")
            out = paths.deck_dir(work) / f"{paths.deck_name(work)}.pptx"

            def fake_build(*a, **k):
                out.write_bytes(b"pptx")

            err = [{"severity": "error", "message": "x"}]
            args = argparse.Namespace(workdir=str(work), out=None, force=False, footer=None)
            with mock.patch("pptx_deck.measure.measure", return_value=object()), \
                    mock.patch("pptx_deck.check.check_model", return_value=[]), \
                    mock.patch("pptx_deck.build.build", side_effect=fake_build), \
                    mock.patch("pptx_deck.check.check_pptx", return_value=err), \
                    mock.patch("pptx_deck.preview.screenshots", return_value=[]), \
                    mock.patch("builtins.print"):
                rc = cli.cmd_build(args)
            self.assertEqual(rc, 1)
            self.assertTrue((work / "build.json").exists())
            self.assertEqual(lifecycle.fingerprint_status(work, out), "unchanged")
            self.assertTrue((work / "slides").is_dir())            # ok でないので prune されない
            self.assertTrue((work / "final.html").exists())


if __name__ == "__main__":
    unittest.main()
