# DrawAI Processor Settings Design

Date: 2026-06-23

Status: approved design for implementation planning

## Goal

Create a unified Workbench settings center for API presets, Agent providers, LLM defaults, and processor configuration.

The processor settings surface should support upcoming processors such as `image_generate`, `image_edit`, and `figure_agent` without moving processor assignment logic into global settings. Fuse and Refine remain responsible for element typing and `build.processing_type` decisions. The settings center only defines which registered processors are available, how each processor is driven, and what operation description Refine receives for enabled processors.

## Confirmed Product Decisions

- Top-level settings sections are peers: `API Presets`, `Agent`, `LLM`, and `Processor`.
- `Processor` can appear last because it references API, Agent, and built-in capabilities configured elsewhere.
- Workbench settings are workspace-private backend settings, not repo config.
- The default workspace remains gitignored, such as `.local/workbench`; users can also set `DRAWAI_WORKBENCH_WORKSPACE` or pass `--workspace` to store settings outside the repo.
- API keys may be saved either as an environment variable name or as plaintext in the private workspace settings file. The UI recommends environment variables, but if a user enters a key in Workbench it is saved as plaintext.
- API presets are strongly typed. A processor can only select compatible preset types.
- LLM settings reference an LLM API preset instead of storing their own base URL, model, or key fields.
- Processor types are registered in code. Users cannot create new `processing_type` values in the settings UI.
- When code registers a new processor, the settings UI should discover and display it automatically.
- Each processor is configured independently.
- Disabled or unconfigured processors are omitted from Refine's available operation list.
- Execution refuses to run disabled or unconfigured processors. There is no silent fallback.
- Processor settings do not define element-type mappings such as `picture -> image_edit`.
- Processor settings do not allow arbitrary Agent providers to drive processors that do not support those providers.
- Processor operation descriptions remain structured as `meaning`, `choose_when`, and `avoid_when` so the existing Refine prompt renderer can keep its current section shape.

## Current Repo Context

Useful current surfaces:

- `src/drawai/workbench/agent_settings.py` stores current Agent and LLM settings at `<workspace>/settings/agent.json`.
- `src/drawai/workbench/api.py` exposes `/api/workbench/agent-settings`, `/api/imagegen/generations`, and `/api/imagegen/edits`.
- `apps/workbench/src/App.tsx` currently has separate Agent/LLM and ImageGen settings dialogs.
- ImageGen connection settings currently use browser `localStorage` under `drawai.imagegen.connection`.
- `src/drawai/v2/registry.py` registers processing types including `image_generate` and `image_edit`.
- `src/drawai/v2/processors.py` implements processors including `CropProcessor`, `CropNoBgProcessor`, `ImageGenerateProcessor`, and `ImageEditProcessor`.
- `src/drawai/v2/stages.py` already accepts provider injections for `image_generate` and `image_edit`.
- `src/drawai/page_spec_assets.py` still blocks `image_generate` and `image_edit` in the PageSpec materialization path.
- `src/drawai/workflow/agent_prompt_defaults.py` currently owns `PAGE_SPEC_PROCESSING_OPERATIONS`, `DEFAULT_PAGE_SPEC_REFINE_PROCESSING_TYPES`, `normalize_page_spec_processing_types()`, and `render_page_spec_processing_operations()`.
- `src/drawai/workflow/templates.py` stores `page_spec_processing_types` in the built-in `page_spec_refine` node config.

## Settings Model

Add workspace-private settings files:

```text
<workbench_workspace>/settings/api_presets.json
<workbench_workspace>/settings/processor.json
```

`api_presets.json` stores reusable, strongly typed API connections:

```json
{
  "schema": "drawai.workbench.api_presets.v1",
  "presets": [
    {
      "id": "openai_images",
      "label": "OpenAI Images",
      "type": "images_api",
      "base_url": "https://api.openai.com",
      "model": "gpt-image-2",
      "api_key_env": "OPENAI_API_KEY",
      "api_key": ""
    }
  ]
}
```

Initial API preset types:

```text
images_api
llm_chat_completions
llm_responses
```

The design can later add more typed presets such as `custom_http`, but the first implementation should avoid untyped generic API presets.

`processor.json` stores user-editable settings for registered processors only:

