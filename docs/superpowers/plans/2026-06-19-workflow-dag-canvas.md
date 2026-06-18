# Workflow DAG Canvas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace DrawAI's fixed v2 linear pipeline with an editable workflow DAG, a Workbench `Workflow` canvas, node-owned run directories, and CLI/Workbench verification against v1-style outputs.

**Architecture:** Add a `drawai.workflow` backend package for workflow templates, typed ports, format validation, node run manifests, default templates, and execution. Then wire it into CLI, Workbench API, Workbench React UI, and the existing runner/resource queues while preserving compatibility mirrors for current SVG/PPTX consumers.

**Tech Stack:** Python 3.12 dataclasses and stdlib JSON/XML/zip validation, existing DrawAI v2 schemas and Workbench store/runner, FastAPI, React 19, TypeScript, Vite, `@xyflow/react`, pytest, npm build, Playwright/browser automation for final Workbench checks.

---

## File Structure

Create focused backend files:

- `src/drawai/workflow/__init__.py`: public exports for workflow contracts.
- `src/drawai/workflow/schema.py`: dataclasses and payload parsers for templates, nodes, ports, edges, artifacts, node runs, and validation errors.
- `src/drawai/workflow/formats.py`: built-in format registry and validators for image, element candidates, element plans, asset packages, semantic SVG, PPTX, and final outputs.
- `src/drawai/workflow/templates.py`: built-in `Default DrawAI DAG`, template serialization, local template paths, and template copy helpers.
- `src/drawai/workflow/validation.py`: graph validation, type compatibility, required input satisfaction, cardinality, cycle detection, and edge output filtering.
- `src/drawai/workflow/node_runs.py`: node workdir creation, `input_manifest.json`, `node_run.json`, safe path resolution, status transitions, and stale markers.
- `src/drawai/workflow/runner.py`: DAG runner orchestration, resource/provider acquisition hooks, fixed node dispatch, Agent node dispatch, Output finalization, and compatibility mirrors.
- `src/drawai/workflow/agents.py`: Agent provider contracts, prompt rendering, safe overrides, preset Agent nodes for Run0 and SVG.
- `src/drawai/workflow/cli.py`: workflow CLI subcommands.

Modify backend integration files:

- `src/drawai/cli.py`: route `drawai workflow ...`.
- `src/drawai/workbench/models.py`: add workflow settings fields to API records where needed.
- `src/drawai/workbench/store.py`: persist batch workflow binding and Workbench default workflow setting.
- `src/drawai/workbench/runner.py`: submit workflow runs, expose provider/resource activity keyed by real provider ids, and keep old entrypoints mapped during transition.
- `src/drawai/workbench/api.py`: template CRUD, validation, batch binding, snapshot retrieval, node run inspection, and rerun endpoints.
- `src/drawai/artifacts.py` or `src/drawai/v2/packages.py`: only if compatibility mirror registration needs shared helpers.

Create focused frontend files:

- `apps/workbench/src/workflowTypes.ts`: TypeScript interfaces matching workflow JSON and node run payloads.
- `apps/workbench/src/workflowApi.ts`: API client functions for templates, validation, binding, snapshots, node runs, and rerun.
- `apps/workbench/src/WorkflowWorkspace.tsx`: top-level `Workflow` tab with React Flow canvas and panels.
- `apps/workbench/src/WorkflowRunView.tsx`: case-level workflow snapshot/run inspection.
- `apps/workbench/src/workflowCanvas.css`: workflow canvas styles.

Modify frontend integration files:

- `apps/workbench/package.json` and `apps/workbench/package-lock.json`: add `@xyflow/react`.
- `apps/workbench/src/App.tsx`: add top-level `Workflow` tab, processing-page template binding controls, and Workflow Run View entry.
- `apps/workbench/src/api.ts` and `apps/workbench/src/types.ts`: only for shared existing API types that cannot stay in `workflowApi.ts`.
- `apps/workbench/src/styles.css`: shared tab and processing-page integration styles.

Create tests:

- `tests/workflow/test_formats.py`
- `tests/workflow/test_schema_validation.py`
- `tests/workflow/test_templates.py`
- `tests/workflow/test_node_runs.py`
- `tests/workflow/test_runner_contract.py`
- `tests/workflow/test_cli.py`
- `tests/workbench/test_workflow_api.py`
- `apps/workbench/src` type/build checks via `npm run build`.
- End-to-end scripts or pytest helpers under `tests/workflow/test_e2e_contracts.py` for CLI/provider/v1 comparison gates.

## Task 1: Workflow Schema, Types, And Validation Foundation

