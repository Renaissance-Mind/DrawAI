import json
from pathlib import Path

from PIL import Image

from scripts.run_codex_element_analysis import (
    SCHEMA_OUTPUT,
    invoke_acp_agent_element_analysis,
    invoke_agent_cli_element_analysis,
    parse_args,
)


def test_parse_args_accepts_agent_cli_invoker_and_command():
    for agent, command in {
        "kimi": ["kimi"],
        "openclaw": ["openclaw", "agent"],
        "hermes": ["hermes", "chat"],
    }.items():
        args = parse_args(
            [
                "case",
                "--invoker",
                "agent_cli",
                "--agent-cli-agent",
                agent,
                "--agent-cli-command",
                *command,
            ]
        )

        assert args.invoker == "agent_cli"
        assert args.agent_cli_agent == agent
        assert args.agent_cli_command == command


def test_parse_args_accepts_acp_agent_invoker_and_command():
    args = parse_args(
        [
            "case",
            "--invoker",
            "acp_agent",
            "--acp-agent",
            "kimi",
            "--acp-agent-command",
            "kimi",
            "acp",
        ]
    )

    assert args.invoker == "acp_agent"
    assert args.acp_agent == "kimi"
    assert args.acp_agent_command == ["kimi", "acp"]


def test_invoke_agent_cli_element_analysis_writes_output_via_cli(monkeypatch, tmp_path: Path):
    case_dir = tmp_path / "case"
    output_dir = case_dir / "reports" / "element_analysis_codex"
    output_path = output_dir / "element_analysis.json"
    trace_path = output_dir / "codex_element_analysis_trace.jsonl"
    case_dir.mkdir(parents=True)
    image_path = case_dir / "inputs" / "figure.png"
    image_path.parent.mkdir(parents=True)
    Image.new("RGB", (2, 2), "white").save(image_path)
    calls = []

    def fake_invoke_agent_cli_text(**kwargs):
        calls.append(kwargs)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(_analysis_payload(case_dir)), encoding="utf-8")
        return "done"

    monkeypatch.setattr(
        "scripts.run_codex_element_analysis.invoke_agent_cli_text",
        fake_invoke_agent_cli_text,
    )

    result = invoke_agent_cli_element_analysis(
        case_dir=case_dir,
        prompt="Write the element analysis JSON.",
        image_paths=[image_path],
        output_dir=output_dir,
        trace_path=trace_path,
        model_name="kimi-code/kimi-for-coding",
        timeout_seconds=5,
        agent="kimi",
        command=["kimi"],
    )

    analysis = json.loads(output_path.read_text(encoding="utf-8"))
    assert analysis["schema"] == SCHEMA_OUTPUT
    assert result["invoker"] == "agent_cli"
    assert result["model_name"] == "kimi-code/kimi-for-coding"
    assert result["duration_ms"] >= 0
    assert calls[0]["runtime_config"]["provider"] == "agent-cli"
    assert calls[0]["runtime_config"]["cli"] == {"agent": "kimi", "command": ["kimi"]}
    trace = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    assert trace[-1]["schema"] == "drawai.agent_cli_element_analysis_trace.v1"
    assert trace[-1]["invoker"] == "agent_cli"
    assert trace[-1]["agent"] == "kimi"


def test_invoke_acp_agent_element_analysis_writes_output_via_acp(monkeypatch, tmp_path: Path):
    case_dir = tmp_path / "case"
    output_dir = case_dir / "reports" / "element_analysis_codex"
    output_path = output_dir / "element_analysis.json"
    trace_path = output_dir / "codex_element_analysis_trace.jsonl"
    case_dir.mkdir(parents=True)
    image_path = case_dir / "inputs" / "figure.png"
    image_path.parent.mkdir(parents=True)
    Image.new("RGB", (2, 2), "white").save(image_path)
    calls = []

    def fake_invoke_acp_agent_text(**kwargs):
        calls.append(kwargs)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(_analysis_payload(case_dir)), encoding="utf-8")
        return "done"

    monkeypatch.setattr(
        "scripts.run_codex_element_analysis.invoke_acp_agent_text",
        fake_invoke_acp_agent_text,
    )

    result = invoke_acp_agent_element_analysis(
        case_dir=case_dir,
        prompt="Write the element analysis JSON.",
        image_paths=[image_path],
        output_dir=output_dir,
        trace_path=trace_path,
        model_name="kimi-code/kimi-for-coding",
        timeout_seconds=5,
        agent="kimi",
        command=["kimi", "acp"],
    )

    analysis = json.loads(output_path.read_text(encoding="utf-8"))
    assert analysis["schema"] == SCHEMA_OUTPUT
    assert result["invoker"] == "acp_agent"
    assert result["model_name"] == "kimi-code/kimi-for-coding"
    assert result["duration_ms"] >= 0
    assert calls[0]["runtime_config"]["provider"] == "acp-agent"
    assert calls[0]["runtime_config"]["acp"] == {"agent": "kimi", "command": ["kimi", "acp"]}
    trace = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    assert trace[-1]["schema"] == "drawai.acp_agent_element_analysis_trace.v1"
    assert trace[-1]["invoker"] == "acp_agent"
    assert trace[-1]["agent"] == "kimi"


