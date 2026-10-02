"""Verify property inventory provenance and cross-format contract distinctions."""

from __future__ import annotations

import csv
import json
from pathlib import Path


REFERENCES = Path(__file__).resolve().parents[1] / "skills" / "drawai-ppt" / "references"


def test_catalog_keeps_targets_separate_from_implementation_and_native_defaults():
    catalog = json.loads((REFERENCES / "property-catalog.json").read_text())
    properties = catalog["properties"]
    assert len(properties) == len({value["id"] for value in properties})
    assert {value["domain"] for value in properties} == {domain["id"] for domain in catalog["domains"]}
    for value in properties:
        assert value["model_status"] == "proposed"
        assert value["test_status"] == "not_tested"
        assert value["native_default"] == "not_assessed"
        assert value["xml_mapping_status"] == "unmapped"
    by_id = {value["id"]: value for value in properties}
    assert by_id["object.transform"]["pptx_target"] != "native"
    assert by_id["object.locks"]["svg_static_target"] == "metadata/host"
    assert by_id["shape.geometry.paths"]["canonical_unit"] == "path-local"
    assert by_id["document.metadata.revision"]["value_type"] == "text"
    assert by_id["text.paragraph.content"]["value_type"] == "(Run|Break|Field|Math)[]"
    with (REFERENCES / "export-capabilities.csv").open(encoding="utf-8-sig", newline="") as stream:
        assert len(list(csv.DictReader(stream))) == len(properties)


def test_schema_inventory_preserves_source_revision_inheritance_and_enumerations():
    inventory = json.loads((REFERENCES / "pptx-inventory" / "schema-inventory.json").read_text())
    assert len(inventory["source_revision"]) == 40
    assert inventory["counts"]["schemas"] == len(inventory["sources"])
    assert inventory["counts"]["properties"] == len(inventory["properties"])
    assert inventory["counts"]["types"] == len(inventory["types"])
    assert inventory["counts"]["enums"] == len(inventory["enums"])
    assert all(inventory["source_revision"] in source["url"] for source in inventory["sources"])
    assert all(len(source["sha256"]) == 64 for source in inventory["sources"])
    assert any(value["inherited"] for value in inventory["properties"])
    assert all(value["implementation_status"] == "not_assessed" for value in inventory["properties"])


def test_matrix_enumerations_are_complete_and_match_their_native_sources():
    catalog = json.loads((REFERENCES / "property-catalog.json").read_text())
    inventory = json.loads((REFERENCES / "pptx-inventory" / "schema-inventory.json").read_text())
    enums = {(item["schema_file"], item["sdk_name"]): item for item in inventory["enums"]}
    for value in catalog["properties"]:
        if value["value_type"] != "enum":
            continue
        assert value["allowed_values"]
        assert len(value["allowed_values"]) == len(set(value["allowed_values"]))
        if value["native_enum"]:
            reference = value["native_enum"]
            declaration = enums[reference["schema_file"], reference["sdk_name"]]
            assert reference["type"] == declaration["type"]
            assert value["allowed_values"] == [item["wire_value"] for item in declaration["values"]]
    by_id = {item["id"]: item for item in catalog["properties"]}
    for end in ("start", "end"):
        for dimension in ("width", "length"):
            assert by_id[f"stroke.{end}_arrow.{dimension}"]["allowed_values"] == ["sm", "med", "lg"]
