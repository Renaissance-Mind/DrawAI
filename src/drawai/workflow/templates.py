from __future__ import annotations

import json
import re
from dataclasses import replace
from pathlib import Path
from typing import Any, Literal, Mapping

from ..prompt_plan import DEFAULT_SAM3_PROMPTS
from .agent_prompt_defaults import (
    CUSTOM_AGENT_CONSTRAINTS,
    CUSTOM_AGENT_TASK,
    RUN0_ELEMENT_REFINE_CONSTRAINTS,
    RUN0_ELEMENT_REFINE_TASK,
    SVG_GENERATION_CONSTRAINTS,
    SVG_GENERATION_TASK,
)
from .agents import DEFAULT_AGENT_TIMEOUT_SECONDS
from .schema import (
    WORKFLOW_TEMPLATE_SCHEMA,
    WorkflowEdge,
    WorkflowNode,
    WorkflowPort,
    WorkflowTemplate,
)
from .validation import validate_workflow_template

DEFAULT_WORKFLOW_TEMPLATE_ID = "default_drawai_dag"
_BUILTIN_TEMPLATE_IDS = (DEFAULT_WORKFLOW_TEMPLATE_ID,)


def default_drawai_workflow_template() -> WorkflowTemplate:
    return WorkflowTemplate(
        template_id=DEFAULT_WORKFLOW_TEMPLATE_ID,
        name="Image-to-PPTX",
        description="Built-in workflow that mirrors the current DrawAI v2 path.",
        nodes=(
            WorkflowNode(
                node_id="input",
                node_type="input",
                title="Input",
                outputs=(
                    _output("image", "Image", ("image",), formats=("drawai.image.v1",)),
                ),
                position={"x": 0, "y": 160},
            ),
            WorkflowNode(
                node_id="sam_parser",
                node_type="parser",
                title="SAM Parser",
                inputs=(_input("image", "Image", ("image",)),),
                outputs=(
                    _output(
                        "candidates",
                        "Candidates",
                        ("element_candidates",),
                        formats=("drawai.element_candidates.v1",),
                    ),
                ),
                config={
                    "parser_id": "sam3_structure_parser",
                    "resource": "sam3",
                    "prompts": _sam3_prompt_configs(),
                },
                position={"x": 240, "y": 80},
            ),
            WorkflowNode(
                node_id="ocr_parser",
                node_type="parser",
                title="OCR Parser",
                inputs=(_input("image", "Image", ("image",)),),
                outputs=(
                    _output(
                        "candidates",
                        "Candidates",
                        ("element_candidates",),
                        formats=("drawai.element_candidates.v1",),
                    ),
                ),
                config={"parser_id": "ocr_text_parser", "resource": "ocr"},
                position={"x": 240, "y": 240},
            ),
            WorkflowNode(
                node_id="fusion",
                node_type="fusion",
                title="Fusion",
                inputs=(
                    _input(
                        "candidates",
                        "Candidates",
                        ("element_candidates",),
                        cardinality="many",
                    ),
                ),
                outputs=(
                    _output(
                        "elements",
                        "Element Plans",
                        ("element_plans",),
                        formats=("drawai.element_plans.v1",),
                    ),
                ),
                config={"fusion_id": "priority_nms"},
                position={"x": 500, "y": 160},
            ),
            WorkflowNode(
                node_id="run0_agent",
                node_type="agent",
                title="Asset Refine Agent",
                inputs=(
                    _input("image", "Image", ("image",), formats=("drawai.image.v1",)),
                    _input("elements", "Element Plans", ("element_plans",)),
                ),
                outputs=(
                    _output(
                        "analysis",
                        "Element Analysis",
                        ("element_analysis",),
                        formats=("drawai.codex_element_analysis.v1",),
                    ),
                ),
                config={
                    "preset_id": "run0_element_refine",
                    "provider_id": "codex_sdk",
                    "reasoning_effort": "high",
                    "timeout_seconds": DEFAULT_AGENT_TIMEOUT_SECONDS,
                    "task": RUN0_ELEMENT_REFINE_TASK,
                    "constraints": list(RUN0_ELEMENT_REFINE_CONSTRAINTS),
                    "outputs": [
                        {
                            "port_id": "analysis",
                            "path": "output/element_analysis.json",
                            "format_id": "drawai.codex_element_analysis.v1",
                            "type": "element_analysis",
                            "description": "Run0 refined asset/source analysis in the standard DrawAI Codex element analysis JSON format.",
                        }
                    ],
                },
                position={"x": 760, "y": 160},
            ),
            WorkflowNode(
                node_id="asset_planner",
                node_type="processor",
                title="Asset Planner",
                inputs=(_input("analysis", "Element Analysis", ("element_analysis",)),),
                outputs=(
                    _output(
                        "elements",
                        "Planned Elements",
                        ("element_plans",),
                        formats=("drawai.element_plans.v1",),
                    ),
                ),
                config={"processor_id": "asset_planner"},
                position={"x": 1020, "y": 160},
            ),
            WorkflowNode(
                node_id="asset_processors",
                node_type="processor",
                title="Asset Processors",
                inputs=(_input("elements", "Planned Elements", ("element_plans",)),),
                outputs=(
                    _output(
                        "asset_packages",
                        "Asset Packages",
                        ("asset_packages",),
                        formats=("drawai.asset_packages.v1",),
                    ),
                ),
                config={"processor_id": "asset_processors"},
                position={"x": 1280, "y": 160},
            ),
            WorkflowNode(
                node_id="asset_confirm",
                node_type="human_review",
                title="Asset Confirm",
                inputs=(
                    _input(
                        "asset_packages",
                        "Asset Packages",
                        ("asset_packages",),
                    ),
                ),
                outputs=(
                    _output(
                        "asset_packages",
                        "Confirmed Asset Packages",
                        ("asset_packages",),
                        formats=("drawai.asset_packages.v1",),
                    ),
                ),
                config={
                    "review_surface": "assets",
                    "result_path": "output/confirmed_asset_packages.json",
                },
                position={"x": 1540, "y": 80},
            ),
            WorkflowNode(
                node_id="svg_agent",
                node_type="agent",
                title="SVG Agent",
                inputs=(
                    _input("elements", "Element Plans", ("element_plans",)),
                    _input("asset_packages", "Asset Packages", ("asset_packages",)),
                ),
                outputs=(
                    _output(
                        "semantic_svg",
                        "Semantic SVG",
                        ("semantic_svg",),
                        formats=("drawai.semantic_svg.v1",),
                        deliverable=True,
                    ),
                ),
                config={
                    "preset_id": "svg_generation",
                    "provider_id": "codex_sdk",
                    "timeout_seconds": DEFAULT_AGENT_TIMEOUT_SECONDS,
                    "task": SVG_GENERATION_TASK,
                    "constraints": list(SVG_GENERATION_CONSTRAINTS),
                    "outputs": [
                        {
                            "port_id": "semantic_svg",
                            "path": "output/semantic.svg",
                            "format_id": "drawai.semantic_svg.v1",
                            "type": "semantic_svg",
                            "description": "Editable semantic SVG rooted at an svg element.",
                        }
                    ],
                },
                position={"x": 1540, "y": 260},
            ),
            WorkflowNode(
                node_id="svg_to_ppt",
                node_type="export",
                title="SVG to PPT",
                inputs=(_input("semantic_svg", "Semantic SVG", ("semantic_svg",)),),
                outputs=(
                    _output(
                        "pptx",
                        "PPTX",
                        ("pptx",),
                        formats=("drawai.pptx.v1",),
                        deliverable=True,
                    ),
                ),
                config={"exporter_id": "svg_to_ppt"},
                position={"x": 1800, "y": 260},
            ),
            WorkflowNode(
                node_id="output",
                node_type="output",
                title="Output",
                inputs=(
                    _input(
                        "deliverables",
                        "Deliverables",
                        ("semantic_svg", "pptx"),
                        cardinality="many",
                    ),
                ),
                outputs=(
                    _output(
                        "final_outputs",
                        "Final Outputs",
                        ("final_outputs",),
                        formats=("drawai.final_outputs.v1",),
                    ),
                ),
                config={"auto_collect_deliverables": True},
                position={"x": 2060, "y": 180},
            ),
        ),
        edges=(
            _edge("input", "image", "sam_parser", "image"),
            _edge("input", "image", "ocr_parser", "image"),
            _edge("sam_parser", "candidates", "fusion", "candidates"),
            _edge("ocr_parser", "candidates", "fusion", "candidates"),
            _edge("input", "image", "run0_agent", "image"),
            _edge("fusion", "elements", "run0_agent", "elements"),
            _edge("run0_agent", "analysis", "asset_planner", "analysis"),
            _edge("asset_planner", "elements", "asset_processors", "elements"),
            _edge("asset_planner", "elements", "svg_agent", "elements"),
            _edge("asset_processors", "asset_packages", "asset_confirm", "asset_packages"),
            _edge("asset_confirm", "asset_packages", "svg_agent", "asset_packages"),
            _edge("svg_agent", "semantic_svg", "svg_to_ppt", "semantic_svg"),
            _edge("svg_agent", "semantic_svg", "output", "deliverables"),
            _edge("svg_to_ppt", "pptx", "output", "deliverables"),
        ),
        defaults={
            "builtin": True,
            "read_only": True,
            "agent_provider_id": "codex_sdk",
        },
    )


