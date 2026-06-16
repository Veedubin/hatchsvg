# png2svg GUI — Architecture & Design Doc

> **Status:** Design, awaiting review before implementation
> **Generated:** 2026-06-15
> **Scope:** Week 3+ of the v1.0.0 release plan (deferred to dedicated effort)

---

## A. Executive Summary

A web-based GUI for png2svg that gives crafters a 4-stage progressive workflow
instead of the current single-shot CLI render. The user uploads an image, sees
a live color-quantization preview, picks a marker palette with click-to-remap
swatches, previews the hatched wireframe, then generates the final
plotter-ready SVG. Each stage is fast (sub-second to ~5s) so the user gets
continuous feedback instead of a 35-second black box.

**Stack:** HTML/CSS/JS frontend + FastAPI backend. Pure local; no AI/ML
dependencies; no network calls. Runs as a single Python process serving a
local web app — `pip install png2svg[gui]` then `png2svg serve`.

**Differentiator vs competitors (vpype, vtracer, hatched, plottter):**

| Competitor | What they do | What we do that's different |
|---|---|---|
| **vtracer webapp** | 1-stage "drop + tune sliders + download" | 4-stage progressive disclosure; you see the quantized color map *before* the slow hatch path runs |
| **hatched** (vpype plugin) | Grayscale threshold hatching, no color | Cricut-native multi-color with **physical marker palette matching** and click-to-remap |
| **plottter** | Full desktop app, 39 generators, AI masks, dithering | Cricut-first, **simpler UX**, **no API keys**, no Replicate, no installation wizard; built on top of an already-shipped, tested CLI; MIT-licensed |
| **saxi** | AGPL, AxiDraw driver only | Different scope (driver, not image-to-vector); we are MIT |

The win is **speed of feedback**, **physical-marker realism**, and **no
installation bloat**. Power users can keep using the CLI; the GUI is for
crafters who don't want to remember flags.

---

