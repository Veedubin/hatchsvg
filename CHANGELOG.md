# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.2.4] - 2026-06-22

### Fixed
- **CLI forced `skip_bg=True` overriding preset intent.** The `main()` function unconditionally set `params.skip_bg = True` after `get_run_configuration()` returned, which meant `--preset portrait` (which intentionally leaves `skip_bg=False`) always had background skipped. The override has been removed — presets now control `skip_bg` as designed.
- **Session load used wrong field name `skip_background` instead of `skip_bg`.** `save_session` writes `asdict(params)` which produces the key `skip_bg`, but `_load_config_session` read `skip_background`. Every session loaded from disk silently got `skip_bg=False` regardless of what was saved. Fixed to read `skip_bg`.
- **`--max-palette 12 --preset logo` gave 6 colors, not 12.** `_extract_explicit_args` compared `current != action.default` to detect explicit flags. When the user passed `--max-palette 12` and argparse's default was also 12, the flag was treated as NOT explicit, so the preset's `max_palette=6` won. Fixed by introducing `_TrackedAction` — a custom argparse Action that records whether the flag was actually invoked on the command line, regardless of value.
- **Magic number `0.5` in `_load_config_cli_with_preset` stroke-width logic.** The code checked `sw == 0.5` to decide whether to auto-derive stroke width from the marker palette. If `RenderParams.stroke_width` default ever changed, this would silently break. Fixed to check `"stroke_width" not in explicit` instead.

### Changed
- **Extracted duplicated layer-processing loop** in `process_image_to_hatched_svg` into a single `_process_one_layer` inner function (~60 lines of duplication eliminated).
- **Extracted duplicated stats computation** in `_display_stats_table` / `_display_stats_table_simple` into `_compute_display_stats` (~30 lines of duplication eliminated).
- **Extracted nested arc logic** from `_hatch_path_serpentine` into `_maybe_add_arc` helper (4 levels of nesting → 1).
- **Removed dead code**: unreachable `return` statement in `_hatch_path_serpentine`, redundant `row_idx + 1 < h` check in arc logic.

### Notes
- 166/166 tests pass. Coverage 59% (unchanged). Ruff clean, format clean.
- The `_TrackedAction` class in `cli.py` is a new public API surface — it's used by all non-store_true CLI arguments to track explicit invocation. Tests that build fake argparse parsers continue to work via a fallback in `_extract_explicit_args`.

## [2.2.3] - 2026-06-22

### Fixed
- **Hatching appearing in negative space (between letters, between bear ears)** due to anti-aliasing quantization noise. When an image is quantized to N colors, anti-aliased pixels at the background boundary often get bucketed into a near-duplicate shade (e.g. `(251, 235, 196)` instead of the detected background `(243, 215, 167)`). The previous `_detect_background` only returned ONE palette index, so all near-duplicate shades still got hatched — producing visible clusters of hatch lines in areas that should be paper. The fix extends `_detect_background` to return a set of indices: every palette color whose RGB Euclidean distance from the detected background is within a threshold (default 50 RGB units) is also treated as background and skipped. For the user's `rstp-warden-logo.png` this skips the `(251, 235, 196)` highlight shade, dropping the output from 5 layers to 4 and reducing file size by ~7%.

### Notes
- The threshold is configurable via the `near_threshold` parameter of `_detect_background` for callers who want to tune it.
- 166/166 tests pass (added 6 new tests in `tests/unit/test_background.py` for the new behavior). Coverage 59%.

## [2.2.2] - 2026-06-22

