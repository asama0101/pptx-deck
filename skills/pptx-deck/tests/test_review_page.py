"""レビューページ（variants.html・final-review.html）: 画面の構成、前回のコメントと直しの表示、見どころの枠、送信の互換。"""
import json
import re

import pytest

from pptx_deck import cli, initdir, measure, variants


def frag(text, note=None):
    attr = f' data-note="{note}"' if note else ""
    return (f'<section class="slide" data-layout="content"><div class="pp-text" data-role="title"{attr} '
            f'style="height:44px">{text}</div></section>')


def make(work, spec, notes=None):
    d = work / "slides"
    d.mkdir(parents=True, exist_ok=True)
    for name, text in spec.items():
        (d / f"{name}.html").write_text(frag(text, (notes or {}).get(name)), encoding="utf-8")


def test_viewer_has_list_panes_thumbs_and_note_toggle(tmp_path):
    make(tmp_path, {"01-A": "a1", "01-B": "b1", "01-C": "c1", "02-A": "a2"}, notes={"01-A": "題：結論の一文"})
    html = variants.assemble(tmp_path).read_text(encoding="utf-8")
    assert html.count('<button data-go="') == 2                       # 左の一覧（スライドごと）
    assert html.count('class="pane"') == 2 and html.count('class="opt"') == 4        # 1 枚ずつの面と、案のサムネ
    assert 'data-note="題：結論の一文"' in html and "見どころの枠を表示" in html
    assert "一覧" in html and "round: 1" in html


def test_viewer_lists_slide_titles(tmp_path):
    make(tmp_path, {"01-A": "B案を採用する"})
    html = variants.assemble(tmp_path).read_text(encoding="utf-8")
    assert "<small>B案を採用する</small>" in html


def test_round_one_has_no_previous_panels(tmp_path):
    make(tmp_path, {"01-A": "a1"})
    (tmp_path / "answers-1.md").write_text("## S01\n- 選択: A\n- コメント: 直して\n", encoding="utf-8")
    html = variants.assemble(tmp_path, round_no=1).read_text(encoding="utf-8")
    assert "前回のコメント</h3>" not in html and "今回の直し</h3>" not in html


def test_round_two_shows_previous_comment_and_fix_notes(tmp_path):
    make(tmp_path, {"01-A": "a1", "02-A": "a2"})
    (tmp_path / "answers-1.md").write_text(
        "## S01\n- 選択: A\n- コメント: \n## S02\n- 選択: A\n- コメント: 色を濃く\n", encoding="utf-8")
    (tmp_path / "round-2-notes.md").write_text("02: 基調色を濃くした\n", encoding="utf-8")
    html = variants.assemble(tmp_path, round_no=2).read_text(encoding="utf-8")
    assert html.count("前回のコメント</h3>") == 1 and "色を濃く" in html            # コメントのあるスライドだけ
    assert html.count("今回の直し</h3>") == 1 and "基調色を濃くした" in html


def test_round_two_without_answers_or_notes_is_fine(tmp_path):
    make(tmp_path, {"01-A": "a1"})
    html = variants.assemble(tmp_path, round_no=3).read_text(encoding="utf-8")
    assert "前回のコメント</h3>" not in html and "<section" in html


def test_previous_comment_is_escaped(tmp_path):
    make(tmp_path, {"01-A": "a1"})
    (tmp_path / "answers-1.md").write_text("## S01\n- 選択: A\n- コメント: <b>x</b>\n", encoding="utf-8")
    html = variants.assemble(tmp_path, round_no=2).read_text(encoding="utf-8")
    assert "&lt;b&gt;x&lt;/b&gt;" in html


def test_parse_notes_accepts_several_line_forms():
    md = "02: 直した\n- S03：別の直し\n* 04: 三つ目\n関係ない行\n"
    assert variants.parse_notes(md) == {"02": "直した", "03": "別の直し", "04": "三つ目"}


ANS = "## S01\n- 選択: A\n- コメント: \n## S02\n- 選択: B\n- コメント: \n"


def test_finalize_also_writes_final_review_without_touching_final_html(tmp_path):
    make(tmp_path, {"01-A": "a1", "02-A": "a2", "02-B": "b2"})
    final = variants.finalize(tmp_path, ANS).read_text(encoding="utf-8")
    assert 'class="rv"' not in final and "b2" in final and "a2" not in final      # final.html は素のまま（build が使う）
    rv = (tmp_path / "final-review.html").read_text(encoding="utf-8")
    assert rv.count('value="FIX"') == 2 and rv.count('value="A"') == 2           # 承認 / 要修正（各スライド 1 案）
    assert "b2" in rv and "a2" not in rv and "round: final" in rv and "最終 HTML の確認" in rv


