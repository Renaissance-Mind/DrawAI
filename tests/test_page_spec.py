from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from PIL import Image

from drawai.page_spec import (
    fuse_page_specs,
    page_spec_from_candidates,
    validate_page_spec_payload,
    write_page_spec,
)
from drawai.page_spec_assets import materialize_page_spec_assets, materialized_asset_records
from drawai.page_spec_svg import draft_semantic_svg_from_page_spec
from drawai.tooling import drawai_tool_cli


class _FakeProviderImage:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.width = 18
        self.height = 12

    def to_dict(self) -> dict[str, object]:
        return {
            "image_id": self.path.stem,
            "path": str(self.path),
            "source_path": str(self.path),
            "width": self.width,
            "height": self.height,
            "mime_type": "image/png",
        }


class _FakeProviderResult:
    def __init__(self, operation: str, output_dir: Path, path: Path) -> None:
        self.operation = operation
        self.output_dir = output_dir
        self.images = (_FakeProviderImage(path),)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "drawai.test.fake_image_provider.v1",
            "operation": self.operation,
            "output_dir": str(self.output_dir),
            "images": [image.to_dict() for image in self.images],
        }


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
                        "build": {"mode": "editable_text", "processing_type": "no_process"},
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


def test_page_spec_from_candidates_preserves_diagram_kind_with_no_process_default() -> None:
    page_spec = page_spec_from_candidates(
        [
            {
                "candidate_id": "sam:B001",
                "element_type": "diagram",
                "bbox": [2, 3, 10, 12],
                "geometry": {"kind": "bbox", "bbox": [2, 3, 12, 15]},
                "confidence": 0.92,
                "source_parser": "sam3_structure_parser",
            }
        ],
        page_id="page-1",
        source_image="inputs/source.png",
        canvas={"width_px": 24, "height_px": 24},
        producer="sam_parse",
    )

    element = page_spec["elements"][0]
    assert element["kind"] == "diagram"
    assert element["role"] == "diagram"
    assert element["build"] == {"mode": "vector", "processing_type": "no_process"}


def test_fuse_page_specs_defaults_non_asset_build_to_no_process() -> None:
    fused = fuse_page_specs(
        (
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
                        "build": {"mode": "editable_text"},
                    }
                ],
            ),
        ),
        page_id="page-1",
        source_image="inputs/source.png",
    )

    assert fused["elements"][0]["build"] == {
        "mode": "editable_text",
        "processing_type": "no_process",
    }


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
                "build": {"mode": "editable_text", "processing_type": "no_process"},
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


