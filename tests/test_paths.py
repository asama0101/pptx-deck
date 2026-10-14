import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests import _paths
from pptx_deck import cli, paths


class PkgLocationTest(unittest.TestCase):
    def test_pkg_has_entry_and_package(self):
        self.assertTrue((_paths.PKG / "run.py").is_file())
        self.assertTrue((_paths.PKG / "pptx_deck" / "cli.py").is_file())


class TempDirNameTest(unittest.TestCase):
    def test_empty_name_is_rejected(self):
        for bad in ("", "  ", ".", ".."):
            with self.assertRaises(ValueError, msg=repr(bad)):
                paths.temp_dir(bad)

    def test_clean_and_build_exit_2_on_empty_name(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "demo"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(["init", str(base), "--color", "navy"]), 0)
            for cmd in ("clean", "build"):
                err = io.StringIO()
                with mock.patch.object(paths, "deck_name", return_value=""),                         contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
                    rc = cli.main([cmd, str(base)])
                self.assertEqual(rc, 2, cmd)
                self.assertIn("エラー", err.getvalue())


if __name__ == "__main__":
    unittest.main()
