import pytest

from pptx_deck import theme


def test_contrast_black_white():
    assert theme.contrast("#000000", "#FFFFFF") == pytest.approx(21.0, abs=0.01)


def test_resolve_preset_and_hex():
    assert theme.resolve("navy") == "#1F3A5F"
    assert theme.resolve("#1e6b52") == "#1E6B52"


@pytest.mark.parametrize("bad", ["1E6B52", "#12345", "red", "#GGGGGG"])
def test_resolve_rejects_bad(bad):
    with pytest.raises(ValueError):
        theme.resolve(bad)


@pytest.mark.parametrize("base", ["#FFFF00", "#1F3A5F", "#FFFFFF", "#00FF88", "#808080"])
def test_derived_accent_is_readable_on_white(base):
    p = theme.derive(base)
    assert theme.contrast(p.accent, "#FFFFFF") >= 4.5
    assert theme.contrast(p.emphasis, "#FFFFFF") >= 4.5
    assert theme.contrast(p.text, "#FFFFFF") >= 7


def test_emphasis_is_a_different_hue():
    for name, hexv in theme.PRESETS.items():
        p = theme.derive(hexv)
        assert theme.hue_distance(p.accent, p.emphasis) >= 60 or theme.is_gray(p.accent), name


def test_gray_base_gets_orange_emphasis():
    assert theme.derive("#3A3F47").emphasis == "#B85A0B"


def test_lighter_tones_are_ordered():
    p = theme.derive("#1F3A5F")
    L = theme.luminance
    assert L(p.accent_dark) < L(p.accent) < L(p.accent_mid) < L(p.accent_light)


def test_theme_css_defines_variables():
    css = theme.theme_css(theme.derive("#1F3A5F"))
    for var in ("--accent", "--accent-dark", "--accent-mid", "--accent-light",
                "--emphasis", "--text", "--text-sub", "--line", "--bg-soft"):
        assert var + ":" in css


def test_tints_follow_28_52_75_percent_white():
    p = theme.derive("#1976D2")
    assert p.accent == "#1976D2"
    assert p.accent_soft == theme.mix("#1976D2", "#FFFFFF", 0.28)
    assert p.accent_mid == theme.mix("#1976D2", "#FFFFFF", 0.52)
    assert p.accent_light == theme.mix("#1976D2", "#FFFFFF", 0.75)


def test_panel_and_rule_colors():
    p = theme.derive("navy")
    assert p.bg_soft == "#EEF3F6" and p.line == "#D9DEE3"


def test_theme_css_has_accent_soft():
    assert "--accent-soft:" in theme.theme_css(theme.derive("navy"))
