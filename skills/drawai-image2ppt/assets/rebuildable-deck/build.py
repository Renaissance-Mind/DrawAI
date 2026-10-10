#!/usr/bin/env python3
"""Rebuild chart assets and compose a slide with editable text and an SVG picture.

Set SKILL_DIR to the complete drawai-image2ppt folder. Install its core requirements
and this project's requirements.txt. Output and data paths are project-relative.
The included CSV is illustrative data in arbitrary units; replace it for a task.
"""

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
skill_dir = Path(os.environ["SKILL_DIR"]).resolve()
sys.path.insert(0, str(skill_dir / "scripts"))
from pptx_skill import Document, export_pptx, export_svg, render_pptx


def text(object_id, content, x, y, width, height, size, color, bold=False):
    return {
        "id": object_id,
        "kind": "text_box",
        "properties": {
            "object.frame": {"left": x, "top": y, "width": width, "height": height},
            "text.run.font.latin": "Arial",
            "text.run.font.size": size,
            "text.run.font.bold": bold,
            "text.run.fill": color,
            "text.body.insets": {"left": 0, "top": 0, "right": 0, "bottom": 0},
            "text.body.paragraphs": [{"content": [{"kind": "run", "text": content}]}],
        },
    }


def compose(points):
    first, last = points[0][1], points[-1][1]
    return Document.model_validate(
        {
            "schema": "presentation.document.v1",
            "id": "data-driven-deck",
            "properties": {"document.page_size": {"width": 960, "height": 540}},
            "assets": {
                "trend-preview": {
                    "path": "assets/rendered/trend.png",
                    "content_type": "image/png",
                },
                "trend-vector": {
                    "path": "assets/rendered/trend.svg",
                    "content_type": "image/svg+xml",
                },
            },
            "pages": [
                {
                    "id": "results",
                    "objects": [
                        text(
                            "heading",
                            "Data-driven presentation",
                            48,
                            36,
                            864,
                            50,
                            32,
                            "#17293E",
                            True,
                        ),
                        text(
                            "subtitle",
                            "Native slide text + independently rendered chart",
                            48,
                            94,
                            864,
                            30,
                            16,
                            "#526070",
                        ),
                        {
                            "id": "trend",
                            "kind": "picture",
                            "properties": {
                                "object.frame": {
                                    "left": 48,
                                    "top": 157,
                                    "width": 640,
                                    "height": 320,
                                },
                                "picture.asset_ref": "trend-preview",
                                "picture.svg_asset": "trend-vector",
                                "picture.aspect_fit": "contain",
                                "accessibility.description": "Iteration scores drawn from data/metrics.csv",
                            },
                        },
                        text(
                            "metric-label",
                            "LATEST SCORE",
                            730,
                            170,
                            182,
                            30,
                            12,
                            "#526070",
                            True,
                        ),
                        text(
                            "latest-score",
                            f"{last:g}",
                            730,
                            208,
                            182,
                            70,
                            48,
                            "#3168F5",
                            True,
                        ),
                        text(
                            "summary",
                            f"{len(points)} points\nChange: {last - first:+g} a.u.",
                            730,
                            294,
                            182,
                            80,
                            16,
                            "#17293E",
                        ),
                        text(
                            "provenance",
                            "Source: data/metrics.csv\nIllustrative data, arbitrary units",
                            48,
                            482,
                            864,
                            40,
                            12,
                            "#526070",
                        ),
                    ],
                }
            ],
        }
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="New project-relative output directory",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("data/metrics.csv"),
        help="Project-relative iteration,score CSV",
    )
    parser.add_argument("--svg", action="store_true")
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    out = ROOT / args.output
    if out.exists() and any(out.iterdir()):
        raise ValueError("Choose a new or empty output directory")
    data = ROOT / args.data
    chart_source = ROOT / "assets/src/line_chart.py"
    snapshot = out / "data/metrics.csv"
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(data, snapshot)
    saved_code = out / "assets/src/line_chart.py"
    saved_code.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(chart_source, saved_code)
    subprocess.run(
        [
            sys.executable,
            str(saved_code),
            "--data",
            str(snapshot),
            "--output-dir",
            str(out / "assets/rendered"),
        ],
        check=True,
    )
    with snapshot.open(encoding="utf-8", newline="") as stream:
        points = [
            (float(r["iteration"]), float(r["score"])) for r in csv.DictReader(stream)
        ]
    doc = compose(points)
    doc.save(out / "document.json")
    report = {
        "pptx": export_pptx(doc, out / "deck.pptx", asset_root=out),
        "source": {
            "data": "data/metrics.csv",
            "data_sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest(),
            "chart_code": "assets/src/line_chart.py",
            "chart_code_sha256": hashlib.sha256(saved_code.read_bytes()).hexdigest(),
            "points": len(points),
        },
    }
    if args.svg:
        report["svg"] = export_svg(doc, out / "svg", asset_root=out)
    if args.preview:
        report["preview"] = render_pptx(out / "deck.pptx", out / "preview")
    (out / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {"output": str(out.resolve()), "points": len(points)}, ensure_ascii=False
        )
    )


if __name__ == "__main__":
    main()
