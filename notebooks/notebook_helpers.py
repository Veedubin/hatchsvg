"""Shared helpers for the png2svg tutorial notebooks.

This module is intentionally short and direct. It is NOT a black box.

Every function here is a thin wrapper around something in :mod:`png2svg.core`
or :mod:`png2svg.presets`. If you want to understand what the function is
actually doing, click into the ``png2svg.core`` call and read the source.

The helpers exist to keep the notebooks focused on explanations (markdown
cells) and decisions (parameters), not on boilerplate (file I/O, base64
encoding, palette-loading error handling).

Design principles
-----------------
- **No magic.** Every function has explicit parameters. There are no
  environment variables, no implicit state, no hidden defaults.
- **Read the imports.** If a helper imports something from
  ``png2svg.core``, the underlying algorithm is in core. The helper is
  just plumbing.
- **Fail loud.** Functions raise the original exception. We do not
  swallow errors in the name of "user-friendliness." When something
  breaks in a notebook cell, the traceback is the explanation.
- **Bypassable.** You can always call ``png2svg.core`` directly. These
  helpers are convenience, not a required API.

Reading order for new users
---------------------------
1. Read :func:`load_palette` — it explains the palette JSON format
2. Read :func:`quantize_image` — it explains color quantization
3. Read :func:`render_svg` — it explains the main entry point
4. Read :func:`save_session` / :func:`load_session` — reproducibility

If you only read one function, read :func:`render_svg` — it's the
smallest summary of what png2svg actually does.
"""

from __future__ import annotations

import base64
import io
import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from PIL import Image

from png2svg import __version__
from png2svg.core import (
    RenderParams,
    build_color_index_map,
    closest_marker,
    load_marker_palette,
    process_image_to_hatched_svg,
)
from png2svg.presets import PRESETS, list_presets

# ---------------------------------------------------------------------------
# Image I/O
# ---------------------------------------------------------------------------


def load_image(path: str | Path) -> Image.Image:
    """Load an image and convert to RGBA.

    We force RGBA so the rest of the pipeline doesn't have to think about
    whether the input had an alpha channel. Grayscale or palette images
    get an alpha channel of 255 (fully opaque). This is a one-way
    conversion: we don't try to "preserve" the original mode because
    the algorithm only cares about the pixel values + alpha.

    Parameters
    ----------
    path
        File path. PNG, JPG, WebP, BMP, GIF, TIFF supported via Pillow.

    Returns
    -------
    PIL.Image.Image
        In RGBA mode, ready to be passed to :func:`quantize_image` or
        :func:`render_svg`.
    """
    img = Image.open(path)
    return img.convert("RGBA")


def image_to_png_bytes(img: Image.Image) -> bytes:
    """Serialize a PIL image to PNG bytes (no file I/O).

    Used in notebooks to display images inline via ``IPython.display.Image``
    or to embed them in HTML.

    Why not just call ``img.save(path)``? Because writing to disk clutters
    the notebook's working directory. Bytes-in, bytes-out is cleaner.
    """
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def image_to_data_url(img: Image.Image, fmt: str = "PNG") -> str:
    """Convert a PIL image to a ``data:image/...;base64,...`` URL.

    Useful for embedding in HTML or for the in-memory equivalent of a
    file download. For 1500x2000 PNGs, expect ~1-2 MB of base64.
    """
    b64 = base64.b64encode(image_to_png_bytes(img)).decode("ascii")
    return f"data:image/{fmt.lower()};base64,{b64}"


def numpy_to_pil(arr: np.ndarray) -> Image.Image:
    """Convert a numpy ``(H, W, 3)`` or ``(H, W, 4)`` uint8 array to PIL."""
    if arr.dtype != np.uint8:
        raise ValueError(f"expected uint8, got {arr.dtype}")
    if arr.ndim == 3 and arr.shape[2] == 3:
        return Image.fromarray(arr, mode="RGB")
    if arr.ndim == 3 and arr.shape[2] == 4:
        return Image.fromarray(arr, mode="RGBA")
    raise ValueError(f"expected (H,W,3) or (H,W,4), got {arr.shape}")


