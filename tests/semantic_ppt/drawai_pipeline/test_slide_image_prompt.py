from __future__ import annotations

from pathlib import Path

from drawai.slide_image_prompt import (
    build_legacy_workbench_image_generation_prompt,
    build_slide_image_generation_manifest,
    build_slide_image_generation_prompt,
    build_slide_image_prompt_comparison,
    codex_imagegen_context_payload,
    merge_codex_imagegen_context,
)
from drawai.slide_image_strategy import build_slide_image_strategy_manifest, template_registry_summary


def test_slide_image_prompt_preserves_grounding_and_text_policy() -> None:
    payload = {
        "prompt": "create a premium slide about Acme widget growth",
        "size": "2048x1152",
        "quality": "high",
        "background": "opaque",
        "output_format": "png",
        "research_context": {
            "sources": [
                {
                    "title": "Acme annual report",
                    "url": "https://example.test/report",
                    "evidence": "Acme shipped 42 reliable widgets in 2026.",
                }
            ]
        },
        "claims": [
            {
                "claim": "Acme shipped 42 reliable widgets in 2026.",
                "source_url": "https://example.test/report",
            }
        ],
        "locked_visible_text": ["Acme shipped 42 widgets"],
        "title": "Acme widget growth",
        "subtitle": "Source-grounded overview",
        "key_message": "Acme shipped 42 widgets",
        "style": "Swiss editorial",
    }

    prompt = build_slide_image_generation_prompt(payload, variant_index=1, variant_count=3)

    assert "DrawAI high-quality PPT slide image request." in prompt
    assert "SOURCE-GROUNDED" in prompt
    assert "Acme shipped 42 reliable widgets in 2026." in prompt
    assert "REQUIRED_VISIBLE_TEXT" in prompt
    assert "Acme shipped 42 widgets" in prompt
    assert "Swiss editorial" in prompt
    assert "Do not invent statistics" in prompt
    assert "variant 1 of 3" in prompt
    assert "OCR-friendly" in prompt
    assert "Required visible text is a floor, not a ceiling" in prompt
    assert "3-6 concise explanatory bullets or callouts" in prompt
    assert "never leave the slide textless" in prompt
    assert "PERMITTED_BODY_COPY_SOURCES" in prompt
    assert "Preserve the user's language" in prompt
    assert "If the request is Chinese, render Chinese slide copy" in prompt
    assert "Acme widget growth" in prompt
    assert "Source-grounded overview" in prompt
    assert "text_density: medium" in prompt
    assert "Composition guidance" in prompt
    assert "avoid large accidental empty regions" in prompt
    assert "not a sparse wireframe" in prompt
    assert "layout-only wireframe" in prompt
    assert "Visual richness guidance" in prompt
    assert "PPT image strategy and selected template" in prompt
    assert "Selected template enforcement" in prompt
    assert "Visual direction" in prompt
    assert "Baked text directive" in prompt
    assert "rendering_mode: baked_text" in prompt
    assert "Style candidate stage" in prompt
    assert "v2_multi_option_baked_text" in prompt
    assert "left input bookend" in prompt
    assert "synthetic figure thumbnails" in prompt
    assert "do not add axis labels" in prompt
    assert "Do not infer a scientific domain" in prompt
    assert "avoid domain-specific imagery" in prompt
    assert "neutral paper-figure thumbnails" in prompt


def test_slide_image_prompt_warns_when_sources_are_missing() -> None:
    prompt = build_slide_image_generation_prompt(
        {
            "prompt": "make a cinematic title slide for a future product",
            "size": "1920x1080",
        }
    )

    assert "NO VERIFIED SOURCES PROVIDED" in prompt
    assert "do not add new facts beyond the primary request" in prompt
    assert "Do not invent statistics" in prompt


def test_slide_image_strategy_defaults_to_baked_text_and_candidates() -> None:
    strategy = build_slide_image_strategy_manifest(
        {
            "prompt": "create a technical model architecture PPT for the KIMI model series",
            "claims": [{"claim": "Kimi K2 is a MoE model."}],
        }
    )

    assert strategy["schema"] == "drawai.slide_image_strategy.v1"
    assert strategy["strategy_version"] == "v2_multi_option_baked_text"
    assert strategy["rendering_mode"] == "baked_text"
    assert strategy["intent"] == "technical"
    assert strategy["selected_template"]["id"] == "dark_tech"
    assert strategy["source_mode"]["id"] == "source_grounded"
    assert len(strategy["candidate_stage"]["templates"]) == 3
    assert strategy["selected_template"]["id"] in {
        item["id"] for item in strategy["candidate_stage"]["templates"]
    }
    assert "Codex built-in image generation tool exactly once per image; never call OpenAI Images API manually in Codex mode." in strategy[
        "prior_research_features"
    ]


