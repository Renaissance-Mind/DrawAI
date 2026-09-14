#!/usr/bin/env python3
"""Run rule-based DrawAI-Bench reconstruction/editability evaluation for one case."""

from __future__ import annotations

import argparse
import json
import math
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import cv2
import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity

SCHEMA_VERSION = "drawai_eval_rule_based.v1"
DEFAULT_IMAGE_MSE_THRESHOLD = 0.02


@dataclass(frozen=True)
class Box:
    x: float
    y: float
    w: float
    h: float

    @property
    def area(self) -> float:
        return max(0.0, self.w) * max(0.0, self.h)

    @property
    def center(self) -> tuple[float, float]:
        return (self.x + self.w / 2.0, self.y + self.h / 2.0)

    @property
    def diagonal(self) -> float:
        return math.hypot(self.w, self.h)

    def as_list(self) -> list[float]:
        return [self.x, self.y, self.w, self.h]

    def clamp(self, width: int, height: int) -> tuple[int, int, int, int]:
        x0 = max(0, min(width, int(round(self.x))))
        y0 = max(0, min(height, int(round(self.y))))
        x1 = max(0, min(width, int(round(self.x + self.w))))
        y1 = max(0, min(height, int(round(self.y + self.h))))
        return x0, y0, x1, y1


@dataclass(frozen=True)
class SpecElement:
    id: str
    kind: str
    box: Box
    text: str | None
    role: str | None = None


@dataclass(frozen=True)
class SvgElement:
    tag: str
    id: str | None
    element_id: str | None
    box: Box
    text: str | None = None
    href: str | None = None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case-dir",
        type=Path,
        help="Directory containing gt_page_spec.json, reference.png, and candidate.svg.",
    )
    parser.add_argument(
        "--gt-spec", type=Path, help="GT PageSpec JSON. Defaults to case-dir/gt_page_spec.json."
    )
    parser.add_argument(
        "--reference-image", type=Path, help="Reference image. Defaults to case-dir/reference.png."
    )
    parser.add_argument(
        "--candidate-svg", type=Path, help="Candidate SVG. Defaults to case-dir/candidate.svg."
    )
    parser.add_argument(
        "--rendered-png",
        type=Path,
        help="Rendered candidate PNG. Defaults to case-dir/drawai_rendered.png.",
    )
    parser.add_argument(
        "--output-json", type=Path, help="Output JSON. Defaults to case-dir/rule_based_eval.json."
    )
    parser.add_argument("--case-id", help="Optional case id override.")
    parser.add_argument("--bench-id", help="Optional bench id override.")
    parser.add_argument(
        "--force-render",
        action="store_true",
        help="Render candidate SVG even if rendered PNG already exists.",
    )
    parser.add_argument(
        "--skip-render",
        action="store_true",
        help="Do not render; require rendered PNG to already exist.",
    )
    parser.add_argument("--image-mse-threshold", type=float, default=DEFAULT_IMAGE_MSE_THRESHOLD)
    parser.add_argument("--image-iou-threshold", type=float, default=0.5)
    parser.add_argument("--text-box-iou-threshold", type=float, default=0.5)
    parser.add_argument("--text-sim-threshold", type=float, default=0.8)
    parser.add_argument("--edge-canny-low", type=int, default=50)
    parser.add_argument("--edge-canny-high", type=int, default=100)
    parser.add_argument(
        "--edge-blur-kernel",
        type=int,
        default=5,
        help="Odd Gaussian blur kernel size before Canny; 0 disables blur.",
    )
    parser.add_argument("--edge-dilation", type=int, default=1)
    args = parser.parse_args()

    paths = resolve_paths(args)
    gt_spec = read_json(paths["gt_spec"])
    canvas_width, canvas_height = canvas_size(gt_spec)

    if not args.skip_render and (args.force_render or not paths["rendered_png"].exists()):
        render_svg(paths["candidate_svg"], paths["rendered_png"], canvas_width, canvas_height)
    if not paths["rendered_png"].exists():
        raise FileNotFoundError(f"rendered PNG does not exist: {paths['rendered_png']}")

    result = evaluate_case(
        gt_spec=gt_spec,
        gt_spec_path=paths["gt_spec"],
        reference_image=paths["reference_image"],
        candidate_svg=paths["candidate_svg"],
        rendered_png=paths["rendered_png"],
        case_id=args.case_id,
        bench_id=args.bench_id,
        image_mse_threshold=args.image_mse_threshold,
        image_iou_threshold=args.image_iou_threshold,
        text_box_iou_threshold=args.text_box_iou_threshold,
        text_sim_threshold=args.text_sim_threshold,
        edge_canny_low=args.edge_canny_low,
        edge_canny_high=args.edge_canny_high,
        edge_blur_kernel=args.edge_blur_kernel,
        edge_dilation=args.edge_dilation,
    )
    write_json(paths["output_json"], result)
    print(f"[rule-based-eval] wrote {paths['output_json']}")
    return 0


