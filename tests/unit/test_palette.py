"""Tests for load_marker_palette."""

import pytest

from png2svg.core import load_marker_palette


def test_load_marker_palette_crayola(crayola_palette):
    assert crayola_palette["brand"] == "Crayola"
    assert len(crayola_palette["colors"]) == 10
    first = crayola_palette["colors"][0]
    assert "rgb_tuple" in first
    assert "hex" in first
    assert first["hex"] == "#000000"


def test_load_marker_palette_jot(jot_palette):
    assert jot_palette["brand"] == "Jot"
    assert len(jot_palette["colors"]) == 20


def test_load_marker_palette_invalid_missing_colors(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text('{"brand": "X"}')
    with pytest.raises(ValueError, match="colors"):
        load_marker_palette(bad)


def test_load_marker_palette_invalid_bad_hex(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text('{"colors": [{"hex": "#ZZZZZZ"}]}')
    with pytest.raises(ValueError):
        load_marker_palette(bad)
