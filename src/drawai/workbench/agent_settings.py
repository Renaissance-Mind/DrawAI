from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from drawai.codex_cli import resolve_codex_executable
from drawai.workflow.agents import SUPPORTED_REASONING_EFFORTS


SETTINGS_SCHEMA = "drawai.workbench.agent_settings.v1"
DEFAULT_AGENT_PROVIDER_ID = "codex_sdk"
VERSION_TIMEOUT_SECONDS = 8


@dataclass(frozen=True)
class WorkbenchAgentDefinition:
    provider_id: str
    label: str
    kind: str
    workflow_provider_id: str
    pipeline_agent: str
    default_command: tuple[str, ...] = ()
    description: str = ""


@dataclass(frozen=True)
class WorkbenchAgentSettings:
    selected_provider_id: str = DEFAULT_AGENT_PROVIDER_ID
    model: str = ""
    reasoning_effort: str = ""
    timeout_seconds: int = 0

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["schema"] = SETTINGS_SCHEMA
        return payload


AGENT_DEFINITIONS: dict[str, WorkbenchAgentDefinition] = {
    "codex_sdk": WorkbenchAgentDefinition(
        provider_id="codex_sdk",
        label="Codex SDK",
        kind="sdk",
        workflow_provider_id="codex_sdk",
        pipeline_agent="",
        description="OpenAI Codex Python SDK provider.",
    ),
    "codex_cli": WorkbenchAgentDefinition(
        provider_id="codex_cli",
        label="Codex CLI",
        kind="cli",
        workflow_provider_id="codex_cli",
        pipeline_agent="codex",
        default_command=("codex", "exec"),
        description="Codex CLI provider for all file-backed Agent stages.",
    ),
    "kimi_cli": WorkbenchAgentDefinition(
        provider_id="kimi_cli",
        label="Kimi CLI",
        kind="cli",
        workflow_provider_id="kimi_cli",
        pipeline_agent="kimi",
        default_command=("kimi",),
        description="Kimi CLI provider for all file-backed Agent stages.",
    ),
    "claude_cli": WorkbenchAgentDefinition(
        provider_id="claude_cli",
        label="Claude CLI",
        kind="cli",
        workflow_provider_id="claude_cli",
        pipeline_agent="claude",
        default_command=("claude",),
        description="Claude CLI provider for local Agent stages.",
    ),
    "openclaw_cli": WorkbenchAgentDefinition(
        provider_id="openclaw_cli",
        label="OpenClaw CLI",
        kind="cli",
        workflow_provider_id="openclaw_cli",
        pipeline_agent="openclaw",
        default_command=("openclaw", "agent"),
        description="OpenClaw local Agent CLI provider.",
    ),
    "hermes_cli": WorkbenchAgentDefinition(
        provider_id="hermes_cli",
        label="Hermes CLI",
        kind="cli",
        workflow_provider_id="hermes_cli",
        pipeline_agent="hermes",
        default_command=("hermes", "chat"),
        description="Hermes local Agent CLI provider.",
    ),
}


def agent_settings_path(workspace: str | Path) -> Path:
    return Path(workspace).expanduser().resolve(strict=False) / "settings" / "agent.json"


def read_workbench_agent_settings(workspace: str | Path) -> WorkbenchAgentSettings:
    path = agent_settings_path(workspace)
    if not path.is_file():
        return WorkbenchAgentSettings()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"Workbench agent settings must be a JSON object: {path}")
    return normalize_workbench_agent_settings(payload)


def write_workbench_agent_settings(
    workspace: str | Path,
    payload: Mapping[str, Any],
) -> WorkbenchAgentSettings:
    settings = normalize_workbench_agent_settings(payload)
    path = agent_settings_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return settings


