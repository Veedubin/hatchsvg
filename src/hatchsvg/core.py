#!/usr/bin/env python3
"""
Hatched SVG generator for Cricut pens with repeatable "sessions".

Features
--------
- Flattened hatch + outline into (by default) ONE <path> per color.
- Optional marker palette JSON (brand / set / colors).
- Optional separate outline paths.
- Optional white-medium mode (don't hatch near-white colors).
- Optional background skip.
- Scale option to control complexity.
- "Session" JSON save/load.
"""

import colorsys
import json
import math
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image

# Optional Rich dependency for progress bars and stats
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
    from rich.table import Table

    HAS_RICH = True
except ImportError:
    HAS_RICH = False


# --------------------------------------------------------------------
# Data Structures
# --------------------------------------------------------------------


@dataclass
class RenderParams:
    """Holds all configuration parameters for the rendering process."""

    max_palette: int = 12
    line_step: int = 4
    alpha_threshold: int = 10
    min_pixels: int = 200
    stroke_width: float = 0.5
    outline_width: float = 0.8
    skip_bg: bool = False
    white_medium: bool = False
    paper_white_soft: int = 20
    scale: float = 1.0
    separate_outline: bool = False
    naming_mode: str = "inkscape"
    continuous_paths: bool = False
    arc_radius: float = 0.0
    hatch_angles: Optional[List[float]] = None
    hatch_angle: float = 0.0


@dataclass
class LayerResult:
    """Return data from processing a single layer."""

    groups: List[str] = field(default_factory=list)
    color_map_entry: Optional[Dict[str, Any]] = None
    is_layer_generated: bool = False


@dataclass
class StrokeStyle:
    """Resolved style information for a specific layer."""

    stroke_rgb: Tuple[int, int, int]
    marker_hex: str
    marker_name: str
    line_step: int
    is_white: bool


# --------------------------------------------------------------------
# Utility helpers
# --------------------------------------------------------------------


def find_segments_in_row(row: np.ndarray) -> List[Tuple[int, int]]:
    """Return continuous True segments as (x_start, x_end)."""
    idx = np.nonzero(row)[0]
    if idx.size == 0:
        return []

    segs = []
    start = idx[0]
    prev = idx[0]

    for x in idx[1:]:
        if x == prev + 1:
            prev = x
        else:
            segs.append((start, prev + 1))
            start = x
            prev = x
    segs.append((start, prev + 1))
    return segs


def _hatch_path_legacy(mask: np.ndarray, line_step: int) -> str:
    """Legacy hatch path generation - all lines left-to-right with separate M commands."""
    h, _ = mask.shape
    cmds = []
    step = max(1, line_step)
    for y in range(0, h, step):
        row = mask[y]
        segs = find_segments_in_row(row)
        for x1, x2 in segs:
            cmds.append(f"M{x1} {y} H{x2}")
    return " ".join(cmds)


def _hatch_path_serpentine(mask: np.ndarray, line_step: int, arc_radius: float = 0.0) -> str:
    """Serpentine hatch path generation - rows alternate direction, segments chained with H.

    The chain spans multiple rows: when row N ends at (x_N_end, y_N) and the
    arc lands at (x_N_end, y_N+step), row N+1's first segment starts there.
    If row N+1's first segment begins at exactly (x_N_end, y_N+step) — i.e.
    the mask is continuous across rows — the path just continues with 'H'
    commands. A new 'M' is only emitted when there's an actual discontinuity
    (gap in the mask, or the very first row).
    """
    h, _ = mask.shape
    cmds: list[str] = []
    step = max(1, line_step)

    # Track whether the chain is currently "live" — i.e. we've drawn at
    # least one segment so far, and the previous row wasn't empty.
    # A live chain continues with 'H' commands. A broken chain starts
    # a new sub-path with 'M'.
    chain_live = False

    for row_idx, y in enumerate(range(0, h, step)):
        row = mask[y]
        segs = find_segments_in_row(row)
        if not segs:
            # No segments in this row — the chain is broken. Next row that
            # has segments will need a new M.
            chain_live = False
            continue

        # Even rows (0,2,4): left-to-right; Odd rows (1,3,5): right-to-left
        if row_idx % 2 == 1:
            segs = [(x2, x1) for x1, x2 in reversed(segs)]

        # Decide whether the first segment of this row needs a new M.
        # A new M is needed if the chain isn't currently live (first row or
        # previous row was empty). Otherwise we just continue with 'H'.
        if not chain_live:
            x1, x2 = segs[0]
            cmds.append(f"M{x1} {y}")
            cmds.append(f"H{x2}")
            start_idx = 1
        else:
            # Chain continues: emit 'H' for the first segment directly.
            x1, x2 = segs[0]
            cmds.append(f"H{x2}")
            start_idx = 1

        # Chain remaining segments in this row with H commands.
        for x1, x2 in segs[start_idx:]:
            cmds.append(f"H{x2}")

        # Phase 3: Add arc at row-end reversal (transition to next row)
        # Even row ends going right; next row will be drawn right-to-left.
        # The arc lands the pen at (last_x, y+step). The chain stays live.
        chain_live = True
        if arc_radius > 0 and row_idx % 2 == 0 and row_idx + 1 < h:
            next_y = y + step
            if next_y < h:
                # Only add the arc if the next row has any segments.
                next_row = mask[next_y]
                if np.any(next_row):
                    # The arc sweeps from (last_x, y) to (last_x, next_y).
                    last_x = segs[-1][1]
                    cmds.append(f"A {arc_radius} {arc_radius} 0 0 1 {last_x} {next_y}")
                    # Chain stays live — next row will continue with H commands.
                else:
                    # Next row is empty — chain breaks.
                    chain_live = False

    return " ".join(cmds)


def _count_segments_in_mask(mask: np.ndarray, line_step: int) -> int:
    """Count total hatch segments in a mask (for stats)."""
    h, _ = mask.shape
    step = max(1, line_step)
    total = 0
    for y in range(0, h, step):
        row = mask[y]
        segs = find_segments_in_row(row)
        total += len(segs)
    return total


def compute_layer_stats(mask: np.ndarray, line_step: int) -> Dict[str, Any]:
    """Compute path statistics for a single layer mask.

    Returns dict with:
    - segments: total hatch segments
    - legacy_lifts: pen lifts with legacy (left-to-right) paths
    - optimized_lifts: pen lifts with serpentine/continuous paths
    - component_count: number of connected components
    - reduction_pct: percentage reduction in pen lifts
    """
    segments = _count_segments_in_mask(mask, line_step)

    # Count legacy pen lifts (one M per segment)
    legacy_lifts = segments

    # Generate optimized path to count its pen lifts
    # M commands are always preceded by a space or start of string
    # The path format is "M{x} {y} H..." or "M{x} {y} A..."
    # Count 'M' at start of a command (preceded by space or at position 0)
    optimized_path = hatch_path_for_mask(mask, line_step, continuous=True, arc_radius=0.0)
    # Count ' M' (space+M) or start-of-string 'M' to find pen lift commands
    optimized_lifts = optimized_path.count(" M") + (1 if optimized_path.startswith("M") else 0)

    # Count connected components
    try:
        from scipy.ndimage import label

        labeled, num_features = label(mask)
        component_count = num_features
    except ImportError:
        component_count = 1

    # Calculate reduction percentage
    reduction_pct = 0.0
    if legacy_lifts > 0:
        reduction_pct = (1 - optimized_lifts / legacy_lifts) * 100
        reduction_pct = max(0.0, min(100.0, reduction_pct))

    return {
        "segments": segments,
        "legacy_lifts": legacy_lifts,
        "optimized_lifts": optimized_lifts,
        "component_count": component_count,
        "reduction_pct": reduction_pct,
    }


