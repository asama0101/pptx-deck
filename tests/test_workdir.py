import tempfile
import unittest
from pathlib import Path

from tests import _paths  # noqa: F401
from pptx_deck import initdir, paths


class ResolveTest(unittest.TestCase):
    def test_new_layout(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "deck"
            self.assertEqual(paths.resolve_work(base), (base / "source").resolve())
            (base / "source").mkdir(parents=True)
            self.assertEqual(paths.resolve_work(base), (base / "source").resolve())
            self.assertEqual(paths.deck_dir(base / "source"), base)
            self.assertEqual(paths.deck_name(base / "source"), "deck")
            self.assertFalse(paths.is_legacy(base / "source"))

    def test_legacy_layout(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "old"
            base.mkdir()
            (base / "template.json").write_text("{}", encoding="utf-8")
            w = paths.resolve_work(base)
            self.assertEqual(w, base.resolve())
            self.assertTrue(paths.is_legacy(w))
            self.assertEqual(paths.deck_name(w), "old")


class InitLayoutTest(unittest.TestCase):
    def test_init_creates_source(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "deck"
            r = initdir.init(base, color="navy")
            self.assertTrue((base / "source" / "template.json").is_file())
            self.assertFalse((base / "template.json").exists())
            self.assertTrue(r["workdir"].endswith("source"))


if __name__ == "__main__":
    unittest.main()
