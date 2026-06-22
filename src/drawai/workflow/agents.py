from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from posixpath import normpath
from typing import Any, Literal

from .agent_prompt_defaults import (
    CUSTOM_AGENT_CONSTRAINTS,
    CUSTOM_AGENT_TASK,
    PAGE_SPEC_REFINE_CONSTRAINTS,
    PAGE_SPEC_REFINE_TASK,
    RUN0_ELEMENT_REFINE_CONSTRAINTS,
    RUN0_ELEMENT_REFINE_TASK,
    SVG_GENERATION_CONSTRAINTS,
    SVG_GENERATION_TASK,
)
from drawai.tooling import render_drawai_tool_prompt_section

from .formats import default_format_contract_descriptions, default_format_registry

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
DEFAULT_AGENT_TIMEOUT_SECONDS = 1800
SVG_AGENT_TIMEOUT_SECONDS = 7200

TYPE_CONTRACTS = {
    "image": "Raster image file. Use it as visual evidence; do not rewrite it unless this node declares an image output.",
    "element_candidates": (
        "Parser candidate elements before fusion/refinement. JSON contains candidates with candidate_id, "
        "source_parser, element_type, bbox [x, y, width, height], geometry, confidence, optional text, evidence_files, provenance, and raw_ref."
    ),
    "element_plans": (
        "Refined/planned DrawAI elements. JSON contains elements with element_id, source_candidate_ids, element_type, "
        "bbox [x, y, width, height], geometry, z_order, confidence low|medium|high, processing_intent "
        "{object_type, processing_type, parameters}, review_status, created_by_stage, and change_reason."
    ),
    "page_spec": (
        "Canonical one-page composition model. JSON contains schema drawai.page_spec.v1, page_id, source, canvas, "
        "optional background, and elements with id, kind, box_px, z_index, role, build instructions, style, "
        "measurement, source_refs, metadata, and optional group parent/children links."
    ),
    "element_analysis": (
        "Legacy Run0 asset/source analysis JSON. JSON contains schema drawai.codex_element_analysis.v1, case_dir, "
        "source, strategy_summary, refinement_summary, categories, refinement_actions, elements, optional "
        "removal_records, and notes. Each retained element uses box_id or element_id, source_candidate_ids, "
        "refinement_action, category svg_self_draw|crop|crop_nobg, confidence, visual_role, reason, evidence, "
        "bbox [x1, y1, x2, y2], type, current_pipeline_method, and recommended_asset_source. Top-level "
        "removal_records cover removed/merged source candidates and must include action or refinement_action "
        "removed|merged, source_candidate_ids or removed_source_candidate_ids, and reason or removal_reason."
    ),
    "asset_packages": (
        "Processed asset package collection. JSON contains asset_packages with asset_id, element_id, processor_type, "
        "status pending|running|ok|failed|unsupported, files, metadata, processor_runs, all_results, active_result, editable_payload, and failure."
    ),
    "semantic_svg": "Editable SVG file with an <svg> root following the DrawAI semantic SVG/PPT profile.",
    "pptx": "PowerPoint Open XML .pptx package.",
    "final_outputs": "Output-node manifest listing collected deliverables and optional mirrored paths.",
}


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
class AgentScriptSpec:
    script_id: str
    path: str
    description: str
    usage: str = ""

    def to_dict(self) -> dict[str, str]:
        payload = {
            "script_id": self.script_id,
            "path": self.path,
            "description": self.description,
        }
        if self.usage:
            payload["usage"] = self.usage
        return payload


@dataclass(frozen=True)
class AgentPreset:
    preset_id: str
    title: str
    provider_id: str
    task: str
    outputs: tuple[AgentOutputDeclaration, ...]
    constraints: tuple[str, ...] = ()
    scripts: tuple[AgentScriptSpec, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "preset_id": self.preset_id,
            "title": self.title,
            "provider_id": self.provider_id,
            "task": self.task,
            "outputs": [output.to_dict() for output in self.outputs],
            "constraints": list(self.constraints),
            "scripts": [script.to_dict() for script in self.scripts],
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
        "claude_cli": AgentProviderSpec(
            provider_id="claude_cli",
            label="Claude CLI",
            kind="cli",
            resource_key="agent_provider:claude_cli",
            default_max_concurrent=1,
            executable="claude",
            description="Claude CLI provider for file-backed Agent nodes.",
        ),
        "openclaw_cli": AgentProviderSpec(
            provider_id="openclaw_cli",
            label="OpenClaw CLI",
            kind="cli",
            resource_key="agent_provider:openclaw_cli",
            default_max_concurrent=1,
            executable="openclaw",
            description="OpenClaw provider for file-backed Agent nodes.",
        ),
        "hermes_cli": AgentProviderSpec(
            provider_id="hermes_cli",
            label="Hermes CLI",
            kind="cli",
            resource_key="agent_provider:hermes_cli",
            default_max_concurrent=1,
            executable="hermes",
            description="Hermes CLI provider for file-backed Agent nodes.",
        ),
    }


