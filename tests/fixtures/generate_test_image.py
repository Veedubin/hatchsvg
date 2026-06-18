"""Generate the synthetic test image used by the e2e golden-file test.

This produces tests/fixtures/test_image.png — a 200x200 image with
4 distinct color regions on a white background. It's deterministic
(no randomness, no system state), so re-running this script always
produces a byte-identical PNG.

The image is small (~5KB golden SVG output) but exercises the same
quantization/hatching code paths as a real photo. We use it instead
of a real photograph to avoid copyright/licensing concerns and to
keep the test image under 1KB.

Run with:
    uv run python tests/fixtures/generate_test_image.py
"""

from pathlib import Path

import numpy as np
from PIL import Image


def main() -> int:
    output = Path(__file__).parent / "test_image.png"
    img = Image.new("RGBA", (200, 200), (255, 255, 255, 255))  # white background
    arr = np.array(img)

    # A blue circle-ish region (top-left)
    for y in range(30, 90):
        for x in range(30, 90):
            if (x - 60) ** 2 + (y - 60) ** 2 < 25**2:
                arr[y, x] = (30, 80, 180, 255)

    # A red rectangle (bottom-right)
    arr[120:170, 110:170] = (200, 30, 30, 255)

    # A yellow stripe (top-right)
    arr[20:60, 130:190] = (240, 200, 30, 255)

    # A dark blue/purple square (bottom-left)
    arr[140:180, 20:60] = (60, 50, 100, 255)

    Image.fromarray(arr).save(output)
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