def workflow_templates_dir(workspace: str | Path) -> Path:
    return Path(workspace).expanduser().resolve(strict=False) / ".drawai" / "workflows"


def user_workflow_template_path(workspace: str | Path, template_id: str) -> Path:
    return workflow_templates_dir(workspace) / f"{_safe_template_id(template_id)}.json"


def builtin_workflow_templates() -> tuple[WorkflowTemplate, ...]:
    return (default_drawai_workflow_template(),)


def load_workflow_template_by_id(workspace: str | Path, template_id: str) -> WorkflowTemplate:
    if template_id in _BUILTIN_TEMPLATE_IDS:
        return _builtin_workflow_template(template_id)
    return load_workflow_template(user_workflow_template_path(workspace, template_id))


def list_workflow_templates(
    workspace: str | Path,
    *,
    include_builtin: bool = True,
) -> tuple[WorkflowTemplate, ...]:
    templates: list[WorkflowTemplate] = []
    if include_builtin:
        templates.extend(builtin_workflow_templates())

    directory = workflow_templates_dir(workspace)
    if directory.exists():
        for path in sorted(directory.glob("*.json")):
            template = load_workflow_template(path)
            if template.template_id not in {item.template_id for item in templates}:
                templates.append(template)
    return tuple(templates)


def load_workflow_template(path: str | Path) -> WorkflowTemplate:
    payload = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"workflow template must be a JSON object: {path}")
    template = workflow_template_from_dict(payload)
    _raise_if_invalid(template)
    return template


