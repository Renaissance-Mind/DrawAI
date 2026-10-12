"""DrawingML constructors. No XML string interpolation or implicit pixel units."""

from __future__ import annotations
from lxml import etree
from pptx.oxml.ns import nsmap
from io import BytesIO
import base64
import re

NS = dict(
    nsmap("a", "p", "r", "c"),
    m="http://schemas.openxmlformats.org/officeDocument/2006/math",
    a14="http://schemas.microsoft.com/office/drawing/2010/main",
    p14="http://schemas.microsoft.com/office/powerpoint/2010/main",
)
EMU = 12700


def tag(name):
    prefix, local = name.split(":")
    return "{" + NS[prefix] + "}" + local


def el(name, attrs=None, children=()):
    node = etree.Element(tag(name))
    for key, value in (attrs or {}).items():
        if value is not None:
            node.set(
                tag(key) if ":" in key else key,
                "1" if value is True else "0" if value is False else str(value),
            )
    node.extend(children)
    return node


def replace(parent, name, node):
    for old in list(parent):
        if old.tag == tag(name):
            parent.remove(old)
    if node is not None:
        parent.append(node)
    return node


def ensure(parent, name):
    found = parent.find(tag(name))
    return found if found is not None else replace(parent, name, el(name))


def clear_choice(parent, names):
    for child in list(parent):
        if child.tag in {tag(n) for n in names}:
            parent.remove(child)


FILL = (
    "a:noFill",
    "a:solidFill",
    "a:gradFill",
    "a:blipFill",
    "a:pattFill",
    "a:grpFill",
)


def asset_data(asset, root):
    if "data" in asset:
        return base64.b64decode(asset["data"], validate=True)
    path = root / asset["path"]
    return path.read_bytes()


def rgb_hex(value):
    value = str(value).lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    if not re.fullmatch("[0-9a-fA-F]{6}", value):
        raise ValueError(f"RGB color must be 3 or 6 hex digits: {value}")
    return value.upper()


def color(value):
    if isinstance(value, str):
        return el("a:srgbClr", {"val": rgb_hex(value)})
    kind = value.get("kind", "rgb")
    ch = value.get("channels", value.get("value"))
    if kind == "rgb":
        node = el("a:srgbClr", {"val": rgb_hex(ch)})
    elif kind == "scheme":
        node = el("a:schemeClr", {"val": ch})
    elif kind == "system":
        node = el("a:sysClr", {"val": ch, "lastClr": value.get("fallback", "000000")})
    elif kind == "preset":
        node = el("a:prstClr", {"val": ch})
    elif kind == "scrgb":
        node = el(
            "a:scrgbClr", dict(zip(("r", "g", "b"), [round(v * 100000) for v in ch]))
        )
    elif kind == "hsl":
        node = el(
            "a:hslClr",
            {
                "hue": round(ch[0] * 60000),
                "sat": round(ch[1] * 100000),
                "lum": round(ch[2] * 100000),
            },
        )
    else:
        raise ValueError(f"Unknown color kind {kind}")
    if "alpha" in value:
        if not 0 <= value["alpha"] <= 1:
            raise ValueError("Color alpha must be within [0,1]")
        node.append(el("a:alpha", {"val": round(value["alpha"] * 100000)}))
    for transform in value.get("transforms", []):
        name = transform["kind"]
        amount = transform.get("value")
        unit = 60000 if name in ("hue", "hueOff") else 100000
        node.append(
            el("a:" + name, {"val": None if amount is None else round(amount * unit)})
        )
    return node


def rect_attrs(value):
    return {
        key: round(value.get(key, value.get(long, 0)) * 100000)
        for key, long in [("l", "left"), ("t", "top"), ("r", "right"), ("b", "bottom")]
    }


