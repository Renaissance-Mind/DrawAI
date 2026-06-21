from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

from drawai.v2.registry import default_registry
from drawai.v2.schema import ElementCandidate, ElementPlan, ProcessingIntent

PAGE_SPEC_SCHEMA = "drawai.page_spec.v1"

PAGE_ELEMENT_KINDS = {
    "text",
    "shape",
    "image",
    "connector",
    "table",
    "chart",
    "formula",
    "group",
    "unknown",
}

_ASSET_PROCESSING_TYPES = {"crop", "crop_nobg", "image_generate", "image_edit"}
_PROCESSING_TO_BUILD_MODE = {
    "svg_self_draw": "vector",
    "crop": "asset_ref",
    "crop_nobg": "asset_ref",
    "image_generate": "asset_ref",
    "image_edit": "asset_ref",
    "chart_rebuild_reserved": "structured",
}
_BUILD_MODE_TO_PROCESSING = {
    "vector": "svg_self_draw",
    "editable_text": "svg_self_draw",
    "vector_shape": "svg_self_draw",
    "connector": "svg_self_draw",
    "group": "svg_self_draw",
    "structured": "svg_self_draw",
}


def validate_page_spec_payload(payload: Mapping[str, Any]) -> None:
    if payload.get("schema") != PAGE_SPEC_SCHEMA:
        raise ValueError(f"invalid page spec schema: {payload.get('schema')}")
    _require_string(payload, "page_id")
    _validate_mapping(payload.get("source", {}), "source")
    _validate_mapping(payload.get("canvas", {}), "canvas")
    background = payload.get("background")
    if background is not None:
        _validate_mapping(background, "background")
    elements = payload.get("elements")
    if isinstance(elements, str) or not isinstance(elements, Sequence):
        raise ValueError("page_spec.elements must be a list")

    seen_ids: set[str] = set()
    parent_ids: dict[str, str] = {}
    child_ids: dict[str, list[str]] = {}
    for index, raw_element in enumerate(elements):
        if not isinstance(raw_element, Mapping):
            raise ValueError(f"elements[{index}] must be a mapping")
        element_id = _require_string(raw_element, "id", field_prefix=f"elements[{index}]")
        if element_id in seen_ids:
            raise ValueError(f"duplicate page element id: {element_id}")
        seen_ids.add(element_id)
        kind = _require_string(raw_element, "kind", field_prefix=f"elements[{index}]")
        if kind not in PAGE_ELEMENT_KINDS:
            raise ValueError(f"elements[{index}].kind is not supported: {kind}")
        _validate_geometry(raw_element, f"elements[{index}]")
        _validate_mapping(raw_element.get("build", {}), f"elements[{index}].build")
        _validate_mapping(raw_element.get("style", {}), f"elements[{index}].style")
        _validate_mapping(raw_element.get("metadata", {}), f"elements[{index}].metadata")
        _validate_mapping(raw_element.get("measurement", {}), f"elements[{index}].measurement")
        _validate_json_value(raw_element.get("source_refs", []), f"elements[{index}].source_refs")
        parent_id = raw_element.get("parent_id")
        if isinstance(parent_id, str) and parent_id:
            parent_ids[element_id] = parent_id
        children = raw_element.get("children", [])
        if children is not None:
            if isinstance(children, str) or not isinstance(children, Sequence):
                raise ValueError(f"elements[{index}].children must be a list")
            child_ids[element_id] = [str(item) for item in children if str(item)]

    missing_parents = sorted(parent for parent in parent_ids.values() if parent not in seen_ids)
    if missing_parents:
        raise ValueError(f"page_spec references missing parent ids: {', '.join(missing_parents)}")
    missing_children = sorted({child for children in child_ids.values() for child in children if child not in seen_ids})
    if missing_children:
        raise ValueError(f"page_spec references missing child ids: {', '.join(missing_children)}")
    _validate_group_cycles(parent_ids)


def page_spec_from_run_package(
    payload: Mapping[str, Any],
    *,
    page_id: str,
    source_image: str = "",
) -> dict[str, Any]:
    raw_elements = payload.get("elements")
    if not isinstance(raw_elements, list):
        raise ValueError("run package must contain an elements list")
    canvas = _mapping(payload.get("canvas", {}), "run_package.canvas")
    metadata = _mapping(payload.get("metadata", {}), "run_package.metadata")
    page_spec = {
        "schema": PAGE_SPEC_SCHEMA,
        "page_id": page_id,
        "source": {
            "image": source_image or str(payload.get("source_image") or ""),
            "width_px": canvas.get("width"),
            "height_px": canvas.get("height"),
        },
        "canvas": {
            "width_px": canvas.get("width"),
            "height_px": canvas.get("height"),
        },
        "background": {},
        "elements": [
            page_element_from_plan_payload(item)
            for item in raw_elements
            if isinstance(item, Mapping)
        ],
        "metadata": {
            "producer": "drawai.v2.run_package_adapter",
            "source_schema": str(payload.get("schema") or ""),
            "last_stage": str(metadata.get("last_stage") or ""),
        },
    }
    validate_page_spec_payload(page_spec)
    return page_spec


