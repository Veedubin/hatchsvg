"""Tests for _write_split_layers (--split-layers file naming)."""

from pathlib import Path
from unittest.mock import patch

from hatchsvg.cli import _write_split_layers
from hatchsvg.core import RenderParams


def _make_color_map_used(*marker_names):
    """Build a color_map_used dict from marker names."""
    result = {}
    for i, name in enumerate(marker_names):
        pal_hex = f"#{i:06X}"
        result[pal_hex] = {"marker_name": name}
    return result


def _mock_render_that_writes(output_path, **_kwargs):
    """Mock render_single_layer_svg that actually writes the file to disk."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("<svg></svg>", encoding="utf-8")
    return "<svg></svg>"


def test_split_layers_single_layer_creates_one_file(tmp_path):
    """With a single layer, creates one split file with correct naming pattern."""
    params = RenderParams()
    color_map_used = _make_color_map_used("Red")
    output_path = tmp_path / "out.svg"

    with patch("hatchsvg.cli.render_single_layer_svg", side_effect=_mock_render_that_writes):
        _write_split_layers(
            input_path=Path("in.png"),
            output_path=output_path,
            params=params,
            marker_palette=None,
            color_map=None,
            color_map_used=color_map_used,
        )

    files = list(tmp_path.glob("*.svg"))
    assert len(files) == 1
    assert files[0].name == "out_00_red.svg"


def test_split_layers_two_layers_same_name_handles_collision(tmp_path):
    """With two layers of the same marker name, handles slug collision (appends -2)."""
    params = RenderParams()
    # Two layers with the same marker name
    color_map_used = {
        "#FF0000": {"marker_name": "Blue"},
        "#0000FF": {"marker_name": "Blue"},
    }
    output_path = tmp_path / "out.svg"

    with patch("hatchsvg.cli.render_single_layer_svg", side_effect=_mock_render_that_writes):
        _write_split_layers(
            input_path=Path("in.png"),
            output_path=output_path,
            params=params,
            marker_palette=None,
            color_map=None,
            color_map_used=color_map_used,
        )

    files = sorted(f.name for f in tmp_path.glob("*.svg"))
    assert len(files) == 2
    assert "out_00_blue.svg" in files
    assert "out_01_blue-2.svg" in files


def test_split_layers_with_hatch_angles(tmp_path):
    """With hatch_angles specified, each layer gets the correct angle."""
    params = RenderParams(hatch_angles=[45.0, 90.0])
    color_map_used = _make_color_map_used("Red", "Green")
    output_path = tmp_path / "out.svg"

    call_args = []

    def _mock_render_capture(**kwargs):
        call_args.append(kwargs)
        return _mock_render_that_writes(**kwargs)

    with patch("hatchsvg.cli.render_single_layer_svg", side_effect=_mock_render_capture):
        _write_split_layers(
            input_path=Path("in.png"),
            output_path=output_path,
            params=params,
            marker_palette=None,
            color_map=None,
            color_map_used=color_map_used,
        )

    assert len(call_args) == 2
    # First layer gets hatch_angle 45.0
    assert call_args[0]["params"].hatch_angle == 45.0
    # Second layer gets hatch_angle 90.0
    assert call_args[1]["params"].hatch_angle == 90.0


def test_split_layers_more_than_99_uses_3digit_index(tmp_path):
    """With >99 layers, uses 3-digit index format."""
    params = RenderParams()
    # Build 100 layers
    color_map_used = {}
    for i in range(100):
        pal_hex = f"#{i:06X}"
        color_map_used[pal_hex] = {"marker_name": f"Layer{i}"}
    output_path = tmp_path / "out.svg"

    with patch("hatchsvg.cli.render_single_layer_svg", side_effect=_mock_render_that_writes):
        _write_split_layers(
            input_path=Path("in.png"),
            output_path=output_path,
            params=params,
            marker_palette=None,
            color_map=None,
            color_map_used=color_map_used,
        )

    files = sorted(tmp_path.glob("*.svg"))
    assert len(files) == 100
    # First file should use 3-digit format
    assert files[0].name.startswith("out_000_")
    # Last file should also use 3-digit format
    assert files[-1].name.startswith("out_099_")
