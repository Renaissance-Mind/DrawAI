"""Machine-readable template editing commands for humans and agents."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence


def pptx_cli(argv: Sequence[str] | None = None) -> int:
    from .engine import PptxCreatePlan, PptxEditPlan, create_pptx, edit_pptx, inspect_pptx, render_pptx, validate_pptx_package

    parser = argparse.ArgumentParser(prog="drawai-ppt", description="Create and edit native PPTX using Python.")
    commands = parser.add_subparsers(dest="command", required=True)
    schema = commands.add_parser("schema", help="Print the JSON Schema for create/edit plans.")
    schema.add_argument("--mode", choices=("create", "edit", "document"), default="document")
    imported = commands.add_parser("import", help="Import PPTX/SVG into a portable document; embed the template package.")
    imported.add_argument("source", type=Path)
    imported.add_argument("--output", required=True, type=Path)
    exported = commands.add_parser("export", help="Export one document model to editable PPTX and static SVG.")
    exported.add_argument("source", type=Path)
    exported.add_argument("--pptx", type=Path)
    exported.add_argument("--svg-dir", type=Path)
    exported.add_argument("--profile", choices=("strict_native", "compatible"), default="strict_native")
    exported.add_argument("--report", type=Path)
    capabilities = commands.add_parser("capabilities", help="Print implementation and preservation coverage of the property matrix.")
    create = commands.add_parser("create", help="Create an editable deck from a JSON plan.")
    create.add_argument("--plan", required=True, type=Path)
    create.add_argument("--output", required=True, type=Path)
    create.add_argument("--report", type=Path)
    create.add_argument("--preview-dir", type=Path)
    inspect = commands.add_parser("inspect", help="List slide objects, shape IDs, layouts, text and geometry.")
    inspect.add_argument("source", type=Path)
    inspect.add_argument("--output", type=Path, help="Write the inventory JSON instead of printing it.")
    inspect.add_argument("--preview-dir", type=Path, help="Also render the original slides.")
    edit = commands.add_parser("edit", help="Apply a JSON plan and save a new PPTX; never overwrite the template.")
    edit.add_argument("source", type=Path)
    edit.add_argument("--plan", required=True, type=Path)
    edit.add_argument("--output", required=True, type=Path)
    edit.add_argument("--report", type=Path)
    edit.add_argument("--preview-dir", type=Path, help="Also render the final PPTX for visual verification.")
    render = commands.add_parser("render", help="Render the actual PPTX into PDF and slide PNGs.")
    render.add_argument("source", type=Path)
    render.add_argument("--output-dir", required=True, type=Path)
    validate = commands.add_parser("validate", help="Check package XML and internal resource relationships.")
    validate.add_argument("source", type=Path)
    for command in (inspect, edit, create, render, exported):
        command.add_argument("--renderer", help="LibreOffice soffice executable; defaults to PATH.")
        command.add_argument("--rasterizer", help="Poppler pdftoppm executable; defaults to PATH.")
    args = parser.parse_args(argv)
    try:
        json_output = args.output if args.command == "inspect" else args.report if args.command in {"edit", "create"} else None
        if json_output:
            if json_output.suffix.lower() != ".json" or json_output.exists():
                raise ValueError("Choose a new .json filename for the inventory or report")
            inputs = [args.source] if hasattr(args, "source") else []
            if args.command in {"edit", "create"}:
                inputs.extend([args.plan, args.output])
            if any(json_output.resolve() == path.resolve() for path in inputs):
                raise ValueError("Inventory/report paths must differ from the source, plan and output PPTX")
        if args.command == "capabilities":
            from .document.capabilities import capability_report
            result = capability_report()
        elif args.command == "import":
            from .document.importer import import_pptx, import_svg
            document = import_pptx(args.source) if args.source.suffix.lower() == ".pptx" else import_svg(args.source)[0]
            document.save(args.output)
            result = {"document": str(args.output.resolve()), "pages": len(document.pages)}
        elif args.command == "export":
            from .document.export import export_pptx
            from .document.svg import export_svg
            if not args.pptx and not args.svg_dir:
                raise ValueError("Choose --pptx, --svg-dir or both")
            result = {}
            if args.pptx:
                result["pptx"] = export_pptx(args.source, args.pptx, profile=args.profile)
            if args.svg_dir:
                result["svg"] = export_svg(args.source, args.svg_dir, profile=args.profile, renderer=args.renderer, rasterizer=args.rasterizer)
            if args.report:
                _write_json(args.report, result)
        elif args.command == "schema":
            from .document.model import Document
            result = (Document if args.mode == "document" else PptxCreatePlan if args.mode == "create" else PptxEditPlan).model_json_schema()
        elif args.command == "inspect":
            result = inspect_pptx(args.source)
            if args.preview_dir:
                result["preview"] = render_pptx(args.source, args.preview_dir,
                                                renderer=args.renderer, rasterizer=args.rasterizer)
            if args.output:
                _write_json(args.output, result)
                return 0
        elif args.command in {"edit", "create"}:
            plan = json.loads(args.plan.read_text(encoding="utf-8"))
            if args.command == "edit":
                result = edit_pptx(args.source, plan, args.output, asset_root=args.plan.resolve().parent)
            else:
                result = create_pptx(plan, args.output, asset_root=args.plan.resolve().parent)
            if args.preview_dir:
                result["preview"] = render_pptx(args.output, args.preview_dir,
                                                renderer=args.renderer, rasterizer=args.rasterizer)
            if args.report:
                _write_json(args.report, result)
        elif args.command == "render":
            result = render_pptx(args.source, args.output_dir,
                                 renderer=args.renderer, rasterizer=args.rasterizer)
        else:
            result = validate_pptx_package(args.source)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:  # CLI boundary: surface the actual error and return a failure code.
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
