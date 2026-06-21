# Slide Image Template Library Final Architecture

## Direction Update

This feature is no longer treated as a small prompt-only adapter or a narrow `template_id` registry extension. The target product is a complete PPT image generation workbench:

1. User enters a PPT type, topic, source material, or reference image.
2. DrawAI recommends multiple template/style cards.
3. User can inspect gallery cards with thumbnails, example outputs, prompt recipes, reference images, risk notes, and source policies.
4. User selects one or more directions and generates high-quality slide images.
5. Generated images can be sent into DrawAI's editable reconstruction pipeline.
6. The system keeps template outputs reusable and comparable through saved samples, manifests, records, and evaluation reports.

The lightweight `src/drawai/slide_template_library.py` seed remains useful as migration scaffolding, but it is not the final architecture.

## Product Goals

- Make template selection visual instead of a hidden dropdown.
- Let users compare different design directions before paying the full generation cost.
- Support scenario templates and visual styles separately, then compose them.
- Support style/reference images as first-class inputs, not text-only path hints.
- Preserve Chinese visible text quality and avoid textless layout-only images.
- Keep factuality controlled through source modes and claim ledgers.
- Protect IP and brand safety, especially for manga/cartoon/reference-driven styles.
- Persist enough artifacts for reuse: prompt, payload, references, generated output, contact sheet, quality notes, and downstream DrawAI case links.

## Reference Summary

- `awesome-notebookLM-prompts`: strong source of reusable visual directions such as Modern Newspaper, Sharp-edged Minimalism, Yellow x Black Editorial, Manga, Magazine, Digital/Neo/Pop, Studio/Premium, and Sports.
- `NotebookLM-Custom-Prompts`: useful for source-to-story strategy: executive summary, report analysis, information extraction, viewpoint checks, and evidence-grounded synthesis.
- `bananaX` infographic gallery: useful as the model for thumbnail galleries, categories, sample pages, and evaluation dimensions.
- `AAAAAAAJ/slides` / `PROMPTS.md`: useful as a style prompt studio with Retro Pop Art, Minimalist Clean, Cyberpunk Neon, Neo-Brutalism, Acid Graphics Y2K, Swiss International, Dark Editorial, Design Blueprint, Bento Grid, Aurora UI, Glassmorphism, and Frutiger Aero.
- `nano-banana-ppt.md`: useful for high-frequency PPT scenes such as courseware, company report, pitch deck, data analysis, weekly retrospective, and sales deck. It also reinforces continuity: keep lighting/color/style stable across a deck while varying the business subject.

## Core Data Model

Final model should split scenario, visual style, references, and generated examples.

### `SlideScenario`

```json
{
  "id": "enterprise_knowledge_agent",
  "name": "Enterprise Knowledge Agent",
  "category": "tech_ai_product",
  "intent_tags": ["ai_agent", "knowledge_base", "workflow", "implementation"],
  "audience_tags": ["executive", "product", "technical"],
  "source_requirements": ["prompt_only", "source_grounded", "data_driven"],
  "story_recipe": "Problem -> workflow -> governance -> rollout",
  "recommended_layouts": ["workflow_map", "capability_dashboard", "roadmap"],
  "default_text_density": "medium-high",
  "factual_risk": "medium"
}
```

### `VisualStyle`

```json
{
  "id": "swiss_international",
  "name": "Swiss International",
  "category": "business_technical",
  "visual_tags": ["swiss", "grid", "modernist"],
  "prompt_recipe": "Strict modular grid, rational asymmetry, strong typography.",
  "visual_keywords": ["Swiss International", "modular grid"],
  "palette": ["white", "black", "red accent"],
  "layout_archetypes": ["numbered grid sections", "evidence columns"],
  "text_density_range": ["medium", "high"],
  "reference_image_ids": ["ref_swiss_001"],
  "sample_output_ids": ["sample_swiss_agent_001"],
  "ip_safety": "",
  "source_policy": "Keep unsourced data abstract.",
  "quality_tests": ["grid alignment visible", "Chinese text dominant"]
}
```

