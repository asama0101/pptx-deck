import pytest

from pptx_deck import variants


def frag(text):
    return f'<section class="slide" data-layout="content"><div class="pp-text" data-role="title">{text}</div></section>'


def make(work, spec):
    d = work / "slides"
    d.mkdir(parents=True)
    for name, text in spec.items():
        (d / f"{name}.html").write_text(frag(text), encoding="utf-8")


def test_collect_groups_by_number(tmp_path):
    make(tmp_path, {"01-A": "a1", "01-B": "b1", "02-A": "a2", "readme": "x"})
    got = variants.collect(tmp_path)
    assert sorted(got) == ["01", "02"] and sorted(got["01"]) == ["A", "B"]


def test_collect_requires_slides(tmp_path):
    with pytest.raises(ValueError, match="slides"):
        variants.collect(tmp_path)


def test_assemble_has_choices_and_submit_hook(tmp_path):
    make(tmp_path, {"01-A": "a1", "01-B": "b1", "01-C": "c1", "02-A": "a2"})
    html = variants.assemble(tmp_path, round_no=2).read_text(encoding="utf-8")
    assert html.count('type="radio"') == 3 + 2            # 3 案 ＋ 1 案（採用／要修正）
    assert 'value="FIX"' in html and 'value="C"' in html
    assert "window.__answersMd" in html and "window.__submitted" in html
    assert "round: 2" in html
    assert 'href="theme.css"' in html and 'href="base.css"' in html
    assert "a1" in html and "c1" in html


def test_parse_answers():
    md = "---\ndeck: x\nround: 1\n---\n## S01\n- 選択: B\n- コメント: 色を濃く\n## S02\n- 選択: A\n- コメント: \n"
    assert variants.parse_answers(md) == {"01": {"choice": "B", "comment": "色を濃く"},
                                          "02": {"choice": "A", "comment": ""}}


ANS_OK = "## S01\n- 選択: B\n- コメント: \n## S02\n- 選択: A\n- コメント: \n"


def test_finalize_picks_selected_in_order(tmp_path):
    make(tmp_path, {"01-A": "a1", "01-B": "b1", "02-A": "a2"})
    out = variants.finalize(tmp_path, ANS_OK).read_text(encoding="utf-8")
    assert "b1" in out and "a1" not in out and out.index("b1") < out.index("a2")
    assert 'href="theme.css"' in out and out.count("<section") == 2


def test_finalize_lists_every_problem(tmp_path):
    make(tmp_path, {"01-A": "a1", "01-B": "b1", "02-A": "a2", "03-A": "a3"})
    md = "## S01\n- 選択: B\n- コメント: 色を変えて\n## S02\n- 選択: FIX\n- コメント: 直して\n"
    with pytest.raises(ValueError) as e:
        variants.finalize(tmp_path, md)
    msg = str(e.value)
    assert "S01" in msg and "色を変えて" in msg and "S02" in msg and "S03" in msg
    assert not (tmp_path / "final.html").exists()


def test_finalize_can_ignore_comments(tmp_path):
    make(tmp_path, {"01-A": "a1", "01-B": "b1", "02-A": "a2"})
    md = "## S01\n- 選択: B\n- コメント: メモ\n## S02\n- 選択: A\n- コメント: \n"
    assert variants.finalize(tmp_path, md, allow_comments=True).exists()