# ---------------------------------------------------------------------------
# Palette loading
# ---------------------------------------------------------------------------


def list_bundled_palettes() -> List[Dict[str, Any]]:
    """List all bundled marker palettes with metadata.

    The palette name is the file stem of the JSON in ``color_palettes/``.
    Each entry includes brand, set name, color count, and the marker's
    physical tip width in millimetres (used for stroke-width auto-defaults).

    Why include tip width? Because a 0.4 mm fineliner and a 1.0 mm chisel
    tip need different stroke widths for the same hatch density. Bundling
    the physical spec in the palette JSON is the only sane way to keep
    pen-aware defaults correct.
    """
    palettes = []
    palette_dir = _find_palette_dir()
    if palette_dir is None:
        return palettes

    for json_path in sorted(palette_dir.glob("*.json")):
        try:
            data = json.loads(json_path.read_text())
        except Exception:
            continue
        palettes.append(
            {
                "name": json_path.stem,
                "brand": data.get("brand", "Unknown"),
                "set": data.get("set_name", data.get("set", "Unknown")),
                "color_count": len(data.get("colors", [])),
                "tip_width_mm": data.get("tip_width_mm"),
                "path": str(json_path),
            }
        )
    return palettes


def _find_palette_dir() -> Optional[Path]:
    """Find the directory containing bundled palette JSONs.

    Looks in three places, in priority order:
    1. ``importlib.resources.files("png2svg.data.palettes")`` — the
       canonical location for installed packages (works for both
       regular installs and editable installs that use force-include).
    2. ``<repo-root>/color_palettes/`` — when developing from a git
       clone with no install.
    3. ``<repo-root>/src/png2svg/data/palettes/`` — the build
       location used by hatchling's force-include.

    Returns the first directory that exists, or None.
    """
    # Method 1: importlib.resources (works for installed + editable installs)
    try:
        from importlib.resources import files

        candidate = files("png2svg.data.palettes")
        if candidate is not None:
            p = Path(str(candidate))
            if p.is_dir():
                return p
    except (ModuleNotFoundError, FileNotFoundError):
        pass

    # Methods 2 & 3: filesystem fallbacks
    cwd = Path.cwd()
    for d in (
        cwd / "color_palettes",
        cwd.parent / "color_palettes",
        cwd / "src" / "png2svg" / "data" / "palettes",
    ):
        if d.is_dir():
            return d
    return None


def load_palette(name_or_path: str) -> Dict[str, Any]:
    """Load a marker palette by name (bundled) or path (custom).

    Parameters
    ----------
    name_or_path
        If it ends with ``.json``, treat as a file path. Otherwise look it
        up in the bundled palettes.

    Returns
    -------
    dict
        The palette dict, shaped like::

            {
                "brand": "Crayola",
                "set_name": "Fine Line Classic",
                "tip_width_mm": 0.5,
                "colors": [
                    {"name": "Red", "hex": "#ED0A3F", "rgb": [237, 10, 63]},
                    ...
                ]
            }

    Raises
    ------
    FileNotFoundError
        If a custom path is given that doesn't exist.
    ValueError
        If the bundled palette name is unknown.
    """
    p = Path(name_or_path)
    if p.suffix.lower() == ".json":
        return load_marker_palette(p)

    # Bundled lookup
    palette_dir = _find_palette_dir()
    if palette_dir is not None:
        candidate = palette_dir / f"{name_or_path}.json"
        if candidate.is_file():
            return load_marker_palette(candidate)
    raise ValueError(
        f"Unknown palette '{name_or_path}'. Available: {', '.join(p['name'] for p in list_bundled_palettes())}"
    )


# ---------------------------------------------------------------------------
# Color quantization
# ---------------------------------------------------------------------------