### `TemplateCard`

`TemplateCard` is what the user sees. It can be composed from one scenario plus one visual style.

```json
{
  "id": "enterprise_agent__swiss_international",
  "scenario_id": "enterprise_knowledge_agent",
  "visual_style_id": "swiss_international",
  "name": "企业知识库 Agent / Swiss Grid",
  "gallery_thumbnail": "assets/template-gallery/enterprise_agent__swiss/thumb.jpg",
  "sample_outputs": ["outputs/template-gallery/.../sample.png"],
  "prompt_preview": "User-readable prompt summary.",
  "recommended_for": ["技术汇报", "管理层解释", "落地路线"],
  "risks": ["无来源时不能写 ROI 或准确率"],
  "source_modes": ["prompt_only", "source_grounded", "data_driven"],
  "reference_policy": "Style/layout only; do not copy logos or protected content.",
  "quality_score": {
    "readability": 0.0,
    "style_match": 0.0,
    "deck_reuse": 0.0
  }
}
```

### `ReferenceImage`

```json
{
  "id": "ref_aurora_001",
  "path": "assets/template-gallery/references/aurora-ui-001.png",
  "role": "style_reference",
  "source": "internal curated sample",
  "license": "internal_or_permitted",
  "allowed_use": "style_layout_only",
  "forbidden_copy": ["logos", "trademarks", "characters", "visible text", "exact UI"],
  "dominant_palette": ["navy", "cyan", "violet"],
  "layout_notes": "Layered panels, soft glow, dashboard rhythm"
}
```

### `GenerationRun`

```json
{
  "id": "gen_20260620_001",
  "template_card_id": "enterprise_agent__aurora_ui",
  "scenario_id": "enterprise_knowledge_agent",
  "visual_style_id": "aurora_ui",
  "topic": "AI Agent 工作流如何落地企业知识库",
  "source_mode": "prompt_only",
  "reference_image_ids": ["ref_aurora_001"],
  "operation": "generate_or_edit",
  "prompt_path": "outputs/.../prompt.txt",
  "payload_path": "outputs/.../payload.json",
  "image_path": "outputs/.../aurora_ui.png",
  "contact_sheet_path": "outputs/.../contact_sheet.jpg",
  "drawai_batch_id": "optional",
  "quality_notes": []
}
```

## Backend Architecture

### Storage

Add a persistent template-gallery root:

- `assets/slide_template_gallery/manifest.json`
- `assets/slide_template_gallery/references/`
- `assets/slide_template_gallery/thumbnails/`
- `assets/slide_template_gallery/samples/`
- `outputs/slide_template_gallery_runs/`

The manifest should be versioned and normalized at load time. Curated reference images and sample outputs should be content-addressed or include sha256 metadata.

### Python Modules

Proposed modules:

- `src/drawai/slide_template_library.py`
  - Current seed module.
  - Should evolve into manifest loader, validator, scorer, and prompt composer.
- `src/drawai/slide_template_models.py`
  - Typed dataclasses or pydantic models for `SlideScenario`, `VisualStyle`, `TemplateCard`, `ReferenceImage`, `GenerationRun`.
- `src/drawai/slide_template_recommender.py`
  - Recommendation/ranking from user topic, source mode, audience, deck type, language, and optional references.
- `src/drawai/slide_template_prompt_builder.py`
  - Compose scenario story recipe, visual style recipe, source policy, text policy, and reference policy.
- `src/drawai/slide_template_gallery_store.py`
  - Save samples, thumbnails, contact sheets, run records, and quality notes.
- `src/drawai/slide_template_runner.py`
  - Generate preview variants, run reference-image edit when needed, and optionally create DrawAI cases.

### API Endpoints

