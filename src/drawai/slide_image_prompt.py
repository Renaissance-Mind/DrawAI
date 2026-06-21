from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from .slide_template_library import get_template_card
from .slide_image_strategy import build_slide_image_strategy_manifest


SLIDE_IMAGE_PROMPT_SCHEMA = "drawai.slide_image_prompt.v1"
DEFAULT_SLIDE_CANVAS = "presentation-grade 16:9 slide image"
DEFAULT_DESIGN_PRINCIPLES = (
    "finished PPT explanation page, not a bare layout scaffold",
    "balanced narrative text and visuals",
    "source-grounded factual content",
    "clear hierarchy with readable body copy",
    "high visual ambition with a polished first-glance impact",
)

CODEX_IMAGEGEN_CONTEXT_FIELDS = {
    "audience",
    "brand",
    "claims",
    "composition_guidance",
    "citations",
    "data_sources",
    "design_system",
    "do_not_translate_visible_text",
    "drawai_postprocess",
    "exact_visible_text",
    "fact_policy",
    "language",
    "locked_visible_text",
    "locked_visible_text_exact",
    "must_avoid",
    "must_include",
    "negative_prompt",
    "quality_gates",
    "research_context",
    "reference_image_tokens",
    "reference_mode",
    "slide_mode",
    "slide_type",
    "source_policy",
    "sources",
    "style",
    "style_reference",
    "style_references",
    "template",
    "text_policy",
    "text_density",
    "subtitle",
    "key_message",
    "candidate_count",
    "candidate_index",
    "deck_type",
    "intent",
    "ip_safety_mode",
    "rendering_mode",
    "source_mode",
    "spec_guided_enabled",
    "design_tokens",
    "reference_roles",
    "reference_style_spec",
    "slot_schema",
    "spec_lock",
    "strategy",
    "style_candidate_count",
    "style_candidate_index",
    "template_id",
    "template_card",
    "template_card_id",
    "template_spec",
    "tone",
    "visible_text",
    "visible_text_blocks",
    "output_language",
    "visual_richness_guidance",
    "visual_style",
}