```json
{
  "schema": "drawai.workbench.processor_settings.v1",
  "processors": {
    "image_generate": {
      "enabled": true,
      "driver_id": "openai_images_api",
      "api_preset_id": "openai_images",
      "operation": {
        "meaning": "Generate a new image asset from element semantics and page context.",
        "choose_when": "Choose for image-like assets that must be generated rather than copied from the source image.",
        "avoid_when": "Do not choose for source content that can be cropped or drawn structurally."
      }
    },
    "crop": {
      "enabled": true,
      "driver_id": "builtin_crop",
      "operation": {
        "meaning": "Crop the source region exactly.",
        "choose_when": "Choose when source pixels should be preserved.",
        "avoid_when": "Do not choose when the element should remain editable structure."
      }
    }
  }
}
```

Unknown processor keys in saved settings should be ignored on read or reported as inactive legacy entries, but they must not become available processing types. Saving from the UI should only write registered processors.

## Processor Registry

Extend the current processing registry so Workbench can discover both processor definitions and driver compatibility.

Each processor definition should include:

```text
processing_type
label
default_enabled
default_operation
supported_driver_ids
default_driver_id
driver requirements
validation metadata
```

Each driver definition should include:

```text
driver_id
label
kind
required_api_preset_type, if any
runtime provider factory or route
description
```

Examples:

```text
crop
  drivers: builtin_crop

crop_nobg
  drivers: rmbg_service

image_generate
  drivers: codex_imagegen_builtin, openai_images_api
  openai_images_api requires api preset type images_api

image_edit
  drivers: codex_image_edit_builtin
  images_api should not be exposed here until an executable edit adapter is registered in code

figure_agent
  drivers: only the figure-agent driver registered in code
```

An Agent provider should not appear as a processor driver unless code explicitly registers a driver for that processor. For example, Kimi or Claude should not become image generation drivers merely because they exist in Agent settings.

## Backend API

Add settings APIs:

```text
GET /api/workbench/api-presets
PUT /api/workbench/api-presets
GET /api/workbench/processor-settings
PUT /api/workbench/processor-settings
```

`GET /api/workbench/processor-settings` returns:

```text
definitions: registered processor and driver definitions
settings: resolved workspace processor settings
validation: per-processor configured/invalid status and exact messages
```

Saving should validate:

- API preset ids are unique.
- API preset type is known.
- API preset `base_url` and `model` are required.
- `api_key_env` and `api_key` are both allowed; at least one usable credential source should be present when validation requires credentials.
- `processing_type` is registered.
- `driver_id` belongs to the processor's supported driver list.
- Required `api_preset_id` exists and has the required type.
- `enabled=true` requires a complete valid driver configuration.
- Processor operation fields `meaning`, `choose_when`, and `avoid_when` are non-empty.

Validation should surface precise errors instead of falling back or masking the issue.

## Refine Operation Catalog

Do not replace the Refine prompt template and do not move processor assignment into settings.

The current flow should remain:

```text
page_spec_processing_types
  -> render_page_spec_processing_operations(...)
  -> Refine prompt
  -> Refine writes build.processing_type
```

The change is to make the operation catalog and default enabled processing types resolvable from registry plus workspace settings.

Current behavior:

```text
page_spec_processing_types comes from workflow node config
PAGE_SPEC_PROCESSING_OPERATIONS is a fixed code constant
render_page_spec_processing_operations() pulls descriptions from that constant
```

Target behavior:

```text
processor registry default definitions
  + workspace processor settings
  + optional workflow node page_spec_processing_types override
  -> resolved operation catalog
  -> existing Refine operation renderer
```

Concretely, evolve the render path toward:

```python
render_page_spec_processing_operations(
    processing_types,
    operation_catalog=resolved_processor_operation_catalog,
)
```

The operation catalog should use each processor's default operation fields unless the workspace setting provides edited fields. The renderer still emits the available processing operation sections used by the existing Refine prompt.

If a workflow node explicitly configures `page_spec_processing_types`, that list remains a workflow-local override of which enabled processors are visible to that node. The override cannot make an unregistered, disabled, or invalid processor available.

## Execution Integration

`process_assets` and single-element processing should read resolved processor settings before running a processor.

Rules:

