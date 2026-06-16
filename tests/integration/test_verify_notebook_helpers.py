"""Unit tests for scripts/verify_notebooks_helpers.py.

This module contains the post-execution checks used by
scripts/verify_notebooks.sh. These tests verify the helpers work
correctly in isolation, without needing to actually execute
notebooks.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

# Project root (parent of tests/)
PROJECT_ROOT = Path(__file__).parent.parent.parent
HELPERS_SCRIPT = PROJECT_ROOT / "scripts" / "verify_notebooks_helpers.py"

from scripts.verify_notebooks_helpers import (  # noqa: E402 — sys.path set by conftest
    check_for_errors,
    strip_execution_timestamps,
)


def _make_notebook(
    tmp_path: Path,
    *,
    cell_id: str = "test-cell-00",
    outputs: list | None = None,
    metadata: dict | None = None,
) -> Path:
    """Write a minimal notebook JSON to tmp_path and return its path."""
    nb = {
        "cells": [
            {
                "cell_type": "code",
                "id": cell_id,
                "metadata": metadata or {},
                "execution_count": 1,
                "source": ["print('hi')"],
                "outputs": outputs or [],
            }
        ],
        "metadata": {
            "kernelspec": {"name": "python3", "display_name": "Python 3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    path = tmp_path / "test.ipynb"
    path.write_text(json.dumps(nb))
    return path


class TestCheckForErrors:
    """``check_for_errors`` returns a list of error tuples."""

    def test_clean_notebook_returns_empty_list(self, tmp_path):

        nb = _make_notebook(tmp_path, outputs=[])
        assert check_for_errors(nb) == []

    def test_text_output_is_not_an_error(self, tmp_path):

        nb = _make_notebook(
            tmp_path,
            outputs=[{"output_type": "stream", "name": "stdout", "text": "hi\n"}],
        )
        assert check_for_errors(nb) == []

    def test_error_output_is_caught(self, tmp_path):

        nb = _make_notebook(
            tmp_path,
            outputs=[{"output_type": "error", "ename": "ValueError", "evalue": "bad"}],
        )
        errors = check_for_errors(nb)
        assert len(errors) == 1
        cell_idx, ename, evalue = errors[0]
        assert cell_idx == 0
        assert ename == "ValueError"
        assert evalue == "bad"

    def test_multiple_cells_with_one_error(self, tmp_path):

        nb = {
            "cells": [
                {
                    "cell_type": "code",
                    "id": "c1",
                    "metadata": {},
                    "outputs": [],
                },
                {
                    "cell_type": "code",
                    "id": "c2",
                    "metadata": {},
                    "outputs": [{"output_type": "error", "ename": "RuntimeError", "evalue": "oops"}],
                },
            ],
            "metadata": {},
        }
        path = tmp_path / "two.ipynb"
        path.write_text(json.dumps(nb))

        errors = check_for_errors(path)
        assert len(errors) == 1
        assert errors[0][0] == 1
        assert errors[0][1] == "RuntimeError"

    def test_missing_outputs_key_treated_as_empty(self, tmp_path):

        # Cell with no "outputs" key at all
        nb = {"cells": [{"cell_type": "code", "id": "c1", "metadata": {}}], "metadata": {}}
        path = tmp_path / "no_outputs.ipynb"
        path.write_text(json.dumps(nb))
        assert check_for_errors(path) == []


class TestStripExecutionTimestamps:
    """``strip_execution_timestamps`` removes Jupyter's per-cell metadata."""

    def test_strips_cell_execution_block(self, tmp_path):

        nb_path = _make_notebook(
            tmp_path,
            metadata={
                "execution": {
                    "iopub.execute_input": "2026-01-01T00:00:00.000Z",
                    "iopub.status.busy": "2026-01-01T00:00:00.000Z",
                    "iopub.status.idle": "2026-01-01T00:00:00.000Z",
                    "shell.execute_reply": "2026-01-01T00:00:00.000Z",
                }
            },
        )
        n = strip_execution_timestamps(nb_path)
        assert n == 4
        # Reload and verify
        nb = json.loads(nb_path.read_text())
        assert "execution" not in nb["cells"][0]["metadata"]

    def test_strips_notebook_level_date_keys(self, tmp_path):

        nb = {
            "cells": [],
            "metadata": {
                "execution_count": 5,
                "last_executed": "2026-01-01T00:00:00.000Z",
                "kernelspec": {"name": "python3"},
            },
        }
        path = tmp_path / "nb.ipynb"
        path.write_text(json.dumps(nb))
        strip_execution_timestamps(path)
        nb = json.loads(path.read_text())
        assert "execution_count" not in nb["metadata"]
        assert "last_executed" not in nb["metadata"]
        assert nb["metadata"]["kernelspec"] == {"name": "python3"}  # preserved

    def test_idempotent(self, tmp_path):

        nb_path = _make_notebook(
            tmp_path,
            metadata={
                "execution": {
                    "iopub.execute_input": "2026-01-01T00:00:00.000Z",
                }
            },
        )
        first = strip_execution_timestamps(nb_path)
        second = strip_execution_timestamps(nb_path)
        assert first == 1
        assert second == 0  # nothing left to strip

    def test_preserves_other_metadata(self, tmp_path):

        nb_path = _make_notebook(
            tmp_path,
            metadata={
                "execution": {"iopub.execute_input": "2026-01-01T00:00:00.000Z"},
                "tags": ["important"],
                "user_specific": {"x": 1},
            },
        )
        strip_execution_timestamps(nb_path)
        nb = json.loads(nb_path.read_text())
        meta = nb["cells"][0]["metadata"]
        assert meta["tags"] == ["important"]
        assert meta["user_specific"] == {"x": 1}


