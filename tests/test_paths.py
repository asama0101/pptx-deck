import unittest

from tests import _paths


class PkgLocationTest(unittest.TestCase):
    def test_pkg_has_entry_and_package(self):
        self.assertTrue((_paths.PKG / "run.py").is_file())
        self.assertTrue((_paths.PKG / "pptx_deck" / "cli.py").is_file())


if __name__ == "__main__":
    unittest.main()
