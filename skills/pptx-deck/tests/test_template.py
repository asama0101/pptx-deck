import io
import shutil
import zipfile
from pathlib import Path

import pytest
from pptx import Presentation
from pptx.util import Emu

from pptx_deck import paths, render, template
from pptx_deck.pptxutil import SLIDE_W_EMU

STANDARD = paths.ASSETS / "template" / "standard.potx"
has_soffice = pytest.mark.skipif(shutil.which("soffice") is None and not Path(
    r"C:\Program Files\LibreOffice\program\soffice.exe").exists(), reason="LibreOffice なし")


def _as_pptx(potx: Path, dst: Path, rename=None, drop=None) -> Path:
    """標準テンプレートから、利用者が持ってきそうな .pptx を作る（content-type を戻す）。"""
    buf = io.BytesIO()
    with zipfile.ZipFile(potx) as zin, zipfile.ZipFile(buf, "w") as zout:
        for it in zin.infolist():
            d = zin.read(it.filename)
            if it.filename == "[Content_Types].xml":
                d = d.replace(b"presentationml.template.main+xml", b"presentationml.presentation.main+xml")
            zout.writestr(it, d)
    buf.seek(0)
    prs = Presentation(buf)
    for lay in prs.slide_layouts:
        if rename and lay.name in rename:
            lay._element.cSld.set("name", rename[lay.name])
    if drop:
        for lay in list(prs.slide_layouts):
            if lay.name == drop:
                prs.slide_layouts.remove(lay)
    prs.save(dst)
    return dst


def test_standard_template_exists_and_opens_as_potx():
    assert STANDARD.exists()
    prs = template.open_template(STANDARD)  # .potx を開ける（Review Focus 1）
    assert [l.name for l in prs.slide_layouts] == ["表紙", "本文", "裏表紙"]


def test_analyze_standard():
    info = template.analyze(STANDARD)
    assert (info.cover, info.body, info.closing) == (0, 1, 2)
    assert info.area.to_dict() == {"x": 64, "y": 150, "w": 1152, "h": 490}
    assert info.title.y == 40
    assert any(r.y >= 670 for r in info.keepout)       # フッター・ページ番号の領域
    assert info.cover_subtitle is not None
    assert info.closing_title.y == 300                  # 裏表紙の題の位置（プレビューと PPTX をそろえる）
    assert not info.notes


def test_analyze_pptx_with_english_names(tmp_path):
    p = _as_pptx(STANDARD, tmp_path / "u.pptx",
                 rename={"表紙": "Title Slide", "本文": "Title and Content", "裏表紙": "Closing"})
    info = template.analyze(p)
    assert (info.cover, info.body, info.closing) == (0, 1, 2)


def test_missing_closing_falls_back_with_note(tmp_path):
    p = _as_pptx(STANDARD, tmp_path / "u.pptx", drop="裏表紙")
    info = template.analyze(p)
    assert info.closing is None                         # Review Focus 4
    assert any("裏表紙" in n for n in info.notes)
    assert info.closing_title == info.title             # 本文のレイアウトで代えるので、題は本文の位置


def test_non_169_template_is_rejected(tmp_path):
    prs = Presentation()  # 既定は 4:3（10in × 7.5in）
    src = tmp_path / "old.pptx"
    prs.save(src)
    with pytest.raises(ValueError, match="13.33"):      # Review Focus 2
        template.analyze(src)


def test_keepout_includes_logo_shapes_on_layout_and_master(tmp_path):
    from pptx.oxml import parse_xml
    from pptx_deck.pptxutil import emu

    def add_rect(shapes, sid, x, y, w, h):
        shapes._spTree.append(parse_xml(
            '<p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
            'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            f'<p:nvSpPr><p:cNvPr id="{sid}" name="logo"/><p:cNvSpPr/><p:nvPr userDrawn="1"/></p:nvSpPr>'
            f'<p:spPr><a:xfrm><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:sp>'))

    src = _as_pptx(STANDARD, tmp_path / "u.pptx")
    prs = Presentation(src)
    body = [l for l in prs.slide_layouts if l.name == "本文"][0]
    add_rect(body.shapes, 901, 1100, 20, 120, 60)                       # ロゴ想定（レイアウト）
    add_rect(prs.slide_master.shapes, 902, 20, 600, 100, 50)            # ロゴ想定（マスター）
    add_rect(prs.slide_master.shapes, 903, 0, 0, 1280, 720)             # 全面の背景は除く
    prs.save(src)
    info = template.analyze(src)
    got = [(r.x, r.y, r.w, r.h) for r in info.keepout]
    assert (1100, 20, 120, 60) in got and (20, 600, 100, 50) in got
    assert not any(r.w >= 1280 for r in info.keepout)


