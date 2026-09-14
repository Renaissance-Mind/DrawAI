#!/usr/bin/env python3
"""Merge DrawAI-Bench rule and SDK rubric outputs into the 39-metric hierarchy."""

from __future__ import annotations

import argparse
import csv
import json
import os
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from drawai_evaluation import rubric as rubric_sdk


def _label(zh: str, en: str) -> dict[str, str]:
    return {"zh": zh, "en": en}


def _metric(
    metric_id: str,
    primary: tuple[str, str],
    secondary: tuple[str, str],
    tertiary: tuple[str, str],
    calculator: str,
    method: str,
    *,
    direction: str = "up",
    rule_key: str | None = None,
    rubric_group: str | None = None,
    criterion: str | None = None,
    kind: str | None = None,
) -> dict[str, Any]:
    return {
        "metric_id": metric_id,
        "primary": _label(*primary),
        "secondary": _label(*secondary),
        "tertiary": _label(*tertiary),
        "calculator": calculator,
        "method": method,
        "direction": direction,
        "rule_key": rule_key,
        "rubric_group": rubric_group,
        "criterion": criterion,
        "kind": kind,
    }


def metric_catalog() -> list[dict[str, Any]]:
    reconstruction = ("还原性", "Reconstruction")
    editability = ("可编辑性", "Editability")
    global_fidelity = ("整图视觉还原", "Global Visual Fidelity")
    text_fidelity = ("文本保真度", "Text Fidelity")
    image_fidelity = ("图像保真度", "Image Fidelity")
    formula_fidelity = ("公式保真度", "Formula Fidelity")
    shape_fidelity = ("Shape 保真度", "Shape Fidelity")
    connector_fidelity = ("连接线保真度", "Connector Fidelity")
    table_fidelity = ("表格保真度", "Table Fidelity")
    text_editability = ("文本可编辑性", "Text Editability")
    image_editability = ("图像组件可编辑性", "Image Editability")
    shape_editability = ("Shape 可编辑性", "Shape Editability")
    connector_editability = ("连接线可编辑性", "Connector Editability")
    formula_editability = ("公式可编辑性", "Formula Editability")
    table_editability = ("表格可编辑性", "Table Editability")
    return [
        _metric(
            "reconstruction.global.structural_match",
            reconstruction,
            global_fidelity,
            ("结构匹配", "Structural match"),
            "SSIM",
            "rule",
            rule_key="ssim",
        ),
        _metric(
            "reconstruction.global.edge_alignment",
            reconstruction,
            global_fidelity,
            ("边缘对齐", "Edge alignment"),
            "Edge F1",
            "rule",
            rule_key="edge_f1",
        ),
        _metric(
            "reconstruction.global.pixel_error",
            reconstruction,
            global_fidelity,
            ("像素误差", "Pixel error"),
            "MSE",
            "rule",
            direction="down",
            rule_key="mse",
        ),
        _metric(
            "reconstruction.global.overall_readability",
            reconstruction,
            global_fidelity,
            ("整体可读性", "Overall readability"),
            "VLM Score",
            "rubric",
            rubric_group="global",
            criterion="overall_readability",
        ),
        _metric(
            "reconstruction.global.layout_skeleton",
            reconstruction,
            global_fidelity,
            ("布局骨架", "Layout skeleton"),
            "Layout QA",
            "rubric",
            rubric_group="global",
            criterion="layout_skeleton",
        ),
        _metric(
            "reconstruction.global.visual_hierarchy",
            reconstruction,
            global_fidelity,
            ("视觉层级", "Visual hierarchy"),
            "Hierarchy QA",
            "rubric",
            rubric_group="global",
            criterion="visual_hierarchy",
        ),
        _metric(
            "reconstruction.text.text_content",
            reconstruction,
            text_fidelity,
            ("文本内容", "Text content"),
            "Text F1",
            "rule",
            rule_key="text_f1",
            kind="text",
        ),
        _metric(
            "reconstruction.text.position_lines",
            reconstruction,
            text_fidelity,
            ("位置与行列", "Position lines"),
            "Layout QA",
            "rubric",
            rubric_group="text",
            criterion="position_lines",
            kind="text",
        ),
        _metric(
            "reconstruction.text.alignment_spacing",
            reconstruction,
            text_fidelity,
            ("对齐与间距", "Alignment spacing"),
            "Layout QA",
            "rubric",
            rubric_group="text",
            criterion="alignment_spacing",
            kind="text",
        ),
        _metric(
            "reconstruction.text.overflow_occlusion",
            reconstruction,
            text_fidelity,
            ("溢出遮挡", "Overflow occlusion"),
            "Occlusion QA",
            "rubric",
            rubric_group="text",
            criterion="overflow_occlusion",
            kind="text",
        ),
        _metric(
            "reconstruction.text.color_emphasis",
            reconstruction,
            text_fidelity,
            ("色彩强调", "Color emphasis"),
            "Style QA",
            "rubric",
            rubric_group="text",
            criterion="color_emphasis",
            kind="text",
        ),
        _metric(
            "reconstruction.text.font_appearance",
            reconstruction,
            text_fidelity,
            ("字体观感", "Font appearance"),
            "Style QA",
            "rubric",
            rubric_group="text",
            criterion="font_appearance",
            kind="text",
        ),
        _metric(
            "reconstruction.text.style_consistency",
            reconstruction,
            text_fidelity,
            ("样式一致性", "Style consistency"),
            "Style QA",
            "rubric",
            rubric_group="text",
            criterion="style_consistency",
            kind="text",
        ),
        _metric(
            "reconstruction.image.image_regions",
            reconstruction,
            image_fidelity,
            ("图像区域", "Image Regions"),
            "Region MSE",
            "rule",
            direction="down",
            rule_key="image_region_mse",
            kind="image",
        ),
        _metric(
            "reconstruction.image.image_alignment",
            reconstruction,
            image_fidelity,
            ("图像对齐", "Image Alignment"),
            "Image mIoU",
            "rule",
            rule_key="image_miou",
            kind="image",
        ),
        _metric(
            "reconstruction.formula.symbol_retention",
            reconstruction,
            formula_fidelity,
            ("符号保留", "Symbol retention"),
            "Formula QA",
            "rubric",
            rubric_group="formula",
            criterion="symbol_retention",
            kind="formula",
        ),
        _metric(
            "reconstruction.formula.structure_relation",
            reconstruction,
            formula_fidelity,
            ("结构关系", "Structure relation"),
            "Formula QA",
            "rubric",
            rubric_group="formula",
            criterion="structure_relation",
            kind="formula",
        ),
        _metric(
            "reconstruction.formula.position_readability",
            reconstruction,
            formula_fidelity,
            ("位置可读性", "Position readability"),
            "Formula QA",
            "rubric",
            rubric_group="formula",
            criterion="position_readability",
            kind="formula",
        ),
        _metric(
            "reconstruction.shape.existence_coverage",
            reconstruction,
            shape_fidelity,
            ("存在覆盖", "Existence coverage"),
            "Shape QA",
            "rubric",
            rubric_group="shape",
            criterion="existence_coverage",
            kind="shape",
        ),
        _metric(
            "reconstruction.shape.visual_attributes",
            reconstruction,
            shape_fidelity,
            ("视觉属性", "Visual attributes"),
            "Shape QA",
            "rubric",
            rubric_group="shape",
            criterion="visual_attributes",
            kind="shape",
        ),
        _metric(
            "reconstruction.shape.neighbor_relation",
            reconstruction,
            shape_fidelity,
            ("相邻关系", "Neighbor relation"),
            "Shape QA",
            "rubric",
            rubric_group="shape",
            criterion="neighbor_relation",
            kind="shape",
        ),
        _metric(
            "reconstruction.connector.path_presence",
            reconstruction,
            connector_fidelity,
            ("路径存在", "Path presence"),
            "Connector QA",
            "rubric",
            rubric_group="connector",
            criterion="path_presence",
            kind="connector",
        ),
        _metric(
            "reconstruction.connector.endpoint_direction",
            reconstruction,
            connector_fidelity,
            ("端点方向", "Endpoint direction"),
            "Connector QA",
            "rubric",
            rubric_group="connector",
            criterion="endpoint_direction",
            kind="connector",
        ),
        _metric(
            "reconstruction.connector.line_style_noise",
            reconstruction,
            connector_fidelity,
            ("线型干扰", "Line style noise"),
            "Connector QA",
            "rubric",
            rubric_group="connector",
            criterion="line_style_noise",
            kind="connector",
        ),
        _metric(
            "reconstruction.table.grid_structure",
            reconstruction,
            table_fidelity,
            ("网格结构", "Grid structure"),
            "Table QA",
            "rubric",
            rubric_group="table",
            criterion="grid_structure",
            kind="table",
        ),
        _metric(
            "reconstruction.table.content_ownership",
            reconstruction,
            table_fidelity,
            ("内容归属", "Content ownership"),
            "Table QA",
            "rubric",
            rubric_group="table",
            criterion="content_ownership",
            kind="table",
        ),
        _metric(
            "reconstruction.table.readability_alignment",
            reconstruction,
            table_fidelity,
            ("可读对齐", "Readability alignment"),
            "Table QA",
            "rubric",
            rubric_group="table",
            criterion="readability_alignment",
            kind="table",
        ),
        _metric(
            "editability.text.text_boxes",
            editability,
            text_editability,
            ("文本框", "Text boxes"),
            "Box Recall",
            "rule",
            rule_key="text_box_recall",
            kind="text",
        ),
        _metric(
            "editability.image.image_sources",
            editability,
            image_editability,
            ("图像源对象", "Image Sources"),
            "Image Recall",
            "rule",
            rule_key="image_recall",
            kind="image",
        ),
        _metric(
            "editability.shape.object_independence",
            editability,
            shape_editability,
            ("对象独立性", "Object independence"),
            "VLM-QA",
            "rubric",
            rubric_group="shape",
            criterion="object_independence",
            kind="shape",
        ),
        _metric(
            "editability.shape.box_placement",
            editability,
            shape_editability,
            ("框位置", "Box placement"),
            "BBox QA",
            "rubric",
            rubric_group="shape",
            criterion="box_placement",
            kind="shape",
        ),
        _metric(
            "editability.shape.conflict_diagnosis",
            editability,
            shape_editability,
            ("冲突诊断", "Conflict diagnosis"),
            "VLM-QA",
            "rubric",
            rubric_group="shape",
            criterion="conflict_diagnosis",
            kind="shape",
        ),
        _metric(
            "editability.connector.independent_path",
            editability,
            connector_editability,
            ("独立路径", "Independent path"),
            "VLM-QA",
            "rubric",
            rubric_group="connector",
            criterion="independent_path",
            kind="connector",
        ),
        _metric(
            "editability.connector.endpoint_control",
            editability,
            connector_editability,
            ("端点控制", "Endpoint control"),
            "VLM-QA",
            "rubric",
            rubric_group="connector",
            criterion="endpoint_control",
            kind="connector",
        ),
        _metric(
            "editability.connector.mis_merge_check",
            editability,
            connector_editability,
            ("误合并检查", "Mis merge check"),
            "VLM-QA",
            "rubric",
            rubric_group="connector",
            criterion="mis_merge_check",
            kind="connector",
        ),
        _metric(
            "editability.formula.editable_representation",
            editability,
            formula_editability,
            ("可编辑表示", "Editable representation"),
            "Object Recall",
            "rule",
            rule_key="formula_editable_representation",
            kind="formula",
        ),
        _metric(
            "editability.table.table_regions",
            editability,
            table_editability,
            ("独立表格区域", "Table region independence"),
            "VLM-QA",
            "rubric",
            rubric_group="table",
            criterion="table_region_independence",
            kind="table",
        ),
        _metric(
            "editability.table.editable_grid",
            editability,
            table_editability,
            ("可编辑网格", "Editable grid"),
            "VLM-QA",
            "rubric",
            rubric_group="table",
            criterion="editable_grid",
            kind="table",
        ),
        _metric(
            "editability.table.text_ownership",
            editability,
            table_editability,
            ("文本归属", "Text ownership"),
            "VLM-QA",
            "rubric",
            rubric_group="table",
            criterion="text_ownership",
            kind="table",
        ),
    ]


