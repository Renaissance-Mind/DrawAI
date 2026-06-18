import json
import subprocess
import sys
import tomllib
from pathlib import Path

from drawai.local_cli import (
    _check_codex_auth,
    _check_codex_executable,
    _check_codex_sdk_auth_connectivity,
    _check_runtime_python_import,
    _codex_auth_candidate_paths,
    _torch_backend_from_cuda_version,
)


def test_openai_codex_dependency_is_project_and_runtime_dependency():
    repo_root = Path(__file__).resolve().parents[3]
    pyproject = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))
    bootstrap_text = (repo_root / "scripts" / "bootstrap_drawai_local_runtime.sh").read_text(encoding="utf-8")
    lock_text = (repo_root / "uv.lock").read_text(encoding="utf-8")

    assert "openai-codex" in pyproject["project"]["dependencies"]
    assert "pydantic<2.14" in pyproject["project"]["dependencies"]
    assert pyproject["tool"]["uv"]["prerelease"] == "allow"
    assert 'name = "openai-codex"' in lock_text
    assert 'name = "openai-codex-cli-bin"' in lock_text
    assert "manylinux_2_17_x86_64" in lock_text
    assert "--prerelease=allow" in bootstrap_text
    assert "installing Codex Python SDK" not in bootstrap_text
    assert "openai-codex \\" not in bootstrap_text


def test_torch_runtime_install_avoids_cu13_pinned_default():
    repo_root = Path(__file__).resolve().parents[3]
    bootstrap_text = (repo_root / "scripts" / "bootstrap_drawai_local_runtime.sh").read_text(encoding="utf-8")

    assert "TORCH_SPEC=\"${DRAWAI_TORCH_SPEC:-torch>=2.4,<2.12}\"" in bootstrap_text
    assert "TORCHVISION_SPEC=\"${DRAWAI_TORCHVISION_SPEC:-torchvision>=0.19,<0.27}\"" in bootstrap_text
    assert "TORCH_BACKEND=\"${DRAWAI_TORCH_BACKEND:-cpu}\"" in bootstrap_text
    assert "detect_torch_backend()" in bootstrap_text
    assert "--reinstall-package torch --reinstall-package torchvision" in bootstrap_text
    assert "torch==2.12.0" not in bootstrap_text
    assert "torchvision==0.27.0" not in bootstrap_text


def test_torch_backend_from_cuda_version_selects_compatible_wheel():
    assert _torch_backend_from_cuda_version("13.0") == "cu130"
    assert _torch_backend_from_cuda_version("12.8") == "cu128"
    assert _torch_backend_from_cuda_version("12.6") == "cu126"
    assert _torch_backend_from_cuda_version("12.4") == "cu124"
    assert _torch_backend_from_cuda_version("12.1") == "cu121"
    assert _torch_backend_from_cuda_version("11.8") == "cpu"


def test_bootstrap_installs_sam3_runtime_import_dependency():
    repo_root = Path(__file__).resolve().parents[3]
    bootstrap_text = (repo_root / "scripts" / "bootstrap_drawai_local_runtime.sh").read_text(encoding="utf-8")

    assert "pycocotools \\" in bootstrap_text


def test_workbench_runtime_pythonpath_uses_sam3_source_checkout():
    repo_root = Path(__file__).resolve().parents[3]
    script_text = (repo_root / "scripts" / "start_drawai_workbench_local.sh").read_text(encoding="utf-8")

    assert "$RUNTIME_ROOT/source/sam3" in script_text
    assert "$RUNTIME_ROOT/sam3_source" not in script_text


def test_workbench_script_separates_bind_and_connect_hosts():
    repo_root = Path(__file__).resolve().parents[3]
    script_text = (repo_root / "scripts" / "start_drawai_workbench_local.sh").read_text(encoding="utf-8")

    assert '0.0.0.0|::|\\[::\\])' in script_text
    assert 'CONNECT_HOST="127.0.0.1"' in script_text
    assert 'MODEL_API="${RAW_MODEL_API:-http://$CONNECT_HOST:$SAM_PORT}"' in script_text
    assert "DRAWAI_WORKBENCH_API_URL='http://$CONNECT_HOST:$API_PORT'" in script_text
    assert 'MODEL_API="${RAW_MODEL_API:-http://$HOST:$SAM_PORT}"' not in script_text


def test_workbench_script_waits_for_local_model_runtime():
    repo_root = Path(__file__).resolve().parents[3]
    script_text = (repo_root / "scripts" / "start_drawai_workbench_local.sh").read_text(encoding="utf-8")

    assert "is_loopback_model_api()" in script_text
    assert 'OCR_TIMEOUT_SECONDS="${DRAWAI_WORKBENCH_OCR_TIMEOUT_SECONDS:-600}"' in script_text
    assert "--ocr-timeout-seconds '$OCR_TIMEOUT_SECONDS'" in script_text
    assert "RUNTIME_BIN=" in script_text
    assert "env PATH='$RUNTIME_BIN:$PATH'" in script_text
    assert "DRAWAI_LOCAL_RUNTIME_ROOT='$RUNTIME_ROOT_ABS'" in script_text
    assert 'DEVICE="${DRAWAI_DEVICE:-cpu}"' in script_text
    assert "--device '$DEVICE'" in script_text
    assert "wait_for_http()" in script_text
    assert 'RUNTIME_LOG=".local/drawai-local-services.log"' in script_text
    assert 'wait_for_http "model runtime" "$MODEL_API/health" "$RUNTIME_LOG"' in script_text
    assert 'tail -n 80 "$log_path" >&2' in script_text
    assert "http://\\[::1\\]:*" in script_text
    assert "http://[::1]:*" not in script_text


