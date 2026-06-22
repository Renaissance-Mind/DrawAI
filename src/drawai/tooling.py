from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from drawai.page_spec_assets import materialized_asset_records, page_spec_asset_manifest


ToolRunner = Callable[[Sequence[str]], int]


@dataclass(frozen=True)
class DrawAITool:
    tool_id: str
    summary: str
    parameters: tuple[str, ...]
    examples: tuple[str, ...]
    runner: ToolRunner

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "summary": self.summary,
            "parameters": list(self.parameters),
            "examples": list(self.examples),
        }


def drawai_tool_registry() -> dict[str, DrawAITool]:
    return {
        "format": DrawAITool(
            tool_id="format",
            summary="Inspect and validate DrawAI workflow file formats.",
            parameters=(
                "describe <format_id>: print the registered format contract.",
                "validate --format-id <format_id> --path <file>: validate a concrete file and print JSON.",
            ),
            examples=(
                "format describe drawai.page_spec.v1",
                "format validate --format-id drawai.page_spec.v1 --path nodes/asset_prepare/runs/001/output/page_spec.json",
            ),
            runner=_format_tool,
        ),
        "page-spec-assets": DrawAITool(
            tool_id="page-spec-assets",
            summary="List materialized PageSpec element assets and compute SVG hrefs from a target SVG directory.",
            parameters=(
                "--page-spec <path>: PageSpec JSON containing element.materialization outputs.",
                "--svg-dir <path>: directory where the SVG will be written; used to compute relative hrefs.",
            ),
            examples=(
                "page-spec-assets --page-spec nodes/asset_prepare/runs/001/output/page_spec.json --svg-dir svg",
            ),
            runner=_page_spec_assets_tool,
        ),
        "svg-validate": DrawAITool(
            tool_id="svg-validate",
            summary="Validate and render a semantic SVG using canvas and materialized asset information from PageSpec.",
            parameters=(
                "--svg <path>: SVG file to validate.",
                "--page-spec <path>: PageSpec JSON used for canvas size and allowed raster assets.",
                "--rendered <path>: PNG render path to write.",
                "--report <path>: JSON validation report path to write.",
                "--href-base-dir <path>: base directory used to resolve SVG hrefs; use svg for final deliverables.",
                "--allow-external-assets: optional escape hatch for non-local assets; default is false.",
            ),
            examples=(
                "svg-validate --svg nodes/svg_compose/runs/001/output/semantic.svg --page-spec nodes/asset_prepare/runs/001/output/page_spec.json --rendered nodes/svg_compose/runs/001/output/rendered.png --report nodes/svg_compose/runs/001/output/validation_report_final.json --href-base-dir svg",
            ),
            runner=_svg_validate_tool,
        ),
    }


def drawai_tool_cli(argv: Sequence[str] | None = None) -> int:
    args = list(argv or ())
    registry = drawai_tool_registry()
    if not args:
        return _tool_list(registry, json_output=False)
    if args[0] == "list":
        parser = argparse.ArgumentParser(prog="drawai tool list", description="List DrawAI tools.")
        parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
        parsed = parser.parse_args(args[1:])
        return _tool_list(registry, json_output=parsed.json)
    if args[0] == "help":
        parser = argparse.ArgumentParser(prog="drawai tool help", description="Show one DrawAI tool contract.")
        parser.add_argument("tool_id")
        parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
        parsed = parser.parse_args(args[1:])
        tool = _required_tool(registry, parsed.tool_id)
        if parsed.json:
            _print_json(tool.to_dict())
        else:
            print(drawai_tool_help_text(tool))
        return 0
    tool = _required_tool(registry, args[0])
    return tool.runner(args[1:])


def drawai_tool_help_text(tool: DrawAITool) -> str:
    lines = [f"DrawAI tool: {tool.tool_id}", "", tool.summary, "", "Parameters:"]
    lines.extend(f"- {parameter}" for parameter in tool.parameters)
    if tool.examples:
        lines.extend(["", "Examples:"])
        lines.extend(f"- drawai tool {example}" for example in tool.examples)
    return "\n".join(lines)


def render_drawai_tool_prompt_section(
    tool_ids: Sequence[str],
    *,
    command_prefix: str,
) -> str:
    registry = drawai_tool_registry()
    selected = [_required_tool(registry, tool_id) for tool_id in _ordered_unique(tool_ids)]
    lines = [
        "## DrawAI Tools",
        "Use only the DrawAI tools listed here. They are CLI product interfaces, not direct Python function calls.",
        f"Exact command prefix from the Agent cwd: `{command_prefix}`",
        "Run `<command prefix> help <tool_id>` for the full contract of a tool before using unfamiliar parameters.",
    ]
    for tool in selected:
        lines.extend(
            [
                "",
                f"### Tool `{tool.tool_id}`",
                tool.summary,
                "Parameters:",
            ]
        )
        lines.extend(f"- {parameter}" for parameter in tool.parameters)
        if tool.examples:
            lines.append("Examples:")
            lines.extend(f"- `{command_prefix} {example}`" for example in tool.examples)
    return "\n".join(lines)


