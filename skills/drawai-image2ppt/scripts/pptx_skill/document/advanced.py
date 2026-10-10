"""Office-specific bindings kept separate from portable drawing constructors."""

from __future__ import annotations
import math
from lxml import etree
from .xml import EMU, color, el, ensure, ordered, replace, tag


def transform(shape, value):
    if isinstance(value, dict):
        value = [value[k] for k in ("a", "b", "c", "d", "e", "f")]
    if len(value) != 6:
        raise ValueError("Transform is [a,b,c,d,e,f], with translations in points")
    a, b, c, d, e, f = value
    sx = math.hypot(a, b)
    det = a * d - b * c
    if sx == 0 or det == 0:
        raise ValueError("Singular transform cannot retain an editable native frame")
    sy = det / sx
    if abs(a * c + b * d) > 1e-8 * max(sx, abs(sy)) ** 2:
        raise ValueError(
            "A shear needs geometry baking; an editable text/shape frame cannot represent it"
        )
    x = shape.left / EMU
    y = shape.top / EMU
    shape.left = round((a * x + c * y + e) * EMU)
    shape.top = round((b * x + d * y + f) * EMU)
    shape.width = round(shape.width * sx)
    shape.height = round(shape.height * abs(sy))
    shape.rotation = (shape.rotation + math.degrees(math.atan2(b, a))) % 360
    sp = shape._element.find(tag("p:spPr"))
    if sp is not None:
        ensure(sp, "a:xfrm").set("flipV", "1" if sy < 0 else "0")


def picture_options(shape, props, ctx):
    used = set()
    blip = shape._element.blipFill.blip
    if "picture.aspect_fit" in props:
        from PIL import Image
        from io import BytesIO

        image = Image.open(BytesIO(shape.image.blob))
        iw, ih = image.size
        w, h = shape.width, shape.height
        mode = props["picture.aspect_fit"]
        for key in ("left", "right", "top", "bottom"):
            setattr(shape, "crop_" + key, 0)
        if mode == "contain":
            scale = min(w / iw, h / ih)
            nw, nh = round(iw * scale), round(ih * scale)
            shape.left += (w - nw) // 2
            shape.top += (h - nh) // 2
            shape.width = nw
            shape.height = nh
        elif mode == "cover":
            scale = max(w / iw, h / ih)
            nw, nh = iw * scale, ih * scale
            shape.crop_left = shape.crop_right = (nw - w) / (2 * nw)
            shape.crop_top = shape.crop_bottom = (nh - h) / (2 * nh)
        used.add("picture.aspect_fit")
    if "picture.svg_asset" in props:
        from pptx.opc.package import Part
        from pptx.opc.constants import RELATIONSHIP_TYPE as RT

        value = props["picture.svg_asset"]
        asset_ref = value if isinstance(value, str) else value["asset_ref"]
        package = shape.part.package
        part = Part(
            package.next_partname("/ppt/media/vector%d.svg"),
            "image/svg+xml",
            package,
            ctx.asset(asset_ref),
        )
        rid = shape.part.relate_to(part, RT.IMAGE)
        extlst = ensure(blip, "a:extLst")
        ext = el("a:ext", {"uri": "{96DAC541-7B7A-43D3-8B79-37D633B846F1}"})
        node = etree.SubElement(
            ext, "{http://schemas.microsoft.com/office/drawing/2016/SVG/main}svgBlip"
        )
        node.set(tag("r:embed"), rid)
        extlst.append(ext)
        used.add("picture.svg_asset")
    for full, name, attrs in [
        ("picture.brightness", "a:lum", {"bright": 100000}),
        ("picture.contrast", "a:lum", {"contrast": 100000}),
        ("picture.alpha", "a:alphaModFix", {"amt": 100000}),
    ]:
        if full in props:
            node = ensure(blip, name)
            for k, mul in attrs.items():
                node.set(k, str(round(props[full] * mul)))
            used.add(full)
    if "picture.transparent_color" in props:
        source = color(props["picture.transparent_color"])
        target = deepcopy_color(source)
        target.append(el("a:alpha", {"val": 0}))
        replace(
            blip,
            "a:clrChange",
            el(
                "a:clrChange",
                {"useA": True},
                [el("a:clrFrom", children=[source]), el("a:clrTo", children=[target])],
            ),
        )
        used.add("picture.transparent_color")
    if "picture.recolor" in props:
        for v in props["picture.recolor"]:
            if v["kind"] == "grayscale":
                blip.append(el("a:grayscl"))
            elif v["kind"] == "duotone":
                blip.append(el("a:duotone", children=[color(c) for c in v["colors"]]))
            elif v["kind"] == "tint":
                blip.append(
                    el(
                        "a:tint",
                        {
                            "hue": round(v["hue"] * 60000),
                            "amt": round(v["amount"] * 100000),
                        },
                    )
                )
            else:
                raise ValueError(f"Picture recolor not supported: {v['kind']}")
        used.add("picture.recolor")
    if "picture.geometry_mask" in props:
        from .rich import geometry

        value = props["picture.geometry_mask"]
        geometry(shape._element.spPr, value)
        used.add("picture.geometry_mask")
    return used


