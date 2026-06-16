"""Helpers for scripts/verify_notebooks.sh.

This module contains the two post-execution checks that the verify
script runs after `nbconvert --execute`:

1. ``check_for_errors`` — verify no cell raised a Python exception
2. ``strip_execution_timestamps`` — remove Jupyter's per-cell
   timestamps so the executed notebook is byte-stable on re-execution

Extracted from inline ``python - <<PY`` heredocs so the logic is
readable, testable, and re-usable.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Timestamp keys that Jupyter's kernel manager writes into every
# executed cell's metadata.execution dict. They make the executed
# notebook differ on every re-run, so we strip them post-execution.
TIMESTAMP_KEYS: tuple[str, ...] = (
    "iopub.execute_input",
    "iopub.status.busy",
    "iopub.status.idle",
    "shell.execute_reply",
)

# Notebook-level date keys that nbformat adds; also removed for the
# same reason as the per-cell timestamps.
NOTEBOOK_DATE_KEYS: tuple[str, ...] = (
    "execution_count",
    "last_executed",
)


def check_for_errors(nb_path: str | Path) -> list[tuple[int, str, str]]:
    """Return a list of (cell_index, ename, evalue) for any error outputs.

    Empty list means the notebook executed cleanly. Used by the verify
    script to fail the CI gate when a cell raises a Python exception.
    """
    nb_path = Path(nb_path)
    nb = json.loads(nb_path.read_text())
    errors: list[tuple[int, str, str]] = []
    for i, cell in enumerate(nb.get("cells", [])):
        for output in cell.get("outputs", []):
            if output.get("output_type") == "error":
                errors.append((i, output.get("ename", "?"), output.get("evalue", "?")))
    return errors


def strip_execution_timestamps(nb_path: str | Path) -> int:
    """Remove Jupyter's per-cell execution timestamps from ``nb_path``.

    Writes the cleaned notebook back to the same path (in-place).
    Returns the number of timestamp keys removed.
    """
    p = Path(nb_path)
    nb = json.loads(p.read_text())
    stripped = 0
    for cell in nb.get("cells", []):
        meta = cell.get("metadata", {})
        exec_meta = meta.get("execution", {})
        for k in TIMESTAMP_KEYS:
            if k in exec_meta:
                del exec_meta[k]
                stripped += 1
        if not exec_meta:
            meta.pop("execution", None)
    for k in NOTEBOOK_DATE_KEYS:
        nb.get("metadata", {}).pop(k, None)
    p.write_text(json.dumps(nb, indent=1) + "\n")
    return stripped


def main() -> int:
    """CLI: ``python -m verify_notebooks_helpers <subcommand> <paths>...``

    Subcommands:
      check    — check each notebook for error outputs (exit 1 if any)
      strip    — strip execution timestamps from each notebook

    Used by scripts/verify_notebooks.sh.
    """
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    subcommand, *paths = sys.argv[1:]
    if subcommand == "check":
        failed = 0
        for p in paths:
            errs = check_for_errors(p)
            if errs:
                failed += 1
                print(f"  {p}: {len(errs)} error(s)")
                for i, ename, evalue in errs:
                    print(f"    cell {i}: {ename}: {evalue}")
            else:
                print(f"  {p}: OK")
        return 1 if failed else 0
    if subcommand == "strip":
        total = 0
        for p in paths:
            n = strip_execution_timestamps(p)
            total += n
            print(f"  {p}: stripped {n} timestamp keys")
        return 0
    print(f"Unknown subcommand: {subcommand!r}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
