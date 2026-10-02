"""One document contract for independent presentation authoring."""

from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import sys
from typing import Sequence


def new_json(path):
    if path is not None and (path.suffix.lower() != ".json" or path.exists()):
        raise ValueError("Choose a new .json filename")


def pptx_cli(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="drawai-ppt",
        description="Author a presentation document and export PPTX/SVG.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "schema", help="Print the presentation.document.v1 JSON Schema."
    )
    capabilities = commands.add_parser(
        "capabilities", help="Show implemented property interfaces and conditions."
    )
    capabilities.add_argument(
        "--property",
        dest="properties",
        action="append",
        help="Query one exact property ID; repeat to query several.",
    )
    imported = commands.add_parser(
        "import", help="Import PPTX or SVG into a presentation document."
    )
    imported.add_argument("source", type=Path)
    imported.add_argument("--output", required=True, type=Path)
    imported.add_argument("--report", type=Path)
    exported = commands.add_parser(
        "export", help="Export a document JSON to editable PPTX and static SVG."
    )
    exported.add_argument("source", type=Path)
    exported.add_argument("--pptx", type=Path)
    exported.add_argument("--svg-dir", type=Path)
    exported.add_argument(
        "--profile", choices=("strict", "best_effort"), default="strict"
    )
    exported.add_argument("--report", type=Path)
    inspected = commands.add_parser(
        "inspect",
        help="List PowerPoint objects, local IDs, layouts and geometry in points.",
    )
    inspected.add_argument("source", type=Path)
    inspected.add_argument("--output", type=Path)
    inspected.add_argument("--preview-dir", type=Path)
    render = commands.add_parser(
        "render", help="Render an actual PPTX into PDF and page PNGs."
    )
    render.add_argument("source", type=Path)
    render.add_argument("--output-dir", required=True, type=Path)
    validate = commands.add_parser(
        "validate", help="Validate package XML and internal relationships."
    )
    validate.add_argument("source", type=Path)
    for command in (exported, inspected, render):
        command.add_argument(
            "--renderer", help="soffice executable, otherwise resolved from PATH."
        )
        command.add_argument(
            "--rasterizer", help="pdftoppm executable, otherwise resolved from PATH."
        )
    args = parser.parse_args(argv)
    try:
        from .io import inspect_pptx, render_pptx, validate_pptx_package
        from .document import Document, import_pptx, import_svg, export_pptx, export_svg

        if args.command == "schema":
            result = Document.model_json_schema()
        elif args.command == "capabilities":
            from .document.capabilities import capability_report

            result = capability_report()
            if args.properties:
                selected = set(args.properties)
                rows = [row for row in result["properties"] if row["id"] in selected]
                unknown = selected - {row["id"] for row in rows}
                if unknown:
                    raise ValueError(f"Unknown property IDs: {sorted(unknown)}")
                result = {"schema": result["schema"], "properties": rows}
        elif args.command == "import":
            new_json(args.output)
            new_json(args.report)
            if args.report and args.report.resolve() == args.output.resolve():
                raise ValueError("Document and report paths must differ")
            if args.source.suffix.lower() == ".pptx":
                document = import_pptx(args.source)
                conversion = {
                    "status": "ok",
                    "backend": "pptx_package",
                    "pages": len(document.pages),
                }
            elif args.source.suffix.lower() == ".svg":
                document, conversion = import_svg(args.source)
            else:
                raise ValueError("Import accepts .pptx or .svg")
            document.save(args.output)
            result = {
                "document": str(args.output.resolve()),
                "pages": len(document.pages),
                "conversion": conversion,
            }
            if args.report:
                _write_json(args.report, result)
        elif args.command == "export":
            new_json(args.report)
            if not args.pptx and not args.svg_dir:
                raise ValueError("Choose --pptx, --svg-dir or both")
            if args.report and args.report.resolve() == args.source.resolve():
                raise ValueError("Report and source paths must differ")
            if args.pptx and (
                args.pptx.suffix.lower() != ".pptx" or args.pptx.exists()
            ):
                raise ValueError("Choose a new .pptx output filename")
            if args.svg_dir and args.svg_dir.exists() and any(args.svg_dir.iterdir()):
                raise ValueError("SVG output directory must be empty")
            if args.svg_dir and not (args.renderer or shutil.which("soffice")):
                raise ValueError(
                    "SVG export requires soffice; install LibreOffice or pass --renderer"
                )
            result = {}
            if args.pptx:
                result["pptx"] = export_pptx(
                    args.source, args.pptx, profile=args.profile
                )
            if args.svg_dir:
                result["svg"] = export_svg(
                    args.source,
                    args.svg_dir,
                    profile=args.profile,
                    renderer=args.renderer,
                    rasterizer=args.rasterizer,
                )
            if args.report:
                _write_json(args.report, result)
        elif args.command == "inspect":
            new_json(args.output)
            result = inspect_pptx(args.source)
            if args.preview_dir:
                result["preview"] = render_pptx(
                    args.source,
                    args.preview_dir,
                    renderer=args.renderer,
                    rasterizer=args.rasterizer,
                )
            if args.output:
                _write_json(args.output, result)
        elif args.command == "render":
            result = render_pptx(
                args.source,
                args.output_dir,
                renderer=args.renderer,
                rasterizer=args.rasterizer,
            )
        else:
            result = validate_pptx_package(args.source)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:  # CLI boundary: expose the real failure to the caller.
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
