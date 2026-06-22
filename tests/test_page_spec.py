from __future__ import annotations

from pathlib import Path

from PIL import Image

from drawai.page_spec import fuse_page_specs, validate_page_spec_payload, write_page_spec
from drawai.page_spec_assets import materialize_page_spec_assets, materialized_asset_records


def test_fuse_page_specs_outputs_page_spec_elements_without_legacy_payloads() -> None:
    fused = fuse_page_specs(
        (
            _page_spec(
                "sam",
                [
                    {
                        "id": "S001",
                        "kind": "image",
                        "role": "picture",
                        "box_px": [2, 3, 10, 12],
                        "z_index": 5,
                        "confidence": 0.92,
                        "build": {"mode": "asset_ref", "processing_type": "crop"},
                        "source_refs": [{"kind": "candidate", "id": "sam:B001"}],
                    }
                ],
            ),
            _page_spec(
                "ocr",
                [
                    {
                        "id": "T001",
                        "kind": "text",
                        "role": "text",
                        "box_px": [4, 5, 8, 3],
                        "z_index": 6,
                        "text": "Hello",
                        "build": {"mode": "editable_text", "processing_type": "svg_self_draw"},
                        "source_refs": [{"kind": "candidate", "id": "ocr:T001"}],
                    }
                ],
            ),
        ),
        page_id="page-1",
        source_image="inputs/source.png",
    )

    validate_page_spec_payload(fused)
    assert [element["id"] for element in fused["elements"]] == ["E001", "E002"]
    assert fused["elements"][0]["build"]["processing_type"] == "crop"
    assert "candidate_payload" not in fused["elements"][0]["metadata"]
    assert fused["metadata"] == {}


def test_materialize_page_spec_assets_writes_bundle_relative_paths(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGBA", (24, 24), (255, 255, 255, 255)).save(source)
    output_dir = tmp_path / "node" / "output"
    page_spec = _page_spec(
        "refine",
        [
            {
                "id": "E001",
                "kind": "image",
                "role": "picture",
                "box_px": [2, 3, 10, 12],
                "z_index": 5,
                "build": {"mode": "asset_ref", "processing_type": "crop"},
                "source_refs": [{"kind": "page_spec_element", "id": "S001"}],
            },
            {
                "id": "E002",
                "kind": "text",
                "role": "text",
                "box_px": [1, 1, 4, 4],
                "build": {"mode": "editable_text", "processing_type": "svg_self_draw"},
            },
        ],
    )

    materialized = materialize_page_spec_assets(page_spec, source_image_path=source, output_dir=output_dir)
    page_spec_path = write_page_spec(output_dir / "page_spec.json", materialized)

    element = materialized["elements"][0]
    assert element["materialization"]["outputs"]["active"]["path"] == "assets/E001/active.png"
    assert (output_dir / "assets" / "E001" / "active.png").is_file()
    assert "materialization" not in materialized["elements"][1]
    records = materialized_asset_records(page_spec_path, svg_dir=tmp_path / "svg")
    assert records[0]["element_id"] == "E001"
    assert records[0]["svg_href"].endswith("node/output/assets/E001/crop.png")


def _page_spec(source: str, elements: list[dict[str, object]]) -> dict[str, object]:
    return {
        "schema": "drawai.page_spec.v1",
        "page_id": "page-1",
        "source": {"image": "inputs/source.png", "width_px": 24, "height_px": 24},
        "canvas": {"width_px": 24, "height_px": 24},
        "background": {},
        "elements": elements,
        "metadata": {"source": source},
    }
