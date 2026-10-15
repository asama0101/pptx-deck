"""テンプレートの全レイアウトから、章扉・目次・型の専用レイアウトを推定し、PPTX に使う（init の推定・template-map の修正・build）。"""
import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from pptx import Presentation

from tests import _paths  # noqa: F401
from tests._paths import PKG
from pptx_deck import cli, paths, template

COMP = PKG / "assets" / "components"


def run(*argv):
    buf, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
        rc = cli.main(list(argv))
    return rc, buf.getvalue(), err.getvalue()


def make_template(path: Path, names: dict[int, str]) -> Path:
    """python-pptx の既定テンプレート（11 レイアウト）を 16:9 にして、レイアウト名を付け替えて保存する。"""
    prs = Presentation()
    prs.slide_width, prs.slide_height = 12192000, 6858000
    for i, name in names.items():
        prs.slide_layouts[i]._element.cSld.set("name", name)
    for lay in prs.slide_layouts:        # 既定の配置は 4:3 用なので、本文のタイトルを標準テンプレートと同じ位置・幅にする
        for ph in lay.placeholders:
            if ph.placeholder_format.type in (1, 3):          # TITLE・CENTER_TITLE
                ph.left, ph.top, ph.width, ph.height = 64 * 9525, 36 * 9525, 1152 * 9525, 50 * 9525
    prs.save(str(path))
    return path


NAMES = {0: "表紙", 1: "本文", 2: "章扉", 3: "目次", 4: "スケジュール", 5: "裏表紙"}


class EstimateTest(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.tpl = make_template(Path(self.td.name) / "t.pptx", NAMES)

    def test_section_agenda_and_types_are_estimated_by_name(self):
        info = template.analyze(self.tpl)
        self.assertEqual(info.kinds, {"section": 2, "agenda": 3})
        self.assertEqual({t: i for t, i in info.types.items() if i == 4}, {"gantt": 4, "roadmap": 4, "timeline": 4})
        self.assertEqual(info.closing, 5)

    def test_standard_template_has_no_extra_layouts(self):
        info = template.analyze(paths.ASSETS / "template" / "standard.potx")
        self.assertEqual((info.kinds, info.types), ({}, {}))
        self.assertTrue(any("章扉" in n for n in info.notes))      # 本文で代える旨を伝える

    def test_roundtrip_and_old_json(self):
        info = template.analyze(self.tpl)
        again = template.TemplateInfo.from_dict(json.loads(json.dumps(info.to_dict())))
        self.assertEqual((again.kinds, again.types), (info.kinds, info.types))
        old = info.to_dict()
        for k in ("kinds", "types", "layout_keepout"):
            old.pop(k)
        self.assertEqual(template.TemplateInfo.from_dict(old).kinds, {})      # 旧い template.json も読める

    def test_layout_index_precedence(self):
        info = template.analyze(self.tpl)
        self.assertEqual(template.layout_index(info, {"layout": "cover", "type": "cover"}), info.cover)
        self.assertEqual(template.layout_index(info, {"layout": "section", "type": "section"}), 2)
        self.assertEqual(template.layout_index(info, {"layout": "diagram", "type": "gantt"}), 4)      # 型の専用レイアウトが先
        self.assertEqual(template.layout_index(info, {"layout": "diagram", "type": "flow-h"}), info.body)
        self.assertEqual(template.layout_index(info, {"layout": "diagram"}), info.body)             # 自由設計の案（型なし）

    def test_set_mapping_and_clear(self):
        info = template.analyze(self.tpl)
        info = template.set_mapping(self.tpl, info, "agenda", "本文")
        self.assertEqual(info.kinds["agenda"], 1)
        info = template.set_mapping(self.tpl, info, "gantt", None)
        self.assertNotIn("gantt", info.types)
        info = template.set_mapping(self.tpl, info, "flow-h", "スケジュール")
        self.assertEqual(info.types["flow-h"], 4)
        with self.assertRaises(ValueError):
            template.set_mapping(self.tpl, info, "nonexistent", "本文")
        with self.assertRaises(ValueError):
            template.set_mapping(self.tpl, info, "agenda", "存在しないレイアウト")


class BuildTest(unittest.TestCase):
    def test_pptx_uses_template_layouts(self):
        with tempfile.TemporaryDirectory() as td:
            tpl = make_template(Path(td) / "t.pptx", NAMES)
            base = Path(td) / "demo"
            rc, out, err = run("init", str(base), "--template", str(tpl))
            self.assertEqual(rc, 0, err)
            self.assertIn("layout_map", out)
            work = paths.resolve_work(base)
            slides = work / "slides"
            shutil.copyfile(COMP / "layouts" / "cover.html", slides / "01-A.html")
            shutil.copyfile(COMP / "layouts" / "section.html", slides / "02-A.html")
            shutil.copyfile(COMP / "layouts" / "agenda.html", slides / "03-A.html")
            shutil.copyfile(COMP / "diagrams" / "gantt.html", slides / "04-A.html")
            shutil.copyfile(COMP / "charts" / "bar.html", slides / "05-A.html")
            self.assertEqual(run("variants", str(base))[0], 0)
            (work / "answers-1.md").write_text(
                "---\ndeck: demo\nround: 1\n---\n" + "".join(f"## S0{i}\n- 選択: A\n- 判定: 承認\n- コメント: \n" for i in range(1, 6)),
                encoding="utf-8")
            self.assertEqual(run("finalize", str(base))[0], 0)
            rc, out, err = run("build", str(base))
            self.assertEqual(rc, 0, out + err)
            prs = Presentation(str(base / "demo.pptx"))
            names = [s.slide_layout.name for s in prs.slides]
            self.assertEqual(names, ["表紙", "章扉", "目次", "スケジュール", "本文"])

    def test_template_map_set_changes_build(self):
        with tempfile.TemporaryDirectory() as td:
            tpl = make_template(Path(td) / "t.pptx", NAMES)
            base = Path(td) / "demo"
            self.assertEqual(run("init", str(base), "--template", str(tpl))[0], 0)
            work = paths.resolve_work(base)
            rc, out, err = run("template-map", str(base), "--clear", "section", "--set", "bar=スケジュール")
            self.assertEqual(rc, 0, err)
            cfg = json.loads((work / "template.json").read_text(encoding="utf-8"))
            self.assertNotIn("section", cfg["info"]["kinds"])
            self.assertEqual(cfg["info"]["types"]["bar"], 4)
            rc, _, err = run("template-map", str(base), "--set", "bar=ない")
            self.assertEqual(rc, 2)
            self.assertIn("決まりません", err)


if __name__ == "__main__":
    unittest.main()