def normalize_workbench_agent_settings(payload: Mapping[str, Any] | None) -> WorkbenchAgentSettings:
    data = dict(payload or {})
    provider_id = str(data.get("selected_provider_id") or data.get("provider_id") or DEFAULT_AGENT_PROVIDER_ID).strip()
    if provider_id not in AGENT_DEFINITIONS:
        supported = ", ".join(sorted(AGENT_DEFINITIONS))
        raise ValueError(f"unsupported Workbench agent provider: {provider_id!r}. Expected one of: {supported}")
    reasoning_effort = str(data.get("reasoning_effort") or "").strip().lower()
    if reasoning_effort and reasoning_effort not in SUPPORTED_REASONING_EFFORTS:
        supported = ", ".join(SUPPORTED_REASONING_EFFORTS)
        raise ValueError(f"unsupported reasoning_effort: {reasoning_effort!r}. Expected one of: {supported}")
    timeout_seconds = _settings_timeout_seconds(data.get("timeout_seconds"))
    return WorkbenchAgentSettings(
        selected_provider_id=provider_id,
        model=str(data.get("model") or "").strip(),
        reasoning_effort=reasoning_effort,
        timeout_seconds=timeout_seconds,
    )


def discover_workbench_agents() -> list[dict[str, Any]]:
    return [_discover_agent(definition) for definition in AGENT_DEFINITIONS.values()]


def workbench_agent_settings_payload(workspace: str | Path) -> dict[str, Any]:
    return {
        "settings": read_workbench_agent_settings(workspace).to_dict(),
        "agents": discover_workbench_agents(),
    }


def apply_workbench_agent_settings_to_node_config(
    node_config: Mapping[str, Any],
    settings: WorkbenchAgentSettings,
) -> dict[str, Any]:
    definition = AGENT_DEFINITIONS[settings.selected_provider_id]
    config = dict(node_config)
    config["provider_id"] = definition.workflow_provider_id
    if settings.model:
        config["model"] = settings.model
    if settings.reasoning_effort:
        config["reasoning_effort"] = settings.reasoning_effort
    if settings.timeout_seconds:
        config["timeout_seconds"] = settings.timeout_seconds
    return config


def workbench_agent_runtime_options(settings: WorkbenchAgentSettings) -> dict[str, Any]:
    command = resolved_agent_command(settings.selected_provider_id)
    return {"agent_cli_command": command} if command else {}


def apply_workbench_agent_settings_to_config_payload(
    payload: dict[str, Any],
    settings: WorkbenchAgentSettings,
) -> None:
    definition = AGENT_DEFINITIONS[settings.selected_provider_id]
    svg_config = _mapping_child(payload, "svg")
    runtime_config = _mapping_child(payload, "model_runtime")
    if definition.provider_id == "codex_sdk":
        svg_config["generation_backend"] = "codex_python_sdk_controlled"
        runtime_config["provider"] = "codex-python-sdk"
        runtime_config["connection_id"] = "codex-python-sdk-controlled"
        if settings.model:
            runtime_config["model_name"] = settings.model
    else:
        svg_config["generation_backend"] = "agent_cli"
        runtime_config["provider"] = "agent-cli"
        runtime_config["connection_id"] = definition.pipeline_agent
        runtime_config["model_name"] = settings.model
        cli_config = _mapping_child(runtime_config, "cli")
        cli_config["agent"] = definition.pipeline_agent
        cli_config["command"] = resolved_agent_command(definition.provider_id)
    if settings.reasoning_effort:
        runtime_config["reasoning_effort"] = settings.reasoning_effort
    if settings.timeout_seconds:
        runtime_config["timeout_seconds"] = settings.timeout_seconds


def resolved_agent_command(provider_id: str) -> list[str]:
    definition = AGENT_DEFINITIONS[provider_id]
    if definition.kind != "cli":
        return []
    if definition.provider_id == "codex_cli":
        path = resolve_codex_executable()
    else:
        executable = definition.default_command[0] if definition.default_command else definition.pipeline_agent
        found = shutil.which(executable)
        path = Path(found).expanduser().resolve(strict=False) if found else None
    if path is None:
        return list(definition.default_command)
    return [str(path), *definition.default_command[1:]]


