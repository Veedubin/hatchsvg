"""Command-line interface for hatchsvg."""

import argparse
import re
import sys
import webbrowser
from pathlib import Path

from hatchsvg import __version__
from hatchsvg.core import (
    HAS_RICH,
    _display_stats_table,
    get_run_configuration,
    process_image_to_hatched_svg,
    render_single_layer_svg,
    save_session,
)
from hatchsvg.presets import PRESETS, list_presets

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

# Input formats Pillow can open (the actual decode happens in core.py via PIL.Image.open)
SUPPORTED_INPUT_FORMATS = (
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".gif",
    ".tiff",
    ".tif",
)


def _sanitize_filename(name: str) -> str:
    """Sanitize a marker name for use in filenames.

    Lowercase, replace whitespace and any char not in [a-z0-9_-] with _,
    collapse runs of underscores.
    """
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9_-]", "_", name)
    name = re.sub(r"_+", "_", name)
    return name or "unnamed"


def _write_split_layers(
    input_path: Path,
    output_path: Path,
    params,
    marker_palette,
    color_map,
    color_map_used: dict,
) -> None:
    """Write one SVG file per color layer alongside the main output."""
    from hatchsvg.core import RenderParams

    stem = output_path.stem
    out_dir = output_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    # Track used slugs to handle collisions (e.g. two layers named "blue")
    used_slugs: dict[str, int] = {}
    layer_idx = 0

    for pal_hex, entry in color_map_used.items():
        marker_name = entry.get("marker_name", "unnamed") or "unnamed"
        slug = _sanitize_filename(marker_name)

        # Handle slug collisions by appending -N
        if slug in used_slugs:
            used_slugs[slug] += 1
            slug = f"{slug}-{used_slugs[slug]}"
        else:
            used_slugs[slug] = 1

        # Determine hatch_angle for this layer
        if params.hatch_angles:
            angles = params.hatch_angles
            angle = angles[min(layer_idx, len(angles) - 1)] if angles else 0.0
        else:
            angle = 0.0

        # Build per-layer params
        layer_params = RenderParams(**{**params.__dict__, "hatch_angles": params.hatch_angles, "hatch_angle": angle})

        # Compute the layer index format (2 digits for <100 layers, 3 for 100+)
        idx_fmt = "03" if len(color_map_used) > 99 else "02"
        filename = f"{stem}_{layer_idx:{idx_fmt}}_{slug}.svg"
        layer_path = out_dir / filename

        svg_content = render_single_layer_svg(
            input_path=input_path,
            params=layer_params,
            marker_palette=marker_palette,
            color_map=color_map,
            pal_hex=pal_hex,
            output_path=layer_path,
        )
        if svg_content is not None:
            print(f"  Split layer: {layer_path}")

        layer_idx += 1


