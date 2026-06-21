# PPT-master Alignment Plan

## Why This Pivot Exists

The previous DrawAI slide-image work proved that Codex image generation can use `LocalImageInput` and that prompt registries can cover many visual styles. That is still not enough for the user goal. The PPT-master route is materially different: it treats a `.pptx` deck as a native editable template, extracts a slide library, prepares a fill plan, checks fit, and writes content back into native PowerPoint shapes/tables/charts instead of flattening every slide into one bitmap.

Primary references:

- PPT-master README: real editable PowerPoint, not image-based output, and support for filling an existing PPTX template.
- PPT-master `SKILL.md`: PPTX route boundary, `pptx_intake.py`, `source_profile.json`, `identity.json`, `slide_library.json`, `design_spec.md`, and `spec_lock.md`.
- PPT-master `template-fill-pptx.md`: `slide_library.json` is a layout inventory; `fill_plan.json` is the single execution contract; `check-plan` validates capacity before `apply`; `apply` clones selected source pages and edits native OOXML.

## Current DrawAI Gap

DrawAI now has real reference-image edit for Codex and a small `templates/slide_image/*/template.json` asset directory. The remaining gap is native PPTX understanding and filling:

- No PPTX template intake.
- No Slide Master/layout inventory.
- No stable slot IDs or fill plan.
- No fit/capacity check.
- No native editable PPTX output from a user template.
- Reference image style is a single source path, not typed roles such as layout/style/color/typography/content reference.

## First-Phase Data Flow

```text
template.pptx
  -> ppt_template_intake.py
  -> template_spec.json
       schema: drawai.ppt_template_spec.v1
       slide_size, theme, layouts, slots, tables, charts, pictures, role_guess
       design_tokens, spec_lock, limitations

reference image
  -> reference_style_spec.json
       schema: drawai.reference_style_spec.v1
       reference_roles: layout/style/color/typography/content
       design_tokens, slot_schema, spec_lock

template_spec + reference_style_spec + user_topic
  -> template_reference_edit_payload.json
  -> fill_plan.json
  -> output_demo.pptx
```

## First-Phase Interfaces

`src/drawai/ppt_template_intake.py`

- `intake_ppt_template(pptx_path) -> dict`: parse slide size, theme colors/fonts, per-slide slots, native table/chart/picture inventory, layout role guesses, and spec lock hints.
- `build_slot_schema_preview(template_spec) -> dict`: compact slot/role schema for UI or review.
- `build_prisma_reference_style_spec(...) -> dict`: express the verified PRISMA reference image as typed reference roles.
- `build_template_reference_payload(...) -> dict`: produce an edit payload with explicit provenance from PPT template, reference image, and user topic.
- `create_minimal_fill_plan(...) -> dict`: first fill-plan contract for existing text slots.
- `apply_minimal_fill_plan(...) -> dict`: replace existing native PPTX text slots and save an editable demo deck.

`scripts/run_ppt_template_intake_demo.py`

- Builds a demo PPTX when no user template is available.
- Runs intake and writes `outputs/ppt_template_intake_demo/template_spec.json`.
- Writes PRISMA `reference_style_spec.json`.
- Writes showcase artifacts under `outputs/ppt_master_alignment_showcase`.
- Produces a minimal editable `output_demo.pptx`.

## What This Is Not Yet

This is not full PPT-master parity. It does not yet clone/reorder arbitrary template pages, preserve all animation XML, edit chart workbook data, expand Slide Master inheritance, render thumbnails, or run automated overflow correction. It is the first executable contract that turns “template/reference support” into real PPTX intake plus native editable output.

## Next Implementation Phase

1. Replace the demo fill with a real `fill_plan` API that can select/reuse/reorder source pages.
2. Expand Slide Master parsing and layout inheritance.
3. Add native table and chart data writers.
4. Add a fit checker using geometry, font metrics, CJK width, and slot role.
5. Connect Workbench UI to upload/select `.pptx` templates and browse extracted slot previews.
6. Feed `output_demo.pptx` or filled decks into DrawAI's editable reconstruction/review pipeline only when image-based generation is still needed.