def test_review_final_command(tmp_path):
    make(tmp_path, {"01-A": "a1"})
    ans = tmp_path / "answers-1.md"
    ans.write_text("## S01\n- 選択: A\n- コメント: \n", encoding="utf-8")
    assert cli.main(["review-final", str(tmp_path), "--answers", str(ans)]) == 0
    assert (tmp_path / "final-review.html").exists() and not (tmp_path / "final.html").exists()


def test_review_final_reports_problems(tmp_path, capsys):
    make(tmp_path, {"01-A": "a1", "02-A": "a2"})
    ans = tmp_path / "answers-1.md"
    ans.write_text("## S01\n- 選択: A\n- コメント: \n", encoding="utf-8")
    assert cli.main(["review-final", str(tmp_path), "--answers", str(ans)]) == 2
    assert "S02" in capsys.readouterr().err


def test_data_note_does_not_change_measurement(tmp_path):
    head = ('<!doctype html><meta charset="utf-8"><style>*{box-sizing:border-box;margin:0;padding:0}'
            '.slide{position:relative;width:1280px;height:720px}.pp-text{position:absolute}</style>')
    body = ('<section class="slide" data-layout="content"><div class="pp-text" data-role="title" {a} '
            'style="left:64px;top:40px;width:900px;font-size:28px">結論</div></section>')
    plain, noted = tmp_path / "p.html", tmp_path / "n.html"
    plain.write_text(head + body.format(a=""), encoding="utf-8")
    noted.write_text(head + body.format(a='data-note="題：結論の一文"'), encoding="utf-8")
    assert json.dumps(measure.measure(plain), sort_keys=True) == json.dumps(measure.measure(noted), sort_keys=True)


def _open(tmp_path, page):
    from playwright.sync_api import sync_playwright
    p = sync_playwright().start()
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1280, "height": 720})
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(page.as_uri())
    return p, b, pg, errors


def test_browser_flow_submits_the_same_answers_format(tmp_path):
    make(tmp_path, {"01-A": "a1", "01-B": "b1", "02-A": "a2"}, notes={"01-A": "題：結論の一文", "01-B": "題：結論の一文"})
    page = variants.assemble(tmp_path)
    p, b, pg, errors = _open(tmp_path, page)
    try:
        pg.wait_for_function("document.querySelector('.pane:not([hidden])') !== null")
        assert pg.evaluate("document.querySelectorAll('.co').length") == 1          # 見どころの枠が重なる
        pg.click('#nav button[data-go="02"]')
        assert pg.evaluate("document.querySelector('.pane[data-slide=\"02\"]').hidden") is False
        pg.click('#nav button[data-go="01"]')
        pg.click('.pane[data-slide="01"] .opt[data-k="B"] .thumb')                  # サムネで大きな表示が切り替わる
        assert "b1" in pg.evaluate("document.querySelector('.pane[data-slide=\"01\"] .big').textContent")
        pg.check('.pane[data-slide="01"] input[value="B"]')
        pg.fill('.pane[data-slide="01"] textarea', "色を濃く")
        pg.click('#nav button[data-go="02"]')
        pg.click('.pane[data-slide="02"] .verdict button[data-v="承認"]')               # 1 案だけのスライドは、承認ボタンで採用になる
        pg.click('.pane:not([hidden]) .copyBtn')
        assert pg.evaluate("window.__submitted") is True
        md = pg.evaluate("window.__answersMd")
    finally:
        b.close()
        p.stop()
    assert errors == []
    assert variants.parse_answers(md) == {"01": {"choice": "B", "comment": "色を濃く"},
                                          "02": {"choice": "A", "comment": "", "verdict": "承認"}}
    assert re.match(r"^---\ndeck: .+\nround: 1\n---\n## S01\n", md)
    variants.finalize(tmp_path, md, allow_comments=True)                            # 従来の finalize がそのまま読める


