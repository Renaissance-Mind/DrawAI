import json
import os
import subprocess
import sys
from pathlib import Path

import tomllib


REPO_ROOT = Path(__file__).resolve().parents[1]


def _subprocess_env() -> dict[str, str]:
    env = dict(os.environ)
    src_path = str(REPO_ROOT / "src")
    env["PYTHONPATH"] = src_path if not env.get("PYTHONPATH") else f"{src_path}{os.pathsep}{env['PYTHONPATH']}"
    return env


def test_python_module_and_cli_help_use_drawai_project_name():
    result = subprocess.run(
        [sys.executable, "-m", "drawai.cli", "--help"],
        cwd=REPO_ROOT,
        env=_subprocess_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "Run the DrawAI SVG pipeline." in result.stdout
    legacy_help = "Run the " + "BoxIR" + " SVG pipeline."
    assert legacy_help not in result.stdout


def test_explainer_help_uses_drawai_project_name():
    result = subprocess.run(
        [sys.executable, "-m", "drawai.explainer_app", "--help"],
        cwd=REPO_ROOT,
        env=_subprocess_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "DrawAI output explainer frontend" in result.stdout
    legacy_help = "BoxIR" + " output explainer frontend"
    assert legacy_help not in result.stdout


def test_config_summary_uses_drawai_schema_namespace():
    from drawai.cli import dry_run_config_summary
    from drawai.config import load_drawai_config

    cfg = load_drawai_config("configs/drawai/config.yaml", validate_input_exists=False)

    summary = dry_run_config_summary(cfg)

    assert summary["schema"] == "drawai.pipeline_config_summary.v1"


def test_public_config_profile_uses_drawai_name():
    assert (REPO_ROOT / "configs/drawai/config.yaml").is_file()
    assert not (REPO_ROOT / "configs/box_ir_svg").exists()


def test_public_python_api_uses_drawai_pipeline_names_only():
    import drawai
    import drawai.config as drawai_config
    import drawai.pipeline as drawai_pipeline

    assert hasattr(drawai, "run_drawai_pipeline")
    assert hasattr(drawai, "run_drawai_pipeline_from_stage")
    assert hasattr(drawai_config, "load_drawai_config")
    assert hasattr(drawai_config, "DrawAiPipelineConfig")
    assert hasattr(drawai_pipeline, "run_drawai_pipeline")
    assert hasattr(drawai_pipeline, "run_drawai_pipeline_from_stage")
    assert "run_drawai_pipeline" in drawai.__all__
    assert "run_drawai_pipeline_from_stage" in drawai.__all__
    assert not hasattr(drawai, "run_box_ir_pipeline")
    assert not hasattr(drawai_config, "load_box_ir_config")
    assert not hasattr(drawai_config, "BoxIrPipelineConfig")
    assert not hasattr(drawai_pipeline, "run_box_ir_pipeline")
    assert not hasattr(drawai_pipeline, "run_box_ir_pipeline_from_stage")


def test_console_entrypoint_uses_drawai_schema_namespace():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "drawai.cli",
            "--config",
            "configs/drawai/config.yaml",
            "--dry-run-config",
        ],
        cwd=REPO_ROOT,
        env=_subprocess_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema"] == "drawai.pipeline_config_summary.v1"
    assert payload["input"]["output_dir"].endswith("results/drawai_svg/config")


def test_pyproject_exposes_drawai_only_console_scripts():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    scripts = pyproject["project"]["scripts"]

    assert scripts == {
        "drawai": "drawai.cli:main",
        "drawai-explainer": "drawai.explainer_app:main",
        "drawai-local-services": "drawai.local_services:main",
        "drawai-workbench-api": "drawai.workbench.api:main",
        "drawai-dataset": "drawai_evaluation.dataset:main",
        "drawai-evaluate": "drawai_evaluation.batch:main",
        "drawai-rubric": "drawai_evaluation.rubric:main",
        "drawai-merge": "drawai_evaluation.merge:main",
        "drawai-scores": "drawai_evaluation.scores:main",
    }


def test_local_runtime_uses_drawai_runtime_root(monkeypatch):
    from drawai.local_runtime import LocalRuntimePaths

    monkeypatch.delenv("DRAWAI_LOCAL_RUNTIME_ROOT", raising=False)

    paths = LocalRuntimePaths.from_root()

    assert paths.runtime_root.name == "drawai_runtime"
