from __future__ import annotations

import copy
import json
import os
import shutil
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from PIL import Image

from drawai.asset_geometry import geometry_crop, normalize_asset_geometry
from drawai.page_spec import validate_page_spec_payload
from drawai.rmbg_client import RmbgResult
from drawai.v2.schema import utc_now

_RASTER_PROCESSING_TYPES = {"crop", "crop_nobg"}
_NON_MATERIALIZED_PROCESSING_TYPES = {"svg_self_draw", "chart_rebuild_reserved"}
_UNSUPPORTED_PROCESSING_TYPES = {"image_generate", "image_edit"}


def materialize_page_spec_assets(
    page_spec: Mapping[str, Any],
    *,
    source_image_path: str | Path,
    output_dir: str | Path,
    rmbg_config: Any = None,
    rmbg_client: Any = None,
) -> dict[str, Any]:
    """Return a PageSpec copy whose raster elements point to assets in output_dir."""

    validate_page_spec_payload(page_spec)
    source_path = Path(source_image_path).expanduser().resolve(strict=False)
    if not source_path.is_file():
        raise FileNotFoundError(f"PageSpec asset_prepare source image does not exist: {source_path}")
    output_root = Path(output_dir).expanduser().resolve(strict=False)
    output_root.mkdir(parents=True, exist_ok=True)
    materialized = copy.deepcopy(dict(page_spec))
    raw_elements = materialized.get("elements")
    if isinstance(raw_elements, str) or not isinstance(raw_elements, Sequence):
        raise ValueError("PageSpec elements must be a list")
    for raw_element in raw_elements:
        if not isinstance(raw_element, dict):
            raise ValueError("PageSpec elements must contain objects")
        processing_type = _processing_type(raw_element)
        if processing_type in _UNSUPPORTED_PROCESSING_TYPES:
            element_id = _required_string(raw_element.get("id"), "element.id")
            raise RuntimeError(
                f"PageSpec asset_prepare cannot run processing_type {processing_type!r} for element {element_id}; "
                "image generation/editing must be modeled as a dedicated real tool or node before enabling it."
            )
        if processing_type in _NON_MATERIALIZED_PROCESSING_TYPES:
            raw_element.pop("materialization", None)
            continue
        if processing_type not in _RASTER_PROCESSING_TYPES:
            element_id = _required_string(raw_element.get("id"), "element.id")
            raise RuntimeError(f"unsupported PageSpec build.processing_type for element {element_id}: {processing_type}")
        raw_element["materialization"] = _materialize_raster_element(
            raw_element,
            source_image_path=source_path,
            output_dir=output_root,
            processing_type=processing_type,
            rmbg_config=rmbg_config,
            rmbg_client=rmbg_client,
        )
    metadata = materialized.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    metadata["asset_prepare"] = {
        "status": "ok",
        "created_at": utc_now(),
        "bundle_root": ".",
    }
    materialized["metadata"] = metadata
    validate_page_spec_payload(materialized)
    validate_page_spec_bundle_payload(materialized, output_root)
    return materialized


def materialized_asset_records(
    page_spec_path: str | Path,
    *,
    svg_dir: str | Path | None = None,
) -> list[dict[str, Any]]:
    page_spec_file = Path(page_spec_path).expanduser().resolve(strict=False)
    page_spec = json.loads(page_spec_file.read_text(encoding="utf-8"))
    if not isinstance(page_spec, Mapping):
        raise ValueError("PageSpec must be a JSON object")
    validate_page_spec_payload(page_spec)
    base_dir = page_spec_file.parent
    records: list[dict[str, Any]] = []
    raw_elements = page_spec.get("elements")
    if isinstance(raw_elements, str) or not isinstance(raw_elements, Sequence):
        raise ValueError("PageSpec elements must be a list")
    for element in raw_elements:
        if not isinstance(element, Mapping):
            continue
        element_id = str(element.get("id") or "")
        materialization = element.get("materialization")
        if not isinstance(materialization, Mapping):
            continue
        outputs = materialization.get("outputs")
        if not isinstance(outputs, Mapping):
            continue
        for output_key, output in outputs.items():
            if not isinstance(output, Mapping):
                continue
            path_value = output.get("path")
            if not isinstance(path_value, str) or not path_value:
                continue
            absolute_path = _resolve_bundle_path(base_dir, path_value)
            record = {
                "element_id": element_id,
                "output_key": str(output_key),
                "path": path_value,
                "absolute_path": str(absolute_path),
                "media_type": output.get("media_type") or "application/octet-stream",
                "width_px": output.get("width_px"),
                "height_px": output.get("height_px"),
            }
            if svg_dir is not None:
                record["svg_href"] = os.path.relpath(absolute_path, Path(svg_dir).expanduser().resolve(strict=False))
            records.append(record)
    return records


