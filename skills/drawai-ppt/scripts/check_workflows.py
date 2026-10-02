#!/usr/bin/env python3
"""Exercise the documented document-only workflows with real files."""

from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lxml import etree
from pptx import Presentation
from pptx_skill import (
    Document,
    export_pptx,
    export_svg,
    import_pptx,
    import_svg,
    duplicate_page,
)
from pptx_skill.document.identity import IDENTITY_NS

HERE = Path(__file__).resolve().parent


def box(id, kind="shape", **properties):
    return {
        "id": id,
        "kind": kind,
        "properties": {
            "object.name": id,
            "object.frame": {"left": 20, "top": 20, "width": 120, "height": 80},
            **properties,
        },
    }


def document(objects):
    return Document.model_validate(
        {
            "schema": "presentation.document.v1",
            "id": "deck",
            "properties": {"document.page_size": {"width": 720, "height": 405}},
            "pages": [{"id": "page", "objects": objects}],
        }
    )


class Workflows(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_crop_full_keys_short_keys_and_import_contract(self):
        doc = document(
            [
                box(
                    "photo",
                    "picture",
                    **{
                        "picture.asset_ref": "image",
                        "picture.crop": {"left": 0.1, "t": 0.2, "right": 0.05},
                    },
                )
            ]
        )
        doc.assets = {
            "image": {"path": str(HERE.parent / "assets/demo/demo_figure.png")}
        }
        p = self.root / "crop.pptx"
        export_pptx(doc, p)
        s = Presentation(p).slides[0].shapes[0]
        self.assertAlmostEqual(s.crop_left, 0.1)
        self.assertAlmostEqual(s.crop_top, 0.2)
        self.assertEqual(
            set(import_pptx(p).pages[0].objects[0].properties["picture.crop"]),
            {"left", "top", "right", "bottom"},
        )

    def test_identity_aliases_create_and_conflicts_reject(self):
        raw = {"kind": "shape", "id": "a", "properties": {"object.id": "b"}}
        with self.assertRaisesRegex(ValueError, "conflicts"):
            document([raw])
        d = document(
            [
                {
                    "properties": {
                        "object.id": "text",
                        "object.kind": "text_box",
                        "object.frame": {
                            "left": 10,
                            "top": 10,
                            "width": 200,
                            "height": 50,
                        },
                        "text.body.paragraphs": [{"content": [{"text": "Title"}]}],
                    }
                }
            ]
        )
        p = self.root / "alias.pptx"
        export_pptx(d, p)
        self.assertEqual(Presentation(p).slides[0].shapes[0].shape_type, 17)
        d.pages[0].objects[0].properties["object.id"] = "different"
        with self.assertRaisesRegex(ValueError, "conflicts"):
            export_pptx(d, self.root / "bad.pptx")
        self.assertFalse((self.root / "bad.pptx").exists())

    def test_clear_format_survives_text_reconstruction(self):
        d = document(
            [
                box(
                    "title",
                    "text_box",
                    **{
                        "text.body.paragraphs": [
                            {
                                "content": [
                                    {
                                        "text": "Original",
                                        "properties": {"text.run.font.bold": True},
                                    }
                                ]
                            }
                        ]
                    },
                )
            ]
        )
        p = self.root / "bold.pptx"
        export_pptx(d, p)
        d = import_pptx(p)
        o = d.pages[0].objects[0]
        o.clear_overrides = ["text.run.font.bold"]
        o.properties["text.body.paragraphs"][0]["content"][0]["text"] = "Updated"
        q = self.root / "updated.pptx"
        export_pptx(d, q)
        r = Presentation(q).slides[0].shapes[0].text_frame.paragraphs[0].runs[0]
        self.assertEqual(r.text, "Updated")
        self.assertIsNone(r.font.bold)

    def test_existing_page_and_group_stacking_order(self):
        group = box("group", "group")
        group["children"] = [box("child-back"), box("child-front")]
        p = self.root / "layers.pptx"
        export_pptx(document([box("back"), box("front"), group]), p)
        d = import_pptx(p)
        d.pages[0].objects[0].properties["object.z_order"] = 3
        d.pages[0].objects[1].properties["object.z_order"] = 1
        d.pages[0].objects[2].properties["object.z_order"] = 2
        d.pages[0].objects[2].children[0].properties["object.z_order"] = 2
        d.pages[0].objects[2].children[1].properties["object.z_order"] = 1
        q = self.root / "layers-updated.pptx"
        export_pptx(d, q)
        s = Presentation(q).slides[0].shapes
        self.assertEqual([o.name for o in s], ["front", "group", "back"])
        self.assertEqual([o.name for o in s[1].shapes], ["child-front", "child-back"])

    def test_copy_and_import_duplicate_extension_ids(self):
        p = self.root / "source.pptx"
        export_pptx(document([box("shape")]), p)
        d = duplicate_page(import_pptx(p), "page", new_id="copy")
        q = self.root / "copied.pptx"
        export_pptx(d, q)
        self.assertEqual(
            len({o.id for page in import_pptx(q).pages for o in page.objects}), 2
        )
        with zipfile.ZipFile(q) as z:
            parts = {n: z.read(n) for n in z.namelist()}
        first = etree.fromstring(parts["ppt/slides/slide1.xml"])
        second = etree.fromstring(parts["ppt/slides/slide2.xml"])
        for a, b in zip(
            first.iter("{" + IDENTITY_NS + "}identity"),
            second.iter("{" + IDENTITY_NS + "}identity"),
            strict=True,
        ):
            b.set("id", a.get("id"))
        parts["ppt/slides/slide2.xml"] = etree.tostring(second)
        modified = self.root / "editor-copy.pptx"
        with zipfile.ZipFile(modified, "w") as z:
            for n, b in parts.items():
                z.writestr(n, b)
        restored = import_pptx(modified)
        self.assertEqual(len({p.id for p in restored.pages}), 2)
        self.assertEqual(len({o.id for p in restored.pages for o in p.objects}), 2)

    @unittest.skipUnless(shutil.which("soffice"), "SVG projection needs LibreOffice")
    def test_page_svg_recovers_full_source_with_page_bindings(self):
        d = document([box("a")])
        raw = d.model_dump(by_alias=True)
        raw["pages"].append({"id": "page-B", "objects": [box("b")]})
        raw["native_bindings"] = [
            {
                "owner_id": "page-B",
                "property_id": "slide.name",
                "part": "ppt/slides/slide2.xml",
                "xpath": "/p:sld/p:cSld",
                "action": "set_attribute",
                "name": "name",
                "value": "Bound B",
            }
        ]
        d = Document.model_validate(raw)
        r = export_svg(d, self.root / "svg")
        recovered, report = import_svg(Path(r["pages"][0]["svg"]))
        self.assertEqual(
            recovered.model_dump(by_alias=True), d.model_dump(by_alias=True)
        )
        self.assertEqual(report["source_scope"], "full_document")
        self.assertEqual(report["projection_page_id"], "page")
        p = self.root / "recovered.pptx"
        export_pptx(recovered, p)
        self.assertEqual(Presentation(p).slides[1]._element.cSld.get("name"), "Bound B")

    def test_cli_retains_svg_report_and_queries_properties(self):
        svg = HERE.parent / "assets/demo/formula.svg"
        out = self.root / "import.json"
        report = self.root / "import-report.json"
        run = subprocess.run(
            [
                sys.executable,
                "-I",
                str(HERE / "ppt.py"),
                "import",
                str(svg),
                "--output",
                str(out),
                "--report",
                str(report),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        result = json.loads(run.stdout)
        self.assertIn("backend", result["conversion"])
        self.assertEqual(json.loads(report.read_text()), result)
        run = subprocess.run(
            [
                sys.executable,
                "-I",
                str(HERE / "ppt.py"),
                "capabilities",
                "--property",
                "picture.crop",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(
            [p["id"] for p in json.loads(run.stdout)["properties"]], ["picture.crop"]
        )

    def test_complete_example_create_and_edit(self):
        create = self.root / "create"
        edit = self.root / "edit"
        subprocess.run(
            [sys.executable, "-I", str(HERE / "example.py"), str(create)],
            capture_output=True,
            text=True,
            check=True,
        )
        subprocess.run(
            [
                sys.executable,
                "-I",
                str(HERE / "example.py"),
                str(edit),
                "--source",
                str(create / "deck.pptx"),
                "--object-id",
                "heading",
                "--find",
                "Original ",
                "--text",
                "Updated ",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        runs = (
            Presentation(edit / "deck.pptx")
            .slides[0]
            .shapes[0]
            .text_frame.paragraphs[0]
            .runs
        )
        self.assertEqual(runs[0].text, "Updated ")
        self.assertTrue(runs[0].font.bold)
        self.assertTrue(runs[1].font.italic)


if __name__ == "__main__":
    unittest.main(verbosity=2)
