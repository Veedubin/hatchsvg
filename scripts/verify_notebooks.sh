#!/usr/bin/env bash
# Verify all 3 notebooks execute end-to-end without errors.
#
# This is the heavy CI gate for the notebook suite. It:
#   1. Re-generates the .ipynb files from scripts/build_notebooks.py
#   2. Executes each notebook via jupyter nbconvert
#   3. Checks the output notebooks for Python errors
#
# The smoke tests in tests/integration/test_notebook_helpers.py cover
# the lightweight case (helpers can be imported, basic functions work).
# This script covers the heavyweight case (notebook cells actually run).
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

echo "== Re-generating notebooks =="
.venv/bin/python scripts/build_notebooks.py --out-dir notebooks

echo ""
echo "== Executing quickstart.ipynb =="
.venv/bin/jupyter nbconvert --to notebook \
    --execute notebooks/quickstart.ipynb \
    --output quickstart_executed.ipynb \
    --ExecutePreprocessor.timeout=120 \
    --ExecutePreprocessor.kernel_name=python3

echo ""
echo "== Executing explore.ipynb =="
.venv/bin/jupyter nbconvert --to notebook \
    --execute notebooks/explore.ipynb \
    --output explore_executed.ipynb \
    --ExecutePreprocessor.timeout=300 \
    --ExecutePreprocessor.kernel_name=python3

echo ""
echo "== Executing craft.ipynb =="
.venv/bin/jupyter nbconvert --to notebook \
    --execute notebooks/craft.ipynb \
    --output craft_executed.ipynb \
    --ExecutePreprocessor.timeout=300 \
    --ExecutePreprocessor.kernel_name=python3

echo ""
echo "== Checking for errors in cell outputs =="
# nbformat writes errors to cell outputs as 'error' or 'evalue'. We check
# each executed notebook for any error output.
ERRORS=0
for nb in notebooks/quickstart_executed.ipynb notebooks/explore_executed.ipynb notebooks/craft_executed.ipynb; do
    .venv/bin/python - "$nb" <<'PY'
import json
import sys
nb_path = sys.argv[1]
with open(nb_path) as f:
    nb = json.load(f)
errors = []
for i, cell in enumerate(nb.get("cells", [])):
    for output in cell.get("outputs", []):
        if output.get("output_type") == "error":
            errors.append((i, output.get("ename", "?"), output.get("evalue", "?")))
if errors:
    print(f"  {nb_path}: {len(errors)} error(s)")
    for i, ename, evalue in errors:
        print(f"    cell {i}: {ename}: {evalue}")
    sys.exit(1)
else:
    print(f"  {nb_path}: OK")
PY
    if [ $? -ne 0 ]; then
        ERRORS=$((ERRORS + 1))
    fi
done

if [ $ERRORS -gt 0 ]; then
    echo ""
    echo "FAIL: $ERRORS notebook(s) had errors"
    exit 1
fi

echo ""
echo "== Stripping execution timestamps for byte-stable outputs =="
# Jupyter's kernel manager stamps every executed cell with timestamps in
# cell.metadata.execution (iopub.execute_input, iopub.status.busy, etc.).
# These make the executed notebook differ on every re-run, producing
# meaningless diffs in PRs. We strip them now so the committed executed
# notebooks are byte-stable on re-execution.
.venv/bin/python - <<'PY'
import json
from pathlib import Path

# Timestamp keys that Jupyter adds per-executed-cell
TIMESTAMP_KEYS = (
    "iopub.execute_input",
    "iopub.status.busy",
    "iopub.status.idle",
    "shell.execute_reply",
)

for nb_path in [
    "notebooks/quickstart_executed.ipynb",
    "notebooks/explore_executed.ipynb",
    "notebooks/craft_executed.ipynb",
]:
    p = Path(nb_path)
    nb = json.loads(p.read_text())
    stripped = 0
    for cell in nb.get("cells", []):
        # Timestamps live in cell.metadata.execution (one entry per cell)
        meta = cell.get("metadata", {})
        exec_meta = meta.get("execution", {})
        for k in TIMESTAMP_KEYS:
            if k in exec_meta:
                del exec_meta[k]
                stripped += 1
        if not exec_meta:
            meta.pop("execution", None)
    # Also strip the notebook-level dates that nbformat adds
    for k in ("execution_count", "last_executed"):
        nb.get("metadata", {}).pop(k, None)
    p.write_text(json.dumps(nb, indent=1) + "\n")
    print(f"  {nb_path}: stripped {stripped} timestamp keys")
PY

echo ""
echo "OK: all 3 notebooks executed without errors"
