from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from drawai.codex_cli import resolve_codex_executable
from drawai.codex_python_sdk_svg import (
    CodexPythonSdkSvgError,
    _archive_codex_session_logs,
    _close_timed_out_thread_client,
    _codex_sdk_env,
    _isolated_codex_home,
    _load_openai_codex_sdk,
    _normalize_codex_model_name,
    _normalize_codex_reasoning_effort,
    controlled_codex_config_overrides,
)

from .agents import DEFAULT_AGENT_TIMEOUT_SECONDS, AgentPrompt
from .formats import validate_format_file


@dataclass(frozen=True)
class AgentExecutionRequest:
    prompt: AgentPrompt
    workdir: Path
    run_root: Path
    node_id: str
    node_type: str


@dataclass(frozen=True)
class AgentExecutionResult:
    provider_id: str
    prompt_path: Path
    stdout_path: Path | None = None
    stderr_path: Path | None = None
    trace_path: Path | None = None
    session_log_path: Path | None = None
    execution_manifest_path: Path | None = None
    exit_code: int = 0


@dataclass(frozen=True)
class _CodexSdkThreadOutcome:
    result: Any | None
    completed_by_outputs: bool = False


@dataclass(frozen=True)
class _DeclaredOutputReadiness:
    ready: bool
    signature: tuple[tuple[str, int, int], ...] = ()
    errors: tuple[str, ...] = ()


class AgentExecutionError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        prompt_path: Path | None = None,
        stdout_path: Path | None = None,
        stderr_path: Path | None = None,
        exit_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.prompt_path = prompt_path
        self.stdout_path = stdout_path
        self.stderr_path = stderr_path
        self.exit_code = exit_code


def execute_agent_prompt(request: AgentExecutionRequest) -> AgentExecutionResult:
    provider_id = request.prompt.provider_id
    request.workdir.mkdir(parents=True, exist_ok=True)
    prompt_path = request.workdir / "prompt.md"
    prompt_path.write_text(request.prompt.text, encoding="utf-8")
    _write_agent_input_manifest(request)
    _require_input_files(request)
    _validate_declared_output_paths(request)
    _write_execution_request_manifest(request, prompt_path)
    if provider_id == "codex_sdk":
        result = _execute_codex_sdk_agent(request, prompt_path=prompt_path)
    elif provider_id == "codex_cli":
        result = _execute_codex_cli_agent(request, prompt_path=prompt_path)
    elif provider_id == "kimi_cli":
        result = _execute_kimi_cli_agent(request, prompt_path=prompt_path)
    else:
        raise AgentExecutionError(
            f"unsupported Agent provider: {provider_id}",
            prompt_path=prompt_path,
        )
    _require_declared_outputs(request)
    manifest_path = _write_execution_manifest(request, result)
    return AgentExecutionResult(
        provider_id=result.provider_id,
        prompt_path=result.prompt_path,
        stdout_path=result.stdout_path,
        stderr_path=result.stderr_path,
        trace_path=result.trace_path,
        session_log_path=result.session_log_path,
        execution_manifest_path=manifest_path,
        exit_code=result.exit_code,
    )


