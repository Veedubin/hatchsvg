"""Tests for save_session / load_session round-trip."""

import json
from pathlib import Path

import numpy as np
import pytest

from hatchsvg.core import (
    RenderParams,
    _load_config_session,
    load_marker_palette,
    load_session,
    save_session,
)


def test_save_and_load_session_roundtrip(tmp_path):
    # Create a session
    out_path = tmp_path / "session.json"
    input_path = Path("test_image.png")
    palette_file = "color_palettes/crayola_10ct_fine_line_classic.json"

    params = RenderParams(
        max_palette=8,
        line_step=3,
        continuous_paths=True,
        arc_radius=5.0,
    )

    color_map_used = {
        "#FF0000": {
            "marker_name": "Red",
            "marker_hex": "#FF0000",
            "marker_rgb": (255, 0, 0),
            "palette_rgb": (255, 0, 0),
            "hatch_step": 3,
            "is_white_medium": False,
        }
    }

    # Save
    save_session(out_path, input_path, palette_file, params, color_map_used)
    assert out_path.exists()

    # Load
    loaded = load_session(out_path)
    assert loaded["input_basename"] == "test_image.png"
    assert loaded["palette_file"] == palette_file
    assert loaded["params"]["max_palette"] == 8
    assert loaded["params"]["line_step"] == 3
    assert loaded["params"]["continuous_paths"] is True
    assert loaded["params"]["arc_radius"] == 5.0
    assert "#FF0000" in loaded["color_map"]
    assert loaded["color_map"]["#FF0000"]["marker_name"] == "Red"


# ---------------------------------------------------------------------------
# load_session error handling
# ---------------------------------------------------------------------------


def test_load_session_nonexistent_file(tmp_path):
    """Loading a non-existent file raises FileNotFoundError."""
    missing = tmp_path / "does_not_exist.json"
    with pytest.raises(FileNotFoundError):
        load_session(missing)


def test_load_session_invalid_json(tmp_path):
    """Loading a file that is not valid JSON raises json.JSONDecodeError."""
    bad = tmp_path / "bad.json"
    bad.write_text("this is not json")
    with pytest.raises(json.JSONDecodeError):
        load_session(bad)


def test_load_session_missing_color_map(tmp_path):
    """Loading a session without 'color_map' key does not crash."""
    session = tmp_path / "session.json"
    session.write_text(json.dumps({"params": {"max_palette": 8}}))
    loaded = load_session(session)
    assert loaded["color_map"] == {}


def test_load_session_marker_rgb_list_to_tuple(tmp_path):
    """Loading a session where marker_rgb is a list converts it to tuple."""
    session = tmp_path / "session.json"
    data = {
        "params": {"max_palette": 8},
        "color_map": {
            "#FF0000": {
                "marker_name": "Red",
                "marker_rgb": [255, 0, 0],
                "palette_rgb": [0, 255, 0],
            }
        },
    }
    session.write_text(json.dumps(data))
    loaded = load_session(session)
    entry = loaded["color_map"]["#FF0000"]
    assert entry["marker_rgb"] == (255, 0, 0)
    assert isinstance(entry["marker_rgb"], tuple)
    assert entry["palette_rgb"] == (0, 255, 0)
    assert isinstance(entry["palette_rgb"], tuple)


# ---------------------------------------------------------------------------
# load_marker_palette error handling
# ---------------------------------------------------------------------------


def test_load_marker_palette_nonexistent_file(tmp_path):
    """Loading a non-existent palette file raises FileNotFoundError."""
    missing = tmp_path / "no_palette.json"
    with pytest.raises(FileNotFoundError):
        load_marker_palette(missing)


def test_load_marker_palette_missing_colors_key(tmp_path):
    """Loading a palette without a 'colors' key raises ValueError."""
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"name": "My Palette"}))
    with pytest.raises(ValueError, match="colors"):
        load_marker_palette(bad)


def test_load_marker_palette_colors_not_list(tmp_path):
    """Loading a palette where 'colors' is not a list raises ValueError."""
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"colors": "not_a_list"}))
    with pytest.raises(ValueError, match="colors"):
        load_marker_palette(bad)