def paint(value, part, assets, root):
    if isinstance(value, str):
        value = (
            {"kind": "none"} if value == "none" else {"kind": "solid", "color": value}
        )
    kind = value["kind"]
    if kind == "none":
        return el("a:noFill")
    if kind == "solid":
        return el("a:solidFill", children=[color(value["color"])])
    if kind == "group_inherit":
        return el("a:grpFill")
    if kind == "gradient":
        node = el(
            "a:gradFill",
            {
                "rotWithShape": value.get("rotate_with_shape", True),
                "flip": value.get("flip"),
            },
        )
        stops = [
            {**s, "position": s.get("position", s.get("offset"))}
            for s in value["stops"]
        ]
        if len(stops) < 2 or any(not 0 <= s["position"] <= 1 for s in stops):
            raise ValueError("Gradient needs at least two stops in [0,1]")
        node.append(
            el(
                "a:gsLst",
                children=[
                    el(
                        "a:gs",
                        {"pos": round(s["position"] * 100000)},
                        [color(s["color"])],
                    )
                    for s in sorted(stops, key=lambda s: s["position"])
                ],
            )
        )
        gradient = value.get("gradient_kind", "linear")
        if gradient == "linear":
            node.append(
                el(
                    "a:lin",
                    {
                        "ang": round(value.get("angle", 0) * 60000),
                        "scaled": value.get("scaled", True),
                    },
                )
            )
        else:
            if gradient not in ("circle", "rect", "shape"):
                raise ValueError(f"Invalid gradient kind {gradient}")
            node.append(
                el(
                    "a:path",
                    {"path": gradient},
                    [el("a:fillToRect", rect_attrs(value.get("fill_to_rect", {})))],
                )
            )
        if "tile_rect" in value:
            node.append(el("a:tileRect", rect_attrs(value["tile_rect"])))
        return node
    if kind == "pattern":
        return el(
            "a:pattFill",
            {"prst": value["preset"]},
            [
                el("a:fgClr", children=[color(value["foreground"])]),
                el("a:bgClr", children=[color(value["background"])]),
            ],
        )
    if kind == "image":
        _, rid = part.get_or_add_image_part(
            BytesIO(asset_data(assets[value["asset_ref"]], root))
        )
        node = el(
            "a:blipFill",
            {"rotWithShape": value.get("rotate_with_shape", True)},
            [el("a:blip", {"r:embed": rid})],
        )
        if "crop" in value:
            node.append(el("a:srcRect", rect_attrs(value["crop"])))
        if value.get("mode", "stretch") == "tile":
            off, scale = (
                value.get("tile_offset", [0, 0]),
                value.get("tile_scale", [1, 1]),
            )
            if isinstance(off, dict):
                off = [off["x"], off["y"]]
            if isinstance(scale, dict):
                scale = [scale["x"], scale["y"]]
            node.append(
                el(
                    "a:tile",
                    {
                        "tx": round(off[0] * EMU),
                        "ty": round(off[1] * EMU),
                        "sx": round(scale[0] * 100000),
                        "sy": round(scale[1] * 100000),
                        "algn": value.get("tile_alignment", "ctr"),
                        "flip": value.get("tile_flip", "none"),
                    },
                )
            )
        else:
            node.append(
                el(
                    "a:stretch",
                    children=[
                        el("a:fillRect", rect_attrs(value.get("stretch_rect", {})))
                    ],
                )
            )
        return node
    raise ValueError(f"Unsupported paint {kind}")


def set_paint(parent, value, part, assets, root):
    clear_choice(parent, FILL)
    parent.append(paint(value, part, assets, root))


def stroke(value, part, assets, root):
    node = el(
        "a:ln",
        {
            "w": round(value.get("width", 1) * EMU),
            "cap": value.get("cap"),
            "cmpd": value.get("compound"),
            "algn": value.get("alignment"),
        },
    )
    node.append(paint(value.get("paint", "none"), part, assets, root))
    if "dash_custom" in value:
        node.append(
            el(
                "a:custDash",
                children=[
                    el(
                        "a:ds",
                        {
                            "d": round(
                                (d["dash"] if isinstance(d, dict) else d[0]) * 100000
                            ),
                            "sp": round(
                                (d["gap"] if isinstance(d, dict) else d[1]) * 100000
                            ),
                        },
                    )
                    for d in value["dash_custom"]
                ],
            )
        )
    elif "dash_preset" in value:
        node.append(el("a:prstDash", {"val": value["dash_preset"]}))
    if "join" in value:
        node.append(
            el(
                "a:" + value["join"],
                {"lim": round(value.get("miter_limit", 8) * 100000)}
                if value["join"] == "miter"
                else {},
            )
        )
    for side, native in [("start_arrow", "headEnd"), ("end_arrow", "tailEnd")]:
        if side in value:
            a = value[side]
            node.append(
                el(
                    "a:" + native,
                    {
                        "type": a.get("kind", "none"),
                        "w": a.get("width", "med"),
                        "len": a.get("length", "med"),
                    },
                )
            )
    return node


def spacing(name, value):
    if isinstance(value, (int, float)):
        value = {"mode": "points", "value": value}
    return el(
        "a:" + name,
        children=[
            el(
                "a:spcPts" if value["mode"] == "points" else "a:spcPct",
                {
                    "val": round(
                        value["value"] * (100 if value["mode"] == "points" else 100000)
                    )
                },
            )
        ],
    )


def ordered(parent, order):
    # Schema sequence order matters in DrawingML, even if some readers tolerate it.
    index = {tag(n): i for i, n in enumerate(order)}
    children = list(parent)
    children.sort(key=lambda n: index.get(n.tag, len(index)))
    parent[:] = children


SP_ORDER = [
    "a:xfrm",
    "a:custGeom",
    "a:prstGeom",
    *FILL,
    "a:ln",
    "a:effectLst",
    "a:effectDag",
    "a:scene3d",
    "a:sp3d",
    "a:extLst",
]
RUN_ORDER = [
    "a:ln",
    *FILL,
    "a:effectLst",
    "a:effectDag",
    "a:highlight",
    "a:uLnTx",
    "a:uLn",
    "a:uFillTx",
    "a:uFill",
    "a:latin",
    "a:ea",
    "a:cs",
    "a:sym",
    "a:hlinkClick",
    "a:hlinkMouseOver",
    "a:rtl",
    "a:extLst",
]
P_ORDER = [
    "a:lnSpc",
    "a:spcBef",
    "a:spcAft",
    "a:buClrTx",
    "a:buClr",
    "a:buSzTx",
    "a:buSzPct",
    "a:buSzPts",
    "a:buFontTx",
    "a:buFont",
    "a:buNone",
    "a:buAutoNum",
    "a:buChar",
    "a:buBlip",
    "a:tabLst",
    "a:defRPr",
    "a:extLst",
]