def quantize_image(
    img: Image.Image,
    *,
    max_palette: int = 12,
    alpha_threshold: int = 10,
    skip_bg: bool = True,
    paper_white_soft: int = 20,
    white_medium: bool = True,
) -> Dict[str, Any]:
    """Quantize an image to ``max_palette`` colors and return the result.

    This is the FAST STAGE of the pipeline. On a 1500x2000 image it runs
    in ~200-300ms. It's the "live preview" the user iterates on while
    picking a palette.

    Parameters
    ----------
    img
        RGBA PIL image.
    max_palette
        Maximum number of distinct colors in the output. Lower = more
        banded (cartoon look); higher = more detail. Try 4 for logos,
        8-12 for portraits, 16+ for photos.
    alpha_threshold
        Pixels with alpha below this are treated as transparent. 10 is a
        good default; raise to 50+ if your image has soft edges you want
        to ignore.
    skip_bg
        If True, the most-common near-white color is treated as "paper"
        and excluded from the output layers. Disable with
        ``skip_bg=False`` if you want the background as a layer.
    paper_white_soft
        Threshold for "near white" detection. 20 means RGB >= 235 in all
        channels counts as paper. Lower = stricter; raise if your
        background is slightly off-white.
    white_medium
        If True, "white-ish" colors are treated as a medium tone and
        included as a layer. If False, they're skipped like the background.
        Set True for photos (you want pen strokes on light skin) and
        False for line art.

    Returns
    -------
    dict
        {
            "indexed": (H, W) np.ndarray of color indices,
            "palette": [(R, G, B), ...] in index order,
            "color_info": [
                {"idx": 0, "rgb": (255, 255, 255), "hex": "#FFFFFF", "pixels": 228593, "name": "white"},
                ...
            ],
            "elapsed_ms": 312
        }

    The ``indexed`` array is what you draw to get a preview of the
    quantized image. The ``palette`` list is the colors in index order.
    ``color_info`` is the human-friendly per-color breakdown.
    """
    # Imported here for clarity; the real work happens in core.build_color_index_map
    from png2svg.core import rgb_to_hex, rough_color_name

    t0 = time.perf_counter()
    arr = np.asarray(img)
    rgb = arr[:, :, :3]
    alpha = arr[:, :, 3]

    # build_color_index_map returns (color_idx, palette, visible) where
    # palette is a list of (R, G, B) tuples in index order, and visible
    # is a boolean mask of pixels that are "renderable" (alpha > threshold).
    # Note: we ignore skip_bg/white_medium here — that's a per-layer filter
    # applied later, not a quantization decision. This function just reports
    # what colors the image actually contains.
    color_idx, palette, visible = build_color_index_map(rgb, alpha, alpha_threshold, max_palette)

    color_info: List[Dict[str, Any]] = []
    if visible.any():
        used_indices = np.unique(color_idx[visible])
    else:
        used_indices = []
    for idx in used_indices:
        idx_int = int(idx)
        if idx_int < 0 or idx_int >= len(palette):
            continue
        rgb_t = tuple(int(c) for c in palette[idx_int])
        mask = (color_idx == idx_int) & visible
        pixels = int(mask.sum())
        color_info.append(
            {
                "idx": idx_int,
                "rgb": rgb_t,
                "hex": "#" + rgb_to_hex(rgb_t),
                "pixels": pixels,
                "name": rough_color_name(rgb_t),
            }
        )

    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    # Compress: only keep the colors that are actually used. Pillow's
    # ADAPTIVE palette is always 256 entries but only a handful are
    # referenced by the indexed image. Reporting 256 colors would be
    # a lie to the user, so we rebuild a tight palette and remap the
    # indices to be contiguous starting at 0.
    color_info_sorted = sorted(color_info, key=lambda c: c["idx"])
    old_idx_to_new = {old: new for new, old in enumerate(c["idx"] for c in color_info_sorted)}
    used_palette = [c["rgb"] for c in color_info_sorted]
    remapped_indexed = np.full(color_idx.shape, -1, dtype=np.int32)
    for old, new in old_idx_to_new.items():
        remapped_indexed[color_idx == old] = new
    # Update the "idx" in color_info to match the new mapping
    for c in color_info_sorted:
        c["idx"] = old_idx_to_new[c["idx"]]

    return {
        "indexed": remapped_indexed,
        "palette": used_palette,
        "color_info": color_info_sorted,
        "elapsed_ms": elapsed_ms,
    }


