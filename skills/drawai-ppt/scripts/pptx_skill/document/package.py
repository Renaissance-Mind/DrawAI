"""Explicit, inspectable native XML editing for properties needing Office trees.

Bindings always name a catalog property, package part, and exact XML target.
They do not pretend to infer a semantic value from arbitrary XML.
"""

from __future__ import annotations
from io import BytesIO
import zipfile
from lxml import etree
from .xml import NS


def apply_bindings(data, bindings):
    if not bindings:
        return data, []
    with zipfile.ZipFile(BytesIO(data)) as z:
        parts = {n: z.read(n) for n in z.namelist()}
    trees = {}
    report = []
    for b in bindings:
        path = b.part
        if path not in parts:
            raise ValueError(
                f"Native binding part does not exist: {path}; supply native_parts for new parts"
            )
        if path not in trees:
            trees[path] = etree.fromstring(
                parts[path], etree.XMLParser(resolve_entities=False, no_network=True)
            )
        tree = trees[path]
        namespaces = {**NS, **b.namespaces}
        targets = tree.xpath(b.xpath, namespaces=namespaces)
        if len(targets) != b.expected_matches:
            raise ValueError(
                f"{b.property_id}: XPath {b.xpath} matched {len(targets)}, expected {b.expected_matches}"
            )
        if any(not isinstance(n, etree._Element) for n in targets):
            raise ValueError(
                "Bindings must select elements; attribute changes use action=set_attribute"
            )
        for target in targets:
            if b.action == "set_attribute":
                name = b.name
                if ":" in name:
                    prefix, local = name.split(":")
                    name = "{" + namespaces[prefix] + "}" + local
                target.set(name, b.value)
            elif b.action == "remove_attribute":
                name = b.name
                if ":" in name:
                    prefix, local = name.split(":")
                    name = "{" + namespaces[prefix] + "}" + local
                target.attrib.pop(name, None)
            elif b.action == "set_text":
                target.text = b.value
            elif b.action == "remove":
                if target.getparent() is None:
                    raise ValueError("Cannot remove a package XML root")
                target.getparent().remove(target)
            else:
                node = etree.fromstring(
                    b.value.encode(),
                    etree.XMLParser(resolve_entities=False, no_network=True),
                )
                if b.action == "append_xml":
                    target.append(node)
                elif b.action == "replace_xml":
                    if target.getparent() is None:
                        trees[path] = node
                    else:
                        target.getparent().replace(target, node)
        report.append(
            {
                "property": b.property_id,
                "object_id": b.owner_id,
                "part": path,
                "xpath": b.xpath,
                "action": b.action,
                "matches": len(targets),
                "status": "explicit_native_xml",
                "validation": "package_and_relationships; semantic equivalence requires a reference file",
            }
        )
    for path, tree in trees.items():
        parts[path] = etree.tostring(
            tree, xml_declaration=True, encoding="UTF-8", standalone=True
        )
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as z:
        for n, value in parts.items():
            z.writestr(n, value)
    return stream.getvalue(), report
