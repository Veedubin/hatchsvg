"""Tests for background detection and near-duplicate shade skipping."""

import numpy as np

from hatchsvg.core import _detect_background


def test_detect_background_returns_set_of_indices():
    """_detect_background now returns a set (not a single index)."""
    visible = np.ones((10, 10), dtype=bool)
    color_idx = np.zeros((10, 10), dtype=np.int32)
    palette = [(255, 255, 255), (0, 0, 0)]

    result = _detect_background(visible, color_idx, palette)
    assert isinstance(result, set), f"Expected set, got {type(result).__name__}"
    assert 0 in result, "Detected background index should be in the returned set"


def test_detect_background_no_border_returns_empty():
    """When there are no visible border pixels, return empty set."""
    visible = np.zeros((10, 10), dtype=bool)
    color_idx = np.zeros((10, 10), dtype=np.int32)
    palette = [(255, 255, 255)]

    result = _detect_background(visible, color_idx, palette)
    assert result == set()


def test_near_duplicate_shade_is_also_background():
    """A palette color whose RGB is close to the detected bg should also be skipped.

    This is the v2.2.3 fix: anti-aliasing quantization noise creates near-duplicate
    shades of the background color. Without this fix, those near-duplicates get
    hatched, producing visible shading in negative space (between letters, between
    bear ears) that should be paper.
    """
    visible = np.ones((20, 20), dtype=bool)
    # All border pixels are the "background" color (243, 215, 167)
    color_idx = np.zeros((20, 20), dtype=np.int32)
    color_idx[1:-1, 1:-1] = -1  # mark interior as not-on-border (doesn't matter for np.bincount)
    # Actually np.bincount only sees color_idx values; for border cells we set them.
    # Reset to make all border = bg color.
    color_idx = np.zeros((20, 20), dtype=np.int32)  # all are "bg color idx 0"

    # Palette: bg (243, 215, 167) + near-duplicate (251, 235, 196, dist ≈ 36)
    # + distinctly-different dark brown (122, 78, 46, dist ≈ 219)
    palette = [
        (243, 215, 167),  # idx 0 — bg
        (251, 235, 196),  # idx 1 — near-duplicate (dist 36.1, within threshold 50)
        (122, 78, 46),  # idx 2 — far from bg (dist 219)
    ]
    result = _detect_background(visible, color_idx, palette)
    assert 0 in result, "bg should be in result"
    assert 1 in result, "near-duplicate should be detected as bg too"
    assert 2 not in result, "far color should NOT be detected as bg"


def test_threshold_zero_only_exact_match():
    """With threshold=0, only the exact background color is returned."""
    visible = np.ones((10, 10), dtype=bool)
    color_idx = np.zeros((10, 10), dtype=np.int32)
    palette = [
        (243, 215, 167),  # idx 0
        (251, 235, 196),  # idx 1 — would be near (36), but threshold=0
    ]
    result = _detect_background(visible, color_idx, palette, near_threshold=0.0)
    assert result == {0}


def test_threshold_high_includes_more_colors():
    """Higher threshold includes more colors as background."""
    visible = np.ones((10, 10), dtype=bool)
    color_idx = np.zeros((10, 10), dtype=np.int32)
    # Bg is idx 0
    palette = [
        (243, 215, 167),  # idx 0
        (180, 140, 100),  # idx 1 — dist ~120 from bg
        (200, 170, 130),  # idx 2 — dist ~70 from bg
        (240, 212, 164),  # idx 3 — dist ~5 from bg
    ]
    # With threshold=10, only idx 0 and 3
    result_low = _detect_background(visible, color_idx, palette, near_threshold=10.0)
    assert 0 in result_low and 3 in result_low
    assert 1 not in result_low and 2 not in result_low

    # With threshold=100, idx 0, 2, 3
    result_high = _detect_background(visible, color_idx, palette, near_threshold=100.0)
    assert 0 in result_high and 2 in result_high and 3 in result_high
    assert 1 not in result_high


def test_no_near_duplicates_returns_single_element_set():
    """If no other palette colors are close to bg, return single-element set."""
    visible = np.ones((10, 10), dtype=bool)
    color_idx = np.zeros((10, 10), dtype=np.int32)
    palette = [
        (255, 255, 255),  # idx 0 — bg
        (0, 0, 0),  # idx 1 — black, far
        (128, 128, 128),  # idx 2 — gray, dist ~173
    ]
    result = _detect_background(visible, color_idx, palette)
    assert result == {0}
