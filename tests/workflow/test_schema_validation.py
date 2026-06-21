from __future__ import annotations

from drawai.workflow.schema import (
    WorkflowEdge,
    WorkflowNode,
    WorkflowPort,
    WorkflowTemplate,
)
from drawai.workflow.validation import validate_workflow_template


def _port(
    port_id: str,
    types: tuple[str, ...],
    *,
    required: bool = True,
    cardinality: str = "single",
) -> WorkflowPort:
    return WorkflowPort(
        port_id=port_id,
        label=port_id,
        types=types,
        required=required,
        cardinality=cardinality,
    )


def _agent_outputs(port_id: str, type_name: str) -> dict[str, object]:
    return {
        "outputs": [
            {
                "port_id": port_id,
                "path": f"output/{port_id}.json",
                "format_id": "drawai.custom_json.v1",
                "type": type_name,
                "description": "Test output.",
            }
        ]
    }


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
                config=_agent_outputs("out", "element_candidates"),
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
            WorkflowEdge(
                edge_id="e1",
                source_node_id="input",
                source_port_id="image",
                target_node_id="agent",
                target_port_id="in",
            ),
            WorkflowEdge(
                edge_id="e2",
                source_node_id="agent",
                source_port_id="out",
                target_node_id="fusion",
                target_port_id="candidates",
            ),
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
            WorkflowEdge(
                edge_id="e1",
                source_node_id="parser",
                source_port_id="candidates",
                target_node_id="ppt",
                target_port_id="svg",
            ),
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
            WorkflowNode(
                node_id="a",
                node_type="parser",
                title="A",
                outputs=(_port("out", ("element_candidates",), required=False),),
            ),
            WorkflowNode(
                node_id="b",
                node_type="parser",
                title="B",
                outputs=(_port("out", ("element_candidates",), required=False),),
            ),
            WorkflowNode(
                node_id="agent",
                node_type="agent",
                title="Agent",
                inputs=(_port("in", ("element_candidates",), cardinality="single"),),
                outputs=(_port("out", ("element_candidates",), required=False),),
                config=_agent_outputs("out", "element_candidates"),
            ),
        ),
        edges=(
            WorkflowEdge(
                edge_id="e1",
                source_node_id="a",
                source_port_id="out",
                target_node_id="agent",
                target_port_id="in",
            ),
            WorkflowEdge(
                edge_id="e2",
                source_node_id="b",
                source_port_id="out",
                target_node_id="agent",
                target_port_id="in",
            ),
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
            WorkflowNode(
                node_id="sam",
                node_type="parser",
                title="SAM",
                outputs=(_port("out", ("element_candidates",), required=False),),
            ),
            WorkflowNode(
                node_id="ocr",
                node_type="parser",
                title="OCR",
                outputs=(_port("out", ("element_candidates",), required=False),),
            ),
            WorkflowNode(
                node_id="fusion",
                node_type="fusion",
                title="Fusion",
                inputs=(_port("in", ("element_candidates",), cardinality="many"),),
            ),
        ),
        edges=(
            WorkflowEdge(
                edge_id="e1",
                source_node_id="sam",
                source_port_id="out",
                target_node_id="fusion",
                target_port_id="in",
            ),
            WorkflowEdge(
                edge_id="e2",
                source_node_id="ocr",
                source_port_id="out",
                target_node_id="fusion",
                target_port_id="in",
            ),
        ),
    )

    result = validate_workflow_template(template)

    assert result.ok


def test_rejects_agent_declared_output_that_does_not_match_node_port() -> None:
    template = WorkflowTemplate(
        template_id="tpl_bad_agent_output",
        name="Bad Agent Output",
        nodes=(
            WorkflowNode(
                node_id="agent",
                node_type="agent",
                title="Agent",
                inputs=(),
                outputs=(_port("asset_packages", ("asset_packages",), required=False),),
                config={
                    "preset_id": "run0_element_refine",
                },
            ),
        ),
        edges=(),
    )

    result = validate_workflow_template(template)

    assert not result.ok
    assert any(error.code == "agent_output_unknown_port" for error in result.errors)


def test_rejects_cycles() -> None:
    template = WorkflowTemplate(
        template_id="tpl_cycle",
        name="Cycle",
        nodes=(
            WorkflowNode(
                node_id="a",
                node_type="agent",
                title="A",
                inputs=(_port("in", ("json",), required=False),),
                outputs=(_port("out", ("json",), required=False),),
                config=_agent_outputs("out", "json"),
            ),
            WorkflowNode(
                node_id="b",
                node_type="agent",
                title="B",
                inputs=(_port("in", ("json",), required=False),),
                outputs=(_port("out", ("json",), required=False),),
                config=_agent_outputs("out", "json"),
            ),
        ),
        edges=(
            WorkflowEdge(
                edge_id="e1",
                source_node_id="a",
                source_port_id="out",
                target_node_id="b",
                target_port_id="in",
            ),
            WorkflowEdge(
                edge_id="e2",
                source_node_id="b",
                source_port_id="out",
                target_node_id="a",
                target_port_id="in",
            ),
        ),
    )

    result = validate_workflow_template(template)

    assert not result.ok
    assert any(error.code == "workflow_cycle" for error in result.errors)
