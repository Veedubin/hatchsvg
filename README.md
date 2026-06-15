# png2svg

> Convert PNG images to hatched SVG files for Cricut pen plotters.

[![CI](https://img.shields.io/github/actions/workflow/png2svg/png2svg/ci.yml?branch=main&label=CI)](https://github.com/png2svg/png2svg/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/png2svg.svg)](https://pypi.org/project/png2svg/)

## Overview

png2svg is a Python CLI tool that converts raster images to hatched SVG vector graphics. It uses marker color palettes to match colors and generates scanline-style hatching optimized for Cricut pen plotters.

## Installation

```bash
pip install png2svg
```

For optional features (progress bars, connected-component chaining):

```bash
pip install png2svg[plot]
```

For development:

```bash
git clone https://github.com/png2svg/png2svg
cd png2svg
python -m venv .venv
.venv/bin/pip install -e ".[dev,plot]"
```

## Usage

```bash
png2svg input.png output.svg
```

### CLI Options

| Flag | Description | Default |
|------|-------------|---------|
| `--palette FILE` | Color palette JSON file | Built-in palette |
| `--layers MODE` | Layer creation mode (auto, single, by-color) | auto |
| `--hatch-angle DEG` | Hatch angle in degrees | 45 |
| `--hatch-spacing PX` | Spacing between hatch lines | 5 |
| `--stroke-width PX` | Stroke width for hatch lines | 1 |
| `--continuous-paths` | Generate serpentine paths (reduces pen lifts) | Off |
| `--arc-radius PX` | Arc radius for U-turn smoothing | 0.0 |
| `--progress` | Show Rich progress bars | Off |
| `--stats` | Show detailed statistics table | Off |
| `--save-session FILE` | Save session parameters to JSON | - |
| `--load-session FILE` | Load session parameters from JSON | - |
| `--verbose` | Enable verbose output | Off |

### Examples

**Basic conversion:**
```bash
png2svg Bluey.png Bluey.svg
```

**With serpentine paths and arc smoothing (recommended for Cricut):**
```bash
png2svg Bluey.png Bluey.svg --continuous-paths --arc-radius 5
```

**Show progress and statistics:**
```bash
png2svg Bluey.png Bluey.svg --progress --stats
```

**Use custom color palette:**
```bash
png2svg image.png output.svg --palette color_palettes/my_palette.json
```

## Features

- **Scanline hatching** — Generates parallel lines at configurable angle and spacing
- **Color matching** — Matches image colors to marker palette colors
- **Multi-layer support** — Creates separate SVG layers per color
- **Serpentine paths** — Alternates direction per row to minimize pen lifts
- **Connected component chaining** — Groups nearby regions to reduce pen lifts (requires scipy)
- **Arc smoothing** — Smooths 180° U-turns with arc commands
- **Session save/load** — Reproducible conversions with JSON session files
- **Progress reporting** — Optional Rich progress bars and statistics

## Project Structure

```
png2svg/
├── src/
│   └── png2svg/
│       ├── __init__.py        # __version__
│       ├── core.py            # Algorithm (extracted from png2svg.py)
│       └── cli.py             # CLI entry point
├── tests/                     # pytest test suite
│   ├── unit/
│   └── integration/
├── color_palettes/            # JSON palette files
├── Bluey.png                  # Sample test image
├── Bluey-orig.png             # Original reference image
├── pyproject.toml             # Build + project config
├── LICENSE                    # MIT license
├── CHANGELOG.md               # Version history
├── REVIEW.md                  # Audit + release plan
├── PLAN.md                    # v1.0.0 implementation plan
└── README.md                  # This file
```

## Tech Stack

- Python 3
- NumPy — Image array processing
- Pillow (PIL) — Image I/O
- dataclasses — Data structures (RenderParams, LayerResult, StrokeStyle)
- JSON — Session and palette serialization
- Rich — Optional progress bars
- scipy — Optional connected component detection

## Output

Generates SVG files compatible with:
- Inkscape
- Cricut Design Space

## Cricut Optimization Notes

For best results on Cricut pen plotters:
1. Use `--continuous-paths` to reduce pen lifts
2. Use `--arc-radius 5` or higher for smooth U-turns
3. This eliminates "ringing" artifacts caused by thousands of disconnected segments

## Development

See [PLAN.md](PLAN.md) for the v1.0.0 release plan and [REVIEW.md](REVIEW.md) for the comprehensive audit, feature roadmap, and 30-day release timeline.

Run tests locally:

```bash
.venv/bin/pytest                  # Run all tests with coverage
.venv/bin/ruff check src tests    # Lint
```

## License

MIT — see [LICENSE](LICENSE).
