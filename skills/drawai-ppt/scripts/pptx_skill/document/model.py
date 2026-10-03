"""Portable, PPTX-first authoring data. All public lengths are points."""

from __future__ import annotations
from pathlib import Path
from typing import Any, Literal
import json
import math
from pydantic import BaseModel, ConfigDict, Field, model_validator

CATALOG = Path(__file__).resolve().parents[3] / "references" / "property-catalog.json"
PROPERTIES = {p["id"]: p for p in json.loads(CATALOG.read_text())["properties"]}


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Object(Model):
    id: str
    kind: str = "shape"
    properties: dict[str, Any] = Field(default_factory=dict)
    children: list[Object] = Field(default_factory=list)
    native_xml: str | None = None
    source_shape_id: int | None = None
    baseline: dict[str, Any] | None = None
    clear_overrides: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def identity_aliases(cls, value):
        if not isinstance(value, dict):
            return value
        value = dict(value)
        props = value.get("properties", {})
        for field in ("id", "kind"):
            alias = "object." + field
            if alias not in props:
                continue
            if field in value and value[field] != props[alias]:
                raise ValueError(
                    f"{alias} conflicts with top-level {field}; use one value"
                )
            value[field] = props[alias]
        return value


class Page(Model):
    id: str
    properties: dict[str, Any] = Field(default_factory=dict)
    objects: list[Object] = Field(default_factory=list)
    source_slide: int | None = None
    baseline: dict[str, Any] | None = None


class NativeBinding(Model):
    property_id: str
    owner_id: str
    part: str
    xpath: str
    action: Literal[
        "set_attribute",
        "remove_attribute",
        "set_text",
        "append_xml",
        "replace_xml",
        "remove",
    ]
    value: str = ""
    name: str = ""
    namespaces: dict[str, str] = Field(default_factory=dict)
    expected_matches: int = Field(default=1, ge=1)


class Document(Model):
    schema_id: Literal["presentation.document.v1"] = Field(
        default="presentation.document.v1", alias="schema"
    )
    id: str = "presentation"
    properties: dict[str, Any] = Field(default_factory=dict)
    assets: dict[str, dict[str, Any]] = Field(default_factory=dict)
    pages: list[Page] = Field(min_length=1)
    template: dict[str, Any] | None = None
    native_parts: dict[str, dict[str, str]] = Field(default_factory=dict)
    baseline: dict[str, Any] | None = None
    native_bindings: list[NativeBinding] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_contract(self):
        seen = set()

        def properties(props):
            for key, value in props.items():
                if key not in PROPERTIES:
                    raise ValueError(
                        f"Unknown property {key}; add a contract before implementing it"
                    )
                choices = PROPERTIES[key].get("allowed_values", [])
                if choices and value not in choices:
                    raise ValueError(f"{key}: {value!r} must be one of {choices}")
                if PROPERTIES[key]["value_type"] == "boolean" and not isinstance(
                    value, bool
                ):
                    raise ValueError(f"{key} requires a boolean")
                nested(value)

        def nested(value):
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError("Properties must contain finite numbers")
            if isinstance(value, dict):
                if "properties" in value:
                    properties(value["properties"])
                for k, v in value.items():
                    if k != "properties":
                        nested(v)
            elif isinstance(value, list):
                for item in value:
                    nested(item)

        def walk(obj):
            if obj.id in seen:
                raise ValueError(f"Duplicate object ID: {obj.id}")
            seen.add(obj.id)
            if obj.kind not in PROPERTIES["object.kind"]["allowed_values"]:
                raise ValueError(f"Unknown object kind: {obj.kind}")
            if "object.frame" in obj.properties:
                value = obj.properties["object.frame"]
                keys = ("left", "top", "width", "height")
                if not isinstance(value, dict) or any(
                    isinstance(value.get(k), bool)
                    or not isinstance(value.get(k), (int, float))
                    or not math.isfinite(value[k])
                    for k in keys
                ):
                    raise ValueError(
                        f"Object {obj.id}: object.frame needs finite numeric left, top, width and height"
                    )
                w, h = value["width"], value["height"]
                invalid = (
                    min(w, h) < 0 or max(w, h) == 0
                    if obj.kind == "connector"
                    else min(w, h) <= 0
                )
                if invalid:
                    guidance = (
                        "; use make_connector with start/end points for directed lines"
                        if obj.kind == "connector"
                        else ""
                    )
                    raise ValueError(
                        f"Object {obj.id}: invalid object.frame dimensions ({w}, {h}){guidance}"
                    )
            properties(obj.properties)
            for key in obj.clear_overrides:
                if key not in PROPERTIES:
                    raise ValueError(f"Unknown override: {key}")
            for child in obj.children:
                walk(child)

        properties(self.properties)
        for page in self.pages:
            if page.id in seen:
                raise ValueError(f"Duplicate page ID: {page.id}")
            seen.add(page.id)
            properties(page.properties)
            for obj in page.objects:
                walk(obj)
        for binding in self.native_bindings:
            if binding.property_id not in PROPERTIES:
                raise ValueError(
                    f"Unknown native binding property: {binding.property_id}"
                )
            if binding.property_id in (
                "package.security.encryption",
                "package.security.permissions",
                "package.security.signature",
                "package.security.sensitivity",
                "live_feed.host_binding",
                "animation.runtime_state",
                "embedded.activation",
            ):
                raise ValueError(
                    f"{binding.property_id} needs its host/container workflow and cannot be implemented by an XML binding"
                )
            if binding.owner_id != self.id and binding.owner_id not in seen:
                raise ValueError(f"Native binding owner missing: {binding.owner_id}")
            if binding.part.startswith("/") or ".." in Path(binding.part).parts:
                raise ValueError("Binding part must be a relative package path")
            if (
                binding.action in ("set_attribute", "remove_attribute")
                and not binding.name
            ):
                raise ValueError("Attribute binding requires name")
        return self

    def save(self, path: Path):
        path = Path(path)
        if path.exists():
            raise FileExistsError(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            self.model_dump_json(indent=2, by_alias=True) + "\n", encoding="utf-8"
        )


def load_document(source: Path | dict | Document) -> Document:
    if isinstance(source, Document):
        return Document.model_validate(source.model_dump(by_alias=True))
    if isinstance(source, dict):
        return Document.model_validate(source)
    return Document.model_validate_json(Path(source).read_text(encoding="utf-8"))
