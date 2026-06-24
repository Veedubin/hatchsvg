"""Integration tests for the CLI binary, including --preset and multi-format inputs."""

import subprocess
from pathlib import Path

import pytest

import hatchsvg

# Project root (parent of tests/)
PROJECT_ROOT = Path(__file__).parent.parent.parent
VENV_HATCHSVG = PROJECT_ROOT / ".venv" / "bin" / "hatchsvg"

# Skip these tests if hatchsvg isn't installed in the venv (CI uses pip install -e .[dev])
pytestmark = pytest.mark.skipif(
    not VENV_HATCHSVG.exists(),
    reason=f"hatchsvg not installed at {VENV_HATCHSVG}",
)


# Generate a small test PNG (procedural, no network) for CLI smoke tests
@pytest.fixture(scope="module")
def small_test_png(tmp_path_factory):
    """Create a 32x32 RGBA test PNG with a red square on opaque white background."""
    import numpy as np
    from PIL import Image

    img_array = np.zeros((32, 32, 4), dtype=np.uint8)
    # Opaque white background (so background detection has something to find)
    img_array[:, :, 0] = 255
    img_array[:, :, 1] = 255
    img_array[:, :, 2] = 255
    img_array[:, :, 3] = 255
    # Red square in the middle
    img_array[8:24, 8:24, 0] = 220
    img_array[8:24, 8:24, 1] = 0
    img_array[8:24, 8:24, 2] = 0
    img = Image.fromarray(img_array, mode="RGBA")
    out = tmp_path_factory.mktemp("cli_inputs") / "tiny.png"
    img.save(out, "PNG")
    return out