def test_slide_image_strategy_template_override() -> None:
    strategy = build_slide_image_strategy_manifest(
        {
            "prompt": "生成市场进入策略PPT",
            "template_id": "consulting_report",
            "source_mode": "prompt_only",
        }
    )

    assert strategy["selected_template"]["id"] == "consulting_report"
    assert strategy["source_mode"]["id"] == "prompt_only"
    assert strategy["candidate_stage"]["templates"][0]["id"] == "consulting_report"


def test_slide_image_strategy_promotes_prompt_only_when_data_is_supplied() -> None:
    strategy = build_slide_image_strategy_manifest(
        {
            "prompt": "生成销售漏斗数据复盘 PPT",
            "source_mode": "prompt_only",
            "data_sources": {"metrics": [{"name": "线索", "value": 1200}]},
        }
    )

    assert strategy["source_mode"]["id"] == "data_driven"


def test_slide_image_generation_prompt_enforces_template_archetypes() -> None:
    prompt = build_slide_image_generation_prompt(
        {
            "prompt": "生成市场进入策略PPT",
            "template_id": "consulting_report",
            "source_mode": "prompt_only",
        }
    )

    assert "Consulting enforcement" in prompt
    assert "executive takeaway" in prompt
    assert "2x2 matrix" in prompt
    assert "do not default to a technical pipeline" in prompt


def test_chinese_prompt_translates_generic_english_visible_text() -> None:
    prompt = build_slide_image_generation_prompt(
        {
            "prompt": "生成一个中文技术PPT：Agent Memory 系统如何支持长期任务。",
            "title": "Agent Memory Systems",
            "subtitle": "Memory Layers",
            "key_message": "Memory turns one-shot agents into durable workflows",
            "locked_visible_text": ["Threat Model", "Source Quality", "World Model Stack"],
            "labels": ["Agent memory", "Long tasks"],
        }
    )

    assert "main_language: Chinese" in prompt
    assert "Do not render generic English section headings" in prompt
    assert "核心结论、来源质量、威胁模型" in prompt
    assert "treat them as semantic hints and render concise Chinese equivalents" in prompt
    assert "EXACT_TEXT_DO_NOT_TRANSLATE" in prompt


def test_exact_visible_text_can_still_be_preserved() -> None:
    prompt = build_slide_image_generation_prompt(
        {
            "prompt": "生成中文PPT，但保留指定产品名。",
            "exact_visible_text": ["DrawAI Studio"],
            "locked_visible_text": ["DrawAI Studio"],
        }
    )

    assert "DrawAI Studio" in prompt
    assert "EXACT_TEXT_DO_NOT_TRANSLATE" in prompt


def test_slide_image_template_registry_exposes_multiple_options() -> None:
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
    categories = {item["category"] for item in registry}
    assert "professional_business_consulting" in categories
    assert "ip_safe_cartoon" in categories


def test_slide_image_strategy_routes_to_new_business_candidates() -> None:
    strategy = build_slide_image_strategy_manifest(
        {
            "prompt": "create an investment memo PPT for market entry strategy and boardroom decision making",
            "source_mode": "prompt_only",
        },
        candidate_count=5,
    )
    candidate_ids = {item["id"] for item in strategy["candidate_stage"]["templates"]}

    assert strategy["intent"] == "business"
    assert strategy["selected_template"]["id"] == "mckinsey_boardroom"
    assert {"mckinsey_boardroom", "bcg_strategy_map", "investment_memo"}.issubset(candidate_ids)


def test_slide_image_strategy_can_select_new_template_id() -> None:
    strategy = build_slide_image_strategy_manifest(
        {
            "prompt": "make a safe cartoon learning PPT with a blue robot tutor",
            "template_id": "blue-robot-learning",
            "source_mode": "prompt_only",
        }
    )

    assert strategy["selected_template"]["id"] == "blue_robot_learning"
    assert strategy["candidate_stage"]["templates"][0]["id"] == "blue_robot_learning"


def test_doraemon_like_request_prefers_ip_safe_blue_robot_template() -> None:
    strategy = build_slide_image_strategy_manifest(
        {
            "prompt": "make a teaching PPT in a Doraemon-like blue robot atmosphere",
            "source_mode": "prompt_only",
        }
    )

    assert strategy["selected_template"]["id"] == "blue_robot_learning"
    assert strategy["candidate_stage"]["templates"][0]["id"] == "blue_robot_learning"


def test_blue_robot_template_ip_safety_is_off_by_default() -> None:
    prompt = build_slide_image_generation_prompt(
        {
            "prompt": "make a teaching PPT in a Doraemon-like blue robot atmosphere",
            "template_id": "blue_robot_learning",
            "source_mode": "prompt_only",
        }
    )

    assert "Template: blue_robot_learning / Blue Robot Learning" in prompt
    assert "Template-specific enforcement" in prompt
    assert "IP safety" not in prompt
    assert "no exact Doraemon likeness" not in prompt
    assert "no collar bell" not in prompt
    assert "Blue-robot visual enforcement" in prompt


