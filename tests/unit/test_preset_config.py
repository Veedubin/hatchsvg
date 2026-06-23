"""Tests for the preset-aware CLI configuration loading."""

import argparse

import pytest

from hatchsvg.core import _extract_explicit_args, get_run_configuration


def _make_args(**overrides):
    """Build a minimal argparse Namespace matching the CLI's attribute names.

    The CLI attaches the parser as ``_hatchsvg_parser`` so core can diff explicit
    args. We mirror that contract here. Defaults come from the CLI's argparse
    spec (see ``src/hatchsvg/cli.py``).
    """
    defaults = {
        "input": "in.png",
        "output_svg": "out.svg",
        "preset": None,
        "max_palette": 12,
        "line_step": 4,
        "alpha_threshold": 10,
        "min_pixels": 200,
        "stroke_width": None,
        "outline_width": None,
        "no_skip_background": False,
        "white_medium": False,
        "paper_white_soft": 20,
        "scale": 1.0,
        "separate_outline": False,
        "palette_file": None,
        "naming_mode": "inkscape",
        "continuous_paths": False,
        "arc_radius": 0.0,
        "save_session": False,
        "use_session": None,
        "progress": False,
        "stats": False,
    }
    defaults.update(overrides)

    # Build a real parser so _extract_explicit_args can introspect defaults
    import sys

    if "hatchsvg.cli" in sys.modules:
        from hatchsvg.cli import main as _cli_main  # noqa: F401

    p = argparse.ArgumentParser()
    p.add_argument("input")
    p.add_argument("output_svg")
    p.add_argument("--preset", default=None)
    p.add_argument("--max-palette", type=int, default=12)
    p.add_argument("--line-step", type=int, default=4)
    p.add_argument("--alpha-threshold", type=int, default=10)
    p.add_argument("--min-pixels", type=int, default=200)
    p.add_argument("--stroke-width", type=float, default=None)
    p.add_argument("--outline-width", type=float, default=None)
    p.add_argument("--no-skip-background", action="store_true")
    p.add_argument("--white-medium", action="store_true")
    p.add_argument("--paper-white-soft", type=int, default=20)
    p.add_argument("--scale", type=float, default=1.0)
    p.add_argument("--separate-outline", action="store_true")
    p.add_argument("--palette-file", default=None)
    p.add_argument("--naming-mode", choices=["inkscape", "flat"], default="inkscape")
    p.add_argument("--continuous-paths", action="store_true")
    p.add_argument("--arc-radius", type=float, default=0.0)
    p.add_argument("--save-session", action="store_true")
    p.add_argument("--use-session", default=None)
    p.add_argument("--progress", action="store_true")
    p.add_argument("--stats", action="store_true")

    args = argparse.Namespace(**defaults)
    args._hatchsvg_parser = p
    return args


def test_no_preset_no_explicit_args_uses_defaults():
    """Without --preset and without explicit flags, RenderParams uses its own defaults."""
    args = _make_args()
    params, _, _, _ = get_run_configuration(args, preset_name=None)
    assert params.max_palette == 12  # RenderParams default
    assert params.line_step == 4
    assert params.continuous_paths is False


def test_preset_alone_applies_all_preset_values():
    """With only --preset logo, all preset values flow through."""
    args = _make_args(preset="logo")
    params, _, _, _ = get_run_configuration(args, preset_name="logo")
    assert params.max_palette == 6  # logo preset value
    assert params.line_step == 5
    assert params.separate_outline is False
    assert params.continuous_paths is True
    assert params.arc_radius == 3.0


def test_explicit_flag_overrides_preset():
    """--preset logo --line-step 2 should keep max_palette=6 (preset) but line_step=2 (explicit)."""
    args = _make_args(preset="logo", line_step=2)
    params, _, _, _ = get_run_configuration(args, preset_name="logo")
    assert params.line_step == 2, "explicit --line-step should override preset"
    assert params.max_palette == 6, "non-explicit field should fall back to preset"
    assert params.separate_outline is False


def test_preset_unknown_name_raises_value_error():
    """An unknown preset name should raise ValueError with a helpful message."""
    args = _make_args(preset="nonexistent")
    with pytest.raises(ValueError, match="Unknown preset"):
        get_run_configuration(args, preset_name="nonexistent")