def run0_agent_preset() -> AgentPreset:
    return AgentPreset(
        preset_id="run0_element_refine",
        title="Run0 Element Refinement",
        provider_id="codex_sdk",
        task=RUN0_ELEMENT_REFINE_TASK,
        outputs=(
            AgentOutputDeclaration(
                port_id="elements",
                path="output/elements.json",
                format_id="drawai.element_plans.v1",
                type="element_plans",
                description="Run0 refined DrawAI element plans for asset materialization and SVG generation.",
            ),
        ),
        constraints=(*RUN0_ELEMENT_REFINE_CONSTRAINTS,),
        scripts=(
            AgentScriptSpec(
                script_id="assets_visualization",
                path="scripts/assets_visualization.py",
                description="Renders Run0 element-plan bbox JSON over the source image for visual QA iterations.",
                usage=(
                    "python {script} --image <image> --json <iteration_json> --output <png> "
                    "--summary-output <summary_json> --color-mode action --label-mode id_type"
                ),
            ),
        ),
    )


def page_spec_refine_agent_preset() -> AgentPreset:
    return AgentPreset(
        preset_id="page_spec_refine",
        title="PageSpec Refine",
        provider_id="codex_sdk",
        task=PAGE_SPEC_REFINE_TASK,
        outputs=(
            AgentOutputDeclaration(
                port_id="page_spec",
                path="output/page_spec.json",
                format_id="drawai.page_spec.v1",
                type="page_spec",
                description="Refined one-page PageSpec JSON. Elements are the source of truth; metadata.refine_changes is only an audit log.",
            ),
        ),
        constraints=(*PAGE_SPEC_REFINE_CONSTRAINTS,),
    )


def svg_agent_preset() -> AgentPreset:
    return AgentPreset(
        preset_id="svg_generation",
        title="SVG Generation",
        provider_id="codex_sdk",
        task=SVG_GENERATION_TASK,
        outputs=(
            AgentOutputDeclaration(
                port_id="semantic_svg",
                path="output/semantic.svg",
                format_id="drawai.semantic_svg.v1",
                type="semantic_svg",
                description="Editable semantic SVG rooted at an svg element.",
            ),
        ),
        constraints=(*SVG_GENERATION_CONSTRAINTS,),
    )


def custom_agent_preset() -> AgentPreset:
    return AgentPreset(
        preset_id="custom_agent",
        title="Custom Agent",
        provider_id="codex_sdk",
        task=CUSTOM_AGENT_TASK,
        outputs=(
            AgentOutputDeclaration(
                port_id="image",
                path="output/image.png",
                format_id="drawai.image.v1",
                type="image",
                description="Generated or edited image file.",
            ),
        ),
        constraints=(*CUSTOM_AGENT_CONSTRAINTS,),
    )


