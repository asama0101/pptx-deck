import sys
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL))


@pytest.fixture
def home(tmp_path, monkeypatch):
    """共通の場所を一時フォルダに差し替える（本物の venv を触らない）。"""
    monkeypatch.setenv("PPTX_DECK_HOME", str(tmp_path / "home"))
    return tmp_path / "home"