def deepcopy_color(node):
    from copy import deepcopy

    return deepcopy(node)


def theme_properties(prs, props):
    used = set()
    if not any(k.startswith("theme.") for k in props):
        return used
    from pptx.opc.constants import RELATIONSHIP_TYPE as RT

    theme = prs.slide_masters[0].part.part_related_by(RT.THEME)
    tree = etree.fromstring(theme.blob)
    elements = tree.find(tag("a:themeElements"))
    if "theme.colors" in props:
        colors = props["theme.colors"]
        scheme = elements.find(tag("a:clrScheme"))
        for key, value in colors.items():
            replace(scheme, "a:" + key, el("a:" + key, children=[color(value)]))
        used.add("theme.colors")
    for full, name in [
        ("theme.fonts.major", "a:majorFont"),
        ("theme.fonts.minor", "a:minorFont"),
    ]:
        if full in props:
            target = elements.find(tag("a:fontScheme")).find(tag(name))
            value = props[full]
            for key, native in [
                ("latin", "a:latin"),
                ("east_asian", "a:ea"),
                ("complex_script", "a:cs"),
            ]:
                if key in value:
                    replace(target, native, el(native, {"typeface": value[key]}))
            if "scripts" in value:
                for node in list(target):
                    if node.tag == tag("a:font"):
                        target.remove(node)
                target.extend(
                    el("a:font", {"script": s, "typeface": f})
                    for s, f in value["scripts"].items()
                )
            ordered(target, ["a:latin", "a:ea", "a:cs", "a:font"])
            used.add(full)
    for full, name in [
        ("theme.format_scheme", "a:fmtScheme"),
        ("theme.defaults", "a:objectDefaults"),
        ("theme.extra_color_schemes", "a:extraClrSchemeLst"),
    ]:
        if full in props:
            value = etree.fromstring(
                props[full].encode(),
                etree.XMLParser(resolve_entities=False, no_network=True),
            )
            if value.tag != tag(name):
                raise ValueError(f"{full} needs an exact {name} tree")
            replace(elements if full == "theme.format_scheme" else tree, name, value)
            used.add(full)
    ordered(elements, ["a:clrScheme", "a:fontScheme", "a:fmtScheme"])
    theme._blob = etree.tostring(
        tree, xml_declaration=True, encoding="UTF-8", standalone=True
    )
    return used


def object_extensions(shape, props):
    used = set()
    nv = shape._element.find(".//" + tag("p:cNvPr"))
    if "object.transform" in props:
        transform(shape, props["object.transform"])
        used.add("object.transform")
    if "object.style_ref" in props:
        value = props["object.style_ref"]
        node = el("p:style")
        for key, name in [
            ("line", "a:lnRef"),
            ("fill", "a:fillRef"),
            ("effect", "a:effectRef"),
            ("font", "a:fontRef"),
        ]:
            if key not in value:
                raise ValueError(
                    "Object style_ref needs line/fill/effect/font references"
                )
            v = value[key]
            node.append(
                el(
                    name,
                    {"idx": v["index"]},
                    [color(v.get("color", {"kind": "scheme", "channels": "accent1"}))],
                )
            )
        replace(shape._element, "p:style", node)
        used.add("object.style_ref")
    if "accessibility.decorative" in props and nv is not None:
        ns = "http://schemas.microsoft.com/office/drawing/2017/decorative"
        extlst = ensure(nv, "a:extLst")
        uri = "{C183D7F6-B498-43B3-948B-1728B52AA6E4}"
        for old in list(extlst):
            if old.get("uri") == uri:
                extlst.remove(old)
        ext = el("a:ext", {"uri": uri})
        dec = etree.SubElement(ext, "{" + ns + "}decorative")
        dec.set("val", "1" if props["accessibility.decorative"] else "0")
        extlst.append(ext)
        used.add("accessibility.decorative")
    if "compatibility.extension_list" in props and nv is not None:
        extlst = ensure(nv, "a:extLst")
        for uri, xml in props["compatibility.extension_list"].items():
            for old in list(extlst):
                if old.get("uri") == uri:
                    extlst.remove(old)
            extlst.append(
                el(
                    "a:ext",
                    {"uri": uri},
                    [
                        etree.fromstring(
                            xml.encode(),
                            etree.XMLParser(resolve_entities=False, no_network=True),
                        )
                    ],
                )
            )
        used.add("compatibility.extension_list")
    if shape._element.tag == tag("p:pic"):
        ordered(
            shape._element, ["p:nvPicPr", "p:blipFill", "p:spPr", "p:style", "p:extLst"]
        )
    elif shape._element.tag == tag("p:sp"):
        ordered(
            shape._element, ["p:nvSpPr", "p:spPr", "p:style", "p:txBody", "p:extLst"]
        )
    return used
