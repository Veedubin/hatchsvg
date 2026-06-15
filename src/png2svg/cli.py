"""Command-line interface for png2svg."""

import argparse
import sys
from pathlib import Path

from png2svg import __version__
from png2svg.core import (
    HAS_RICH,
    _display_stats_table,
    get_run_configuration,
    process_image_to_hatched_svg,
    save_session,
)

_ERROR_HINTS = {
    "No layers produced.": (
        "No layers were produced. Try:\n"
        "  - Adding --no-skip-background (to include the background color)\n"
        "  - Lowering --min-pixels (e.g. --min-pixels 50)\n"
        "  - Checking your input image has visible content"
    ),
    "No visible pixels.": (
        "No visible pixels found in the image.\nCheck that your image is not fully transparent or all-black."
    ),
}


def main():
    """Entry point for the `png2svg` console script."""
    p = argparse.ArgumentParser(
        prog="png2svg",
        description="Convert PNG images to hatched SVG files for Cricut pen plotters.",
    )
    p.add_argument("input", help="Path to input PNG image")
    p.add_argument("output_svg", help="Path to output SVG file")
    p.add_argument(
        "--version",
        action="version",
        version=f"png2svg {__version__}",
    )
    p.add_argument(
        "--max-palette",
        type=int,
        default=12,
        help="Maximum number of palette colors (default: 12)",
    )
    p.add_argument(
        "--line-step",
        type=int,
        default=4,
        help="Line step size for hatching (default: 4)",
    )
    p.add_argument(
        "--alpha-threshold",
        type=int,
        default=10,
        help="Alpha threshold for visibility (default: 10)",
    )
    p.add_argument(
        "--min-pixels",
        type=int,
        default=200,
        help="Minimum pixels for a layer (default: 200)",
    )
    p.add_argument(
        "--stroke-width",
        type=float,
        default=None,
        help="Stroke width for hatch lines (default: auto)",
    )
    p.add_argument(
        "--outline-width",
        type=float,
        default=None,
        help="Outline stroke width (default: auto)",
    )
    p.add_argument(
        "--no-skip-background",
        action="store_true",
        help="Include background layer in output",
    )
    p.add_argument(
        "--white-medium",
        action="store_true",
        help="Use white as a medium color instead of skipping near-white",
    )
    p.add_argument(
        "--paper-white-soft",
        type=int,
        default=20,
        help="Soft threshold for paper white (default: 20)",
    )
    p.add_argument(
        "--scale",
        type=float,
        default=1.0,
        help="Scale factor for output (default: 1.0)",
    )
    p.add_argument(
        "--separate-outline",
        action="store_true",
        help="Generate separate outline paths",
    )
    p.add_argument("--palette-file", help="Path to marker palette JSON file")
    p.add_argument(
        "--naming-mode",
        choices=["inkscape", "flat"],
        default="inkscape",
        help="Layer naming mode (default: inkscape)",
    )
    p.add_argument(
        "--continuous-paths",
        action="store_true",
        help="Generate continuous serpentine paths to reduce pen plotter vibration",
    )
    p.add_argument(
        "--arc-radius",
        type=float,
        default=0.0,
        help="Add arc smoothing at row-end 180° reversals (0 = disabled)",
    )
    p.add_argument(
        "--save-session",
        action="store_true",
        help="Save session JSON for reproducible runs",
    )
    p.add_argument("--use-session", help="Load previous session JSON for reproducible output")
    p.add_argument("--progress", action="store_true", help="Show progress bars (requires rich)")
    p.add_argument("--stats", action="store_true", help="Show processing statistics")

    a = p.parse_args()

    # Check for Rich if --progress is requested
    if a.progress and not HAS_RICH:
        print("Warning: --progress requires 'rich' package. Install with: pip install rich")

    input_path = Path(a.input)
    output_path = Path(a.output_svg)

    # Load configuration — wrap with friendly error handling
    try:
        params, marker_palette, color_map, palette_file = get_run_configuration(a)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        print(
            "\nHint: check that your --palette-file is a valid JSON palette with a 'colors' list.",
            file=sys.stderr,
        )
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"Error: file not found: {e.filename}", file=sys.stderr)
        sys.exit(1)

    # Run Process — wrap with friendly error handling
    try:
        color_map_used, processing_stats = process_image_to_hatched_svg(
            input_path,
            output_path,
            params,
            marker_palette,
            color_map,
            show_progress=a.progress,
            show_stats=a.stats,
        )
    except SystemExit as e:
        # core.py raises SystemExit with cryptic strings; translate them
        msg = str(e.code) if e.code is not None else ""
        hint = _ERROR_HINTS.get(msg)
        if hint:
            print(f"Error: {msg}\n\n{hint}", file=sys.stderr)
        else:
            print(f"Error: {msg}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        # Palette loading / invalid input
        print(f"Error: {e}", file=sys.stderr)
        print(
            "\nHint: check that your --palette-file is a valid JSON palette with a 'colors' list.",
            file=sys.stderr,
        )
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"Error: file not found: {e.filename}", file=sys.stderr)
        sys.exit(1)

    # Display stats if requested
    if a.stats:
        _display_stats_table(processing_stats)

    if a.save_session:
        session_out_path = output_path.with_suffix(output_path.suffix + ".session.json")
        save_session(session_out_path, input_path, palette_file, params, color_map_used)


if __name__ == "__main__":
    main()
