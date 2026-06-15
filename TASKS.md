# png2svg Tasks

> **Strategic Context**: See [PLAN.md](./PLAN.md) for the v1.0.0 release plan
> and [REVIEW.md](./REVIEW.md) for the comprehensive audit + 30-day roadmap.

## In Progress

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

## Next Up (Week 2)

### README Rewrite & Presets

- [ ] Full README rewrite per [REVIEW.md §6](./REVIEW.md):
  - Hero GIF showing input → output
  - Gallery (3-5 example pairs)
  - Comparison table vs alternatives
  - Quickstart above the install block
- [ ] Named presets: `--preset portrait`, `--preset logo`, `--preset line-art`
- [ ] Multi-format input: accept JPG / WebP / BMP / GIF / TIFF (Pillow handles all)
- [ ] `examples/` directory with sample input/output pairs

### Module Split (refactor of `core.py`)

The 700-line `core.py` is functional but monolithic. Week 2 splits it into:

- `src/png2svg/color.py` — palette loading, color matching, naming
- `src/png2svg/path.py` — hatch path generation, components, arcs
- `src/png2svg/svg.py` — SVG group rendering, XML emission
- `src/png2svg/session.py` — save/load
- `src/png2svg/stats.py` — compute_layer_stats, display
- `src/png2svg/params.py` — RenderParams, LayerResult, StrokeStyle
- `src/png2svg/core.py` — orchestration / `process_image_to_hatched_svg`

Tests are now in place to verify the refactor is non-breaking.

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

## Quality Status (as of 2026-06-15)

| Gate | Status |
|------|--------|
| `pip install -e .` succeeds | ✅ |
| `pip install -e ".[plot]"` succeeds | ✅ |
| `pip install -e ".[dev]"` succeeds | ✅ |
| `png2svg --version` prints `png2svg 1.0.0` | ✅ |
| `python -m png2svg --version` works | ✅ |
| `pytest tests/` passes all 27 tests | ✅ |
| `ruff check src tests` clean | ✅ |
| `ruff format` clean | ✅ |
| `.github/workflows/ci.yml` valid YAML | ✅ (6 matrix jobs) |
| Git history clean (7 conventional commits) | ✅ |

## Resume Instructions

1. `git checkout v1.0.0-release`
2. `python -m venv .venv && .venv/bin/pip install -e ".[dev,plot]"`
3. `.venv/bin/pytest tests/ -v` — should show 27 passing
4. Pick a Week 2 task from "Next Up" above
5. See [PLAN.md](./PLAN.md) for the full implementation plan