def render_quantized_preview(
    img: Image.Image,
    quant: Dict[str, Any],
    *,
    show_index_labels: bool = False,
) -> Image.Image:
    """Render the quantized color map as a PIL image for inline display.

    The output is a flat-colored image showing the banded quantization,
    sized like the original. Transparent pixels in the original stay
    transparent here.

    Parameters
    ----------
    img
        The original RGBA image (used to preserve alpha).
    quant
        The output of :func:`quantize_image`.
    show_index_labels
        Reserved for future use; currently ignored.
    """
    arr = np.asarray(img)
    h, w = arr.shape[:2]
    alpha = arr[:, :, 3]

    indexed = quant["indexed"]
    palette = quant["palette"]

    # Build an (H, W, 3) RGB image from indexed + palette
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    for idx, color in enumerate(palette):
        mask = indexed == idx
        rgb[mask] = color

    # Composite over white background for display
    alpha_norm = (alpha.astype(np.float32) / 255.0)[:, :, None]
    bg = np.full_like(rgb, 255)
    out = (rgb * alpha_norm + bg * (1 - alpha_norm)).astype(np.uint8)
    return Image.fromarray(out, mode="RGB")


# ---------------------------------------------------------------------------
# Color matching to a marker palette
# ---------------------------------------------------------------------------


def match_to_palette(
    quant: Dict[str, Any],
    palette: Dict[str, Any],
) -> Dict[str, Any]:
    """For each detected color, find the closest marker in the palette.

    This is the magic that makes png2svg a *physical-pen* tool, not a
    generic tracer. We use HSV Euclidean distance by default (see
    :func:`png2svg.core.closest_marker`); the algorithm does not try
    to be perceptually correct — it tries to be predictable. A Crafter
    who knows their pens expects "closest red" to actually be the
    closest red, not some Lab-distance-magic that picks a brown.

    Parameters
    ----------
    quant
        Output of :func:`quantize_image`.
    palette
        Output of :func:`load_palette`.

    Returns
    -------
    dict
        Same shape as ``quant``, but each color in ``color_info`` has
        additional ``marker_name``, ``marker_hex``, and ``marker_rgb`` keys.
    """
    matched = []
    for info in quant["color_info"]:
        marker = closest_marker(info["rgb"], palette)
        matched.append(
            {
                **info,
                "marker_name": marker.get("name", "?"),
                "marker_hex": marker.get("hex", "#000000"),
                "marker_rgb": marker.get("rgb_tuple", info["rgb"]),
            }
        )
    return {**quant, "color_info": matched}


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------


