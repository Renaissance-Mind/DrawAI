#!/usr/bin/env python3
"""Run isolated Codex Python SDK rubric evaluation tasks for DrawAI-Bench."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Mapping
from zoneinfo import ZoneInfo

from drawai_evaluation.rubric_evidence import (
    RubricEvidenceWorkspace,
    prepare_rubric_evidence_workspace,
    publish_validated_rubric_output,
)

MODEL_NAME = "gpt-5.6-sol"
EXECUTION_ENGINE = "codex-python-sdk"
RUBRIC_SCHEMA = "drawai_eval_rubric_batch.v1"
USAGE_LIMIT_EXIT_CODE = 75
LOCAL_TIMEZONE = ZoneInfo("Asia/Shanghai")

GROUP_CRITERIA: dict[str, dict[str, str]] = {
    "global": {
        "overall_readability": (
            "Compare the complete reference and rendered candidate. Is the whole result readable "
            "and coherent, with important content legible?"
        ),
        "layout_skeleton": (
            "Are the major regions, flow, alignment, proportions, and overall composition skeleton preserved?"
        ),
        "visual_hierarchy": (
            "Are emphasis, contrast, visual hierarchy, and the absence of distracting artifacts preserved?"
        ),
    },
    "text": {
        "position_lines": (
            "For this GT text element, is the text in the correct region with equivalent line grouping and line breaks?"
        ),
        "alignment_spacing": (
            "Is its alignment and spacing relative to its box and neighboring elements preserved?"
        ),
        "overflow_occlusion": (
            "Is it visible without overflow, clipping, collision, or occlusion?"
        ),
        "color_emphasis": "Are text color and emphasis relationships visually faithful?",
        "font_appearance": (
            "Are approximate font-family appearance, size, weight, and styling faithful?"
        ),
        "style_consistency": (
            "Is its style consistent with other text elements of the same visual class?"
        ),
    },
    "shape": {
        "existence_coverage": "Is the GT shape visibly reconstructed in the correct area?",
        "visual_attributes": (
            "Are fill, stroke, corner style, opacity, and overall appearance faithful?"
        ),
        "neighbor_relation": (
            "Are its spatial and containment relationships with neighboring elements preserved?"
        ),
        "object_independence": (
            "Does candidate.svg provide an independently editable SVG object or coherent group for this shape, "
            "rather than baking it into unrelated content?"
        ),
        "box_placement": (
            "Does the editable object occupy the correct GT bbox with reasonable placement and size?"
        ),
        "conflict_diagnosis": (
            "Is the object cleanly separated without incorrect merges, splits, duplicate ownership, or object conflicts? "
            "Answer yes when there is no material conflict."
        ),
    },
    "connector": {
        "path_presence": "Is the GT connector visibly present with the intended route?",
        "endpoint_direction": (
            "Do its endpoints, attachment regions, and direction or arrow orientation match?"
        ),
        "line_style_noise": (
            "Are stroke style, dash, width, arrowhead, and routing faithful without extra line noise? "
            "Answer yes when the line is faithful and clean."
        ),
        "independent_path": (
            "Is it represented by an independent editable line, path, polyline, or coherent connector group in candidate.svg?"
        ),
        "endpoint_control": "Can its endpoints and route be edited coherently as connector geometry?",
        "mis_merge_check": (
            "Is it not incorrectly merged into a shape, text, raster image, or unrelated connector? "
            "Answer yes when it is correctly separate."
        ),
    },
    "formula": {
        "symbol_retention": (
            "For this GT formula element, are its visible symbols, operators, labels, and key notation retained?"
        ),
        "structure_relation": (
            "Are superscripts, subscripts, fractions, grouping, baselines, and symbol relationships reconstructed coherently?"
        ),
        "position_readability": (
            "Is the formula in the correct region, legible, and free from clipping, overlap, or destructive spacing changes?"
        ),
    },
    "table": {
        "grid_structure": (
            "For this GT table element, are the visible rows, columns, dividers, merged regions, and outer structure reconstructed?"
        ),
        "content_ownership": (
            "Do the visible labels and values belong to the correct cells or table regions without leaking into neighbors?"
        ),
        "readability_alignment": (
            "Is the table readable, with faithful cell alignment, spacing, ordering, and no material clipping or overlap?"
        ),
        "table_region_independence": (
            "Does candidate.svg provide an independently locatable editable group, grid, line, rect, or text structure "
            "for this table region, rather than baking it into an unrelated full-page raster image?"
        ),
        "editable_grid": (
            "Does candidate.svg provide independently editable grid geometry or a coherent editable table group?"
        ),
        "text_ownership": (
            "Are table text objects independently editable and associated with the correct table region or cell?"
        ),
    },
}

ANSWER_SCORES = {"yes": 1.0, "partial": 0.5, "no": 0.0, "N/A": None}
FORBIDDEN_COMMAND_PATHS = (
    "/.codex/memories",
    "/.codex/sessions",
    "/nodes/",
    "/prompts/",
    "/traces/",
)
DEFAULT_CODEX_BIN = Path(shutil.which("codex") or "codex")


def criteria_for_group(group: str) -> tuple[str, ...]:
    try:
        return tuple(GROUP_CRITERIA[group])
    except KeyError as error:
        raise ValueError(f"unsupported rubric group: {group}") from error


def gt_element_ids(gt_spec: dict[str, Any], group: str) -> list[str]:
    return [
        str(element["id"])
        for element in gt_spec.get("elements", [])
        if element.get("kind") == group and element.get("id")
    ]


def build_task_prompt(task: dict[str, Any]) -> str:
    group = str(task["group"])
    criteria = GROUP_CRITERIA[group]
    criteria_text = "\n".join(f"- {name}: {question}" for name, question in criteria.items())
    if group == "global":
        scope = "Judge the whole page once."
        output_contract = """The JSON must contain an aggregate object with exactly the three criteria above. Each value must contain answer, score, and a concise evidence-based reason."""
    else:
        gt_count = int(task["gt_count"])
        scope = (
            f"GT contains {gt_count} {group} elements. Evaluate every one of them, not a sample. "
            f"Parse all matching kind={group} elements from the GT PageSpec."
        )
        output_contract = (
            f"The top-level gt_count field must be the integer {gt_count}. The top-level evaluated_ids array must "
            f"contain exactly {gt_count} unique GT ids, and the top-level per_element array must contain exactly "
            f'{gt_count} rows. Each row must be {{"gt_id": <GT id>, "scores": {{<criterion>: '
            '{"answer": "yes|partial|no|N/A", "score": 1.0|0.5|0.0|null}}}}}. Every row must '
            "contain all six criteria above. The top-level aggregate object must contain one key per criterion, and "
            "each criterion value must contain score, valid_count, yes_count, partial_count, no_count, na_count, and "
            "a concise reason. Recompute aggregate values from per_element before writing the file. Do not omit "
            "gt_count even though it is already stated in this prompt."
        )
        output_contract = output_contract.replace(
            "all six criteria above", f"all {len(criteria)} criteria above"
        )

    return f"""You are a rubric evaluator, not a coding or generation agent. Evaluate exactly one DrawAI-Bench candidate.