def agent_preset_by_id(preset_id: str) -> AgentPreset:
    if preset_id == "run0_element_refine":
        return run0_agent_preset()
    if preset_id == "page_spec_refine":
        return page_spec_refine_agent_preset()
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
    runtime_context: Mapping[str, Any] | None = None,
) -> AgentPrompt:
    config = dict(node_config or {})
    _validate_agent_config(config)
    runtime = _runtime_context(runtime_context)
    provider_id = str(config.get("provider_id") or preset.provider_id)
    selected_inputs = _selected_inputs(inputs, config)
    outputs = _configured_outputs(preset, config)
    options = _agent_options(config)
    scripts = _configured_scripts(preset, config, runtime)
    drawai_tools = _drawai_tools_for_inputs(_configured_drawai_tools(config), selected_inputs)
    text = _render_prompt_text(
        node_id=str(config.get("node_id") or "<agent_node_id>"),
        provider_id=provider_id,
        inputs=selected_inputs,
        outputs=outputs,
        options=options,
        task=_agent_task(preset, config),
        constraints=_agent_constraints(preset, config),
        scripts=scripts,
        drawai_tools=drawai_tools,
        runtime_context=runtime,
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
    *,
    node_id: str,
    provider_id: str,
    inputs: tuple[Mapping[str, Any], ...],
    outputs: tuple[Mapping[str, Any], ...],
    options: Mapping[str, Any],
    task: str,
    constraints: tuple[str, ...],
    scripts: tuple[Mapping[str, Any], ...],
    drawai_tools: tuple[str, ...],
    runtime_context: Mapping[str, str],
) -> str:
    workflow_run_root = (
        runtime_context.get("workflow_run_root") or "<workflow_run_root>"
    )
    node_workdir = (
        runtime_context.get("node_workdir")
        or f"{workflow_run_root}/nodes/{node_id}/runs/<attempt_id>"
    )
    agent_cwd = runtime_context.get("agent_cwd") or workflow_run_root
    repo_root = runtime_context.get("repo_root") or "<repository_root>"
    drawai_tool_command_prefix = (
        runtime_context.get("drawai_tool_command_prefix")
        or "<drawai_tool_command_prefix>"
    )
    lines = [
        "## Agent Runtime Settings",
        f"- Provider: {provider_id}",
        f"- Workflow run root: {workflow_run_root}",
        f"- Current node workdir: {node_workdir}",
        f"- Agent process cwd: {agent_cwd}",
        f"- Repository root: {repo_root}",
        f"- Node run manifest path: {node_workdir}/node_run.json",
    ]
    for key, value in options.items():
        lines.append(f"- {key}: {value}")

    lines.extend(
        [
            "",
            "## Task",
            task,
            "",
            "## Connected Input Files",
            (
                "Every connected input is listed below. Open only these files, using the "
                "path from the Agent cwd when possible. The Format and Type contracts below "
                "describe how to interpret each file."
            ),
        ]
    )
    if inputs:
        for item in inputs:
            source = _source_label(item)
            lines.extend(
                [
                    f"- Source: {source}",
                    f"  Format: {item.get('format_id') or 'unspecified'}",
                    f"  Type: {item.get('type') or 'unspecified'}",
                    f"  Run-root path: {item['path']}",
                    f"  Absolute path: {_input_absolute_path(item['path'], runtime_context)}",
                    f"  From Agent cwd: {_input_path_from_agent_cwd(item['path'], runtime_context)}",
                    f"  Description: {item.get('description') or 'No description supplied.'}",
                ]
            )
    else:
        lines.append("- No connected input files were provided.")

    lines.extend(
        [
            "",
            "## Declared Output Files",
            (
                "Write each declared output exactly; these are the semantic files consumed by downstream nodes. "
                "The Agent cwd is the workflow run root, so use the run-root path when creating outputs. "
                "When the task explicitly asks for render/report/log helper files, keep those auxiliary files "
                "inside the current node output directory. The harness records declared outputs in node_run.json after the run."
            ),
        ]
    )
    for output in outputs:
        final_run_root_path = _output_path_from_run_root(node_id, output["path"], runtime_context)
        lines.extend(
            [
                f"- Port: {output['port_id']}",
                f"  Format: {output['format_id']}",
                f"  Type: {output['type']}",
                f"  Node-output relative path: {output['path']}",
                f"  Write path from Agent cwd: {final_run_root_path}",
                f"  Final run-root path: {final_run_root_path}",
                f"  Final absolute path: {_output_absolute_path(node_id, output['path'], runtime_context)}",
                f"  Description: {output['description']}",
            ]
        )

    if scripts:
        lines.extend(
            [
                "",
                "## Built-in Script Files",
                (
                    "These scripts are explicitly available to this Agent node. Use them only when they help produce "
                    "the declared outputs, and keep all generated files inside the current node output directory unless an "
                    "output declaration says otherwise."
                ),
            ]
        )
        for script in scripts:
            usage = str(script.get("usage") or "").replace(
                "{script}",
                str(script.get("from_agent_cwd") or script.get("path") or ""),
            )
            lines.extend(
                [
                    f"- Script: {script['script_id']}",
                    f"  Repository path: {script['path']}",
                    f"  From Agent cwd: {script['from_agent_cwd']}",
                    f"  Description: {script['description']}",
                ]
            )
            if usage:
                lines.append(f"  Usage: {usage}")

    if drawai_tools:
        lines.extend(["", render_drawai_tool_prompt_section(drawai_tools, command_prefix=drawai_tool_command_prefix)])

    lines.extend(["", "## Type And Format Contracts"])
    format_contracts = default_format_contract_descriptions()
    for type_name in _ordered_unique(
        [str(item.get("type") or "") for item in inputs]
        + [str(output.get("type") or "") for output in outputs]
    ):
        lines.append(
            f"- Type `{type_name}`: {TYPE_CONTRACTS.get(type_name, 'No built-in type description is registered. Follow the node description and connected file contents.')}"
        )
    for format_id in _ordered_unique(
        [str(item.get("format_id") or "") for item in inputs]
        + [str(output.get("format_id") or "") for output in outputs]
    ):
        lines.append(
            f"- Format `{format_id}`: {format_contracts.get(format_id, 'No built-in format description is registered. Follow the node declaration and validate the file before returning.')}"
        )

    if constraints:
        lines.extend(["", "## Constraints"])
        for constraint in constraints:
            lines.append(f"- {constraint}")

    return "\n".join(lines).strip() + "\n"


