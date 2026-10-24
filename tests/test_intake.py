"""開始ページの回答の検証（intake）。"""

# ruff: noqa: S101  # pytest の assert
import json
from pathlib import Path

import pytest
from pptx_deck import cli, intake


def _md(files=(), out="", name="", kind="ファイル", text=None) -> str:
    lines = ["---", "start: 1", "---", "## 入力", f"- 種別: {kind}"]
    lines += [f"- ファイル: {f}" for f in files]
    lines += ["## 出力先", f"- フォルダ: {out}", "## 成果物名", f"- 名前: {name}"]
    if text is not None:
        lines += ["## 本文", text]
    return "\n".join(lines) + "\n"


def _touch(d: Path, n: str) -> Path:
    p = d / n
    p.write_text("x", encoding="utf-8")
    return p


def _resolve(raw_md: str, cwd: Path) -> dict:
    return intake.resolve(intake.parse(raw_md), cwd)


def test_parse_は複数ファイルと引用符付きのパスを読む():
    r = intake.parse(_md(files=[r'"C:\a b\資料.docx"', r"C:\c\d.txt"], out=r'"C:\out dir"', name="稟議書"))
    assert r == {
        "kind": "file",
        "files": [r"C:\a b\資料.docx", r"C:\c\d.txt"],
        "text": "",
        "out_dir": r"C:\out dir",
        "name": "稟議書",
    }


def test_parse_は種別がテキストのとき本文を次の見出しか末尾まで読む():
    md = _md(kind="テキスト", name="x", text="一行目\n\n二行目") + "## 後ろ\n- 無関係\n"
    r = intake.parse(md)
    assert r["kind"] == "text"
    assert r["text"] == "一行目\n\n二行目"


def test_parse_は_start_がない_md_をエラーにする():
    with pytest.raises(intake.IntakeError, match="start"):
        intake.parse("## 入力\n- 種別: ファイル\n")


def test_resolve_は名前の空欄を先頭のファイル名から決め_workdir_と_pptx_を返す(tmp_path):
    f = _touch(tmp_path, "資料.docx")
    out = tmp_path / "out"
    out.mkdir()
    _touch(tmp_path, "b.docx")
    r = _resolve(_md(files=[str(f), str(tmp_path / "b.docx")], out=str(out)), tmp_path)
    assert r["name"] == "資料"
    assert r["workdir"] == str(out / "pptx-deck-source" / "資料")
    assert r["pptx"] == str(out / "資料.pptx")
    assert r["files"] == [str(f), str(tmp_path / "b.docx")]
    assert r["kind"] == "file"
    assert r["collisions"] == []


def test_resolve_は出力先の空欄を作業フォルダ直下にし_相対パスを作業フォルダから解決する(tmp_path):
    _touch(tmp_path, "a.docx")
    r = _resolve(_md(files=["a.docx"], name="n"), tmp_path)
    assert r["out_dir"] == str(tmp_path)
    assert r["files"] == [str(tmp_path / "a.docx")]
    (tmp_path / "sub").mkdir()
    r = _resolve(_md(files=["a.docx"], out="sub", name="n"), tmp_path)
    assert r["out_dir"] == str(tmp_path / "sub")


def test_resolve_はテキストと名前から解決する(tmp_path):
    r = _resolve(_md(kind="テキスト", name="メモ", text="本文です"), tmp_path)
    assert (r["kind"], r["files"], r["text"], r["name"]) == ("text", [], "本文です", "メモ")


def test_resolve_は同名の_pptx_か元データがあれば_collisions_に入れる(tmp_path):
    f = _touch(tmp_path, "a.docx")
    (tmp_path / "pptx-deck-source" / "n").mkdir(parents=True)
    r = _resolve(_md(files=[str(f)], name="n"), tmp_path)
    assert r["collisions"] == [str(tmp_path / "pptx-deck-source" / "n")]
    _touch(tmp_path, "n.pptx")
    r = _resolve(_md(files=[str(f)], name="n"), tmp_path)
    assert r["collisions"] == [str(tmp_path / "pptx-deck-source" / "n"), str(tmp_path / "n.pptx")]


def test_日本語と空白を含む出力先でも解決できる(tmp_path):
    out = tmp_path / "出力 先" / "さらに 下"
    out.mkdir(parents=True)
    f = _touch(tmp_path, "資料 1.docx")
    r = _resolve(_md(files=[f'"{f}"'], out=f'"{out}"', name="稟議 書"), tmp_path)
    assert r["workdir"] == str(out / "pptx-deck-source" / "稟議 書")
    assert r["pptx"] == str(out / "稟議 書.pptx")


