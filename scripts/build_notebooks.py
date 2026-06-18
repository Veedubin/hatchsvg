"""Build the three hatchsvg tutorial notebooks programmatically.

This script generates ``quickstart.ipynb``, ``explore.ipynb``, and
``craft.ipynb`` from the in-source definitions below. It exists so the
notebooks are reviewable as Python (not JSON), diffable in PRs, and
reproducible — running this script regenerates the .ipynb files
byte-for-byte.

The notebooks themselves are the user-facing artifact. This script is
the maintainer's tool. Users should open the .ipynb files in Jupyter
and never need to know this script exists.

Why programmatically?
---------------------
- The .ipynb JSON is ugly to write by hand
- Code is reviewable, JSON isn't
- We can lint the cell source with ruff the same way we lint src/

To run: ``python scripts/build_notebooks.py``
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict

import nbformat as nbf
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook


def md(*lines: str) -> Dict[str, Any]:
    """Build a markdown cell from one or more lines (each is a paragraph)."""
    return new_markdown_cell("\n\n".join(lines))


def code(*sources: str) -> Dict[str, Any]:
    """Build a code cell from one or more source strings (each is a cell)."""
    if len(sources) == 1:
        return new_code_cell(sources[0])
    raise ValueError("Use multiple `code(...)` calls for multiple cells")


def _assign_stable_ids(nb: nbf.NotebookNode, prefix: str) -> None:
    """Give every cell a deterministic ID based on its position.

    nbformat's ``new_code_cell``/``new_markdown_cell`` assign random hex
    IDs by default. When notebooks are re-executed via ``nbconvert``,
    those IDs get re-randomized, which produces a flood of meaningless
    diffs. This helper assigns ``f"{prefix}-cell-{i:02d}"`` IDs so
    subsequent re-executions produce byte-identical notebooks (assuming
    the cell content and output are stable).

    Args:
        nb: The notebook whose cells should be assigned IDs.
        prefix: Short notebook identifier (e.g. ``"qs"`` for quickstart).
    """
    for i, cell in enumerate(nb.cells):
        cell.id = f"{prefix}-cell-{i:02d}"


# ---------------------------------------------------------------------------
# Quickstart notebook — 5 cells, copy-paste-done
# ---------------------------------------------------------------------------


def build_quickstart() -> nbf.NotebookNode:
    """5-cell quickstart: install, load, quantize, render, save."""
    nb = new_notebook()
    nb.cells = [
        md(
            "# hatchsvg — Quickstart",
            "**Goal:** turn a PNG into a plotter-ready SVG in under 5 minutes.",
            "If anything is unclear, see `explore.ipynb` for the detailed walkthrough,",
            "or `craft.ipynb` for advanced usage.",
        ),
        md(
            "## Step 1 — Install",
            "```bash",
            "pip install hatchsvg matplotlib",
            "```",
            "Then start Jupyter:",
            "```bash",
            "jupyter lab",
            "```",
            "Open this notebook in Jupyter and run the cells one at a time.",
        ),
        md(
            "## Step 2 — Load an image",
            "Change `IMAGE_PATH` to point at your own image. PNG, JPG, WebP, BMP, GIF, and TIFF are all supported.",
            "If you don't have an image handy, the `Bluey.png` file in the repo root works.",
        ),
        code(
            "from pathlib import Path\n"
            "import notebook_helpers as nh\n"
            "\n"
            "IMAGE_PATH = '../Bluey.png'  # <-- change this to your own image\n"
            "img = nh.load_image(IMAGE_PATH)\n"
            "print(f'Loaded: {img.size[0]}x{img.size[1]} {img.mode}')\n"
            "nh.display_image(img)\n",
        ),
        md(
            "## Step 3 — Quantize (fast, ~300ms)",
            "The quantize step finds the dominant colors in the image.",
            "Try changing `MAX_PALETTE` to 4, 8, 16, or 24 and re-running this cell to see the effect.",
        ),
        code(
            "MAX_PALETTE = 12  # try 4 (cartoon), 8 (portrait), 16+ (photo)\n"
            "quant = nh.quantize_image(img, max_palette=MAX_PALETTE)\n"
            "preview = nh.render_quantized_preview(img, quant)\n"
            "nh.display_image(preview)\n"
            "from IPython.display import Markdown, display\n"
            "display(Markdown(nh.format_quantize_report(quant)))",
        ),
        md(
            "## Step 4 — Render the SVG (slow)",
            "This is the slow step — it generates the actual hatch paths. For a 1500×2000 image, expect 5-30 seconds.",
            "",
            "We start with the `fast` preset to validate the workflow quickly (3-5s).",
            "When you're happy with the color choices, re-run this cell with `preset='portrait'`",
            "for the dense, high-quality final version (30-60s).",
            "",
            "**Don't change parameters randomly and re-run** — this is the expensive step.",
            "Use Step 3 first to validate color choices.",
        ),
        code(
            "result = nh.render_svg(\n"
            "    img,\n"
            "    preset='fast',           # change to 'portrait' for the final version\n"
            "    palette=None,            # set to a palette dict to use physical markers\n"
            "    max_palette=MAX_PALETTE,\n"
            "    continuous_paths=True,   # chains rows to reduce pen lifts\n"
            "    arc_radius=5.0,          # smooth U-turns; 0 disables\n"
            ")\n"
            "from IPython.display import Markdown, display\n"
            "display(Markdown(nh.format_render_report(result)))",
        ),
        md(
            "## Step 5 — Preview and download",
            "Display the SVG inline (works in Jupyter, not on GitHub) and save a copy to disk.",
        ),
        code(
            "# Display inline\n"
            "nh.display_svg(result['svg_path'])\n"
            "\n"
            "# Save a copy with a friendlier name\n"
            "import shutil\n"
            "from pathlib import Path\n"
            "out_path = Path('my_drawing.svg')\n"
            "shutil.copy(result['svg_path'], out_path)\n"
            "print(f'Saved: {out_path.absolute()} ({out_path.stat().st_size:,} bytes)')",
        ),
        md(
            "## Next steps",
            "- Open `explore.ipynb` to understand what each step does (and why)",
            "- Open `craft.ipynb` for advanced usage: custom marker palettes, batch processing, reproducibility",
            "- Or use the CLI directly: `hatchsvg Bluey.png out.svg --preset portrait`",
        ),
    ]
    _assign_stable_ids(nb, "qs")
    return nb


# ---------------------------------------------------------------------------
# Explore notebook — 4 stages with explanations, 2a/2b/2c branches
# ---------------------------------------------------------------------------


def build_explore() -> nbf.NotebookNode:
    """4-stage walkthrough with explanations and 2a/2b/2c color matching branches."""
    nb = new_notebook()
    nb.cells = [
        md(
            "# hatchsvg — Explore",
            "**Goal:** understand what each step of the pipeline does, and how the parameters interact.",
            "Read the markdown cells — they explain *why*, not just *what*.",
            "When you see a `2a` / `2b` / `2c` heading, those are alternative paths; pick the one that matches your use case.",
        ),
        md(
            "## The 4 stages",
            "1. **Load** — read the image, convert to RGBA",
            "2. **Quantize** — find the dominant colors. **Three alternative paths (2a/2b/2c) depending on what kind of input you have.**",
            "3. **Render** — generate the hatch paths (the slow step, 30-60s)",
            "4. **Save & reproduce** — write the SVG and a session file so you can come back to this exact render later",
        ),
        md(
            "## Stage 1 — Load",
            "The image loader is dumb on purpose: it opens whatever Pillow can decode and converts to RGBA.",
            "The algorithm doesn't care about the original mode; it only cares about pixel values + alpha.",
            "If your image has a soft alpha channel (e.g. a PNG with feathered edges),",
            "the `alpha_threshold` parameter (in Stage 2) controls which pixels get rendered.",
        ),
        code(
            "from pathlib import Path\n"
            "import notebook_helpers as nh\n"
            "from IPython.display import display, Markdown\n"
            "\n"
            "img = nh.load_image('../Bluey.png')\n"
            "print(f'Loaded: {img.size[0]}x{img.size[1]} {img.mode}')\n"
            "nh.display_image(img)",
        ),
        md(
            "## Stage 2 — Quantize",
            "Quantization is the **fast** part of the pipeline (~200-300ms on a 1500x2000 image).",
            "It collapses thousands of unique colors into a small palette. The actual SVG hatching is much",
            "more expensive; doing quantization first lets you iterate on color choices quickly.",
            "",
            "There are three sub-paths depending on what you have:",
            "",
            "- **2a.** You have a physical marker set (Crayola, Jot, Copic, your own) — use palette matching",
            "- **2b.** You have a photo or complex image with no fixed pen set — use plain k-means quantize",
            "- **2c.** You have a logo or line art with very few colors — use aggressive quantize",
        ),
        md(
            "### Stage 2a — Quantize with a physical marker palette",
            "This is the path that makes hatchsvg a *physical-pen* tool, not a generic tracer.",
            "We map each detected color to the **closest marker you actually own**.",
            "",
            "Bundled palettes: `crayola_10ct_fine_line_classic`, `jot_20ct_washable_fineline`.",
            "You can also pass a path to a custom JSON palette (see `craft.ipynb`).",
        ),
        code(
            "palette = nh.load_palette('crayola_10ct_fine_line_classic')\n"
            'print(f\'Palette: {palette["brand"]} {palette["set_name"]}, {len(palette["colors"])} colors, tip {palette["tip_width_mm"]}mm\')\n'
            "\n"
            "quant = nh.quantize_image(img, max_palette=6)\n"
            "matched = nh.match_to_palette(quant, palette)\n"
            "\n"
            "preview = nh.render_quantized_preview(img, matched)\n"
            "nh.display_image(preview)\n"
            "display(Markdown(nh.format_quantize_report(matched)))",
        ),
        md(
            "**Reading the report:**",
            "- The `Hex` column is the color detected in your image",
            "- The marker mapping is `closest_marker()` — by default, HSV Euclidean distance",
            "- If the marker mapping is wrong, you'll see e.g. `#FFFFFF` mapped to `Gray` — that means your",
            "  lightest color is closer to gray than to any white-ish marker in the palette. Solutions:",
            "  - Increase `max_palette` so a true white is detected separately",
            "  - Use a palette that has a true white marker",
            "  - Skip palette matching (use Stage 2b) and accept the raw quantized colors",
        ),
        md(
            "### Stage 2b — Quantize without a marker palette (photos, complex images)",
            "If you don't have a fixed pen set, you can quantize to a generic palette and let the SVG",
            "use the raw colors. The pen plotter will still draw it, but you're not constrained to",
            "markers you actually own.",
            "",
            "This is the same as Stage 2a minus the `match_to_palette` call — simpler, but less 'real'.",
        ),
        code(
            "quant = nh.quantize_image(img, max_palette=8)\n"
            "preview = nh.render_quantized_preview(img, quant)\n"
            "nh.display_image(preview)\n"
            "display(Markdown(nh.format_quantize_report(quant)))",
        ),
        md(
            "### Stage 2c — Aggressive quantize for logos and line art",
            "For graphics with 2-4 distinct colors, force `max_palette=4` (or even less).",
            "This gives you the cleanest banded look. Pair with `--no-skip-background` if you want",
            "the background to be a layer (we set `skip_bg=False` here).",
        ),
        code(
            "quant = nh.quantize_image(img, max_palette=4, skip_bg=False)\n"
            "preview = nh.render_quantized_preview(img, quant)\n"
            "nh.display_image(preview)\n"
            "display(Markdown(nh.format_quantize_report(quant)))",
        ),
        md(
            "## Stage 3 — Render the hatch paths",
            "**This is the slow step.** It iterates pixel-by-pixel to generate the hatch lines.",
            "On a 1500x2000 image, expect 30-60 seconds.",
            "",
            "**Always validate your color choices in Stage 2 first.** Re-running Stage 3 with bad",
            "parameters wastes time. Use Stage 2's preview to confirm:",
            "1. The number of colors is right",
            "2. The marker mapping is right (if using a palette)",
            "3. The background is handled correctly (skipped or not, per your preference)",
        ),
        code(
            "# Use the matched quant from Stage 2a (palette-aware)\n"
            "quant = nh.quantize_image(img, max_palette=6)\n"
            "matched = nh.match_to_palette(quant, palette)\n"
            "\n"
            "result = nh.render_svg(\n"
            "    img,\n"
            "    preset='portrait',\n"
            "    palette=palette,\n"
            "    max_palette=6,\n"
            "    line_step=4,\n"
            "    continuous_paths=True,\n"
            "    arc_radius=5.0,\n"
            ")\n"
            "display(Markdown(nh.format_render_report(result)))\n"
            "nh.display_svg(result['svg_path'])",
        ),
        md(
            "## Stage 4 — Save & reproduce",
            "Save the SVG to a friendly name AND a session JSON. The session JSON captures every",
            "input — image path, params, palette, color mapping — so you can come back to this exact",
            "render months later by loading the session and re-running.",
            "",
            "Why bother? Because you'll iterate: 'this is close, but with a 6-color palette and arc_radius 3",
            "it's better' — and then lose the settings. The session file is the recipe.",
        ),
        code(
            "import shutil\n"
            "from pathlib import Path\n"
            "\n"
            "# Save the SVG with a friendlier name\n"
            "svg_out = Path('explore_output.svg')\n"
            "shutil.copy(result['svg_path'], svg_out)\n"
            "print(f'SVG: {svg_out.absolute()} ({svg_out.stat().st_size:,} bytes)')\n"
            "\n"
            "# Save the session (params + palette + color map) for reproducibility\n"
            "from hatchsvg.core import RenderParams\n"
            "session = nh.snapshot_session(\n"
            "    params=RenderParams(**result['params']),\n"
            "    palette=palette,\n"
            "    color_map=result['color_map_used'],\n"
            "    image_path='../Bluey.png',\n"
            ")\n"
            "session_path = Path('explore_session.json')\n"
            "nh.save_session_file(session, session_path)\n"
            "print(f'Session: {session_path.absolute()} ({session_path.stat().st_size:,} bytes)')",
        ),
        md(
            "## What now?",
            "You should now have an intuition for what each stage does. Open `craft.ipynb` for:",
            "- Custom marker palettes (your own pen set)",
            "- Per-color remap (force a specific marker for a specific color)",
            "- Batch processing (apply the same recipe to many images)",
            "- Comparison with vtracer / vpype / hatched (when to use what)",
        ),
    ]
    _assign_stable_ids(nb, "exp")
    return nb


# ---------------------------------------------------------------------------
# Craft notebook — advanced usage
# ---------------------------------------------------------------------------


def build_craft() -> nbf.NotebookNode:
    """Advanced usage: custom palettes, manual remap, sessions, batch processing."""
    nb = new_notebook()
    nb.cells = [
        md(
            "# hatchsvg — Craft",
            "**Goal:** fine-grained control. Custom marker palettes, per-color remap, batch processing, comparison with adjacent tools.",
            "If you haven't read `quickstart.ipynb` and `explore.ipynb`, do that first — this notebook assumes you understand the 4 stages.",
        ),
        md(
            "## Contents",
            "1. Custom marker palettes (your own pen set)",
            "2. Per-color remap (force a specific marker for a specific detected color)",
            "3. Render with the remap applied",
            "4. Saving and reloading sessions (reproducibility)",
            "5. Batch processing (apply the same recipe to many images)",
            "6. Parameter deep-dive: what each setting does and how it affects the output",
            "7. Comparison with adjacent tools (vtracer, vpype, hatched, plottter)",
            "8. Troubleshooting",
        ),
        md(
            "## 1. Custom marker palettes",
            "A palette is a JSON file with brand, set, optional tip width, and a list of colors:",
            "```json",
            "{",
            '  "brand": "My Pens",',
            '  "set_name": "Fineliner 12",',
            '  "tip_width_mm": 0.4,',
            '  "colors": [',
            '    {"name": "Red",    "hex": "#E63946", "rgb": [230, 57, 70]},',
            '    {"name": "Blue",   "hex": "#1D3557", "rgb": [29, 53, 87]},',
            "    ...",
            "  ]",
            "}",
            "```",
            "`rgb` is optional; if you provide `hex` we parse it. `tip_width_mm` controls the default",
            "stroke width (your pen's physical tip).",
        ),
        code(
            "import json\n"
            "from pathlib import Path\n"
            "import notebook_helpers as nh\n"
            "\n"
            "my_palette = {\n"
            '    "brand": "My Pens",\n'
            '    "set_name": "Fineliner 12",\n'
            '    "tip_width_mm": 0.4,\n'
            '    "colors": [\n'
            '        {"name": "Red",    "hex": "#E63946", "rgb": [230, 57, 70]},\n'
            '        {"name": "Orange", "hex": "#F4A261", "rgb": [244, 162, 97]},\n'
            '        {"name": "Yellow", "hex": "#E9C46A", "rgb": [233, 196, 106]},\n'
            '        {"name": "Green",  "hex": "#2A9D8F", "rgb": [42, 157, 143]},\n'
            '        {"name": "Blue",   "hex": "#264653", "rgb": [38, 70, 83]},\n'
            '        {"name": "Black",  "hex": "#000000", "rgb": [0, 0, 0]},\n'
            "    ],\n"
            "}\n"
            "\n"
            "palette_path = Path('my_palette.json')\n"
            "palette_path.write_text(json.dumps(my_palette, indent=2))\n"
            "print(f'Wrote {palette_path.absolute()}')\n"
            "\n"
            "# Now load it via the helper\n"
            "loaded = nh.load_palette(str(palette_path))\n"
            'print(f\'Loaded: {loaded["brand"]} {loaded["set_name"]}, {len(loaded["colors"])} colors, tip {loaded["tip_width_mm"]}mm\')',
        ),
        md(
            "## 2. Per-color remap",
            "Sometimes `closest_marker()` makes a bad call — e.g. a near-white detected in the image",
            "maps to a gray marker because the palette has no true white. The fix is to **force the",
            "mapping for that specific color**.",
            "",
            "This is also useful when you have two near-identical pens and want to make sure a specific",
            "shade always uses the lighter one (or whatever your preference is).",
        ),
        code(
            "import notebook_helpers as nh\n"
            "from IPython.display import display, Markdown\n"
            "\n"
            "img = nh.load_image('../Bluey.png')\n"
            "palette = nh.load_palette('crayola_10ct_fine_line_classic')\n"
            "quant = nh.quantize_image(img, max_palette=6)\n"
            "matched = nh.match_to_palette(quant, palette)\n"
            "\n"
            "# Before remap: see the auto-mappings\n"
            "print('Before remap:')\n"
            "for c in matched['color_info']:\n"
            '    print(f\'  {c["hex"]} -> {c["marker_hex"]} ({c["marker_name"]})\')\n'
            "\n"
            "# Find the detected color we want to remap (e.g. the lightest one)\n"
            "lightest = min(matched['color_info'], key=lambda c: sum(c['rgb']))\n"
            "print(f'\\nRemapping lightest color: {lightest[\"hex\"]}')\n"
            "\n"
            "# Build a remap dict: {color_id: marker_index_in_palette}\n"
            "remap = {lightest['idx']: 0}  # force map to the first marker in the palette\n"
            "\n"
            "# Apply the remap by rebuilding color_info\n"
            "remapped = []\n"
            "for c in matched['color_info']:\n"
            "    if c['idx'] in remap:\n"
            "        marker = palette['colors'][remap[c['idx']]]\n"
            "        marker_rgb = marker.get('rgb', [int(marker['hex'][i:i+2], 16) for i in (1, 3, 5)])\n"
            "        c = {**c, 'marker_name': marker['name'], 'marker_hex': marker['hex'], 'marker_rgb': tuple(marker_rgb)}\n"
            "    remapped.append(c)\n"
            "matched['color_info'] = remapped\n"
            "\n"
            "print('\\nAfter remap:')\n"
            "for c in matched['color_info']:\n"
            '    print(f\'  {c["hex"]} -> {c["marker_hex"]} ({c["marker_name"]})\')',
        ),
        md(
            "## 3. Render with the remap applied",
            "Before we save the session, let's actually render the SVG with the remap in place.",
            "This is the slow step — expect 5-30 seconds depending on the image.",
            "We use the `fast` preset to keep render time low; the goal here is to validate the workflow,",
            "not produce a final plot. Re-run with `portrait` for higher quality.",
        ),
        code(
            "result = nh.render_svg(\n"
            "    img,\n"
            "    preset='fast',         # use 'portrait' for the final version\n"
            "    palette=palette,        # the marker palette we loaded above\n"
            "    max_palette=6,\n"
            "    continuous_paths=True,\n"
            "    arc_radius=5.0,\n"
            ")\n"
            "from IPython.display import Markdown, display\n"
            "display(Markdown(nh.format_render_report(result)))\n"
            "nh.display_svg(result['svg_path'])",
        ),
        md(
            "## 4. Saving and reloading sessions",
            "Sessions capture: image path, params, palette, color mapping. They're a recipe for",
            "reproducing an exact render later. Save them alongside the SVG; reload them when you",
            "want to iterate without losing the working version.",
        ),
        code(
            "from pathlib import Path\n"
            "from hatchsvg.core import RenderParams\n"
            "import notebook_helpers as nh\n"
            "import json\n"
            "\n"
            "# Save a session\n"
            "session = nh.snapshot_session(\n"
            "    params=RenderParams(**result['params']),\n"
            "    palette=palette,\n"
            "    color_map=result['color_map_used'],\n"
            "    image_path='../Bluey.png',\n"
            ")\n"
            "session_path = Path('craft_session.json')\n"
            "nh.save_session_file(session, session_path)\n"
            "print(f'Saved: {session_path.absolute()}')\n"
            "print(f'Contains: {list(session.keys())}')\n"
            "\n"
            "# Reload it later\n"
            "reloaded = nh.load_session_file(session_path)\n"
            "print('\\nReloaded session:')\n"
            "print(f'  image: {reloaded[\"image\"]}')\n"
            'print(f\'  params: max_palette={reloaded["params"]["max_palette"]}, line_step={reloaded["params"]["line_step"]}\')\n'
            'print(f\'  palette: {reloaded["palette"]["brand"]} ({len(reloaded["palette"]["colors"])} colors)\')\n'
            "print(f'  version: hatchsvg {reloaded[\"version\"]}')",
        ),
        md(
            "## 5. Batch processing",
            "Apply the same recipe to many images. The trick is to wrap the slow stage in a loop and",
            "save the SVG to a per-image path. This is the same logic the CLI uses internally; doing it",
            "in a notebook lets you customize per-image if needed.",
        ),
        code(
            "from pathlib import Path\n"
            "\n"
            "# Find all PNGs in a directory (e.g. a sticker pack)\n"
            "source_dir = Path('../examples')  # change to your image directory\n"
            "output_dir = Path('batch_output')\n"
            "output_dir.mkdir(exist_ok=True)\n"
            "\n"
            "image_paths = sorted(source_dir.glob('*.png'))\n"
            "print(f'Found {len(image_paths)} images')\n"
            "\n"
            "results = []\n"
            "for img_path in image_paths:\n"
            "    print(f'\\n--- {img_path.name} ---')\n"
            "    img = nh.load_image(img_path)\n"
            "    result = nh.render_svg(\n"
            "        img,\n"
            "        preset='fast',  # use 'fast' for batch — quality matters less when iterating\n"
            "        palette=palette,\n"
            "        max_palette=4,\n"
            "        line_step=8,\n"
            "    )\n"
            "\n"
            "    # Save with matching name\n"
            "    out_path = output_dir / f'{img_path.stem}.svg'\n"
            "    out_path.write_text(result['svg_path'].read_text())\n"
            "    print(f'  -> {out_path.name} ({out_path.stat().st_size:,} bytes)')\n"
            "    results.append({'image': img_path.name, 'svg': out_path.name})\n"
            "\n"
            "print(f'\\nBatch complete: {len(results)} images')",
        ),
        md(
            "## 6. Parameter deep-dive",
            "What each RenderParams field does and how it affects the output. Skip to the section you need.",
        ),
        md(
            "### `max_palette` (default 12)",
            "Maximum number of colors in the quantized image. Lower = more banded (cartoon look),",
            "higher = more detail.",
            "",
            "Try: 2-3 for very simple line art, 4-6 for logos, 8-12 for portraits, 16+ for photos.",
            "Beyond ~16, the SVG gets slow to render and the pen plotter has trouble — markers",
            "are physically limited.",
        ),
        md(
            "### `line_step` (default 4)",
            "Spacing between hatch lines in pixels. Lower = denser hatch, slower to render, harder",
            "for the pen to follow. Higher = sparser, faster, but may miss detail.",
            "",
            "Rule of thumb: 1.5x to 2x your marker's stroke width in image pixels. For a 0.5mm",
            "tip on a 1500px-wide image, try 4-6.",
        ),
        md(
            "### `continuous_paths` (default off)",
            "Chain rows of hatching into a single zigzag path. **Huge** reduction in pen lifts (often 50-80%).",
            "Always enable for Cricut — the 'ringing' artifact you see without this is from thousands",
            "of micro-pen-lifts per color layer.",
        ),
        md(
            "### `arc_radius` (default 0)",
            "Smooths the 180° U-turns at the end of each row with arc commands. Values 3-5 are typical.",
            "**Requires `continuous_paths=True`** — arcs only make sense at the end of chained rows.",
            "Set to 0 to disable and use sharp corners.",
        ),
        md(
            "### `min_pixels` (default 200)",
            "Skip layers with fewer than this many pixels. Useful for filtering out JPEG artifacts",
            "and tiny specks. Set to 0 to keep everything; raise to 1000+ to aggressively clean up",
            "noisy images.",
        ),
        md(
            "### `white_medium` (default off)",
            "When True, 'white-ish' colors are rendered as a medium tone (not skipped as background).",
            "**Set True for photos** — you want pen strokes on light skin and pale highlights. **Set",
            "False for line art** — white is paper, not a color.",
        ),
        md(
            "### `skip_bg` / `paper_white_soft`",
            "`skip_bg=True` excludes the most-common near-white color as the paper background.",
            "`paper_white_soft` (0-255) controls the threshold for 'near white': values 20-30 are typical.",
            "Lower = stricter (only true white is paper); higher = more permissive (cream backgrounds count).",
        ),
        md(
            "### `separate_outline` (default off)",
            "Emit outline paths as a separate SVG group from the hatch fills. Use this if you want",
            "to assign the outline a different pen (e.g. a black fineliner for crisp edges, while the",
            "fills are colored markers).",
        ),
        md(
            "## 7. Comparison with adjacent tools",
            "There are several other open-source pen-plotter tools. Use this table to pick the right one.",
            "",
            "| Tool | Use when | Skip when |",
            "|------|----------|-----------|",
            "| **hatchsvg** | You want hatched SVG with **physical marker awareness** and a Cricut-friendly output | You want a smooth photo trace (use vtracer); you want grayscale halftone (use hatched) |",
            "| **vtracer** (MIT) | You want a smooth multi-color trace of a photo, output goes to vpype for optimization | You want hatched fills (vtracer doesn't hatch) |",
            "| **vpype + hatched** (MIT) | You already have an SVG and want to add hatching; or you want grayscale halftone | You want color, physical-marker awareness, or a Cricut-ready output |",
            "| **plottter** (MIT) | You want a full desktop app with AI masks, dithering, and many generator styles | You want a simple CLI + notebook workflow with no AI dependencies |",
            "| **saxi** (AGPL) | You have an AxiDraw and want a driver for it (note: AGPL license) | You want raster-to-vector (out of scope) |",
            "",
            "**Common workflow:** hatchsvg → Inkscape (manual tweaks) → vpype (plot optimization) → Cricut Design Space or your plotter's driver.",
        ),
        md(
            "## 8. Troubleshooting",
            "",
            "**'No layers produced'**",
            "- Lower `--min-pixels` (try 50)",
            "- Add `--no-skip-background` to include the background as a layer",
            "- Check that your image isn't all-transparent or all-black",
            "",
            "**Colors don't match my expectations**",
            "- The quantize step is in HSV Euclidean; for perceptually-accurate matching, you'd",
            "  need Lab color space (not yet implemented; see issues)",
            "- Try increasing `max_palette` — fewer colors means more aggressive merging",
            "- Check `white_medium` — if False, near-white pixels are skipped",
            "",
            "**Render is too slow**",
            "- Use the `fast` preset for iteration; `portrait` only for the final render",
            "- Lower `max_palette` (4-6 vs 12+ has a big effect)",
            "- Increase `line_step` (8 vs 4 cuts hatch time in half)",
            "- Resize the image first: `img.resize((img.size[0] // 2, img.size[1] // 2))`",
            "",
            "**SVG opens but the plotter jitters**",
            "- Enable `continuous_paths=True` (this is the #1 cause of jitter)",
            "- Set `arc_radius=3.0` to `5.0` for smoother U-turns",
            "- Some plotters want `stroke_width` lower than the marker's spec; try halving it",
        ),
        md(
            "## Where to go from here",
            "- Read the source: `src/hatchsvg/core.py` (the algorithm)",
            "- Read `src/hatchsvg/presets.py` (preset definitions)",
            "- Read `src/hatchsvg/cli.py` (the CLI — the notebook helpers wrap the same functions)",
            "- File an issue: https://github.com/Veedubin/hatchsvg/issues",
        ),
    ]
    _assign_stable_ids(nb, "craft")
    return nb


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the hatchsvg tutorial notebooks")
    parser.add_argument(
        "--out-dir",
        default=".",
        help="Output directory (default: current directory, intended to be notebooks/)",
    )
    parser.add_argument(
        "--only",
        choices=["quickstart", "explore", "craft", "all"],
        default="all",
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    builders = {
        "quickstart": ("quickstart.ipynb", build_quickstart),
        "explore": ("explore.ipynb", build_explore),
        "craft": ("craft.ipynb", build_craft),
    }
    targets = list(builders.keys()) if args.only == "all" else [args.only]

    for name in targets:
        filename, builder = builders[name]
        nb = builder()
        # Make the kernel Python 3
        nb.metadata = {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.11",
                "mimetype": "text/x-python",
                "file_extension": ".py",
                "codemirror_mode": {"name": "ipython", "version": 3},
                "pygments_lexer": "ipython3",
            },
        }
        path = out_dir / filename
        nbf.write(nb, path)
        cell_count = len(nb.cells)
        md_count = sum(1 for c in nb.cells if c.cell_type == "markdown")
        code_count = sum(1 for c in nb.cells if c.cell_type == "code")
        print(f"Wrote {path}: {cell_count} cells ({md_count} markdown, {code_count} code)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
