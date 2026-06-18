# DrawAI v2 Robust Pipeline Design

Date: 2026-06-18

Status: approved design for implementation planning

Branch: `caopu/drawai-v2-robust-pipeline-design`

## Goal

Replace the current DrawAI main path with a more robust v2 pipeline for element parsing, element refinement, asset processing, and package-based reuse.

The v2 path should make parser outputs, fusion decisions, agent refinement, processor execution, and asset results explicit and versioned. A user may only see the final PNG/SVG/PPTX, but DrawAI must retain a complete run-level package and asset-level packages so future edits can continue from structured provenance instead of from opaque output files.

## Confirmed Product Decisions

- v2 directly replaces the main pipeline path.
- Existing legacy run outputs remain visible and downloadable, but are read-only.
- A legacy run can create a new v2 run from its original source image when the source image is available.
- Legacy artifacts cannot be reprocessed, re-exported, migrated into v2 packages, or mixed with v2 asset packages.
- Agent refinement is configurable, but product defaults keep it enabled.
- If default Agent refinement fails, the run fails explicitly. DrawAI does not silently continue with lower-confidence output.
- Types use a core enum plus extension registry.
- Fusion uses built-in priority/NMS rules plus pluggable rule hooks.
- Packages have two levels: a run-level entry package and per-asset subpackages.
- First implementation includes current crop, crop with background removal, SVG self-draw, image generation, and image editing processors.
- Chart Agent support is reserved as a formal processor slot and capability, but chart rebuild does not need to execute in the first implementation.
- Failure handling is staged: parse, fusion, and refine are run-critical; individual asset processors can fail at asset level; export fails by default if any required asset failed unless partial export is explicitly enabled.
- First implementation covers Core, CLI, API, and Workbench asset package/processor UI.

## Current Repo Context

The current public stage surface is:

```text
prepare
detect_structure
detect_text
assemble_boxir
asset_plan
asset_analyze
asset_materialize
svg
export
```

The current implementation already has useful building blocks:

- `drawai.core.DagRunner`, `StageSpec`, `RunContext`, and `ProviderRef` provide execution contracts.
- `drawai.stages.file_backed` provides file-backed stage definitions and artifact registration.
- `drawai.pipeline` records stage status and stage I/O manifests.
- `drawai.public_stages` exposes coarse product stages.
- `drawai.workbench.assets` already models editable asset drafts, approval, processing, and compatibility with the current `element_analysis.json` shape.
- Current parser and processor behavior is spread across SAM3 raw regions, OCR boxes, BoxIR merge, Codex run0 element analysis, asset policy, RMBG materialization, and SVG generation.

v2 should reuse the runner, stage status, artifact store, and Workbench foundations, but should replace the main authority model. The v2 authority should be `drawai_package.json` plus per-asset packages, not `box_ir.json`, `element_analysis.json`, or `asset_manifest.json`.

## Pipeline Architecture

The v2 main path is:

```text
prepare
parse_elements
fuse_elements
refine_elements
plan_assets
process_assets
compose_svg
export
package_run
```

### Stage Semantics

`prepare`
: Normalize or copy the input image, write source metadata, and establish the run root.

`parse_elements`
: Run one or more parser providers and write parser-specific raw outputs plus normalized `ElementCandidate` records.

`fuse_elements`
: Combine candidates with deterministic priority/NMS rules and registered fusion hooks. Write `ElementPlan` draft records and `fusion_trace.json`.

`refine_elements`
: Optionally run an Agent refiner. Product defaults enable Codex refinement. The refiner corrects element positions, sizes, types, and processing intent. It cannot directly create final asset output. It writes final `ElementPlan` records and `refine_trace.json`.

`plan_assets`
: Convert final `ElementPlan.processing_intent` into explicit processor plans. Validate that every selected processor is available or intentionally unsupported.

`process_assets`
: Execute processors per element and write asset subpackages. Processor failures are isolated to asset packages.

`compose_svg`
: Build the semantic SVG from final element plans, active asset results, and editable payloads.

`export`
: Export SVG/PPTX/PNG deliverables. By default, export refuses to proceed when required asset packages are failed or unsupported.

`package_run`
: Write or refresh the run-level package index with all stage outputs, package references, provenance, and compatibility metadata.

## Data Model

