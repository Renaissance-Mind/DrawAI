#!/usr/bin/env python3
"""Check native document editing, data isolation, SVG insertion and Office Math."""

from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from PIL import Image
from pptx import Presentation
from pptx_skill import (
    Document,
    export_pptx,
    import_pptx,
    duplicate_page,
    insert_svg,
    inspect_pptx,
    validate_pptx_package,
)


class ToolkitChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "source.pptx"
        self.document = Document.model_validate(
            {
                "schema": "presentation.document.v1",
                "id": "source",
                "properties": {"document.page_size": {"width": 960, "height": 540}},
                "pages": [
                    {
                        "id": "title-page",
                        "objects": [
                            {
                                "id": "title",
                                "kind": "text_box",
                                "properties": {
                                    "object.frame": {
                                        "left": 60,
                                        "top": 30,
                                        "width": 600,
                                        "height": 80,
                                    },
                                    "text.body.paragraphs": [
                                        {
                                            "content": [
                                                {
                                                    "text": "Original title",
                                                    "properties": {
                                                        "text.run.font.bold": True
                                                    },
                                                }
                                            ]
                                        }
                                    ],
                                },
                            }
                        ],
                    },
                    {
                        "id": "data-page",
                        "objects": [
                            {
                                "id": "table",
                                "kind": "table",
                                "properties": {
                                    "object.frame": {
                                        "left": 60,
                                        "top": 140,
                                        "width": 400,
                                        "height": 150,
                                    },
                                    "table.grid_columns": [200, 200],
                                    "table.rows.height": [75, 75],
                                    "table.cells.content": [
                                        ["Input", "Output"],
                                        ["Model", "PPTX"],
                                    ],
                                },
                            },
                            {
                                "id": "chart",
                                "kind": "chart",
                                "properties": {
                                    "object.frame": {
                                        "left": 500,
                                        "top": 140,
                                        "width": 400,
                                        "height": 250,
                                    },
                                    "chart.type": "barChart",
                                    "chart.categories": ["A", "B"],
                                    "chart.series": [{"name": "S", "values": [10, 20]}],
                                },
                            },
                        ],
                    },
                ],
            }
        )
        export_pptx(self.document, self.source)

    def test_create_and_style_preserving_edit(self):
        inventory = inspect_pptx(self.source)
        self.assertEqual(inventory["units"], "pt")
        self.assertEqual(len(inventory["slides"]), 2)
        before = self.source.read_bytes()
        doc = import_pptx(self.source)
        doc.pages[0].objects[0].properties["text.body.paragraphs"][0]["content"][0][
            "text"
        ] = "Updated title"
        out = self.root / "edited.pptx"
        export_pptx(doc, out)
        run = Presentation(out).slides[0].shapes[0].text_frame.paragraphs[0].runs[0]
        self.assertEqual(run.text, "Updated title")
        self.assertTrue(run.font.bold)
        self.assertEqual(self.source.read_bytes(), before)

    def test_independent_chart_copy(self):
        doc = duplicate_page(import_pptx(self.source), "data-page", new_id="data-copy")
        chart = next(obj for obj in doc.pages[-1].objects if obj.kind == "chart")
        chart.properties["chart.series"][0]["values"] = [30, 40]
        out = self.root / "copied.pptx"
        export_pptx(doc, out)
        prs = Presentation(out)
        self.assertEqual(list(prs.slides[1].shapes[1].chart.series[0].values), [10, 20])
        self.assertEqual(list(prs.slides[2].shapes[1].chart.series[0].values), [30, 40])
        restored = import_pptx(out)
        self.assertEqual(len({p.id for p in restored.pages}), 3)

    def test_svg_paths_text_image_and_nonzero_viewbox(self):
        Image.new("RGB", (60, 40), "navy").save(self.root / "image.png")
        svg = self.root / "diagram.svg"
        svg.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="100 50 400 200"><rect x="100" y="50" width="80" height="40" fill="#123456"/><path d="M 200 100 C 220 60 260 140 280 100" stroke="#456789" fill="none"/><text x="110" y="80" font-size="20">Editable text</text><image href="image.png" x="300" y="100" width="60" height="40"/></svg>'
        )
        before = svg.read_bytes()
        doc, report = insert_svg(
            import_pptx(self.source),
            "title-page",
            svg,
            {"left": 60, "top": 140, "width": 400, "height": 200},
        )
        out = self.root / "vector.pptx"
        export_pptx(doc, out)
        group = Presentation(out).slides[0].shapes[-1]
        self.assertEqual(group.shapes[0].left, 0)
        self.assertEqual(group.shapes[0].top, 0)
        self.assertTrue(
            any(s.has_text_frame and s.text == "Editable text" for s in group.shapes)
        )
        self.assertTrue(any(s.shape_type == 13 for s in group.shapes))
        self.assertEqual(svg.read_bytes(), before)
        self.assertEqual(validate_pptx_package(out)["status"], "ok")
        self.assertTrue(report["backend"])

    @unittest.skipUnless(
        shutil.which("pandoc"), "Office Math conversion requires Pandoc"
    )
    def test_real_office_math(self):
        svg = self.root / "formula.svg"
        svg.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200"><g id="equation" data-pb-role="formula" data-pb-formula-latex="x^2+y^2" data-pb-formula-bbox="40 60 220 60"><text x="40" y="100" font-size="30">x²+y²</text></g></svg>'
        )
        doc, report = insert_svg(
            import_pptx(self.source),
            "title-page",
            svg,
            {"left": 60, "top": 140, "width": 400, "height": 200},
        )
        out = self.root / "math.pptx"
        export_pptx(doc, out)
        self.assertEqual(report["formula_export"]["converted"], 1)
        self.assertTrue(
            any(
                s["kind"] == "office_math"
                for s in inspect_pptx(out)["slides"][0]["shapes"]
            )
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