- If a processor is disabled, execution fails with a clear disabled message.
- If a processor is enabled but not configured, execution fails with a configuration message.
- If a driver requires an API preset and the preset is missing or incompatible, execution fails.
- There is no fallback from an invalid configured driver to Codex, API, crop, or any other driver.
- Processor run metadata should record `driver_id`, `api_preset_id` when applicable, and enough non-secret settings to reproduce what happened.

Provider injection should become settings-driven:

```text
image_generate -> selected image generation driver provider
image_edit -> selected image edit driver provider; currently codex_image_edit_builtin only
crop_nobg -> selected RMBG service driver provider
figure_agent -> registered figure-agent provider when implemented
```

The driver route is defined by code, not by arbitrary UI strings.

## Frontend Settings Center

Replace the separate settings dialogs with one settings center:

```text
API Presets
Agent
LLM
Processor
```

`API Presets`:

- Create, edit, delete, and validate strongly typed API presets.
- Fields: label, id, type, base URL, model, API key env, API key.
- Recommend API key env in UI copy.
- Preserve plaintext keys when users enter them.

`Agent`:

- Migrate the current Agent provider settings page.
- Continue to show local provider availability, command, version, auth status, model, reasoning effort, and timeout.

`LLM`:

- Select a default LLM API preset.
- Store LLM-specific defaults such as wire API, extra body, reasoning effort, and timeout.
- Do not duplicate base URL, key, or model fields outside API presets.

`Processor`:

- Display processors from backend definitions.
- Show processing type, label, enabled state, configured state, current driver, and validation details.
- Allow editing enabled state, driver, required driver parameters, and processor operation description fields.
- Provide a restore-default-description action.
- Only show drivers supported by that processor.
- Do not allow creating new processor types.
- Do not expose element-type mapping rules.

## Migration

Migration should be explicit and conservative:

- Keep reading existing `<workspace>/settings/agent.json`.
- Move existing LLM base URL, model, key, key env, wire API, and extra body into the new API preset plus LLM settings model when the new settings API first writes.
- Import browser `drawai.imagegen.connection` into an `images_api` API preset when the Workbench frontend first sees localStorage data and no equivalent workspace preset exists.
- Leave old localStorage intact until workspace save succeeds.
- If `processor.json` does not exist, return default resolved settings from the registry without writing a file until the user saves.
- Existing runs are not rewritten.

Default resolved processor behavior should be conservative:

```text
crop: enabled with builtin driver
crop_nobg: enabled only when RMBG service configuration is available
image_generate: disabled or unconfigured until a valid driver is selected
image_edit: disabled or unconfigured until a valid driver is selected
figure_agent: shown only if registered in code; unavailable until implemented/configured
```

## Testing

Backend tests:

- Read defaults when settings files are absent.
- Write and read `api_presets.json`.
- Write and read `processor.json`.
- Reject duplicate API preset ids.
- Reject unknown API preset types.
- Reject unknown processor types on save.
- Reject incompatible processor driver ids.
- Reject processor driver settings with wrong API preset type.
- Resolve operation catalog using workspace-edited operation descriptions.
- Omit disabled, invalid, and unconfigured processors from Refine operation lists.
- Refuse execution for disabled and unconfigured processors.

Workflow tests:

- Existing Refine prompt template still renders the same structure.
- `page_spec_processing_types` node config continues to work.
- Node override cannot enable invalid processors.
- Workspace operation description overrides appear in the rendered operation sections.

Frontend tests:

- Settings center renders the four top-level sections.
- API preset forms enforce known types.
- LLM settings select only compatible LLM presets.
- Processor page uses backend definitions, not hard-coded frontend lists.
- Processor driver selector only shows compatible drivers.
- Restore default description works.
- ImageGen localStorage migration creates an `images_api` preset only after workspace save succeeds.

## Risks And Constraints

- The design must not introduce element-type-to-processor mapping in global settings.
- The design must not allow UI registration of arbitrary processing types.
- The design must not duplicate credentials across API Presets and LLM settings.
- The design must not silently run a different processor driver from the one configured.
- The design should keep implementation changes scoped around settings, registry resolution, operation catalog rendering, and provider injection.
- PageSpec materialization support for `image_generate` and `image_edit` remains a separate execution integration task. This design defines how those processors are configured and exposed, not every downstream materialization behavior.