def save_workflow_template(
    workspace: str | Path,
    template: WorkflowTemplate,
    *,
    overwrite: bool = True,
    validate: bool = True,
) -> Path:
    if validate:
        _raise_if_invalid(template)
    path = user_workflow_template_path(workspace, template.template_id)
    if path.exists() and not overwrite:
        raise FileExistsError(f"workflow template already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(template.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def copy_builtin_template_to_workspace(
    workspace: str | Path,
    template_id: str,
    *,
    name: str,
    overwrite: bool = True,
) -> WorkflowTemplate:
    template = copy_builtin_template(template_id, name=name)
    save_workflow_template(workspace, template, overwrite=overwrite)
    return template


def copy_builtin_template(template_id: str, *, name: str) -> WorkflowTemplate:
    if template_id != DEFAULT_WORKFLOW_TEMPLATE_ID:
        raise ValueError(f"unknown built-in workflow template: {template_id}")
    copied_id = f"custom_{_safe_template_id(name).replace('-', '_')}"
    defaults = dict(default_drawai_workflow_template().defaults)
    defaults["builtin"] = False
    defaults["read_only"] = False
    defaults["source_template_id"] = template_id
    return replace(
        default_drawai_workflow_template(),
        template_id=copied_id,
        name=name,
        defaults=defaults,
    )


def workflow_template_from_dict(payload: Mapping[str, Any]) -> WorkflowTemplate:
    schema = _string(payload.get("schema", WORKFLOW_TEMPLATE_SCHEMA), "schema")
    if schema != WORKFLOW_TEMPLATE_SCHEMA:
        raise ValueError(f"unsupported workflow template schema: {schema}")
    return WorkflowTemplate(
        schema=schema,
        template_id=_string(payload.get("template_id"), "template_id"),
        name=_string(payload.get("name"), "name"),
        description=_string(payload.get("description", ""), "description"),
        version=_integer(payload.get("version", 1), "version"),
        nodes=tuple(_node_from_dict(item, f"nodes[{index}]") for index, item in enumerate(_sequence(payload.get("nodes"), "nodes"))),
        edges=tuple(_edge_from_dict(item, f"edges[{index}]") for index, item in enumerate(_sequence(payload.get("edges"), "edges"))),
        defaults=dict(_mapping(payload.get("defaults", {}), "defaults")),
    )


def _builtin_workflow_template(template_id: str) -> WorkflowTemplate:
    if template_id == DEFAULT_WORKFLOW_TEMPLATE_ID:
        return default_drawai_workflow_template()
    raise ValueError(f"unknown built-in workflow template: {template_id}")


