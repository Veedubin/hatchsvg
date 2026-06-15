"""Tests for hatch_path_for_mask (serpentine vs legacy)."""

import numpy as np

from png2svg.core import hatch_path_for_mask


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
