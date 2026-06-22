import json
from pathlib import Path

import pytest
from PIL import Image

import drawai.pipeline as pipeline_module
from drawai.pipeline import _svg_generation_prompt
from drawai.domain.box_ir import build_svg_template_ir
from drawai.svg_generation_loop import (
    SvgGenerationError,
    _extract_svg_text,
    run_svg_generation_loop,
)


VALID_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80" width="100" height="80"><rect width="100" height="80" fill="white"/><circle cx="20" cy="20" r="10" fill="red"/></svg>'
VALID_BLUE_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80" width="100" height="80"><rect width="100" height="80" fill="white"/><rect x="70" y="50" width="20" height="20" fill="blue"/></svg>'
LAYOUT_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80" width="100" height="80"><rect width="100" height="80" fill="white"/><rect x="5" y="5" width="60" height="30" fill="none" stroke="black"/><path d="M20 50 L60 50" stroke="black" fill="none"/></svg>'
REFINED_LAYOUT_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80" width="100" height="80"><rect width="100" height="80" fill="white"/><rect x="6" y="6" width="58" height="28" fill="none" stroke="black"/><path d="M18 50 L62 50" stroke="black" fill="none"/></svg>'
REFINED_LAYOUT_ROUND2_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80" width="100" height="80"><rect width="100" height="80" fill="white"/><rect x="7" y="7" width="56" height="26" fill="none" stroke="black"/><path d="M19 51 L61 51" stroke="black" fill="none"/></svg>'
MODEL_TEXT = '<text data-pb-role="label" data-pb-editable="true" data-pb-text-source="ocr" data-pb-orientation="horizontal" x="10" y="65" font-family="Arial" font-size="12">Hello</text>'
VERTICAL_MODEL_TEXT = '<text data-pb-role="label" data-pb-editable="true" data-pb-text-source="ocr" data-pb-orientation="vertical-rl" transform="rotate(90 20 20)" x="20" y="20" font-family="Arial" font-size="12">Vertical</text>'
VERTICAL_MODEL_TEXT_WITHOUT_ROTATE = '<text data-pb-role="label" data-pb-editable="true" data-pb-text-source="ocr" data-pb-orientation="vertical-rl" x="20" y="20" font-family="Arial" font-size="12">Vertical</text>'


def _make_inputs(tmp_path: Path) -> tuple[Path, Path, dict]:
    figure = tmp_path / "figure.png"
    reference = tmp_path / "reference.png"
    Image.new("RGB", (100, 80), "white").save(figure)
    Image.new("RGB", (100, 80), "white").save(reference)
    box_ir = {"canvas": {"width": 100, "height": 80}, "boxes": [], "ocr_text_boxes": []}
    return figure, reference, box_ir


def _make_staged_inputs(tmp_path: Path) -> tuple[Path, Path, dict, dict]:
    figure, reference, box_ir = _make_inputs(tmp_path)
    box_ir["boxes"] = [
        {"id": "B001", "type": "content_box", "bbox": [5, 5, 65, 35]},
        {"id": "B002", "type": "arrow", "bbox": [20, 48, 60, 52]},
        {"id": "B003", "type": "icon", "bbox": [70, 10, 88, 28]},
    ]
    box_ir["ocr_text_boxes"] = [
        {"id": "T001", "bbox": [10, 55, 55, 68], "text": "Hello", "confidence": 0.95},
    ]
    asset = tmp_path / "out" / "assets" / "crops" / "AF01.png"
    asset.parent.mkdir(parents=True)
    Image.new("RGBA", (18, 18), (255, 0, 0, 255)).save(asset)
    asset_manifest = {
        "schema": "drawai.asset_manifest.v1",
        "assets": [
            {"asset_id": "AF01", "box_id": "B003", "bbox": [70, 10, 88, 28], "svg_href": "../assets/crops/AF01.png"}
        ],
    }
    return figure, reference, box_ir, asset_manifest


def test_svg_generation_loop_retries_until_valid(tmp_path: Path):
    figure, reference, box_ir = _make_inputs(tmp_path)
    calls = []

    def fake_invoker(*, attempt, feedback, **kwargs):
        calls.append((attempt, feedback))
        if attempt == 1:
            return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 90 80"></svg>'
        return VALID_SVG

    result = run_svg_generation_loop(
        box_ir=box_ir,
        figure_path=figure,
        reference_image_path=reference,
        asset_manifest={"assets": []},
        output_dir=tmp_path / "svg",
        max_attempts=3,
        invoker=fake_invoker,
    )
    assert result["status"] == "ok"
    assert result["attempt_count"] == 2
    assert len(calls) == 2
    assert calls[0] == (1, None)
    assert any(issue["code"] == "viewbox_mismatch" for issue in calls[1][1]["issues"])
    assert (tmp_path / "svg" / "attempts" / "001" / "validation_report.json").exists()
    assert (tmp_path / "svg" / "semantic.svg").exists()
    assert (tmp_path / "svg" / "rendered.png").exists()
    assert (tmp_path / "svg" / "svg_validation_report.json").exists()


def test_svg_generation_loop_extracts_fenced_svg(tmp_path: Path):
    figure, reference, box_ir = _make_inputs(tmp_path)

    def fake_invoker(**kwargs):
        return f"Here is the SVG:\n```svg\n{VALID_SVG}\n```"

    result = run_svg_generation_loop(
        box_ir=box_ir,
        figure_path=figure,
        reference_image_path=reference,
        asset_manifest={"assets": []},
        output_dir=tmp_path / "svg",
        max_attempts=1,
        invoker=fake_invoker,
    )

    semantic_svg = Path(result["artifacts"]["semantic_svg"])
    assert result["status"] == "ok"
    assert semantic_svg.read_text(encoding="utf-8") == VALID_SVG


def test_svg_generation_loop_preserves_invoker_written_model_response(tmp_path: Path):
    figure, reference, box_ir = _make_inputs(tmp_path)

    def fake_invoker(*, output_response_path, **_kwargs):
        Path(output_response_path).write_text("codex wrote this response\n", encoding="utf-8")
        return VALID_SVG

    result = run_svg_generation_loop(
        box_ir=box_ir,
        figure_path=figure,
        reference_image_path=reference,
        asset_manifest={"assets": []},
        output_dir=tmp_path / "svg",
        max_attempts=1,
        invoker=fake_invoker,
    )

    response_path = tmp_path / "svg" / "attempts" / "001" / "model_response.txt"
    assert result["status"] == "ok"
    assert response_path.read_text(encoding="utf-8") == "codex wrote this response\n"


def test_extract_svg_text_accepts_prefaced_complete_svg():
    raw_response = f"Here is the reconstruction.\n\n{VALID_SVG}\n\nDone."

    assert _extract_svg_text(raw_response) == VALID_SVG


def test_svg_generation_loop_normalizes_circle_text_badges(tmp_path: Path):
    figure, reference, box_ir = _make_inputs(tmp_path)
    badge_svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80" width="100" height="80">'
        '<rect width="100" height="80" fill="white"/>'
        '<circle cx="30" cy="30" r="12" fill="#5b4593"/>'
        '<text data-pb-role="label" data-pb-editable="true" data-pb-text-source="visual_inferred" '
        'data-pb-orientation="horizontal" x="26" y="37" font-family="Arial" font-size="16" '
        'font-weight="700" fill="#ffffff">1</text>'
        "</svg>"
    )

    result = run_svg_generation_loop(
        box_ir=box_ir,
        figure_path=figure,
        reference_image_path=reference,
        asset_manifest={"assets": []},
        output_dir=tmp_path / "svg",
        max_attempts=1,
        invoker=lambda **_: badge_svg,
    )

    semantic_svg = Path(result["artifacts"]["semantic_svg"]).read_text(encoding="utf-8")
    report = json.loads(Path(result["artifacts"]["validation_report"]).read_text(encoding="utf-8"))
    assert 'data-pb-role="badge"' in semantic_svg
    assert 'data-pb-badge-kind="number"' in semantic_svg
    assert 'x="30"' in semantic_svg
    assert 'y="37.04"' in semantic_svg
    assert 'text-anchor="middle"' in semantic_svg
    assert 'dominant-baseline' not in semantic_svg
    assert report["badge_normalization"]["normalized_count"] == 1


def test_svg_generation_loop_normalizes_large_canvas_text_format(tmp_path: Path):
    figure = tmp_path / "figure.png"
    reference = tmp_path / "reference.png"
    Image.new("RGB", (3840, 2560), "white").save(figure)
    Image.new("RGB", (3840, 2560), "white").save(reference)
    box_ir = {"canvas": {"width": 3840, "height": 2560}, "boxes": [], "ocr_text_boxes": []}
    dummy_texts = "".join(
        f'<text data-pb-role="label" data-pb-editable="true" data-pb-text-source="visual_inferred" '
        f'data-pb-orientation="horizontal" x="100" y="{100 + index * 10}" '
        f'font-family="Arial" font-size="18">D{index}</text>'
        for index in range(40)
    )
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 3840 2560" width="3840" height="2560">'
        '<rect width="3840" height="2560" fill="white"/>'
        '<rect x="1049" y="230" width="738" height="175" fill="#fbf7ff"/>'
        '<text data-pb-role="label" data-pb-editable="true" data-pb-text-source="visual_inferred" '
        'data-pb-orientation="horizontal" x="1284" y="290" font-family="Arial" '
        'font-size="35" font-weight="700">Long Card Title</text>'
        '<text data-pb-role="label" data-pb-editable="true" data-pb-text-source="visual_inferred" '
        'data-pb-orientation="horizontal" x="1283" y="337" font-family="Arial" '
        'font-size="33">Card body line</text>'
        '<text data-pb-role="label" data-pb-editable="true" data-pb-text-source="visual_inferred" '
        'data-pb-orientation="horizontal" x="1230" y="293" font-family="Arial" '
        'font-size="34" font-weight="700">1</text>'
        f"{dummy_texts}"
        "</svg>"
    )

    result = run_svg_generation_loop(
        box_ir=box_ir,
        figure_path=figure,
        reference_image_path=reference,
        asset_manifest={"assets": []},
        output_dir=tmp_path / "svg",
        max_attempts=1,
        invoker=lambda **_: svg,
    )

    semantic_svg = Path(result["artifacts"]["semantic_svg"]).read_text(encoding="utf-8")
    report = json.loads(Path(result["artifacts"]["validation_report"]).read_text(encoding="utf-8"))
    assert 'font-size="28"' in semantic_svg
    assert 'font-size="27"' in semantic_svg
    assert 'font-size="34" font-weight="700">1</text>' in semantic_svg
    assert report["text_format_normalization"]["normalized_count"] == 2


