import csv
import json
import os
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

import yaml
import pytest
from PIL import Image

from drawai.experiment_artifacts import next_timestamped_run_dir
from scripts.run_drawai_experiment import (
    CaseSpec,
    _ensure_host_home_env,
    _ensure_local_codex_gateway_if_needed,
    _finalize_case_status_row,
    _validate_codex_python_sdk_auth_if_needed,
)


def test_next_timestamped_run_dir_uses_date_time_and_slug(tmp_path: Path):
    run_root = tmp_path / "runs"

    run_dir = next_timestamped_run_dir(
        run_root,
        slug="Two Sample",
        now=__import__("datetime").datetime(2026, 5, 28, 12, 34, 56),
    )

    assert run_dir == run_root.resolve() / "20260528" / "123456_two_sample"


def test_next_timestamped_run_dir_adds_suffix_on_collision(tmp_path: Path):
    run_root = tmp_path / "runs"
    (run_root / "20260528" / "123456_probe").mkdir(parents=True)

    run_dir = next_timestamped_run_dir(
        run_root,
        slug="probe",
        now=__import__("datetime").datetime(2026, 5, 28, 12, 34, 56),
    )

    assert run_dir == run_root.resolve() / "20260528" / "123456_probe_02"


def test_run_drawai_experiment_dry_run_writes_manifest_backed_layout(tmp_path: Path):
    image1 = tmp_path / "ref_ref_32_Beyond_Pairwise_Connections_Extracting.jpg"
    image2 = tmp_path / "test_test_170_Normalization_in_Attention_Dynamics.jpg"
    Image.new("RGB", (12, 8), "white").save(image1)
    Image.new("RGB", (10, 10), "white").save(image2)
    base_config = tmp_path / "base.yaml"
    base_config.write_text(
        """
input:
  image: placeholder.png
  output_dir: placeholder_out
sam3:
  base_url: http://127.0.0.1:18080
ocr:
  provider: remote_paddleocr
  remote_paddleocr:
    base_url: http://127.0.0.1:18080
svg_to_ppt:
  enabled: true
  export_pptx: true
""",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_drawai_experiment.py",
            "--images",
            str(image1),
            str(image2),
            "--run-name",
            "two sample",
            "--expected-outcome",
            "dry-run manifest check",
            "--base-config",
            str(base_config),
            "--run-root",
            str(tmp_path / "runs"),
            "--dry-run",
        ],
        cwd=Path(__file__).resolve().parents[3],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    run_dir_line = next(line for line in result.stdout.splitlines() if line.startswith("run_dir: "))
    run_dir = Path(run_dir_line.removeprefix("run_dir: "))

    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == "drawai.run_manifest.v1"
    assert manifest["mode"] == "batch"
    assert manifest["case_count"] == 2
    assert manifest["expected_outcome"] == "dry-run manifest check"

    selected = [
        json.loads(line)
        for line in (run_dir / "selected_cases.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert [item["case_id"] for item in selected] == ["case_001", "case_002"]
    assert selected[0]["config_path"] == "configs/case_001.yaml"
    assert selected[0]["output_dir"].startswith("outputs/case_001_")

    case_config = yaml.safe_load((run_dir / "configs" / "case_001.yaml").read_text(encoding="utf-8"))
    assert case_config["input"]["image"] == str(image1.resolve())
    assert Path(case_config["input"]["output_dir"]).is_absolute()
    assert "configs/runs" not in case_config["input"]["output_dir"]

    case_manifest = json.loads(
        next((run_dir / "outputs").glob("case_001_*/case_manifest.json")).read_text(encoding="utf-8")
    )
    assert case_manifest["schema"] == "drawai.case_manifest.v1"
    assert case_manifest["status"] == "planned"
    assert case_manifest["artifacts"]["semantic_svg"] == "svg/semantic.svg"
    assert case_manifest["artifacts"]["rendered_png"] == "svg/rendered.png"
    assert case_manifest["artifacts"]["svg_to_pptx"] == "svg_to_ppt/semantic.svg_to_ppt.pptx"

    with (run_dir / "reports" / "run_status.csv").open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["status"] for row in rows] == ["planned", "planned"]

    summary = json.loads((run_dir / "reports" / "run_summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "planned"
    assert summary["dry_run"] is True


def test_local_inprocess_dry_run_defaults_public_stages_to_sequential(tmp_path: Path):
    image = tmp_path / "input.jpg"
    Image.new("RGB", (12, 8), "white").save(image)
    base_config = tmp_path / "base.yaml"
    base_config.write_text(
        """
input:
  image: placeholder.png
  output_dir: placeholder_out
sam3:
  base_url: http://127.0.0.1:18080
ocr:
  provider: remote_paddleocr
  remote_paddleocr:
    base_url: http://127.0.0.1:18080
svg_to_ppt:
  enabled: true
  export_pptx: true
""",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_drawai_experiment.py",
            "--local-inprocess",
            "--images",
            str(image),
            "--run-name",
            "local inprocess dry run",
            "--base-config",
            str(base_config),
            "--run-root",
            str(tmp_path / "runs"),
            "--dry-run",
        ],
        cwd=Path(__file__).resolve().parents[3],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    run_dir_line = next(line for line in result.stdout.splitlines() if line.startswith("run_dir: "))
    run_dir = Path(run_dir_line.removeprefix("run_dir: "))
    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["local_runtime"]["sam3_device"] == "cpu"
    assert manifest["local_runtime"]["rmbg_device"] == "cpu"
    assert manifest["local_runtime"]["paddle_device"] == "cpu"
    assert manifest["local_runtime"]["public_stage_parallel"] is False

    case_manifest = json.loads(
        next((run_dir / "outputs").glob("case_001_*/case_manifest.json")).read_text(encoding="utf-8")
    )
    assert "--sequential" in case_manifest["command"]


def test_local_inprocess_codex_python_sdk_config_does_not_ensure_gateway(monkeypatch, tmp_path: Path):
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: calls.append((args, kwargs)))
    args = Namespace(
        local_inprocess=True,
        dry_run=False,
        skip_local_codex_gateway_ensure=False,
        local_runtime_root=str(tmp_path / "runtime"),
    )
    base_config = {
        "svg": {"generation_backend": "codex_python_sdk_controlled"},
        "model_runtime": {
            "provider": "codex-python-sdk",
            "connection_id": "codex-python-sdk-controlled",
            "base_url": "",
        },
    }

    _ensure_local_codex_gateway_if_needed(args, tmp_path, base_config)

    assert calls == []


def test_ensure_host_home_env_records_home_without_overwriting_existing_value(monkeypatch, tmp_path: Path):
    host_home = tmp_path / "host_home"
    host_home.mkdir()
    monkeypatch.setenv("HOME", str(host_home))
    monkeypatch.delenv("DRAWAI_HOST_HOME", raising=False)

    _ensure_host_home_env()

    assert os.environ["DRAWAI_HOST_HOME"] == str(host_home)

    monkeypatch.setenv("HOME", str(tmp_path / "changed_home"))
    _ensure_host_home_env()

    assert os.environ["DRAWAI_HOST_HOME"] == str(host_home)


def test_codex_python_sdk_auth_preflight_accepts_chatgpt_auth_with_configured_model(monkeypatch, tmp_path: Path):
    host_home = tmp_path / "host_home"
    auth_dir = host_home / ".codex"
    auth_dir.mkdir(parents=True)
    (auth_dir / "auth.json").write_text(
        json.dumps({"auth_mode": "chatgpt", "tokens": {"access_token": "redacted"}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("DRAWAI_HOST_HOME", str(host_home))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    _validate_codex_python_sdk_auth_if_needed(_codex_python_sdk_base_config(model_name="gpt-5.5"))


def test_codex_python_sdk_auth_preflight_accepts_chatgpt_auth_with_default_model(monkeypatch, tmp_path: Path):
    host_home = tmp_path / "host_home"
    auth_dir = host_home / ".codex"
    auth_dir.mkdir(parents=True)
    (auth_dir / "auth.json").write_text(
        json.dumps({"auth_mode": "chatgpt", "tokens": {"access_token": "redacted"}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("DRAWAI_HOST_HOME", str(host_home))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    _validate_codex_python_sdk_auth_if_needed(_codex_python_sdk_base_config())


def test_codex_python_sdk_auth_preflight_accepts_openai_api_key_env(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("DRAWAI_HOST_HOME", str(tmp_path / "host_home"))
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")

    _validate_codex_python_sdk_auth_if_needed(_codex_python_sdk_base_config())


def test_final_status_requires_required_artifacts(tmp_path: Path):
    case = _sample_case_spec(tmp_path)
    (case.output_dir / "reports").mkdir(parents=True)
    (case.output_dir / "reports" / "pipeline_summary.json").write_text(
        json.dumps({"status": "ok", "stages": ["svg_to_ppt_exported"]}),
        encoding="utf-8",
    )
    (case.output_dir / "reports" / "stage_status.json").write_text(
        json.dumps({"latest_stage": "completed", "latest_status": "ok"}),
        encoding="utf-8",
    )

    row = _finalize_case_status_row(case, status="completed", exitcode=0, duration_seconds=1.25)

    assert row["status"] == "failed"
    assert row["exitcode"] == 1
    assert row["failed_stage"] == "artifact_validation"
    assert "missing required artifacts" in row["notes"]
    assert "svg/semantic.svg" in row["notes"]
    assert "svg/rendered.png" in row["notes"]
    assert "svg_to_ppt/semantic.svg_to_ppt.pptx" in row["notes"]


def test_final_status_rejects_failed_stage_status_even_with_artifacts(tmp_path: Path):
    case = _sample_case_spec(tmp_path)
    _write_success_artifacts(case.output_dir)
    (case.output_dir / "reports" / "pipeline_summary.json").write_text(
        json.dumps({"status": "ok", "stages": ["svg_to_ppt_exported"]}),
        encoding="utf-8",
    )
    (case.output_dir / "reports" / "stage_status.json").write_text(
        json.dumps({"latest_stage": "svg_generated", "latest_status": "failed"}),
        encoding="utf-8",
    )

    row = _finalize_case_status_row(case, status="completed", exitcode=0, duration_seconds=2.0)

    assert row["status"] == "failed"
    assert row["exitcode"] == 1
    assert row["failed_stage"] == "svg_generated"
    assert "stage_status latest_status=failed" in row["notes"]


def test_final_status_accepts_completed_case_with_artifacts_and_ok_reports(tmp_path: Path):
    case = _sample_case_spec(tmp_path)
    _write_success_artifacts(case.output_dir)
    (case.output_dir / "reports" / "pipeline_summary.json").write_text(
        json.dumps({"status": "ok", "stages": ["svg_to_ppt_exported"]}),
        encoding="utf-8",
    )
    (case.output_dir / "reports" / "stage_status.json").write_text(
        json.dumps({"latest_stage": "completed", "latest_status": "ok"}),
        encoding="utf-8",
    )
    (case.output_dir / "reports" / "svg_validation_report.json").write_text(
        json.dumps({"status": "ok", "issues": []}),
        encoding="utf-8",
    )
    (case.output_dir / "reports" / "svg_to_ppt_export_report.json").write_text(
        json.dumps({"status": "ok", "issues": []}),
        encoding="utf-8",
    )

    row = _finalize_case_status_row(case, status="completed", exitcode=0, duration_seconds=3.0)

    assert row["status"] == "completed"
    assert row["exitcode"] == 0
    assert row["failed_stage"] == ""
    assert row["notes"] == ""


def _sample_case_spec(tmp_path: Path) -> CaseSpec:
    output_dir = tmp_path / "outputs" / "case_001_sample"
    output_dir.mkdir(parents=True)
    return CaseSpec(
        case_id="case_001",
        case_slug="sample",
        source_image=tmp_path / "input.png",
        source_sha256="abc123",
        config_path=tmp_path / "config.yaml",
        output_dir=output_dir,
        stdout_log=tmp_path / "logs" / "case_001.stdout.json",
        stderr_log=tmp_path / "logs" / "case_001.stderr.log",
        expected_result="ok",
    )


def _write_success_artifacts(output_dir: Path) -> None:
    (output_dir / "svg").mkdir(parents=True, exist_ok=True)
    (output_dir / "svg_to_ppt").mkdir(parents=True, exist_ok=True)
    (output_dir / "reports").mkdir(parents=True, exist_ok=True)
    (output_dir / "svg" / "semantic.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"></svg>',
        encoding="utf-8",
    )
    (output_dir / "svg" / "rendered.png").write_bytes(b"png")
    (output_dir / "svg_to_ppt" / "semantic.svg_to_ppt.pptx").write_bytes(b"pptx")


def _codex_python_sdk_base_config(model_name: str = "") -> dict[str, dict[str, str]]:
    return {
        "svg": {"generation_backend": "codex_python_sdk_controlled"},
        "model_runtime": {"provider": "codex-python-sdk", "model_name": model_name},
    }