**Files:**
- Create: `src/drawai/workflow/__init__.py`
- Create: `src/drawai/workflow/schema.py`
- Create: `src/drawai/workflow/validation.py`
- Test: `tests/workflow/test_schema_validation.py`

- [ ] **Step 1: Write failing schema and graph validation tests**

Create `tests/workflow/test_schema_validation.py` with:

```python
from __future__ import annotations

import pytest

from drawai.workflow.schema import (
    WorkflowEdge,
    WorkflowNode,
    WorkflowPort,
    WorkflowTemplate,
)
from drawai.workflow.validation import validate_workflow_template


def _port(port_id: str, types: tuple[str, ...], *, required: bool = True, cardinality: str = "single") -> WorkflowPort:
    return WorkflowPort(
        port_id=port_id,
        label=port_id,
        types=types,
        required=required,
        cardinality=cardinality,
    )


def test_valid_workflow_accepts_type_compatible_edges() -> None:
    template = WorkflowTemplate(
        template_id="tpl_valid",
        name="Valid",
        nodes=(
            WorkflowNode(
                node_id="input",
                node_type="input",
                title="Input",
                outputs=(_port("image", ("image",), required=False),),
            ),
            WorkflowNode(
                node_id="agent",
                node_type="agent",
                title="Agent",
                inputs=(_port("in", ("image",), cardinality="single"),),
                outputs=(_port("out", ("element_candidates",), required=False),),
            ),
            WorkflowNode(
                node_id="fusion",
                node_type="fusion",
                title="Fusion",
                inputs=(_port("candidates", ("element_candidates",), cardinality="many"),),
                outputs=(_port("elements", ("element_plans",), required=False),),
            ),
        ),
        edges=(
            WorkflowEdge(edge_id="e1", source_node_id="input", source_port_id="image", target_node_id="agent", target_port_id="in"),
            WorkflowEdge(edge_id="e2", source_node_id="agent", source_port_id="out", target_node_id="fusion", target_port_id="candidates"),
        ),
    )

    result = validate_workflow_template(template)

    assert result.ok
    assert result.errors == ()


def test_rejects_edge_with_no_type_overlap() -> None:
    template = WorkflowTemplate(
        template_id="tpl_bad_edge",
        name="Bad Edge",
        nodes=(
            WorkflowNode(
                node_id="parser",
                node_type="parser",
                title="Parser",
                outputs=(_port("candidates", ("element_candidates",), required=False),),
            ),
            WorkflowNode(
                node_id="ppt",
                node_type="export",
                title="PPT",
                inputs=(_port("svg", ("semantic_svg",), cardinality="single"),),
            ),
        ),
        edges=(
            WorkflowEdge(edge_id="e1", source_node_id="parser", source_port_id="candidates", target_node_id="ppt", target_port_id="svg"),
        ),
    )

    result = validate_workflow_template(template)

    assert not result.ok
    assert any(error.code == "incompatible_edge_types" for error in result.errors)


def test_rejects_missing_required_input() -> None:
    template = WorkflowTemplate(
        template_id="tpl_missing",
        name="Missing",
        nodes=(
            WorkflowNode(
                node_id="fusion",
                node_type="fusion",
                title="Fusion",
                inputs=(_port("candidates", ("element_candidates",), cardinality="many"),),
            ),
        ),
        edges=(),
    )

    result = validate_workflow_template(template)

    assert not result.ok
    assert any(error.code == "required_input_unconnected" for error in result.errors)


def test_rejects_multiple_same_type_sources_for_single_input() -> None:
    template = WorkflowTemplate(
        template_id="tpl_single",
        name="Single Input",
        nodes=(
            WorkflowNode(node_id="a", node_type="parser", title="A", outputs=(_port("out", ("element_candidates",), required=False),)),
            WorkflowNode(node_id="b", node_type="parser", title="B", outputs=(_port("out", ("element_candidates",), required=False),)),
            WorkflowNode(node_id="agent", node_type="agent", title="Agent", inputs=(_port("in", ("element_candidates",), cardinality="single"),)),
        ),
        edges=(
            WorkflowEdge(edge_id="e1", source_node_id="a", source_port_id="out", target_node_id="agent", target_port_id="in"),
            WorkflowEdge(edge_id="e2", source_node_id="b", source_port_id="out", target_node_id="agent", target_port_id="in"),
        ),
    )

    result = validate_workflow_template(template)

    assert not result.ok
    assert any(error.code == "single_input_multiple_sources" for error in result.errors)


def test_allows_multiple_sources_for_many_input() -> None:
    template = WorkflowTemplate(
        template_id="tpl_many",
        name="Many Input",
        nodes=(
            WorkflowNode(node_id="sam", node_type="parser", title="SAM", outputs=(_port("out", ("element_candidates",), required=False),)),
            WorkflowNode(node_id="ocr", node_type="parser", title="OCR", outputs=(_port("out", ("element_candidates",), required=False),)),
            WorkflowNode(node_id="fusion", node_type="fusion", title="Fusion", inputs=(_port("in", ("element_candidates",), cardinality="many"),)),
        ),
        edges=(
            WorkflowEdge(edge_id="e1", source_node_id="sam", source_port_id="out", target_node_id="fusion", target_port_id="in"),
            WorkflowEdge(edge_id="e2", source_node_id="ocr", source_port_id="out", target_node_id="fusion", target_port_id="in"),
        ),
    )

    result = validate_workflow_template(template)

    assert result.ok


def test_rejects_cycles() -> None:
    template = WorkflowTemplate(
        template_id="tpl_cycle",
        name="Cycle",
        nodes=(
            WorkflowNode(node_id="a", node_type="agent", title="A", inputs=(_port("in", ("json",), required=False),), outputs=(_port("out", ("json",), required=False),)),
            WorkflowNode(node_id="b", node_type="agent", title="B", inputs=(_port("in", ("json",), required=False),), outputs=(_port("out", ("json",), required=False),)),
        ),
        edges=(
            WorkflowEdge(edge_id="e1", source_node_id="a", source_port_id="out", target_node_id="b", target_port_id="in"),
            WorkflowEdge(edge_id="e2", source_node_id="b", source_port_id="out", target_node_id="a", target_port_id="in"),
        ),
    )

    result = validate_workflow_template(template)

    assert not result.ok
    assert any(error.code == "workflow_cycle" for error in result.errors)
```