def test_workbench_script_falls_back_to_nohup_without_tmux():
    repo_root = Path(__file__).resolve().parents[3]
    script_text = (repo_root / "scripts" / "start_drawai_workbench_local.sh").read_text(encoding="utf-8")

    assert 'if command -v tmux >/dev/null 2>&1; then' in script_text
    assert 'LAUNCHER="tmux"' in script_text
    assert 'LAUNCHER="nohup"' in script_text
    assert "tmux is not available; falling back to nohup" in script_text
    assert "start_nohup_process()" in script_text
    assert 'nohup bash -lc "$command" >"$log_path" 2>&1 &' in script_text
    assert 'echo "$!" >"$pid_path"' in script_text
    assert 'stop_pid_file ".local/workbench-api.pid"' in script_text
    assert 'stop_pid_file ".local/workbench-frontend.pid"' in script_text


def test_workbench_frontend_script_uses_nvm_and_checks_node_requirement():
    repo_root = Path(__file__).resolve().parents[3]
    frontend_script = (repo_root / "scripts" / "run_drawai_workbench_frontend.sh").read_text(encoding="utf-8")
    start_script = (repo_root / "scripts" / "start_drawai_workbench_local.sh").read_text(encoding="utf-8")
    package_json = json.loads((repo_root / "apps" / "workbench" / "package.json").read_text(encoding="utf-8"))

    assert 'NODE_REQUIREMENT="^20.19.0 || >=22.12.0"' in frontend_script
    assert "node_version_satisfies_vite()" in frontend_script
    assert "load_nvm_default_if_available()" in frontend_script
    assert 'elif [[ -s "$HOME/.nvm/nvm.sh" ]]' in frontend_script
    assert "nvm use --silent default" in frontend_script
    assert "run_drawai_workbench_frontend.sh" in start_script
    assert 'FRONTEND_LOG=".local/workbench-frontend.log"' in start_script
    assert 'wait_for_http "workbench frontend" "http://$CONNECT_HOST:$FRONTEND_PORT/" "$FRONTEND_LOG"' in start_script
    assert package_json["engines"]["node"] == "^20.19.0 || >=22.12.0"


def test_doctor_runtime_import_check_reports_missing_dependency():
    check = _check_runtime_python_import(
        "runtime import: missing",
        Path(sys.executable),
        "import drawai_missing_dependency_for_doctor_test",
    )

    assert check.status == "missing"
    assert "drawai_missing_dependency_for_doctor_test" in check.detail
    assert check.fix == "Run: uv run drawai setup local --bootstrap-only"


def test_doctor_project_python_codex_sdk_import_uses_project_fix(tmp_path: Path, monkeypatch):
    project_python = tmp_path / "project" / ".venv" / "bin" / "python"
    project_python.parent.mkdir(parents=True)
    project_python.write_text("#!/bin/sh\n", encoding="utf-8")

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="ModuleNotFoundError: No module named 'openai_codex'")

    monkeypatch.setattr("drawai.local_cli.subprocess.run", fake_run)

    check = _check_runtime_python_import(
        "Workbench/API Python import: Codex SDK",
        project_python,
        "import openai_codex; import drawai.codex_python_sdk_svg",
        "Run: uv sync",
    )

    assert check.status == "missing"
    assert check.fix == "Run: uv sync"


def test_doctor_checks_codex_executable_in_runtime(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path / "empty-path"))
    runtime_root = tmp_path / "runtime"
    bin_dir = runtime_root / ".venv" / "bin"
    bin_dir.mkdir(parents=True)
    codex = bin_dir / "codex"
    codex.write_text("#!/bin/sh\n", encoding="utf-8")

    check = _check_codex_executable(runtime_root)

    assert check.status == "ok"
    assert check.detail == str(codex)


def test_doctor_checks_packaged_codex_executable_in_runtime(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path / "empty-path"))
    runtime_root = tmp_path / "runtime"
    package_bin = runtime_root / ".venv" / "lib" / "python3.12" / "site-packages" / "codex_cli_bin" / "bin"
    package_bin.mkdir(parents=True)
    codex = package_bin / "codex"
    codex.write_text("#!/bin/sh\n", encoding="utf-8")

    check = _check_codex_executable(runtime_root)

    assert check.status == "ok"
    assert check.detail == str(codex)


