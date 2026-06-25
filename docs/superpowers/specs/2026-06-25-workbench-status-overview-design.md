# DrawAI Workbench Status Overview Design

Date: 2026-06-25

Status: approved design for implementation planning

## Goal

Add a read-only status overview to the Workbench settings center so users can quickly understand whether DrawAI is ready to run, which capabilities are enabled, which capabilities are missing configuration, and where to go to fix each issue.

The overview should act as a state guide, not as an automatic configuration wizard. It summarizes runtime health, API presets, the selected Agent, default LLM settings, processor readiness, and key user-facing capabilities such as image generation and image editing. Each actionable issue links to the existing settings category and, when possible, selects the relevant preset, Agent, LLM preset, or processor.

## Confirmed Product Decisions

- Add a new `Overview` settings category and make it the default page when opening the settings center.
- Keep the overview read-only. It must not write settings or perform automatic setup.
- Existing settings categories remain the editing surfaces: `API Presets`, `Agent`, `LLM`, and `Processor`.
- The overview should provide direct navigation to existing configuration surfaces instead of duplicating form controls.
- Status should be grouped by user-understandable areas: runtime services, API/model providers, Agent, LLM, processors, and key capabilities.
- The overview should call out image generation and image editing readiness explicitly instead of hiding those states only under processor details.
- Use three severities: `ok`, `warning`, and `error`.
- Use `warning` for optional or currently disabled capabilities that do not block the baseline editable-PPT workflow.
- Use `error` for missing or conflicting configuration that blocks an enabled/default path.
- Do not introduce mock data. Overview content comes from real Workbench settings and runtime probes.

## Current Repo Context

Useful current surfaces:

- `apps/workbench/src/App.tsx` implements the settings center with `api`, `agent`, `llm`, and `processor` categories.
- `apps/workbench/src/types.ts` defines `HealthResponse`, `ApiPresetsResponse`, `WorkbenchAgentSettingsResponse`, and `ProcessorSettingsResponse`.
- `apps/workbench/src/api.ts` exposes frontend calls for `/api/health`, `/api/workbench/agent-settings`, `/api/workbench/api-presets`, and `/api/workbench/processor-settings`.
- `src/drawai/workbench/api.py` exposes `/api/health`, agent settings, API presets, and processor settings.
- `src/drawai/workbench/agent_settings.py` stores the selected Agent and LLM defaults in `<workspace>/settings/agent.json`.
- `src/drawai/workbench/api_presets.py` stores typed API presets in `<workspace>/settings/api_presets.json`.
- `src/drawai/workbench/processor_settings.py` defines processor drivers, default processor settings, and `processor_settings_validation()`.
- Runtime health currently probes `sam3`, `ocr`, and `rmbg`.
- Agent discovery can be slower because it checks local CLI availability and Codex auth. The overview should not force discovery of every provider just to render.

## UX Structure

Add `overview` to the settings category type and navigation.

Recommended navigation structure:

```text
工作空间
  总览
  模型供应商
  Agent
  LLM 配置

运行
  处理器
```

The settings center should open on `overview`.

The overview page contains:

1. A compact top summary with the overall status label and issue counts.
2. A set of status groups:
   - Runtime services
   - API and model presets
   - Agent
   - LLM
   - Processors
   - Key capabilities
3. A prioritized issue list:
   - `error` items first
   - `warning` items second
   - stable ordering within each group
4. Action buttons on issue rows:
   - `去配置` for settings that need editing
   - `查看` for read-only runtime/service detail
   - `选择` when the action is to pick an existing preset/provider

The overview should follow the current settings center visual language: restrained, dense enough for scanning, 8px-or-less radii, no nested cards, and no marketing-style hero panel.

## Navigation Behavior

Overview actions route to existing pages:

```text
Missing images API preset
  -> API Presets category
  -> select an existing images_api preset if one exists, otherwise open the add-preset path

Missing or invalid image_generate processor configuration
  -> Processor category
  -> select image_generate

Missing or invalid image_edit processor configuration
  -> Processor category
  -> select image_edit

Selected Agent unavailable
  -> Agent category
  -> select current selected_provider_id

No default LLM preset selected
  -> LLM category

LLM selected preset missing or invalid
  -> API Presets category
  -> select the referenced preset when it can be identified

Runtime service offline
  -> Overview runtime group
```

The implementation can support this with a small frontend helper such as:

```text
openSettingsTarget({ category, targetId, action })
```

The helper should reuse existing functions such as `openApiPresetSettings()`, `openAgentSettings()`, `openLlmSettings()`, and `openProcessorSettings()` where possible.

## Backend Overview API

Add a read-only endpoint:

```text
GET /api/workbench/status-overview
```

The endpoint aggregates existing sources and returns a normalized status payload for the frontend.

Recommended top-level shape:

```json
{
  "schema": "drawai.workbench.status_overview.v1",
  "overall": {
    "severity": "warning",
    "label": "部分能力未启用",
    "error_count": 0,
    "warning_count": 2
  },
  "groups": [
    {
      "id": "runtime",
      "label": "运行服务",
      "severity": "ok",
      "summary": "SAM3、OCR、RMBG 在线",
      "items": []
    }
  ],
  "issues": [
    {
      "id": "capability.image_generate.disabled",
      "severity": "warning",
      "title": "图像生成未启用",
      "message": "image_generate processor 目前关闭，涉及生成新图像的元素不会走图像生成能力。",
      "scope": "图像生成",
      "action": {
        "label": "去配置",
        "category": "processor",
        "target_id": "image_generate"
      }
    }
  ]
}
```

