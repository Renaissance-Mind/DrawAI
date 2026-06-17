from drawai.domain.box_ir import build_raw_box_ir, validate_box_ir
from drawai.domain.box_ir import merge_box_ir


def test_build_raw_box_ir_uses_figure_image_coordinate_system():
    raw = build_raw_box_ir(
        canvas=(100, 80),
        source_image="inputs/figure.png",
        normalized_long_edge=3840,
        prompt_runs=[],
        raw_regions=[],
    )

    assert raw["source"]["coordinate_system"] == "figure_image_pixels"


def test_validate_box_ir_rejects_non_figure_image_coordinate_system():
    raw = build_raw_box_ir(
        canvas=(100, 80),
        source_image="inputs/figure.png",
        normalized_long_edge=3840,
        prompt_runs=[],
        raw_regions=[],
    )
    raw["source"]["coordinate_system"] = "image_pixels"

    issues = validate_box_ir(raw)

    assert any("source.coordinate_system" in issue and "figure_image_pixels" in issue for issue in issues)


def test_merge_dedupes_same_type_high_iou_and_keeps_children():
    raw = build_raw_box_ir(
        canvas=(300, 200),
        source_image="inputs/figure.png",
        normalized_long_edge=3840,
        prompt_runs=[],
        raw_regions=[
            {"type": "icon", "source_prompt": "icon", "bbox": [10, 10, 60, 60], "score": 0.9},
            {"type": "icon", "source_prompt": "icon", "bbox": [12, 12, 61, 61], "score": 0.8},
            {"type": "content_box", "source_prompt": "content_box", "bbox": [0, 0, 100, 100], "score": 0.7},
        ],
    )
    merged, trace = merge_box_ir(
        raw,
        duplicate_iou_threshold=0.85,
        duplicate_smaller_overlap_threshold=0.92,
    )
    assert validate_box_ir(merged) == []
    icons = [box for box in merged["boxes"] if box["type"] == "icon"]
    content = [box for box in merged["boxes"] if box["type"] == "content_box"][0]
    assert len(icons) == 1
    assert icons[0]["parent_ids"] == [content["id"]]
    assert any(decision["action"] == "merge" for decision in trace["decisions"])


def test_different_types_are_not_merged_when_overlap_is_containment_not_duplicate():
    raw = build_raw_box_ir(
        canvas=(100, 100),
        source_image="inputs/figure.png",
        normalized_long_edge=3840,
        prompt_runs=[],
        raw_regions=[
            {"type": "border", "source_prompt": "border", "bbox": [0, 0, 90, 90], "score": 0.9},
            {"type": "content_box", "source_prompt": "content_box", "bbox": [12, 12, 78, 78], "score": 0.8},
        ],
    )
    merged, _ = merge_box_ir(raw)
    border, content_box = merged["boxes"]

    assert [box["type"] for box in merged["boxes"]] == ["border", "content_box"]
    assert content_box["parent_ids"] == [border["id"]]
    assert border["child_ids"] == [content_box["id"]]


def test_cross_type_icon_content_box_duplicate_prefers_content_box_without_type_candidates():
    raw = build_raw_box_ir(
        canvas=(120, 120),
        source_image="inputs/figure.png",
        normalized_long_edge=3840,
        prompt_runs=[],
        raw_regions=[
            {"source_prompt": "content_box", "bbox": [10, 10, 70, 70], "score": 0.92},
            {"source_prompt": "icon", "bbox": [11, 11, 70, 70], "score": 0.80},
        ],
    )

    merged, trace = merge_box_ir(raw)

    assert validate_box_ir(merged) == []
    assert len(merged["boxes"]) == 1
    box = merged["boxes"][0]
    assert box["type"] == "content_box"
    assert "type_candidates" not in box
    assert box["source_box_ids"] == ["B001", "B002"]
    assert any(decision["reason"] == "cross_type_geometric_duplicate" for decision in trace["decisions"])


