"""Resolve DrawAI's stages, conversion mode and only the missing intake questions."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

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
    source = environment.get("model_source", "unknown")
    if source not in {"session_metadata", "host_display", "user", "unknown"}:
        raise ValueError("model_source must describe the current session, not a global default")
    model = environment.get("model")
    if model is not None and not isinstance(model, str):
        raise ValueError("environment.model must be a string or null")
    identified = identify_model(model) if source != "unknown" else None
    context = environment.get("context", "session")
    if context not in {"session", "workbench", "cli", "server"}:
        raise ValueError("environment.context must be session, workbench, cli or server")
    imagegen = boolean_fact(environment, "image_generation_available")
    view_images = boolean_fact(environment, "image_viewing_available")
    execute = boolean_fact(environment, "local_execution_available")
    flow_available = boolean_fact(environment, "flow_available")
    recommended = "skill" if context == "session" else "flow"
    requested = preferences.get("mode", "auto")
    if requested not in {"auto", "skill", "flow"}:
        raise ValueError("preferences.mode must be auto, skill or flow")
    mode = requested if requested != "auto" else recommended
    mode_source = "user" if requested != "auto" else "current_session" if context == "session" else "configured_runtime"
    implementation_agent = preferences.get("implementation_agent", "current" if context == "session" else "configured")
    if not isinstance(implementation_agent, str) or not implementation_agent.strip():
        raise ValueError("implementation_agent must be a non-empty agent identifier")
    image_source = preferences.get("image_generation", "auto")
    if image_source not in {"auto", "session", "api", "local"}:
        raise ValueError("image_generation must be auto, session, api or local")
    image_connection = preferences.get("image_connection")
    if image_connection is not None and (not isinstance(image_connection, str) or not image_connection.strip()):
        raise ValueError("image_connection must be a non-empty connection identifier")
    image_api = boolean_fact(environment, "image_api_available")
    if image_connection and image_source == "auto":
        image_source = "api"
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
    if implementation_agent not in {"current", "configured"} and boolean_fact(environment, "external_agent_available") is not True:
        blockers.append("用户指定的 Agent 执行环境尚未确认；先配置并检查该 Agent")
    if count:
        design = "provided_visuals"
    elif image_source == "session" or (image_source == "auto" and context == "session" and imagegen is True):
        design = "image_generation_tool"
        if imagegen is not True:
            blockers.append("已选择宿主图像工具，但当前会话尚未提供该能力")
    elif image_source == "api" or (image_source == "auto" and image_api is True):
        design = "image_generation_api"
        if image_api is not True:
            blockers.append("已选择图像 API，但所选连接未配置或尚未确认可用")
    elif image_source == "local" or (image_source == "auto" and execute is True):
        design = "local_render"
        if execute is not True:
            blockers.append("本地排版需要真实代码执行与渲染能力")
    else:
        design = "needs_visual_input"
        blockers.append("需要真实页面图像，或可用的宿主图像工具、图像 API／本地渲染能力")
    caller_config = environment.get("agent_config", {})
    if not isinstance(caller_config, dict):
        raise ValueError("environment.agent_config must be an object")
    actor = environment.get("agent", "current") if implementation_agent == "current" else implementation_agent
    configuration_source = "caller_session" if implementation_agent == "current" else "workbench" if implementation_agent == "configured" else "user"
    implementation = {
        "executor": "flow" if mode == "flow" else "current_session" if implementation_agent == "current" else "explicit_agent",
        "agent": actor,
        "model": model if implementation_agent == "current" and source != "unknown" else preferences.get("implementation_model"),
        "configuration_source": configuration_source,
    }
    requested_model = preferences.get("implementation_model")
    if requested_model is not None:
        if not isinstance(requested_model, str) or not requested_model.strip():
            raise ValueError("implementation_model must be a non-empty model identifier")
        if mode == "skill" and implementation_agent == "current":
            implementation["requested_model"] = requested_model
            if implementation["model"] != requested_model:
                blockers.append("指定实施模型尚未与宿主实际模型一致；在宿主切换模型，或明确选择对应 Agent 执行器")
        else:
            implementation["model"] = requested_model
    if mode == "flow" and implementation_agent != "configured":
        providers = {"claude": "claude_cli", "codex": "codex_cli"}
        provider = caller_config.get("selected_provider_id") or providers.get(actor)
        if provider is None:
            blockers.append("Session Flow 需要实际 Agent 类型或显式指定工作台 Agent 配置")
        else:
            # Auth stays at the executing host; never copy Session credentials.
            allowed = {"model", "reasoning_effort", "fast", "timeout_seconds", "llm_api_preset_id", "llm_endpoint_id"}
            flow_settings = {key: value for key, value in caller_config.items() if key in allowed}
            flow_settings["selected_provider_id"] = provider
            if implementation["model"]:
                flow_settings["model"] = implementation["model"]
            implementation["flow_agent_settings"] = flow_settings
    return {
        "schema": "drawai.workflow-plan.v1",
        "environment": {**environment, "identified_model": identified, "context": context},
        "design": {"method": design, "image_generation_available": imagegen, "connection": image_connection, "source": image_source},
        "implementation": implementation,
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
