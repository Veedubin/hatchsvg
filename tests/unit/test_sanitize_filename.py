"""Tests for _sanitize_filename (used by --split-layers for file naming)."""

from png2svg.cli import _sanitize_filename


def test_sanitize_lowercases():
    """Red Marker becomes red_marker."""
    assert _sanitize_filename("Red Marker") == "red_marker"


def test_sanitize_strips_special_chars():
    """Special characters like / and ! become underscores."""
    result = _sanitize_filename("Blue/Sky!")
    assert "blue" in result
    assert "sky" in result
    assert "/" not in result
    assert "!" not in result


def test_sanitize_collapses_runs():
    """Multiple spaces collapse to single underscore."""
    assert _sanitize_filename("a   b") == "a_b"


def test_sanitize_empty_returns_placeholder():
    """Empty string returns 'unnamed'."""
    assert _sanitize_filename("") == "unnamed"


def test_sanitize_leading_trailing_whitespace():
    """Leading/trailing whitespace is stripped."""
    assert _sanitize_filename("  hello  ") == "hello"


def test_sanitize_already_clean():
    """Already-clean name passes through unchanged."""
    assert _sanitize_filename("hello_world") == "hello_world"


def test_sanitize_dashes_preserved():
    """Dashes are preserved (valid in filenames)."""
    assert _sanitize_filename("light-blue") == "light-blue"


def test_sanitize_underscores_preserved():
    """Underscores are kept as-is."""
    assert _sanitize_filename("my_color") == "my_color"
