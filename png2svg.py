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

import argparse
from pathlib import Path
import json
import colorsys
import numpy as np
from PIL import Image
from dataclasses import dataclass, field, asdict
from typing import List, Tuple, Optional, Dict, Any


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
    """Serpentine hatch path generation - rows alternate direction, segments chained with H."""
    h, _ = mask.shape
    cmds = []
    step = max(1, line_step)

    for row_idx, y in enumerate(range(0, h, step)):
        row = mask[y]
        segs = find_segments_in_row(row)
        if not segs:
            continue

        # Even rows (0,2,4): left-to-right; Odd rows (1,3,5): right-to-left
        if row_idx % 2 == 1:
            # Reverse segment order and swap start/end for R→L direction
            segs = [(x2, x1) for x1, x2 in reversed(segs)]

        # Chain contiguous segments within the row
        is_first_seg = True
        for x1, x2 in segs:
            if is_first_seg:
                cmds.append(f"M{x1} {y} H{x2}")
                is_first_seg = False
            else:
                # Continue drawing - just extend to new x2
                cmds.append(f"H{x2}")

        # Phase 3: Add arc at row-end reversal (transition to next row)
        if arc_radius > 0 and row_idx % 2 == 0:  # Even row ending, next row goes R→L
            next_y = y + step
            if next_y < h:
                # Add a 180° arc at the right end to smooth the U-turn
                # Arc sweeps from (x2, y) to (x2, next_y) bulging right
                cmds.append(f"A {arc_radius} {arc_radius} 0 0 1 {x2} {next_y}")

    return " ".join(cmds)


def _order_components_nearest_neighbor(
    component_paths: List[str], centroids: List[Tuple[float, float]]
) -> List[str]:
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
        min_dist = float('inf')
        for i in range(n):
            if not visited[i]:
                dist = ((centroids[current][0] - centroids[i][0]) ** 2 +
                        (centroids[current][1] - centroids[i][1]) ** 2) ** 0.5
                if dist < min_dist:
                    min_dist = dist
                    nearest = i

        visited[nearest] = True
        ordered.append(component_paths[nearest])
        current = nearest

    return ordered


def hatch_path_for_mask(mask: np.ndarray, line_step: int, continuous: bool = False,
                        arc_radius: float = 0.0) -> str:
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
        component_mask = (labeled == i)
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
    up = np.zeros_like(mask);  up[1:]   = mask[:-1]
    dn = np.zeros_like(mask);  dn[:-1]  = mask[1:]
    lf = np.zeros_like(mask);  lf[:,1:] = mask[:,:-1]
    rt = np.zeros_like(mask);  rt[:,:-1]= mask[:,1:]

    interior = mask & up & dn & lf & rt
    return mask & ~interior


def outline_path_for_mask(mask: np.ndarray, continuous: bool = False,
                          arc_radius: float = 0.0) -> str:
    """Flatten all outline segments into one path string (border only)."""
    bmask = border_mask(mask)
    return hatch_path_for_mask(bmask, line_step=1, continuous=continuous, arc_radius=arc_radius)


def luminance(rgb: Tuple[int, int, int]) -> float:
    r, g, b = rgb
    return 0.2126*r + 0.7152*g + 0.0722*b


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
    r_n, g_n, b_n = r/255.0, g/255.0, b/255.0
    
    h_val, _, _ = colorsys.rgb_to_hsv(r_n, g_n, b_n)
    return get_hue_name(h_val * 360.0)


def rgb_to_hsv_deg(rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
    """RGB (0-255) -> (H_deg 0-360, S 0-1, V 0-1)."""
    r, g, b = rgb
    h, s, v = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)
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

        score = (3.0 * dh*dh) + (1.0 * ds*ds) + (0.7 * dv*dv)

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
        return {"name": "Unknown", "hex": "#000000", "rgb_tuple": (0,0,0)}

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


