# ruff: noqa: S101  # pytest の assert
import json
from collections import namedtuple

import pytest
from pptx_deck import cli

EDIT_MD = '# 回答\n## S01\n- 編集: {"f":"01-A","t":"t0","before":"旧","after":"新"}\n'
SKIP_LINE = '- 編集: {"f":"09-Z","t":"t0","before":"a","after":"b"}\n'

Deck = namedtuple("Deck", "deck work frag")


@pytest.fixture
def run(capsys):
    def _run(*argv):
        capsys.readouterr()
        code = cli.main(list(argv))
        cap = capsys.readouterr()
        return code, cap.out, cap.err

    return _run


@pytest.fixture
def d(tmp_path, run):
    deck = tmp_path / "デッキ"
    work = deck / "source"
    code, _, err = run("init", str(deck))  # build は template.json を先に読む
    assert code == 0, err
    (work / "slides").mkdir(exist_ok=True)
    frag = work / "slides" / "01-A.html"
    frag.write_text('<div class="pp-text">旧</div>', encoding="utf-8")
    (work / "final.html").write_text("<html></html>", encoding="utf-8")
    (work / "answers-1.md").write_text(EDIT_MD, encoding="utf-8")
    return Deck(deck, work, frag)


def read(p):
    return p.read_text(encoding="utf-8")


@pytest.mark.parametrize("cmd", ["finalize", "review-final", "build"])
def test_未反映の編集があると_apply_edits_を案内して止まる(d, run, cmd):
    code, _, err = run(cmd, str(d.deck))
    assert code == 2
    assert "apply-edits" in err
    assert "answers-1.md" in err
    assert read(d.frag) == '<div class="pp-text">旧</div>'


def test_variants_も未反映の編集で止まる(d, run):
    code, _, err = run("variants", str(d.deck))
    assert code == 2
    assert "apply-edits" in err
    assert not (d.work / "variants.html").exists()


def test_apply_edits_は断片を書き換え_final_html_を消して_止めていたものを外す(d, run):
    code, out, err = run("apply-edits", str(d.deck))
    assert code == 0, err
    assert read(d.frag) == '<div class="pp-text">新</div>'
    res = json.loads(out)
    assert len(res) == 1
    assert res[0]["answers"] == "answers-1.md"
    assert len(res[0]["applied"]) == 1
    assert "finalize" in err
    assert not (d.work / "final.html").exists()
    code, _, err = run("build", str(d.deck))
    assert code == 2
    assert "final.html がありません" in err  # 編集の未反映では止まらなくなった


def test_反映済みの編集が1つもないとき_apply_edits_は空の結果を返しガードも外れる(d, run):
    (d.work / "answers-1.md").write_text("# 回答\n", encoding="utf-8")
    code, out, _ = run("apply-edits", str(d.deck))
    assert code == 0
    assert json.loads(out) == {"applied": []}
    code, _, err = run("variants", str(d.deck))
    assert code == 0, err


def test_answers_を指定すると_そのファイルの編集を反映する(d, run):
    other = d.work / "memo.md"
    other.write_text(EDIT_MD, encoding="utf-8")
    (d.work / "answers-1.md").write_text("# 回答\n", encoding="utf-8")
    code, out, _ = run("apply-edits", str(d.deck), "--answers", str(other))
    assert code == 0
    assert json.loads(out)[0]["answers"] == "memo.md"
    assert read(d.frag) == '<div class="pp-text">新</div>'


def test_すべて読み飛ばされると報告して終了コード1で止め_以後は止め続けない(d, run):
    (d.work / "answers-1.md").write_text(
        '## S01\n- 編集: {"f":"09-Z","t":"t0","before":"a","after":"b"}\n', encoding="utf-8"
    )
    code, out, err = run("apply-edits", str(d.deck))
    assert code == 1
    assert "09-Z" in err
    assert "answers-1.md" in err
    assert read(d.frag) == '<div class="pp-text">旧</div>'
    assert json.loads(out)[0]["applied"] == []
    code, _, err = run("variants", str(d.deck))  # 知らせたので、止め続けない
    assert code == 0, err


def test_読めない行だけのときは終了コード1で報告し_繰り返し止めない(d, run):
    (d.work / "answers-1.md").write_text("## S01\n- 編集: {壊れ\n", encoding="utf-8")
    code, _, err = run("apply-edits", str(d.deck))
    assert code == 1
    assert "answers-1.md" in err
    assert "読めません" in err
    code, _, err = run("variants", str(d.deck))
    assert code == 0, err
    code, out, _ = run("apply-edits", str(d.deck))
    assert code == 0
    assert json.loads(out) == {"applied": []}


def test_反映できる編集とできない編集が混ざると_反映して終了コード1になる(d, run):
    (d.work / "answers-1.md").write_text(EDIT_MD + SKIP_LINE, encoding="utf-8")
    code, _, err = run("apply-edits", str(d.deck))
    assert code == 1
    assert read(d.frag) == '<div class="pp-text">新</div>'
    assert "09-Z" in err