def _order_components_nearest_neighbor(component_paths: List[str], centroids: List[Tuple[float, float]]) -> List[str]:
    """Order components using greedy nearest-neighbor to minimize pen travel."""
    if not component_paths:
        return []

    n = len(component_paths)
    visited = [False] * n
    ordered = []

    # Start with the leftmost component
    current = min(range(n), key=lambda i: centroids[i][0])
    visited[current] = True
    ordered.append(component_paths[current])

    for _ in range(n - 1):
        # Find nearest unvisited component by Euclidean distance
        nearest = None
        min_dist = float("inf")
        for i in range(n):
            if not visited[i]:
                dist = (
                    (centroids[current][0] - centroids[i][0]) ** 2 + (centroids[current][1] - centroids[i][1]) ** 2
                ) ** 0.5
                if dist < min_dist:
                    min_dist = dist
                    nearest = i

        visited[nearest] = True
        ordered.append(component_paths[nearest])
        current = nearest

    return ordered


def hatch_path_for_mask(mask: np.ndarray, line_step: int, continuous: bool = False, arc_radius: float = 0.0) -> str:
    """Flatten all hatch segments into ONE path 'd' string.

    When continuous=True, generates serpentine paths that alternate direction
    per row to reduce pen plotter vibration (ringing). Contiguous segments
    within a row are connected to minimize pen lifts.

    Phase 2: For discontinuous regions (islands), generates separate paths
    per connected component and orders them with nearest-neighbor TSP.

    Phase 3: When arc_radius > 0, adds small arcs at row-end 180° reversals
    to smooth transitions.
    """
    if not continuous:
        return _hatch_path_legacy(mask, line_step)

    # Phase 2: Find connected components
    try:
        from scipy.ndimage import label

        labeled, num_features = label(mask)
    except ImportError:
        # Fallback: use serpentine without component splitting
        return _hatch_path_serpentine(mask, line_step, arc_radius)

    if num_features <= 1:
        return _hatch_path_serpentine(mask, line_step, arc_radius)

    # Generate path for each component
    component_paths = []
    centroids = []
    for i in range(1, num_features + 1):
        component_mask = labeled == i
        path = _hatch_path_serpentine(component_mask, line_step, arc_radius)
        component_paths.append(path)
        # Compute centroid for ordering
        y_coords, x_coords = np.where(component_mask)
        centroids.append((float(np.mean(x_coords)), float(np.mean(y_coords))))

    # Order components by nearest-neighbor
    ordered_paths = _order_components_nearest_neighbor(component_paths, centroids)

    return " ".join(ordered_paths)


def border_mask(mask: np.ndarray) -> np.ndarray:
    """Return border pixels of a region (4-neighbor)."""
    up = np.zeros_like(mask)
    up[1:] = mask[:-1]
    dn = np.zeros_like(mask)
    dn[:-1] = mask[1:]
    lf = np.zeros_like(mask)
    lf[:, 1:] = mask[:, :-1]
    rt = np.zeros_like(mask)
    rt[:, :-1] = mask[:, 1:]

    interior = mask & up & dn & lf & rt
    return mask & ~interior


def outline_path_for_mask(mask: np.ndarray, continuous: bool = False, arc_radius: float = 0.0) -> str:
    """Flatten all outline segments into one path string (border only)."""
    bmask = border_mask(mask)
    return hatch_path_for_mask(bmask, line_step=1, continuous=continuous, arc_radius=arc_radius)


def luminance(rgb: Tuple[int, int, int]) -> float:
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    return f"{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"


def get_hue_name(h_deg: float) -> str:
    """Helper for rough_color_name to reduce complexity."""
    if h_deg < 15 or h_deg >= 345:
        return "red"
    elif h_deg < 45:
        return "orange"
    elif h_deg < 75:
        return "yellow"
    elif h_deg < 150:
        return "green"
    elif h_deg < 210:
        return "cyan"
    elif h_deg < 270:
        return "blue"
    elif h_deg < 330:
        return "purple"
    return "red"


def rough_color_name(rgb: Tuple[int, int, int]) -> str:
    """Very rough human color name; used if no marker palette."""
    maxc = max(rgb)
    minc = min(rgb)
    diff = maxc - minc

    # Achromatic check
    if diff < 15:
        if maxc > 240:
            return "white"
        if maxc < 25:
            return "black"
        return "gray"

    r, g, b = rgb
    r_n, g_n, b_n = r / 255.0, g / 255.0, b / 255.0

    h_val, _, _ = colorsys.rgb_to_hsv(r_n, g_n, b_n)
    return get_hue_name(h_val * 360.0)