PRIVACY AND EVIDENCE CONSTRAINTS
- Do not read or use Memory.
- Do not browse the web.
- You may read only these four evaluation inputs:
  1. GT PageSpec: {task["gt_page_spec"]}
  2. Reference image: {task["reference_image"]}
  3. Final candidate SVG: {task["candidate_svg"]}
  4. Rendered candidate PNG: {task["rendered_png"]}
- Do not inspect nodes/, prompts, traces, agent results, notes, manifests, source assets, or any other intermediate or candidate directory.
- Candidate visual evidence is the rendered PNG. Candidate editability evidence is candidate.svg only.
- SVG ids may help locate objects but are never sufficient evidence by themselves.
- Temporary crops under /tmp are allowed. Do not persist them.
- Write only the assigned output JSON: {task["output_json"]}

TASK
Rubric group: {group}
{scope}

SCORING
- yes = 1.0: fully or substantially correct
- partial = 0.5: recognizable and mostly correct but materially imperfect
- no = 0.0: missing, wrong, or unusable
- N/A = null: genuinely inapplicable only
- Do not invent a free-form overall score.

CRITERIA
{criteria_text}

OUTPUT CONTRACT
- schema: {RUBRIC_SCHEMA}
- task_id: {task["task_id"]}
- bench_id: {task["bench_id"]}
- dag: {task["dag"]}
- lane: {task["lane"]}
- group: {group}
- model: {MODEL_NAME}
- execution_engine: {EXECUTION_ENGINE}
- notes: an array
{output_contract}

