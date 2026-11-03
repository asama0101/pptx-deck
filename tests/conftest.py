"""全テスト共通のフィクスチャ。pptx_deck の import 経路は pyproject.toml の pythonpath で通す。"""

from pathlib import Path

import pytest

from tests._paths import PKG


@pytest.fixture
def pkg() -> Path:
    """プラグイン本体（plugins/pptx-deck）のパス。読み取り専用で使う。"""
    return PKG


def pytest_collection_modifyitems(items):
    """ブラウザを起動する `browser` フィクスチャを使うテストに slow を付ける。"""
    for item in items:
        if "browser" in getattr(item, "fixturenames", ()):
            item.add_marker(pytest.mark.slow)


@pytest.fixture
def deck_base(tmp_path) -> Path:
    """成果物の作業フォルダ（<出力先>/pptx-deck-source/<成果物名>）。resolve_work(deck_base) はそのまま返る。"""
    return tmp_path / "out" / "pptx-deck-source" / "deck"
