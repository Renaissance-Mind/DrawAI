"""Explicit override removal; omission alone does not erase template formatting."""

from copy import deepcopy
from .model import load_document, PROPERTIES
from .identity import fresh_identity
from .xml import FILL, replace, tag
from .rich import RUN_ATTRS, P_ATTRS, BODY_ATTRS


def duplicate_page(document, page_id, *, new_id=None):
    """Return a document with one appended page, assigning fresh semantic IDs."""
    doc = load_document(document)
    matches = [page for page in doc.pages if page.id == page_id]
    if len(matches) != 1:
        raise ValueError(f"Expected one page {page_id!r}, found {len(matches)}")
    source = matches[0]
    copied = deepcopy(source)
    mapping = {source.id: new_id or fresh_identity(source.id)}

    def rename(obj):
        old = obj.id
        obj.id = mapping.setdefault(old, fresh_identity(old))
        if "object.id" in obj.properties:
            obj.properties["object.id"] = obj.id
        for child in obj.children:
            rename(child)

    copied.id = mapping[source.id]
    for obj in copied.objects:
        rename(obj)
    if any(binding.owner_id in mapping for binding in doc.native_bindings):
        raise ValueError(
            "This page has explicit native_bindings; copy it with retargeted package bindings"
        )

    def remap(value):
        if isinstance(value, str):
            return mapping.get(value, value)
        if isinstance(value, dict):
            return {key: remap(item) for key, item in value.items()}
        if isinstance(value, list):
            return [remap(item) for item in value]
        return value

    def references(obj):
        for key, value in obj.properties.items():
            if "ref" in PROPERTIES[key]["value_type"]:
                obj.properties[key] = remap(value)
        for child in obj.children:
            references(child)

    for obj in copied.objects:
        references(obj)
    doc.pages.append(copied)
    return load_document(doc)


def clear_overrides(shape, keys):
    for full in keys:
        nodes = []
        attribute = None
        children = []
        if full.startswith("text.run."):
            key = full[len("text.run.") :]
            nodes = [
                n
                for n in shape._element.iter()
                if n.tag in (tag("a:rPr"), tag("a:defRPr"), tag("a:endParaRPr"))
            ]
            if key in RUN_ATTRS:
                attribute = RUN_ATTRS[key][0]
            elif key == "fill":
                children = list(FILL)
            elif key == "outline":
                children = ["a:ln"]
            elif key.startswith("font.") and key[5:] in (
                "latin",
                "east_asian",
                "complex_script",
                "symbol",
            ):
                children = [
                    {
                        "latin": "a:latin",
                        "east_asian": "a:ea",
                        "complex_script": "a:cs",
                        "symbol": "a:sym",
                    }[key[5:]]
                ]
            else:
                raise ValueError(f"Override removal not mapped: {full}")
        elif full.startswith("text.paragraph."):
            key = full[len("text.paragraph.") :]
            nodes = list(shape._element.iter(tag("a:pPr")))
            if key in P_ATTRS:
                attribute = P_ATTRS[key][0]
            elif key in ("line_spacing", "space_before", "space_after"):
                children = [
                    {
                        "line_spacing": "a:lnSpc",
                        "space_before": "a:spcBef",
                        "space_after": "a:spcAft",
                    }[key]
                ]
            elif key.startswith("bullet."):
                children = [
                    "a:buNone",
                    "a:buAutoNum",
                    "a:buChar",
                    "a:buBlip",
                    "a:buClr",
                    "a:buFont",
                    "a:buSzPts",
                    "a:buSzPct",
                ]
            else:
                raise ValueError(f"Override removal not mapped: {full}")
        elif full.startswith("text.body."):
            key = full[len("text.body.") :]
            nodes = list(shape._element.iter(tag("a:bodyPr")))
            if key in BODY_ATTRS:
                attribute = BODY_ATTRS[key][0]
            elif key == "autofit":
                children = ["a:noAutofit", "a:normAutofit", "a:spAutoFit"]
            else:
                raise ValueError(f"Override removal not mapped: {full}")
        elif full in (
            "object.rotation",
            "object.flip_horizontal",
            "object.flip_vertical",
        ):
            nodes = list(shape._element.iter(tag("a:xfrm")))
            attribute = {
                "object.rotation": "rot",
                "object.flip_horizontal": "flipH",
                "object.flip_vertical": "flipV",
            }[full]
        elif full == "paint.kind":
            nodes = [n for n in shape._element if n.tag == tag("p:spPr")]
            children = list(FILL)
        elif full.startswith("stroke."):
            nodes = list(shape._element.iter(tag("a:ln")))
            native = {
                "stroke.width": "w",
                "stroke.cap": "cap",
                "stroke.compound": "cmpd",
                "stroke.alignment": "algn",
            }
            if full in native:
                attribute = native[full]
            elif full == "stroke.paint":
                children = list(FILL)
            else:
                raise ValueError(f"Override removal not mapped: {full}")
        else:
            raise ValueError(f"Override removal not mapped: {full}")
        for node in nodes:
            if attribute:
                node.attrib.pop(attribute, None)
            for name in children:
                replace(node, name, None)
