"""Shared pytest fixtures for png2svg tests."""

from pathlib import Path

import numpy as np
import pytest

PALETTES_DIR = Path(__file__).parent.parent / "color_palettes"


@pytest.fixture
def crayola_palette():
    """Load the bundled Crayola 10ct Fine Line Classic palette."""
    from png2svg.core import load_marker_palette

    palette_path = PALETTES_DIR / "crayola_10ct_fine_line_classic.json"
    return load_marker_palette(palette_path)


@pytest.fixture
def jot_palette():
    """Load the bundled Jot 20ct Washable Fineline palette."""
    from png2svg.core import load_marker_palette

    palette_path = PALETTES_DIR / "jot_20ct_washable_fineline.json"
    return load_marker_palette(palette_path)


@pytest.fixture
def small_rgba_image():
    """10x10 RGBA image: white background with a 6x6 red square in the middle.

    Returns
    -------
    numpy.ndarray
        Shape (10, 10, 4), dtype uint8. Channels are R, G, B, A.
    """
    img = np.zeros((10, 10, 4), dtype=np.uint8)
    img[:, :, 3] = 255  # fully opaque
    img[:, :, :3] = 255  # white background
    img[2:8, 2:8, 0] = 255  # red square
    img[2:8, 2:8, 1] = 0
    img[2:8, 2:8, 2] = 0
    return img


@pytest.fixture
def tmp_output_path(tmp_path):
    """Provide a temporary output path ending in .svg."""
    return tmp_path / "out.svg"