def resolve_paths(args: argparse.Namespace) -> dict[str, Path]:
    case_dir = args.case_dir.expanduser().resolve(strict=False) if args.case_dir else None

    def pick(value: Path | None, default_name: str) -> Path:
        if value is not None:
            return value.expanduser().resolve(strict=False)
        if case_dir is None:
            raise ValueError(f"--{default_name.replace('_', '-')} is required without --case-dir")
        return (case_dir / default_name).resolve(strict=False)

    gt_spec = pick(args.gt_spec, "gt_page_spec.json")
    reference_image = pick(args.reference_image, "reference.png")
    candidate_svg = pick(args.candidate_svg, "candidate.svg")
    rendered_png = (
        args.rendered_png.expanduser().resolve(strict=False)
        if args.rendered_png
        else (case_dir / "drawai_rendered.png").resolve(strict=False)
        if case_dir
        else candidate_svg.with_suffix(".rendered.png")
    )
    output_json = (
        args.output_json.expanduser().resolve(strict=False)
        if args.output_json
        else (case_dir / "rule_based_eval.json").resolve(strict=False)
        if case_dir
        else candidate_svg.with_name("rule_based_eval.json")
    )
    return {
        "gt_spec": gt_spec,
        "reference_image": reference_image,
        "candidate_svg": candidate_svg,
        "rendered_png": rendered_png,
        "output_json": output_json,
    }


