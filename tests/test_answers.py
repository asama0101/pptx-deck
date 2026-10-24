"""回答 md（answers-N.md）の並び順・読み込み・統合（variants）。"""

# ruff: noqa: S101  # pytest の assert
from pathlib import Path

import pytest
from pptx_deck import variants

EMPTY = "---\n---\n"

MD1 = (
    "---\n---\n## S01\n- 選択: B\n- デザイン: 2\n- 判定: 承認\n- コメント: \n"
    "## S02\n- 選択: A\n- 判定: 承認\n- コメント: 直して\n"
    "## S03\n- 選択: \n- 判定: 要修正\n- コメント: 違う\n"
)
MD2 = "---\n---\n## S03\n- 選択: A\n- 判定: 承認\n- コメント: \n## S01\n- 選択: \n- 判定: 要修正\n- コメント: \n"
R1_OK = "---\n---\n## S02\n- 選択: A\n- 判定: 承認\n- コメント: \n"
R2_FIX = "---\n---\n## S02\n- 選択: \n- 判定: 要修正\n- コメント: どの案でもない。作り直してほしい\n"
FIX_COMMENT = "どの案でもない。作り直してほしい"


def touch(d: Path, *names):
    for n in names:
        (d / n).write_text(EMPTY, encoding="utf-8")


def test_回答ファイルは番号順で_finalが最後_planは別扱い(tmp_path):
    touch(
        tmp_path, "answers-10.md", "answers-2.md", "answers-1.md", "answers-final.md", "answers-plan-1.md", "other.md"
    )
    assert [p.name for p in variants.answer_paths(tmp_path)] == [
        "answers-1.md",
        "answers-2.md",
        "answers-10.md",
        "answers-final.md",
    ]
    assert [p.name for p in variants.answer_paths(tmp_path, upto=2)] == ["answers-1.md", "answers-2.md"]
    assert [p.name for p in variants.plan_answer_paths(tmp_path)] == ["answers-plan-1.md"]
    assert variants.next_round(tmp_path) == 11


def test_回答がないとき_一覧は空で次の回は1(tmp_path):
    assert variants.answer_paths(tmp_path) == []
    assert variants.next_round(tmp_path) == 1


def test_あとの回の判定が勝ち_コメントのある承認は事前選択しない():
    assert variants.approved_preset([MD1]) == {"01": {"c": "B", "d": 2, "v": "承認"}}
    # S01 は後の回で要修正、S02 はコメントあり、S03 は後の回で承認
    assert variants.approved_preset([MD1, MD2]) == {"03": {"c": "A", "d": 1, "v": "承認"}}


def test_判定の行がない古い回答は承認として数える():
    md = "---\n---\n## S04\n- 選択: C\n- コメント: \n"
    assert variants.approved_preset([md]) == {"04": {"c": "C", "d": 1, "v": "承認"}}


def test_あとの回が選択なしの要修正なら事前選択しない():
    assert variants.approved_preset([R1_OK, R2_FIX]) == {}


@pytest.mark.parametrize(
    ("r2", "expected"),
    [
        ("---\n---\n## S01\n- 選択: C\n- 判定: 承認\n- コメント: \n", {"01": {"c": "C", "d": 1, "v": "承認"}}),
        ("---\n---\n## S01\n- 選択: \n- 判定: 承認\n- コメント: \n", {"01": {"c": "B", "d": 3, "v": "承認"}}),
    ],
    ids=["別の案に変えたらデザインを引き継がない", "判定だけ変えたらデザインを保つ"],
)
def test_デザインは同じ案のときだけ引き継ぐ(r2, expected):
    r1 = "---\n---\n## S01\n- 選択: B\n- デザイン: 3\n- 判定: 承認\n- コメント: \n"
    assert variants.approved_preset([r1, r2]) == expected


def test_あとの回の選択なし要修正が前の承認を上書きする():
    a = variants.merge_answers([R1_OK, R2_FIX])["02"]
    assert (a["choice"], a.get("verdict"), a["comment"]) == ("", "要修正", FIX_COMMENT)


@pytest.mark.parametrize(
    "later",
    [
        "---\n---\n## S02\n- 選択: \n- コメント: \n",
        "---\n---\n## S02\n- 選択: \n- 判定: \n- コメント: \n",
    ],
    ids=["判定の行なし_古い形式", "判定が空"],
)
def test_未回答の節は前の選択を消さない(later):
    a = variants.merge_answers([R1_OK, later])["02"]
    assert (a["choice"], a.get("verdict")) == ("A", "承認")


def test_あとの回の選択つき承認が前の要修正を上書きする():
    a = variants.merge_answers([R2_FIX, "---\n---\n## S02\n- 選択: B\n- 判定: 承認\n- コメント: \n"])["02"]
    assert (a["choice"], a.get("verdict"), a["comment"]) == ("B", "承認", "")


def test_未回答のスライドの要修正はそのまま残る():
    a = variants.merge_answers([R2_FIX])["02"]
    assert (a["choice"], a.get("verdict"), a["comment"]) == ("", "要修正", FIX_COMMENT)
