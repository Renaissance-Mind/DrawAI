import base64
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import drawai.svg_to_ppt as svg_to_ppt
from drawai.svg_to_ppt import SvgToPptCompiler, prepare_svg_for_ppt_input


def test_prepare_svg_for_ppt_input_renames_reserved_background_id(tmp_path):
    source = tmp_path / "semantic_standalone.svg"
    source.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
  <rect id="page_background" width="100" height="100" fill="#fff"/>
  <rect id="content" width="10" height="10" fill="url(#page_background)"/>
</svg>""",
        encoding="utf-8",
    )

    prepared, report = prepare_svg_for_ppt_input(source)

    assert prepared == tmp_path / "semantic_standalone.svg_to_ppt.svg"
    prepared_text = prepared.read_text(encoding="utf-8")
    assert 'id="canvas_background"' in prepared_text
    assert "url(#canvas_background)" in prepared_text
    assert "page_background" not in prepared_text
    assert report == {
        "status": "rewritten",
        "source_svg": str(source),
        "prepared_svg": str(prepared),
        "id_rewrites": [{"old_id": "page_background", "new_id": "canvas_background"}],
    }


def test_prepare_svg_for_ppt_input_renames_non_page_objects_with_page_token(tmp_path):
    source = tmp_path / "semantic_standalone.svg"
    source.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
  <rect id="canvas_background" width="100" height="100" fill="#fff"/>
  <g id="prompt_document_icon_bottom_page">
    <rect id="prompt_document_icon_bottom_page_inner" width="10" height="10" fill="#000"/>
  </g>
  <use id="safe_use" href="#prompt_document_icon_bottom_page"/>
</svg>""",
        encoding="utf-8",
    )

    prepared, report = prepare_svg_for_ppt_input(source)

    prepared_text = prepared.read_text(encoding="utf-8")
    assert "prompt_document_icon_bottom_page" not in prepared_text
    assert 'id="svg_to_ppt_object"' in prepared_text
    assert 'id="svg_to_ppt_object_2"' in prepared_text
    assert 'href="#svg_to_ppt_object"' in prepared_text
    assert report["id_rewrites"] == [
        {"old_id": "prompt_document_icon_bottom_page", "new_id": "svg_to_ppt_object"},
        {"old_id": "prompt_document_icon_bottom_page_inner", "new_id": "svg_to_ppt_object_2"},
    ]


def test_prepare_svg_for_ppt_input_keeps_safe_svg_in_place(tmp_path):
    source = tmp_path / "semantic_standalone.svg"
    source.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
  <rect id="canvas_background" width="100" height="100" fill="#fff"/>
  <rect id="content" width="10" height="10" fill="#000"/>
</svg>""",
        encoding="utf-8",
    )

    prepared, report = prepare_svg_for_ppt_input(source)

    assert prepared == source
    assert report == {
        "status": "unchanged",
        "source_svg": str(source),
        "prepared_svg": str(source),
        "id_rewrites": [],
    }


def test_prepare_svg_for_ppt_input_expands_tspan_dy_to_absolute_y(tmp_path):
    source = tmp_path / "semantic_standalone.svg"
    source.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200">
  <text id="paragraph" x="35" y="80" font-family="Comic Sans MS" font-size="20">
    <tspan x="35" dy="0">Line one</tspan>
    <tspan x="35" dy="23">Line two</tspan>
    <tspan x="35" dy="23" font-weight="700">Line three</tspan>
  </text>
</svg>""",
        encoding="utf-8",
    )

    prepared, report = prepare_svg_for_ppt_input(source)

    prepared_text = prepared.read_text(encoding="utf-8")
    assert 'dy="0"' not in prepared_text
    assert 'dy="23"' not in prepared_text
    assert 'y="80"' in prepared_text
    assert 'y="103"' in prepared_text
    assert 'y="126"' in prepared_text
    assert report["tspan_position_normalizations"] == [{"text_id": "paragraph", "tspan_count": 3}]


def test_prepare_svg_for_ppt_input_materializes_positioned_tspan_text_attrs(tmp_path):
    source = tmp_path / "semantic_standalone.svg"
    source.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200">
  <text id="paragraph" x="200" y="80" text-anchor="middle" font-family="Arial" font-size="20" fill="#111111" font-weight="700">
    <tspan x="200" y="80" textLength="48">ABCD</tspan>
    <tspan x="200" y="106" fill="#222222" textLength="48">WXYZ</tspan>
    <tspan>inline emphasis</tspan>
  </text>