## B. 4-Stage User Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Stage 1: LOAD                                                           │
│  ┌──────────────┐    ┌─────────────────────────────────┐                │
│  │ Drop image   │ -> │ Preview thumbnail (instant)     │                │
│  │ or file pick │    │ "photo.png (1402×1903, 1.2 MB)" │                │
│  └──────────────┘    └─────────────────────────────────┘                │
│                                          │                              │
│                                          ▼                              │
├─────────────────────────────────────────────────────────────────────────┤
│ Stage 2: PALETTE + LIVE QUANTIZE PREVIEW                                │
│  ┌────────────────┐   ┌──────────────────┐    ┌────────────────────┐   │
│  │ Original       │   │ Quantized        │    │ Palette picker     │   │
│  │ preview        │   │ (live, <300ms)   │    │ [Crayola ▼]        │   │
│  │                │   │                  │    │ ──────────         │   │
│  │  [photo]       │   │  [photo]         │    │ ▢ red  ▢ blue      │   │
│  │                │   │                  │    │ ▢ grn  ▢ ylw      │   │
│  │                │   │                  │    │ ▢ ...  ▢ ...      │   │
│  └────────────────┘   └──────────────────┘    └────────────────────┘   │
│       ↑ click swatch to remap: original RGB → swap with palette color   │
│                                          │                              │
│                                          ▼                              │
├─────────────────────────────────────────────────────────────────────────┤
│ Stage 3: WIREFRAME PREVIEW (after "Render wireframe" click, ~3-5s)     │
│  ┌─────────────────────────────────────┐                                │
│  │ Hatched overlay on quantized image │   Preset: [portrait ▼]          │
│  │ (low-opacity hatch lines visible)  │   Line step: [────●──] 3        │
│  │                                     │   Arc radius: [──●────] 5      │
│  └─────────────────────────────────────┘   [ Re-quantize ] [ Next → ]   │
│                                          │                              │
│                                          ▼                              │
├─────────────────────────────────────────────────────────────────────────┤
│ Stage 4: GENERATE PATHS (after "Generate SVG" click, ~30-60s)          │
│  ┌─────────────────────────────────────┐                                │
│  │ Final SVG preview (rendered as PNG │   Colors detected: 5            │
│  │ for the GUI; SVG is downloadable)  │   Pen lifts: 1240 → 380         │
│  │                                     │   Plot time: ~12 min            │
│  │                                     │   ─────────────────────         │
│  │                                     │   [ Download .svg ]             │
│  │                                     │   [ Download .session.json ]    │
│  └─────────────────────────────────────┘                                │
└─────────────────────────────────────────────────────────────────────────┘
```

**Why this matters:** Today, `png2svg Bluey.png out.svg` takes ~35s and the
user has no idea if it will look good until the end. The 4-stage flow turns
this into:

- **Stage 1**: instant (<100ms) — just the image preview
- **Stage 2**: ~300ms per palette change — "is this the right number of colors?"
- **Stage 3**: ~3-5s — "is the hatch density right?"
- **Stage 4**: ~30-60s — the only stage that can't be cheap; user has already
  validated everything by now, so the wait feels earned

**Render time savings** (per the user's ask): the "spread out the total render
time" is real — Stage 1 + 2 + 3 give instant feedback; the slow Stage 4 only
runs once the user is confident in the choices.

---

## C. Architecture

### Stack

| Layer | Choice | Rationale |
|---|---|---|
| **Frontend** | Vanilla HTML + CSS + JS, no build step | Single-file `index.html` for distribution; no npm; no React; no Vue. ~500 lines max. |
| **Backend** | FastAPI (Python) | Already in the Python ecosystem; async-friendly for streaming progress; typed; auto OpenAPI docs |
| **Server** | `uvicorn` (single-worker is fine for one user) | Standard FastAPI runner |
| **Image I/O** | Existing `core.py` (PIL + numpy) | No new dependencies |
| **Live quantize rendering** | numpy → base64 PNG (returned to browser) | No canvas dependencies on Python side; browser just sets `<img src="data:image/png;base64,...">` |
| **Wireframe rendering** | Render hatch lines as colored SVG → render via headless tool? **No** — just emit SVG and let the browser render via `<svg>` element | Browser SVG is fine; saves us a Pillow→SVG→PNG round-trip |
| **Final SVG** | Generated by `core.process_image_to_hatched_svg`, served as `text/svg` | Trivial download |

### Why split (HTML+JS frontend, FastAPI backend) instead of Gradio?

- **No opinionated layout** — we get pixel-perfect control over the 2-column
  compare (original | quantized) and the click-to-remap swatch grid
- **No Gradio 5.x deprecation churn** — we own the JS
- **Smaller dep surface** — no Gradio, no Gradio themes, no Gradio queue
- **Better for the long-term product** — if this evolves, we already have
  the right architecture

### Project Layout (new files)

```
png2svg/
├── src/png2svg/
│   ├── __init__.py
│   ├── __main__.py
│   ├── core.py                  # existing algorithm
│   ├── cli.py                   # existing CLI; gains `serve` subcommand
│   ├── presets.py               # existing
│   ├── gui/                     # NEW: web app
│   │   ├── __init__.py
│   │   ├── app.py               # FastAPI app factory
│   │   ├── state.py             # in-memory session state (per upload)
│   │   ├── render.py            # thin wrappers around core.py for GUI use
│   │   └── static/
│   │       ├── index.html       # single-file UI
│   │       ├── style.css
│   │       └── app.js           # frontend logic
├── tests/
│   ├── unit/
│   │   ├── test_gui_render.py   # NEW: test the render wrappers
│   └── integration/
│       └── test_gui_api.py      # NEW: FastAPI TestClient
```

### New dependencies

- `fastapi` (new)
- `uvicorn[standard]` (new, includes `httptools` and `uvloop` for performance)
- Both go in a new `[gui]` extra in `pyproject.toml`

```toml
[project.optional-dependencies]
plot = ["rich>=13.0", "scipy>=1.7"]
dev  = ["pytest>=7.0", "pytest-cov>=4.0", "ruff>=0.1"]
gui  = ["fastapi>=0.110", "uvicorn[standard]>=0.27"]
```

### CLI: new `serve` subcommand

```python
# src/png2svg/cli.py
sub = p.add_subparsers(dest="command")
serve_p = sub.add_parser("serve", help="Launch the local web UI")
serve_p.add_argument("--host", default="127.0.0.1", help="Bind address")
serve_p.add_argument("--port", default=7860, type=int, help="Bind port")
```

After install: `png2svg serve` → opens browser to `http://127.0.0.1:7860`.

---

## D. API Contract

All endpoints are JSON unless noted. Errors return `{"error": str, "hint": str}`.

### `POST /api/upload` — Stage 1

Upload an image, return a session ID + thumbnail.

- **Request**: `multipart/form-data` with `file` field
- **Response 200**:
  ```json
  {
    "session_id": "s_abc123",
    "filename": "photo.png",
    "width": 1402,
    "height": 1903,
    "mode": "RGBA",
    "size_bytes": 1245678,
    "thumbnail_data_url": "data:image/png;base64,..."
  }
  ```
