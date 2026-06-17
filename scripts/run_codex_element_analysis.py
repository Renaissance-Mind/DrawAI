#!/usr/bin/env python
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from drawai.codex_python_sdk_svg import (  # noqa: E402
    _archive_codex_session_logs,
    _codex_sdk_env,
    _codex_sdk_jsonable,
    _isolated_codex_home,
    _load_openai_codex_sdk,
    _normalize_codex_model_name,
    _normalize_codex_reasoning_effort,
    _run_thread_with_timeout,
    controlled_codex_config_overrides,
)
from drawai.codex_cli import resolve_codex_executable  # noqa: E402


SCHEMA_REQUEST = "drawai.codex_element_analysis_request.v1"
SCHEMA_OUTPUT = "drawai.codex_element_analysis.v1"
CATEGORIES = ("svg_self_draw", "crop", "crop_nobg")
REFINEMENT_ACTIONS = ("unchanged", "adjusted", "split", "added")


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    case_dirs = [path.expanduser().resolve(strict=False) for path in args.case_dirs]
    if not case_dirs:
        raise SystemExit("At least one case directory is required.")

    started_at = time.monotonic()
    if args.max_workers == 1 or len(case_dirs) == 1:
        results = [run_case(case_dir, args) for case_dir in case_dirs]
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.max_workers) as pool:
            futures = [pool.submit(run_case, case_dir, args) for case_dir in case_dirs]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
            results.sort(key=lambda item: item["case_dir"])

    summary = {
        "schema": "drawai.codex_element_analysis_batch.v1",
        "status": "ok" if all(item["status"] == "ok" for item in results) else "failed",
        "case_count": len(results),
        "elapsed_seconds": round(time.monotonic() - started_at, 3),
        "results": results,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "ok" else 1


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a Codex pass that classifies DrawAI layout elements into SVG/crop/no-bg buckets."
    )
    parser.add_argument("case_dirs", nargs="+", type=Path, help="DrawAI case output directories.")
    parser.add_argument("--max-workers", type=int, default=1, help="Parallel Codex workers.")
    parser.add_argument("--model", default="", help="Optional Codex model override.")
    parser.add_argument(
        "--reasoning-effort",
        default="medium",
        choices=("none", "minimal", "low", "medium", "high", "xhigh"),
        help="Codex reasoning effort for this analysis pass.",
    )
    parser.add_argument("--timeout-seconds", type=float, default=900.0)
    parser.add_argument(
        "--invoker",
        choices=("cli", "sdk"),
        default="cli",
        help="Use codex exec CLI by default; sdk is retained for parity with SVG generation experiments.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Do not invoke Codex when element_analysis.json already exists.",
    )
    parser.add_argument(
        "--config-override",
        action="append",
        default=[],
        help="Additional Codex -c key=value override for the SDK app-server.",
    )
    parsed = parser.parse_args(argv)
    if parsed.max_workers <= 0:
        parser.error("--max-workers must be positive")
    if parsed.timeout_seconds <= 0:
        parser.error("--timeout-seconds must be positive")
    return parsed


