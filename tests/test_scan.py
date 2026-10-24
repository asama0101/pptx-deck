"""開始ページの事前スキャン（scan）と、最近使った場所の記録。"""

# ruff: noqa: S101  # pytest の assert
import json
import subprocess
from pathlib import Path

import pytest
from pptx_deck import scan


def _touch(p: Path) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("x", encoding="utf-8")
    return p


def _place(r: dict, label: str) -> dict:
    return next(p for p in r["places"] if p["label"] == label)


def _names(node: dict) -> list[str]:
    return [d["name"] for d in node["dirs"]]


@pytest.fixture
def no_recent(monkeypatch, tmp_path):
    """最近使った場所の記録を、空の置き場にする（本物の置き場を読まない）。"""
    home = tmp_path / "pptx-home"
    home.mkdir()
    monkeypatch.setenv("PPTX_DECK_HOME", str(home))
    return home


def test_対象の拡張子だけを拾い隠しと_pptx_deck_source_は辿らない(tmp_path, no_recent):
    cwd = tmp_path / "作業 フォルダ"
    for n in ("a.docx", "b.PDF", "c.pptx", "d.md", "e.txt", "f.xlsx", "g.png", "~$a.docx", ".h.md"):
        _touch(cwd / n)
    _touch(cwd / "資料" / "x.docx")
    _touch(cwd / ".git" / "y.md")
    _touch(cwd / ".hidden" / "y.md")
    _touch(cwd / "node_modules" / "y.md")
    _touch(cwd / "pptx-deck-source" / "deck" / "script.md")
    _touch(cwd / "attr-hidden" / "y.md")
    subprocess.run(["attrib", "+h", str(cwd / "attr-hidden")], check=True)  # noqa: S603,S607  # Windows の隠し属性

    tree = _place(scan.scan(cwd, home=tmp_path / "nohome"), "作業フォルダ")["tree"]

    assert tree["path"] == str(cwd)
    assert tree["files"] == [str(cwd / n) for n in ("a.docx", "b.PDF", "c.pptx", "d.md", "e.txt")]
    assert _names(tree) == ["資料"]
    assert tree["dirs"][0] == {
        "name": "資料",
        "path": str(cwd / "資料"),
        "dirs": [],
        "files": [str(cwd / "資料" / "x.docx")],
    }


def test_ジャンクションは辿らず_Path_is_junction_がない版でも動く(tmp_path, no_recent, monkeypatch):
    cwd = tmp_path / "w"
    _touch(cwd / "本物" / "a.md")
    _touch(tmp_path / "外" / "b.md")
    # Windows のジャンクション（管理者権限なしで作れる）
    mklink = ["cmd", "/c", "mklink", "/J", str(cwd / "リンク"), str(tmp_path / "外")]
    subprocess.run(mklink, check=True, capture_output=True)  # noqa: S603,S607
    monkeypatch.delattr(Path, "is_junction", raising=False)  # Python 3.10・3.11 には Path.is_junction がない

    tree = _place(scan.scan(cwd, home=tmp_path / "nohome"), "作業フォルダ")["tree"]

    assert _names(tree) == ["本物"]


def test_深さの上限を超えたフォルダは辿らない(tmp_path, no_recent):
    _touch(tmp_path / "w" / "a" / "b" / "c" / "c.md")
    _touch(tmp_path / "w" / "a" / "b" / "c" / "d" / "d.md")

    tree = _place(scan.scan(tmp_path / "w", home=tmp_path / "nohome"), "作業フォルダ")["tree"]

    c = tree["dirs"][0]["dirs"][0]["dirs"][0]
    assert c["name"] == "c"
    assert c["files"] == [str(tmp_path / "w" / "a" / "b" / "c" / "c.md")]  # 深さ 3 のフォルダのファイルは出る
    assert c["dirs"] == []  # その下（深さ 4）は辿らない


def test_1フォルダの件数は上限で切る(tmp_path, no_recent):
    for i in range(205):
        _touch(tmp_path / "w" / f"{i:03}.md")

    tree = _place(scan.scan(tmp_path / "w", home=tmp_path / "nohome"), "作業フォルダ")["tree"]

    assert len(tree["files"]) == 200
    assert tree["files"][-1] == str(tmp_path / "w" / "199.md")


def test_存在しない場所は一覧に入らない(tmp_path, no_recent):
    home = tmp_path / "home"
    (home / "Documents").mkdir(parents=True)
    (home / "Downloads").mkdir()
    (tmp_path / "w").mkdir()

    r = scan.scan(tmp_path / "w", home=home)

    assert r["cwd"] == str(tmp_path / "w")
    assert [(p["label"], p["path"]) for p in r["places"]] == [
        ("作業フォルダ", str(tmp_path / "w")),
        ("ドキュメント", str(home / "Documents")),
        ("ダウンロード", str(home / "Downloads")),
    ]


def test_最近使った場所は記録した順に出て_10件を超えない(tmp_path, no_recent):
    dirs = [tmp_path / f"r{i:02}" for i in range(12)]
    for d in dirs:
        d.mkdir()
    scan.remember_recent([str(d) for d in dirs[:6]])
    scan.remember_recent([str(d) for d in dirs[6:]])
    scan.remember_recent([str(dirs[0]), str(tmp_path / "消えた")])  # 既にある場所は先頭へ移る

    recent = scan.load_recent()
    assert recent[:2] == [str(dirs[0]), str(tmp_path / "消えた")]
    assert recent[2:] == [str(d) for d in dirs[6:]] + [str(dirs[1]), str(dirs[2])]
    assert len(recent) == 10
    assert json.loads((no_recent / "recent.json").read_text(encoding="utf-8")) == recent

    (tmp_path / "w").mkdir()
    place = _place(scan.scan(tmp_path / "w", home=tmp_path / "nohome"), "最近使った場所")
    # 存在しない場所は出ない。各場所の名前はフルパス
    assert _names(place["tree"]) == [str(dirs[0])] + [str(d) for d in dirs[6:]] + [str(dirs[1]), str(dirs[2])]


def test_最近使った場所の記録が壊れていても空として読む(no_recent):
    (no_recent / "recent.json").write_text("{壊れた", encoding="utf-8")
    assert scan.load_recent() == []


def test_PPTX_DECK_HOME_がなければ_remember_recent_は何もしない(tmp_path, monkeypatch):
    monkeypatch.delenv("PPTX_DECK_HOME", raising=False)
    monkeypatch.chdir(tmp_path)
    scan.remember_recent([str(tmp_path)])
    assert scan.load_recent() == []
    assert list(tmp_path.iterdir()) == []