- [ ] **Step 2: Run schema validation tests and confirm they fail**

Run:

```bash
uv run pytest tests/workflow/test_schema_validation.py -q
```

Expected: import failure for `drawai.workflow`.

- [ ] **Step 3: Implement workflow schema dataclasses**

Create `src/drawai/workflow/schema.py` with:

```python
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

WORKFLOW_TEMPLATE_SCHEMA = "drawai.workflow_template.v1"
NODE_RUN_SCHEMA = "drawai.workflow_node_run.v1"
PortCardinality = Literal["single", "many"]
NodeRunStatus = Literal["queued", "running", "ok", "failed", "blocked", "stale"]


@dataclass(frozen=True)
class WorkflowPort:
    port_id: str
    label: str
    types: tuple[str, ...]
    required: bool = True
    cardinality: PortCardinality = "single"
    formats: tuple[str, ...] = ()
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "port_id": self.port_id,
            "label": self.label,
            "types": list(self.types),
            "required": self.required,
            "cardinality": self.cardinality,
            "formats": list(self.formats),
            "description": self.description,
        }


@dataclass(frozen=True)
class WorkflowNode:
    node_id: str
    node_type: str
    title: str
    inputs: tuple[WorkflowPort, ...] = ()
    outputs: tuple[WorkflowPort, ...] = ()
    config: Mapping[str, Any] = field(default_factory=dict)
    position: Mapping[str, float] = field(default_factory=dict)
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "title": self.title,
            "inputs": [port.to_dict() for port in self.inputs],
            "outputs": [port.to_dict() for port in self.outputs],
            "config": _jsonable(self.config),
            "position": _jsonable(self.position),
            "description": self.description,
        }


@dataclass(frozen=True)
class WorkflowEdge:
    edge_id: str
    source_node_id: str
    source_port_id: str
    target_node_id: str
    target_port_id: str
    enabled_types: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "source_node_id": self.source_node_id,
            "source_port_id": self.source_port_id,
            "target_node_id": self.target_node_id,
            "target_port_id": self.target_port_id,
            "enabled_types": list(self.enabled_types),
        }


@dataclass(frozen=True)
class WorkflowTemplate:
    template_id: str
    name: str
    nodes: tuple[WorkflowNode, ...]
    edges: tuple[WorkflowEdge, ...]
    description: str = ""
    version: int = 1
    schema: str = WORKFLOW_TEMPLATE_SCHEMA
    defaults: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "defaults": _jsonable(self.defaults),
        }


@dataclass(frozen=True)
class WorkflowValidationError:
    code: str
    message: str
    node_id: str = ""
    edge_id: str = ""
    details: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "node_id": self.node_id,
            "edge_id": self.edge_id,
            "details": _jsonable(self.details),
        }


@dataclass(frozen=True)
class WorkflowValidationResult:
    ok: bool
    errors: tuple[WorkflowValidationError, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "errors": [error.to_dict() for error in self.errors],
        }


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_jsonable(item) for item in value]
    return value
```

