"""絵の提案と構造の確認: 計画の検証・ページ・回答の解析と凍結の判定。

ページの操作と見本から PPTX までの流れは Chromium を実際に起動する（slow）。
"""

# ruff: noqa: S101  # pytest の assert
import copy
import json
from types import SimpleNamespace

import pytest
from pptx_deck import cli, paths
from pptx_deck import picture_plan as pp

PLAN = {
    "title": "絵の提案",
    "intro": "確認してください",
    "proposals": [
        {
            "id": "P1",
            "title": "S05 通信経路",
            "reason": "経路の順番を見せるため",
            "summary": "利用者から DB まで 5 経路",
            "items": [
                {"id": "P1-1", "kind": "要素", "text": "FW"},
                {"id": "P1-2", "kind": "順序", "text": "FW → LB"},
                {"id": "P1-3", "kind": "強調", "text": "Web から DB への直接接続"},
            ],
        },
        {
            "id": "P2",
            "title": "S06 自己紹介",
            "asked": True,
            "summary": "経歴 3 点",
            "items": [{"id": "P2-1", "kind": "要素", "text": "経歴"}],
        },
        {
            "id": "P3",
            "title": "S07 体制",
            "reason": "階層を見せるため",
            "summary": "3 層",
            "items": [{"id": "P3-1", "kind": "要素", "text": "PM"}],
        },
    ],
}

MD1 = (
    "---\npicture-plan: demo\nround: 1\n---\n"
    "## P1\n- 提案: する\n- 項目 P1-1: OK\n- 項目 P1-2: 修正｜LB は FW の後\n- 項目 P1-3: OK\n- コメント: \n"
    "## P2\n- 提案: 依頼済み\n- 項目 P2-1: OK\n- コメント: \n"
    "## P3\n- 提案: しない\n- コメント: 文章のままでよい\n"
)

slow = pytest.mark.slow


@pytest.fixture
def run(capsys):
    """cli.main を実行して (終了コード, 標準出力, 標準エラー出力) を返す関数。"""

    def _run(*argv):
        capsys.readouterr()
        rc = cli.main(list(argv))
        captured = capsys.readouterr()
        return rc, captured.out, captured.err

    return _run


@pytest.fixture
def demo(tmp_path, run):
    """init 済みの作業フォルダ。write(plan) で picture-plan.json を書く。"""
    base = tmp_path / "out" / "pptx-deck-source" / "demo"
    assert run("init", str(base), "--color", "navy")[0] == 0
    work = paths.resolve_work(base)

    def write(plan):
        (work / "picture-plan.json").write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")

    return SimpleNamespace(base=base, work=work, write=write)


@pytest.fixture
def browser():
    """テストごとに起動する。measure など本体も sync_playwright を使うので、同時に生かさない。"""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        b = pw.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def review_page(browser, demo, run):
    """計画を書いて review-picture でページを作り、Chromium で開く。"""
    demo.write(PLAN)
    assert run("review-picture", str(demo.base))[0] == 0
    page = browser.new_page()
    page.goto((demo.work / "picture-review.html").resolve().as_uri())
    yield page
    page.close()


# ---- 回答の解析・判定 ----


def test_回答mdを提案_項目_コメントに解析する():
    a = pp.parse_answers(MD1)
    assert a["P1"]["proposal"] == "する"
    assert a["P1"]["items"]["P1-2"] == ("修正", "LB は FW の後")
    assert a["P1"]["items"]["P1-1"] == ("OK", "")
    assert a["P3"]["comment"] == "文章のままでよい"


def test_resolveは描く提案と見送る提案と直す項目を挙げ凍結しない():
    r = pp.resolve(PLAN, pp.merge_answers([MD1]))
    assert (r["draw"], r["skip"]) == (["P1", "P2"], ["P3"])
    assert r["fixes"] == [{"id": "P1-2", "text": "FW → LB", "comment": "LB は FW の後"}]
    assert r["frozen"] is False


