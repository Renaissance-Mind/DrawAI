#!/usr/bin/env python3
"""Inventory Microsoft's version-pinned PPTX/DrawingML schema metadata."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import hashlib
import json
from pathlib import Path
import urllib.request


REPOSITORY = "https://github.com/dotnet/Open-XML-SDK"
PREFIXES = (
    "schemas_openxmlformats_org_presentationml_2006",
    "schemas_openxmlformats_org_drawingml_2006_main",
    "schemas_openxmlformats_org_drawingml_2006_chart",
    "schemas_openxmlformats_org_drawingml_2006_diagram",
    "schemas_openxmlformats_org_drawingml_2006_picture",
    "schemas_openxmlformats_org_officeDocument_2006_math",
    "schemas_openxmlformats_org_officeDocument_2006_extended-properties",
    "schemas_openxmlformats_org_officeDocument_2006_custom-properties",
    "schemas_microsoft_com_office_drawing_",
    "schemas_microsoft_com_office_powerpoint_",
    "schemas_microsoft_com_ink_2010_main",
)


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "PPTX-schema-inventory"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def inventory(revision: str, output: Path, cache: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    listing = json.loads(fetch(f"https://api.github.com/repos/dotnet/Open-XML-SDK/contents/data/schemas?ref={revision}"))
    names = sorted(item["name"] for item in listing if item["name"].endswith(".json") and item["name"].startswith(PREFIXES))

    def load(name: str):
        url = f"https://raw.githubusercontent.com/dotnet/Open-XML-SDK/{revision}/data/schemas/{name}"
        path = cache / revision / name
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = path.read_bytes() if path.exists() else fetch(url)
        if not path.exists():
            path.write_bytes(raw)
        return name, json.loads(raw), {"file": name, "url": url, "sha256": hashlib.sha256(raw).hexdigest()}

    with ThreadPoolExecutor(max_workers=8) as pool:
        schemas = list(pool.map(load, names))
    rows, enumerations, types, sources = [], [], [], []
    for name, schema, source in schemas:
        sources.append(source)
        namespace = schema["TargetNamespace"]
        declarations = {item["ClassName"]: item for item in schema.get("Types", [])}
        for item in schema.get("Enums", []):
            enumerations.append({"schema_file": name, "namespace": namespace,
                                 "type": item.get("Type"), "sdk_name": item.get("Name"),
                                 "values": [{"wire_value": value.get("Value"), "sdk_name": value.get("Name")}
                                            for value in item.get("Facets", [])]})
        for item in schema.get("Types", []):
            types.append({"schema_file": name, "namespace": namespace, "name": item["Name"],
                          "sdk_class": item["ClassName"], "base_class": item.get("BaseClass"),
                          "version": item.get("Version"), "particle": item.get("Particle")})
            lineage = [item]
            visited = {item["ClassName"]}
            base = item.get("BaseClass")
            while base in declarations and base not in visited:
                ancestor = declarations[base]
                lineage.append(ancestor)
                visited.add(base)
                base = ancestor.get("BaseClass")
            seen = set()
            for declaration in lineage:
                for kind, field in [("attribute", value) for value in declaration.get("Attributes", [])] + [("element", value) for value in declaration.get("Children", [])]:
                    wire = field.get("QName") if kind == "attribute" else field["Name"].split("/")[-1]
                    key = (kind, wire)
                    if key in seen:
                        continue
                    seen.add(key)
                    rows.append({"schema_file": name, "namespace": namespace,
                                 "parent_name": item["Name"], "sdk_class": item["ClassName"],
                                 "kind": kind, "wire_name": wire,
                                 "sdk_property": field.get("PropertyName", ""),
                                 "sdk_type": field.get("Type", field.get("Name", "").split("/")[0]),
                                 "declared_on": declaration["ClassName"],
                                 "inherited": declaration is not item,
                                 "version": field.get("Version", item.get("Version", "")),
                                 "validators": json.dumps(field.get("Validators", []), separators=(",", ":")),
                                 "implementation_status": "not_assessed", "verification_status": "not_tested"})
    payload = {"schema": "pptx.schema_inventory.v1", "source_repository": REPOSITORY,
               "source_revision": revision, "sources": sources,
               "counts": {"schemas": len(sources), "types": len(types), "properties": len(rows), "enums": len(enumerations)},
               "scope": "PPTX/PowerPoint, shared DrawingML, charts, diagrams, math, metadata and drawing extensions; shared types need PPTX-context applicability checks.",
               "properties": rows, "types": types, "enums": enumerations}
    # One record per line keeps a complete inventory inspectable in version control.
    sections = []
    for key, value in payload.items():
        if key in {"properties", "types", "enums"}:
            encoded = "[\n" + ",\n".join("    " + json.dumps(row, ensure_ascii=False, separators=(",", ":")) for row in value) + "\n  ]"
        else:
            encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        sections.append("  " + json.dumps(key) + ": " + encoded)
    (output / "schema-inventory.json").write_text("{\n" + ",\n".join(sections) + "\n}\n", encoding="utf-8")
    with (output / "schema-properties.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    (output / "schema-sources.json").write_text(json.dumps({key: value for key, value in payload.items() if key not in {"properties", "types", "enums"}}, indent=2) + "\n", encoding="utf-8")
    return payload["counts"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", required=True, help="Exact Open XML SDK Git revision, not a moving branch.")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--cache", required=True, type=Path)
    args = parser.parse_args()
    if len(args.revision) != 40 or any(char not in "0123456789abcdef" for char in args.revision):
        parser.error("--revision must be a complete lowercase Git commit SHA")
    print(json.dumps(inventory(args.revision, args.output, args.cache), indent=2))


if __name__ == "__main__":
    main()