### Run Layout

Recommended v2 run layout:

```text
drawai_package.json
inputs/
  original.png
  figure.png
  source_metadata.json
elements/
  E001/
    element.json
    asset_package.json
    source.png
    results/
      R001/
        result.json
        output.png
  E002/
    element.json
    asset_package.json
reports/
  parser_outputs/
  fusion_trace.json
  refine_trace.json
  processor_trace.jsonl
  stage_status.json
  stage_io_manifest.json
svg/
  semantic.svg
  rendered.png
exports/
  semantic.pptx
```

Existing output paths may remain as compatibility exports during transition, but v2 code should treat the package files as authoritative.

### ElementCandidate

`ElementCandidate` is the normalized output of any parser.

Required fields:

- `schema`: `drawai.element_candidate.v1`
- `candidate_id`
- `source_parser`
- `source_parser_version`
- `element_type`
- `bbox`
- `geometry`
- `confidence`
- `z_hint`
- `text`
- `evidence_files`
- `provenance`
- `raw_ref`

Rules:

- Coordinates use normalized figure-image pixels.
- `geometry.kind` may be `bbox`, `mask`, or `polygon`.
- Parser-specific details stay in `raw_ref` or parser output files, not in ad hoc top-level fields.
- Locked geometry, especially SAM mask geometry, must be marked explicitly.

### ElementPlan

`ElementPlan` is the fusion/refine authority for each final element.

Required fields:

- `schema`: `drawai.element_plan.v1`
- `element_id`
- `source_candidate_ids`
- `element_type`
- `bbox`
- `geometry`
- `z_order`
- `confidence`
- `processing_intent`
- `review_status`
- `created_by_stage`
- `change_reason`

Rules:

- Every non-added plan must retain source candidate lineage.
- Added elements must use stable generated IDs and empty `source_candidate_ids`.
- Refined or split elements must explain the action in `change_reason`.
- Locked mask geometry can be preserved, merged, or removed, but not resized or reshaped by Agent refinement.

### ProcessingIntent

`ProcessingIntent` separates object identity from processing behavior.

Core object types:

```text
text
icon
picture
table
chart
diagram
arrow
frame
grid
symbol
content_box
unknown
```

Core processing types:

```text
svg_self_draw
crop
crop_nobg
image_generate
image_edit
chart_rebuild_reserved
```

Extension rules:

- Unknown extension strings are rejected unless registered.
- Each registry entry declares `type_id`, `schema_version`, `capabilities`, `supported_inputs`, `supported_outputs`, and UI label metadata.
- Extensions cannot override a core type without an explicit compatibility adapter.

### AssetPackage

Each final element gets one asset package.

Required fields:

- `schema`: `drawai.asset_package.v1`
- `asset_id`
- `element_id`
- `status`: `pending`, `running`, `ok`, `failed`, or `unsupported`
- `source_refs`
- `processor_plan`
- `processor_runs`
- `active_result`
- `all_results`
- `editable_payload`
- `failure`

Rules:

- Every processor execution appends a `processor_runs` entry.
- `active_result` points to one result from `all_results`.
- Failed processors must preserve enough input and error data to debug the failure.
- Image generation and image editing results must record provider metadata, prompt or edit instruction, source result references, dimensions, and response metadata.

### RunPackage

`drawai_package.json` is the run-level entrypoint.

Required fields:

- `schema`: `drawai.run_package.v1`
- `run_id`
- `package_version`
- `source_image`
- `canvas`
- `stage_status`
- `parser_registry`
- `fusion_config`
- `refine_config`
- `processor_registry`
- `elements`
- `asset_packages`
- `compose_outputs`
- `export_outputs`
- `legacy_compatibility`
- `created_at`
- `updated_at`

Rules:

- `legacy_compatibility.mode` is `v2`, `legacy_readonly`, or `none`.
- A v2 package may export legacy-shaped files for current SVG/PPT code, but those exports are derived artifacts.
- Workbench and API writes must update the run package or asset package, not only compatibility files.

## Parser Providers

Each parser declares:

- `parser_id`
- `schema_version`
- `input_contract`
- `output_contract`
- `supported_element_types`
- `priority`
- `default_fusion_rules`
- `artifact_outputs`

First implementation providers:

- `sam3_structure_parser`: adapts current SAM3 bbox/mask proposals into `ElementCandidate`.
- `ocr_text_parser`: adapts OCR text boxes into text candidates.
- `existing_adapter_parser`: transitional adapter for current raw region and OCR outputs while the main stages are replaced.

Reserved registry slots:

- `vision_layout_parser`
- `table_parser`
- `chart_parser`

Reserved slots should validate as unavailable unless configured. They should not look available in Workbench.

## Fusion Rules

The built-in fusion engine handles:

- parser priority
- candidate confidence
- IoU threshold
- smaller-overlap threshold
- containment relationships
- element-type compatibility
- text/visual non-overwrite rules
- locked geometry preservation

Rule hooks can be registered by parser or element type.

The fusion trace must record:

- candidate IDs considered
- action: `kept`, `merged`, `suppressed`, `split_hint`, or `delegated_to_refine`
- rule ID
- thresholds used
- resulting element draft ID when applicable
- explanation

Fusion is run-critical. Invalid parser output or invalid fusion output fails the run.

## Agent Refinement

Agent refinement is a `RefineProcessor` style provider, but it runs before asset processing and is run-critical when enabled.

Default provider:

- `codex_element_refiner`

Reserved providers:

- `kimi_element_refiner`
- `external_cli_element_refiner`

Inputs:

- source image
- normalized candidates
- fusion trace
- candidate overlay
- OCR text
- mask previews
- registry definitions
- processor capability list

Allowed actions:

- adjust bbox
- correct `element_type`
- split element
- add missing element
- remove duplicate/noise element
- choose or correct `processing_intent`
- write confidence and evidence

Disallowed actions:

- generate final raster asset
- edit SVG/PPT output
- mutate locked mask geometry
- use legacy run artifacts as source for v2 processing

Validation:

- all source candidates must be represented unless intentionally removed with reason
- all element IDs must be unique
- bboxes must be valid
- geometry locks must be respected
- processing intents must be registered

## Asset Processors

All processors implement a common contract:

- validate input `ElementPlan`
- declare required source refs
- declare output result schema
- append processor run metadata
- write result artifacts inside the element package
- update package status

### Supported in First Implementation

`svg_self_draw_processor`
: Produces editable constraints and payload for `compose_svg`. It is for text, simple lines, arrows, frames, boxes, simple diagrams, and simple icons. It does not create a raster crop as its primary output.

`crop_processor`
: Crops the source image using bbox/geometry and preserves local background.

`crop_nobg_processor`
: Crops the source image and uses RMBG to produce a transparent PNG. Failure marks that asset package failed.

`image_generate_processor`
: Generates a replacement element image using the configured model provider. It stores prompt, provider metadata, dimensions, source context, response metadata, and output PNG.

`image_edit_processor`
: Edits an element crop or an existing active result. It stores edit instruction, input result reference, provider metadata, and output PNG.

### Reserved

`chart_rebuild_processor`
: Registered as `chart_rebuild_reserved`, but first implementation may return `unsupported`. It exists so chart/table-specific plans and UI do not need another schema break later.

## Workbench Behavior

Workbench must distinguish v2 and legacy runs.

For v2 runs:

- show stage status for parse, fusion, refine, process, compose, and export
- show element list with bbox, type, processing intent, confidence, and processor status
- show asset drawer for each element
- display source refs, active result, all result history, processor runs, failure details, and editable payload summary
- allow processor execution for available processors
- allow choosing active result
- allow recomposing SVG after asset changes
- allow export after successful compose
- show chart rebuild as reserved/unsupported when relevant

For legacy runs:

- display existing artifacts
- allow downloads
- disable or hide all asset processing, regeneration, recompose, and re-export controls
- if source image exists, show "Create v2 run from source"
- mutating actions return `legacy_readonly_case`

## CLI Behavior

Main v2 commands:

```bash
uv run drawai run image.png --local
uv run drawai run image.png --stage parse_elements
uv run drawai run image.png --from-stage process_assets
uv run drawai asset process <run-dir> <element-id> --processor image_edit
uv run drawai asset activate <run-dir> <element-id> <result-id>
uv run drawai compose <run-dir>
uv run drawai export <run-dir>
```

Legacy stage names may remain as aliases for a compatibility window, but output should warn that v2 package files are authoritative.