Add Workbench API endpoints:

- `GET /api/slide-templates/cards`
  - Query: `category`, `scenario`, `visual_style`, `source_mode`, `q`.
  - Returns gallery cards with thumbnails and sample output URLs.
- `POST /api/slide-templates/recommend`
  - Body: topic, deck type, audience, language, source mode, source/data/reference availability.
  - Returns ranked cards and the reason for each recommendation.
- `GET /api/slide-templates/cards/{card_id}`
  - Returns full metadata, prompt recipe, references, sample outputs, risks, tests.
- `POST /api/slide-templates/preview-prompts`
  - Builds prompt previews for selected cards without image generation.
- `POST /api/slide-templates/generate-previews`
  - Generates 2-4 selected preview images, saves records/contact sheet.
- `POST /api/slide-templates/reference-images`
  - Uploads or registers reference images for style/layout use.
- `POST /api/slide-templates/generate-with-reference`
  - Uses Codex `invoke_codex_python_sdk_image_edit` / `LocalImageInput` when a reference image should actively condition generation.
- `POST /api/slide-templates/runs/{run_id}/create-drawai-batch`
  - Sends selected generated images into the existing DrawAI reconstruction flow.

### Reference Image Execution

There are two paths:

1. Text-to-image without actual image input:
   - Use card style recipe and source policy.
   - No reference image is sent.
2. Reference-conditioned generation/edit:
   - Use `invoke_codex_python_sdk_image_edit(source_image_path=..., prompt=...)`.
   - The supplied local image is a style/layout reference or source image.
   - Prompt must forbid copying protected content and visible text from the reference.

Current backend already has `/api/imagegen/edits` and `invoke_codex_python_sdk_image_edit`. The product gap is exposing references in template-gallery UI and routing card generation through the edit path when a selected card/reference requires it.

## Frontend Architecture

Add a new gallery-driven workflow inside Workbench image generation:

### Left Panel

- PPT topic / type input.
- Deck type selector: report, pitch, course, weekly, sales, research, data story.
- Source mode selector: prompt-only, source-grounded, data-driven, web-research-ready, brand/reference-driven.
- Optional audience/tone/language fields.
- Reference image upload/drop area.

### Center Gallery

Template/style cards:

- Thumbnail.
- Name.
- Category.
- Tags.
- Best-for scenarios.
- Palette chips.
- Text density.
- Safety/source badges.
- Sample output preview.
- "Generate preview" and "Use this style" actions.

### Right Panel

- Selected card detail.
- Prompt recipe preview.
- Reference image policy.
- Example outputs.
- Generated previews/contact sheet.
- Button to create DrawAI batch from selected generated images.

### UX Rules

- Show recommendations after topic input, not only after generation.
- Let users compare at least 3 directions side by side.
- Make reference images explicit: "style reference", "source image to edit", "brand guide", "sample output".
- Do not hide safety policy; show short user-facing warnings for IP-risk styles.
- Do not force one visual style as globally best.

## Experiment Strategy

Experiments must demonstrate product-visible behavior:

1. Gallery experiment:
   - Generate thumbnails/contact sheet for 8-12 cards using one topic.
   - Save prompt, payload, record, and sample image per card.
2. Recommendation experiment:
   - Use 5 topic categories: business strategy, AI product, data report, courseware, sales deck.
   - Save recommended cards and reasons.
3. Reference image experiment:
   - Select one reference image.
   - Run true Codex image edit using `LocalImageInput`.
   - Compare text-only style recipe vs reference-conditioned generation.
4. DrawAI handoff experiment:
   - Take selected generated images.
   - Create a Workbench batch/case from them.
   - Verify they can enter asset analysis and reconstruction.
5. Deck continuity experiment:
   - Pick one selected template card.
   - Generate 5-10 consecutive pages with locked visual style, palette, text policy, and layout rhythm.

Evaluation should produce:

- `contact_sheet.jpg`
- `summary.json`
- `summary.md`
- per-case prompt/payload/record
- image dimensions/hash
- qualitative notes: readability, Chinese quality, style match, reference adherence, factual safety, DrawAI segmentation suitability.

## Current Experiment Result

The first seed experiment produced:

- Output directory: `outputs/codex_slide_template_library_experiment`
- Contact sheet: `outputs/codex_slide_template_library_experiment/contact_sheet.jpg`
- Prompt-only cards: `modern_newspaper`, `corporate_strategy_cinematic`, `light_glassmorphism`
- Real generated cards: `swiss_international`, `aurora_ui`, `manga_safe_learning`
- All real generated images succeeded.
- Generated image size observed: `1672x941`, approximately 16:9 but lower than requested `2048x1152`.
- The visible output contact sheet shows Chinese text is mostly readable in the real images.
- `manga_safe_learning` used an original learning/cartoon composition rather than directly copying Doraemon or another protected character.
- The current reference case is still prompt-only: `light_glassmorphism` includes a reference image path and policy, but did not yet send `LocalImageInput`.

## Migration Plan

### Phase 1: Product Gallery Foundation

Deliverables:

- Formal manifest-backed card library.
- Backend API to list, recommend, and inspect cards.
- Frontend gallery cards with thumbnails, tags, categories, sample outputs, and prompt preview.
- Seed sample outputs from current experiment.
- Tests for API, manifest validation, recommendation, and prompt builder.

Acceptance:

- User can enter a PPT topic and see ranked template cards.
- User can click a card and inspect sample output/prompt recipe/reference policy.
- No image generation required to browse the gallery.

### Phase 2: Preview Generation Loop

Deliverables:

- API to generate previews for selected cards.
- Runner that saves per-card prompts, payloads, images, contact sheet, and report.
- UI that shows generated previews side by side.
- Reuse previous outputs when available.

Acceptance:

- User can select 2-4 cards and generate comparable preview images.
- Output records are reusable and visible in the gallery.

### Phase 3: First-Class Reference Images

Deliverables:

- Reference image upload/register endpoint.
- UI role labeling: style reference, source image, brand guide, sample output.
- Runner path that calls `invoke_codex_python_sdk_image_edit` with `LocalImageInput`.
- Safety policy visible in UI and enforced in prompt.

Acceptance:

- User can choose a reference image and generate a style-adapted slide.
- The prompt and record prove that the local image was actually passed to Codex edit, not only written as text.

### Phase 4: DrawAI Reconstruction Handoff

Deliverables:

- Create Workbench batch from selected generated previews.
- Store link between `GenerationRun` and `CaseRecord`.
- Run analysis/reconstruction smoke test on selected generated images.

Acceptance:

- A selected generated PPT image appears as a DrawAI case and can enter the existing editable reconstruction pipeline.

### Phase 5: Deck Continuity And Evaluation

Deliverables:

- Multi-page deck generation runner from one selected card.
- Style lock: palette, typography, card rhythm, density, reference policy, source policy.
- Quality comparison report across pages.

Acceptance:

- 5-10 pages from the same deck look coherent and remain readable.
- Summary report identifies text, style, factuality, and continuity issues.

## First Implementation Step

Start with Phase 1:

1. Convert the current seed card data into a manifest-backed library.
2. Add Workbench API endpoints:
   - `GET /api/slide-templates/cards`
   - `POST /api/slide-templates/recommend`
   - `GET /api/slide-templates/cards/{card_id}`
   - `POST /api/slide-templates/preview-prompts`
3. Add a gallery section to `ImageGenStudio.tsx` that consumes those APIs and shows cards.
4. Register current experiment images as sample outputs for `swiss_international`, `aurora_ui`, and `manga_safe_learning`.
5. Add tests for API responses and UI-independent card/recommendation behavior.

After this, Phase 2 should add true preview generation from selected cards.