def recompute_element_criterion(payload: dict[str, Any], criterion: str) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    scores: list[float] = []
    for row in payload["per_element"]:
        value = row["scores"][criterion]
        counts[value["answer"]] += 1
        if value["score"] is not None:
            scores.append(float(value["score"]))
    return {
        "score": sum(scores) / len(scores) if scores else None,
        "valid_count": len(scores),
        "yes_count": counts["yes"],
        "partial_count": counts["partial"],
        "no_count": counts["no"],
        "na_count": counts["N/A"],
    }


def _metric_base(definition: dict[str, Any]) -> dict[str, Any]:
    return {
        key: definition[key]
        for key in (
            "metric_id",
            "primary",
            "secondary",
            "tertiary",
            "calculator",
            "method",
            "direction",
            "kind",
        )
    }


def not_applicable_metric(definition: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        **_metric_base(definition),
        "status": "not_applicable",
        "score": None,
        "reason": reason,
        "evidence": {},
    }


def _scored_rule_metric(
    definition: dict[str, Any], value: float, rule_path: Path
) -> dict[str, Any]:
    return {
        **_metric_base(definition),
        "status": "scored",
        "score": float(value),
        "reason": "Computed by the standard rule-based evaluator.",
        "evidence": {"rule_based_eval": str(rule_path), "metric_key": definition["rule_key"]},
    }


