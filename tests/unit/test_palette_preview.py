"""Tests for scripts/palette_preview.py — the standalone HTML palette preview generator."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Make scripts/ importable
SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from palette_preview import (  # type: ignore[import-not-found]  # noqa: E402 — sys.path set above
    _contrast_text_color,
    _hex_to_rgb,
    load_palette_json,
    render_palette_html,
    write_palette_html,
)


@pytest.fixture
def simple_palette() -> dict:
    """A minimal 3-color palette for testing."""
    return {
        "brand": "TestBrand",
        "set_name": "Test Set",
        "tip_width_mm": 0.8,
        "colors": [
            {"name": "Black", "hex": "#000000"},
            {"name": "White", "hex": "#FFFFFF"},
            {"name": "Red", "hex": "#FF0000"},
        ],
    }


@pytest.fixture
def bundled_palette() -> dict:
    """Load the real bundled Crayola palette for integration tests."""
    palettes_dir = Path(__file__).parent.parent.parent / "color_palettes"
    return json.loads((palettes_dir / "crayola_10ct_fine_line_classic.json").read_text())


# --- _hex_to_rgb ---


class TestHexToRgb:
    def test_standard_hex(self):
        assert _hex_to_rgb("#FF0000") == (255, 0, 0)

    def test_hex_without_hash(self):
        assert _hex_to_rgb("00FF00") == (0, 255, 0)

    def test_lowercase(self):
        assert _hex_to_rgb("#abcdef") == (0xAB, 0xCD, 0xEF)

    def test_with_whitespace(self):
        assert _hex_to_rgb("  #112233  ") == (0x11, 0x22, 0x33)

    def test_invalid_length(self):
        assert _hex_to_rgb("#FFF") is None

    def test_invalid_chars(self):
        assert _hex_to_rgb("#ZZZZZZ") is None

    def test_empty(self):
        assert _hex_to_rgb("") is None


# --- _contrast_text_color ---


class TestContrastTextColor:
    def test_black_background_uses_white_text(self):
        assert _contrast_text_color((0, 0, 0)) == "#fff"

    def test_white_background_uses_black_text(self):
        assert _contrast_text_color((255, 255, 255)) == "#000"

    def test_red_background_uses_white_text(self):
        assert _contrast_text_color((255, 0, 0)) == "#fff"

    def test_yellow_background_uses_black_text(self):
        # Yellow is bright; should use black for legibility
        assert _contrast_text_color((255, 255, 0)) == "#000"

    def test_light_blue_uses_black_text(self):
        assert _contrast_text_color((173, 216, 230)) == "#000"


# --- render_palette_html ---


class TestRenderPaletteHtml:
    def test_returns_complete_html_document(self, simple_palette):
        html = render_palette_html(simple_palette)
        assert html.startswith("<!DOCTYPE html>")
        assert "</html>" in html
        assert "<head>" in html
        assert "<body>" in html

    def test_includes_brand_and_set_name(self, simple_palette):
        html = render_palette_html(simple_palette)
        assert "TestBrand" in html
        assert "Test Set" in html

    def test_includes_tip_width(self, simple_palette):
        html = render_palette_html(simple_palette)
        assert "0.8" in html
        assert "mm" in html

    def test_renders_swatch_for_each_color(self, simple_palette):
        html = render_palette_html(simple_palette)
        assert html.count('class="swatch"') == 3
        for color in simple_palette["colors"]:
            assert color["name"] in html
            assert color["hex"] in html

    def test_no_external_resources(self, simple_palette):
        """The HTML should be self-contained — no <link>, <script src=>, or http(s) URLs."""
        html = render_palette_html(simple_palette)
        assert "<link" not in html
        assert "<script src=" not in html
        # Allow http(s) in comments/generator meta only, not in resource refs
        assert 'href="http' not in html
        assert 'src="http' not in html

    def test_handles_empty_colors_list(self):
        palette = {"brand": "Empty", "set_name": "None", "colors": []}
        html = render_palette_html(palette)
        assert "No colors" in html
        assert "1 color" not in html  # Singular word shouldn't appear for 0
        # Should still be valid HTML
        assert html.startswith("<!DOCTYPE html>")

    def test_handles_missing_tip_width(self):
        palette = {"brand": "X", "set_name": "Y", "colors": [{"name": "Red", "hex": "#FF0000"}]}
        html = render_palette_html(palette)
        assert "X" in html
        assert "tip width" not in html.lower() or "mm" not in html  # No tip-width line rendered

    def test_escapes_html_in_color_names(self):
        """Color names with HTML chars should be escaped, not interpreted."""
        palette = {
            "brand": "Brand",
            "set_name": "Set",
            "colors": [{"name": "<script>alert(1)</script>", "hex": "#FF0000"}],
        }
        html = render_palette_html(palette)
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;" in html

    def test_includes_color_count_singular(self):
        palette = {"brand": "X", "set_name": "Y", "colors": [{"name": "Red", "hex": "#FF0000"}]}
        html = render_palette_html(palette)
        assert "1 color" in html
        assert "1 colors" not in html

    def test_includes_color_count_plural(self, simple_palette):
        html = render_palette_html(simple_palette)
        assert "3 colors" in html

    def test_uses_responsive_grid(self, simple_palette):
        html = render_palette_html(simple_palette)
        assert "grid-template-columns" in html
        assert "auto-fill" in html

    def test_picks_legible_text_color_per_swatch(self, simple_palette):
        html = render_palette_html(simple_palette)
        # Black swatch should have white text
        assert "background-color: #000000;" in html
        # Find the next swatch-overlay after a black swatch
        # (this is approximate — the important thing is that contrast is
        # computed per-swatch, not globally)
        assert "color: #fff;" in html  # at least one white-text swatch
        assert "color: #000;" in html  # at least one black-text swatch


class TestBundledPalette:
    """Integration tests using the real bundled palette."""

    def test_crayola_palette_renders(self, bundled_palette):
        html = render_palette_html(bundled_palette)
        assert "Crayola" in html
        assert "10ct Fine Line Classic" in html
        # 10 colors = 10 swatches
        assert html.count('class="swatch"') == 10

    def test_crayola_palette_contains_all_color_names(self, bundled_palette):
        html = render_palette_html(bundled_palette)
        for color in bundled_palette["colors"]:
            assert color["name"] in html, f"Missing {color['name']} in rendered HTML"


# --- load_palette_json ---


class TestLoadPaletteJson:
    def test_loads_valid_palette(self, tmp_path):
        p = tmp_path / "test.json"
        p.write_text(
            json.dumps(
                {
                    "brand": "B",
                    "set_name": "S",
                    "colors": [{"name": "Red", "hex": "#FF0000"}],
                }
            )
        )
        palette = load_palette_json(p)
        assert palette["brand"] == "B"
        assert len(palette["colors"]) == 1

    def test_raises_on_invalid_json(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{not json")
        with pytest.raises(ValueError, match="Invalid JSON"):
            load_palette_json(p)

    def test_raises_on_missing_colors(self, tmp_path):
        p = tmp_path / "no_colors.json"
        p.write_text('{"brand": "X"}')
        with pytest.raises(ValueError, match="missing 'colors'"):
            load_palette_json(p)

    def test_raises_on_color_missing_hex(self, tmp_path):
        p = tmp_path / "no_hex.json"
        p.write_text('{"brand": "X", "colors": [{"name": "Red"}]}')
        with pytest.raises(ValueError, match="missing 'hex'"):
            load_palette_json(p)

    def test_raises_on_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_palette_json(tmp_path / "nonexistent.json")

    def test_accepts_string_path(self, tmp_path):
        p = tmp_path / "test.json"
        p.write_text('{"brand": "B", "colors": []}')
        # Should accept str, not just Path
        palette = load_palette_json(str(p))
        assert palette["brand"] == "B"


# --- write_palette_html ---


class TestWritePaletteHtml:
    def test_writes_file(self, tmp_path, simple_palette):
        out = tmp_path / "out.html"
        result = write_palette_html(simple_palette, out)
        assert result == out
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert content.startswith("<!DOCTYPE html>")
        assert "TestBrand" in content

    def test_accepts_string_path(self, tmp_path, simple_palette):
        out = tmp_path / "out.html"
        write_palette_html(simple_palette, str(out))
        assert out.exists()

    def test_overwrites_existing(self, tmp_path, simple_palette):
        out = tmp_path / "out.html"
        out.write_text("OLD CONTENT")
        write_palette_html(simple_palette, out)
        assert "OLD CONTENT" not in out.read_text()
        assert "TestBrand" in out.read_text()


# --- CLI main ---


class TestCliMain:
    def test_cli_writes_html_with_default_output(self, tmp_path, simple_palette):
        palette_path = tmp_path / "test.json"
        palette_path.write_text(json.dumps(simple_palette))

        from palette_preview import main

        result = main([str(palette_path)])
        assert result == 0

        # Default output: <palette>.html
        expected_output = palette_path.with_suffix(".html")
        assert expected_output.exists()
        assert "TestBrand" in expected_output.read_text()

    def test_cli_writes_html_with_explicit_output(self, tmp_path, simple_palette):
        palette_path = tmp_path / "test.json"
        palette_path.write_text(json.dumps(simple_palette))
        out = tmp_path / "custom_output.html"

        from palette_preview import main

        result = main([str(palette_path), str(out)])
        assert result == 0
        assert out.exists()

    def test_cli_fails_on_missing_file(self, tmp_path, capsys):
        from palette_preview import main

        result = main([str(tmp_path / "nonexistent.json")])
        assert result == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err

    def test_cli_fails_on_invalid_json(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{not valid")
        from palette_preview import main

        result = main([str(bad)])
        assert result == 1

    def test_cli_no_args_prints_help(self, capsys):
        from palette_preview import main

        result = main([])
        assert result == 1
        # Should have printed something to stdout (the docstring's first line)
        captured = capsys.readouterr()
        assert len(captured.out) > 0
