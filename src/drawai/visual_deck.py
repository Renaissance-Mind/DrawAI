"""Save and verify the actual ordered page images shared by both conversion modes."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from PIL import Image

SCHEMA = "drawai.visual-deck.v1"


def ratio_value(ratio):
    values = ratio.split(":")
    if len(values) != 2 or any(not value.isdigit() or int(value) <= 0 for value in values):
        raise ValueError("aspect_ratio must be positive width:height")
    return int(values[0]) / int(values[1])


def save_visual_deck(spec_path, output):
    spec_path, output = Path(spec_path).resolve(), Path(output).resolve()
    spec = json.loads(spec_path.read_text())
    pages = spec.get("pages", [])
    if not pages:
        raise ValueError("A visual deck requires actual page images")
    ids = set()
    records = []
    ratio = spec.get("aspect_ratio")
    for index, page in enumerate(pages, 1):
        page_id = page.get("id", f"page-{index:03d}")
        if not isinstance(page_id, str) or not page_id.strip():
            raise ValueError("Page IDs must be non-empty strings")
        if page_id in ids:
            raise ValueError(f"Duplicate page id: {page_id}")
        ids.add(page_id)
        image_path = Path(page["image"])
        if not image_path.is_absolute():
            image_path = spec_path.parent / image_path
        image_path = image_path.resolve()
        if image_path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            raise ValueError("Page images must be PNG, JPEG or WebP; render other inputs first")
        with Image.open(image_path) as image:
            width, height = image.size
            image.verify()
        if ratio is None:
            divisor = math.gcd(width, height)
            ratio = f"{width // divisor}:{height // divisor}"
        if not math.isclose(width / height, ratio_value(ratio), rel_tol=0.005):
            raise ValueError(f"Page {page_id} does not match {ratio}; finish canvas adaptation in the design stage")
        records.append({
            **page, "id": page_id, "order": index, "image": str(image_path),
            "width": width, "height": height,
            "sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
        })
    deck = {**spec, "schema": SCHEMA, "aspect_ratio": ratio, "pages": records}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x") as stream:
        json.dump(deck, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return deck


def verify_visual_deck(path):
    path = Path(path).resolve()
    deck = json.loads(path.read_text())
    if deck.get("schema") != SCHEMA or not deck.get("pages"):
        raise ValueError("Expected a completed drawai.visual-deck.v1 manifest")
    ids = set()
    for index, page in enumerate(deck["pages"], 1):
        if page["id"] in ids or page["order"] != index:
            raise ValueError("Visual page IDs and order are invalid")
        ids.add(page["id"])
        image = Path(page["image"])
        if not image.is_absolute():
            raise ValueError("Saved visual page paths must be absolute")
        if hashlib.sha256(image.read_bytes()).hexdigest() != page["sha256"]:
            raise ValueError(f"Visual image changed: {page['id']}")
        with Image.open(image) as opened:
            if opened.size != (page["width"], page["height"]):
                raise ValueError("Saved image dimensions differ from actual image")
            opened.verify()
        if not math.isclose(page["width"] / page["height"], ratio_value(deck["aspect_ratio"]), rel_tol=0.005):
            raise ValueError("Visual page ratio differs from deck canvas")
    return deck


def main(argv=None):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    save = sub.add_parser("save")
    save.add_argument("spec")
    save.add_argument("output")
    verify = sub.add_parser("verify")
    verify.add_argument("manifest")
    args = parser.parse_args(argv)
    deck = save_visual_deck(args.spec, args.output) if args.action == "save" else verify_visual_deck(args.manifest)
    print(json.dumps({"schema": deck["schema"], "pages": len(deck["pages"]), "aspect_ratio": deck["aspect_ratio"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    main()
