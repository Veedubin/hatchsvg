"""Tests for closest_marker edge cases."""

from hatchsvg.core import closest_marker


def test_empty_palette_returns_fallback():
    """With an empty marker palette, returns the fallback Unknown marker."""
    marker_palette = {"colors": []}
    result = closest_marker((255, 0, 0), marker_palette)
    assert result == {"name": "Unknown", "hex": "#000000", "rgb_tuple": (0, 0, 0)}


def test_single_marker_always_returned():
    """With a single marker in the palette, always returns that marker."""
    marker_palette = {
        "colors": [
            {"name": "Red", "hex": "#FF0000", "rgb_tuple": (255, 0, 0)},
        ]
    }
    result = closest_marker((0, 255, 0), marker_palette)
    assert result["name"] == "Red"
    assert result["hex"] == "#FF0000"
    assert result["rgb_tuple"] == (255, 0, 0)


def test_saturated_pixel_penalizes_neutral_markers():
    """A highly saturated pixel (s > 0.30) penalizes neutral markers (s < 0.20)."""
    # Pixel: bright red (s=1.0, highly saturated)
    # Neutral marker: gray (s=0, neutral) — gets +1.0 penalty
    # Colorful marker: blue (s=1.0) — no penalty
    marker_palette = {
        "colors": [
            {"name": "Gray", "hex": "#C8C8C8", "rgb_tuple": (200, 200, 200)},
            {"name": "Blue", "hex": "#0000FF", "rgb_tuple": (0, 0, 255)},
        ]
    }
    result = closest_marker((255, 0, 0), marker_palette)
    # Blue should win because Gray gets +1.0 penalty for being neutral
    assert result["name"] == "Blue"


def test_desaturated_pixel_favors_neutral_markers():
    """A very desaturated pixel (s < 0.15) slightly favors neutral markers."""
    # Pixel: light gray (s=0, very desaturated) — neutral markers get -0.1 bonus
    # Neutral marker: slightly darker gray (s=0, neutral) — gets -0.1
    # Colorful marker: red (s=1.0) — no adjustment
    marker_palette = {
        "colors": [
            {"name": "Gray", "hex": "#B4B4B4", "rgb_tuple": (180, 180, 180)},
            {"name": "Red", "hex": "#FF0000", "rgb_tuple": (255, 0, 0)},
        ]
    }
    result = closest_marker((200, 200, 200), marker_palette)
    # Gray should win because it gets -0.1 bonus for being neutral
    assert result["name"] == "Gray"


def test_equal_hsv_distance_lower_score_wins():
    """Two markers at equal HSV distance — the one with lower score wins."""
    # Pixel: mid-gray (s=0, desaturated) — both markers get -0.1 bonus
    # Both markers are at equal dv=0.110 from the pixel
    marker_palette = {
        "colors": [
            {"name": "DarkGray", "hex": "#646464", "rgb_tuple": (100, 100, 100)},
            {"name": "LightGray", "hex": "#9C9C9C", "rgb_tuple": (156, 156, 156)},
        ]
    }
    result = closest_marker((128, 128, 128), marker_palette)
    # Both have equal scores; DarkGray is iterated first so it wins
    assert result["name"] == "DarkGray"
