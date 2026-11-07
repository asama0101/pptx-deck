"""回答の文字サイズの解析・finalize への反映・set-font-size。"""

# ruff: noqa: S101  # pytest の assert
import json
from types import SimpleNamespace

import pytest
from pptx_deck import cli, initdir, variants

MD_HEAD = "---\nround: 1\n---\n"


def cfg(work):
    return json.loads((work / "template.json").read_text(encoding="utf-8"))


def css(work):
    return (work / "theme.css").read_text(encoding="utf-8")


@pytest.fixture
def deck(tmp_path):
    base = tmp_path / "out" / "pptx-deck-source" / "deck"
    initdir.init(base, color="navy")
    (base / "slides" / "01-A.html").write_text('<div class="pp-text">x</div>', encoding="utf-8")

    def answers(n, line):
        md = f"---\nround: {n}\n---\n{line}\n## S01\n- 選択: A\n- 判定: 承認\n"
        (base / f"answers-{n}.md").write_text(md, encoding="utf-8")

    return SimpleNamespace(base=base, answers=answers, pptx=base.parent.parent / "deck.pptx")


@pytest.fixture
def run(deck, capsys):
    def _run(*argv, expect=0):
        capsys.readouterr()
        rc = cli.main([argv[0], str(deck.base), *argv[1:]])
        err = capsys.readouterr().err
        assert rc == expect, err
        return err

    return _run


def test_parse_settings_fontsizes():
    mds = [MD_HEAD + "- 文字サイズ: title=40 body=20 nope=3\n", MD_HEAD + "- 文字サイズ: title=44 lead=x\n"]
    assert variants.parse_settings(mds)["fontsizes"] == {"title": 44, "body": 20}


def test_finalize_applies(deck, run):
    deck.answers(1, "- 文字サイズ: title=40")
    err = run("finalize")
    assert cfg(deck.base)["fontsizes"] == {"title": 40}
    assert "--fs-title: 40px;" in css(deck.base)
    assert "文字サイズ" in err


def test_finalize_clamps(deck, run):
    deck.answers(1, "- 文字サイズ: title=99 body=5")
    run("finalize")
    assert cfg(deck.base)["fontsizes"] == {"title": 60}  # body=5 は 19 に丸まり既定と同じなので外れる


def test_finalize_skips_when_pptx_exists(deck, run):
    deck.answers(1, "- 文字サイズ: title=40")
    before = css(deck.base)
    deck.pptx.write_bytes(b"dummy")
    err = run("finalize")
    assert css(deck.base) == before
    assert "set-font-size" in err
    assert "set-font-size" not in run("finalize")  # 同じ警告は繰り返さない


def test_set_font_size_not_reverted_by_old_answers(deck, run):
    deck.answers(1, "- 文字サイズ: title=40")
    run("finalize")
    run("set-font-size", "--set", "title=45")
    run("finalize")
    assert cfg(deck.base)["fontsizes"] == {"title": 45}


def test_set_font_size_cli_errors(deck, run):
    run("set-font-size", "--set", "title=40")
    before = css(deck.base)
    run("set-font-size", "--set", "nope=1", expect=2)
    run("set-font-size", "--set", "title=abc", expect=2)
    run("set-font-size", "--set", "title", expect=2)
    assert css(deck.base) == before
    assert cfg(deck.base)["fontsizes"] == {"title": 40}
    run("set-font-size", "--reset")
    assert "fontsizes" not in cfg(deck.base)


def test_initdir_set_font_size_unknown_key(deck):
    with pytest.raises(ValueError, match="nope"):
        initdir.set_font_size(deck.base, {"nope": 1})
