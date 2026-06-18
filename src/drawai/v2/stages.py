from __future__ import annotations

import html
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, cast

from PIL import Image, ImageDraw

from drawai.artifacts import DrawAiArtifactPaths, write_json
from drawai.config import DrawAiPipelineConfig
from drawai.core import ArtifactRef, ArtifactStore, ProviderRef, RunContext, StageResult, StageSpec
from drawai.image_normalization import normalize_input_image
from drawai.ocr_provider import clamp_ocr_boxes_to_canvas
from drawai.sam3_client import JsonTransport, run_sam3_prompt_plan
from drawai.svg_to_ppt_check import CompilerCallable

from .compat import write_asset_manifest_compat, write_box_ir_compat, write_element_analysis_compat
from .fusion import FusionConfig, fuse_candidates
from .packages import write_asset_package, write_element_plan
from .parsers import ocr_payload_to_candidates, sam3_payload_to_candidates
from .processors import processor_for_type
from .refine import CodexElementRefiner, RefineConfig
from .schema import (
    RUN_PACKAGE_SCHEMA,
    AssetPackage,
    ElementCandidate,
    ElementPlan,
    ProcessingIntent,
    utc_now,
)

V2_STAGE_ORDER = (
    "prepare",
    "parse_elements",
    "fuse_elements",
    "refine_elements",
    "plan_assets",
    "process_assets",
    "compose_svg",
    "export",
    "package_run",
)

_CHAIN_DEPENDENCIES: dict[str, tuple[str, ...]] = {
    "prepare": (),
    "parse_elements": ("prepare",),
    "fuse_elements": ("parse_elements",),
    "refine_elements": ("fuse_elements",),
    "plan_assets": ("refine_elements",),
    "process_assets": ("plan_assets",),
    "compose_svg": ("process_assets",),
    "export": ("compose_svg",),
    "package_run": ("export",),
}

_STAGE_OUTPUT_PATHS: Mapping[str, Mapping[str, str]] = {
    "prepare": {
        "original_image": "original_image",
        "figure_image": "figure_image",
        "source_metadata": "source_metadata",
    },
    "parse_elements": {
        "parser_outputs": "v2_parser_outputs_dir",
        "raw_regions": "raw_regions_json",
        "ocr_boxes": "ocr_boxes_json",
    },
    "fuse_elements": {
        "run_package": "run_package_json",
        "elements": "v2_elements_dir",
        "fusion_trace": "v2_fusion_trace_json",
        "box_ir": "box_ir_json",
    },
    "refine_elements": {
        "run_package": "run_package_json",
        "elements": "v2_elements_dir",
        "refine_trace": "v2_refine_trace_json",
        "element_analysis": "element_analysis_json",
    },
    "plan_assets": {
        "run_package": "run_package_json",
        "elements": "v2_elements_dir",
        "asset_manifest": "asset_manifest_json",
    },
    "process_assets": {
        "run_package": "run_package_json",
        "elements": "v2_elements_dir",
        "asset_manifest": "asset_manifest_json",
        "processor_trace": "v2_processor_trace_jsonl",
    },
    "compose_svg": {
        "semantic_svg": "semantic_svg",
        "rendered_png": "rendered_png",
        "svg_validation_report": "svg_validation_report_json",
    },
    "export": {
        "svg_to_ppt_export_report": "svg_to_ppt_export_report_json",
        "exports": "exports_dir",
    },
    "package_run": {
        "run_package": "run_package_json",
    },
}

_PROVIDER_REFS: Mapping[str, tuple[ProviderRef, ...]] = {
    "parse_elements": (
        ProviderRef("sam3_transport", "SamDetector", required=False),
        ProviderRef("ocr_provider", "OcrDetector", required=False),
    ),
    "process_assets": (
        ProviderRef("rmbg_client", "BackgroundRemover", required=False),
        ProviderRef("image_generate", "ImageGenerator", required=False),
        ProviderRef("image_edit", "ImageEditor", required=False),
    ),
    "compose_svg": (
        ProviderRef("svg_invoker", "SvgGenerator", required=False),
    ),
    "export": (ProviderRef("svg_to_ppt_compiler", "PptExporter", required=False),),
}