- **Errors**: 415 (unsupported format), 413 (file too large, 50MB cap)

The session ID is opaque and identifies an in-memory state object holding the
uploaded PIL image, palette overrides, and progress flags. Sessions are
TTL'd to 30 minutes (configurable). No disk persistence in v1.

### `GET /api/session/{sid}/preview` — Stage 2 (image preview)

- **Response**: same as upload response (for refresh)

### `POST /api/session/{sid}/quantize` — Stage 2 (live quantize)

Quantize the image to the chosen palette. Returns a side-by-side preview as a
data URL plus the palette mapping.

- **Request body**:
  ```json
  {
    "palette_name": "crayola_10ct",     // built-in, OR
    "palette_json": { ... },            // user-uploaded custom palette
    "max_palette": 8,                   // optional override
    "alpha_threshold": 10,
    "skip_bg": true,
    "white_medium": true,
    "paper_white_soft": 20
  }
  ```
- **Response 200**:
  ```json
  {
    "quantized_data_url": "data:image/png;base64,...",
    "colors": [
      {
        "id": 0,
        "rgb": [255, 255, 255],
        "hex": "#FFFFFF",
        "name": "white",
        "pixels": 228593,
        "marker_name": null,            // null if no palette applied
        "marker_hex": null
      },
      ...
    ],
    "color_count": 5
  }
  ```
- **Latency target**: <300ms for a 1500×2000 image (one quantization pass)

### `POST /api/session/{sid}/remap` — Stage 2 (click swatch to remap)

User clicked the "white" color in the quantized preview and chose the "yellow"
marker from the palette. We swap the mapping for that color ID.

- **Request body**:
  ```json
  {
    "color_id": 0,                       // id from /quantize response
    "marker_index": 4,                  // index into the palette colors array
    "marker_palette": "crayola_10ct"     // name OR inline palette_json
  }
  ```
- **Response 200**: same shape as `/quantize` (re-rendered with new mapping)

### `POST /api/session/{sid}/wireframe` — Stage 3

Generate the hatched wireframe overlay. Fast (~3-5s). Returns the SVG
path data for the hatches + the quantized base image, so the browser can
render them layered.

- **Request body**:
  ```json
  {
    "preset": "portrait",                // or null
    "line_step": 3,
    "continuous_paths": true,
    "arc_radius": 5.0,
    "white_medium": true,
    "separate_outline": false
  }
  ```
- **Response 200**:
  ```json
  {
    "base_data_url": "data:image/png;base64,...",  // quantized image
    "overlay_svg": "<g><path d=\"M147 958 H148 A 4 4 ...\"/></g>",
    "color_count": 5,
    "total_segments": 1247,
    "render_ms": 3214
  }
  ```
- **Latency target**: <5s for typical 1500×2000 image

### `POST /api/session/{sid}/generate` — Stage 4 (the slow one)

Generate the final SVG. This is the only stage that reuses
`core.process_image_to_hatched_svg`.

- **Request body**: same as wireframe + the final palette overrides
- **Response 200**:
  ```json
  {
    "svg_content": "<?xml version=\"1.0\"...<path d=\"...\"/>...</svg>",
    "stats": {
      "layers": 5,
      "total_segments": 1247,
      "pen_lifts_optimized": 380,
      "pen_lifts_legacy": 1240,
      "reduction_pct": 69.4,
      "estimated_plot_min": 12.3
    },
    "session_json": { ... }   // for reproducibility
  }
  ```
- **Latency target**: 30-60s; we should add a `/api/session/{sid}/progress`
  endpoint with SSE for a real progress bar (Phase 2)

### `GET /api/palettes` — list bundled palettes

- **Response 200**:
  ```json
  {
    "palettes": [
      {
        "name": "crayola_10ct_fine_line_classic",
        "brand": "Crayola",
        "set": "Fine Line Classic",
        "color_count": 10,
        "tip_width_mm": 0.5
      },
      {
        "name": "jot_20ct_washable_fineline",
        "brand": "Jot",
        "set": "Washable Fineliner",
        "color_count": 20,
        "tip_width_mm": 0.4
      }
    ]
  }
  ```

### `POST /api/palettes/upload` — user-supplied palette

- **Request**: `multipart/form-data` with `file` field (JSON palette)
- **Response 200**:
  ```json
  {
    "name": "user_palette_2026_06_15_142233",
    "brand": "Custom",
    "color_count": 12
  }
  ```

