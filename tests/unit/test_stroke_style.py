"""Tests for _is_white_medium_pixel and _resolve_stroke_style."""

from hatchsvg.core import (
    RenderParams,
    StrokeStyle,
    _is_white_medium_pixel,
    _resolve_stroke_style,
)

# ---------------------------------------------------------------------------
# _is_white_medium_pixel
# ---------------------------------------------------------------------------


def test_white_medium_disabled_always_false():
    """With white_medium=False, _is_white_medium_pixel always returns False."""
    params = RenderParams(white_medium=False)
    assert _is_white_medium_pixel((255, 255, 255), params) is False
    assert _is_white_medium_pixel((0, 0, 0), params) is False
    assert _is_white_medium_pixel((128, 128, 128), params) is False


def test_white_medium_pure_white_returns_true():
    """With white_medium=True, pure white (255,255,255) returns True."""
    params = RenderParams(white_medium=True, paper_white_soft=20)
    assert _is_white_medium_pixel((255, 255, 255), params) is True


def test_white_medium_near_white_within_threshold_returns_true():
    """Near-white within paper_white_soft threshold returns True."""
    params = RenderParams(white_medium=True, paper_white_soft=20)
    # (240, 240, 240): distance^2 from (255,255,255) = 15^2+15^2+15^2 = 675
    # threshold^2 = 20^2 = 400. 675 > 400, so not within Euclidean threshold.
    # But v_val=0.94 >= 0.85 and s_val=0.0 <= 0.35, so HSV check passes.
    assert _is_white_medium_pixel((240, 240, 240), params) is True


def test_white_medium_dark_color_returns_false():
    """Dark color (0,0,0) returns False with white_medium=True."""
    params = RenderParams(white_medium=True, paper_white_soft=20)
    assert _is_white_medium_pixel((0, 0, 0), params) is False


def test_white_medium_high_value_low_saturation_returns_true():
    """High-value, low-saturation color (e.g. 240,240,240) returns True via HSV check."""
    params = RenderParams(white_medium=True, paper_white_soft=20)
    # v_val = 240/255 approx 0.94 >= 0.85, s_val = 0.0 <= 0.35
    assert _is_white_medium_pixel((240, 240, 240), params) is True


def test_white_medium_low_value_returns_false():
    """Low-value color (e.g. 50,50,50) returns False."""
    params = RenderParams(white_medium=True, paper_white_soft=20)
    # v_val = 50/255 approx 0.20 < 0.85, distance^2 from white is huge
    assert _is_white_medium_pixel((50, 50, 50), params) is False


def test_white_medium_high_saturation_returns_false():
    """High-saturation color (e.g. pure red) returns False even if value is high."""
    params = RenderParams(white_medium=True, paper_white_soft=20)
    # (255, 0, 0): v_val=1.0 >= 0.85, but s_val=1.0 > 0.35
    # distance^2 from white = 0^2 + 255^2 + 255^2 = 130050 > 400
    assert _is_white_medium_pixel((255, 0, 0), params) is False


def test_white_medium_barely_within_euclidean_threshold():
    """A pixel just within the Euclidean distance threshold returns True."""
    params = RenderParams(white_medium=True, paper_white_soft=20)
    # (245, 245, 245): distance^2 = 10^2+10^2+10^2 = 300 <= 400
    assert _is_white_medium_pixel((245, 245, 245), params) is True


# ---------------------------------------------------------------------------
# _resolve_stroke_style
# ---------------------------------------------------------------------------


def test_resolve_stroke_style_basic_fallback():
    """Basic call with no marker_palette and no color_map returns StrokeStyle with fallback values."""
    params = RenderParams(line_step=4)
    # Use a bright yellow (high luminance) to get "light" shade
    style = _resolve_stroke_style((255, 255, 0), params, marker_palette=None, color_map=None)

    assert isinstance(style, StrokeStyle)
    # Fallback: stroke_rgb should be the input rgb
    assert style.stroke_rgb == (255, 255, 0)
    assert style.marker_hex == "#FFFF00"
    assert "yellow" in style.marker_name.lower()
    # Luminance of (255,255,0) = 0.2126*255 + 0.7152*255 + 0.0722*0 = ~236.6 > 190
    # So shade is "light" with line_step + 3
    assert style.line_step == params.line_step + 3
    assert style.is_white is False


