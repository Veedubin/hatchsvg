# png2svg Handoff — 2026-06-16 (Code review + bug fix)

> **Session log**: This file accumulates across sessions. Newest content is
> at the top. Earlier sessions are preserved below.

## Code Review Session (2026-06-16)

Multi-agent parallel code review. Three specialist agents dispatched
in parallel: `boomerang-linter` (lint/type), `boomerang-coder`
(dead code/deps), and `boomerang-architect` (refactor). Findings
were aggregated and applied in two commits.

### What Shipped (2 commits)

| Commit | Description |
|--------|-------------|
| `aba677f` | `chore: code review fixes (lint, dead code, refactor)` |
| `fa1a1a0` | `test: add CLI session roundtrip and verify_helpers unit tests; fix JSON bug` |

### Commit `aba677f` — Code Review Fixes

1. **Dead code removed**: `src/png2svg/core.py` had a duplicate
   `main()` function (54 lines) that was never called. The real entry
   point is `png2svg.cli:main` per `pyproject.toml`. Also removed
   the now-unused `import argparse` at module top.

2. **Lint clean**: 50 ruff errors → 0 via per-file ignores:
   - `notebooks/*.ipynb` — ignore I001/E402/F811 (Jupyter cell
     architecture violates these by design)
   - `notebooks/*_executed.ipynb` — ignore ALL (generated output)
   - `scripts/png2svg_legacy.py` — added I001 to existing ignore

3. **Format clean**: Added explicit `ruff format` steps in
   `verify_notebooks.sh` for both source and executed notebooks to
   prevent future drift.

4. **Refactor**: Extracted Python from inline heredocs in
   `verify_notebooks.sh` to a new module
   `scripts/verify_notebooks_helpers.py`. The heredocs were 30+
   lines of Python inside bash; extracting them makes the logic
   readable, testable, and re-usable.

5. **Notebook cleanup**: Removed unused `from dataclasses import asdict`
   imports (F401) and the `f-string` without placeholders (F541)
   that ruff flagged.

6. **conftest.py**: Added `SCRIPTS_DIR` to `sys.path` so tests can
   import `scripts/verify_notebooks_helpers.py` as a module.

### Commit `fa1a1a0` — Tests + Bug Fix

The new `test_cli_save_session_roundtrip` test **caught a real bug
on the first run**: `save_session()` failed with
`TypeError: Object of type uint32 is not JSON serializable`. The
color_map values contained numpy `uint32` scalars (from the
quantization path), and `json.dump` couldn't serialize them.

**Fix**: in `src/png2svg/core.py::save_session`, convert each RGB
value to a plain Python `int` via `int(c) for c in ...` before
serializing. The data is conceptually 8-bit RGB, so this is a safe
coercion. Comment added explaining the constraint.

**New tests**:
- `test_cli_save_session_roundtrip` — exercises `--save-session` and
  `--use-session` end-to-end
- `test_cli_missing_input_file` — exercises the FileNotFoundError
  path in cli.py
- `test_cli_stats_flag_runs` — exercises the `--stats` flag
- `test_verify_notebook_helpers.py` (15 tests) — unit tests for the
  extracted verify_helpers module: check_for_errors,
  strip_execution_timestamps, CLI subprocess, byte-stability

### Quality Gates After This Session

- `ruff check` (full project): **clean**
- `ruff format --check` (full project): **clean**
- `pytest`: **88/88 pass** (was 70; +18 new), coverage **60%** (was 58%)
- `bash scripts/verify_notebooks.sh`: 3/3 execute, byte-identical
- `git status`: clean

### Findings Deferred (With Reason)

These were identified but not fixed because they're not worth the
risk in this session:

1. **Splitting `core.py` into 6 modules** (color.py, path.py,
   svg.py, session.py, stats.py, params.py) — would require
   rewriting tests, currently workable structure. Defer to v1.2.0.
