from __future__ import annotations

from drawai.slide_template_library import (
    build_prompt_from_template_card,
    list_template_cards,
    recommend_template_cards,
)


def test_template_library_has_expected_seed_cards() -> None:
    cards = list_template_cards()
    ids = {card["id"] for card in cards}

    assert len(cards) >= 60
    assert {
        "modern_newspaper",
        "sharp_minimal",
        "yellow_black_editorial",
        "manga_safe_learning",
        "studio_premium_mockup",
        "retro_pop_art",
        "minimalist_clean",
        "cyberpunk_neon",
        "neo_brutalism",
        "acid_y2k",
        "swiss_international",
        "dark_editorial",
        "design_blueprint",
        "aurora_ui",
        "light_glassmorphism",
        "frutiger_aero",
        "course_clay",
        "corporate_strategy_cinematic",
        "weekly_kanban",
        "sales_architectural",
    }.issubset(ids)

    for card in cards:
        assert card["prompt_recipe"]
        assert card["visual_keywords"]
        assert card["layout_archetypes"]
        assert "source_policy" in card
        assert "reference_images" in card
        assert "sample_outputs" in card
        assert "tests" in card
        assert "provenance" in card


def test_template_library_covers_external_style_families() -> None:
    cards = list_template_cards()
    ids = {card["id"] for card in cards}
    provenance_sources = {
        source.get("source")
        for card in cards
        for source in card.get("provenance", [])
    }

    assert {
        "modern_minimal_pop",
        "neo_brutalist_ui",
        "y2k_pixel_retro",
        "bento_grid_showcase",
        "scrapbook_diy",
        "dark_glassmorphism",
        "classic_deep_skeuomorphism",
    }.issubset(ids)
    assert {
        "black_orange_agency",
        "mature_cute_magazine",
        "pink_street_pop",
        "digital_neo_pop",
        "anti_gravity_artifact",
        "sports_athletic_energy",
        "neo_retro_dev_deck",
    }.issubset(ids)
    assert {
        "editorial_magazine_architecture",
        "bloomberg_dark_dashboard",
        "glassmorphism_saas",
        "memphis_pop_festival",
        "risograph_zine",
    }.issubset(ids)
    assert {
        "creative_class_clay",
        "tech_knowledge_isometric_lab",
        "annual_strategy_cinematic",
        "company_profile_swiss",
        "fintech_glass_data",
        "market_analysis_3d_infographic",
        "project_progress_kanban",
        "personal_review_paper_cutout",
        "b2b_solution_architectural",
        "consumer_marketing_neobrutal",
    }.issubset(ids)
    assert {
        "AAAAAAAJ/slides PROMPTS.md",
        "awesome-notebookLM-prompts",
        "ppt-master examples",
        "nano-banana-ppt scene prompt collection",
        "frontend-slides / beautiful-html-templates / html-ppt-skill family",
    }.issubset(provenance_sources)


def test_recommend_template_cards_routes_enterprise_agent_topic() -> None:
    cards = recommend_template_cards("AI Agent 工作流如何落地企业知识库", limit=5)
    ids = {card["id"] for card in cards}
    categories = {card["category"] for card in cards}

    assert len(cards) == 5
    assert ids.intersection({"aurora_ui", "design_blueprint", "minimalist_clean", "swiss_international", "corporate_strategy_cinematic"})
    assert categories.intersection({"tech_ai_product", "business_technical", "business_strategy"})


def test_prompt_from_swiss_card_contains_style_keywords_and_chinese_policy() -> None:
    prompt = build_prompt_from_template_card(
        "swiss_international",
        "AI Agent 工作流如何落地企业知识库",
        language="zh",
    )

    assert "Swiss International" in prompt
    assert "modular grid" in prompt
    assert "main_language: Chinese" in prompt
    assert "Render main title" in prompt
    assert "3-6 concise bullets" in prompt
    assert "Do not leave empty layout placeholders" in prompt


def test_reference_image_paths_enter_prompt_policy() -> None:
    prompt = build_prompt_from_template_card(
        "light_glassmorphism",
        "企业知识库 Agent 工作流产品页",
        language="zh",
        reference_image_paths=["outputs/example/reference.png"],
    )

    assert "Reference image policy" in prompt
    assert "outputs/example/reference.png" in prompt
    assert "style_reference_images" in prompt
    assert "style/layout references only" in prompt
    assert "Do not copy logos" in prompt
    assert "protected artwork" in prompt


def test_manga_safe_learning_prompt_enforces_ip_safety() -> None:
    prompt = build_prompt_from_template_card(
        "manga_safe_learning",
        "用漫画课堂讲解 AI Agent 记忆机制",
        language="zh",
    )

    assert "IP safety" in prompt
    assert "No copyrighted manga/anime characters" in prompt
    assert "no exact likeness" in prompt
    assert "no trademarked props" in prompt
    assert "no Doraemon-like bell" in prompt