def rgb_to_hsv_deg(rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
    """RGB (0-255) -> (H_deg 0-360, S 0-1, V 0-1)."""
    r, g, b = rgb
    h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    return h * 360.0, s, v


# --------------------------------------------------------------------
# Marker palette handling
# --------------------------------------------------------------------


def load_marker_palette(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "colors" not in data or not isinstance(data["colors"], list):
        raise ValueError("Palette JSON must have a 'colors' list.")

    for c in data["colors"]:
        if "hex" in c:
            h = c["hex"].lstrip("#")
            if len(h) != 6:
                raise ValueError(f"Bad hex color {c['hex']}")
            r = int(h[0:2], 16)
            g = int(h[2:4], 16)
            b = int(h[4:6], 16)
            c["rgb_tuple"] = (r, g, b)
        elif "rgb" in c and len(c["rgb"]) == 3:
            c["rgb_tuple"] = tuple(int(v) for v in c["rgb"])
            c["hex"] = "#" + rgb_to_hex(c["rgb_tuple"])
        else:
            raise ValueError("Each color needs 'hex' or 'rgb'.")

        if "name" not in c:
            c["name"] = rgb_to_hex(c["rgb_tuple"])

    return data


def closest_marker(rgb: Tuple[int, int, int], marker_palette: Dict[str, Any]) -> Dict[str, Any]:
    """Map an image RGB to the closest marker in the palette."""
    img_h, img_s, img_v = rgb_to_hsv_deg(rgb)

    best_idx = -1
    best_score = 1e9

    for i, c in enumerate(marker_palette["colors"]):
        mr, mg, mb = c["rgb_tuple"]
        m_h, m_s, m_v = rgb_to_hsv_deg((mr, mg, mb))

        marker_is_neutral = m_s < 0.20

        # Base HSV distance
        dh = abs(img_h - m_h)
        dh = min(dh, 360.0 - dh) / 180.0
        ds = abs(img_s - m_s)
        dv = abs(img_v - m_v)

        score = (3.0 * dh * dh) + (1.0 * ds * ds) + (0.7 * dv * dv)

        # Penalize neutrals for colorful pixels
        if img_s > 0.30 and marker_is_neutral:
            score += 1.0

        # Slightly favor neutrals for very desaturated pixels
        if img_s < 0.15 and marker_is_neutral:
            score -= 0.1

        if score < best_score:
            best_score = score
            best_idx = i

    if best_idx == -1:
        return {"name": "Unknown", "hex": "#000000", "rgb_tuple": (0, 0, 0)}

    return marker_palette["colors"][best_idx]


# --------------------------------------------------------------------
# Session load/save
# --------------------------------------------------------------------


def load_session(path: Path) -> Dict[str, Any]:
    """Load a session JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Normalize color_map marker_rgb / palette_rgb to tuples
    color_map_raw = data.get("color_map", {})
    color_map = {}
    for pal_hex, entry in color_map_raw.items():
        key = "#" + pal_hex.lstrip("#").upper()
        e = dict(entry)
        if "marker_rgb" in e and e["marker_rgb"] is not None:
            e["marker_rgb"] = tuple(e["marker_rgb"])
        if "palette_rgb" in e and e["palette_rgb"] is not None:
            e["palette_rgb"] = tuple(e["palette_rgb"])
        color_map[key] = e

    data["color_map"] = color_map
    return data


def save_session(
    path: Path, input_path: Path, palette_file: Optional[str], params: RenderParams, color_map_used: Dict[str, Any]
):
    """Write a session JSON file."""
    color_map_out = {}
    for pal_hex, entry in color_map_used.items():
        if pal_hex is None:
            continue
        key = pal_hex.lstrip("#").upper()
        # RGB tuples may contain numpy scalars (e.g. np.uint32 from the
        # quantization path). json.dump can't serialize those — convert
        # each value to a plain Python int.
        marker_rgb = [int(c) for c in (entry.get("marker_rgb") or [])]
        palette_rgb = [int(c) for c in (entry.get("palette_rgb") or [])]
        color_map_out[key] = {
            "marker_name": entry.get("marker_name"),
            "marker_hex": entry.get("marker_hex"),
            "marker_rgb": marker_rgb,
            "palette_rgb": palette_rgb,
            "hatch_step": entry.get("hatch_step"),
            "is_white_medium": bool(entry.get("is_white_medium", False)),
        }

    session_data = {
        "input_basename": input_path.name,
        "palette_file": palette_file,
        "params": asdict(params),
        "color_map": color_map_out,
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(session_data, f, indent=2)
    print(f"Saved session to {path}")


# --------------------------------------------------------------------
# Color indexing
# --------------------------------------------------------------------


def build_color_index_map(orig_rgb: np.ndarray, alpha: np.ndarray, alpha_threshold: int, max_palette: int):
    """
    If unique visible colors <= max_palette: use them exactly.
    Otherwise: fall back to adaptive palette quantization.
    """
    h, w, _ = orig_rgb.shape
    visible = alpha > alpha_threshold

    flat = orig_rgb.reshape(-1, 3)
    vis_flat = visible.reshape(-1)
    vis_rgb = flat[vis_flat]
    if vis_rgb.size == 0:
        raise SystemExit("No visible pixels.")

    packed = (
        vis_rgb[:, 0].astype(np.uint32) << 16 | vis_rgb[:, 1].astype(np.uint32) << 8 | vis_rgb[:, 2].astype(np.uint32)
    )
    uniq, inv = np.unique(packed, return_inverse=True)

    if len(uniq) <= max_palette:
        print(f"Exact-color mode: {len(uniq)} colors.")
        out = np.full(flat.shape[0], -1, np.int32)
        out[vis_flat] = inv
        palette = [((p >> 16) & 255, (p >> 8) & 255, p & 255) for p in uniq]
        return out.reshape(h, w), palette, visible

    print(f"Quantizing: Found {len(uniq)} unique colors > max_palette={max_palette}.")
    img_rgba = Image.fromarray(np.dstack([orig_rgb, alpha]), "RGBA")

    img_p = img_rgba.convert("P", palette=Image.Palette.ADAPTIVE, colors=max_palette)
    idx_arr = np.array(img_p)

    raw_p = img_p.getpalette()
    if raw_p is None:
        raw_p = []

    pal = []
    for i in range(256):
        j = 3 * i
        if j + 2 < len(raw_p):
            pal.append((raw_p[j], raw_p[j + 1], raw_p[j + 2]))
        else:
            pal.append((0, 0, 0))
    return idx_arr, pal, visible


# --------------------------------------------------------------------
# Main rendering logic
# --------------------------------------------------------------------


def _detect_background(
    visible: np.ndarray, color_idx: np.ndarray, palette: List[Tuple[int, int, int]]
) -> Optional[int]:
    """Helper to detect dominant border color for background skipping."""
    h, w = visible.shape
    border = visible.copy()
    if h > 2 and w > 2:
        border[1:-1, 1:-1] = False

    border_vals = color_idx[border]
    if border_vals.size > 0:
        cnt = np.bincount(border_vals.astype(int))
        bg_idx = int(cnt.argmax())
        if 0 <= bg_idx < len(palette):
            print(f"Background detected as index {bg_idx}, RGB={palette[bg_idx]}")
            return bg_idx

    print("No border pixels or invalid detection → not skipping background.")
    return None


def _is_white_medium_pixel(rgb: Tuple[int, int, int], params: RenderParams) -> bool:
    """Return True if the pixel should be treated as paper/white medium."""
    if not params.white_medium:
        return False

    white_thresh_sq = params.paper_white_soft**2
    dr = rgb[0] - 255
    dg = rgb[1] - 255
    db = rgb[2] - 255
    dist2_white = dr * dr + dg * dg + db * db

    _, s_val, v_val = rgb_to_hsv_deg(rgb)
    return dist2_white <= white_thresh_sq or (v_val >= 0.85 and s_val <= 0.35)


def _default_hatch_spacing(params: RenderParams, lum: float) -> Tuple[int, str]:
    """Return (line_step, shade_label) based on luminance."""
    if lum < 70:
        return params.line_step + 2, "dark"
    if lum <= 190:
        return max(2, params.line_step), "mid"
    return params.line_step + 3, "light"


def _apply_session_color_map(
    pal_key: str, color_map: Optional[Dict[str, Any]], ls: int, is_white: bool
) -> Tuple[Optional[str], Optional[str], Optional[Tuple[int, int, int]], int, bool]:
    """Apply session overrides for marker mapping and hatch spacing."""
    if not color_map or pal_key not in color_map:
        return None, None, None, ls, is_white

    entry = color_map[pal_key]
    marker_name = entry.get("marker_name")
    marker_hex = entry.get("marker_hex")

    stroke_rgb = None
    marker_rgb = entry.get("marker_rgb")
    if marker_rgb:
        stroke_rgb = tuple(marker_rgb)

    hatch_step = entry.get("hatch_step")
    if hatch_step is not None:
        ls = int(hatch_step)

    is_white = bool(entry.get("is_white_medium", is_white))
    return marker_name, marker_hex, stroke_rgb, ls, is_white


def _apply_marker_palette_mapping(
    rgb: Tuple[int, int, int],
    marker_palette: Optional[Dict[str, Any]],
    stroke_rgb: Optional[Tuple[int, int, int]],
    marker_name: Optional[str],
    marker_hex: Optional[str],
) -> Tuple[Optional[Tuple[int, int, int]], Optional[str], Optional[str]]:
    """If no session mapping was set, map to the closest marker palette color."""
    if stroke_rgb is not None or marker_palette is None:
        return stroke_rgb, marker_name, marker_hex

    m = closest_marker(rgb, marker_palette)

    # FIX: Explicitly type the retrieved value to satisfy pyright
    found_rgb: Tuple[int, int, int] = m["rgb_tuple"]
    stroke_rgb = found_rgb

    marker_name = marker_name or m.get("name", "marker")
    marker_hex = marker_hex or m.get("hex", "#" + rgb_to_hex(found_rgb))

    return stroke_rgb, marker_name, marker_hex


def _apply_fallback_style(
    rgb: Tuple[int, int, int],
    shade: str,
    stroke_rgb: Optional[Tuple[int, int, int]],
    marker_name: Optional[str],
    marker_hex: Optional[str],
) -> Tuple[Tuple[int, int, int], str, str]:
    """Final fallback if neither a session map nor marker palette could resolve a style."""
    if stroke_rgb is None:
        stroke_rgb = rgb
        marker_hex = marker_hex or ("#" + rgb_to_hex(rgb))
        marker_name = marker_name or f"{shade}_{rough_color_name(rgb)}"

    # Final safeguards
    marker_hex = marker_hex if marker_hex else "#000000"
    marker_name = marker_name if marker_name else "Unknown"
    if stroke_rgb is None:
        stroke_rgb = (0, 0, 0)

    return stroke_rgb, marker_hex, marker_name


def _apply_paper_white_override(
    stroke_rgb: Tuple[int, int, int], marker_hex: str, marker_name: str, is_white: bool
) -> Tuple[Tuple[int, int, int], str, str]:
    """Force paper/white medium layers to draw as a black outline only."""
    if not is_white:
        return stroke_rgb, marker_hex, marker_name
    return (0, 0, 0), "#000000", "WhiteOutline"


def _resolve_stroke_style(
    rgb: Tuple[int, int, int],
    params: RenderParams,
    marker_palette: Optional[Dict[str, Any]],
    color_map: Optional[Dict[str, Any]],
) -> StrokeStyle:
    """Determine the stroke color, name, and hatch settings for a layer."""
    lum = luminance(rgb)
    pal_key = ("#" + rgb_to_hex(rgb)).upper()

    is_white = _is_white_medium_pixel(rgb, params)
    ls, shade = _default_hatch_spacing(params, lum)

    marker_name, marker_hex, stroke_rgb, ls, is_white = _apply_session_color_map(pal_key, color_map, ls, is_white)

    stroke_rgb, marker_name, marker_hex = _apply_marker_palette_mapping(
        rgb, marker_palette, stroke_rgb, marker_name, marker_hex
    )

    stroke_rgb, marker_hex, marker_name = _apply_fallback_style(rgb, shade, stroke_rgb, marker_name, marker_hex)

    stroke_rgb, marker_hex, marker_name = _apply_paper_white_override(stroke_rgb, marker_hex, marker_name, is_white)

    return StrokeStyle(stroke_rgb, marker_hex, marker_name, ls, is_white)


def _layer_base_name(
    idx: int,
    style: StrokeStyle,
    params: RenderParams,
    marker_counters: Dict[str, int],
) -> str:
    """Compute a stable, human-readable layer base name."""
    hex_clean = style.marker_hex.lstrip("#") if style.marker_hex else "000000"

    if params.naming_mode == "flat":
        marker_key = f"{style.marker_name}|{style.marker_hex}"
        marker_index = marker_counters.get(marker_key, 0) + 1
        marker_counters[marker_key] = marker_index
        base_name = f"{style.marker_name}_{marker_index}-{hex_clean}"
        return base_name.replace(" ", "_")

    safe_label = style.marker_name.replace(" ", "_")
    return f"layer_{idx:02d}_{safe_label}_{hex_clean}"


def _part_id(base_name: str, idx: int, params: RenderParams, part: str) -> str:
    """Return the id for hatch/outline paths, preserving the existing naming behavior."""
    if params.naming_mode == "flat":
        suffix = "-Hatch" if part == "hatch" else "-Outline"
        return f"{base_name}{suffix}"
    return f"{part}_{idx}"


def _append_hatch_group(
    groups: List[str],
    hatch_id: str,
    marker_name: str,
    d_hatch: str,
    stroke_str: str,
    params: RenderParams,
) -> None:
    groups.append(
        f'<g id="{hatch_id}"><title>{marker_name} Hatch</title>'
        f'<path d="{d_hatch}" stroke="{stroke_str}" stroke-width="{params.stroke_width}" '
        f'stroke-linecap="round" fill="none"/></g>\n'
    )


def _append_outline_group(
    groups: List[str],
    outline_id: str,
    marker_name: str,
    d_outline: str,
    stroke_str: str,
    params: RenderParams,
) -> None:
    groups.append(
        f'<g id="{outline_id}"><title>{marker_name} Outline</title>'
        f'<path d="{d_outline}" stroke="{stroke_str}" stroke-width="{params.outline_width}" '
        f'stroke-linecap="round" fill="none"/></g>\n'
    )


def _append_combined_group(
    groups: List[str],
    layer_id: str,
    marker_name: str,
    combined_cmds: str,
    stroke_str: str,
    params: RenderParams,
) -> None:
    groups.append(
        f'<g id="{layer_id}"><title>{marker_name}</title>'
        f'<path d="{combined_cmds}" stroke="{stroke_str}" stroke-width="{params.outline_width}" '
        f'stroke-linecap="round" fill="none"/></g>\n'
    )


def _create_layer_groups(
    idx: int, style: StrokeStyle, mask: np.ndarray, params: RenderParams, marker_counters: Dict[str, int]
) -> List[str]:
    """Generate the SVG group strings for a specific layer."""
    d_hatch = (
        "" if style.is_white else hatch_path_for_mask(mask, style.line_step, params.continuous_paths, params.arc_radius)
    )
    d_outline = outline_path_for_mask(mask, params.continuous_paths, params.arc_radius)

    groups: List[str] = []
    stroke_str = f"rgb({style.stroke_rgb[0]},{style.stroke_rgb[1]},{style.stroke_rgb[2]})"
    base_name = _layer_base_name(idx, style, params, marker_counters)

    if params.separate_outline:
        if d_hatch:
            _append_hatch_group(
                groups,
                _part_id(base_name, idx, params, "hatch"),
                style.marker_name,
                d_hatch,
                stroke_str,
                params,
            )
        if d_outline:
            _append_outline_group(
                groups,
                _part_id(base_name, idx, params, "outline"),
                style.marker_name,
                d_outline,
                stroke_str,
                params,
            )
        return groups

    combined_cmds = " ".join([p for p in (d_hatch, d_outline) if p])
    if combined_cmds:
        _append_combined_group(groups, base_name, style.marker_name, combined_cmds, stroke_str, params)
    return groups


def _process_single_layer(
    idx: int,
    rgb: Tuple[int, int, int],
    mask: np.ndarray,
    params: RenderParams,
    marker_counters: Dict[str, int],
    marker_palette: Optional[Dict[str, Any]],
    color_map: Optional[Dict[str, Any]],
) -> LayerResult:
    """
    Process a single color index: Determine stroke color, create paths, generate SVG groups.
    """
    count = int(mask.sum())
    if count < params.min_pixels:
        print(f"Skip color idx {idx}: only {count} pixels")
        return LayerResult()

    style = _resolve_stroke_style(rgb, params, marker_palette, color_map)

    print(
        f"idx {idx}: {style.marker_name} ({style.marker_hex}) "
        f"RGB={rgb}, L={luminance(rgb):.1f}, white={style.is_white}, "
        f"pixels={count}, ls={style.line_step}"
    )

    groups = _create_layer_groups(idx, style, mask, params, marker_counters)

    map_entry = {
        "marker_name": style.marker_name,
        "marker_hex": style.marker_hex,
        "marker_rgb": style.stroke_rgb,
        "palette_rgb": rgb,
        "hatch_step": style.line_step,
        "is_white_medium": bool(style.is_white),
    }

    return LayerResult(groups=groups, color_map_entry=map_entry, is_layer_generated=True)


def optimize_layer_order(layers: List[Dict[str, Any]], start: Tuple[float, float] = (0.0, 0.0)) -> List[Dict[str, Any]]:
    """Reorder layers using greedy nearest-neighbor to minimize pen-up travel.

    Parameters
    ----------
    layers
        List of layer dicts, each with a ``path_start`` key holding a
        ``(x, y)`` tuple of the first coordinate in the layer's first path.
    start
        Starting pen position (default: origin).

    Returns
    -------
    list
        Layers reordered by nearest-neighbor heuristic.
    """
    if len(layers) <= 1:
        return list(layers)

    remaining = list(range(len(layers)))
    ordered: List[Dict[str, Any]] = []
    current_pos = start

    while remaining:
        best_idx = None
        best_dist = float("inf")
        for idx in remaining:
            pos = layers[idx].get("path_start", (0.0, 0.0))
            dist = math.hypot(pos[0] - current_pos[0], pos[1] - current_pos[1])
            if dist < best_dist:
                best_dist = dist
                best_idx = idx
        if best_idx is not None:
            remaining.remove(best_idx)
            ordered.append(layers[best_idx])
            current_pos = layers[best_idx].get("path_start", current_pos)

    return ordered


def _extract_path_start(d_string: str) -> Tuple[float, float]:
    """Extract the first (x, y) coordinate from an SVG path 'd' attribute.

    Looks for the first 'M' command and returns its coordinates.
    Returns (0.0, 0.0) if no move command is found.
    """
    match = re.search(r"M\s*([0-9.eE+-]+)\s+([0-9.eE+-]+)", d_string)
    if match:
        return (float(match.group(1)), float(match.group(2)))
    return (0.0, 0.0)


def _rotate_path(d_string: str, angle_deg: float, cx: float, cy: float) -> str:
    """Rotate an SVG path by the given angle around (cx, cy).

    Applies a rotation transform by transforming all coordinate pairs
    in the path string. Uses the standard 2D rotation matrix.

    Note: The actual rotation is applied via SVG group transforms in
    process_image_to_hatched_svg. This function is kept as a utility
    placeholder for future per-coordinate rotation.
    """
    if abs(angle_deg) < 0.001:
        return d_string

    # Rotation is applied via SVG transform="rotate(...)" on group elements,
    # not by transforming individual coordinates. Return as-is.
    return d_string


def render_single_layer_svg(
    input_path: Path,
    params: RenderParams,
    marker_palette: Optional[Dict[str, Any]],
    color_map: Optional[Dict[str, Any]],
    pal_hex: str,
    output_path: Path,
) -> Optional[str]:
    """Re-render a single color layer as its own SVG file.

    This is used by ``--split-layers`` to write one SVG per color.

    Parameters
    ----------
    input_path
        Path to the original input image.
    params
        Render parameters (with per-layer ``hatch_angle`` set if applicable).
    marker_palette
        Marker palette (same as the main render).
    color_map
        Color map (same as the main render).
    pal_hex
        The hex key of the layer to render (e.g. ``#FF0000``).
    output_path
        Where to write the SVG file.

    Returns
    -------
    str or None
        The SVG content written, or None if the layer was skipped.
    """
    img = Image.open(input_path).convert("RGBA")

    if abs(params.scale - 1.0) > 1e-6:
        w0, h0 = img.size
        w1 = max(1, int(w0 * params.scale))
        h1 = max(1, int(h0 * params.scale))
        img = img.resize((w1, h1), Image.Resampling.LANCZOS)

    rgba = np.array(img)
    orig_rgb = rgba[:, :, :3]
    alpha = rgba[:, :, 3]
    H, W = rgba.shape[0], rgba.shape[1]  # noqa: N806

    color_idx, palette, visible = build_color_index_map(orig_rgb, alpha, params.alpha_threshold, params.max_palette)

    # Find the palette index for the requested pal_hex
    target_idx = None
    for idx_int, rgb in enumerate(palette):
        hex_key = "#" + rgb_to_hex(rgb)
        if hex_key.upper() == pal_hex.upper():
            target_idx = idx_int
            break

    if target_idx is None:
        return None

    mask = (color_idx == target_idx) & visible
    rgb = palette[target_idx]

    marker_counters: Dict[str, int] = {}
    result = _process_single_layer(target_idx, rgb, mask, params, marker_counters, marker_palette, color_map)

    if not result.is_layer_generated or not result.groups:
        return None

    # Build SVG with rotation transform if hatch_angle != 0
    all_groups_str = "".join(result.groups)
    W_int = int(round(W))  # noqa: N806
    H_int = int(round(H))  # noqa: N806

    if abs(params.hatch_angle) > 0.001:
        # Wrap all groups in a rotation transform
        cx = W_int / 2.0
        cy = H_int / 2.0
        transform = f' transform="rotate({params.hatch_angle:.2f},{cx:.2f},{cy:.2f})"'
        group_wrap = f"<g{transform}>\n{all_groups_str}</g>\n"
    else:
        group_wrap = all_groups_str

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{W_int}" height="{H_int}" viewBox="0 0 {W_int} {H_int}">\n'
        f"{group_wrap}</svg>\n"
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(svg, encoding="utf-8")
    return svg


def process_image_to_hatched_svg(
    input_path: Path,
    output_path: Path,
    params: RenderParams,
    marker_palette: Optional[Dict[str, Any]] = None,
    color_map: Optional[Dict[str, Any]] = None,
    show_progress: bool = False,
    show_stats: bool = False,
    optimize_travel: bool = False,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Render SVG and return a color_map_used dict for session saving.

    Returns:
        Tuple of (color_map_used, processing_stats)
    """
    console = Console() if HAS_RICH else None

    # Stats accumulation
    processing_stats = {
        "image_dimensions": (0, 0),
        "colors_detected": 0,
        "layers_generated": 0,
        "total_segments": 0,
        "legacy_pen_lifts": 0,
        "optimized_pen_lifts": 0,
        "layer_stats": [],
    }

    def _print(msg):
        """Print helper that works with or without Rich."""
        if console and HAS_RICH:
            console.print(msg)
        else:
            print(msg)

    # Progress tracking helper
    def _get_progress_bar():
        if not HAS_RICH or not show_progress:
            return None
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        )

    progress = _get_progress_bar()
    use_progress = progress is not None

    # Step 1: Loading image
    if use_progress:
        with progress:
            task1 = progress.add_task("[1/5] Loading image...", total=1)
            img = Image.open(input_path).convert("RGBA")
            progress.update(task1, completed=1)
    else:
        _print(f"Loading image: {input_path}")
        img = Image.open(input_path).convert("RGBA")

    if abs(params.scale - 1.0) > 1e-6:
        w0, h0 = img.size
        w1 = max(1, int(w0 * params.scale))
        h1 = max(1, int(h0 * params.scale))
        _print(f"Scaling from {w0}x{h0} → {w1}x{h1}")
        img = img.resize((w1, h1), Image.Resampling.LANCZOS)

    rgba = np.array(img)
    orig_rgb = rgba[:, :, :3]
    alpha = rgba[:, :, 3]
    H, W = rgba.shape[0], rgba.shape[1]  # noqa: N806
    processing_stats["image_dimensions"] = (W, H)

    # Step 2: Quantizing colors
    if use_progress:
        with progress:
            task2 = progress.add_task("[2/5] Quantizing colors...", total=1)
            color_idx, palette, visible = build_color_index_map(
                orig_rgb, alpha, params.alpha_threshold, params.max_palette
            )
            progress.update(task2, completed=1)
    else:
        color_idx, palette, visible = build_color_index_map(orig_rgb, alpha, params.alpha_threshold, params.max_palette)

    used = np.unique(color_idx[visible])
    _print(f"Colors used: {len(used)}")
    processing_stats["colors_detected"] = len(used)

    # Step 3: Building color index
    if use_progress:
        with progress:
            task3 = progress.add_task("[3/5] Building color index...", total=1)
            progress.update(task3, completed=1)
    else:
        pass  # Already done in step 2

    bg_idx = None
    if params.skip_bg:
        bg_idx = _detect_background(visible, color_idx, palette)

    all_groups: List[str] = []
    layers_count = 0

    color_map_used: Dict[str, Any] = {}
    marker_counters: Dict[str, int] = {}

    # Collect layer data for potential reordering
    layer_data: List[Dict[str, Any]] = []

    # Step 4: Processing layers
    total_layers = len(used)
    if use_progress:
        with progress:
            task4 = progress.add_task(f"[4/5] Processing layers (0/{total_layers})...", total=total_layers)
            for i, idx in enumerate(used):
                idx_int = int(idx)
                if idx_int < 0:
                    progress.update(task4, advance=1)
                    continue
                if params.skip_bg and bg_idx == idx_int:
                    _print(f"Skip BG idx {idx_int}")
                    progress.update(task4, advance=1)
                    continue

                mask = (color_idx == idx_int) & visible
                rgb = palette[idx_int]
                pal_hex = "#" + rgb_to_hex(rgb)

                # Determine per-layer hatch_angle
                if params.hatch_angles:
                    angles_list = params.hatch_angles
                    layer_angle = angles_list[min(layers_count, len(angles_list) - 1)] if angles_list else 0.0
                else:
                    layer_angle = params.hatch_angle

                # Build per-layer params with hatch_angle
                layer_params = RenderParams(**{**params.__dict__, "hatch_angle": layer_angle})

                # Compute layer stats if requested
                layer_stat = None
                if show_stats:
                    layer_stat = compute_layer_stats(mask, layer_params.line_step)
                    layer_stat["color_name"] = rough_color_name(rgb)
                    layer_stat["hex"] = pal_hex
                    processing_stats["total_segments"] += layer_stat["segments"]
                    processing_stats["legacy_pen_lifts"] += layer_stat["legacy_lifts"]
                    processing_stats["optimized_pen_lifts"] += layer_stat["optimized_lifts"]
                    processing_stats["layer_stats"].append(layer_stat)

                result = _process_single_layer(
                    idx_int, rgb, mask, layer_params, marker_counters, marker_palette, color_map
                )

                if result.is_layer_generated and result.color_map_entry:
                    # Extract path start for optimize_travel
                    path_start = (0.0, 0.0)
                    if result.groups:
                        # Find first path's start coordinate
                        first_group = result.groups[0]
                        match = re.search(r'd="([^"]*)"', first_group)
                        if match:
                            path_start = _extract_path_start(match.group(1))

                    layer_data.append(
                        {
                            "groups": result.groups,
                            "color_map_entry": result.color_map_entry,
                            "pal_hex": pal_hex,
                            "hatch_angle": layer_angle,
                            "path_start": path_start,
                        }
                    )
                    color_map_used[pal_hex] = result.color_map_entry
                    if result.groups:
                        layers_count += 1

                progress.update(task4, description=f"[4/5] Processing layers ({i + 1}/{total_layers})...", advance=1)
    else:
        for i, idx in enumerate(used):
            idx_int = int(idx)
            if idx_int < 0:
                continue
            if params.skip_bg and bg_idx == idx_int:
                _print(f"Skip BG idx {idx_int}")
                continue

            mask = (color_idx == idx_int) & visible
            rgb = palette[idx_int]
            pal_hex = "#" + rgb_to_hex(rgb)

            # Determine per-layer hatch_angle
            if params.hatch_angles:
                angles_list = params.hatch_angles
                layer_angle = angles_list[min(layers_count, len(angles_list) - 1)] if angles_list else 0.0
            else:
                layer_angle = params.hatch_angle

            # Build per-layer params with hatch_angle
            layer_params = RenderParams(**{**params.__dict__, "hatch_angle": layer_angle})

            # Compute layer stats if requested
            if show_stats:
                layer_stat = compute_layer_stats(mask, layer_params.line_step)
                layer_stat["color_name"] = rough_color_name(rgb)
                layer_stat["hex"] = pal_hex
                processing_stats["total_segments"] += layer_stat["segments"]
                processing_stats["legacy_pen_lifts"] += layer_stat["legacy_lifts"]
                processing_stats["optimized_pen_lifts"] += layer_stat["optimized_lifts"]
                processing_stats["layer_stats"].append(layer_stat)

            result = _process_single_layer(idx_int, rgb, mask, layer_params, marker_counters, marker_palette, color_map)

            if result.is_layer_generated and result.color_map_entry:
                # Extract path start for optimize_travel
                path_start = (0.0, 0.0)
                if result.groups:
                    first_group = result.groups[0]
                    match = re.search(r'd="([^"]*)"', first_group)
                    if match:
                        path_start = _extract_path_start(match.group(1))

                layer_data.append(
                    {
                        "groups": result.groups,
                        "color_map_entry": result.color_map_entry,
                        "pal_hex": pal_hex,
                        "hatch_angle": layer_angle,
                        "path_start": path_start,
                    }
                )
                color_map_used[pal_hex] = result.color_map_entry
                if result.groups:
                    layers_count += 1

    # --optimize-travel: reorder layers by nearest-neighbor
    if optimize_travel and len(layer_data) > 1:
        # Use image center as start position
        start_pos = (W / 2.0, H / 2.0)
        layer_data = optimize_layer_order(layer_data, start=start_pos)
        # Rebuild color_map_used in optimized order
        color_map_used = {}
        for ld in layer_data:
            color_map_used[ld["pal_hex"]] = ld["color_map_entry"]

    processing_stats["layers_generated"] = layers_count

    if layers_count == 0:
        raise SystemExit("No layers produced.")

    # Assemble groups with optional rotation transforms for hatch_angle
    for ld in layer_data:
        angle = ld.get("hatch_angle", 0.0)
        if abs(angle) > 0.001:
            # Wrap layer groups in a rotation transform
            cx = W / 2.0
            cy = H / 2.0
            transform = f' transform="rotate({angle:.2f},{cx:.2f},{cy:.2f})"'
            all_groups.append(f"<g{transform}>\n")
            all_groups.extend(ld["groups"])
            all_groups.append("</g>\n")
        else:
            all_groups.extend(ld["groups"])

    # Step 5: Writing SVG — viewBox uses integer dimensions
    W_int = int(round(W))  # noqa: N806
    H_int = int(round(H))  # noqa: N806

    if use_progress:
        with progress:
            task5 = progress.add_task("[5/5] Writing SVG...", total=1)
            svg = (
                f'<svg xmlns="http://www.w3.org/2000/svg" '
                f'width="{W_int}" height="{H_int}" viewBox="0 0 {W_int} {H_int}">\n' + "".join(all_groups) + "</svg>\n"
            )
            output_path.write_text(svg, encoding="utf-8")
            progress.update(task5, completed=1)
    else:
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{W_int}" height="{H_int}" viewBox="0 0 {W_int} {H_int}">\n' + "".join(all_groups) + "</svg>\n"
        )
        output_path.write_text(svg, encoding="utf-8")

    _print(
        f"Saved {layers_count} color layers to {output_path} "
        f"(separate_outline={params.separate_outline}, naming_mode={params.naming_mode})"
    )

    return color_map_used, processing_stats


# --------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------


def _load_config_session(args) -> Tuple[RenderParams, Optional[Dict], Optional[Dict], Optional[str]]:
    """Load configuration from a session JSON file."""
    session_path = Path(args.use_session)
    session = load_session(session_path)

    p_dict = session["params"]
    params = RenderParams(
        max_palette=p_dict.get("max_palette", 12),
        line_step=p_dict.get("line_step", 4),
        alpha_threshold=p_dict.get("alpha_threshold", 10),
        min_pixels=p_dict.get("min_pixels", 200),
        stroke_width=p_dict.get("stroke_width", 0.5),
        outline_width=p_dict.get("outline_width", 0.8),
        skip_bg=p_dict.get("skip_background", False),
        white_medium=p_dict.get("white_medium", False),
        paper_white_soft=p_dict.get("paper_white_soft", 20),
        scale=p_dict.get("scale", 1.0),
        separate_outline=p_dict.get("separate_outline", False),
        naming_mode=p_dict.get("naming_mode", "inkscape"),
        continuous_paths=p_dict.get("continuous_paths", False),
        arc_radius=p_dict.get("arc_radius", 0.0),
        hatch_angles=p_dict.get("hatch_angles", None),
        hatch_angle=p_dict.get("hatch_angle", 0.0),
    )
    color_map = session["color_map"]

    marker_palette = None
    palette_file = session.get("palette_file")
    if palette_file:
        pf = Path(palette_file)
        if not pf.exists():
            pf = session_path.parent / palette_file
        if pf.exists():
            marker_palette = load_marker_palette(pf)
            palette_file = str(pf)

    return params, marker_palette, color_map, palette_file


def _load_config_cli(args) -> Tuple[RenderParams, Optional[Dict], Optional[Dict], Optional[str]]:
    """Load configuration from CLI arguments."""
    marker_palette = None
    if args.palette_file:
        marker_palette = load_marker_palette(Path(args.palette_file))

    sw = args.stroke_width
    if sw is None and marker_palette and "tip_width_mm" in marker_palette:
        sw = float(marker_palette["tip_width_mm"])
    if sw is None:
        sw = 0.5

    ow = args.outline_width if args.outline_width is not None else max(1.0, sw * 1.6)

    params = RenderParams(
        max_palette=args.max_palette,
        line_step=args.line_step,
        alpha_threshold=args.alpha_threshold,
        min_pixels=args.min_pixels,
        stroke_width=sw,
        outline_width=ow,
        skip_bg=not args.no_skip_background,
        white_medium=args.white_medium,
        paper_white_soft=args.paper_white_soft,
        scale=args.scale,
        separate_outline=args.separate_outline,
        naming_mode=args.naming_mode,
        continuous_paths=args.continuous_paths,
        arc_radius=args.arc_radius,
    )
    return params, marker_palette, None, args.palette_file


def get_run_configuration(
    args, preset_name: Optional[str] = None
) -> Tuple[RenderParams, Optional[Dict], Optional[Dict], Optional[str]]:
    """Determine the runtime configuration based on arguments.

    Parameters
    ----------
    args
        Parsed argparse ``Namespace`` (or any object exposing the same
        attribute names).
    preset_name
        Optional name of a :mod:`hatchsvg.presets` entry. Preset values are
        applied as a base; any explicit CLI flags override them. Ignored when
        ``args.use_session`` is set, since session files already encode the
        full configuration.
    """
    if args.use_session:
        return _load_config_session(args)
    if preset_name:
        return _load_config_cli_with_preset(args, preset_name)
    return _load_config_cli(args)


def _load_config_cli_with_preset(
    args, preset_name: str
) -> Tuple[RenderParams, Optional[Dict], Optional[Dict], Optional[str]]:
    """Build a config from CLI args with a named preset as the base layer.

    Strategy: snapshot the user's explicit CLI values first, then overlay the
    preset's defaults for any field the user did NOT explicitly set. This
    means ``--preset logo --line-step 2`` produces a logo preset whose
    ``line_step`` is 2 (overridden) and whose ``max_palette`` is 6 (from
    preset, since the user didn't pass ``--max-palette``).
    """
    from hatchsvg.presets import PRESETS

    if preset_name not in PRESETS:
        raise ValueError(f"Unknown preset '{preset_name}'. Available: {', '.join(sorted(PRESETS.keys()))}")

    spec = PRESETS[preset_name]
    # Build a snapshot of the user's explicit CLI values for RenderParams fields.
    # Any field the user touched keeps its value; any field they didn't touch
    # falls back to the preset's value.
    explicit = _extract_explicit_args(args)

    # Merge: preset values are defaults; explicit values win.
    merged: Dict[str, Any] = {}
    for key, value in spec.items():
        if key == "description":
            continue
        merged[key] = value
    for key, value in explicit.items():
        merged[key] = value

    # Build RenderParams from the merged dict. This is the only safe way to
    # set a mix of preset defaults + explicit overrides without re-argparsing.
    params = RenderParams(
        max_palette=merged.get("max_palette", 12),
        line_step=merged.get("line_step", 4),
        alpha_threshold=merged.get("alpha_threshold", 10),
        min_pixels=merged.get("min_pixels", 200),
        stroke_width=merged.get("stroke_width", 0.5),
        outline_width=merged.get("outline_width", 0.8),
        skip_bg=merged.get("skip_bg", False),
        white_medium=merged.get("white_medium", False),
        paper_white_soft=merged.get("paper_white_soft", 20),
        scale=merged.get("scale", 1.0),
        separate_outline=merged.get("separate_outline", False),
        naming_mode=merged.get("naming_mode", "inkscape"),
        continuous_paths=merged.get("continuous_paths", False),
        arc_radius=merged.get("arc_radius", 0.0),
        hatch_angles=merged.get("hatch_angles", None),
        hatch_angle=merged.get("hatch_angle", 0.0),
    )

    # Load palette if provided (not affected by preset)
    marker_palette = None
    if args.palette_file:
        marker_palette = load_marker_palette(Path(args.palette_file))

    # Recompute stroke/outline widths the same way _load_config_cli does
    sw = params.stroke_width
    if sw == 0.5 and marker_palette and "tip_width_mm" in marker_palette:
        # 0.5 is the RenderParams default; only override if user didn't pass --stroke-width
        if "stroke_width" not in explicit:
            sw = float(marker_palette["tip_width_mm"])
    if params.outline_width == 0.8 and "outline_width" not in explicit:
        params = RenderParams(**{**params.__dict__, "stroke_width": sw, "outline_width": max(1.0, sw * 1.6)})
    else:
        params = RenderParams(**{**params.__dict__, "stroke_width": sw})

    return params, marker_palette, None, args.palette_file


def _extract_explicit_args(args) -> Dict[str, Any]:
    """Return a dict of CLI args the user explicitly set on the command line.

    Compares each attribute of ``args`` against the corresponding argparse
    action's default. Anything that differs is treated as explicit. For
    store_true flags, presence (value=True) is explicit; absence is not.

    The parser instance must be attached to ``args`` as ``_hatchsvg_parser``
    (the CLI does this so we don't have to walk the call stack).

    Returns
    -------
    dict
        Mapping of ``RenderParams`` field name to value, containing only the
        fields the user touched. Field names are normalized to ``RenderParams``
        field names (e.g. ``--no-skip-background`` becomes ``skip_bg``).
    """
    import argparse as _argparse

    parser = getattr(args, "_hatchsvg_parser", None)
    explicit: Dict[str, Any] = {}
    if parser is None:
        return explicit

    for action in parser._actions:
        if not isinstance(action, _argparse.Action):
            continue
        if action.dest in ("help", "version", "input", "output_svg", "preset"):
            continue
        if not action.option_strings:
            continue
        try:
            current = getattr(args, action.dest)
        except AttributeError:
            continue
        # Normalize: --no-skip-background sets args.no_skip_background=True but
        # means skip_bg=False on RenderParams.
        if action.dest == "no_skip_background" and current is True:
            explicit["skip_bg"] = False
            continue
        # store_true: explicit iff True
        if isinstance(action, _argparse._StoreTrueAction):
            if current is True:
                explicit[action.dest] = current
            continue
        # store_false: explicit iff False
        if isinstance(action, _argparse._StoreFalseAction):
            if current is False:
                explicit[action.dest] = current
            continue
        # Anything else: explicit iff different from default
        if current != action.default:
            explicit[action.dest] = current

    return explicit


def _display_stats_table(stats: Dict[str, Any]) -> None:
    """Display the processing statistics table."""
    if not HAS_RICH:
        _display_stats_table_simple(stats)
        return

    console = Console()

    # Calculate derived stats
    total_segments = stats.get("total_segments", 0)
    legacy_lifts = stats.get("legacy_pen_lifts", 0)
    optimized_lifts = stats.get("optimized_pen_lifts", 0)
    layers = stats.get("layers_generated", 0)
    w, h = stats.get("image_dimensions", (0, 0))
    colors = stats.get("colors_detected", 0)

    # Calculate lift reduction
    reduction_pct = 0.0
    if legacy_lifts > 0:
        reduction_pct = (1 - optimized_lifts / legacy_lifts) * 100

    # Estimate plot times (conservative: 0.1s per pen lift, 0.02s per segment draw)
    legacy_time = (legacy_lifts * 0.1) + (total_segments * 0.02)
    optimized_time = (optimized_lifts * 0.1) + (total_segments * 0.02)
    time_saved = legacy_time - optimized_time
    time_saved_pct = (time_saved / legacy_time * 100) if legacy_time > 0 else 0

    # Main stats table
    table = Table(title="Processing Statistics", show_header=True, header_style="bold magenta")
    table.add_column("Statistic", style="cyan", width=30)
    table.add_column("Value", style="green", width=20)

    table.add_row("Image Dimensions", f"{w} x {h}")
    table.add_row("Colors Detected", str(colors))
    table.add_row("Layers Generated", str(layers))
    table.add_row("Total Segments", f"{total_segments:,}")
    table.add_row("Pen Lifts (legacy)", f"{legacy_lifts:,}")
    table.add_row("Pen Lifts (optimized)", f"{optimized_lifts:,}")
    table.add_row("Pen Lift Reduction", f"{reduction_pct:.1f}%")
    table.add_row("Estimated Plot Time (legacy)", f"~{legacy_time / 60:.1f} min")
    table.add_row("Estimated Plot Time (optimized)", f"~{optimized_time / 60:.1f} min")
    table.add_row("Time Saved", f"~{time_saved / 60:.1f} min ({time_saved_pct:.0f}%)")

    console.print(Panel(table, title="[bold]Processing Statistics[/bold]", expand=False))

    # Per-layer breakdown if available
    layer_stats = stats.get("layer_stats", [])
    if layer_stats:
        layer_table = Table(title="Layer Breakdown", show_header=True, header_style="bold cyan")
        layer_table.add_column("Layer", style="white", width=15)
        layer_table.add_column("Segments", justify="right", style="yellow")
        layer_table.add_column("Pen Lifts (opt)", justify="right", style="green")
        layer_table.add_column("Components", justify="right", style="blue")
        layer_table.add_column("Reduction", justify="right", style="magenta")

        for ls in layer_stats:
            layer_table.add_row(
                f"{ls.get('color_name', 'unknown')} ({ls.get('hex', '#000000')})",
                f"{ls.get('segments', 0):,}",
                f"{ls.get('optimized_lifts', 0):,}",
                f"{ls.get('component_count', 0):,}",
                f"{ls.get('reduction_pct', 0):.1f}%",
            )

        console.print(Panel(layer_table, title="[bold]Layer Breakdown[/bold]", expand=False))


def _display_stats_table_simple(stats: Dict[str, Any]) -> None:
    """Display stats using simple print formatting (when Rich is not available)."""
    total_segments = stats.get("total_segments", 0)
    legacy_lifts = stats.get("legacy_pen_lifts", 0)
    optimized_lifts = stats.get("optimized_pen_lifts", 0)
    layers = stats.get("layers_generated", 0)
    w, h = stats.get("image_dimensions", (0, 0))
    colors = stats.get("colors_detected", 0)

    reduction_pct = 0.0
    if legacy_lifts > 0:
        reduction_pct = (1 - optimized_lifts / legacy_lifts) * 100

    legacy_time = (legacy_lifts * 0.1) + (total_segments * 0.02)
    optimized_time = (optimized_lifts * 0.1) + (total_segments * 0.02)
    time_saved = legacy_time - optimized_time
    time_saved_pct = (time_saved / legacy_time * 100) if legacy_time > 0 else 0

    print("\n" + "=" * 50)
    print("Processing Statistics")
    print("=" * 50)
    print(f"  Image Dimensions:     {w} x {h}")
    print(f"  Colors Detected:       {colors}")
    print(f"  Layers Generated:      {layers}")
    print(f"  Total Segments:        {total_segments:,}")
    print(f"  Pen Lifts (legacy):    {legacy_lifts:,}")
    print(f"  Pen Lifts (optimized): {optimized_lifts:,}")
    print(f"  Pen Lift Reduction:   {reduction_pct:.1f}%")
    print(f"  Est. Plot Time (leg):  ~{legacy_time / 60:.1f} min")
    print(f"  Est. Plot Time (opt):  ~{optimized_time / 60:.1f} min")
    print(f"  Time Saved:            ~{time_saved / 60:.1f} min ({time_saved_pct:.0f}%)")
    print("=" * 50)

    layer_stats = stats.get("layer_stats", [])
    if layer_stats:
        print("\nLayer Breakdown:")
        print("-" * 70)
        print(f"{'Layer':<20} {'Segments':>10} {'Pen Lifts':>10} {'Components':>12} {'Reduction':>10}")
        print("-" * 70)
        for ls in layer_stats:
            name = f"{ls.get('color_name', 'unknown')} ({ls.get('hex', '#000000')})"
            print(
                f"{name:<20} {ls.get('segments', 0):>10,} {ls.get('optimized_lifts', 0):>10,} "
                f"{ls.get('component_count', 0):>12,} {ls.get('reduction_pct', 0):>9.1f}%"
            )
        print("-" * 70)
