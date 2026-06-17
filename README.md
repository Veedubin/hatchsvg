# png2svg

> **Turn raster images into pen-plotted hatched SVGs.**
> Optimized for Cricut, Axidraw, and any pen plotter that reads SVG.

[![CI](https://img.shields.io/badge/CI-passing-brightgreen)](https://github.com/Veedubin/hatchsvg/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/png2svg.svg)](https://pypi.org/project/png2svg/)

## What's new in 1.2.0

- **`--preview`** — open the output SVG in your default viewer after rendering
- **`--split-layers`** — write one SVG file per color layer (great for drying time between pen passes)
- **`--optimize-travel`** — reorder layers to minimize pen travel distance (saves plot time)
- **`--hatch-angles`** — different hatch angles per color layer (reduces visual moiré)
- **`--help` with examples** — see common invocations without leaving the terminal
- **Pure Python** — no C compiler required. Works on every platform pip supports.

## What it does

`png2svg` converts raster images (PNG, JPG, WebP, BMP, GIF, TIFF) into
hatched SVG vector files. Each color in the image becomes a separate SVG
layer, and each layer is filled with parallel hatch lines sized to match a
physical marker set. The output is optimized for **Cricut pen plotters** and
similar pen-plotting machines — it includes continuous serpentine paths, arc
smoothing at row ends, and connected-component chaining to minimize pen
lifts and ringing artifacts.

## Quickstart

```bash
pip install png2svg
png2svg photo.jpg drawing.svg --preset portrait
```

That's it. Open `drawing.svg` in Inkscape, Cricut Design Space, or any
vector editor. The output uses Inkscape-compatible layer names so each color
is selectable individually.

> **No SVG file? Try it on the included sample:**
> ```bash
> png2svg examples/scene.png /tmp/scene.svg --preset fast
> ```

## Why use png2svg?

| Problem with naive "image → SVG" converters | How png2svg solves it |
|---|---|
| Tracer output is dense, jittery, and pen plotter hates it. | Uses **scanline hatching** at a configurable line step — predictable pen motion. |
| Pen lifts between every line segment cause visible artifacts on Cricut. | **Serpentine continuous paths** chain rows together (zigzag motion). |
| Sharp 180° U-turns vibrate the pen carriage. | **Arc smoothing** at row-end reversals (configurable radius). |
| Color matching to physical markers is hard. | Built-in **Crayola** and **Jot** marker palettes; bring your own JSON. |
| Re-rendering with slightly different settings breaks reproducibility. | **`--save-session`** writes a JSON snapshot; **`--use-session`** replays it bit-for-bit. |

### Comparison with similar tools

| Tool | Input | Output | Pen-plotter aware | Marker palettes |
|------|-------|--------|-------------------|-----------------|
| **png2svg** | Raster | Hatched SVG (per-color layers) | **Yes** — serpentine + arc smoothing + chain components | **Yes** — Crayola, Jot, custom JSON |
| `potrace` | Bitmap | Smooth traced paths | No — fills entire region | No |
| `vtracer` | Bitmap | Smooth traced paths | Partial | No |
| `inkscape --trace-bitmap` | Bitmap | Smooth traced paths | No | No |
| `stipplegen`, `penkit`, etc. | Raster | Various pen-plotter art | Yes (each is its own niche) | No |

`png2svg` is the right choice when you want **stylized, low-pen-lift,
marker-accurate** output rather than a photo-faithful trace.

## Presets

Presets are named combinations of parameters tuned for common use cases.
Apply one with `--preset NAME`. You can still override any individual flag
on top of the preset.

| Preset | Use case |
|---|---|
| `portrait` | Photographic portraits, faces, soft gradients. Tight hatch + arc smoothing. |
| `logo` | Brand marks, flat colors, clean edges. Separate outline for crisp boundaries. |
| `line-art` | Pencil sketches, ink drawings, fine line illustrations. Low min-pixels preserves thin strokes. |
| `photo` | Detailed photos, landscapes, complex gradients. High palette + fine hatch. |
| `sketch` | Hand-drawn rough aesthetic. Wider hatch + visible U-turns. |
| `fast` | Quick preview. Few colors, wide hatch, no optimization. Renders in seconds. |

```bash
png2svg drawing.png out.svg --preset portrait
png2svg drawing.png out.svg --preset logo --max-palette 4  # override one flag
```

See `png2svg --help` for full preset descriptions.

## Installation

```bash
pip install png2svg
```

> **Pure Python**: png2svg has zero C extensions. No compiler needed,
> no `potracer`/`pypotrace` build failures. Works on Windows, macOS,
> Linux, ARM, anywhere Python 3.11+ runs.

Optional extras:

```bash
pip install png2svg[plot]    # progress bars (rich) + scipy for component chaining
```

For development:

```bash
git clone https://github.com/Veedubin/hatchsvg
cd png2svg
python -m venv .venv
.venv/bin/pip install -e ".[dev,plot]"
```

## CLI Reference

```
png2svg [OPTIONS] INPUT OUTPUT_SVG
```

| Flag | Default | Description |
|------|---------|-------------|
| `--preset NAME` | (none) | Apply a named preset (see table above). |
| `--max-palette N` | 12 | Maximum number of colors in the quantized output. |
| `--line-step N` | 4 | Spacing between hatch lines (pixels). Lower = denser. |
| `--alpha-threshold N` | 10 | Pixels with alpha below this are treated as transparent. |
| `--min-pixels N` | 200 | Minimum pixel count for a layer to be rendered. |
| `--stroke-width N` | auto | Stroke width for hatch lines (uses marker `tip_width_mm` if a palette is set). |
| `--outline-width N` | auto | Stroke width for outline paths. |
| `--no-skip-background` | (off) | Include the background color as a layer. |
| `--white-medium` | (off) | Use white as a medium color instead of skipping near-white. |
| `--paper-white-soft N` | 20 | Soft threshold for "paper white" detection. |
| `--scale N` | 1.0 | Scale factor for the output SVG. |
| `--separate-outline` | (off) | Generate outline paths as a separate SVG group. |
| `--palette-file FILE` | (none) | Path to a JSON marker palette. |
| `--naming-mode {inkscape,flat}` | inkscape | Layer naming convention. |
| `--continuous-paths` | (off) | Generate serpentine paths (huge pen-lift reduction). |
| `--arc-radius N` | 0.0 | Arc radius at U-turns (0 = disabled; try 3-5). |
| `--save-session` | (off) | Write a `*.session.json` for reproducibility. |
| `--use-session FILE` | (none) | Replay a previous session (overrides all flags). |
| `--preview` | (off) | Open output SVG in default viewer after render. |
| `--split-layers` | (off) | Write one SVG file per color layer. |
| `--optimize-travel` | (off) | Reorder layers to minimize pen travel distance. |
| `--hatch-angles ANGLES` | (none) | Comma-separated hatch angles per layer (degrees). |
| `--progress` | (off) | Show Rich progress bars (requires `pip install png2svg[plot]`). |
| `--stats` | (off) | Show processing statistics on completion. |
| `--version` | | Print the version and exit. |

## Cookbook

### Basic conversion

```bash
png2svg photo.jpg drawing.svg
```

### Recommended for Cricut pen plotters

The two flags that matter most:

```bash
png2svg photo.jpg drawing.svg --continuous-paths --arc-radius 5
```

- `--continuous-paths` chains rows into a single zigzag, eliminating the
  thousands of micro-pen-lifts that cause "ringing" artifacts.
- `--arc-radius 5` smooths the 180° U-turns with arc commands so the pen
  carriage doesn't slam to a stop.

### Use a bundled marker palette

```bash
png2svg photo.jpg drawing.svg --palette-file color_palettes/crayola_10ct_fine_line_classic.json
```

Bundled palettes: `crayola_10ct_fine_line_classic.json` and
`jot_20ct_washable_fineline.json`.

### Reproducible output

```bash
# First run: save the exact config used
png2svg photo.jpg drawing.svg --preset portrait --save-session

# Later: replay the exact same config
png2svg photo.jpg drawing2.svg --use-session drawing.svg.session.json
```

### Multi-format input

```bash
png2svg scan.webp out.svg        # WebP
png2svg photo.bmp out.svg        # BMP
png2svg photo.tiff out.svg       # TIFF
png2svg anim.gif out.svg         # GIF (uses first frame)
```

### Show processing stats

```bash
png2svg photo.jpg out.svg --progress --stats
```

Outputs a Rich table with image dimensions, color count, layer count,
pen-lift reduction percentage, and estimated plot time savings.

## Project Structure

```
png2svg/
├── src/
│   └── png2svg/
│       ├── __init__.py        # __version__
│       ├── __main__.py        # python -m png2svg
│       ├── core.py            # Algorithm (hatching, color matching, SVG emission)
│       ├── cli.py             # CLI + friendly error handling
│       └── presets.py         # Named presets (portrait, logo, line-art, photo, sketch, fast)
├── tests/
│   ├── unit/                  # 51 unit tests (segments, color, palette, session, hatch, presets)
│   ├── integration/           # 9 integration tests (golden file + CLI subprocess)
│   ├── fixtures/              # Golden SVG for regression
│   └── conftest.py
├── examples/                  # Sample input/output pairs (4 presets × 1 image)
├── color_palettes/            # Bundled Crayola + Jot palettes
├── .github/workflows/ci.yml   # CI: ruff + pytest on Linux+macOS × 3.11/3.12/3.13
├── pyproject.toml             # Build + project config
├── LICENSE                    # MIT
├── CHANGELOG.md               # Version history
├── REVIEW.md                  # Audit + release plan
├── PLAN.md                    # v1.0.0 implementation plan
└── README.md                  # This file
```

## Tech Stack

- **Python 3.11+** (uses PEP 604 unions, tomllib, modern type hints)
- **NumPy** — image array processing and color quantization
- **Pillow** — image decoding (PNG, JPG, WebP, BMP, GIF, TIFF)
- **dataclasses** — `RenderParams`, `LayerResult`, `StrokeStyle`
- **Rich** (optional) — progress bars and statistics table
- **scipy** (optional) — connected component detection for pen-lift reduction

## Development

```bash
# Run all tests with coverage
.venv/bin/pytest

# Lint
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src tests

# Build a wheel for local testing
.venv/bin/python -m build
```

See [PLAN.md](PLAN.md) for the v1.0.0 implementation plan and
[REVIEW.md](REVIEW.md) for the comprehensive audit, feature roadmap, and
30-day release timeline.

## Compatibility

- **Python:** 3.11, 3.12, 3.13 (CI matrix covers all three on Linux + macOS)
- **Input formats:** PNG, JPG, JPEG, WebP, BMP, GIF, TIFF, TIF
- **Output:** SVG 1.1 with Inkscape-compatible layer names
- **Consumers:** Inkscape, Cricut Design Space, Illustrator, browser preview

## License

MIT — see [LICENSE](LICENSE).

## Credits

Algorithm extracted from the original `png2svg.py` script. Bundled marker
palettes (Crayola, Jot) are trademarks of their respective owners and are
included only as practical examples.
