from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

AgentProviderKind = Literal["sdk", "cli"]

SUPPORTED_REASONING_EFFORTS = ("none", "minimal", "low", "medium", "high", "xhigh")
DANGEROUS_AGENT_CONFIG_KEYS = (
    "argv",
    "cmd",
    "command",
    "env",
    "executable",
    "shell_command",
)


@dataclass(frozen=True)
class AgentProviderSpec:
    provider_id: str
    label: str
    kind: AgentProviderKind
    resource_key: str
    default_max_concurrent: int
    executable: str = ""
    supports_images: bool = True
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "label": self.label,
            "kind": self.kind,
            "resource_key": self.resource_key,
            "default_max_concurrent": self.default_max_concurrent,
            "executable": self.executable,
            "supports_images": self.supports_images,
            "description": self.description,
        }


@dataclass(frozen=True)
class AgentOutputDeclaration:
    port_id: str
    path: str
    format_id: str
    type: str
    description: str

    def to_dict(self) -> dict[str, str]:
        return {
            "port_id": self.port_id,
            "path": self.path,
            "format_id": self.format_id,
            "type": self.type,
            "description": self.description,
        }


@dataclass(frozen=True)
class AgentPreset:
    preset_id: str
    title: str
    provider_id: str
    task: str
    outputs: tuple[AgentOutputDeclaration, ...]
    constraints: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "preset_id": self.preset_id,
            "title": self.title,
            "provider_id": self.provider_id,
            "task": self.task,
            "outputs": [output.to_dict() for output in self.outputs],
            "constraints": list(self.constraints),
        }


@dataclass(frozen=True)
class AgentPrompt:
    preset_id: str
    provider_id: str
    text: str
    inputs: tuple[Mapping[str, Any], ...]
    outputs: tuple[Mapping[str, Any], ...]
    options: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "preset_id": self.preset_id,
            "provider_id": self.provider_id,
            "text": self.text,
            "inputs": [dict(item) for item in self.inputs],
            "outputs": [dict(item) for item in self.outputs],
            "options": dict(self.options),
        }


def default_agent_provider_registry() -> dict[str, AgentProviderSpec]:
    return {
        "codex_sdk": AgentProviderSpec(
            provider_id="codex_sdk",
            label="Codex SDK",
            kind="sdk",
            resource_key="agent_provider:codex_sdk",
            default_max_concurrent=5,
            description="OpenAI Codex Python SDK provider.",
        ),
        "codex_cli": AgentProviderSpec(
            provider_id="codex_cli",
            label="Codex CLI",
            kind="cli",
            resource_key="agent_provider:codex_cli",
            default_max_concurrent=1,
            executable="codex",
            description="Codex CLI provider for file-backed Agent nodes.",
        ),
        "kimi_cli": AgentProviderSpec(
            provider_id="kimi_cli",
            label="Kimi CLI",
            kind="cli",
            resource_key="agent_provider:kimi_cli",
            default_max_concurrent=2,
            executable="kimi",
            description="Kimi CLI provider for file-backed Agent nodes.",
        ),
    }


def run0_agent_preset() -> AgentPreset:
    return AgentPreset(
        preset_id="run0_element_refine",
        title="Run0 Element Refinement",
        provider_id="codex_sdk",
        task=(
            "Refine element positions, sizes, and object types from connected "
            "parser or fusion outputs. Preserve the DrawAI element plan format."
        ),
        outputs=(
            AgentOutputDeclaration(
                port_id="elements",
                path="output/elements.json",
                format_id="drawai.element_plans.v1",
                type="element_plans",
                description="Refined element plans in the standard DrawAI v1 element plan JSON format.",
            ),
        ),
        constraints=(
            "Use only the connected input files listed in this prompt.",
            "Keep element ids stable unless an element is split or newly added.",
            "Write the declared output file exactly once as UTF-8 JSON.",
        ),
    )


def svg_agent_preset() -> AgentPreset:
    return AgentPreset(
        preset_id="svg_generation",
        title="SVG Generation",
        provider_id="codex_sdk",
        task=(
            "Generate an editable semantic SVG from connected element plans and "
            "asset packages. Preserve raster assets only through declared package references."
        ),
        outputs=(
            AgentOutputDeclaration(
                port_id="semantic_svg",
                path="output/semantic.svg",
                format_id="drawai.semantic_svg.v1",
                type="semantic_svg",
                description="Editable semantic SVG rooted at an svg element.",
            ),
        ),
        constraints=(
            "Use SVG primitives and text for editable elements.",
            "Do not inline unrelated local files or hidden state.",
            "Write the declared SVG output path exactly.",
        ),
    )