def test_invoke_agent_cli_element_analysis_accepts_lightweight_review_of_preseeded_baseline(
    monkeypatch,
    tmp_path: Path,
):
    case_dir = tmp_path / "case"
    output_dir = case_dir / "reports" / "element_analysis_codex"
    output_path = output_dir / "element_analysis.json"
    trace_path = output_dir / "codex_element_analysis_trace.jsonl"
    output_dir.mkdir(parents=True)
    image_path = case_dir / "inputs" / "figure.png"
    image_path.parent.mkdir(parents=True)
    Image.new("RGB", (20, 10), "white").save(image_path)
    (output_dir / "element_analysis_request.json").write_text(
        json.dumps(
            {
                "schema": "drawai.codex_element_analysis_request.v1",
                "case_dir": str(case_dir),
                "canvas": {"width": 20, "height": 10},
                "candidate_count": 2,
                "candidates": [
                    {
                        "box_id": "B001",
                        "type": "content_box",
                        "bbox": [0, 0, 10, 10],
                        "current_pipeline_method": "svg_self_draw",
                    },
                    {
                        "box_id": "B002",
                        "type": "icon",
                        "bbox": [10, 0, 20, 10],
                        "current_pipeline_method": "crop",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    (output_dir / "candidate_table.tsv").write_text(
        "box_id\ttype\tbbox\tcurrent_pipeline_method\tasset_id\trender_policy\tbackground_policy\tactive_variant\tpolicy_reasons\tocr_text\n"
        "B001\tcontent_box\t0,0,10,10\tsvg_self_draw\t\t\t\t\t\tTitle\n"
        "B002\ticon\t10,0,20,10\tcrop\tAF01\t\t\t\t\t\n",
        encoding="utf-8",
    )

    def fake_invoke_agent_cli_text(**kwargs):
        (output_dir / "agent_cli_review.json").write_text(
            json.dumps(
                {
                    "schema": "drawai.agent_cli_element_analysis_review.v1",
                    "status": "ok",
                    "strategy_summary": "baseline reviewed",
                    "notes": ["baseline accepted"],
                }
            ),
            encoding="utf-8",
        )
        return "reviewed"

    monkeypatch.setattr(
        "scripts.run_codex_element_analysis.invoke_agent_cli_text",
        fake_invoke_agent_cli_text,
    )

    result = invoke_agent_cli_element_analysis(
        case_dir=case_dir,
        prompt="Review the preseeded baseline only.",
        image_paths=[image_path],
        output_dir=output_dir,
        trace_path=trace_path,
        model_name="",
        timeout_seconds=5,
        agent="claude",
        command=["claude"],
    )

    analysis = json.loads(output_path.read_text(encoding="utf-8"))
    assert analysis["schema"] == SCHEMA_OUTPUT
    assert analysis["source"] == "agent_cli_baseline_review"
    assert analysis["categories"] == {"svg_self_draw": 1, "crop": 1, "crop_nobg": 0}
    assert [element["box_id"] for element in analysis["elements"]] == ["B001", "B002"]
    assert analysis["agent_cli_review"]["strategy_summary"] == "baseline reviewed"
    assert result["invoker"] == "agent_cli"
    assert result["agent"] == "claude"
    assert result["output_path"] == str(output_path)
    assert (output_dir / "agent_cli_review.json").exists()


def test_invoke_acp_agent_element_analysis_accepts_lightweight_review_of_preseeded_baseline(
    monkeypatch,
    tmp_path: Path,
):
    case_dir = tmp_path / "case"
    output_dir = case_dir / "reports" / "element_analysis_codex"
    output_path = output_dir / "element_analysis.json"
    trace_path = output_dir / "codex_element_analysis_trace.jsonl"
    output_dir.mkdir(parents=True)
    image_path = case_dir / "inputs" / "figure.png"
    image_path.parent.mkdir(parents=True)
    Image.new("RGB", (20, 10), "white").save(image_path)
    (output_dir / "element_analysis_request.json").write_text(
        json.dumps(
            {
                "schema": "drawai.codex_element_analysis_request.v1",
                "case_dir": str(case_dir),
                "canvas": {"width": 20, "height": 10},
                "candidate_count": 2,
                "candidates": [
                    {
                        "box_id": "B001",
                        "type": "content_box",
                        "bbox": [0, 0, 10, 10],
                        "current_pipeline_method": "svg_self_draw",
                    },
                    {
                        "box_id": "B002",
                        "type": "icon",
                        "bbox": [10, 0, 20, 10],
                        "current_pipeline_method": "crop",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    (output_dir / "candidate_table.tsv").write_text(
        "box_id\ttype\tbbox\tcurrent_pipeline_method\tasset_id\trender_policy\tbackground_policy\tactive_variant\tpolicy_reasons\tocr_text\n"
        "B001\tcontent_box\t0,0,10,10\tsvg_self_draw\t\t\t\t\t\tTitle\n"
        "B002\ticon\t10,0,20,10\tcrop\tAF01\t\t\t\t\t\n",
        encoding="utf-8",
    )

    def fake_invoke_acp_agent_text(**kwargs):
        (output_dir / "acp_agent_review.json").write_text(
            json.dumps(
                {
                    "schema": "drawai.acp_agent_element_analysis_review.v1",
                    "status": "ok",
                    "strategy_summary": "baseline reviewed",
                    "notes": ["baseline accepted"],
                }
            ),
            encoding="utf-8",
        )
        return "reviewed"

    monkeypatch.setattr(
        "scripts.run_codex_element_analysis.invoke_acp_agent_text",
        fake_invoke_acp_agent_text,
    )

    result = invoke_acp_agent_element_analysis(
        case_dir=case_dir,
        prompt="Review the preseeded baseline only.",
        image_paths=[image_path],
        output_dir=output_dir,
        trace_path=trace_path,
        model_name="",
        timeout_seconds=5,
        agent="kimi",
        command=["kimi", "acp"],
    )

    analysis = json.loads(output_path.read_text(encoding="utf-8"))
    assert analysis["schema"] == SCHEMA_OUTPUT
    assert analysis["source"] == "acp_agent_baseline_review"
    assert analysis["categories"] == {"svg_self_draw": 1, "crop": 1, "crop_nobg": 0}
    assert [element["box_id"] for element in analysis["elements"]] == ["B001", "B002"]
    assert analysis["acp_agent_review"]["strategy_summary"] == "baseline reviewed"
    assert result["invoker"] == "acp_agent"
    assert result["agent"] == "kimi"
    assert result["output_path"] == str(output_path)
    assert (output_dir / "acp_agent_review.json").exists()


def _analysis_payload(case_dir: Path) -> dict[str, object]:
    return {
        "schema": SCHEMA_OUTPUT,
        "case_dir": str(case_dir),
        "source": "agent_cli",
        "strategy_summary": "test",
        "refinement_summary": "test",
        "refinement_iterations": [],
        "categories": {"svg_self_draw": 1, "crop": 0, "crop_nobg": 0},
        "refinement_actions": {"unchanged": 1, "adjusted": 0, "split": 0, "added": 0},
        "elements": [
            {
                "box_id": "B001",
                "source_candidate_ids": ["B001"],
                "refinement_action": "unchanged",
                "category": "svg_self_draw",
                "confidence": "high",
                "visual_role": "test",
                "reason": "test",
                "evidence": ["test"],
                "bbox": [0, 0, 1, 1],
                "type": "content_box",
                "current_pipeline_method": "svg_self_draw",
                "recommended_asset_source": "svg",
            }
        ],
        "notes": [],
    }
