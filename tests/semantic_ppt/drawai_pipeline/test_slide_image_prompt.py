from __future__ import annotations

from drawai.slide_image_prompt import (
    build_legacy_workbench_image_generation_prompt,
    build_slide_image_generation_manifest,
    build_slide_image_generation_prompt,
    build_slide_image_prompt_comparison,
    codex_imagegen_context_payload,
    merge_codex_imagegen_context,
)
from drawai.slide_image_strategy import build_slide_image_strategy_manifest, template_registry_summary


def test_slide_image_prompt_ignores_removed_structured_controls() -> None:
    payload = {
        "prompt": "create a premium slide about Acme widget growth",
        "size": "2048x1152",
        "quality": "high",
        "background": "opaque",
        "output_format": "png",
        "research_context": {"sources": [{"evidence": "Acme shipped 42 reliable widgets in 2026."}]},
        "claims": [{"claim": "Acme shipped 42 reliable widgets in 2026."}],
        "locked_visible_text": ["Acme shipped 42 widgets"],
        "visible_text_blocks": {"title": "Acme 业务进展"},
        "data_sources": {"metrics": [{"name": "reliable widgets shipped", "value": 42}]},
        "source_mode": "data_driven",
        "text_density": "high",
        "style_candidate_count": 3,
        "style_candidate_index": 2,
        "visual_style": "Swiss editorial",
        "composition_guidance": ["avoid empty regions"],
        "ip_safety_mode": "generic",
    }

    prompt = build_slide_image_generation_prompt(payload, variant_index=1, variant_count=3)

    assert "DrawAI high-quality PPT slide image request." in prompt
    assert "create a premium slide about Acme widget growth" in prompt
    assert "- size: 2048x1152" in prompt
    assert "- quality: high" in prompt
    assert "variant 1 of 3" in prompt
    assert "Baked text directive" in prompt
    assert "rendering_mode: baked_text" in prompt
    assert "Do not invent statistics" in prompt
    assert "OCR-friendly" in prompt
    assert "Optional template:" in prompt
    assert "- none selected." in prompt
    assert "SOURCE-GROUNDED" not in prompt
    assert "REQUIRED_VISIBLE_TEXT" not in prompt
    assert "Acme shipped 42 reliable widgets" not in prompt
    assert "Acme shipped 42 widgets" not in prompt
    assert "Acme 业务进展" not in prompt
    assert "reliable widgets shipped" not in prompt
    assert "source_mode" not in prompt
    assert "text_density" not in prompt
    assert "Style candidate" not in prompt
    assert "Swiss editorial" not in prompt
    assert "Composition guidance" not in prompt
    assert "IP safety" not in prompt


def test_slide_image_strategy_defaults_to_no_template() -> None:
    strategy = build_slide_image_strategy_manifest(
        {
            "prompt": "create a technical model architecture PPT for the KIMI model series",
            "claims": [{"claim": "Kimi K2 is a MoE model."}],
            "source_mode": "source_grounded",
            "data_sources": {"metrics": [{"name": "线索", "value": 1200}]},
        }
    )

    assert strategy["schema"] == "drawai.slide_image_strategy.v1"
    assert strategy["strategy_version"] == "v3_optional_template_baked_text"
    assert strategy["rendering_mode"] == "baked_text"
    assert strategy["intent"] == "technical"
    assert strategy["selected_template"] is None
    assert strategy["template_selection"] == {"mode": "none", "id": ""}
    assert "source_mode" not in strategy
    assert "candidate_stage" not in strategy


def test_slide_image_strategy_template_override_is_explicit_only() -> None:
    strategy = build_slide_image_strategy_manifest(
        {
            "prompt": "生成市场进入策略PPT",
            "template_id": "consulting_report",
            "source_mode": "prompt_only",
        }
    )

    assert strategy["selected_template"]["id"] == "consulting_report"
    assert strategy["template_selection"] == {"mode": "selected", "id": "consulting_report"}
    assert "text_density" not in strategy["selected_template"]
    assert "data_policy" not in strategy["selected_template"]
    assert "ip_safety" not in strategy["selected_template"]
    assert "source_mode" not in strategy
    assert "candidate_stage" not in strategy


def test_slide_image_generation_prompt_includes_selected_template_without_old_blocks() -> None:
    prompt = build_slide_image_generation_prompt(
        {
            "prompt": "生成市场进入策略PPT",
            "template_id": "consulting_report",
            "source_mode": "prompt_only",
            "text_density": "high",
        }
    )

    assert "Template: consulting_report / Consulting Report" in prompt
    assert "executive headline takeaway" in prompt
    assert "2x2 decision matrix" in prompt
    assert "Optional template:" in prompt
    assert "Selected template enforcement" not in prompt
    assert "PPT image strategy and selected template" not in prompt
    assert "source_mode" not in prompt
    assert "text_density" not in prompt