def _execute_codex_sdk_agent(
    request: AgentExecutionRequest,
    *,
    prompt_path: Path,
) -> AgentExecutionResult:
    sdk = _load_openai_codex_sdk()
    options = dict(request.prompt.options)
    model_name = _normalize_codex_model_name(options.get("model"))
    reasoning_effort = _codex_sdk_reasoning_effort(options.get("reasoning_effort"))
    timeout_seconds = _timeout_seconds(options)
    trace_path = request.workdir / "codex_sdk_trace.jsonl"
    stdout_path = request.workdir / "codex_sdk_final_response.txt"
    stderr_path = request.workdir / "codex_sdk_error.txt"
    session_log_path = request.workdir / "codex_session_log"
    started_at = time.monotonic()
    result: Any | None = None
    archive: Mapping[str, Any] | None = None
    completed_by_outputs = False
    try:
        with _isolated_codex_home(request.workdir) as prepared_codex_home:
            try:
                with sdk.Codex(
                    sdk.CodexConfig(
                        cwd=str(request.workdir),
                        config_overrides=controlled_codex_config_overrides(),
                        env=_codex_sdk_env(prepared_codex_home.codex_home),
                    )
                ) as codex:
                    thread = codex.thread_start(
                        approval_mode=sdk.ApprovalMode.deny_all,
                        config={"model_reasoning_effort": reasoning_effort},
                        cwd=str(request.workdir),
                        developer_instructions=_developer_instructions(request),
                        ephemeral=True,
                        model=model_name,
                        sandbox=sdk.Sandbox.full_access,
                    )
                    codex_inputs: list[Any] = [sdk.TextInput(request.prompt.text)]
                    image_paths = _image_input_paths(request)
                    codex_inputs.extend(
                        sdk.LocalImageInput(path=str(path))
                        for path in image_paths
                    )
                    _append_trace(
                        trace_path,
                        {
                            "type": "agent_request",
                            "provider_id": "codex_sdk",
                            "node_id": request.node_id,
                            "cwd": str(request.workdir),
                            "prompt_path": str(prompt_path),
                            "input_paths": [str(path) for path in _input_paths(request)],
                            "image_input_paths": [str(path) for path in image_paths],
                            "declared_outputs": list(request.prompt.outputs),
                            "model": model_name or "codex-default",
                            "reasoning_effort": reasoning_effort,
                            "timeout_seconds": timeout_seconds,
                        },
                    )
                    thread_outcome = _run_codex_sdk_thread_until_done_or_outputs(
                        thread,
                        codex_inputs,
                        request=request,
                        trace_path=trace_path,
                        timeout_seconds=timeout_seconds,
                        approval_mode=sdk.ApprovalMode.deny_all,
                        cwd=str(request.workdir),
                        effort=reasoning_effort,
                        model=model_name,
                        sandbox=sdk.Sandbox.full_access,
                    )
                    result = thread_outcome.result
                    completed_by_outputs = thread_outcome.completed_by_outputs
                    final_response = str(getattr(result, "final_response", "") or "")
                    if thread_outcome.completed_by_outputs and not final_response.strip():
                        final_response = (
                            "Done: declared output files were present, stable, and format-valid "
                            "before the Codex SDK turn returned."
                        )
                    stdout_path.write_text(final_response, encoding="utf-8")
            except Exception as exc:
                archive = _archive_codex_session_logs(
                    prepared_codex_home.codex_home,
                    session_log_path,
                    task_name=f"drawai.workflow.agent.{request.node_id}.codex_sdk",
                    sdk_turn_result=result,
                )
                _append_trace(
                    trace_path,
                    {
                        "type": "agent_error",
                        "provider_id": "codex_sdk",
                        "node_id": request.node_id,
                        "duration_ms": int((time.monotonic() - started_at) * 1000),
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                        "session_log_archive": archive,
                        "output_paths": [
                            str(_declared_output_path(request, output))
                            for output in request.prompt.outputs
                        ],
                    },
                )
                raise
            archive = _archive_codex_session_logs(
                prepared_codex_home.codex_home,
                session_log_path,
                task_name=f"drawai.workflow.agent.{request.node_id}.codex_sdk",
                sdk_turn_result=result,
            )
    except Exception as exc:
        stderr_path.write_text(f"{type(exc).__name__}: {exc}\n", encoding="utf-8")
        raise AgentExecutionError(
            f"Codex SDK Agent run failed: {exc}",
            prompt_path=prompt_path,
            stdout_path=stdout_path if stdout_path.exists() else None,
            stderr_path=stderr_path,
            exit_code=1,
        ) from exc
    _append_trace(
        trace_path,
        {
            "type": "agent_response",
            "provider_id": "codex_sdk",
            "node_id": request.node_id,
            "duration_ms": int((time.monotonic() - started_at) * 1000),
            "session_log_archive": archive,
            "output_paths": [str(_declared_output_path(request, output)) for output in request.prompt.outputs],
            "completed_by_outputs": completed_by_outputs,
        },
    )
    return AgentExecutionResult(
        provider_id="codex_sdk",
        prompt_path=prompt_path,
        stdout_path=stdout_path,
        stderr_path=stderr_path if stderr_path.exists() else None,
        trace_path=trace_path,
        session_log_path=session_log_path,
    )


