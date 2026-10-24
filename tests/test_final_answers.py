"""answers-final.md（最終確認の回答）は、finalize / review-final の案の決定に使わない。"""

# ruff: noqa: S101  # pytest の assert
import re
from collections import namedtuple

import pytest
from pptx_deck import cli, initdir, paths, variants

FINAL_OK = "---\n---\n## S01\n- 選択: A\n- 判定: 承認\n- コメント: \n## S02\n- 選択: A\n- 判定: 承認\n- コメント: \n"
FINAL_FIX = (
    "---\n---\n## S01\n- 選択: A\n- 判定: 承認\n- コメント: \n## S02\n- 選択: FIX\n- 判定: 要修正\n- コメント: 直す\n"
)
ANS1 = (
    "---\n---\n## S01\n- 選択: B\n- デザイン: 2\n- 判定: 承認\n- コメント: \n"
    "## S02\n- 選択: A\n- 判定: 承認\n- コメント: \n"
)
FIX_NO_CHOICE = "---\n---\n## S02\n- 選択: \n- 判定: 要修正\n- コメント: どの案でもない。作り直してほしい\n"
FIX_MSG = "S02: 要修正です。直してから再提示してください: どの案でもない。作り直してほしい"

Deck = namedtuple("Deck", "base work")


def read(p):
    return p.read_text(encoding="utf-8")


@pytest.fixture
def run(capsys):
    def _run(*argv):
        capsys.readouterr()
        rc = cli.main(list(argv))
        cap = capsys.readouterr()
        return rc, cap.out, cap.err

    return _run


@pytest.fixture
def deck(tmp_path):
    base = tmp_path / "demo"
    initdir.init(base, color="navy")
    work = paths.resolve_work(base)
    s = work / "slides"
    (s / "01-A.html").write_text("<section>MARK-1A</section>", encoding="utf-8")
    (s / "01-B.html").write_text("<section>MARK-1B</section>", encoding="utf-8")
    (s / "01-B-d2.html").write_text("<section>MARK-1B2</section>", encoding="utf-8")
    (s / "02-A.html").write_text("<section>MARK-2A</section>", encoding="utf-8")
    (work / "answers-1.md").write_text(ANS1, encoding="utf-8")
    return Deck(base, work)


def test_最終確認の承認は案の選択を上書きしない(deck, run):
    (deck.work / "answers-final.md").write_text(FINAL_OK, encoding="utf-8")
    assert run("finalize", str(deck.base))[0] == 0
    html = read(deck.work / "final.html")
    assert "MARK-1B2" in html
    assert "MARK-1A" not in html


def test_最終確認の要修正は_finalize_も_review_final_も止めない(deck, run):
    (deck.work / "answers-final.md").write_text(FINAL_FIX, encoding="utf-8")
    rc, _, err = run("finalize", str(deck.base))
    assert rc == 0, err
    assert "MARK-1B2" in read(deck.work / "final.html")
    (deck.work / "final-review.html").unlink()
    rc, _, err = run("review-final", str(deck.base))
    assert rc == 0, err
    assert "MARK-1B2" in read(deck.work / "final-review.html")


def test_回答の一覧は最終確認を含めるかどうかを選べる(deck):
    (deck.work / "answers-final.md").write_text(FINAL_OK, encoding="utf-8")
    assert [p.name for p in variants.answer_paths(deck.work)] == ["answers-1.md", "answers-final.md"]
    assert [p.name for p in variants.answer_paths(deck.work, include_final=False)] == ["answers-1.md"]


def test_前回の最終確認で承認したスライドだけが_選択済みで開く(deck, run):
    (deck.work / "answers-final.md").write_text(FINAL_FIX, encoding="utf-8")
    assert run("finalize", str(deck.base))[0] == 0
    page = read(deck.work / "final-review.html")
    assert '"01": {"c": "A"' in page  # 前回の最終確認で承認した S01 は選択済み
    assert '"02": {"c"' not in page  # 要修正の S02 は選択済みにしない


def test_後の回の回答は古い最終確認より優先される(deck, run):
    (deck.work / "answers-final.md").write_text(FINAL_OK, encoding="utf-8")
    (deck.work / "answers-2.md").write_text(
        "---\n---\n## S01\n- 選択: B\n- デザイン: 1\n- 判定: 承認\n- コメント: \n", encoding="utf-8"
    )
    assert run("finalize", str(deck.base))[0] == 0
    html = read(deck.work / "final.html")
    assert "MARK-1B</section>" in html
    assert "MARK-1B2" not in html
    assert "MARK-1A" not in html


# 後の回の「要修正（案なし）」は、前の回の承認を上書きして finalize を止める。


def test_後の回の要修正は_コメントつきで報告され_承認済みのスライドは含まない(deck):
    with pytest.raises(ValueError, match=re.escape(FIX_MSG)) as cm:
        variants.finalize(deck.work, [ANS1, FIX_NO_CHOICE])
    assert FIX_MSG in str(cm.value)
    assert "S01" not in str(cm.value)


def test_前の回に回答がないスライドの要修正も_コメントつきで報告される(deck):
    ans1_s01 = ANS1.split("## S02")[0]
    with pytest.raises(ValueError, match=re.escape(FIX_MSG)) as cm:
        variants.finalize(deck.work, [ans1_s01, FIX_NO_CHOICE])
    assert FIX_MSG in str(cm.value)


def test_cli_の_finalize_は後の回の要修正で終了コード2で止まる(deck, run):
    (deck.work / "answers-2.md").write_text(FIX_NO_CHOICE, encoding="utf-8")
    rc, _, err = run("finalize", str(deck.base))
    assert rc == 2
    assert "S02: 要修正です" in err
    assert "どの案でもない。作り直してほしい" in err
    assert not (deck.work / "final.html").exists()