def copy_page_spec_bundle(
    source_page_spec: str | Path,
    target_dir: str | Path,
    *,
    output_name: str = "page_spec.json",
) -> Path:
    source_path = Path(source_page_spec).expanduser().resolve(strict=False)
    target_root = Path(target_dir).expanduser().resolve(strict=False)
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("PageSpec must be a JSON object")
    validate_page_spec_payload(payload)
    for record in materialized_asset_records(source_path):
        target_path = _resolve_bundle_path(target_root, str(record["path"]))
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(record["absolute_path"], target_path)
    target_path = target_root / output_name
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    validate_page_spec_bundle(target_path)
    return target_path


def page_spec_asset_manifest(
    page_spec_path: str | Path,
    *,
    svg_dir: str | Path,
) -> dict[str, Any]:
    records = [
        record
        for record in materialized_asset_records(page_spec_path, svg_dir=svg_dir)
        if record.get("output_key") == "active"
    ]
    return {
        "schema": "drawai.page_spec_asset_manifest.v1",
        "source": "page_spec.materialization",
        "page_spec": str(Path(page_spec_path).expanduser().resolve(strict=False)),
        "assets": [
            {
                "asset_id": record["element_id"],
                "element_id": record["element_id"],
                "status": "ok",
                "path": record["absolute_path"],
                "svg_href": record["svg_href"],
                "media_type": record["media_type"],
                "width": record.get("width_px"),
                "height": record.get("height_px"),
                "render_policy": "raster_png",
                "insertable": True,
            }
            for record in records
        ],
    }