def test_svg_generation_loop_preserves_native_2048_canvas_text_format(tmp_path: Path):
    figure = tmp_path / "figure.png"
    reference = tmp_path / "reference.png"
    Image.new("RGB", (2048, 1365), "white").save(figure)
    Image.new("RGB", (2048, 1365), "white").save(reference)
    box_ir = {"canvas": {"width": 2048, "height": 1365}, "boxes": [], "ocr_text_boxes": []}
    dummy_texts = "".join(
        f'<text data-pb-role="label" data-pb-editable="true" data-pb-text-source="visual_inferred" '
        f'data-pb-orientation="horizontal" x="100" y="{100 + index * 10}" '
        f'font-family="Arial" font-size="18">D{index}</text>'
        for index in range(40)
    )
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2048 1365" width="2048" height="1365">'
        '<rect width="2048" height="1365" fill="white"/>'
        '<text data-pb-role="label" data-pb-editable="true" data-pb-text-source="ocr" '
        'data-pb-orientation="horizontal" x="35" y="742" font-family="Arial" '
        'font-size="34" font-weight="700">Dynamics</text>'
        '<text data-pb-role="title" data-pb-editable="true" data-pb-text-source="ocr" '
        'data-pb-orientation="horizontal" x="825" y="39" font-family="Arial" '
        'font-size="36" font-weight="700">Real World State St</text>'
        f"{dummy_texts}"
        "</svg>"
    )

    result = run_svg_generation_loop(
        box_ir=box_ir,
        figure_path=figure,
        reference_image_path=reference,
        asset_manifest={"assets": []},
        output_dir=tmp_path / "svg",
        max_attempts=1,
        invoker=lambda **_: svg,
    )

    semantic_svg = Path(result["artifacts"]["semantic_svg"]).read_text(encoding="utf-8")
    report = json.loads(Path(result["artifacts"]["validation_report"]).read_text(encoding="utf-8"))
    assert 'font-size="34" font-weight="700">Dynamics</text>' in semantic_svg
    assert 'font-size="36" font-weight="700">Real World State St</text>' in semantic_svg
    assert "text_format_normalization" not in report


