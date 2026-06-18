"""End-to-end integration test: PNG -> SVG golden file comparison.

Uses tests/fixtures/test_image.png — a small synthetic 200x200
image with 4 distinct color regions (a red square, blue circle,
yellow stripe, dark purple square on white). It's deterministic,
generated once via tests/fixtures/generate_test_image.py, and
exercises the same code paths as a real photo without needing
any third-party image assets.
"""

import os
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from hatchsvg.core import RenderParams, process_image_to_hatched_svg

REPO_ROOT = Path(__file__).parent.parent.parent
TEST_IMAGE_PATH = REPO_ROOT / "tests" / "fixtures" / "test_image.png"
GOLDEN_PATH = Path(__file__).parent.parent / "fixtures" / "test_image_golden.svg"

# Golden file generation parameters.
#
# The synthetic test image has 4 color regions + white background.
# --max-palette 4 --line-step 10 produces a small (~5KB) golden
# file while still exercising the multi-color quantization path.
#
# If the algorithm changes intentionally, regenerate the golden file with:
#
#   uv run python -c "
#   from hatchsvg.core import RenderParams, process_image_to_hatched_svg
#   from pathlib import Path
#   params = RenderParams(max_palette=4, line_step=10,
#       continuous_paths=True, arc_radius=5.0, skip_bg=True,
#       stroke_width=0.5, outline_width=1.0)
#   process_image_to_hatched_svg(
#       Path('tests/fixtures/test_image.png'),
#       Path('tests/fixtures/test_image_golden.svg'),
#       params)
#   "
#
GOLDEN_PARAMS = RenderParams(
    max_palette=4,
    line_step=10,
    continuous_paths=True,
    arc_radius=5.0,
    skip_bg=True,
    stroke_width=0.5,
    outline_width=1.0,
)

# Number of expected layers in the golden file (3 non-background layers).
EXPECTED_LAYERS = 3


@pytest.mark.skipif(not TEST_IMAGE_PATH.exists(), reason="test_image.png not found")
@pytest.mark.skipif(not GOLDEN_PATH.exists(), reason="test_image_golden.svg not found")
def test_e2e_golden():
    """Run the full pipeline and compare output to the golden file.

    This test catches regressions in the rendering pipeline. If the
    algorithm changes intentionally, regenerate the golden file by
    running the command documented above.
    """
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as tmp:
        output_path = Path(tmp.name)

    try:
        color_map, stats = process_image_to_hatched_svg(TEST_IMAGE_PATH, output_path, GOLDEN_PARAMS)

        actual = output_path.read_text(encoding="utf-8")
        expected = GOLDEN_PATH.read_text(encoding="utf-8")

        # Byte-for-byte comparison
        assert actual == expected, (
            f"SVG output differs from golden file.\n"
            f"  Expected length: {len(expected)}\n"
            f"  Actual length:   {len(actual)}\n"
            f"  If this is an intentional algorithm change, regenerate:\n"
            f'    uv run python -c "\n'
            f"    from hatchsvg.core import RenderParams, process_image_to_hatched_svg\n"
            f"    from pathlib import Path\n"
            f"    params = RenderParams(max_palette={GOLDEN_PARAMS.max_palette}, "
            f"line_step={GOLDEN_PARAMS.line_step}, continuous_paths=True, "
            f"arc_radius=5.0, skip_bg=True, stroke_width=0.5, outline_width=1.0)\n"
            f"    process_image_to_hatched_svg(\n"
            f"        Path('tests/fixtures/test_image.png'),\n"
            f"        Path('tests/fixtures/test_image_golden.svg'),\n"
            f"        params)\n"
            f'    "'
        )

        # Verify color_map and stats are non-empty
        assert len(color_map) > 0, "color_map is empty"
        assert stats["layers_generated"] > 0, "No layers generated"
        assert stats["layers_generated"] == EXPECTED_LAYERS, (
            f"Expected {EXPECTED_LAYERS} layers, got {stats['layers_generated']}"
        )

    finally:
        if output_path.exists():
            os.unlink(output_path)


@pytest.mark.skipif(not TEST_IMAGE_PATH.exists(), reason="test_image.png not found")
def test_e2e_basic_runs():
    """Smoke test: basic conversion runs without error using default params."""
    params = RenderParams(
        max_palette=4,
        line_step=10,
        continuous_paths=False,
        arc_radius=0.0,
        skip_bg=True,
    )

    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as tmp:
        output_path = Path(tmp.name)

    try:
        color_map, stats = process_image_to_hatched_svg(TEST_IMAGE_PATH, output_path, params)
        assert output_path.exists()
        assert output_path.stat().st_size > 0
        assert len(color_map) > 0
        assert stats["layers_generated"] > 0

        # Verify output is valid XML
        content = output_path.read_text(encoding="utf-8")
        root = ET.fromstring(content)
        assert root.tag.endswith("svg")

        # Verify output contains <path> elements
        ns = {"svg": "http://www.w3.org/2000/svg"}
        paths = root.findall(".//svg:path", ns)
        assert len(paths) > 0, "No <path> elements in output SVG"

    finally:
        if output_path.exists():
            os.unlink(output_path)