Inspect both images and the SVG carefully. Write valid UTF-8 JSON with no Markdown fences to {task["output_json"]}, validate it by loading it with Python json, then respond only with the output path and one-line completion status.
"""


def validate_rubric_payload(
    task: dict[str, Any], payload: dict[str, Any], gt_spec: dict[str, Any]
) -> dict[str, Any]:
    expected_metadata = {
        "schema": RUBRIC_SCHEMA,
        "task_id": str(task["task_id"]),
        "bench_id": str(task["bench_id"]),
        "dag": str(task["dag"]),
        "lane": str(task["lane"]),
        "group": str(task["group"]),
        "model": MODEL_NAME,
        "execution_engine": EXECUTION_ENGINE,
    }
    for key, expected in expected_metadata.items():
        if payload.get(key) != expected:
            raise ValueError(f"{key} must be {expected!r}, got {payload.get(key)!r}")
    if not isinstance(payload.get("notes"), list):
        raise ValueError("notes must be an array")

    group = expected_metadata["group"]
    criteria = criteria_for_group(group)
    aggregate = payload.get("aggregate")
    if not isinstance(aggregate, dict) or set(aggregate) != set(criteria):
        raise ValueError(f"aggregate criteria must be exactly {criteria}")

    if group == "global":
        for criterion in criteria:
            _validate_answer_score(aggregate[criterion], f"aggregate.{criterion}")
            if not str(aggregate[criterion].get("reason") or "").strip():
                raise ValueError(f"aggregate.{criterion}.reason must be non-empty")
        return payload

    expected_ids = gt_element_ids(gt_spec, group)
    if len(expected_ids) != int(task["gt_count"]):
        raise ValueError(
            f"manifest gt_count={task['gt_count']} does not match GT {group} count={len(expected_ids)}"
        )
    if payload.get("gt_count") != len(expected_ids):
        raise ValueError(f"gt_count must be {len(expected_ids)}")
    evaluated_ids = payload.get("evaluated_ids")
    if not isinstance(evaluated_ids, list) or len(evaluated_ids) != len(set(evaluated_ids)):
        raise ValueError("evaluated_ids must be a unique array")
    if set(evaluated_ids) != set(expected_ids) or len(evaluated_ids) != len(expected_ids):
        raise ValueError("evaluated_ids must exactly cover all GT ids")

    per_element = payload.get("per_element")
    if not isinstance(per_element, list) or len(per_element) != len(expected_ids):
        raise ValueError(f"per_element must contain exactly {len(expected_ids)} rows")
    rows_by_id: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(per_element):
        if not isinstance(row, dict):
            raise ValueError(f"per_element[{index}] must be an object")
        element_id = str(row.get("gt_id") or "")
        if not element_id or element_id in rows_by_id:
            raise ValueError(f"per_element contains missing or duplicate gt_id: {element_id!r}")
        if element_id not in expected_ids:
            raise ValueError(f"per_element contains unknown gt_id: {element_id}")
        scores = row.get("scores")
        if not isinstance(scores, dict) or set(scores) != set(criteria):
            raise ValueError(f"per_element[{element_id}] criteria must be exactly {criteria}")
        for criterion in criteria:
            _validate_answer_score(scores[criterion], f"per_element.{element_id}.{criterion}")
        rows_by_id[element_id] = row
    if set(rows_by_id) != set(expected_ids):
        raise ValueError("per_element must exactly cover all GT ids")

    for criterion in criteria:
        _validate_aggregate(criterion, aggregate[criterion], per_element)
    return payload


def _validate_answer_score(value: Any, location: str) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"{location} must be an object")
    answer = value.get("answer")
    if answer not in ANSWER_SCORES:
        raise ValueError(f"{location}.answer is invalid: {answer!r}")
    expected = ANSWER_SCORES[answer]
    actual = value.get("score")
    if expected is None:
        if actual is not None:
            raise ValueError(f"{location}.score must be null for N/A")
    elif not isinstance(actual, int | float) or not math.isclose(float(actual), expected):
        raise ValueError(f"{location}.score must be {expected} for {answer}")


def _validate_aggregate(criterion: str, aggregate: Any, per_element: list[dict[str, Any]]) -> None:
    if not isinstance(aggregate, dict):
        raise ValueError(f"aggregate.{criterion} must be an object")
    counts = {answer: 0 for answer in ANSWER_SCORES}
    valid_scores: list[float] = []
    for row in per_element:
        score = row["scores"][criterion]
        counts[score["answer"]] += 1
        if score["score"] is not None:
            valid_scores.append(float(score["score"]))
    expected_fields = {
        "valid_count": len(valid_scores),
        "yes_count": counts["yes"],
        "partial_count": counts["partial"],
        "no_count": counts["no"],
        "na_count": counts["N/A"],
    }
    for field, expected in expected_fields.items():
        if aggregate.get(field) != expected:
            raise ValueError(f"aggregate.{criterion}.{field} must be {expected}")
    expected_score = sum(valid_scores) / len(valid_scores) if valid_scores else None
    actual_score = aggregate.get("score")
    if expected_score is None:
        if actual_score is not None:
            raise ValueError(f"aggregate.{criterion}.score must be null")
    elif not isinstance(actual_score, int | float) or not math.isclose(
        float(actual_score), expected_score, rel_tol=0.0, abs_tol=5e-5
    ):
        raise ValueError(f"aggregate.{criterion}.score must be {expected_score}")
    if not str(aggregate.get("reason") or "").strip():
        raise ValueError(f"aggregate.{criterion}.reason must be non-empty")


def prepare_isolated_home(attempt_dir: Path, host_codex_home: Path) -> dict[str, str]:
    auth_source = host_codex_home.expanduser() / "auth.json"
    if not auth_source.is_file():
        raise FileNotFoundError(f"missing Codex auth: {auth_source}")
    home = attempt_dir / "_temp_home"
    codex_home = home / ".codex"
    if home.exists():
        shutil.rmtree(home)
    codex_home.mkdir(parents=True)
    shutil.copy2(auth_source, codex_home / "auth.json")
    return {"home": str(home), "codex_home": str(codex_home)}


def create_attempt_dir(candidate_eval_dir: Path, group: str) -> Path:
    group_dir = candidate_eval_dir / "sdk_runs" / group
    group_dir.mkdir(parents=True, exist_ok=True)
    existing = [
        int(path.name.split("_", 1)[1])
        for path in group_dir.glob("attempt_[0-9][0-9][0-9]")
        if path.is_dir()
    ]
    attempt_dir = group_dir / f"attempt_{max(existing, default=0) + 1:03d}"
    attempt_dir.mkdir()
    return attempt_dir


def _parse_usage_limit_retry_at(text: str) -> str | None:
    match = re.search(
        r"try again at\s+([A-Za-z]{3}\s+\d{1,2}(?:st|nd|rd|th)?,\s+"
        r"\d{4}\s+\d{1,2}:\d{2}\s+(?:AM|PM))",
        text,
        flags=re.IGNORECASE,
    )
    if match is None:
        return None
    normalized = re.sub(r"(\d{1,2})(?:st|nd|rd|th)", r"\1", match.group(1))
    retry_at = dt.datetime.strptime(normalized, "%b %d, %Y %I:%M %p")
    return retry_at.replace(tzinfo=LOCAL_TIMEZONE).isoformat()


def inspect_usage_limit_failure(attempt_dir: Path) -> dict[str, Any]:
    texts: list[str] = []
    result_path = attempt_dir / "sdk_result.json"
    if result_path.is_file():
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        texts.extend(str(payload.get(key) or "") for key in ("error", "traceback"))
    stderr_path = attempt_dir / "worker.stderr.log"
    if stderr_path.is_file():
        texts.append(stderr_path.read_text(encoding="utf-8", errors="replace"))
    combined = "\n".join(texts)
    limited = "you've hit your usage limit" in combined.casefold()
    return {
        "limited": limited,
        "retry_at": _parse_usage_limit_retry_at(combined) if limited else None,
        "error": combined.strip() if limited else None,
    }


def assert_no_forbidden_command_access(events_path: Path) -> dict[str, Any]:
    command_count = 0
    bad_hits: list[dict[str, Any]] = []
    all_forbidden_text_hits = 0
    for line_number, line in enumerate(
        events_path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1
    ):
        record = json.loads(line)
        text = str(record.get("repr") or "")
        if any(path in text for path in FORBIDDEN_COMMAND_PATHS):
            all_forbidden_text_hits += 1
        payload = record.get("payload")
        item = payload.get("item") if isinstance(payload, dict) else None
        command = item.get("command") if isinstance(item, dict) else None
        if not command and "CommandExecutionThreadItem(command=" in text:
            command = text.split("CommandExecutionThreadItem(command=", 1)[1].split(")", 1)[0]
        if not command:
            continue
        command_count += 1
        command_text = str(command)
        hits = [path for path in FORBIDDEN_COMMAND_PATHS if path in command_text]
        if hits:
            bad_hits.append({"line": line_number, "paths": hits, "excerpt": command_text[:2000]})
    if bad_hits:
        raise RuntimeError(f"forbidden paths appeared in executed commands: {bad_hits[:3]}")
    return {
        "command_count": command_count,
        "bad_command_hits": 0,
        "all_forbidden_text_hits": all_forbidden_text_hits,
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def task_input_sha256(task: Mapping[str, Any]) -> dict[str, str]:
    return {
        key: sha256_file(Path(str(task[key])))
        for key in ("gt_page_spec", "reference_image", "candidate_svg", "rendered_png")
    }


def validate_task_inputs(task: dict[str, Any]) -> None:
    for key in ("gt_page_spec", "reference_image", "candidate_svg", "rendered_png"):
        path = Path(str(task[key])).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"missing {key}: {path}")
    if str(task.get("group")) not in GROUP_CRITERIA:
        raise ValueError(f"unsupported rubric group: {task.get('group')!r}")


def prepare_sdk_task(task: dict[str, Any], runtime_dir: Path) -> RubricEvidenceWorkspace:
    workspace = prepare_rubric_evidence_workspace(task, runtime_dir)
    (runtime_dir / "task.json").write_text(
        json.dumps(workspace.task, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return workspace


def finalize_sdk_task_result(
    task: dict[str, Any],
    workspace: RubricEvidenceWorkspace,
    record_dir: Path,
) -> dict[str, Any]:
    runtime_task = workspace.task
    runtime_dir = Path(str(runtime_task["output_json"])).parent
    local_output = Path(str(runtime_task["output_json"]))
    child_result = json.loads((runtime_dir / "sdk_result.json").read_text(encoding="utf-8"))
    required = {
        "schema": "drawbench.codex_sdk_rubric.result.v1",
        "task_id": str(task["task_id"]),
        "model": MODEL_NAME,
        "execution_engine": EXECUTION_ENGINE,
        "turn_completed": True,
        "turn_status": "completed",
        "validation_passed": True,
        "output_json": str(local_output),
        "output_sha256": sha256_file(local_output),
        "input_sha256": task_input_sha256(runtime_task),
    }
    for key, expected in required.items():
        if child_result.get(key) != expected:
            raise ValueError(
                f"isolated SDK result has invalid {key}: "
                f"expected={expected!r} actual={child_result.get(key)!r}"
            )

    gt_spec = json.loads(Path(str(task["gt_page_spec"])).read_text(encoding="utf-8"))
    payload = json.loads(local_output.read_text(encoding="utf-8"))
    validate_rubric_payload(task, payload, gt_spec)
    publish_validated_rubric_output(local_output, workspace.published_output)

    record_dir.mkdir(parents=True, exist_ok=True)
    for filename in (
        "task.json",
        "sdk_setup.json",
        "events.jsonl",
        "final_response.txt",
    ):
        source = runtime_dir / filename
        if source.is_file():
            shutil.copy2(source, record_dir / filename)

    result = dict(child_result)
    result.update(
        {
            "output_json": str(workspace.published_output),
            "output_sha256": sha256_file(workspace.published_output),
            "input_sha256": task_input_sha256(task),
            "events_path": str(record_dir / "events.jsonl"),
            "final_response_path": str(record_dir / "final_response.txt"),
            "evidence_isolation": {
                "sandbox": "workspace_write",
                "runtime_root": "temporary",
                "published_after_validation": True,
            },
        }
    )
    (record_dir / "sdk_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return result


def _candidate_eval_dir(task: dict[str, Any]) -> Path:
    output = Path(str(task["output_json"]))
    if output.parent.name != "rubric":
        raise ValueError(f"output_json must be inside a rubric directory: {output}")
    return output.parent.parent


def inspect_task_completion(task: dict[str, Any]) -> dict[str, Any]:
    output = Path(str(task["output_json"]))
    if not output.is_file():
        return {"complete": False, "reason": "output JSON is missing"}
    try:
        gt_spec = json.loads(Path(str(task["gt_page_spec"])).read_text(encoding="utf-8"))
        payload = json.loads(output.read_text(encoding="utf-8"))
        validate_rubric_payload(task, payload, gt_spec)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        return {"complete": False, "reason": f"output JSON is invalid: {error}"}

    expected_hash = sha256_file(output)
    try:
        expected_inputs = task_input_sha256(task)
    except FileNotFoundError as error:
        return {
            "complete": False,
            "reason": f"task input is unavailable: {error}",
        }
    result_paths = sorted(
        (_candidate_eval_dir(task) / "sdk_runs" / str(task["group"])).glob(
            "attempt_[0-9][0-9][0-9]/sdk_result.json"
        ),
        reverse=True,
    )
    for result_path in result_paths:
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if (
            result.get("schema") == "drawbench.codex_sdk_rubric.result.v1"
            and result.get("task_id") == str(task["task_id"])
            and result.get("model") == MODEL_NAME
            and result.get("execution_engine") == EXECUTION_ENGINE
            and result.get("turn_completed") is True
            and result.get("turn_status") == "completed"
            and result.get("validation_passed") is True
            and result.get("output_json") == str(output)
            and result.get("output_sha256") == expected_hash
            and result.get("input_sha256") == expected_inputs
        ):
            return {
                "complete": True,
                "reason": "validated output is bound to a completed SDK result",
                "result_path": str(result_path),
                "output_sha256": expected_hash,
            }
    return {
        "complete": False,
        "reason": "no completed SDK result matches the validated output hash",
    }


def select_manifest_tasks(
    tasks: list[dict[str, Any]], task_ids: set[str], *, resume: bool
) -> list[dict[str, Any]]:
    known_ids = {str(task["task_id"]) for task in tasks}
    unknown_ids = task_ids - known_ids
    if unknown_ids:
        raise ValueError(f"unknown task ids: {sorted(unknown_ids)}")
    selected = [task for task in tasks if not task_ids or str(task["task_id"]) in task_ids]
    if resume:
        selected = [task for task in selected if not inspect_task_completion(task)["complete"]]
    return selected


def archive_unverified_outputs(
    tasks: list[dict[str, Any]], evaluation_root: Path
) -> dict[str, Any]:
    timestamp = time.strftime("%Y%m%dT%H%M%S")
    archive_root = evaluation_root / "_discarded_subagent_outputs" / timestamp
    archived: list[dict[str, str]] = []
    for task in tasks:
        output = Path(str(task["output_json"]))
        if not output.is_file() or inspect_task_completion(task)["complete"]:
            continue
        relative = output.relative_to(evaluation_root)
        destination = archive_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(output), destination)
        archived.append(
            {
                "task_id": str(task["task_id"]),
                "source": str(output),
                "destination": str(destination),
            }
        )
    report = {
        "schema": "drawbench.discarded_rubric_outputs.v1",
        "created_at": timestamp,
        "archive_root": str(archive_root),
        "archived_count": len(archived),
        "archived": archived,
    }
    if archived:
        archive_root.mkdir(parents=True, exist_ok=True)
        (archive_root / "archive_manifest.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return report


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str | int | float | bool):
        return enum_value
    if hasattr(value, "model_dump"):
        return value.model_dump(by_alias=True, exclude_none=True, mode="json")
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "__dict__"):
        return {
            str(key): _jsonable(item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }
    return repr(value)


def _final_assistant_response(items: list[Any]) -> str:
    fallback = ""
    for item in reversed(items):
        root = getattr(item, "root", item)
        if root.__class__.__name__ != "AgentMessageThreadItem":
            continue
        text = str(getattr(root, "text", "") or "")
        phase = getattr(getattr(root, "phase", None), "value", getattr(root, "phase", None))
        if phase == "final_answer":
            return text
        if phase is None and not fallback:
            fallback = text
    return fallback


def _collect_turn_with_event_log(turn: Any, events_path: Path) -> dict[str, Any]:
    items: list[Any] = []
    usage = None
    completed_turn = None
    events_path.parent.mkdir(parents=True, exist_ok=True)
    stream = turn.stream()
    try:
        with events_path.open("w", encoding="utf-8") as handle:
            for event in stream:
                handle.write(
                    json.dumps(
                        {
                            "method": getattr(event, "method", None),
                            "payload": _jsonable(getattr(event, "payload", None)),
                            "repr": repr(event),
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                    + "\n"
                )
                handle.flush()
                payload = getattr(event, "payload", None)
                payload_name = payload.__class__.__name__ if payload is not None else ""
                if (
                    payload_name == "ItemCompletedNotification"
                    and getattr(payload, "turn_id", None) == turn.id
                ):
                    items.append(payload.item)
                elif (
                    payload_name == "ThreadTokenUsageUpdatedNotification"
                    and getattr(payload, "turn_id", None) == turn.id
                ):
                    usage = payload.token_usage
                elif payload_name == "TurnCompletedNotification":
                    candidate = getattr(payload, "turn", None)
                    if getattr(candidate, "id", None) == turn.id:
                        completed_turn = candidate
    finally:
        stream.close()
    if completed_turn is None:
        raise RuntimeError("Codex SDK turn completed event was not received")
    status = getattr(
        getattr(completed_turn, "status", None), "value", getattr(completed_turn, "status", None)
    )
    error = getattr(completed_turn, "error", None)
    if status == "failed":
        message = getattr(error, "message", None) or json.dumps(
            _jsonable(error), ensure_ascii=False
        )
        raise RuntimeError(f"Codex SDK turn failed: {message}")
    return {
        "id": turn.id,
        "status": status,
        "error": _jsonable(error),
        "started_at": getattr(completed_turn, "started_at", None),
        "completed_at": getattr(completed_turn, "completed_at", None),
        "duration_ms": getattr(completed_turn, "duration_ms", None),
        "final_response": _final_assistant_response(items),
        "usage": _jsonable(usage),
    }


@contextmanager
def _turn_deadline(timeout_seconds: float):
    if timeout_seconds <= 0:
        yield
        return

    def raise_timeout(_signum: int, _frame: Any) -> None:
        raise TimeoutError(f"Codex SDK turn exceeded timeout_seconds={timeout_seconds}")

    previous_handler = signal.signal(signal.SIGALRM, raise_timeout)
    signal.setitimer(signal.ITIMER_REAL, timeout_seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)


def _developer_instructions() -> str:
    return """You are an isolated DrawAI-Bench rubric evaluator. Follow the task prompt exactly.