def test_staged_svg_generation_uses_model_text_and_two_visual_review_rounds(tmp_path: Path):
    figure, reference, box_ir, asset_manifest = _make_staged_inputs(tmp_path)
    output_dir = tmp_path / "out" / "svg"
    calls = []

    def fake_invoker(*, phase, attempt, base_svg=None, feedback=None, **kwargs):
        calls.append({"phase": phase, "attempt": attempt, "base_svg": base_svg, "feedback": feedback})
        if phase == "template":
            return (
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80" width="100" height="80">'
                '<rect width="100" height="80" fill="white"/>'
                '<text data-pb-role="label" data-pb-editable="true" '
                'data-pb-text-source="ocr" data-pb-orientation="horizontal" '
                'x="10" y="65" font-family="Arial" font-size="12">Hello</text>'
                "</svg>"
            )
        if phase == "visual_review_text_style":
            assert kwargs["reference_image_path"] == output_dir / "template_rendered.png"
            assert base_svg == (
                output_dir / "template_iterations" / "01_template" / "001" / "semantic.svg"
            ).read_text(encoding="utf-8")
            return (
                "```modification_notes\n"
                "- Text/style: preserved editable text and confirmed OCR label placement.\n"
                "```\n"
                "```svg\n"
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80" width="100" height="80">'
                '<rect width="100" height="80" fill="white"/>'
                '<text data-pb-role="label" data-pb-editable="true" '
                'data-pb-text-source="ocr" data-pb-orientation="horizontal" '
                'x="10" y="65" font-family="Times New Roman" font-size="12">Hello</text>'
                "</svg>\n"
                "```"
            )
        if phase == "visual_review_layout":
            assert kwargs["visual_review_round"] == 2
            assert kwargs["visual_review_focus"] == "layout"
            assert "Times New Roman" in base_svg
            return (
                "```modification_notes\n"
                "- Layout: aligned module geometry and kept text editable.\n"
                "```\n"
                "```svg\n"
                f"{REFINED_LAYOUT_SVG[:-6]}"
                '<text data-pb-role="label" data-pb-editable="true" '
                'data-pb-text-source="ocr" data-pb-orientation="horizontal" '
                'x="10" y="65" font-family="Times New Roman" font-size="12">Hello</text>'
                "</svg>\n"
                "```"
            )
        assert phase == "ir_refine"
        assert 'font-family="Times New Roman"' in base_svg
        assert "Hello" in base_svg
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80" width="100" height="80">'
            '<rect width="100" height="80" fill="white"/>'
            '<rect x="5" y="5" width="60" height="30" fill="none" stroke="black"/>'
            '<path d="M20 50 L60 50" stroke="black" fill="none"/>'
            '<rect x="70" y="10" width="18" height="18" fill="#ccc"/>'
            '<text data-pb-role="label" data-pb-editable="true" '
            'data-pb-text-source="ocr" data-pb-orientation="horizontal" '
            'x="10" y="65" font-family="Times New Roman" font-size="12">Hello</text>'
            "</svg>"
        )

    result = run_svg_generation_loop(
        box_ir=box_ir,
        figure_path=figure,
        reference_image_path=reference,
        asset_manifest=asset_manifest,
        output_dir=output_dir,
        max_attempts=2,
        invoker=fake_invoker,
        staged_generation=True,
        text_rendering="model_text",
        visual_review_rounds=("text_style", "layout"),
    )

    final_svg = Path(result["artifacts"]["semantic_svg"]).read_text(encoding="utf-8")
    assert result["status"] == "ok"
    assert [call["phase"] for call in calls] == [
        "template",
        "visual_review_text_style",
        "visual_review_layout",
        "ir_refine",
    ]
    assert '<g id="pb-manifest-raster-assets"' in final_svg
    assert '<image' in final_svg
    assert 'href="../assets/crops/AF01.png"' in final_svg
    assert 'x="70"' in final_svg
    assert 'y="10"' in final_svg
    assert 'width="18"' in final_svg
    assert 'height="18"' in final_svg
    assert 'data-asset-id="AF01"' not in final_svg
    assert "data-placeholder-kind" not in final_svg
    assert "Hello" in final_svg
    assert 'data-placeholder-kind="text"' not in final_svg
    assert Path(result["artifacts"]["template_svg"]) == output_dir / "template.svg"
    template_svg = (output_dir / "template.svg").read_text(encoding="utf-8")
    assert "Hello" in template_svg
    assert 'data-placeholder-kind="text"' not in template_svg
    assert (output_dir / "template_rendered.png").exists()
    template_attempt = output_dir / "template_iterations" / "01_template" / "001"
    review_round1 = output_dir / "template_iterations" / "02_visual_review_loop" / "round_01_text_style" / "001"
    review_round2 = output_dir / "template_iterations" / "02_visual_review_loop" / "round_02_layout" / "001"
    assert (template_attempt / "semantic.svg").exists()
    assert (template_attempt / "request_context.json").exists()
    assert (review_round1 / "semantic.svg").exists()
    assert (review_round1 / "input_template.svg").exists()
    assert (review_round1 / "request_context.json").exists()
    assert (review_round2 / "semantic.svg").exists()
    assert (review_round2 / "input_template.svg").exists()
    assert (review_round2 / "request_context.json").exists()
    manifest = json.loads((output_dir / "template_iterations" / "iteration_manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == "drawai.svg_template_iterations.v1"
    assert [phase["phase"] for phase in manifest["phases"]] == [
        "template",
        "visual_review_text_style",
        "visual_review_layout",
    ]
    assert [phase.get("round") for phase in manifest["phases"]] == [None, 1, 2]
    assert [phase.get("focus") for phase in manifest["phases"]] == [None, "text_style", "layout"]


def test_codex_sdk_staged_generation_merges_three_runs_into_one_self_iterating_turn(tmp_path: Path):
    figure, reference, box_ir, asset_manifest = _make_staged_inputs(tmp_path)
    output_dir = tmp_path / "out" / "svg"
    calls = []

    def fake_invoker(
        *,
        phase,
        attempt,
        output_svg_path,
        iteration_log_path,
        iteration_log_jsonl_path,
        template_svg_path,
        **kwargs,
    ):
        prompt_kwargs = dict(kwargs)
        prompt_kwargs.update(
            {
                "phase": phase,
                "output_svg_path": output_svg_path,
                "iteration_log_path": iteration_log_path,
                "iteration_log_jsonl_path": iteration_log_jsonl_path,
                "template_svg_path": template_svg_path,
                "file_context_mode": True,
                "codex_thread_turn_mode": True,
            }
        )
        prompt_text = _svg_generation_prompt(prompt_kwargs)
        Path(kwargs["prompt_path"]).write_text(prompt_text, encoding="utf-8")
        calls.append(
            {
                "phase": phase,
                "attempt": attempt,
                "output_svg_path": Path(output_svg_path),
                "iteration_log_path": Path(iteration_log_path),
                "iteration_log_jsonl_path": Path(iteration_log_jsonl_path),
                "template_svg_path": Path(template_svg_path),
                "validator_script_path": Path(kwargs["validator_script_path"]),
                "validator_command": kwargs["validator_command"],
                "native_backfill_request_path": Path(kwargs["native_backfill_request_path"]),
                "native_backfill_tools_dir": Path(kwargs["native_backfill_tools_dir"]),
                "native_backfill_assets_dir": Path(kwargs["native_backfill_assets_dir"]),
                "prompt": Path(kwargs["prompt_path"]).read_text(encoding="utf-8"),
            }
        )
        Path(iteration_log_path).write_text(
            "# Codex SVG self-iteration log\n\n- semantic_0.svg rendered_0.png\n- semantic_1.svg rendered_1.png\n",
            encoding="utf-8",
        )
        Path(iteration_log_jsonl_path).write_text(
            '{"iteration":0,"svg":"semantic_0.svg","rendered":"rendered_0.png"}\n'
            '{"iteration":1,"svg":"semantic_1.svg","rendered":"rendered_1.png"}\n',
            encoding="utf-8",
        )
        Path(output_svg_path).with_name("semantic_0.svg").write_text(VALID_SVG, encoding="utf-8")
        Path(output_svg_path).with_name("semantic_1.svg").write_text(VALID_BLUE_SVG, encoding="utf-8")
        return VALID_BLUE_SVG

    result = run_svg_generation_loop(
        box_ir=box_ir,
        figure_path=figure,
        reference_image_path=reference,
        asset_manifest=asset_manifest,
        output_dir=output_dir,
        max_attempts=3,
        invoker=fake_invoker,
        runtime_config={
            "provider": "codex-python-sdk",
            "connection_id": "codex-python-sdk-controlled",
        },
        staged_generation=True,
        text_rendering="model_text",
        visual_review_rounds=("text_style",),
    )

    assert result["status"] == "ok"
    assert result["attempt_count"] == 1
    assert [call["phase"] for call in calls] == ["codex_merged_stages"]
    attempt_dir = output_dir / "attempts" / "codex_merged" / "001"
    assert calls[0]["output_svg_path"] == attempt_dir / "semantic.svg"
    assert calls[0]["iteration_log_path"] == attempt_dir / "iteration_log.md"
    assert calls[0]["iteration_log_jsonl_path"] == attempt_dir / "iteration_log.jsonl"
    assert calls[0]["template_svg_path"] == output_dir / "template.svg"
    assert calls[0]["validator_script_path"] == attempt_dir / "validate_svg_attempt.py"
    assert "validate_svg_attempt.py" in calls[0]["validator_command"]
    assert "--svg" in calls[0]["validator_command"]
    assert "--report" in calls[0]["validator_command"]
    assert calls[0]["native_backfill_request_path"] == attempt_dir / "native_backfill_request.json"
    assert calls[0]["native_backfill_tools_dir"] == attempt_dir / "native_backfill_tools"
    assert calls[0]["native_backfill_assets_dir"] == output_dir / "native_backfill_assets" / "codex_merged_stages_001"
    assert "RUN1 / COMPLETE FIRST PASS" in calls[0]["prompt"]
    assert "REFINE LOOP / DEFAULT 1 ROUND, MAX 2 ROUNDS" in calls[0]["prompt"]
    assert "Run 2 / visual_review_text_style" not in calls[0]["prompt"]
    assert "Run 3 / ir_refine" not in calls[0]["prompt"]
    assert "NATIVE SVG BACKFILL MODE" in calls[0]["prompt"]
    assert "native_backfill_request.json" in calls[0]["prompt"]
    assert "crop_region.py" in calls[0]["prompt"]
    assert "remove_background.py" in calls[0]["prompt"]
    assert "semantic_0.svg" in calls[0]["prompt"]
    assert "semantic_2.svg" in calls[0]["prompt"]
    assert "rendered_0.png" in calls[0]["prompt"]
    assert "iteration_log.md" in calls[0]["prompt"]
    assert "iteration_log.jsonl" in calls[0]["prompt"]
    assert "validate_svg_attempt.py" in calls[0]["prompt"]
    assert "validation_report_0.json" in calls[0]["prompt"]
    assert (attempt_dir / "iteration_log.md").exists()
    assert (attempt_dir / "iteration_log.jsonl").exists()
    assert (attempt_dir / "validate_svg_attempt.py").exists()
    assert (attempt_dir / "native_backfill_request.json").exists()
    assert (attempt_dir / "native_backfill_tools" / "crop_region.py").exists()
    assert (attempt_dir / "native_backfill_tools" / "remove_background.py").exists()
    assert (attempt_dir / "request_context.json").exists()
    context = json.loads((attempt_dir / "request_context.json").read_text(encoding="utf-8"))
    assert context["phase"] == "codex_merged_stages"
    assert context["iteration_log"] == str(attempt_dir / "iteration_log.md")
    assert context["iteration_log_jsonl"] == str(attempt_dir / "iteration_log.jsonl")
    assert context["validator_script"] == str(attempt_dir / "validate_svg_attempt.py")
    assert "validate_svg_attempt.py" in context["validator_command"]
    assert context["native_backfill_request"] == str(attempt_dir / "native_backfill_request.json")
    assert context["native_backfill_candidate_count"] == 1
    request = json.loads((attempt_dir / "native_backfill_request.json").read_text(encoding="utf-8"))
    assert request["schema"] == "drawai.native_backfill_request.v1"
    assert request["candidate_count"] == 1
    assert request["candidates"][0]["box_id"] == "B003"
    assert request["candidates"][0]["preserve_href"] == "native_backfill_assets/codex_merged_stages_001/NB_B003.png"
    validator_context = json.loads((attempt_dir / "validator_context.json").read_text(encoding="utf-8"))
    validator_hrefs = {
        asset["svg_href"]
        for asset in validator_context["asset_manifest"]["assets"]
        if asset.get("native_backfill_candidate")
    }
    assert validator_hrefs == {
        "native_backfill_assets/codex_merged_stages_001/NB_B003.png",
        "native_backfill_assets/codex_merged_stages_001/NB_B003_nobg.png",
    }
    assert Path(result["artifacts"]["iteration_log"]) == attempt_dir / "iteration_log.md"
    assert Path(result["artifacts"]["template_svg"]) == output_dir / "template.svg"
    assert (output_dir / "template_rendered.png").exists()
    final_svg = (output_dir / "semantic.svg").read_text(encoding="utf-8")
    assert '<rect x="70" y="50" width="20" height="20" fill="blue"' in final_svg
    assert '<g id="pb-manifest-raster-assets"' in final_svg
    assert "<image" in final_svg
    assert 'href="../assets/crops/AF01.png"' in final_svg
    assert 'href="../assets/crops/AF01.png"' in (attempt_dir / "semantic_0.svg").read_text(encoding="utf-8")
    assert 'href="../assets/crops/AF01.png"' in (attempt_dir / "semantic_1.svg").read_text(encoding="utf-8")
    assert "native_backfill_assets" not in final_svg
    assert "data-placeholder-kind" not in final_svg
    assert "data-asset-id" not in final_svg


def test_agent_cli_staged_generation_uses_quality_stage_turns_by_default(tmp_path: Path):
    figure, reference, box_ir, asset_manifest = _make_staged_inputs(tmp_path)
    output_dir = tmp_path / "out" / "svg"
    calls = []

    def fake_invoker(
        *,
        phase,
        attempt,
        output_svg_path,
        **kwargs,
    ):
        prompt_kwargs = dict(kwargs)
        prompt_kwargs.update(
            {
                "phase": phase,
                "attempt": attempt,
                "output_svg_path": output_svg_path,
                "file_context_mode": True,
                "codex_thread_turn_mode": False,
            }
        )
        Path(kwargs["prompt_path"]).write_text(
            _svg_generation_prompt(prompt_kwargs),
            encoding="utf-8",
        )
        calls.append(
            {
                "phase": phase,
                "output_svg_path": Path(output_svg_path),
                "prompt": Path(kwargs["prompt_path"]).read_text(encoding="utf-8"),
            }
        )
        return VALID_BLUE_SVG

    result = run_svg_generation_loop(
        box_ir=box_ir,
        figure_path=figure,
        reference_image_path=reference,
        asset_manifest=asset_manifest,
        output_dir=output_dir,
        max_attempts=3,
        invoker=fake_invoker,
        runtime_config={
            "provider": "agent-cli",
            "connection_id": "kimi",
            "cli": {"agent": "kimi", "command": ["kimi"]},
        },
        staged_generation=True,
        text_rendering="model_text",
        visual_review_rounds=("text_style",),
    )

    assert result["status"] == "ok"
    assert [call["phase"] for call in calls] == [
        "template",
        "visual_review_text_style",
        "ir_refine",
    ]
    assert calls[0]["output_svg_path"] == output_dir / "template_iterations" / "01_template" / "001" / "semantic.svg"
    assert calls[-1]["output_svg_path"] == output_dir / "attempts" / "ir_refine" / "001" / "semantic.svg"
    assert "Run 1 / template" in calls[0]["prompt"]
    assert "Run 2 / visual_review_text_style" in calls[1]["prompt"]
    assert "Run 3 / ir_refine" in calls[2]["prompt"]
    assert "RUN1 / COMPLETE FIRST PASS" not in calls[0]["prompt"]


def test_codex_merged_thread_prompt_instructs_self_rendered_iteration():
    box_ir = {"canvas": {"width": 200, "height": 120}, "boxes": [], "ocr_text_boxes": []}
    prompt = _svg_generation_prompt(
        {
            "phase": "codex_merged_stages",
            "box_ir": box_ir,
            "asset_manifest": {"assets": []},
            "template_ir": build_svg_template_ir(box_ir),
            "file_context_mode": True,
            "codex_thread_turn_mode": True,
            "workspace_dir": "out",
            "figure_path": "svg/svg_generation_reference.png",
            "reference_image_path": "svg/template_reference.png",
            "request_context_path": "svg/attempts/codex_merged/001/request_context.json",
            "prompt_path": "svg/attempts/codex_merged/001/prompt.txt",
            "output_svg_path": "svg/attempts/codex_merged/001/semantic.svg",
            "output_response_path": "svg/attempts/codex_merged/001/model_response.txt",
            "output_rendered_path": "svg/attempts/codex_merged/001/rendered.png",
            "iteration_log_path": "svg/attempts/codex_merged/001/iteration_log.md",
            "iteration_log_jsonl_path": "svg/attempts/codex_merged/001/iteration_log.jsonl",
            "template_svg_path": "svg/template.svg",
            "template_rendered_path": "svg/template_rendered.png",
            "validator_script_path": "svg/attempts/codex_merged/001/validate_svg_attempt.py",
            "validator_command": "python svg/attempts/codex_merged/001/validate_svg_attempt.py --svg {svg} --rendered {rendered} --report {report}",
            "native_backfill_request_path": "svg/attempts/codex_merged/001/native_backfill_request.json",
            "native_backfill_tools_dir": "svg/attempts/codex_merged/001/native_backfill_tools",
            "native_backfill_assets_dir": "svg/native_backfill_assets/codex_merged_stages_001",
            "native_backfill_asset_href_prefix": "native_backfill_assets/codex_merged_stages_001",
            "native_backfill_candidate_count": 2,
            "feedback": {},
            "visual_review_rounds": ("text_style",),
        }
    )

    assert "IMAGE VECTORIZATION TASK" in prompt
    assert "AVAILABLE FILES AND READING LOGIC" in prompt
    assert "OVERALL DRAWAI PIPELINE" in prompt
    assert "RUN1 / COMPLETE FIRST PASS" in prompt
    assert "REFINE LOOP / DEFAULT 1 ROUND, MAX 2 ROUNDS" in prompt
    assert "Run 2 / visual_review_text_style" not in prompt
    assert "Run 3 / ir_refine" not in prompt
    assert "NATIVE SVG BACKFILL MODE" in prompt
    assert "native_backfill_request.json" in prompt
    assert "crop_region.py" in prompt
    assert "remove_background.py" in prompt
    assert "native_backfill_assets/codex_merged_stages_001" in prompt
    assert "semantic_0.svg" in prompt
    assert "semantic_2.svg" in prompt
    assert "rendered_0.png" in prompt
    assert "semantic_1.svg" in prompt
    assert "rendered_1.png" in prompt
    assert "iteration_log.md" in prompt
    assert "iteration_log.jsonl" in prompt
    assert "Chrome" in prompt
    assert "validate_svg_attempt.py" in prompt
    assert "validation_report_0.json" in prompt
    assert "Do not run a third refinement round" in prompt
    assert "A complete valid final SVG is better than an unfinished extra refinement" in prompt
    assert "must run this validator after each semantic_N.svg" in prompt
    assert "Copy the accepted final SVG/render to the required final SVG/rendered output paths" in prompt


def test_staged_svg_generation_does_not_use_asset_placeholder_contract(tmp_path: Path):
    figure, reference, box_ir, asset_manifest = _make_staged_inputs(tmp_path)
    output_dir = tmp_path / "out" / "svg"
    request_has_placeholder_plan = []

    def fake_invoker(*, phase, **kwargs):
        request_has_placeholder_plan.append("placeholder_plan" in kwargs)
        if phase == "template":
            return LAYOUT_SVG[:-6] + MODEL_TEXT + "</svg>"
        if phase.startswith("visual_review_"):
            return kwargs["base_svg"]
        assert phase == "ir_refine"
        return REFINED_LAYOUT_SVG[:-6] + MODEL_TEXT + "</svg>"

    result = run_svg_generation_loop(
        box_ir=box_ir,
        figure_path=figure,
        reference_image_path=reference,
        asset_manifest=asset_manifest,
        output_dir=output_dir,
        max_attempts=1,
        invoker=fake_invoker,
        staged_generation=True,
        text_rendering="model_text",
    )

    final_svg = Path(result["artifacts"]["semantic_svg"]).read_text(encoding="utf-8")
    assert result["status"] == "ok"
    assert request_has_placeholder_plan == [False, False, False]
    assert '<g id="pb-manifest-raster-assets"' in final_svg
    assert '<image' in final_svg
    assert 'href="../assets/crops/AF01.png"' in final_svg
    assert "data-placeholder-kind" not in final_svg
    assert "data-asset-id" not in final_svg
    assert not (output_dir / "postprocess" / "placeholder_expansion_report.json").exists()


def test_staged_svg_generation_does_not_inject_missing_asset_placeholders_from_ir(tmp_path: Path):
    figure, reference, box_ir, asset_manifest = _make_staged_inputs(tmp_path)
    output_dir = tmp_path / "out" / "svg"

    def fake_invoker(*, phase, **kwargs):
        if phase == "template":
            return LAYOUT_SVG[:-6] + MODEL_TEXT + "</svg>"
        if phase.startswith("visual_review_"):
            return kwargs["base_svg"]
        return LAYOUT_SVG[:-6] + MODEL_TEXT + "</svg>"

    result = run_svg_generation_loop(
        box_ir=box_ir,
        figure_path=figure,
        reference_image_path=reference,
        asset_manifest=asset_manifest,
        output_dir=output_dir,
        max_attempts=1,
        invoker=fake_invoker,
        staged_generation=True,
        visual_review_rounds=("text_style", "layout"),
        text_rendering="model_text",
    )

    final_svg = Path(result["artifacts"]["semantic_svg"]).read_text(encoding="utf-8")
    assert '<g id="pb-manifest-raster-assets"' in final_svg
    assert '<image' in final_svg
    assert 'href="../assets/crops/AF01.png"' in final_svg
    assert 'data-asset-id="AF01"' not in final_svg
    assert "data-placeholder-kind" not in final_svg
    assert "Hello" in final_svg
    assert not (output_dir / "postprocess" / "placeholder_expansion_report.json").exists()


def test_staged_svg_generation_retries_when_ir_refine_text_omits_required_attributes(tmp_path: Path):
    figure, reference, box_ir, asset_manifest = _make_staged_inputs(tmp_path)
    output_dir = tmp_path / "out" / "svg"
    calls = []

    def fake_invoker(*, phase, attempt, feedback=None, **kwargs):
        calls.append({"phase": phase, "attempt": attempt, "feedback": feedback})
        if phase == "template":
            return LAYOUT_SVG[:-6] + MODEL_TEXT + "</svg>"
        if phase.startswith("visual_review_"):
            return kwargs["base_svg"]
        assert phase == "ir_refine"
        if attempt == 1:
            return (
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80" width="100" height="80">'
                '<rect width="100" height="80" fill="white"/>'
                '<text x="10" y="20">model text</text>'
                "</svg>"
            )
        assert any(issue["code"] == "model_text_missing_role" for issue in feedback["issues"])
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80" width="100" height="80">'
            '<rect width="100" height="80" fill="white"/>'
            '<rect x="70" y="10" width="18" height="18" fill="#ccc"/>'
            f"{MODEL_TEXT}"
            "</svg>"
        )

    result = run_svg_generation_loop(
        box_ir=box_ir,
        figure_path=figure,
        reference_image_path=reference,
        asset_manifest=asset_manifest,
        output_dir=output_dir,
        max_attempts=2,
        invoker=fake_invoker,
        staged_generation=True,
        text_rendering="model_text",
    )

    assert result["status"] == "ok"
    assert [call["phase"] for call in calls] == [
        "template",
        "visual_review_text_style",
        "ir_refine",
        "ir_refine",
    ]
    first_details_report = json.loads(
        (output_dir / "attempts" / "ir_refine" / "001" / "validation_report.json").read_text(encoding="utf-8")
    )
    assert first_details_report["status"] == "failed"
    assert any(issue["code"] == "model_text_missing_role" for issue in first_details_report["issues"])


def test_staged_svg_generation_retries_when_template_text_omits_required_attributes(tmp_path: Path):
    figure, reference, box_ir, asset_manifest = _make_staged_inputs(tmp_path)
    output_dir = tmp_path / "out" / "svg"
    calls = []

    def fake_invoker(*, phase, attempt, feedback=None, **kwargs):
        calls.append({"phase": phase, "attempt": attempt, "feedback": feedback})
        if phase == "template":
            if attempt == 1:
                return (
                    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80" width="100" height="80">'
                    '<rect width="100" height="80" fill="white"/>'
                    '<text x="10" y="65">Hello</text>'
                    "</svg>"
                )
            assert any(issue["code"] == "model_text_missing_role" for issue in feedback["issues"])
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80" width="100" height="80">'
            '<rect width="100" height="80" fill="white"/>'
            '<rect x="5" y="5" width="60" height="30" fill="none" stroke="black"/>'
            f"{MODEL_TEXT}"
                "</svg>"
            )
        if phase.startswith("visual_review_"):
            return kwargs["base_svg"]
        assert phase == "ir_refine"
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80" width="100" height="80">'
            '<rect width="100" height="80" fill="white"/>'
            '<rect x="70" y="10" width="18" height="18" fill="#ccc"/>'
            f"{MODEL_TEXT}"
            "</svg>"
        )

    result = run_svg_generation_loop(
        box_ir=box_ir,
        figure_path=figure,
        reference_image_path=reference,
        asset_manifest=asset_manifest,
        output_dir=output_dir,
        max_attempts=2,
        invoker=fake_invoker,
        staged_generation=True,
        text_rendering="model_text",
    )

    assert result["status"] == "ok"
    assert [call["phase"] for call in calls] == [
        "template",
        "template",
        "visual_review_text_style",
        "ir_refine",
    ]
    template_svg = (output_dir / "template.svg").read_text(encoding="utf-8")
    assert 'data-placeholder-kind="text"' not in template_svg
    assert "Hello" in template_svg
    first_template_report = json.loads(
        (
            output_dir / "template_iterations" / "01_template" / "001" / "validation_report.json"
        ).read_text(encoding="utf-8")
    )
    assert first_template_report["status"] == "failed"
    assert any(issue["code"] == "model_text_missing_role" for issue in first_template_report["issues"])