def _run_codex_sdk_thread_until_done_or_outputs(
    thread: Any,
    run_input: Any,
    *,
    request: AgentExecutionRequest,
    trace_path: Path,
    timeout_seconds: float,
    **kwargs: Any,
) -> _CodexSdkThreadOutcome:
    timeout = float(timeout_seconds)
    if timeout <= 0:
        raise CodexPythonSdkSvgError("runtime_config.timeout_seconds must be positive")
    poll_seconds = _positive_float_option(
        request.prompt.options,
        "output_completion_poll_seconds",
        default=0.5,
    )
    stable_seconds = _positive_float_option(
        request.prompt.options,
        "output_completion_stable_seconds",
        default=2.0,
    )
    close_wait_seconds = _positive_float_option(
        request.prompt.options,
        "output_completion_close_wait_seconds",
        default=5.0,
    )
    done = threading.Event()
    state: dict[str, Any] = {}

    def _target() -> None:
        try:
            state["result"] = thread.run(run_input, **kwargs)
        except BaseException as exc:  # noqa: BLE001 - propagate SDK worker failure.
            state["error"] = exc
        finally:
            done.set()

    worker = threading.Thread(
        target=_target,
        name=f"drawai-codex-sdk-agent-{request.node_id}",
        daemon=True,
    )
    started_at = time.monotonic()
    deadline = started_at + timeout
    ready_since: float | None = None
    ready_signature: tuple[tuple[str, int, int], ...] = ()
    last_readiness = _DeclaredOutputReadiness(ready=False)
    worker.start()

    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            _close_timed_out_thread_client(thread)
            raise CodexPythonSdkSvgError(
                f"Codex Python SDK run exceeded timeout_seconds={timeout:g}"
            )
        if done.wait(min(poll_seconds, remaining)):
            if "error" in state:
                raise state["error"]
            return _CodexSdkThreadOutcome(result=state.get("result"))

        readiness = _declared_outputs_readiness(request)
        last_readiness = readiness
        if not readiness.ready:
            ready_since = None
            ready_signature = ()
            continue
        if readiness.signature != ready_signature:
            ready_signature = readiness.signature
            ready_since = time.monotonic()
            continue
        if ready_since is not None and time.monotonic() - ready_since >= stable_seconds:
            _close_timed_out_thread_client(thread)
            done.wait(close_wait_seconds)
            _append_trace(
                trace_path,
                {
                    "type": "agent_outputs_satisfied_before_sdk_turn_finished",
                    "provider_id": "codex_sdk",
                    "node_id": request.node_id,
                    "duration_ms": int((time.monotonic() - started_at) * 1000),
                    "output_paths": [
                        str(_declared_output_path(request, output))
                        for output in request.prompt.outputs
                    ],
                    "readiness_errors": list(last_readiness.errors),
                },
            )
            if "result" in state:
                return _CodexSdkThreadOutcome(result=state["result"], completed_by_outputs=True)
            return _CodexSdkThreadOutcome(result=None, completed_by_outputs=True)


def _execute_codex_cli_agent(
    request: AgentExecutionRequest,
    *,
    prompt_path: Path,
) -> AgentExecutionResult:
    executable = resolve_codex_executable()
    if executable is None:
        raise AgentExecutionError("codex executable was not found", prompt_path=prompt_path)
    options = dict(request.prompt.options)
    command = [
        str(executable),
        "exec",
        "--ignore-user-config",
        "--ignore-rules",
        "--skip-git-repo-check",
        "--disable",
        "plugins",
        "--json",
        "-C",
        str(request.workdir),
        "-s",
        "danger-full-access",
        "-o",
        str(request.workdir / "codex_cli_last_message.txt"),
        *(_codex_image_args(request)),
        *(_codex_cli_config_args(options)),
    ]
    model = _normalize_codex_model_name(options.get("model"))
    if model is not None:
        command.extend(["-m", model])
    command.append("-")
    session_log_path = request.workdir / "codex_cli_session_log"
    with _isolated_codex_home(request.workdir) as prepared_codex_home:
        result = _execute_subprocess_agent(
            request,
            prompt_path=prompt_path,
            provider_id="codex_cli",
            command=command,
            stdout_name="codex_cli_events.jsonl",
            stderr_name="codex_cli_stderr.txt",
            env_overrides=_codex_cli_env(prepared_codex_home.codex_home),
        )
        archive = _archive_codex_session_logs(
            prepared_codex_home.codex_home,
            session_log_path,
            task_name=f"drawai.workflow.agent.{request.node_id}.codex_cli",
        )
        _append_trace(
            result.trace_path or (request.workdir / "codex_cli_trace.jsonl"),
            {
                "type": "session_log_archive",
                "provider_id": "codex_cli",
                "node_id": request.node_id,
                "archive": archive,
            },
        )
    return AgentExecutionResult(
        provider_id=result.provider_id,
        prompt_path=result.prompt_path,
        stdout_path=result.stdout_path,
        stderr_path=result.stderr_path,
        trace_path=result.trace_path,
        session_log_path=session_log_path,
        exit_code=result.exit_code,
    )