2. **Replacing the byte-for-byte golden file test with semantic XML
   comparison** — would change the test contract, defer until the
   next refactor that touches SVG output.
3. **Adding `from __future__ import annotations` to all files** —
   Python 3.11+ supports PEP 604 natively; the import is redundant
   cargo cult. Skipped.
4. **Moving `scipy` from `plot` extra to core dependencies** —
   semantic change to `pyproject.toml`, not a code fix. Defer.
5. **Notebook helpers public API bloat** (`display_side_by_side`,
   `image_to_png_bytes`, `image_to_data_url`, `numpy_to_pil` are
   never used) — they're part of the public API for users to call
   from their own notebooks. KEEP for now, evaluate after v1.2.0.

## Post-release Housekeeping Session (2026-06-16)

Two follow-up commits on top of v1.1.0, addressing accidental-commit
risk and notebook reproducibility.

### What Shipped (2 commits)

| Commit | Description |
|--------|-------------|
| `b017674` | `chore: stop tracking Boomerang plugin artifacts and session files` |
| `3686b28` | `fix(notebooks): make executed notebooks byte-identical on re-execution` |

### Commit `b017674` — Untrack the noise

The user noticed that `.opencode/`, `AGENTS.md`, `memory_data/`,
`REVIEW.md`, and `PLAN.md` could accidentally be committed by a
hasty `git add -A` and asked for them to be gitignored.

- `.gitignore`: added `.opencode/`, `AGENTS.md`, `PLAN.md`, `REVIEW.md`
  (memory_data/ was already on line 62 from the Week 1 commit)
- `git rm --cached` on the 41 already-tracked files. Files remain on
  disk; they're just not in git's index anymore.
- The v1.1.0 tag's tree still references the removed paths. This is
  expected: tags are immutable snapshots.

**Lesson learned:** When a project is bootstrapped, the initial
`git add .` may sweep in files that belong to the development
environment, not the project. Add `.gitignore` BEFORE the first
commit, or be ready to do `git rm --cached` cleanup later.

### Commit `3686b28` — Make executed notebooks byte-identical

Running `bash scripts/verify_notebooks.sh` on a fresh checkout would
change the committed `*_executed.ipynb` files in ways that had
nothing to do with the actual content. Three non-determinism sources,
all fixed:

1. **Random cell IDs** (193/193 churn). nbformat's `new_code_cell`
   assigns random hex IDs by default. Fixed by adding
   `_assign_stable_ids(nb, prefix)` in `scripts/build_notebooks.py`
   that gives every cell `f"{prefix}-cell-{i:02d}"`. After a rebuild,
   subsequent `nbconvert --execute` calls preserve the IDs.

