"""Tests for multi-format input support."""

import pytest
from PIL import Image

from png2svg.cli import SUPPORTED_INPUT_FORMATS


def test_supported_formats_includes_png():
    """.png must always be supported."""
    assert ".png" in SUPPORTED_INPUT_FORMATS


def test_supported_formats_includes_common_raster_types():
    """JPG, WebP, BMP, GIF, TIFF should all be in the supported list."""
    assert ".jpg" in SUPPORTED_INPUT_FORMATS
    assert ".jpeg" in SUPPORTED_INPUT_FORMATS
    assert ".webp" in SUPPORTED_INPUT_FORMATS
    assert ".bmp" in SUPPORTED_INPUT_FORMATS
    assert ".gif" in SUPPORTED_INPUT_FORMATS
    assert ".tiff" in SUPPORTED_INPUT_FORMATS
    assert ".tif" in SUPPORTED_INPUT_FORMATS


def test_supported_formats_excludes_exotic_types():
    """SVG, PDF, EPS are NOT raster inputs and should not be listed."""
    assert ".svg" not in SUPPORTED_INPUT_FORMATS
    assert ".pdf" not in SUPPORTED_INPUT_FORMATS


def test_pillow_can_decode_each_supported_format(tmp_path):
    """Pillow must be able to open every format we claim to support (regression check)."""
    # Build a tiny RGB image and round-trip it through each format Pillow supports
    img = Image.new("RGB", (8, 8), color=(200, 100, 50))
    for ext in SUPPORTED_INPUT_FORMATS:
        # gif can't store RGB, but can read what it writes; skip strict round-trip
        out = tmp_path / f"sample{ext}"
        save_kwargs = {}
        if ext in (".jpg", ".jpeg"):
            save_kwargs["quality"] = 90
        elif ext == ".gif":
            save_kwargs["palette"] = Image.Palette.ADAPTIVE
        try:
            img.save(out, **save_kwargs)
        except Exception as e:
            pytest.fail(f"Pillow failed to write {ext}: {e}")
        # Re-open to confirm Pillow can decode it
        with Image.open(out) as reloaded:
            assert reloaded.size == (8, 8)
