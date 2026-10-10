"""Run the standalone document regression suite through pytest as well."""

from pathlib import Path
import subprocess
import sys


def test_standalone_document_real_file_checks():
    script = (
        Path(__file__).resolve().parents[1]
        / "skills/drawai-image2ppt/scripts/check_document.py"
    )
    result = subprocess.run(
        [sys.executable, str(script)], capture_output=True, text=True, timeout=180
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_standalone_document_workflow_regressions():
    script = (
        Path(__file__).resolve().parents[1]
        / "skills/drawai-image2ppt/scripts/check_workflows.py"
    )
    result = subprocess.run(
        [sys.executable, str(script)], capture_output=True, text=True, timeout=180
    )
    assert result.returncode == 0, result.stdout + result.stderr