def test_radio_can_be_unselected_by_clicking_again_or_by_the_clear_button(tmp_path):
    make(tmp_path, {"01-A": "a1", "01-B": "b1"})
    page = variants.assemble(tmp_path)
    assert "選択を外す" in page.read_text(encoding="utf-8")
    p, b, pg, errors = _open(tmp_path, page)
    try:
        sel = '.pane[data-slide="01"] input[value="B"]'
        pg.click(sel)
        assert pg.is_checked(sel)
        pg.click(sel)                                                  # もう一度押すと外れる
        assert not pg.is_checked(sel)
        pg.click(sel)
        pg.click('.pane[data-slide="01"] .clear')                      # 「選択を外す」でも外れる
        assert not pg.is_checked(sel)
        pg.click('.pane:not([hidden]) .copyBtn')
        md = pg.evaluate("window.__answersMd")
    finally:
        b.close()
        p.stop()
    assert errors == []
    assert variants.parse_answers(md)["01"]["choice"] == ""            # 未選択のまま送れる（従来の形式）


@pytest.mark.parametrize("size", [(1280, 720), (1366, 768), (1920, 1080)])
def test_layout_follows_the_review_artifact(tmp_path, size):
    """点検ページ（Artifact）と同じ構成: 左に一覧（270px・追従）、右に大きなスライド（16:9）、判断欄。「回答をコピー」は判断欄の最後（右端・固定しない）。"""
    make(tmp_path, {"01-A": "a1", "01-B": "b1", "01-C": "c1"}, notes={"01-A": "題：結論の一文"})
    from playwright.sync_api import sync_playwright
    page = variants.assemble(tmp_path)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": size[0], "height": size[1]})
        pg.goto(page.as_uri())
        pg.wait_for_function("document.querySelector('.pane:not([hidden]) .big .slide') !== null")
        m = pg.evaluate("""() => {
            const big = document.querySelector('.pane:not([hidden]) .big').getBoundingClientRect();
            const nav = document.querySelector('#nav').getBoundingClientRect();
            const cp = document.querySelector('.pane:not([hidden]) .copyBtn').getBoundingClientRect(), bar = document.querySelector('.pane:not([hidden]) .copyBtn');
            const judge = document.querySelector('.pane:not([hidden]) .judge').getBoundingClientRect();
            const verdict = document.querySelector('.pane:not([hidden]) .verdict').getBoundingClientRect();
            const opts = document.querySelector('.pane:not([hidden]) .opts').getBoundingClientRect();
            return { bw: big.width, bh: big.height, navW: nav.width, barPos: getComputedStyle(bar).position, copyRight: cp.right, copyTop: cp.top, judgeRight: judge.right, vh: innerHeight,
                     optsBottom: opts.bottom, verdictTop: verdict.top, judgeTop: judge.top, bigBottom: big.bottom,
                     sw: document.documentElement.scrollWidth }; }""")
        b.close()
    assert abs(m["bw"] / m["bh"] - 16 / 9) < 0.02 and m["bw"] >= 560           # 大きな表示は 16:9 で、小さすぎない
    assert abs(m["navW"] - 270) < 2                                            # 左の一覧は 270px（Artifact と同じ）
    assert m["barPos"] == "static" and m["copyRight"] >= m["judgeRight"] - 30 and m["copyTop"] >= m["verdictTop"]     # 固定せず、判断欄の最後（右端）にある
    assert m["verdictTop"] >= m["optsBottom"] - 1 and m["judgeTop"] >= m["bigBottom"] - 1      # 大きな表示 → 3 択 → 承認／要修正
    assert m["sw"] <= size[0] + 1                                              # 横にはみ出さない


def test_parse_answers_reads_the_optional_verdict_line():
    md = "## S01\n- 選択: B\n- 判定: 要修正\n- コメント: 色\n## S02\n- 選択: A\n- 判定: \n- コメント: \n## S03\n- 選択: A\n- コメント: \n"
    got = variants.parse_answers(md)
    assert got["01"] == {"choice": "B", "comment": "色", "verdict": "要修正"}
    assert got["02"] == {"choice": "A", "comment": ""} and got["03"] == {"choice": "A", "comment": ""}      # 判定が空・なしは従来どおり


def test_finalize_stops_on_a_verdict_of_needs_fix_even_without_comment(tmp_path):
    make(tmp_path, {"01-A": "a1", "01-B": "b1"})
    md = "## S01\n- 選択: B\n- 判定: 要修正\n- コメント: \n"
    with pytest.raises(ValueError, match="S01.*要修正"):
        variants.finalize(tmp_path, md)
    variants.finalize(tmp_path, md, allow_comments=True)                 # 承知のうえなら通せる