Do not use Memory, web search, apps, project instructions, skills, subagents, or prior sessions.
Read only the four absolute input paths named in the task. Use rendered PNG for visual evidence and final SVG for editability evidence.
Do not inspect sibling directories or intermediate generation artifacts. Evaluate every requested GT element and write only the assigned JSON.
Use shell or Python only when needed to inspect the named files or temporary crops under /tmp. Never infer correctness from SVG ids alone."""


def run_sdk_worker(
    task: dict[str, Any],
    attempt_dir: Path,
    *,
    host_codex_home: Path,
    codex_bin: Path,
    reasoning_effort: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    validate_task_inputs(task)
    if not codex_bin.is_file():
        raise FileNotFoundError(f"missing Codex CLI binary: {codex_bin}")
    if MODEL_NAME != "gpt-5.6-sol":
        raise RuntimeError("formal rubric evaluation requires gpt-5.6-sol")
    output = Path(str(task["output_json"]))
    output.parent.mkdir(parents=True, exist_ok=True)
    attempt_dir.mkdir(parents=True, exist_ok=True)
    (attempt_dir / "task.json").write_text(
        json.dumps(task, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    prepared = prepare_isolated_home(attempt_dir, host_codex_home)
    setup = {
        "schema": "drawbench.codex_sdk_rubric.setup.v1",
        "task_id": str(task["task_id"]),
        "model": MODEL_NAME,
        "reasoning_effort": reasoning_effort,
        "execution_engine": EXECUTION_ENGINE,
        "codex_bin": str(codex_bin),
        "ephemeral": True,
        "approval_mode": "deny_all",
        "sandbox": "workspace_write",
        "auth_copied": True,
        "memory_copied": False,
    }
    (attempt_dir / "sdk_setup.json").write_text(
        json.dumps(setup, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    events_path = attempt_dir / "events.jsonl"
    final_response_path = attempt_dir / "final_response.txt"
    started_at = time.monotonic()

    from openai_codex import (
        ApprovalMode,
        Codex,
        CodexConfig,
        LocalImageInput,
        Sandbox,
        TextInput,
    )

    from drawai_evaluation.codex_config import controlled_codex_config_overrides

    env = {
        "HOME": prepared["home"],
        "CODEX_HOME": prepared["codex_home"],
        "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
    }
    if os.environ.get("OPENAI_API_KEY"):
        env["OPENAI_API_KEY"] = os.environ["OPENAI_API_KEY"]

    try:
        with Codex(
            CodexConfig(
                codex_bin=str(codex_bin),
                cwd=str(attempt_dir),
                config_overrides=tuple(controlled_codex_config_overrides()),
                env=env,
            )
        ) as codex:
            thread = codex.thread_start(
                approval_mode=ApprovalMode.deny_all,
                config={"model_reasoning_effort": reasoning_effort},
                cwd=str(attempt_dir),
                developer_instructions=_developer_instructions(),
                ephemeral=True,
                model=MODEL_NAME,
                sandbox=Sandbox.workspace_write,
            )
            turn = thread.turn(
                [
                    TextInput(build_task_prompt(task)),
                    LocalImageInput(path=str(task["reference_image"])),
                    LocalImageInput(path=str(task["rendered_png"])),
                ],
                approval_mode=ApprovalMode.deny_all,
                cwd=str(attempt_dir),
                effort=reasoning_effort,
                model=MODEL_NAME,
                sandbox=Sandbox.workspace_write,
            )
            with _turn_deadline(timeout_seconds):
                turn_result = _collect_turn_with_event_log(turn, events_path)
        final_response_path.write_text(
            str(turn_result.get("final_response") or ""), encoding="utf-8"
        )
        if not output.is_file():
            raise FileNotFoundError(f"SDK turn did not create output_json: {output}")
        gt_spec = json.loads(Path(str(task["gt_page_spec"])).read_text(encoding="utf-8"))
        payload = json.loads(output.read_text(encoding="utf-8"))
        validate_rubric_payload(task, payload, gt_spec)
        privacy_check = assert_no_forbidden_command_access(events_path)
        result = {
            "schema": "drawbench.codex_sdk_rubric.result.v1",
            "task_id": str(task["task_id"]),
            "bench_id": str(task["bench_id"]),
            "dag": str(task["dag"]),
            "lane": str(task["lane"]),
            "group": str(task["group"]),
            "model": MODEL_NAME,
            "execution_engine": EXECUTION_ENGINE,
            "thread_id": thread.id,
            "turn_id": turn_result["id"],
            "turn_completed": True,
            "turn_status": turn_result["status"],
            "validation_passed": True,
            "output_json": str(output),
            "output_sha256": sha256_file(output),
            "input_sha256": task_input_sha256(task),
            "events_path": str(events_path),
            "final_response_path": str(final_response_path),
            "elapsed_ms": int((time.monotonic() - started_at) * 1000),
            "usage": turn_result.get("usage"),
            "privacy_check": privacy_check,
        }
        (attempt_dir / "sdk_result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return result
    finally:
        shutil.rmtree(Path(prepared["home"]), ignore_errors=True)


def _write_failed_worker_result(
    task: dict[str, Any], attempt_dir: Path, error: BaseException
) -> None:
    result = {
        "schema": "drawbench.codex_sdk_rubric.result.v1",
        "task_id": str(task.get("task_id")),
        "model": MODEL_NAME,
        "execution_engine": EXECUTION_ENGINE,
        "turn_completed": False,
        "turn_status": "failed",
        "validation_passed": False,
        "error_type": error.__class__.__name__,
        "error": str(error),
        "traceback": traceback.format_exc(),
    }
    (attempt_dir / "sdk_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _run_worker_subprocess(
    task: dict[str, Any],
    *,
    host_codex_home: Path,
    codex_bin: Path,
    reasoning_effort: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    attempt_dir = create_attempt_dir(_candidate_eval_dir(task), str(task["group"]))
    stdout_path = attempt_dir / "worker.stdout.log"
    stderr_path = attempt_dir / "worker.stderr.log"
    with tempfile.TemporaryDirectory(prefix=f"drawbench-rubric-{task['task_id']}-") as temp_dir:
        runtime_dir = Path(temp_dir)
        workspace = prepare_sdk_task(task, runtime_dir)
        task_path = runtime_dir / "task.json"
        command = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--worker-task-json",
            str(task_path),
            "--attempt-dir",
            str(runtime_dir),
            "--host-codex-home",
            str(host_codex_home),
            "--codex-bin",
            str(codex_bin),
            "--reasoning-effort",
            reasoning_effort,
            "--timeout-seconds",
            str(timeout_seconds),
        ]
        with (
            stdout_path.open("w", encoding="utf-8") as stdout,
            stderr_path.open("w", encoding="utf-8") as stderr,
        ):
            process = subprocess.Popen(
                command,
                stdout=stdout,
                stderr=stderr,
                text=True,
                start_new_session=True,
            )
            try:
                return_code = process.wait(timeout=timeout_seconds + 30)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                return_code = 124

        if return_code == 0:
            try:
                finalize_sdk_task_result(task, workspace, attempt_dir)
            except (OSError, json.JSONDecodeError, ValueError) as error:
                return_code = 1
                (attempt_dir / "publish_error.json").write_text(
                    json.dumps(
                        {
                            "error_type": error.__class__.__name__,
                            "error": str(error),
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )

        if not (attempt_dir / "sdk_result.json").is_file():
            for filename in (
                "task.json",
                "sdk_setup.json",
                "events.jsonl",
                "final_response.txt",
                "sdk_result.json",
            ):
                source = runtime_dir / filename
                if source.is_file():
                    shutil.copy2(source, attempt_dir / filename)
        local_output = Path(str(workspace.task["output_json"]))
        if return_code != 0 and local_output.is_file():
            shutil.copy2(local_output, attempt_dir / "invalid_output.json")

    completion = inspect_task_completion(task)
    if return_code == 0 and completion["complete"]:
        return {
            "task_id": str(task["task_id"]),
            "status": "completed",
            "attempt_dir": str(attempt_dir),
            "completion": completion,
        }
    usage_limit = inspect_usage_limit_failure(attempt_dir)
    if usage_limit["limited"]:
        return {
            "task_id": str(task["task_id"]),
            "status": "usage_limited",
            "attempt_dir": str(attempt_dir),
            "return_code": return_code,
            "completion": completion,
            "stderr_path": str(stderr_path),
            "retry_at": usage_limit["retry_at"],
        }
    return {
        "task_id": str(task["task_id"]),
        "status": "failed",
        "attempt_dir": str(attempt_dir),
        "return_code": return_code,
        "completion": completion,
        "stderr_path": str(stderr_path),
    }


def _run_task_with_retries(
    task: dict[str, Any],
    *,
    host_codex_home: Path,
    codex_bin: Path,
    reasoning_effort: str,
    timeout_seconds: float,
    max_attempts: int,
    usage_limit_event: threading.Event,
) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    for _ in range(max_attempts):
        if usage_limit_event.is_set():
            return {
                "task_id": str(task["task_id"]),
                "status": "usage_limit_cancelled",
                "attempts": attempts,
            }
        try:
            validate_task_inputs(task)
            result = _run_worker_subprocess(
                task,
                host_codex_home=host_codex_home,
                codex_bin=codex_bin,
                reasoning_effort=reasoning_effort,
                timeout_seconds=timeout_seconds,
            )
        except FileNotFoundError as error:
            return {
                "task_id": str(task["task_id"]),
                "status": "input_unavailable",
                "attempts": attempts,
                "error_type": error.__class__.__name__,
                "error": str(error),
            }
        attempts.append(result)
        if result["status"] == "completed":
            return {**result, "attempts": attempts}
        if result["status"] == "usage_limited":
            usage_limit_event.set()
            return {**result, "attempts": attempts}
    return {
        "task_id": str(task["task_id"]),
        "status": "failed",
        "attempts": attempts,
    }


def _load_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "drawbench_rubric_task_manifest.v1":
        raise ValueError(f"unsupported task manifest schema: {manifest.get('schema')!r}")
    tasks = manifest.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != int(manifest.get("task_count", -1)):
        raise ValueError("manifest task_count does not match tasks")
    return manifest


def run_scheduler(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest).resolve()
    manifest = _load_manifest(manifest_path)
    tasks = manifest["tasks"]
    if args.archive_unverified_outputs:
        archive = archive_unverified_outputs(tasks, manifest_path.parent)
        print(f"archived_unverified={archive['archived_count']}", flush=True)
    selected = select_manifest_tasks(tasks, set(args.task_id), resume=not args.no_resume)
    precompleted = sum(inspect_task_completion(task)["complete"] for task in tasks)
    print(
        f"manifest_tasks={len(tasks)} selected={len(selected)} precompleted={precompleted} "
        f"concurrency={args.concurrency} model={MODEL_NAME}",
        flush=True,
    )
    results: list[dict[str, Any]] = []
    usage_limit_event = threading.Event()
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        future_to_task = {
            executor.submit(
                _run_task_with_retries,
                task,
                host_codex_home=Path(args.host_codex_home).expanduser(),
                codex_bin=Path(args.codex_bin).expanduser(),
                reasoning_effort=args.reasoning_effort,
                timeout_seconds=args.timeout_seconds,
                max_attempts=args.max_attempts,
                usage_limit_event=usage_limit_event,
            ): task
            for task in selected
        }
        for future in as_completed(future_to_task):
            result = future.result()
            results.append(result)
            done = sum(item["status"] == "completed" for item in results)
            failed = sum(item["status"] == "failed" for item in results)
            input_unavailable = sum(item["status"] == "input_unavailable" for item in results)
            usage_limited = sum(item["status"] == "usage_limited" for item in results)
            cancelled = sum(item["status"] == "usage_limit_cancelled" for item in results)
            print(
                f"task={result['task_id']} status={result['status']} finished={len(results)}/{len(selected)} "
                f"completed={done} failed={failed} input_unavailable={input_unavailable} "
                f"usage_limited={usage_limited} "
                f"cancelled={cancelled}",
                flush=True,
            )
    completion = {str(task["task_id"]): inspect_task_completion(task) for task in tasks}
    retry_times = sorted(
        str(item["retry_at"])
        for item in results
        if item.get("status") == "usage_limited" and item.get("retry_at")
    )
    summary = {
        "schema": "drawbench.codex_sdk_rubric.scheduler_summary.v1",
        "manifest": str(manifest_path),
        "model": MODEL_NAME,
        "execution_engine": EXECUTION_ENGINE,
        "reasoning_effort": args.reasoning_effort,
        "concurrency": args.concurrency,
        "selected_count": len(selected),
        "completed_count": sum(value["complete"] for value in completion.values()),
        "incomplete_count": sum(not value["complete"] for value in completion.values()),
        "usage_limit_detected": usage_limit_event.is_set(),
        "usage_limit_retry_at": retry_times[-1] if retry_times else None,
        "results": sorted(results, key=lambda item: item["task_id"]),
        "completion": completion,
    }
    summary_path = manifest_path.parent / "sdk_scheduler_summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"summary={summary_path}", flush=True)
    if usage_limit_event.is_set():
        return USAGE_LIMIT_EXIT_CODE
    return 0 if all(item["status"] == "completed" for item in results) else 1


MAX_CONCURRENCY = 150


def validate_concurrency(value: int) -> int:
    if value < 1 or value > MAX_CONCURRENCY:
        raise ValueError(f"--concurrency must be between 1 and {MAX_CONCURRENCY}")
    return value


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest")
    parser.add_argument("--task-id", action="append", default=[])
    parser.add_argument("--concurrency", type=int, default=40)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--timeout-seconds", type=float, default=1800)
    parser.add_argument("--reasoning-effort", default="high")
    parser.add_argument("--host-codex-home", default=str(Path.home() / ".codex"))
    parser.add_argument(
        "--codex-bin", default=os.environ.get("DRAWBENCH_CODEX_BIN", str(DEFAULT_CODEX_BIN))
    )
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--archive-unverified-outputs", action="store_true")
    parser.add_argument("--worker-task-json")
    parser.add_argument("--attempt-dir")
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    if not 1 <= args.concurrency <= MAX_CONCURRENCY:
        parser.error(f"--concurrency must be between 1 and {MAX_CONCURRENCY}")
    if args.max_attempts < 1:
        parser.error("--max-attempts must be at least 1")
    if args.worker_task_json:
        if not args.attempt_dir:
            parser.error("--attempt-dir is required with --worker-task-json")
        task = json.loads(Path(args.worker_task_json).read_text(encoding="utf-8"))
        attempt_dir = Path(args.attempt_dir).resolve()
        try:
            result = run_sdk_worker(
                task,
                attempt_dir,
                host_codex_home=Path(args.host_codex_home).expanduser(),
                codex_bin=Path(args.codex_bin).expanduser(),
                reasoning_effort=args.reasoning_effort,
                timeout_seconds=args.timeout_seconds,
            )
        except BaseException as error:
            _write_failed_worker_result(task, attempt_dir, error)
            raise
        print(json.dumps(result, ensure_ascii=False), flush=True)
        return 0
    if not args.manifest:
        parser.error("--manifest is required in scheduler mode")
    return run_scheduler(args)


if __name__ == "__main__":
    raise SystemExit(main())