@dataclass(frozen=True)
class V2StageOptions:
    sam3_transport: JsonTransport | None = None
    ocr_provider: Any | None = None
    rmbg_client: Any | None = None
    svg_invoker: Any | None = None
    svg_to_ppt_compiler: CompilerCallable | None = None
    image_generate: Any | None = None
    image_edit: Any | None = None

    def provider_mapping(self) -> dict[str, Any]:
        providers = {
            "sam3_transport": self.sam3_transport,
            "ocr_provider": self.ocr_provider,
            "rmbg_client": self.rmbg_client,
            "svg_invoker": self.svg_invoker,
            "svg_to_ppt_compiler": self.svg_to_ppt_compiler,
            "image_generate": self.image_generate,
            "image_edit": self.image_edit,
        }
        return {name: provider for name, provider in providers.items() if provider is not None}


def build_v2_run_context(
    cfg: DrawAiPipelineConfig,
    paths: DrawAiArtifactPaths,
    *,
    options: V2StageOptions | None = None,
) -> RunContext:
    resolved_options = options or V2StageOptions()
    return RunContext(
        config={
            "pipeline_config": cfg,
            "artifact_paths": paths,
            "v2_stage_options": resolved_options,
        },
        artifacts=ArtifactStore(paths.root),
        providers=resolved_options.provider_mapping(),
        metadata={"execution_mode": "v2_file_stage_runner"},
    )


def build_v2_stage_specs(
    stage_ids: Iterable[str],
    *,
    options: V2StageOptions | None = None,
) -> list[StageSpec]:
    selected = tuple(stage_ids)
    _validate_stage_ids(selected)
    selected_set = set(selected)
    resolved_options = options or V2StageOptions()
    return [
        StageSpec(
            stage_id=stage_id,
            depends_on=tuple(dependency for dependency in _CHAIN_DEPENDENCIES[stage_id] if dependency in selected_set),
            outputs=tuple(_STAGE_OUTPUT_PATHS[stage_id]),
            providers=_PROVIDER_REFS.get(stage_id, ()),
            run=_stage_runner(stage_id, resolved_options),
        )
        for stage_id in selected
    ]


def _stage_runner(stage_id: str, options: V2StageOptions):
    def run(context: RunContext) -> StageResult:
        cfg = cast(DrawAiPipelineConfig, context.config["pipeline_config"])
        paths = cast(DrawAiArtifactPaths, context.config["artifact_paths"])
        _run_v2_stage(stage_id, cfg, paths, options=options)
        return StageResult.ok(
            stage_id,
            artifacts=_register_stage_outputs(context.artifacts, paths, stage_id),
        )

    return run


