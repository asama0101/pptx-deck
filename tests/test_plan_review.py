"""review-plan: 設計図（design.md）と原稿（script.md）の確認ページ。"""

# ruff: noqa: S101  # pytest の assert
import pytest
from pptx_deck import cli, plan_review, variants


@pytest.fixture
def design(pkg):
    return (pkg / "assets" / "sample" / "design.md").read_text(encoding="utf-8")


@pytest.fixture
def script(pkg):
    return (pkg / "assets" / "sample" / "script.md").read_text(encoding="utf-8")


@pytest.fixture
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def make_work(tmp_path, design_md=None, script_md=None):
    work = tmp_path / "deck" / "source"
    work.mkdir(parents=True)
    if design_md is not None:
        (work / "design.md").write_text(design_md, encoding="utf-8")
    if script_md is not None:
        (work / "script.md").write_text(script_md, encoding="utf-8")
    return work


# ---- 解析 ----


def test_設計図を資料全体とページごとの記述に分ける(design):
    overview, pages = plan_review.parse_design(design)
    assert "ガバニングメッセージ" in overview
    assert "台帳" in overview
    assert sorted(pages) == ["04"]
    assert "レイアウト記述" in pages["04"]


def test_原稿の全スライドと資料全体の文書を作り設計図のページ記述を合流する(design, script):
    docs, titles = plan_review.build_docs(design, script)
    assert sorted(docs)[0] == "00"
    assert len(docs) == 12  # 見本の原稿は 11 枚 + 資料全体
    assert titles["00"] == "資料全体"
    assert "削減で生む原資が成長投資を支えるため" in docs["02"]  # 見出し（ヘッドメッセージ）が出る
    assert "レイアウト記述" in docs["04"]


EVIL_DESIGN = """# 設計図
<script>alert(1)</script>
## ページごと
### S01 <img src=x onerror=alert(1)>
- <script>alert(1)</script>
### S09 孤立"ページ<
- 本文
"""
EVIL_SCRIPT = """# 原稿
<script>alert(1)</script>
## S01 題"<b
- 題: 表紙"<
- 本文: a|b <img src=x onerror=alert(1)>
## S02 設計なし
- 題: 設計なし
"""


def assert_escaped(text):
    assert "<script>alert(1)" not in text
    assert "<img src=x onerror" not in text
    assert "&lt;script&gt;" in text
    assert "&lt;img src=x onerror" in text


def test_文書の生成で設計図と原稿の山括弧をエスケープする():
    docs, titles = plan_review.build_docs(EVIL_DESIGN, EVIL_SCRIPT)
    assert_escaped("".join(docs.values()) + "".join(titles.values()))


def test_確認ページの組み立てでも山括弧をエスケープする(tmp_path):
    work = make_work(tmp_path, EVIL_DESIGN, EVIL_SCRIPT)
    page = plan_review.assemble(work).read_text(encoding="utf-8")
    assert "<script>alert(1)" not in page
    assert "<img src=x onerror" not in page
    assert "&lt;script&gt;" in page


def test_ページごとの節がない設計図は全体として読む():
    overview, pages = plan_review.parse_design("# 設計図\n本文だけ\n")
    assert "本文だけ" in overview
    assert pages == {}


def test_設計図と原稿の食い違いを両方向で示す():
    docs, titles = plan_review.build_docs(EVIL_DESIGN, EVIL_SCRIPT)
    assert "設計図にこのスライドのページがありません" in docs["02"]
    assert "設計図にこのスライドのページがありません" not in docs["01"]
    assert "<p><b>原稿にこのスライドがありません</b></p>" in docs["09"]
    assert list(docs)[-1] == "09"
    assert "孤立" in titles["09"]


def test_review_planは設計図か原稿がなければ終了コード2(tmp_path, capsys, design, script):
    work = make_work(tmp_path, None, script)  # 設計図なし
    assert cli.main(["review-plan", str(work)]) == 2
    assert "design.md がありません" in capsys.readouterr().err
    (work / "design.md").write_text(design, encoding="utf-8")
    (work / "script.md").unlink()  # 原稿なし
    assert cli.main(["review-plan", str(work)]) == 2
    assert "script.md がありません" in capsys.readouterr().err


def test_次の回番号は既存の回答の最大に1を足す(tmp_path):
    assert variants.plan_next_round(tmp_path) == 1
    (tmp_path / "answers-plan-1.md").write_text("x", encoding="utf-8")
    (tmp_path / "answers-plan-3.md").write_text("x", encoding="utf-8")
    assert variants.plan_next_round(tmp_path) == 4


# ---- ブラウザで開く ----


@pytest.mark.slow
def test_確認ページが他のレビューページと同じく動く(tmp_path, browser, design, script):
    work = make_work(tmp_path, design, script)
    (work / "answers-plan-1.md").write_text(
        "---\n---\n## S02\n- 選択: A\n- 判定: 承認\n- コメント: \n", encoding="utf-8"
    )
    out = plan_review.assemble(work, round_no=2)
    assert out.name == "plan-review.html"
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    page.goto(out.as_uri())
    page.wait_for_selector(".pane")
    assert page.evaluate("document.querySelectorAll('.pane').length") == 12
    assert (
        page.evaluate("document.querySelector('.pane[data-slide=\"02\"] input[value=A]').checked") is True
    )  # 前回承認
    page.click('.pane[data-slide="00"] .verdict .ok')  # 承認で次へ
    assert page.evaluate("document.querySelector('#nav button[aria-current=true]').dataset.go") == "01"
    page.click('.pane[data-slide="01"] .copyBtn')
    md = page.evaluate("window.__answersMd")
    assert "round: plan-2" in md
    assert "## S00" in md
    assert "## S02" in md


@pytest.mark.slow
def test_原稿が変わって作り直したページは空から始める(tmp_path, browser, design, script):
    work = make_work(tmp_path, design, script)
    out = plan_review.assemble(work, round_no=1)
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    page.goto(out.as_uri())
    page.wait_for_selector(".pane")
    cm = '.pane[data-slide="01"] .cm'
    page.click('#nav button[data-go="01"]')
    page.fill(cm, "古いコメント")
    page.click('.pane[data-slide="01"] .verdict .ng')
    page.reload()
    page.wait_for_selector(".pane")
    page.click('#nav button[data-go="01"]')
    assert page.input_value(cm) == "古いコメント"  # 同じ内容の開き直しは引き継ぐ
    changed = script.replace("Care拡販の打ち手は", "Care拡販の新しい打ち手は")
    assert changed != script
    (work / "script.md").write_text(changed, encoding="utf-8")
    plan_review.assemble(work, round_no=1)  # 同じ回で作り直す
    page.reload()
    page.wait_for_selector(".pane")
    page.click('#nav button[data-go="01"]')
    assert page.input_value(cm) == ""  # 内容が変われば空から始める