def run_case(case_dir: Path, args: argparse.Namespace) -> dict[str, Any]:
    output_dir = case_dir / "reports" / "element_analysis_codex"
    output_path = output_dir / "element_analysis.json"
    started_at = time.monotonic()
    if args.skip_existing and output_path.exists():
        return {
            "status": "ok",
            "case_dir": str(case_dir),
            "output_path": str(output_path),
            "skipped": True,
        }

    output_dir.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()
    request = build_request(case_dir)
    request_path = output_dir / "element_analysis_request.json"
    candidate_table_path = output_dir / "candidate_table.tsv"
    prompt_path = output_dir / "prompt.txt"
    trace_path = output_dir / "codex_element_analysis_trace.jsonl"
    write_json(request_path, request)
    write_candidate_table(candidate_table_path, request)
    prompt_path.write_text(
        build_prompt(case_dir, request_path, candidate_table_path, output_path),
        encoding="utf-8",
    )

    status_path = output_dir / "run_status.json"
    write_json(
        status_path,
        {
            "schema": "drawai.codex_element_analysis_status.v1",
            "status": "running",
            "case_dir": str(case_dir),
            "started_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "request_path": str(request_path),
            "candidate_table_path": str(candidate_table_path),
            "prompt_path": str(prompt_path),
        },
    )

    if args.invoker == "sdk":
        codex_result = invoke_codex_element_analysis_sdk(
            case_dir=case_dir,
            prompt=prompt_path.read_text(encoding="utf-8"),
            image_paths=analysis_images(case_dir),
            output_dir=output_dir,
            trace_path=trace_path,
            model_name=args.model,
            reasoning_effort=args.reasoning_effort,
            timeout_seconds=args.timeout_seconds,
            config_overrides=args.config_override,
        )
    else:
        codex_result = invoke_codex_element_analysis_cli(
            case_dir=case_dir,
            prompt=prompt_path.read_text(encoding="utf-8"),
            image_paths=analysis_images(case_dir),
            output_dir=output_dir,
            trace_path=trace_path,
            model_name=args.model,
            reasoning_effort=args.reasoning_effort,
            timeout_seconds=args.timeout_seconds,
            config_overrides=args.config_override,
        )
    analysis = read_json(output_path)
    validation = validate_analysis(analysis, request)
    write_json(output_dir / "validation.json", validation)
    elapsed_seconds = round(time.monotonic() - started_at, 3)
    summary = {
        "schema": "drawai.codex_element_analysis_status.v1",
        "status": "ok",
        "case_dir": str(case_dir),
        "output_path": str(output_path),
        "request_path": str(request_path),
        "candidate_table_path": str(candidate_table_path),
        "prompt_path": str(prompt_path),
        "trace_path": str(trace_path),
        "elapsed_seconds": elapsed_seconds,
        "validation": validation,
        "codex_result": codex_result,
        "ended_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    write_json(status_path, summary)
    return {
        "status": "ok",
        "case_dir": str(case_dir),
        "output_path": str(output_path),
        "elapsed_seconds": elapsed_seconds,
        "category_counts": validation["category_counts"],
    }


def build_request(case_dir: Path) -> dict[str, Any]:
    figure_path = case_dir / "inputs" / "figure.png"
    with Image.open(figure_path) as image:
        width, height = image.size

    box_ir = read_json(case_dir / "box_ir" / "box_ir.json")
    raw_box_ir = read_json(case_dir / "box_ir" / "box_ir.raw.json", default={})
    ocr = read_json(case_dir / "ocr" / "ocr_boxes.json", default={"ocr_text_boxes": []})
    initial_decisions = read_json(
        case_dir / "svg_to_ppt" / "assets" / "initial_asset_decisions.json",
        default={"decisions": []},
    )
    asset_decisions = read_json(
        case_dir / "svg_to_ppt" / "assets" / "asset_decisions.json",
        default={"decisions": []},
    )
    asset_policy = read_json(
        case_dir / "svg_to_ppt" / "assets" / "asset_policy_report.json",
        default={"assets": []},
    )
    asset_manifest = read_json(
        case_dir / "svg_to_ppt" / "assets" / "asset_manifest.json",
        default={"assets": []},
    )

    initial_by_box = records_by_key(initial_decisions.get("decisions"), "box_id")
    decision_by_box = records_by_key(asset_decisions.get("decisions"), "box_id")
    policy_by_asset = records_by_key(asset_policy.get("assets"), "asset_id")
    manifest_by_asset = records_by_key(asset_manifest.get("assets"), "asset_id")
    ocr_boxes = [dict(item) for item in ocr.get("ocr_text_boxes", []) if isinstance(item, Mapping)]
    candidates = []
    for index, box in enumerate(box_ir.get("boxes", []) or [], start=1):
        if not isinstance(box, Mapping):
            continue
        box_id = str(box.get("id") or f"B{index:03d}")
        decision = decision_by_box.get(box_id, {})
        initial = initial_by_box.get(box_id, {})
        asset_id = str(
            decision.get("asset_id")
            or initial.get("asset_id")
            or decision.get("recovered_asset_id")
            or ""
        )
        policy = policy_by_asset.get(asset_id, {})
        manifest = manifest_by_asset.get(asset_id, {})
        current_method = current_pipeline_method(decision, initial, policy, manifest)
        candidates.append(
            {
                "box_id": box_id,
                "type": box.get("type", "unknown"),
                "bbox": box.get("bbox"),
                "parent_ids": box.get("parent_ids", []),
                "child_ids": box.get("child_ids", []),
                "source_box_ids": box.get("source_box_ids", []),
                "source_prompt": box.get("source_prompt", ""),
                "score": box.get("score", None),
                "current_pipeline_method": current_method,
                "asset_id": asset_id,
                "asset_decision": compact_mapping(decision),
                "initial_asset_decision": compact_mapping(initial),
                "asset_policy": compact_mapping(policy),
                "asset_manifest": compact_mapping(manifest),
                "asset_hrefs": asset_hrefs(manifest),
                "overlapping_ocr": overlapping_ocr(box.get("bbox"), ocr_boxes),
            }
        )

    return {
        "schema": SCHEMA_REQUEST,
        "case_dir": str(case_dir),
        "canvas": {"width": width, "height": height},
        "source_image": "inputs/figure.png",
        "asset_plan_overlay": "reports/assemble_debug/assets/08_asset_plan.png",
        "files": {
            "final_box_ir": "box_ir/box_ir.json",
            "raw_box_ir": "box_ir/box_ir.raw.json",
            "ocr": "ocr/ocr_boxes.json",
            "initial_asset_decisions": "svg_to_ppt/assets/initial_asset_decisions.json",
            "asset_decisions": "svg_to_ppt/assets/asset_decisions.json",
            "asset_policy_report": "svg_to_ppt/assets/asset_policy_report.json",
            "asset_manifest": "svg_to_ppt/assets/asset_manifest.json (optional pre-analysis preview; usually absent before final materialization)",
        },
        "raw_sam_box_count": len(raw_box_ir.get("boxes", []) or []),
        "ocr_box_count": len(ocr_boxes),
        "candidate_count": len(candidates),
        "candidates": candidates,
        "classification_contract": {
            "categories": list(CATEGORIES),
            "refinement_actions": list(REFINEMENT_ACTIONS),
            "required_coverage_for_existing_candidates": True,
            "allow_added_candidates": True,
            "coverage_field": "source_candidate_ids",
            "output_path": str(Path("reports") / "element_analysis_codex" / "element_analysis.json"),
        },
    }


def write_candidate_table(path: Path, request: Mapping[str, Any]) -> None:
    columns = (
        "box_id",
        "type",
        "bbox",
        "current_pipeline_method",
        "asset_id",
        "render_policy",
        "background_policy",
        "active_variant",
        "policy_reasons",
        "ocr_text",
    )
    lines = ["\t".join(columns)]
    for candidate in request.get("candidates", []):
        if not isinstance(candidate, Mapping):
            continue
        policy = candidate.get("asset_policy") if isinstance(candidate.get("asset_policy"), Mapping) else {}
        manifest = candidate.get("asset_manifest") if isinstance(candidate.get("asset_manifest"), Mapping) else {}
        ocr_text = " | ".join(
            str(item.get("text", "")).replace("\t", " ").replace("\n", " ")
            for item in candidate.get("overlapping_ocr", [])
            if isinstance(item, Mapping) and item.get("text")
        )
        reasons = policy.get("reason_codes") if isinstance(policy.get("reason_codes"), list) else []
        values = (
            candidate.get("box_id", ""),
            candidate.get("type", ""),
            ",".join(str(item) for item in candidate.get("bbox", [])),
            candidate.get("current_pipeline_method", ""),
            candidate.get("asset_id", ""),
            policy.get("render_policy", ""),
            policy.get("background_policy", ""),
            manifest.get("active_variant", ""),
            "|".join(str(item) for item in reasons),
            ocr_text,
        )
        lines.append("\t".join(str(value).replace("\t", " ").replace("\n", " ") for value in values))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_prompt(case_dir: Path, request_path: Path, candidate_table_path: Path, output_path: Path) -> str:
    output_dir_rel = output_path.parent.relative_to(case_dir)
    assets_visualization_script = REPO_ROOT / "scripts" / "assets_visualization.py"
    return f"""DrawAI asset post-processing and source analysis task.

We are performing an image vectorization task: a bitmap image will eventually be transformed into an editable representation. The whole process has three parts:
- Asset parsing: divide the image into independent assets. Each asset may be text, an icon, table, frame, arrow, and so on.
- Asset post-processing: refine the pre-parsed assets.
- Editable reconstruction: combine assets and finish the final visual result.

Some assets should become editable forms, such as text, frames, arrows, and simple vector graphics. Some assets should instead be cropped from the original image and pasted back into their original positions. We have already preprocessed the image with layout analysis and OCR methods. You need to use the preprocessing result as evidence and execute the second stage, "asset post-processing", to refine the result. The detailed task instructions are below.

Workspace/case root:
{case_dir}

Inputs:
- Original image: inputs/figure.png
- Current DrawAI asset-plan overlay: reports/assemble_debug/assets/08_asset_plan.png
- Compact candidate table: {candidate_table_path.relative_to(case_dir)}
- Machine-readable request: {request_path.relative_to(case_dir)}
- The request lists final layout candidates, overlapping OCR text, current crop/native decisions, asset policy metrics, and any optional pre-existing asset hrefs. The final asset manifest is generated after this analysis, so do not assume local crop hrefs already exist.

You may read files under the case root, but this is a bounded analysis pass. Do not render SVG/PPT, do not spend time searching unrelated files, and do not print the full request JSON to the terminal. Start from the compact candidate table; use the full request JSON only for exact bbox/details when needed. Use the attached original image, the attached asset-plan overlay, and the request JSON as the factual sources. Do not use MCP tools, apps, web search, memories, skills, hooks, or multi-agent delegation.

Task 1: refine request.candidates into minimum independent assets.
Each output element should be the smallest independent visual part, such as one icon, image, frame, arrow, text line, chart mark, chart block, or diagram component.
- Split a candidate when one box contains multiple independent parts, for example several icons/images inside one block.
- Add a new element when an asset is visible in the original image but not covered by any current candidate.
- Adjust the bbox when the current position is wrong or misses part of a component, for example a complex image whose frame does not include all visible content.
- Preserve traceability. For an unchanged or adjusted element, set source_candidate_ids to the original candidate ID. For a split element, use a new stable ID such as B012_S01 and set source_candidate_ids to ["B012"]. For a newly added element, use a stable ID such as N001 and set source_candidate_ids to [].
- Bboxes must be visual extents in image pixels. For a straight line or divider, give at least 1 pixel of thickness so the bbox has positive width and height.
- Pay close attention to whether coordinates are correct and whether each bbox tightly contains the corresponding asset.

Task 2: repeat the following refinement loop until you believe the asset parsing quality is perfect, all elements are reasonable assets, and all bbox coordinates are accurate. Run at most 3 visualization/refinement iterations.
1. Write the current refined assets JSON for the iteration to:
   {output_dir_rel}/refine_iteration_<N>.json
   where <N> starts at 1 and increases by one each time. The iteration JSON should contain at least schema, case_dir, refinement_summary, refinement_actions, and elements with box_id, source_candidate_ids, refinement_action, bbox, type, visual_role, and reason.
2. Run assets_visualization for that iteration:
   python {assets_visualization_script} --image inputs/figure.png --json {output_dir_rel}/refine_iteration_<N>.json --output {output_dir_rel}/assets_visualization_iteration_<N>.png --summary-output {output_dir_rel}/assets_visualization_iteration_<N>.summary.json --color-mode action --label-mode id_type --title "DrawAI assets refinement iteration <N>"
3. Inspect the visualization output at:
   {output_dir_rel}/assets_visualization_iteration_<N>.png
   Use it to correct Task 1 results. You may add assets, remove assets, split assets, merge accidental duplicates, and adjust bbox coordinates. One iteration may change any number of assets.
4. Repeat steps 1-3 until the assets are perfect, or until you have completed 3 iterations.
5. Save the final refined asset list used for classification to:
   {output_dir_rel}/refined_assets_final.json

Task 3: classify every final refined output element into exactly one of these three categories:
- svg_self_draw: use editable SVG primitives/text/paths directly. Use this for text, arrows, boxes, lines, charts, simple geometric diagrams, and visually simple icons that can be faithfully redrawn.
- crop: use a precise source-image crop with its local background preserved. Use this for screenshots, photographs, dense texture, heatmaps, complex small raster icons, or visual details whose background is coupled with the object.
- crop_nobg: use a precise crop after background removal/transparent subject extraction. Use this when the foreground object is separable and should sit over reconstructed SVG background.

Important:
- Treat SAM/OCR/current asset plan as evidence, not truth. You may disagree with current_pipeline_method if the image supports it.
- Do not skip candidates. Every original request.candidates item must be represented by at least one output element through source_candidate_ids, or by an unchanged output element with the same box_id.
- New IDs are allowed only for split or added refined elements. Keep IDs short and stable.
- This task only classifies and explains; do not modify the main SVG/PPT outputs.
- If uncertain, choose the most faithful final-source strategy and mark confidence as low or medium.
- After Task 2 is complete, complete the Task 3 classification in one pass. Write the final JSON file first, then write the markdown note. Keep reasons concise.
- Do not run git commands, do not commit, and do not change repository code.

Write UTF-8 JSON to:
{output_path.relative_to(case_dir)}

The JSON file must have this shape:
{{
  "schema": "{SCHEMA_OUTPUT}",
  "case_dir": "{case_dir}",
  "source": "codex",
  "strategy_summary": "short paragraph",
  "refinement_summary": "short paragraph",
  "refinement_iterations": [
    {{"iteration": 1, "json_path": "{output_dir_rel}/refine_iteration_1.json", "visualization_path": "{output_dir_rel}/assets_visualization_iteration_1.png", "changes": "short summary"}}
  ],
  "categories": {{"svg_self_draw": 0, "crop": 0, "crop_nobg": 0}},
  "refinement_actions": {{"unchanged": 0, "adjusted": 0, "split": 0, "added": 0}},
  "elements": [
    {{
      "box_id": "B001",
      "source_candidate_ids": ["B001"],
      "refinement_action": "unchanged",
      "category": "svg_self_draw",
      "confidence": "high",
      "visual_role": "short label",
      "reason": "one or two sentences",
      "evidence": ["short evidence item"],
      "bbox": [0, 0, 10, 10],
      "type": "content_box",
      "current_pipeline_method": "svg_self_draw",
      "recommended_asset_source": "svg"
    }}
  ],
  "notes": []
}}

Also write a concise markdown audit note to:
reports/element_analysis_codex/analysis_notes.md

Keep the final chat response to one sentence. The JSON file is the source of truth.
"""


def invoke_codex_element_analysis_cli(
    *,
    case_dir: Path,
    prompt: str,
    image_paths: Sequence[Path],
    output_dir: Path,
    trace_path: Path,
    model_name: str,
    reasoning_effort: str,
    timeout_seconds: float,
    config_overrides: Sequence[str],
) -> dict[str, Any]:
    codex_bin = resolve_codex_executable()
    if codex_bin is None:
        raise RuntimeError(
            "codex executable was not found. Run `uv run drawai setup local`, or run this script through: "
            "uv run --with openai-codex --prerelease=allow python ..."
        )
    normalized_model = _normalize_codex_model_name(model_name)
    normalized_effort = _normalize_codex_reasoning_effort(reasoning_effort)
    output_dir.mkdir(parents=True, exist_ok=True)
    events_path = output_dir / "cli_events.jsonl"
    stderr_path = output_dir / "cli_stderr.txt"
    last_message_path = output_dir / "cli_last_message.txt"
    for path in (events_path, stderr_path, last_message_path):
        if path.exists():
            path.unlink()

    started_at = time.monotonic()
    with _isolated_codex_home(case_dir) as prepared_codex_home:
        command = [
            str(codex_bin),
            "exec",
            "--ignore-user-config",
            "--skip-git-repo-check",
            "--json",
            "-C",
            str(case_dir),
            "-s",
            "danger-full-access",
            "-o",
            str(last_message_path),
            *image_cli_args(image_paths),
            *cli_config_args(normalized_effort, config_overrides),
        ]
        if normalized_model is not None:
            command.extend(["-m", normalized_model])
        command.append("-")
        env = os.environ.copy()
        env.update(
            {
                "CODEX_HOME": str(prepared_codex_home.codex_home),
                "HOME": str(prepared_codex_home.codex_home),
            }
        )
        for key in ("DRAWAI_HOST_HOME", "DRAWAI_HOST_CODEX_HOME"):
            env.pop(key, None)
        with events_path.open("w", encoding="utf-8") as stdout_handle, stderr_path.open("w", encoding="utf-8") as stderr_handle:
            completed = subprocess.run(
                command,
                input=prompt,
                text=True,
                cwd=str(case_dir),
                env=env,
                stdout=stdout_handle,
                stderr=stderr_handle,
                timeout=timeout_seconds,
                check=False,
            )
        archive = _archive_codex_session_logs(
            prepared_codex_home.codex_home,
            output_dir / "codex_session_log",
            task_name="drawai.element_analysis.cli.v1",
        )

    duration_ms = int((time.monotonic() - started_at) * 1000)
    stderr_text = stderr_path.read_text(encoding="utf-8") if stderr_path.exists() else ""
    last_message = last_message_path.read_text(encoding="utf-8") if last_message_path.exists() else ""
    trace = {
        "schema": "drawai.codex_element_analysis_cli_trace.v1",
        "case_dir": str(case_dir),
        "command": redact_command(command),
        "returncode": completed.returncode,
        "model_name": normalized_model or "codex-default",
        "reasoning_effort": normalized_effort,
        "timeout_seconds": timeout_seconds,
        "duration_ms": duration_ms,
        "image_paths": [str(path) for path in image_paths],
        "events_path": str(events_path),
        "stderr_path": str(stderr_path),
        "last_message_path": str(last_message_path),
        "last_message_excerpt": last_message[:2000],
        "stderr_excerpt": stderr_text[:2000],
        "session_log_archive": archive,
    }
    with trace_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(trace, ensure_ascii=False, sort_keys=True) + "\n")
    if completed.returncode != 0:
        raise RuntimeError(
            f"codex exec failed with returncode={completed.returncode}. stderr tail: {stderr_text[-2000:]}"
        )
    return {
        "invoker": "cli",
        "model_name": normalized_model or "codex-default",
        "reasoning_effort": normalized_effort,
        "duration_ms": duration_ms,
        "events_path": str(events_path),
        "last_message_path": str(last_message_path),
        "session_log_archive_path": str(output_dir / "codex_session_log"),
    }


