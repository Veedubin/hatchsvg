"""Palette Extractor — a Streamlit app for building marker palettes from photos.

Workflow:
  1. User takes a photo of their marker set, OR draws colors on paper
     and scans it.
  2. User uploads the image to this app.
  3. App extracts N dominant colors using colorgram.py.
  4. User can edit each color's name, reorder them, remove unwanted ones.
  5. User clicks "Generate JSON" -> writes a palette JSON file that
     hatchsvg can load via --palette-file.
  6. User clicks "Generate HTML preview" -> writes a standalone .html
     file alongside the JSON for human browsing.

Usage:
    uv run --with streamlit --with colorgram.py streamlit run scripts/palette_extractor.py

The palette JSON format matches the bundled Crayola/Jot palettes
(brand, set_name, tip_width_mm, colors: [{name, hex}, ...]).
"""

import io
import json
import re
from pathlib import Path

import streamlit as st
from PIL import Image

# colorgram.py is the extraction backend. It's not in the core deps because
# not every hatchsvg user needs it. Import inside the function so the
# rest of the app loads even if colorgram is missing.
try:
    import colorgram  # type: ignore[import-untyped]
except ImportError:
    colorgram = None  # type: ignore[assignment]

# Try to import the HTML preview generator. If hatchsvg itself isn't
# importable (e.g. running this script standalone), we fall back to
# inlining the HTML template.
try:
    from hatchsvg.scripts.palette_preview import render_palette_html  # type: ignore[attr-defined]
except ImportError:
    try:
        # Fallback: import the script directly via path manipulation
        import sys

        SCRIPTS_DIR = Path(__file__).parent
        if str(SCRIPTS_DIR) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_DIR))
        from palette_preview import render_palette_html  # type: ignore[no-redef]
    except ImportError:
        render_palette_html = None  # type: ignore[assignment]


HEX_RE = re.compile(r"^#?([0-9A-Fa-f]{6})$")


def hex_to_rgb(hex_str: str) -> tuple[int, int, int] | None:
    """Normalize '#RRGGBB' or 'RRGGBB' to (r, g, b) tuple."""
    m = HEX_RE.match(hex_str.strip())
    if not m:
        return None
    return (int(m.group(1)[0:2], 16), int(m.group(1)[2:4], 16), int(m.group(1)[4:6], 16))


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    """Format (r, g, b) as '#RRGGBB' (uppercase)."""
    return f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"


def _downscale_image(img: Image.Image, max_dim: int = 400) -> Image.Image:
    """Downscale an image to max_dim on its longest side. Returns the original
    if it's already smaller. colorgram.py is sensitive to image size; this
    makes extraction fast and consistent.
    """
    w, h = img.size
    if max(w, h) <= max_dim:
        return img
    if w >= h:
        new_w = max_dim
        new_h = int(h * (max_dim / w))
    else:
        new_h = max_dim
        new_w = int(w * (max_dim / h))
    return img.resize((new_w, new_h), Image.Resampling.LANCZOS)


@st.cache_data(show_spinner=False)
def _extract_colors_cached(image_bytes: bytes, num_colors: int) -> list[tuple[int, int, int]]:
    """Extract N dominant colors from a PNG/JPG. Cached by hash of input."""
    if colorgram is None:
        raise RuntimeError(
            "colorgram.py is not installed. Install it with: `pip install colorgram.py` or `uv add colorgram.py`"
        )
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img = _downscale_image(img)
    # colorgram.extract needs a file path or file-like, or a Pillow Image
    colors = colorgram.extract(img, num_colors)
    return [(c.rgb.r, c.rgb.g, c.rgb.b) for c in colors]


def _auto_name(rgb: tuple[int, int, int]) -> str:
    """Suggest a human-readable name from RGB. Not a full color namer —
    just rough names that users can edit."""
    r, g, b = rgb
    max_c = max(r, g, b)
    min_c = min(r, g, b)
    if max_c < 30:
        return "Black"
    if min_c > 225:
        return "White"
    if max_c - min_c < 20:
        if max_c < 100:
            return "Dark Gray"
        if max_c < 180:
            return "Gray"
        return "Light Gray"
    # Dominant channel
    if r > g and r > b:
        if g > 100 and b < 80:
            return "Orange" if g > b + 30 else "Red"
        if b > g:
            return "Pink" if r > 200 else "Magenta"
        return "Red"
    if g > r and g > b:
        if r > 100 and b < 80:
            return "Yellow" if r > 180 else "Olive"
        if b > 50:
            return "Teal" if b > 120 else "Green"
        return "Green"
    if b > r and b > g:
        if r > 100 and g < 80:
            return "Purple" if r > 150 else "Indigo"
        if g > 100:
            return "Cyan" if g > 150 else "Teal"
        return "Blue"
    return "Color"


