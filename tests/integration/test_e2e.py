"""End-to-end integration test: PNG -> SVG golden file comparison."""

import os
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from png2svg.core import RenderParams, process_image_to_hatched_svg

REPO_ROOT = Path(__file__).parent.parent.parent
BLUEY_PATH = REPO_ROOT / "Bluey.png"
GOLDEN_PATH = Path(__file__).parent.parent / "fixtures" / "bluey_golden.svg"

# Golden file generation parameters.
#
# NOTE: The original spec called for --max-palette 12 --line-step 4, but
# that produced a 1.5 MB SVG (exceeding the 500 KB size limit). To keep the
# golden file under 500 KB, --max-palette 4 --line-step 10 was used instead.
#
# The outline_width differs from the RenderParams default (0.8) because the
# CLI computes outline_width = max(1.0, stroke_width * 1.6) = 1.0 when no
# palette file is specified. We match the CLI behavior exactly.
#
# If the algorithm changes intentionally, regenerate the golden file with:
#
#   .venv/bin/png2svg Bluey.png tests/fixtures/bluey_golden.svg \
#       --continuous-paths --arc-radius 5 \
#       --max-palette 4 --line-step 10
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


@pytest.mark.skipif(not BLUEY_PATH.exists(), reason="Bluey.png not found")
@pytest.mark.skipif(not GOLDEN_PATH.exists(), reason="bluey_golden.svg not found")
def test_e2e_bluey_golden():
    """Run the full pipeline and compare output to the golden file.

    This test catches regressions in the rendering pipeline. If the
    algorithm changes intentionally, regenerate the golden file by
    running the command documented above.
    """
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as tmp:
        output_path = Path(tmp.name)

    try:
        color_map, stats = process_image_to_hatched_svg(BLUEY_PATH, output_path, GOLDEN_PARAMS)

        actual = output_path.read_text(encoding="utf-8")
        expected = GOLDEN_PATH.read_text(encoding="utf-8")

        # Byte-for-byte comparison
        assert actual == expected, (
            f"SVG output differs from golden file.\n"
            f"  Expected length: {len(expected)}\n"
            f"  Actual length:   {len(actual)}\n"
            f"  If this is an intentional algorithm change, regenerate:\n"
            f"    .venv/bin/png2svg Bluey.png {GOLDEN_PATH} "
            f"--continuous-paths --arc-radius 5 "
            f"--max-palette {GOLDEN_PARAMS.max_palette} "
            f"--line-step {GOLDEN_PARAMS.line_step}"
        )

        # Verify output is valid XML
        root = ET.fromstring(actual)
        assert root.tag.endswith("svg"), f"Root element is not <svg>: {root.tag}"

        # Verify output contains <path> elements
        ns = {"svg": "http://www.w3.org/2000/svg"}
        paths = root.findall(".//svg:path", ns)
        assert len(paths) > 0, "No <path> elements in output SVG"

        # Verify color_map and stats are non-empty
        assert len(color_map) > 0, "color_map is empty"
        assert stats["layers_generated"] > 0, "No layers generated"
        assert stats["layers_generated"] == EXPECTED_LAYERS, (
            f"Expected {EXPECTED_LAYERS} layers, got {stats['layers_generated']}"
        )

    finally:
        if output_path.exists():
            os.unlink(output_path)


@pytest.mark.skipif(not BLUEY_PATH.exists(), reason="Bluey.png not found")
def test_e2e_bluey_basic_runs():
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
        color_map, stats = process_image_to_hatched_svg(BLUEY_PATH, output_path, params)
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
