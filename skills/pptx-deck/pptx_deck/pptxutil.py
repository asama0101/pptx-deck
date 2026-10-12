from pptx.dml.color import RGBColor
from pptx.oxml.ns import qn
from pptx.util import Emu, Pt

PX = 9525
FONT = "BIZ UDPゴシック"
SLIDE_W_EMU = 12192000  # 13.333in
SLIDE_H_EMU = 6858000   # 7.5in


def emu(px: float) -> Emu:
    return Emu(round(px * PX))


def rgb(hex6: str) -> RGBColor:
    return RGBColor.from_string(hex6.lstrip("#").upper())


def drop_all_slides(prs) -> None:
    """テンプレートの既存スライドをすべて外す（マスターとレイアウトは残す）。"""
    lst = prs.slides._sldIdLst
    for sld in list(lst):
        prs.part.drop_rel(sld.rId)
        lst.remove(sld)
    # セクション・目的別スライド ショーが、消したスライドの id を指したままだと PowerPoint が修復を求める
    root = prs.part._element
    for ref in list(root.iter("{http://schemas.microsoft.com/office/powerpoint/2010/main}sldId")):
        ref.getparent().remove(ref)
    for show in root.findall(qn("p:custShowLst")):
        root.remove(show)


def set_run_font(run, size_px: float, bold: bool, italic: bool, color_hex: str) -> None:
    f = run.font
    f.size = Pt(round(size_px * 0.75 * 2) / 2)  # 0.5pt 刻み
    f.bold = bold
    f.italic = italic
    f.color.rgb = rgb(color_hex)
    f.name = FONT  # a:latin
    rPr = run._r.get_or_add_rPr()
    latin = rPr.find(qn("a:latin"))
    ea = rPr.find(qn("a:ea"))
    if ea is None:
        from lxml import etree
        ea = etree.Element(qn("a:ea"))
        latin.addnext(ea)
    ea.set("typeface", FONT)
