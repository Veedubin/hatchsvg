"""Tests for the named-parameter presets module."""

import pytest

from hatchsvg.presets import PRESETS, apply_preset, get_preset, list_presets


def test_all_six_presets_present():
    """The 6 documented presets must all be available."""
    expected = {"portrait", "logo", "line-art", "photo", "sketch", "fast"}
    assert set(PRESETS.keys()) == expected


def test_each_preset_has_description():
    """Every preset must have a human-readable description string."""
    for name, spec in PRESETS.items():
        assert "description" in spec, f"preset '{name}' is missing description"
        assert isinstance(spec["description"], str)
        assert len(spec["description"]) > 20, f"preset '{name}' has too-short description"


def test_each_preset_has_at_least_two_overrides():
    """A preset with only one override isn't really a preset — verify minimum useful surface."""
    for name, spec in PRESETS.items():
        overrides = {k: v for k, v in spec.items() if k != "description"}
        assert len(overrides) >= 2, f"preset '{name}' has fewer than 2 overrides"


def test_preset_field_names_match_render_params():
    """Every override key must be a valid RenderParams field."""
    from hatchsvg.core import RenderParams

    valid_fields = {f for f in RenderParams.__dataclass_fields__}
    for name, spec in PRESETS.items():
        for key in spec:
            if key == "description":
                continue
            assert key in valid_fields, f"preset '{name}' uses invalid field '{key}'"


def test_list_presets_sorted():
    """list_presets must return sorted names for stable CLI --preset choices."""
    names = list_presets()
    assert names == sorted(names)
    assert "portrait" in names
    assert "logo" in names


def test_get_preset_returns_spec():
    """get_preset returns the dict for a known name."""
    spec = get_preset("logo")
    assert spec["max_palette"] == 6
    assert spec["separate_outline"] is False


def test_get_preset_raises_for_unknown():
    """get_preset raises KeyError for unknown name."""
    with pytest.raises(KeyError):
        get_preset("nonexistent-preset")


def test_apply_preset_overrides_base():
    """apply_preset overlays the preset's values on top of an empty base."""
    result = apply_preset({}, "logo")
    assert result["max_palette"] == 6
    assert result["line_step"] == 5
    assert result["separate_outline"] is False


def test_apply_preset_does_not_leak_description():
    """The 'description' field is metadata only — must not be in the merged params."""
    result = apply_preset({}, "portrait")
    assert "description" not in result
    assert "max_palette" in result
    assert result["max_palette"] == 8


def test_apply_preset_does_not_mutate_input():
    """apply_preset must return a new dict, not mutate the caller's base."""
    base = {"max_palette": 99}
    result = apply_preset(base, "logo")
    assert base["max_palette"] == 99, "apply_preset mutated the input base dict"
    assert result["max_palette"] == 6, "preset value should have overridden the base"


def test_fast_preset_disables_optimization():
    """The 'fast' preset should explicitly turn off continuous_paths and separate_outline."""
    spec = get_preset("fast")
    assert spec["continuous_paths"] is False
    assert spec["separate_outline"] is False
    assert spec["line_step"] == 8  # very coarse


def test_logo_preset_disables_separate_outline():
    """The 'logo' preset should disable separate_outline — for pen plotters, separate
    outline mode generates thousands of short pen-down moves (one per pixel row of
    the border mask), wasting ink and time on complex shapes. v2.2.2 reverted to
    the v1.x default of False.
    """
    spec = get_preset("logo")
    assert spec["separate_outline"] is False


def test_line_art_preset_low_min_pixels():
    """The 'line-art' preset should allow thin strokes through (low min_pixels)."""
    spec = get_preset("line-art")
    assert spec["min_pixels"] <= 150
    assert spec["line_step"] <= 3