@pytest.mark.parametrize(
    "bad",
    [
        "a<b",
        "a>b",
        "a:b",
        'a"b',
        "a/b",
        r"a\b",
        "a|b",
        "a?b",
        "a*b",
        "a\x01b",
        "CON",
        "nul",
        "COM1",
        "lpt9",
        "CON.txt",
        "abc.",
        "abc ",
        ".",
        "..",
    ],
    ids=lambda s: repr(s),
)
def test_resolve_は不正な成果物名をエラーにし何も作らない(bad, tmp_path):
    f = _touch(tmp_path, "a.docx")
    before = sorted(p.name for p in tmp_path.rglob("*"))
    raw = intake.parse(_md(files=[str(f)], name="ok"))
    raw["name"] = bad  # md を経由すると末尾の空白が落ちるので、解決の入力に直接入れる
    with pytest.raises(intake.IntakeError, match="成果物名"):
        intake.resolve(raw, tmp_path)
    assert sorted(p.name for p in tmp_path.rglob("*")) == before


def test_resolve_はファイル由来の名前が不正でもエラーにする(tmp_path):
    f = _touch(tmp_path, "a..docx")  # 幹が "a." になる
    with pytest.raises(intake.IntakeError, match="成果物名"):
        _resolve(_md(files=[str(f)]), tmp_path)


def test_resolve_はファイルが存在しないとエラーにする(tmp_path):
    with pytest.raises(intake.IntakeError, match="見つかりません"):
        _resolve(_md(files=[str(tmp_path / "no.docx")], name="n"), tmp_path)


def test_resolve_はフォルダを指すファイルをエラーにする(tmp_path):
    with pytest.raises(intake.IntakeError, match="ファイルではありません"):
        _resolve(_md(files=[str(tmp_path)], name="n"), tmp_path)


def test_resolve_は種別がファイルでファイルが空だとエラーにする(tmp_path):
    with pytest.raises(intake.IntakeError, match="ファイル"):
        _resolve(_md(name="n"), tmp_path)


def test_resolve_は出力先が存在しないとエラーにし何も作らない(tmp_path):
    f = _touch(tmp_path, "a.docx")
    with pytest.raises(intake.IntakeError, match="出力先"):
        _resolve(_md(files=[str(f)], out=str(tmp_path / "no"), name="n"), tmp_path)
    assert not (tmp_path / "no").exists()


def test_resolve_は出力先がファイルだとエラーにする(tmp_path):
    f = _touch(tmp_path, "a.docx")
    with pytest.raises(intake.IntakeError, match="出力先"):
        _resolve(_md(files=[str(f)], out=str(f), name="n"), tmp_path)


def test_resolve_は書き込めない出力先をエラーにする(tmp_path, monkeypatch):
    f = _touch(tmp_path, "a.docx")

    def boom(*a, **k):
        raise PermissionError("denied")

    monkeypatch.setattr(intake.tempfile, "TemporaryFile", boom)
    with pytest.raises(intake.IntakeError, match="書き込めません"):
        _resolve(_md(files=[str(f)], name="n"), tmp_path)


def test_resolve_は種別がテキストで名前が空だとエラーにする(tmp_path):
    with pytest.raises(intake.IntakeError, match="成果物名"):
        _resolve(_md(kind="テキスト", text="本文"), tmp_path)


def test_resolve_は種別がテキストで本文が空だとエラーにする(tmp_path):
    with pytest.raises(intake.IntakeError, match="本文"):
        _resolve(_md(kind="テキスト", name="n", text=""), tmp_path)


def test_resolve_はファイルとテキストの両方があるとエラーにする(tmp_path):
    f = _touch(tmp_path, "a.docx")
    with pytest.raises(intake.IntakeError, match="両方"):
        _resolve(_md(files=[str(f)], name="n", text="本文"), tmp_path)
    with pytest.raises(intake.IntakeError, match="両方"):
        _resolve(_md(kind="テキスト", files=[str(f)], name="n", text="本文"), tmp_path)


def _run(tmp_path, md, *extra, capsys):
    ans = tmp_path / "answers.md"
    ans.write_text(md, encoding="utf-8")
    code = cli.main(["intake", str(ans), *extra])
    return code, capsys.readouterr()


def test_cli_intake_は成功すると_JSON_を出し終了コード_0(tmp_path, capsys):
    f = _touch(tmp_path, "a.docx")
    code, cap = _run(tmp_path, _md(files=[str(f)], out=str(tmp_path), name="n"), capsys=capsys)
    assert code == 0
    assert json.loads(cap.out)["pptx"] == str(tmp_path / "n.pptx")


def test_cli_intake_は衝突があれば終了コード_4_で_allow_existing_なら_0(tmp_path, capsys):
    f = _touch(tmp_path, "a.docx")
    _touch(tmp_path, "n.pptx")
    md = _md(files=[str(f)], out=str(tmp_path), name="n")
    code, cap = _run(tmp_path, md, capsys=capsys)
    assert code == 4
    assert json.loads(cap.out)["collisions"] == [str(tmp_path / "n.pptx")]
    code, cap = _run(tmp_path, md, "--allow-existing", capsys=capsys)
    assert code == 0


def test_cli_intake_は検証エラーで終了コード_2_を返し何も作らない(tmp_path, capsys):
    code, cap = _run(tmp_path, _md(files=[str(tmp_path / "no.docx")], name="n"), capsys=capsys)
    assert code == 2
    assert "見つかりません" in cap.err
    assert sorted(p.name for p in tmp_path.rglob("*")) == ["answers.md"]
    assert not (tmp_path / "pptx-deck-source").exists()
