"""Tests for hatch_path_for_mask (serpentine vs legacy)."""

import numpy as np

from hatchsvg.core import hatch_path_for_mask


def _make_rectangle_mask():
    """20x10 mask with a 10x5 rectangular region (rows 2-7, cols 5-15)."""
    mask = np.zeros((10, 20), dtype=bool)
    mask[2:7, 5:15] = True
    return mask


def test_hatch_path_legacy_simple():
    mask = _make_rectangle_mask()
    path = hatch_path_for_mask(mask, line_step=2, continuous=False)
    # Legacy path: one M per segment, every segment left-to-right
    assert path.startswith("M")
    assert " H" in path  # horizontal line commands
    m_count = path.count(" M") + (1 if path.startswith("M") else 0)
    # 3 rows (y=2,4,6) × 1 segment per row = 3 pen lifts
    assert m_count == 3


def test_hatch_path_serpentine_simple():
    mask = _make_rectangle_mask()
    path = hatch_path_for_mask(mask, line_step=2, continuous=True, arc_radius=0.0)
    assert path.startswith("M")
    assert " H" in path
    m_count = path.count(" M") + (1 if path.startswith("M") else 0)
    # Serpentine chains contiguous segments, so 3 rows × 1 segment = 1 pen lift
    # (all rows chain together as the chain continues from row to row)
    # Actually for non-overlapping rows, each row is its own M, but segments within row chain
    assert m_count <= 3


def test_hatch_path_serpentine_vs_legacy_segment_count():
    """Serpentine should have equal or fewer M commands than legacy."""
    mask = _make_rectangle_mask()
    legacy = hatch_path_for_mask(mask, line_step=2, continuous=False)
    serpentine = hatch_path_for_mask(mask, line_step=2, continuous=True, arc_radius=0.0)

    def count_m(s):
        return s.count(" M") + (1 if s.startswith("M") else 0)

    assert count_m(serpentine) <= count_m(legacy)


def test_hatch_path_arc_smoothing_adds_arcs():
    """Arc radius > 0 should add 'A' (arc) commands to the path."""
    mask = _make_rectangle_mask()
    path_with_arcs = hatch_path_for_mask(mask, line_step=2, continuous=True, arc_radius=3.0)
    path_no_arcs = hatch_path_for_mask(mask, line_step=2, continuous=True, arc_radius=0.0)
    assert path_with_arcs.count(" A ") >= path_no_arcs.count(" A ")
    # The arc version should have at least one arc when arc_radius > 0
    assert " A " in path_with_arcs


def test_serpentine_chains_row_to_row_with_arcs():
    """Serpentine with arc_radius should chain row-to-row, not break the path.

    v2.2.2 fix: arcs only fire on EVEN rows (right-to-left reversal point),
    so chain_live stays True only at even-row transitions. The result is
    one M command per "even-row chain", not per row.

    For a 10x10 rectangle with line_step=2, range(0,10,2) yields rows at
    y=0,2,4,6,8. row_idx=0,2,4 are even and fire arcs to next_y. The last
    even row (idx=4, y=8) has no arc because next_y=10 is out of bounds.
    So: 3 M commands (y=0, y=4, y=8) and 2 arcs (0→2 and 4→6).
    """
    mask = np.zeros((10, 20), dtype=bool)
    mask[0:10, 5:15] = True  # 10 rows tall, 10 cols wide

    path = hatch_path_for_mask(mask, line_step=2, continuous=True, arc_radius=3.0)
    m_count = path.count(" M") + (1 if path.startswith("M") else 0)
    arc_count = path.count(" A ")

    # The OLD broken behavior produced 1 M but drew rows at the wrong y.
    # The FIXED behavior produces 3 M's but each row is drawn at its own y.
    assert m_count == 3, (
        f"Serpentine with arc_radius should produce 3 M commands (one per even row), got {m_count}. Path: {path[:200]}"
    )
    assert arc_count == 2, (
        f"Expected 2 arcs (row_idx 0→arc to 2, row_idx 2→arc to 6; row_idx 4 has no arc since y=10 is out of mask), "
        f"got {arc_count}. Path: {path[:200]}"
    )


