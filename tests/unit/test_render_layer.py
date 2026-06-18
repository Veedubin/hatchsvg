"""Tests for render_single_layer_svg (used by --split-layers)."""

import numpy as np
import pytest
from PIL import Image

from hatchsvg.core import RenderParams, render_single_layer_svg


@pytest.fixture
def tiny_rgba_png(tmp_path):
    """Create a 4x4 RGBA PNG with a single red pixel for layer rendering tests."""
    img = np.zeros((4, 4, 4), dtype=np.uint8)
    img[:, :, 3] = 255  # fully opaque
    img[:, :, :3] = 255  # white background
    img[1:3, 1:3, 0] = 255  # red square
    img[1:3, 1:3, 1] = 0
    img[1:3, 1:3, 2] = 0
    out = tmp_path / "tiny.png"
    Image.fromarray(img, mode="RGBA").save(out, "PNG")
    return out


def test_render_single_layer_returns_string(tiny_rgba_png, tmp_path):
    """render_single_layer_svg returns a non-empty string."""
    params = RenderParams(max_palette=4, line_step=2, min_pixels=1)
    output_path = tmp_path / "layer.svg"
    result = render_single_layer_svg(
        input_path=tiny_rgba_png,
        params=params,
        marker_palette=None,
        color_map=None,
        pal_hex="#FF0000",
        output_path=output_path,
    )
    assert result is not None
    assert len(result) > 0


def test_render_single_layer_contains_svg_tag(tiny_rgba_png, tmp_path):
    """Output contains <svg tag."""
    params = RenderParams(max_palette=4, line_step=2, min_pixels=1)
    output_path = tmp_path / "layer.svg"
    result = render_single_layer_svg(
        input_path=tiny_rgba_png,
        params=params,
        marker_palette=None,
        color_map=None,
        pal_hex="#FF0000",
        output_path=output_path,
    )
    assert result is not None
    assert "<svg" in result


def test_render_single_layer_viewbox_is_integer(tiny_rgba_png, tmp_path):
    """viewBox uses integer format (no decimal points)."""
    params = RenderParams(max_palette=4, line_step=2, min_pixels=1)
    output_path = tmp_path / "layer.svg"
    result = render_single_layer_svg(
        input_path=tiny_rgba_png,
        params=params,
        marker_palette=None,
        color_map=None,
        pal_hex="#FF0000",
        output_path=output_path,
    )
    assert result is not None
    # Extract viewBox attribute
    import re

    match = re.search(r'viewBox="([^"]*)"', result)
    assert match is not None, "viewBox not found in SVG output"
    viewbox = match.group(1)
    parts = viewbox.split()
    assert len(parts) == 4
    for part in parts:
        assert "." not in part, f"viewBox part '{part}' contains decimal point"


def test_render_single_layer_returns_none_for_missing_color(tiny_rgba_png, tmp_path):
    """Asking for a color that doesn't exist returns None."""
    params = RenderParams(max_palette=4, line_step=2, min_pixels=1)
    output_path = tmp_path / "layer.svg"
    result = render_single_layer_svg(
        input_path=tiny_rgba_png,
        params=params,
        marker_palette=None,
        color_map=None,
        pal_hex="#00FF00",  # green — not in the image
        output_path=output_path,
    )
    assert result is None


def test_render_single_layer_writes_file(tiny_rgba_png, tmp_path):
    """The output file is actually written to disk."""
    params = RenderParams(max_palette=4, line_step=2, min_pixels=1)
    output_path = tmp_path / "layer.svg"
    render_single_layer_svg(
        input_path=tiny_rgba_png,
        params=params,
        marker_palette=None,
        color_map=None,
        pal_hex="#FF0000",
        output_path=output_path,
    )
    assert output_path.exists()
    content = output_path.read_text()
    assert "<svg" in content
