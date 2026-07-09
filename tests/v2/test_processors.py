from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from drawai.rmbg_client import RmbgResult
from drawai.v2.compat import write_asset_manifest_compat
from drawai.v2.packages import read_asset_package
from drawai.v2.processors import (
    ChartRebuildReservedProcessor,
    CropNoBgProcessor,
    CropProcessor,
    ImageEditProcessor,
    ImageGenerateProcessor,
    NoProcessProcessor,
    SvgSelfDrawProcessor,
    processor_for_type,
)
from drawai.v2.schema import ElementPlan, ProcessingIntent


class FakeRmbgClient:
    def remove_background(
        self,
        image: Image.Image,
        output_name: str,
        *,
        timeout_s: float,
        model_path: str = "",
        artifact_prefix: str | None = None,
    ) -> RmbgResult:
        rgba = image.convert("RGBA")
        rgba.putpixel((0, 0), (255, 255, 255, 0))
        return RmbgResult(
            image=rgba,
            elapsed_ms=12.0,
            artifacts={"output_name": output_name},
        )


@dataclass(frozen=True)
class FakeGeneratedImage:
    image_id: str
    path: Path
    width: int
    height: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "image_id": self.image_id,
            "status": "completed",
            "path": str(self.path),
            "source_path": str(self.path),
            "revised_prompt": "fake revised prompt",
            "mime_type": "image/png",
            "width": self.width,
            "height": self.height,
            "bytes": self.path.stat().st_size,
            "sha256": "fake-sha",
        }


@dataclass(frozen=True)
class FakeImageGenResult:
    operation: str
    prompt: str
    output_dir: Path
    images: tuple[FakeGeneratedImage, ...]
    source_image_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "drawai.codex_python_sdk_imagegen_result.v1",
            "runner": "fake_imagegen",
            "task_name": f"drawai.v2.fake.{self.operation}.v1",
            "operation": self.operation,
            "prompt": self.prompt,
            "source_image_path": str(self.source_image_path)
            if self.source_image_path is not None
            else None,
            "output_dir": str(self.output_dir),
            "images": [image.to_dict() for image in self.images],
        }


def test_crop_processor_writes_asset_package_result(tmp_path: Path) -> None:
    source_path = _write_figure(tmp_path)

    CropProcessor().process(tmp_path, _plan("crop"), source_image_path=source_path)

    package = read_asset_package(tmp_path, "E001")
    assert package["status"] == "ok"
    assert package["active_result"]
    assert (tmp_path / package["active_result"]["path"]).exists()
    assert package["active_result"]["metadata"]["crop_bbox_xyxy"] == [2, 2, 14, 14]


def test_crop_asset_manifest_uses_svg_relative_href_and_bbox(tmp_path: Path) -> None:
    source_path = _write_figure(tmp_path)

    CropProcessor().process(tmp_path, _plan("crop"), source_image_path=source_path)
    manifest = write_asset_manifest_compat(tmp_path, [read_asset_package(tmp_path, "E001")])

    asset = manifest["assets"][0]
    assert asset["path"].startswith("elements/E001/results/")
    assert asset["svg_href"] == f"../{asset['path']}"
    assert asset["bbox"] == [2, 2, 14, 14]


def test_crop_processor_records_relative_source_refs_on_failure(tmp_path: Path) -> None:
    _write_figure(tmp_path)
    plan = _plan("crop", bbox=(20.0, 20.0, 4.0, 4.0), geometry={"kind": "bbox", "bbox": [20, 20, 24, 24]})

    with pytest.raises(ValueError, match="invalid crop bounds"):
        CropProcessor().process(
            tmp_path,
            plan,
            source_image_path=Path("inputs") / "figure.png",
        )

    package = read_asset_package(tmp_path, "E001")
    assert package["processor_runs"][0]["input_refs"]["source_image"] == "inputs/figure.png"


def test_crop_nobg_processor_records_rmbg_metadata(tmp_path: Path) -> None:
    source_path = _write_figure(tmp_path)

    CropNoBgProcessor(rmbg_client=FakeRmbgClient()).process(
        tmp_path,
        _plan("crop_nobg"),
        source_image_path=source_path,
    )

    package = read_asset_package(tmp_path, "E001")
    assert package["status"] == "ok"
    assert package["processor_runs"][0]["processor_type"] == "crop_nobg"
    assert package["all_results"][0]["metadata"]["rmbg_elapsed_ms"] == 12.0
    with Image.open(tmp_path / package["active_result"]["path"]) as image:
        assert image.getpixel((0, 0))[3] == 0


def test_svg_self_draw_processor_creates_editable_payload(tmp_path: Path) -> None:
    SvgSelfDrawProcessor().process(tmp_path, _plan("svg_self_draw"))

    package = read_asset_package(tmp_path, "E001")
    assert package["status"] == "ok"
    assert package["editable_payload"]["kind"] == "svg_self_draw_constraints"
    assert package["editable_payload"]["element_id"] == "E001"


