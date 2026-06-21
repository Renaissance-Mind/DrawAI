from __future__ import annotations

from drawai.slide_template_assets import (
    load_slide_template_asset,
    template_asset_summary,
)


def test_template_asset_loader_reads_manifest_directories() -> None:
    summary = template_asset_summary()
    ids = {item["id"] for item in summary}

    assert {"swiss_international", "aurora_ui", "prisma_flow_diagram"}.issubset(ids)
    assert all(item["manifest_path"].endswith("template.json") for item in summary)


def test_prisma_flow_template_asset_contains_real_reference_image() -> None:
    asset = load_slide_template_asset("prisma_flow_diagram")

    assert asset["schema"] == "drawai.slide_template_asset.v1"
    assert asset["layout"]["archetype"] == "prisma_flow"
    assert asset["slot_schema"]["flow_boxes"]["required"] is True
    assert asset["reference_images"]
    assert asset["reference_images"][0]["path"].endswith("prisma_reference.jpg")
    assert "original study numbers" in asset["reference_images"][0]["forbidden_copy"]
