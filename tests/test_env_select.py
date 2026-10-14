import contextlib
import io
import json
import os
import unittest
from pathlib import Path
from unittest import mock

from tests import _paths  # noqa: F401
from pptx_deck import cli, env

GOOD = {"python": [3, 14], "versions": {"python-pptx": "1.0.2", "playwright": "1.52.0", "pymupdf": "1.28.2", "lxml": "5.3.0"}, "chromium": True}


def bad(**over):
    d = {"python": [3, 14], "versions": dict(GOOD["versions"]), "chromium": True}
    d.update(over)
    return d


class MissingTest(unittest.TestCase):
    def test_all_good(self):
        self.assertEqual(env.missing(GOOD), [])

    def test_version_mismatch_is_missing(self):
        info = bad(versions={**GOOD["versions"], "playwright": "1.40.0"})
        self.assertTrue(any("playwright" in m for m in env.missing(info)))

    def test_not_installed_and_no_chromium(self):
        info = bad(versions={**GOOD["versions"], "pymupdf": None}, chromium=False)
        m = env.missing(info)
        self.assertTrue(any("pymupdf" in x for x in m))
        self.assertTrue(any("chromium" in x for x in m))

    def test_old_python(self):
        self.assertTrue(any("Python" in m for m in env.missing(bad(python=[3, 9]))))

    def test_lxml_major_only(self):
        self.assertEqual(env.missing(bad(versions={**GOOD["versions"], "lxml": "6.0.0"})), [])
        self.assertTrue(env.missing(bad(versions={**GOOD["versions"], "lxml": "4.9.0"})))

    def test_requirements_txt_matches(self):
        from tests._paths import PKG
        lines = [l.strip() for l in (PKG / "requirements.txt").read_text(encoding="utf-8").splitlines() if l.strip()]
        self.assertEqual(sorted(lines), sorted(f"{k}{v}" for k, v in env.REQUIREMENTS.items()))


class SelectTest(unittest.TestCase):
    def test_system_first(self):
        with mock.patch.object(env, "probe", return_value=GOOD):
            sel = env.select_python(Path("C:/sys/python.exe"))
        self.assertEqual((sel.kind, sel.path), ("system", Path("C:/sys/python.exe")))

    def test_falls_back_to_venv(self):
        system = Path("C:/sys/python.exe")

        def fake(py):
            return bad(chromium=False) if py == system else GOOD
        with mock.patch.object(env, "probe", side_effect=fake), \
                mock.patch.object(env.paths, "venv_python", return_value=Path("C:/v/python.exe")), \
                mock.patch.object(Path, "exists", return_value=True):
            sel = env.select_python(system)
        self.assertEqual(sel.kind, "venv")
        self.assertTrue(sel.system_missing)

    def test_none_when_both_unusable(self):
        with mock.patch.object(env, "probe", return_value=bad(chromium=False)), \
                mock.patch.object(env.paths, "venv_python", return_value=Path("C:/nope/python.exe")), \
                mock.patch.object(Path, "exists", return_value=False):
            sel = env.select_python(Path("C:/sys/python.exe"))
        self.assertEqual(sel.kind, "none")
        self.assertIsNone(sel.path)
        self.assertTrue(sel.venv_missing)


class DoctorTest(unittest.TestCase):
    def test_shows_system_missing(self):
        buf = io.StringIO()
        with mock.patch.dict(os.environ, {"PPTX_DECK_PYTHON_KIND": "venv",
                                          "PPTX_DECK_SYSTEM_MISSING": '["playwright が未導入です"]'}),                 mock.patch.object(cli, "_font_installed", return_value=True),                 contextlib.redirect_stdout(buf):
            cli.cmd_doctor(None)
        out = json.loads(buf.getvalue())
        self.assertEqual(out["python"]["kind"], "venv")
        self.assertEqual(out["python"]["system_missing"], ["playwright が未導入です"])


if __name__ == "__main__":
    unittest.main()