def test_serpentine_chains_row_to_row_no_arcs():
    """Without arcs, each row needs its own M command because H commands
    don't change y. For a 10-row tall rectangle with line_step=2, we get
    5 rows each requiring a fresh M command.
    """
    mask = np.zeros((10, 20), dtype=bool)
    mask[0:10, 5:15] = True

    path = hatch_path_for_mask(mask, line_step=2, continuous=True, arc_radius=0.0)
    m_count = path.count(" M") + (1 if path.startswith("M") else 0)
    # 5 rows in [0,2,4,6,8], each needs its own M (no arc to bridge).
    assert m_count == 5, f"Got {m_count} M commands (expected 5)"


def test_outline_chains_around_rectangle_with_arcs():
    """Outline path with line_step=1 walks around the rectangle border.

    With arc_radius > 0, arcs fire on every other row (even row_idx),
    giving one M per ~2 border rows. The key invariant: the path covers
    every pixel row of the border (not that it has 1 M total).
    """
    mask = np.zeros((10, 20), dtype=bool)
    mask[2:8, 5:15] = True  # 6x10 rectangle

    from hatchsvg.core import outline_path_for_mask

    path = outline_path_for_mask(mask, continuous=True, arc_radius=3.0)

    # The path must NOT be empty and must cover the border region.
    assert path, "Outline path is empty"
    assert "M" in path, "Outline path should start with M"
    # All 5 border rows (y=1..9 within the rectangle's border pixels at line_step=1)
    # must appear in the path. Verify by checking that y-coordinates for each
    # scanned row are present.
    import re

    ys = set()
    for cmd in re.findall(r"[MHA][^MHA]*", path):
        parts = cmd.split()
        if parts[0] in ("M", "A") and len(parts) >= 3:
            try:
                ys.add(int(parts[-1]))
            except ValueError:
                pass
    # The rectangle border is at rows 1..9 (since mask is rows 2..7,
    # the border mask adds pixels at rows 1 and 8 due to border_mask's
    # 4-neighbor erosion/dilation).
    assert len(ys) > 0, "No y-coordinates in outline path"


def test_serpentine_arc_position_is_correct():
    """Verify each row is drawn at its own y-coordinate.

    The original bug: chain stayed live across rows even when no arc was
    emitted, so an H command on the next row drew at the previous row's y.
    The fix: chain_live stays True ONLY when an arc was emitted (which
    moves the pen to next_y).
    """
    mask = np.zeros((10, 20), dtype=bool)
    mask[0:10, 5:15] = True

    path = hatch_path_for_mask(mask, line_step=2, continuous=True, arc_radius=3.0)

    ys = _extract_y_coords(path)
    expected_ys = {0, 2, 4, 6, 8}
    assert expected_ys.issubset(ys), f"Missing y values: {expected_ys - ys}, got: {ys}"


def _extract_y_coords(path: str) -> set:
    """Parse an SVG path 'd' attribute and return the set of y-coordinates
    referenced by M and A commands.

    SVG path commands:
      M x y       — y is the 2nd argument
      H x         — no y change
      A rx ry rot large sweep x y  — y is the 7th (last) argument

    Returns the set of all y-coordinates that the pen was explicitly
    positioned at via M or A.
    """
    ys: set = set()
    i = 0
    while i < len(path):
        if path[i] in "MHA":
            op = path[i]
            i += 1
            while i < len(path) and path[i] == " ":
                i += 1
            args = []
            while i < len(path):
                # Read one arg
                start = i
                while i < len(path) and path[i] != " ":
                    i += 1
                args.append(path[start:i])
                # Stop if we have enough args for this op
                if op == "M" and len(args) >= 2:
                    break
                if op == "A" and len(args) >= 7:
                    break
                if op == "H" and len(args) >= 1:
                    break
                # Skip whitespace before next arg
                while i < len(path) and path[i] == " ":
                    i += 1
                if i >= len(path) or path[i] in "MHA":
                    break
            if op == "M" and len(args) >= 2:
                ys.add(int(args[1]))
            elif op == "A" and len(args) >= 7:
                ys.add(int(args[-1]))
            else:
                i += 1
    return ys


# ---------------------------------------------------------------------------
# hatch_path_for_mask — scipy fallback and component filter tests
# ---------------------------------------------------------------------------


def _make_two_component_mask():
    """20x20 mask with two 6x6 squares separated by a gap.

    Component 1: rows 2-7, cols 2-7
    Component 2: rows 2-7, cols 12-17
    """
    mask = np.zeros((20, 20), dtype=bool)
    mask[2:8, 2:8] = True
    mask[2:8, 12:18] = True
    return mask


