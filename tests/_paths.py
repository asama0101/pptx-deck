"""テストから pptx_deck を import するための足場。再配置（skills → plugins）の前後どちらでも動く。"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
_PLUGIN = REPO / "plugins" / "pptx-deck"
PKG = _PLUGIN if (_PLUGIN / "pptx_deck").is_dir() else REPO / "skills" / "pptx-deck"
if str(PKG) not in sys.path:
    sys.path.insert(0, str(PKG))