def _run_v2_stage(
    stage: str,
    cfg: DrawAiPipelineConfig,
    paths: DrawAiArtifactPaths,
    *,
    options: V2StageOptions,
) -> None:
    if stage == "prepare":
        if not cfg.input.image.exists():
            raise FileNotFoundError(f"input.image does not exist: {cfg.input.image}")
        normalize_input_image(cfg.input, paths)
        return

    if stage == "parse_elements":
        _require_path(paths.figure_image, "normalized figure image")
        _run_parse_elements(cfg, paths, options)
        return

    if stage == "fuse_elements":
        candidates = _read_parser_candidates(paths)
        fusion_result = fuse_candidates(
            candidates,
            config=FusionConfig(duplicate_iou_threshold=cfg.v2.fusion.duplicate_iou_threshold),
        )
        plans = _plans_with_candidate_text(fusion_result.elements, candidates)
        _write_element_plans(paths.root, plans)
        write_json(paths.v2_fusion_trace_json, fusion_result.trace)
        _write_v2_package(paths, cfg, elements=plans, stage="fuse_elements")
        _write_box_ir_compat_output(paths, plans)
        return

    if stage == "refine_elements":
        plans = _read_element_plans(paths)
        if cfg.v2.refine.enabled:
            refine_config = RefineConfig(
                enabled=cfg.v2.refine.enabled,
                provider=cfg.v2.refine.provider,
            )
            plans = _refine_with_codex_analysis(paths, plans, refine_config)
            write_json(
                paths.v2_refine_trace_json,
                {
                    "schema": "drawai.v2.refine_trace.v1",
                    "stage": "refine_elements",
                    "status": "agent_refined",
                    "provider": refine_config.provider,
                    "element_count": len(plans),
                    "analysis_path": str(paths.element_analysis_json),
                },
            )
        else:
            write_json(
                paths.v2_refine_trace_json,
                {
                    "schema": "drawai.v2.refine_trace.v1",
                    "stage": "refine_elements",
                    "status": "skipped",
                    "provider": cfg.v2.refine.provider,
                    "element_count": len(plans),
                },
            )
        _write_element_plans(paths.root, plans)
        _write_v2_package(paths, cfg, elements=plans, stage="refine_elements")
        _write_compat_outputs(paths, plans)
        return

    if stage == "plan_assets":
        plans = tuple(_asset_planned_element(cfg, plan) for plan in _read_element_plans(paths))
        _write_element_plans(paths.root, plans)
        pending_packages = tuple(
            AssetPackage.empty(
                asset_id=_asset_id(plan),
                element_id=plan.element_id,
                processor_type=plan.processing_intent.processing_type,
            )
            for plan in plans
        )
        for package in pending_packages:
            write_asset_package(paths.root, package)
        asset_manifest = write_asset_manifest_compat(paths.root, pending_packages)
        _write_v2_package(paths, cfg, elements=plans, asset_packages=pending_packages, stage="plan_assets")
        write_json(
            paths.v2_processor_trace_jsonl.with_suffix(".plan.json"),
            {
                "schema": "drawai.v2.asset_plan_trace.v1",
                "stage": "plan_assets",
                "asset_count": len(pending_packages),
            },
        )
        write_json(paths.asset_manifest_json, asset_manifest)
        return

    if stage == "process_assets":
        plans = _read_element_plans(paths)
        packages = _process_asset_packages(cfg, paths, plans, options)
        write_asset_manifest_compat(paths.root, packages)
        _write_v2_package(paths, cfg, elements=plans, asset_packages=packages, stage="process_assets")
        return

    if stage == "compose_svg":
        plans = _read_element_plans(paths)
        asset_packages = _read_asset_packages(paths, plans)
        write_asset_manifest_compat(paths.root, asset_packages)
        _write_semantic_svg(paths, plans)
        _write_rendered_preview(paths, plans)
        write_json(
            paths.svg_validation_report_json,
            {
                "schema": "drawai.svg_validation_report.v1",
                "status": "ok",
                "source": "v2.compose_svg",
                "semantic_svg": str(paths.semantic_svg),
            },
        )
        _write_v2_package(paths, cfg, elements=plans, asset_packages=asset_packages, stage="compose_svg")
        return

    if stage == "export":
        asset_manifest = _read_json_if_exists(paths.asset_manifest_json, default={"assets": []})
        if cfg.svg_to_ppt.enabled and cfg.svg_to_ppt.export_pptx:
            from drawai.pipeline import _check_svg_to_ppt

            report = _check_svg_to_ppt(cfg, paths, asset_manifest, options.svg_to_ppt_compiler)
        else:
            report = {
                "schema": "drawai.svg_to_ppt_export_report.v1",
                "status": "ok",
                "source": "v2.export",
                "enabled": cfg.svg_to_ppt.enabled,
                "export_pptx": cfg.svg_to_ppt.export_pptx,
                "semantic_svg": str(paths.semantic_svg),
            }
        write_json(paths.svg_to_ppt_export_report_json, report)
        if report.get("status") != "ok":
            raise RuntimeError("SVG-to-PPTX export failed.")
        return

    if stage == "package_run":
        plans = _read_element_plans(paths)
        asset_packages = _read_asset_packages(paths, plans)
        _write_v2_package(paths, cfg, elements=plans, asset_packages=asset_packages, stage="package_run")
        return

    raise ValueError(f"Unsupported v2 stage: {stage}")