def test_staged_svg_generation_requires_vertical_text_rotation(tmp_path: Path):
    figure, reference, box_ir = _make_inputs(tmp_path)
    output_dir = tmp_path / "out" / "svg"

    def fake_invoker(*, phase, attempt, base_svg=None, feedback=None, **kwargs):
        if phase == "template":
            if attempt == 1:
                return (
                    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80" width="100" height="80">'
                    '<rect width="100" height="80" fill="white"/>'
                    f"{VERTICAL_MODEL_TEXT_WITHOUT_ROTATE}"
                    "</svg>"
                )
            assert any(issue["code"] == "vertical_text_missing_rotation" for issue in feedback["issues"])
            return (
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80" width="100" height="80">'
                '<rect width="100" height="80" fill="white"/>'
                f"{VERTICAL_MODEL_TEXT}"
                "</svg>"
            )
        return base_svg

    result = run_svg_generation_loop(
        box_ir=box_ir,
        figure_path=figure,
        reference_image_path=reference,
        asset_manifest={"assets": []},
        output_dir=output_dir,
        max_attempts=2,
        invoker=fake_invoker,
        staged_generation=True,
        text_rendering="model_text",
    )

    final_svg = Path(result["artifacts"]["semantic_svg"]).read_text(encoding="utf-8")
    first_template_report = json.loads(
        (
            output_dir / "template_iterations" / "01_template" / "001" / "validation_report.json"
        ).read_text(encoding="utf-8")
    )
    assert first_template_report["status"] == "failed"
    assert any(issue["code"] == "vertical_text_missing_rotation" for issue in first_template_report["issues"])
    assert 'data-pb-orientation="vertical-rl"' in final_svg
    assert 'transform="rotate(90 20 20)"' in final_svg


