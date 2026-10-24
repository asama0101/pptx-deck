"""文書（SKILL.md・references・README・plugin.json・requirements.txt）の整合を検査する。"""

# ruff: noqa: S101  # pytest の assert
import json
import re

import pytest

from tests._paths import PKG, REPO

SKILL_NAMES = ("create", "revise", "rebuild", "review-plan", "diagram")
SKILL_FILES = sorted((PKG / "skills").rglob("SKILL.md"))
REFERENCE_FILES = sorted((PKG / "references").glob("*.md"))
DOC_FILES = SKILL_FILES + REFERENCE_FILES  # run.py の呼び出し・コマンド名を検査する文書
ALL_MD = sorted(PKG.rglob("*.md"))
REQ_LINES = [x.strip() for x in (PKG / "requirements.txt").read_text(encoding="utf-8").splitlines() if x.strip()]


def read(p):
    return p.read_text(encoding="utf-8")


def rel(p):
    return p.relative_to(PKG).as_posix()


def skill_text(name):
    return read(PKG / "skills" / name / "SKILL.md")


def test_スキルは5つ揃っている():
    assert sorted(f.parent.name for f in SKILL_FILES) == sorted(SKILL_NAMES)


@pytest.mark.parametrize("name", SKILL_NAMES)
def test_スキルの_frontmatter_はスキル名と一致する(name):
    text = skill_text(name)
    m = re.match(r"^---\nname: (.+)\ndescription: (.+)\n(?:compatibility: .+\n)?(?:allowed-tools: .+\n)?---\n", text)
    assert m, f"{name}: frontmatter が読めない"
    assert m.group(1).strip() == name


@pytest.mark.parametrize("f", SKILL_FILES, ids=lambda f: f.parent.name)
def test_allowed_tools_は_run_py_の呼び出しだけに絞る(f):
    """`Bash(python *)` のような広い許可は書かない。"""
    want = "allowed-tools: 'Bash(python \"${CLAUDE_PLUGIN_ROOT}/run.py\" *)'"
    head = read(f).split("\n---\n", 1)[0]
    assert want in head.split("\n")


@pytest.mark.parametrize("key", ["name", "version", "description", "license", "repository", "keywords"])
def test_plugin_json_に推奨項目がある(key):
    m = json.loads(read(PKG / ".claude-plugin" / "plugin.json"))
    assert m.get(key), key


def test_plugin_json_の_author_に名前がある():
    m = json.loads(read(PKG / ".claude-plugin" / "plugin.json"))
    assert m["author"]["name"]


@pytest.mark.parametrize("f", SKILL_FILES, ids=lambda f: f.parent.name)
def test_スキルにパスの直書きがなく_プラグインルート変数を使う(f):
    t = read(f)
    assert "C:/Users" not in t
    assert "${CLAUDE_SKILL_DIR}" not in t
    assert "${CLAUDE_PLUGIN_ROOT}" in t


@pytest.mark.parametrize("f", [REPO / "README.md", *ALL_MD], ids=lambda f: f.name if f.name == "README.md" else rel(f))
def test_libreoffice_は依存として書かず_使わないと書く(f):
    for line in read(f).splitlines():
        if re.search(r"LibreOffice|soffice", line):
            assert re.search(r"使わ|使用しな|不要|廃止", line), f"{f}: {line}"


@pytest.mark.parametrize(
    "path",
    [
        "skills/create/SKILL.md",
        "skills/review-plan/SKILL.md",
        "skills/diagram/SKILL.md",
        "references/review-flow.md",
    ],
    ids=["create", "review-plan", "diagram", "review-flow"],
)
def test_待機の上限18回と続行方法の質問が書いてある(path):
    t = read(PKG / path)
    assert "18 回" in t
    assert re.search(r"続行方法.*質問|質問.*続行方法", t)


def test_revise_は待機の上限と_create_の手順4を指す():
    t = skill_text("revise")
    assert "create の手順 4" in t
    assert "18 回" in t


def test_revise_の_build_手順は_force_と_out_を引き継ぐ():
    t = skill_text("revise")
    m = re.search(r"^4\. .*build.*$", t, re.M)
    assert m, "手順 4 の build の行がない"
    assert "--force" in m.group(0)
    assert "--out" in m.group(0)


@pytest.mark.parametrize("f", ALL_MD, ids=rel)
def test_参照文書に旧い変数や_pngs_がない(f):
    t = read(f)
    assert "${CLAUDE_SKILL_DIR}" not in t
    assert "pngs" not in t


@pytest.mark.parametrize("f", SKILL_FILES, ids=lambda f: f.parent.name)
def test_スキルのパスはプラグインルート基準で実在する(f):
    """相対リンク（references/…）は使わない。${CLAUDE_PLUGIN_ROOT}/ の後ろは実在する。"""
    t = read(f)
    assert not re.search(r"\]\((references|assets)/", t), "相対リンク"
    assert not re.search(r"`(references|assets)/[A-Za-z0-9_]", t), "地の文の相対パス"
    missing = []
    for m in re.finditer(r"\$\{CLAUDE_PLUGIN_ROOT\}/((?:run\.py|references/|assets/)[A-Za-z0-9_./-]*)", t):
        r = m.group(1)
        if "<" not in r and not (PKG / r.rstrip("/")).exists():
            missing.append(r)
    assert missing == []


def test_revise_は_create_スキルの場所を指す():
    assert "${CLAUDE_PLUGIN_ROOT}/skills/create/SKILL.md" in skill_text("revise")