def evaluate_case(
    *,
    gt_spec: dict[str, Any],
    gt_spec_path: Path,
    reference_image: Path,
    candidate_svg: Path,
    rendered_png: Path,
    case_id: str | None,
    bench_id: str | None,
    image_mse_threshold: float,
    image_iou_threshold: float,
    text_box_iou_threshold: float,
    text_sim_threshold: float,
    edge_canny_low: int,
    edge_canny_high: int,
    edge_blur_kernel: int,
    edge_dilation: int,
) -> dict[str, Any]:
    canvas_width, canvas_height = canvas_size(gt_spec)
    reference = load_rgb_canvas(reference_image, canvas_width, canvas_height)
    rendered = load_rgb_canvas(rendered_png, canvas_width, canvas_height)
    reference_arr = np.asarray(reference, dtype=np.float32) / 255.0
    rendered_arr = np.asarray(rendered, dtype=np.float32) / 255.0

    global_metrics = compute_global_metrics(
        reference_arr,
        rendered_arr,
        edge_canny_low=edge_canny_low,
        edge_canny_high=edge_canny_high,
        edge_blur_kernel=edge_blur_kernel,
        edge_dilation=edge_dilation,
    )

    gt_elements = parse_gt_elements(gt_spec)
    svg_elements = parse_svg_elements(candidate_svg, canvas_width, canvas_height)
    gt_text = [element for element in gt_elements if element.kind == "text"]
    gt_images = [element for element in gt_elements if element.kind == "image"]
    gt_formulas = [element for element in gt_elements if element.kind == "formula"]
    svg_text = [element for element in svg_elements if element.tag == "text"]
    svg_images = [element for element in svg_elements if element.tag == "image"]
    svg_editable = [element for element in svg_elements if element.tag != "image"]

    text_content_matches = match_text_content(gt_text, svg_text, text_sim_threshold)
    text_box_matches = match_text_boxes(gt_text, svg_text, text_box_iou_threshold)
    image_object_matches = match_images(gt_images, svg_images, image_iou_threshold)
    formula_editable_matches = match_formula_editability(gt_formulas, svg_editable)
    image_region_mses = compute_image_region_mses(gt_images, reference_arr, rendered_arr)
    image_object_matched_ids = {match["gt_id"] for match in image_object_matches}
    image_fallback = [
        {
            "id": item["gt_id"],
            "role": item["role"],
            "mse": item["mse"],
        }
        for item in image_region_mses
        if item["gt_id"] not in image_object_matched_ids and item["mse"] < image_mse_threshold
    ]
    image_failed = [
        {
            "id": item["gt_id"],
            "role": item["role"],
            "mse": item["mse"],
        }
        for item in image_region_mses
        if item["gt_id"] not in image_object_matched_ids and item["mse"] >= image_mse_threshold
    ]

    if gt_text:
        text_precision = safe_div(len(text_content_matches), len(svg_text))
        text_recall = safe_div(len(text_content_matches), len(gt_text))
        text_f1 = safe_div(2 * text_precision * text_recall, text_precision + text_recall)
        text_box_recall = safe_div(len(text_box_matches), len(gt_text))
    else:
        text_precision = None
        text_recall = None
        text_f1 = None
        text_box_recall = None
    image_recalled_total = len(image_object_matches) + len(image_fallback)
    image_region_mse_values = [item["mse"] for item in image_region_mses]
    image_miou_values = [match["iou"] for match in image_object_matches]

    counts = {
        "gt_text": len(gt_text),
        "candidate_text": len(svg_text),
        "matched_text_boxes": len(text_box_matches),
        "text_content_tp": len(text_content_matches),
        "gt_image": len(gt_images),
        "candidate_image": len(svg_images),
        "matched_images": len(image_object_matches),
        "object_matched_images": len(image_object_matches),
        "mse_fallback_images": len(image_fallback),
        "recalled_images_total": image_recalled_total,
        "image_region_mse_below_threshold": sum(
            1 for value in image_region_mse_values if value < image_mse_threshold
        ),
        "gt_formula": len(gt_formulas),
        "editable_formula_matches": len(formula_editable_matches),
    }
    metrics = {
        "ssim": global_metrics["ssim"],
        "mse": global_metrics["mse"],
        "edge_precision": global_metrics["edge_precision"],
        "edge_recall": global_metrics["edge_recall"],
        "edge_f1": global_metrics["edge_f1"],
        "text_box_recall": text_box_recall,
        "text_precision": text_precision,
        "text_recall": text_recall,
        "text_f1": text_f1,
        "image_object_recall": safe_div(len(image_object_matches), len(gt_images))
        if gt_images
        else None,
        "image_recall": safe_div(image_recalled_total, len(gt_images)) if gt_images else None,
        "image_miou": safe_div(sum(image_miou_values), len(gt_images)) if gt_images else None,
        "image_region_mse": float(np.mean(image_region_mse_values))
        if image_region_mse_values
        else None,
        "image_region_mse_median": float(np.median(image_region_mse_values))
        if image_region_mse_values
        else None,
        "image_region_mse_threshold": image_mse_threshold,
        "image_region_mse_pass_rate": (
            safe_div(
                sum(1 for value in image_region_mse_values if value < image_mse_threshold),
                len(gt_images),
            )
            if gt_images
            else None
        ),
        "formula_editable_representation": (
            safe_div(len(formula_editable_matches), len(gt_formulas)) if gt_formulas else None
        ),
    }

    gt_text_matched_ids = {match["gt_id"] for match in text_content_matches}
    gt_text_box_matched_ids = {match["gt_id"] for match in text_box_matches}
    gt_image_unmatched_object_ids = [
        element.id for element in gt_images if element.id not in image_object_matched_ids
    ]
    gt_image_recalled_ids = image_object_matched_ids | {item["id"] for item in image_fallback}

    return {
        "schema": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "case_id": case_id or infer_case_id(gt_spec, candidate_svg),
        "bench_id": bench_id or gt_spec.get("page_id"),
        "inputs": {
            "gt_page_spec": str(gt_spec_path),
            "reference_image": str(reference_image),
            "candidate_svg": str(candidate_svg),
            "rendered_png": str(rendered_png),
        },
        "canvas": {
            "width_px": canvas_width,
            "height_px": canvas_height,
        },
        "parameters": {
            "image_mse_threshold": image_mse_threshold,
            "image_iou_threshold": image_iou_threshold,
            "text_box_iou_threshold": text_box_iou_threshold,
            "text_sim_threshold": text_sim_threshold,
            "edge_canny_low": edge_canny_low,
            "edge_canny_high": edge_canny_high,
            "edge_blur_kernel": edge_blur_kernel,
            "edge_dilation": edge_dilation,
            "reference_resize_filter": "LANCZOS",
        },
        "method_notes": [
            "Candidate-side source evidence is limited to candidate.svg plus rendered.png.",
            "Candidate SVG geometry is normalized from its viewBox into the GT PageSpec canvas before element matching.",
            "Text Box Recall ignores text content and element ids, aggregates split native SVG text lines inside each GT region, and requires the configured aggregate bbox IoU.",
            "Text bboxes use SVG textLength when present and otherwise estimate width from text x/y/font-size/content.",
            "Image bboxes are read from SVG <image> x/y/width/height.",
            "SVG element ids are used only as matching hints together with bbox/text evidence, not as a standalone Semantic Tag Coverage metric.",
            "Image Recall counts independent image/raster object matches plus visual reconstruction fallback when same-bbox reference/rendered Region MSE is below the configured threshold.",
            "Image Region MSE resizes reference.png to the GT canvas with LANCZOS, crops each kind=image bbox from reference/rendered, normalizes RGB to 0-1, and averages crop MSE.",
            "Formula Editable Representation matches kind=formula GT boxes to independent native SVG text or vector primitives; raster image objects never count.",
        ],
        "counts": counts,
        "metrics": metrics,
        "global_metrics": global_metrics,
        "element_metrics": {
            "text": {
                "box_recall": metrics["text_box_recall"],
                "precision": text_precision,
                "recall": text_recall,
                "f1": text_f1,
                "unmatched_gt_text_ids": [
                    element.id for element in gt_text if element.id not in gt_text_matched_ids
                ],
                "unmatched_gt_text_box_ids": [
                    element.id for element in gt_text if element.id not in gt_text_box_matched_ids
                ],
                "low_text_similarity_matches": [
                    match for match in text_content_matches if match["text_similarity"] < 0.95
                ],
            },
            "image": {
                "object_recall": metrics["image_object_recall"],
                "recall": metrics["image_recall"],
                "miou": metrics["image_miou"],
                "region_mse": metrics["image_region_mse"],
                "region_mse_median": metrics["image_region_mse_median"],
                "region_mse_pass_rate": metrics["image_region_mse_pass_rate"],
                "mse_threshold": image_mse_threshold,
                "object_only_unmatched_gt_image_ids": gt_image_unmatched_object_ids,
                "mse_fallback_gt_images": image_fallback,
                "unmatched_gt_image_ids": [
                    element.id for element in gt_images if element.id not in gt_image_recalled_ids
                ],
                "region_mse_failed_gt_images": image_failed,
            },
            "formula": {
                "editable_representation": metrics["formula_editable_representation"],
                "unmatched_gt_formula_ids": [
                    element.id
                    for element in gt_formulas
                    if element.id not in {match["gt_id"] for match in formula_editable_matches}
                ],
            },
        },
        "matches": {
            "text_content": text_content_matches,
            "text_boxes": text_box_matches,
            "image_objects": image_object_matches,
            "image_region_mse": image_region_mses,
            "formula_editable": formula_editable_matches,
        },
    }


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def canvas_size(gt_spec: dict[str, Any]) -> tuple[int, int]:
    canvas = gt_spec.get("canvas") or {}
    width = canvas.get("width_px") or canvas.get("width") or gt_spec.get("width_px")
    height = canvas.get("height_px") or canvas.get("height") or gt_spec.get("height_px")
    if width is None or height is None:
        raise KeyError("GT spec does not contain canvas width_px/height_px")
    return int(round(float(width))), int(round(float(height)))


