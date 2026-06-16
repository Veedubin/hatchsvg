#!/usr/bin/env bash
# Verify all 3 notebooks execute end-to-end without errors.
#
# This is the heavy CI gate for the notebook suite. It:
#   1. Re-generates the .ipynb files from scripts/build_notebooks.py
#   2. Formats the source notebooks (matches project quote style)
#   3. Executes each notebook via jupyter nbconvert
#   4. Formats the executed notebooks
#   5. Strips Jupyter's per-cell execution timestamps (byte-stability)
#   6. Checks the output notebooks for Python errors
#
# The smoke tests in tests/integration/test_notebook_helpers.py cover
# the lightweight case (helpers can be imported, basic functions work).
# This script covers the heavyweight case (notebook cells actually run).
#
# The Python post-processing (steps 5 and 6) lives in
# scripts/verify_notebooks_helpers.py for readability and testability.
#
# Usage:  bash scripts/verify_notebooks.sh
#
# Exit code 0 = all notebooks executed without error.
# Exit code non-zero = at least one notebook raised an exception.

set -euo pipefail

# Get to repo root regardless of where this is run from
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

NOTEBOOKS=(
    "notebooks/quickstart_executed.ipynb"
    "notebooks/explore_executed.ipynb"
    "notebooks/craft_executed.ipynb"
)

echo "== Re-generating notebooks =="
.venv/bin/python scripts/build_notebooks.py --out-dir notebooks

echo ""
echo "== Formatting source notebooks =="
# Ruff's per-file-ignores apply to lint but not to format. Run format
# after build so the generated cell source matches the project quote
# style (double quotes, per [tool.ruff.format] in pyproject.toml).
.venv/bin/ruff format \
    notebooks/quickstart.ipynb \
    notebooks/explore.ipynb \
    notebooks/craft.ipynb \
    >/dev/null

echo ""
echo "== Executing notebooks =="
.venv/bin/jupyter nbconvert --to notebook \
    --execute notebooks/quickstart.ipynb \
    --output quickstart_executed.ipynb \
    --ExecutePreprocessor.timeout=120 \
    --ExecutePreprocessor.kernel_name=python3
.venv/bin/jupyter nbconvert --to notebook \
    --execute notebooks/explore.ipynb \
    --output explore_executed.ipynb \
    --ExecutePreprocessor.timeout=300 \
    --ExecutePreprocessor.kernel_name=python3
.venv/bin/jupyter nbconvert --to notebook \
    --execute notebooks/craft.ipynb \
    --output craft_executed.ipynb \
    --ExecutePreprocessor.timeout=300 \
    --ExecutePreprocessor.kernel_name=python3

echo ""
echo "== Formatting executed notebooks =="
# Match the project quote style. nbconvert's serialization uses
# different defaults; this normalizes them.
.venv/bin/ruff format "${NOTEBOOKS[@]}" >/dev/null

echo ""
echo "== Stripping execution timestamps for byte-stable outputs =="
# Jupyter's kernel manager stamps every executed cell with timestamps
# in cell.metadata.execution (iopub.execute_input, iopub.status.busy,
# iopub.status.idle, shell.execute_reply). These make the executed
# notebook differ on every re-run, producing meaningless diffs in
# PRs. The strip step makes the committed executed notebooks
# byte-stable on re-execution.
.venv/bin/python scripts/verify_notebooks_helpers.py strip "${NOTEBOOKS[@]}"

echo ""
echo "== Checking for errors in cell outputs =="
.venv/bin/python scripts/verify_notebooks_helpers.py check "${NOTEBOOKS[@]}"

echo ""
echo "OK: all 3 notebooks executed without errors"