2. **Wall-clock timing** in 3 cells ("Render took 3.2s") and in
   `format_quantize_report` / `format_render_report` ("Quantized in
   100ms"). Removed the prints and the timing from the formatted
   reports. The `elapsed_ms` field is still in the result dict for
   interactive use.

3. **Jupyter kernel timestamps** in `cell.metadata.execution`
   (iopub.execute_input, iopub.status.busy, iopub.status.idle,
   shell.execute_reply). Fixed by adding a post-processing step at
   the end of `verify_notebooks.sh` that strips these 4 keys after
   every nbconvert run. Stripped 16/24/20 keys per notebook.

**Test result:** 3 consecutive runs of `bash scripts/verify_notebooks.sh`
produce byte-identical executed notebooks (sha256 verified end-to-end).

**Test fix:** `test_format_quantize_report_is_markdown_table` was
asserting "Quantized in 100ms" in the report. Updated to assert
"Quantized in" NOT in report and "**Quantized**" IS in report, with
a comment explaining the timing removal.

### Quality Gates After Both Commits

- `ruff check src tests`: clean
- `ruff format --check src tests`: clean
- `pytest`: 70/70 pass, coverage 58%
- `bash scripts/verify_notebooks.sh`: 3/3 execute, 0 errors
- **sha256 determinism test**: 3 consecutive runs produce identical
  `*_executed.ipynb` files
- `git status`: clean (no noise)

### Critical Note About the v1.1.0 Tag

The v1.1.0 tag (`bad254a`, points at `e800c2c`) was created BEFORE
the two follow-up commits. The tag's tree still contains the
noise files and the random cell IDs. This is fine for now — tags
are immutable snapshots of a moment in time. When you push, you
have two reasonable options:

1. **Push the branch as-is.** Anyone who clones the v1.0.0-release
   branch gets the latest commit, which has the noise removed and
   the deterministic notebooks. The tag itself is just a marker.

2. **Re-tag.** If you want v1.1.0 to point at the post-fix commit,
   move the tag: `git tag -f v1.1.0 <new-commit>` and re-push.
   This violates "tags are immutable" convention but is sometimes
   necessary for a v1.x.y that had late-breaking fixes.

For now, option 1 is recommended. The released wheels (when you
build them) will reflect the branch tip, not the tag.

## v1.1.0 Release Session Summary (2026-06-16)

Tagged **v1.1.0** and **v1.0.0** (retroactive). No remote configured, so
push is deferred to the user. The release is shippable from this branch
the moment a remote is added.

### What Shipped (1 commit, 1 tag)

| Commit | Description |
|--------|-------------|
| `e800c2c` | `chore(release): bump version to 1.1.0` |
| `a5ae576` | `docs: record v1.1.0 release in HANDOFF.md and TASKS.md` |

- Bumped `__version__` to 1.1.0
- Finalized `[1.1.0] - 2026-06-16` entry in CHANGELOG.md
- Fixed `test_cli_version` to import `png2svg.__version__` instead of
  hardcoding `1.0.0` (test was breaking on the very first commit, but
  never noticed because previous session didn't run the full suite)
- Tagged `v1.1.0` (annotated, SHA `bad254a`) at `e800c2c` and
  `v1.0.0` (annotated, SHA `2702afc`) retroactively at `6e7f3f7` —
  both have release-note messages

### Why 1.1.0, Not 1.0.1

Per SemVer, a **patch** is bug fixes only; a **minor** is backwards-
compatible new features. Everything in the unreleased changelog is
additive:

- Named presets (new flag, new module)
- Multi-format input (new supported extensions)
- 3 tutorial notebooks + helpers (new user-facing artifacts)
- `[notebook]` extra (new optional dep group)
- 39 new tests (60 → 70)
- README rewrite (docs only)

No bug fixes, no breaking changes. Textbook minor bump.

### Quality Gates at Tag Time

- `ruff check src tests`: clean
- `ruff format --check src tests`: 20 files clean
- `pytest`: **70/70 pass in ~40s**, coverage 58%
- `bash scripts/verify_notebooks.sh`: all 3 notebooks execute end-to-end
  with 0 errors

### What's NOT in This Release

I deliberately did **not** commit the following working-tree noise, which
is unrelated to v1.1.0:

- `.opencode/` (Boomerang plugin sync, 14 files modified)
- `AGENTS.md` (plugin roster changes)
- `memory_data/memories.lance/` (memini-ai transaction churn)
- `REVIEW.md` and `PLAN.md` (untracked Boomerang session artifacts)

These should be committed in a separate "chore: sync Boomerang plugin"
commit before/after the release, **not** as part of the v1.1.0 tag.

### Next Steps (Pending User)

1. **Add a remote** (`git remote add origin <URL>`)
2. **Push the branch**: `git push -u origin v1.0.0-release`
3. **Push the tag**: `git push origin v1.0.0 v1.1.0`
4. **Create GitHub Release** for v1.1.0 with the tag's annotation text
   (or use the CHANGELOG entry)
5. **Merge v1.0.0-release → main** when ready (this is a big body of
   work — 11 commits since the v1.0.0 cutoff)

## Notebook Suite Session Summary (2026-06-15)

## Notebook Suite Session Summary (2026-06-15)

Pivoted from the deferred GUI work (design doc shipped in commit `77ea467`)
to a **Jupyter notebook tutorial suite** at the user's request. The user
wanted "really good explanations" and "multiple examples for different
ways to use this file" — notebooks are the right tool for that.

### What Shipped

**1 new commit (Notebook Suite):**

```
010e14d feat(notebooks): ship 3-notebook tutorial suite
```

(Previous commits: `77ea467` GUI design doc, `64c8ae6` HANDOFF update,
`386be6d` Week 2 polish.)

### New Files

**Notebooks (`.ipynb` generated from `scripts/build_notebooks.py`):**
- `notebooks/quickstart.ipynb` — 11 cells (7 markdown, 4 code). ~5 min.
- `notebooks/explore.ipynb` — 17 cells (11 markdown, 6 code). 30-60 min.
- `notebooks/craft.ipynb` — 24 cells (19 markdown, 5 code). 1-2 hours.
- `notebooks/quickstart_executed.ipynb`, `explore_executed.ipynb`, `craft_executed.ipynb` — last successful execution outputs (committed so reviewers can see what each notebook produces without running them)

**Supporting files:**
- `notebooks/notebook_helpers.py` — 738-line shared module wrapping `png2svg.core` (no magic, every function is a one-liner around a `core` call)
- `notebooks/README.md` — entry point with "start here" guidance
- `scripts/build_notebooks.py` — 680-line Python builder (notebooks are reviewable as Python in PRs)
- `scripts/verify_notebooks.sh` — CI script that runs all 3 notebooks end-to-end via `nbconvert --execute`
- `tests/integration/test_notebook_helpers.py` — 10 smoke tests covering helper imports, palette loading, quantization, session save/load

### Modified Files

- `pyproject.toml` — added `[notebook]` extra (jupyter, matplotlib, ipykernel, nbformat); per-file ruff ignores for `scripts/png2svg_legacy.py` (pre-existing bugs in preserved legacy file)
- `CHANGELOG.md` — added 1.1.0 entries
- `TASKS.md` — added notebook suite completion, deferred module split and GUI

### Key Design Decisions

1. **Notebooks, not GUI.** User feedback: "I hate it when a vendor only shows
   me how to do the simplest thing." Notebooks give us 3 tiers of depth
   (quickstart/explore/craft) and let users see the actual code.

2. **3 notebooks, not 1.** A single notebook would either be too shallow
   (offensive to advanced users) or too deep (intimidating to beginners).
   Three tiers with explicit "start with X, then Y, then Z" guidance in
   `README.md` respects both audiences.

3. **Helpers are thin, not magical.** Every function in
   `notebook_helpers.py` is a one-liner around a `png2svg.core` call.
   The user can click into the helper to see what it does, then click
   into `core` to see the actual algorithm. No black boxes.

4. **Notebooks are built from Python source, not JSON.** `scripts/build_notebooks.py`
   generates the `.ipynb` files. PRs show the notebook as Python (reviewable,
   lintable). The `.ipynb` files are the generated artifact.

5. **`nbconvert --execute` is the test.** The verify script runs all 3
   notebooks end-to-end via `nbconvert` and checks cell outputs for errors.
   This is the heavy test; the unit tests in
   `test_notebook_helpers.py` are the cheap regression.

6. **2a/2b/2c branches in explore.** The color-matching stage has 3
   paths: 2a) physical marker palette, 2b) plain k-means quantize,
   2c) aggressive quantize for line art. This is the most opinionated
   stage; users with different needs take different paths.