def test_visual_template_prompt_is_autofigure_style_and_uses_compact_template_ir_only():
    box_ir = {
        "canvas": {"width": 100, "height": 80},
        "boxes": [
            {"id": "B001", "type": "content_box", "bbox": [1, 2, 30, 40]},
            {"id": "B002", "type": "arrow", "bbox": [35, 20, 60, 25]},
            {"id": "B003", "type": "icon", "bbox": [70, 10, 90, 30]},
        ],
        "ocr_text_boxes": [{"id": "T001", "text": "Secret", "bbox": [5, 6, 7, 8]}],
    }
    prompt = _svg_generation_prompt(
        {
            "phase": "template",
            "box_ir": box_ir,
            "template_ir": build_svg_template_ir(box_ir),
            "text_rendering": "model_text",
            "feedback": {"issues": [{"code": "viewbox_mismatch"}]},
        }
    )

    assert "using editable SVG primitives for run0 svg_self_draw elements and allowed manifest images for run0 crop/crop_nobg elements" in prompt
    assert "This template stage builds the first PPT-stable editable SVG reconstruction" in prompt
    assert "Image 1 is the original/current reference image" in prompt
    assert "Image 2 is a secondary semantic/template reference image" in prompt
    assert "The asset manifest lists allowed local raster image hrefs" in prompt
    assert "Treat Image 1 as the primary visual truth and run0 element analysis as the primary structured asset plan" in prompt
    assert "Compact Template IR JSON is only a soft geometry hint" in prompt
    assert "Do not output CSS <style> blocks, SVG filters, feDropShadow" in prompt
    assert "Do not output <symbol> or <use>" in prompt
    assert "Treat the input as an editable scientific structure diagram, not as a bitmap tracing task" in prompt
    assert "First infer the visual language" in prompt
    assert "Generate the PPT-stable SVG subset that the local svg_to_ppt tool maps to native PowerPoint objects" in prompt
    assert "Use rect for panels/modules/boxes" in prompt
    assert "Use line/polyline for straight or orthogonal connectors" in prompt
    assert "use <image> only for manifest-listed crop/crop_nobg assets" in prompt
    assert "Avoid symbol/use in model output" in prompt
    assert "Prefer explicit SVG presentation attributes on each object over CSS <style> blocks" in prompt
    assert "ids prefixed with module-, flow-, annotation-" in prompt
    assert "line/polyline/path with marker-end" in prompt
    assert "explicit polygon arrowheads only when marker-end cannot reproduce the source" in prompt
    assert "Unicode math characters and tspan superscript/subscript" in prompt
    assert "Compact Template IR JSON" in prompt
    assert "B001" in prompt
    assert "B002" in prompt
    assert "B003" not in prompt
    assert "OCR Text Hints JSON" in prompt
    assert "T001" in prompt
    assert "confidence" not in prompt
    assert "data-pb-orientation=\"horizontal|vertical-rl\"" in prompt
    assert "data-placeholder-kind=\"text\"" in prompt
    assert "Do not emit data-placeholder-kind=\"text\"" in prompt
    assert "Secret" in prompt
    assert "viewbox_mismatch" in prompt


def test_template_prompt_omits_grid_skill_when_no_grid_boxes():
    box_ir = {
        "canvas": {"width": 100, "height": 80},
        "boxes": [
            {"id": "B001", "type": "content_box", "bbox": [1, 2, 30, 40]},
            {"id": "B002", "type": "arrow", "bbox": [50, 10, 80, 20]},
        ],
        "ocr_text_boxes": [],
    }

    prompt = _svg_generation_prompt(
        {
            "phase": "template",
            "box_ir": box_ir,
            "asset_manifest": {"assets": []},
            "template_ir": build_svg_template_ir(box_ir),
            "feedback": {},
        }
    )

    assert "GRID/TABLE SVG SKILL" not in prompt


def test_grid_boxes_trigger_table_svg_skill_without_polluting_compact_ir():
    box_ir = {
        "canvas": {"width": 200, "height": 120},
        "boxes": [
            {"id": "B001", "type": "content_box", "bbox": [0, 0, 190, 110]},
            {"id": "B002", "type": "arrow", "bbox": [20, 100, 160, 104]},
            {"id": "B010", "type": "grid", "bbox": [20, 20, 180, 90]},
        ],
        "ocr_text_boxes": [],
    }
    template_ir = build_svg_template_ir(box_ir)

    prompt = _svg_generation_prompt(
        {
            "phase": "template",
            "box_ir": box_ir,
            "asset_manifest": {"assets": []},
            "template_ir": template_ir,
            "feedback": {},
        }
    )

    assert template_ir["boxes"] == [
        {"id": "B001", "type": "content_box", "bbox": [0, 0, 190, 110]},
        {"id": "B002", "type": "arrow", "bbox": [20, 100, 160, 104]},
    ]
    assert "GRID/TABLE SVG SKILL" in prompt
    assert "Detected grid/table layout IR regions" in prompt
    assert '"id": "B010"' in prompt
    assert "Use editable rect/line/polyline primitives" in prompt
    assert "Do not rasterize grids or tables" in prompt
    assert "Do not invent rows or columns" in prompt
    assert 'data-pb-role="grid"' in prompt


def test_visual_review_and_ir_refine_prompts_preserve_detected_grid_tables():
    box_ir = {
        "canvas": {"width": 200, "height": 120},
        "boxes": [
            {"id": "B001", "type": "content_box", "bbox": [0, 0, 190, 110]},
            {"id": "B010", "type": "grid", "bbox": [20, 20, 180, 90]},
        ],
        "ocr_text_boxes": [],
    }
    template_ir = build_svg_template_ir(box_ir)

    visual_review_prompt = _svg_generation_prompt(
        {
            "phase": "visual_review_layout",
            "visual_review_round": 2,
            "visual_review_total_rounds": 2,
            "visual_review_focus": "layout",
            "box_ir": box_ir,
            "asset_manifest": {"assets": []},
            "template_ir": template_ir,
            "base_svg": VALID_SVG,
            "feedback": {},
        }
    )
    ir_refine_prompt = _svg_generation_prompt(
        {
            "phase": "ir_refine",
            "box_ir": box_ir,
            "asset_manifest": {"assets": []},
            "template_ir": template_ir,
            "base_svg": VALID_SVG,
            "feedback": {},
        }
    )

    assert "GRID/TABLE SVG SKILL" in visual_review_prompt
    assert "correct grid/table alignment" in visual_review_prompt
    assert "GRID/TABLE SVG SKILL" in ir_refine_prompt
    assert "Preserve existing editable grid/table groups" in ir_refine_prompt


def test_codex_file_context_prompt_references_structured_files_without_inline_regions():
    box_ir = {
        "canvas": {"width": 200, "height": 120},
        "boxes": [
            {"id": "B001", "type": "content_box", "bbox": [0, 0, 190, 110]},
            {"id": "B002", "type": "arrow", "bbox": [20, 100, 160, 104]},
            {"id": "B010", "type": "grid", "bbox": [20, 20, 180, 90]},
        ],
        "ocr_text_boxes": [{"id": "T001", "text": "Secret Label", "bbox": [5, 6, 80, 20]}],
    }
    asset_manifest = {
        "assets": [
            {
                "asset_id": "AF99",
                "box_id": "B099",
                "bbox": [70, 10, 88, 28],
                "svg_href": "../assets/crops/AF99.png",
                "render_policy": "raster_png",
            }
        ]
    }

    template_prompt = _svg_generation_prompt(
        {
            "phase": "template",
            "box_ir": box_ir,
            "asset_manifest": asset_manifest,
            "template_ir": build_svg_template_ir(box_ir),
            "feedback": {"issues": [{"code": "viewbox_mismatch"}]},
            "file_context_mode": True,
            "workspace_dir": "out",
            "figure_path": "svg/svg_generation_reference.png",
            "reference_image_path": "svg/template_reference.png",
            "request_context_path": "svg/template_iterations/01_template/001/request_context.json",
            "prompt_path": "svg/template_iterations/01_template/001/prompt.txt",
            "output_svg_path": "svg/template_iterations/01_template/001/semantic.svg",
            "output_response_path": "svg/template_iterations/01_template/001/model_response.txt",
        }
    )
    ir_refine_prompt = _svg_generation_prompt(
        {
            "phase": "ir_refine",
            "box_ir": box_ir,
            "asset_manifest": asset_manifest,
            "template_ir": build_svg_template_ir(box_ir),
            "base_svg": LAYOUT_SVG,
            "base_svg_path": "svg/attempts/ir_refine/001/input_template.svg",
            "feedback": {"issues": [{"code": "text_overlap"}]},
            "file_context_mode": True,
            "workspace_dir": "out",
            "figure_path": "svg/svg_generation_reference.png",
            "reference_image_path": "svg/template_rendered.png",
            "request_context_path": "svg/attempts/ir_refine/001/request_context.json",
            "prompt_path": "svg/attempts/ir_refine/001/prompt.txt",
            "output_svg_path": "svg/attempts/ir_refine/001/semantic.svg",
            "output_response_path": "svg/attempts/ir_refine/001/model_response.txt",
        }
    )

    for prompt in (template_prompt, ir_refine_prompt):
        assert "Compact Template IR JSON:" not in prompt
        assert "OCR Text Hints JSON" not in prompt
        assert "Attempt feedback JSON" not in prompt
        assert '"bbox"' not in prompt
        assert '"id": "B010"' not in prompt
        assert "Secret Label" not in prompt
        assert "AF99.png" not in prompt
        assert "Read the compact template IR from: svg/svg_template_ir.json" in prompt
        assert "Attempt feedback source" in prompt
        assert "layout IR JSON: box_ir/box_ir.json" in prompt
        assert "Asset manifest JSON: svg_to_ppt/assets/asset_manifest.json" in prompt

    assert "OCR boxes JSON: ocr/ocr_boxes.json" in template_prompt
    assert "Detected grid/table layout IR regions are available in the layout IR file" in template_prompt
    assert "Read the validated visual template SVG from: svg/attempts/ir_refine/001/input_template.svg" in ir_refine_prompt
    assert "Read the only allowed local raster image entries from: svg_to_ppt/assets/asset_manifest.json" in ir_refine_prompt
    assert "Validated visual template SVG from stage 1:\n<svg" not in ir_refine_prompt