def resolve_drawai_tool_command_prefix(repo_root: str | Path, *, cwd: str | Path) -> str:
    repo = Path(repo_root).expanduser().resolve(strict=False)
    src_dir = repo / "src"
    command = [sys.executable, "-m", "drawai.cli", "tool", "list", "--json"]
    env = os.environ.copy()
    env["PYTHONPATH"] = _prepend_pythonpath(src_dir, env.get("PYTHONPATH"))
    completed = subprocess.run(
        command,
        cwd=str(Path(cwd).expanduser().resolve(strict=False)),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        timeout=30,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "DrawAI tool CLI is not executable from the workflow run root: "
            + completed.stderr.strip()
        )
    return " ".join(
        [
            "env",
            f"PYTHONPATH={shlex.quote(str(src_dir))}",
            shlex.quote(sys.executable),
            "-m",
            "drawai.cli",
            "tool",
        ]
    )


def _format_tool(argv: Sequence[str]) -> int:
    from drawai.workflow.formats import default_format_registry, validate_format_file

    parser = argparse.ArgumentParser(prog="drawai tool format", description="Inspect and validate DrawAI formats.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    describe = subparsers.add_parser("describe", help="Describe a format contract.")
    describe.add_argument("format_id")
    validate = subparsers.add_parser("validate", help="Validate a file against a format.")
    validate.add_argument("--format-id", required=True)
    validate.add_argument("--path", required=True, type=Path)
    args = parser.parse_args(list(argv))
    registry = default_format_registry()
    if args.command == "describe":
        spec = registry.get(args.format_id)
        if spec is None:
            raise SystemExit(f"unknown format: {args.format_id}")
        _print_json(
            {
                "format_id": spec.format_id,
                "label": spec.label,
                "media_type": spec.media_type,
                "artifact_type": spec.artifact_type,
                "description": spec.description,
            }
        )
        return 0
    if args.command == "validate":
        result = validate_format_file(args.format_id, args.path, registry=registry)
        _print_json(result.to_dict())
        return 0 if result.ok else 1
    raise AssertionError(f"unsupported format tool command: {args.command}")


def _page_spec_assets_tool(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="drawai tool page-spec-assets",
        description="List materialized PageSpec assets and SVG hrefs.",
    )
    parser.add_argument("--page-spec", required=True, type=Path)
    parser.add_argument("--svg-dir", required=True, type=Path)
    args = parser.parse_args(list(argv))
    _print_json(
        {
            "schema": "drawai.tool.page_spec_assets.v1",
            "page_spec": str(args.page_spec),
            "svg_dir": str(args.svg_dir),
            "assets": materialized_asset_records(args.page_spec, svg_dir=args.svg_dir),
        }
    )
    return 0


def _svg_validate_tool(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="drawai tool svg-validate",
        description="Validate/render a semantic SVG with PageSpec materialization constraints.",
    )
    parser.add_argument("--svg", required=True, type=Path)
    parser.add_argument("--page-spec", required=True, type=Path)
    parser.add_argument("--rendered", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--href-base-dir", type=Path)
    parser.add_argument("--allow-external-assets", action="store_true")
    args = parser.parse_args(list(argv))
    from drawai.svg_validation import validate_svg_file

    page_spec = json.loads(args.page_spec.read_text(encoding="utf-8"))
    if not isinstance(page_spec, Mapping):
        raise ValueError("PageSpec must be a JSON object")
    canvas = page_spec.get("canvas") if isinstance(page_spec.get("canvas"), Mapping) else {}
    canvas_payload = {
        "width": canvas.get("width_px", canvas.get("width")),
        "height": canvas.get("height_px", canvas.get("height")),
    }
    href_base_dir = args.href_base_dir or args.svg.parent
    asset_manifest = page_spec_asset_manifest(args.page_spec, svg_dir=href_base_dir)
    report = validate_svg_file(
        args.svg,
        canvas_payload,
        asset_manifest,
        args.rendered,
        allow_external_assets=args.allow_external_assets,
        reference_dir=href_base_dir,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _print_json(report)
    return 0 if report.get("status") == "ok" else 1


def _tool_list(registry: Mapping[str, DrawAITool], *, json_output: bool) -> int:
    if json_output:
        _print_json({"tools": [tool.to_dict() for tool in registry.values()]})
    else:
        for tool in registry.values():
            print(f"{tool.tool_id}\t{tool.summary}")
    return 0


def _required_tool(registry: Mapping[str, DrawAITool], tool_id: str) -> DrawAITool:
    tool = registry.get(tool_id)
    if tool is None:
        available = ", ".join(sorted(registry))
        raise SystemExit(f"unknown DrawAI tool {tool_id!r}; available tools: {available}")
    return tool


def _ordered_unique(values: Sequence[str]) -> tuple[str, ...]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        clean = str(value).strip()
        if not clean or clean in seen:
            continue
        ordered.append(clean)
        seen.add(clean)
    return tuple(ordered)


def _prepend_pythonpath(src_dir: Path, current: str | None) -> str:
    src = str(src_dir)
    if not current:
        return src
    parts = current.split(os.pathsep)
    if src in parts:
        return current
    return os.pathsep.join([src, current])


def _print_json(payload: Mapping[str, Any]) -> None:
    print(json.dumps(dict(payload), ensure_ascii=False, indent=2))