def test_blue_robot_template_enforces_ip_safety_when_enabled() -> None:
    prompt = build_slide_image_generation_prompt(
        {
            "prompt": "make a teaching PPT in a Doraemon-like blue robot atmosphere",
            "template_id": "blue_robot_learning",
            "source_mode": "prompt_only",
            "ip_safety_mode": "generic",
        }
    )

    assert "Template: blue_robot_learning / Blue Robot Learning" in prompt
    assert "IP safety" in prompt
    assert "no copyrighted character" in prompt
    assert "no exact Doraemon likeness" in prompt
    assert "no trademarked symbols" in prompt
    assert "no collar bell" in prompt


def test_slide_image_prompt_includes_template_card_and_reference_mode() -> None:
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

    assert "Template effect card" in prompt
    assert "Card: swiss_international / Swiss International" in prompt
    assert "Prompt recipe" in prompt
    assert "reference_mode: reference_tokens_only" in prompt
    assert "reference_image_tokens" in prompt
    assert "#f7c400" in prompt


def test_codex_imagegen_context_is_kept_out_of_api_payload() -> None:
    raw = {
        "prompt": "draw a slide",
        "size": "1024x1024",
        "research_context": {"url": "https://example.test"},
        "locked_visible_text": ["Exact title"],
        "spec_guided_enabled": True,
        "template_spec": {"schema": "drawai.ppt_template_spec.v1"},
        "ip_safety_mode": "off",
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
        "ip_safety_mode": "off",
        "locked_visible_text": ["Exact title"],
        "research_context": {"url": "https://example.test"},
        "spec_guided_enabled": True,
        "template_spec": {"schema": "drawai.ppt_template_spec.v1"},
    }
    assert merged["model"] == "gpt-image-2"
    assert merged["research_context"] == {"url": "https://example.test"}
    assert merged["locked_visible_text"] == ["Exact title"]
    assert merged["spec_guided_enabled"] is True
    assert merged["template_spec"] == {"schema": "drawai.ppt_template_spec.v1"}
    assert "api_key" not in merged


def test_original_codex_imagegen_runner_snapshot_is_available() -> None:
    snapshot = Path("docs/baselines/codex_python_sdk_imagegen.original.py")

    assert snapshot.is_file()
    text = snapshot.read_text(encoding="utf-8")
    assert "def invoke_codex_python_sdk_imagegen" in text
    assert "Internal DrawAI text-to-image runner." in text


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
    assert manifest["text"]["locked_visible_text"] == ["Readable subtitle", "One useful takeaway", "Visible title"]
    assert "brand-consistent" in manifest["quality_gates"]
    assert "no unreadable microtext, mojibake, pseudo-letters, or random captions" in manifest["quality_gates"]
    assert "use the full 16:9 canvas with balanced density; avoid large accidental empty regions" in manifest["quality_gates"]


def test_slide_image_generation_manifest_accepts_spec_guided_fields() -> None:
    payload = {
        "prompt": "生成系统综述流程页",
        "spec_guided_enabled": True,
        "template_spec": {
            "schema": "drawai.ppt_template_spec.v1",
            "slide_size": {"width_in": 13.333, "height_in": 7.5},
        },
        "slot_schema": {"slots": [{"id": "title", "role": "headline"}]},
        "reference_style_spec": {
            "schema": "drawai.reference_style_spec.v1",
            "reference_roles": [{"role": "layout_reference"}],
        },
        "design_tokens": {"palette": ["yellow", "white", "charcoal"]},
        "spec_lock": {"lock_canvas": True, "lock_layout_roles": True},
        "reference_roles": [{"role": "layout_reference"}],
    }

    manifest = build_slide_image_generation_manifest(payload)
    prompt = build_slide_image_generation_prompt(payload)

    assert manifest["spec_guided"]["enabled"] is True
    assert manifest["spec_guided"]["template_spec"]["schema"] == "drawai.ppt_template_spec.v1"
    assert manifest["spec_guided"]["slot_schema"]["slots"][0]["role"] == "headline"
    assert manifest["spec_guided"]["reference_roles"][0]["role"] == "layout_reference"
    assert "Spec-guided design lock:" in prompt
    assert "template_spec" in prompt
    assert "slot_schema" in prompt
    assert "reference_style_spec" in prompt
    assert "layout_reference" in prompt


def test_legacy_and_improved_prompt_comparison_exposes_added_controls() -> None:
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
    assert "SOURCE-GROUNDED" not in legacy
    assert "REQUIRED_VISIBLE_TEXT" not in legacy
    assert "SOURCE-GROUNDED" in comparison["improved_prompt"]
    assert "REQUIRED_VISIBLE_TEXT" in comparison["improved_prompt"]
    assert "source_grounding" in comparison["diff_summary"]["added_controls"]
    assert "required_visible_text" in comparison["diff_summary"]["added_controls"]
