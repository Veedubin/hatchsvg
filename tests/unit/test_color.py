"""Tests for color utility functions."""

from png2svg.core import luminance, rgb_to_hex, rgb_to_hsv_deg, rough_color_name


def test_luminance_black():
    assert luminance((0, 0, 0)) == 0.0


def test_luminance_white():
    assert abs(luminance((255, 255, 255)) - 255.0) < 0.01


def test_luminance_red():
    # Perceptual luminance weights: R=0.2126
    assert abs(luminance((255, 0, 0)) - 0.2126 * 255) < 0.01


def test_rgb_to_hex_red():
    assert rgb_to_hex((255, 0, 0)) == "FF0000"


def test_rgb_to_hex_mixed():
    assert rgb_to_hex((0, 255, 128)) == "00FF80"


def test_rough_color_name_red():
    assert rough_color_name((255, 0, 0)) == "red"


def test_rough_color_name_gray():
    assert rough_color_name((128, 128, 128)) == "gray"


def test_rough_color_name_white():
    assert rough_color_name((250, 250, 250)) == "white"


def test_rough_color_name_black():
    assert rough_color_name((5, 5, 5)) == "black"


def test_rgb_to_hsv_deg_red():
    h, s, v = rgb_to_hsv_deg((255, 0, 0))
    assert abs(h - 0.0) < 0.01
    assert abs(s - 1.0) < 0.01
    assert abs(v - 1.0) < 0.01


def test_rgb_to_hsv_deg_green():
    h, s, v = rgb_to_hsv_deg((0, 255, 0))
    assert abs(h - 120.0) < 0.01
    assert abs(s - 1.0) < 0.01
    assert abs(v - 1.0) < 0.01