def _sam3_prompt_configs() -> list[dict[str, Any]]:
    return [
        {
            "id": prompt.id,
            "text": prompt.text,
            "confidence_threshold": prompt.confidence_threshold,
        }
        for prompt in DEFAULT_SAM3_PROMPTS
    ]


def _node_from_dict(payload: object, field_name: str) -> WorkflowNode:
    data = _mapping(payload, field_name)
    node_type = _string(data.get("node_type"), f"{field_name}.node_type")
    config = dict(_mapping(data.get("config", {}), f"{field_name}.config"))
    config = _normalized_node_config(node_type, config)
    title = _normalized_node_title(
        node_type,
        _string(data.get("title"), f"{field_name}.title"),
        config,
    )
    return WorkflowNode(
        node_id=_string(data.get("node_id"), f"{field_name}.node_id"),
        node_type=node_type,
        title=title,
        inputs=tuple(
            _port_from_dict(item, f"{field_name}.inputs[{index}]")
            for index, item in enumerate(_sequence(data.get("inputs", ()), f"{field_name}.inputs"))
        ),
        outputs=tuple(
            _port_from_dict(item, f"{field_name}.outputs[{index}]")
            for index, item in enumerate(_sequence(data.get("outputs", ()), f"{field_name}.outputs"))
        ),
        config=config,
        position=_number_mapping(data.get("position", {}), f"{field_name}.position"),
        description=_string(data.get("description", ""), f"{field_name}.description"),
    )


_LEGACY_AGENT_TASK_TEXTS: dict[str, set[str]] = {
    "run0_element_refine": {
        "Refine element bbox, size, and type. Preserve IDs unless merge/delete is declared.",
        "Refine element positions, types, and processing intent.",
        "Refine element positions, sizes, and object types from connected parser or fusion outputs. Preserve the DrawAI element plan format.",
    },
    "svg_generation": {
        "Generate an editable SVG using connected element plans and confirmed assets.",
        "Generate editable semantic SVG from element plans and asset packages.",
        "Generate an editable semantic SVG from connected element plans and asset packages. Preserve raster assets only through declared package references.",
    },
    "custom_agent": {
        "Use the connected files as context and write the declared outputs exactly.",
        "Use the connected input files as context and produce exactly the output files declared by this node configuration.",
    },
}

_AGENT_TASK_DEFAULTS = {
    "run0_element_refine": RUN0_ELEMENT_REFINE_TASK,
    "svg_generation": SVG_GENERATION_TASK,
    "custom_agent": CUSTOM_AGENT_TASK,
}

_AGENT_CONSTRAINT_DEFAULTS = {
    "run0_element_refine": RUN0_ELEMENT_REFINE_CONSTRAINTS,
    "svg_generation": SVG_GENERATION_CONSTRAINTS,
    "custom_agent": CUSTOM_AGENT_CONSTRAINTS,
}


def _normalized_node_config(node_type: str, config: dict[str, Any]) -> dict[str, Any]:
    if node_type != "agent":
        return config
    preset_id = str(config.get("preset_id") or "")
    default_task = _AGENT_TASK_DEFAULTS.get(preset_id)
    if default_task is None:
        return config
    normalized = dict(config)
    raw_task = _config_text(
        normalized.get("task")
        or normalized.get("prompt_role")
        or normalized.get("prompt_fragments")
        or normalized.get("user_prompt")
    )
    if not raw_task or raw_task in _LEGACY_AGENT_TASK_TEXTS.get(preset_id, set()):
        normalized["task"] = default_task
        normalized.pop("prompt_role", None)
        normalized.pop("prompt_fragments", None)
    raw_constraints = normalized.get("constraints")
    if raw_constraints in (None, "", []):
        normalized["constraints"] = list(_AGENT_CONSTRAINT_DEFAULTS[preset_id])
    if preset_id == "run0_element_refine":
        normalized.setdefault("reasoning_effort", "high")
    if preset_id in _AGENT_TASK_DEFAULTS:
        normalized.setdefault("timeout_seconds", DEFAULT_AGENT_TIMEOUT_SECONDS)
    return normalized


def _config_text(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list | tuple):
        return "\n\n".join(item.strip() for item in value if isinstance(item, str)).strip()
    return ""