def validate_page_spec_bundle(path: str | Path) -> None:
    page_spec_path = Path(path).expanduser().resolve(strict=False)
    payload = json.loads(page_spec_path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("PageSpec must be a JSON object")
    validate_page_spec_payload(payload)
    validate_page_spec_bundle_payload(payload, page_spec_path.parent)


def validate_page_spec_bundle_payload(page_spec: Mapping[str, Any], bundle_dir: str | Path) -> None:
    base_dir = Path(bundle_dir).expanduser().resolve(strict=False)
    raw_elements = page_spec.get("elements")
    if isinstance(raw_elements, str) or not isinstance(raw_elements, Sequence):
        raise ValueError("PageSpec elements must be a list")
    for index, element in enumerate(raw_elements):
        if not isinstance(element, Mapping):
            continue
        materialization = element.get("materialization")
        if materialization is None:
            continue
        if not isinstance(materialization, Mapping):
            raise ValueError(f"elements[{index}].materialization must be a mapping")
        outputs = materialization.get("outputs")
        if outputs is None:
            continue
        if not isinstance(outputs, Mapping):
            raise ValueError(f"elements[{index}].materialization.outputs must be a mapping")
        for output_key, output in outputs.items():
            if not isinstance(output, Mapping):
                raise ValueError(f"elements[{index}].materialization.outputs.{output_key} must be a mapping")
            path_value = output.get("path")
            if not isinstance(path_value, str) or not path_value:
                raise ValueError(f"elements[{index}].materialization.outputs.{output_key}.path is required")
            resolved = _resolve_bundle_path(base_dir, path_value)
            if not resolved.is_file():
                raise FileNotFoundError(
                    f"PageSpec materialization file does not exist for element {element.get('id')}: {path_value}"
                )


def _materialize_raster_element(
    element: Mapping[str, Any],
    *,
    source_image_path: Path,
    output_dir: Path,
    processing_type: str,
    rmbg_config: Any,
    rmbg_client: Any,
) -> dict[str, Any]:
    element_id = _required_string(element.get("id"), "element.id")
    element_dir = output_dir / "assets" / _safe_asset_dir_name(element_id)
    element_dir.mkdir(parents=True, exist_ok=True)
    crop, crop_bbox = _crop_element(source_image_path, element, base_dir=output_dir)
    crop_path = element_dir / "crop.png"
    crop.save(crop_path)
    active_image = crop
    active_variant = "crop"
    if processing_type == "crop_nobg":
        if rmbg_client is None or not _rmbg_enabled(rmbg_config):
            raise RuntimeError(f"PageSpec element {element_id} requested crop_nobg but RMBG is not enabled")
        rmbg_result = _remove_background(
            rmbg_client,
            crop,
            element_id,
            timeout_s=_rmbg_timeout_seconds(rmbg_config),
            model_path=_rmbg_model_path(rmbg_config),
        )
        active_image = rmbg_result.image.convert("RGBA")
        active_variant = "crop_nobg"
    active_path = element_dir / "active.png"
    active_image.save(active_path)
    return {
        "status": "ok",
        "processor": "asset_prepare",
        "processing_type": processing_type,
        "created_at": utc_now(),
        "outputs": {
            "crop": _image_output_record(crop_path, output_dir),
            "active": _image_output_record(active_path, output_dir),
        },
        "metadata": {
            "source_image": str(source_image_path),
            "crop_bbox_xyxy": list(crop_bbox),
            "active_variant": active_variant,
        },
    }


def _crop_element(
    source_image_path: Path,
    element: Mapping[str, Any],
    *,
    base_dir: Path,
) -> tuple[Image.Image, tuple[int, int, int, int]]:
    with Image.open(source_image_path) as image:
        source = image.convert("RGBA")
        bbox = _crop_bounds(_bbox_xywh(element), source.size)
        geometry = normalize_asset_geometry(element.get("geometry"), fallback_bbox=bbox, image_size=source.size)
        crop = geometry_crop(source, bbox, geometry, base_dir=base_dir)
        crop.load()
        return crop, bbox


def _image_output_record(path: Path, output_dir: Path) -> dict[str, Any]:
    with Image.open(path) as image:
        width, height = image.size
    return {
        "path": os.path.relpath(path.resolve(strict=False), output_dir.resolve(strict=False)),
        "media_type": "image/png",
        "width_px": width,
        "height_px": height,
    }


def _processing_type(element: Mapping[str, Any]) -> str:
    build = element.get("build")
    if not isinstance(build, Mapping):
        return "svg_self_draw"
    processing_type = build.get("processing_type")
    if isinstance(processing_type, str) and processing_type:
        return processing_type
    mode = str(build.get("mode") or "")
    if mode == "asset_ref":
        return "crop"
    return "svg_self_draw"


def _bbox_xywh(element: Mapping[str, Any]) -> tuple[float, float, float, float]:
    raw = element.get("box_px")
    if isinstance(raw, str) or not isinstance(raw, Sequence) or len(raw) != 4:
        raise ValueError(f"PageSpec element {element.get('id')!r} must contain box_px [x,y,width,height]")
    x, y, width, height = (float(value) for value in raw)
    if width <= 0 or height <= 0:
        raise ValueError(f"PageSpec element {element.get('id')!r} must have positive box_px width/height")
    return x, y, width, height


def _crop_bounds(
    bbox_xywh: Sequence[float],
    image_size: tuple[int, int],
) -> tuple[int, int, int, int]:
    x, y, width, height = (float(value) for value in bbox_xywh)
    image_width, image_height = image_size
    left = max(0, min(image_width, int(x // 1)))
    top = max(0, min(image_height, int(y // 1)))
    right = max(0, min(image_width, int(-(-float(x + width) // 1))))
    bottom = max(0, min(image_height, int(-(-float(y + height) // 1))))
    if right <= left or bottom <= top:
        raise ValueError(f"invalid crop bounds after clamping: {[left, top, right, bottom]}")
    return left, top, right, bottom


def _remove_background(
    rmbg_client: Any,
    crop: Image.Image,
    output_name: str,
    *,
    timeout_s: float,
    model_path: str,
) -> RmbgResult:
    result = rmbg_client.remove_background(
        crop,
        output_name,
        timeout_s=timeout_s,
        model_path=model_path,
        artifact_prefix=f"drawai_pagespec/{output_name}",
    )
    if isinstance(result, RmbgResult):
        return result
    if isinstance(result, Mapping):
        image = result.get("image")
        if not isinstance(image, Image.Image):
            raise RuntimeError("RMBG response mapping must include a PIL image")
        artifacts = result.get("artifacts")
        return RmbgResult(
            image=image,
            artifacts=dict(artifacts) if isinstance(artifacts, Mapping) else {},
            elapsed_ms=float(result.get("elapsed_ms", 0.0)),
        )
    if isinstance(result, Image.Image):
        return RmbgResult(image=result, artifacts={}, elapsed_ms=0.0)
    raise RuntimeError(f"RMBG client returned unsupported result type: {type(result).__name__}")


def _rmbg_enabled(config: Any) -> bool:
    return bool(getattr(config, "enabled", False))


def _rmbg_timeout_seconds(config: Any) -> float:
    return float(getattr(config, "timeout_seconds", 60.0) or 60.0)


def _rmbg_model_path(config: Any) -> str:
    return str(getattr(config, "model_path", "") or "")


def _resolve_bundle_path(bundle_dir: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        raise ValueError(f"PageSpec materialization path must be relative to its bundle: {raw_path}")
    resolved = (bundle_dir / path).resolve(strict=False)
    try:
        resolved.relative_to(bundle_dir.resolve(strict=False))
    except ValueError as exc:
        raise ValueError(f"PageSpec materialization path escapes its bundle: {raw_path}") from exc
    return resolved


def _safe_asset_dir_name(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in value)


def _required_string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} is required")
    return value