- [ ] **Step 4: Implement graph validation**

Create `src/drawai/workflow/validation.py` with:

```python
from __future__ import annotations

from collections import defaultdict

from .schema import (
    WorkflowEdge,
    WorkflowNode,
    WorkflowPort,
    WorkflowTemplate,
    WorkflowValidationError,
    WorkflowValidationResult,
)


def validate_workflow_template(template: WorkflowTemplate) -> WorkflowValidationResult:
    errors: list[WorkflowValidationError] = []
    nodes = {node.node_id: node for node in template.nodes}
    if len(nodes) != len(template.nodes):
        errors.append(WorkflowValidationError("duplicate_node_id", "Workflow node ids must be unique."))

    edge_sources: dict[str, tuple[WorkflowNode, WorkflowPort, WorkflowNode, WorkflowPort, tuple[str, ...]]] = {}
    incoming_by_target_port: dict[tuple[str, str], list[tuple[WorkflowEdge, tuple[str, ...]]]] = defaultdict(list)
    adjacency: dict[str, list[str]] = defaultdict(list)

    for edge in template.edges:
        source_node = nodes.get(edge.source_node_id)
        target_node = nodes.get(edge.target_node_id)
        if source_node is None or target_node is None:
            errors.append(
                WorkflowValidationError(
                    "edge_unknown_node",
                    "Workflow edge references an unknown node.",
                    edge_id=edge.edge_id,
                    details={"source_node_id": edge.source_node_id, "target_node_id": edge.target_node_id},
                )
            )
            continue
        source_port = _find_port(source_node.outputs, edge.source_port_id)
        target_port = _find_port(target_node.inputs, edge.target_port_id)
        if source_port is None or target_port is None:
            errors.append(
                WorkflowValidationError(
                    "edge_unknown_port",
                    "Workflow edge references an unknown port.",
                    edge_id=edge.edge_id,
                    details={"source_port_id": edge.source_port_id, "target_port_id": edge.target_port_id},
                )
            )
            continue
        overlap = _edge_type_overlap(edge, source_port, target_port)
        if not overlap:
            errors.append(
                WorkflowValidationError(
                    "incompatible_edge_types",
                    "Workflow edge has no compatible output/input type overlap.",
                    edge_id=edge.edge_id,
                    details={"source_types": source_port.types, "target_types": target_port.types},
                )
            )
            continue
        edge_sources[edge.edge_id] = (source_node, source_port, target_node, target_port, overlap)
        incoming_by_target_port[(target_node.node_id, target_port.port_id)].append((edge, overlap))
        adjacency[source_node.node_id].append(target_node.node_id)

    for node in template.nodes:
        for input_port in node.inputs:
            incoming = incoming_by_target_port.get((node.node_id, input_port.port_id), [])
            if input_port.required and not incoming:
                errors.append(
                    WorkflowValidationError(
                        "required_input_unconnected",
                        "Required workflow input is not connected.",
                        node_id=node.node_id,
                        details={"port_id": input_port.port_id},
                    )
                )
            if input_port.cardinality == "single" and len(incoming) > 1:
                seen_types: dict[str, int] = defaultdict(int)
                for _edge, overlap in incoming:
                    for type_name in overlap:
                        seen_types[type_name] += 1
                duplicated_types = sorted(type_name for type_name, count in seen_types.items() if count > 1)
                if duplicated_types:
                    errors.append(
                        WorkflowValidationError(
                            "single_input_multiple_sources",
                            "Single-cardinality input receives multiple sources with the same type.",
                            node_id=node.node_id,
                            details={"port_id": input_port.port_id, "types": duplicated_types},
                        )
                    )

    cycle_node = _first_cycle_node(tuple(nodes), adjacency)
    if cycle_node:
        errors.append(
            WorkflowValidationError(
                "workflow_cycle",
                "Workflow graph contains a cycle.",
                node_id=cycle_node,
            )
        )

    return WorkflowValidationResult(ok=not errors, errors=tuple(errors))


def _find_port(ports: tuple[WorkflowPort, ...], port_id: str) -> WorkflowPort | None:
    return next((port for port in ports if port.port_id == port_id), None)


def _edge_type_overlap(edge: WorkflowEdge, source_port: WorkflowPort, target_port: WorkflowPort) -> tuple[str, ...]:
    source_types = set(source_port.types)
    if edge.enabled_types:
        source_types &= set(edge.enabled_types)
    return tuple(sorted(source_types & set(target_port.types)))


def _first_cycle_node(node_ids: tuple[str, ...], adjacency: dict[str, list[str]]) -> str:
    temporary: set[str] = set()
    permanent: set[str] = set()

    def visit(node_id: str) -> str:
        if node_id in permanent:
            return ""
        if node_id in temporary:
            return node_id
        temporary.add(node_id)
        for next_node_id in adjacency.get(node_id, []):
            cycle = visit(next_node_id)
            if cycle:
                return cycle
        temporary.remove(node_id)
        permanent.add(node_id)
        return ""

    for node_id in node_ids:
        cycle = visit(node_id)
        if cycle:
            return cycle
    return ""
```