def test_codex_file_context_prompts_have_unambiguous_stage_and_output_contracts():
    box_ir = {
        "canvas": {"width": 200, "height": 120},
        "boxes": [
            {"id": "B001", "type": "content_box", "bbox": [0, 0, 190, 110]},
            {"id": "B002", "type": "arrow", "bbox": [20, 100, 160, 104]},
        ],
        "ocr_text_boxes": [],
    }
    template_ir = build_svg_template_ir(box_ir)
    common_kwargs = {
        "box_ir": box_ir,
        "asset_manifest": {"assets": []},
        "template_ir": template_ir,
        "file_context_mode": True,
        "workspace_dir": "out",
        "request_context_path": "svg/attempt/request_context.json",
        "prompt_path": "svg/attempt/prompt.txt",
        "output_svg_path": "svg/attempt/semantic.svg",
        "output_response_path": "svg/attempt/model_response.txt",
        "feedback": {},
    }

    template_prompt = _svg_generation_prompt(
        {
            **common_kwargs,
            "phase": "template",
            "figure_path": "svg/svg_generation_reference.png",
            "reference_image_path": "svg/template_reference.png",
        }
    )
    visual_prompt = _svg_generation_prompt(
        {
            **common_kwargs,
            "phase": "visual_review_text_style",
            "visual_review_round": 1,
            "visual_review_total_rounds": 1,
            "visual_review_focus": "text_style",
            "base_svg_path": "svg/template_iterations/01_template/003/semantic.svg",
            "figure_path": "svg/svg_generation_reference.png",
            "reference_image_path": "svg/template_rendered.png",
        }
    )
    ir_prompt = _svg_generation_prompt(
        {
            **common_kwargs,
            "phase": "ir_refine",
            "base_svg_path": "svg/template_iterations/02_visual_review_loop/round_01_text_style/001/semantic.svg",
            "figure_path": "svg/svg_generation_reference.png",
            "reference_image_path": "svg/template_rendered.png",
        }
    )

    for prompt in (template_prompt, visual_prompt, ir_prompt):
        assert "ROLE" in prompt
        assert "STAGE GOAL" in prompt
        assert "MUST READ FILES" in prompt
        assert "IMAGE MEANINGS" in prompt
        assert "SOURCE PRIORITY" in prompt
        assert "ALLOWED ACTIONS" in prompt
        assert "FORBIDDEN ACTIONS" in prompt
        assert "VALIDATION CHECKLIST" in prompt
        assert "OUTPUT CONTRACT" in prompt
        assert "Write exactly one complete SVG document to: svg/attempt/semantic.svg" in prompt
        assert "Do not put SVG code in the final chat response" in prompt
        assert "Return exactly two fenced blocks" not in prompt
        assert "Return raw SVG only" not in prompt

    assert "Run 1 / template" in template_prompt
    assert "Build the first editable vector template" in template_prompt
    assert "Insert allowed local raster images listed in the asset manifest" in template_prompt
    assert "Run 2 / visual_review_text_style" in visual_prompt
    assert "Use allowed local raster images listed in the asset manifest" in visual_prompt
    assert "Do not invent raster assets" in visual_prompt
    assert "Run 3 / ir_refine" in ir_prompt
    assert "Keep using manifest-listed raster <image> elements" in ir_prompt
    assert "Use the asset manifest for allowed raster asset insertion" in ir_prompt


def test_codex_thread_prompts_split_shared_context_from_per_turn_instructions():
    box_ir = {
        "canvas": {"width": 200, "height": 120},
        "boxes": [
            {"id": "B001", "type": "content_box", "bbox": [0, 0, 190, 110]},
            {"id": "B002", "type": "arrow", "bbox": [20, 100, 160, 104]},
            {"id": "B010", "type": "grid", "bbox": [20, 20, 180, 90]},
        ],
        "ocr_text_boxes": [
            {"id": "T001", "text": "Secret Label", "bbox": [5, 6, 80, 20]}
        ],
    }
    asset_manifest = {
        "assets": [
            {
                "asset_id": "AF99",
                "box_id": "B099",
                "bbox": [70, 10, 88, 28],
                "svg_href": "../assets/crops/AF99.png",
                "render_policy": "raster_png",
            }
        ]
    }
    common_kwargs = {
        "box_ir": box_ir,
        "asset_manifest": asset_manifest,
        "template_ir": build_svg_template_ir(box_ir),
        "file_context_mode": True,
        "codex_thread_turn_mode": True,
        "workspace_dir": "out",
        "figure_path": "svg/svg_generation_reference.png",
        "reference_image_path": "svg/template_reference.png",
        "request_context_path": "svg/attempt/request_context.json",
        "prompt_path": "svg/attempt/prompt.txt",
        "output_svg_path": "svg/attempt/semantic.svg",
        "output_response_path": "svg/attempt/model_response.txt",
        "feedback": {},
    }

    shared_prompt = pipeline_module._svg_generation_thread_shared_prompt(common_kwargs)
    template_prompt = _svg_generation_prompt(
        {
            **common_kwargs,
            "phase": "template",
            "reference_image_path": "svg/template_reference.png",
        }
    )
    visual_prompt = _svg_generation_prompt(
        {
            **common_kwargs,
            "phase": "visual_review_text_style",
            "visual_review_round": 1,
            "visual_review_total_rounds": 1,
            "visual_review_focus": "text_style",
            "base_svg_path": "svg/template_iterations/01_template/001/semantic.svg",
            "reference_image_path": "svg/template_rendered.png",
        }
    )
    ir_prompt = _svg_generation_prompt(
        {
            **common_kwargs,
            "phase": "ir_refine",
            "base_svg_path": "svg/template_iterations/02_visual_review_loop/round_01_text_style/001/semantic.svg",
            "reference_image_path": "svg/template_rendered.png",
        }
    )

    assert "DRAWAI CODEX THREAD SHARED CONTEXT" in shared_prompt
    assert "MUST READ FILES" in shared_prompt
    assert "WORKSPACE RULES" in shared_prompt
    assert "layout IR JSON: box_ir/box_ir.json" in shared_prompt
    assert "SVG template IR JSON: svg/svg_template_ir.json" in shared_prompt
    assert "OUTPUT CONTRACT" not in shared_prompt
    assert "Write exactly one complete SVG document to:" not in shared_prompt

    for prompt in (template_prompt, visual_prompt, ir_prompt):
        assert "STAGE GOAL" in prompt
        assert "IMAGE MEANINGS" in prompt
        assert "CURRENT TURN FILES" in prompt
        assert "Attempt feedback source" in prompt
        assert "MUST READ FILES" not in prompt
        assert "WORKSPACE RULES" not in prompt
        assert "OUTPUT CONTRACT" not in prompt
        assert "Sandbox cwd / run root" not in prompt
        assert "Write exactly one complete SVG document to:" not in prompt
        assert "Secret Label" not in prompt
        assert "AF99.png" not in prompt
        assert '"bbox"' not in prompt

    assert "Run 1 / template" in template_prompt
    assert "Run 2 / visual_review_text_style" in visual_prompt
    assert "Current input template SVG: svg/template_iterations/01_template/001/semantic.svg" in visual_prompt
    assert "Run 3 / ir_refine" in ir_prompt
    assert "Current input template SVG: svg/template_iterations/02_visual_review_loop/round_01_text_style/001/semantic.svg" in ir_prompt


def test_template_prompt_retires_asset_placeholder_group_contract():
    box_ir = {
        "canvas": {"width": 100, "height": 80},
        "boxes": [
            {"id": "B001", "type": "content_box", "bbox": [1, 2, 30, 40]},
            {"id": "B002", "type": "arrow", "bbox": [35, 20, 60, 25]},
            {"id": "B003", "type": "icon", "bbox": [70, 10, 90, 30]},
        ],
        "ocr_text_boxes": [{"id": "T001", "text": "Secret", "bbox": [5, 6, 7, 8]}],
    }
    prompt = _svg_generation_prompt(
        {
            "phase": "template",
            "box_ir": box_ir,
            "template_ir": build_svg_template_ir(box_ir),
            "text_rendering": "model_text",
        }
    )

    assert "RETIRED PLACEHOLDER CONTRACT" in prompt
    assert "Do not output AF01/AF02 identifiers" in prompt
    assert '<g id="AF01" data-placeholder-group="asset">' not in prompt
    assert '<rect data-placeholder-kind="asset" data-asset-id="AF01"' not in prompt
    assert "Asset Placeholder Plan JSON" not in prompt


def test_ir_refine_prompt_retires_asset_placeholder_group_contract():
    box_ir = {
        "canvas": {"width": 100, "height": 80},
        "boxes": [
            {"id": "B001", "type": "content_box", "bbox": [1, 2, 30, 40]},
            {"id": "B002", "type": "arrow", "bbox": [35, 20, 60, 25]},
        ],
        "ocr_text_boxes": [{"id": "T001", "text": "Secret", "bbox": [5, 6, 7, 8]}],
    }
    prompt = _svg_generation_prompt(
        {
            "phase": "ir_refine",
            "box_ir": box_ir,
            "template_ir": build_svg_template_ir(box_ir),
            "base_svg": LAYOUT_SVG,
            "text_rendering": "model_text",
            "asset_manifest": {
                "assets": [
                    {
                        "asset_id": "AF01",
                        "box_id": "B003",
                        "bbox": [70, 10, 88, 28],
                        "svg_href": "../assets/crops/AF01.png",
                        "source_svg_href": "../assets/crops/AF01_source.png",
                        "render_policy": "raster_png",
                    }
                ]
            },
        }
    )

    assert "Do not output AF01/AF02 identifiers" in prompt
    assert "Asset Placeholder Plan JSON" not in prompt
    assert "Compact asset constraints for manifest-backed raster restoration" in prompt
    assert "../assets/crops/AF01.png" in prompt
    assert '"render_policy": "raster_png"' in prompt
    assert '"source_svg_href":' not in prompt
    assert "OCR Text Hints JSON" not in prompt
    assert "Secret" not in prompt
    assert "RASTER ASSET EXCLUSION ZONES" in prompt
    assert "do not redraw complex crop/crop_nobg content when an allowed href exists" in prompt
    assert "line/polyline/path with marker-end" in prompt
    assert "Render connector arrows after background panels/modules and before raster image assets" in prompt
    assert '<g id="AF01" data-placeholder-group="asset">' not in prompt
    assert '<rect data-placeholder-kind="asset" data-asset-id="AF01"' not in prompt
    assert "may be inserted as local raster <image> elements" in prompt
    assert "insertable_components[].svg_href" in prompt
    assert "never use the parent crop/source_svg_href" in prompt