## API Behavior

New or updated API endpoints:

```text
GET  /api/cases/{id}/package
GET  /api/cases/{id}/elements
GET  /api/cases/{id}/elements/{element_id}/asset-package
POST /api/cases/{id}/elements/{element_id}/process
POST /api/cases/{id}/elements/{element_id}/active-result
POST /api/cases/{id}/compose
POST /api/cases/{id}/export
POST /api/cases/{id}/fork-v2-from-source
```

Rules:

- All mutating endpoints reject legacy cases.
- Processor endpoints validate registry capabilities before execution.
- Export rejects failed/unsupported required assets unless `allow_partial_export=true`.
- Forking from legacy uses the source image only, not legacy intermediate artifacts.

## Error Handling

Run-critical failures:

- invalid config
- missing source image
- parser failure
- invalid parser output
- fusion failure
- invalid fusion output
- enabled Agent refine failure
- invalid refined element plans
- package write failure

Asset-level failures:

- crop failure for one element
- RMBG failure for one element
- image generation failure for one element
- image editing failure for one element
- reserved processor selected for an unsupported element

Export behavior:

- default export fails if required asset packages are `failed` or `unsupported`
- explicit partial export records all omitted or fallback assets in export report

Code should expose failures instead of broadly catching them. Top-level pipeline and API boundaries may catch exceptions only to write structured status and reports.

## Compatibility and Migration

Compatibility exports may be produced during transition:

- `box_ir/box_ir.json`
- `reports/element_analysis_codex/element_analysis.json`
- `svg_to_ppt/assets/asset_manifest.json`

These files are derived from v2 package state. They are not authoritative and should not be used by v2 mutating flows.

Legacy detection:

- v2 run: has `drawai_package.json` with `schema=drawai.run_package.v1`
- legacy run: has current artifacts but no v2 package
- unknown run: missing enough metadata to classify

Legacy action policy:

- view: allowed
- download: allowed
- fork from source: allowed when source exists
- process asset: rejected
- regenerate asset: rejected
- compose: rejected
- export: rejected
- migrate old intermediates into v2: rejected

## Testing Strategy

Test categories:

- schema validation for `ElementCandidate`, `ElementPlan`, `ProcessingIntent`, `AssetPackage`, and `RunPackage`
- registry validation for core enum and extension entries
- parser adapter tests with real small images and fixture parser payloads
- fusion tests for priority, IoU/NMS, containment, type compatibility, text/visual non-overwrite, and locked geometry
- Agent refine contract tests for coverage, bbox validity, source lineage, geometry locks, and processing intent
- processor tests for crop, crop_nobg, image_generate, image_edit, package result writing, and failure records
- Workbench API tests for v2 mutating actions, legacy rejection, and fork-from-source
- Workbench UI tests for v2 asset drawer and legacy read-only controls
- end-to-end smoke using a real demo image through package creation, SVG composition, rendered PNG, and export report

Production code should not use artificial fallback data. Unit tests should prefer real local functions and fixture payloads. Provider-boundary tests may use explicit test doubles only when running the external service is impractical, while integration tests should exercise real local services where practical.

## Non-Goals for First Implementation

- Do not implement actual chart rebuilding beyond registry slot, schema, and unsupported UI/API state.
- Do not migrate legacy run intermediates into v2 packages.
- Do not remove all compatibility file outputs if current SVG/PPTX code still needs them.
- Do not add silent fallback from failed Agent refine to deterministic fusion output when refine is enabled.
- Do not change public README marketing copy as part of the first implementation unless required by CLI behavior changes.

## Acceptance Criteria

- `uv run drawai run ...` uses the v2 main path by default.
- Each successful v2 run writes `drawai_package.json`.
- Each final element has an asset package directory.
- Parser, fusion, refine, processor, compose, export, and package stages are visible in stage status.
- Workbench can inspect v2 run package and asset packages.
- Workbench can process a v2 asset with available processors.
- Workbench can set an active asset result and recompute downstream outputs.
- Legacy runs are visible but read-only.
- Legacy mutating API calls fail with `legacy_readonly_case`.
- Legacy runs with source image can create a new v2 run from source.
- Export fails by default when required assets are failed or unsupported.
- Chart rebuild appears only as reserved/unsupported, not as a working feature.
