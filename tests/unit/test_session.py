"""Tests for save_session / load_session round-trip."""

from pathlib import Path

from hatchsvg.core import RenderParams, load_session, save_session


def test_save_and_load_session_roundtrip(tmp_path):
    # Create a session
    out_path = tmp_path / "session.json"
    input_path = Path("Bluey.png")
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
    assert loaded["input_basename"] == "Bluey.png"
    assert loaded["palette_file"] == palette_file
    assert loaded["params"]["max_palette"] == 8
    assert loaded["params"]["line_step"] == 3
    assert loaded["params"]["continuous_paths"] is True
    assert loaded["params"]["arc_radius"] == 5.0
    assert "#FF0000" in loaded["color_map"]
    assert loaded["color_map"]["#FF0000"]["marker_name"] == "Red"