def test_ir_refine_finalizer_injects_insertable_components_and_skips_parent_crop(tmp_path: Path):
    figure, reference, box_ir = _make_inputs(tmp_path)
    output_dir = tmp_path / "out" / "svg"
    component_asset = tmp_path / "out" / "assets" / "crops" / "AF13_C01_nobg.png"
    parent_asset = tmp_path / "out" / "assets" / "crops" / "AF13.png"
    duplicate_asset = tmp_path / "out" / "assets" / "crops" / "AF16_nobg.png"
    component_asset.parent.mkdir(parents=True)
    Image.new("RGBA", (10, 15), (255, 80, 0, 128)).save(component_asset)
    Image.new("RGB", (30, 30), "lightblue").save(parent_asset)
    Image.new("RGBA", (12, 17), (255, 120, 0, 128)).save(duplicate_asset)
    asset_manifest = {
        "schema": "drawai.asset_manifest.v1",
        "assets": [
            {
                "asset_id": "AF13",
                "box_id": "B013",
                "bbox": [10, 10, 40, 40],
                "insertable": False,
                "restore_strategy": "component_assets",
                "source_svg_href": "../assets/crops/AF13.png",
                "insertable_components": [
                    {
                        "component_id": "AF13_C01",
                        "parent_asset_id": "AF13",
                        "bbox": [30, 15, 40, 30],
                        "svg_href": "../assets/crops/AF13_C01_nobg.png",
                        "render_policy": "raster_png",
                        "background_policy": "transparent_subject",
                    }
                ],
            },
            {
                "asset_id": "AF16",
                "box_id": "B016",
                "bbox": [29, 14, 41, 31],
                "svg_href": "../assets/crops/AF16_nobg.png",
                "render_policy": "raster_png",
                "background_policy": "transparent_subject",
            },
        ],
    }
    svg_with_draft_placeholders = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80" width="100" height="80">'
        '<rect width="100" height="80" fill="white"/>'
        '<rect x="30" y="15" width="10" height="15" fill="#858584"/>'
        '<rect x="29" y="14" width="12" height="17" fill="#858584"/>'
        "</svg>"
    )

    def fake_invoker(*, phase, **kwargs):
        if phase == "template":
            return svg_with_draft_placeholders
        if phase.startswith("visual_review_"):
            return kwargs["base_svg"]
        assert phase == "ir_refine"
        return svg_with_draft_placeholders

    result = run_svg_generation_loop(
        box_ir=box_ir,
        figure_path=figure,
        reference_image_path=reference,
        asset_manifest=asset_manifest,
        output_dir=output_dir,
        max_attempts=1,
        invoker=fake_invoker,
        staged_generation=True,
        text_rendering="model_text",
    )

    final_svg = Path(result["artifacts"]["semantic_svg"]).read_text(encoding="utf-8")
    assert "../assets/crops/AF13_C01_nobg.png" in final_svg
    assert "../assets/crops/AF13.png" not in final_svg
    assert "../assets/crops/AF16_nobg.png" not in final_svg
    assert "#858584" not in final_svg
    assert 'x="30"' in final_svg
    assert 'y="15"' in final_svg
    assert 'width="10"' in final_svg
    assert 'height="15"' in final_svg
    assert 'data-pb-parent-asset-id="AF13"' in final_svg
    assert 'data-pb-component-id="AF13_C01"' in final_svg


def test_ir_refine_finalizer_removes_neutral_underlay_for_existing_manifest_image(tmp_path: Path):
    figure, reference, box_ir = _make_inputs(tmp_path)
    output_dir = tmp_path / "out" / "svg"
    asset = tmp_path / "out" / "assets" / "crops" / "AF01.png"
    asset.parent.mkdir(parents=True)
    Image.new("RGB", (20, 18), "orange").save(asset)
    asset_manifest = {
        "schema": "drawai.asset_manifest.v1",
        "assets": [
            {
                "asset_id": "AF01",
                "box_id": "B001",
                "bbox": [20, 10, 40, 28],
                "svg_href": "../assets/crops/AF01.png",
                "render_policy": "raster_png",
                "background_policy": "preserve_crop",
            }
        ],
    }
    svg_with_existing_image = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80" width="100" height="80">'
        '<rect width="100" height="80" fill="white"/>'
        '<rect x="20" y="10" width="20" height="18" fill="#f1f1ec"/>'
        '<image x="20" y="10" width="20" height="18" href="../assets/crops/AF01.png" preserveAspectRatio="none"/>'
        "</svg>"
    )

    def fake_invoker(*, phase, **kwargs):
        if phase == "template":
            return VALID_SVG
        if phase.startswith("visual_review_"):
            return kwargs["base_svg"]
        assert phase == "ir_refine"
        return svg_with_existing_image

    result = run_svg_generation_loop(
        box_ir=box_ir,
        figure_path=figure,
        reference_image_path=reference,
        asset_manifest=asset_manifest,
        output_dir=output_dir,
        max_attempts=1,
        invoker=fake_invoker,
        staged_generation=True,
        text_rendering="model_text",
    )

    final_svg = Path(result["artifacts"]["semantic_svg"]).read_text(encoding="utf-8")
    report = json.loads(Path(result["phase_reports"]["ir_refine"][0]["validation_report"]).read_text(encoding="utf-8"))
    assert "../assets/crops/AF01.png" in final_svg
    assert "#f1f1ec" not in final_svg
    assert report["manifest_asset_injection"]["removed_underlay_count"] == 1


def test_visual_review_layout_prompt_requires_arrow_deletion_and_visual_acceptance():
    box_ir = {
        "canvas": {"width": 100, "height": 80},
        "boxes": [
            {"id": "B001", "type": "content_box", "bbox": [1, 2, 30, 40]},
            {"id": "B002", "type": "arrow", "bbox": [35, 20, 60, 25]},
            {"id": "B003", "type": "icon", "bbox": [70, 10, 90, 30]},
        ],
        "ocr_text_boxes": [{"id": "T001", "text": "Secret", "bbox": [5, 6, 7, 8]}],
    }
    prompt = _svg_generation_prompt(
        {
            "phase": "visual_review_layout",
            "visual_review_round": 2,
            "visual_review_total_rounds": 2,
            "visual_review_focus": "layout",
            "box_ir": box_ir,
            "template_ir": build_svg_template_ir(box_ir),
            "base_svg": LAYOUT_SVG,
            "text_rendering": "model_text",
            "feedback": {"issues": [{"code": "visual_template_alignment"}]},
        }
    )

    assert "Image 1 is the original/current reference image" in prompt
    assert "Image 2 is the current rendered template SVG" in prompt
    assert "Use the run0-refined asset manifest for crop/crop_nobg regions" in prompt
    assert "visual review loop round 2 of 2" in prompt
    assert "Review the whole figure together, not only arrows or one local region" in prompt
    assert "Check and correct panels/modules/content boxes" in prompt
    assert "Remove unsupported duplicate/invented arrows" in prompt
    assert "Do not optimize one category by breaking another" in prompt
    assert "whole-figure Modification Notes" in prompt
    assert "```modification_notes" in prompt
    assert "layout IR arrow geometry is a soft hint" in prompt
    assert "visual acceptance check" in prompt
    assert "Text is part of the editable reconstruction" in prompt
    assert "Use direct <image> elements only for allowed manifest entries" in prompt
    assert "Do not use AF01/AF02 identifiers" in prompt
    assert "Compact Template IR JSON" in prompt
    assert "B001" in prompt
    assert "B002" in prompt
    assert "B003" not in prompt
    assert "OCR Text Hints JSON" not in prompt
    assert "Secret" not in prompt
    assert "visual_template_alignment" in prompt


def test_refine_attempts_save_model_modification_notes(tmp_path: Path):
    figure, reference, box_ir, asset_manifest = _make_staged_inputs(tmp_path)
    output_dir = tmp_path / "out" / "svg"

    def fake_invoker(*, phase, **kwargs):
        if phase == "template":
            return LAYOUT_SVG[:-6] + MODEL_TEXT + "</svg>"
        if phase == "visual_review_text_style":
            return (
                "```modification_notes\n"
                "- Text/style: preserved editable label text and font styling.\n"
                "```\n"
                f"```svg\n{LAYOUT_SVG[:-6]}{MODEL_TEXT}</svg>\n```"
            )
        if phase == "visual_review_layout":
            return (
                "```modification_notes\n"
                "- Layout: removed unsupported connector and aligned panel headers.\n"
                "- Arrows: shortened the main connector endpoint.\n"
                "```\n"
                f"```svg\n{REFINED_LAYOUT_SVG[:-6]}{MODEL_TEXT}</svg>\n```"
            )
        assert phase == "ir_refine"
        return (
            "```modification_notes\n"
            "- Full image: refined simplified complex regions without asset placeholders.\n"
            "- Assets: kept model-authored text and ordinary editable SVG geometry.\n"
            "```\n"
            "```svg\n"
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80" width="100" height="80">'
            '<rect width="100" height="80" fill="white"/>'
            '<rect x="70" y="10" width="18" height="18" fill="#ccc"/>'
            f"{MODEL_TEXT}"
            "</svg>\n"
            "```"
        )

    result = run_svg_generation_loop(
        box_ir=box_ir,
        figure_path=figure,
        reference_image_path=reference,
        asset_manifest=asset_manifest,
        output_dir=output_dir,
        max_attempts=1,
        invoker=fake_invoker,
        staged_generation=True,
        visual_review_rounds=("text_style", "layout"),
        text_rendering="model_text",
    )

    visual_attempt = output_dir / "template_iterations" / "02_visual_review_loop" / "round_02_layout" / "001"
    ir_attempt = output_dir / "attempts" / "ir_refine" / "001"
    visual_notes = visual_attempt / "modification_notes.md"
    ir_notes = ir_attempt / "modification_notes.md"
    assert "removed unsupported connector" in visual_notes.read_text(encoding="utf-8")
    assert "without asset placeholders" in ir_notes.read_text(encoding="utf-8")

    visual_report = result["phase_reports"]["visual_review"][1]
    ir_report = result["phase_reports"]["ir_refine"][0]
    assert visual_report["modification_notes"] == str(visual_notes)
    assert ir_report["modification_notes"] == str(ir_notes)


def test_svg_generation_loop_rejects_non_model_text_rendering(tmp_path: Path):
    figure, reference, box_ir = _make_inputs(tmp_path)

    with pytest.raises(SvgGenerationError) as exc_info:
        run_svg_generation_loop(
            box_ir=box_ir,
            figure_path=figure,
            reference_image_path=reference,
            asset_manifest={"assets": []},
            output_dir=tmp_path / "svg",
            max_attempts=1,
            invoker=lambda **kwargs: VALID_SVG,
            text_rendering="unsupported",
        )

    assert exc_info.value.metadata["last_issues"][0]["code"] == "unsupported_text_rendering"