def save_session(path: Path, input_path: Path, palette_file: Optional[str],
                 params: RenderParams, color_map_used: Dict[str, Any]):
    """Write a session JSON file."""
    color_map_out = {}
    for pal_hex, entry in color_map_used.items():
        if pal_hex is None: 
            continue
        key = pal_hex.lstrip("#").upper()
        color_map_out[key] = {
            "marker_name": entry.get("marker_name"),
            "marker_hex": entry.get("marker_hex"),
            "marker_rgb": list(entry.get("marker_rgb") or []),
            "palette_rgb": list(entry.get("palette_rgb") or []),
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
        vis_rgb[:, 0].astype(np.uint32) << 16 |
        vis_rgb[:, 1].astype(np.uint32) << 8 |
        vis_rgb[:, 2].astype(np.uint32)
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
            pal.append((raw_p[j], raw_p[j+1], raw_p[j+2]))
        else:
            pal.append((0, 0, 0))
    return idx_arr, pal, visible


# --------------------------------------------------------------------
# Main rendering logic
# --------------------------------------------------------------------

def _detect_background(visible: np.ndarray, color_idx: np.ndarray, palette: List[Tuple[int, int, int]]) -> Optional[int]:
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

    white_thresh_sq = params.paper_white_soft ** 2
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
    pal_key: str,
    color_map: Optional[Dict[str, Any]],
    ls: int,
    is_white: bool
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
    stroke_rgb: Tuple[int, int, int],
    marker_hex: str,
    marker_name: str,
    is_white: bool
) -> Tuple[Tuple[int, int, int], str, str]:
    """Force paper/white medium layers to draw as a black outline only."""
    if not is_white:
        return stroke_rgb, marker_hex, marker_name
    return (0, 0, 0), "#000000", "WhiteOutline"


def _resolve_stroke_style(
    rgb: Tuple[int, int, int],
    params: RenderParams,
    marker_palette: Optional[Dict[str, Any]],
    color_map: Optional[Dict[str, Any]]
) -> StrokeStyle:
    """Determine the stroke color, name, and hatch settings for a layer."""
    lum = luminance(rgb)
    pal_key = ("#" + rgb_to_hex(rgb)).upper()

    is_white = _is_white_medium_pixel(rgb, params)
    ls, shade = _default_hatch_spacing(params, lum)

    marker_name, marker_hex, stroke_rgb, ls, is_white = _apply_session_color_map(
        pal_key, color_map, ls, is_white
    )

    stroke_rgb, marker_name, marker_hex = _apply_marker_palette_mapping(
        rgb, marker_palette, stroke_rgb, marker_name, marker_hex
    )

    stroke_rgb, marker_hex, marker_name = _apply_fallback_style(
        rgb, shade, stroke_rgb, marker_name, marker_hex
    )

    stroke_rgb, marker_hex, marker_name = _apply_paper_white_override(
        stroke_rgb, marker_hex, marker_name, is_white
    )

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
    idx: int,
    style: StrokeStyle,
    mask: np.ndarray,
    params: RenderParams,
    marker_counters: Dict[str, int]
) -> List[str]:
    """Generate the SVG group strings for a specific layer."""
    d_hatch = "" if style.is_white else hatch_path_for_mask(mask, style.line_step, params.continuous_paths, params.arc_radius)
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
    color_map: Optional[Dict[str, Any]]
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


