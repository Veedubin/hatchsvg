"""Smoke tests for the notebook helpers module.

These tests verify the helper functions used by the three tutorial
notebooks (quickstart/explore/craft). They are NOT a substitute for
running the notebooks end-to-end via ``jupyter nbconvert --execute``
(``scripts/verify_notebooks.sh`` does that), but they catch the
common failures cheaply: import errors, signature mismatches,
return-type regressions.

Why are these in ``tests/integration/`` and not ``tests/unit/``?
Because the helpers depend on the installed ``hatchsvg`` package
(installed via ``pip install -e .``) and on bundled palette
JSONs. They're integration tests by nature.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make the notebook helpers importable
NOTEBOOKS_DIR = Path(__file__).parent.parent.parent / "notebooks"
if str(NOTEBOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(NOTEBOOKS_DIR))

import notebook_helpers as nh  # noqa: E402

# Use the sample Bluey image that ships with the repo
BLUEY = Path(__file__).parent.parent.parent / "Bluey.png"


def test_helpers_module_imports():
    """The helpers module loads without error."""
    assert hasattr(nh, "load_image")
    assert hasattr(nh, "quantize_image")
    assert hasattr(nh, "render_svg")
    assert hasattr(nh, "match_to_palette")
    assert hasattr(nh, "snapshot_session")


def test_list_bundled_palettes_returns_two():
    """The two shipped palettes (Crayola, Jot) are findable."""
    palettes = nh.list_bundled_palettes()
    names = {p["name"] for p in palettes}
    assert "crayola_10ct_fine_line_classic" in names
    assert "jot_20ct_washable_fineline" in names


def test_load_palette_by_name():
    """Bundled palette lookup works."""
    palette = nh.load_palette("crayola_10ct_fine_line_classic")
    assert palette["brand"] == "Crayola"
    assert len(palette["colors"]) == 10
    # All color entries have name + hex + rgb_tuple (added by load_marker_palette)
    for c in palette["colors"]:
        assert "name" in c
        assert "hex" in c
        assert "rgb_tuple" in c
        assert len(c["rgb_tuple"]) == 3


def test_load_palette_unknown_raises():
    """Unknown palette name raises ValueError with helpful message."""
    with pytest.raises(ValueError, match="Unknown palette"):
        nh.load_palette("nonexistent-palette")


@pytest.mark.skipif(not BLUEY.exists(), reason="Bluey.png not in repo root")
def test_load_image_returns_rgba():
    """Image loader forces RGBA mode."""
    img = nh.load_image(BLUEY)
    assert img.mode == "RGBA"
    assert img.size[0] > 0 and img.size[1] > 0


@pytest.mark.skipif(not BLUEY.exists(), reason="Bluey.png not in repo root")
def test_quantize_image_runs_and_returns_expected_shape():
    """Quantize returns the documented dict shape."""
    img = nh.load_image(BLUEY)
    quant = nh.quantize_image(img, max_palette=6)

    # Required keys
    assert "indexed" in quant
    assert "palette" in quant
    assert "color_info" in quant
    assert "elapsed_ms" in quant

    # Palette and color_info are aligned
    assert len(quant["palette"]) == len(quant["color_info"])

    # Each color_info entry has the required fields
    for c in quant["color_info"]:
        assert {"idx", "rgb", "hex", "pixels", "name"} <= set(c.keys())
        assert len(c["rgb"]) == 3
        assert c["hex"].startswith("#")
        assert c["idx"] in range(len(quant["palette"]))

    # elapsed_ms is sane (positive, not absurdly high)
    assert quant["elapsed_ms"] >= 0
    assert quant["elapsed_ms"] < 30000  # quantize should be fast


@pytest.mark.skipif(not BLUEY.exists(), reason="Bluey.png not in repo root")
def test_match_to_palette_adds_marker_fields():
    """match_to_palette enriches each color with marker_name / marker_hex."""
    img = nh.load_image(BLUEY)
    quant = nh.quantize_image(img, max_palette=6)
    palette = nh.load_palette("crayola_10ct_fine_line_classic")
    matched = nh.match_to_palette(quant, palette)

    for c in matched["color_info"]:
        assert "marker_name" in c
        assert "marker_hex" in c
        assert "marker_rgb" in c


@pytest.mark.skipif(not BLUEY.exists(), reason="Bluey.png not in repo root")
def test_render_quantized_preview_returns_image():
    """The preview helper returns a PIL Image sized like the original."""
    from PIL import Image

    img = nh.load_image(BLUEY)
    quant = nh.quantize_image(img, max_palette=6)
    preview = nh.render_quantized_preview(img, quant)
    assert isinstance(preview, Image.Image)
    assert preview.size == img.size


@pytest.mark.skipif(not BLUEY.exists(), reason="Bluey.png not in repo root")
def test_snapshot_session_roundtrip():
    """snapshot_session + save/load gives back an equivalent dict."""

    from hatchsvg.core import RenderParams

    img = nh.load_image(BLUEY)
    quant = nh.quantize_image(img, max_palette=6)
    palette = nh.load_palette("crayola_10ct_fine_line_classic")

    # Build a fake color_map_used (we don't need a real render to test this)
    color_map = {c["hex"]: {"name": c["name"], "rgb": list(c["rgb"])} for c in quant["color_info"]}

    session = nh.snapshot_session(
        params=RenderParams(max_palette=6),
        palette=palette,
        color_map=color_map,
        image_path=str(BLUEY),
    )
    assert "version" in session
    assert "image" in session
    assert "params" in session
    assert "palette" in session
    assert "color_map" in session

    # Round-trip
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        path = Path(f.name)
    try:
        nh.save_session_file(session, path)
        loaded = nh.load_session_file(path)
        assert loaded["image"] == session["image"]
        assert loaded["params"]["max_palette"] == 6
        assert loaded["palette"]["brand"] == "Crayola"
    finally:
        path.unlink()


def test_format_quantize_report_is_markdown_table():
    """The report formatter produces a markdown table."""
    quant = {
        "elapsed_ms": 100,
        "palette": [(255, 0, 0), (0, 255, 0)],
        "color_info": [
            {"idx": 0, "rgb": (255, 0, 0), "hex": "#FF0000", "pixels": 1000, "name": "red"},
            {"idx": 1, "rgb": (0, 255, 0), "hex": "#00FF00", "pixels": 500, "name": "green"},
        ],
    }
    report = nh.format_quantize_report(quant)
    # Timing is intentionally NOT in the formatted report (would make the
    # executed notebook non-deterministic). The quant['elapsed_ms'] field
    # is still available for interactive use; we just don't display it.
    assert "Quantized in" not in report
    assert "**Quantized**" in report
    assert "2 colors" in report
    assert "|" in report  # markdown table
    assert "#FF0000" in report
    assert "red" in report