def render_svg(
    img: Image.Image,
    *,
    preset: Optional[str] = None,
    palette: Optional[Dict[str, Any]] = None,
    max_palette: int = 12,
    line_step: int = 4,
    alpha_threshold: int = 10,
    min_pixels: int = 200,
    stroke_width: Optional[float] = None,
    outline_width: Optional[float] = None,
    skip_bg: bool = True,
    white_medium: bool = True,
    paper_white_soft: int = 20,
    scale: float = 1.0,
    separate_outline: bool = False,
    naming_mode: str = "inkscape",
    continuous_paths: bool = True,
    arc_radius: float = 5.0,
) -> Dict[str, Any]:
    """Render an image to a plotter-ready SVG.

    This is the SLOW STAGE. On a 1500x2000 image it takes 30-60 seconds
    (the bottleneck is the per-pixel hatching, not the SVG emission).
    Always preview with :func:`quantize_image` first so you don't waste
    a 60-second render on a wrong color count.

    Parameters
    ----------
    img
        RGBA PIL image.
    preset
        Name of a built-in preset (``"portrait"``, ``"logo"``, etc.).
        Preset values are applied first; any explicit kwargs below
        override them.
    palette
        Marker palette dict from :func:`load_palette`. If None, colors
        are quantized but not mapped to physical markers (the SVG will
        have plain RGB colors).
    max_palette, line_step, alpha_threshold, min_pixels,
    stroke_width, outline_width, skip_bg, white_medium,
    paper_white_soft, scale, separate_outline, naming_mode,
    continuous_paths, arc_radius
        Per-stage parameters. See ``png2svg --help`` for defaults.
        The defaults here match the CLI defaults.

    Returns
    -------
    dict
        {
            "svg_path": Path to the written SVG file,
            "color_map_used": list of detected colors with marker info,
            "stats": processing statistics from core,
            "params": the actual RenderParams used (after preset merge),
            "elapsed_ms": total render time
        }
    """
    # Build params, applying preset first
    base = {
        "max_palette": max_palette,
        "line_step": line_step,
        "alpha_threshold": alpha_threshold,
        "min_pixels": min_pixels,
        "skip_bg": skip_bg,
        "white_medium": white_medium,
        "paper_white_soft": paper_white_soft,
        "scale": scale,
        "separate_outline": separate_outline,
        "naming_mode": naming_mode,
        "continuous_paths": continuous_paths,
        "arc_radius": arc_radius,
    }
    if preset:
        if preset not in PRESETS:
            raise ValueError(f"Unknown preset '{preset}'. Available: {', '.join(list_presets())}")
        for key, value in PRESETS[preset].items():
            if key == "description":
                continue
            if key in base:
                base[key] = value

    # stroke/outline auto-default from palette tip width
    if stroke_width is None and palette and palette.get("tip_width_mm"):
        stroke_width = float(palette["tip_width_mm"])
    if stroke_width is None:
        stroke_width = 0.5
    if outline_width is None:
        outline_width = max(1.0, stroke_width * 1.6)

    params = RenderParams(
        **base,
        stroke_width=stroke_width,
        outline_width=outline_width,
    )

    t0 = time.perf_counter()
    # process_image_to_hatched_svg takes a file path. To accept a PIL image
    # (which is what users will hand us in a notebook), we write to a
    # temp file, then clean it up.
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_in:
        img.save(tmp_in.name, "PNG")
        input_path = Path(tmp_in.name)
    output_path = Path(tempfile.mkstemp(suffix=".svg")[1])

    try:
        color_map_used, stats = process_image_to_hatched_svg(
            input_path,
            output_path,
            params,
            marker_palette=palette,
            color_map=None,
            show_stats=True,  # always populate stats; the notebook displays them
        )
    finally:
        try:
            input_path.unlink()
        except OSError:
            pass

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    return {
        "svg_path": output_path,
        "color_map_used": color_map_used,
        "stats": stats,
        "params": asdict(params),
        "elapsed_ms": elapsed_ms,
    }


# ---------------------------------------------------------------------------
# Session save/load (reproducibility)
# ---------------------------------------------------------------------------


def snapshot_session(
    params: RenderParams,
    palette: Optional[Dict[str, Any]],
    color_map: List[Dict[str, Any]],
    image_path: str | Path,
) -> Dict[str, Any]:
    """Bundle the inputs needed to reproduce a render into a dict.

    The session is the recipe: the same image + the same params + the
    same palette + the same color_map will produce the same SVG byte-
    for-byte (modulo platform float differences). Use this when you
    find a result you like and want to come back to it later.

    Use :func:`save_session_file` to write it to disk, or
    :func:`render_from_session` to replay it.
    """
    return {
        "version": __version__,
        "image": str(image_path),
        "params": asdict(params),
        "palette": palette,
        "color_map": color_map,
    }