### Error handling

All endpoints return:
```json
{ "error": "human-readable message", "hint": "actionable advice" }
```

With appropriate HTTP status code. The frontend shows these in a toast
notification (top-right corner) that auto-dismisses after 4s.

---

## E. Frontend Layout

Single-file `index.html` (with linked `style.css` and `app.js`):

```
┌────────────────────────────────────────────────────────────────────────┐
│ png2svg                                  [upload] [help] [github]     │  ← header
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  Stage 1: Load                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │   Drop image here, or [Choose file]                              │  │
│  │   (drag-drop zone when no image loaded)                          │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  Stage 2: Palette                                                      │
│  ┌─────────────┬─────────────────┬────────────────────────────────┐   │
│  │  Original   │  Quantized      │  Palette                        │   │
│  │  [img]      │  [img, live]    │  Crayola 10ct ▼                 │   │
│  │             │                 │  ┌────┬────┬────┬────┐          │   │
│  │             │                 │  │ ▣  │ ▣  │ ▣  │ ▣  │ markers  │   │
│  │             │                 │  └────┴────┴────┴────┘          │   │
│  │             │                 │  Detected colors:               │   │
│  │             │                 │  ┌────┬────┬────┐                │   │
│  │             │                 │  │ ▣R │ ▣G │ ▣B │ click→remap   │   │
│  │             │                 │  └────┴────┴────┘                │   │
│  └─────────────┴─────────────────┴────────────────────────────────┘   │
│                                                                        │
│  Stage 3: Wireframe  [Render wireframe →]                              │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │  [overlay: quantized image + hatch lines preview]                │ │
│  │  Preset: [portrait ▼]    Line step: [────●──] 3                  │ │
│  │  Continuous: [x]    Arc radius: [──●────] 5                      │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│  Stage 4: Generate  [Generate SVG paths →]                             │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │  [final SVG preview, 5 layers, 380 pen lifts saved, ~12 min]     │ │
│  │  [Download SVG]  [Download session.json]                         │ │
│  └──────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────┘
```

**Frontend implementation notes:**

- Plain `<div>` + CSS grid. No framework.
- State held in a single `state` object in `app.js`; updates trigger
  `renderUI(state)` which idempotently reflects state to DOM
- All API calls use `fetch()` with `async/await`
- The 2-column compare in Stage 2 uses `display: flex` with equal widths
- Click-to-remap: clicking a detected color swatch opens a small popover
  with the palette marker grid; user clicks a marker → POST `/remap`
- No external icons; pure CSS shapes for arrows/spinners

---

## F. Implementation Plan (3 phases)

### Phase 1: Skeleton + Stage 1 (1-2 hours)
- Add `fastapi` + `uvicorn` to `[gui]` extra in `pyproject.toml`
- Add `serve` subcommand to `cli.py`
- Create `gui/app.py` with FastAPI app factory + 4 stub endpoints
- Create `gui/static/index.html`, `style.css`, `app.js` with single-page shell
- Wire up Stage 1: drag/drop, file picker, `/api/upload` → display thumbnail
- Tests: `tests/integration/test_gui_api.py` with TestClient

### Phase 2: Stage 2 (live quantize + remap) (1-2 hours)
- `gui/render.py` wraps `core.build_color_index_map` + `load_marker_palette`
- Emit a quantized PNG as a base64 data URL using PIL
- Frontend: 2-column compare + palette dropdown + detected-color chips
- Click-to-remap popover + POST `/remap`
- Tests: cover the render wrapper + remap behavior

### Phase 3: Stages 3 + 4 (2-3 hours)
- Stage 3 (`/wireframe`): call `core._create_layer_groups`, emit hatch SVG
  fragments per color, return base + overlay for the browser to composite
- Stage 4 (`/generate`): call `core.process_image_to_hatched_svg`, return
  full SVG + stats
- Add `GET /api/palettes` and `POST /api/palettes/upload`
- Frontend: progress bar (CSS animation while Stage 4 is in flight; eventually
  upgrade to SSE for real progress)
- Tests: end-to-end via TestClient, plus UI smoke test

### Total estimated scope: 4-7 hours of focused work, plus this design doc

---

## G. Out of Scope (v1.0)

