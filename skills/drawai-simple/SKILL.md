---
name: drawai-simple
description: Reconstruct a single raster image as a standalone, visually faithful, structurally editable SVG using the DrawAI Simple Baseline protocol.
---

## Image-to-Editable-SVG Reconstruction Protocol

### Role

Given a single source raster image, reconstruct it as a standalone, visually faithful, and structurally editable SVG document.

### Objective

Create an SVG whose rendered appearance closely matches the source image while preserving semantic structure and editability wherever practical. The task must be completed by inspecting the supplied image and writing and executing local code within the run directory. Do not merely describe a solution, return a declarative scene specification, or stop at an intermediate representation.

### Permitted Operations

- Use the selected agent/model as the only model for visual understanding, reasoning, and implementation.
- Write local scripts and intermediate files required to construct, render, and validate the SVG.
- Use native SVG elements, including text, groups, paths, rectangles, circles, ellipses, polygons, polylines, lines, gradients, clipping paths, masks, and filters when appropriate.
- Use deterministic crops from the source image for complex photos, illustrations, textures, screenshots, icons, logos, or other regions that cannot be faithfully reconstructed as vector objects.

## Reconstruction Procedure

1. Inspect the complete source image and infer its canvas dimensions, visual hierarchy, major regions, text, spatial relationships, colors, and reusable graphical structures.
2. Decompose the slide into semantic components. Distinguish content that should be represented as editable SVG text and vector primitives from complex raster content that should be preserved through localized source crops.
3. Set the SVG `viewBox` to match the source dimensions or an exactly proportional coordinate system, then reconstruct the slide in visual stacking order: background, large regions, structural elements, text, diagrams, and localized raster assets.
4. Preserve text as SVG `<text>` and `<tspan>` elements when it is readable. Preserve grouping, alignment, line breaks, emphasis, and approximate font metrics.
5. When local deterministic SVG rendering is available, render `output/result.svg` to `output/preview.png`, compare it with the source image, and revise discrepancies in element presence, layout, text placement, scale, color, style, stacking order, and clarity.
6. Generate the final SVG only after checking that it is valid, standalone, renderable, and visually faithful.

### Fidelity Criteria

- Preserve the source slide's aspect ratio, composition, alignment, spacing, typography hierarchy, colors, borders, and relative element sizes as closely as practical.
- Use semantic SVG primitives rather than converting all content into undifferentiated paths.
- Represent simple shapes, connectors, arrows, tables, charts, diagrams, and icons as native editable SVG elements whenever possible.
- Prefer a localized deterministic crop over an inaccurate vector simplification for complex raster artwork.
- Do not use the whole source image, or a near-full-page crop, as an SVG `<image>` background.
- Avoid omitted elements, unintended overlaps, clipped text, malformed paths, broken asset references, and generic placeholder graphics.

### Output Contract

Produce the following files:

- `output/result.svg`: the final standalone SVG reconstruction.
- `output/notes.md`: a concise record of the reconstruction strategy, native SVG elements, source crops, and known limitations.
- `output/preview.png`: a deterministic local rendering of the final SVG when a renderer is available.
- `output/agent-result.json`: the completion sentinel, written last.

`output/result.svg` must contain `xmlns="http://www.w3.org/2000/svg"`, a valid `viewBox` matching the source aspect ratio, and a closing `</svg>` element.

`output/agent-result.json` must contain `success: true` and `final: true` and follow this structure:

```json
{
  "success": true,
  "final": true,
  "svg": "output/result.svg",
  "preview": "output/preview.png",
  "notes": "output/notes.md",
  "used_tools": ["svg"],
  "used_source_crops": true,
  "used_full_page_background": false,
  "errors": []
}
```

## Runtime Constraints

- Use the selected Agent and model as the only source of visual understanding and reasoning.
- Do not call another LLM, OCR service, vision API, image generation API, or web service.
- Keep all generated files and deterministic source crops inside the current run directory.
- Write output/agent-result.json last, only after validating the final SVG and its declared artifacts.