def test_draft_semantic_svg_from_materialized_page_spec_uses_active_asset_href(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGBA", (48, 32), (255, 255, 255, 255)).save(source)
    output_dir = tmp_path / "node" / "output"
    page_spec = _page_spec(
        "refine",
        [
            {
                "id": "E001",
                "kind": "image",
                "role": "picture",
                "box_px": [2, 3, 16, 12],
                "z_index": 5,
                "build": {"mode": "asset_ref", "processing_type": "crop"},
            },
            {
                "id": "E002",
                "kind": "text",
                "role": "text",
                "box_px": [20, 8, 18, 8],
                "z_index": 6,
                "text": "Hello",
                "build": {"mode": "editable_text", "processing_type": "svg_self_draw"},
            },
        ],
    )
    materialized = materialize_page_spec_assets(page_spec, source_image_path=source, output_dir=output_dir)
    page_spec_path = write_page_spec(output_dir / "page_spec.json", materialized)
    svg_path = tmp_path / "nodes" / "svg_compose" / "runs" / "001" / "output" / "semantic.svg"

    result = draft_semantic_svg_from_page_spec(page_spec_path, svg_path, href_base_dir=tmp_path / "svg")

    svg = svg_path.read_text(encoding="utf-8")
    assert result["asset_images"] == 1
    assert 'href="../node/output/assets/E001/active.png"' in svg
    assert 'data-pb-editable="false"' in svg
    assert 'data-drawai-source="crop"' in svg or 'data-drawai-source="image' in svg
    assert ">Hello</text>" in svg


def test_materialize_page_spec_assets_runs_image_generate_and_edit(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGBA", (96, 64), (255, 255, 255, 255)).save(source)
    output_dir = tmp_path / "bundle"
    calls: list[tuple[str, str]] = []

    def fake_generate(**kwargs):
        calls.append(("generate", str(kwargs["prompt"])))
        result_dir = Path(kwargs["output_dir"])
        result_dir.mkdir(parents=True, exist_ok=True)
        result_path = result_dir / "generated.png"
        Image.new("RGBA", (18, 12), (20, 90, 220, 255)).save(result_path)
        return _FakeProviderResult("generate", result_dir, result_path)

    def fake_edit(**kwargs):
        calls.append(("edit", str(kwargs["prompt"])))
        with Image.open(kwargs["source_image_path"]) as crop:
            assert crop.size == (16, 12)
        result_dir = Path(kwargs["output_dir"])
        result_dir.mkdir(parents=True, exist_ok=True)
        result_path = result_dir / "edited.png"
        Image.new("RGBA", (16, 12), (220, 80, 20, 255)).save(result_path)
        return _FakeProviderResult("edit", result_dir, result_path)

    page_spec = _page_spec(
        "refine",
        [
            {
                "id": "E001",
                "kind": "image",
                "role": "representation",
                "box_px": [2, 3, 18, 12],
                "z_index": 1,
                "build": {
                    "mode": "asset_ref",
                    "processing_type": "image_generate",
                    "parameters": {"prompt": "Small blue predictive-state icon."},
                },
                "measurement": {"text": "Future representation"},
            },
            {
                "id": "E002",
                "kind": "image",
                "role": "representation",
                "box_px": [24, 3, 16, 12],
                "z_index": 2,
                "build": {"mode": "asset_ref", "processing_type": "image_edit"},
            },
        ],
    )

    materialized = materialize_page_spec_assets(
        page_spec,
        source_image_path=source,
        output_dir=output_dir,
        image_generate=fake_generate,
        image_edit=fake_edit,
        processor_workers=2,
    )

    assert {call[0] for call in calls} == {"generate", "edit"}
    assert any("Small blue predictive-state icon" in call[1] for call in calls)
    first, second = materialized["elements"]
    assert first["materialization"]["processing_type"] == "image_generate"
    assert second["materialization"]["processing_type"] == "image_edit"
    assert (output_dir / first["materialization"]["outputs"]["active"]["path"]).is_file()
    assert (output_dir / second["materialization"]["outputs"]["active"]["path"]).is_file()


def test_materialize_page_spec_assets_processes_image_elements_in_parallel(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGBA", (96, 64), (255, 255, 255, 255)).save(source)
    output_dir = tmp_path / "bundle"
    barrier = threading.Barrier(2)
    calls: list[str] = []
    calls_lock = threading.Lock()

    def fake_generate(**kwargs):
        with calls_lock:
            calls.append(str(kwargs["prompt"]))
        barrier.wait(timeout=2.0)
        result_dir = Path(kwargs["output_dir"])
        result_dir.mkdir(parents=True, exist_ok=True)
        result_path = result_dir / "generated.png"
        Image.new("RGBA", (18, 12), (20, 90, 220, 255)).save(result_path)
        return _FakeProviderResult("generate", result_dir, result_path)

    page_spec = _page_spec(
        "refine",
        [
            {
                "id": "E001",
                "kind": "image",
                "role": "representation",
                "box_px": [2, 3, 18, 12],
                "z_index": 1,
                "build": {"mode": "asset_ref", "processing_type": "image_generate"},
            },
            {
                "id": "E002",
                "kind": "image",
                "role": "representation",
                "box_px": [24, 3, 18, 12],
                "z_index": 2,
                "build": {"mode": "asset_ref", "processing_type": "image_generate"},
            },
        ],
    )

    materialized = materialize_page_spec_assets(
        page_spec,
        source_image_path=source,
        output_dir=output_dir,
        image_generate=fake_generate,
        processor_workers=2,
    )

    assert len(calls) == 2
    assert [element["materialization"]["status"] for element in materialized["elements"]] == ["ok", "ok"]


def test_materialize_page_spec_assets_defaults_to_bounded_parallel_workers(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGBA", (96, 64), (255, 255, 255, 255)).save(source)
    output_dir = tmp_path / "bundle"
    active_calls = 0
    max_active_calls = 0
    calls_lock = threading.Lock()

    def fake_generate(**kwargs):
        nonlocal active_calls, max_active_calls
        with calls_lock:
            active_calls += 1
            max_active_calls = max(max_active_calls, active_calls)
        time.sleep(0.03)
        with calls_lock:
            active_calls -= 1
        result_dir = Path(kwargs["output_dir"])
        result_dir.mkdir(parents=True, exist_ok=True)
        result_path = result_dir / "generated.png"
        Image.new("RGBA", (18, 12), (20, 90, 220, 255)).save(result_path)
        return _FakeProviderResult("generate", result_dir, result_path)

    page_spec = _page_spec(
        "refine",
        [
            {
                "id": f"E{index:03d}",
                "kind": "image",
                "role": "representation",
                "box_px": [2 + index, 3, 18, 12],
                "z_index": index,
                "build": {"mode": "asset_ref", "processing_type": "image_generate"},
            }
            for index in range(1, 10)
        ],
    )

    materialized = materialize_page_spec_assets(
        page_spec,
        source_image_path=source,
        output_dir=output_dir,
        image_generate=fake_generate,
    )

    assert 1 < max_active_calls <= 4
    assert [element["materialization"]["status"] for element in materialized["elements"]] == ["ok"] * 9


def test_page_spec_svg_draft_tool_promotes_validated_draft_outputs(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    source = tmp_path / "source.png"
    Image.new("RGBA", (48, 32), (255, 255, 255, 255)).save(source)
    output_dir = tmp_path / "node" / "output"
    page_spec = _page_spec(
        "refine",
        [
            {
                "id": "E001",
                "kind": "image",
                "role": "picture",
                "box_px": [2, 3, 16, 12],
                "z_index": 5,
                "build": {"mode": "asset_ref", "processing_type": "crop"},
            },
            {
                "id": "E002",
                "kind": "text",
                "role": "text",
                "box_px": [20, 8, 18, 8],
                "z_index": 6,
                "text": "Hello",
                "build": {"mode": "editable_text", "processing_type": "svg_self_draw"},
            },
        ],
    )
    materialized = materialize_page_spec_assets(page_spec, source_image_path=source, output_dir=output_dir)
    page_spec_path = write_page_spec(output_dir / "page_spec.json", materialized)
    svg_output_dir = tmp_path / "nodes" / "svg_compose" / "runs" / "001" / "output"

    exit_code = drawai_tool_cli(
        [
            "page-spec-svg-draft",
            "--page-spec",
            str(page_spec_path),
            "--svg",
            str(svg_output_dir / "semantic_0.svg"),
            "--href-base-dir",
            str(tmp_path / "svg"),
            "--rendered",
            str(svg_output_dir / "rendered_0.png"),
            "--report",
            str(svg_output_dir / "validation_report_0.json"),
            "--iteration-log-md",
            str(svg_output_dir / "iteration_log.md"),
            "--iteration-log-jsonl",
            str(svg_output_dir / "iteration_log.jsonl"),
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["validation"]["status"] == "ok"
    assert payload["finalized_outputs"]["semantic_svg"] == str(svg_output_dir / "semantic.svg")
    assert (svg_output_dir / "semantic.svg").read_text(encoding="utf-8") == (
        svg_output_dir / "semantic_0.svg"
    ).read_text(encoding="utf-8")
    assert (svg_output_dir / "semantic_svg.svg").read_text(encoding="utf-8") == (
        svg_output_dir / "semantic_0.svg"
    ).read_text(encoding="utf-8")
    assert (svg_output_dir / "rendered.png").is_file()
    assert (svg_output_dir / "validation_report_final.json").is_file()


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