### Deviations from PLAN

- **GUI was planned, notebooks shipped.** Per user pivot. GUI design
  doc preserved in `GUI_ARCHITECTURE.md` as reference.
- **Module split (color.py/path.py/svg.py/etc.)** — still deferred.
  Risk vs reward didn't justify it for a notebook launch.

### Quality Gate Status (after Notebook Suite)

- ✅ `pip install -e ".[notebook]"` succeeds
- ✅ **70 tests pass** (60 → 70 with 10 new smoke tests; was 27 in Week 1)
- ✅ Coverage: 58% (up from 55% in Week 2; was 49% in Week 1)
- ✅ `ruff check` clean (with per-file ignores for legacy script)
- ✅ `ruff format` clean
- ✅ All 3 notebooks execute end-to-end via `bash scripts/verify_notebooks.sh`
- ✅ `notebook_helpers.py` is 100% importable and tested

### Test Breakdown

| File | Test count | Coverage |
|------|-----------|----------|
| `tests/integration/test_notebook_helpers.py` | 10 | ~60% of `notebook_helpers.py` |
| All other tests (from Week 1 + 2) | 60 | unchanged |
| **Total** | **70** | (was 60 in Week 2) |

### Where to Resume Next Session

1. **Merge `v1.0.0-release` → `main`** (when user is ready — this is now a
   big body of work; merge is non-trivial)
