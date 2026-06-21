from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


def test_assets_visualization_reads_element_plan_bbox_as_xywh() -> None:
    module = _load_assets_visualization()
    record = {
        "schema": "drawai.element_plan.v1",
        "element_id": "E001",
        "element_type": "picture",
        "bbox": [2, 3, 10, 12],
        "processing_intent": {"processing_type": "crop"},
        "review_status": "agent_refined",
    }

    assert module.bbox_from_record(record) == (2.0, 3.0, 12.0, 15.0)
    drawable = module.normalize_drawable_record(
        record,
        index=0,
        bbox=(2.0, 3.0, 12.0, 15.0),
        color_mode="category",
        label_mode="id_category",
    )
    assert drawable["category"] == "crop"
    assert drawable["action"] == "agent_refined"
    assert drawable["label"] == "E001 crop"


def _load_assets_visualization() -> ModuleType:
    script_path = Path(__file__).parents[2] / "scripts" / "assets_visualization.py"
    spec = importlib.util.spec_from_file_location("assets_visualization", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
