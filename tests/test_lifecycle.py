import json
import tempfile
import unittest
from pathlib import Path

from tests import _paths  # noqa: F401
from pptx_deck import lifecycle


class FingerprintTest(unittest.TestCase):
    def test_status_transitions(self):
        with tempfile.TemporaryDirectory() as td:
            work = Path(td) / "source"
            work.mkdir()
            pptx = Path(td) / "deck.pptx"
            self.assertEqual(lifecycle.fingerprint_status(work, pptx), "missing")
            pptx.write_bytes(b"v1")
            self.assertEqual(lifecycle.fingerprint_status(work, pptx), "unrecorded")
            lifecycle.record_build(work, pptx)
            self.assertEqual(lifecycle.fingerprint_status(work, pptx), "unchanged")
            pptx.write_bytes(b"v1-edited")
            self.assertEqual(lifecycle.fingerprint_status(work, pptx), "modified")
            self.assertEqual(json.loads((work / "build.json").read_text(encoding="utf-8"))["pptx"], "deck.pptx")


class PruneTest(unittest.TestCase):
    def test_removes_only_known_derived(self):
        with tempfile.TemporaryDirectory() as td:
            w = Path(td)
            for n in lifecycle.DERIVED_FILES:
                (w / n).write_text("x", encoding="utf-8")
            (w / "icons").mkdir()
            (w / "icons" / "a.svg").write_text("x", encoding="utf-8")
            (w / "_template").mkdir()
            (w / "_template" / "template.potx").write_bytes(b"t")
            (w / "_template" / "bg-body.png").write_bytes(b"p")
            for keep in ("design.md", "script.md", "template.json", "build.json", "answers-1.md", "round-2-notes.md", "素材メモ.md"):
                (w / keep).write_text("k", encoding="utf-8")
            (w / "slides").mkdir()
            (w / "slides" / "01-A.html").write_text("s", encoding="utf-8")
            removed = lifecycle.prune(w)
            self.assertIn("final.html", removed)
            self.assertIn("icons", removed)
            self.assertIn("_template/bg-body.png", removed)
            left = sorted(p.name for p in w.iterdir())
            self.assertEqual(left, sorted(["_template", "answers-1.md", "build.json", "design.md", "round-2-notes.md", "script.md", "slides", "template.json", "素材メモ.md"]))
            self.assertEqual([p.name for p in (w / "_template").iterdir()], ["template.potx"])

    def test_prune_empty_dir_is_safe(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(lifecycle.prune(Path(td)), [])


if __name__ == "__main__":
    unittest.main()
