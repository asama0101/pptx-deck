"""原稿（script.md）の検査 script_lint.lint。"""

# ruff: noqa: S101  # pytest の assert
import pytest
from pptx_deck import script_lint

HEAD = "導入により月次の集計作業が半分に縮むため、来期の人員計画を見直す必要がある"


def _script(head_block=f"- ヘッドメッセージ: {HEAD}", second="## S02 本文", third=""):
    return (
        "## S01 表紙\n- layout: cover\n- ヘッドメッセージ: 表紙のメッセージです\n\n"
        f"{second}\n- layout: content\n- 章名: 何が変わるか\n{head_block}\n- 本文:\n  - 要点\n\n{third}"
    )


def test_ヘッドメッセージをリストで書いても落ちずに指摘する():
    md = _script("- ヘッドメッセージ:\n  - 一行目\n  - 二行目")
    assert "S02: ヘッドメッセージは 1 行で書いてください（リストにしない）" in script_lint.lint(md)


def test_正しい原稿は指摘ゼロ():
    assert script_lint.lint(_script()) == []


@pytest.mark.parametrize("bad", ["### S01 表紙", "## S1 表紙"], ids=["見出しレベル違い", "番号が1桁"])
def test_見出しの書式違いを指摘する(bad):
    out = script_lint.lint(_script() + bad + "\n")
    assert f"見出しの書式が不正です: {bad!r}（`## S01 名前` の形にしてください）" in out


@pytest.mark.parametrize(
    ("second", "expected"),
    [
        ("## S03 本文", "S03: 番号が連番ではありません（2 番目は S02）"),
        ("## S01 本文", "S01: 番号が連番ではありません（2 番目は S02）"),
    ],
    ids=["欠番", "重複"],
)
def test_番号が連番でないとき指摘する(second, expected):
    assert expected in script_lint.lint(_script(second=second))


@pytest.mark.parametrize("layout", ["- layout:", "- layout:\n  - content"], ids=["空", "リスト"])
def test_layout_が文字列でなくても落ちずに指摘する(layout):
    md = (
        "## S01 表紙\n" + layout + "\n- ヘッドメッセージ: 表紙\n\n"
        "## S02 本文\n- layout:\n  - a\n- 章名: x\n- 本文:\n  - y\n"
    )
    out = script_lint.lint(md)
    assert any("layout が不正です" in o for o in out)
    assert script_lint.title_notes(md) == []


def test_3桁のスライド番号を2桁に読み違えない():
    out = script_lint.lint(_script() + "## S100 最後\n- layout: closing\n")
    assert any("S100" in o and "99" in o for o in out), out
    assert not any(o.startswith("S10:") for o in out), out