def _normalized_node_title(
    node_type: str,
    title: str,
    config: Mapping[str, Any],
) -> str:
    if (
        node_type == "agent"
        and config.get("preset_id") == "run0_element_refine"
        and title in {"Run0 Agent", "Run0 元素校正"}
    ):
        return "Asset Refine Agent"
    return title


def _port_from_dict(payload: object, field_name: str) -> WorkflowPort:
    data = _mapping(payload, field_name)
    cardinality = _string(data.get("cardinality", "single"), f"{field_name}.cardinality")
    if cardinality not in {"single", "many"}:
        raise ValueError(f"{field_name}.cardinality must be single or many")
    return WorkflowPort(
        port_id=_string(data.get("port_id"), f"{field_name}.port_id"),
        label=_string(data.get("label"), f"{field_name}.label"),
        types=_string_tuple(data.get("types"), f"{field_name}.types"),
        required=_boolean(data.get("required", True), f"{field_name}.required"),
        cardinality=cardinality,  # type: ignore[arg-type]
        formats=_string_tuple(data.get("formats", ()), f"{field_name}.formats"),
        description=_string(data.get("description", ""), f"{field_name}.description"),
    )


def _edge_from_dict(payload: object, field_name: str) -> WorkflowEdge:
    data = _mapping(payload, field_name)
    return WorkflowEdge(
        edge_id=_string(data.get("edge_id"), f"{field_name}.edge_id"),
        source_node_id=_string(data.get("source_node_id"), f"{field_name}.source_node_id"),
        source_port_id=_string(data.get("source_port_id"), f"{field_name}.source_port_id"),
        target_node_id=_string(data.get("target_node_id"), f"{field_name}.target_node_id"),
        target_port_id=_string(data.get("target_port_id"), f"{field_name}.target_port_id"),
        enabled_types=_string_tuple(data.get("enabled_types", ()), f"{field_name}.enabled_types"),
    )


def _raise_if_invalid(template: WorkflowTemplate) -> None:
    result = validate_workflow_template(template)
    if not result.ok:
        codes = ", ".join(error.code for error in result.errors)
        raise ValueError(f"workflow template is invalid: {codes}")


def _input(
    port_id: str,
    label: str,
    types: tuple[str, ...],
    *,
    cardinality: str = "single",
    formats: tuple[str, ...] = (),
) -> WorkflowPort:
    return WorkflowPort(
        port_id=port_id,
        label=label,
        types=types,
        required=True,
        cardinality=cardinality,  # type: ignore[arg-type]
        formats=formats,
    )


def _output(
    port_id: str,
    label: str,
    types: tuple[str, ...],
    *,
    formats: tuple[str, ...] = (),
    deliverable: bool = False,
) -> WorkflowPort:
    description = "deliverable" if deliverable else ""
    return WorkflowPort(
        port_id=port_id,
        label=label,
        types=types,
        required=False,
        formats=formats,
        description=description,
    )


def _edge(
    source_node_id: str,
    source_port_id: str,
    target_node_id: str,
    target_port_id: str,
) -> WorkflowEdge:
    return WorkflowEdge(
        edge_id=f"{source_node_id}:{source_port_id}->{target_node_id}:{target_port_id}",
        source_node_id=source_node_id,
        source_port_id=source_port_id,
        target_node_id=target_node_id,
        target_port_id=target_port_id,
    )


def _safe_template_id(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", value.strip()).strip("_").lower()
    if not slug:
        raise ValueError("template id must contain at least one safe character")
    return slug


def _mapping(value: object, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be an object")
    return value


def _sequence(value: object, field_name: str) -> tuple[object, ...]:
    if not isinstance(value, list | tuple):
        raise ValueError(f"{field_name} must be an array")
    return tuple(value)


def _string(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    return value


def _string_tuple(value: object, field_name: str) -> tuple[str, ...]:
    items = _sequence(value, field_name)
    strings: list[str] = []
    for index, item in enumerate(items):
        if not isinstance(item, str):
            raise ValueError(f"{field_name}[{index}] must be a string")
        strings.append(item)
    return tuple(strings)


def _boolean(value: object, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be a boolean")
    return value


def _integer(value: object, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{field_name} must be an integer")
    return value


def _number_mapping(value: object, field_name: str) -> Mapping[str, float]:
    data = _mapping(value, field_name)
    result: dict[str, float] = {}
    for key, item in data.items():
        if not isinstance(key, str):
            raise ValueError(f"{field_name} keys must be strings")
        if not isinstance(item, int | float) or isinstance(item, bool):
            raise ValueError(f"{field_name}.{key} must be numeric")
        result[key] = float(item)
    return result
