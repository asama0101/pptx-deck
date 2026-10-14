import re
import unittest

from tests import _paths  # noqa: F401
from tests._paths import PKG, REPO


class DocsTest(unittest.TestCase):
    def test_four_skills_with_frontmatter(self):
        for name in ("create", "revise", "rebuild", "review-plan"):
            text = (PKG / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
            m = re.match(r"^---\nname: (.+)\ndescription: (.+)\n(?:compatibility: .+\n)?---\n", text)
            self.assertIsNotNone(m, name)
            self.assertEqual(m.group(1).strip(), name)

    def test_no_hardcoded_skill_paths(self):
        for f in (PKG / "skills").rglob("SKILL.md"):
            t = f.read_text(encoding="utf-8")
            self.assertNotIn("C:/Users", t, f)
            self.assertNotIn("${CLAUDE_SKILL_DIR}", t, f)
            self.assertIn("${CLAUDE_PLUGIN_ROOT}", t, f)

    def test_no_libreoffice_as_dependency(self):
        for f in [REPO / "README.md", *PKG.rglob("*.md")]:
            for line in f.read_text(encoding="utf-8").splitlines():
                if re.search(r"LibreOffice|soffice", line):
                    self.assertRegex(line, r"使わ|使用しな|不要|なし|廃止", f"{f}: {line}")

    def test_wait_cap_documented(self):
        for f in (PKG / "skills" / "create" / "SKILL.md", PKG / "references" / "review-flow.md"):
            t = f.read_text(encoding="utf-8")
            self.assertIn("18 回", t, f)
            self.assertRegex(t, r"続行方法.*質問|質問.*続行方法", f)

    def test_references_have_no_old_vars(self):
        for f in PKG.rglob("*.md"):
            t = f.read_text(encoding="utf-8")
            self.assertNotIn("${CLAUDE_SKILL_DIR}", t, f)
            self.assertNotIn("pngs", t, f)


if __name__ == "__main__":
    unittest.main()