</svg>""",
        encoding="utf-8",
    )

    prepared, report = prepare_svg_for_ppt_input(source)

    root = ElementTree.fromstring(prepared.read_text(encoding="utf-8"))
    tspans = [element for element in root.iter() if element.tag.endswith("tspan")]
    assert tspans[0].attrib == {
        "x": "176",
        "y": "80",
        "text-anchor": "start",
        "font-family": "Arial",
        "font-size": "20",
        "fill": "#111111",
        "font-weight": "700",
        "textLength": "48",
    }
    assert tspans[1].attrib == {
        "x": "176",
        "y": "106",
        "fill": "#222222",
        "text-anchor": "start",
        "font-family": "Arial",
        "font-size": "20",
        "font-weight": "700",
        "textLength": "48",
    }
    assert tspans[2].attrib == {}
    assert report["tspan_attribute_normalizations"] == [
        {
            "text_id": "paragraph",
            "tspan_count": 2,
            "attributes": ["fill", "font-family", "font-size", "font-weight", "text-anchor"],
        }
    ]
    assert report["tspan_anchor_normalizations"] == [
        {
            "text_id": "paragraph",
            "tspans": [
                {"text": "ABCD", "anchor": "middle", "x_source": "tspan_x", "old_x": 200.0, "new_x": 176.0, "estimated_width": 48.0},
                {"text": "WXYZ", "anchor": "middle", "x_source": "tspan_x", "old_x": 200.0, "new_x": 176.0, "estimated_width": 48.0},
            ],
        }
    ]


def test_prepare_svg_for_ppt_input_expands_straight_marker_endings(tmp_path):
    source = tmp_path / "arrow.svg"
    source.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" width="120" height="80" viewBox="0 0 120 80">
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="4" markerHeight="4" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="context-stroke"/>
    </marker>
  </defs>
  <line id="flow" x1="10" y1="40" x2="100" y2="40" stroke="#d57945" stroke-width="5" marker-end="url(#arrow)"/>
</svg>""",
        encoding="utf-8",
    )

    prepared, report = prepare_svg_for_ppt_input(source)

    prepared_text = prepared.read_text(encoding="utf-8")
    assert 'marker-end="url(#arrow)"' not in prepared_text
    assert 'data-drawai-svg_to_ppt-marker="arrow"' in prepared_text
    assert report["marker_expansions"] == [
        {"element_id": "flow", "marker_id": "arrow", "position": "end", "polygon_id": "flow_marker_end_arrow"}
    ]


def test_prepare_svg_for_ppt_input_leaves_curved_marker_for_converter(tmp_path):
    source = tmp_path / "curved_arrow.svg"
    source.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" width="120" height="80" viewBox="0 0 120 80">
  <defs>
    <marker id="curved-marker" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="4" markerHeight="4" orient="auto">
      <path d="M 0 0 C 4 2 8 4 10 5 C 8 6 4 8 0 10 z" fill="context-stroke"/>
    </marker>
  </defs>
  <line id="flow" x1="10" y1="40" x2="100" y2="40" stroke="#d57945" stroke-width="5" marker-end="url(#curved-marker)"/>
</svg>""",
        encoding="utf-8",
    )

    prepared, report = prepare_svg_for_ppt_input(source)

    assert prepared == source
    assert report["status"] == "unchanged"
    assert "marker_expansions" not in report
    assert 'marker-end="url(#curved-marker)"' in source.read_text(encoding="utf-8")


def test_svg_to_ppt_compiler_uses_native_shape_converter(tmp_path):
    source = tmp_path / "semantic.svg"
    source.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 360">
  <rect x="0" y="0" width="640" height="360" fill="#ffffff"/>
  <rect x="32" y="40" width="160" height="90" fill="#dceeff" stroke="#2563eb"/>
  <text x="48" y="92" font-size="24" fill="#111827">DrawAI</text>
</svg>""",
        encoding="utf-8",
    )
    output = tmp_path / "semantic.pptx"
    report_path = tmp_path / "svg_to_ppt_report.json"

    compiler = SvgToPptCompiler()
    report = compiler.compile(svg_path=source, output_path=output, report_path=report_path)

    assert compiler.backend == "drawai_native_shapes"
    assert output.exists()
    assert report_path.exists()
    assert report["backend"] == "drawai_native_shapes"
    assert report["editable_surface"] == "native_shapes"
    assert report["requested_export_mode"] == "native_shapes"
    assert report["effective_export_mode"] == "native_shapes"
    assert report["pptx_structure"]["slide_count"] == 1
    assert not report["pptx_structure"]["is_single_screenshot_like"]
    assert Path(report["conversion_trace_path"]).exists()


