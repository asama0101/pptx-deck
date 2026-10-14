import tempfile
import unittest
from pathlib import Path

from tests import _paths  # noqa: F401
from pptx_deck import variants


def touch(d: Path, *names):
    for n in names:
        (d / n).write_text("---\n---\n", encoding="utf-8")


class AnswerPathsTest(unittest.TestCase):
    def test_numeric_order_and_final_last(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            touch(d, "answers-10.md", "answers-2.md", "answers-1.md", "answers-final.md", "answers-plan-1.md", "other.md")
            self.assertEqual([p.name for p in variants.answer_paths(d)],
                             ["answers-1.md", "answers-2.md", "answers-10.md", "answers-final.md"])
            self.assertEqual([p.name for p in variants.answer_paths(d, upto=2)], ["answers-1.md", "answers-2.md"])
            self.assertEqual([p.name for p in variants.plan_answer_paths(d)], ["answers-plan-1.md"])
            self.assertEqual(variants.next_round(d), 11)

    def test_empty(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            self.assertEqual(variants.answer_paths(d), [])
            self.assertEqual(variants.next_round(d), 1)


MD1 = "---\n---\n## S01\n- 選択: B\n- デザイン: 2\n- 判定: 承認\n- コメント: \n## S02\n- 選択: A\n- 判定: 承認\n- コメント: 直して\n## S03\n- 選択: \n- 判定: 要修正\n- コメント: 違う\n"
MD2 = "---\n---\n## S03\n- 選択: A\n- 判定: 承認\n- コメント: \n## S01\n- 選択: \n- 判定: 要修正\n- コメント: \n"


class PresetTest(unittest.TestCase):
    def test_latest_verdict_wins_and_comments_block(self):
        self.assertEqual(variants.approved_preset([MD1]), {"01": {"c": "B", "d": 2, "v": "承認"}})
        got = variants.approved_preset([MD1, MD2])
        self.assertEqual(got, {"03": {"c": "A", "d": 1, "v": "承認"}})     # S01 は後の回で要修正、S02 はコメントあり

    def test_old_answers_without_verdict_count_as_approved(self):
        md = "---\n---\n## S04\n- 選択: C\n- コメント: \n"
        self.assertEqual(variants.approved_preset([md]), {"04": {"c": "C", "d": 1, "v": "承認"}})


if __name__ == "__main__":
    unittest.main()