def page_element_from_plan_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    element_id = _require_string(payload, "element_id")
    element_type = str(payload.get("element_type") or "unknown")
    processing_intent = _mapping(payload.get("processing_intent", {}), "processing_intent")
    processing_type = str(processing_intent.get("processing_type") or "svg_self_draw")
    kind = _page_kind_from_element_type(element_type, processing_type)
    box_px = _bbox4(payload.get("bbox"), "element.bbox")
    build_mode = _PROCESSING_TO_BUILD_MODE.get(processing_type, "vector")
    asset_id = f"A{element_id.removeprefix('E')}"
    build: dict[str, Any] = {
        "mode": build_mode,
        "processing_type": processing_type,
    }
    if processing_type in _ASSET_PROCESSING_TYPES:
        build["asset_id"] = asset_id
    text = payload.get("text")
    element: dict[str, Any] = {
        "id": element_id,
        "kind": kind,
        "role": str(processing_intent.get("object_type") or element_type),
        "box_px": list(box_px),
        "z_index": int(payload.get("z_order", 0)),
        "confidence": str(payload.get("confidence") or "medium"),
        "geometry": _mapping(payload.get("geometry", {}), "element.geometry"),
        "source_refs": [
            {
                "kind": "candidate",
                "id": str(source_id),
            }
            for source_id in payload.get("source_candidate_ids", ())
            if str(source_id)
        ],
        "build": build,
        "metadata": {
            "review_status": str(payload.get("review_status") or ""),
            "created_by_stage": str(payload.get("created_by_stage") or ""),
            "change_reason": str(payload.get("change_reason") or ""),
            "legacy_element_type": element_type,
        },
    }
    if isinstance(text, str) and text:
        element["text"] = text
    return element


def page_spec_from_candidates(
    candidates: Sequence[ElementCandidate | Mapping[str, Any]],
    *,
    page_id: str,
    source_image: str = "",
    canvas: Mapping[str, Any] | None = None,
    producer: str,
) -> dict[str, Any]:
    canvas_payload = _mapping(canvas or {}, "canvas")
    page_spec = {
        "schema": PAGE_SPEC_SCHEMA,
        "page_id": page_id,
        "source": {
            "image": source_image,
            "width_px": canvas_payload.get("width_px", canvas_payload.get("width")),
            "height_px": canvas_payload.get("height_px", canvas_payload.get("height")),
        },
        "canvas": {
            "width_px": canvas_payload.get("width_px", canvas_payload.get("width")),
            "height_px": canvas_payload.get("height_px", canvas_payload.get("height")),
        },
        "background": {},
        "elements": [
            page_element_from_candidate_payload(_candidate_payload(candidate))
            for candidate in candidates
        ],
        "metadata": {"producer": producer},
    }
    validate_page_spec_payload(page_spec)
    return page_spec


def page_element_from_candidate_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    candidate_id = _require_string(payload, "candidate_id")
    element_type = str(payload.get("element_type") or "unknown")
    kind = _page_kind_from_element_type(element_type, _candidate_processing_type(element_type))
    bbox = _bbox4(payload.get("bbox"), "candidate.bbox")
    text = str(payload.get("text") or "")
    build: dict[str, Any] = {
        "mode": _candidate_build_mode(kind, element_type),
        "processing_type": _candidate_processing_type(element_type),
    }
    if build["mode"] == "asset_ref":
        build["asset_id"] = _asset_id_from_candidate_id(candidate_id)
    element: dict[str, Any] = {
        "id": _element_id_from_candidate_id(candidate_id),
        "kind": kind,
        "role": element_type,
        "box_px": list(bbox),
        "z_index": int(payload.get("z_hint", 0) or 0),
        "confidence": float(payload.get("confidence", 0.0) or 0.0),
        "geometry": _mapping(payload.get("geometry", {}), "candidate.geometry"),
        "source_refs": [{"kind": "candidate", "id": candidate_id}],
        "build": build,
        "measurement": {
            "text": text,
            "confidence": payload.get("confidence"),
        } if text else {"confidence": payload.get("confidence")},
        "metadata": {
            "source_parser": str(payload.get("source_parser") or ""),
            "source_parser_version": str(payload.get("source_parser_version") or ""),
            "legacy_element_type": element_type,
            "candidate_payload": dict(payload),
        },
    }
    if text:
        element["text"] = text
    return element


