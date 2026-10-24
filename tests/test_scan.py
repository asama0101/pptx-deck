"""開始ページの事前スキャン（scan）。一覧は作業フォルダだけ。"""

# ruff: noqa: S101  # pytest の assert
import json
import subprocess
from pathlib import Path

from pptx_deck import scan


def _touch(p: Path) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("x", encoding="utf-8")
    return p


def _place(r: dict, label: str) -> dict:
    return next(p for p in r["places"] if p["label"] == label)


def _names(node: dict) -> list[str]:
    return [d["name"] for d in node["dirs"]]


def test_対象の拡張子だけを拾い隠しと_pptx_deck_source_は辿らない(tmp_path):
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

    tree = _place(scan.scan(cwd), "作業フォルダ")["tree"]

    assert tree["path"] == str(cwd)
    assert tree["files"] == [str(cwd / n) for n in ("a.docx", "b.PDF", "c.pptx", "d.md", "e.txt")]
    assert _names(tree) == ["資料"]
    assert tree["dirs"][0] == {
        "name": "資料",
        "path": str(cwd / "資料"),
        "dirs": [],
        "files": [str(cwd / "資料" / "x.docx")],
    }


def test_ジャンクションは辿らず_Path_is_junction_がない版でも動く(tmp_path, monkeypatch):
    cwd = tmp_path / "w"
    _touch(cwd / "本物" / "a.md")
    _touch(tmp_path / "外" / "b.md")
    # Windows のジャンクション（管理者権限なしで作れる）
    mklink = ["cmd", "/c", "mklink", "/J", str(cwd / "リンク"), str(tmp_path / "外")]
    subprocess.run(mklink, check=True, capture_output=True)  # noqa: S603,S607
    monkeypatch.delattr(Path, "is_junction", raising=False)  # Python 3.10・3.11 には Path.is_junction がない

    tree = _place(scan.scan(cwd), "作業フォルダ")["tree"]

    assert _names(tree) == ["本物"]


def test_深さの上限を超えたフォルダは辿らない(tmp_path):
    _touch(tmp_path / "w" / "a" / "b" / "c" / "c.md")
    _touch(tmp_path / "w" / "a" / "b" / "c" / "d" / "d.md")

    tree = _place(scan.scan(tmp_path / "w"), "作業フォルダ")["tree"]

    c = tree["dirs"][0]["dirs"][0]["dirs"][0]
    assert c["name"] == "c"
    assert c["files"] == [str(tmp_path / "w" / "a" / "b" / "c" / "c.md")]  # 深さ 3 のフォルダのファイルは出る
    assert c["dirs"] == []  # その下（深さ 4）は辿らない


def test_1フォルダの件数は上限で切る(tmp_path):
    for i in range(205):
        _touch(tmp_path / "w" / f"{i:03}.md")

    tree = _place(scan.scan(tmp_path / "w"), "作業フォルダ")["tree"]

    assert len(tree["files"]) == 200
    assert tree["files"][-1] == str(tmp_path / "w" / "199.md")


def test_一覧は作業フォルダだけでほかの場所を読まない(tmp_path, monkeypatch):
    fake_home = tmp_path / "home"
    for n in ("Documents", "Desktop", "Downloads"):
        _touch(fake_home / n / "a.docx")
    monkeypatch.setattr(scan.Path, "home", classmethod(lambda cls: fake_home))
    pd_home = tmp_path / "pptx-home"
    pd_home.mkdir()
    (pd_home / "recent.json").write_text(json.dumps([str(fake_home / "Documents")]), encoding="utf-8")
    monkeypatch.setenv("PPTX_DECK_HOME", str(pd_home))
    _touch(tmp_path / "w" / "a.md")

    r = scan.scan(tmp_path / "w")

    assert r["cwd"] == str(tmp_path / "w")
    assert [(p["label"], p["path"]) for p in r["places"]] == [("作業フォルダ", str(tmp_path / "w"))]
    assert r["places"][0]["tree"]["files"] == [str(tmp_path / "w" / "a.md")]