class TestCLISubprocess:
    """The script's CLI (used by verify_notebooks.sh) works correctly."""

    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(HELPERS_SCRIPT), *args],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_check_subcommand_clean_notebook(self, tmp_path):
        nb = _make_notebook(tmp_path, outputs=[])
        result = self._run("check", str(nb))
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "OK" in result.stdout

    def test_check_subcommand_with_error(self, tmp_path):
        nb = _make_notebook(
            tmp_path,
            outputs=[{"output_type": "error", "ename": "E", "evalue": "v"}],
        )
        result = self._run("check", str(nb))
        assert result.returncode == 1
        assert "1 error" in result.stdout

    def test_strip_subcommand(self, tmp_path):
        nb = _make_notebook(
            tmp_path,
            metadata={
                "execution": {
                    "iopub.execute_input": "2026-01-01T00:00:00.000Z",
                    "iopub.status.busy": "2026-01-01T00:00:00.000Z",
                }
            },
        )
        result = self._run("strip", str(nb))
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "stripped 2 timestamp keys" in result.stdout

    def test_no_args_prints_usage_and_exits_2(self):
        result = self._run()
        assert result.returncode == 2

    def test_unknown_subcommand_exits_2(self, tmp_path):
        result = self._run("frobnicate", str(tmp_path / "x.ipynb"))
        assert result.returncode == 2


class TestByteStability:
    """The strip operation should be byte-stable on re-execution.

    This is the property that ``verify_notebooks.sh`` relies on. Two
    successive ``strip`` calls on the same notebook (after a
    ``nbconvert`` between them) should produce the same JSON.
    """

    def test_two_strips_produce_same_content(self, tmp_path):

        # Simulate an executed notebook (with one timestamp)
        nb_path = _make_notebook(
            tmp_path,
            metadata={
                "execution": {
                    "iopub.execute_input": "2026-01-01T00:00:00.000Z",
                }
            },
        )
        strip_execution_timestamps(nb_path)
        first = nb_path.read_text()
        # Re-simulate an execution (add the timestamp back)
        nb = json.loads(first)
        nb["cells"][0]["metadata"]["execution"] = {
            "iopub.execute_input": "2099-12-31T23:59:59.999Z",
        }
        nb_path.write_text(json.dumps(nb))
        # Strip again
        strip_execution_timestamps(nb_path)
        second = nb_path.read_text()
        assert first == second, "Re-execution should produce byte-identical notebook"
