"""Tests for optimize_layer_order (used by --optimize-travel)."""

from png2svg.core import optimize_layer_order


def test_optimize_layer_order_single_layer():
    """Single layer is returned as-is."""
    layers = [{"path_start": (10.0, 20.0)}]
    result = optimize_layer_order(layers)
    assert result == layers


def test_optimize_layer_order_empty_list():
    """Empty list returns empty list."""
    assert optimize_layer_order([]) == []


def test_optimize_layer_order_two_layers_picks_closer_first():
    """With start at (0,0), the layer closer to origin should come first."""
    layers = [
        {"path_start": (100.0, 100.0)},  # far
        {"path_start": (5.0, 5.0)},  # close to origin
    ]
    result = optimize_layer_order(layers, start=(0.0, 0.0))
    # The closer layer (index 1) should be first
    assert result[0]["path_start"] == (5.0, 5.0)
    assert result[1]["path_start"] == (100.0, 100.0)


def test_optimize_layer_order_idempotent_for_colocated():
    """Layers at the same point preserve their relative order."""
    layers = [
        {"path_start": (50.0, 50.0), "name": "A"},
        {"path_start": (50.0, 50.0), "name": "B"},
    ]
    result = optimize_layer_order(layers, start=(0.0, 0.0))
    assert len(result) == 2
    assert result[0]["name"] == "A"
    assert result[1]["name"] == "B"


def test_optimize_layer_order_three_layers():
    """Three layers with known distances: nearest-neighbor ordering."""
    layers = [
        {"path_start": (0.0, 100.0)},  # far from origin
        {"path_start": (10.0, 0.0)},  # close to origin
        {"path_start": (5.0, 5.0)},  # closest to origin
    ]
    result = optimize_layer_order(layers, start=(0.0, 0.0))
    # Closest to origin first
    assert result[0]["path_start"] == (5.0, 5.0)
    # Then the next closest to (5,5) is (10,0) — distance ~7.07
    # vs (0,100) — distance ~95.0
    assert result[1]["path_start"] == (10.0, 0.0)
    assert result[2]["path_start"] == (0.0, 100.0)


def test_optimize_layer_order_default_start_origin():
    """Default start position is (0,0)."""
    layers = [
        {"path_start": (100.0, 100.0)},
        {"path_start": (1.0, 1.0)},
    ]
    result = optimize_layer_order(layers)
    assert result[0]["path_start"] == (1.0, 1.0)


def test_optimize_layer_order_missing_path_start():
    """Layer without path_start defaults to (0,0)."""
    layers = [
        {"path_start": (100.0, 100.0)},
        {},  # missing path_start
    ]
    result = optimize_layer_order(layers, start=(0.0, 0.0))
    # The empty layer defaults to (0,0) which is closest to origin
    assert result[0] == {}
    assert result[1]["path_start"] == (100.0, 100.0)