def test_chinese_prompt_uses_auto_language_inference() -> None:
    prompt = build_slide_image_generation_prompt(
        {
            "prompt": "生成一个中文技术PPT：Agent Memory 系统如何支持长期任务。",
            "locked_visible_text": ["Threat Model", "Source Quality", "World Model Stack"],
        }
    )

    assert "main_language: Chinese" in prompt
    assert "Do not render generic English section headings" in prompt
    assert "核心结论、来源质量、威胁模型" in prompt
    assert "Threat Model" not in prompt
    assert "EXACT_TEXT_DO_NOT_TRANSLATE" not in prompt


def test_exact_visible_text_fields_are_ignored() -> None:
    prompt = build_slide_image_generation_prompt(
        {
            "prompt": "生成中文PPT，标题由主提示词自然决定。",
            "exact_visible_text": ["DrawAI Studio"],
            "locked_visible_text": ["DrawAI Studio"],
        }
    )

    assert "DrawAI Studio" not in prompt
    assert "EXACT_TEXT_DO_NOT_TRANSLATE" not in prompt
    assert "REQUIRED_VISIBLE_TEXT" not in prompt


def test_slide_image_template_registry_exposes_multiple_options_without_density() -> None:
    registry = template_registry_summary()
    ids = {item["id"] for item in registry}

    assert len(registry) >= 49
    assert {
        "academic_technical",
        "consulting_report",
        "data_journalism",
        "product_launch",
        "notebooklm_briefing",
        "mckinsey_boardroom",
        "bcg_strategy_map",
        "investment_memo",
        "vc_pitch_deck",
        "annual_report",
        "openai_minimal",
        "apple_keynote",
        "linear_product_dark",
        "vercel_gradient",
        "stripe_saas",
        "developer_docs",
        "cyberpunk_infra",
        "economist_data_story",
        "bloomberg_terminal",
        "nyt_scrollytelling",
        "financial_times_report",
        "infographic_dashboard",
        "nature_paper_briefing",
        "neurips_poster",
        "lab_meeting",
        "notebooklm_cards",
        "teaching_whiteboard",
        "courseware_explainer",
        "swiss_grid",
        "bauhaus_geometric",
        "memphis_playful",
        "brutalist_poster",
        "glassmorphism",
        "claymorphism",
        "bento_grid",
        "isometric_3d",
        "retro_futurism",
        "pixel_art",
        "blue_robot_learning",
        "soft_storybook_anime",
        "collectible_creature_cards",
        "toy_block_diagram",
        "retro_platform_game",
        "comic_manga_classroom",
    }.issubset(ids)
    assert all("text_density" not in item for item in registry)
    categories = {item["category"] for item in registry}
    assert "professional_business_consulting" in categories
    assert "ip_safe_cartoon" in categories


def test_doraemon_like_request_does_not_auto_select_cartoon_template() -> None:
    strategy = build_slide_image_strategy_manifest(
        {
            "prompt": "make a teaching PPT in a Doraemon-like blue robot atmosphere",
            "source_mode": "prompt_only",
        }
    )

    assert strategy["selected_template"] is None
    assert strategy["template_selection"]["mode"] == "none"


def test_blue_robot_template_no_longer_emits_ip_safety_policy() -> None:
    prompt = build_slide_image_generation_prompt(
        {
            "prompt": "make a teaching PPT in a Doraemon-like blue robot atmosphere",
            "template_id": "blue_robot_learning",
            "source_mode": "prompt_only",
            "ip_safety_mode": "generic",
        }
    )

    assert "Template: blue_robot_learning / Blue Robot Learning" in prompt
    assert "friendly original blue-white rounded robot tutor" in prompt
    assert "IP safety" not in prompt
    assert "no exact Doraemon likeness" not in prompt
    assert "no collar bell" not in prompt
    assert "ip_safety_mode" not in prompt


def test_slide_image_prompt_includes_template_card_without_reference_mode() -> None:
    prompt = build_slide_image_generation_prompt(
        {
            "prompt": "生成企业知识库 AI Agent 落地方案 PPT",
            "template_card_id": "swiss_international",
            "reference_mode": "reference_tokens_only",
            "reference_image_tokens": {
                "schema": "drawai.reference_image_tokens.v1",
                "dominant_palette": ["#ffffff", "#f7c400", "#1f2937"],
            },
        }
    )

    assert "Card: swiss_international / Swiss International" in prompt
    assert "Prompt recipe" in prompt
    assert "modular grid" in prompt
    assert "reference_mode" not in prompt
    assert "reference_image_tokens" not in prompt
    assert "#f7c400" not in prompt