def test_content_box_duplicate_preserves_nested_visual_asset_child():
    raw = build_raw_box_ir(
        canvas=(200, 180),
        source_image="inputs/figure.png",
        normalized_long_edge=3840,
        prompt_runs=[],
        raw_regions=[
            {"source_prompt": "content_box", "bbox": [10, 10, 150, 150], "score": 0.92},
            {"source_prompt": "icon", "bbox": [10, 10, 150, 150], "score": 0.80},
            {"source_prompt": "icon", "bbox": [42, 38, 124, 132], "score": 0.86},
        ],
    )

    merged, trace = merge_box_ir(raw)
    content_boxes = [box for box in merged["boxes"] if box["type"] == "content_box"]
    icons = [box for box in merged["boxes"] if box["type"] == "icon"]

    assert validate_box_ir(merged) == []
    assert len(content_boxes) == 1
    assert len(icons) == 1
    assert icons[0]["bbox"] == [42.0, 38.0, 124.0, 132.0]
    assert icons[0]["parent_ids"] == [content_boxes[0]["id"]]
    assert content_boxes[0]["child_ids"] == [icons[0]["id"]]
    assert any(decision["reason"] == "preserve_visual_asset_child" for decision in trace["decisions"])


def test_cross_type_duplicate_cluster_prefers_container_when_it_contains_children():
    raw = build_raw_box_ir(
        canvas=(160, 160),
        source_image="inputs/figure.png",
        normalized_long_edge=3840,
        prompt_runs=[],
        raw_regions=[
            {"source_prompt": "icon", "bbox": [10, 10, 130, 130], "score": 0.95},
            {"source_prompt": "content_box", "bbox": [10, 10, 130, 130], "score": 0.70},
            {"source_prompt": "symbol", "bbox": [40, 40, 70, 70], "score": 0.90},
        ],
    )

    merged, _ = merge_box_ir(raw)
    boxes = {box["type"]: box for box in merged["boxes"]}

    assert validate_box_ir(merged) == []
    assert sorted(boxes) == ["content_box", "symbol"]
    assert boxes["symbol"]["parent_ids"] == [boxes["content_box"]["id"]]
    assert boxes["content_box"]["child_ids"] == [boxes["symbol"]["id"]]


def test_invalid_and_zero_area_boxes_are_excluded_from_raw_box_ir():
    raw = build_raw_box_ir(
        canvas=(100, 80),
        source_image="inputs/figure.png",
        normalized_long_edge=3840,
        prompt_runs=[],
        raw_regions=[
            {"source_prompt": "text", "bbox": [10, 10, 40, 30], "score": 0.8},
            {"source_prompt": "icon", "bbox": [20, 20, 20, 40], "score": 0.7},
            {"source_prompt": "picture", "bbox": [90, 70, 200, 70], "score": 0.6},
            {"source_prompt": "symbol", "bbox": ["bad", 1, 3, 4], "score": 0.5},
        ],
    )

    assert validate_box_ir(raw) == []
    assert [(box["id"], box["type"], box["bbox"]) for box in raw["boxes"]] == [
        ("B001", "text", [10.0, 10.0, 40.0, 30.0])
    ]


def test_build_raw_box_ir_preserves_mask_and_polygon_geometry():
    raw = build_raw_box_ir(
        canvas=(120, 100),
        source_image="inputs/figure.png",
        normalized_long_edge=3840,
        prompt_runs=[],
        raw_regions=[
            {
                "source_prompt": "picture",
                "geometry": {
                    "kind": "polygon",
                    "points": [[10, 12], [42, 14], [38, 40], [12, 36]],
                },
                "score": 0.9,
            },
            {
                "source_prompt": "icon",
                "bbox": [70, 20, 96, 54],
                "mask_path": "sam3/masks/icon.png",
                "score": 0.8,
            },
        ],
    )

    assert validate_box_ir(raw) == []
    picture, icon = raw["boxes"]
    assert picture["bbox"] == [10.0, 12.0, 42.0, 40.0]
    assert picture["geometry"]["kind"] == "polygon"
    assert picture["geometry"]["points"] == [[10.0, 12.0], [42.0, 14.0], [38.0, 40.0], [12.0, 36.0]]
    assert icon["geometry"] == {
        "kind": "mask",
        "mask_path": "sam3/masks/icon.png",
        "bbox": [70.0, 20.0, 96.0, 54.0],
        "coordinate_system": "figure_image_pixels",
    }