def test_後の回の回答が前を上書きし直す項目がなくなると凍結する():
    md2 = "---\nround: 2\n---\n## P1\n- 項目 P1-2: OK\n"
    r = pp.resolve(PLAN, pp.merge_answers([MD1, md2]))
    assert r["fixes"] == []
    assert r["frozen"] is True, r


def test_未回答の提案は保留になるが依頼済みは回答が要らない():
    r = pp.resolve(PLAN, {})
    assert "P1 提案" in r["pending"]
    assert "P3 提案" in r["pending"]
    assert "P2 提案" not in r["pending"]
    assert r["frozen"] is False


# ---- 計画ファイルとコマンド ----


def bad_item_id():
    bad = copy.deepcopy(PLAN)
    bad["proposals"][0]["items"][0]["id"] = "X-1"
    return bad


@pytest.mark.parametrize(
    ("plan", "message"),
    [
        (None, ""),  # ファイルがない
        (bad_item_id(), "P1-1"),  # 項目の id が提案の id で始まらない
        ({"proposals": []}, ""),  # 提案が空
    ],
    ids=["計画なし", "項目idの不整合", "提案が空"],
)
def test_計画がないか不正だとreview_pictureは終了コード2で止まる(demo, run, plan, message):
    if plan is not None:
        demo.write(plan)
    rc, _, err = run("review-picture", str(demo.base))
    assert rc == 2
    assert message in err
    assert not (demo.work / "picture-review.html").exists()


def test_ページはHTMLをエスケープし依頼済みの提案の欄を省く(demo, run):
    plan = copy.deepcopy(PLAN)
    plan["proposals"][0]["items"][0]["text"] = "<script>alert(1)</script>"
    demo.write(plan)
    assert run("review-picture", str(demo.base))[0] == 0
    html = (demo.work / "picture-review.html").read_text(encoding="utf-8")
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)" in html
    assert html.count('name="prop-P1"') == 2
    assert 'name="prop-P2"' not in html  # 依頼済みは、提案の欄を省く


def test_picture_statusは直す項目があれば1_なければ0で次の回は3(demo, run):
    demo.write(PLAN)
    (demo.work / "answers-picture-1.md").write_text(MD1, encoding="utf-8")
    rc, out, _ = run("picture-status", str(demo.base))
    assert rc == 1
    assert json.loads(out)["fixes"] == [{"id": "P1-2", "text": "FW → LB", "comment": "LB は FW の後"}]
    (demo.work / "answers-picture-2.md").write_text("---\n---\n## P1\n- 項目 P1-2: OK\n", encoding="utf-8")
    assert run("picture-status", str(demo.base))[0] == 0
    assert pp.next_round(demo.work) == 3


# ---- ページの操作（Chromium） ----


def answer_all(page):
    page.click('input[name="prop-P1"][value="する"]')
    page.click('input[name="prop-P3"][value="しない"]')
    for i in ("P1-1", "P1-3", "P2-1"):
        page.click(f'li[data-i="{i}"] button[data-v="OK"]')
    page.click('li[data-i="P1-2"] button[data-v="修正"]')


@slow
def test_ページを最後まで操作すると回答mdが返り未選択では送信されない(review_page):
    page = review_page
    page.click("#copy")  # 未選択のまま押すと、送信されず、足りない所が出る
    assert not page.evaluate("!!window.__submitted")
    assert "P1" in page.inner_text("#state")
    answer_all(page)
    page.fill('li[data-i="P1-2"] .cm', "LB は FW の後")
    page.click("#copy")
    assert page.evaluate("!!window.__submitted")
    md = page.evaluate("window.__answersMd")
    a = pp.parse_answers(md)
    assert a["P1"]["items"]["P1-2"] == ("修正", "LB は FW の後")
    assert a["P2"]["proposal"] == "依頼済み"
    assert a["P3"]["proposal"] == "しない"
    assert "P3-1" not in a["P3"]["items"]  # 「しない」の提案は、項目を聞かない
    r = pp.resolve(PLAN, pp.merge_answers([md]))
    assert [f["id"] for f in r["fixes"]] == ["P1-2"]