def candidate_payloads_from_page_specs(
    payloads: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for payload in payloads:
        validate_page_spec_payload(payload)
        for raw_element in payload.get("elements", ()):
            if not isinstance(raw_element, Mapping):
                continue
            metadata = raw_element.get("metadata")
            if not isinstance(metadata, Mapping):
                continue
            candidate = metadata.get("candidate_payload")
            if isinstance(candidate, Mapping):
                candidates.append(dict(candidate))
    return candidates


def element_plans_from_page_spec(payload: Mapping[str, Any]) -> tuple[ElementPlan, ...]:
    validate_page_spec_payload(payload)
    plans: list[ElementPlan] = []
    registry = default_registry()
    for raw_element in payload["elements"]:
        if not isinstance(raw_element, Mapping):
            continue
        if raw_element.get("kind") == "group":
            continue
        element_id = _require_string(raw_element, "id")
        kind = _require_string(raw_element, "kind")
        element_type = _legacy_element_type(raw_element, kind)
        if not registry.has_element_type(element_type):
            element_type = "unknown"
        processing_type = _processing_type(raw_element)
        if not registry.has_processing_type(processing_type):
            processing_type = "svg_self_draw"
        plans.append(
            ElementPlan(
                element_id=element_id,
                source_candidate_ids=tuple(_source_candidate_ids(raw_element, fallback=element_id)),
                element_type=element_type,
                bbox=_bbox4(raw_element.get("box_px"), f"{element_id}.box_px"),
                geometry=_mapping(raw_element.get("geometry", {}), f"{element_id}.geometry"),
                z_order=int(raw_element.get("z_index", 0)),
                confidence=cast(Any, _plan_confidence(raw_element.get("confidence"))),
                processing_intent=ProcessingIntent(
                    object_type=str(raw_element.get("role") or element_type),
                    processing_type=processing_type,
                    parameters=_mapping(_mapping(raw_element.get("build", {}), "build").get("parameters", {}), "build.parameters"),
                ),
                review_status=cast(Any, "agent_refined"),
                created_by_stage="page_spec",
                change_reason=str(_mapping(raw_element.get("metadata", {}), "metadata").get("change_reason") or "Converted from PageSpec."),
            )
        )
    return tuple(plans)


def load_page_spec(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("page spec must be a JSON object")
    page_spec = dict(payload)
    validate_page_spec_payload(page_spec)
    return page_spec


def write_page_spec(path: str | Path, payload: Mapping[str, Any]) -> Path:
    validate_page_spec_payload(payload)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def _page_kind_from_element_type(element_type: str, processing_type: str) -> str:
    if element_type == "text":
        return "text"
    if element_type in {"arrow"}:
        return "connector"
    if element_type in {"table", "chart"}:
        return element_type
    if processing_type in _ASSET_PROCESSING_TYPES or element_type in {"icon", "picture", "symbol"}:
        return "image"
    if element_type in {"frame", "grid", "content_box"}:
        return "shape"
    if element_type == "diagram":
        return "group"
    return "unknown"


def _legacy_element_type(element: Mapping[str, Any], kind: str) -> str:
    metadata = element.get("metadata")
    if isinstance(metadata, Mapping):
        legacy = metadata.get("legacy_element_type")
        if isinstance(legacy, str) and legacy:
            return legacy
    if kind == "shape":
        return "frame"
    if kind == "connector":
        return "arrow"
    if kind == "image":
        role = str(element.get("role") or "")
        if role in {"icon", "symbol", "picture"}:
            return role
        return "picture"
    if kind == "formula":
        return "text"
    if kind in {"text", "table", "chart", "unknown"}:
        return kind
    return "unknown"


def _processing_type(element: Mapping[str, Any]) -> str:
    build = _mapping(element.get("build", {}), "build")
    processing_type = build.get("processing_type")
    if isinstance(processing_type, str) and processing_type:
        return processing_type
    mode = str(build.get("mode") or "")
    if mode == "asset_ref":
        return "crop"
    return _BUILD_MODE_TO_PROCESSING.get(mode, "svg_self_draw")


def _candidate_payload(candidate: ElementCandidate | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(candidate, ElementCandidate):
        return candidate.to_dict()
    if isinstance(candidate, Mapping):
        return dict(candidate)
    raise ValueError("candidate must be an ElementCandidate or mapping")


def _candidate_build_mode(kind: str, element_type: str) -> str:
    if kind == "text":
        return "editable_text"
    if kind in {"shape", "connector", "table", "chart", "formula"}:
        return "vector"
    if element_type in {"picture", "icon", "symbol", "diagram", "unknown"}:
        return "asset_ref"
    return "vector"


def _candidate_processing_type(element_type: str) -> str:
    if element_type in {"picture", "icon", "symbol", "diagram", "unknown"}:
        return "crop"
    return "svg_self_draw"


def _element_id_from_candidate_id(candidate_id: str) -> str:
    slug = candidate_id.replace(":", "_").replace("-", "_")
    return f"C_{slug}"


def _asset_id_from_candidate_id(candidate_id: str) -> str:
    slug = candidate_id.replace(":", "_").replace("-", "_")
    return f"A_{slug}"


def _source_candidate_ids(element: Mapping[str, Any], *, fallback: str) -> list[str]:
    source_ids: list[str] = []
    for raw_ref in element.get("source_refs", ()):
        if not isinstance(raw_ref, Mapping):
            continue
        if str(raw_ref.get("kind") or "") != "candidate":
            continue
        source_id = raw_ref.get("id")
        if isinstance(source_id, str) and source_id:
            source_ids.append(source_id)
    return source_ids or [fallback]


def _plan_confidence(value: object) -> str:
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"low", "medium", "high"}:
            return normalized
    if isinstance(value, int | float) and not isinstance(value, bool):
        numeric = float(value)
        if numeric >= 0.75:
            return "high"
        if numeric <= 0.35:
            return "low"
    return "medium"


def _validate_geometry(payload: Mapping[str, Any], field_prefix: str) -> None:
    if "box_px" in payload:
        _bbox4(payload["box_px"], f"{field_prefix}.box_px")
    if "points_px" in payload:
        _points4(payload["points_px"], f"{field_prefix}.points_px")
    if "polygon_px" in payload:
        polygon = payload["polygon_px"]
        if isinstance(polygon, str) or not isinstance(polygon, Sequence):
            raise ValueError(f"{field_prefix}.polygon_px must be a list")
        for index, point in enumerate(polygon):
            if isinstance(point, str) or not isinstance(point, Sequence) or len(point) != 2:
                raise ValueError(f"{field_prefix}.polygon_px[{index}] must contain two numbers")
            _finite_float(point[0], f"{field_prefix}.polygon_px[{index}][0]")
            _finite_float(point[1], f"{field_prefix}.polygon_px[{index}][1]")


def _validate_group_cycles(parent_ids: Mapping[str, str]) -> None:
    for element_id in parent_ids:
        seen: set[str] = set()
        current = element_id
        while current in parent_ids:
            current = parent_ids[current]
            if current in seen:
                raise ValueError(f"page_spec group cycle detected at {current}")
            seen.add(current)


def _mapping(value: Any, field_name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be a mapping")
    return dict(value)


def _validate_mapping(value: object, field_name: str) -> None:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be a mapping")
    _validate_json_value(value, field_name)


def _validate_json_value(value: object, field_name: str) -> None:
    if value is None or isinstance(value, str | bool):
        return
    if isinstance(value, int | float) and not isinstance(value, bool):
        if not math.isfinite(float(value)):
            raise ValueError(f"{field_name} must be finite")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{field_name} keys must be strings")
            _validate_json_value(item, f"{field_name}.{key}")
        return
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        for index, item in enumerate(value):
            _validate_json_value(item, f"{field_name}[{index}]")
        return
    raise ValueError(f"{field_name} must be JSON-compatible")


def _require_string(payload: Mapping[str, Any], field_name: str, *, field_prefix: str = "") -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value:
        prefix = f"{field_prefix}." if field_prefix else ""
        raise ValueError(f"{prefix}{field_name} is required")
    return value


def _bbox4(value: Any, field_name: str) -> tuple[float, float, float, float]:
    if isinstance(value, str) or not isinstance(value, Sequence) or len(value) != 4:
        raise ValueError(f"{field_name} must contain four numbers")
    x, y, width, height = (_finite_float(item, field_name) for item in value)
    if width <= 0 or height <= 0:
        raise ValueError(f"{field_name} must have positive width and height")
    return (x, y, width, height)


def _points4(value: Any, field_name: str) -> tuple[float, float, float, float]:
    if isinstance(value, str) or not isinstance(value, Sequence) or len(value) != 4:
        raise ValueError(f"{field_name} must contain four numbers")
    return tuple(_finite_float(item, field_name) for item in value)  # type: ignore[return-value]


def _finite_float(value: Any, field_name: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field_name} must contain finite numbers")
    return result