def main() -> None:
    """Entry point for `streamlit run scripts/palette_extractor.py`."""
    st.set_page_config(
        page_title="hatchsvg Palette Builder",
        page_icon="🎨",
        layout="wide",
    )
    st.title("hatchsvg Palette Builder")
    st.caption(
        "Take a photo of your marker set (or color a sheet of paper and scan it), "
        "upload it, and generate a palette JSON for `hatchsvg --palette-file`."
    )

    if colorgram is None:
        st.error("colorgram.py is not installed. Install it with:\n\n```\npip install colorgram.py\n```")
        st.stop()

    # Sidebar: brand metadata
    with st.sidebar:
        st.header("Palette metadata")
        brand = st.text_input("Brand", value="My Brand")
        set_name = st.text_input("Set name", value="Custom Set")
        tip_width_mm = st.number_input(
            "Tip width (mm)",
            min_value=0.1,
            max_value=10.0,
            value=0.8,
            step=0.1,
            help="Physical marker tip width. Used by hatchsvg for stroke-width calculations.",
        )

    # Main: image upload
    uploaded = st.file_uploader(
        "Marker photo or color sheet (PNG, JPG, WebP)",
        type=["png", "jpg", "jpeg", "webp"],
    )
    if uploaded is None:
        st.info("Upload an image to get started.")
        st.stop()

    image_bytes = uploaded.read()
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Source")
        st.image(image_bytes, use_container_width=True)

    # Extraction controls
    with col2:
        st.subheader("Extract")
        num_colors = st.slider(
            "How many colors to extract?",
            min_value=2,
            max_value=24,
            value=8,
            help="colorgram.py will return this many dominant colors. "
            "You can remove any you don't want after extraction.",
        )
        with st.spinner("Extracting colors..."):
            try:
                extracted = _extract_colors_cached(image_bytes, num_colors)
            except Exception as e:
                st.error(f"Extraction failed: {e}")
                st.stop()

        st.success(f"Extracted {len(extracted)} colors. Edit names below:")

        # Editable color list
        edited_colors: list[tuple[str, tuple[int, int, int]]] = []
        keep_flags: list[bool] = []
        for i, rgb in enumerate(extracted):
            with st.container(border=True):
                cols = st.columns([1, 3, 1])
                with cols[0]:
                    # Color swatch as a colored block (use a 1x1 PNG with the
                    # color filled in, since streamlit doesn't have a "color"
                    # widget). Data URL approach is most reliable.
                    hex_str = rgb_to_hex(rgb)
                    swatch_html = (
                        f'<div style="width:80px;height:80px;'
                        f"background-color:{hex_str};border:1px solid #ccc;"
                        f'border-radius:4px;"></div>'
                    )
                    st.markdown(swatch_html, unsafe_allow_html=True)
                    st.caption(f"RGB({rgb[0]}, {rgb[1]}, {rgb[2]})")
                with cols[1]:
                    default_name = _auto_name(rgb)
                    # Use a unique key per color so Streamlit state works
                    name = st.text_input(
                        "Name",
                        value=default_name,
                        key=f"name_{i}",
                        label_visibility="collapsed",
                    )
                    # Allow hex editing too
                    hex_input = st.text_input(
                        "Hex",
                        value=hex_str,
                        key=f"hex_{i}",
                        label_visibility="collapsed",
                    )
                with cols[2]:
                    keep = st.checkbox(
                        "Keep",
                        value=True,
                        key=f"keep_{i}",
                    )
                # Validate hex; fall back to extracted rgb if invalid
                parsed = hex_to_rgb(hex_input) or rgb
                edited_colors.append((name, parsed))
                keep_flags.append(keep)

        # Filter to kept colors
        final_colors = [c for c, k in zip(edited_colors, keep_flags, strict=False) if k]
        if not final_colors:
            st.warning("No colors selected. Tick at least one 'Keep' box.")
            st.stop()

        st.subheader(f"Final palette ({len(final_colors)} colors)")
        # Show the final palette preview
        preview_cols = st.columns(min(len(final_colors), 8))
        for idx, (name, rgb) in enumerate(final_colors):
            with preview_cols[idx % len(preview_cols)]:
                hex_str = rgb_to_hex(rgb)
                st.markdown(
                    f'<div style="width:60px;height:60px;'
                    f"background-color:{hex_str};border:1px solid #ccc;"
                    f'border-radius:4px;margin-bottom:4px;"></div>'
                    f'<div style="font-size:0.85em;"><b>{name}</b><br/>{hex_str}</div>',
                    unsafe_allow_html=True,
                )

        # Build the JSON
        palette_obj = {
            "brand": brand,
            "set_name": set_name,
            "tip_width_mm": float(tip_width_mm),
            "colors": [{"name": n, "hex": rgb_to_hex(rgb)} for n, rgb in final_colors],
        }
        json_str = json.dumps(palette_obj, indent=2)

        st.subheader("Output")
        col_json, col_html = st.columns(2)
        with col_json:
            st.download_button(
                label="Download palette JSON",
                data=json_str,
                file_name=f"{brand.lower().replace(' ', '_')}_{set_name.lower().replace(' ', '_')}.json",
                mime="application/json",
                use_container_width=True,
            )
            st.caption("Save this file and use it with: `hatchsvg photo.jpg out.svg --palette-file <this-file>.json`")
        with col_html:
            if render_palette_html is None:
                st.warning(
                    "HTML preview generator not importable. "
                    "Make sure scripts/palette_preview.py is in the same directory."
                )
            else:
                html_str = render_palette_html(palette_obj)
                st.download_button(
                    label="Download HTML preview",
                    data=html_str,
                    file_name=f"{brand.lower().replace(' ', '_')}_{set_name.lower().replace(' ', '_')}.html",
                    mime="text/html",
                    use_container_width=True,
                )
                st.caption(
                    "Open this in any browser to see what the palette looks like. No server, no JS, just colors."
                )

        with st.expander("Raw JSON", expanded=False):
            st.code(json_str, language="json")


if __name__ == "__main__":
    main()