def _execute_kimi_cli_agent(
    request: AgentExecutionRequest,
    *,
    prompt_path: Path,
) -> AgentExecutionResult:
    executable = shutil.which("kimi")
    if executable is None:
        raise AgentExecutionError("kimi executable was not found", prompt_path=prompt_path)
    options = dict(request.prompt.options)
    command = [
        executable,
        "--work-dir",
        str(request.workdir),
        "--print",
        "--input-format",
        "text",
        "--output-format",
        "stream-json",
    ]
    skills_dir = request.workdir / "_isolated_kimi_skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    command.extend(["--skills-dir", str(skills_dir)])
    model = str(options.get("model") or "").strip()
    if model:
        command.extend(["--model", model])
    result = _execute_subprocess_agent(
        request,
        prompt_path=prompt_path,
        provider_id="kimi_cli",
        command=command,
        stdout_name="kimi_events.jsonl",
        stderr_name="kimi_stderr.txt",
    )
    export_path = request.workdir / "kimi_session.zip"
    export_command = [executable, "export", "--output", str(export_path), "--yes"]
    completed = subprocess.run(
        export_command,
        cwd=str(request.workdir),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        timeout=120,
    )
    session_log_path = export_path if completed.returncode == 0 and export_path.is_file() else None
    return AgentExecutionResult(
        provider_id=result.provider_id,
        prompt_path=result.prompt_path,
        stdout_path=result.stdout_path,
        stderr_path=result.stderr_path,
        trace_path=result.trace_path,
        session_log_path=session_log_path,
        exit_code=result.exit_code,
    )


def _execute_subprocess_agent(
    request: AgentExecutionRequest,
    *,
    prompt_path: Path,
    provider_id: str,
    command: Sequence[str],
    stdout_name: str,
    stderr_name: str,
    env_overrides: Mapping[str, str | None] | None = None,
) -> AgentExecutionResult:
    stdout_path = request.workdir / stdout_name
    stderr_path = request.workdir / stderr_name
    trace_path = request.workdir / f"{provider_id}_trace.jsonl"
    timeout_seconds = _timeout_seconds(request.prompt.options)
    env = os.environ.copy()
    for key in tuple(env):
        if key.startswith("CODEX_"):
            env.pop(key, None)
    if env_overrides:
        for key, value in env_overrides.items():
            env_key = str(key)
            if value is None:
                env.pop(env_key, None)
            else:
                env[env_key] = str(value)
    started_at = time.monotonic()
    _append_trace(
        trace_path,
        {
            "type": "agent_request",
            "provider_id": provider_id,
            "node_id": request.node_id,
            "cwd": str(request.workdir),
            "prompt_path": str(prompt_path),
            "command": _redact_command(command),
            "input_paths": [str(path) for path in _input_paths(request)],
            "declared_outputs": list(request.prompt.outputs),
            "timeout_seconds": timeout_seconds,
        },
    )
    try:
        with stdout_path.open("w", encoding="utf-8") as stdout_handle, stderr_path.open("w", encoding="utf-8") as stderr_handle:
            process = subprocess.Popen(
                list(command),
                stdin=subprocess.PIPE,
                text=True,
                cwd=str(request.workdir),
                env=env,
                stdout=stdout_handle,
                stderr=stderr_handle,
            )
            if process.stdin is None:
                raise RuntimeError("Agent subprocess stdin pipe was not created")
            process.stdin.write(request.prompt.text)
            process.stdin.close()
            returncode, completed_by_outputs = _wait_for_subprocess_until_done_or_outputs(
                process,
                request=request,
                trace_path=trace_path,
                provider_id=provider_id,
                timeout_seconds=timeout_seconds,
            )
    except Exception as exc:
        _append_trace(
            trace_path,
            {
                "type": "agent_error",
                "provider_id": provider_id,
                "node_id": request.node_id,
                "duration_ms": int((time.monotonic() - started_at) * 1000),
                "error_type": type(exc).__name__,
                "error": str(exc),
                "output_paths": [str(_declared_output_path(request, output)) for output in request.prompt.outputs],
            },
        )
        raise AgentExecutionError(
            f"{provider_id} Agent run failed: {exc}",
            prompt_path=prompt_path,
            stdout_path=stdout_path if stdout_path.exists() else None,
            stderr_path=stderr_path if stderr_path.exists() else None,
            exit_code=1,
        ) from exc
    _append_trace(
        trace_path,
        {
            "type": "agent_response",
            "provider_id": provider_id,
            "node_id": request.node_id,
            "returncode": returncode,
            "duration_ms": int((time.monotonic() - started_at) * 1000),
            "output_paths": [str(_declared_output_path(request, output)) for output in request.prompt.outputs],
            "completed_by_outputs": completed_by_outputs,
        },
    )
    if returncode != 0:
        stderr_tail = stderr_path.read_text(encoding="utf-8")[-2000:] if stderr_path.exists() else ""
        raise AgentExecutionError(
            f"{provider_id} Agent run failed with returncode={returncode}: {stderr_tail}",
            prompt_path=prompt_path,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            exit_code=returncode,
        )
    return AgentExecutionResult(
        provider_id=provider_id,
        prompt_path=prompt_path,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        trace_path=trace_path,
        exit_code=returncode,
    )