def test_cli_version():
    """`hatchsvg --version` exits 0 and prints the version string."""
    result = subprocess.run(
        [str(VENV_HATCHSVG), "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert f"hatchsvg {hatchsvg.__version__}" in result.stdout


def test_cli_help_lists_presets():
    """`hatchsvg --help` mentions the --preset choices."""
    result = subprocess.run(
        [str(VENV_HATCHSVG), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "--preset" in result.stdout
    for preset in ("portrait", "logo", "line-art", "photo", "sketch", "fast"):
        assert preset in result.stdout, f"preset '{preset}' missing from --help output"


def test_cli_runs_with_preset_fast(small_test_png, tmp_path):
    """`hatchsvg in.png out.svg --preset fast` produces a valid SVG."""
    out_svg = tmp_path / "out.svg"
    result = subprocess.run(
        [str(VENV_HATCHSVG), str(small_test_png), str(out_svg), "--preset", "fast"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert out_svg.exists()
    content = out_svg.read_text()
    assert content.startswith("<?xml") or content.startswith("<svg")
    assert "<path" in content


def test_cli_runs_with_preset_line_art(small_test_png, tmp_path):
    """`hatchsvg --preset line-art` works on a small PNG."""
    out_svg = tmp_path / "out.svg"
    result = subprocess.run(
        [str(VENV_HATCHSVG), str(small_test_png), str(out_svg), "--preset", "line-art"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert out_svg.exists()


def test_cli_explicit_flag_overrides_preset(small_test_png, tmp_path):
    """`hatchsvg --preset logo --line-step 2` should succeed (line_step is an override)."""
    out_svg = tmp_path / "out.svg"
    result = subprocess.run(
        [
            str(VENV_HATCHSVG),
            str(small_test_png),
            str(out_svg),
            "--preset",
            "logo",
            "--line-step",
            "2",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"


def test_cli_rejects_unsupported_format(tmp_path):
    """`hatchsvg foo.exe out.svg` exits 1 with a friendly error."""
    fake = tmp_path / "test.exe"
    fake.write_bytes(b"MZ")
    out_svg = tmp_path / "out.svg"
    result = subprocess.run(
        [str(VENV_HATCHSVG), str(fake), str(out_svg)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "unsupported input format" in result.stderr.lower()


def test_cli_rejects_unknown_preset(small_test_png, tmp_path):
    """`hatchsvg --preset bogus` exits 2 (argparse error) before reaching core."""
    out_svg = tmp_path / "out.svg"
    result = subprocess.run(
        [
            str(VENV_HATCHSVG),
            str(small_test_png),
            str(out_svg),
            "--preset",
            "bogus",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    # argparse exits 2 on invalid choice
    assert result.returncode == 2
    assert "invalid choice" in result.stderr.lower()


def test_cli_accepts_jpg_input(tmp_path):
    """`hatchsvg in.jpg out.svg --preset fast` works (multi-format input).

    Uses a 64x64 image so default ``min_pixels=200`` finds enough pixels per
    color after quantization.
    """
    import numpy as np
    from PIL import Image

    # Build a 64x64 RGB image with a solid 32x32 colored square (1024 pixels each color)
    arr = np.full((64, 64, 3), [200, 100, 50], dtype=np.uint8)
    arr[16:48, 16:48] = [50, 200, 100]
    img = Image.fromarray(arr, mode="RGB")
    in_jpg = tmp_path / "test.jpg"
    img.save(in_jpg, "JPEG", quality=80)
    out_svg = tmp_path / "out.svg"

    result = subprocess.run(
        [str(VENV_HATCHSVG), str(in_jpg), str(out_svg), "--preset", "fast"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert out_svg.exists()


def test_cli_save_session_roundtrip(small_test_png, tmp_path):
    """`hatchsvg --save-session` writes a session JSON, --use-session reproduces it."""
    import json

    out_svg = tmp_path / "first.svg"
    # The CLI names the session file "<output>.session.json" (e.g.
    # "first.svg.session.json"). See src/hatchsvg/cli.py:242.
    session_path = tmp_path / "first.svg.session.json"

    # First run: render + save session
    result = subprocess.run(
        [
            str(VENV_HATCHSVG),
            str(small_test_png),
            str(out_svg),
            "--preset",
            "fast",
            "--save-session",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"first run stderr: {result.stderr}"
    assert session_path.exists(), f"session JSON was not written at {session_path}"

    session = json.loads(session_path.read_text())
    assert "image" in session or "input_basename" in session
    assert "params" in session
    assert "color_map" in session

    # Second run: re-render using the saved session
    out_svg2 = tmp_path / "second.svg"
    result = subprocess.run(
        [
            str(VENV_HATCHSVG),
            str(small_test_png),
            str(out_svg2),
            "--use-session",
            str(session_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"second run stderr: {result.stderr}"
    assert out_svg2.exists()


def test_cli_missing_input_file(tmp_path):
    """`hatchsvg /nonexistent.png out.svg` exits 1 with a friendly error."""
    fake = tmp_path / "does_not_exist.png"
    out_svg = tmp_path / "out.svg"
    result = subprocess.run(
        [str(VENV_HATCHSVG), str(fake), str(out_svg)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    # The error message should mention the missing file or "not found"
    err = result.stderr.lower()
    assert "not found" in err or "no such file" in err or "does not exist" in err


def test_cli_stats_flag_runs(small_test_png, tmp_path):
    """`hatchsvg --stats` runs successfully and prints stats to stderr."""
    out_svg = tmp_path / "out.svg"
    result = subprocess.run(
        [
            str(VENV_HATCHSVG),
            str(small_test_png),
            str(out_svg),
            "--preset",
            "fast",
            "--stats",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert out_svg.exists()


def test_cli_help_shows_examples():
    """`hatchsvg --help` shows the Examples: section."""
    result = subprocess.run(
        [str(VENV_HATCHSVG), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "Examples:" in result.stdout


def test_cli_preview_flag_parsed(small_test_png, tmp_path):
    """`hatchsvg --preview` parses and exits 0 (browser open is best-effort)."""
    out_svg = tmp_path / "out.svg"
    result = subprocess.run(
        [
            str(VENV_HATCHSVG),
            str(small_test_png),
            str(out_svg),
            "--preset",
            "fast",
            "--preview",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    # --preview may warn about browser but should not fail
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert out_svg.exists()


def test_cli_split_layers_creates_one_file_per_layer(small_test_png, tmp_path):
    """`hatchsvg --split-layers` creates N+1 files (main + N layer files)."""
    out_svg = tmp_path / "out.svg"
    result = subprocess.run(
        [
            str(VENV_HATCHSVG),
            str(small_test_png),
            str(out_svg),
            "--preset",
            "fast",
            "--split-layers",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert out_svg.exists()

    # Find split-layer files matching the pattern <stem>_<NN>_<name>.svg
    layer_files = sorted(tmp_path.glob("out_??_*.svg"))
    assert len(layer_files) >= 1, f"Expected at least 1 split-layer file, found {len(layer_files)}"
    # Verify naming pattern: out_00_<name>.svg, out_01_<name>.svg, etc.
    for f in layer_files:
        assert f.stem.startswith("out_"), f"Unexpected split-layer filename: {f.name}"
        parts = f.stem.split("_")
        assert len(parts) >= 3, f"Unexpected split-layer filename parts: {parts}"


def test_cli_optimize_travel_runs(tmp_path):
    """`hatchsvg --optimize-travel` on the test image exits 0 and produces valid SVG."""
    project_root = Path(__file__).parent.parent.parent
    test_png = project_root / "tests" / "fixtures" / "test_image.png"
    if not test_png.exists():
        pytest.skip("test_image.png not found in tests/fixtures/")

    out_svg = tmp_path / "out.svg"
    result = subprocess.run(
        [
            str(VENV_HATCHSVG),
            str(test_png),
            str(out_svg),
            "--preset",
            "fast",
            "--optimize-travel",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert out_svg.exists()
    content = out_svg.read_text()
    assert "<svg" in content
    assert "<path" in content


def test_cli_hatch_angles_parses_csv(small_test_png, tmp_path):
    """`hatchsvg --hatch-angles=0,45,90` parses and runs successfully."""
    out_svg = tmp_path / "out.svg"
    result = subprocess.run(
        [
            str(VENV_HATCHSVG),
            str(small_test_png),
            str(out_svg),
            "--preset",
            "fast",
            "--hatch-angles=0,45,90",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert out_svg.exists()


def test_cli_hatch_angles_invalid_value_errors(small_test_png, tmp_path):
    """`hatchsvg --hatch-angles=foo` exits non-zero with a friendly error."""
    out_svg = tmp_path / "out.svg"
    result = subprocess.run(
        [
            str(VENV_HATCHSVG),
            str(small_test_png),
            str(out_svg),
            "--hatch-angles=foo",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    err = result.stderr.lower()
    assert "hatch-angles" in err or "comma-separated" in err or "numbers" in err


def test_cli_skip_background_default_excludes_bg_layer(small_test_png, tmp_path):
    """By default (no flag), the dominant background color is skipped from
    the output. This is a v2.2.1+ behavior — earlier versions had an
    orphan --no-skip-background flag that was registered but never read.
    """
    out_svg = tmp_path / "out.svg"
    result = subprocess.run(
        [str(VENV_HATCHSVG), str(small_test_png), str(out_svg), "--preset", "logo"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    # The synthetic test image is a red square on white background. The
    # white background should be detected and skipped by default.
    assert "Skip BG" in result.stdout, f"Expected 'Skip BG' in stdout: {result.stdout}"

    # Without the bg, the red square is the only color. With the logo
    # preset's separate_outline=True, that's 1 color * 2 (hatch + outline)
    # = 2 groups.
    content = out_svg.read_text(encoding="utf-8")
    total_groups = content.count("<g ")
    assert total_groups == 2, (
        f"Expected 2 groups (1 non-bg color, separate_outline=True), got {total_groups}. "
        f"Output likely missing outline group or includes background."
    )


def test_cli_no_skip_background_includes_bg_layer(small_test_png, tmp_path):
    """--no-skip-background disables background skipping, so ALL detected
    color layers (including the background) appear in the output.
    """
    out_svg = tmp_path / "out.svg"
    result = subprocess.run(
        [
            str(VENV_HATCHSVG),
            str(small_test_png),
            str(out_svg),
            "--preset",
            "logo",
            "--no-skip-background",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    # --no-skip-background should NOT print the "Skip BG" message
    assert "Skip BG" not in result.stdout, f"Expected NO 'Skip BG' in stdout with --no-skip-background: {result.stdout}"
    # With --no-skip-background, the background is included. The synthetic
    # test image has 2 colors (white bg + red square), and logo preset uses
    # separate_outline=True, so 2 colors * 2 (hatch + outline) = 4 groups.
    content = out_svg.read_text(encoding="utf-8")
    total_groups = content.count("<g ")
    assert total_groups == 4, (
        f"Expected 4 groups (2 colors, separate_outline=True) with --no-skip-background, got {total_groups}"
    )
