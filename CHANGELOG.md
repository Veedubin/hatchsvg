# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - Unreleased

### Added
- **Named presets** — `--preset portrait|logo|line-art|photo|sketch|fast` for common use cases; explicit flags override preset values
- **Multi-format input** — CLI now accepts `.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`, `.gif`, `.tiff`, `.tif` (Pillow handles the decoding; CLI validates the extension up front with a friendly error)
- **New module `png2svg.presets`** — `PRESETS` dict, `list_presets()`, `get_preset(name)`, `apply_preset(base, name)`; ships with 6 hand-tuned presets
- **`get_run_configuration(args, preset_name=...)`** — preset-aware variant of the CLI config loader; explicit CLI flags still win over preset defaults
- **21 new unit tests** in `test_presets.py` (13 tests) and `test_preset_config.py` (8 tests); all preset fields validated against `RenderParams` dataclass
- **8 new CLI integration tests** in `tests/integration/test_cli.py` — full subprocess coverage of `--version`, `--help`, presets, multi-format input, error handling
- **`examples/` directory** with `scene.png` (procedural 200×200 input) and 4 output SVGs demonstrating each preset (fast/portrait/logo/sketch)

### Changed
- **README rewrite** — new quickstart, comparison table vs similar tools (potrace, vtracer, Inkscape), full CLI flag table, Cookbook section with 5+ recipes, expanded project structure
- **Test count** — 27 → 60 tests; coverage 49% → 55%; `presets.py` 100% covered

## [1.0.0] - 2026-06-15

### Added
- MIT license
- `pyproject.toml` with hatchling build system
- `--version` flag (`png2svg --version` → `png2svg 1.0.0`)
- Friendly error messages for `SystemExit` and palette loading failures
- Test suite: 8 unit tests + 1 end-to-end integration test with golden-file comparison
- GitHub Actions CI matrix (Linux + macOS, Python 3.11 / 3.12 / 3.13)
- `CHANGELOG.md` (this file)
- `.gitignore` with standard Python exclusions

### Changed
- Project restructured into `src/png2svg/` package layout
- `core.py` extracted from `png2svg.py` (algorithm preserved verbatim)
- CLI entry point moved to `png2svg.cli:main` (script `png2svg.py` retained as reference)
- Python requirement raised to 3.11+

### Fixed
- Cryptic `SystemExit` errors now show actionable advice
- Missing `--version` flag

[1.0.0]: https://github.com/png2svg/png2svg/releases/tag/v1.0.0
[1.1.0]: https://github.com/png2svg/png2svg/compare/v1.0.0...HEAD
