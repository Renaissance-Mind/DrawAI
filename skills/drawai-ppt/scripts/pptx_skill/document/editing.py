"""Explicit override removal; omission alone does not erase template formatting."""

from .xml import FILL, replace, tag
from .rich import RUN_ATTRS, P_ATTRS, BODY_ATTRS


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
