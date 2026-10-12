"""Dependency-free MCP stdio adapter over DrawAI's shared tools.

Only this JSON-RPC boundary converts exceptions into MCP errors. Core failures
remain explicit. No Agent process is launched for Session implementation.
"""
import hashlib
import json
import sys

from .resources import resource_path
from .shared_tools import dispatch

FILTERS = {"query": {"type": "string"}, "category": {"type": "string"}, "with_images": {"type": "boolean"}, "template_ids": {"type": "array", "items": {"type": "string"}}, "offset": {"type": "integer", "minimum": 0}, "limit": {"type": "integer", "minimum": 1, "maximum": 120}}


def tool(name, description, properties, required=(), *, read_only=False):
    return {"name": name, "description": description, "inputSchema": {"type": "object", "properties": properties, "required": list(required), "additionalProperties": False}, "annotations": {"readOnlyHint": read_only, "destructiveHint": False, "openWorldHint": name in {"drawai_image", "drawai_flow", "drawai_prepare_template"}}}


TOOLS = [
    tool("drawai_templates", "Search/get/recommend actual template references for drawai-design.", {"action": {"enum": ["search", "get", "recommend"]}, "template_id": {"type": "string"}, **FILTERS}, ["action"], read_only=True),
    tool("drawai_show_templates", "Show the template chooser inline; selected references continue in the current Session.", FILTERS, read_only=True),
    tool("drawai_prepare_template", "Download and hash-check selected references to a new task directory.", {"template_id": {"type": "string"}, "output_directory": {"type": "string"}}, ["template_id", "output_directory"]),
    tool("drawai_plan", "Plan visual generation with host tools or a configured image API. Final implementation defaults to the current Agent's configuration; change Agent or delegate Flow only when explicitly requested.", {"request": {"type": "object"}}, ["request"], read_only=True),
    tool("drawai_flow", "Explicitly delegate conversion. Session submits must pass the planner implementation.flow_agent_settings to retain the caller Agent; standalone submits use configured Workbench settings.", {"action": {"enum": ["status", "submit", "start", "export"]}, "visual_manifest": {"type": "string"}, "batch_id": {"type": "string"}, "name": {"type": "string"}, "output_path": {"type": "string"}, "agent_settings": {"type": "object"}}, ["action"]),
    tool("drawai_image", "Generate/edit an actual image using a user's shared Images API connection. For host generation use the current Session's own image tool instead. This never selects or changes the implementation Agent.", {"action": {"enum": ["generate", "edit"]}, "connection": {"type": "string"}, "prompt": {"type": "string"}, "source_image": {"type": "string"}, "output_directory": {"type": "string"}, "output_stem": {"type": "string"}, "task_name": {"type": "string"}, "options": {"type": "object"}}, ["action", "prompt", "output_directory"]),
]


def ui_resource():
    text = resource_path("apps/workbench/dist-plugin/templates-inline.html").read_text(encoding="utf-8")
    return "ui://drawai/templates-" + hashlib.sha256(text.encode()).hexdigest()[:16] + ".html", text


def handle(method, params):
    if method == "initialize":
        from importlib.metadata import version
        supported = {"2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25"}
        protocol = params.get("protocolVersion", "2025-06-18")
        return {"protocolVersion": protocol if protocol in supported else "2025-06-18", "serverInfo": {"name": "drawai", "version": version("drawai")}, "capabilities": {"tools": {}, "resources": {}}}
    if method == "ping":
        return {}
    if method == "tools/list":
        uri, _ = ui_resource()
        return {"tools": [dict(t, **{"_meta": {"ui": {"resourceUri": uri}}}) if t["name"] == "drawai_show_templates" else t for t in TOOLS]}
    if method == "tools/call":
        name = params["name"]
        definition = next((t for t in TOOLS if t["name"] == name), None)
        if definition is None:
            raise ValueError(f"Unknown DrawAI tool: {name}")
        args = params.get("arguments", {})
        allowed = definition["inputSchema"]["properties"]
        if not isinstance(args, dict) or set(args) - set(allowed) or set(definition["inputSchema"]["required"]) - set(args):
            raise ValueError("Invalid tool arguments")
        data = dispatch(name, args)
        return {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}], "structuredContent": data, **({"_meta": {"ui": {"resourceUri": ui_resource()[0]}}} if name == "drawai_show_templates" else {})}
    if method == "resources/list":
        return {"resources": [{"uri": ui_resource()[0], "name": "DrawAI Templates", "mimeType": "text/html;profile=mcp-app"}]}
    if method == "resources/read":
        uri, text = ui_resource()
        if params.get("uri") != uri:
            raise ValueError("Unknown resource URI")
        return {"contents": [{"uri": uri, "text": text, "mimeType": "text/html;profile=mcp-app", "_meta": {"openai/ui": {"availableDisplayModes": ["inline", "fullscreen"]}, "ui": {"prefersBorder": True, "csp": {"resourceDomains": ["https://assets.visualize.renaissancemind.ai", "https://visualize.renaissancemind.ai"], "connectDomains": []}}}}]}
    raise ValueError(f"Unsupported MCP method: {method}")


def main():
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    for line in sys.stdin:
        request = None
        try:
            request = json.loads(line)
            if not isinstance(request, dict) or not isinstance(request.get("method"), str):
                raise ValueError("Expected a JSON-RPC request object with a method")
            if "id" not in request:
                continue
            result = handle(request["method"], request.get("params", {}))
            response = {"jsonrpc": "2.0", "id": request["id"], "result": result}
        except Exception as exc:
            if isinstance(request, dict) and request.get("method") == "tools/call":
                response = {"jsonrpc": "2.0", "id": request.get("id"), "result": {"isError": True, "content": [{"type": "text", "text": f"{type(exc).__name__}: {exc}"}]}}
            else:
                response = {"jsonrpc": "2.0", "id": request.get("id") if isinstance(request, dict) else None, "error": {"code": -32603, "message": f"{type(exc).__name__}: {exc}"}}
        print(json.dumps(response, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
