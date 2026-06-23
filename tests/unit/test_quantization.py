"""Tests for build_color_index_map — quantization path (lines 614-657)."""

import numpy as np
import pytest

from hatchsvg.core import build_color_index_map


def _make_gradient_rgba(height: int = 16, width: int = 16) -> tuple:
    """Create a gradient RGBA image with many unique colors.

    Returns (orig_rgb, alpha) as numpy arrays.
    """
    # Create a smooth gradient: each pixel has a slightly different color
    # so we get >4 unique colors.
    r = np.linspace(0, 255, height, dtype=np.uint8).repeat(width).reshape(height, width)
    g = np.linspace(255, 0, height, dtype=np.uint8).repeat(width).reshape(height, width)
    b = np.zeros((height, width), dtype=np.uint8)
    orig_rgb = np.stack([r, g, b], axis=-1)
    alpha = np.full((height, width), 255, dtype=np.uint8)
    return orig_rgb, alpha


def test_quantization_falls_back_when_unique_colors_exceed_max_palette():
    """When unique visible colors > max_palette, adaptive quantization is used."""
    orig_rgb, alpha = _make_gradient_rgba(16, 16)
    max_palette = 4

    color_idx, palette, visible = build_color_index_map(orig_rgb, alpha, alpha_threshold=10, max_palette=max_palette)

    # Palette is always 256 entries (Pillow format), but only first max_palette
    # entries are meaningful quantized colors; the rest are (0,0,0) padding.
    assert len(palette) == 256
    # color_idx values should be in range [0, max_palette-1]
    assert color_idx.min() >= 0, f"color_idx has negative values: min={color_idx.min()}"
    assert color_idx.max() < max_palette, f"color_idx exceeds palette: max={color_idx.max()}"
    # Shape should match original
    assert color_idx.shape == (16, 16)


def test_quantization_palette_entries_are_rgb_tuples():
    """Each palette entry should be a 3-tuple of ints."""
    orig_rgb, alpha = _make_gradient_rgba(16, 16)
    _, palette, _ = build_color_index_map(orig_rgb, alpha, alpha_threshold=10, max_palette=4)

    # Palette is always 256 entries (Pillow format)
    assert len(palette) == 256
    for entry in palette:
        assert isinstance(entry, tuple), f"Expected tuple, got {type(entry)}"
        assert len(entry) == 3, f"Expected 3 elements, got {len(entry)}"
        assert all(0 <= v <= 255 for v in entry), f"RGB values out of range: {entry}"
    # First max_palette entries should be non-zero (actual quantized colors)
    assert any(v > 0 for entry in palette[:4] for v in entry), "First 4 palette entries should be non-zero"


def test_quantization_visible_mask_correct():
    """Visible mask should be True where alpha > threshold."""
    orig_rgb, alpha = _make_gradient_rgba(16, 16)
    # Make some pixels transparent
    alpha[0:4, 0:4] = 0  # top-left 4x4 fully transparent
    alpha[12:16, 12:16] = 5  # bottom-right 4x4 below threshold

    _, _, visible = build_color_index_map(orig_rgb, alpha, alpha_threshold=10, max_palette=4)

    assert visible.shape == (16, 16)
    # Top-left 4x4 should be invisible
    assert not visible[0:4, 0:4].any(), "Top-left 4x4 should be invisible (alpha=0)"
    # Bottom-right 4x4 should be invisible (alpha=5 < 10)
    assert not visible[12:16, 12:16].any(), "Bottom-right 4x4 should be invisible (alpha=5 < 10)"
    # Rest should be visible
    assert visible[4:12, 4:12].all(), "Center region should be visible"


def test_quantization_exact_color_path_when_few_unique_colors():
    """When unique colors <= max_palette, exact colors are used (no quantization)."""
    # Create a simple 2-color image
    orig_rgb = np.zeros((8, 8, 3), dtype=np.uint8)
    orig_rgb[0:4, :] = [255, 0, 0]  # top half red
    orig_rgb[4:8, :] = [0, 255, 0]  # bottom half green
    alpha = np.full((8, 8), 255, dtype=np.uint8)

    color_idx, palette, visible = build_color_index_map(orig_rgb, alpha, alpha_threshold=10, max_palette=12)

    # Should have exactly 2 palette entries (red and green)
    assert len(palette) == 2, f"Expected 2 palette entries, got {len(palette)}"
    # color_idx should have exactly 2 unique values (0 and 1)
    unique_vals = set(np.unique(color_idx))
    assert unique_vals == {0, 1}, f"Expected indices 0 and 1, got {unique_vals}"
    # Top half should all be one index, bottom half all the other
    top_val = color_idx[0, 0]
    bottom_val = color_idx[4, 0]
    assert top_val != bottom_val, "Top and bottom should have different indices"
    assert (color_idx[0:4, :] == top_val).all(), "Top half should all have the same index"
    assert (color_idx[4:8, :] == bottom_val).all(), "Bottom half should all have the same index"


def test_quantization_no_visible_pixels_raises():
    """When no pixels are visible, SystemExit is raised."""
    orig_rgb = np.zeros((4, 4, 3), dtype=np.uint8)
    alpha = np.zeros((4, 4), dtype=np.uint8)  # all transparent

    with pytest.raises(SystemExit, match="No visible pixels"):
        build_color_index_map(orig_rgb, alpha, alpha_threshold=10, max_palette=4)
