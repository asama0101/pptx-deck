"""配色。基調色 1 つから、薄色・濃色・強調色を導く。色は #RRGGBB（大文字）。"""
import colorsys
import re
from dataclasses import dataclass

PRESETS = {"navy": "#1F3A5F", "green": "#1E6B52", "gray": "#3A3F47"}
_EMPHASIS = ["#B85A0B", "#0B6E99", "#7A3E9D", "#1E7A4A"]
_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


@dataclass(frozen=True)
class Palette:
    accent: str
    accent_dark: str
    accent_soft: str
    accent_mid: str
    accent_light: str
    emphasis: str
    text: str
    text_sub: str
    line: str
    bg_soft: str


def _rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _hex(rgb) -> str:
    return "#%02X%02X%02X" % tuple(round(c) for c in rgb)


def mix(a: str, b: str, t: float) -> str:
    return _hex(tuple(x + (y - x) * t for x, y in zip(_rgb(a), _rgb(b))))


def luminance(h: str) -> float:
    def f(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (f(c) for c in _rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _hls(h: str):
    r, g, b = (c / 255 for c in _rgb(h))
    return colorsys.rgb_to_hls(r, g, b)


def is_gray(h: str) -> bool:
    _, l, s = _hls(h)
    return s < 0.15 or l > 0.97 or l < 0.03


def hue_distance(a: str, b: str) -> float:
    d = abs(_hls(a)[0] * 360 - _hls(b)[0] * 360) % 360
    return min(d, 360 - d)


def resolve(arg: str) -> str:
    if arg in PRESETS:
        return PRESETS[arg]
    if not _HEX.match(arg):
        raise ValueError(f"色はプリセット名（{', '.join(PRESETS)}）か #RRGGBB で指定してください: {arg}")
    return arg.upper()


def derive(base: str) -> Palette:
    accent = resolve(base)
    while contrast(accent, "#FFFFFF") < 4.5:
        accent = mix(accent, "#000000", 0.1)
    if is_gray(accent):
        emphasis = _EMPHASIS[0]
    else:
        emphasis = next((c for c in _EMPHASIS
                         if hue_distance(c, accent) >= 60 and contrast(c, "#FFFFFF") >= 4.5),
                        "#404040")
    return Palette(
        accent=accent,
        accent_dark=mix(accent, "#000000", 0.35),
        accent_soft=mix(accent, "#FFFFFF", 0.28),
        accent_mid=mix(accent, "#FFFFFF", 0.52),
        accent_light=mix(accent, "#FFFFFF", 0.75),
        emphasis=emphasis,
        text="#1A1A1A",
        text_sub="#595959",
        line="#D9DEE3",
        bg_soft="#EEF3F6",
    )


def theme_css(p: Palette) -> str:
    rows = [("accent", p.accent), ("accent-dark", p.accent_dark), ("accent-soft", p.accent_soft), ("accent-mid", p.accent_mid),
            ("accent-light", p.accent_light), ("emphasis", p.emphasis), ("text", p.text),
            ("text-sub", p.text_sub), ("line", p.line), ("bg-soft", p.bg_soft)]
    body = "".join(f"  --{k}: {v};\n" for k, v in rows)
    return f":root {{\n{body}}}\n"