def _scored_rubric_metric(
    definition: dict[str, Any], payload: dict[str, Any], rubric_path: Path, sdk_result: str
) -> dict[str, Any]:
    criterion = str(definition["criterion"])
    if definition["rubric_group"] == "global":
        aggregate = payload["aggregate"][criterion]
        score = aggregate["score"]
        details = {"answer": aggregate["answer"]}
        reason = aggregate["reason"]
    else:
        details = recompute_element_criterion(payload, criterion)
        score = details["score"]
        reason = payload["aggregate"][criterion]["reason"]
    if score is None:
        return not_applicable_metric(definition, reason or "all rubric answers were N/A")
    return {
        **_metric_base(definition),
        "status": "scored",
        "score": float(score),
        "reason": reason,
        "aggregate_details": details,
        "evidence": {
            "rubric_json": str(rubric_path),
            "sdk_result": sdk_result,
            "criterion": criterion,
            "model": payload["model"],
            "execution_engine": payload["execution_engine"],
        },
    }


def expected_rubric_groups(kind_counts: Mapping[str, int]) -> set[str]:
    return {
        "global",
        *(
            group
            for group in ("text", "shape", "connector", "formula", "table")
            if int(kind_counts.get(group, 0)) > 0
        ),
    }


def build_candidate_rows(
    tasks: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    task_by_group = {str(task["group"]): task for task in tasks}
    first = tasks[0]
    gt_path = Path(str(first["gt_page_spec"]))
    gt_spec = json.loads(gt_path.read_text(encoding="utf-8"))
    kind_counts = Counter(str(element.get("kind")) for element in gt_spec.get("elements", []))
    expected_groups = expected_rubric_groups(kind_counts)
    if set(task_by_group) != expected_groups:
        raise ValueError(
            f"candidate rubric groups must be {sorted(expected_groups)}, got {sorted(task_by_group)}"
        )
    for task in tasks:
        completion = rubric_sdk.inspect_task_completion(task)
        if not completion["complete"]:
            raise RuntimeError(f"task {task['task_id']} is incomplete: {completion['reason']}")

    rule_path = Path(str(first["rule_based_eval"]))
    rule_payload = json.loads(rule_path.read_text(encoding="utf-8"))
    rule_metrics = rule_payload["metrics"]
    rubric_payloads: dict[str, dict[str, Any]] = {}
    completions: dict[str, dict[str, Any]] = {}
    for group, task in task_by_group.items():
        rubric_path = Path(str(task["output_json"]))
        rubric_payloads[group] = json.loads(rubric_path.read_text(encoding="utf-8"))
        completions[group] = rubric_sdk.inspect_task_completion(task)

    rows: list[dict[str, Any]] = []
    for definition in metric_catalog():
        kind = definition["kind"]
        if kind and kind_counts[kind] == 0:
            rows.append(not_applicable_metric(definition, f"no GT elements of kind {kind}"))
            continue
        if definition["method"] == "rule":
            value = rule_metrics.get(definition["rule_key"])
            if value is None:
                raise ValueError(
                    f"rule metric {definition['rule_key']} is missing for {first['bench_id']}"
                )
            rows.append(_scored_rule_metric(definition, value, rule_path))
            continue
        group = str(definition["rubric_group"])
        if group not in rubric_payloads:
            raise ValueError(f"missing rubric group {group} for a non-empty GT kind")
        task = task_by_group[group]
        rows.append(
            _scored_rubric_metric(
                definition,
                rubric_payloads[group],
                Path(str(task["output_json"])),
                str(completions[group]["result_path"]),
            )
        )
    if len(rows) != 39 or len({row["metric_id"] for row in rows}) != 39:
        raise RuntimeError("candidate evaluation must contain exactly 39 unique rows")
    metadata = {
        "bench_id": str(first["bench_id"]),
        "dag": str(first["dag"]),
        "lane": str(first["lane"]),
        "gt_page_spec": str(gt_path),
        "reference_image": str(first["reference_image"]),
        "candidate_svg": str(first["candidate_svg"]),
        "rendered_png": str(first["rendered_png"]),
        "rule_based_eval": str(rule_path),
        "gt_kind_counts": dict(sorted(kind_counts.items())),
    }
    return rows, metadata


def _candidate_key(metadata: dict[str, Any]) -> str:
    return f"{metadata['bench_id']}::{metadata['dag']}::{metadata['lane']}"


def _write_csv_outputs(
    output_root: Path, evaluations: list[dict[str, Any]], catalog: list[dict[str, Any]]
) -> None:
    long_path = output_root / "full_evaluation_long.csv"
    long_fields = [
        "bench_id",
        "dag",
        "lane",
        "metric_id",
        "primary_zh",
        "primary_en",
        "secondary_zh",
        "secondary_en",
        "tertiary_zh",
        "tertiary_en",
        "calculator",
        "method",
        "direction",
        "kind",
        "status",
        "score",
        "reason",
    ]
    with long_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=long_fields)
        writer.writeheader()
        for evaluation in evaluations:
            metadata = evaluation["candidate"]
            for row in evaluation["metrics"]:
                writer.writerow(
                    {
                        "bench_id": metadata["bench_id"],
                        "dag": metadata["dag"],
                        "lane": metadata["lane"],
                        "metric_id": row["metric_id"],
                        "primary_zh": row["primary"]["zh"],
                        "primary_en": row["primary"]["en"],
                        "secondary_zh": row["secondary"]["zh"],
                        "secondary_en": row["secondary"]["en"],
                        "tertiary_zh": row["tertiary"]["zh"],
                        "tertiary_en": row["tertiary"]["en"],
                        "calculator": row["calculator"],
                        "method": row["method"],
                        "direction": row["direction"],
                        "kind": row["kind"] or "",
                        "status": row["status"],
                        "score": "" if row["score"] is None else row["score"],
                        "reason": row["reason"],
                    }
                )

    metric_ids = [row["metric_id"] for row in catalog]
    wide_path = output_root / "full_evaluation_wide.csv"
    with wide_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["bench_id", "dag", "lane", *metric_ids])
        writer.writeheader()
        for evaluation in evaluations:
            metadata = evaluation["candidate"]
            scores = {row["metric_id"]: row["score"] for row in evaluation["metrics"]}
            writer.writerow(
                {
                    "bench_id": metadata["bench_id"],
                    "dag": metadata["dag"],
                    "lane": metadata["lane"],
                    **scores,
                }
            )

    candidate_keys = [_candidate_key(evaluation["candidate"]) for evaluation in evaluations]
    comparison_path = output_root / "metric_comparison.csv"
    with comparison_path.open("w", newline="", encoding="utf-8") as handle:
        fields = [
            "metric_id",
            "primary_zh",
            "secondary_zh",
            "tertiary_zh",
            "method",
            "direction",
            *candidate_keys,
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for definition in catalog:
            row = {
                "metric_id": definition["metric_id"],
                "primary_zh": definition["primary"]["zh"],
                "secondary_zh": definition["secondary"]["zh"],
                "tertiary_zh": definition["tertiary"]["zh"],
                "method": definition["method"],
                "direction": definition["direction"],
            }
            for evaluation, key in zip(evaluations, candidate_keys, strict=True):
                value = next(
                    item["score"]
                    for item in evaluation["metrics"]
                    if item["metric_id"] == definition["metric_id"]
                )
                row[key] = "" if value is None else value
            writer.writerow(row)


def _candidate_tasks_are_complete(tasks: list[dict[str, Any]]) -> bool:
    if not all(Path(str(task["output_json"])).is_file() for task in tasks):
        return False
    return all(rubric_sdk.inspect_task_completion(task)["complete"] for task in tasks)


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def merge_manifest(manifest_path: Path, *, allow_partial: bool = False) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    tasks = manifest["tasks"]
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for task in tasks:
        key = (str(task["bench_id"]), str(task["dag"]), str(task["lane"]))
        grouped.setdefault(key, []).append(task)
    output_root = manifest_path.parent
    catalog = metric_catalog()
    evaluations: list[dict[str, Any]] = []
    for key in sorted(grouped):
        candidate_tasks = sorted(grouped[key], key=lambda task: str(task["task_id"]))
        if allow_partial and not _candidate_tasks_are_complete(candidate_tasks):
            continue
        rows, metadata = build_candidate_rows(candidate_tasks)
        candidate_dir = Path(str(candidate_tasks[0]["output_json"])).parent.parent
        evaluation = {
            "schema": "drawbench.full_tertiary_evaluation.v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "candidate": metadata,
            "metric_count": len(rows),
            "scored_count": sum(row["status"] == "scored" for row in rows),
            "not_applicable_count": sum(row["status"] == "not_applicable" for row in rows),
            "metrics": rows,
        }
        path = candidate_dir / "full_evaluation.json"
        _write_json_atomic(path, evaluation)
        evaluation["output_json"] = str(path)
        evaluations.append(evaluation)
    _write_csv_outputs(output_root, evaluations, catalog)
    summary = {
        "schema": "drawbench.full_tertiary_summary.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "manifest": str(manifest_path),
        "candidate_count": len(evaluations),
        "expected_candidate_count": int(manifest.get("candidate_count", len(grouped))),
        "partial": len(evaluations) < int(manifest.get("candidate_count", len(grouped))),
        "metrics_per_candidate": len(catalog),
        "total_metric_rows": sum(len(item["metrics"]) for item in evaluations),
        "rule_metric_count": sum(row["method"] == "rule" for row in catalog),
        "rubric_metric_count": sum(row["method"] == "rubric" for row in catalog),
        "outputs": {
            "long_csv": str(output_root / "full_evaluation_long.csv"),
            "wide_csv": str(output_root / "full_evaluation_wide.csv"),
            "comparison_csv": str(output_root / "metric_comparison.csv"),
        },
        "candidates": [
            {
                "bench_id": item["candidate"]["bench_id"],
                "dag": item["candidate"]["dag"],
                "lane": item["candidate"]["lane"],
                "scored_count": item["scored_count"],
                "not_applicable_count": item["not_applicable_count"],
                "output_json": item["output_json"],
            }
            for item in evaluations
        ],
    }
    _write_json_atomic(
        output_root / "metric_catalog.json",
        {"schema": "drawbench.metric_catalog.v1", "metrics": catalog},
    )
    summary_path = output_root / "full_evaluation_summary.json"
    _write_json_atomic(summary_path, summary)
    return summary


def watch_partial_merge(manifest_path: Path, interval_seconds: float) -> int:
    while True:
        summary = merge_manifest(manifest_path, allow_partial=True)
        print(
            f"merged={summary['candidate_count']}/{summary['expected_candidate_count']} "
            f"generated_at={summary['generated_at']}",
            flush=True,
        )
        if not summary["partial"]:
            return 0
        time.sleep(interval_seconds)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument("--watch-partial", action="store_true")
    parser.add_argument("--watch-interval-seconds", type=float, default=30)
    args = parser.parse_args()
    manifest_path = Path(args.manifest).resolve()
    if args.watch_interval_seconds <= 0:
        parser.error("--watch-interval-seconds must be positive")
    if args.watch_partial:
        return watch_partial_merge(manifest_path, args.watch_interval_seconds)
    summary = merge_manifest(manifest_path, allow_partial=args.allow_partial)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
