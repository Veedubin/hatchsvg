"""Named parameter presets for common use cases.

Presets are partial overrides for :class:`hatchsvg.core.RenderParams` — they
provide sensible defaults that the user can still refine with individual CLI
flags. Apply a preset via ``--preset portrait`` etc.

To add a new preset, append to :data:`PRESETS` with the fields you want to
override. All other fields keep their :class:`RenderParams` defaults (or any
explicit values the user passes on the command line).
"""

from __future__ import annotations

from typing import Any, Dict, List, TypedDict


class PresetSpec(TypedDict, total=False):
    """Partial RenderParams override plus a human-readable description."""

    description: str
    # RenderParams fields (all optional — only the ones set will override):
    max_palette: int
    line_step: int
    alpha_threshold: int
    min_pixels: int
    stroke_width: float
    outline_width: float
    skip_bg: bool
    white_medium: bool
    paper_white_soft: int
    scale: float
    separate_outline: bool
    naming_mode: str
    continuous_paths: bool
    arc_radius: float


PRESETS: Dict[str, PresetSpec] = {
    "portrait": {
        "description": "Photographic portraits, faces, soft gradients. Tighter hatch spacing + arc smoothing for skin tones.",
        "max_palette": 8,
        "line_step": 3,
        "white_medium": True,
        "paper_white_soft": 15,
        "continuous_paths": True,
        "arc_radius": 5.0,
    },
    "logo": {
        "description": "Brand marks, flat colors, clean edges. Bold hatch + separate outline for crisp boundaries.",
        "max_palette": 6,
        "line_step": 5,
        "separate_outline": True,
        "continuous_paths": True,
        "arc_radius": 3.0,
        "skip_bg": True,
    },
    "line-art": {
        "description": "Pencil sketches, ink drawings, fine line illustrations. Very fine hatch + low min-pixels so thin strokes survive.",
        "max_palette": 4,
        "line_step": 2,
        "min_pixels": 100,
        "white_medium": True,
        "continuous_paths": True,
        "arc_radius": 2.0,
        "skip_bg": True,
    },
    "photo": {
        "description": "Detailed photos, landscapes, complex gradients. High palette count + fine hatch for maximum detail.",
        "max_palette": 12,
        "line_step": 2,
        "white_medium": True,
        "continuous_paths": True,
        "arc_radius": 4.0,
    },
    "sketch": {
        "description": "Hand-drawn rough aesthetic, generative feel. Wider hatch + larger arc radius for visible U-turns.",
        "max_palette": 6,
        "line_step": 4,
        "continuous_paths": True,
        "arc_radius": 6.0,
        "skip_bg": True,
    },
    "fast": {
        "description": "Quick preview, low-fidelity draft. Few colors, wide hatch, no optimization. Renders in seconds.",
        "max_palette": 4,
        "line_step": 8,
        "continuous_paths": False,
        "separate_outline": False,
        "skip_bg": True,
    },
}


def list_presets() -> List[str]:
    """Return the sorted names of all available presets."""
    return sorted(PRESETS.keys())


def get_preset(name: str) -> PresetSpec:
    """Look up a preset by name. Raises :class:`KeyError` if not found."""
    return PRESETS[name]


def apply_preset(base: Dict[str, Any], name: str) -> Dict[str, Any]:
    """Merge a preset's overrides on top of a base dict (non-destructive).

    Returns a new dict with preset values applied. The preset only touches the
    fields it defines — other fields in ``base`` are preserved as-is. This
    lets callers merge presets into a CLI-arg dict in any order.
    """
    spec = PRESETS[name]
    merged = dict(base)
    for key, value in spec.items():
        # Don't let the preset's 'description' field leak into RenderParams
        if key == "description":
            continue
        merged[key] = value
    return merged
