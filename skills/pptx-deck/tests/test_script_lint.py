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
- 見出し: 現行基盤は2028年に保守が切れる
- 本文:
  - 保守期限は2028年3月
  - 運用負荷が年々増えている
- 出典: 社内資料（2026年9月）

## S03 比較
- layout: table
- 章名: 3案のどれを選ぶか
- 見出し: B案は3項目で最も釣り合っている
- 図表: 表/compare — 3案を項目ごとに並べるため
"""


def test_parse():
    s = script_lint.parse(OK)
    assert [x["id"] for x in s] == ["S01", "S02", "S03"]
    assert s[1]["fields"]["本文"] == ["保守期限は2028年3月", "運用負荷が年々増えている"]
    assert s[1]["fields"]["見出し"] == "現行基盤は2028年に保守が切れる"


def test_ok_has_no_problems():
    assert script_lint.lint(OK) == []


def test_lists_every_problem_at_once():           # Review Focus 4
    bad = OK.replace("## S02", "## S04").replace("- 見出し: B案は3項目で最も釣り合っている\n", "") \
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


def test_sample_script_is_valid():
    from pptx_deck import paths
    md = (paths.ASSETS / "sample" / "script.md").read_text(encoding="utf-8")
    assert script_lint.lint(md) == []
    assert len(script_lint.parse(md)) == 10
