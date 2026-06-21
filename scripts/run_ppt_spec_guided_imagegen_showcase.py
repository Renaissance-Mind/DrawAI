#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from drawai.codex_python_sdk_imagegen import (  # noqa: E402
    invoke_codex_python_sdk_image_edit,
    invoke_codex_python_sdk_imagegen,
)


DEFAULT_OUTPUT_DIR = REPO_ROOT / "outputs" / "ppt_spec_guided_imagegen_showcase"
DEFAULT_TEMPLATE_SPEC = REPO_ROOT / "outputs" / "ppt_master_alignment_showcase" / "template_spec.json"
DEFAULT_SLOT_SCHEMA = REPO_ROOT / "outputs" / "ppt_master_alignment_showcase" / "slot_schema_preview.json"
DEFAULT_REFERENCE_STYLE_SPEC = REPO_ROOT / "outputs" / "ppt_master_alignment_showcase" / "reference_style_spec.json"
DEFAULT_TEMPLATE_ASSET = REPO_ROOT / "templates" / "slide_image" / "prisma_flow_diagram" / "template.json"
DEFAULT_SOURCE_IMAGE = Path(r"C:\Users\yanrupeng\AppData\Local\hermes\image_cache\img_3801f9a210be.jpg")


PAGE_CASES: list[dict[str, Any]] = [
    {
        "id": "cover_design_lock",
        "page_type": "cover",
        "operation": "generate",
        "selected_layout_role": "cover",
        "title": "DrawAI PPT 图像生成重构",
        "subtitle": "用模板 spec、slot schema 和 reference roles 锁定首图质量",
        "takeaway": "这不是 PPTX 输出，而是 PPT 图像生成阶段的结构化设计锁定",
        "layout_intent": "Use a polished executive cover page with a strong title block, one subtitle, three small capability badges, and visible design-lock annotations.",
        "slots_to_use": ["slot_cover_title", "slot_cover_subtitle", "slot_metric_1", "slot_metric_2", "slot_metric_3"],
        "visible_text": {
            "title": "DrawAI PPT 图像生成重构",
            "subtitle": "Template Spec + Slot Schema + Reference Roles",
            "badges": ["模板结构", "参考图角色", "设计锁定"],
            "footer": "PPT 图像生成，不是 PPTX 交付",
        },
    },
    {
        "id": "prisma_process_flow_edit",
        "page_type": "process_flow",
        "operation": "edit",
        "selected_layout_role": "process_or_timeline",
        "title": "DrawAI PPT 图像生成能力验证流程",
        "subtitle": "参考 PRISMA/systematic review 流程图布局，但替换为 DrawAI 生成链路",
        "takeaway": "LocalImageInput 参与生成：保留黄色顶栏、白底节点、箭头和左侧阶段标签",
        "layout_intent": "Use the supplied PRISMA screenshot as a layout reference. Preserve the flowchart grammar and replace all content with Chinese DrawAI workflow labels.",
        "slots_to_use": ["slot_flow_title", "slot_flow_step_1", "slot_flow_step_2", "slot_flow_step_3", "slot_flow_step_4", "slot_flow_note"],
        "visible_text": {
            "headers": ["输入与模板来源", "生成与质量验证"],
            "stage_labels": ["输入", "筛选", "生成", "验证", "重建"],
            "nodes": [
                "用户输入：PPT 类型、主题、语言、文字密度",
                "读取模板资产：design_tokens、slot_schema、reference_images",
                "候选策略：template_id、source_mode、style lock",
                "参考图输入：LocalImageInput / Codex edit",
                "PPT 图像生成：中文标题、流程框、箭头与说明",
                "质量检查：文字可读、事实不编造、布局不混乱",
                "进入 DrawAI：元素识别、分层、可编辑重建",
                "输出记录：payload、prompt、record、contact sheet",
            ],
            "checks": ["禁止复制原图数字", "禁止伪造来源", "检查 operation=edit"],
        },
    },
    {
        "id": "data_evidence_spec",
        "page_type": "data_evidence",
        "operation": "generate",
        "selected_layout_role": "data_page",
        "title": "结构化输入如何降低幻觉",
        "subtitle": "只展示给定事实清单和示例数据，不生成未提供指标",
        "takeaway": "模板槽位约束页面结构，数据源约束图表内容，reference roles 约束视觉语言",
        "layout_intent": "Use the data-page layout: title at top, table/chart evidence in the middle, right-side explanation cards, and a small source note.",
        "slots_to_use": ["slot_data_title", "native_table_capability_matrix", "native_chart_phase_coverage", "slot_data_caption"],
        "data_sources": [
            {"input": "prompt only", "risk": 5, "control": "无结构约束"},
            {"input": "template_spec", "risk": 3, "control": "锁定画布/槽位"},
            {"input": "reference_style_spec", "risk": 2, "control": "锁定布局/颜色角色"},
            {"input": "claims + data_sources", "risk": 1, "control": "禁止未给定数字"},
        ],
        "visible_text": {
            "title": "结构化输入如何降低幻觉",
            "labels": ["输入层", "风险", "控制方式", "证据页", "只用给定数据"],
            "source_note": "示例数据仅用于流程验证，不代表真实产品指标",
        },
    },
    {
        "id": "comparison_template_vs_prompt",
        "page_type": "comparison",
        "operation": "generate",
        "selected_layout_role": "content",
        "title": "Prompt-only 与 Spec-guided 的差异",
        "subtitle": "同样生成 PPT 图像，但约束粒度完全不同",
        "takeaway": "Spec-guided 不是更长的 prompt，而是把模板结构、槽位和参考图角色显式注入图像生成",
        "layout_intent": "Create a clean comparison slide with two columns: prompt-only vs spec-guided. Use callout cards and a bottom decision row.",
        "slots_to_use": ["slot_content_title", "slot_card_1", "slot_card_2", "slot_card_3", "slot_content_caption"],
        "visible_text": {
            "title": "Prompt-only vs Spec-guided",
            "left_header": "Prompt-only",
            "right_header": "Spec-guided",
            "left_points": ["容易风格漂移", "布局靠模型猜", "参考图只在文字里描述"],
            "right_points": ["slot_schema 锁定结构", "design_tokens 锁定视觉", "LocalImageInput 真实参与"],
            "decision": "当前主线：先生成高质量 PPT 图像，再进入 DrawAI 可编辑重建",
        },
    },
    {
        "id": "summary_reference_roles_edit",
        "page_type": "summary",
        "operation": "edit",
        "selected_layout_role": "process_or_timeline",
        "title": "Reference Roles 如何驱动一页 PPT 图像",
        "subtitle": "同一张参考图被拆成 layout/style/color/typography/content 五类作用",
        "takeaway": "不是照抄参考图，而是复用流程图语法并替换业务内容",
        "layout_intent": "Use the supplied PRISMA reference as the structural base, but turn it into a summary map of the five reference roles.",
        "slots_to_use": ["layout_reference", "style_reference", "color_reference", "typography_reference", "content_reference"],
        "visible_text": {
            "headers": ["Reference Roles", "PPT 图像生成约束"],
            "stage_labels": ["布局", "风格", "颜色", "字体", "内容"],
            "nodes": [
                "layout_reference：两列流程、左侧阶段标签、箭头拓扑",
                "style_reference：学术流程图、白底、细线框",
                "color_reference：黄色顶栏、浅蓝阶段条、黑色箭头",
                "typography_reference：紧凑中文标签、节点可读",
                "content_reference：只借流程语法，不复制原始研究数字",
                "生成目标：高质量 PPT 页面 PNG",
                "后续：DrawAI 识别元素并重建为可编辑结构",
            ],
            "checks": ["不复制原文", "不伪造数据", "保持 PPT 页面感"],
        },
    },
]


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.resolve(strict=False)
    if args.force and output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    source_image = args.source_image.expanduser().resolve(strict=False)
    if not source_image.is_file():
        raise FileNotFoundError(f"reference source image does not exist: {source_image}")
    source_copy = output_dir / "source_reference.jpg"
    shutil.copy2(source_image, source_copy)

    inputs = load_structured_inputs(
        template_spec_path=args.template_spec,
        slot_schema_path=args.slot_schema,
        reference_style_spec_path=args.reference_style_spec,
        template_asset_path=args.template_asset,
    )
    runtime_config: dict[str, Any] = {
        "timeout_seconds": args.timeout_seconds,
        "reasoning_effort": args.reasoning_effort,
    }
    if args.model:
        runtime_config["model_name"] = args.model

    selected_cases = PAGE_CASES[: args.limit] if args.limit else PAGE_CASES
    report: dict[str, Any] = {
        "schema": "drawai.ppt_spec_guided_imagegen_showcase.summary.v1",
        "status": "running",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "output_dir": str(output_dir),
        "contact_sheet": "",
        "source_image_path": str(source_copy),
        "original_source_image_path": str(source_image),
        "statement": {
            "delivery": "PPT slide images as PNG files, not PPTX output.",
            "ppt_master_usage": "PPT-master is used as an architectural idea: template/spec/slot/design lock for image generation.",
            "not_prompt_only": "Prompts are built from template_spec, slot_schema_preview, reference_style_spec, template asset roles, and user page goals.",
        },
        "input_assets": _input_asset_paths(args, source_copy=source_copy),
        "case_count": len(selected_cases),
        "cases": [],
    }
    _write_json(output_dir / "summary.json", report)

    blocked_reason = ""
    started_at = time.time()
    for index, case in enumerate(selected_cases, start=1):
        case_dir = output_dir / f"{index:02d}_{case['id']}"
        existing = None if args.force else _load_existing_record(case_dir)
        if existing and _first_image_path(existing):
            record = existing
        else:
            record = write_prompt_record(
                case,
                case_dir=case_dir,
                inputs=inputs,
                source_copy=source_copy,
                original_source_image=source_image,
            )
            if not args.prompt_only and not blocked_reason:
                try:
                    record = run_case(
                        case,
                        case_dir=case_dir,
                        runtime_config=runtime_config,
                        source_copy=source_copy,
                        original_source_image=source_image,
                    )
                except Exception as exc:  # noqa: BLE001 - preserve prompt/payload on imagegen blocker.
                    blocked_reason = repr(exc)
                    record["status"] = "blocked"
                    record["blocked_reason"] = blocked_reason
                    _write_json(case_dir / "record.json", record)
            elif blocked_reason:
                record["status"] = "prompt_only"
                record["blocked_reason"] = blocked_reason
                _write_json(case_dir / "record.json", record)
        report["cases"].append(_case_summary(record))
        _write_json(output_dir / "summary.json", report)

    completed_records = [_load_existing_record(output_dir / f"{i:02d}_{case['id']}") for i, case in enumerate(selected_cases, start=1)]
    completed_records = [record for record in completed_records if record]
    if any(_first_image_path(record) for record in completed_records):
        report["contact_sheet"] = str(_write_contact_sheet(output_dir, completed_records))
    report["status"] = "blocked" if blocked_reason else "ok"
    report["blocked_reason"] = blocked_reason
    report["elapsed_seconds"] = round(time.time() - started_at, 3)
    report["cases"] = [_case_summary(record) for record in completed_records]
    report["quality_review"] = _build_quality_review(completed_records)
    _write_json(output_dir / "summary.json", report)
    _write_summary_md(output_dir, report)
    print(json.dumps(_compact_summary(report), ensure_ascii=False, indent=2))
    return 2 if blocked_reason and not any(case.get("status") == "ok" for case in report["cases"]) else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate PPT slide PNGs using PPT-master-style specs and design locks.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--template-spec", type=Path, default=DEFAULT_TEMPLATE_SPEC)
    parser.add_argument("--slot-schema", type=Path, default=DEFAULT_SLOT_SCHEMA)
    parser.add_argument("--reference-style-spec", type=Path, default=DEFAULT_REFERENCE_STYLE_SPEC)
    parser.add_argument("--template-asset", type=Path, default=DEFAULT_TEMPLATE_ASSET)
    parser.add_argument("--source-image", type=Path, default=DEFAULT_SOURCE_IMAGE)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--model", default="")
    parser.add_argument("--reasoning-effort", default="low", choices=["none", "minimal", "low", "medium", "high", "xhigh"])
    parser.add_argument("--timeout-seconds", type=float, default=540.0)
    parser.add_argument("--prompt-only", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def load_structured_inputs(
    *,
    template_spec_path: Path,
    slot_schema_path: Path,
    reference_style_spec_path: Path,
    template_asset_path: Path,
) -> dict[str, Any]:
    return {
        "template_spec_path": str(template_spec_path.resolve(strict=False)),
        "slot_schema_path": str(slot_schema_path.resolve(strict=False)),
        "reference_style_spec_path": str(reference_style_spec_path.resolve(strict=False)),
        "template_asset_path": str(template_asset_path.resolve(strict=False)),
        "template_spec": _read_json(template_spec_path),
        "slot_schema": _read_json(slot_schema_path),
        "reference_style_spec": _read_json(reference_style_spec_path),
        "template_asset": _read_json(template_asset_path),
    }


def build_case_payload(
    case: Mapping[str, Any],
    *,
    inputs: Mapping[str, Any],
    source_copy: Path,
    original_source_image: Path,
) -> dict[str, Any]:
    template_spec = inputs["template_spec"]
    slot_schema = inputs["slot_schema"]
    reference_style_spec = inputs["reference_style_spec"]
    template_asset = inputs["template_asset"]
    selected_layout = _select_layout(template_spec, str(case["selected_layout_role"]))
    selected_slots = _select_slots(slot_schema, case.get("slots_to_use") or [], selected_layout.get("slide_index"))
    reference_roles = _reference_roles(reference_style_spec)
    operation = str(case["operation"])
    payload = {
        "schema": "drawai.ppt_spec_guided_imagegen.case_payload.v1",
        "provider": "codex",
        "operation": operation,
        "page_type": case["page_type"],
        "case_id": case["id"],
        "output_format": "png",
        "size": "2048x1152",
        "quality": "high",
        "rendering_mode": "baked_text",
        "user_topic": case["title"],
        "source_image_path": str(source_copy) if operation == "edit" else "",
        "original_source_image_path": str(original_source_image) if operation == "edit" else "",
        "uses_local_image_input": operation == "edit",
        "input_assets": {
            "template_spec_path": inputs["template_spec_path"],
            "slot_schema_path": inputs["slot_schema_path"],
            "reference_style_spec_path": inputs["reference_style_spec_path"],
            "template_asset_path": inputs["template_asset_path"],
            "source_reference_path": str(source_copy),
        },
        "from_template_spec": {
            "schema": template_spec.get("schema"),
            "source_pptx": template_spec.get("source_pptx"),
            "slide_size": template_spec.get("slide_size", {}),
            "selected_layout": selected_layout,
            "design_tokens": template_spec.get("design_tokens", {}),
            "spec_lock": template_spec.get("spec_lock", {}),
        },
        "from_slot_schema": {
            "selected_slots": selected_slots,
            "slot_policy": {
                "use_slot_geometry_as_layout_hint": True,
                "keep_text_inside_slot_regions": True,
                "prefer_named_slots_from_demo_template": True,
                "do_not_generate_empty_placeholder_layout": True,
            },
        },
        "from_reference_style_spec": {
            "schema": reference_style_spec.get("schema"),
            "source_image_path": reference_style_spec.get("source_image_path"),
            "reference_roles": reference_roles,
            "design_tokens": reference_style_spec.get("design_tokens", {}),
            "spec_lock": reference_style_spec.get("spec_lock", {}),
        },
        "from_template_asset": {
            "id": template_asset.get("id"),
            "design_tokens": template_asset.get("design_tokens", {}),
            "layout": template_asset.get("layout", {}),
            "slot_schema": template_asset.get("slot_schema", {}),
            "reference_roles": template_asset.get("reference_roles", []),
        },
        "from_user_page_goal": {
            "title": case["title"],
            "subtitle": case["subtitle"],
            "takeaway": case["takeaway"],
            "layout_intent": case["layout_intent"],
            "visible_text": case["visible_text"],
            "data_sources": case.get("data_sources", []),
        },
        "quality_gates": {
            "must_be_ppt_slide_image": True,
            "must_not_output_pptx": True,
            "chinese_first_visible_text": True,
            "avoid_random_english": True,
            "avoid_fake_numbers_or_sources": True,
            "keep_16_9_slide_composition": True,
            "for_edit_cases_use_local_image_input": operation == "edit",
        },
    }
    payload["prompt"] = build_image_prompt(payload)
    return payload


def build_image_prompt(payload: Mapping[str, Any]) -> str:
    operation = payload["operation"]
    reference_note = (
        "The supplied image is a real LocalImageInput. Use it as a layout/style reference, not as copied content."
        if operation == "edit"
        else "No bitmap input is supplied for this case. Use the structured specs as the design lock."
    )
    compact_spec = {
        "page_type": payload["page_type"],
        "operation": operation,
        "from_template_spec": {
            "slide_size": payload["from_template_spec"]["slide_size"],
            "selected_layout": payload["from_template_spec"]["selected_layout"],
            "design_tokens": payload["from_template_spec"]["design_tokens"],
            "spec_lock": payload["from_template_spec"]["spec_lock"],
        },
        "from_slot_schema": payload["from_slot_schema"],
        "from_reference_style_spec": {
            "reference_roles": payload["from_reference_style_spec"]["reference_roles"],
            "design_tokens": payload["from_reference_style_spec"]["design_tokens"],
            "spec_lock": payload["from_reference_style_spec"]["spec_lock"],
        },
        "from_user_page_goal": payload["from_user_page_goal"],
        "quality_gates": payload["quality_gates"],
    }
    return f"""DrawAI PPT spec-guided image generation.

Delivery target:
- Generate one 16:9 PNG PPT slide image.
- This is NOT a PPTX file and NOT a native editable PowerPoint export.
- PPT-master is used only as an idea: template/spec/slot/design lock drives the image-generation prompt.

Execution:
- operation: {operation}
- provider: codex
- page_type: {payload['page_type']}
- {reference_note}

Structured input contract:
{json.dumps(compact_spec, ensure_ascii=False, indent=2)}

Rendering rules:
- The result must look like a polished PPT page, with clear hierarchy, slide margins, readable blocks, and intentional layout.
- Use Chinese-first visible text. Avoid random English headers unless explicitly present in the supplied text.
- Use the selected slots as layout anchors: title/subtitle/card/process/data/caption regions should visibly correspond to the slot schema.
- Use design_tokens/spec_lock as visual constraints: canvas ratio, template role, color family, geometry discipline, and reference roles.
- Do not invent facts, dates, citations, percentages, benchmarks, product claims, or source names not supplied in the structured input.
- For PRISMA-style edit cases: preserve the yellow top bars, white rectangular nodes, black arrows, pale-blue left stage labels, and systematic-review flow grammar, while replacing all original content.
- For text-to-image cases: produce a complete PPT slide, not a decorative background or empty wireframe.
- No fake logos, no watermarks, no tiny unreadable microtext, no copied protected designs.

Final response contract: reply only {{"generated": true}} for generate or {{"edited": true}} for edit."""


def write_prompt_record(
    case: Mapping[str, Any],
    *,
    case_dir: Path,
    inputs: Mapping[str, Any],
    source_copy: Path,
    original_source_image: Path,
) -> dict[str, Any]:
    case_dir.mkdir(parents=True, exist_ok=True)
    payload = build_case_payload(case, inputs=inputs, source_copy=source_copy, original_source_image=original_source_image)
    prompt = str(payload["prompt"])
    _write_json(case_dir / "payload.json", payload)
    (case_dir / "prompt.txt").write_text(prompt + "\n", encoding="utf-8")
    record = {
        "schema": "drawai.ppt_spec_guided_imagegen.case_record.v1",
        "case_id": case["id"],
        "page_type": case["page_type"],
        "operation": case["operation"],
        "status": "prompt_only",
        "case_dir": str(case_dir),
        "payload_path": str(case_dir / "payload.json"),
        "prompt_path": str(case_dir / "prompt.txt"),
        "image_path": "",
        "source_image_path": payload.get("source_image_path", ""),
        "original_source_image_path": payload.get("original_source_image_path", ""),
        "uses_local_image_input": bool(payload.get("uses_local_image_input")),
        "slots_used": [slot.get("slot_id") or slot.get("name") for slot in payload["from_slot_schema"]["selected_slots"]],
        "design_tokens_used": list((payload["from_template_spec"].get("design_tokens") or {}).keys()),
        "reference_roles_used": [role.get("role") for role in payload["from_reference_style_spec"]["reference_roles"]],
        "generation": None,
        "quality_notes": [],
    }
    _write_json(case_dir / "record.json", record)
    return record


def run_case(
    case: Mapping[str, Any],
    *,
    case_dir: Path,
    runtime_config: Mapping[str, Any],
    source_copy: Path,
    original_source_image: Path,
) -> dict[str, Any]:
    record = _load_existing_record(case_dir)
    if record is None:
        raise RuntimeError(f"record missing before generation: {case_dir}")
    prompt = (case_dir / "prompt.txt").read_text(encoding="utf-8")
    operation = str(case["operation"])
    if operation == "edit":
        result = invoke_codex_python_sdk_image_edit(
            source_image_path=source_copy,
            prompt=prompt,
            output_dir=case_dir / "generated",
            task_name="drawai.experiment.ppt_spec_guided_imagegen_showcase.edit.v1",
            output_stem=f"{case['id']}",
            runtime_config=runtime_config,
            trace_path=case_dir / "trace.jsonl",
            isolated_cwd=case_dir / "codex_cwd",
        )
    else:
        result = invoke_codex_python_sdk_imagegen(
            prompt=prompt,
            output_dir=case_dir / "generated",
            task_name="drawai.experiment.ppt_spec_guided_imagegen_showcase.generate.v1",
            output_stem=f"{case['id']}",
            runtime_config=runtime_config,
            trace_path=case_dir / "trace.jsonl",
            isolated_cwd=case_dir / "codex_cwd",
        )
    first = result.images[0] if result.images else None
    if first is None:
        raise RuntimeError(f"{case['id']} returned no image")
    image_path = _copy_png(Path(first.path), case_dir / f"{case['id']}.png")
    record.update(
        {
            "status": "ok",
            "image_path": str(image_path),
            "operation": result.operation,
            "source_image_path": str(result.source_image_path) if result.source_image_path else "",
            "original_source_image_path": str(original_source_image) if operation == "edit" else "",
            "uses_local_image_input": operation == "edit",
            "generation": result.to_dict(),
            "quality_notes": _basic_image_notes(image_path),
        }
    )
    _write_json(case_dir / "record.json", record)
    return record


def _select_layout(template_spec: Mapping[str, Any], role: str) -> dict[str, Any]:
    layouts = [dict(item) for item in template_spec.get("layouts", [])]
    for layout in layouts:
        if layout.get("role_guess") == role:
            return {
                "id": layout.get("id"),
                "name": layout.get("name"),
                "slide_index": layout.get("slide_index"),
                "role_guess": layout.get("role_guess"),
                "slot_summary": layout.get("slot_summary", {}),
            }
    return {
        "id": layouts[0].get("id") if layouts else "",
        "name": layouts[0].get("name") if layouts else "",
        "slide_index": layouts[0].get("slide_index") if layouts else None,
        "role_guess": layouts[0].get("role_guess") if layouts else "",
        "slot_summary": layouts[0].get("slot_summary", {}) if layouts else {},
    }


def _select_slots(slot_schema: Mapping[str, Any], requested: list[str], slide_index: int | None) -> list[dict[str, Any]]:
    layouts = slot_schema.get("layouts", [])
    candidates: list[dict[str, Any]] = []
    for layout in layouts:
        if slide_index is None or layout.get("slide_index") == slide_index:
            candidates.extend(dict(slot) for slot in layout.get("slots", []))
            candidates.extend(dict(table) | {"kind": "table"} for table in layout.get("tables", []))
            candidates.extend(dict(chart) | {"kind": "chart"} for chart in layout.get("charts", []))
    if not requested:
        return candidates[:8]
    selected: list[dict[str, Any]] = []
    for key in requested:
        key_lower = str(key).lower()
        for slot in candidates:
            slot_text = " ".join(str(slot.get(field, "")) for field in ("slot_id", "name", "table_id", "chart_id", "role")).lower()
            if key_lower in slot_text and slot not in selected:
                selected.append(slot)
                break
    if not selected:
        selected = candidates[:8]
    return selected[:10]


def _reference_roles(reference_style_spec: Mapping[str, Any]) -> list[dict[str, Any]]:
    roles = []
    for item in reference_style_spec.get("reference_roles", []):
        roles.append(
            {
                "role": item.get("role"),
                "weight": item.get("weight"),
                "locked_features": item.get("locked_features", []),
                "forbidden_copy": item.get("forbidden_copy", []),
            }
        )
    return roles


def _copy_png(source: Path, target: Path) -> Path:
    Image, _, _ = _pil()
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.suffix.lower() == ".png":
        shutil.copy2(source, target)
        return target
    with Image.open(source) as image:
        image.save(target)
    return target


def _basic_image_notes(path: Path) -> list[str]:
    notes: list[str] = []
    if not path.is_file():
        return ["missing PNG"]
    Image, _, _ = _pil()
    with Image.open(path) as image:
        ratio = image.width / max(1, image.height)
        if image.width < 1200 or image.height < 675:
            notes.append(f"resolution below expected slide draft: {image.width}x{image.height}")
        if ratio < 1.55 or ratio > 1.9:
            notes.append(f"aspect ratio may not be 16:9: {image.width}x{image.height}")
    return notes


def _write_contact_sheet(output_dir: Path, records: list[dict[str, Any]]) -> Path:
    Image, ImageDraw, _ = _pil()
    thumb_w = 620
    thumb_h = 349
    label_h = 76
    margin = 20
    cols = 2
    rows = (len(records) + cols - 1) // cols
    width = margin * (cols + 1) + cols * thumb_w
    height = margin + rows * (label_h + thumb_h + margin)
    sheet = Image.new("RGB", (width, height), (246, 247, 249))
    draw = ImageDraw.Draw(sheet)
    font = _font(20)
    small = _font(15)
    for index, record in enumerate(records):
        row = index // cols
        col = index % cols
        x = margin + col * (thumb_w + margin)
        y = margin + row * (label_h + thumb_h + margin)
        draw.text((x, y), f"{record['page_type']} / {record['operation']}", fill=(15, 23, 42), font=font)
        draw.text((x, y + 28), f"{record['case_id']} / {record['status']}", fill=(71, 85, 105), font=small)
        draw.text((x, y + 50), "LocalImageInput" if record.get("uses_local_image_input") else "spec-guided text-to-image", fill=(37, 99, 235), font=small)
        _paste_thumb(sheet, _first_image_path(record), x, y + label_h, thumb_w, thumb_h)
    path = output_dir / "contact_sheet.jpg"
    sheet.save(path, quality=92)
    return path


def _paste_thumb(sheet: Any, path: Path | None, x: int, y: int, width: int, height: int) -> None:
    Image, ImageDraw, _ = _pil()
    draw = ImageDraw.Draw(sheet)
    draw.rounded_rectangle((x, y, x + width, y + height), radius=8, fill=(226, 232, 240), outline=(203, 213, 225))
    if path is None:
        draw.text((x + 20, y + 20), "missing image", fill=(148, 27, 27), font=_font(20))
        return
    with Image.open(path) as image:
        image = image.convert("RGB")
        image.thumbnail((width, height), Image.Resampling.LANCZOS)
        ox = x + (width - image.width) // 2
        oy = y + (height - image.height) // 2
        sheet.paste(image, (ox, oy))


def _case_summary(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "case_id": record.get("case_id"),
        "page_type": record.get("page_type"),
        "operation": record.get("operation"),
        "status": record.get("status"),
        "image_path": record.get("image_path", ""),
        "payload_path": record.get("payload_path", ""),
        "prompt_path": record.get("prompt_path", ""),
        "record_path": str(Path(str(record.get("case_dir", ""))) / "record.json") if record.get("case_dir") else "",
        "source_image_path": record.get("source_image_path", ""),
        "uses_local_image_input": record.get("uses_local_image_input", False),
        "slots_used": record.get("slots_used", []),
        "design_tokens_used": record.get("design_tokens_used", []),
        "reference_roles_used": record.get("reference_roles_used", []),
        "quality_notes": record.get("quality_notes", []),
        "blocked_reason": record.get("blocked_reason", ""),
    }


def _build_quality_review(records: list[dict[str, Any]]) -> dict[str, Any]:
    ok_records = [record for record in records if record.get("status") == "ok"]
    edit_records = [record for record in ok_records if record.get("operation") == "edit"]
    return {
        "script_check": {
            "png_count": len(ok_records),
            "edit_png_count": len(edit_records),
            "all_ok_have_png": all(_first_image_path(record) is not None for record in ok_records),
            "edit_records_use_local_image_input": all(record.get("uses_local_image_input") for record in edit_records),
        },
        "manual_review_targets": [
            "PPT 页面感是否明确",
            "多页是否共享模板感和结构语言",
            "PRISMA edit 页是否保留黄色顶栏、白底节点、箭头和左侧阶段标签",
            "中文是否可读，是否避免随机英文标题",
            "是否比 prompt-only 更像受模板/spec 约束的页面",
        ],
    }


def _write_summary_md(output_dir: Path, report: Mapping[str, Any]) -> None:
    lines = [
        "# PPT Spec-guided Imagegen Showcase",
        "",
        "这轮交付是 PPT 页面图像 PNG，不是 PPTX 输出。PPT-master 只用于借鉴 template/spec/slot/design lock 思想，用结构化输入提高图像生成阶段的模板感、参考图能力和风格一致性。",
        "",
        f"- Status: {report.get('status')}",
        f"- Output dir: `{report.get('output_dir')}`",
        f"- Contact sheet: `{report.get('contact_sheet', '')}`",
        f"- Reference image: `{report.get('source_image_path', '')}`",
        "",
        "| Case | Page type | Operation | LocalImageInput | Image | What it verifies |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    descriptions = {
        "cover_design_lock": "template_spec/slot_schema 可以约束封面结构和模板感",
        "prisma_process_flow_edit": "真实参考图 edit，验证 PRISMA 流程布局参与生成",
        "data_evidence_spec": "data/page slots + claims/data_sources 约束图表与事实",
        "comparison_template_vs_prompt": "比较 prompt-only 与 spec-guided 的结构差异",
        "summary_reference_roles_edit": "真实参考图 edit，验证 reference roles 可驱动总结页",
    }
    for case in report.get("cases", []):
        lines.append(
            "| {case_id} | {page_type} | {operation} | {local} | `{image}` | {desc} |".format(
                case_id=case.get("case_id", ""),
                page_type=case.get("page_type", ""),
                operation=case.get("operation", ""),
                local="yes" if case.get("uses_local_image_input") else "no",
                image=case.get("image_path", ""),
                desc=descriptions.get(str(case.get("case_id")), ""),
            )
        )
    lines.extend(
        [
            "",
            "## Structured Inputs Used",
            f"- template_spec: `{report.get('input_assets', {}).get('template_spec_path', '')}`",
            f"- slot_schema_preview: `{report.get('input_assets', {}).get('slot_schema_path', '')}`",
            f"- reference_style_spec: `{report.get('input_assets', {}).get('reference_style_spec_path', '')}`",
            f"- template_asset: `{report.get('input_assets', {}).get('template_asset_path', '')}`",
            "",
            "## Current Limits",
            "- 图像模型仍可能把少量中文渲染得不够准，后续需要 OCR/视觉检查闭环和针对性重试。",
            "- 当前是 spec-guided prompt + LocalImageInput，不是自动从任意 PPTX 提取完整视觉系统后批量稳定生成。",
            "- text-to-image 页没有 bitmap 参考图，主要依赖 template_spec/slot_schema/reference_style_spec 的结构化摘要。",
        ]
    )
    (output_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _compact_summary(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": report.get("status"),
        "output_dir": report.get("output_dir"),
        "contact_sheet": report.get("contact_sheet", ""),
        "case_count": report.get("case_count"),
        "ok_cases": sum(1 for case in report.get("cases", []) if case.get("status") == "ok"),
        "edit_cases": [case.get("case_id") for case in report.get("cases", []) if case.get("operation") == "edit"],
        "blocked_reason": report.get("blocked_reason", ""),
    }


def _input_asset_paths(args: argparse.Namespace, *, source_copy: Path) -> dict[str, str]:
    return {
        "template_spec_path": str(args.template_spec.resolve(strict=False)),
        "slot_schema_path": str(args.slot_schema.resolve(strict=False)),
        "reference_style_spec_path": str(args.reference_style_spec.resolve(strict=False)),
        "template_asset_path": str(args.template_asset.resolve(strict=False)),
        "source_reference_path": str(source_copy.resolve(strict=False)),
    }


def _load_existing_record(case_dir: Path) -> dict[str, Any] | None:
    path = case_dir / "record.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _first_image_path(record: Mapping[str, Any]) -> Path | None:
    direct = Path(str(record.get("image_path") or ""))
    if direct.is_file():
        return direct
    generation = record.get("generation") or {}
    if isinstance(generation, Mapping):
        for image in generation.get("images", []):
            path = Path(str(image.get("path") or ""))
            if path.is_file():
                return path
    return None


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"required JSON input does not exist: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON input must be an object: {path}")
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _font(size: int) -> Any:
    _, _, ImageFont = _pil()
    for candidate in ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf", "C:/Windows/Fonts/arial.ttf"):
        path = Path(candidate)
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _pil() -> tuple[Any, Any, Any]:
    from PIL import Image, ImageDraw, ImageFont

    return Image, ImageDraw, ImageFont


if __name__ == "__main__":
    raise SystemExit(main())