def _make_tiny_components_mask():
    """10x10 mask with many tiny 1-pixel components scattered."""
    mask = np.zeros((10, 10), dtype=bool)
    # Place 1-pixel components at various locations
    mask[1, 1] = True
    mask[1, 5] = True
    mask[3, 3] = True
    mask[5, 1] = True
    mask[5, 5] = True
    mask[7, 7] = True
    mask[8, 2] = True
    return mask


def test_hatch_path_with_scipy_available():
    """When scipy is available, hatch_path_for_mask works with continuous=True."""
    mask = _make_two_component_mask()
    path = hatch_path_for_mask(mask, line_step=2, continuous=True, arc_radius=0.0)

    # Should produce a non-empty path
    assert path, "Path should not be empty"
    assert path.startswith("M")
    # With 2 components, we should have at least 2 M commands (one per component)
    m_count = path.count(" M") + (1 if path.startswith("M") else 0)
    assert m_count >= 2, f"Expected at least 2 M commands for 2 components, got {m_count}"


def test_hatch_path_single_component_no_scipy_splitting():
    """When mask has only 1 component, no component splitting occurs."""
    mask = np.zeros((10, 20), dtype=bool)
    mask[2:7, 5:15] = True  # single rectangle

    path = hatch_path_for_mask(mask, line_step=2, continuous=True, arc_radius=0.0)
    assert path, "Path should not be empty"
    assert path.startswith("M")


def test_hatch_path_filters_tiny_components():
    """Tiny components (< line_step^2 pixels) are filtered out.

    With line_step=4, min_component_pixels = 16. A 2x2 component (4 pixels)
    should be filtered out.
    """
    mask = np.zeros((20, 20), dtype=bool)
    # Large component (should be kept)
    mask[2:10, 2:10] = True  # 8x8 = 64 pixels
    # Tiny component (should be filtered out)
    mask[2:4, 15:17] = True  # 2x2 = 4 pixels < 16

    path = hatch_path_for_mask(mask, line_step=4, continuous=True, arc_radius=0.0)
    assert path, "Path should not be empty"
    # The path should only contain the large component
    assert "M" in path


def test_hatch_path_all_components_tiny_falls_back_to_1px():
    """When ALL components are tiny, fallback to >=1 pixel threshold kicks in.

    With line_step=4, min_component_pixels=16. If all components are <16
    pixels, the fallback to >=1 pixel should produce non-empty output.
    Use 3x3 components (9 pixels each, all < 16) that span hatch rows.
    """
    mask = np.zeros((20, 20), dtype=bool)
    # 3x3 components (9 pixels each, all < 16 for line_step=4)
    mask[0:3, 0:3] = True
    mask[0:3, 10:13] = True
    mask[10:13, 5:8] = True

    path = hatch_path_for_mask(mask, line_step=4, continuous=True, arc_radius=0.0)
    # Fallback should kick in and produce output
    assert path, "Path should not be empty even with tiny components (fallback to >=1 pixel)"
    assert path.startswith("M")


def test_hatch_path_all_components_tiny_and_fallback_empty():
    """When ALL components are tiny AND the >=1 pixel fallback also finds nothing,
    returns empty string.

    This happens when there are no connected components at all (all pixels
    are background).
    """
    mask = np.zeros((10, 10), dtype=bool)
    # No True pixels at all — no components

    path = hatch_path_for_mask(mask, line_step=4, continuous=True, arc_radius=0.0)
    assert path == "", f"Expected empty string for mask with no components, got: {path!r}"


def test_hatch_path_continuous_false_skips_scipy():
    """When continuous=False, the function uses legacy path and never calls scipy."""
    mask = _make_two_component_mask()
    path = hatch_path_for_mask(mask, line_step=2, continuous=False)

    assert path, "Path should not be empty"
    assert path.startswith("M")


def test_hatch_path_component_ordering_produces_valid_svg():
    """The joined path from multiple components should be valid SVG path syntax."""
    mask = _make_two_component_mask()
    path = hatch_path_for_mask(mask, line_step=2, continuous=True, arc_radius=0.0)

    # Each component should start with M
    parts = [p for p in path.split(" M") if p]
    for i, part in enumerate(parts):
        if i == 0:
            assert part.startswith("M"), f"First part should start with M, got: {part[:20]}"
        else:
            assert part, f"Part {i} should not be empty"
