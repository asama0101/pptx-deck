"""init → variants → finalize → build → reopen を、LibreOffice を呼ばずに通す。
部品の見本（assets/components）を案に使う。"""

# ruff: noqa: S101  # pytest の assert
import json
import shutil
import subprocess

import pytest
from pptx import Presentation
from pptx_deck import cli, lifecycle, paths


@pytest.fixture
def comp(pkg):
    return pkg / "assets" / "components"


@pytest.fixture
def run(capsys):
    def _run(*argv):
        capsys.readouterr()
        rc = cli.main(list(argv))
        cap = capsys.readouterr()
        return rc, cap.out, cap.err

    return _run


def read(p):
    return p.read_text(encoding="utf-8")


@pytest.mark.slow
def test_全工程をLibreOfficeを呼ばずに通し_手直しされたPPTXは黙って上書きしない(tmp_path, monkeypatch, run, comp):
    calls = []
    real_run, real_popen = subprocess.run, subprocess.Popen

    def spy_run(cmd, *a, **k):
        calls.append(str(cmd[0] if isinstance(cmd, (list, tuple)) else cmd))
        return real_run(cmd, *a, **k)

    def spy_popen(cmd, *a, **k):
        calls.append(str(cmd[0] if isinstance(cmd, (list, tuple)) else cmd))
        return real_popen(cmd, *a, **k)

    monkeypatch.setattr(subprocess, "run", spy_run)
    monkeypatch.setattr(subprocess, "Popen", spy_popen)

    base = tmp_path / "demo"
    assert run("init", str(base), "--color", "navy")[0] == 0
    work = paths.resolve_work(base)
    slides = work / "slides"
    shutil.copyfile(comp / "layouts" / "cover.html", slides / "01-A.html")
    shutil.copyfile(comp / "diagrams" / "flow-h.html", slides / "02-A.html")
    shutil.copyfile(comp / "diagrams" / "flow-v.html", slides / "02-B.html")
    shutil.copyfile(comp / "charts" / "bar.html", slides / "03-A.html")

    assert run("variants", str(base))[0] == 0
    assert (work / "variants.html").exists()
    (work / "answers-1.md").write_text(
        "---\ndeck: demo\nround: 1\n---\n"
        "## S01\n- 選択: A\n- 判定: 承認\n- コメント: \n"
        "## S02\n- 選択: B\n- 判定: 承認\n- コメント: \n"
        "## S03\n- 選択: A\n- 判定: 承認\n- コメント: \n",
        encoding="utf-8",
    )
    # --answers を省略 → answers-*.md を自動で使う。S02 は B（縦フロー）が選ばれる
    assert run("finalize", str(base))[0] == 0
    final = read(work / "final.html")
    assert read(comp / "diagrams" / "flow-v.html") in final
    assert read(comp / "diagrams" / "flow-h.html") not in final

    rc, out, _ = run("build", str(base))
    assert rc == 0, out
    result = json.loads(out)
    pptx = base / "demo.pptx"
    assert pptx.exists()
    assert len(Presentation(str(pptx)).slides) == 3
    assert "final.html" in result["removed"]
    assert sorted(p.name for p in base.iterdir()) == ["demo.pptx", "source"]
    assert not (work / "theme.css").exists()
    assert (work / "build.json").exists()
    assert result["previews"]

    rc, out, _ = run("reopen", str(base))
    assert (rc, json.loads(out)["status"]) == (0, "ok")
    assert (work / "theme.css").exists()
    # 2 回目: 前回承認が選択済みで開く
    assert run("variants", str(base))[0] == 0
    assert '"01": {"c": "A"' in read(work / "variants.html")

    lifecycle.prune(work)
    # PowerPoint で手直しした想定
    edited = pptx.read_bytes() + b"x"
    pptx.write_bytes(edited)
    assert run("reopen", str(base))[0] == 4
    assert run("reopen", str(base), "--force")[0] == 0
    assert run("finalize", str(base))[0] == 0
    # 手直し済みの PPTX を黙って上書きしない
    rc, _, err = run("build", str(base))
    assert rc == 4, err
    assert pptx.read_bytes() == edited
    assert run("build", str(base), "--force")[0] == 0
    assert pptx.read_bytes() != edited
    assert run("clean", str(base))[0] == 0

    assert [c for c in calls if "soffice" in c.lower() or "libreoffice" in c.lower()] == []


@pytest.mark.slow
def test_最終確認の回答は案の選択を変えず_後の回の回答が効いて_build_まで通る(tmp_path, run, comp):
    base = tmp_path / "demo"
    assert run("init", str(base), "--color", "navy")[0] == 0
    work = paths.resolve_work(base)
    flow_h, flow_v = read(comp / "diagrams" / "flow-h.html"), read(comp / "diagrams" / "flow-v.html")
    shutil.copyfile(comp / "layouts" / "cover.html", work / "slides" / "01-A.html")
    shutil.copyfile(comp / "diagrams" / "flow-h.html", work / "slides" / "02-A.html")
    shutil.copyfile(comp / "diagrams" / "flow-v.html", work / "slides" / "02-B.html")
    (work / "answers-1.md").write_text(
        "---\n---\n## S01\n- 選択: A\n- 判定: 承認\n- コメント: \n## S02\n- 選択: B\n- 判定: 承認\n- コメント: \n",
        encoding="utf-8",
    )
    (work / "answers-final.md").write_text(
        "---\n---\n## S01\n- 選択: A\n- 判定: 承認\n- コメント: \n## S02\n- 選択: A\n- 判定: 承認\n- コメント: \n",
        encoding="utf-8",
    )
    assert run("finalize", str(base))[0] == 0
    assert flow_v in read(work / "final.html")
    assert run("build", str(base))[0] == 0
    # revise (a): 2 回目の回答で S02 を A に変える。古い answers-final.md（A）とは無関係に answers-2.md が効く
    assert run("reopen", str(base))[0] == 0
    (work / "answers-2.md").write_text("---\n---\n## S02\n- 選択: A\n- 判定: 承認\n- コメント: \n", encoding="utf-8")
    (work / "answers-final.md").write_text(
        "---\n---\n## S02\n- 選択: B\n- 判定: 承認\n- コメント: \n", encoding="utf-8"
    )
    assert run("finalize", str(base))[0] == 0
    body = read(work / "final.html")
    assert flow_h in body
    assert flow_v not in body