def _input_path_from_agent_cwd(
    path: object, runtime_context: Mapping[str, str] | None = None
) -> str:
    path_value = str(path or "")
    if not path_value:
        return ""
    if path_value.startswith("/"):
        return path_value
    runtime = runtime_context or {}
    agent_cwd = runtime.get("agent_cwd") or runtime.get("workflow_run_root")
    workflow_run_root = runtime.get("workflow_run_root")
    if agent_cwd and workflow_run_root:
        return _relative_from_node_workdir(
            Path(workflow_run_root) / path_value, Path(agent_cwd)
        )
    return path_value.lstrip("./")


def _input_absolute_path(
    path: object, runtime_context: Mapping[str, str] | None = None
) -> str:
    path_value = str(path or "")
    if not path_value:
        return ""
    if path_value.startswith("/"):
        return path_value
    runtime = runtime_context or {}
    workflow_run_root = runtime.get("workflow_run_root")
    if workflow_run_root and not workflow_run_root.startswith("<"):
        return (
            (Path(workflow_run_root) / path_value)
            .expanduser()
            .resolve(strict=False)
            .as_posix()
        )
    return f"<workflow_run_root>/{path_value.lstrip('./')}"


def _output_path_from_run_root(
    node_id: str,
    path: object,
    runtime_context: Mapping[str, str] | None = None,
) -> str:
    path_value = str(path or "")
    if not path_value:
        return ""
    if path_value.startswith("/"):
        return path_value
    runtime = runtime_context or {}
    attempt_id = runtime.get("attempt_id") or "<attempt_id>"
    return f"nodes/{node_id}/runs/{attempt_id}/{path_value.lstrip('./')}"


def _output_absolute_path(
    node_id: str,
    path: object,
    runtime_context: Mapping[str, str] | None = None,
) -> str:
    path_value = str(path or "")
    if not path_value:
        return ""
    if path_value.startswith("/"):
        return path_value
    runtime = runtime_context or {}
    node_workdir = runtime.get("node_workdir")
    if node_workdir and not node_workdir.startswith("<"):
        return (
            (Path(node_workdir) / path_value)
            .expanduser()
            .resolve(strict=False)
            .as_posix()
        )
    return f"<workflow_run_root>/{_output_path_from_run_root(node_id, path_value, runtime_context)}"


def _relative_from_node_workdir(path: Path, node_workdir: Path) -> str:
    return os.path.relpath(
        Path(path).expanduser().resolve(strict=False),
        node_workdir.expanduser().resolve(strict=False),
    )