def test_verdict_buttons_and_copy_button_in_the_browser(tmp_path):
    make(tmp_path, {"01-A": "a1", "01-B": "b1", "02-A": "a2"})
    page = variants.assemble(tmp_path)
    html = page.read_text(encoding="utf-8")
    assert html.count('data-v="承認"') == 2 and html.count('data-v="要修正"') == 2 and "回答をコピー" in html
    p, b, pg, errors = _open(tmp_path, page)
    try:
        ok = '.pane[data-slide="01"] .verdict button[data-v="承認"]'
        pg.click(ok)                                                    # 案を選んでいなければ、表示中の案が選ばれる
        assert pg.get_attribute(ok, "aria-pressed") == "true"
        assert pg.is_checked('.pane[data-slide="01"] input[value="A"]')
        pg.click('.pane[data-slide="01"] .verdict button[data-v="要修正"]')
        assert pg.get_attribute(ok, "aria-pressed") == "false"
        pg.click('.pane[data-slide="01"] .verdict button[data-v="要修正"]')      # もう一度押すと外れる
        assert pg.get_attribute('.pane[data-slide="01"] .verdict button[data-v="要修正"]', "aria-pressed") == "false"
        pg.click('.pane[data-slide="01"] .verdict button[data-v="要修正"]')
        pg.click('#nav button[data-go="02"]')
        pg.click('.pane[data-slide="02"] .verdict button[data-v="要修正"]')
        pg.click('.pane:not([hidden]) .copyBtn')
        pg.wait_for_function("document.querySelector('.pane:not([hidden]) .state').textContent !== ''")
        pg.click('.pane:not([hidden]) .copyBtn')
        md = pg.evaluate("window.__answersMd")
    finally:
        b.close()
        p.stop()
    assert errors == []
    got = variants.parse_answers(md)
    assert got["01"]["verdict"] == "要修正" and got["01"]["choice"] == "A"
    assert got["02"] == {"choice": "FIX", "comment": "", "verdict": "要修正"}


def test_there_is_no_separate_submit_button_and_copy_does_both(tmp_path):
    make(tmp_path, {"01-A": "a1", "01-B": "b1"})
    page = variants.assemble(tmp_path)
    html = page.read_text(encoding="utf-8")
    assert 'id="submit"' not in html and "送信</button>" not in html and html.count("回答をコピー") >= 1
    p, b, pg, errors = _open(tmp_path, page)
    try:
        assert pg.evaluate("window.__submitted") is None
        pg.check('.pane[data-slide="01"] input[value="A"]')
        pg.click('.pane:not([hidden]) .copyBtn')                                              # コピーと同時に、受け取り用の変数が立つ
        assert pg.evaluate("window.__submitted") is True
        md = pg.evaluate("window.__answersMd")
        pg.wait_for_function("document.querySelector('.pane:not([hidden]) .state').textContent !== ''")
    finally:
        b.close()
        p.stop()
    assert errors == [] and variants.parse_answers(md)["01"]["choice"] == "A"


def test_same_note_text_is_grouped_into_one_frame(tmp_path):
    d = tmp_path / "slides"
    d.mkdir()
    (tmp_path / "base.css").write_text(".slide{position:relative;width:1280px;height:720px}.pp-text{position:absolute}", encoding="utf-8")
    (d / "01-A.html").write_text(
        '<section class="slide" data-layout="content">'
        '<div class="pp-text" data-note="見どころ A" style="left:64px;top:40px;width:300px;height:40px">a</div>'
        '<div class="pp-text" data-note="見どころ A" style="left:64px;top:200px;width:300px;height:40px">b</div>'
        '<div class="pp-text" data-note="見どころ B" style="left:500px;top:300px;width:300px;height:40px">c</div></section>', encoding="utf-8")
    p, b, pg, errors = _open(tmp_path, variants.assemble(tmp_path))
    try:
        pg.wait_for_function("document.querySelector('.pane:not([hidden]) .big .slide') !== null")
        n = pg.evaluate("document.querySelectorAll('.pane:not([hidden]) .big .co').length")
        legend = pg.evaluate("[...document.querySelectorAll('.pane:not([hidden]) .legend li')].map(l => l.textContent)")
        h = pg.evaluate("parseFloat(document.querySelector('.pane:not([hidden]) .big .co').style.height)")
    finally:
        b.close()
        p.stop()
    assert errors == [] and n == 2 and len(legend) == 2        # 同じ文の 2 つの要素が 1 つの枠
    assert h >= 200                                            # 枠は 2 つの要素をまとめた大きさ（top 40〜240）
