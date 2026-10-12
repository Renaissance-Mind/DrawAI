"""Tools called identically by CLI, Session MCP and Workbench integrations."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import uuid
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .resources import resource_path
from .runtime_paths import flow_urls, read_preferences, workspace_path

ALIASES = {"技术架构": "technical architecture", "工作流程": "workflow flow", "消融": "ablation", "组会": "research", "学术": "academic", "论文": "academic", "科研": "research", "教学": "teaching", "课程": "course", "架构": "architecture", "流程": "flow", "图表": "chart", "数据": "data", "方法": "method", "实验": "experiment", "对比": "comparison", "时间线": "timeline", "极简": "minimal", "咨询": "consulting", "品牌": "brand", "产品": "product", "信息图": "infographic", "答辩": "academic"}


def template_catalog():
    return json.loads(resource_path("apps/workbench/templates/data/visual-reference-templates.json").read_text(encoding="utf-8"))


def find_template(identifier):
    for card in template_catalog()["templates"]:
        if card["id"] == identifier:
            return card
    raise ValueError(f"Unknown visual reference: {identifier}")


def search_templates(args):
    source = template_catalog()
    all_cards = source["templates"]
    offset, limit = args.get("offset", 0), args.get("limit", 12)
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 120:
        raise ValueError("offset must be non-negative; limit must be between 1 and 120")
    ids = args.get("template_ids")
    if ids is not None and any(identifier not in {c["id"] for c in all_cards} for identifier in ids):
        raise ValueError("Unknown template in template_ids")
    query = args.get("query", "").strip().lower()
    for zh, en in ALIASES.items():
        query = query.replace(zh, " " + en + " ")
    words = list(dict.fromkeys(re.split(r"[^\w-]+", query)))
    words = [word for word in words if word]
    ranked = []
    for card in all_cards:
        if args.get("category") and card["category"] != args["category"]:
            continue
        if args.get("with_images") and not card["assets"] or ids is not None and card["id"] not in ids:
            continue
        fields = [(card["name"], 4), (card["category"], 3), (" ".join(card.get("scenario_tags", [])), 3), (" ".join(card.get("layout_archetypes", [])), 3), (" ".join(card.get("visual_tags", [])), 2), (card.get("prompt_recipe", ""), 1), (card["id"], 1)]
        matched = [word for word in words if any(word in text.lower() for text, _ in fields)]
        if words and (not matched if args.get("action") == "recommend" else len(matched) != len(words)):
            continue
        score = sum(weight for word in words for text, weight in fields if word in text.lower())
        ranked.append((card, score))
    if args.get("action") == "recommend":
        ranked.sort(key=lambda item: (-item[1], item[0]["name"].casefold()))
    elif ids is not None:
        ranked.sort(key=lambda item: ids.index(item[0]["id"]))
    return {"total": len(ranked), "library_count": len(all_cards), "image_count": sum(bool(c["assets"]) for c in all_cards), "categories": sorted({c["category"] for c in all_cards}), "offset": offset, "limit": limit, "templates": [c for c, _ in ranked[offset:offset + limit]], "source": source["source"], **({"ranking": "keyword_relevance"} if args.get("action") == "recommend" else {})}


def save_same_or_new(path, data):
    if path.exists():
        if path.read_bytes() != data:
            raise FileExistsError(f"File already exists with different content: {path}")
        return
    with path.open("xb") as stream:
        stream.write(data)


def prepare_template(args):
    template = find_template(args["template_id"])
    directory = Path(args["output_directory"]).expanduser().resolve() / re.sub(r"[^a-zA-Z0-9_-]", "_", template["id"])
    directory.mkdir(parents=True, exist_ok=True)
    images = []
    for index, asset in enumerate(template["assets"], 1):
        parsed = urlparse(asset["original_url"])
        if parsed.scheme != "https" or parsed.hostname != "assets.visualize.renaissancemind.ai":
            raise ValueError("Unsupported template asset source")
        with urlopen(asset["original_url"], timeout=45) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != asset["sha256"]:
            raise ValueError(f"Template image hash mismatch: {template['id']}")
        filename = f"{index}-" + re.sub(r"[^a-zA-Z0-9._-]", "_", Path(asset.get("filename") or parsed.path).name)
        path = directory / filename
        save_same_or_new(path, data)
        images.append({"path": str(path), "sha256": asset["sha256"], "original_url": asset["original_url"], "width": asset["width"], "height": asset["height"]})
    result = {"schema": "drawai.template-reference.v1", "template": template, "images": images}
    manifest = directory / "template-reference.json"
    save_same_or_new(manifest, (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode())
    return {**result, "manifest": str(manifest)}


def plan_session(request):
    from .session_plan import create_plan
    from .workbench.api_presets import read_workbench_api_presets
    request = copy.deepcopy(request)
    preferences = request.setdefault("preferences", {})
    if preferences.get("image_connection") and "image_generation" not in preferences:
        preferences["image_generation"] = "api"
    defaults = read_preferences()
    for key in ("image_generation", "image_connection"):
        if key not in preferences and defaults.get(key) is not None:
            preferences[key] = defaults[key]
    connection = preferences.get("image_connection")
    if connection:
        preset = next((p for p in read_workbench_api_presets(workspace_path()) if p.id == connection and p.type == "images_api"), None)
        available = bool(preset and (preset.api_key or preset.api_key_env and os.environ.get(preset.api_key_env)))
        request.setdefault("environment", {})["image_api_available"] = available
    agent = preferences.get("implementation_agent")
    if agent in {"claude", "codex"} and request.setdefault("environment", {}).get("external_agent_available") is None:
        import shutil
        request["environment"]["external_agent_available"] = bool(shutil.which(agent))
    return create_plan(request)


def api_request(path, *, method="GET", body=None, headers=None):
    api, _ = flow_urls()
    with urlopen(Request(api + path, data=body, method=method, headers=headers or {}), timeout=60) as response:
        return response.read()


def flow_action(args):
    _, ui = flow_urls()
    action = args["action"]
    batch = args.get("batch_id")
    if action == "status" and not batch:
        return {"ui_url": ui, "health": json.loads(api_request("/api/health"))}
    if action == "submit":
        from .visual_deck import verify_visual_deck
        path = Path(args["visual_manifest"])
        if not path.is_absolute():
            raise ValueError("visual_manifest must be an absolute task path")
        deck = verify_visual_deck(path)
        boundary = "drawai-" + uuid.uuid4().hex
        parts = []
        fields = {"input_mode": "upload", "name": args.get("name") or deck.get("title") or "DrawAI PPT", "auto_start": "false", "auto_run_svg_after_analysis": "true"}
        if args.get("agent_settings") is not None:
            from .settings_cli import redacted
            if not isinstance(args["agent_settings"], dict) or redacted(args["agent_settings"]) != args["agent_settings"]:
                raise ValueError("Flow task Agent settings must be an object with connection references, not raw secrets")
            fields["agent_settings"] = json.dumps(args["agent_settings"], ensure_ascii=False)
        for key, value in fields.items():
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
        for page in deck["pages"]:
            image = Path(page["image"])
            filename = f"{page['order']:04d}-" + image.name.replace('"', "_").replace("\r", "_").replace("\n", "_")
            parts.extend([f'--{boundary}\r\nContent-Disposition: form-data; name="files"; filename="{filename}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode(), image.read_bytes(), b"\r\n"])
        parts.append(f"--{boundary}--\r\n".encode())
        result = json.loads(api_request("/api/batches", method="POST", body=b"".join(parts), headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}))
        return {**result, "ui_url": ui, "visual_manifest": str(path), "state": "queued"}
    if not isinstance(batch, str) or not re.fullmatch(r"batch_[a-zA-Z0-9]+", batch):
        raise ValueError("A batch_id from this task's Flow submission is required")
    if action == "start":
        return {"ui_url": ui, **json.loads(api_request(f"/api/batches/{batch}/run", method="POST", body=b""))}
    if action == "status":
        return {"ui_url": ui, **json.loads(api_request(f"/api/batches/{batch}"))}
    if action != "export":
        raise ValueError(f"Unknown Flow action: {action}")
    output = Path(args["output_path"])
    if not output.is_absolute() or output.suffix.lower() != ".pptx" or output.exists():
        raise ValueError("Choose a new absolute .pptx output path")
    data = api_request(f"/api/batches/{batch}/pptx")
    if not data.startswith(b"PK"):
        raise ValueError("Workbench did not return a PPTX package")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream:
        stream.write(data)
    return {"path": str(output), "size": len(data), "needs_validation": True}


def image_action(args):
    from .workbench.api_presets import api_preset_by_id, read_workbench_api_presets
    from .capabilities import require_capability
    require_capability("images")
    from .image_api import images_api_generate_provider, images_api_edit_provider
    connection = args.get("connection") or read_preferences().get("image_connection")
    preset = api_preset_by_id(read_workbench_api_presets(workspace_path()), connection)
    if preset is None or preset.type != "images_api":
        raise ValueError(f"No images_api connection: {connection}")
    output = Path(args["output_directory"]).expanduser().resolve()
    stem = args.get("output_stem", "page")
    if not re.fullmatch(r"[\w-]+", stem):
        raise ValueError("output_stem must be a filename stem without path separators")
    if output.exists() and any(output.glob(stem + ".*")):
        raise FileExistsError("Choose a new image output stem")
    options = args.get("options") or {}
    if not isinstance(options, dict) or options.get("n", 1) != 1:
        raise ValueError("The page image tool requires one image per call (n=1); generate deck pages individually")
    common = {"prompt": args["prompt"], "output_dir": output, "output_stem": stem, "task_name": args.get("task_name", "DrawAI Session visual"), "runtime_config": options}
    if args["action"] == "edit":
        return images_api_edit_provider(preset)(source_image_path=args["source_image"], **common)
    if args["action"] != "generate":
        raise ValueError("Image action must be generate or edit")
    return images_api_generate_provider(preset)(**common)


def dispatch(name, args):
    if name == "drawai_plan":
        return plan_session(args["request"])
    if name == "drawai_flow":
        return flow_action(args)
    if name == "drawai_image":
        return image_action(args)
    if name == "drawai_templates":
        if args.get("action") not in {"search", "get", "recommend"}:
            raise ValueError("Unknown template action")
        return {"template": find_template(args["template_id"])} if args.get("action") == "get" else search_templates(args)
    if name == "drawai_prepare_template":
        return prepare_template(args)
    if name == "drawai_show_templates":
        view = {"with_images": not bool(args.get("template_ids")), "limit": 6, "offset": 0, **args}
        return {"view": view, "result": search_templates(view)}
    raise ValueError(f"Unknown DrawAI tool: {name}")


def tool_cli(argv):
    import sys
    parser = argparse.ArgumentParser(prog="drawai session tool")
    parser.add_argument("tool")
    parser.add_argument("arguments", nargs="?", default="-", help="JSON file, @file, or - for stdin")
    args = parser.parse_args(argv)
    raw = sys.stdin.read() if args.arguments == "-" else Path(args.arguments.removeprefix("@")).read_text(encoding="utf-8")
    arguments = json.loads(raw)
    if args.tool == "drawai_plan" and "request" not in arguments:
        arguments = {"request": arguments}
    print(json.dumps(dispatch(args.tool, arguments), ensure_ascii=False))
    return 0


def flow_cli(argv):
    parser = argparse.ArgumentParser(prog="drawai flow")
    parser.add_argument("action", choices=("status", "submit", "start", "export"))
    parser.add_argument("--manifest", dest="visual_manifest")
    parser.add_argument("--batch-id")
    parser.add_argument("--agent-settings", type=Path, help="Per-task Agent settings; global Workbench settings are retained.")
    parser.add_argument("--name")
    parser.add_argument("--output", dest="output_path")
    args = vars(parser.parse_args(argv))
    if args["agent_settings"] is not None:
        args["agent_settings"] = json.loads(args["agent_settings"].read_text(encoding="utf-8"))
    print(json.dumps(flow_action(args), ensure_ascii=False, indent=2))
    return 0


def image_cli(argv):
    parser = argparse.ArgumentParser(prog="drawai image")
    parser.add_argument("action", choices=("generate", "edit"))
    parser.add_argument("--connection")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--source", dest="source_image")
    parser.add_argument("--output-dir", dest="output_directory", required=True)
    parser.add_argument("--stem", dest="output_stem", default="page")
    parser.add_argument("--options", type=Path, help="Optional Images API options JSON")
    args = vars(parser.parse_args(argv))
    if args["options"]:
        args["options"] = json.loads(args["options"].read_text(encoding="utf-8"))
    if args["action"] == "edit" and not args["source_image"]:
        parser.error("edit requires --source")
    print(json.dumps(image_action(args), ensure_ascii=False, indent=2))
    return 0
