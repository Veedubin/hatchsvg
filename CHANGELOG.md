# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-06-17

### ⚠️ BREAKING CHANGE: rename `png2svg` → `hatchsvg`

The package has been renamed from `png2svg` to `hatchsvg` to match
the GitHub repository name (`github.com/Veedubin/hatchsvg`) and to
better describe the algorithm. **The repo was renamed to `hatchsvg`
in v1.1.1; this release brings the package in line.**

### Migration guide

| Old (v1.2.0) | New (v2.0.0) |
|--------------|--------------|
| `pip install png2svg` | `pip install hatchsvg` |
| `import png2svg` | `import hatchsvg` |
| `png2svg photo.jpg out.svg` | `hatchsvg photo.jpg out.svg` |
| `python -m png2svg` | `python -m hatchsvg` |
| `from png2svg.core import ...` | `from hatchsvg.core import ...` |
| `from png2svg.presets import ...` | `from hatchsvg.presets import ...` |
| `src/png2svg/` directory | `src/hatchsvg/` directory |
| Internal attribute `_png2svg_parser` | `_hatchsvg_parser` |

### Why a major bump (v2.0.0)?

Per [SemVer](https://semver.org/), any backward-incompatible change
to the public API requires a major version bump. The rename touches:

- **PyPI package name** (`pip install` no longer finds `png2svg`)
- **Import name** (`import png2svg` raises `ModuleNotFoundError`)
- **CLI command** (`png2svg` command no longer exists)
- **Module path** (`python -m png2svg` fails)

The CLI flags, file output, session JSON schema, palette JSON
schema, and Python API function signatures are unchanged.

### What did NOT change

- 114 tests still pass
- Golden file is byte-identical
- All v1.2.0 CLI flags work the same
- Output SVG format unchanged

### Migration shim

A compatibility shim is **not** shipped in v2.0.0. If you need to
keep `png2svg` working for existing scripts, add this to your
project's `requirements.txt`:

```
hatchsvg>=2.0.0
```

Then in your code, change `import png2svg` to `import hatchsvg as png2svg`.
A standalone `png2svg` PyPI shim package that depends on `hatchsvg`
may be added in v2.1.0 if user demand warrants it.

## [1.2.0] - 2026-06-17

### Added
- **`--preview`** — opens the output SVG in the default system viewer after render (uses stdlib `webbrowser`)
- **`--split-layers`** — writes one SVG file per color layer alongside the main output (`<stem>_<NN>_<color>.svg`)
- **`--optimize-travel`** — reorders layers using greedy nearest-neighbor to minimize pen-up travel distance
- **`--hatch-angles`** — comma-separated hatch rotation per layer in degrees (e.g. `--hatch-angles=0,45,90,135`)
- **`--help` examples** — 5 inline examples below the presets block in `hatchsvg --help` output
- **ViewBox normalization** — viewBox values are now always integer strings (no floats) for Cricut Design Space compatibility
- **`render_single_layer_svg()`** — new public function in `core.py` for per-layer SVG rendering (used by `--split-layers`)
- **`optimize_layer_order()`** — new public function in `core.py` for nearest-neighbor layer reordering (used by `--optimize-travel`)
- **Test count** — 88 → 98 (new tests for all 6 features)

### Changed
- `RenderParams` gained two additive fields: `hatch_angles: Optional[List[float]]` and `hatch_angle: float` (both backward-compatible defaults)
- `process_image_to_hatched_svg()` gained an `optimize_travel: bool = False` parameter (backward-compatible)

## [1.1.1] - 2026-06-16

### Fixed
- **`save_session` JSON serialization bug** (`src/hatchsvg/core.py:484`) — when
  `--save-session` was used, the color_map contained numpy `uint32` scalars
  from the quantization path and `json.dump` raised
  `TypeError: Object of type uint32 is not JSON serializable`. The bug
  was in the codebase since v1.0.0 but only ever triggered for users
  who ran `--save-session`. The fix coerces each RGB value to a plain
  Python `int` at the serialization boundary (RGB is conceptually 8-bit
  so no precision is lost). Caught by a new test, not by a linter or
  type-checker — see [Discipline note](#discipline-note).
- **Notebook byte-stability** (`scripts/build_notebooks.py`,
  `scripts/verify_notebooks_helpers.py`) — three non-determinism sources
  in the executed notebooks: (1) random `cell.id` values assigned by
  `nbformat.v4.new_code_cell` — fixed with `_assign_stable_ids(nb, prefix)`
  producing `f"{prefix}-cell-{i:02d}"` IDs; (2) wall-clock timing
  prints (`print(f'Render took ...s')`) and timing fields in
  `format_quantize_report` / `format_render_report` — removed; (3)
  Jupyter kernel execution timestamps in
  `cell.metadata.execution` (note: nested, not in
  `output.metadata.execution`) — stripped post-execution. Three
  consecutive `verify_notebooks.sh` runs now produce identical `sha256`.

### Removed
- **Duplicate `main()` in `src/hatchsvg/core.py`** (54 lines, lines
  1405-1458 prior to removal) — never called, dead code. The real CLI
  entry point is `hatchsvg.cli:main` per the `[project.scripts]`
  table in `pyproject.toml`. Removed along with an unused
  `import argparse` that was the only consumer.
- **Untracked planning/session documents** — `AGENTS.md`, `PLAN.md`,
  `REVIEW.md`, `CONTEXT_hatchsvg.md`, `GUI_ARCHITECTURE.md`, `HANDOFF.md`,
  `ROADMAP.md`, `SETUP.md`, `TASKS.md`, and `.opencode/` are now in
  `.gitignore` and removed from tracking. These are internal AI
  development notes that should never have been in a public repo.
  The package, tests, and user-facing docs (`README`, `CHANGELOG`,
  `LICENSE`) are the only public artifacts that ship on GitHub.

### Changed
- **Per-file ruff ignores** in `pyproject.toml` — added `notebooks/*.ipynb`
  (ignores `I001`/`E402`/`F811` for Jupyter cell architecture) and
  `notebooks/*_executed.ipynb` (ignores all rules for generated output).
  `scripts/hatchsvg_legacy.py` now ignores `I001` in addition to its
  existing rule groups. Resolves 50 lint errors without restructuring
  notebook sources.
- **`scripts/verify_notebooks_helpers.py`** (new) — Python module
  extracted from inline `python - <<PY` heredocs in
  `verify_notebooks.sh`. Two functions, `check_for_errors(nb_path)`
  and `strip_execution_timestamps(nb_path)`, plus a `__main__` CLI
  (`check` and `strip` subcommands). Enables 15 new unit tests
  for previously-untestable inline code.
- **Test count** — 70 → 88 tests; coverage 58% → 60%.

### Discipline note

The `save_session` JSON bug had been in the codebase since v1.0.0
and was *only* caught by writing a new test
(`test_cli_save_session_roundtrip`). Neither `ruff`, `ruff format`,
nor static type analysis flagged it. A linter will never find a
type that survives the boundary between numpy and stdlib. **Always
include a "test quality" agent in any code review pass, and always
run the new tests before declaring the review done.** The same
session also caught — and shipped the fix for — a subtle Jupyter
internals issue: kernel execution timestamps live in
`cell.metadata.execution` (a *nested* dict), not in
`output.metadata.execution`. The wrong-tree-level bug took two
debug iterations to diagnose.

## [1.1.0] - 2026-06-16

### Added
- **Three tutorial notebooks** in `notebooks/`:
  - `quickstart.ipynb` — 5 cells, ~5 minutes, copy-paste-done path
  - `explore.ipynb` — 6 cells, 4-stage walkthrough with explanations and 2a/2b/2c branches for color matching
  - `craft.ipynb` — 5 cells, advanced usage: custom palettes, per-color remap, session save/load, batch processing, parameter deep-dive, comparison with adjacent tools
- **Shared `notebooks/notebook_helpers.py`** — thin wrappers around `hatchsvg.core` (load_image, quantize_image, match_to_palette, render_svg, snapshot_session, etc.). No magic — every function is a one-liner around a `core` call.
- **`notebooks/README.md`** — entry point that says "start with quickstart, then explore, then craft"
- **`scripts/build_notebooks.py`** — programmatic notebook builder (notebooks are reviewable as Python in PRs, not as JSON)
- **`scripts/verify_notebooks.sh`** — CI script that runs all 3 notebooks end-to-end via `nbconvert --execute` and checks for errors
- **10 smoke tests** in `tests/integration/test_notebook_helpers.py` covering helper imports, palette loading, quantization, session save/load
- **`[notebook]` extra** in `pyproject.toml`: `jupyter`, `ipykernel`, `matplotlib`, `nbformat`
- **Per-file ruff ignores** for `scripts/hatchsvg_legacy.py` (pre-existing bugs in the preserved legacy file)
- **Named presets** — `--preset portrait|logo|line-art|photo|sketch|fast` for common use cases; explicit CLI flags override preset values
- **Multi-format input** — CLI now accepts `.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`, `.gif`, `.tiff`, `.tif` (Pillow decodes; CLI validates extension with a friendly error)
- **New module `hatchsvg.presets`** — typed `PRESETS` dict with 6 hand-tuned presets, `list_presets()`, `get_preset()`, `apply_preset()`; ships with 6 hand-tuned presets
- **`get_run_configuration(args, preset_name=...)`** — preset-aware variant of the CLI config loader; explicit CLI flags still win over preset defaults
- **21 new tests** in `test_presets.py` (13 tests) and `test_preset_config.py` (8 tests); all preset fields validated against `RenderParams` dataclass
- **8 new CLI integration tests** in `tests/integration/test_cli.py` — full subprocess coverage of `--version`, `--help`, presets, multi-format input, error handling
- **`examples/` directory** with `scene.png` (procedural 200×200 input) and 4 output SVGs demonstrating each preset (fast/portrait/logo/sketch)

### Changed
- **README rewrite** — new quickstart, comparison table vs potrace/vtracer/Inkscape, full CLI flag table, 5+ Cookbook recipes, expanded project structure
- **Test count** — 27 → 70 tests; coverage 49% → 58%; `presets.py` 100% covered, `notebook_helpers.py` ~60% covered

## [1.0.0] - 2026-06-15

### Added
- MIT license
- `pyproject.toml` with hatchling build system
- `--version` flag (`hatchsvg --version` → `hatchsvg 1.0.0`)
- Friendly error messages for `SystemExit` and palette loading failures
- Test suite: 8 unit tests + 1 end-to-end integration test with golden-file comparison
- GitHub Actions CI matrix (Linux + macOS, Python 3.11 / 3.12 / 3.13)
- `CHANGELOG.md` (this file)
- `.gitignore` with standard Python exclusions

### Changed
- Project restructured into `src/hatchsvg/` package layout
- `core.py` extracted from `hatchsvg.py` (algorithm preserved verbatim)
- CLI entry point moved to `hatchsvg.cli:main` (script `hatchsvg.py` retained as reference)
- Python requirement raised to 3.11+

### Fixed
- Cryptic `SystemExit` errors now show actionable advice
- Missing `--version` flag

[1.0.0]: https://github.com/Veedubin/hatchsvg/releases/tag/v1.0.0
[1.1.0]: https://github.com/Veedubin/hatchsvg/compare/v1.0.0...v1.1.0
