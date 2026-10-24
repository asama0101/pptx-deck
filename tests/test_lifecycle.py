"""PPTX の指紋（build.json）と、派生ファイルの整理（prune）。"""

# ruff: noqa: S101  # pytest の assert
import json
import os
import time

from pptx_deck import lifecycle


def test_指紋の状態は_missing_unrecorded_unchanged_modified_の順に変わる(tmp_path):
    work = tmp_path / "source"
    work.mkdir()
    pptx = tmp_path / "deck.pptx"
    assert lifecycle.fingerprint_status(work, pptx) == "missing"
    pptx.write_bytes(b"v1")
    assert lifecycle.fingerprint_status(work, pptx) == "unrecorded"
    lifecycle.record_build(work, pptx)
    assert lifecycle.fingerprint_status(work, pptx) == "unchanged"
    pptx.write_bytes(b"v1-edited")
    assert lifecycle.fingerprint_status(work, pptx) == "modified"
    assert json.loads((work / "build.json").read_text(encoding="utf-8"))["pptx"] == "deck.pptx"


def test_pruneは既知の派生ファイルだけを消す(tmp_path):
    w = tmp_path
    for n in lifecycle.DERIVED_FILES:
        (w / n).write_text("x", encoding="utf-8")
    (w / "icons").mkdir()
    (w / "icons" / "a.svg").write_text("x", encoding="utf-8")
    (w / "_template").mkdir()
    (w / "_template" / "template.potx").write_bytes(b"t")
    for keep in (
        "design.md",
        "script.md",
        "template.json",
        "build.json",
        "answers-1.md",
        "round-2-notes.md",
        "素材メモ.md",
    ):
        (w / keep).write_text("k", encoding="utf-8")
    (w / "slides").mkdir()
    (w / "slides" / "01-A.html").write_text("s", encoding="utf-8")
    removed = lifecycle.prune(w)
    assert "final.html" in removed
    assert "icons" in removed
    assert sorted(p.name for p in w.iterdir()) == sorted(
        [
            "_template",
            "answers-1.md",
            "build.json",
            "design.md",
            "round-2-notes.md",
            "script.md",
            "slides",
            "template.json",
            "素材メモ.md",
        ]
    )
    assert [p.name for p in (w / "_template").iterdir()] == ["template.potx"]
    assert (w / "slides" / "01-A.html").read_text(encoding="utf-8") == "s"


def test_古い_draft_html_だけ消し_draft_で始まる_md_は残す(tmp_path):
    w = tmp_path
    (w / "draft-abc123.html").write_text("x", encoding="utf-8")
    old = time.time() - 3600
    os.utime(w / "draft-abc123.html", (old, old))
    (w / "draft-notes.md").write_text("k", encoding="utf-8")
    assert lifecycle.prune(w) == ["draft-abc123.html"]
    assert (w / "draft-notes.md").exists()


def test_10分以内の_draft_html_は残す(tmp_path):
    """束 F4 #13: 別のエージェントが使っているかもしれない。"""
    w = tmp_path
    (w / "draft-new.html").write_text("x", encoding="utf-8")
    (w / "draft-old.html").write_text("x", encoding="utf-8")
    old = time.time() - 11 * 60
    os.utime(w / "draft-old.html", (old, old))
    assert lifecycle.prune(w) == ["draft-old.html"]
    assert (w / "draft-new.html").exists()
    assert not (w / "draft-old.html").exists()


def test_空のフォルダをpruneしても何も消えず落ちない(tmp_path):
    assert lifecycle.prune(tmp_path) == []