def _wait_for_subprocess_until_done_or_outputs(
    process: subprocess.Popen[str],
    *,
    request: AgentExecutionRequest,
    trace_path: Path,
    provider_id: str,
    timeout_seconds: float,
) -> tuple[int, bool]:
    timeout = float(timeout_seconds)
    if timeout <= 0:
        raise ValueError("timeout_seconds must be positive")
    poll_seconds = _positive_float_option(
        request.prompt.options,
        "output_completion_poll_seconds",
        default=0.5,
    )
    stable_seconds = _positive_float_option(
        request.prompt.options,
        "output_completion_stable_seconds",
        default=2.0,
    )
    close_wait_seconds = _positive_float_option(
        request.prompt.options,
        "output_completion_close_wait_seconds",
        default=5.0,
    )
    started_at = time.monotonic()
    deadline = started_at + timeout
    ready_since: float | None = None
    ready_signature: tuple[tuple[str, int, int], ...] = ()

    while True:
        readiness = _declared_outputs_readiness(request)
        if readiness.ready:
            if readiness.signature != ready_signature:
                ready_signature = readiness.signature
                ready_since = time.monotonic()
            elif ready_since is not None and time.monotonic() - ready_since >= stable_seconds:
                _terminate_process(process, timeout=close_wait_seconds)
                _append_trace(
                    trace_path,
                    {
                        "type": "agent_outputs_satisfied_before_process_finished",
                        "provider_id": provider_id,
                        "node_id": request.node_id,
                        "duration_ms": int((time.monotonic() - started_at) * 1000),
                        "output_paths": [
                            str(_declared_output_path(request, output))
                            for output in request.prompt.outputs
                        ],
                    },
                )
                return 0, True
        else:
            ready_since = None
            ready_signature = ()

        returncode = process.poll()
        if returncode is not None:
            return int(returncode), False
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            _terminate_process(process, timeout=close_wait_seconds, kill=True)
            raise subprocess.TimeoutExpired(process.args, timeout)
        time.sleep(min(poll_seconds, remaining))


def _terminate_process(
    process: subprocess.Popen[str],
    *,
    timeout: float,
    kill: bool = False,
) -> None:
    if process.poll() is not None:
        return
    if kill:
        process.kill()
    else:
        process.terminate()
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=timeout)


def _write_execution_manifest(
    request: AgentExecutionRequest,
    result: AgentExecutionResult,
) -> Path:
    path = request.workdir / "agent_execution.json"
    _write_json(
        path,
        {
            "schema": "drawai.workflow_agent_execution.v1",
            "node_id": request.node_id,
            "provider_id": result.provider_id,
            "cwd": str(request.workdir),
            "prompt_path": _relative_or_absolute(result.prompt_path, request.run_root),
            "stdout_path": _relative_or_absolute(result.stdout_path, request.run_root),
            "stderr_path": _relative_or_absolute(result.stderr_path, request.run_root),
            "trace_path": _relative_or_absolute(result.trace_path, request.run_root),
            "session_log_path": _relative_or_absolute(result.session_log_path, request.run_root),
            "declared_inputs": [dict(item) for item in request.prompt.inputs],
            "input_paths": [
                _relative_or_absolute(path, request.run_root)
                for path in _input_paths(request)
            ],
            "image_input_paths": [
                _relative_or_absolute(path, request.run_root)
                for path in _image_input_paths(request)
            ],
            "declared_outputs": list(request.prompt.outputs),
            "actual_outputs": [
                _relative_or_absolute(_declared_output_path(request, output), request.run_root)
                for output in request.prompt.outputs
            ],
            "exit_code": result.exit_code,
        },
    )
    return path


