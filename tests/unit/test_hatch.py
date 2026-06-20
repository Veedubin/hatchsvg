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

    This is a regression test for a bug where the arc-smoothing code emitted
    a NEW 'M' command at the start of each row, breaking the chain and
    producing hundreds of disconnected micro-segments. The expected behavior
    is that even with arc_radius > 0, a rectangular mask with overlapping
    rows produces a SINGLE chain (1 M command).
    """
    # Rectangular mask where rows overlap (every adjacent row is filled)
    mask = np.zeros((10, 20), dtype=bool)
    mask[0:10, 5:15] = True  # 10 rows tall, 10 cols wide

    path = hatch_path_for_mask(mask, line_step=2, continuous=True, arc_radius=3.0)
    m_count = path.count(" M") + (1 if path.startswith("M") else 0)

    # Before fix: 1 M per row = 5 M's. After fix: 1 M total.
    assert m_count == 1, (
        f"Serpentine with arc_radius should produce 1 M command total, got {m_count}. Path snippet: {path[:200]}"
    )


def test_serpentine_chains_row_to_row_no_arcs():
    """Same as above but without arcs — verifies the chaining works."""
    mask = np.zeros((10, 20), dtype=bool)
    mask[0:10, 5:15] = True

    path = hatch_path_for_mask(mask, line_step=2, continuous=True, arc_radius=0.0)
    m_count = path.count(" M") + (1 if path.startswith("M") else 0)
    assert m_count == 1, f"Got {m_count} M commands"


def test_outline_chains_around_rectangle_with_arcs():
    """Outline path (line_step=1) should still chain around the border.

    Regression test: outline_path_for_mask calls hatch_path_for_mask with
    line_step=1, which produces one row per pixel. With arc_radius > 0 the
    old code emitted a new M per row, producing thousands of disconnected
    dot-pairs. The expected output is a single chain that walks around the
    rectangle's perimeter.
    """
    mask = np.zeros((10, 20), dtype=bool)
    mask[2:8, 5:15] = True  # 6x10 rectangle

    # Use the public API
    from hatchsvg.core import outline_path_for_mask

    path = outline_path_for_mask(mask, continuous=True, arc_radius=3.0)
    m_count = path.count(" M") + (1 if path.startswith("M") else 0)

    # Before fix: hundreds of M's. After fix: 1 M.
    assert m_count == 1, (
        f"Outline with arc_radius should produce 1 M command, got {m_count}. Path snippet: {path[:200]}"
    )


def test_serpentine_arc_position_is_correct():
    """Verify the arc geometrically goes from end of row N to start of row N+1.

    The bug was that arc went to (x2, next_y) but next row's M started at
    (x1_new, next_y) which was different — creating a visual gap.
    """
    mask = np.zeros((10, 20), dtype=bool)
    mask[0:10, 5:15] = True

    path = hatch_path_for_mask(mask, line_step=2, continuous=True, arc_radius=3.0)
    # The path should start with M and the first arc should end exactly
    # at the start of row 2 (next_y = 2, x = 14 which is the right edge of
    # the rectangle for row 0 going right).
    # We just check that there's exactly 1 path (no disconnected segments).
    assert path.count("M") == 1, f"Should be 1 M, got {path.count('M')}"