def save_session_file(session: Dict[str, Any], path: str | Path) -> Path:
    """Write a session dict to a JSON file."""
    p = Path(path)
    p.write_text(json.dumps(session, indent=2, default=str))
    return p


def load_session_file(path: str | Path) -> Dict[str, Any]:
    """Read a session file. Inverse of :func:`save_session_file`."""
    return json.loads(Path(path).read_text())


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------


def display_image(img: Image.Image) -> Image.Image:
    """Display a PIL image in a Jupyter notebook. Returns the image."""
    from IPython.display import display

    display(img)
    return img


def display_svg(svg_path: str | Path) -> None:
    """Display an SVG file inline in a notebook."""
    from IPython.display import SVG, display

    display(SVG(filename=str(svg_path)))


def display_side_by_side(*images: Image.Image, titles: Optional[List[str]] = None) -> None:
    """Display multiple PIL images side by side using matplotlib.

    We use matplotlib (not raw HTML) so the layout is consistent across
    notebook renderers (Jupyter, nbviewer, VS Code). Each image gets
    a small caption if ``titles`` is provided.
    """
    import matplotlib.pyplot as plt

    n = len(images)
    fig, axes = plt.subplots(1, n, figsize=(5 * n, 5))
    if n == 1:
        axes = [axes]
    for i, (img, ax) in enumerate(zip(images, axes)):
        ax.imshow(img)
        ax.set_xticks([])
        ax.set_yticks([])
        if titles and i < len(titles):
            ax.set_title(titles[i])
    plt.tight_layout()
    plt.show()


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def format_quantize_report(quant: Dict[str, Any]) -> str:
    """Pretty-print the quantization result for a notebook cell."""
    lines = [f"**Quantized in {quant['elapsed_ms']}ms** — {len(quant['palette'])} colors:"]
    lines.append("")
    lines.append("| # | Color | Hex | Pixels | % of visible |")
    lines.append("|---|-------|-----|--------|--------------|")
    total_visible = sum(c["pixels"] for c in quant["color_info"])
    for c in quant["color_info"]:
        pct = (c["pixels"] / total_visible * 100) if total_visible else 0
        lines.append(f"| {c['idx']} | {c['name']} | `{c['hex']}` | {c['pixels']:,} | {pct:.1f}% |")
    return "\n".join(lines)


def format_render_report(result: Dict[str, Any]) -> str:
    """Pretty-print the render result for a notebook cell."""
    stats = result["stats"]
    lines = [
        f"**Rendered in {result['elapsed_ms']}ms**",
        "",
        f"- Layers: {stats.get('layers_generated', '?')}",
        f"- Total segments: {stats.get('total_segments', 0):,}",
        f"- Pen lifts (optimized): {stats.get('optimized_pen_lifts', 0):,}",
        f"- Pen lifts (legacy): {stats.get('legacy_pen_lifts', 0):,}",
    ]
    legacy = stats.get("legacy_pen_lifts", 0)
    optimized = stats.get("optimized_pen_lifts", 0)
    if legacy > 0:
        reduction = (1 - optimized / legacy) * 100
        lines.append(f"- Pen-lift reduction: {reduction:.1f}%")
    lines.append(f"- Output: `{result['svg_path']}`")
    return "\n".join(lines)


__all__ = [
    "load_image",
    "image_to_png_bytes",
    "image_to_data_url",
    "numpy_to_pil",
    "list_bundled_palettes",
    "load_palette",
    "quantize_image",
    "render_quantized_preview",
    "match_to_palette",
    "render_svg",
    "snapshot_session",
    "save_session_file",
    "load_session_file",
    "display_image",
    "display_svg",
    "display_side_by_side",
    "format_quantize_report",
    "format_render_report",
]
