# Processor Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the unified Workbench settings center for API presets, Agent, LLM, and registered processor configuration.

**Architecture:** Add focused backend settings modules for API presets and processor settings, then expose them through Workbench API endpoints. Keep the existing Refine prompt template and make the operation catalog injectable through node config. Replace the separate frontend settings dialogs with one settings center that consumes backend definitions and writes workspace-private settings.

**Tech Stack:** Python dataclasses/FastAPI/pytest, existing DrawAI workflow prompt utilities, React + TypeScript + Vite Workbench UI.

---

## File Structure

- Create `src/drawai/workbench/api_presets.py`: workspace API preset schema, validation, read/write helpers, and payload conversion.
- Create `src/drawai/workbench/processor_settings.py`: processor/driver definitions, workspace settings schema, validation, resolved operation catalog, and provider metadata.
- Modify `src/drawai/workflow/agent_prompt_defaults.py`: allow `render_page_spec_processing_operations()` to receive an operation catalog while preserving default behavior.
- Modify `src/drawai/workflow/agents.py`: validate and render optional `page_spec_processing_operations` from node config.
- Modify `src/drawai/workbench/api.py`: add API preset and processor settings endpoints, and route single-element processor execution through resolved settings.
- Modify `src/drawai/workbench/runner.py`: inject resolved processor operation config into `page_spec_refine` workflow nodes.
- Modify `apps/workbench/src/types.ts`: add API preset and processor settings response types.
- Modify `apps/workbench/src/api.ts`: add client calls for new settings endpoints.
- Modify `apps/workbench/src/App.tsx`: replace separate Agent/ImageGen settings dialogs with a unified settings center and migrate ImageGen localStorage data.
- Modify `apps/workbench/src/styles.css`: style the unified settings center using the existing restrained settings visual language.
- Add/modify tests in `tests/workbench/test_workflow_api.py`, `tests/workflow/test_agents.py`, and `tests/v2/test_processors.py`.

## Tasks

### Task 1: Backend API Presets

**Files:**
- Create: `src/drawai/workbench/api_presets.py`
- Test: `tests/workbench/test_workflow_api.py`

- [ ] **Step 1: Write failing API preset tests**

Add tests that call:

```python
response = client.get("/api/workbench/api-presets")
assert response.status_code == 200
assert response.json()["schema"] == "drawai.workbench.api_presets.v1"

save_response = client.put(
    "/api/workbench/api-presets",
    json={
        "presets": [
            {
                "id": "openai_images",
                "label": "OpenAI Images",
                "type": "images_api",
                "base_url": "https://api.openai.com",
                "model": "gpt-image-2",
                "api_key_env": "OPENAI_API_KEY",
                "api_key": "sk-local",
            }
        ]
    },
)
assert save_response.status_code == 200
```

Also add duplicate-id and unknown-type rejection tests.

- [ ] **Step 2: Run targeted failing tests**

Run:

```bash
uv run --extra dev pytest tests/workbench/test_workflow_api.py -k "api_preset" -q
```

Expected: fails because endpoint/module does not exist.

- [ ] **Step 3: Implement API preset module**

Create dataclasses:

```python
@dataclass(frozen=True)
class ApiPreset:
    id: str
    label: str
    type: str
    base_url: str
    model: str
    api_key_env: str = ""
    api_key: str = ""
```

Expose `read_workbench_api_presets()`, `write_workbench_api_presets()`, `workbench_api_presets_payload()`, and `normalize_workbench_api_presets()`.

- [ ] **Step 4: Add FastAPI endpoints**

Wire `GET/PUT /api/workbench/api-presets` in `src/drawai/workbench/api.py`.

- [ ] **Step 5: Run tests**

Run:

```bash
uv run --extra dev pytest tests/workbench/test_workflow_api.py -k "api_preset" -q
```

Expected: pass.

### Task 2: Processor Settings Registry And API

**Files:**
- Create: `src/drawai/workbench/processor_settings.py`
- Modify: `src/drawai/workbench/api.py`
- Test: `tests/workbench/test_workflow_api.py`

