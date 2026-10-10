"""Local visual fallback for SVG filter defects, with explicit loss records."""

from io import BytesIO
import base64
import math
from lxml import etree
from PIL import Image

SVG = "{http://www.w3.org/2000/svg}"


def path_gradient_objects(page):
    return [
        obj
        for obj in page.objects
        if obj.properties.get("paint.kind") == "gradient"
        and obj.properties.get("paint.gradient.kind") in ("rect", "shape")
    ]


def apply_gradient_fallback(tree, page, preview, slide_width, slide_height):
    issues = []
    _, _, vw, vh = map(float, tree.get("viewBox").split())
    image = Image.open(preview).convert("RGB")
    px_x, px_y = image.width / slide_width, image.height / slide_height
    unit_x, unit_y = vw / slide_width, vh / slide_height
    boxes = tree.xpath('//*[local-name()="rect" and @class="BoundingBox"]')
    covered = set()
    for obj in path_gradient_objects(page):
        if obj.id in covered:
            continue
        props = obj.properties
        if props.get("object.rotation", 0) or "object.transform" in props:
            issues.append(
                {
                    "object_id": obj.id,
                    "property": "paint.gradient.kind",
                    "status": "approximation",
                    "reason": "Rotated/transformed path gradient retains the office SVG approximation.",
                }
            )
            continue
        frame = props["object.frame"]
        x, y, w, h = [frame[k] for k in ("left", "top", "width", "height")]
        target = (x * unit_x, y * unit_y, w * unit_x, h * unit_y)
        candidates = []
        for box in boxes:
            if box.getparent().getparent().getparent() is None:
                continue
            boxframe = tuple(
                float(box.get(k, 0)) for k in ("x", "y", "width", "height")
            )
            error = sum(abs(a - b) for a, b in zip(target, boxframe))
            if error < max(1000, max(target[2:]) * 0.2):
                candidates.append((error, box))
        if not candidates:
            raise ValueError(
                f"Cannot identify the exported SVG path gradient region for {obj.id}"
            )
        box = min(candidates, key=lambda c: c[0])[1]
        drawing = box.getparent().getparent()
        parent = drawing.getparent()
        # Include the shadow margin. Rasterize contained captions together so font
        # positioning does not produce a doubled text overlay at the same location.
        margin = 6
        left = max(0, math.floor((x - margin) * px_x))
        top = max(0, math.floor((y - margin) * px_y))
        right = min(image.width, math.ceil((x + w + margin) * px_x))
        bottom = min(image.height, math.ceil((y + h + margin) * px_y))
        if right <= left or bottom <= top:
            continue
        out = BytesIO()
        image.crop((left, top, right, bottom)).save(out, format="PNG")
        node = etree.Element(
            SVG + "image",
            {
                "x": str(left / image.width * vw),
                "y": str(top / image.height * vh),
                "width": str((right - left) / image.width * vw),
                "height": str((bottom - top) / image.height * vh),
                "preserveAspectRatio": "none",
            },
        )
        node.set(
            "{http://www.w3.org/1999/xlink}href",
            "data:image/png;base64," + base64.b64encode(out.getvalue()).decode(),
        )
        index = parent.index(drawing)
        removed = []
        for child in list(parent):
            bounds = child.find(".//" + SVG + 'rect[@class="BoundingBox"]')
            if bounds is None:
                continue
            bx, by, bw, bh = [
                float(bounds.get(k, 0)) for k in ("x", "y", "width", "height")
            ]
            if (
                bx >= left / image.width * vw - 2
                and by >= top / image.height * vh - 2
                and bx + bw <= right / image.width * vw + 2
                and by + bh <= bottom / image.height * vh + 2
            ):
                parent.remove(child)
                removed.append(child.get("id", bounds.getparent().get("id")))
        parent.insert(min(index, len(parent)), node)
        affected = [
            o.id
            for o in page.objects
            if "object.frame" in o.properties
            and o.properties["object.frame"]["left"] >= x - margin
            and o.properties["object.frame"]["top"] >= y - margin
            and o.properties["object.frame"]["left"]
            + o.properties["object.frame"]["width"]
            <= x + w + margin
            and o.properties["object.frame"]["top"]
            + o.properties["object.frame"]["height"]
            <= y + h + margin
        ]
        covered.update(affected)
        issues.append(
            {
                "object_id": obj.id,
                "property": "paint.gradient.kind",
                "status": "raster_visual_fallback",
                "affected_objects": affected,
                "requested": props["paint.gradient.kind"],
                "reason": "Office SVG filter changes this path gradient. The actual PPTX PDF region is embedded as PNG; editable settings remain in the source/PPTX.",
                "resolution_dpi": 192,
            }
        )
    return issues