def _discover_agent(definition: WorkbenchAgentDefinition) -> dict[str, Any]:
    if definition.kind == "sdk":
        package_available = importlib.util.find_spec("openai_codex") is not None
        auth = _codex_auth_status()
        status = "ok" if package_available and auth["available"] else "missing"
        detail = "Codex SDK package and auth are available." if status == "ok" else "Codex SDK needs package import and auth."
        return {
            "provider_id": definition.provider_id,
            "label": definition.label,
            "kind": definition.kind,
            "available": status == "ok",
            "status": status,
            "detail": detail,
            "fix": "" if status == "ok" else "Install the local runtime and run Codex login or set OPENAI_API_KEY.",
            "executable_path": "",
            "command": [],
            "version": "",
            "auth": auth,
            "workflow_provider_id": definition.workflow_provider_id,
            "pipeline_agent": definition.pipeline_agent,
            "description": definition.description,
        }
    command = resolved_agent_command(definition.provider_id)
    executable_path = command[0] if command else ""
    executable_exists = bool(executable_path and Path(executable_path).is_file())
    version = _agent_version(command) if executable_exists else ""
    status = "ok" if executable_exists else "missing"
    return {
        "provider_id": definition.provider_id,
        "label": definition.label,
        "kind": definition.kind,
        "available": executable_exists,
        "status": status,
        "detail": f"{definition.label} executable found." if executable_exists else f"{definition.label} executable was not found.",
        "fix": "" if executable_exists else f"Install {definition.default_command[0]} or add it to PATH.",
        "executable_path": executable_path,
        "command": command,
        "version": version,
        "auth": _codex_auth_status() if definition.provider_id == "codex_cli" else {"available": True, "detail": ""},
        "workflow_provider_id": definition.workflow_provider_id,
        "pipeline_agent": definition.pipeline_agent,
        "description": definition.description,
    }


def _agent_version(command: Sequence[str]) -> str:
    try:
        completed = subprocess.run(
            [command[0], "--version"],
            capture_output=True,
            text=True,
            timeout=VERSION_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    output = (completed.stdout or completed.stderr).strip()
    return " ".join(output.split())


def _codex_auth_status() -> dict[str, Any]:
    if os.environ.get("OPENAI_API_KEY"):
        return {"available": True, "detail": "OPENAI_API_KEY is set"}
    candidates = _codex_auth_candidate_paths()
    for path in candidates:
        if path.is_file():
            return {"available": True, "detail": f"{path} exists"}
    return {
        "available": False,
        "detail": "Checked: " + ", ".join(str(path) for path in candidates),
    }


def _codex_auth_candidate_paths() -> list[Path]:
    paths: list[Path] = []

    def append(path: Path) -> None:
        resolved = path.expanduser().resolve(strict=False)
        if resolved not in paths:
            paths.append(resolved)

    codex_home = os.environ.get("DRAWAI_HOST_CODEX_HOME") or os.environ.get("CODEX_HOME")
    if codex_home:
        append(Path(codex_home) / "auth.json")
    for home_var in ("DRAWAI_HOST_HOME", "HOME", "USERPROFILE"):
        value = os.environ.get(home_var)
        if value:
            append(Path(value) / ".codex" / "auth.json")
    append(Path.home() / ".codex" / "auth.json")
    return paths


def _settings_timeout_seconds(raw: Any) -> int:
    if raw in (None, ""):
        return 0
    value = int(raw)
    if value < 0:
        raise ValueError("timeout_seconds must be positive")
    return value


def _mapping_child(parent: dict[str, Any], key: str) -> dict[str, Any]:
    child = parent.get(key)
    if not isinstance(child, dict):
        child = {}
        parent[key] = child
    return child