def process_image_to_hatched_svg(
    input_path: Path,
    output_path: Path,
    params: RenderParams,
    marker_palette: Optional[Dict[str, Any]] = None,
    color_map: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Render SVG and return a color_map_used dict for session saving.
    """
    img = Image.open(input_path).convert("RGBA")

    if abs(params.scale - 1.0) > 1e-6:
        w0, h0 = img.size
        w1 = max(1, int(w0 * params.scale))
        h1 = max(1, int(h0 * params.scale))
        print(f"Scaling from {w0}x{h0} → {w1}x{h1}")
        img = img.resize((w1, h1), Image.Resampling.LANCZOS)

    rgba = np.array(img)
    orig_rgb = rgba[:, :, :3]
    alpha = rgba[:, :, 3]

    color_idx, palette, visible = build_color_index_map(
        orig_rgb, alpha, params.alpha_threshold, params.max_palette
    )
    used = np.unique(color_idx[visible])
    print(f"Colors used: {len(used)}")

    bg_idx = None
    if params.skip_bg:
        bg_idx = _detect_background(visible, color_idx, palette)

    all_groups = []
    layers_count = 0
    H, W = visible.shape

    color_map_used = {}
    marker_counters = {}

    for idx in used:
        idx_int = int(idx)
        if idx_int < 0:
            continue
        if params.skip_bg and bg_idx == idx_int:
            print(f"Skip BG idx {idx_int}")
            continue

        mask = (color_idx == idx_int) & visible
        rgb = palette[idx_int]
        pal_hex = "#" + rgb_to_hex(rgb)

        result = _process_single_layer(
            idx_int, rgb, mask, params, marker_counters, marker_palette, color_map
        )

        if result.is_layer_generated and result.color_map_entry:
            all_groups.extend(result.groups)
            color_map_used[pal_hex] = result.color_map_entry
            if result.groups:
                layers_count += 1

    if layers_count == 0:
        raise SystemExit("No layers produced.")

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{W}" height="{H}" viewBox="0 0 {W} {H}">\n' +
        "".join(all_groups) +
        "</svg>\n"
    )
    output_path.write_text(svg, encoding="utf-8")
    print(f"Saved {layers_count} color layers to {output_path} "
          f"(separate_outline={params.separate_outline}, naming_mode={params.naming_mode})")

    return color_map_used


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
        arc_radius=p_dict.get("arc_radius", 0.0)
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
        arc_radius=args.arc_radius
    )
    return params, marker_palette, None, args.palette_file


def get_run_configuration(args) -> Tuple[RenderParams, Optional[Dict], Optional[Dict], Optional[str]]:
    """Determine the runtime configuration based on arguments."""
    if args.use_session:
        return _load_config_session(args)
    else:
        return _load_config_cli(args)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("input")
    p.add_argument("output_svg")
    p.add_argument("--max-palette", type=int, default=12)
    p.add_argument("--line-step", type=int, default=4)
    p.add_argument("--alpha-threshold", type=int, default=10)
    p.add_argument("--min-pixels", type=int, default=200)
    p.add_argument("--stroke-width", type=float, default=None)
    p.add_argument("--outline-width", type=float, default=None)
    p.add_argument("--no-skip-background", action="store_true")
    p.add_argument("--white-medium", action="store_true")
    p.add_argument("--paper-white-soft", type=int, default=20)
    p.add_argument("--scale", type=float, default=1.0)
    p.add_argument("--separate-outline", action="store_true")
    p.add_argument("--palette-file", help="Path to marker palette JSON")
    p.add_argument("--naming-mode", choices=["inkscape", "flat"], default="inkscape")
    p.add_argument("--continuous-paths", action="store_true",
                   help="Generate continuous serpentine paths to reduce pen plotter vibration")
    p.add_argument("--arc-radius", type=float, default=0.0,
                   help="Add arc smoothing at row-end 180° reversals (0 = disabled)")
    p.add_argument("--save-session", action="store_true")
    p.add_argument("--use-session", help="Load previous session JSON")

    a = p.parse_args()

    input_path = Path(a.input)
    output_path = Path(a.output_svg)
    
    # Load configuration
    params, marker_palette, color_map, palette_file = get_run_configuration(a)

    # Run Process
    color_map_used = process_image_to_hatched_svg(
        input_path,
        output_path,
        params,
        marker_palette,
        color_map
    )

    if a.save_session:
        session_out_path = output_path.with_suffix(output_path.suffix + ".session.json")
        save_session(session_out_path, input_path, palette_file, params, color_map_used)


if __name__ == "__main__":
    main()