The frontend should not infer important readiness from unrelated raw fields when the backend can provide a direct status. This keeps rule changes centralized and testable.

## Backend Status Sources

The endpoint should reuse current backend functions:

- Runtime: use the same runtime probe path as `/api/health`.
- API presets: use `read_workbench_api_presets()`.
- Agent settings: use `read_workbench_agent_settings()`.
- Agent availability: validate only the currently selected provider for the overview.
- Processor settings: use `read_workbench_processor_settings()` and `processor_settings_validation()`.

Agent availability should avoid scanning every provider. A focused helper can validate the selected provider using the same logic as `_discover_agent()` for that provider. This preserves the usefulness of overview without restoring the settings-center discovery delay that was recently removed.

## Severity Rules

Overall severity:

- `error` if any issue has severity `error`.
- `warning` if there are no errors and at least one warning.
- `ok` if there are no errors or warnings.

Runtime services:

- `ok` when API health is available and all runtime services are online.
- `error` when a runtime service required for the baseline workflow is offline.
- Include `sam3`, `ocr`, and `rmbg` in the baseline readiness group.

API presets:

- `warning` when no API presets exist.
- `warning` when no `images_api` preset exists, because image generation/editing through API presets cannot be configured.
- `warning` when no LLM API preset exists.
- `error` when a saved preset that is referenced by current settings is missing, has the wrong type, or is invalid.

Agent:

- `ok` when the selected provider is available and any required auth is available.
- `error` when the selected provider is a CLI/ACP provider and the executable is missing.
- `error` when the selected Codex provider requires auth and auth is unavailable.
- `warning` when the selected provider is usable but the model is empty for a provider where users commonly expect an explicit model. `codex_sdk` may remain ok with an empty model because it can use its own default.

LLM:

- `ok` when the default LLM can be resolved to a valid LLM API preset or complete direct LLM settings.
- `warning` when no default LLM preset is selected and no complete direct LLM settings are present.
- `error` when the selected or referenced LLM preset is missing, has a non-LLM type, or lacks required base URL, model, or credential source.

Processors:

- `ok` for enabled processors that are valid and configured.
- `warning` for disabled optional processors.
- `error` for enabled processors that are invalid or unconfigured.
- `error` when there is no enabled configured processor at all.

Key capabilities:

- Baseline editable workflow is `ok` when runtime services are online and `no_process`, `crop`, and `crop_nobg` are enabled/configured.
- Image generation is `ok` when `image_generate` is enabled, valid, and configured.
- Image generation is `warning` when `image_generate` is disabled or missing a driver/API preset.
- Image editing is `ok` when `image_edit` is enabled, valid, and configured.
- Image editing is `warning` when `image_edit` is disabled or missing a driver/API preset.
- If a user explicitly enables `image_generate` or `image_edit` but leaves it invalid, the capability issue should become `error`.

## Frontend Types and State

Add TypeScript types for the new overview response in `apps/workbench/src/types.ts`.

Add a frontend API helper in `apps/workbench/src/api.ts`:

```text
getWorkbenchStatusOverview(): Promise<WorkbenchStatusOverviewResponse>
```

In `WorkbenchSettingsCenter`:

- Initialize `settingsCategory` to `overview`.
- Load overview data alongside current settings data.
- Refresh overview after saving settings.
- If the user navigates back to overview after editing draft fields but before saving, overview still reflects saved backend state. This is acceptable because the overview is a saved-state diagnostic.
- Keep `localError` behavior consistent with existing settings loads.

If overview loading fails but individual settings loads succeed, show an error state inside the overview page and keep the rest of the settings center usable.

## Frontend Rendering

Render overview content as a dedicated branch in the current settings center:

```text
settingsCategory === "overview"
```

Suggested components inside `App.tsx` for the first implementation:

```text
SettingsOverviewPage
SettingsOverviewSummary
SettingsOverviewGroup
SettingsOverviewIssueList
```

These can remain in `App.tsx` initially because the existing settings center is already in that file. If the section grows substantially, a later refactor can extract settings-specific components, but the first implementation should keep the change close to current code.

Overview copy should be concise and operational. Avoid explaining how the application works; focus on current status and next action.

## Non-Goals

- No automatic configuration.
- No one-click repair.
- No test calls to external model APIs.
- No synthetic/mock status data in the UI.
- No new settings storage file for the overview.
- No replacement of existing API preset, Agent, LLM, or Processor edit surfaces.
- No change to Fuse or Refine authority over `build.processing_type`.
- No change to processor execution behavior.

## Testing

Backend tests:

- Add focused tests for `/api/workbench/status-overview`.
- Verify all-online baseline returns overall `ok` when settings are sufficient.
- Verify offline runtime service produces an `error`.
- Verify no API presets produces warnings for API/model readiness.
- Verify enabled `image_generate` with `openai_images_api` and no preset produces an `error`.
- Verify disabled `image_generate` and `image_edit` produce warnings, not errors.
- Verify current selected Agent unavailable produces an `error`.

Frontend verification:

- Run `npm --prefix apps/workbench run build`.
- If frontend tests exist in the active branch, run the focused test suite.
- Use a local Workbench session or browser screenshot check to verify:
  - settings opens on Overview,
  - issue actions navigate to the expected settings category,
  - text fits at desktop and mobile widths,
  - existing API/Agent/LLM/Processor save flow still works.

General checks:

- Run `git diff --check`.
- Run a focused backend pytest subset that includes the new overview tests and the existing health/settings tests.