def test_resolve_stroke_style_with_marker_palette():
    """With marker_palette, stroke_rgb comes from closest_marker."""
    params = RenderParams(line_step=4)
    marker_palette = {
        "colors": [
            {"hex": "#FF0000", "name": "RedMarker", "rgb_tuple": (255, 0, 0)},
            {"hex": "#0000FF", "name": "BlueMarker", "rgb_tuple": (0, 0, 255)},
        ]
    }
    style = _resolve_stroke_style((200, 0, 0), params, marker_palette=marker_palette, color_map=None)

    # Should map to the closest red marker
    assert style.stroke_rgb == (255, 0, 0)
    assert style.marker_name == "RedMarker"
    assert style.is_white is False


def test_resolve_stroke_style_with_color_map():
    """With color_map session entry, session values override defaults."""
    params = RenderParams(line_step=4)
    pal_key = "#FF0000"
    color_map = {
        pal_key: {
            "marker_name": "CustomRed",
            "marker_hex": "#CC0000",
            "marker_rgb": [204, 0, 0],
            "hatch_step": 2,
        }
    }
    style = _resolve_stroke_style((255, 0, 0), params, marker_palette=None, color_map=color_map)

    assert style.stroke_rgb == (204, 0, 0)
    assert style.marker_hex == "#CC0000"
    assert style.marker_name == "CustomRed"
    assert style.line_step == 2  # overridden by color_map


def test_resolve_stroke_style_white_medium_override():
    """With white_medium=True, paper_white_override kicks in."""
    params = RenderParams(white_medium=True, paper_white_soft=20, line_step=4)
    style = _resolve_stroke_style((255, 255, 255), params, marker_palette=None, color_map=None)

    # Paper white override forces (0,0,0), "#000000", "WhiteOutline"
    assert style.stroke_rgb == (0, 0, 0)
    assert style.marker_hex == "#000000"
    assert style.marker_name == "WhiteOutline"
    assert style.is_white is True


def test_resolve_stroke_style_white_medium_with_color_map():
    """White medium override takes precedence even with color_map."""
    params = RenderParams(white_medium=True, paper_white_soft=20, line_step=4)
    pal_key = "#FFFFFF"
    color_map = {
        pal_key: {
            "marker_name": "CustomWhite",
            "marker_hex": "#EEEEEE",
            "marker_rgb": [238, 238, 238],
        }
    }
    style = _resolve_stroke_style((255, 255, 255), params, marker_palette=None, color_map=color_map)

    # Paper white override should win over color_map
    assert style.stroke_rgb == (0, 0, 0)
    assert style.marker_hex == "#000000"
    assert style.marker_name == "WhiteOutline"
    assert style.is_white is True


def test_resolve_stroke_style_dark_color():
    """Dark color should get 'dark' shade and smaller line_step."""
    params = RenderParams(line_step=4)
    style = _resolve_stroke_style((30, 30, 30), params, marker_palette=None, color_map=None)

    # Luminance approx 30, so shade should be "dark" with line_step + 2
    assert style.line_step == params.line_step + 2
    assert "dark" in style.marker_name.lower() or "black" in style.marker_name.lower()
    assert style.is_white is False


def test_resolve_stroke_style_mid_color():
    """Mid-luminance color should get 'mid' shade."""
    params = RenderParams(line_step=4)
    style = _resolve_stroke_style((128, 128, 128), params, marker_palette=None, color_map=None)

    # Luminance approx 128, so shade should be "mid" with max(2, line_step)
    assert style.line_step == max(2, params.line_step)
    assert "mid" in style.marker_name.lower() or "gray" in style.marker_name.lower()
    assert style.is_white is False
