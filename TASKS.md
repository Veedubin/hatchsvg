# png2svg Tasks

> **Strategic Context**: See [PLAN.md](./PLAN.md) for the v1.0.0 release plan
> and [REVIEW.md](./REVIEW.md) for the comprehensive audit + 30-day roadmap.

## In Progress

### Week 2 Polish ✅ COMPLETE (2026-06-15)

All Week 2 deliverables shipped on branch `v1.0.0-release` (continuing the same
branch from Week 1):

- [x] **Multi-format input** — CLI now accepts `.png`, `.jpg`, `.jpeg`,
      `.webp`, `.bmp`, `.gif`, `.tiff`, `.tif` with friendly error on
      unsupported formats
- [x] **Named presets** — `--preset portrait|logo|line-art|photo|sketch|fast`;
      explicit CLI flags override preset values (8 new tests in
      `test_preset_config.py` + 13 in `test_presets.py`)
- [x] **`png2svg.presets` module** — typed `PRESETS` dict with 6 hand-tuned
      presets, `list_presets()`, `get_preset()`, `apply_preset()` (100%
      covered)
- [x] **`examples/` directory** — `scene.png` (procedural 200×200 input) + 4
      output SVGs (fast/portrait/logo/sketch) + `examples/README.md`
- [x] **README rewrite** — quickstart above the install block, comparison
      table vs potrace/vtracer/Inkscape, full CLI flag table, 5+ Cookbook
      recipes, updated project structure
- [x] **21 new tests** — 13 in `test_presets.py`, 8 in
      `test_preset_config.py`, 8 in `tests/integration/test_cli.py`
- [x] **60 total tests** (up from 27); coverage 49% → 55%
- [x] All quality gates pass: `ruff check`, `ruff format`, `pytest -q`

### Week 1 Hardening ✅ COMPLETE (2026-06-15)

All Week 1 deliverables shipped on branch `v1.0.0-release`:

- [x] MIT `LICENSE` file
- [x] `pyproject.toml` with hatchling build, Python 3.11+, optional `[plot]` and `[dev]` extras
- [x] `src/png2svg/` package layout (`__init__.py`, `core.py`, `cli.py`, `__main__.py`)
- [x] `--version` flag (`png2svg --version` → `png2svg 1.0.0`)
- [x] `python -m png2svg` entry point
- [x] Friendly error wrapper (translates `SystemExit`/`ValueError`/`FileNotFoundError` to actionable advice)
- [x] `tests/` directory: 25 unit tests + 2 integration tests (golden file comparison)
- [x] `pytest` config with coverage
- [x] `ruff` config (lint + format)
- [x] `.github/workflows/ci.yml` matrix: Linux + macOS × Python 3.11/3.12/3.13
- [x] `CHANGELOG.md` (v1.0.0 entry)
- [x] `.gitignore` (Python + png2svg-specific)
- [x] Updated `README.md` with badges, pip install, project structure, development section
- [x] Legacy `png2svg.py` moved to `scripts/png2svg_legacy.py` (out of import path)
- [x] 7 clean conventional commits on `v1.0.0-release` branch

### Cricut Hardware Testing (still open from prior session)

- [ ] Test serpentine path generation on actual Cricut hardware
- [ ] Verify ringing artifact is eliminated with `--continuous-paths`
- [ ] Validate arc smoothing with `--arc-radius` produces smooth U-turns
- [ ] Confirm pen lift reduction improves drawing speed

## Next Up (Week 3)

### Module Split (refactor of `core.py`)

The 700-line `core.py` is functional but monolithic. Week 3 splits it into:

- `src/png2svg/color.py` — palette loading, color matching, naming
- `src/png2svg/path.py` — hatch path generation, components, arcs
- `src/png2svg/svg.py` — SVG group rendering, XML emission
- `src/png2svg/session.py` — save/load
- `src/png2svg/stats.py` — compute_layer_stats, display
- `src/png2svg/params.py` — RenderParams, LayerResult, StrokeStyle
- `src/png2svg/core.py` — orchestration / `process_image_to_hatched_svg`

Tests are now in place to verify the refactor is non-breaking.

### README Polish (Week 2 leftover)

- [ ] Add a hero GIF showing input → output (requires a screen recorder or
      external tool)
- [ ] Add 3-5 real photo examples (vs the procedural scene)
- [ ] Add a "When NOT to use png2svg" section

## Backlog

### Week 3: Web UI + Color Editor

- [ ] Gradio web UI (`png2svg serve --port 7860`)
- [ ] Self-contained HTML preview (`--preview-html out.html`)
- [ ] Interactive color override (TUI with `questionary` or web component)

### Week 4: PyPI Publish + Launch

- [ ] `python -m build` to produce sdist + wheel
- [ ] `twine upload dist/*` to PyPI
- [ ] Create GitHub release `v1.0.0` with hero GIF and `examples/` outputs
- [ ] Blog post + dev.to / Reddit (r/cricut, r/python, r/PlotterArt) / HN Show HN
- [ ] Submit to awesome-python list
- [ ] Add 5 "good first issue" labels to GitHub issues
- [ ] Enable GitHub Discussions for show-and-tell

### Long-Term Feature Backlog (from REVIEW.md)

- [ ] Lab / CIEDE2000 color matching (vs current HSV Euclidean)
- [ ] Alternative fill modes: stippling, cross-hatch, contour-parallel, halftone
- [ ] Per-color hatch tuning (`--light-hatch 6 --dark-hatch 2`)
- [ ] `lxml`/`ElementTree` for safe SVG emission
- [ ] Plugin entry-points for community hatch styles
- [ ] Docker image
- [ ] Inkscape plugin

## Recently Completed ✓

- [x] Audit & review (REVIEW.md) — 2026-06-15
- [x] v1.0.0 implementation plan (PLAN.md) — 2026-06-15
- [x] Week 1 hardening (license, packaging, tests, CI) — 2026-06-15
- [x] All Boomerang agent work from previous sessions (commits 9beabd5, 6fab09e, 4f4e6b9)
- [x] Add Rich progress bars — commit 4f4e6b9
- [x] Add processing statistics with `--stats` flag
- [x] Quality gates for all changes (ruff, mypy-free, pytest)

## Quality Status (as of 2026-06-15, end of Week 2)

| Gate | Status |
|------|--------|
| `pip install -e .` succeeds | ✅ |
| `pip install -e ".[plot]"` succeeds | ✅ |
| `pip install -e ".[dev]"` succeeds | ✅ |
| `png2svg --version` prints `png2svg 1.0.0` | ✅ |
| `python -m png2svg --version` works | ✅ |
| `pytest tests/` passes all 60 tests (was 27 in Week 1) | ✅ |
| `ruff check src tests` clean | ✅ |
| `ruff format` clean | ✅ |
| `.github/workflows/ci.yml` valid YAML | ✅ (6 matrix jobs) |
| Git history clean (conventional commits) | ✅ |
| Coverage | 55% (up from 49% in Week 1) |
| `png2svg.presets` coverage | 100% |
| Multi-format input (JPG/WebP/BMP/GIF/TIFF) | ✅ tested |
| Named presets (6) | ✅ tested |
| `--version` flag | ✅ |
| `python -m png2svg` | ✅ |

## Resume Instructions

1. `git checkout v1.0.0-release`
2. `python -m venv .venv && .venv/bin/pip install -e ".[dev,plot]"`
3. `.venv/bin/pytest tests/ -v` — should show 27 passing
4. Pick a Week 2 task from "Next Up" above
5. See [PLAN.md](./PLAN.md) for the full implementation plan
