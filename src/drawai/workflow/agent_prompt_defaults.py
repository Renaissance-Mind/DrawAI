from __future__ import annotations

RUN0_ELEMENT_REFINE_TASK = """DrawAI asset post-processing and element-plans task.

We are performing an image vectorization task: a bitmap image will eventually be transformed into an editable representation. The whole process has three parts:
- Asset parsing: divide the image into independent assets. Each asset may be text, an icon, table, frame, arrow, and so on.
- Asset post-processing: refine the pre-parsed assets.
- Editable reconstruction: combine assets and finish the final visual result.

Some assets should become editable forms, such as text, frames, arrows, and simple vector graphics. Some assets should instead be cropped from the original image and pasted back into their original positions. The parser/OCR/fusion outputs are evidence, not truth. Execute the second stage, asset post-processing, and produce refined DrawAI element plans that later asset materialization and SVG generation will consume.

Required evidence:
- Original image from the connected input, when available.
- Current DrawAI asset-plan overlay or parser/fusion visualization, when connected.
- Compact candidate table or element candidate JSON.
- Machine-readable request / element candidates / element plans from connected parser or fusion nodes.
- OCR text boxes when visible text content, grouping, or bbox needs confirmation.
- Mask preview sheet and individual mask previews when mask candidates exist.

Task 1: refine the connected candidates into minimum independent assets.
Each output element should be the smallest independent visual part, such as one icon, image, frame, arrow, text line, chart mark, chart block, or diagram component.
- Split a candidate when one box contains multiple independent parts, for example several icons/images inside one block.
- Add a new element when an asset is visible in the original image but not covered by any current candidate.
- Adjust the bbox when the current position is wrong or misses part of a component.
- Remove or merge a candidate only when it is clearly duplicate, noise, or wholly represented by another retained element.
- Preserve traceability. For unchanged or adjusted elements, keep source_candidate_ids pointing to the original candidate ID. For split elements, use stable IDs like B012_S01 with source_candidate_ids ["B012"]. For newly added elements, use stable IDs like N001 with source_candidate_ids [].
- Bboxes must be visual extents in image pixels. For straight lines or dividers, give at least 1 pixel of thickness so width and height are positive.
- Pay close attention to coordinate accuracy and whether each bbox tightly contains the corresponding asset.
- For geometry_kind="mask", use mask_preview PNGs and the mask preview sheet as visual evidence. Do not adjust or resize the mask region; preserve its bbox/geometry when keeping it. Remove or merge a mask candidate only when it is clearly duplicate or noise. Do not read or rely on raw mask files.

Task 2: repeat a bounded visualization/refinement loop until the asset parsing quality is good enough, all elements are reasonable assets, and bbox coordinates are accurate. Run at most 3 iterations.
1. Write the current element-plans JSON for the iteration to reports/element_plans_codex/refine_iteration_<N>.json, where <N> starts at 1.
2. Run assets_visualization.py with the original image and that iteration JSON, using color-mode action and label-mode id_type.
3. Inspect reports/element_plans_codex/assets_visualization_iteration_<N>.png.
4. Correct Task 1 results from the visualization. You may add assets, remove assets, split assets, merge accidental duplicates, and adjust bbox coordinates. One iteration may change any number of assets.
5. Repeat until the assets are correct or 3 iterations have completed.
6. Save the final refined element-plans JSON to the declared output path, normally output/elements.json.

Task 3: classify every final retained output element into exactly one processing intent.
- svg_self_draw: use editable SVG primitives/text/paths directly. Use this for text, arrows, boxes, lines, charts, simple geometric diagrams, and visually simple icons that can be faithfully redrawn.
- crop: use a precise source-image crop with local background preserved. Use this for screenshots, photographs, dense texture, heatmaps, complex small raster icons, or visual details whose background is coupled with the object.
- crop_nobg: use a precise crop after background removal/transparent subject extraction. Use this when the foreground object is separable and should sit over reconstructed SVG background.

Important classification and coverage rules:
- Treat SAM/OCR/current asset plan as evidence, not truth. You may disagree with current_pipeline_method if the image supports it.
- Output only retained final element plans. Do not output removal_records, strategy_summary, refinement_summary, categories, notes, or old element_analysis fields.
- Do not skip real visual assets. Every retained or merged original candidate should appear in source_candidate_ids on at least one output element. Clearly duplicate/noise candidates may be omitted.
- The element_type field must be a concrete DrawAI element type: text, icon, picture, table, chart, diagram, arrow, frame, grid, symbol, content_box, or unknown. For newly added elements, do not use a meta type such as added_asset.
- New IDs are allowed only for split or added refined elements. Keep IDs short and stable.
- If uncertain, choose the most faithful final-source strategy and mark confidence as low or medium.
- After the visualization loop, complete classification in one pass. Write the final JSON file first. Keep change_reason concise.

The final JSON must use format drawai.element_plans.v1 and contain:
- top-level schema="drawai.element_plans.v1"
- elements: array of retained element plans only

Each element plan must contain:
- schema="drawai.element_plan.v1"
- element_id: stable short ID
- source_candidate_ids: list of source candidate IDs; [] only for newly added visual assets
- element_type: text|icon|picture|table|chart|diagram|arrow|frame|grid|symbol|content_box|unknown
- bbox: [x, y, width, height] in image pixels, with positive width and height
- geometry: object; for ordinary boxes use {"kind":"bbox","bbox":[x,y,width,height],"coordinate_system":"figure_image_pixels"}
- z_order: integer, lower values behind higher values
- confidence: low|medium|high
- processing_intent: {"object_type": element_type or a more specific object name, "processing_type": svg_self_draw|crop|crop_nobg, "parameters": {}}
- review_status: agent_refined
- created_by_stage: refine_elements
- change_reason: concise explanation of keep/split/merge/add/bbox/source decision

The declared output JSON file is the source of truth."""

