"""前の回で選んだ文字サイズの引き継ぎ、古い theme.css の補い、メッセージ（Chromium なし）。"""

# ruff: noqa: S101  # pytest の assert
import json
import re

import pytest
from pptx_deck import cli, initdir, lifecycle, paths, variants

FRAG = (
    '<section class="slide" data-layout="content" data-variant="{n}｜理由" style="width:1280px;height:720px"></section>'
)
R1 = "---\nround: 1\n---\n- 文字サイズ: title=45\n## S01\n- 選択: A\n- 判定: 承認\n"


@pytest.fixture
def work(tmp_path):
    w = tmp_path / "out" / "pptx-deck-source" / "deck"
    initdir.init(w, color="navy")
    (w / "slides" / "01-A.html").write_text(FRAG.replace("{n}", "a"), encoding="utf-8")
    return w


def attr(html: str, key: str, name: str) -> str:
    m = re.search(rf'<input[^>]*data-fs="{key}"[^>]*', html)
    assert m
    return re.search(rf'{name}="([^"]*)"', m.group(0)).group(1)


def page(work, round_no=2):
    return variants.assemble(work, round_no).read_text(encoding="utf-8")


def test_前の回で選んだ文字サイズが次の回の初期値になる(work):
    (work / "answers-1.md").write_text(R1, encoding="utf-8")
    html = page(work)
    assert attr(html, "title", "value") == "45"
    assert attr(html, "title", "data-init") == "45"
    assert attr(html, "title", "data-tpl") == "37"  # theme.css の値。違うので読み込み時に反映する
    assert attr(html, "body", "data-init") == "19"


def test_反映済みの回答の文字サイズは重ねない(work):
    (work / "answers-1.md").write_text(R1, encoding="utf-8")
    initdir.set_font_size(work, {"title": 40})
    cfg = paths.read_cfg(work)
    cfg["answers_fontsizes"] = {"title": [45, "answers-1.md"]}
    paths.write_cfg(work, cfg)
    html = page(work)
    assert attr(html, "title", "data-init") == "40"


def test_別の回答ファイルが書いた同じ値は未反映として重ねる(work):
    (work / "answers-1.md").write_text(R1, encoding="utf-8")
    cfg = paths.read_cfg(work)
    cfg["answers_fontsizes"] = {"title": [45, "answers-0.md"]}
    paths.write_cfg(work, cfg)
    assert attr(page(work), "title", "data-init") == "45"


def test_theme_cssに文字サイズの変数がなければensure_derivedが作り直す(work):
    css = work / "theme.css"
    css.write_text(
        re.sub(r"^.*--(fs|num|chart)-.*\n", "", css.read_text(encoding="utf-8"), flags=re.M), encoding="utf-8"
    )
    assert "--fs-title" not in css.read_text(encoding="utf-8")
    assert lifecycle.ensure_derived(work) is True
    assert "--fs-title" in css.read_text(encoding="utf-8")
    assert lifecycle.ensure_derived(work) is False


def test_set_font_sizeとset_colorのメッセージはfinalizeからbuildを案内する(work, capsys):
    assert cli.main(["set-font-size", str(work), "--set", "title=40"]) == 0
    assert "finalize" in capsys.readouterr().out
    assert cli.main(["set-color", str(work), "green"]) == 0
    assert "finalize" in capsys.readouterr().out
    json.loads((work / "template.json").read_text(encoding="utf-8"))
