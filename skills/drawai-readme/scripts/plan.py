"""Resolve DrawAI's stages, conversion mode and only the missing intake questions."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

POLICY_PATH = Path(__file__).resolve().parents[1] / "references/model-policy.json"
MODE_LABELS = {"skill": "Skill：在当前会话按图像重建、制作和检查 PPT", "flow": "DrawAI-Flow：提交 Workbench，由工作台流程解析、重建和导出"}


def identify_model(name):
    if not name:
        return None
    normalized = name.lower().replace("_", "-")
    patterns = [
        ("gpt", r"(?:^|[/ :])gpt[ -]?(\d+)(?:[.](\d+)|-(\d{1,2})(?:-|$))?"),
        ("claude", r"(?:^|[/ :])claude(?:[ -](?:opus|sonnet|haiku))?[ -]?(\d+)(?:[.](\d+)|-(\d{1,2})(?:-|$))?"),
        ("deepseek-flash", r"(?:^|[/ :])deepseek[ -]?(?:flash[ -]?)?v?(\d+)(?:[.](\d+)|-(\d{1,2})(?:-|$))?"),
    ]
    for family, pattern in patterns:
        if family == "deepseek-flash" and "flash" not in normalized:
            continue
        match = re.search(pattern, normalized)
        if match:
            version = [int(match[1]), int(match[2] or match[3] or 0)]
            return {"family": family, "version": version}
    return None


def boolean_fact(environment, key):
    value = environment.get(key)
    if value is not None and not isinstance(value, bool):
        raise ValueError(f"environment.{key} must be boolean or null")
    return value


def create_plan(request):
    environment = request.get("environment", {})
    preferences = request.get("preferences", {})
    inputs = request.get("inputs", {})
    policy = json.loads(POLICY_PATH.read_text())
    source = environment.get("model_source", "unknown")
    if source not in {"session_metadata", "host_display", "user", "unknown"}:
        raise ValueError("model_source must describe the current session, not a global default")
    model = environment.get("model")
    if model is not None and not isinstance(model, str):
        raise ValueError("environment.model must be a string or null")
    identified = identify_model(model) if source != "unknown" else None
    eligible = bool(identified and any(
        item["family"] == identified["family"] and tuple(identified["version"]) >= tuple(item["minimum_version"])
        for item in policy["session_families"]
    ))
    imagegen = boolean_fact(environment, "image_generation_available")
    view_images = boolean_fact(environment, "image_viewing_available")
    execute = boolean_fact(environment, "local_execution_available")
    flow_available = boolean_fact(environment, "flow_available")
    recommended = "skill" if eligible and view_images is True and execute is True else policy["default_mode"]
    requested = preferences.get("mode", "auto")
    if requested not in {"auto", "skill", "flow"}:
        raise ValueError("preferences.mode must be auto, skill or flow")
    mode = requested if requested != "auto" else recommended
    mode_source = "user" if requested != "auto" else "model_and_capabilities"
    count = inputs.get("visual_page_count", 0)
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise ValueError("visual_page_count must be a non-negative integer")
    pages = preferences.get("page_count")
    if pages is not None and (isinstance(pages, bool) or not isinstance(pages, int) or pages <= 0):
        raise ValueError("page_count must be a positive integer")
    if count and pages is not None and pages != count:
        raise ValueError("page_count differs from provided visual pages; resolve which pages to use")
    ratio = preferences.get("aspect_ratio") or inputs.get("visual_aspect_ratio")
    if ratio is not None and (not isinstance(ratio, str) or not re.fullmatch(r"[1-9]\d*:[1-9]\d*", ratio)):
        raise ValueError("aspect_ratio must be a positive width:height ratio")
    reference = preferences.get("reference")
    if reference not in {None, "project", "provided", "library", "none"}:
        raise ValueError("reference must be project, provided, library or none")
    if reference is None:
        if inputs.get("pptx_templates"):
            reference = "project"
        elif inputs.get("reference_images"):
            reference = "provided"
    skip = preferences.get("skip_questions", False)
    specified = preferences.get("workflow_specified", False)
    if not isinstance(skip, bool) or not isinstance(specified, bool):
        raise ValueError("skip_questions and workflow_specified must be boolean")
    questions = []
    if not skip and not specified:
        if reference is None and not count:
            questions.append({"id": "reference", "title": "是否使用项目中的模板或参考图？", "options": ["使用项目模板或已有参考图", "从模板库选择", "不使用参考图"]})
        if (pages is None and not count) or ratio is None:
            known = f"已确定 {pages or count} 页；" if pages or count else ""
            question = f"{known}请确定{'画面比例' if pages or count else '页数与画面比例'}。"
            options = ["16:9（推荐）", "4:3", "自定比例"] if pages or count else ["8 页，16:9（推荐）", "自定页数与比例"]
            questions.append({"id": "details", "title": question, "options": options})
        if requested == "auto":
            first = MODE_LABELS[recommended] + "（推荐）"
            other = MODE_LABELS["flow" if recommended == "skill" else "skill"]
            questions.append({"id": "mode", "title": "图像确定后，使用哪种方式转成可编辑 PPT？", "options": [first, other]})
    blockers = []
    if reference == "project" and not inputs.get("pptx_templates"):
        blockers.append("已选择项目模板，但尚未定位真实 PPTX 模板文件")
    if reference == "provided" and not inputs.get("reference_images") and not inputs.get("pptx_templates"):
        blockers.append("已选择已有参考，但尚未读取真实参考文件")
    if mode == "skill":
        if view_images is not True:
            blockers.append("当前会话的看图能力尚未确认或不可用")
        if execute is not True:
            blockers.append("当前会话的本地代码执行能力尚未确认或不可用")
    elif flow_available is False:
        blockers.append("Workbench 尚未连接；先检查其配置与运行状态")
    if count:
        design = "provided_visuals"
    elif imagegen is True:
        design = "image_generation_tool"
    elif execute is True:
        design = "local_render"
    else:
        design = "needs_visual_input"
        blockers.append("需要真实页面图像，或可用的图像生成／本地渲染能力")
    return {
        "schema": "drawai.workflow-plan.v1",
        "environment": {**environment, "identified_model": identified, "session_model_eligible": eligible},
        "design": {"method": design, "image_generation_available": imagegen},
        "decisions": {
            "reference": reference or "none", "reference_source": "user_or_inputs" if reference else "default",
            "page_count": pages or count or 8, "page_count_source": "user" if pages else "inputs" if count else "default",
            "aspect_ratio": ratio or "16:9", "aspect_ratio_source": "user" if preferences.get("aspect_ratio") else "inputs" if ratio else "default",
            "mode": mode, "mode_source": mode_source, "recommended_mode": recommended,
        },
        "mode_descriptions": MODE_LABELS,
        "questions": questions, "question_policy": "skip" if skip else "specified_workflow" if specified else "missing_only",
        "blockers": blockers, "ready_to_start": not questions and not blockers,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("request", help="JSON file, or - for stdin")
    args = parser.parse_args()
    raw = sys.stdin.read() if args.request == "-" else Path(args.request).read_text()
    print(json.dumps(create_plan(json.loads(raw)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