def main():
    """Entry point for the `hatchsvg` console script."""
    formats_help = " | ".join(SUPPORTED_INPUT_FORMATS)
    _examples = (
        "\nExamples:\n"
        "```\n"
        "# Quick default conversion\n"
        "hatchsvg photo.jpg out.svg\n"
        "\n"
        "# Preset with override\n"
        "hatchsvg drawing.png out.svg --preset logo --line-step 2\n"
        "\n"
        "# Custom marker palette\n"
        "hatchsvg photo.jpg out.svg --palette-file markers.json\n"
        "\n"
        "# Split layers and preview\n"
        "hatchsvg photo.jpg out.svg --split-layers --preview\n"
        "\n"
        "# Session reproducibility\n"
        "hatchsvg photo.jpg out.svg --save-session && \\\n"
        "  hatchsvg photo.jpg out2.svg --use-session out.svg.session.json\n"
        "```\n"
    )

    p = argparse.ArgumentParser(
        prog="hatchsvg",
        description=(
            f"Convert images to hatched SVG files for Cricut pen plotters. Accepts input formats: {formats_help}."
        ),
        epilog=(
            "Presets:\n"
            + "\n".join(f"  {name}: {spec['description']}" for name, spec in sorted(PRESETS.items()))
            + "\n"
            + _examples
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("input", help=f"Path to input image ({formats_help})")
    p.add_argument("output_svg", help="Path to output SVG file")
    p.add_argument(
        "--preset",
        choices=list_presets(),
        default=None,
        help=(
            "Named preset for common use cases (portrait, logo, line-art, photo, sketch, fast). "
            "Preset values are applied first, then any explicit flags override them."
        ),
    )
    p.add_argument(
        "--version",
        action="version",
        version=f"hatchsvg {__version__}",
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
    p.add_argument(
        "--preview",
        action="store_true",
        help="Open output SVG in default viewer after render",
    )
    p.add_argument(
        "--split-layers",
        action="store_true",
        help="Also write one SVG file per color layer to <stem>_<NN>_<color>.svg",
    )
    p.add_argument(
        "--optimize-travel",
        action="store_true",
        help="Reorder layers to minimize pen-up travel distance",
    )
    p.add_argument(
        "--hatch-angles",
        type=str,
        default=None,
        help=(
            "Comma-separated hatch angles per layer in degrees. "
            "If fewer angles than layers, the last value is reused. "
            "Example: --hatch-angles=0,45,90,135"
        ),
    )

    a = p.parse_args()

    # Attach the parser to args so core._extract_explicit_args can diff
    # explicit CLI flags against parser defaults (used by --preset).
    a._hatchsvg_parser = p  # type: ignore[attr-defined]

    # Check for Rich if --progress is requested
    if a.progress and not HAS_RICH:
        print("Warning: --progress requires 'rich' package. Install with: pip install rich")

    input_path = Path(a.input)
    output_path = Path(a.output_svg)

    # Validate input format early with a friendly hint before Pillow tries to open it
    if input_path.suffix.lower() not in SUPPORTED_INPUT_FORMATS:
        print(
            f"Error: unsupported input format '{input_path.suffix}'.",
            file=sys.stderr,
        )
        print(
            f"Supported formats: {', '.join(SUPPORTED_INPUT_FORMATS)}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Parse --hatch-angles into a list of floats
    hatch_angles: list[float] = []
    if a.hatch_angles is not None:
        raw = a.hatch_angles.strip()
        if raw:
            try:
                hatch_angles = [float(v) for v in raw.split(",")]
            except ValueError:
                print(
                    f"Error: --hatch-angles must be comma-separated numbers, got: {a.hatch_angles!r}",
                    file=sys.stderr,
                )
                sys.exit(1)
        # Empty string → treat as default (no rotation)

    # Load configuration — wrap with friendly error handling.
    # If --preset is set, the preset's overrides are applied as a base, then
    # any explicit CLI flags on top of it. So `hatchsvg img out --preset logo
    # --line-step 2` gives a logo preset with line_step=2.
    try:
        params, marker_palette, color_map, palette_file = get_run_configuration(a, preset_name=a.preset)
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

    # Override hatch_angles on params if the user specified --hatch-angles
    if hatch_angles:
        params.hatch_angles = hatch_angles

    # Skip background by default (the dominant color at the image border).
    # --no-skip-background disables this for users who want the full image
    # hatched (e.g. photo mosaics where the "background" is itself a color
    # they want plotted).
    if not a.no_skip_background:
        params.skip_bg = True

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
            optimize_travel=a.optimize_travel,
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

    # --split-layers: write one SVG per color layer
    if a.split_layers:
        _write_split_layers(
            input_path=input_path,
            output_path=output_path,
            params=params,
            marker_palette=marker_palette,
            color_map=color_map,
            color_map_used=color_map_used,
        )

    if a.save_session:
        session_out_path = output_path.with_suffix(output_path.suffix + ".session.json")
        save_session(session_out_path, input_path, palette_file, params, color_map_used)

    # --preview: open the main output SVG in the default viewer
    if a.preview:
        try:
            uri = output_path.resolve().as_uri()
            opened = webbrowser.open(uri)
            if not opened:
                print(f"Warning: could not open browser for {uri}", file=sys.stderr)
        except Exception as exc:
            print(f"Warning: --preview failed: {exc}", file=sys.stderr)
        if a.split_layers:
            print("Note: --preview opens the main output only (not split-layer files)", file=sys.stderr)


if __name__ == "__main__":
    main()
