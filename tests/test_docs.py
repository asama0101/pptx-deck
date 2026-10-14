import re
import unittest

from tests import _paths  # noqa: F401
from tests._paths import PKG, REPO


class DocsTest(unittest.TestCase):
    def test_five_skills_with_frontmatter(self):
        for name in ("create", "revise", "rebuild", "review-plan", "diagram"):
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
                    self.assertRegex(line, r"使わ|使用しな|不要|廃止", f"{f}: {line}")

    def test_wait_cap_documented(self):
        for f in (PKG / "skills" / "create" / "SKILL.md", PKG / "skills" / "review-plan" / "SKILL.md",
                  PKG / "skills" / "diagram" / "SKILL.md", PKG / "references" / "review-flow.md"):
            t = f.read_text(encoding="utf-8")
            self.assertIn("18 回", t, f)
            self.assertRegex(t, r"続行方法.*質問|質問.*続行方法", f)
        revise = (PKG / "skills" / "revise" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("create の手順 4", revise)
        self.assertIn("18 回", revise)

    def test_revise_carries_force_or_out_to_build(self):
        t = (PKG / "skills" / "revise" / "SKILL.md").read_text(encoding="utf-8")
        m = re.search(r"^4\. .*build.*$", t, re.M)
        self.assertIsNotNone(m)
        self.assertIn("--force", m.group(0))
        self.assertIn("--out", m.group(0))

    def test_references_have_no_old_vars(self):
        for f in PKG.rglob("*.md"):
            t = f.read_text(encoding="utf-8")
            self.assertNotIn("${CLAUDE_SKILL_DIR}", t, f)
            self.assertNotIn("pngs", t, f)

    def test_skill_paths_resolve_from_plugin_root(self):
        """SKILL.md のパスは ${CLAUDE_PLUGIN_ROOT} 基準で、実在する。相対リンク（references/…）は使わない。"""
        for f in (PKG / "skills").rglob("SKILL.md"):
            t = f.read_text(encoding="utf-8")
            self.assertNotRegex(t, r"\]\((references|assets)/", f"{f}: 相対リンク")
            self.assertNotRegex(t, r"`(references|assets)/[A-Za-z0-9_]", f"{f}: 地の文の相対パス")
            for m in re.finditer(r"\$\{CLAUDE_PLUGIN_ROOT\}/((?:run\.py|references/|assets/)[A-Za-z0-9_./-]*)", t):
                rel = m.group(1)
                if "<" in rel:
                    continue
                self.assertTrue((PKG / rel.rstrip("/")).exists(), f"{f}: {rel}")

    def test_revise_points_to_create_skill_location(self):
        t = (PKG / "skills" / "revise" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("${CLAUDE_PLUGIN_ROOT}/skills/create/SKILL.md", t)

    def test_commands_in_docs_exist_in_cli(self):
        """SKILL.md・references・README が `run.py" <コマンド>` と書くコマンドは、cli.py に実在する。"""
        cli_src = (PKG / "pptx_deck" / "cli.py").read_text(encoding="utf-8")
        known = set(re.findall(r'sub\.add_parser\("([a-z-]+)"', cli_src)) | {"setup"}       # setup は run.py が直接処理する
        files = [*(PKG / "skills").rglob("SKILL.md"), *(PKG / "references").glob("*.md")]
        for f in files:
            for m in re.finditer(r'run\.py" ([a-z][a-z-]*)', f.read_text(encoding="utf-8")):
                self.assertIn(m.group(1), known, f"{f.name}: 存在しないコマンド {m.group(1)}")
        for name in ("draft", "history", "review-picture", "picture-status"):
            self.assertIn(name, known)

    def test_diagram_flow_is_documented(self):
        t = (PKG / "skills" / "diagram" / "SKILL.md").read_text(encoding="utf-8")
        for word in ("review-picture", "picture-status", "draft", "history", "answers-picture-N.md", "PowerPoint で直せない", "xx"):
            self.assertIn(word, t, word)
        craft = (PKG / "references" / "picture-craft.md").read_text(encoding="utf-8")
        for word in ("NW 構成図", "トラフィックフロー", "障害動作", "自己紹介", "marker", "viewBox", "history"):
            self.assertIn(word, craft, word)
        create = (PKG / "skills" / "create" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("skills/diagram/SKILL.md", create)
        self.assertTrue((REPO / "README.md").read_text(encoding="utf-8").count("diagram") >= 2)


if __name__ == "__main__":
    unittest.main()