- [ ] **Step 5: Export workflow symbols**

Create `src/drawai/workflow/__init__.py` with:

```python
"""DrawAI workflow DAG contracts."""

from .schema import (
    WorkflowEdge,
    WorkflowNode,
    WorkflowPort,
    WorkflowTemplate,
    WorkflowValidationError,
    WorkflowValidationResult,
)
from .validation import validate_workflow_template

__all__ = [
    "WorkflowEdge",
    "WorkflowNode",
    "WorkflowPort",
    "WorkflowTemplate",
    "WorkflowValidationError",
    "WorkflowValidationResult",
    "validate_workflow_template",
]
```

- [ ] **Step 6: Run schema validation tests**

Run:

```bash
uv run pytest tests/workflow/test_schema_validation.py -q
```

Expected: all tests pass.

- [ ] **Step 7: Commit Task 1**

Run:

```bash
git add src/drawai/workflow/__init__.py src/drawai/workflow/schema.py src/drawai/workflow/validation.py tests/workflow/test_schema_validation.py
git commit -m "feat: add workflow DAG validation contracts"
```

## Task 2: Built-In Format Registry And Strong Validators

**Files:**
- Create: `src/drawai/workflow/formats.py`
- Test: `tests/workflow/test_formats.py`

- [ ] **Step 1: Write failing format validation tests**

Create `tests/workflow/test_formats.py` with tests for `drawai.image.v1`, `drawai.element_candidates.v1`, `drawai.semantic_svg.v1`, and `drawai.pptx.v1` using a temp PNG, a valid candidate JSON, an invalid candidate JSON, a valid SVG, an invalid SVG, and a minimal zip lacking `[Content_Types].xml` to prove PPTX validation rejects malformed packages.

- [ ] **Step 2: Implement format registry**

Create `src/drawai/workflow/formats.py` with `FormatSpec`, `FormatValidationResult`, `default_format_registry()`, `validate_format_file(format_id, path)`, and validators that reuse `drawai.v2.schema.ElementCandidate` plus `validate_element_candidate` for candidate payloads.

- [ ] **Step 3: Run format tests**

Run:

```bash
uv run pytest tests/workflow/test_formats.py -q
```

Expected: all tests pass.

- [ ] **Step 4: Commit Task 2**

Run:

```bash
git add src/drawai/workflow/formats.py tests/workflow/test_formats.py
git commit -m "feat: add workflow format registry"
```

## Task 3: Default DrawAI Workflow Template

**Files:**
- Create: `src/drawai/workflow/templates.py`
- Test: `tests/workflow/test_templates.py`

- [ ] **Step 1: Write failing default template tests**

Create tests that assert `default_drawai_workflow_template()` validates, contains `input`, `sam_parser`, `ocr_parser`, `fusion`, `run0_agent`, `asset_planner`, `asset_processors`, `svg_agent`, `svg_to_ppt`, and `output`, and models Run0/SVG as `agent` nodes with provider defaults.

- [ ] **Step 2: Implement default template and local paths**

Create `default_drawai_workflow_template()`, `workflow_templates_dir(workspace)`, `user_workflow_template_path(workspace, template_id)`, and `copy_builtin_template(template_id, name)`.

- [ ] **Step 3: Run template tests**

Run:

```bash
uv run pytest tests/workflow/test_templates.py tests/workflow/test_schema_validation.py -q
```

Expected: all tests pass.

- [ ] **Step 4: Commit Task 3**

Run:

```bash
git add src/drawai/workflow/templates.py tests/workflow/test_templates.py
git commit -m "feat: add default workflow template"
```

## Task 4: Node Run Manifests And Canonical Workdirs

**Files:**
- Create: `src/drawai/workflow/node_runs.py`
- Test: `tests/workflow/test_node_runs.py`

- [ ] **Step 1: Write failing node run tests**