def _run_parse_elements(
    cfg: DrawAiPipelineConfig,
    paths: DrawAiArtifactPaths,
    options: V2StageOptions,
) -> None:
    from drawai.pipeline import _extract_ocr_boxes, _load_normalized_size, _release_runtime_if_supported, _sam_boxes_by_prompt

    if not cfg.v2.parser.enabled:
        _write_parser_outputs(paths, (), ())
        return

    normalized_size = _load_normalized_size(paths)
    sam_payload = _sam_payload_for_parse(cfg, paths, options)
    sam_candidates = (
        sam3_payload_to_candidates(sam_payload, paths.figure_image)
        if cfg.v2.parser.sam3_enabled
        else ()
    )

    if cfg.v2.parser.ocr_enabled:
        ocr_payload = _extract_ocr_boxes(cfg, paths.figure_image, options.ocr_provider)
        ocr_payload = clamp_ocr_boxes_to_canvas(
            ocr_payload,
            canvas_width=normalized_size[0],
            canvas_height=normalized_size[1],
        )
        write_json(paths.ocr_boxes_json, ocr_payload)
        ocr_candidates = ocr_payload_to_candidates(ocr_payload, paths.figure_image)
        _release_runtime_if_supported(options.ocr_provider)
    else:
        ocr_candidates = ()

    if options.sam3_transport is not None:
        _release_runtime_if_supported(options.sam3_transport)
    if not paths.sam_boxes_by_prompt_json.exists():
        write_json(paths.sam_boxes_by_prompt_json, _sam_boxes_by_prompt(_EmptySamResult(sam_payload.get("raw_regions", []))))
    _write_parser_outputs(paths, sam_candidates, ocr_candidates)


def _sam_payload_for_parse(
    cfg: DrawAiPipelineConfig,
    paths: DrawAiArtifactPaths,
    options: V2StageOptions,
) -> dict[str, Any]:
    if not cfg.v2.parser.sam3_enabled:
        payload = {"raw_regions": [], "prompt_runs": []}
        write_json(paths.raw_regions_json, payload)
        return payload
    if paths.raw_regions_json.exists():
        return _read_json_file(paths.raw_regions_json, "SAM3 raw regions")
    should_skip_default_sam = cfg.ocr.provider == "fixture" and options.sam3_transport is None
    if should_skip_default_sam:
        payload = {"raw_regions": [], "prompt_runs": []}
        write_json(paths.raw_regions_json, payload)
        return payload

    sam3_result = run_sam3_prompt_plan(
        cfg.sam3,
        paths.figure_image,
        paths,
        transport=options.sam3_transport,
    )
    return {
        "raw_regions": list(sam3_result.raw_regions),
        "prompt_runs": [
            {
                "prompt_id": run.prompt_id,
                "artifact_path": str(run.artifact_path),
                "elapsed_ms": run.elapsed_ms,
            }
            for run in sam3_result.prompt_runs
        ],
    }


def _write_parser_outputs(
    paths: DrawAiArtifactPaths,
    sam_candidates: Sequence[ElementCandidate],
    ocr_candidates: Sequence[ElementCandidate],
) -> None:
    sam_payload = [candidate.to_dict() for candidate in sam_candidates]
    ocr_payload = [candidate.to_dict() for candidate in ocr_candidates]
    all_payload = [*sam_payload, *ocr_payload]
    write_json(paths.v2_parser_outputs_dir / "sam3_candidates.json", {"candidates": sam_payload})
    write_json(paths.v2_parser_outputs_dir / "ocr_candidates.json", {"candidates": ocr_payload})
    write_json(
        paths.v2_parser_outputs_dir / "element_candidates.json",
        {
            "schema": "drawai.v2.parser_outputs.v1",
            "candidate_count": len(all_payload),
            "candidates": all_payload,
        },
    )


def _read_parser_candidates(paths: DrawAiArtifactPaths) -> tuple[ElementCandidate, ...]:
    payload = _read_json_file(paths.v2_parser_outputs_dir / "element_candidates.json", "v2 parser outputs")
    raw_candidates = payload.get("candidates") if isinstance(payload, Mapping) else None
    if not isinstance(raw_candidates, list):
        raise ValueError("v2 parser outputs must contain a candidates list")
    return tuple(_candidate_from_payload(item) for item in raw_candidates)