def codex_imagegen_context_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return Codex-only prompt context fields without leaking them to the Images API path."""

    context = {key: payload[key] for key in CODEX_IMAGEGEN_CONTEXT_FIELDS if key in payload}
    if "visible_text" in context and "locked_visible_text" not in context:
        context["locked_visible_text"] = context["visible_text"]
    return context


def merge_codex_imagegen_context(
    normalized_payload: Mapping[str, Any],
    raw_payload: Mapping[str, Any],
) -> dict[str, Any]:
    merged = dict(normalized_payload)
    merged.update(codex_imagegen_context_payload(raw_payload))
    return merged


def build_slide_image_generation_manifest(
    payload: Mapping[str, Any],
    *,
    variant_index: int = 1,
    variant_count: int = 1,
) -> dict[str, Any]:
    prompt = _clean_text(payload.get("prompt"))
    strategy = build_slide_image_strategy_manifest(
        payload,
        candidate_index=_int_value(
            payload.get("style_candidate_index") or payload.get("candidate_index"),
            default=variant_index,
        ),
        candidate_count=_int_value(
            payload.get("style_candidate_count") or payload.get("candidate_count"),
            default=3,
        ),
    )
    manifest: dict[str, Any] = {
        "schema": SLIDE_IMAGE_PROMPT_SCHEMA,
        "primary_request": prompt,
        "variant": {
            "index": int(variant_index),
            "count": int(variant_count),
        },
        "generation_settings": {
            "size": _clean_text(payload.get("size")) or "1024x1024",
            "quality": _clean_text(payload.get("quality")) or "auto",
            "background": _clean_text(payload.get("background")) or "auto",
            "output_format": _clean_text(payload.get("output_format")) or "png",
        },
        "slide_intent": {
            "mode": _clean_text(payload.get("slide_mode")) or "image_first_ppt_slide",
            "type": _clean_text(payload.get("slide_type")) or "single-slide visual",
            "audience": _clean_text(payload.get("audience")),
            "tone": _clean_text(payload.get("tone")),
            "brand": _jsonish(payload.get("brand")),
        },
        "design": {
            "style": _clean_text(payload.get("style") or payload.get("visual_style")),
            "template": _clean_text(payload.get("template")),
            "template_id": _clean_text(payload.get("template_id")),
            "template_card_id": _clean_text(payload.get("template_card_id")),
            "template_card": _template_card_manifest(payload),
            "design_system": _jsonish(payload.get("design_system")),
            "style_references": _jsonish(payload.get("style_references") or payload.get("style_reference")),
            "design_principles": list(DEFAULT_DESIGN_PRINCIPLES),
        },
        "reference_execution": {
            "reference_mode": _clean_text(payload.get("reference_mode")) or "auto",
            "reference_image_tokens": _jsonish(payload.get("reference_image_tokens")),
        },
        "strategy": strategy,
        "grounding": {
            "sources": _jsonish(payload.get("sources") or payload.get("citations")),
            "research_context": _jsonish(payload.get("research_context")),
            "claims": _jsonish(payload.get("claims")),
            "data_sources": _jsonish(payload.get("data_sources")),
            "source_policy": _clean_text(payload.get("source_policy"))
            or "Use only provided sources and primary-request facts; never invent facts, dates, numbers, logos, citations, maps, UI, or named-entity details.",
        },
        "text": {
            "locked_visible_text": _locked_visible_text(payload),
            "exact_visible_text": _exact_visible_text(payload),
            "requested_language": _requested_language(payload),
            "visible_text_blocks": _jsonish(payload.get("visible_text_blocks")),
            "text_density": _clean_text(payload.get("text_density")) or "medium",
            "policy": _clean_text(payload.get("text_policy"))
            or (
                "Render a normal PPT explanation page: include required visible content, then add concise "
                "source-grounded body copy from the primary request, claims, and visible_text_blocks. Text must be "
                "readable, useful, and large enough for a slide thumbnail. Preserve the user's language unless the "
                "user explicitly asks for another language."
            ),
        },
        "inclusion": {
            "must_include": _jsonish(payload.get("must_include")),
            "must_avoid": _jsonish(payload.get("must_avoid")),
            "negative_prompt": _clean_text(payload.get("negative_prompt")),
        },
        "quality_gates": _quality_gates(payload),
        "drawai_postprocess": _drawai_postprocess(payload),
        "spec_guided": _spec_guided_manifest(payload),
    }
    return manifest


def build_legacy_workbench_image_generation_prompt(
    payload: Mapping[str, Any],
    *,
    variant_index: int = 1,
    variant_count: int = 1,
) -> str:
    """Reproduce the pre-grounding Workbench Codex image prompt for A/B tests."""

    lines = [
        "DrawAI image generation request.",
        f"Primary request: {_clean_text(payload.get('prompt'))}",
        "",
        "Generation settings selected in the DrawAI UI:",
        f"- Requested size/aspect: {payload.get('size')}",
        f"- Quality preference: {payload.get('quality')}",
        f"- Background preference: {payload.get('background')}",
        f"- Output format preference: {payload.get('output_format')}",
        f"- Requested image count: {variant_count}",
    ]
    if variant_count > 1:
        lines.append(
            f"- This tool call should produce image {variant_index} of {variant_count}; "
            "create a distinct useful variant without making a collage."
        )
    if _clean_text(payload.get("background")).lower() == "transparent":
        lines.append(
            "- Transparent background was requested. If true alpha is unavailable, keep the subject isolated on a clean removable background; do not draw a checkerboard pattern."
        )
    lines.extend(
        [
            "",
            "Use the built-in Codex image generation tool for exactly one output image.",
            "Do not render these settings as visible text unless the primary request explicitly asks for text.",
        ]
    )
    return "\n".join(lines)


def build_slide_image_generation_prompt(
    payload: Mapping[str, Any],
    *,
    variant_index: int = 1,
    variant_count: int = 1,
) -> str:
    manifest = build_slide_image_generation_manifest(
        payload,
        variant_index=variant_index,
        variant_count=variant_count,
    )
    grounding = manifest["grounding"]
    has_sources = any(
        _has_content(grounding.get(key))
        for key in ("sources", "research_context", "claims", "data_sources")
    )
    grounding_status = (
        "SOURCE-GROUNDED: use the supplied source context as factual authority."
        if has_sources
        else "NO VERIFIED SOURCES PROVIDED: do not add new facts beyond the primary request."
    )

    lines = [
        "DrawAI high-quality PPT slide image request.",
        "",
        "Goal:",
        "- Produce one premium slide-ready bitmap image for a PPT workflow.",
        "- The image may be non-editable; it will later pass through DrawAI's editable reconstruction pipeline.",
        "- Optimize for visual quality, factual restraint, clear structure, OCR-readability, and downstream segmentation.",
        "- Default rendering mode is baked_text: render complete title, body copy, diagrams, charts, and visual structure directly inside the final bitmap.",
        "- Do not trade away presentation beauty for caution: keep the slide visually memorable, premium, and finished while staying source-grounded.",
        "",
        "Mandatory tool behavior:",
        "- Use the built-in Codex image generation tool for exactly one output image.",
        "- Do not call OpenAI Images API manually.",
        "- Do not use shell commands, web search, MCP tools, or multi-agent delegation in this image-generation turn.",
        "",
        "Primary request:",
        manifest["primary_request"],
        "",
        "Generation settings:",
        *[f"- {key}: {value}" for key, value in manifest["generation_settings"].items()],
        "",
        "Slide intent:",
        *_render_mapping_lines(manifest["slide_intent"]),
        "",
        "Design direction:",
        *_render_mapping_lines(manifest["design"]),
        "",
        "Template effect card:",
        *_template_card_lines(manifest["design"].get("template_card")),
        "",
        "Reference execution mode:",
        *_reference_execution_lines(manifest["reference_execution"]),
        "",
        "PPT image strategy and selected template:",
        _compact_json(manifest["strategy"], limit=8000),
        "",
        "Spec-guided design lock:",
        *_spec_guided_lines(manifest["spec_guided"]),
        "",
        "Selected template enforcement:",
        *_selected_template_lines(manifest["strategy"]),
        "",
        "Baked text directive:",
        f"- rendering_mode: {manifest['strategy']['rendering_mode']}",
        "- Generate the final PPT slide as a complete bitmap with readable in-image text.",
        "- Do not leave empty placeholders assuming a later text overlay pass.",
        "- DrawAI may reconstruct/edit the generated bitmap later, but this generation step must already be useful to read as a slide.",
        "",
        "Grounding policy:",
        f"- {grounding_status}",
        f"- source_policy: {grounding['source_policy']}",
        "- If a real-world detail is not supplied in the source context, keep it generic or omit it.",
        "- Do not infer a scientific domain from words like Nature-style, academic, or high-impact; those describe publication polish unless a domain is explicitly supplied.",
        "- Do not invent statistics, citations, dates, product UI, maps, charts, rankings, logos, or named-entity details.",
        "- Generated decorative visuals may be imaginative, but factual content must stay source-bound.",
        "",
        "Source-grounded context:",
        _compact_json(grounding, limit=5000),
        "",
        "Visible text and body-copy policy:",
        f"- {manifest['text']['policy']}",
        f"- text_density: {manifest['text']['text_density']}",
        *_language_policy_lines(manifest["text"]),
        "- Match the language of the primary request and supplied visible text. If the request is Chinese, render Chinese slide copy; preserve model names, APIs, metrics, and technical terms in English only where they are proper nouns or standard terms.",
        "- Do not translate Chinese headings, bullets, or speaker-facing explanations into English unless the user explicitly requests English.",
        "- Required visible text is a floor, not a ceiling: do not reduce the slide to labels and layout only.",
        "- Minimum useful text: a clear title, subtitle or takeaway when supplied, readable section/module labels, and 3-6 concise explanatory bullets or callouts.",
        "- For medium-density technical PPT pages, use normal slide copy density: enough text to explain the idea at a glance while preserving spacing.",
        "- Body copy may paraphrase only the primary request, supplied claims, visible_text_blocks, and source-grounded context.",
        "- Avoid tiny text, gibberish, pseudo-writing, watermark-like marks, signatures, random labels, and unreadable micro-captions.",
        "- If exact long text rendering is risky, split it into shorter readable bullets or callouts; never leave the slide textless.",
        "REQUIRED_VISIBLE_TEXT:",
        _compact_json(manifest["text"]["locked_visible_text"], limit=2200),
        "EXACT_TEXT_DO_NOT_TRANSLATE:",
        _compact_json(manifest["text"]["exact_visible_text"], limit=1200),
        "VISIBLE_TEXT_BLOCKS:",
        _compact_json(manifest["text"]["visible_text_blocks"], limit=2200),
        "PERMITTED_BODY_COPY_SOURCES:",
        _compact_json(
            {
                "primary_request": manifest["primary_request"],
                "claims": grounding.get("claims"),
                "research_context": grounding.get("research_context"),
            },
            limit=3200,
        ),
        "",
        "Quality gates to satisfy visually:",
        *_render_list_lines(manifest["quality_gates"]),
        "",
        "Visual richness guidance:",
        *_render_list_lines(_visual_richness_guidance(payload)),
        "",
        "Composition guidance:",
        *_render_list_lines(_composition_guidance(payload)),
        "",
        "DrawAI post-processing constraints:",
        *_render_list_lines(manifest["drawai_postprocess"]),
        "",
        "Variant instruction:",
        _variant_instruction(variant_index, variant_count),
        "",
        "Negative constraints:",
        _compact_json(manifest["inclusion"], limit=3000),
        "",
        'Final response contract: reply only {"generated": true}.',
    ]
    return "\n".join(line for line in lines if line is not None).strip()


def build_slide_image_prompt_comparison(
    payload: Mapping[str, Any],
    *,
    variant_index: int = 1,
    variant_count: int = 1,
) -> dict[str, Any]:
    legacy_prompt = build_legacy_workbench_image_generation_prompt(
        payload,
        variant_index=variant_index,
        variant_count=variant_count,
    )
    improved_prompt = build_slide_image_generation_prompt(
        payload,
        variant_index=variant_index,
        variant_count=variant_count,
    )
    manifest = build_slide_image_generation_manifest(
        payload,
        variant_index=variant_index,
        variant_count=variant_count,
    )
    return {
        "schema": "drawai.slide_image_prompt_comparison.v1",
        "variant": {"index": variant_index, "count": variant_count},
        "legacy_prompt": legacy_prompt,
        "improved_prompt": improved_prompt,
        "improved_manifest": manifest,
        "diff_summary": _prompt_diff_summary(legacy_prompt, improved_prompt),
    }


def _quality_gates(payload: Mapping[str, Any]) -> list[str]:
    supplied = _string_list(payload.get("quality_gates"))
    defaults = [
        "single coherent slide, not a collage of unrelated panels",
        "use the full 16:9 canvas with balanced density; avoid large accidental empty regions",
        "presentation polish should be comparable to a manually designed high-impact academic overview slide",
        "contains enough readable explanatory text to be useful as a PPT slide: title, takeaway, section labels, and concise body copy",
        "must not look like a layout-only wireframe or unlabeled component scaffold",
        "clear focal hierarchy with generous margins and no overcrowding",
        "high contrast between foreground and background",
        "no overlapping text or visual elements",
        "no cropped important content near slide edges",
        "no unreadable microtext, mojibake, pseudo-letters, or random captions",
        "data-like visuals must be source-grounded or deliberately abstract",
        "when verified metrics are unavailable, use unlabeled abstract mini-charts or schematic indicators rather than fake numbers",
        "professional typography and spacing suitable for a 16:9 presentation",
    ]
    return _dedupe([*supplied, *defaults])


def _template_card_manifest(payload: Mapping[str, Any]) -> Any:
    supplied = payload.get("template_card")
    if _has_content(supplied):
        return _jsonish(supplied)
    card_id = _clean_text(payload.get("template_card_id"))
    if not card_id:
        return None
    try:
        card = get_template_card(card_id)
    except KeyError:
        return {"id": card_id, "status": "unknown"}
    return {
        "id": card.get("id"),
        "name": card.get("name"),
        "category": card.get("category"),
        "scenario_tags": card.get("scenario_tags"),
        "visual_tags": card.get("visual_tags"),
        "prompt_recipe": card.get("prompt_recipe"),
        "visual_keywords": card.get("visual_keywords"),
        "palette": card.get("palette"),
        "layout_archetypes": card.get("layout_archetypes"),
        "text_density": card.get("text_density"),
        "source_policy": card.get("source_policy"),
        "tests": card.get("tests"),
        "provenance": card.get("provenance"),
    }


def _template_card_lines(card: Any) -> list[str]:
    if not _has_content(card):
        return ["- none: use the selected strategy template only."]
    if not isinstance(card, Mapping):
        return [f"- {card}"]
    if card.get("status") == "unknown":
        return [f"- requested_template_card_id: {card.get('id')}", "- status: unknown card id; fall back to selected strategy template."]
    lines = [
        f"- Card: {card.get('id')} / {card.get('name')}",
        f"- Category: {card.get('category')}",
        f"- Scenario tags: {_compact_json(card.get('scenario_tags'), limit=900)}",
        f"- Visual tags: {_compact_json(card.get('visual_tags'), limit=900)}",
        f"- Prompt recipe: {card.get('prompt_recipe')}",
        f"- Visual keywords: {_compact_json(card.get('visual_keywords'), limit=900)}",
        f"- Palette: {_compact_json(card.get('palette'), limit=900)}",
        f"- Layout archetypes: {_compact_json(card.get('layout_archetypes'), limit=900)}",
        f"- Text density: {card.get('text_density')}",
        f"- Source policy: {card.get('source_policy')}",
        f"- Provenance: {_compact_json(card.get('provenance'), limit=1200)}",
    ]
    tests = card.get("tests")
    if _has_content(tests):
        lines.append(f"- Card QA tests: {_compact_json(tests, limit=900)}")
    return [line for line in lines if _has_content(line)]


def _reference_execution_lines(reference_execution: Mapping[str, Any]) -> list[str]:
    mode = _clean_text(reference_execution.get("reference_mode")) or "auto"
    lines = [f"- reference_mode: {mode}"]
    tokens = reference_execution.get("reference_image_tokens")
    if _has_content(tokens):
        lines.append(f"- reference_image_tokens: {_compact_json(tokens, limit=1600)}")
    if mode == "reference_tokens_only":
        lines.append("- Use only extracted/declared reference tokens; the reference bitmap is not supplied as image input in this generation call.")
    elif mode == "reference_context":
        lines.append("- A reference bitmap may be supplied as visual context; use it for style/layout, not literal content preservation.")
    elif mode in {"reference_edit_low", "reference_edit_high"}:
        lines.append("- A reference bitmap may be supplied through the edit path; follow the requested reference strength.")
    elif mode == "content_edit":
        lines.append("- The supplied image is the actual edit target; preserve unchanged regions unless instructed otherwise.")
    return lines


def _spec_guided_manifest(payload: Mapping[str, Any]) -> dict[str, Any]:
    enabled = _bool_value(payload.get("spec_guided_enabled"))
    fields = {
        "template_spec": _jsonish(payload.get("template_spec")),
        "slot_schema": _jsonish(payload.get("slot_schema")),
        "reference_style_spec": _jsonish(payload.get("reference_style_spec")),
        "design_tokens": _jsonish(payload.get("design_tokens")),
        "spec_lock": _jsonish(payload.get("spec_lock")),
        "reference_roles": _jsonish(payload.get("reference_roles")),
    }
    if not enabled:
        enabled = any(_has_content(value) for value in fields.values())
    return {
        "enabled": enabled,
        **fields,
    }


def _spec_guided_lines(spec_guided: Mapping[str, Any]) -> list[str]:
    if not spec_guided.get("enabled"):
        return ["- disabled: use the selected prompt template strategy only."]
    lines = [
        "- enabled: treat supplied template/spec/slot/design-lock fields as stronger structural guidance than generic style words.",
        "- This is still PPT image generation, not PPTX output; render one complete baked-text bitmap slide.",
        "- Respect slot roles, page type, canvas ratio, palette tokens, typography cues, and reference roles when present.",
    ]
    for key in (
        "template_spec",
        "slot_schema",
        "reference_style_spec",
        "design_tokens",
        "spec_lock",
        "reference_roles",
    ):
        value = spec_guided.get(key)
        if _has_content(value):
            lines.append(f"- {key}: {_compact_json(value, limit=2200)}")
    return lines


def _locked_visible_text(payload: Mapping[str, Any]) -> Any:
    values: list[str] = []
    for key in ("title", "subtitle", "key_message"):
        text = _clean_text(payload.get(key))
        if text:
            values.append(text)
    values.extend(_string_list(payload.get("locked_visible_text") or payload.get("visible_text")))
    blocks = payload.get("visible_text_blocks")
    if isinstance(blocks, Mapping):
        for key in ("title", "subtitle", "takeaway"):
            text = _clean_text(blocks.get(key))
            if text:
                values.append(text)
        labels = blocks.get("labels")
        values.extend(_string_list(labels))
    elif isinstance(blocks, Sequence) and not isinstance(blocks, (bytes, bytearray, str)):
        for block in blocks:
            if isinstance(block, Mapping):
                values.extend(_string_list(block.get("text") or block.get("label")))
            else:
                values.extend(_string_list(block))
    return _dedupe(values)


def _exact_visible_text(payload: Mapping[str, Any]) -> list[str]:
    values = _string_list(payload.get("exact_visible_text") or payload.get("do_not_translate_visible_text"))
    if payload.get("locked_visible_text_exact") is True:
        values.extend(_string_list(payload.get("locked_visible_text") or payload.get("visible_text")))
    return _dedupe(values)


def _requested_language(payload: Mapping[str, Any]) -> str:
    explicit = _clean_text(payload.get("language") or payload.get("output_language")).lower()
    if explicit in {"zh", "zh-cn", "chinese", "中文", "简体中文"}:
        return "zh"
    if explicit in {"en", "english", "英文"}:
        return "en"
    text = " ".join(
        _clean_text(payload.get(key))
        for key in ("prompt", "title", "subtitle", "key_message", "style", "tone")
        if _clean_text(payload.get(key))
    )
    return "zh" if _contains_cjk(text) else "auto"


def _contains_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def _language_policy_lines(text_policy: Mapping[str, Any]) -> list[str]:
    if text_policy.get("requested_language") != "zh":
        return ["- main_language: follow the user's request and supplied text."]
    return [
        "- main_language: Chinese. Use Chinese for the main title, subtitle, section headers, bullets, callouts, captions, warnings, and takeaway text.",
        "- Keep English only for model/product/API names, acronyms, code identifiers, benchmark names, and standard technical terms where Chinese translation would be unnatural.",
        "- Do not render generic English section headings. Use Chinese headings such as 核心结论、来源质量、威胁模型、记忆分层、状态表示、技术栈、风险边界.",
        "- If REQUIRED_VISIBLE_TEXT contains English generic descriptors, treat them as semantic hints and render concise Chinese equivalents unless they also appear in EXACT_TEXT_DO_NOT_TRANSLATE.",
        "- A mixed Chinese/English technical slide is acceptable only when the Chinese text remains dominant and explanatory.",
    ]


def _drawai_postprocess(payload: Mapping[str, Any]) -> list[str]:
    supplied = _string_list(payload.get("drawai_postprocess"))
    defaults = [
        "use crisp object boundaries and clean layer separation where possible",
        "keep text regions high contrast and OCR-friendly if text appears",
        "avoid textured noise directly behind text or chart labels",
        "avoid excessive glow, blur, transparency, and low-contrast gradients over semantic content",
        "prefer simple geometric regions for tables, charts, cards, arrows, and panels",
        "leave enough spacing for DrawAI to segment text, icons, charts, and decorative assets",
    ]
    return _dedupe([*supplied, *defaults])


def _composition_guidance(payload: Mapping[str, Any]) -> list[str]:
    supplied = _string_list(payload.get("composition_guidance"))
    defaults = [
        "compose like a finished slide, not a sparse wireframe or UI mockup",
        "use a rich overview structure when appropriate: title plus subtitle, left input bookend, central pipeline, right output bookend, and compact bottom overview band",
        "for academic or technical topics, prefer a left-to-right pipeline, method/results overview, or evidence hierarchy",
        "use abstract, source-safe visual evidence when exact datasets are unavailable: synthetic figure thumbnails, module cards, flow arrows, masks, crop examples, schematic charts without numeric labels",
        "maintain Swiss/editorial discipline: aligned columns, consistent spacing, restrained color accents, and clear typographic scale",
        "keep every visible label purposeful; do not add decorative pseudo-text to fill space",
        "make the result feel publication/presentation ready at first glance while preserving factual restraint",
    ]
    return _dedupe([*supplied, *defaults])


def _visual_richness_guidance(payload: Mapping[str, Any]) -> list[str]:
    supplied = _string_list(payload.get("visual_richness_guidance"))
    defaults = [
        "do not reduce the slide to five plain cards; add source-safe visual substance inside and around the pipeline",
        "synthetic thumbnails are allowed when they are clearly generic: microscopy-like panels, figure crops, mask overlays, charts, asset swatches, vector nodes, and editable-canvas previews",
        "unlabeled charts may show abstract trends, bars, or scatter patterns for visual metaphor only; do not add axis labels, numeric values, legends with unsupported method names, or performance claims",
        "avoid domain-specific imagery such as biomedical cells, molecules, organs, maps, hardware, company products, or clinical scenes unless provided by the source context",
        "for generic AI/pipeline topics, use neutral paper-figure thumbnails, document crops, layout grids, chart placeholders, mask overlays, UI-free vector diagrams, and editable-canvas previews",
        "show process transformation visually: raw figure -> detected text/regions -> separated assets -> native shapes -> editable slide output",
        "use varied panel scale, subtle shadows, thin rules, and accent color blocks to create depth and a finished editorial look",
        "include enough small visual detail to feel premium, while keeping semantic modules cleanly separable for DrawAI",
        "if a subtitle is useful, derive it only from the primary request and avoid unsupported claims",
    ]
    return _dedupe([*supplied, *defaults])


def _variant_instruction(variant_index: int, variant_count: int) -> str:
    if variant_count <= 1:
        return "Create the strongest single version; do not make a collage or compare alternatives inside the image."
    return (
        f"This is variant {variant_index} of {variant_count}. Keep the same factual content and constraints, "
        "but vary composition, visual metaphor, color balance, or spatial hierarchy. Do not make a collage."
    )


def _prompt_diff_summary(legacy_prompt: str, improved_prompt: str) -> dict[str, Any]:
    improved_checks = {
        "source_grounding": "SOURCE-GROUNDED" in improved_prompt or "NO VERIFIED SOURCES PROVIDED" in improved_prompt,
        "anti_hallucination": "Do not invent" in improved_prompt,
        "required_visible_text": "REQUIRED_VISIBLE_TEXT" in improved_prompt,
        "ocr_text_policy": "OCR" in improved_prompt or "mojibake" in improved_prompt,
        "drawai_postprocess": "DrawAI post-processing constraints" in improved_prompt,
        "quality_gates": "Quality gates" in improved_prompt,
    }
    legacy_checks = {
        "source_grounding": "SOURCE-GROUNDED" in legacy_prompt,
        "anti_hallucination": "Do not invent" in legacy_prompt,
        "required_visible_text": "REQUIRED_VISIBLE_TEXT" in legacy_prompt,
        "ocr_text_policy": "OCR" in legacy_prompt or "mojibake" in legacy_prompt,
        "drawai_postprocess": "DrawAI post-processing constraints" in legacy_prompt,
        "quality_gates": "Quality gates" in legacy_prompt,
    }
    return {
        "legacy_chars": len(legacy_prompt),
        "improved_chars": len(improved_prompt),
        "added_controls": [
            key for key, enabled in improved_checks.items() if enabled and not legacy_checks.get(key)
        ],
        "legacy_controls": [key for key, enabled in legacy_checks.items() if enabled],
        "improved_controls": [key for key, enabled in improved_checks.items() if enabled],
    }


def _render_mapping_lines(value: Mapping[str, Any]) -> list[str]:
    lines: list[str] = []
    for key, item in value.items():
        if _has_content(item):
            lines.append(f"- {key}: {_compact_json(item, limit=1400) if not isinstance(item, str) else item}")
    return lines or ["- default: premium, modern, presentation-ready visual design"]


def _render_list_lines(values: Sequence[str]) -> list[str]:
    return [f"- {item}" for item in values if item]


def _selected_template_lines(strategy: Mapping[str, Any]) -> list[str]:
    selected = strategy.get("selected_template")
    if not isinstance(selected, Mapping):
        return ["- Use the selected deck visual system consistently."]
    lines = [
        f"- Template: {selected.get('id')} / {selected.get('name')}",
        f"- Category: {selected.get('category')}",
        f"- Visual direction: {selected.get('visual_direction')}",
        f"- Palette: {selected.get('palette')}",
        f"- Typography: {selected.get('typography')}",
        f"- Text density: {selected.get('text_density')}",
        f"- Image policy: {selected.get('image_policy')}",
        f"- Data policy: {selected.get('data_policy')}",
    ]
    template_enforcement = selected.get("template_enforcement")
    if _has_content(template_enforcement):
        lines.append(f"- Template-specific enforcement: {template_enforcement}")
    style_safety = selected.get("style_safety")
    if _has_content(style_safety):
        lines.append(f"- Style safety: {style_safety}")
    ip_safety = selected.get("ip_safety")
    if _has_content(ip_safety) and _ip_safety_enabled(strategy.get("ip_safety_mode")):
        lines.append(f"- IP safety: {ip_safety}")
    archetypes = selected.get("layout_archetypes")
    if _has_content(archetypes):
        lines.append(f"- Layout archetypes to choose from: {_compact_json(archetypes, limit=900)}")
    qa_gates = selected.get("qa_gates")
    if _has_content(qa_gates):
        lines.append(f"- Template QA gates: {_compact_json(qa_gates, limit=900)}")
    template_id = str(selected.get("id") or "")
    if template_id == "consulting_report":
        lines.append(
            "- Consulting enforcement: lead with an executive takeaway and use a 2x2 matrix, issue tree, decision table, or executive dashboard; do not default to a technical pipeline."
        )
    elif template_id == "academic_technical":
        lines.append(
            "- Academic-technical enforcement: build a premium method/evidence figure with a strong visual center, not a plain sequence of equal cards."
        )
    elif template_id == "data_journalism":
        lines.append(
            "- Data-journalism enforcement: make the chart/evidence panel the visual anchor; if no numeric data is supplied, use clearly abstract unlabeled chart shapes."
        )
    elif template_id == "product_launch":
        lines.append(
            "- Product-launch enforcement: use a keynote-like hero capability, roadmap, module map, or before/after workflow; avoid a dense research-paper layout."
        )
    elif template_id == "dark_tech":
        lines.append(
            "- Dark-tech enforcement: use a premium dark keynote or frontier-lab technical look with luminous diagrams, high-contrast readable text, and no pseudo-code filler."
        )
    elif template_id == "blue_robot_learning":
        if _ip_safety_enabled(strategy.get("ip_safety_mode")):
            lines.append(
                "- Blue-robot IP-safe enforcement: blue-white palette, rounded original educational robot, future gadgets, Japanese children's manga panel feel, no copyrighted character, no exact Doraemon likeness, no trademarked symbols."
            )
        else:
            lines.append(
                "- Blue-robot visual enforcement: blue-white palette, rounded educational robot mood, future gadgets, and Japanese children's manga panel rhythm."
            )
    return [line for line in lines if _has_content(line)]


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [_clean_text(value)] if _clean_text(value) else []
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        return [_clean_text(item) for item in value if _clean_text(item)]
    return [_compact_json(value, limit=1000)]


def _jsonish(value: Any) -> Any:
    if isinstance(value, str):
        return _clean_text(value)
    if isinstance(value, Mapping):
        return {str(key): _jsonish(item) for key, item in value.items() if _has_content(item)}
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        return [_jsonish(item) for item in value if _has_content(item)]
    return value


def _compact_json(value: Any, *, limit: int) -> str:
    if not _has_content(value):
        return "none"
    text = json.dumps(value, ensure_ascii=False, sort_keys=True) if not isinstance(value, str) else value
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _int_value(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "on", "enabled"}


def _ip_safety_enabled(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "on", "enabled", "generic", "strict"}


def _has_content(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Mapping):
        return any(_has_content(item) for item in value.values())
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        return any(_has_content(item) for item in value)
    return True


def _dedupe(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        key = value.lower().strip()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(value)
    return deduped