Test that `begin_node_run(root, node_id)` creates `nodes/<node_id>/runs/001`, writes `node_run.json` with `running`, rejects unsafe node ids, writes `input_manifest.json`, marks `ok`, marks `failed`, and creates `002` on the next attempt.

- [ ] **Step 2: Implement node run helpers**

Create functions `node_run_dir`, `begin_node_run`, `write_input_manifest`, `finish_node_run_ok`, `finish_node_run_failed`, and `mark_node_run_stale`. Use safe path checks matching `v2.packages.element_dir`.

- [ ] **Step 3: Run node run tests**

Run:

```bash
uv run pytest tests/workflow/test_node_runs.py -q
```

Expected: all tests pass.

- [ ] **Step 4: Commit Task 4**

Run:

```bash
git add src/drawai/workflow/node_runs.py tests/workflow/test_node_runs.py
git commit -m "feat: add workflow node run manifests"
```

## Task 5: Workflow Runner Skeleton And Output Finalization

**Files:**
- Create: `src/drawai/workflow/runner.py`
- Test: `tests/workflow/test_runner_contract.py`

- [ ] **Step 1: Write failing runner contract tests**

Test a tiny `Input -> Agent-like fake -> Output` workflow using in-process fake node handlers. Assert topological execution, node run manifests, blocked downstream behavior, Output collecting `deliverable=true`, and compatibility mirror creation.

- [ ] **Step 2: Implement runner skeleton**

Implement `WorkflowRunner`, `WorkflowRunContext`, `NodeHandler` protocol, resource acquire callback, topological scheduling in deterministic order for tests, output validation hook, and Output node finalization.

- [ ] **Step 3: Run runner contract tests**

Run:

```bash
uv run pytest tests/workflow/test_runner_contract.py tests/workflow/test_node_runs.py -q
```

Expected: all tests pass.

- [ ] **Step 4: Commit Task 5**

Run:

```bash
git add src/drawai/workflow/runner.py tests/workflow/test_runner_contract.py
git commit -m "feat: add workflow runner skeleton"
```

## Task 6: Agent Provider Contracts And Prompt Rendering

**Files:**
- Create: `src/drawai/workflow/agents.py`
- Test: `tests/workflow/test_agents.py`

- [ ] **Step 1: Write failing Agent prompt tests**

Test that Run0 and SVG Agent presets render prompts with connected file descriptions, user fragments, output declarations, provider id, and no arbitrary shell command field.

- [ ] **Step 2: Implement Agent provider and prompt contracts**

Implement `AgentProviderSpec`, `AgentNodeConfig`, `render_agent_prompt`, `run0_agent_preset`, `svg_agent_preset`, and safe override validation for `model`, `profile`, `timeout_seconds`, and `reasoning_effort`.

- [ ] **Step 3: Run Agent tests**

Run:

```bash
uv run pytest tests/workflow/test_agents.py -q
```

Expected: all tests pass.

- [ ] **Step 4: Commit Task 6**

Run:

```bash
git add src/drawai/workflow/agents.py tests/workflow/test_agents.py
git commit -m "feat: add workflow Agent node contracts"
```

## Task 7: CLI Workflow Commands

**Files:**
- Create: `src/drawai/workflow/cli.py`
- Modify: `src/drawai/cli.py`
- Test: `tests/workflow/test_cli.py`

- [ ] **Step 1: Write failing CLI tests**

Test `drawai workflow templates`, `drawai workflow validate --template default`, `drawai workflow validate <json>`, and `drawai workflow inspect-node-run <run_dir> <node_id>`.

- [ ] **Step 2: Implement CLI routing**

Add this branch near the top of `drawai.cli.main`:

```python
if args_list and args_list[0] == "workflow":
    from .workflow.cli import workflow_cli

    return workflow_cli(args_list[1:])
```

Implement argparse subcommands in `src/drawai/workflow/cli.py`.

- [ ] **Step 3: Run CLI tests**

Run:

```bash
uv run pytest tests/workflow/test_cli.py -q
```

Expected: all tests pass.

- [ ] **Step 4: Commit Task 7**

Run:

```bash
git add src/drawai/cli.py src/drawai/workflow/cli.py tests/workflow/test_cli.py
git commit -m "feat: add workflow CLI commands"
```

## Task 8: Workbench Template API And Batch Binding

**Files:**
- Modify: `src/drawai/workbench/models.py`
- Modify: `src/drawai/workbench/store.py`
- Modify: `src/drawai/workbench/api.py`
- Test: `tests/workbench/test_workflow_api.py`

- [ ] **Step 1: Write failing Workbench API tests**