def _candidate_from_payload(payload: Any) -> ElementCandidate:
    if not isinstance(payload, Mapping):
        raise ValueError("element candidate payload must be a mapping")
    return ElementCandidate(
        candidate_id=_required_string(payload, "candidate_id"),
        source_parser=_required_string(payload, "source_parser"),
        source_parser_version=_required_string(payload, "source_parser_version"),
        element_type=_required_string(payload, "element_type"),
        bbox=_bbox4(payload.get("bbox"), "candidate.bbox"),
        geometry=_mapping(payload.get("geometry"), "candidate.geometry"),
        confidence=float(payload.get("confidence")),
        z_hint=payload.get("z_hint") if isinstance(payload.get("z_hint"), int) else None,
        text=str(payload.get("text") or ""),
        evidence_files=tuple(str(item) for item in payload.get("evidence_files", ())),
        provenance=_mapping(payload.get("provenance"), "candidate.provenance"),
        raw_ref=_mapping(payload.get("raw_ref"), "candidate.raw_ref"),
    )


def _plans_with_candidate_text(
    plans: Sequence[ElementPlan],
    candidates: Sequence[ElementCandidate],
) -> tuple[ElementPlan, ...]:
    candidates_by_id = {candidate.candidate_id: candidate for candidate in candidates}
    updated: list[ElementPlan] = []
    for plan in plans:
        if plan.element_type != "text":
            updated.append(plan)
            continue
        text = next(
            (
                candidates_by_id[candidate_id].text
                for candidate_id in plan.source_candidate_ids
                if candidate_id in candidates_by_id and candidates_by_id[candidate_id].text
            ),
            "",
        )
        parameters = dict(plan.processing_intent.parameters)
        parameters["text"] = text
        updated.append(
            replace(
                plan,
                processing_intent=ProcessingIntent(
                    object_type=plan.processing_intent.object_type,
                    processing_type=plan.processing_intent.processing_type,
                    parameters=parameters,
                ),
            )
        )
    return tuple(updated)


def _asset_planned_element(cfg: DrawAiPipelineConfig, plan: ElementPlan) -> ElementPlan:
    processing_type = plan.processing_intent.processing_type
    if processing_type == "crop_nobg" and not cfg.asset_materialization.rmbg.enabled:
        processing_type = "crop"
    if processing_type == plan.processing_intent.processing_type:
        return plan
    return replace(
        plan,
        processing_intent=ProcessingIntent(
            object_type=plan.processing_intent.object_type,
            processing_type=processing_type,
            parameters=dict(plan.processing_intent.parameters),
        ),
        change_reason=f"{plan.change_reason} Processor planned as {processing_type}.",
    )


def _process_asset_packages(
    cfg: DrawAiPipelineConfig,
    paths: DrawAiArtifactPaths,
    plans: Sequence[ElementPlan],
    options: V2StageOptions,
) -> tuple[AssetPackage, ...]:
    if not cfg.v2.processor.enabled:
        packages = tuple(
            AssetPackage.empty(
                asset_id=_asset_id(plan),
                element_id=plan.element_id,
                processor_type=plan.processing_intent.processing_type,
            )
            for plan in plans
        )
        for package in packages:
            write_asset_package(paths.root, package)
        return packages

    providers = {
        "rmbg_client": options.rmbg_client or _default_rmbg_client_if_enabled(cfg),
        "image_generate": options.image_generate,
        "image_edit": options.image_edit,
    }
    if paths.v2_processor_trace_jsonl.exists():
        paths.v2_processor_trace_jsonl.unlink()
    packages: list[AssetPackage] = []
    for plan in plans:
        processor = processor_for_type(plan.processing_intent.processing_type, providers=providers)
        package = processor.process(paths.root, plan, source_image_path=paths.figure_image)
        packages.append(package)
        _append_jsonl(
            paths.v2_processor_trace_jsonl,
            {
                "schema": "drawai.v2.processor_trace_record.v1",
                "stage": "process_assets",
                "element_id": plan.element_id,
                "asset_id": package.asset_id,
                "processor_type": package.processor_type,
                "status": package.status,
                "created_at": utc_now(),
            },
        )
    return tuple(packages)