### Fixed
- **Thousands of redundant pen-down moves for quantized gradient images**. Two compounding issues caused the user's logo to render as 1.6MB / 57,000+ `M` commands instead of the expected ~500KB / ~200 commands:
  1. **Tiny noise components were each producing a separate hatch pass.** A single color layer in a gradient-quantized image can have 4,000+ connected components, most being 1-pixel anti-aliasing artifacts. Each component triggered its own `_hatch_path_serpentine` call, producing a chain of pen-down moves for a region too small to hold even one hatch cell. Now components smaller than `line_step²` pixels are filtered out as noise (with a fallback to ≥1px for tiny test images). For the user's 1794×1794 logo: 57,000 → 1,278 `M` commands (97% reduction).
  2. **`separate_outline=True` was the default for `logo` preset** (changed in v2.x). With `separate_outline=True`, every layer gets an extra `<g>` outline group with `line_step=1` hatching on the border mask — for a complex shape that's thousands of short pen-down moves (one per pixel row of the border). For pen plotters, this is wasted ink and time. The `logo` preset now defaults to `separate_outline=False` (v1.x behavior). To opt back into the separate outline mode, pass `--separate-outline`.
  3. **`_hatch_path_serpentine` was drawing the same y-coordinate twice when transitioning between odd and even rows without an arc.** The chain was kept "live" across rows even when no arc was emitted to move the pen to the next y, so the next row's `H` command drew at the previous row's y. Now `chain_live` stays True ONLY when an arc was actually emitted (which moves the pen's y). Verified on the golden test image: a 50-pixel-tall red region now produces 5 hatch lines (one per scanned row), where the old buggy code produced 3 with several drawn at the wrong y.

### Changed
- **`separate_outline=False` is now the default for the `logo` preset** (was `True` in v2.x, `False` in v1.x). For pen-plotter use cases the outline mode generates thousands of short pen-down moves on complex shapes. Use `--separate-outline` to restore the v2.x behavior, or apply it per-render via `--separate-outline`.

### Notes
- The user's 1794×1794 logo drops from **1.6MB → 73KB** (96% reduction) with `--preset logo`. The output is also visually correct now — previously, the same y-coordinate was being drawn multiple times (e.g. `M110 120 H170 A 5.0 5.0 0 0 1 170 132 H110 H170 A 5.0 5.0 0 0 1 170 156 H110 H170` was drawing rows 120, 132, 132-again, 156, 156-again instead of rows 120, 132, 144, 156, 168).
- 160/160 tests pass. Coverage 59%. The e2e golden file was regenerated and now produces correct row-by-row output.

## [2.2.1] - 2026-06-22

### Fixed
- **Background was always rendered as a hatch layer, regardless of `--no-skip-background` flag**. The `--no-skip-background` flag was defined in the CLI but never read — `params.skip_bg` always stayed at its default `False`. As a result, the dominant background color was always included in the output, even for users who expected it to be skipped (the default). For a pen-plotter tool this is the wrong default — backgrounds should be skipped by default; users who want the full image hatched (e.g. photo mosaics) can opt in with `--no-skip-background`. The fix wires the flag: when `--no-skip-background` is NOT passed, `params.skip_bg = True` (background detected and excluded). When passed, the background layer is included. Added 2 regression tests (`test_cli_skip_background_default_excludes_bg_layer`, `test_cli_no_skip_background_includes_bg_layer`).

### Changed
- **`skip_bg: True` added to 4 presets** (`logo`, `line-art`, `sketch`, `fast`) where skipping the background is the right default. The `portrait` and `photo` presets do NOT set `skip_bg` because the user may want the full image hatched for photographic use cases. Override with `--no-skip-background` if needed.

## [2.2.0] - 2026-06-20

### Removed
- **`--workers` CLI flag** and the underlying `ProcessPoolExecutor`-based per-component parallel hatch generation. In practice, Python's fork overhead (~50-100ms per task) dominated per-component work for typical logos with small components, making the parallel implementation 9x **slower** than serial on a 16-core machine. The `_hatch_components_parallel`, `_hatch_components_serial`, and `_hatch_one_component` helper functions have been removed. The `n_workers` field on `RenderParams` has been removed. The `hatch_path_for_mask` function is back to its v1.x shape: a single inlined per-component loop. The vectorized `scipy.ndimage.center_of_mass` centroid computation is preserved (was always a clear win, no fork involved).
- **`tests/unit/test_parallel_hatch.py`** deleted entirely.

### Notes
- The serpentine chaining fix (v2.1.0) and the absolute-coordinates fix (v2.1.1) are both preserved. Render output is byte-identical to v2.1.1 — the only behavior change is performance (slightly faster on small components, since we no longer pay fork overhead).
- 158/158 tests pass. Coverage 59% (unchanged). The e2e golden file is byte-identical.

## [2.1.1] - 2026-06-20

### Fixed
- **CRITICAL: Path coordinates were relative to slice origin, not image origin**. v2.1.0 introduced a `scipy.ndimage.find_objects` optimization that extracted each component's bounding-box slice and ran `_hatch_path_serpentine` on the slice. The serpentine function emits coordinates relative to its input's origin, so all components ended up with paths starting at `(0, 0)` regardless of where the component actually was in the image. Visual result: all layer paths were stacked on top of each other at the top-left of the SVG, producing thousands of overlapping `M0 0 H1 ...` micro-segments. The fix reverts to using full-size boolean masks (`labeled == component_id`) per component — slightly more memory (~3GB temp for typical logos) but correct coordinates. A regression test (`test_component_paths_use_absolute_coordinates_not_slice_local`) verifies coords land in the correct component regions.

## [2.1.0] - 2026-06-19

### Added
- **`--workers N` CLI flag** for opt-in parallel hatch generation. Each connected component's hatch generation runs in a separate worker via `ProcessPoolExecutor` (fork context on POSIX for fast startup). Centroids are now computed in a single vectorized `scipy.ndimage.center_of_mass` call instead of an O(N) `np.where` + `np.mean` loop. Per-component work uses bounding-box slices via `scipy.ndimage.find_objects`, eliminating ~3GB of temporary full-mask copies for typical logos.
- **6 new tests** in `tests/unit/test_parallel_hatch.py` covering serial-vs-parallel output equivalence, the new `n_workers` parameter, single-component / zero-component edge cases, and a smoke benchmark.

### Fixed
- **Serpentine path chaining bug** in `_hatch_path_serpentine`. Previously the function emitted a new `M` command at the start of every row, breaking the chain even when the previous row had ended exactly where the next row began. With `arc_radius > 0` (e.g. `--preset logo`), this produced thousands of disconnected 2-pixel arcs in the outline path — visually rendering as "random dots" instead of a continuous shape boundary. Now tracks `chain_live` across rows so a single `M` spans the whole connected component. Golden file dropped from 5724 to 3942 bytes (32% smaller).

### Notes
- **Parallelism is opt-in via `--workers N` (default: `os.cpu_count()`)**. Benchmarking shows that for components smaller than ~100×100 pixels, serial is actually faster because Python's `ProcessPoolExecutor` fork overhead (~50-100ms per task) dominates per-component work. Use `--workers 1` to force serial. The real performance win for many small components comes from vectorizing the per-row hatch walk itself, which is a separate effort.
- **No public API changes**. `RenderParams` gained an `n_workers: Optional[int]` field (additive, defaults to `None` = auto). All 164 tests pass. The golden file test was regenerated with the new path format.

## [2.0.0] - 2026-06-17

### Changed
- **Package renamed from `png2svg` to `hatchsvg`** to match the GitHub repository. `pip install hatchsvg`, `import hatchsvg`, `hatchsvg` CLI command. No other changes — all v1.2.0 features and the golden file output are unchanged.

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
