from __future__ import annotations

import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from run_ppt_template_gallery_category_sample import (  # noqa: E402
    DECK_PAGES,
    SELECTED_TEMPLATES,
    _base_payload,
    _write_prompt_only_record,
)


def test_gallery_sample_uses_two_templates_per_major_category() -> None:
    categories: dict[str, list[str]] = {}
    for template in SELECTED_TEMPLATES:
        categories.setdefault(template["category"], []).append(template["template_id"])

    assert len(SELECTED_TEMPLATES) == 12
    assert len(categories) == 6
    assert all(len(template_ids) == 2 for template_ids in categories.values())
    assert {item["template_id"] for item in SELECTED_TEMPLATES} >= {
        "mckinsey_boardroom",
        "openai_minimal",
        "economist_data_story",
        "nature_paper_briefing",
        "swiss_grid",
        "blue_robot_learning",
    }


def test_gallery_sample_payload_is_continuous_baked_text_deck() -> None:
    payload = _base_payload(
        template=SELECTED_TEMPLATES[0],
        template_meta={"best_for": "boardroom strategy", "visual_direction": "consulting grid"},
        page=DECK_PAGES[0],
        page_index=1,
        page_count=4,
    )

    assert payload["template_id"] == "mckinsey_boardroom"
    assert payload["candidate_count"] == 1
    assert payload["style_candidate_count"] == 1
    assert payload["rendering_mode"] == "baked_text"
    assert payload["source_mode"] == "source_grounded"
    assert payload["visible_text_blocks"]["title"]
    assert "1/4" in payload["prompt"]
    assert "continuous deck" not in payload["prompt"]
    assert any("deck" in item for item in payload["composition_guidance"])
    assert payload["data_sources"]["metrics"]


def test_gallery_sample_prompt_only_record_writes_artifacts(tmp_path: Path) -> None:
    record = _write_prompt_only_record(
        output_dir=tmp_path,
        template=SELECTED_TEMPLATES[1],
        template_meta={"best_for": "strategy maps", "visual_direction": "consulting strategy map"},
        page=DECK_PAGES[1],
        page_dir=tmp_path / "case",
        page_index=2,
        page_count=4,
    )

    assert record["status"] == "prompt_only"
    assert record["operation"] == "generate"
    assert record["template_id"] == "bcg_strategy_map"
    assert (tmp_path / "case" / "payload.json").is_file()
    assert (tmp_path / "case" / "prompt.txt").is_file()
    assert (tmp_path / "case" / "record.json").is_file()
    payload = json.loads((tmp_path / "case" / "payload.json").read_text(encoding="utf-8"))
    prompt = (tmp_path / "case" / "prompt.txt").read_text(encoding="utf-8")
    assert payload["rendering_mode"] == "baked_text"
    assert "template_id: bcg_strategy_map" in prompt
    assert "Selected template enforcement" in prompt