def infer_case_id(gt_spec: dict[str, Any], candidate_svg: Path) -> str | None:
    page_id = gt_spec.get("page_id")
    if isinstance(page_id, str) and page_id:
        return page_id.split("/")[-1]
    for parent in candidate_svg.parents:
        if parent.name.startswith("case_"):
            return parent.name
    return None


def render_svg(candidate_svg: Path, rendered_png: Path, width: int, height: int) -> None:
    from drawai_evaluation.batch import render_candidate_svg

    render_candidate_svg(candidate_svg, rendered_png)


def load_rgb_canvas(path: Path, width: int, height: int) -> Image.Image:
    image = Image.open(path).convert("RGBA")
    background = Image.new("RGBA", image.size, (255, 255, 255, 255))
    image = Image.alpha_composite(background, image).convert("RGB")
    if image.size != (width, height):
        image = image.resize((width, height), Image.Resampling.LANCZOS)
    return image


def compute_global_metrics(
    reference_arr: np.ndarray,
    rendered_arr: np.ndarray,
    *,
    edge_canny_low: int,
    edge_canny_high: int,
    edge_blur_kernel: int,
    edge_dilation: int,
) -> dict[str, float]:
    mse = float(np.mean((reference_arr - rendered_arr) ** 2))
    ssim = float(
        structural_similarity(reference_arr, rendered_arr, channel_axis=-1, data_range=1.0)
    )
    ref_gray = np.clip(reference_arr.mean(axis=2) * 255.0, 0, 255).astype(np.uint8)
    ren_gray = np.clip(rendered_arr.mean(axis=2) * 255.0, 0, 255).astype(np.uint8)
    if edge_blur_kernel > 0:
        if edge_blur_kernel % 2 == 0:
            raise ValueError("--edge-blur-kernel must be odd, or 0 to disable blur")
        ref_gray = cv2.GaussianBlur(ref_gray, (edge_blur_kernel, edge_blur_kernel), 0)
        ren_gray = cv2.GaussianBlur(ren_gray, (edge_blur_kernel, edge_blur_kernel), 0)
    ref_edges = cv2.Canny(ref_gray, edge_canny_low, edge_canny_high) > 0
    ren_edges = cv2.Canny(ren_gray, edge_canny_low, edge_canny_high) > 0
    kernel = np.ones((3, 3), dtype=np.uint8)
    ref_dilated = cv2.dilate(ref_edges.astype(np.uint8), kernel, iterations=edge_dilation) > 0
    ren_dilated = cv2.dilate(ren_edges.astype(np.uint8), kernel, iterations=edge_dilation) > 0
    edge_precision = safe_div(np.logical_and(ren_edges, ref_dilated).sum(), ren_edges.sum())
    edge_recall = safe_div(np.logical_and(ref_edges, ren_dilated).sum(), ref_edges.sum())
    edge_f1 = safe_div(2 * edge_precision * edge_recall, edge_precision + edge_recall)
    return {
        "ssim": ssim,
        "mse": mse,
        "edge_precision": edge_precision,
        "edge_recall": edge_recall,
        "edge_f1": edge_f1,
    }


def parse_gt_elements(gt_spec: dict[str, Any]) -> list[SpecElement]:
    elements = []
    for raw in gt_spec.get("elements", []):
        box = raw.get("box_px")
        kind = raw.get("kind")
        element_id = raw.get("id")
        if not box or not kind or not element_id:
            continue
        elements.append(
            SpecElement(
                id=str(element_id),
                kind=str(kind),
                box=Box(float(box[0]), float(box[1]), float(box[2]), float(box[3])),
                text=raw.get("text"),
                role=raw.get("role"),
            )
        )
    return elements