def _ordered_unique(values: Sequence[str]) -> tuple[str, ...]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        clean = value.strip()
        if not clean or clean in seen:
            continue
        ordered.append(clean)
        seen.add(clean)
    return tuple(ordered)


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
        outputs = tuple(output.to_dict() for output in preset.outputs)
        for index, output in enumerate(outputs):
            _validate_relative_output_path(str(output["path"]), f"outputs[{index}].path")
        return outputs
    if not isinstance(raw_outputs, list | tuple):
        raise ValueError("Agent outputs must be an array")
    outputs: list[Mapping[str, Any]] = []
    for index, raw_output in enumerate(raw_outputs):
        if not isinstance(raw_output, Mapping):
            raise ValueError(f"Agent outputs[{index}] must be an object")
        port_id = _required_string(raw_output.get("port_id"), f"outputs[{index}].port_id")
        format_id = _required_string(
            raw_output.get("format_id"), f"outputs[{index}].format_id"
        )
        output_path = _default_output_path(port_id, format_id)
        _validate_relative_output_path(output_path, f"outputs[{index}].path")
        outputs.append(
            {
                "port_id": port_id,
                "path": output_path,
                "format_id": format_id,
                "type": _type_for_format(
                    format_id,
                    raw_output.get("type"),
                    f"outputs[{index}].type",
                ),
                "description": _required_string(
                    raw_output.get("description"),
                    f"outputs[{index}].description",
                ),
            }
        )
    return tuple(outputs)


def _type_for_format(format_id: str, fallback: object, field_name: str) -> str:
    spec = default_format_registry().get(format_id)
    if spec is not None:
        return spec.artifact_type
    return _required_string(fallback, field_name)


def _default_output_path(port_id: str, format_id: str) -> str:
    return f"output/{_safe_output_stem(port_id)}.{_extension_for_format(format_id)}"


def _safe_output_stem(value: str) -> str:
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789_")
    stem = "".join(
        char if char in allowed else "_" for char in value.strip().lower()
    )
    stem = stem.strip("_")
    return stem or "output"


def _extension_for_format(format_id: str) -> str:
    if "svg" in format_id:
        return "svg"
    if "pptx" in format_id:
        return "pptx"
    if "image" in format_id:
        return "png"
    return "json"


def _configured_scripts(
    preset: AgentPreset,
    config: Mapping[str, Any],
    runtime_context: Mapping[str, str],
) -> tuple[Mapping[str, Any], ...]:
    raw_scripts = config.get("scripts")
    if raw_scripts is None:
        scripts: list[Mapping[str, Any]] = [
            script.to_dict() for script in preset.scripts
        ]
    else:
        if not isinstance(raw_scripts, list | tuple):
            raise ValueError("Agent scripts must be an array")
        scripts = []
        for index, raw_script in enumerate(raw_scripts):
            if not isinstance(raw_script, Mapping):
                raise ValueError(f"Agent scripts[{index}] must be an object")
            scripts.append(raw_script)

    normalized: list[Mapping[str, Any]] = []
    for index, script in enumerate(scripts):
        script_id = _required_string(
            script.get("script_id") or script.get("id"), f"scripts[{index}].script_id"
        )
        path = _required_string(script.get("path"), f"scripts[{index}].path")
        description = _required_string(
            script.get("description"), f"scripts[{index}].description"
        )
        usage = str(script.get("usage") or "")
        resolved_path = _script_path_for_prompt(path, runtime_context)
        agent_cwd = runtime_context.get("agent_cwd") or runtime_context.get("workflow_run_root")
        from_agent_cwd = (
            _relative_from_node_workdir(Path(resolved_path), Path(agent_cwd))
            if agent_cwd and Path(resolved_path).is_absolute()
            else resolved_path
        )
        normalized.append(
            {
                "script_id": script_id,
                "path": resolved_path,
                "description": description,
                "usage": usage,
                "from_agent_cwd": from_agent_cwd,
            }
        )
    return tuple(normalized)


def _script_path_for_prompt(path: str, runtime_context: Mapping[str, str]) -> str:
    path_obj = Path(path)
    if path_obj.is_absolute():
        return path_obj.as_posix()
    repo_root = runtime_context.get("repo_root")
    if repo_root and not repo_root.startswith("<"):
        return (
            (Path(repo_root) / path_obj).expanduser().resolve(strict=False).as_posix()
        )
    return path_obj.as_posix()


def _runtime_context(runtime_context: Mapping[str, Any] | None) -> Mapping[str, str]:
    raw = dict(runtime_context or {})
    normalized: dict[str, str] = {}
    for key in (
        "workflow_run_root",
        "node_workdir",
        "agent_cwd",
        "repo_root",
        "attempt_id",
        "drawai_tool_command_prefix",
    ):
        value = raw.get(key)
        if value not in (None, ""):
            normalized[key] = str(value)
    return normalized


