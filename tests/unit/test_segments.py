"""Tests for find_segments_in_row."""

import numpy as np

from hatchsvg.core import find_segments_in_row


def test_find_segments_in_row_empty():
    row = np.zeros(10, dtype=bool)
    assert find_segments_in_row(row) == []


def test_find_segments_in_row_single():
    row = np.zeros(10, dtype=bool)
    row[5] = True
    assert find_segments_in_row(row) == [(5, 6)]


def test_find_segments_in_row_multiple():
    row = np.array([True, True, False, False, True, True], dtype=bool)
    assert find_segments_in_row(row) == [(0, 2), (4, 6)]


def test_find_segments_in_row_full_row():
    row = np.ones(8, dtype=bool)
    assert find_segments_in_row(row) == [(0, 8)]


def test_find_segments_in_row_at_start():
    row = np.array([True, True, False, True], dtype=bool)
    assert find_segments_in_row(row) == [(0, 2), (3, 4)]