def _default_rmbg_client_if_enabled(cfg: DrawAiPipelineConfig) -> Any | None:
    if not cfg.asset_materialization.rmbg.enabled:
        return None
    from drawai.pipeline import _default_rmbg_client

    return _default_rmbg_client(cfg)


def _write_compat_outputs(paths: DrawAiArtifactPaths, plans: Sequence[ElementPlan]) -> None:
    _write_box_ir_compat_output(paths, plans)
    write_element_analysis_compat(paths.root, plans)


def _write_box_ir_compat_output(paths: DrawAiArtifactPaths, plans: Sequence[ElementPlan]) -> None:
    source_metadata = _read_json_file(paths.source_metadata, "source metadata")
    write_box_ir_compat(paths.root, plans, source_metadata)


def _refine_with_codex_analysis(
    paths: DrawAiArtifactPaths,
    plans: Sequence[ElementPlan],
    refine_config: RefineConfig,
) -> tuple[ElementPlan, ...]:
    if refine_config.provider != "codex_element_refiner":
        raise RuntimeError(f"Unsupported v2 refine provider: {refine_config.provider}")
    analysis = _read_external_refinement_analysis(paths)
    candidates = _read_parser_candidates(paths)
    expected_candidate_ids = {
        candidate_id
        for plan in plans
        for candidate_id in plan.source_candidate_ids
    }
    locked_geometry_by_candidate = {
        candidate.candidate_id: dict(candidate.geometry)
        for candidate in candidates
        if str(candidate.geometry.get("kind") or "").lower() == "mask"
    }
    return CodexElementRefiner(refine_config).convert_analysis(
        analysis,
        expected_candidate_ids=expected_candidate_ids,
        locked_geometry_by_candidate=locked_geometry_by_candidate,
    )


def _read_external_refinement_analysis(paths: DrawAiArtifactPaths) -> Mapping[str, Any]:
    if not paths.element_analysis_json.is_file():
        raise FileNotFoundError(
            "Codex element refinement analysis is required when v2.refine.enabled is true: "
            f"{paths.element_analysis_json}"
        )
    analysis = _read_json_file(paths.element_analysis_json, "Codex element refinement analysis")
    if not isinstance(analysis, Mapping):
        raise ValueError("Codex element refinement analysis must be a JSON object")
    source = str(analysis.get("source") or "")
    if source.startswith("v2."):
        raise FileNotFoundError(
            "Codex element refinement analysis is required when v2.refine.enabled is true; "
            f"{paths.element_analysis_json} is a v2-derived compatibility export, not a refinement artifact"
        )
    return analysis


def _write_element_plans(root: Path, plans: Sequence[ElementPlan]) -> None:
    for plan in plans:
        write_element_plan(root, plan)


def _read_element_plans(paths: DrawAiArtifactPaths) -> tuple[ElementPlan, ...]:
    payload = _read_json_file(paths.run_package_json, "v2 run package")
    raw_elements = payload.get("elements") if isinstance(payload, Mapping) else None
    if not isinstance(raw_elements, list):
        raise ValueError("v2 run package must contain an elements list")
    return tuple(_plan_from_payload(item) for item in raw_elements)


def _plan_from_payload(payload: Any) -> ElementPlan:
    if not isinstance(payload, Mapping):
        raise ValueError("element plan payload must be a mapping")
    intent_payload = _mapping(payload.get("processing_intent"), "processing_intent")
    return ElementPlan(
        element_id=_required_string(payload, "element_id"),
        source_candidate_ids=tuple(str(item) for item in payload.get("source_candidate_ids", ())),
        element_type=_required_string(payload, "element_type"),
        bbox=_bbox4(payload.get("bbox"), "element.bbox"),
        geometry=_mapping(payload.get("geometry"), "element.geometry"),
        z_order=int(payload.get("z_order", 0)),
        confidence=cast(Any, _required_string(payload, "confidence")),
        processing_intent=ProcessingIntent(
            object_type=str(intent_payload.get("object_type") or payload.get("element_type") or "unknown"),
            processing_type=str(intent_payload.get("processing_type") or "crop"),
            parameters=_mapping(intent_payload.get("parameters", {}), "processing_intent.parameters"),
        ),
        review_status=cast(Any, _required_string(payload, "review_status")),
        created_by_stage=_required_string(payload, "created_by_stage"),
        change_reason=_required_string(payload, "change_reason"),
    )


