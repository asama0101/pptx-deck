# ruff: noqa: S101  # pytest の assert

from pptx_deck import initdir, paths


def test_存在しない作品名は_source_を足した場所に解決される(tmp_path):
    base = tmp_path / "deck"
    assert paths.resolve_work(base) == (base / "source").resolve()


def test_source_が既にあっても_source_に解決され_作品名と作品フォルダが取れる(tmp_path):
    base = tmp_path / "deck"
    (base / "source").mkdir(parents=True)
    assert paths.resolve_work(base) == (base / "source").resolve()
    assert paths.deck_dir(base / "source") == base
    assert paths.deck_name(base / "source") == "deck"


def test_source_を直接渡してもそのまま返る(tmp_path):
    base = tmp_path / "deck"
    (base / "source").mkdir(parents=True)
    (base / "source" / "template.json").write_text("{}", encoding="utf-8")
    assert paths.resolve_work(base / "source") == (base / "source").resolve()


def test_init_は_source_の下に作品を作り作品直下には作らない(tmp_path):
    base = tmp_path / "deck"
    r = initdir.init(base, color="navy")
    assert (base / "source" / "template.json").is_file()
    assert not (base / "template.json").exists()
    assert r["workdir"] == str((base / "source").resolve())
