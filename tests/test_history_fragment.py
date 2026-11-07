# ruff: noqa: S101
"""断片 1 つ単位の履歴（snapshot_fragment / restore_fragment / latest_ai_edit）。"""

import pytest
from pptx_deck import history


@pytest.fixture
def work(tmp_path):
    slides = tmp_path / "slides"
    slides.mkdir()
    (slides / "02-A.html").write_text("A-元", encoding="utf-8")
    (slides / "02-B.html").write_text("B-元", encoding="utf-8")
    return tmp_path


def _read(work, name):
    return (work / "slides" / name).read_text(encoding="utf-8")


def test_断片1つだけが戻り別の断片は触らない(work):
    v = history.snapshot_fragment(work, "02-A")["version"]
    (work / "slides" / "02-A.html").write_text("A-新", encoding="utf-8")
    (work / "slides" / "02-B.html").write_text("B-新", encoding="utf-8")
    r = history.restore_fragment(work, v, "02-A")
    assert _read(work, "02-A.html") == "A-元"
    assert _read(work, "02-B.html") == "B-新"
    assert r["restored_version"] == v
    assert r["restored"] == ["02-A.html"]


def test_戻す前の状態も版として残る(work):
    v = history.snapshot_fragment(work, "02-A")["version"]
    r = history.restore_fragment(work, v, "02-A")
    labels = {x["version"]: x["label"] for x in history.versions(work)}
    assert labels[r["saved_as"]] == f"before-restore-{v}-02-A"


def test_保持は最新の5版まで(work):
    history.snapshot_fragment(work, "02-B")
    for _ in range(7):
        history.snapshot_fragment(work, "02-A")
    vs = history.versions(work)
    a = [x["version"] for x in vs if x["label"] == "ai-edit-02-A"]
    assert len(a) == 5
    assert a == [4, 5, 6, 7, 8]
    assert len([x for x in vs if x["label"] == "ai-edit-02-B"]) == 1


def test_不正な断片名と無い断片はエラー(work):
    v = history.snapshot_fragment(work, "02-A")["version"]
    with pytest.raises(ValueError, match="断片名の形"):
        history.snapshot_fragment(work, "x")
    with pytest.raises(ValueError, match="がありません"):
        history.snapshot_fragment(work, "09-A")
    with pytest.raises(ValueError, match="がありません"):
        history.restore_fragment(work, v, "03-A")


def test_最新のai編集の版を返す(work):
    assert history.latest_ai_edit(work, "02-A") is None
    for _ in range(3):
        last = history.snapshot_fragment(work, "02-A")["version"]
    assert history.latest_ai_edit(work, "02-A")["version"] == last