def image_cli_args(image_paths: Sequence[Path]) -> list[str]:
    args: list[str] = []
    for image_path in image_paths:
        args.extend(["-i", str(image_path)])
    return args


def cli_config_args(reasoning_effort: str, extra_overrides: Sequence[str]) -> list[str]:
    overrides = controlled_codex_config_overrides(
        [f'model_reasoning_effort="{reasoning_effort}"', *[str(item) for item in extra_overrides]]
    )
    args: list[str] = []
    for override in overrides:
        args.extend(["-c", override])
    return args


def redact_command(command: Sequence[str]) -> list[str]:
    redacted: list[str] = []
    skip_next = False
    for item in command:
        if skip_next:
            redacted.append(item)
            skip_next = False
            continue
        redacted.append(item)
        if item in {"-i", "-C", "-o", "-m", "-s", "-c"}:
            skip_next = True
    return redacted


def invoke_codex_element_analysis_sdk(
    *,
    case_dir: Path,
    prompt: str,
    image_paths: Sequence[Path],
    output_dir: Path,
    trace_path: Path,
    model_name: str,
    reasoning_effort: str,
    timeout_seconds: float,
    config_overrides: Sequence[str],
) -> dict[str, Any]:
    sdk = _load_openai_codex_sdk()
    normalized_model = _normalize_codex_model_name(model_name)
    normalized_effort = _normalize_codex_reasoning_effort(reasoning_effort)
    output_dir.mkdir(parents=True, exist_ok=True)
    session_log_archive_dir = output_dir / "codex_session_log"
    started_at = time.monotonic()
    result = None
    with _isolated_codex_home(case_dir) as prepared_codex_home:
        with sdk.Codex(
            sdk.CodexConfig(
                cwd=str(case_dir),
                config_overrides=controlled_codex_config_overrides(config_overrides),
                env=_codex_sdk_env(prepared_codex_home.codex_home),
            )
        ) as codex:
            thread = codex.thread_start(
                approval_mode=sdk.ApprovalMode.deny_all,
                config={"model_reasoning_effort": normalized_effort},
                cwd=str(case_dir),
                developer_instructions=(
                    "Internal DrawAI element source analysis thread.\n"
                    f"Workspace root: {case_dir}\n"
                    "You may use shell commands to inspect files and write outputs inside this workspace. "
                    "Do not use MCP tools, apps, web search, memories, skills, hooks, or multi-agent delegation."
                ),
                ephemeral=True,
                model=normalized_model,
                sandbox=sdk.Sandbox.full_access,
            )
            run_input = [
                sdk.TextInput(prompt),
                *(sdk.LocalImageInput(path=str(image_path)) for image_path in image_paths),
            ]
            result = _run_thread_with_timeout(
                thread,
                run_input,
                timeout_seconds=timeout_seconds,
                approval_mode=sdk.ApprovalMode.deny_all,
                cwd=str(case_dir),
                effort=normalized_effort,
                model=normalized_model,
                sandbox=sdk.Sandbox.full_access,
            )
        archive = _archive_codex_session_logs(
            prepared_codex_home.codex_home,
            session_log_archive_dir,
            task_name="drawai.element_analysis.v1",
            sdk_turn_result=result,
        )

    trace = {
        "schema": "drawai.codex_element_analysis_trace.v1",
        "case_dir": str(case_dir),
        "model_name": normalized_model or "codex-default",
        "reasoning_effort": normalized_effort,
        "timeout_seconds": timeout_seconds,
        "image_paths": [str(path) for path in image_paths],
        "duration_ms": int((time.monotonic() - started_at) * 1000),
        "result": {
            "id": getattr(result, "id", None),
            "status": _codex_sdk_jsonable(getattr(result, "status", None)),
            "duration_ms": getattr(result, "duration_ms", None),
            "usage": _codex_sdk_jsonable(getattr(result, "usage", None)),
            "final_response": getattr(result, "final_response", None),
        },
        "session_log_archive": archive,
    }
    with trace_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(trace, ensure_ascii=False, sort_keys=True) + "\n")
    return {
        "model_name": normalized_model or "codex-default",
        "reasoning_effort": normalized_effort,
        "duration_ms": trace["duration_ms"],
        "session_log_archive_path": str(session_log_archive_dir),
        "usage": trace["result"]["usage"],
    }