def test_no_process_processor_writes_empty_ok_package(tmp_path: Path) -> None:
    NoProcessProcessor().process(tmp_path, _plan("no_process"))

    package = read_asset_package(tmp_path, "E001")
    assert package["status"] == "ok"
    assert package["processor_type"] == "no_process"
    assert package["files"] == []
    assert package["active_result"] is None
    assert "does not require asset materialization" in package["metadata"]["last_run_metadata"]["reason"]
    assert package["processor_runs"][0]["output_refs"] == {}


def test_chart_reserved_processor_is_unsupported(tmp_path: Path) -> None:
    ChartRebuildReservedProcessor().process(tmp_path, _plan("chart_rebuild_reserved"))

    package = read_asset_package(tmp_path, "E001")
    assert package["status"] == "unsupported"
    assert "reserved" in package["failure"]


def test_processor_failure_writes_failed_package_before_reraising(tmp_path: Path) -> None:
    source_path = _write_figure(tmp_path, size=(10, 10))
    plan = _plan("crop", bbox=(20.0, 20.0, 4.0, 4.0), geometry={"kind": "bbox", "bbox": [20, 20, 24, 24]})

    with pytest.raises(ValueError, match="invalid crop bounds"):
        CropProcessor().process(tmp_path, plan, source_image_path=source_path)

    package = read_asset_package(tmp_path, "E001")
    assert package["status"] == "failed"
    assert "invalid crop bounds" in package["failure"]
    assert package["processor_runs"][0]["status"] == "failed"


def test_crop_processor_rejects_mask_paths_outside_run_root(tmp_path: Path) -> None:
    for case_name, raw_mask_path in (
        ("traversal", "../traversal_mask.png"),
        ("absolute", None),
    ):
        root = tmp_path / case_name
        source_path = _write_figure(root)
        outside_mask = tmp_path / f"{case_name}_mask.png"
        Image.new("L", (20, 20), 255).save(outside_mask)
        mask_path = str(outside_mask) if raw_mask_path is None else raw_mask_path
        plan = _plan(
            "crop",
            geometry={"kind": "mask", "mask_path": mask_path, "bbox": [2, 2, 14, 14]},
        )

        with pytest.raises(ValueError, match="mask_path.*run root"):
            CropProcessor().process(root, plan, source_image_path=source_path)

        package = read_asset_package(root, "E001")
        assert package["status"] == "failed"
        assert "mask_path" in package["failure"]


