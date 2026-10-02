#!/usr/bin/env python3
"""A runnable document-authoring example; adapt its content and layout for a task."""

from pathlib import Path
import argparse
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pptx_skill import Document, load_document, import_pptx, export_pptx, export_svg


def sample_document():
    return Document.model_validate(
        {
            "schema": "presentation.document.v1",
            "id": "example-deck",
            "properties": {"document.page_size": {"width": 960, "height": 540}},
            "pages": [
                {
                    "id": "overview",
                    "objects": [
                        {
                            "id": "heading",
                            "kind": "text_box",
                            "properties": {
                                "object.frame": {
                                    "left": 40,
                                    "top": 30,
                                    "width": 880,
                                    "height": 80,
                                },
                                "text.run.font.latin": "Arial",
                                "text.run.font.size": 32,
                                "text.body.insets": {
                                    "left": 0,
                                    "top": 0,
                                    "right": 0,
                                    "bottom": 0,
                                },
                                "text.body.paragraphs": [
                                    {
                                        "content": [
                                            {
                                                "kind": "run",
                                                "text": "Original ",
                                                "properties": {
                                                    "text.run.font.bold": True
                                                },
                                            },
                                            {
                                                "kind": "run",
                                                "text": "title",
                                                "properties": {
                                                    "text.run.font.italic": True
                                                },
                                            },
                                        ]
                                    }
                                ],
                            },
                        },
                        {
                            "id": "panel",
                            "kind": "shape",
                            "properties": {
                                "object.frame": {
                                    "left": 40,
                                    "top": 150,
                                    "width": 400,
                                    "height": 200,
                                },
                                "shape.geometry.preset": "roundRect",
                                "paint.kind": "gradient",
                                "paint.gradient.kind": "linear",
                                "paint.gradient.angle": 35,
                                "paint.gradient.stops": [
                                    {"offset": 0, "color": "#244E9B"},
                                    {"offset": 1, "color": "#49B8CF"},
                                ],
                                "stroke.paint": "#17354D",
                                "stroke.width": 1.5,
                            },
                        },
                    ],
                }
            ],
        }
    )


def objects(document):
    def walk(items):
        for obj in items:
            yield obj
            yield from walk(obj.children)

    for page in document.pages:
        yield from walk(page.objects)


def replace_run(document, object_id, find, text):
    matches = [obj for obj in objects(document) if obj.id == object_id]
    if len(matches) != 1:
        raise ValueError(f"Expected one object {object_id!r}, found {len(matches)}")
    runs = [
        item
        for p in matches[0].properties.get("text.body.paragraphs", [])
        for item in p.get("content", [])
        if item.get("kind", "run") == "run" and item.get("text") == find
    ]
    if len(runs) != 1:
        raise ValueError(
            f"Expected one exact run {find!r}, found {len(runs)}; inspect the imported JSON"
        )
    runs[0]["text"] = text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument(
        "--source", type=Path, help="Optional PPTX or document JSON to edit."
    )
    parser.add_argument("--object-id")
    parser.add_argument("--find", help="Exact text of one existing run.")
    parser.add_argument("--text", help="Replacement run text.")
    parser.add_argument("--svg", action="store_true")
    args = parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise ValueError("Choose a new or empty output directory")
    if args.source:
        document = (
            import_pptx(args.source)
            if args.source.suffix.lower() == ".pptx"
            else load_document(args.source)
        )
        if args.object_id is None or args.find is None or args.text is None:
            raise ValueError("Editing needs --object-id, --find and --text")
        replace_run(document, args.object_id, args.find, args.text)
    else:
        document = sample_document()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    document.save(args.output_dir / "document.json")
    report = {
        "pptx": export_pptx(
            document,
            args.output_dir / "deck.pptx",
            asset_root=args.source.resolve().parent if args.source else None,
        )
    }
    if args.svg:
        report["svg"] = export_svg(
            document,
            args.output_dir / "svg",
            asset_root=args.source.resolve().parent if args.source else None,
        )
    (args.output_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "document": str(args.output_dir / "document.json"),
                "pptx": str(args.output_dir / "deck.pptx"),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
