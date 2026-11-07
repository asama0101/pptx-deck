"""文字サイズの項目。既定・範囲・CSS 変数・回答の 1 行（`- 文字サイズ: title=40 body=20`）を扱う。"""

import math
import re
from typing import NamedTuple


class Item(NamedTuple):
    key: str
    label: str
    var: str
    default: float
    lo: float
    hi: float
    kind: str  # "px" か "scale"


ITEMS: tuple[Item, ...] = (
    Item("title", "題", "--fs-title", 37, 19, 60, "px"),
    Item("lead", "ヘッドメッセージ", "--fs-lead", 27, 19, 40, "px"),
    Item("body", "本文", "--fs-body", 19, 19, 30, "px"),
    Item("caption", "注記", "--fs-caption", 16, 14, 24, "px"),
    Item("source", "出典・脚注", "--fs-source", 14, 14, 20, "px"),
    Item("cover-title", "表紙・章扉の題", "--fs-cover-title", 40, 19, 64, "px"),
    Item("cover-sub", "表紙・章扉の副題", "--fs-cover-sub", 22, 19, 36, "px"),
    Item("subhead", "小見出し", "--fs-subhead", 22, 19, 32, "px"),
    Item("num-scale", "大きな数字の倍率", "--num-scale", 1.0, 0.7, 1.5, "scale"),
    Item("chart-scale", "グラフ内の文字の倍率", "--chart-scale", 1.0, 0.84, 1.5, "scale"),
)
_BY_KEY = {i.key: i for i in ITEMS}
_LINE = re.compile(r"^- 文字サイズ:(.*)$", re.MULTILINE)


def _num(value) -> float | None:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def clamp(key: str, value: float) -> float:
    """範囲に丸める。px は整数、scale は小数 2 桁。"""
    it = _BY_KEY[key]
    x = min(max(float(value), it.lo), it.hi)
    return float(round(x)) if it.kind == "px" else round(x, 2)


def current(cfg: dict) -> dict[str, float]:
    """既定に cfg["fontsizes"] を重ねる。壊れた値は丸め、数でなければ既定。"""
    saved = cfg.get("fontsizes") or {}
    out = {}
    for it in ITEMS:
        x = _num(saved.get(it.key)) if isinstance(saved, dict) else None
        out[it.key] = it.default if x is None else clamp(it.key, x)
    return out


def css(values: dict[str, float]) -> str:
    """:root の中に置く変数の行。"""
    rows = []
    for it in ITEMS:
        v = values.get(it.key, it.default)
        rows.append(f"  {it.var}: {v:g}{'px' if it.kind == 'px' else ''};\n")
    return "".join(rows)


def parse_line(text: str) -> dict[str, float]:
    """`- 文字サイズ: …` の行を全部読む（後勝ち）。未知のキー・数でない値は捨てる。"""
    out: dict[str, float] = {}
    for m in _LINE.finditer(text):
        for tok in m.group(1).split():
            key, _, raw = tok.partition("=")
            x = _num(raw)
            if key in _BY_KEY and x is not None:
                out[key] = x
    return out


def format_line(changed: dict[str, float]) -> str:
    if not changed:
        return ""
    return "- 文字サイズ: " + " ".join(f"{k}={v:g}" for k, v in changed.items())
