# Context: png2svg SonarLint Cognitive Complexity Refactor

## Objective
Resolve two SonarLint findings (`python:S3776`) in `png2svg.py` by reducing Cognitive Complexity:
- `_resolve_stroke_style` (was reported at line ~376)
- `_create_layer_groups` (was reported at line ~452)

The functional behavior of the tool should remain unchanged; this is a structural refactor to improve maintainability and satisfy the rule threshold (<= 15).

## What Changed

### 1) `_resolve_stroke_style` refactor
**Problem:** The function mixed several concerns (white-medium detection, default hatch spacing selection, session override mapping, palette mapping, fallback naming, final safeguards) in one block with multiple nested branches.

**Solution:** Split the logic into focused helpers and kept the original evaluation order:
1. White-medium detection (computed first, then may be overridden by session map)
2. Default hatch spacing + shade selection based on luminance
3. Session color-map override (marker name/hex/rgb + hatch_step + white-medium flag)
4. Marker palette mapping (only if session did not set `stroke_rgb`)
5. Fallback mapping (if still unresolved)
6. Final safeguards + paper-white override

**New helpers:**
- `_is_white_medium_pixel(rgb, params) -> bool`
- `_default_hatch_spacing(params, lum) -> (line_step, shade)`
- `_apply_session_color_map(pal_key, color_map, ls, is_white) -> (marker_name, marker_hex, stroke_rgb, ls, is_white)`
- `_apply_marker_palette_mapping(rgb, marker_palette, stroke_rgb, marker_name, marker_hex) -> (...)`
- `_apply_fallback_style(rgb, shade, stroke_rgb, marker_name, marker_hex) -> (stroke_rgb, marker_hex, marker_name)`
- `_apply_paper_white_override(stroke_rgb, marker_hex, marker_name, is_white) -> (...)`

This reduces Cognitive Complexity in the primary function because branching now lives in small helper functions (method calls are “free” for Sonar’s metric).

### 2) `_create_layer_groups` refactor
**Problem:** The function combined naming logic and separate/combined outline rendering logic, creating multiple decision paths.

**Solution:** Split into helpers:
- `_layer_base_name(...)` — preserves both `"flat"` and `"inkscape"` naming rules, including marker counters.
- `_part_id(...)` — preserves the existing ID behavior for hatch/outline groups (flat uses `base_name-*`, inkscape uses `hatch_{idx}` / `outline_{idx}`).
- `_append_hatch_group(...)`, `_append_outline_group(...)`, `_append_combined_group(...)` — isolate string formatting and reduce branching.

## Behavioral Notes (Intentionally Preserved)
- **Naming behavior** is unchanged for both `--naming-mode flat` and `--naming-mode inkscape`.
- **Separate outline mode** (`--separate-outline`) still emits hatch and outline groups exactly as before (including which stroke-width each uses).
- **Paper/white medium behavior** still forces the “white” layers to use `stroke_rgb=(0,0,0)`, `marker_hex=#000000`, `marker_name=WhiteOutline`.
- The only output difference you may notice is purely formatting-related (e.g., code organization). SVG output structure is preserved.

## Files Produced
- `png2svg_refactor.py` — the refactored drop-in replacement for `png2svg.py`.

## How To Apply In Your Repo
1. Replace your repo file:
   - From: `/home/jcharles/Projects/python/png2svg/png2svg.py`
   - To: the contents of `png2svg_refactor.py`

2. Run a quick smoke test:
```bash
python3 png2svg.py input.png out.svg --max-palette 12 --line-step 4
```

3. If you use sessions/palettes, validate those paths too:
```bash
python3 png2svg.py input.png out.svg --palette-file markers.json --save-session
python3 png2svg.py input.png out2.svg --use-session out.svg.session.json
```

## Validation Checklist
- Script runs with the same CLI flags as before.
- SVG output renders in Inkscape; layers/groups present and IDs follow the expected naming mode.
- SonarLint no longer flags `_resolve_stroke_style` and `_create_layer_groups` for `python:S3776`.