def _validate_agent_config(config: Mapping[str, Any]) -> None:
    for key in DANGEROUS_AGENT_CONFIG_KEYS:
        if key in config:
            raise ValueError(f"Agent node config cannot override {key}")
    if config.get("reasoning_effort") not in (None, ""):
        effort = str(config["reasoning_effort"]).strip().lower()
        if effort not in SUPPORTED_REASONING_EFFORTS:
            raise ValueError(f"unsupported reasoning_effort: {effort}")
    if config.get("timeout_seconds") not in (None, ""):
        timeout = config["timeout_seconds"]
        if (
            not isinstance(timeout, int | float)
            or isinstance(timeout, bool)
            or timeout <= 0
        ):
            raise ValueError("timeout_seconds must be positive")
    for field_name in ("model", "profile", "provider_id"):
        if field_name in config and not isinstance(config[field_name], str):
            raise ValueError(f"{field_name} must be a string")
    if "drawai_tools" in config and not isinstance(config["drawai_tools"], list | tuple):
        raise ValueError("drawai_tools must be an array of tool ids")


def _agent_options(config: Mapping[str, Any]) -> Mapping[str, Any]:
    options: dict[str, Any] = {}
    for key in ("model", "profile", "timeout_seconds", "reasoning_effort"):
        if key in config and config[key] not in (None, ""):
            options[key] = config[key]
    return options


def _configured_drawai_tools(config: Mapping[str, Any]) -> tuple[str, ...]:
    raw_tools = config.get("drawai_tools")
    tool_ids: list[str] = ["format"]
    if raw_tools is not None:
        for index, raw_tool in enumerate(raw_tools):
            if not isinstance(raw_tool, str) or not raw_tool.strip():
                raise ValueError(f"drawai_tools[{index}] must be a non-empty string")
            tool_ids.append(raw_tool.strip())
    return _ordered_unique(tool_ids)


PAGE_SPEC_ONLY_DRAWAI_TOOLS = frozenset({"page-spec-assets", "svg-validate"})


def _drawai_tools_for_inputs(
    tool_ids: Sequence[str],
    inputs: Sequence[Mapping[str, Any]],
) -> tuple[str, ...]:
    has_page_spec = any(
        str(item.get("type") or "") == "page_spec"
        or str(item.get("format_id") or "") == "drawai.page_spec.v1"
        for item in inputs
    )
    if has_page_spec:
        return tuple(tool_ids)
    return tuple(tool_id for tool_id in tool_ids if tool_id not in PAGE_SPEC_ONLY_DRAWAI_TOOLS)


def _agent_task(preset: AgentPreset, config: Mapping[str, Any]) -> str:
    raw = (
        config.get("task")
        or config.get("prompt_role")
        or config.get("prompt_fragments")
        or config.get("user_prompt")
        or preset.task
    )
    if not isinstance(raw, str):
        raise ValueError("Agent task must be a string")
    task = raw.strip()
    if not task:
        raise ValueError("Agent task must be non-empty")
    return task


def _agent_constraints(
    preset: AgentPreset, config: Mapping[str, Any]
) -> tuple[str, ...]:
    raw = config.get("constraints")
    if raw is None:
        return tuple(preset.constraints)
    if raw == "":
        return ()
    if isinstance(raw, str):
        return tuple(line.strip() for line in raw.splitlines() if line.strip())
    if not isinstance(raw, list | tuple):
        raise ValueError("Agent constraints must be a string or array of strings")
    constraints: list[str] = []
    for index, item in enumerate(raw):
        if not isinstance(item, str):
            raise ValueError(f"Agent constraints[{index}] must be a string")
        constraint = item.strip()
        if constraint:
            constraints.append(constraint)
    return tuple(constraints)


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


def _validate_relative_output_path(value: str, field_name: str) -> None:
    if Path(value).is_absolute():
        raise ValueError(f"{field_name} must be relative to the Agent node workdir")
    normalized = normpath(value.replace("\\", "/"))
    if normalized in {"", ".", ".."} or normalized.startswith("../"):
        raise ValueError(f"{field_name} must stay inside the Agent node workdir")