def _write_execution_request_manifest(
    request: AgentExecutionRequest,
    prompt_path: Path,
) -> Path:
    path = request.workdir / "agent_execution_request.json"
    _write_json(
        path,
        {
            "schema": "drawai.workflow_agent_execution_request.v1",
            "node_id": request.node_id,
            "node_type": request.node_type,
            "provider_id": request.prompt.provider_id,
            "cwd": str(request.workdir),
            "run_root": str(request.run_root),
            "prompt_path": _relative_or_absolute(prompt_path, request.run_root),
            "declared_inputs": [dict(item) for item in request.prompt.inputs],
            "input_paths": [
                _relative_or_absolute(path_item, request.run_root)
                for path_item in _input_paths(request)
            ],
            "image_input_paths": [
                _relative_or_absolute(path_item, request.run_root)
                for path_item in _image_input_paths(request)
            ],
            "declared_outputs": list(request.prompt.outputs),
            "options": dict(request.prompt.options),
        },
    )
    return path


def _write_agent_input_manifest(request: AgentExecutionRequest) -> Path:
    path = request.workdir / "input_manifest.json"
    input_paths = _input_paths(request)
    inputs: list[dict[str, Any]] = []
    for item, absolute_path in zip(request.prompt.inputs, input_paths, strict=False):
        enriched = dict(item)
        enriched["absolute_path"] = str(absolute_path)
        enriched["from_agent_cwd"] = _relative_from_workdir(absolute_path, request.workdir)
        enriched["exists"] = absolute_path.is_file()
        inputs.append(enriched)
    _write_json(
        path,
        {
            "schema": "drawai.workflow_input_manifest.v1",
            "node_id": request.node_id,
            "node_type": request.node_type,
            "provider_id": request.prompt.provider_id,
            "run_root": str(request.run_root),
            "workdir": str(request.workdir),
            "inputs": inputs,
        },
    )
    return path


def _require_declared_outputs(request: AgentExecutionRequest) -> None:
    missing: list[str] = []
    for output in request.prompt.outputs:
        output_path = _declared_output_path(request, output)
        if not output_path.is_file():
            missing.append(str(output_path))
    if missing:
        raise AgentExecutionError(
            "Agent did not write declared output files: " + ", ".join(missing),
            prompt_path=request.workdir / "prompt.md",
        )


def _require_input_files(request: AgentExecutionRequest) -> None:
    missing: list[str] = []
    for path in _input_paths(request):
        if not path.is_file():
            missing.append(str(path))
    if missing:
        raise AgentExecutionError(
            "Agent input files do not exist: " + ", ".join(missing),
            prompt_path=request.workdir / "prompt.md",
        )


def _validate_declared_output_paths(request: AgentExecutionRequest) -> None:
    for output in request.prompt.outputs:
        _declared_output_path(request, output)


def _declared_outputs_readiness(request: AgentExecutionRequest) -> _DeclaredOutputReadiness:
    signatures: list[tuple[str, int, int]] = []
    errors: list[str] = []
    for output in request.prompt.outputs:
        output_path = _declared_output_path(request, output)
        if not output_path.is_file():
            errors.append(f"missing: {output_path}")
            continue
        stat = output_path.stat()
        signatures.append((str(output_path), stat.st_size, stat.st_mtime_ns))
        format_id = output.get("format_id")
        if isinstance(format_id, str) and format_id:
            validation = validate_format_file(format_id, output_path)
            if not validation.ok:
                errors.extend(f"{output_path}: {error}" for error in validation.errors)
    return _DeclaredOutputReadiness(
        ready=not errors and len(signatures) == len(request.prompt.outputs),
        signature=tuple(signatures),
        errors=tuple(errors),
    )


