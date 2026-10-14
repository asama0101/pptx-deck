import unittest

from lxml import etree
from pptx import Presentation

from tests import _paths  # noqa: F401
from pptx_deck import template

A = "http://schemas.openxmlformats.org/drawingml/2006/main"
P = "http://schemas.openxmlformats.org/presentationml/2006/main"


def _set_layout_bg(layout, inner_xml: str):
    cSld = layout._element.find(f"{{{P}}}cSld")
    old = cSld.find(f"{{{P}}}bg")
    if old is not None:
        cSld.remove(old)
    bg = etree.fromstring(f'<p:bg xmlns:p="{P}" xmlns:a="{A}">{inner_xml}</p:bg>')
    cSld.insert(0, bg)


class LayoutBgTest(unittest.TestCase):
    def setUp(self):
        self.prs = Presentation()      # python-pptx の既定テンプレート（マスターの背景は bgRef の bg1 = 白）

    def test_inherits_master_scheme_color(self):
        self.assertEqual(template.layout_bg_hex(self.prs, 0), "#FFFFFF")

    def test_layout_srgb_override(self):
        _set_layout_bg(self.prs.slide_layouts[1], '<p:bgPr><a:solidFill><a:srgbClr val="1F3A5F"/></a:solidFill><a:effectLst/></p:bgPr>')
        self.assertEqual(template.layout_bg_hex(self.prs, 1), "#1F3A5F")

    def test_layout_scheme_color_is_resolved_via_theme(self):
        _set_layout_bg(self.prs.slide_layouts[2], '<p:bgPr><a:solidFill><a:schemeClr val="tx1"/></a:solidFill><a:effectLst/></p:bgPr>')
        self.assertEqual(template.layout_bg_hex(self.prs, 2), "#000000")

    def test_color_transform_returns_none(self):
        _set_layout_bg(self.prs.slide_layouts[4], '<p:bgPr><a:solidFill><a:schemeClr val="bg1"><a:lumMod val="95000"/></a:schemeClr></a:solidFill><a:effectLst/></p:bgPr>')
        self.assertIsNone(template.layout_bg_hex(self.prs, 4))

    def test_no_theme_part(self):
        from pptx.opc.constants import RELATIONSHIP_TYPE as RT
        master = self.prs.slide_masters[0]
        for rId, rel in list(master.part.rels.items()):
            if rel.reltype == RT.THEME:
                master.part.rels.pop(rId)
        _set_layout_bg(self.prs.slide_layouts[1], '<p:bgPr><a:solidFill><a:srgbClr val="1F3A5F"/></a:solidFill><a:effectLst/></p:bgPr>')
        _set_layout_bg(self.prs.slide_layouts[2], '<p:bgPr><a:solidFill><a:schemeClr val="tx1"/></a:solidFill><a:effectLst/></p:bgPr>')
        self.assertEqual(template.layout_bg_hex(self.prs, 1), "#1F3A5F")
        self.assertIsNone(template.layout_bg_hex(self.prs, 2))

    def test_gradient_returns_none(self):
        _set_layout_bg(self.prs.slide_layouts[3], '<p:bgPr><a:gradFill><a:gsLst><a:gs pos="0"><a:srgbClr val="000000"/></a:gs></a:gsLst></a:gradFill><a:effectLst/></p:bgPr>')
        self.assertIsNone(template.layout_bg_hex(self.prs, 3))


class BackgroundColorsTest(unittest.TestCase):
    def test_standard_template(self):
        from tests._paths import PKG
        path = PKG / "assets" / "template" / "standard.potx"
        info = template.analyze(path)
        colors, notes = template.background_colors(path, info)
        self.assertEqual(set(colors), {"cover", "body", "closing"})
        for v in colors.values():
            self.assertRegex(v, r"^#[0-9A-F]{6}$")

    def test_css_has_no_image(self):
        from tests._paths import PKG
        info = template.analyze(PKG / "assets" / "template" / "standard.potx")
        css = template.layout_css(info, "#FFFFFF", {"cover": "#112233", "body": "#FFFFFF", "closing": "#FFFFFF"})
        self.assertNotIn("background-image", css)
        self.assertIn('.slide[data-layout="cover"] { --bg: #112233; }', css)


if __name__ == "__main__":
    unittest.main()