- Real-time SSE progress for Stage 4 (CSS spinner is fine for v1)
- Disk persistence of sessions (TTL'd in-memory is fine)
- User accounts, gallery, history
- WebSocket-based live preview as you drag sliders
- Mask painting (plottter has this; we don't, in v1)
- AI background removal (plottter has this; we don't, in v1)
- Dithering (plottter has Floyd-Steinberg + Atkinson; we just hard-quantize)
- Lab-color palette matching (plottter has this; we use HSV Euclidean — could
  add in v1.1 as a "Lab" preset)
- Multi-user support (single-user local app)
- Mobile-responsive layout (desktop-only for v1)

---

## H. Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| 1 | **Stage 4 takes 30-60s with no progress feedback** — user thinks the app is hung | High | High | CSS spinner + clear "Stage 4/4: Generating tool paths..." text. v1.1: SSE progress. |
| 2 | **Base64 data URLs for 1500×2000 images are large** — could be 1-2MB JSON response | Medium | Medium | Use JPEG for the quantized preview (smaller, lossy is fine for preview). Keep PNG for the final SVG. |
| 3 | **`build_color_index_map` is not designed for real-time use** — may have numpy overhead per call | Medium | Medium | Pre-allocate, use existing function; measure; if slow, add a fast path that skips alpha threshold / paper-white logic for preview |
| 4 | **Remap complexity** — when user remaps a color, the layer mask for that color changes; the wireframe is invalidated | High | High | When remap happens, mark wireframe + final as "stale"; show "Re-render wireframe" hint |
| 5 | **Browser-only-no-network rule** — uvicorn on 127.0.0.1 is fine, but docs must make this clear | Low | Low | README: "the app runs entirely on your computer. No image leaves your device." |
| 6 | **Python 3.11+ already shipped; FastAPI requires 3.8+; no conflict** | — | — | — |
| 7 | **v1.0.0 CLI users see a regression if we break the existing import path** | Low | High | The GUI is a NEW module (`png2svg.gui.*`); the CLI is unchanged unless the user runs `png2svg serve`. No regression. |

---

## I. What I'll deliver in the first coding pass (after this doc is approved)

Per your answer: "Design doc first, then code."

If this doc is approved, I'll:
1. Add the `[gui]` extra to `pyproject.toml`
2. Add the `serve` subcommand to `cli.py`
3. Create `src/png2svg/gui/{__init__.py, app.py, state.py, render.py}`
4. Create `src/png2svg/gui/static/{index.html, style.css, app.js}`
5. Implement Stage 1 (upload + preview) end-to-end, with tests
6. Implement Stage 2 (live quantize + click-to-remap) end-to-end, with tests
7. Commit + push the design doc + skeleton

**NOT in this first pass** (to keep it shippable and reviewable):
- Stages 3 and 4 — those need a separate, larger commit because the
  wireframe rendering requires us to expose `_create_layer_groups`
  or build a new "wireframe-only" mode in `core.py`
- Progress bar polish
- Mobile responsiveness

I'd estimate ~2-3 hours for the doc-approved Phase 1+2 deliverable.

---

## J. Open questions for the user

1. **Distribution**: should `png2svg[gui]` install via pip as a normal
   optional extra, or should we ship a separate `png2svg-desktop`
   package with a bundled binary? Pip extra is simpler; desktop bundle
   is friendlier for non-Python users. My recommendation: pip extra
   for v1; desktop bundle (PyInstaller) for v1.1.

2. **Browser support**: should the GUI work on Safari/Firefox/Edge, or
   Chromium-only is fine? Chromium-only is much simpler (we can use
   newer CSS features). My recommendation: Chromium-only for v1
   (Chrome/Edge/Brave), since most crafters use one of those.

3. **Single-user or multi-user from day 1?** The current design is
   single-user (in-memory state, no auth). If you want to host this
   for multiple users, we'd need to add session storage to disk
   or a real DB. My recommendation: single-user for v1.

4. **Default port**: 7860 (Gradio's default) is the de-facto standard
   for ML/AI tools. Or 8000 (FastAPI's default). My recommendation:
   7860 because crafters coming from the pen-plotter community are
   already familiar with that port.

---

## K. References

- **vtracer webapp** (MIT): https://www.visioncortex.org/vtracer/ — UI
  reference for slider groups + drag/drop
- **vpype + hatched** (MIT): https://github.com/plottertools/hatched —
  technical reference for the hatch algorithm (we use a similar approach
  but with palette matching instead of thresholds)
- **plottter** (MIT): https://github.com/pywkt/plottter — feature reference
  for the desktop-app pen-plotter workflow; we deliberately simplify
- **FastAPI docs**: https://fastapi.tiangolo.com/ — backend framework