def parse_svg_elements(svg_path: Path, canvas_width: int, canvas_height: int) -> list[SvgElement]:
    root = ET.parse(svg_path).getroot()
    elements: list[SvgElement] = []
    walk_svg(root, svg_canvas_matrix(root, canvas_width, canvas_height), {}, elements)
    return elements


def svg_canvas_matrix(root: ET.Element, canvas_width: int, canvas_height: int) -> np.ndarray:
    view_box = [
        float(value)
        for value in re.findall(
            r"-?\d+(?:\.\d+)?(?:e[+-]?\d+)?",
            root.attrib.get("viewBox", ""),
            re.I,
        )
    ]
    if len(view_box) == 4 and view_box[2] > 0 and view_box[3] > 0:
        min_x, min_y, source_width, source_height = view_box
    else:
        min_x = min_y = 0.0
        source_width = parse_float(root.attrib.get("width"), float(canvas_width))
        source_height = parse_float(root.attrib.get("height"), float(canvas_height))
    if source_width <= 0 or source_height <= 0:
        raise ValueError("candidate SVG must declare a positive viewBox or width/height")
    scale_x = canvas_width / source_width
    scale_y = canvas_height / source_height
    return np.array(
        [
            [scale_x, 0.0, -min_x * scale_x],
            [0.0, scale_y, -min_y * scale_y],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )


def walk_svg(
    node: ET.Element, parent_matrix: np.ndarray, parent_style: dict[str, str], out: list[SvgElement]
) -> None:
    style = {**parent_style, **parse_style(node.attrib.get("style", ""))}
    for attr in ("display", "visibility", "opacity", "fill-opacity"):
        if attr in node.attrib:
            style[attr] = node.attrib[attr]
    matrix = parent_matrix @ parse_transform(node.attrib.get("transform", ""))
    tag = local_name(node.tag)
    if is_hidden(node, style):
        return
    if tag == "image":
        box = box_from_xywh(node.attrib, matrix)
        if box and box.area > 0:
            out.append(
                SvgElement(
                    tag="image",
                    id=node.attrib.get("id"),
                    element_id=drawai_element_id(node),
                    box=box,
                    href=node.attrib.get("href")
                    or node.attrib.get("{http://www.w3.org/1999/xlink}href"),
                )
            )
    elif tag == "text":
        text = normalize_visible_text("".join(node.itertext()))
        if text:
            box = text_box(node, text, matrix, style)
            if box.area > 0:
                out.append(
                    SvgElement(
                        tag="text",
                        id=node.attrib.get("id"),
                        element_id=drawai_element_id(node),
                        box=box,
                        text=text,
                    )
                )
    elif tag in {"rect", "line", "polyline", "polygon", "circle", "ellipse", "path"}:
        box = primitive_box(tag, node.attrib, matrix)
        if box and box.area > 0:
            out.append(
                SvgElement(
                    tag=tag,
                    id=node.attrib.get("id"),
                    element_id=drawai_element_id(node),
                    box=box,
                )
            )
    for child in list(node):
        walk_svg(child, matrix, style, out)


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def drawai_element_id(node: ET.Element) -> str | None:
    return node.attrib.get("data-drawai-element-id") or node.attrib.get("data-pb-element-id")


def parse_style(style_text: str) -> dict[str, str]:
    result = {}
    for part in style_text.split(";"):
        if ":" not in part:
            continue
        key, value = part.split(":", 1)
        result[key.strip()] = value.strip()
    return result


def is_hidden(node: ET.Element, style: dict[str, str]) -> bool:
    display = node.attrib.get("display") or style.get("display")
    visibility = node.attrib.get("visibility") or style.get("visibility")
    opacity = node.attrib.get("opacity") or style.get("opacity")
    if display == "none" or visibility == "hidden":
        return True
    return opacity is not None and parse_float(opacity, 1.0) <= 0.0


def identity_matrix() -> np.ndarray:
    return np.eye(3, dtype=np.float64)


def parse_transform(value: str) -> np.ndarray:
    matrix = identity_matrix()
    for name, args_text in re.findall(r"([a-zA-Z]+)\(([^)]*)\)", value or ""):
        args = [float(part) for part in re.split(r"[\s,]+", args_text.strip()) if part]
        op = identity_matrix()
        if name == "matrix" and len(args) == 6:
            a, b, c, d, e, f = args
            op = np.array([[a, c, e], [b, d, f], [0, 0, 1]], dtype=np.float64)
        elif name == "translate" and args:
            tx, ty = args[0], args[1] if len(args) > 1 else 0.0
            op = np.array([[1, 0, tx], [0, 1, ty], [0, 0, 1]], dtype=np.float64)
        elif name == "scale" and args:
            sx, sy = args[0], args[1] if len(args) > 1 else args[0]
            op = np.array([[sx, 0, 0], [0, sy, 0], [0, 0, 1]], dtype=np.float64)
        elif name == "rotate" and args:
            angle = math.radians(args[0])
            cos_v, sin_v = math.cos(angle), math.sin(angle)
            rot = np.array([[cos_v, -sin_v, 0], [sin_v, cos_v, 0], [0, 0, 1]], dtype=np.float64)
            if len(args) >= 3:
                cx, cy = args[1], args[2]
                to_origin = np.array([[1, 0, -cx], [0, 1, -cy], [0, 0, 1]], dtype=np.float64)
                back = np.array([[1, 0, cx], [0, 1, cy], [0, 0, 1]], dtype=np.float64)
                op = back @ rot @ to_origin
            else:
                op = rot
        matrix = matrix @ op
    return matrix


def box_from_xywh(attrs: dict[str, str], matrix: np.ndarray) -> Box | None:
    x = parse_float(attrs.get("x"), 0.0)
    y = parse_float(attrs.get("y"), 0.0)
    width = parse_float(attrs.get("width"), 0.0)
    height = parse_float(attrs.get("height"), 0.0)
    if width <= 0 or height <= 0:
        return None
    return transformed_box(Box(x, y, width, height), matrix)


def primitive_box(tag: str, attrs: dict[str, str], matrix: np.ndarray) -> Box | None:
    if tag == "rect":
        return box_from_xywh(attrs, matrix)
    if tag == "line":
        x1 = parse_float(attrs.get("x1"), 0.0)
        y1 = parse_float(attrs.get("y1"), 0.0)
        x2 = parse_float(attrs.get("x2"), 0.0)
        y2 = parse_float(attrs.get("y2"), 0.0)
        return transformed_box(
            Box(min(x1, x2), min(y1, y2), max(1.0, abs(x2 - x1)), max(1.0, abs(y2 - y1))),
            matrix,
        )
    if tag in {"circle", "ellipse"}:
        cx = parse_float(attrs.get("cx"), 0.0)
        cy = parse_float(attrs.get("cy"), 0.0)
        rx = parse_float(attrs.get("r") or attrs.get("rx"), 0.0)
        ry = parse_float(attrs.get("r") or attrs.get("ry"), 0.0)
        if rx <= 0 or ry <= 0:
            return None
        return transformed_box(Box(cx - rx, cy - ry, rx * 2, ry * 2), matrix)
    source = attrs.get("points") if tag in {"polyline", "polygon"} else attrs.get("d")
    numbers = [
        float(value) for value in re.findall(r"-?\d+(?:\.\d+)?(?:e[+-]?\d+)?", source or "", re.I)
    ]
    if len(numbers) < 4:
        return None
    xs = numbers[0::2]
    ys = numbers[1::2]
    if not xs or not ys:
        return None
    return transformed_box(
        Box(min(xs), min(ys), max(1.0, max(xs) - min(xs)), max(1.0, max(ys) - min(ys))),
        matrix,
    )


def text_box(node: ET.Element, text: str, matrix: np.ndarray, style: dict[str, str]) -> Box:
    font_size = svg_font_size(node, style)
    x = parse_float(first_attr(node, "x"), 0.0)
    y = parse_float(first_attr(node, "y"), 0.0)
    declared_width = parse_float(node.attrib.get("textLength"), 0.0)
    width = declared_width if declared_width > 0 else estimate_text_width(text, font_size)
    height = max(1.0, font_size * 1.2)
    anchor = node.attrib.get("text-anchor") or style.get("text-anchor")
    if anchor == "middle":
        x -= width / 2.0
    elif anchor == "end":
        x -= width
    return transformed_box(Box(x, y - font_size, width, height), matrix)


def first_attr(node: ET.Element, attr: str) -> str | None:
    if attr in node.attrib:
        return node.attrib[attr]
    for child in node.iter():
        if child is not node and attr in child.attrib:
            return child.attrib[attr]
    return None


def svg_font_size(node: ET.Element, style: dict[str, str]) -> float:
    return parse_float(node.attrib.get("font-size") or style.get("font-size"), 16.0)


def estimate_text_width(text: str, font_size: float) -> float:
    weight = 0.0
    for char in text:
        if char.isspace():
            weight += 0.33
        elif ord(char) > 127:
            weight += 1.0
        elif char in ".,:;|!ilI'`":
            weight += 0.28
        elif char in "-_()[]{}":
            weight += 0.42
        elif char.isupper():
            weight += 0.68
        else:
            weight += 0.56
    return max(font_size * 0.35, weight * font_size)


def transformed_box(box: Box, matrix: np.ndarray) -> Box:
    points = np.array(
        [
            [box.x, box.y, 1.0],
            [box.x + box.w, box.y, 1.0],
            [box.x + box.w, box.y + box.h, 1.0],
            [box.x, box.y + box.h, 1.0],
        ],
        dtype=np.float64,
    )
    transformed = (matrix @ points.T).T
    xs = transformed[:, 0]
    ys = transformed[:, 1]
    return Box(
        float(xs.min()), float(ys.min()), float(xs.max() - xs.min()), float(ys.max() - ys.min())
    )


def parse_float(value: str | None, default: float) -> float:
    if value is None:
        return default
    match = re.search(r"-?\d+(?:\.\d+)?", str(value))
    return float(match.group(0)) if match else default


def normalize_visible_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def normalize_match_text(value: str | None) -> str:
    text = unicodedata.normalize("NFKC", value or "")
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def match_text_content(
    gt_text: list[SpecElement], svg_text: list[SvgElement], threshold: float
) -> list[dict[str, Any]]:
    pairs = []
    for gt in gt_text:
        gt_norm = normalize_match_text(gt.text)
        if not gt_norm:
            continue
        for candidate in svg_text:
            cand_norm = normalize_match_text(candidate.text)
            if not cand_norm:
                continue
            text_similarity = SequenceMatcher(None, gt_norm, cand_norm).ratio()
            if text_similarity < threshold:
                continue
            spatial = spatial_score(gt.box, candidate.box)
            id_bonus = 0.15 if candidate.element_id == gt.id else 0.0
            pairs.append(
                (
                    (text_similarity * 2.0) + spatial + id_bonus,
                    {
                        "gt_id": gt.id,
                        "candidate_id": candidate.id,
                        "candidate_element_id": candidate.element_id,
                        "gt_text": gt.text,
                        "candidate_text": candidate.text,
                        "text_similarity": text_similarity,
                        "spatial_score": spatial,
                        "iou": iou(gt.box, candidate.box),
                    },
                )
            )
    return greedy_pairs(pairs)


def match_text_boxes(
    gt_text: list[SpecElement],
    svg_text: list[SvgElement],
    iou_threshold: float,
) -> list[dict[str, Any]]:
    if not 0 <= iou_threshold <= 1:
        raise ValueError("--text-box-iou-threshold must be between 0 and 1")
    pairs: list[tuple[float, tuple[int, ...], dict[str, Any]]] = []
    indexed_candidates = list(enumerate(svg_text))
    for gt in gt_text:
        nearby = [
            (index, candidate)
            for index, candidate in indexed_candidates
            if intersection_area(gt.box, candidate.box) > 0
            or box_contains(expand_box(gt.box, 0.08), candidate.box.center)
        ]
        for index, candidate in nearby:
            pair_iou = iou(gt.box, candidate.box)
            if pair_iou < iou_threshold:
                continue
            pairs.append(
                (
                    pair_iou,
                    (index,),
                    text_box_match_payload(gt, [candidate], candidate.box, pair_iou),
                )
            )
        if len(nearby) < 2:
            continue
        aggregate_box = enclosing_box([candidate.box for _, candidate in nearby])
        aggregate_iou = iou(gt.box, aggregate_box)
        if aggregate_iou < iou_threshold:
            continue
        pairs.append(
            (
                aggregate_iou,
                tuple(index for index, _ in nearby),
                text_box_match_payload(
                    gt,
                    [candidate for _, candidate in nearby],
                    aggregate_box,
                    aggregate_iou,
                ),
            )
        )
    return greedy_text_box_groups(pairs)


def text_box_match_payload(
    gt: SpecElement,
    candidates: list[SvgElement],
    aggregate_box: Box,
    pair_iou: float,
) -> dict[str, Any]:
    return {
        "gt_id": gt.id,
        "candidate_ids": [candidate.id for candidate in candidates],
        "candidate_element_ids": [candidate.element_id for candidate in candidates],
        "candidate_box": aggregate_box.as_list(),
        "iou": pair_iou,
    }


def greedy_text_box_groups(
    pairs: list[tuple[float, tuple[int, ...], dict[str, Any]]],
) -> list[dict[str, Any]]:
    matched_gt: set[str] = set()
    matched_candidates: set[int] = set()
    matches: list[dict[str, Any]] = []
    for _, candidate_indexes, payload in sorted(pairs, key=lambda item: item[0], reverse=True):
        if payload["gt_id"] in matched_gt or any(
            index in matched_candidates for index in candidate_indexes
        ):
            continue
        matched_gt.add(payload["gt_id"])
        matched_candidates.update(candidate_indexes)
        matches.append(payload)
    return matches


def match_images(
    gt_images: list[SpecElement], svg_images: list[SvgElement], iou_threshold: float
) -> list[dict[str, Any]]:
    pairs = []
    for gt in gt_images:
        for candidate in svg_images:
            pair_iou = iou(gt.box, candidate.box)
            same_id = candidate.element_id == gt.id
            center = center_score(gt.box, candidate.box)
            if not same_id and pair_iou < iou_threshold:
                continue
            if same_id and pair_iou < 0.05 and center < 0.5:
                continue
            pairs.append(
                (
                    pair_iou + (1.0 if same_id else 0.0),
                    {
                        "gt_id": gt.id,
                        "gt_role": gt.role,
                        "candidate_id": candidate.id,
                        "candidate_element_id": candidate.element_id,
                        "href": candidate.href,
                        "iou": pair_iou,
                    },
                )
            )
    return greedy_pairs(pairs)


def greedy_pairs(pairs: list[tuple[float, dict[str, Any]]]) -> list[dict[str, Any]]:
    matched_gt = set()
    matched_candidates = set()
    matches = []
    for _, payload in sorted(pairs, key=lambda item: item[0], reverse=True):
        gt_id = payload["gt_id"]
        candidate_key = payload.get("candidate_id") or f"anon:{id(payload)}"
        if gt_id in matched_gt or candidate_key in matched_candidates:
            continue
        matched_gt.add(gt_id)
        matched_candidates.add(candidate_key)
        matches.append(payload)
    return matches


def match_formula_editability(
    gt_formulas: list[SpecElement], svg_editable: list[SvgElement]
) -> list[dict[str, Any]]:
    pairs: list[tuple[float, dict[str, Any]]] = []
    for gt in gt_formulas:
        for candidate in svg_editable:
            intersection = intersection_area(gt.box, candidate.box)
            same_id = candidate.element_id == gt.id
            gt_coverage = safe_div(intersection, gt.box.area)
            candidate_coverage = safe_div(intersection, candidate.box.area)
            if not same_id and (gt_coverage < 0.05 or candidate_coverage < 0.2):
                continue
            score = max(gt_coverage, candidate_coverage) + (1.0 if same_id else 0.0)
            pairs.append(
                (
                    score,
                    {
                        "gt_id": gt.id,
                        "candidate_id": candidate.id,
                        "candidate_element_id": candidate.element_id,
                        "candidate_tag": candidate.tag,
                        "gt_box": gt.box.as_list(),
                        "candidate_box": candidate.box.as_list(),
                        "gt_coverage": gt_coverage,
                        "candidate_coverage": candidate_coverage,
                    },
                )
            )
    matches = []
    matched_gt = set()
    matched_candidates = set()
    for _, payload in sorted(pairs, key=lambda item: item[0], reverse=True):
        gt_id = payload["gt_id"]
        candidate_key = payload.get("candidate_id") or (
            f"{payload['candidate_tag']}:{payload['candidate_box']}"
        )
        if gt_id in matched_gt or candidate_key in matched_candidates:
            continue
        matched_gt.add(gt_id)
        matched_candidates.add(candidate_key)
        matches.append(payload)
    return matches


def intersection_area(a: Box, b: Box) -> float:
    x0 = max(a.x, b.x)
    y0 = max(a.y, b.y)
    x1 = min(a.x + a.w, b.x + b.w)
    y1 = min(a.y + a.h, b.y + b.h)
    return max(0.0, x1 - x0) * max(0.0, y1 - y0)


def expand_box(box: Box, ratio: float) -> Box:
    pad_x = max(2.0, box.w * ratio)
    pad_y = max(2.0, box.h * ratio)
    return Box(box.x - pad_x, box.y - pad_y, box.w + (2 * pad_x), box.h + (2 * pad_y))


def box_contains(box: Box, point: tuple[float, float]) -> bool:
    x, y = point
    return box.x <= x <= box.x + box.w and box.y <= y <= box.y + box.h


def enclosing_box(boxes: list[Box]) -> Box:
    if not boxes:
        raise ValueError("cannot enclose an empty box list")
    x0 = min(box.x for box in boxes)
    y0 = min(box.y for box in boxes)
    x1 = max(box.x + box.w for box in boxes)
    y1 = max(box.y + box.h for box in boxes)
    return Box(x0, y0, x1 - x0, y1 - y0)


def iou(a: Box, b: Box) -> float:
    inter = intersection_area(a, b)
    union = a.area + b.area - inter
    return safe_div(inter, union)


def spatial_score(a: Box, b: Box) -> float:
    return max(iou(a, b), center_score(a, b))


def center_score(a: Box, b: Box) -> float:
    ax, ay = a.center
    bx, by = b.center
    distance = math.hypot(ax - bx, ay - by)
    scale = max(1.0, a.diagonal * 2.5)
    return max(0.0, 1.0 - distance / scale)


def compute_image_region_mses(
    gt_images: list[SpecElement], reference_arr: np.ndarray, rendered_arr: np.ndarray
) -> list[dict[str, Any]]:
    height, width = reference_arr.shape[:2]
    rows = []
    for element in gt_images:
        x0, y0, x1, y1 = element.box.clamp(width, height)
        if x1 <= x0 or y1 <= y0:
            mse = None
        else:
            ref_crop = reference_arr[y0:y1, x0:x1, :]
            ren_crop = rendered_arr[y0:y1, x0:x1, :]
            mse = float(np.mean((ref_crop - ren_crop) ** 2))
        rows.append(
            {
                "gt_id": element.id,
                "role": element.role,
                "box_px": element.box.as_list(),
                "mse": mse,
            }
        )
    return rows


def safe_div(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else 0.0


if __name__ == "__main__":
    raise SystemExit(main())
