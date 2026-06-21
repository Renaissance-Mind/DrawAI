# DrawAI PPT Image Master Plan

## Positioning

This plan keeps the current `v1_source_grounded_chinese` behavior and adds a higher-level strategy layer for PPT image generation. The goal is not to find one universal best-looking prompt. The system should provide multiple high-quality directions for different user needs, while preserving factual control and DrawAI downstream editability.

Default rendering mode is `baked_text`: the image model generates a complete PPT slide bitmap with title, body copy, diagrams, charts, and layout already visible. DrawAI reconstruction/editing handles downstream correction and editability.

## Not a direct copy of ppt-master

`ppt-master` is used as workflow inspiration: source planning, template selection, image-source policy, and quality gates. DrawAI keeps its own image-first constraints:

- Codex built-in image generation tool exactly once per image.
- Do not call OpenAI Images API manually in Codex mode.
- Baked text by default, not deterministic text overlay.
- Chinese-first language policy.
- Source-grounded claim control.
- Multi-style first-slide candidates.
- DrawAI post-processing constraints for later editable reconstruction.
- Generated-image QA focused on text presence, mojibake, factual safety, template fit, and deck continuity.

## Strategy Pipeline

1. Intent router
   Identify deck type, audience, factual risk, expected visual genre, and source/data availability.

2. Source planner
   Choose one source mode:
   - `prompt_only`: only user prompt is available; no invented facts, numbers, rankings, or citations.
   - `source_grounded`: claims/sources/research context are supplied; concrete facts must be traceable.
   - `data_driven`: structured data is supplied; charts and numbers must follow the data.
   - `brand_template`: template, brand, or style references are supplied; match them without inventing logos.
   - `web_research`: current facts are needed; research must happen before image generation.

3. Template selector
   Select a visual system based on intent, source mode, and user preference. A user-specified template overrides auto selection.

4. First-slide candidate stage
   For new decks, generate three first-slide directions by default. The user selects one before full deck expansion.

5. Baked-text image generation
   Generate the full slide image directly, including readable Chinese title/body copy and source-grounded diagrams.

6. Continuity lock
   After a candidate is selected, lock template id, palette, typography, layout archetypes, density, image policy, data policy, and language policy across the deck.

7. QA gate
   Check missing text, wrong language, mojibake, pseudo-writing, unsupported facts, fake data, template mismatch, and multi-slide inconsistency.

## Template Registry

Implemented template ids:

- `academic_technical`: research talks, model architecture, methods, scientific results.
- `consulting_report`: business strategy, executive summary, decision memos.
- `data_journalism`: chart-led evidence stories and data reports.
- `product_launch`: feature launches, roadmap, model/product capability pages.
- `magazine_editorial`: public-facing explainers and story-led decks.
- `teaching_explainer`: courseware, onboarding, step-by-step explanations.
- `dark_tech`: frontier AI, infra, cybersecurity, developer platform decks.
- `government_report`: formal policy or institutional reports.
- `notebooklm_briefing`: document-to-slides, reading notes, source-backed briefings.
- `creative_zine`: expressive creative decks and campaign concepts.

## Current Implementation

- Strategy registry and router: `src/drawai/slide_image_strategy.py`
- Prompt integration: `src/drawai/slide_image_prompt.py`
- Workbench TS fields: `apps/workbench/src/types.ts`
- Experiment CLI knobs:
  - `--strategy`
  - `--template`
  - `--source-mode`
  - `--style-candidate-index`
  - `--style-candidate-count`

## Next Execution Step

Use the Kimi prompt to generate three first-slide candidates:

1. `academic_technical`
2. `consulting_report`
3. `product_launch`

The selected direction becomes the continuity lock for a 5-10 page deck.