def test_image_generate_processor_records_provider_metadata(tmp_path: Path) -> None:
    calls: list[dict[str, Any]] = []

    def fake_generate(**kwargs: Any) -> FakeImageGenResult:
        calls.append(kwargs)
        output_dir = Path(kwargs["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        image_path = output_dir / "generated.png"
        Image.new("RGBA", (16, 10), (20, 90, 220, 255)).save(image_path)
        return FakeImageGenResult(
            operation="generate",
            prompt=str(kwargs["prompt"]),
            output_dir=output_dir,
            images=(FakeGeneratedImage("generated", image_path, 16, 10),),
        )

    plan = _plan(
        "image_generate",
        parameters={"prompt": "draw a blue scientific icon", "quality": "high"},
    )
    ImageGenerateProcessor(image_generate=fake_generate).process(tmp_path, plan)

    package = read_asset_package(tmp_path, "E001")
    assert package["status"] == "ok"
    assert calls[0]["prompt"] == "draw a blue scientific icon"
    assert (tmp_path / package["active_result"]["path"]).exists()
    assert package["all_results"][0]["metadata"]["provider"]["operation"] == "generate"
    provider_image_path = package["all_results"][0]["metadata"]["provider"]["images"][0]["path"]
    assert provider_image_path.startswith("elements/E001/results/")
    assert tmp_path.as_posix() not in provider_image_path


def test_image_generate_processor_rejects_provider_output_outside_result_dir(tmp_path: Path) -> None:
    source_path = _write_figure(tmp_path)

    def fake_generate(**kwargs: Any) -> FakeImageGenResult:
        output_dir = Path(kwargs["output_dir"])
        return FakeImageGenResult(
            operation="generate",
            prompt=str(kwargs["prompt"]),
            output_dir=output_dir,
            images=(FakeGeneratedImage("wrong-place", source_path, 20, 20),),
        )

    plan = _plan("image_generate", parameters={"prompt": "draw a clean icon"})
    with pytest.raises(ValueError, match="result directory"):
        ImageGenerateProcessor(image_generate=fake_generate).process(tmp_path, plan)

    package = read_asset_package(tmp_path, "E001")
    assert package["status"] == "failed"
    assert "result directory" in package["failure"]


def test_image_generate_package_write_failure_persists_failed_package(tmp_path: Path) -> None:
    class BadMetadataResult(FakeImageGenResult):
        def to_dict(self) -> dict[str, Any]:
            payload = super().to_dict()
            payload["opaque"] = object()
            return payload

    def fake_generate(**kwargs: Any) -> BadMetadataResult:
        output_dir = Path(kwargs["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        image_path = output_dir / "generated.png"
        Image.new("RGBA", (16, 10), (20, 90, 220, 255)).save(image_path)
        return BadMetadataResult(
            operation="generate",
            prompt=str(kwargs["prompt"]),
            output_dir=output_dir,
            images=(FakeGeneratedImage("generated", image_path, 16, 10),),
        )

    plan = _plan("image_generate", parameters={"prompt": "draw a clean icon"})
    with pytest.raises(Exception, match="JSON"):
        ImageGenerateProcessor(image_generate=fake_generate).process(tmp_path, plan)

    package = read_asset_package(tmp_path, "E001")
    assert package["status"] == "failed"
    assert "JSON" in package["failure"]


def test_image_edit_processor_crops_source_before_calling_provider(tmp_path: Path) -> None:
    source_path = _write_figure(tmp_path)
    calls: list[dict[str, Any]] = []

    def fake_edit(**kwargs: Any) -> FakeImageGenResult:
        calls.append(kwargs)
        source_image_path = Path(kwargs["source_image_path"])
        with Image.open(source_image_path) as image:
            assert image.size == (12, 12)
        output_dir = Path(kwargs["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        image_path = output_dir / "edited.png"
        Image.new("RGBA", (12, 12), (0, 200, 140, 255)).save(image_path)
        return FakeImageGenResult(
            operation="edit",
            prompt=str(kwargs["prompt"]),
            output_dir=output_dir,
            source_image_path=source_image_path,
            images=(FakeGeneratedImage("edited", image_path, 12, 12),),
        )

    plan = _plan("image_edit", parameters={"prompt": "simplify this icon"})
    ImageEditProcessor(image_edit=fake_edit).process(
        tmp_path,
        plan,
        source_image_path=source_path,
    )

    package = read_asset_package(tmp_path, "E001")
    assert package["status"] == "ok"
    assert calls[0]["prompt"] == "simplify this icon"
    assert (tmp_path / package["active_result"]["path"]).exists()
    assert "elements/E001/results/" in package["files"][0]
    assert any(path.endswith("/source.png") for path in package["files"])
    assert package["all_results"][0]["metadata"]["provider"]["operation"] == "edit"


def test_image_edit_processor_rejects_provider_output_in_other_result_dir(tmp_path: Path) -> None:
    source_path = _write_figure(tmp_path)
    other_result_dir = tmp_path / "elements" / "E999" / "results" / "other"
    other_result_dir.mkdir(parents=True)
    other_image_path = other_result_dir / "edited.png"
    Image.new("RGBA", (12, 12), (0, 200, 140, 255)).save(other_image_path)

    def fake_edit(**kwargs: Any) -> FakeImageGenResult:
        output_dir = Path(kwargs["output_dir"])
        return FakeImageGenResult(
            operation="edit",
            prompt=str(kwargs["prompt"]),
            output_dir=output_dir,
            source_image_path=Path(kwargs["source_image_path"]),
            images=(FakeGeneratedImage("wrong-result", other_image_path, 12, 12),),
        )

    plan = _plan("image_edit", parameters={"prompt": "simplify this icon"})
    with pytest.raises(ValueError, match="result directory"):
        ImageEditProcessor(image_edit=fake_edit).process(
            tmp_path,
            plan,
            source_image_path=source_path,
        )

    package = read_asset_package(tmp_path, "E001")
    assert package["status"] == "failed"
    assert "result directory" in package["failure"]


def test_processor_for_type_uses_provider_dependencies() -> None:
    rmbg_client = FakeRmbgClient()

    assert isinstance(processor_for_type("no_process", {}), NoProcessProcessor)
    assert isinstance(processor_for_type("crop", {}), CropProcessor)
    assert isinstance(
        processor_for_type("crop_nobg", {"rmbg_client": rmbg_client}),
        CropNoBgProcessor,
    )
    assert isinstance(
        processor_for_type("image_generate", {"image_generate": lambda **_: None}),
        ImageGenerateProcessor,
    )

    with pytest.raises(ValueError, match="unknown processing_type"):
        processor_for_type("missing_type", {})


def _plan(
    processing_type: str,
    *,
    bbox: tuple[float, float, float, float] = (2.0, 2.0, 12.0, 12.0),
    geometry: dict[str, object] | None = None,
    parameters: dict[str, object] | None = None,
) -> ElementPlan:
    return ElementPlan(
        element_id="E001",
        source_candidate_ids=("sam3:B001",),
        element_type="icon",
        bbox=bbox,
        geometry=geometry or {"kind": "bbox", "bbox": [2, 2, 14, 14]},
        z_order=0,
        confidence="high",
        processing_intent=ProcessingIntent(
            object_type="icon",
            processing_type=processing_type,
            parameters=parameters or {},
        ),
        review_status="agent_refined",
        created_by_stage="refine_elements",
        change_reason="Test element.",
    )


def _write_figure(root: Path, *, size: tuple[int, int] = (20, 20)) -> Path:
    source_path = root / "inputs" / "figure.png"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGBA", size, (255, 255, 255, 255))
    for x in range(2, min(size[0], 14)):
        for y in range(2, min(size[1], 14)):
            image.putpixel((x, y), (20, 120, 220, 255))
    image.save(source_path)
    return source_path