2. **Bump version to 1.1.0** in `__init__.py` and tag the release
3. **Module split of `core.py`** (the long-deferred refactor) — tests
   are in place, so this is now safe
4. **PyPI publish** (Week 4 from original plan) — needs a real repo URL
5. **Hero GIF for README** (requires screen recorder)
6. **Update placeholders** — global find-replace on `png2svg contributors`
   and `github.com/png2svg/png2svg` once user provides real values
7. **GUI (deferred)** — the design doc is in `GUI_ARCHITECTURE.md`; revisit
   if user demand exists

### Warnings (carried forward)

- 14 uncommitted Boomerang plugin files + memory_data lance churn
  STILL NOT part of v1.0.0. Review and commit separately if merging.
- Author/repo placeholders still in place. User will swap later.
- Golden file is 441KB (intentional for fast CI). Default params produce
  ~1.5MB. The test uses specific params intentionally.

---

# Week 1 + Week 2 Handoffs (archived)

> The Week 1 and Week 2 handoff content is preserved verbatim below.
> See "Previous Session Reference" for Week 1, and the previous handoff
> sections for Week 2 (preserved at the bottom of the file in earlier
> commits).

## Week 2 Session Summary (2026-06-15)

Continued v1.0.0 release work. **Week 2 polish complete**: named presets,
multi-format input, examples directory, comprehensive README rewrite, and
33 new tests. Branch `v1.0.0-release` now has 8 commits.

### What Shipped

**1 new commit (Week 2):** `386be6d feat: add named presets and multi-format input support`

(Week 1 commits 0022496, e9f20a2, b4c3571, fa6211a, 9e318b7, a2aa45a, cfe9361
are described in the Week 1 handoff below.)

### New Files (Week 2)

- `src/png2svg/presets.py` — `PRESETS` dict with 6 hand-tuned presets
  (portrait, logo, line-art, photo, sketch, fast) + `list_presets()`,
  `get_preset()`, `apply_preset()`. 100% line coverage.
- `tests/unit/test_presets.py` — 13 tests
- `tests/unit/test_preset_config.py` — 8 tests (preset merge behavior,
  explicit-flag override, unknown-name error, session path)
- `tests/unit/test_input_formats.py` — 4 tests (Pillow round-trip per
  format, exclusion of unsupported types)
- `tests/integration/test_cli.py` — 8 CLI subprocess tests
- `examples/README.md` — gallery documentation
- `examples/scene.png` — procedural 200×200 input (sky + sun + mountain + tree)
- `examples/scene_fast.svg`, `scene_portrait.svg`, `scene_logo.svg`,
  `scene_sketch.svg` — 4 example outputs (10-25KB each)

### Modified Files (Week 2)

