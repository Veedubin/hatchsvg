# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