def test_svg_generation_loop_accepts_canonical_svg_href_from_attempt_dir(tmp_path: Path):
    figure, reference, box_ir = _make_inputs(tmp_path)
    output_dir = tmp_path / "out" / "svg"
    asset = tmp_path / "out" / "assets" / "crops" / "AF01.png"
    asset.parent.mkdir(parents=True)
    Image.new("RGBA", (2, 2), (255, 0, 0, 255)).save(asset)

    def fake_invoker(**kwargs):
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80" width="100" height="80">'
            '<rect width="100" height="80" fill="white"/>'
            '<image href="../assets/crops/AF01.png" width="10" height="10"/>'
            "</svg>"
        )

    result = run_svg_generation_loop(
        box_ir=box_ir,
        figure_path=figure,
        reference_image_path=reference,
        asset_manifest={"assets": [{"asset_id": "AF01", "svg_href": "../assets/crops/AF01.png"}]},
        output_dir=output_dir,
        max_attempts=1,
        invoker=fake_invoker,
    )

    assert result["status"] == "ok"
    assert (output_dir / "semantic.svg").read_text(encoding="utf-8").find("../assets/crops/AF01.png") != -1


def test_svg_generation_loop_rewrites_native_backfill_source_crop_href(tmp_path: Path):
    figure, reference, box_ir = _make_inputs(tmp_path)
    box_ir["boxes"] = [
        {"id": "B031", "type": "icon", "bbox": [10, 12, 28, 30]},
    ]
    output_dir = tmp_path / "out" / "svg"
    crops_dir = tmp_path / "out" / "svg_to_ppt" / "assets" / "crops"
    crops_dir.mkdir(parents=True)
    Image.new("RGBA", (18, 18), (0, 128, 255, 255)).save(crops_dir / "AF31.png")
    decisions_path = tmp_path / "out" / "svg_to_ppt" / "assets" / "asset_decisions.json"
    decisions_path.write_text(
        json.dumps(
            {
                "decisions": [
                    {
                        "box_id": "B031",
                        "decision": "native_svg",
                        "asset_id": "AF31",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    def fake_invoker(**kwargs):
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80" width="100" height="80">'
            '<rect width="100" height="80" fill="white"/>'
            '<image href="../svg_to_ppt/assets/crops/AF31.png" x="10" y="12" width="18" height="18"/>'
            "</svg>"
        )

    result = run_svg_generation_loop(
        box_ir=box_ir,
        figure_path=figure,
        reference_image_path=reference,
        asset_manifest={"assets": []},
        output_dir=output_dir,
        max_attempts=1,
        invoker=fake_invoker,
    )

    final_svg = (output_dir / "semantic.svg").read_text(encoding="utf-8")
    attempt_report = json.loads(
        (output_dir / "attempts" / "001" / "validation_report.json").read_text(encoding="utf-8")
    )
    repaired_href = "native_backfill_assets/single_001/AF31.png"
    assert result["status"] == "ok"
    assert repaired_href in final_svg
    assert "../svg_to_ppt/assets/crops/AF31.png" not in final_svg
    assert (output_dir / repaired_href).is_file()
    assert attempt_report["native_backfill_href_repair"]["rewritten_count"] == 1
    assert attempt_report["native_backfill_href_repair"]["materialized_count"] == 1


def test_svg_generation_loop_missing_svg_retries_with_feedback(tmp_path: Path):
    figure, reference, box_ir = _make_inputs(tmp_path)
    calls = []

    def fake_invoker(*, attempt, feedback, **kwargs):
        calls.append((attempt, feedback))
        if attempt == 1:
            return "I cannot produce that."
        return VALID_SVG

    result = run_svg_generation_loop(
        box_ir=box_ir,
        figure_path=figure,
        reference_image_path=reference,
        asset_manifest={"assets": []},
        output_dir=tmp_path / "svg",
        max_attempts=2,
        invoker=fake_invoker,
    )

    assert result["status"] == "ok"
    assert len(calls) == 2
    feedback_issues = calls[1][1]["issues"]
    feedback_codes = {issue["code"] for issue in feedback_issues}
    assert "missing_svg_output" in feedback_codes
    assert "xml_parse_error" in feedback_codes
    assert any("SVG" in issue["message"] for issue in feedback_issues if issue["code"] == "missing_svg_output")
    rendered_path = tmp_path / "svg" / "attempts" / "001" / "rendered.png"
    assert rendered_path.exists()
    with Image.open(rendered_path) as rendered:
        assert rendered.size == (100, 80)
        assert rendered.getpixel((0, 0)) != (255, 255, 255)

    report_path = tmp_path / "svg" / "attempts" / "001" / "validation_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report_codes = {issue["code"] for issue in report["issues"]}
    assert report["status"] == "failed"
    assert "missing_svg_output" in report_codes
    assert "xml_parse_error" in report_codes


def test_svg_generation_loop_exhaustion_raises_and_keeps_reports(tmp_path: Path):
    figure, reference, box_ir = _make_inputs(tmp_path)

    def fake_invoker(**kwargs):
        return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 90 80"></svg>'

    with pytest.raises(SvgGenerationError) as exc_info:
        run_svg_generation_loop(
            box_ir=box_ir,
            figure_path=figure,
            reference_image_path=reference,
            asset_manifest={"assets": []},
            output_dir=tmp_path / "svg",
            max_attempts=2,
            invoker=fake_invoker,
        )

    error = exc_info.value
    assert error.metadata["status"] == "failed"
    assert error.metadata["attempt_count"] == 2
    assert any(issue["code"] == "viewbox_mismatch" for issue in error.metadata["last_issues"])
    assert (tmp_path / "svg" / "attempts" / "001" / "validation_report.json").exists()
    assert (tmp_path / "svg" / "attempts" / "002" / "validation_report.json").exists()
    assert (tmp_path / "svg" / "svg_validation_report.json").exists()
    assert not (tmp_path / "svg" / "semantic.svg").exists()


def test_svg_generation_loop_copies_final_render_only_from_valid_attempt(tmp_path: Path):
    figure, reference, box_ir = _make_inputs(tmp_path)

    def fake_invoker(*, attempt, **kwargs):
        if attempt == 1:
            return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 90 80" width="100" height="80"><rect width="100" height="80" fill="white"/><circle cx="20" cy="20" r="10" fill="red"/></svg>'
        return VALID_BLUE_SVG

    result = run_svg_generation_loop(
        box_ir=box_ir,
        figure_path=figure,
        reference_image_path=reference,
        asset_manifest={"assets": []},
        output_dir=tmp_path / "svg",
        max_attempts=2,
        invoker=fake_invoker,
    )

    final_render = Path(result["artifacts"]["rendered_png"])
    invalid_render = tmp_path / "svg" / "attempts" / "001" / "rendered.png"
    valid_render = tmp_path / "svg" / "attempts" / "002" / "rendered.png"
    assert invalid_render.exists()
    assert valid_render.exists()
    assert final_render.read_bytes() == valid_render.read_bytes()
    assert final_render.read_bytes() != invalid_render.read_bytes()


def test_svg_generation_loop_attempt_directories_are_zero_padded(tmp_path: Path):
    figure, reference, box_ir = _make_inputs(tmp_path)

    def fake_invoker(*, attempt, **kwargs):
        if attempt == 1:
            return "not svg"
        return VALID_SVG

    run_svg_generation_loop(
        box_ir=box_ir,
        figure_path=figure,
        reference_image_path=reference,
        asset_manifest={"assets": []},
        output_dir=tmp_path / "svg",
        max_attempts=2,
        invoker=fake_invoker,
    )

    attempts = sorted(path.name for path in (tmp_path / "svg" / "attempts").iterdir())
    assert attempts == ["001", "002"]


def test_svg_generation_loop_writes_complete_artifact_set_for_each_attempt(tmp_path: Path):
    figure, reference, box_ir = _make_inputs(tmp_path)

    def fake_invoker(*, attempt, **kwargs):
        if attempt == 1:
            return "not svg"
        return VALID_SVG

    run_svg_generation_loop(
        box_ir=box_ir,
        figure_path=figure,
        reference_image_path=reference,
        asset_manifest={"assets": []},
        output_dir=tmp_path / "svg",
        max_attempts=2,
        invoker=fake_invoker,
    )

    for attempt_name in ("001", "002"):
        attempt_dir = tmp_path / "svg" / "attempts" / attempt_name
        assert (attempt_dir / "model_response.txt").exists()
        assert (attempt_dir / "semantic.svg").exists()
        assert (attempt_dir / "rendered.png").exists()
        assert (attempt_dir / "validation_report.json").exists()


def test_svg_generation_loop_clears_stale_outputs_when_reusing_output_dir(tmp_path: Path):
    figure, reference, box_ir = _make_inputs(tmp_path)
    output_dir = tmp_path / "svg"
    unrelated = output_dir / "keep.txt"

    def successful_invoker(*, attempt, **kwargs):
        if attempt < 3:
            return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 90 80"></svg>'
        return VALID_SVG

    run_svg_generation_loop(
        box_ir=box_ir,
        figure_path=figure,
        reference_image_path=reference,
        asset_manifest={"assets": []},
        output_dir=output_dir,
        max_attempts=3,
        invoker=successful_invoker,
    )
    unrelated.write_text("preserve me", encoding="utf-8")
    assert (output_dir / "semantic.svg").exists()
    assert (output_dir / "rendered.png").exists()
    assert sorted(path.name for path in (output_dir / "attempts").iterdir()) == ["001", "002", "003"]

    def failing_invoker(**kwargs):
        return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 90 80"></svg>'

    with pytest.raises(SvgGenerationError):
        run_svg_generation_loop(
            box_ir=box_ir,
            figure_path=figure,
            reference_image_path=reference,
            asset_manifest={"assets": []},
            output_dir=output_dir,
            max_attempts=1,
            invoker=failing_invoker,
        )

    assert not (output_dir / "semantic.svg").exists()
    assert not (output_dir / "rendered.png").exists()
    assert (output_dir / "svg_validation_report.json").exists()
    assert unrelated.read_text(encoding="utf-8") == "preserve me"
    assert sorted(path.name for path in (output_dir / "attempts").iterdir()) == ["001"]


def test_svg_generation_loop_requires_injected_invoker(tmp_path: Path):
    figure, reference, box_ir = _make_inputs(tmp_path)

    with pytest.raises(SvgGenerationError) as exc_info:
        run_svg_generation_loop(
            box_ir=box_ir,
            figure_path=figure,
            reference_image_path=reference,
            asset_manifest={"assets": []},
            output_dir=tmp_path / "svg",
            max_attempts=1,
        )

    error = exc_info.value
    assert "invoker" in str(error)
    assert error.metadata["last_issues"][0]["code"] == "invoker_missing"