- `src/png2svg/cli.py` — new `--preset` flag, multi-format validation,
  attach parser as `args._png2svg_parser`
- `src/png2svg/core.py` — `get_run_configuration(args, preset_name=None)`
  + new `_load_config_cli_with_preset` + `_extract_explicit_args` helpers
- `README.md` — comprehensive rewrite: quickstart, comparison table,
  full flag table, 5+ Cookbook recipes
- `CHANGELOG.md` — added 1.1.0 (unreleased) section
- `TASKS.md` — added Week 2 completion summary, updated Quality Status

### Key Decisions Made (Week 2)

1. **Preset as a base, explicit flags override** — `png2svg img out
   --preset logo --line-step 2` keeps logo's `max_palette=6,
   separate_outline=True` but applies the user's `line_step=2`.
2. **Parser attached to args, not stack-walked** — The CLI does
   `a._png2svg_parser = p` after `parse_args()`. `core._extract_explicit_args`
   reads `args._png2svg_parser` to diff against the parser's defaults.
3. **6 presets, not 3** — Original PLAN called for 3; added photo, sketch,
   and fast. The `fast` preset is especially useful for iterating without
   waiting 35s per render.
4. **Validation up-front, not Pillow's cryptic error** — Check the suffix
   in the CLI and print a one-line "Supported formats: ..." message.
5. **No hero GIF** — REVIEW.md called for one. Skipped: requires a screen
   recorder or external tool. Left as a "later" item.

### Deviations from PLAN.md (Week 2)

| Item | PLAN | Actual | Reason |
|------|------|--------|--------|
| Preset count | 3 (portrait, logo, line-art) | 6 (added photo, sketch, fast) | More useful + minimal extra code |
| README sections | "Hero GIF" | Comparison table + Cookbook | No screen recorder; comparison table is more useful |
| Module split | "Week 2" | "Week 3" | Defer the refactor; ship user-facing value first |
| Examples | "3-5 example pairs" | 1 input + 4 outputs (4 presets) | Same plan, different split |
| CLI refactor for explicit-args | Not specified | `args._png2svg_parser` attribute | Cleaner than stack-walking |

### Quality Gate Status (after Week 2)

- ✅ `pip install -e .` / `[plot]` / `[dev]` — all succeed
- ✅ `png2svg --version` → `png2svg 1.0.0`
- ✅ `python -m png2svg --version` works
- ✅ `png2svg --help` shows new --preset choices
- ✅ `png2svg photo.jpg out.svg` — multi-format input works
- ✅ `png2svg img out --preset portrait` — preset works
- ✅ `png2svg img out --preset logo --line-step 2` — explicit override works
- ✅ `png2svg foo.exe out.svg` — friendly error on unsupported format
- ✅ `png2svg --preset bogus` — argparse rejects with exit 2
- ✅ **60 tests pass** (was 27 in Week 1; 33 new tests)
- ✅ `ruff check src tests` clean
- ✅ `ruff format` clean
- ✅ Coverage: 55% (was 49% in Week 1); `presets.py` at 100%

### Test Breakdown

| File | Test count | Coverage |
|------|-----------|----------|
| `tests/unit/test_presets.py` | 13 | 100% of `presets.py` |
| `tests/unit/test_preset_config.py` | 8 | new preset merge logic |
| `tests/unit/test_input_formats.py` | 4 | format whitelist |
| `tests/integration/test_cli.py` | 8 | CLI subprocess flows |
| All other unit + integration tests | 27 | (unchanged from Week 1) |
| **Total** | **60** | (was 27) |

### Where to Resume Next Session

1. **Merge `v1.0.0-release` → `main`** (when user is ready)
2. **Bump version to 1.1.0** in `__init__.py` and tag the release
3. **Start Week 3**: module split of `core.py` into `color.py`,
   `path.py`, `svg.py`, `session.py`, `stats.py`, `params.py`
4. **Test on actual Cricut hardware** (still open from prior session)
5. **Generate hero GIF** (requires external tooling)
6. **Ship to PyPI** (Week 4) — needs a real repo URL the user hasn't
   provided yet
7. **Update placeholders** — global find-replace on `png2svg contributors`
   and `github.com/png2svg/png2svg` once user provides real values

### Warnings (carried forward)

- The pre-existing uncommitted changes (`.opencode/`, `AGENTS.md`,
  `memory_data/`) are STILL NOT part of v1.0.0. When merging, they should
  be reviewed separately and may need to be committed as a "chore: sync
  Boomerang plugin state" commit. There are now 14 modified files in
  `.opencode/agents/` and 1 deleted skill (boomerang-compactor).
- The user mentioned they will change the author and repo URL
  placeholders later. Easy global find-replace: `png2svg contributors`
  and `github.com/png2svg/png2svg`.
- The golden file is small (441KB) for fast CI; if someone re-runs with
  default params, the file will be ~1.5MB. The test uses specific params
  intentionally.

---

# Week 1 Handoff (2026-06-15, archived)

> Original Week 1 handoff preserved verbatim below for reference.

## Session Summary

Completed **Week 1 of the v1.0.0 release plan** for png2svg. The project is now
ready for public release: pip-installable, tested, CI-backed, and properly
licensed.

## What Shipped

### 7 Conventional Commits on branch `v1.0.0-release`

```
0022496 feat: add __main__.py to support python -m png2svg
e9f20a2 ci: add GitHub Actions workflow with ruff and pytest matrix
b4c3571 test: add unit and integration tests with golden file
fa6211a docs: rewrite README for v1.0.0 release
9e318b7 chore: move legacy script to scripts/ directory
a2aa45a feat: package png2svg with hatchling and src layout
cfe9361 chore: add MIT license, .gitignore, and changelog
```

### New Files

- `LICENSE` — MIT, copyright `png2svg contributors` 2026
- `pyproject.toml` — hatchling build, Python 3.11+, `[plot]` + `[dev]` extras
- `CHANGELOG.md` — v1.0.0 entry
- `.gitignore` — Python + png2svg-specific patterns
- `src/png2svg/__init__.py` — `__version__ = "1.0.0"`
- `src/png2svg/core.py` — algorithm (extracted from legacy `png2svg.py`, then lint-cleaned)
- `src/png2svg/cli.py` — full CLI with `--version` and friendly error wrapper
- `src/png2svg/__main__.py` — supports `python -m png2svg`
- `tests/__init__.py`, `tests/conftest.py`, `tests/unit/__init__.py`, `tests/integration/__init__.py`
- `tests/unit/test_segments.py`, `test_color.py`, `test_palette.py`, `test_session.py`, `test_hatch.py`
- `tests/integration/test_e2e.py`
- `tests/fixtures/bluey_golden.svg` — 441KB golden file
- `.github/workflows/ci.yml` — 6-job matrix (Linux + macOS × Python 3.11/3.12/3.13)
- `REVIEW.md` — comprehensive audit
- `PLAN.md` — v1.0.0 implementation plan

### Modified Files

- `README.md` — new title, badges, pip install instructions, updated project structure, development section
- `png2svg.py` → `scripts/png2svg_legacy.py` (renamed to remove from import path)

### Pre-existing Unrelated Changes (left untouched)

The following were modified before this session and are NOT part of the v1.0.0
release. Leave them alone — they belong to a different concern (Boomerang
plugin agent files + memory data).

- `.opencode/agents/*` (13 files modified, 1 deleted, 3 new)
- `.opencode/skills/boomerang-compactor/` (deleted)
- `AGENTS.md`, `HANDOFF.md` (the old Boomerang one), `TASKS.md`
- `memory_data/` (lance database transactions)

## Key Decisions Made (Week 1)

1. **Python 3.11+ floor** (not 3.9) — user explicitly chose this; widens
   available syntax (PEP 604 unions, `tomllib`).
2. **Hatchling build** — modern PEP 621, faster than setuptools.
3. **Verbatim `core.py` extraction** — algorithm code is byte-for-byte the
   same as the legacy `png2svg.py`, then `ruff format` was run to clean
   whitespace and import order (zero behavior changes).
4. **Legacy script moved to `scripts/`** — `png2svg.py` at the repo root
   shadowed the `png2svg` package during test collection. Moving it to
   `scripts/png2svg_legacy.py` keeps it accessible for reference while
   letting the package import cleanly.
5. **Generic placeholders** — author and repo URL are `png2svg contributors`
   and `github.com/png2svg/png2svg` placeholders. User can swap via
   `git commit --amend` or project-wide find-replace later.
6. **Golden file params** — slightly different from the spec
   (`--max-palette 4 --line-step 10`) to keep the file under 500KB. Spec
   was `default --max-palette 12` which produced 1.5MB.
7. **Python 3.13 added to matrix** — beyond spec (3.9/3.11) since the user
   chose 3.11+ as the floor; testing 3.11/3.12/3.13 is the modern standard.

## Deviations from PLAN.md (Week 1)

| Item | PLAN | Actual | Reason |
|------|------|--------|--------|
| Python floor | 3.9 | 3.11 | User decision |
| Python classifiers | 3.9/3.10/3.11/3.12 | 3.11/3.12/3.13 | User decision + modern floor |
| Golden file params | default (1.5MB) | `--max-palette 4 --line-step 10` (441KB) | <500KB size constraint |
| `core.py` line count | 1268 (per PLAN) | 1326 | PLAN had wrong count; guard is lines 1327-1328 of original |
| CLI helpers in core | "stay in cli.py" | "stay in core.py" | Preserved verbatim-copy constraint; helpers already in core |
| Legacy script | (not addressed) | Moved to `scripts/png2svg_legacy.py` | Required to avoid module shadowing |
| Commit count | 4-6 | 7 | Added `__main__.py` as bonus commit |

## Quality Gate Status (Week 1)

All gates pass:

- ✅ `pip install -e .` succeeds
- ✅ `pip install -e ".[plot]"` succeeds
- ✅ `pip install -e ".[dev]"` succeeds
- ✅ `png2svg --version` → `png2svg 1.0.0`
- ✅ `python -m png2svg --version` → `png2svg 1.0.0`
- ✅ `png2svg --help` shows all 18 flags + `--version`
- ✅ All 27 tests pass (25 unit + 2 integration, ~35s)
- ✅ `ruff check src tests` clean
- ✅ `ruff format` clean
- ✅ `.github/workflows/ci.yml` valid YAML (6 jobs)
- ✅ Git history: 7 clean conventional commits
- ✅ Regression test: legacy `python scripts/png2svg_legacy.py` and
  `.venv/bin/png2svg` produce equivalent output

## Files Preserved (Week 1)

- `scripts/png2svg_legacy.py` — original 1328-line script, retained as reference
- `color_palettes/` — 2 bundled palettes
- `Bluey.png`, `Bluey-orig.png` — sample images
- All `test_*.svg` outputs from prior sessions

## Warnings (Week 1, still relevant)

- The pre-existing uncommitted changes (`.opencode/`, `AGENTS.md`,
  `HANDOFF.md`, `TASKS.md`, `memory_data/`) are NOT part of v1.0.0. When
  merging, they should be reviewed separately and may need to be committed
  as a "chore: sync Boomerang plugin state" commit.
- The user mentioned they will change the author and repo URL
  placeholders later. Easy global find-replace: `png2svg contributors`
  and `github.com/png2svg/png2svg`.
- The golden file is small (441KB) for fast CI; if someone re-runs with
  default params, the file will be ~1.5MB. The test uses specific params
  intentionally.