def _declared_output_path(
    request: AgentExecutionRequest,
    output: Mapping[str, Any],
) -> Path:
    raw_path = output.get("path")
    if not isinstance(raw_path, str) or not raw_path:
        raise AgentExecutionError(
            "Agent declared output path must be a non-empty string",
            prompt_path=request.workdir / "prompt.md",
        )
    path = Path(raw_path)
    if path.is_absolute():
        raise AgentExecutionError(
            f"Agent declared output path must be relative to node workdir: {raw_path}",
            prompt_path=request.workdir / "prompt.md",
        )
    resolved = (request.workdir / path).resolve(strict=False)
    try:
        resolved.relative_to(request.workdir.resolve(strict=False))
    except ValueError as exc:
        raise AgentExecutionError(
            f"Agent declared output path escapes node workdir: {raw_path}",
            prompt_path=request.workdir / "prompt.md",
        ) from exc
    return resolved


def _developer_instructions(request: AgentExecutionRequest) -> str:
    return (
        "You are a DrawAI file-backed Agent node. Run inside the current node workdir, "
        "read only the connected input files and built-in script files declared by the prompt, and write "
        "the declared output files exactly. Do not use web search, external apps, hooks, memories, or "
        "multi-agent delegation."
    )


def _timeout_seconds(options: Mapping[str, Any]) -> float:
    raw = options.get("timeout_seconds", DEFAULT_AGENT_TIMEOUT_SECONDS)
    timeout = float(raw)
    if timeout <= 0:
        raise ValueError("timeout_seconds must be positive")
    return timeout


def _positive_float_option(
    options: Mapping[str, Any],
    key: str,
    *,
    default: float,
) -> float:
    raw = options.get(key, default)
    value = float(raw)
    if value <= 0:
        raise ValueError(f"{key} must be positive")
    return value


def _input_paths(request: AgentExecutionRequest) -> tuple[Path, ...]:
    paths: list[Path] = []
    for item in request.prompt.inputs:
        path = item.get("path")
        if isinstance(path, str) and path:
            path_obj = Path(path)
            paths.append(path_obj if path_obj.is_absolute() else request.run_root / path_obj)
    return tuple(paths)


def _image_input_paths(request: AgentExecutionRequest) -> tuple[Path, ...]:
    return tuple(
        path
        for path, item in zip(_input_paths(request), request.prompt.inputs, strict=False)
        if str(item.get("type") or "") == "image" and path.is_file()
    )


def _codex_image_args(request: AgentExecutionRequest) -> list[str]:
    args: list[str] = []
    for image_path in _image_input_paths(request):
        args.extend(["-i", str(image_path)])
    return args


def _codex_cli_config_args(options: Mapping[str, Any]) -> list[str]:
    raw_effort = options.get("reasoning_effort")
    reasoning_effort = _normalize_codex_reasoning_effort(raw_effort)
    args: list[str] = []
    for override in controlled_codex_config_overrides([f'model_reasoning_effort="{reasoning_effort}"']):
        args.extend(["-c", override])
    return args


def _codex_cli_env(codex_home: Path) -> dict[str, str | None]:
    env: dict[str, str | None] = {
        key: None for key in os.environ if key.startswith("CODEX_")
    }
    env["CODEX_HOME"] = str(codex_home)
    env["HOME"] = str(codex_home.parent)
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if openai_api_key:
        env["OPENAI_API_KEY"] = openai_api_key
    return env


def _codex_sdk_reasoning_effort(value: Any) -> str:
    reasoning_effort = _normalize_codex_reasoning_effort(value)
    if reasoning_effort == "minimal":
        return "low"
    return reasoning_effort


def _append_trace(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _relative_or_absolute(path: Path | None, root: Path) -> str:
    if path is None:
        return ""
    resolved = path.expanduser().resolve(strict=False)
    try:
        return resolved.relative_to(root.expanduser().resolve(strict=False)).as_posix()
    except ValueError:
        return str(resolved)


def _relative_from_workdir(path: Path, workdir: Path) -> str:
    return os.path.relpath(path.resolve(strict=False), workdir.resolve(strict=False))


def _redact_command(command: Sequence[str]) -> list[str]:
    redacted: list[str] = []
    skip_next = False
    for item in command:
        if skip_next:
            redacted.append(item)
            skip_next = False
            continue
        redacted.append(str(item))
        if item in {"-i", "-C", "-o", "-m", "-s", "-c", "--model", "--work-dir", "--output"}:
            skip_next = True
    return redacted