def test_box_ids_are_assigned_in_top_left_reading_order():
    raw = build_raw_box_ir(
        canvas=(200, 200),
        source_image="inputs/figure.png",
        normalized_long_edge=3840,
        prompt_runs=[],
        raw_regions=[
            {"label": "symbol", "bbox": [60, 80, 90, 100]},
            {"label": "arrow", "bbox": [100, 10, 130, 40]},
            {"label": "text", "bbox": [10, 10, 40, 30]},
            {"label": "icon", "x1": 20, "y1": 50, "x2": 70, "y2": 90},
        ],
    )

    assert [(box["id"], box["type"], box["bbox"]) for box in raw["boxes"]] == [
        ("B001", "text", [10.0, 10.0, 40.0, 30.0]),
        ("B002", "arrow", [100.0, 10.0, 130.0, 40.0]),
        ("B003", "icon", [20.0, 50.0, 70.0, 90.0]),
        ("B004", "symbol", [60.0, 80.0, 90.0, 100.0]),
    ]


def test_containment_parent_child_relation_after_merge():
    raw = build_raw_box_ir(
        canvas=(240, 160),
        source_image="inputs/figure.png",
        normalized_long_edge=3840,
        prompt_runs=[],
        raw_regions=[
            {"type": "content_box", "bbox": [0, 0, 220, 140], "score": 0.9},
            {"type": "text", "box": [20, 20, 100, 50], "score": 0.8},
            {"type": "picture", "coordinates": [120, 40, 210, 120], "score": 0.8},
        ],
    )

    merged, _ = merge_box_ir(raw)
    content = [box for box in merged["boxes"] if box["type"] == "content_box"][0]
    children = [box for box in merged["boxes"] if box["type"] in {"text", "picture"}]

    assert validate_box_ir(merged) == []
    assert sorted(content["child_ids"]) == sorted(box["id"] for box in children)
    assert all(box["parent_ids"] == [content["id"]] for box in children)


def test_nested_content_box_merges_to_outer_box():
    raw = build_raw_box_ir(
        canvas=(300, 220),
        source_image="inputs/figure.png",
        normalized_long_edge=3840,
        prompt_runs=[],
        raw_regions=[
            {"source_prompt": "content_box", "bbox": [0, 0, 240, 180], "score": 0.9},
            {"source_prompt": "content_box", "bbox": [30, 30, 90, 80], "score": 0.8},
        ],
    )

    merged, trace = merge_box_ir(raw)
    content_boxes = [box for box in merged["boxes"] if box["type"] == "content_box"]

    assert validate_box_ir(merged) == []
    assert len(content_boxes) == 1
    assert content_boxes[0]["bbox"] == [0.0, 0.0, 240.0, 180.0]
    assert content_boxes[0]["source_box_ids"] == ["B001", "B002"]
    assert any(decision["reason"] == "same_type_nested_content_box" for decision in trace["decisions"])