def analysis_images(case_dir: Path) -> list[Path]:
    candidates = [
        case_dir / "inputs" / "figure.png",
        case_dir / "reports" / "assemble_debug" / "assets" / "08_asset_plan.png",
    ]
    return [path for path in candidates if path.exists()]


def validate_analysis(analysis: Mapping[str, Any], request: Mapping[str, Any]) -> dict[str, Any]:
    if analysis.get("schema") != SCHEMA_OUTPUT:
        raise ValueError(f"Unexpected element analysis schema: {analysis.get('schema')!r}")
    elements = analysis.get("elements")
    if not isinstance(elements, list):
        raise ValueError("element_analysis.json must contain an elements list")
    expected = {str(item.get("box_id")) for item in request.get("candidates", []) if isinstance(item, Mapping)}
    seen_output_ids: list[str] = []
    covered_source_ids: set[str] = set()
    added_ids: list[str] = []
    action_counts: Counter[str] = Counter()
    for element in elements:
        if not isinstance(element, Mapping):
            raise ValueError("Every element analysis record must be an object")
        box_id = str(element.get("box_id") or "")
        category = str(element.get("category") or "")
        if not box_id:
            raise ValueError("Every element analysis record must contain box_id")
        if category not in CATEGORIES:
            raise ValueError(f"Unexpected category for {box_id}: {category}")
        bbox = normalize_bbox(element.get("bbox"), allow_line=True)
        if bbox is None:
            raise ValueError(f"Invalid bbox for {box_id}: {element.get('bbox')!r}")
        action = str(element.get("refinement_action") or "unchanged")
        if action not in REFINEMENT_ACTIONS:
            raise ValueError(f"Unexpected refinement_action for {box_id}: {action}")
        raw_source_ids = element.get("source_candidate_ids")
        if isinstance(raw_source_ids, list):
            source_ids = [str(item) for item in raw_source_ids if str(item)]
        else:
            source_ids = [box_id] if box_id in expected else []
        unexpected_source_ids = sorted(source_id for source_id in source_ids if source_id not in expected)
        if unexpected_source_ids:
            raise ValueError(f"Unexpected source_candidate_ids for {box_id}: {unexpected_source_ids[:20]}")
        if source_ids:
            covered_source_ids.update(source_ids)
        elif action != "added":
            raise ValueError(f"{box_id} has no source_candidate_ids but refinement_action is {action!r}")
        if box_id not in expected:
            added_ids.append(box_id)
        seen_output_ids.append(box_id)
        action_counts[action] += 1
    duplicates = sorted(box_id for box_id, count in Counter(seen_output_ids).items() if count > 1)
    missing = sorted(expected - covered_source_ids)
    if duplicates or missing:
        raise ValueError(f"Invalid element coverage. missing={missing[:20]} duplicates={duplicates[:20]}")
    category_counts = dict(Counter(str(item.get("category")) for item in elements))
    return {
        "schema": "drawai.codex_element_analysis_validation.v1",
        "candidate_count": len(expected),
        "element_count": len(elements),
        "added_element_count": len(added_ids),
        "category_counts": {category: int(category_counts.get(category, 0)) for category in CATEGORIES},
        "refinement_action_counts": {action: int(action_counts.get(action, 0)) for action in REFINEMENT_ACTIONS},
    }