def custom_agent_preset() -> AgentPreset:
    return AgentPreset(
        preset_id="custom_agent",
        title="Custom Agent",
        provider_id="codex_sdk",
        task=(
            "Use the connected input files as context and produce exactly the "
            "output files declared by this node configuration."
        ),
        outputs=(
            AgentOutputDeclaration(
                port_id="image",
                path="output/image.png",
                format_id="drawai.image.v1",
                type="image",
                description="Generated or edited image file.",
            ),
        ),
        constraints=(
            "Treat every connected input file as explicit node context.",
            "Honor the configured output declarations over the preset defaults.",
            "Write only the declared output paths inside this node work directory.",
        ),
    )


def agent_preset_by_id(preset_id: str) -> AgentPreset:
    if preset_id == "run0_element_refine":
        return run0_agent_preset()
    if preset_id == "svg_generation":
        return svg_agent_preset()
    if preset_id == "custom_agent":
        return custom_agent_preset()
    raise ValueError(f"unknown Agent preset: {preset_id}")


def render_agent_prompt(
    preset: AgentPreset,
    *,
    inputs: Sequence[Mapping[str, Any]],
    node_config: Mapping[str, Any] | None = None,
) -> AgentPrompt:
    config = dict(node_config or {})
    _validate_agent_config(config)
    provider_id = str(config.get("provider_id") or preset.provider_id)
    selected_inputs = _selected_inputs(inputs, config)
    outputs = _configured_outputs(preset, config)
    options = _agent_options(config)
    text = _render_prompt_text(
        preset,
        provider_id=provider_id,
        inputs=selected_inputs,
        outputs=outputs,
        options=options,
        prompt_fragments=_prompt_fragments(config),
    )
    return AgentPrompt(
        preset_id=preset.preset_id,
        provider_id=provider_id,
        text=text,
        inputs=selected_inputs,
        outputs=outputs,
        options=options,
    )


def _render_prompt_text(
    preset: AgentPreset,
    *,
    provider_id: str,
    inputs: tuple[Mapping[str, Any], ...],
    outputs: tuple[Mapping[str, Any], ...],
    options: Mapping[str, Any],
    prompt_fragments: tuple[str, ...],
) -> str:
    lines = [
        f"# {preset.title}",
        "",
        f"Preset: {preset.preset_id}",
        f"Provider: {provider_id}",
        "",
        "## Task",
        preset.task,
        "",
        "## Available Input Files",
    ]
    if inputs:
        for item in inputs:
            source = _source_label(item)
            lines.extend(
                [
                    f"- Path: {item['path']}",
                    f"  Format: {item.get('format_id') or 'unspecified'}",
                    f"  Type: {item.get('type') or 'unspecified'}",
                    f"  Source: {source}",
                    f"  Description: {item.get('description') or 'No description supplied.'}",
                ]
            )
    else:
        lines.append("- No connected input files were provided.")

    lines.extend(["", "## Required Output Files"])
    for output in outputs:
        lines.extend(
            [
                f"- Path: {output['path']}",
                f"  Format: {output['format_id']}",
                f"  Type: {output['type']}",
                f"  Port: {output['port_id']}",
                f"  Description: {output['description']}",
            ]
        )

    lines.extend(["", "## Constraints"])
    for constraint in preset.constraints:
        lines.append(f"- {constraint}")
    lines.append("- Do not change files outside this node work directory unless an output declaration says so.")
    lines.append("- Do not use web search, memories, skills, hooks, or multi-agent delegation.")

    if options:
        lines.extend(["", "## Runtime Options"])
        for key, value in options.items():
            lines.append(f"- {key}: {value}")

    if prompt_fragments:
        lines.extend(["", "## Additional Node Instructions"])
        for fragment in prompt_fragments:
            lines.append(fragment)

    return "\n".join(lines).strip() + "\n"


def _selected_inputs(
    inputs: Sequence[Mapping[str, Any]],
    config: Mapping[str, Any],
) -> tuple[Mapping[str, Any], ...]:
    overrides = _input_overrides(config)
    selected: list[Mapping[str, Any]] = []
    for item in inputs:
        normalized = dict(item)
        path = _required_string(normalized.get("path"), "input.path")
        normalized["path"] = path
        override = _override_for_input(overrides, normalized)
        if override and override.get("include") is False:
            continue
        if override and isinstance(override.get("description"), str):
            normalized["description"] = override["description"]
        selected.append(normalized)
    return tuple(selected)


