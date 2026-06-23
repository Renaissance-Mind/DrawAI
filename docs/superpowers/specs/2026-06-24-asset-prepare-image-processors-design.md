# Asset Prepare Image Processor Test Design

Date: 2026-06-24

Status: approved design, awaiting written-spec review

## Goal

Support Workbench testing for PageSpec image generation and image editing processors on
`/Users/chunqiu/Downloads/飞书20260608-121226.jpg`.

The test path should keep `asset_prepare` as the PageSpec processor executor. It should not use
`asset_processors`, should not call SVG Compose, and should not build PPTX. The point of this
workflow is to verify whether PageSpec Refine chooses the right `build.processing_type` values and
whether processed raster results can be placed back into the original element boxes.

## Scope

Allowed changes:

- Processor operation descriptions, especially when `image_generate` and `image_edit` should or
  should not be selected.
- Image generation and image editing processor execution code.
- The PageSpec `asset_prepare` path required to call those processors and write their results back
  to PageSpec materialization.
- A dedicated built-in Workbench DAG for processor testing.
- Focused tests for processor selection configuration, PageSpec materialization, parallel
  processing, and workbench template exposure.

Out of scope:

- SVG Compose behavior.
- PPT export behavior.
- The v2 `asset_processors` node path.
- Mock visual content in the user-facing verification run.
- Broad unrelated refactors.

## Workflow

Add a built-in Workbench template for processor testing:

```text
Input
  -> SAM Parse
  -> PageSpec Fuse
  -> PageSpec Refine
  -> Asset Prepare
  -> Output

Input
  -> OCR Parse
  -> PageSpec Fuse
```

The `PageSpec Refine` node exposes these processing operations:

```text
no_process
crop
crop_nobg
image_generate
image_edit
```

The template deliberately omits `svg_compose` and `svg_to_ppt`. `Asset Prepare` becomes the final
processor-test node. Its output is a materialized PageSpec plus a deterministic placement preview
that puts processed assets back at each element's `box_px`.

## Asset Prepare Behavior

`asset_prepare` should execute each PageSpec element according to `build.processing_type`:

- `no_process`, `svg_self_draw`, and `chart_rebuild_reserved`: remove stale materialization and keep
  the element structural.
- `crop`: crop source pixels and preserve local background.
- `crop_nobg`: crop source pixels and remove the background when RMBG is enabled.
- `image_generate`: generate a new raster asset from element semantics, box dimensions, local page
  context, and the current prompt settings.
- `image_edit`: crop the element from the source image, then edit it with a prompt that preserves
  the original composition, colors, aspect, and visual role unless the prompt explicitly asks for a
  change.

For processed raster elements, `asset_prepare` writes:

```text
element.materialization.status = "ok"
element.materialization.processor = "asset_prepare"
element.materialization.processing_type = <processing_type>
element.materialization.outputs.active.path = <relative png path>
```

The active output path must be relative to the PageSpec bundle so existing PageSpec asset utilities
can compute SVG hrefs and the Workbench viewer can inspect the result.

## Parallel Processing

`asset_prepare` should process independent elements concurrently with a bounded worker pool. Results
must be written back in deterministic element order so PageSpec output remains stable.

Failure behavior should expose real errors. Do not silently fall back from `image_generate` or
`image_edit` to `crop`. If a processor fails, the element's materialization should show the failure
and the node should fail unless the existing PageSpec asset contract already allows a recoverable
status.

## Processor Prompts

Refine operation descriptions should make these distinctions clear:

- Use `image_edit` when the source crop already contains the desired object but needs cleanup,
  redraw, deblurring, background adjustment, or style harmonization.
- Use `image_generate` when the element represents an image-like idea that is missing, too abstract,
  too low quality to crop, or should be synthesized from semantic context rather than copied.
- Use `crop` when source pixels are already acceptable and local background should remain attached.
- Use `crop_nobg` only for separable foreground objects with clear boundaries.
- Use `no_process` for text, lines, simple shapes, charts, layout structure, and anything that should
  remain structural.

The generation/edit prompts should include the element bbox size, object role, nearby labels or
metadata when available, and a clear placement instruction: produce a clean transparent or
background-compatible raster asset that will be scaled back into the exact original box.

## Providers

The same test image must be verified with two provider paths:

- Apimart through the configured `openai_images_api` processor driver.
- Codex built-in image generation and image editing.

If `image_edit` does not yet support `openai_images_api`, register that driver only after adding an
executable edit adapter. It should share the Images API materialization and response parsing
behavior with generation where the upstream API supports edits.

## Expected Visual Outcome

After Refine, most image-like elements in Representation column 2, Representation column 3,
Representation column 4, and the Future representations row should be assigned to
`image_generate` or `image_edit`.

Not every element should be generated or edited. Some elements should remain `no_process`,
`crop`, or `crop_nobg` when those choices better match the source image.

After `asset_prepare`, generated or edited elements should be pasted back into their original
positions and should remain broadly consistent with the source: same conceptual object, similar
layout role, similar color/shape language, and no large unintended background blocks.

## Verification

Automated verification:

- Focused Python tests for PageSpec `asset_prepare` materializing `image_generate` and `image_edit`.
- A concurrency test proving multiple independent image elements can process in parallel.
- Tests confirming `image_edit` can be configured with an executable Images API preset driver when
  implemented.
- Workbench template tests confirming the processor-test DAG is available and omits SVG Compose.

Manual/live verification:

- Start backend and frontend Workbench from this worktree.
- Use Chrome, not headless browser automation, to create/run processor-test batches for the provided
  image.
- Run one batch with Apimart settings and one batch with Codex built-in image processor settings.
- Inspect Refine and Asset Prepare node viewers. Confirm processor distribution and placement
  quality against the acceptance criteria above.
