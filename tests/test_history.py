"""絵の往復の履歴: 直す前の版を残し、戻せる。build は履歴を消さない。"""

# ruff: noqa: S101  # pytest の assert
import json
import os
import subprocess
import sys
from collections import namedtuple
from pathlib import Path

import pytest
from pptx_deck import cli, history, paths

Deck = namedtuple("Deck", "base work slides")


def run(capsys, *argv):
    capsys.readouterr()
    rc = cli.main(list(argv))
    cap = capsys.readouterr()
    return rc, cap.out, cap.err


def read(p):
    return p.read_text(encoding="utf-8")


@pytest.fixture
def deck(tmp_path, capsys):
    base = tmp_path / "demo"
    assert run(capsys, "init", str(base), "--color", "navy")[0] == 0
    work = paths.resolve_work(base)
    s = work / "slides"
    (s / "01-A.html").write_text("v1-01A", encoding="utf-8")
    (s / "02-A.html").write_text("v1-02A", encoding="utf-8")
    return Deck(base, work, s)


def test_スナップショットは版番号を振り断片をコピーする(deck):
    a = history.snapshot(deck.work, "構図を変える前")
    b = history.snapshot(deck.work)
    assert (a["version"], b["version"]) == (1, 2)
    assert read(deck.work / "history" / "001" / "01-A.html") == "v1-01A"
    assert [v["version"] for v in history.versions(deck.work)] == [1, 2]


def test_戻すと断片が戻り戻す前の状態が次の版に残り取り消せる(deck):
    history.snapshot(deck.work)  # 版 1: v1
    (deck.slides / "01-A.html").write_text("v2-01A", encoding="utf-8")
    (deck.slides / "03-A.html").write_text("v2-03A", encoding="utf-8")  # 版 1 には無いファイル
    r = history.restore(deck.work, 1)
    assert read(deck.slides / "01-A.html") == "v1-01A"
    assert not (deck.slides / "03-A.html").exists()
    assert r["saved_as"] == 2  # 戻す前の状態は版 2 に残る
    assert read(deck.work / "history" / "002" / "03-A.html") == "v2-03A"
    history.restore(deck.work, 2)  # 取り消せる
    assert read(deck.slides / "03-A.html") == "v2-03A"
    assert read(deck.slides / "01-A.html") == "v2-01A"


def test_スライドを指定すると_そのスライドだけ戻る(deck):
    history.snapshot(deck.work)
    (deck.slides / "01-A.html").write_text("v2-01A", encoding="utf-8")
    (deck.slides / "02-A.html").write_text("v2-02A", encoding="utf-8")
    history.restore(deck.work, 1, slide="02")
    assert read(deck.slides / "01-A.html") == "v2-01A"
    assert read(deck.slides / "02-A.html") == "v1-02A"


def test_存在しない版を戻そうとすると_版の一覧つきで拒否する(deck):
    history.snapshot(deck.work)
    with pytest.raises(ValueError, match=r"版 9 がありません（1）"):
        history.restore(deck.work, 9)


def test_断片が無いときスナップショットは拒否する(deck):
    for f in deck.slides.glob("*.html"):
        f.unlink()
    with pytest.raises(ValueError, match=r"断片（\*\.html）がありません"):
        history.snapshot(deck.work)


def test_cli_で_スナップショット_一覧_戻すを通せる(deck, capsys):
    base = str(deck.base)
    rc, out, _ = run(capsys, "history", base, "snapshot", "--label", "初回")
    assert (rc, json.loads(out)["version"]) == (0, 1)
    rc, out, _ = run(capsys, "history", base, "list")
    assert json.loads(out)[0]["label"] == "初回"
    rc, _, err = run(capsys, "history", base, "restore")  # 版の指定が無い
    assert rc == 2
    assert "restore には版の番号が要ります" in err
    (deck.slides / "01-A.html").write_text("v2-01A", encoding="utf-8")
    rc, out, _ = run(capsys, "history", base, "restore", "1")
    assert rc == 0
    assert json.loads(out)["restored_version"] == 1
    assert read(deck.slides / "01-A.html") == "v1-01A"