def _configured_outputs(
    preset: AgentPreset,
    config: Mapping[str, Any],
) -> tuple[Mapping[str, Any], ...]:
    raw_outputs = config.get("outputs", config.get("output_declarations"))
    if raw_outputs is None:
        return tuple(output.to_dict() for output in preset.outputs)
    if not isinstance(raw_outputs, list | tuple):
        raise ValueError("Agent outputs must be an array")
    outputs: list[Mapping[str, Any]] = []
    for index, raw_output in enumerate(raw_outputs):
        if not isinstance(raw_output, Mapping):
            raise ValueError(f"Agent outputs[{index}] must be an object")
        outputs.append(
            {
                "port_id": _required_string(raw_output.get("port_id"), f"outputs[{index}].port_id"),
                "path": _required_string(raw_output.get("path"), f"outputs[{index}].path"),
                "format_id": _required_string(raw_output.get("format_id"), f"outputs[{index}].format_id"),
                "type": _required_string(raw_output.get("type"), f"outputs[{index}].type"),
                "description": _required_string(
                    raw_output.get("description"),
                    f"outputs[{index}].description",
                ),
            }
        )
    return tuple(outputs)


def _validate_agent_config(config: Mapping[str, Any]) -> None:
    for key in DANGEROUS_AGENT_CONFIG_KEYS:
        if key in config:
            raise ValueError(f"Agent node config cannot override {key}")
    if "reasoning_effort" in config:
        effort = str(config["reasoning_effort"]).strip().lower()
        if effort not in SUPPORTED_REASONING_EFFORTS:
            raise ValueError(f"unsupported reasoning_effort: {effort}")
    if "timeout_seconds" in config:
        timeout = config["timeout_seconds"]
        if not isinstance(timeout, int | float) or isinstance(timeout, bool) or timeout <= 0:
            raise ValueError("timeout_seconds must be positive")
    for field_name in ("model", "profile", "provider_id"):
        if field_name in config and not isinstance(config[field_name], str):
            raise ValueError(f"{field_name} must be a string")


def _agent_options(config: Mapping[str, Any]) -> Mapping[str, Any]:
    options: dict[str, Any] = {}
    for key in ("model", "profile", "timeout_seconds", "reasoning_effort"):
        if key in config:
            options[key] = config[key]
    return options


def _prompt_fragments(config: Mapping[str, Any]) -> tuple[str, ...]:
    raw = config.get("prompt_fragments", config.get("user_prompt", ()))
    if raw in (None, ""):
        return ()
    if isinstance(raw, str):
        return (raw,)
    if not isinstance(raw, list | tuple):
        raise ValueError("Agent prompt_fragments must be a string or array of strings")
    fragments: list[str] = []
    for index, item in enumerate(raw):
        if not isinstance(item, str):
            raise ValueError(f"Agent prompt_fragments[{index}] must be a string")
        fragments.append(item)
    return tuple(fragments)


def _input_overrides(config: Mapping[str, Any]) -> Mapping[str, Mapping[str, Any]]:
    raw = config.get("input_overrides", {})
    if not isinstance(raw, Mapping):
        raise ValueError("Agent input_overrides must be an object")
    overrides: dict[str, Mapping[str, Any]] = {}
    for key, value in raw.items():
        if not isinstance(key, str):
            raise ValueError("Agent input_overrides keys must be strings")
        if not isinstance(value, Mapping):
            raise ValueError(f"Agent input_overrides.{key} must be an object")
        overrides[key] = value
    return overrides


def _override_for_input(
    overrides: Mapping[str, Mapping[str, Any]],
    item: Mapping[str, Any],
) -> Mapping[str, Any]:
    path = str(item.get("path") or "")
    source_node = str(item.get("source_node_id") or "")
    source_port = str(item.get("source_port_id") or "")
    return (
        overrides.get(path)
        or overrides.get(f"{source_node}.{source_port}")
        or overrides.get(source_node)
        or {}
    )


def _source_label(item: Mapping[str, Any]) -> str:
    source_node = str(item.get("source_node_id") or "")
    source_port = str(item.get("source_port_id") or "")
    if source_node and source_port:
        return f"{source_node}.{source_port}"
    if source_node:
        return source_node
    return "connected input"


def _required_string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")
    return value