def _known_commands():
    cli_src = read(PKG / "pptx_deck" / "cli.py")
    return set(re.findall(r'sub\.add_parser\(\s*"([a-z-]+)"', cli_src)) | {"setup"}  # setup は run.py が直接処理する


@pytest.mark.parametrize("f", DOC_FILES, ids=rel)
def test_文書に書かれたコマンドは_cli_に実在する(f):
    """`run.py" <コマンド>` と書かれたコマンド名は、cli.py の add_parser にある。"""
    known = _known_commands()
    used = re.findall(r'run\.py"(?: --data "\$\{CLAUDE_PLUGIN_DATA\}")? ([a-z][a-z-]*)', read(f))
    assert [c for c in used if c not in known] == []


@pytest.mark.parametrize(
    "name",
    ["draft", "history", "review-picture", "picture-status", "apply-edits", "output-format", "start-page", "intake"],
)
def test_主要コマンドが_cli_に登録されている(name):
    assert name in _known_commands()


@pytest.mark.parametrize("f", DOC_FILES, ids=rel)
def test_run_py_の呼び出しはすべて_data_を付ける(f):
    """Bash の環境変数には入らないので、本文の ${...} で渡す。
    frontmatter の allowed-tools（許可の書式）は呼び出しではない。"""
    t = read(f).split("\n---\n", 1)[-1]
    n_all = len(re.findall(r'run\.py"', t))
    n_ok = len(re.findall(r'run\.py" --data "\$\{CLAUDE_PLUGIN_DATA\}"', t))
    assert n_all == n_ok, f"{f.name}: --data のない run.py の呼び出し"


def test_run_py_の呼び出しが文書全体で29件以上ある():
    total = sum(len(re.findall(r'run\.py"', read(f).split("\n---\n", 1)[-1])) for f in DOC_FILES)
    assert total >= 29


@pytest.mark.parametrize(
    "f",
    [REPO / "README.md", *SKILL_FILES],
    ids=lambda f: f.name if f.name != "SKILL.md" else f.parent.name,
)
def test_システムの_python_を使う記述が残っていない(f):
    """専用 venv だけで動かす。システムの Python・旧い置き場の記述を残さない。"""
    words = (
        "python.kind",
        "システムの Python に必要",
        r"LOCALAPPDATA%\pptx-deck\venv",
        "$LOCALAPPDATA/pptx-deck/venv",
        "system_missing",
        "PPTX_DECK_SYSTEM_MISSING",
    )
    for line in read(f).splitlines():
        for word in words:
            if word not in line:
                continue
            legacy_path_note = "LOCALAPPDATA" in word and re.search(
                r"旧い.*使わ", line
            )  # 「旧い置き場は使わない」という注意書きだけ可
            assert legacy_path_note, f"{f.name}: {word}"


def test_requirements_txt_に依存が書かれている():
    assert REQ_LINES


@pytest.mark.parametrize("line", REQ_LINES, ids=lambda s: s.split("==")[0])
def test_requirements_は_固定の版で書かれている(line):
    assert re.match(r"^[A-Za-z0-9_.-]+==[0-9][A-Za-z0-9_.]*$", line)


@pytest.mark.parametrize(
    "word",
    ["review-picture", "picture-status", "draft", "history", "answers-picture-N.md", "PowerPoint で直せない", "xx"],
)
def test_diagram_スキルに絵の往復の手順の語が書いてある(word):
    assert word in skill_text("diagram")


@pytest.mark.parametrize(
    "word", ["NW 構成図", "トラフィックフロー", "障害動作", "自己紹介", "marker", "viewBox", "history"]
)
def test_picture_craft_に絵の作法の語が書いてある(word):
    assert word in read(PKG / "references" / "picture-craft.md")


def test_create_は_diagram_スキルを指し_readme_は_diagram_に2回以上触れる():
    assert "skills/diagram/SKILL.md" in skill_text("create")
    assert read(REPO / "README.md").count("diagram") >= 2


def test_create_は開始ページから_intake_init_の順に案内する():
    t = skill_text("create")
    pos = [t.find(w) for w in ("start-page", "intake", 'init "', "input.md")]
    assert all(p >= 0 for p in pos), pos
    assert pos == sorted(pos)


@pytest.mark.parametrize("name", ["revise", "rebuild"])
def test_revise_と_rebuild_は_pptx_のパスを受け取ると書いている(name):
    t = skill_text(name)
    assert "<出力先>/<成果物名>.pptx" in t
    assert "旧配置は未対応" in t


def test_スキルと_README_に旧配置の_source_スラッシュ_の説明が残っていない():
    for f in [*ALL_MD, REPO / "README.md", REPO / "docs" / "development.md"]:
        t = read(f)
        assert "<名前>/source/" not in t, f
        assert not re.search(
            r"(?<![\w-])source/(slides|script|design|final|answers|variants|material|history|picture)", t
        ), f


def test_成果物の用語が統一されている():
    old = "".join(["作", "品"])
    targets = [
        f
        for ext in ("py", "md", "html", "json")
        for f in PKG.rglob(f"*.{ext}")
        if "__pycache__" not in f.parts and f.name != "部品見本.html"
    ]
    targets += [
        REPO / "CLAUDE.md",
        REPO / "README.md",
        REPO / ".claude-plugin" / "marketplace.json",
        *sorted((REPO / "docs").glob("*.md")),
        *sorted((REPO / "tests").glob("*.py")),
    ]
    offenders = [f.relative_to(REPO).as_posix() for f in targets if f.exists() and old in read(f)]
    assert not offenders, offenders