def _read_asset_packages(
    paths: DrawAiArtifactPaths,
    plans: Sequence[ElementPlan],
) -> tuple[AssetPackage, ...]:
    packages: list[AssetPackage] = []
    for plan in plans:
        package_path = paths.v2_elements_dir / plan.element_id / "asset_package.json"
        if package_path.is_file():
            packages.append(_asset_package_from_payload(_read_json_file(package_path, "v2 asset package")))
    return tuple(packages)


def _asset_package_from_payload(payload: Any) -> AssetPackage:
    if not isinstance(payload, Mapping):
        raise ValueError("asset package payload must be a mapping")
    return AssetPackage(
        asset_id=_required_string(payload, "asset_id"),
        element_id=_required_string(payload, "element_id"),
        processor_type=_required_string(payload, "processor_type"),
        status=cast(Any, _required_string(payload, "status")),
        files=tuple(str(item) for item in payload.get("files", ())),
        metadata=_mapping(payload.get("metadata", {}), "asset_package.metadata"),
        processor_runs=tuple(_mapping(item, "asset_package.processor_run") for item in payload.get("processor_runs", ())),
        all_results=tuple(_mapping(item, "asset_package.result") for item in payload.get("all_results", ())),
        active_result=(
            _mapping(payload["active_result"], "asset_package.active_result")
            if isinstance(payload.get("active_result"), Mapping)
            else None
        ),
        editable_payload=(
            _mapping(payload["editable_payload"], "asset_package.editable_payload")
            if isinstance(payload.get("editable_payload"), Mapping)
            else None
        ),
        failure=payload.get("failure") if isinstance(payload.get("failure"), str) else None,
        created_at=str(payload.get("created_at") or utc_now()),
    )


def _write_v2_package(
    paths: DrawAiArtifactPaths,
    cfg: DrawAiPipelineConfig,
    *,
    elements: Sequence[ElementPlan],
    asset_packages: Sequence[AssetPackage | Mapping[str, Any]] = (),
    stage: str,
) -> dict[str, Any]:
    source_metadata = _read_json_file(paths.source_metadata, "source metadata")
    canvas_width, canvas_height = _canvas_size(source_metadata)
    payload = {
        "schema": RUN_PACKAGE_SCHEMA,
        "run_id": paths.root.name,
        "root": str(paths.root),
        "source_image": str(paths.figure_image),
        "canvas": {"width": canvas_width, "height": canvas_height},
        "created_at": utc_now(),
        "metadata": {
            "config_path": str(cfg.config_path) if cfg.config_path is not None else None,
            "last_stage": stage,
            "v2_enabled": cfg.v2.enabled,
        },
        "elements": [element.to_dict() for element in elements],
        "asset_packages": [
            package.to_dict() if isinstance(package, AssetPackage) else dict(package)
            for package in asset_packages
        ],
    }
    write_json(paths.run_package_json, payload)
    return payload


def _write_semantic_svg(paths: DrawAiArtifactPaths, plans: Sequence[ElementPlan]) -> None:
    source_metadata = _read_json_file(paths.source_metadata, "source metadata")
    width, height = _canvas_size(source_metadata)
    body: list[str] = [f'<rect x="0" y="0" width="{width}" height="{height}" fill="white"/>']
    for plan in sorted(plans, key=lambda item: (item.z_order, item.element_id)):
        x, y, w, h = plan.bbox
        if plan.element_type == "text":
            text = html.escape(str(plan.processing_intent.parameters.get("text") or ""))
            body.append(
                f'<text x="{x:.2f}" y="{y + h:.2f}" font-size="{max(8.0, h):.2f}" fill="#111111">{text}</text>'
            )
        else:
            body.append(
                f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" '
                'fill="none" stroke="#1f5fbf" stroke-width="1.5"/>'
            )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}">\n  '
        + "\n  ".join(body)
        + "\n</svg>\n"
    )
    paths.semantic_svg.parent.mkdir(parents=True, exist_ok=True)
    paths.semantic_svg.write_text(svg, encoding="utf-8")