- [ ] **Step 1: Write failing processor settings API tests**

Cover:

```python
response = client.get("/api/workbench/processor-settings")
payload = response.json()
assert "image_generate" in payload["definitions"]["processors"]
assert "openai_images_api" in payload["definitions"]["drivers"]
assert payload["settings"]["processors"]["crop"]["enabled"] is True
```

Add rejection cases for unknown processor, incompatible driver, wrong API preset type, and empty operation fields.

- [ ] **Step 2: Implement definitions and validation**

Define processors: `no_process`, `crop`, `crop_nobg`, `svg_self_draw`, `image_generate`, `image_edit`, `chart_rebuild_reserved`.

Define drivers: `builtin_no_process`, `builtin_crop`, `rmbg_service`, `builtin_svg_self_draw`, `codex_imagegen_builtin`, `codex_image_edit_builtin`, `openai_images_api`, `reserved`.

Expose `workbench_processor_settings_payload()`, `read_workbench_processor_settings()`, `write_workbench_processor_settings()`, and `resolved_processor_operations()`.

- [ ] **Step 3: Add FastAPI endpoints**

Wire `GET/PUT /api/workbench/processor-settings`.

- [ ] **Step 4: Run tests**

Run:

```bash
uv run --extra dev pytest tests/workbench/test_workflow_api.py -k "processor_settings" -q
```

Expected: pass.

### Task 3: Refine Operation Catalog Injection

**Files:**
- Modify: `src/drawai/workflow/agent_prompt_defaults.py`
- Modify: `src/drawai/workflow/agents.py`
- Modify: `src/drawai/workbench/runner.py`
- Test: `tests/workflow/test_agents.py`
- Test: `tests/workbench/test_workflow_api.py`

- [ ] **Step 1: Write failing prompt catalog tests**

Add a test where node config contains:

```python
"page_spec_processing_types": ["no_process", "image_edit"],
"page_spec_processing_operations": {
    "image_edit": {
        "meaning": "Workspace edited meaning.",
        "choose_when": "Workspace edited choose.",
        "avoid_when": "Workspace edited avoid.",
    }
}
```

Assert the rendered prompt contains the edited strings and still uses the existing `### image_edit` section shape.

- [ ] **Step 2: Add operation catalog support**

Change `render_page_spec_processing_operations(processing_types, operation_catalog=None)` and `normalize_page_spec_processing_types(processing_types, operation_catalog=None)`.

In `workflow/agents.py`, read optional `page_spec_processing_operations` from config and pass it through to `render_page_spec_refine_task()`.

- [ ] **Step 3: Inject workspace processor settings into workflow templates**

In `WorkbenchRunner`, after applying Agent/LLM settings, set `page_spec_processing_types` and `page_spec_processing_operations` on `page_spec_refine` nodes from `resolved_processor_operations(workspace)`.

- [ ] **Step 4: Run tests**

Run:

```bash
uv run --extra dev pytest tests/workflow/test_agents.py tests/workbench/test_workflow_api.py -k "page_spec_refine or processor_settings" -q
```

Expected: pass.

### Task 4: Processor Execution Guard And Provider Routing

**Files:**
- Modify: `src/drawai/workbench/api.py`
- Modify: `src/drawai/workbench/processor_settings.py`
- Test: `tests/v2/test_processors.py`
- Test: `tests/workbench/test_workflow_api.py`

- [ ] **Step 1: Write failing execution guard tests**

Add tests proving:

```python
client.post("/api/cases/<case>/elements/E001/process", json={"processor": "image_generate"})
```

fails when `image_generate` is disabled or unconfigured, and succeeds only when a compatible driver is configured with a fake provider injected in tests.

- [ ] **Step 2: Implement guard**

Before `process_case_asset()`, resolve processor settings. Reject disabled or invalid processors with HTTP 400 and a clear message.

- [ ] **Step 3: Implement provider routing scaffold**

Keep existing `crop_nobg` RMBG route. Add driver metadata for `image_generate` and `image_edit`; route `image_generate` API preset drivers to the existing Images API path, keep `image_edit` on the executable Codex edit adapter until an Images edit adapter is registered in code, and do not silently fall back when a configured driver is unavailable.

