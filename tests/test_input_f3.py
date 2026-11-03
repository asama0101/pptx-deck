"""再監査 F3: 入力の読み取り・確認ページ（#7・#8・#12・#14・#19・#20・#27）。"""

# ruff: noqa: S101  # pytest の assert
import json

import pytest
from pptx_deck import cli, initdir, paths, picture_plan, variants

FRAG_OK = '<div class="pp-text">x</div>'


@pytest.fixture
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


# ---- 断片のファイル名 ----


def make_slides(tmp_path, names):
    work = tmp_path / "out" / "pptx-deck-source" / "d"
    (work / "slides").mkdir(parents=True)
    for n in names:
        (work / "slides" / n).write_text(FRAG_OK, encoding="utf-8")
    return work


@pytest.mark.parametrize(
    "bad",
    ["1-A.html", "100-A.html", "01-a.html", "01-A-d4.html"],
    ids=["桁が足りない", "桁が多い", "案が小文字", "デザイン番号が範囲外"],
)
def test_名前の違う断片はファイル名を挙げてValueErrorにする(tmp_path, bad):
    work = make_slides(tmp_path, ["02-B.html", bad])
    with pytest.raises(ValueError, match=bad):
        variants.collect_designs(work)


def test_スライド断片でないhtmlは無視する(tmp_path):
    work = make_slides(tmp_path, ["01-A.html", "draft-1.html", "memo.html"])
    assert list(variants.collect_designs(work)) == ["01"]


# ---- 反映済みの配色は選択済みにしない ----


def review_page_initial_color(tmp_path, after_set_color):
    base = tmp_path / "out" / "pptx-deck-source" / "deck"
    initdir.init(base, color="navy")
    work = base
    (work / "slides" / "01-A.html").write_text(FRAG_OK, encoding="utf-8")
    md = "---\nround: 1\n---\n## S01\n- 選択: A\n- 判定: 承認\n- 配色: green\n"
    (work / "answers-1.md").write_text(md, encoding="utf-8")
    assert cli._apply_color_from_answers(work, [md]) == "applied"  # finalize が green を反映した
    if after_set_color:
        initdir.set_color(work, "navy")  # そのあと利用者が set-color navy
    html = variants.assemble(work, 2).read_text(encoding="utf-8")
    return html.split('class="rv-scheme" data-init="', 1)[1].split('"', 1)[0]


def test_set_colorのあとは反映済みの配色を選択済みにせず現在の色にする(tmp_path):
    assert review_page_initial_color(tmp_path, True) == "navy"


def test_まだ反映されていなければ前回の選択を引き継ぐ(tmp_path):
    assert review_page_initial_color(tmp_path, False) == "green"


# ---- 修正メモ ----


def test_S始まりの行だけをスライドの修正メモにする():
    md = "12:30 に会議\n- S01: 数字を直した\nS12: 題を短くした\n05: 番号だけ\n"
    assert variants.parse_notes(md) == {"01": "数字を直した", "12": "題を短くした"}


# ---- テキストの読み込み ----


def test_BOMを落として読む(tmp_path):
    f = tmp_path / "a.md"
    f.write_bytes(b"\xef\xbb\xbf## S01 \xe8\xa1\xa8\xe7\xb4\x99\n")
    assert paths.read_text(f) == "## S01 表紙\n"


def test_UTF8でない文書はファイル名つきのValueErrorにする(tmp_path):
    f = tmp_path / "script.md"
    f.write_bytes("## S01 表紙\n".encode("cp932"))
    with pytest.raises(ValueError, match="script.md") as e:
        paths.read_text(f)
    assert "script.md" in str(e.value)
    assert "UTF-8 で保存してください" in str(e.value)


def test_lint_scriptはcp932の原稿を終了コード2とUTF8の案内で断る(tmp_path, capsys):
    f = tmp_path / "script.md"
    f.write_bytes("## S01 表紙\n- layout: cover\n".encode("cp932"))
    rc = cli.entry(["lint-script", str(f)])
    assert rc == 2
    assert "UTF-8 で保存してください" in capsys.readouterr().err


def test_lint_scriptはBOMつきの原稿を読んで検査を通す(tmp_path, capsys):
    f = tmp_path / "script.md"
    f.write_bytes(b"\xef\xbb\xbf" + "## S01 表紙\n- layout: cover\n- ヘッドメッセージ: 表紙\n".encode())
    assert cli.main(["lint-script", str(f)]) == 0
    assert "ありません" not in capsys.readouterr().out
    # 対照: BOM だけの空の原稿はスライドなしとして落ちる（BOM つきでも中身を読んでいる）
    f.write_bytes(b"\xef\xbb\xbf")
    assert cli.main(["lint-script", str(f)]) == 1
    assert "スライド（## S01 …）がありません" in capsys.readouterr().out


# ---- 絵の提案の読み込み ----

PLAN = {
    "proposals": [
        {
            "id": "P1",
            "title": "t",
            "reason": "r",
            "summary": "s",
            "items": [{"id": "P1-1", "kind": "要素", "text": "FW"}],
        }
    ]
}


def plan_with(change):
    p = json.loads(json.dumps(PLAN))
    change(p)
    return p


def test_BOMつきのJSONを読む(tmp_path):
    (tmp_path / "picture-plan.json").write_bytes(b"\xef\xbb\xbf" + json.dumps(PLAN).encode("utf-8"))
    assert picture_plan.load_plan(tmp_path)["proposals"][0]["id"] == "P1"


@pytest.mark.parametrize(
    ("plan", "word"),
    [
        ([PLAN], "最上位"),
        (plan_with(lambda p: p["proposals"][0]["items"][0].pop("text")), "P1-1"),
        (plan_with(lambda p: p["proposals"][0]["items"][0].update(id=11)), "P1"),
        (plan_with(lambda p: p["proposals"][0].update(items=["x"])), "P1"),
        (plan_with(lambda p: p.update(proposals=["x"])), "proposals"),
        (plan_with(lambda p: p["proposals"][0].update(items={"a": 1})), "P1"),
    ],
    ids=["最上位が配列", "項目にtextがない", "項目のidが数値", "項目が文字列", "提案が文字列", "itemsが辞書"],
)
def test_形の誤りは該当の項目を挙げたValueErrorにする(tmp_path, plan, word):
    (tmp_path / "picture-plan.json").write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match=word):
        picture_plan.load_plan(tmp_path)


# ---- 確認ページの保存キー ----


@pytest.mark.slow
def test_計画が変わって作り直したページは空から始める(tmp_path, browser):
    out = tmp_path / "picture-review.html"
    out.write_text(picture_plan.render(PLAN, "demo", 1), encoding="utf-8")
    sel = 'li[data-i="P1-1"]'
    page = browser.new_page()
    page.goto(out.as_uri())
    page.click(f'{sel} button[data-v="OK"]')
    page.reload()
    assert page.get_attribute(sel, "data-v") == "OK"  # 同じ内容の開き直しは引き継ぐ
    changed = plan_with(lambda p: p["proposals"][0]["items"][0].update(text="LB"))
    out.write_text(picture_plan.render(changed, "demo", 1), encoding="utf-8")
    page.reload()
    assert page.get_attribute(sel, "data-v") == ""  # 計画が変われば空から始める