RUN0_ELEMENT_REFINE_CONSTRAINTS = (
    "Use only the connected input files listed in this prompt and explicitly declared built-in script files.",
    "Do not render final SVG/PPT and do not modify repository code. This node only refines/classifies assets.",
    "Do not use MCP tools, apps, web search, memories, skills, hooks, or multi-agent delegation.",
    "Do not print full request JSON to the terminal or logs; start from compact candidate tables and read exact details only when needed.",
    "Output only drawai.element_plans.v1 JSON; do not output codex element analysis, summaries, notes, or removal records.",
    "Write the declared output files exactly, in UTF-8 JSON or markdown according to the output declaration.",
)

SVG_GENERATION_TASK = """IMAGE VECTORIZATION TASK
Goal: convert one bitmap figure into an editable, PPT-stable SVG.

OVERALL DRAWAI PIPELINE
The full DrawAI task is split into three conceptual stages:
1. Asset parsing: split the bitmap figure into independent visual assets, such as text, icons, tables, frames, arrows, chart marks, screenshots, pictures, diagram components, formulas, axes, panels, and other meaningful regions.
2. Asset post-processing: refine the pre-parsed assets, adjust bboxes, split/merge elements, add missing elements, and decide the source strategy for each asset: svg_self_draw, crop, or crop_nobg.
3. Image editabilization: reconstruct the whole figure as an editable SVG/PPT representation by combining editable SVG primitives/text with allowed raster crop assets.

The current Agent node executes stage 3 only. Do not redo stage 1 or stage 2. Use their outputs as evidence, especially the refined element/source analysis and the asset manifest. Your job is to create one complete first-pass SVG, then refine it for up to 3 rounds inside this same Agent run.

EXECUTION MODEL
- The DrawAI runner prepares the node work directory and connected input files. You must read those files yourself.
- You must create intermediate SVGs/renders, inspect them, revise them, and finish with the declared final SVG and logs.
- Run1 and every refine round may use allowed local raster image hrefs from the refined asset manifest when the asset source is crop or crop_nobg.

AVAILABLE FILES AND READING LOGIC
Primary files for this stage:
- Original/current reference image. Use it as the visual truth for layout, color, text placement, arrows, icons, images, tables, axes, and spacing.
- Refined element/source analysis JSON. Use it as the main structured plan for refined asset boundaries and source decisions: svg_self_draw, crop, or crop_nobg.
- Asset manifest JSON. Use it as the authoritative list of local raster image hrefs that may appear in the SVG.
- Native backfill request JSON, when connected. Use it only for listed candidates when the existing manifest does not provide a faithful crop/no-background source. It is not permission to crop arbitrary regions.
- SVG validator script or validator command, when connected or declared by the run.

Auxiliary files to read only when needed:
- OCR boxes JSON when visible text content, text grouping, or text bbox needs confirmation.
- Template/reference image only as a secondary comparison for early layout, never as higher-priority visual truth than the original image.
- SVG template IR JSON only as a low-priority editable-geometry hint when the refined plan or original image leaves an ambiguity.
- Layout IR JSON as a legacy detection artifact. Do not rebuild the task around old layout IR boxes; use it only as a fallback debug hint if a refined element is missing or unclear.
- Attempt request context only for operational paths or optional response instructions.

Reading sequence:
1. Start from the original image and refined element/source analysis. These two sources define what the stage is trying to reproduce.
2. Before inserting any raster image href, verify it against the asset manifest or native_backfill_request.
3. Read OCR only when text details need help.
4. Read SVG template IR or layout IR only as fallback hints. They must not override visible evidence or the refined asset plan.
5. Keep request JSON compact in reasoning. Do not print full JSON files to terminal or logs.

SOURCE POLICY
- svg_self_draw: use editable SVG primitives/text for text, formulas, arrows, frames, tables, axes, borders, simple charts, simple icons, and simple diagram components.
- crop: use an exact local crop image for screenshots, photos, dense raster texture, heatmaps, complex small icons, or details that are not worth or not possible to faithfully redraw as SVG.
- crop_nobg: use a no-background crop image when the foreground object is separable and should sit on top of reconstructed editable SVG background.
- Use refined source labels as the default. Override only when the original image and current render clearly show that another source strategy is more faithful. Record the reason in the iteration log.
- Insert only hrefs listed in asset_manifest or native_backfill_request. Do not invent image paths, external URLs, file:// URLs, absolute paths, or base64 images.
- Do not use raster images to cover text, arrows, panels, tables, formulas, axes, or other structure that should remain editable.

RUN1 / COMPLETE FIRST PASS
- Write semantic_0.svg.
- It must be a complete whole-figure SVG, not a placeholder map, skeleton, gray-box map, or list of asset boxes.
- Cover the whole canvas.
- Use SVG/text for svg_self_draw elements.
- Use manifest image hrefs for crop/crop_nobg elements when available.
- Preserve refined bboxes unless visible evidence shows they need adjustment.
- Keep major objects separated and editable where appropriate.
- Avoid overfitting tiny details before the whole figure layout is coherent.
- Render/validate semantic_0.svg to rendered_0.png and validation_report_0.json using the validator command.
- Record Run1 in iteration_log.md and iteration_log.jsonl, including what was created, obvious issues, and any crop/crop_nobg regions that still need source decisions.

REFINE LOOP / MAX 3 ROUNDS
At the start of each round:
1. Use the latest SVG as input.
2. Render it.
3. Compare the render against the original image.
4. First inspect the whole figure, then inspect local regions.
5. Decide the highest-impact fixes yourself.

In each round, consider:
- Whole-figure layout mismatch: canvas scale, panel positions, major blocks, relative spacing, z-order.
- Text mismatch: missing text, wrong content, wrong grouping, wrong size, wrong baseline, wrong color.
- Connector/arrow mismatch: missing arrows, wrong direction, wrong endpoint, wrong arrowhead, wrong layering.
- Shape/table/axis mismatch: wrong borders, grids, ticks, legends, blocks, fills, strokes.
- Asset source mismatch: crop/crop_nobg region redrawn badly, missing image href, wrong crop/no-background choice, image placed at the wrong bbox.
- Editability regression: text/arrow/table/panel became raster when it should be editable.
- PPT stability issue: unsupported SVG feature, unsafe href, invalid image reference, bad structure for SVG-to-PPT conversion.
- Validator issue: parse error, blank render, asset_href_not_in_manifest, blocked feature, viewBox mismatch, or failed report.

Allowed refine actions:
- Edit SVG shapes, text, groups, arrow geometry, fills, strokes, transforms, z-order, and object IDs.
- Add or remove SVG elements when the original image supports it.
- Insert allowed manifest/backfill image hrefs for crop/crop_nobg regions.
- Replace an unfaithful SVG approximation with an allowed crop/crop_nobg image.
- Replace a crop with editable SVG only when the region is visually simple and the SVG version is faithful.
- Adjust manifest image placement/size to match refined bboxes or visible evidence.
- Use OCR to correct text.
- Use Template IR or layout IR only as fallback geometry hints.

Round outputs:
- Round 1 writes semantic_1.svg, rendered_1.png, validation_report_1.json.
- Round 2 writes semantic_2.svg, rendered_2.png, validation_report_2.json.
- Round 3 writes semantic_3.svg, rendered_3.png, validation_report_3.json.

After each round, write to iteration_log.md and iteration_log.jsonl: round number, input SVG, output SVG/render/report, issues found, changes made, asset source changes if any, validation status, and stop or continue decision.

Stop before 3 rounds only if all of these are true:
- The whole-figure render is perfectly close to the original, or no further improvement is achievable under the current constraints.
- Text, arrows, panels, tables, axes, images, and icons all have correct style, position, and attributes.
- crop/crop_nobg regions use the right allowed image source, or any exception is explicitly logged.
- Editable structures remain editable.
- The latest validator report is status=\"ok\".
- Another round would likely not make the figure better.

FINALIZATION
- Choose the latest acceptable SVG as the final result.
- Write the accepted final SVG as semantic.svg in the attempt directory and to the declared output path.
- Render/validate semantic.svg to rendered.png and validation_report_final.json.
- Copy semantic_0.svg/rendered_0.png to stable template SVG/render paths when those outputs are declared.
- Finish only after validation_report_final.json reports status=\"ok\".

OVERALL SVG/PPT PROFILE
Target the DrawAI Scientific SVG Profile v1 for editable PPT conversion. Treat the input as an editable scientific structure diagram, not as a bitmap tracing task. Infer the visual language: background, major modules, arrows/connectors, annotations, legends, stroke weights, rounded corners, palette, gradients, typography, and flow direction.
- Use rect for panels/modules/boxes, circle/ellipse for simple nodes/badges/dots, line/polyline for straight or orthogonal connectors, path only when curves/brackets/custom geometry are really needed, polygon for arrowheads or simple closed geometry, text/tspan for all visible text and formulas, and g for stable grouping.
- Use defs only for simple reusable markers or supported gradients. Prefer solid fills for core semantic objects.
- Use image elements only for explicit local raster assets from the refined asset manifest.
- Do not output CSS style blocks, filters, masks, clipPath, foreignObject, textPath, pattern fills, base64 images, external image URLs, absolute paths, symbol, or use.
- Prefer direct SVG presentation attributes over CSS classes for fill, stroke, font-size, opacity, and dash styling.
- Use stable semantic groups with ids prefixed module-, flow-, annotation-, legend-, panel-, connector-, label-, node-, image-, decorative-, or background-.
- For numbered/lettered badges, use a simple circle/ellipse plus centered editable text.
- Prefer orthogonal connector geometry when the source uses horizontal/vertical flows. Route connectors to module edges and avoid crossing text or panel centers.
- Filled or thick block arrows should be one closed shape. Thin connectors should keep shaft and arrowhead together after SVG-to-PPT conversion.
- Render connector arrows after background panels/modules and before raster image assets.
- Preserve editable text with text/tspan. Represent formulas with Unicode math characters and tspan superscript/subscript instead of LaTeX source or formula screenshots.
- Mark non-editable raster assets with data-pb-editable=\"false\" and editable vectors/text with data-pb-editable=\"true\".

FINAL CHECK BEFORE ENDING THIS RUN
- semantic_0.svg exists and has render/validation output.
- 0-3 refine rounds were run. If 0 rounds were run, explain why Run1 already met the strict stop condition.
- semantic.svg and rendered.png are the accepted final outputs.
- validation_report_final.json is status=\"ok\".
- iteration_log.md and iteration_log.jsonl explain every round and stop/continue decision.
- Keep the final chat response short; files are the source of truth."""

SVG_GENERATION_CONSTRAINTS = (
    "Use only connected input files listed in this prompt and explicitly declared built-in script files.",
    "Do not redo parsing or asset-source analysis; consume the connected refined elements and asset manifest as evidence.",
    "Do not use MCP tools, apps, web search, memories, skills, hooks, or multi-agent delegation.",
    "Do not invent image hrefs, external URLs, file:// URLs, absolute paths, or base64 images.",
    "Do not rasterize panels, arrows, text, formulas, grids, tables, axes, or whole diagram structure.",
    "Write the declared SVG/render/log outputs exactly and keep the final chat response short.",
)

CUSTOM_AGENT_TASK = """Use the connected input files as context and produce exactly the output files declared by this node configuration.

This is a configurable DrawAI Agent node. The node editor controls the task, input inclusion, input descriptions, output declarations, provider, model/profile/reasoning settings, timeout, and runtime constraints. Read the connected files listed in the prompt, follow the declared output formats, and write only the declared outputs."""

CUSTOM_AGENT_CONSTRAINTS = (
    "Treat every connected input file as explicit node context.",
    "Honor the configured output declarations over node defaults.",
    "Write only the declared output paths inside this node work directory.",
)