def test_doctor_reports_missing_codex_executable(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path / "empty-path"))

    check = _check_codex_executable(tmp_path / "runtime")

    assert check.status == "missing"
    assert "Codex CLI" == check.name
    assert check.fix == "Run: uv run drawai setup local --bootstrap-only"


def test_doctor_reports_codex_auth_file_before_sdk_connectivity_check(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "codex-home"))
    auth = tmp_path / "codex-home" / "auth.json"
    auth.parent.mkdir()
    auth.write_text("{}", encoding="utf-8")

    check = _check_codex_auth()

    assert check.status == "ok"
    assert "SDK connectivity check follows" in check.detail


def test_doctor_reports_codex_auth_file_from_explicit_host_codex_home(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("DRAWAI_HOST_CODEX_HOME", str(tmp_path / "host-codex-home"))
    auth = tmp_path / "host-codex-home" / "auth.json"
    auth.parent.mkdir()
    auth.write_text("{}", encoding="utf-8")

    check = _check_codex_auth()

    assert check.status == "ok"
    assert str(auth) in check.detail


def test_doctor_reports_codex_auth_file_from_windows_userprofile(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("DRAWAI_HOST_CODEX_HOME", raising=False)
    monkeypatch.delenv("CODEX_HOME", raising=False)
    monkeypatch.delenv("DRAWAI_HOST_HOME", raising=False)
    monkeypatch.delenv("HOME", raising=False)
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "windows-user"))
    auth = tmp_path / "windows-user" / ".codex" / "auth.json"
    auth.parent.mkdir(parents=True)
    auth.write_text("{}", encoding="utf-8")

    check = _check_codex_auth()

    assert check.status == "ok"
    assert str(auth) in check.detail


def test_doctor_codex_auth_candidates_include_path_home_fallback(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("DRAWAI_HOST_CODEX_HOME", raising=False)
    monkeypatch.delenv("CODEX_HOME", raising=False)
    monkeypatch.delenv("DRAWAI_HOST_HOME", raising=False)
    monkeypatch.delenv("HOME", raising=False)
    monkeypatch.delenv("USERPROFILE", raising=False)
    fallback_home = tmp_path / "path-home"
    auth = fallback_home / ".codex" / "auth.json"
    auth.parent.mkdir(parents=True)
    auth.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(Path, "home", staticmethod(lambda: fallback_home))

    candidates = _codex_auth_candidate_paths()
    check = _check_codex_auth()

    assert auth.resolve(strict=False) in candidates
    assert check.status == "ok"
    assert str(auth) in check.detail


def test_doctor_codex_sdk_connectivity_requires_runtime_python(tmp_path: Path):
    check = _check_codex_sdk_auth_connectivity(tmp_path / "runtime" / ".venv" / "bin" / "python")

    assert check.status == "missing"
    assert check.name == "Codex SDK auth connectivity"
    assert check.fix == "Run: uv run drawai setup local --bootstrap-only"


def test_doctor_codex_sdk_connectivity_requires_credentials(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("DRAWAI_HOST_CODEX_HOME", raising=False)
    monkeypatch.delenv("DRAWAI_HOST_HOME", raising=False)
    monkeypatch.delenv("USERPROFILE", raising=False)
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "codex-home"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "path-home"))
    runtime_python = tmp_path / "runtime" / ".venv" / "bin" / "python"
    runtime_python.parent.mkdir(parents=True)
    runtime_python.write_text("#!/bin/sh\n", encoding="utf-8")

    check = _check_codex_sdk_auth_connectivity(runtime_python)

    assert check.status == "missing"
    assert "No OPENAI_API_KEY or Codex auth file" in check.detail


def test_doctor_codex_sdk_connectivity_runs_low_effort_sdk_probe(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    runtime_python = tmp_path / "runtime" / ".venv" / "bin" / "python"
    runtime_python.parent.mkdir(parents=True)
    runtime_python.write_text("#!/bin/sh\n", encoding="utf-8")
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, stdout="Codex SDK responded with 2 chars\n", stderr="")

    monkeypatch.setattr("drawai.local_cli.subprocess.run", fake_run)

    check = _check_codex_sdk_auth_connectivity(runtime_python)

    assert check.status == "ok"
    assert check.detail == "Codex SDK responded with 2 chars"
    command, kwargs = calls[0]
    assert command[0] == str(runtime_python)
    assert "check_codex_python_sdk_connectivity" in command[2]
    assert kwargs["timeout"] == 600.0


def test_doctor_codex_sdk_connectivity_redacts_failed_probe_output(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    runtime_python = tmp_path / "runtime" / ".venv" / "bin" / "python"
    runtime_python.parent.mkdir(parents=True)
    runtime_python.write_text("#!/bin/sh\n", encoding="utf-8")

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(
            command,
            1,
            stdout="",
            stderr="Authorization: Bearer sk-secret1234567890 failed with 401",
        )

    monkeypatch.setattr("drawai.local_cli.subprocess.run", fake_run)

    check = _check_codex_sdk_auth_connectivity(runtime_python)

    assert check.status == "missing"
    assert "401" in check.detail
    assert "sk-secret" not in check.detail
    assert "Bearer <redacted>" in check.detail