@pytest.mark.slow
def test_build_は履歴を消さない(deck, capsys, pkg):
    sample = pkg / "assets" / "components" / "pictures" / "traffic-flow.html"
    for f in deck.slides.glob("*.html"):
        f.unlink()
    (deck.slides / "01-A.html").write_text(read(sample), encoding="utf-8")
    history.snapshot(deck.work, "before")
    (deck.work / "answers-1.md").write_text(
        "---\n---\n## S01\n- 選択: A\n- 判定: 承認\n- コメント: \n", encoding="utf-8"
    )
    assert run(capsys, "finalize", str(deck.base))[0] == 0
    rc, out, err = run(capsys, "build", str(deck.base))
    assert rc == 0, out + err
    assert read(deck.work / "history" / "001" / "01-A.html") == read(sample)
    assert (deck.base / "demo.pptx").exists()


def test_版のディレクトリは番号だけでラベルは中に保存される(deck):
    a = history.snapshot(deck.work, "構図を変える前")
    assert a["path"].endswith("001")
    assert read(deck.work / "history" / "001" / "label.txt") == "構図を変える前"
    v = history.versions(deck.work)[0]
    assert (v["version"], v["label"]) == (1, "構図を変える前")
    assert v["files"] == ["01-A.html", "02-A.html"]  # label.txt は断片に数えない


def test_同じラベルを2回使っても衝突しない(deck):
    a = history.snapshot(deck.work, "before-apply-edits")
    b = history.snapshot(deck.work, "before-apply-edits")
    assert (a["version"], b["version"]) == (1, 2)
    assert [v["label"] for v in history.versions(deck.work)] == ["before-apply-edits"] * 2


def test_ラベル入りの古い名前のディレクトリも一覧し戻せる(deck):
    old = deck.work / "history" / "007-古い版"
    old.mkdir(parents=True)
    (old / "01-A.html").write_text("old", encoding="utf-8")
    assert [(x["version"], x["label"]) for x in history.versions(deck.work)] == [(7, "古い版")]
    assert history.snapshot(deck.work)["version"] == 8
    history.restore(deck.work, 7)
    assert read(deck.slides / "01-A.html") == "old"


def test_999を超える版も一覧され次の番号は重ならない(deck):
    d = deck.work / "history" / "1000"
    d.mkdir(parents=True)
    (d / "01-A.html").write_text("x", encoding="utf-8")
    assert [v["version"] for v in history.versions(deck.work)] == [1000]
    assert history.snapshot(deck.work, "x")["version"] == 1001


def test_並行するスナップショットでも版番号は重ならない(deck):
    code = (
        "import sys; from pathlib import Path; from pptx_deck import history; "
        "print(history.snapshot(Path(sys.argv[1]), sys.argv[2])['version'])"
    )
    pkg_dir = str(Path(history.__file__).parent.parent)
    env = dict(os.environ, PYTHONPATH=pkg_dir)
    procs = [
        subprocess.Popen(  # noqa: S603  # 自分のコードを sys.executable で起動する（外部入力なし）
            [sys.executable, "-c", code, str(deck.work), "same" if i % 2 else f"l{i}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
        )
        for i in range(8)
    ]
    results = [(p.communicate(), p.returncode) for p in procs]
    assert [rc for _, rc in results] == [0] * 8, [o[1] for o, _ in results]
    assert sorted(int(o[0]) for o, _ in results) == list(range(1, 9))
    assert [v["version"] for v in history.versions(deck.work)] == list(range(1, 9))


def test_戻すと統合結果の_final_html_が消える(deck):
    history.snapshot(deck.work)
    for n in ("final.html", "final-review.html"):
        (deck.work / n).write_text("stale", encoding="utf-8")
    history.restore(deck.work, 1)
    assert not (deck.work / "final.html").exists()
    assert not (deck.work / "final-review.html").exists()


@pytest.mark.parametrize(
    ("bad", "msg"),
    [
        ("2", "2 桁の数字"),
        ("02-A", "2 桁の数字"),
        (".*", "2 桁の数字"),
        ("", "2 桁の数字"),
        ("99", "スライド 99 の断片"),
    ],
    ids=["1桁", "断片名", "正規表現", "空", "存在しない番号"],
)
def test_不正なスライド指定は版を作る前に拒否する(deck, bad, msg):
    history.snapshot(deck.work, "x")
    with pytest.raises(ValueError, match=msg):
        history.restore(deck.work, 1, slide=bad)
    assert [v["version"] for v in history.versions(deck.work)] == [1]  # 戻す前の版を作っていない
    assert (deck.slides / "01-A.html").exists()