Test listing templates, reading the built-in template, copying a built-in template to workspace storage, setting default template, validating a template, binding a custom template to an unstarted batch, and rejecting binding changes when a batch has active/running cases.

- [ ] **Step 2: Add store schema migration**

Extend `_init_schema` to add a `workflow_template_id` column to `batches` and a `workbench_settings` key/value table if not present. Add store methods `set_batch_workflow_template`, `get_batch_workflow_template`, `set_default_workflow_template`, and `get_default_workflow_template`.

- [ ] **Step 3: Add API endpoints**

Add endpoints:

```text
GET /api/workflows/templates
GET /api/workflows/templates/{template_id}
POST /api/workflows/templates/{template_id}/copy
POST /api/workflows/templates/{template_id}/default
POST /api/workflows/validate
PATCH /api/batches/{batch_id}/workflow
```

- [ ] **Step 4: Run API tests**

Run:

```bash
uv run pytest tests/workbench/test_workflow_api.py tests/workbench/test_store_api.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit Task 8**

Run:

```bash
git add src/drawai/workbench/models.py src/drawai/workbench/store.py src/drawai/workbench/api.py tests/workbench/test_workflow_api.py
git commit -m "feat: add workbench workflow template API"
```

## Task 9: Workbench Workflow Canvas UI

**Files:**
- Modify: `apps/workbench/package.json`
- Modify: `apps/workbench/package-lock.json`
- Create: `apps/workbench/src/workflowTypes.ts`
- Create: `apps/workbench/src/workflowApi.ts`
- Create: `apps/workbench/src/WorkflowWorkspace.tsx`
- Create: `apps/workbench/src/workflowCanvas.css`
- Modify: `apps/workbench/src/App.tsx`
- Modify: `apps/workbench/src/styles.css`

- [ ] **Step 1: Install React Flow**

Run:

```bash
npm --prefix apps/workbench install @xyflow/react
```

Expected: package files update and install succeeds.

- [ ] **Step 2: Add workflow TypeScript API types and client**

Create `workflowTypes.ts` and `workflowApi.ts` with `WorkflowTemplate`, `WorkflowNode`, `WorkflowEdge`, `WorkflowValidationResult`, `listWorkflowTemplates`, `getWorkflowTemplate`, `copyWorkflowTemplate`, `setDefaultWorkflowTemplate`, and `validateWorkflowTemplate`.

- [ ] **Step 3: Add Workflow tab and canvas workspace**

Create `WorkflowWorkspace.tsx` using `ReactFlow`, `MiniMap`, `Controls`, `Background`, node cards grouped by fixed node type, template list, property panel, validation errors, save/copy/default buttons, and final prompt preview area for Agent nodes.

- [ ] **Step 4: Wire top-level tab**

Change `BoardMode` in `App.tsx` from:

```ts
type BoardMode = "generate" | "process";
```

to:

```ts
type BoardMode = "generate" | "process" | "workflow";
```

Render the third tab and show `WorkflowWorkspace` when `boardMode === "workflow"`.

- [ ] **Step 5: Run frontend build**

Run:

```bash
npm --prefix apps/workbench run build
```

Expected: TypeScript and Vite build pass.

- [ ] **Step 6: Commit Task 9**

Run:

```bash
git add apps/workbench/package.json apps/workbench/package-lock.json apps/workbench/src/workflowTypes.ts apps/workbench/src/workflowApi.ts apps/workbench/src/WorkflowWorkspace.tsx apps/workbench/src/workflowCanvas.css apps/workbench/src/App.tsx apps/workbench/src/styles.css
git commit -m "feat: add workflow canvas workspace"
```

## Task 10: Processing Page Workflow Selection And Run View

**Files:**
- Create: `apps/workbench/src/WorkflowRunView.tsx`
- Modify: `apps/workbench/src/BoardWorkspace` section in `apps/workbench/src/App.tsx`
- Modify: `apps/workbench/src/workflowApi.ts`
- Modify: `src/drawai/workbench/api.py`
- Test: `tests/workbench/test_workflow_api.py`

- [ ] **Step 1: Add API tests for case snapshots and node run inspection**

Extend Workbench API tests for `GET /api/cases/{case_id}/workflow`, `GET /api/cases/{case_id}/workflow/nodes/{node_id}/runs`, and rerun endpoints.

- [ ] **Step 2: Add backend endpoints**

Add snapshot and node run endpoints that read `workflow_snapshot.json` and `nodes/<node_id>/runs/*/node_run.json` safely under the case run root.

- [ ] **Step 3: Add processing-page selector**

Add batch-level workflow template selector in the processing board top controls. It binds templates only for unstarted batches and shows the selected template name on task rows.

- [ ] **Step 4: Add Workflow Run View**

Implement `WorkflowRunView.tsx` with DAG snapshot display, node status list, selected node inputs, outputs, actual prompt, logs, and rerun buttons.

- [ ] **Step 5: Run backend and frontend tests**

Run:

```bash
uv run pytest tests/workbench/test_workflow_api.py -q
npm --prefix apps/workbench run build
```

Expected: both pass.

- [ ] **Step 6: Commit Task 10**

Run:

```bash
git add src/drawai/workbench/api.py tests/workbench/test_workflow_api.py apps/workbench/src/WorkflowRunView.tsx apps/workbench/src/workflowApi.ts apps/workbench/src/App.tsx
git commit -m "feat: add workflow run inspection UI"
```

## Task 11: Full Workflow Execution And Provider Resource Pools

**Files:**
- Modify: `src/drawai/workflow/runner.py`
- Modify: `src/drawai/workflow/agents.py`
- Modify: `src/drawai/workbench/runner.py`
- Test: `tests/workflow/test_runner_contract.py`
- Test: `tests/workbench/test_store_api.py`

- [ ] **Step 1: Add failing provider resource tests**

Test that `codex_sdk`, `codex_cli`, and `kimi_cli` resource counters are separate, queued/running counts are visible, and two runs using different workflows still share provider limits.

- [ ] **Step 2: Replace fixed stage resource mapping with node resource mapping**

Add workflow node resource resolution: fixed nodes use `sam3`, `ocr`, `rmbg`, `svg_to_ppt`; Agent nodes use their selected `provider_id`.

- [ ] **Step 3: Connect workflow runner to WorkbenchRunner**

Add `submit_workflow_batch` and `submit_workflow_case` paths that create `workflow_snapshot.json`, run the workflow, update case status, and register compatibility artifacts.

- [ ] **Step 4: Run provider/resource tests**

Run:

```bash
uv run pytest tests/workflow/test_runner_contract.py tests/workbench/test_store_api.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit Task 11**

Run:

```bash
git add src/drawai/workflow/runner.py src/drawai/workflow/agents.py src/drawai/workbench/runner.py tests/workflow/test_runner_contract.py tests/workbench/test_store_api.py
git commit -m "feat: run workflows with provider resource pools"
```

## Task 12: CLI And Workbench End-To-End Verification

**Files:**
- Create: `tests/workflow/test_e2e_contracts.py`
- Create or update: `scripts/verify_workflow_dag_e2e.py`
- Update docs if command names differ from this plan.

- [ ] **Step 1: Add e2e verification harness**

Create a script that runs a fixture through the built-in default workflow, a no-OCR workflow, and an Agent-as-OCR workflow. It records v1 baseline metrics, workflow metrics, output file paths, and differences into a JSON report.

- [ ] **Step 2: Run CLI with Codex SDK Agent provider**

Run:

```bash
uv run python scripts/verify_workflow_dag_e2e.py --provider codex_sdk --fixture examples/demo_figure.png
```

Expected: report includes SVG, PPTX, node manifests, and v1 comparison.

- [ ] **Step 3: Run CLI with Kimi CLI Agent provider**

Run:

```bash
uv run python scripts/verify_workflow_dag_e2e.py --provider kimi_cli --fixture examples/demo_figure.png
```

Expected: report includes SVG, PPTX, node manifests, and v1 comparison.

- [ ] **Step 4: Run Workbench browser verification**

Start local services, open the real Workbench with browser automation, copy the built-in template, save a custom template, bind it to an unstarted batch, run it, inspect Workflow Run View, verify Output deliverables, and run rerun actions.

- [ ] **Step 5: Commit e2e harness and final fixes**

Run:

```bash
git add tests/workflow/test_e2e_contracts.py scripts/verify_workflow_dag_e2e.py
git commit -m "test: add workflow DAG end-to-end verification"
```

## Self-Review Notes

- Spec coverage: the tasks cover workflow JSON, typed ports, built-in formats, default template, node workdirs, Agent nodes, provider limits, CLI, Workbench API, React Flow UI, processing-page template selection, run inspection, rerun semantics, and real CLI/Workbench acceptance checks.
- Testing coverage: the plan includes unit/contract tests, CLI tests, Workbench API tests, npm build, real Workbench browser verification, Codex SDK, Kimi CLI, v1 comparison, no-OCR workflow, and Agent-as-OCR workflow.
- Scope: this is one cohesive architecture replacement. The tasks are vertical enough to commit frequently and keep existing workbench behavior observable while replacing the v2 execution authority with the workflow DAG.
