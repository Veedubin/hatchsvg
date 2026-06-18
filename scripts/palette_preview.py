"""Standalone HTML palette preview generator.

Takes a hatchsvg palette JSON (brand, set_name, tip_width_mm, colors: [{name, hex}])
and produces a self-contained HTML file showing each color as a swatch with its
name and hex code. No external CSS, no JavaScript, no network — just a file the
user can double-click and see what their palette looks like.

Usage:
    from palette_preview import render_palette_html, write_palette_html

    html = render_palette_html(palette_dict)
    write_palette_html(palette_dict, "my_palette.html")
    # Or use the CLI: python palette_preview.py path/to/palette.json
"""

import html as html_lib
import json
import sys
from pathlib import Path
from typing import Any


def _hex_to_rgb(hex_str: str) -> tuple[int, int, int] | None:
    """Parse '#RRGGBB' or 'RRGGBB' to (r, g, b). Returns None on invalid input."""
    s = hex_str.strip().lstrip("#")
    if len(s) != 6:
        return None
    try:
        return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
    except ValueError:
        return None


def _contrast_text_color(rgb: tuple[int, int, int]) -> str:
    """Return '#000' or '#fff' for legibility on the given background color.
    Uses the standard W3C relative-luminance formula."""
    r, g, b = (c / 255 for c in rgb)

    # Linearize sRGB
    def _linearize(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    rl, gl, bl = _linearize(r), _linearize(g), _linearize(b)
    luminance = 0.2126 * rl + 0.7152 * gl + 0.0722 * bl
    return "#000" if luminance > 0.5 else "#fff"


def render_palette_html(palette: dict[str, Any]) -> str:
    """Render a palette dict as a self-contained HTML page.

    The output is a complete <html>...</html> document with inline CSS.
    No external resources are referenced. Safe to email, drop in a repo,
    or open from a file:// URL.
    """
    brand = html_lib.escape(str(palette.get("brand", "Custom Palette")))
    set_name = html_lib.escape(str(palette.get("set_name", "")))
    tip_width = palette.get("tip_width_mm", "")
    colors = palette.get("colors", [])

    # Build swatch HTML for each color
    swatch_blocks: list[str] = []
    for i, color in enumerate(colors):
        name = html_lib.escape(str(color.get("name", "Unnamed")))
        hex_str = str(color.get("hex", "#888888"))
        rgb = _hex_to_rgb(hex_str) or (136, 136, 136)
        text_color = _contrast_text_color(rgb)
        rgb_label = f"rgb({rgb[0]}, {rgb[1]}, {rgb[2]})"

        swatch_blocks.append(
            f"""    <div class="swatch" style="background-color: {hex_lib_escape(hex_str)};">
      <div class="swatch-overlay" style="color: {text_color};">
        <div class="swatch-name">{name}</div>
        <div class="swatch-hex">{html_lib.escape(hex_str.upper())}</div>
        <div class="swatch-rgb">{rgb_label}</div>
        <div class="swatch-index">#{i + 1}</div>
      </div>
    </div>"""
        )

    swatches_html = (
        "\n".join(swatch_blocks) if swatch_blocks else ('    <p class="empty">No colors in this palette.</p>')
    )

    tip_line = f'<p class="meta">Marker tip width: <b>{html_lib.escape(str(tip_width))} mm</b></p>' if tip_width else ""
    title = f"{brand} — {set_name}" if set_name else brand
    color_count = len(colors)
    count_word = "color" if color_count == 1 else "colors"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html_lib.escape(title)}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="generator" content="hatchsvg palette_preview">
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      margin: 0;
      padding: 2rem;
      background: #f5f5f5;
      color: #222;
    }}
    header {{
      max-width: 1200px;
      margin: 0 auto 2rem;
    }}
    h1 {{
      margin: 0 0 0.5rem;
      font-size: 1.75rem;
    }}
    .meta {{
      margin: 0.25rem 0;
      color: #555;
    }}
    .swatches {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
      gap: 1rem;
      max-width: 1200px;
      margin: 0 auto;
    }}
    .swatch {{
      position: relative;
      aspect-ratio: 4 / 3;
      border-radius: 8px;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12);
      overflow: hidden;
    }}
    .swatch-overlay {{
      position: absolute;
      inset: 0;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      padding: 0.75rem;
    }}
    .swatch-name {{
      font-size: 1rem;
      font-weight: 600;
      text-shadow: 0 1px 2px rgba(0, 0, 0, 0.15);
    }}
    .swatch-hex {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 0.85rem;
      opacity: 0.9;
    }}
    .swatch-rgb {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 0.75rem;
      opacity: 0.75;
    }}
    .swatch-index {{
      position: absolute;
      top: 0.5rem;
      right: 0.75rem;
      font-size: 0.7rem;
      opacity: 0.6;
    }}
    .empty {{
      text-align: center;
      color: #888;
      padding: 3rem;
    }}
    footer {{
      max-width: 1200px;
      margin: 2rem auto 0;
      padding-top: 1rem;
      border-top: 1px solid #ddd;
      color: #888;
      font-size: 0.85rem;
    }}
  </style>
</head>
<body>
  <header>
    <h1>{html_lib.escape(title)}</h1>
    <p class="meta">{color_count} {count_word}</p>
    {tip_line}
  </header>
  <main>
    <div class="swatches">
{swatches_html}
    </div>
  </main>
  <footer>
    Generated by hatchsvg palette_preview. View the source for the embedded JSON.
  </footer>
</body>
</html>
"""


def hex_lib_escape(s: str) -> str:
    """Wrap Python's html.escape to make the call site read naturally.

    The 'html_lib' import is `import html as html_lib` to avoid shadowing
    stdlib's html module. This wrapper is just `html_lib.escape(s)`.
    """
    return html_lib.escape(s)


def load_palette_json(path: Path | str) -> dict[str, Any]:
    """Load a palette JSON file. Raises ValueError on invalid format."""
    p = Path(path)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {p}: {e}") from e
    if not isinstance(data, dict):
        raise ValueError(f"{p}: top-level value must be a JSON object")
    if "colors" not in data or not isinstance(data["colors"], list):
        raise ValueError(f"{p}: missing 'colors' list")
    for i, color in enumerate(data["colors"]):
        if not isinstance(color, dict):
            raise ValueError(f"{p}: colors[{i}] must be an object")
        if "hex" not in color:
            raise ValueError(f"{p}: colors[{i}] missing 'hex'")
    return data


def write_palette_html(palette: dict[str, Any], output_path: Path | str) -> Path:
    """Render the palette as HTML and write it to output_path. Returns the path."""
    out = Path(output_path)
    out.write_text(render_palette_html(palette), encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    """CLI: python palette_preview.py PALETTE.json [OUTPUT.html]"""
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print(__doc__.split("\n\n")[0])
        return 1
    palette_path = Path(argv[0])
    output_path = Path(argv[1]) if len(argv) > 1 else palette_path.with_suffix(".html")

    try:
        palette = load_palette_json(palette_path)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except FileNotFoundError:
        print(f"Error: {palette_path} not found", file=sys.stderr)
        return 1

    write_palette_html(palette, output_path)
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