def test_nested_icon_merges_to_outer_icon_when_small_box_is_fully_overlapped():
    raw = build_raw_box_ir(
        canvas=(300, 220),
        source_image="inputs/figure.png",
        normalized_long_edge=3840,
        prompt_runs=[],
        raw_regions=[
            {"source_prompt": "icon", "bbox": [0, 0, 240, 180], "score": 0.8},
            {"source_prompt": "icon", "bbox": [40, 40, 90, 80], "score": 0.95},
        ],
    )

    merged, trace = merge_box_ir(raw)
    icons = [box for box in merged["boxes"] if box["type"] == "icon"]

    assert validate_box_ir(merged) == []
    assert len(icons) == 1
    assert icons[0]["bbox"] == [0.0, 0.0, 240.0, 180.0]
    assert icons[0]["source_box_ids"] == ["B001", "B002"]
    assert any(decision["reason"] == "same_type_nested_icon" for decision in trace["decisions"])


def test_same_type_nested_duplicate_merges_by_smaller_overlap():
    raw = build_raw_box_ir(
        canvas=(120, 120),
        source_image="inputs/figure.png",
        normalized_long_edge=3840,
        prompt_runs=[],
        raw_regions=[
            {"source_prompt": "text", "bbox": [10, 10, 80, 80], "score": 0.7},
            {"source_prompt": "text", "bbox": [12, 12, 78, 78], "score": 0.9},
        ],
    )

    merged, trace = merge_box_ir(raw, duplicate_iou_threshold=0.95, duplicate_smaller_overlap_threshold=0.92)

    assert [box["bbox"] for box in merged["boxes"]] == [[10.0, 10.0, 80.0, 80.0]]
    assert any(decision["reason"] == "same_type_smaller_overlap" for decision in trace["decisions"])


def test_source_prompt_aliases_merge_to_singular_canonical_prompt():
    raw = build_raw_box_ir(
        canvas=(120, 120),
        source_image="inputs/figure.png",
        normalized_long_edge=3840,
        prompt_runs=[],
        raw_regions=[
            {"source_prompt": "icon", "bbox": [10, 10, 60, 60], "score": 0.7},
            {"source_prompt": "icons", "bbox": [12, 12, 61, 61], "score": 0.9},
        ],
    )

    assert [box["source_prompt"] for box in raw["boxes"]] == ["icon", "icon"]

    merged, _ = merge_box_ir(raw)

    assert len(merged["boxes"]) == 1
    assert merged["boxes"][0]["type"] == "icon"
    assert merged["boxes"][0]["source_prompt"] == "icon"
    assert merged["boxes"][0]["source_prompts"] == ["icon"]


def test_non_string_source_prompt_metadata_does_not_crash_merge():
    raw = build_raw_box_ir(
        canvas=(120, 120),
        source_image="inputs/figure.png",
        normalized_long_edge=3840,
        prompt_runs=[],
        raw_regions=[
            {"type": "icon", "bbox": [10, 10, 60, 60]},
            {"type": "icon", "bbox": [12, 12, 61, 61]},
        ],
    )
    raw["boxes"][0]["source_prompt"] = {"id": "icon", "text": "diagram icon"}
    raw["boxes"][1]["source_prompt"] = {"id": "icons", "text": "diagram icons"}

    merged, _ = merge_box_ir(raw)

    assert len(merged["boxes"]) == 1
    assert merged["boxes"][0]["source_prompt"] == "icon"
    assert merged["boxes"][0]["source_prompts"] == ["icon"]


def test_keep_trace_is_summarized_for_many_non_overlapping_boxes():
    raw = build_raw_box_ir(
        canvas=(600, 80),
        source_image="inputs/figure.png",
        normalized_long_edge=3840,
        prompt_runs=[],
        raw_regions=[
            {"source_prompt": "icon", "bbox": [index * 30, 10, index * 30 + 10, 20]}
            for index in range(18)
        ],
    )

    merged, trace = merge_box_ir(raw)

    assert len(merged["boxes"]) == 18
    assert len(trace["decisions"]) < 40
    assert trace["keep_summary"]["overlap_below_duplicate_threshold"] == 153
    assert trace["keep_summary"]["different_type"] == 0
    assert 1 <= len(trace["keep_summary"]["samples"]) <= 8
    assert trace["keep_summary"]["samples"][0]["action"] == "keep"