def test_load_marker_palette_bad_hex_length(tmp_path):
    """Loading a palette with a bad hex color (wrong length) raises ValueError."""
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"colors": [{"hex": "#FFF"}]}))
    with pytest.raises(ValueError, match="Bad hex color"):
        load_marker_palette(bad)


def test_load_marker_palette_no_hex_nor_rgb(tmp_path):
    """Loading a palette where a color has neither 'hex' nor 'rgb' raises ValueError."""
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"colors": [{"name": "Nameless"}]}))
    with pytest.raises(ValueError, match="hex.*rgb"):
        load_marker_palette(bad)


def test_load_marker_palette_rgb_tuple_auto_hex(tmp_path):
    """Loading a valid palette with 'rgb' tuples auto-generates hex."""
    good = tmp_path / "good.json"
    good.write_text(json.dumps({"colors": [{"rgb": [255, 0, 0], "name": "Red"}]}))
    result = load_marker_palette(good)
    assert len(result["colors"]) == 1
    c = result["colors"][0]
    assert c["hex"] == "#FF0000"
    assert c["rgb_tuple"] == (255, 0, 0)
    assert c["name"] == "Red"


# ---------------------------------------------------------------------------
# save_session numpy serialization
# ---------------------------------------------------------------------------


def test_save_session_numpy_scalars(tmp_path):
    """save_session with numpy scalar values produces valid JSON with plain ints."""
    out = tmp_path / "session.json"
    params = RenderParams(max_palette=8)
    color_map_used = {
        "#FF0000": {
            "marker_name": "Red",
            "marker_hex": "#FF0000",
            "marker_rgb": (np.int64(255), np.int64(0), np.int64(0)),
            "palette_rgb": (np.uint32(0), np.uint32(255), np.uint32(0)),
            "hatch_step": 3,
            "is_white_medium": False,
        }
    }
    save_session(out, Path("test.png"), None, params, color_map_used)
    raw = out.read_text()
    # Must be valid JSON
    data = json.loads(raw)
    entry = data["color_map"]["FF0000"]
    assert entry["marker_rgb"] == [255, 0, 0]
    assert entry["palette_rgb"] == [0, 255, 0]
    assert entry["hatch_step"] == 3
    # Verify they are plain Python ints, not numpy types
    assert all(isinstance(v, int) for v in entry["marker_rgb"])
    assert all(isinstance(v, int) for v in entry["palette_rgb"])
    assert isinstance(entry["hatch_step"], int)


def test_save_session_skips_none_pal_hex(tmp_path):
    """save_session skips entries where pal_hex is None."""
    out = tmp_path / "session.json"
    params = RenderParams(max_palette=8)
    color_map_used = {
        None: {
            "marker_name": "Skipped",
            "marker_hex": "#000000",
            "marker_rgb": (0, 0, 0),
            "palette_rgb": (0, 0, 0),
            "hatch_step": 1,
            "is_white_medium": False,
        },
        "#00FF00": {
            "marker_name": "Green",
            "marker_hex": "#00FF00",
            "marker_rgb": (0, 255, 0),
            "palette_rgb": (0, 255, 0),
            "hatch_step": 2,
            "is_white_medium": False,
        },
    }
    save_session(out, Path("test.png"), None, params, color_map_used)
    data = json.loads(out.read_text())
    # The None entry should be skipped; only Green remains
    assert "FF0000" not in data["color_map"]
    assert "00FF00" in data["color_map"]
    assert data["color_map"]["00FF00"]["marker_name"] == "Green"


# ---------------------------------------------------------------------------
# _load_config_session skip_bg field name
# ---------------------------------------------------------------------------


def test_load_config_session_skip_bg(tmp_path):
    """_load_config_session reads 'skip_bg' (not 'skip_background') from session JSON."""
    session = tmp_path / "session.json"
    session.write_text(
        json.dumps(
            {
                "params": {"skip_bg": True, "max_palette": 8},
                "color_map": {},
            }
        )
    )

    class FakeArgs:
        use_session = str(session)

    params, _, _, _ = _load_config_session(FakeArgs())
    assert params.skip_bg is True