def test_codex_imagegen_context_keeps_only_supported_prompt_fields() -> None:
    raw = {
        "prompt": "draw a slide",
        "size": "1024x1024",
        "research_context": {"url": "https://example.test"},
        "locked_visible_text": ["Exact title"],
        "spec_guided_enabled": True,
        "template_spec": {"schema": "drawai.ppt_template_spec.v1"},
        "ip_safety_mode": "off",
        "template_id": "consulting_report",
        "language": "zh",
        "api_key": "do-not-merge",
    }
    normalized = {
        "model": "gpt-image-2",
        "prompt": "draw a slide",
        "size": "1024x1024",
        "n": 1,
    }

    context = codex_imagegen_context_payload(raw)
    merged = merge_codex_imagegen_context(normalized, raw)

    assert context == {
        "language": "zh",
        "template_id": "consulting_report",
    }
    assert merged["model"] == "gpt-image-2"
    assert merged["template_id"] == "consulting_report"
    assert merged["language"] == "zh"
    assert "research_context" not in merged
    assert "locked_visible_text" not in merged
    assert "spec_guided_enabled" not in merged
    assert "template_spec" not in merged
    assert "ip_safety_mode" not in merged
    assert "api_key" not in merged


def test_slide_image_generation_manifest_is_structured() -> None:
    manifest = build_slide_image_generation_manifest(
        {
            "prompt": "draw a slide",
            "visible_text": ["Visible title"],
            "subtitle": "Readable subtitle",
            "key_message": "One useful takeaway",
            "quality_gates": ["brand-consistent"],
        }
    )

    assert manifest["schema"] == "drawai.slide_image_prompt.v1"
    assert manifest["text"]["requested_language"] == "auto"
    assert "locked_visible_text" not in manifest["text"]
    assert "grounding" not in manifest
    assert "spec_guided" not in manifest
    assert "reference_execution" not in manifest
    assert "brand-consistent" in manifest["quality_gates"]
    assert "no unreadable microtext, mojibake, pseudo-letters, or random captions" in manifest["quality_gates"]
    assert "use the full 16:9 canvas with balanced density; avoid large accidental empty regions" in manifest["quality_gates"]


def test_slide_image_generation_manifest_ignores_spec_guided_fields() -> None:
    payload = {
        "prompt": "生成系统综述流程页",
        "spec_guided_enabled": True,
        "template_spec": {"schema": "drawai.ppt_template_spec.v1"},
        "slot_schema": {"slots": [{"id": "title", "role": "headline"}]},
        "reference_style_spec": {"schema": "drawai.reference_style_spec.v1"},
        "design_tokens": {"palette": ["yellow", "white", "charcoal"]},
        "spec_lock": {"lock_canvas": True, "lock_layout_roles": True},
        "reference_roles": [{"role": "layout_reference"}],
    }

    manifest = build_slide_image_generation_manifest(payload)
    prompt = build_slide_image_generation_prompt(payload)

    assert "spec_guided" not in manifest
    assert "Spec-guided design lock:" not in prompt
    assert "template_spec" not in prompt
    assert "slot_schema" not in prompt
    assert "reference_style_spec" not in prompt
    assert "layout_reference" not in prompt


def test_legacy_and_improved_prompt_comparison_exposes_current_added_controls() -> None:
    payload = {
        "prompt": "academic slide about a grounded reconstruction pipeline",
        "size": "2048x1152",
        "quality": "high",
        "background": "opaque",
        "output_format": "png",
        "research_context": {"source": "project brief"},
        "locked_visible_text": ["Exact title"],
    }

    legacy = build_legacy_workbench_image_generation_prompt(payload)
    comparison = build_slide_image_prompt_comparison(payload)

    assert "DrawAI image generation request." in legacy
    assert "SOURCE-GROUNDED" not in comparison["improved_prompt"]
    assert "REQUIRED_VISIBLE_TEXT" not in comparison["improved_prompt"]
    assert "baked_text" in comparison["diff_summary"]["added_controls"]
    assert "drawai_postprocess" in comparison["diff_summary"]["added_controls"]
    assert "quality_gates" in comparison["diff_summary"]["added_controls"]
    assert "source_grounding" not in comparison["diff_summary"]["added_controls"]
    assert "required_visible_text" not in comparison["diff_summary"]["added_controls"]