- [ ] **Step 4: Run tests**

Run:

```bash
uv run --extra dev pytest tests/v2/test_processors.py tests/workbench/test_workflow_api.py -k "processor" -q
```

Expected: pass.

### Task 5: Frontend Unified Settings Center

**Files:**
- Modify: `apps/workbench/src/types.ts`
- Modify: `apps/workbench/src/api.ts`
- Modify: `apps/workbench/src/App.tsx`
- Modify: `apps/workbench/src/styles.css`

- [ ] **Step 1: Add frontend types and API calls**

Add `ApiPreset`, `ApiPresetsResponse`, `ProcessorSettingsResponse`, `ProcessorDefinition`, and `ProcessorDriverDefinition` to `types.ts`.

Add `getApiPresets()`, `saveApiPresets()`, `getProcessorSettings()`, and `saveProcessorSettings()` to `api.ts`.

- [ ] **Step 2: Replace top-bar settings actions**

Keep one settings button that opens `WorkbenchSettingsCenter`.

- [ ] **Step 3: Implement settings center sections**

Create tabs in `App.tsx`: `API Presets`, `Agent`, `LLM`, `Processor`.

Reuse current Agent form logic inside the `Agent` tab.

Move LLM fields into the `LLM` tab and make them select compatible `llm_*` presets.

Add Processor list/detail UI driven by backend definitions.

- [ ] **Step 4: Migrate ImageGen localStorage**

On opening settings, if `drawai.imagegen.connection` exists and no compatible workspace preset exists, offer/save an `images_api` preset from that data. Leave localStorage intact unless the workspace save succeeds.

- [ ] **Step 5: Run frontend checks**

Run:

```bash
npm test
npm run build
```

from `apps/workbench`.

Expected: pass.

### Task 6: Full Verification And Commit

**Files:**
- All touched files.

- [ ] **Step 1: Run focused backend tests**

```bash
uv run --extra dev pytest tests/workbench/test_workflow_api.py tests/workflow/test_agents.py tests/v2/test_processors.py -q
```

- [ ] **Step 2: Run frontend tests/build**

```bash
cd apps/workbench
npm test
npm run build
```

- [ ] **Step 3: Run diff checks**

```bash
git diff --check
git status --short
```

- [ ] **Step 4: Commit**

```bash
git add src/drawai/workbench/api_presets.py src/drawai/workbench/processor_settings.py src/drawai/workbench/api.py src/drawai/workbench/runner.py src/drawai/workflow/agent_prompt_defaults.py src/drawai/workflow/agents.py apps/workbench/src/types.ts apps/workbench/src/api.ts apps/workbench/src/App.tsx apps/workbench/src/styles.css tests/workbench/test_workflow_api.py tests/workflow/test_agents.py tests/v2/test_processors.py
git commit -m "feat(workbench): add processor settings center"
```

### Task 7: Start Testable Workbench Service

**Files:**
- No code files.

- [ ] **Step 1: Start backend**

Use a local ignored workspace:

```bash
DRAWAI_WORKBENCH_WORKSPACE=.local/workbench-processor-settings \
uv run drawai-workbench-api --host 127.0.0.1 --port 8890
```

- [ ] **Step 2: Start frontend**

```bash
cd apps/workbench
VITE_DRAWAI_API_URL=http://127.0.0.1:8890 npm run dev -- --host 127.0.0.1 --port 5173
```

- [ ] **Step 3: Report URL**

Tell the user to open:

```text
http://127.0.0.1:5173
```

Do not merge this branch.

## Self-Review

- Spec coverage: API presets, Agent/LLM/Processor top-level settings, registered processors only, strong API preset typing, operation catalog injection, disabled/unconfigured filtering, and no global mapping rules are covered.
- Placeholder scan: no task relies on a hidden TODO; each task names files, commands, and expected behavior.
- Type consistency: `api_presets`, `processor_settings`, `page_spec_processing_operations`, and `operation.meaning/choose_when/avoid_when` are used consistently.