def _write_rendered_preview(paths: DrawAiArtifactPaths, plans: Sequence[ElementPlan]) -> None:
    source_metadata = _read_json_file(paths.source_metadata, "source metadata")
    width, height = _canvas_size(source_metadata)
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    for plan in sorted(plans, key=lambda item: (item.z_order, item.element_id)):
        x, y, w, h = plan.bbox
        if plan.element_type == "text":
            draw.text((x, y), str(plan.processing_intent.parameters.get("text") or ""), fill=(17, 17, 17))
        else:
            draw.rectangle((x, y, x + w, y + h), outline=(31, 95, 191), width=2)
    paths.rendered_png.parent.mkdir(parents=True, exist_ok=True)
    image.save(paths.rendered_png)


def _register_stage_outputs(
    store: ArtifactStore,
    paths: DrawAiArtifactPaths,
    stage_id: str,
) -> dict[str, ArtifactRef]:
    artifacts: dict[str, ArtifactRef] = {}
    for artifact_id, path_name in _STAGE_OUTPUT_PATHS[stage_id].items():
        path = _resolve_stage_output(paths, path_name)
        if path.is_dir():
            artifacts[artifact_id] = ArtifactRef(
                artifact_id=artifact_id,
                path=path,
                media_type="inode/directory",
            )
            continue
        artifacts[artifact_id] = store.register(artifact_id, path)
    return artifacts


def _resolve_stage_output(paths: DrawAiArtifactPaths, path_name: str) -> Path:
    return cast(Path, getattr(paths, path_name))


def _validate_stage_ids(stage_ids: tuple[str, ...]) -> None:
    if len(stage_ids) == 0:
        raise ValueError("at least one v2 stage is required")
    unknown = [stage_id for stage_id in stage_ids if stage_id not in V2_STAGE_ORDER]
    if unknown:
        raise ValueError(f"unknown v2 stage: {', '.join(unknown)}")


def _read_json_file(path: str | Path, label: str) -> Any:
    json_path = _require_path(path, label)
    with json_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _read_json_if_exists(path: str | Path, *, default: Any) -> Any:
    json_path = Path(path)
    if not json_path.exists():
        return default
    with json_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _require_path(path: str | Path, label: str) -> Path:
    required = Path(path)
    if not required.exists():
        raise FileNotFoundError(f"Required {label} file is missing: {required}")
    return required


def _canvas_size(source_metadata: Mapping[str, Any]) -> tuple[int, int]:
    raw_size = source_metadata.get("normalized_size")
    if not isinstance(raw_size, Sequence) or isinstance(raw_size, str) or len(raw_size) != 2:
        raise ValueError("source metadata must contain normalized_size [width, height]")
    width = int(raw_size[0])
    height = int(raw_size[1])
    if width <= 0 or height <= 0:
        raise ValueError("source metadata normalized_size must be positive")
    return width, height


def _bbox4(raw: Any, field_name: str) -> tuple[float, float, float, float]:
    if not isinstance(raw, Sequence) or isinstance(raw, str) or len(raw) != 4:
        raise ValueError(f"{field_name} must contain four numbers")
    return tuple(float(item) for item in raw)  # type: ignore[return-value]


def _mapping(raw: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ValueError(f"{field_name} must be a mapping")
    return dict(raw)


def _required_string(payload: Mapping[str, Any], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} is required")
    return value


def _asset_id(plan: ElementPlan) -> str:
    return f"A{plan.element_id.removeprefix('E')}"


def _append_jsonl(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(payload), ensure_ascii=False, sort_keys=True))
        handle.write("\n")


@dataclass(frozen=True)
class _EmptySamRun:
    prompt_id: str
    regions: tuple[Any, ...] = ()
    raw_regions: tuple[Any, ...] = ()
    artifact_path: str = ""
    elapsed_ms: float | None = None


@dataclass(frozen=True)
class _EmptySamResult:
    raw_regions: Sequence[Any]
    prompt_runs: tuple[_EmptySamRun, ...] = ()