def current_pipeline_method(
    decision: Mapping[str, Any],
    initial: Mapping[str, Any],
    policy: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> str:
    if decision.get("decision") != "crop_asset":
        return "svg_self_draw"
    if (
        manifest.get("active_variant") == "without_background"
        or manifest.get("nobg_svg_href")
        or policy.get("background_policy") in {"transparent_subject", "split_backplate"}
    ):
        return "crop_nobg"
    if manifest.get("restore_strategy") == "component_assets" or manifest.get("insertable_components"):
        return "crop"
    return "crop"


def overlapping_ocr(bbox: Any, ocr_boxes: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    target = normalize_bbox(bbox)
    if target is None:
        return []
    hits = []
    for box in ocr_boxes:
        other = normalize_bbox(box.get("bbox"))
        if other is None:
            continue
        overlap = intersection_area(target, other)
        if overlap <= 0:
            continue
        other_area = area(other)
        if other_area <= 0 or overlap / other_area < 0.2:
            continue
        hits.append(
            {
                "id": box.get("id", ""),
                "text": box.get("text", ""),
                "confidence": box.get("confidence", None),
                "bbox": box.get("bbox"),
            }
        )
    return hits[:12]


def asset_hrefs(manifest: Mapping[str, Any]) -> dict[str, str]:
    keys = (
        "svg_href",
        "source_svg_href",
        "nobg_svg_href",
        "source_png_href",
        "nobg_png_href",
        "href",
    )
    return {key: str(manifest.get(key)) for key in keys if manifest.get(key)}


def compact_mapping(record: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        return {}
    keep = (
        "asset_id",
        "box_id",
        "decision",
        "role",
        "render_policy",
        "background_policy",
        "split_policy",
        "confidence",
        "reason_codes",
        "active_variant",
        "restore_strategy",
        "should_run_rmbg",
        "bbox",
        "current_label",
        "svg_href",
        "source_svg_href",
        "nobg_svg_href",
    )
    result = {key: record[key] for key in keep if key in record}
    metrics = record.get("metrics")
    if isinstance(metrics, Mapping):
        result["metrics_summary"] = {
            key: metrics[key]
            for key in (
                "crop_width",
                "crop_height",
                "foreground_ratio",
                "edge_density",
                "thin_line_score",
                "color_complexity",
                "texture_score",
                "simple_geometry_score",
                "connected_component_count",
                "foreground_touches_sides",
            )
            if key in metrics
        }
    return result


def records_by_key(records: Any, key: str) -> dict[str, dict[str, Any]]:
    if not isinstance(records, list):
        return {}
    result = {}
    for record in records:
        if isinstance(record, Mapping) and isinstance(record.get(key), str):
            result[str(record[key])] = dict(record)
    return result


def normalize_bbox(raw: Any, *, allow_line: bool = False) -> tuple[float, float, float, float] | None:
    if not isinstance(raw, (list, tuple)) or len(raw) != 4:
        return None
    x1, y1, x2, y2 = [float(item) for item in raw]
    left, right = sorted((x1, x2))
    top, bottom = sorted((y1, y2))
    if allow_line:
        if right == left:
            left -= 0.5
            right += 0.5
        if bottom == top:
            top -= 0.5
            bottom += 0.5
    if right <= left or bottom <= top:
        return None
    return left, top, right, bottom


def intersection_area(left: tuple[float, float, float, float], right: tuple[float, float, float, float]) -> float:
    return max(0.0, min(left[2], right[2]) - max(left[0], right[0])) * max(0.0, min(left[3], right[3]) - max(left[1], right[1]))


def area(bbox: tuple[float, float, float, float]) -> float:
    return max(0.0, bbox[2] - bbox[0]) * max(0.0, bbox[3] - bbox[1])


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