def test_svg_to_ppt_compiler_promotes_latex_formula_metadata_to_office_math(tmp_path, monkeypatch):
    latex = r"\int_0^\infty e^{-x^2}\,dx = \frac{\sqrt{\pi}}{2}"
    latex_b64 = base64.b64encode(latex.encode("utf-8")).decode("ascii")
    source = tmp_path / "semantic.svg"
    source.write_text(
        f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 360">
  <rect x="0" y="0" width="640" height="360" fill="#ffffff"/>
  <g id="formula-gaussian" data-pb-role="formula" data-pb-editable="true"
     data-pb-formula-latex-b64="{latex_b64}" data-pb-formula-bbox="170 130 300 70">
    <text x="170" y="176" font-family="Times New Roman, Times, serif" font-size="28"
          fill="#0070c0" font-weight="700" font-style="italic" data-pb-role="formula"
          data-pb-editable="true" data-pb-text-source="model_inferred"
          data-pb-orientation="horizontal">SVG fallback formula only</text>
  </g>
  <text x="42" y="72" font-size="24" fill="#111827">Gaussian integral</text>
</svg>""",
        encoding="utf-8",
    )
    output = tmp_path / "semantic.pptx"
    report_path = tmp_path / "svg_to_ppt_report.json"
    converted_latex: list[str] = []

    def fake_latex_to_omml(value: str) -> str:
        converted_latex.append(value)
        return (
            '<a14:m xmlns:a14="http://schemas.microsoft.com/office/drawing/2010/main">'
            '<m:oMathPara xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">'
            "<m:oMath><m:r><m:t>converted office math</m:t></m:r></m:oMath>"
            "</m:oMathPara>"
            "</a14:m>"
        )

    monkeypatch.setattr(svg_to_ppt, "_latex_to_omml", fake_latex_to_omml)

    report = SvgToPptCompiler().compile(svg_path=source, output_path=output, report_path=report_path)

    assert converted_latex == [latex]
    assert report["editable_surface"] == "native_shapes+office_math"
    assert report["formula_export"]["status"] == "ok"
    assert report["formula_export"]["count"] == 1
    assert report["formula_export"]["converted"] == 1
    assert report["formula_export"]["fallback"] == 0
    stripped_svg = Path(report["prepared_svg"])
    assert stripped_svg.exists()
    assert "SVG fallback formula only" not in stripped_svg.read_text(encoding="utf-8")

    with zipfile.ZipFile(output) as archive:
        slide_xml = archive.read("ppt/slides/slide1.xml").decode("utf-8")
    assert "<mc:AlternateContent" in slide_xml
    formula_start = slide_xml.index('name="DrawAI formula formula-gaussian"')
    formula_xml = slide_xml[formula_start : slide_xml.index("</mc:AlternateContent>", formula_start)]
    assert 'wrap="none" anchor="ctr" rtlCol="0" lIns="0" tIns="0" rIns="0" bIns="0"' in formula_xml
    assert "<a:noAutofit" in formula_xml
    assert "<a:spAutoFit" not in formula_xml
    assert '<a:defRPr sz="2800" b="1" i="1">' in formula_xml
    assert '<a:srgbClr val="0070C0"' in formula_xml
    assert '<a:latin typeface="Times New Roman"' in formula_xml
    assert '<m:sty m:val="bi"' in formula_xml
    assert "<m:oMathPara" in slide_xml
    assert "converted office math" in slide_xml
    assert "SVG fallback formula only" not in slide_xml


def test_formula_collection_corrects_misaligned_formula_bbox_from_fallback_text(tmp_path):
    latex = r"p_0"
    latex_b64 = base64.b64encode(latex.encode("utf-8")).decode("ascii")
    source = tmp_path / "semantic.svg"
    source.write_text(
        f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2000 800">
  <g id="legend-transport-p0" data-pb-role="formula" data-pb-editable="true"
     data-pb-formula-latex-b64="{latex_b64}" data-pb-formula-bbox="1936 9 24 15">
    <text id="legend-transport-p0-fallback" x="1936" y="104"
          font-family="Times New Roman, Times, serif" font-size="13" fill="#000000"
          data-pb-editable="true" data-pb-role="formula" data-pb-text-source="visual_inferred"
          data-pb-orientation="horizontal" font-weight="700" font-style="italic">p<tspan
          baseline-shift="sub" font-size="8">0</tspan></text>
  </g>
</svg>""",
        encoding="utf-8",
    )

    specs, report = svg_to_ppt._collect_svg_formula_specs(source)

    assert len(specs) == 1
    assert specs[0].element_id == "legend-transport-p0"
    assert specs[0].bbox[0] == 1936
    assert 88 <= specs[0].bbox[1] <= 96
    assert specs[0].bbox[2] > 8
    assert specs[0].bbox[3] > 10
    assert report["items"][0]["bbox"] == list(specs[0].bbox)
    assert report["bbox_corrections"] == [
        {
            "element_id": "legend-transport-p0",
            "old_bbox": [1936.0, 9.0, 24.0, 15.0],
            "new_bbox": list(specs[0].bbox),
            "reason": "fallback_text_bbox_misaligned",
        }
    ]
