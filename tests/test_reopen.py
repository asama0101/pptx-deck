"""reopen（派生ファイルの再生成と PPTX の指紋の確認）、ensure_derived、build の指紋の記録。"""

# ruff: noqa: S101  # pytest の assert
from pathlib import Path

import pytest
from pptx_deck import check, cli, initdir, lifecycle, paths


@pytest.fixture
def work(tmp_path) -> Path:
    """init して断片と回答を置き、build 後の状態（派生ファイルを prune した状態）にした作業フォルダ。"""
    base = tmp_path / "out" / "pptx-deck-source" / "deck"
    initdir.init(base, color="navy")
    w = paths.resolve_work(base)
    (w / "slides" / "01-A.html").write_text("<section class='slide'></section>", encoding="utf-8")
    (w / "answers-1.md").write_text("---\n---\n", encoding="utf-8")
    (w / "answers-final.md").write_text("---\n---\n", encoding="utf-8")
    lifecycle.prune(w)
    return w


def _built_pptx(work: Path, content: bytes = b"v1") -> Path:
    pptx = paths.deck_dir(work) / "deck.pptx"
    pptx.write_bytes(content)
    lifecycle.record_build(work, pptx)
    return pptx


def test_reopenは派生ファイルを再生成し_回答と次の回を返す(work):
    assert not (work / "theme.css").exists()
    _built_pptx(work)
    r = lifecycle.reopen(work)
    assert r["status"] == "ok"
    assert (work / "theme.css").exists()
    assert (work / "base.css").exists()
    assert (work / "icons").is_dir()
    assert [Path(a).name for a in r["answers"]] == ["answers-1.md", "answers-final.md"]
    assert r["next_round"] == 2
    assert r["slides"] == 1


def test_reopenはPPTXが手直しされていたら_modified_を返す(work):
    pptx = _built_pptx(work)
    pptx.write_bytes("v1 + 手直し".encode())
    assert lifecycle.reopen(work)["status"] == "modified"


def test_reopenはPPTXがなければ_missing_pptx_を返す(work):
    assert lifecycle.reopen(work)["status"] == "missing_pptx"


def test_ensure_derivedは_prune_のあとに再生成し_2回目は何もしない(work):
    assert lifecycle.ensure_derived(work) is True
    assert (work / "theme.css").exists()
    assert (work / "base.css").exists()
    assert (work / "icons").is_dir()
    assert lifecycle.ensure_derived(work) is False


@pytest.mark.slow
def test_PPTXの検査が失敗しても_build_json_を残し_派生ファイルは消さない(work, monkeypatch, tmp_path, capsys):
    """実際にブラウザで測って PPTX を書く。PPTX 側の検査（check_pptx）だけが落ちるよう、
    PPTX の文字の下限（定数 MIN_PT_SMALL）を本文の 15pt より上に上げる（測定側の検査は通る）。"""
    monkeypatch.setattr("tempfile.tempdir", str(tmp_path / "tmp"))  # 確認用の画像の置き場を tmp_path の下にする
    (tmp_path / "tmp").mkdir()
    monkeypatch.setattr(check, "MIN_PT_SMALL", 20)
    (work / "final.html").write_text(
        '<!doctype html><html lang="ja"><head><meta charset="utf-8">'
        '<link rel="stylesheet" href="theme.css"><link rel="stylesheet" href="base.css"></head><body>'
        '<section class="slide" data-layout="content">'
        '<div class="pp-text" data-role="title" style="position:absolute;left:80px;top:40px;width:800px;height:60px;'
        'font-size:32px">題</div>'
        '<div class="pp-text" style="position:absolute;left:80px;top:200px;width:600px;height:60px;font-size:20px">'
        "本文</div>"
        "</section></body></html>",
        encoding="utf-8",
    )
    out = paths.deck_dir(work) / f"{paths.deck_name(work)}.pptx"

    rc = cli.main(["build", str(work)])

    out_text = capsys.readouterr().out
    assert rc == 1
    assert '"rule": "pptxFontMin"' in out_text  # 落ちた理由は PPTX 側の検査
    assert out.exists()
    assert (work / "build.json").exists()
    assert lifecycle.fingerprint_status(work, out) == "unchanged"
    assert (work / "slides").is_dir()  # ok でないので prune されない
    assert (work / "final.html").exists()