def test_explicit_max_palette_overrides_preset():
    """--preset portrait --max-palette 4 should give max_palette=4, not 8 (preset default)."""
    args = _make_args(preset="portrait", max_palette=4)
    params, _, _, _ = get_run_configuration(args, preset_name="portrait")
    assert params.max_palette == 4
    # Other preset values still apply
    assert params.white_medium is True
    assert params.continuous_paths is True


def test_explicit_continuous_paths_overrides_preset_off():
    """--preset fast --continuous-paths should turn on continuous_paths (fast preset has it off)."""
    args = _make_args(preset="fast", continuous_paths=True)
    params, _, _, _ = get_run_configuration(args, preset_name="fast")
    assert params.continuous_paths is True
    assert params.line_step == 8  # non-explicit; from preset


def test_use_session_ignores_preset():
    """--use-session encodes the full config, so --preset is ignored."""
    # We can't easily test the session path here without a real session file,
    # but we can verify that the function dispatches to _load_config_session
    # when use_session is set. Easiest check: pass a fake path and expect a
    # FileNotFoundError from the session loader, NOT a ValueError from the
    # preset path.
    args = _make_args(use_session="/nonexistent/session.json", preset="logo")
    with pytest.raises(FileNotFoundError):
        get_run_configuration(args, preset_name="logo")


def test_no_skip_background_explicit_overrides_preset_skip_bg():
    """--no-skip-background should set skip_bg=False even if the preset didn't touch it."""
    args = _make_args(preset="portrait", no_skip_background=True)
    params, _, _, _ = get_run_configuration(args, preset_name="portrait")
    assert params.skip_bg is False  # --no-skip-background wins


# ---------------------------------------------------------------------------
# _extract_explicit_args unit tests
# ---------------------------------------------------------------------------


def test_explicit_no_skip_background_normalizes_to_skip_bg():
    """--no-skip-background normalizes to skip_bg: False in the explicit dict."""
    args = _make_args(no_skip_background=True)
    explicit = _extract_explicit_args(args)
    assert explicit == {"skip_bg": False}


def test_explicit_store_true_false_not_in_dict():
    """A store_true flag that is False (not passed) does NOT appear in explicit dict."""
    args = _make_args(white_medium=False)
    explicit = _extract_explicit_args(args)
    assert "white_medium" not in explicit


def test_explicit_store_true_true_in_dict():
    """A store_true flag that is True (passed) DOES appear in explicit dict."""
    args = _make_args(white_medium=True)
    explicit = _extract_explicit_args(args)
    assert explicit.get("white_medium") is True


def test_explicit_numeric_matches_default_not_in_dict():
    """A numeric flag with value matching default does NOT appear (fallback path)."""
    args = _make_args(max_palette=12)
    # Remove any _explicit_ marker that _make_args might have set
    if hasattr(args, "_explicit_max_palette"):
        delattr(args, "_explicit_max_palette")
    explicit = _extract_explicit_args(args)
    assert "max_palette" not in explicit


def test_explicit_numeric_differs_from_default_in_dict():
    """A numeric flag with value different from default DOES appear."""
    args = _make_args(max_palette=6)
    if hasattr(args, "_explicit_max_palette"):
        delattr(args, "_explicit_max_palette")
    explicit = _extract_explicit_args(args)
    assert explicit.get("max_palette") == 6


def test_explicit_action_info_path_used_when_present():
    """When _hatchsvg_action_info is present, it's used instead of parser._actions."""
    args = _make_args(max_palette=6)
    # Attach action_info dict (the new preferred path)
    args._hatchsvg_action_info = {
        "max_palette": {"default": 12, "is_store_bool": False},
        "white_medium": {"default": False, "is_store_bool": True},
    }
    explicit = _extract_explicit_args(args)
    assert explicit.get("max_palette") == 6
    assert "white_medium" not in explicit


def test_explicit_no_parser_no_action_info_returns_empty():
    """When neither _hatchsvg_action_info nor _hatchsvg_parser is present, returns empty dict."""
    args = argparse.Namespace(input="in.png", output_svg="out.svg")
    explicit = _extract_explicit_args(args)
    assert explicit == {}