@slow
def test_コメントの行区切り文字は回答mdの行を割らず空白に置き換わる(review_page):
    page = review_page
    answer_all(page)
    page.fill('li[data-i="P1-2"] .cm', "後\x0b- 提案: しない")
    page.fill('.card[data-p="P1"] .gc', "全体 ## P2\x85- 提案: しない")
    page.click("#copy")
    a = pp.parse_answers(page.evaluate("window.__answersMd"))
    assert a["P1"]["proposal"] == "する"
    assert a["P1"]["items"]["P1-2"] == ("修正", "後 - 提案: しない")
    assert a["P2"]["proposal"] == "依頼済み"
    assert a["P1"]["comment"] == "全体 ## P2 - 提案: しない"


# ---- 見本の素材から PPTX まで ----


@pytest.mark.parametrize(
    "name", ["incident-report.md", "self-intro-hearing.md", "network-memo.md", "picture-plan.example.json"]
)
def test_見本の素材ファイルがある(pkg, name):
    assert (pkg / "assets" / "sample" / "picture" / name).is_file()


@slow
def test_見本の提案から構造の確認_凍結_描画_PPTXまで通る(demo, run, pkg):
    """提案・構造の確認 → 凍結 → 描く → PPTX まで、実物を通す。"""
    sample = pkg / "assets" / "sample" / "picture"
    pictures = pkg / "assets" / "components" / "pictures"
    base, work = demo.base, demo.work
    (work / "picture-plan.json").write_text(
        (sample / "picture-plan.example.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    assert run("review-picture", str(base))[0] == 0
    # 1 回目: P1 は「する」で、1 項目だけ修正。P2 は「しない」
    md1 = (
        "---\npicture-plan: demo\nround: 1\n---\n"
        "## P1\n- 提案: する\n- 項目 P1-1: OK\n- 項目 P1-2: 修正｜4 番目は「応答なしのエラー」と書く\n- 項目 P1-3: "
        "OK\n- 項目 P1-4: OK\n- コメント: \n"
        "## P2\n- 提案: しない\n- コメント: \n"
    )
    (work / "answers-picture-1.md").write_text(md1, encoding="utf-8")
    rc, out, _ = run("picture-status", str(base))
    assert rc == 1
    assert [f["id"] for f in json.loads(out)["fixes"]] == ["P1-2"]
    # 2 回目: 直して OK。P2 を「する」に変える（後の回答が前を上書きする）
    md2 = (
        "---\npicture-plan: demo\nround: 2\n---\n## P1\n- 提案: する\n- 項目 P1-2: OK\n- コメント: \n"
        "## P2\n- 提案: する\n" + "".join(f"- 項目 P2-{i}: OK\n" for i in (1, 2, 3, 4)) + "- コメント: \n"
    )
    (work / "answers-picture-2.md").write_text(md2, encoding="utf-8")
    rc, out, _ = run("picture-status", str(base))
    r = json.loads(out)
    assert (rc, r["draw"], r["frozen"]) == (0, ["P1", "P2"], True), out
    # 凍結した構造を描く（見本をそのまま使う）→ 下書きの確認 → 最終 → PPTX
    for nn, n in (("01", "failure"), ("02", "traffic-flow")):
        (work / "slides" / f"{nn}-A.html").write_text(
            (pictures / f"{n}.html").read_text(encoding="utf-8"), encoding="utf-8"
        )
    assert run("draft", str(base))[0] == 0
    (work / "answers-1.md").write_text("---\n---\n## S01\n- 選択: A\n## S02\n- 選択: A\n", encoding="utf-8")
    assert run("finalize", str(base))[0] == 0
    rc, out, err = run("build", str(base))
    assert rc == 0, out + err
    assert json.loads(out)["violations"] == []
    assert (base.parent.parent / "demo.pptx").exists()
