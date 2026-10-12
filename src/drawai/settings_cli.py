"""Manage the same settings used by the Workbench and Session tools."""
import argparse
import json
from pathlib import Path

from .runtime_paths import initialize_home, read_preferences, write_preferences, workspace_path


def redacted(value):
    if isinstance(value, dict):
        return {key: "***" if (key.lower() in {"api_key", "token", "password", "authorization", "secret"} or key.lower().endswith(("_api_key", "_token", "_password", "_secret"))) and item else redacted(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redacted(item) for item in value]
    return value


def settings_cli(argv):
    parser = argparse.ArgumentParser(prog="drawai config", description="Shared Session, Workbench and CLI configuration.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("show")
    connections = sub.add_parser("connections")
    connections.add_argument("--import", dest="source", type=Path, help="Import the Workbench API presets JSON; omitted prints redacted connections.")
    images = sub.add_parser("image")
    images.add_argument("--source", choices=("auto", "session", "api", "local"), default="auto")
    images.add_argument("--connection", default="")
    flow = sub.add_parser("flow")
    flow.add_argument("--api-url", required=True)
    flow.add_argument("--ui-url", required=True)
    agent = sub.add_parser("agent")
    agent.add_argument("--provider", required=True)
    agent.add_argument("--connection", default="")
    agent.add_argument("--endpoint", default="")
    agent.add_argument("--model", default="")
    args = parser.parse_args(argv)
    initialize_home()
    from .workbench.api_presets import read_workbench_api_presets, write_workbench_api_presets
    if args.command == "connections":
        if args.source:
            presets = write_workbench_api_presets(workspace_path(), json.loads(args.source.read_text(encoding="utf-8")))
            (workspace_path() / "settings/api_presets.json").chmod(0o600)
        else:
            presets = read_workbench_api_presets(workspace_path())
        result = {"presets": [preset.to_dict() for preset in presets]}
    elif args.command == "image":
        if args.connection and not any(p.id == args.connection and p.type == "images_api" for p in read_workbench_api_presets(workspace_path())):
            raise ValueError(f"No images_api connection: {args.connection}")
        if args.source == "api" and not args.connection:
            raise ValueError("API image generation requires --connection")
        result = write_preferences({"image_generation": args.source, "image_connection": args.connection or None})
    elif args.command == "flow":
        from urllib.parse import urlparse
        for url in (args.api_url, args.ui_url):
            if urlparse(url).scheme not in {"http", "https"} or not urlparse(url).hostname:
                raise ValueError("Flow URLs must be absolute HTTP(S) addresses")
        result = write_preferences({"workbench_api_url": args.api_url.rstrip("/"), "workbench_ui_url": args.ui_url})
    elif args.command == "agent":
        from .workbench.agent_settings import write_workbench_agent_settings
        result = write_workbench_agent_settings(workspace_path(), {
            "selected_provider_id": args.provider, "llm_api_preset_id": args.connection,
            "llm_endpoint_id": args.endpoint, "llm_model": args.model, "model": args.model,
        }).to_persisted_dict()
    else:
        result = {**initialize_home(), "preferences": read_preferences(), "presets": [p.to_dict() for p in read_workbench_api_presets(workspace_path())]}
    print(json.dumps(redacted(result), ensure_ascii=False, indent=2))
    return 0