def test_drop_all_slides_clears_section_and_custom_show_refs(tmp_path):
    from lxml import etree
    from pptx_deck.pptxutil import drop_all_slides
    prs = template.open_template(STANDARD)
    s = prs.slides.add_slide(prs.slide_layouts[1])
    sid = prs.slides._sldIdLst[0].get("id")
    P14 = "http://schemas.microsoft.com/office/powerpoint/2010/main"
    root = prs.part._element
    root.append(etree.fromstring(
        '<p:extLst xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
        '<p:ext uri="{521415D9-36F7-43E2-AB2F-B90AF26B5E84}">'
        f'<p14:sectionLst xmlns:p14="{P14}"><p14:section name="A" id="{{11111111-1111-1111-1111-111111111111}}">'
        f'<p14:sldIdLst><p14:sldId id="{sid}"/></p14:sldIdLst></p14:section></p14:sectionLst></p:ext></p:extLst>'))
    drop_all_slides(prs)
    assert not list(root.iter(f"{{{P14}}}sldId"))                    # 消したスライドの id を残さない
    out = tmp_path / "x.pptx"
    prs.save(out)
    assert len(Presentation(out).slides) == 0


def test_info_roundtrip():
    info = template.analyze(STANDARD)
    assert template.TemplateInfo.from_dict(info.to_dict()) == info


def test_layout_css_has_area_and_backgrounds():
    info = template.analyze(STANDARD)
    css = template.layout_css(info, "#FFFFFF")
    for token in ("--area-x: 64px", "--title-y: 40px", "--cover-title-x: 96px", "--closing-title-y: 300px",
                  "_template/bg-cover.png", "_template/bg-body.png", "--bg: #FFFFFF"):
        assert token in css


def test_layout_css_sets_background_per_layout():
    info = template.analyze(STANDARD)
    css = template.layout_css(info, "#FFFFFF", {"cover": "#101820", "closing": "#202830"})
    assert '.slide[data-layout="cover"] { --bg: #101820; }' in css
    assert '.slide[data-layout="closing"] { --bg: #202830; }' in css


@has_soffice
def test_underlay_colors_are_sampled_per_layout(tmp_path):
    info = template.analyze(STANDARD)
    template.render_underlays(STANDARD, info, tmp_path)
    assert template.underlay_colors(tmp_path, info) == {"cover": "#FFFFFF", "body": "#FFFFFF", "closing": "#FFFFFF"}


@has_soffice
def test_render_underlays(tmp_path):
    info = template.analyze(STANDARD)
    bg = template.render_underlays(STANDARD, info, tmp_path)
    for name in ("bg-cover.png", "bg-body.png", "bg-closing.png"):
        assert (tmp_path / name).exists()
    assert bg == "#FFFFFF"                              # 標準テンプレートの本文は白


@has_soffice
def test_underlay_shows_the_page_number_like_the_pptx(tmp_path):
    import fitz
    info = template.analyze(STANDARD)
    template.render_underlays(STANDARD, info, tmp_path)
    pix = fitz.Pixmap(str(tmp_path / "bg-body.png"))
    dark = [(x, y) for x in range(1150, 1216) for y in range(676, 704) if sum(pix.pixel(x, y)[:3]) < 600]
    assert dark, "HTML のプレビューにもページ番号が出る（PPTX と見た目をそろえる）"


@has_soffice
def test_pptx_to_pngs_uses_os_temp_and_returns_files(tmp_path):
    prs = template.open_template(STANDARD)
    prs.slides.add_slide(prs.slide_layouts[1])
    src = tmp_path / "x.pptx"
    prs.save(src)
    pngs = render.pptx_to_pngs(src, tmp_path / "out", width_px=640)
    assert len(pngs) == 1 and pngs[0].exists()
