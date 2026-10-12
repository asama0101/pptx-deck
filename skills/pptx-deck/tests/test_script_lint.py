import pytest

from pptx_deck import script_lint

OK = """# クラウド移行
- 目的: 承認を得る
- 対象: 経営会議
- 配色: navy

## S01 表紙
- layout: cover
- 見出し: クラウド基盤への移行を承認いただきたい
- 副題: 3案の比較

## S02 背景
- layout: content
- 章名: なぜ今、移行を決める必要があるのか
- 見出し: 現行基盤は2028年に保守が切れるため、今期中に移行先を決める必要がある
- 本文:
  - 保守期限は2028年3月
  - 運用負荷が年々増えている
- 出典: 社内資料（2026年9月）

## S03 比較
- layout: table
- 章名: 3案のどれを選ぶか
- 見出し: B案は費用・期間・リスクの3項目で最も釣り合っているため、採用に値する
- 図表: 表/compare — 3案を項目ごとに並べるため
"""


def test_parse():
    s = script_lint.parse(OK)
    assert [x["id"] for x in s] == ["S01", "S02", "S03"]
    assert s[1]["fields"]["本文"] == ["保守期限は2028年3月", "運用負荷が年々増えている"]
    assert s[1]["fields"]["見出し"] == "現行基盤は2028年に保守が切れるため、今期中に移行先を決める必要がある"


def test_ok_has_no_problems():
    assert script_lint.lint(OK) == []


def test_lists_every_problem_at_once():           # Review Focus 4
    bad = OK.replace("## S02", "## S04").replace("- 見出し: B案は費用・期間・リスクの3項目で最も釣り合っているため、採用に値する\n", "") \
            .replace("- layout: cover", "- layout: banner")
    got = "\n".join(script_lint.lint(bad))
    assert "S04" in got and "連番" in got
    assert "S03" in got and "見出し" in got
    assert "banner" in got


def test_first_must_be_cover():
    md = OK.replace("- layout: cover", "- layout: content")
    assert any("表紙" in p for p in script_lint.lint(md))


def test_diagram_needs_figure_field():
    md = OK.replace("- 図表: 表/compare — 3案を項目ごとに並べるため\n", "- 本文:\n  - 要点\n")
    assert any("図表" in p for p in script_lint.lint(md))


def test_bad_color():
    assert any("配色" in p for p in script_lint.lint(OK.replace("- 配色: navy", "- 配色: red")))


def test_empty_script():
    assert script_lint.lint("") == ["スライド（## S01 …）がありません"]


def test_malformed_slide_headings_are_reported():
    for bad_heading in ("## S1 背景", "### S02 背景", "##S02 背景", "## s02 背景"):
        md = OK + f"\n{bad_heading}\n- layout: content\n- 見出し: x\n"
        got = "\n".join(script_lint.lint(md))
        assert "見出しの書式" in got and bad_heading in got, bad_heading


@pytest.mark.xfail(reason="Task 7 で置き換え")
def test_sample_script_is_valid():
    from pptx_deck import paths
    md = (paths.ASSETS / "sample" / "script.md").read_text(encoding="utf-8")
    assert script_lint.lint(md) == []
    assert len(script_lint.parse(md)) == 10


BODY = "\n## S02 背景\n- layout: content\n- 章名: なぜか\n- 見出し: {head}\n- 本文:\n  - 要点\n"
HEAD = "# 題\n- 目的: x\n- 対象: y\n\n## S01 表紙\n- layout: cover\n- 見出し: 題\n"


def lint_head(head):
    return "\n".join(script_lint.lint(HEAD + BODY.format(head=head)))


def test_good_head_passes():
    assert lint_head("削減で生む原資が成長投資を支えるため、4件は一括での承認が必要だ") == ""


@pytest.mark.parametrize("head,word", [
    ("コストの分析", "判断"),                                                  # 題名であって主張ではない（判断語・接続語がない）
    ("費用は1.7億円。A案より低い", "二段"),
    ("本ページでは費用を比較し、B案が最も安いと判断すべきだ", "自己言及"),
    ("B案は——費用が最も低く、採用すべきだ", "ダッシュ"),
    ("短いため、採用すべきだ", "字数"),
    ("費用が高いため、" + "あ" * 60 + "べきだ", "字数"),
])
def test_bad_heads(head, word):
    assert word in lint_head(head)


def test_cover_section_closing_are_exempt():
    md = HEAD + "\n## S02 章\n- layout: section\n- 章名: x\n- 見出し: 背景\n- 本文:\n  - a\n\n## S03 結び\n- layout: closing\n- 見出し: 以上\n"
    assert script_lint.lint(md) == []


def test_empty_head_is_reported_once():
    got = script_lint.lint(HEAD + BODY.format(head=""))
    assert sum("見出し" in g for g in got) == 1


def test_three_same_type_in_a_row():
    md = HEAD
    for i, h in enumerate(["A案は費用が低いため、採用に値する案だと言える", "B案は期間が短いため、採用に値する案だと言える", "C案は停止が少ないため、採用に値する案だと言える"], start=2):
        md += BODY.format(head=h).replace("S02", f"S{i:02d}")
    assert "文型" in "\n".join(script_lint.lint(md))


def test_sentence_type():
    assert script_lint.sentence_type("費用が低いため、B案を採る") == "因果"
    assert script_lint.sentence_type("承認すれば、着手できる") == "条件"
    assert script_lint.sentence_type("伸びは首位だが、問題は増分にある") == "逆接"
    assert script_lint.sentence_type("集中させるべきだ") == "提言"


def test_issue_count_is_checked_only_when_written():
    ok = "# 題\n- 目的: x\n- 対象: y\n- 論点:\n  - ①a\n  - ②b\n  - ③c\n\n## S01 表紙\n- layout: cover\n- 見出し: 題\n"
    assert script_lint.lint(ok) == []
    two = ok.replace("  - ③c\n", "")
    assert "論点" in "\n".join(script_lint.lint(two))
    assert script_lint.lint(HEAD) == []                  # 書かなければ検査しない

