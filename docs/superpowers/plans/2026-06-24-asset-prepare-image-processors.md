# Asset Prepare Image Processors Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Workbench `asset_prepare` execute PageSpec `image_generate` and `image_edit` processors, add a processor-test DAG, and verify Apimart plus Codex image processing on the provided figure.

**Architecture:** Keep the PageSpec workflow on `asset_prepare`; do not use the v2 `asset_processors` node and do not call SVG Compose. `asset_prepare` will materialize PageSpec elements by `build.processing_type`, run image processors through provider callables, write active PNG outputs back into PageSpec materialization, and produce a deterministic placement SVG preview. Workbench provider settings will supply either Codex built-ins or an Images API preset.

**Tech Stack:** Python 3, pytest, PIL, FastAPI Workbench backend, Vite React Workbench frontend, DrawAI PageSpec utilities, Codex imagegen adapter, OpenAI-compatible Images API.

---

### Task 1: Processor Operation Descriptions And Test DAG

**Files:**
- Modify: `src/drawai/workflow/agent_prompt_defaults.py`
- Modify: `src/drawai/workflow/templates.py`
- Modify: `apps/workbench/src/WorkflowWorkspace.tsx`
- Modify: `tests/workflow/test_templates.py`
- Modify: `tests/workbench/test_workflow_api.py`

- [ ] **Step 1: Add failing tests for the new built-in processor-test DAG**

Add this test to `tests/workflow/test_templates.py`:

```python
def test_builtin_processor_test_template_uses_asset_prepare_without_svg_compose() -> None:
    from drawai.workflow.templates import load_workflow_template_by_id

    template = load_workflow_template_by_id(".", "processor_test_page_spec_assets")
    nodes = {node.node_id: node for node in template.nodes}
    assert "page_spec_refine" in nodes
    assert "asset_prepare" in nodes
    assert "svg_compose" not in nodes
    assert "svg_to_ppt" not in nodes
    assert nodes["page_spec_refine"].config["page_spec_processing_types"] == [
        "no_process",
        "crop",
        "crop_nobg",
        "image_generate",
        "image_edit",
    ]
    assert nodes["asset_prepare"].config["processor_id"] == "asset_prepare"
    assert nodes["asset_prepare"].config["stage"] == "process_assets"
```

Add this assertion to `test_workbench_processor_settings_api_lists_registered_processors` in
`tests/workbench/test_workflow_api.py`:

```python
assert "openai_images_api" in payload["definitions"]["processors"]["image_edit"]["supported_driver_ids"]
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
uv run --extra dev pytest tests/workflow/test_templates.py::test_builtin_processor_test_template_uses_asset_prepare_without_svg_compose tests/workbench/test_workflow_api.py::test_workbench_processor_settings_api_lists_registered_processors -q
```

Expected: FAIL because `processor_test_page_spec_assets` is unknown and `image_edit` does not yet expose `openai_images_api`.

- [ ] **Step 3: Implement operation descriptions and template registration**

In `src/drawai/workflow/agent_prompt_defaults.py`, replace the `image_generate` and `image_edit`
entries in `PAGE_SPEC_PROCESSING_OPERATIONS` with:

```python
"image_generate": PageSpecProcessingOperation(
    processing_type="image_generate",
    meaning=(
        "Generate a new raster image asset from the element's semantic role, nearby labels, "
        "page context, and target box size. The result will be scaled back into the original PageSpec box."
    ),
    choose_when=(
        "Choose for image-like conceptual graphics, illustrative icons, missing or low-quality visual assets, "
        "and regions where copying source pixels would preserve noise rather than a clean representation."
    ),
    avoid_when=(
        "Do not choose for editable text, lines, simple shapes, tables, charts, source pixels that are already "
        "acceptable as crops, or foreground objects that only need background removal."
    ),
),
"image_edit": PageSpecProcessingOperation(
    processing_type="image_edit",
    meaning=(
        "Crop the source element and edit it into a cleaner raster asset while preserving its original composition, "
        "visual role, colors, aspect, and placement constraints."
    ),
    choose_when=(
        "Choose when the source crop already contains the target object but needs cleanup, redraw, deblurring, "
        "background adjustment, style harmonization, or higher-quality reconstruction."
    ),
    avoid_when=(
        "Do not choose for elements that should remain structural, direct crops that are already good enough, "
        "or standalone foreground objects where crop_nobg is sufficient."
    ),
),
```

In `src/drawai/workflow/templates.py`:

```python
PROCESSOR_TEST_WORKFLOW_TEMPLATE_ID = "processor_test_page_spec_assets"
_BUILTIN_TEMPLATE_IDS = (DEFAULT_WORKFLOW_TEMPLATE_ID, PROCESSOR_TEST_WORKFLOW_TEMPLATE_ID)
PROCESSOR_TEST_PAGE_SPEC_PROCESSING_TYPES = (
    "no_process",
    "crop",
    "crop_nobg",
    "image_generate",
    "image_edit",
)
```

Create `processor_test_page_spec_assets_workflow_template()` by copying the default template's
input, parser, fuse, refine, asset_prepare, and output nodes. Remove `svg_compose` and `svg_to_ppt`
nodes and edges. Set the refine node config:

```python
"page_spec_processing_types": list(PROCESSOR_TEST_PAGE_SPEC_PROCESSING_TYPES),
```

Set the `asset_prepare` output description to:

```python
"Materialized PageSpec plus processor placement preview. crop/crop_nobg/image_generate/image_edit elements contain active materialization paths."
```

Update `builtin_workflow_templates()`:

```python
def builtin_workflow_templates() -> tuple[WorkflowTemplate, ...]:
    return (
        default_drawai_workflow_template(),
        processor_test_page_spec_assets_workflow_template(),
    )
```

In `apps/workbench/src/WorkflowWorkspace.tsx`, update the static operation option text to match the
backend copy for `image_generate` and `image_edit`. Built-in workflow templates are loaded from the
backend, so do not add a hardcoded frontend workflow template.

In `src/drawai/workbench/processor_settings.py`, change `image_edit.supported_driver_ids` to:

```python
supported_driver_ids=("codex_image_edit_builtin", "openai_images_api"),
```

- [ ] **Step 4: Run tests and verify they pass**

Run:

```bash
uv run --extra dev pytest tests/workflow/test_templates.py::test_builtin_processor_test_template_uses_asset_prepare_without_svg_compose tests/workbench/test_workflow_api.py::test_workbench_processor_settings_api_lists_registered_processors -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 1**

```bash
git add src/drawai/workflow/agent_prompt_defaults.py src/drawai/workflow/templates.py apps/workbench/src/WorkflowWorkspace.tsx tests/workflow/test_templates.py tests/workbench/test_workflow_api.py
git commit -m "feat(workflow): add asset prepare processor test dag"
```

### Task 2: PageSpec Asset Prepare Image Processor Materialization

**Files:**
- Modify: `src/drawai/page_spec_assets.py`
- Modify: `src/drawai/page_spec_svg.py`
- Modify: `tests/test_page_spec.py`

- [ ] **Step 1: Add failing tests for `image_generate` and `image_edit` materialization**

Add these test helpers to `tests/test_page_spec.py`:

```python
class _FakeProviderImage:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.width = 18
        self.height = 12

    def to_dict(self) -> dict[str, object]:
        return {
            "image_id": self.path.stem,
            "path": str(self.path),
            "source_path": str(self.path),
            "width": self.width,
            "height": self.height,
            "mime_type": "image/png",
        }


class _FakeProviderResult:
    def __init__(self, operation: str, output_dir: Path, path: Path) -> None:
        self.operation = operation
        self.output_dir = output_dir
        self.images = (_FakeProviderImage(path),)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "drawai.test.fake_image_provider.v1",
            "operation": self.operation,
            "output_dir": str(self.output_dir),
            "images": [image.to_dict() for image in self.images],
        }
```

Add this test to `tests/test_page_spec.py`:

```python
def test_materialize_page_spec_assets_runs_image_generate_and_edit(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGBA", (96, 64), (255, 255, 255, 255)).save(source)
    output_dir = tmp_path / "bundle"
    calls: list[tuple[str, str]] = []

    def fake_generate(**kwargs):
        calls.append(("generate", str(kwargs["prompt"])))
        result_dir = Path(kwargs["output_dir"])
        result_dir.mkdir(parents=True, exist_ok=True)
        result_path = result_dir / "generated.png"
        Image.new("RGBA", (18, 12), (20, 90, 220, 255)).save(result_path)
        return _FakeProviderResult("generate", result_dir, result_path)

    def fake_edit(**kwargs):
        calls.append(("edit", str(kwargs["prompt"])))
        with Image.open(kwargs["source_image_path"]) as crop:
            assert crop.size == (16, 12)
        result_dir = Path(kwargs["output_dir"])
        result_dir.mkdir(parents=True, exist_ok=True)
        result_path = result_dir / "edited.png"
        Image.new("RGBA", (16, 12), (220, 80, 20, 255)).save(result_path)
        return _FakeProviderResult("edit", result_dir, result_path)

    page_spec = _page_spec(
        "refine",
        [
            {
                "id": "E001",
                "kind": "image",
                "role": "representation",
                "box_px": [2, 3, 18, 12],
                "z_index": 1,
                "build": {"mode": "asset_ref", "processing_type": "image_generate"},
                "measurement": {"text": "Future representation"},
            },
            {
                "id": "E002",
                "kind": "image",
                "role": "representation",
                "box_px": [24, 3, 16, 12],
                "z_index": 2,
                "build": {"mode": "asset_ref", "processing_type": "image_edit"},
            },
        ],
    )

    materialized = materialize_page_spec_assets(
        page_spec,
        source_image_path=source,
        output_dir=output_dir,
        image_generate=fake_generate,
        image_edit=fake_edit,
        processor_workers=2,
    )

    assert [call[0] for call in calls] == ["generate", "edit"]
    first, second = materialized["elements"]
    assert first["materialization"]["processing_type"] == "image_generate"
    assert second["materialization"]["processing_type"] == "image_edit"
    assert (output_dir / first["materialization"]["outputs"]["active"]["path"]).is_file()
    assert (output_dir / second["materialization"]["outputs"]["active"]["path"]).is_file()
```

Add this assertion to `test_draft_semantic_svg_from_materialized_page_spec_uses_active_asset_href`:

```python
assert 'data-drawai-source="crop"' in svg or 'data-drawai-source="image' in svg
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```bash
uv run --extra dev pytest tests/test_page_spec.py::test_materialize_page_spec_assets_runs_image_generate_and_edit -q
```

Expected: FAIL because `materialize_page_spec_assets()` does not accept `image_generate`, `image_edit`, or `processor_workers`.

- [ ] **Step 3: Implement PageSpec image processor execution**

In `src/drawai/page_spec_assets.py`:

Add imports:

```python
from concurrent.futures import ThreadPoolExecutor

from drawai.v2.processors import ImageEditProcessor, ImageGenerateProcessor
from drawai.v2.schema import ElementPlan, ProcessingIntent
```

Remove `_UNSUPPORTED_PROCESSING_TYPES`. Add:

```python
_IMAGE_PROCESSING_TYPES = {"image_generate", "image_edit"}
```

Update `materialize_page_spec_assets()` signature:

```python
def materialize_page_spec_assets(
    page_spec: Mapping[str, Any],
    *,
    source_image_path: str | Path,
    output_dir: str | Path,
    rmbg_config: Any = None,
    rmbg_client: Any = None,
    image_generate: Any = None,
    image_edit: Any = None,
    processor_workers: int | None = None,
) -> dict[str, Any]:
```

Replace the element loop with deterministic parallel execution:

```python
elements = [item for item in raw_elements if isinstance(item, dict)]
workers = max(1, int(processor_workers or min(8, max(1, len(elements)))))

def materialize_one(raw_element: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    processing_type = _processing_type(raw_element)
    element_id = _required_string(raw_element.get("id"), "element.id")
    if processing_type in _NON_MATERIALIZED_PROCESSING_TYPES:
        return element_id, None
    if processing_type in _RASTER_PROCESSING_TYPES:
        return element_id, _materialize_raster_element(
            raw_element,
            source_image_path=source_path,
            output_dir=output_root,
            processing_type=processing_type,
            rmbg_config=rmbg_config,
            rmbg_client=rmbg_client,
        )
    if processing_type in _IMAGE_PROCESSING_TYPES:
        return element_id, _materialize_image_processor_element(
            raw_element,
            source_image_path=source_path,
            output_dir=output_root,
            processing_type=processing_type,
            image_generate=image_generate,
            image_edit=image_edit,
        )
    raise RuntimeError(f"unsupported PageSpec build.processing_type for element {element_id}: {processing_type}")

with ThreadPoolExecutor(max_workers=workers) as executor:
    materialized_by_id = dict(executor.map(materialize_one, elements))

for raw_element in elements:
    materialization = materialized_by_id[_required_string(raw_element.get("id"), "element.id")]
    if materialization is None:
        raw_element.pop("materialization", None)
    else:
        raw_element["materialization"] = materialization
```

Add helper functions:

```python
def _materialize_image_processor_element(
    element: Mapping[str, Any],
    *,
    source_image_path: Path,
    output_dir: Path,
    processing_type: str,
    image_generate: Any,
    image_edit: Any,
) -> dict[str, Any]:
    element_id = _required_string(element.get("id"), "element.id")
    plan = _element_plan_from_page_spec_element(element, processing_type=processing_type)
    if processing_type == "image_generate":
        package = ImageGenerateProcessor(image_generate=image_generate).process(output_dir, plan)
    elif processing_type == "image_edit":
        package = ImageEditProcessor(image_edit=image_edit).process(output_dir, plan, source_image_path=source_image_path)
    else:
        raise RuntimeError(f"unsupported image processor: {processing_type}")
    active = package.active_result
    if not isinstance(active, Mapping) or not active.get("path"):
        raise RuntimeError(f"PageSpec element {element_id} image processor did not produce an active result")
    active_path = output_dir / str(active["path"])
    return {
        "status": package.status,
        "processor": "asset_prepare",
        "processing_type": processing_type,
        "created_at": utc_now(),
        "outputs": {
            "active": _image_output_record(active_path, output_dir),
        },
        "metadata": {
            "asset_package_path": f"elements/{_safe_asset_dir_name(element_id)}/asset_package.json",
            "processor_metadata": dict(package.metadata),
        },
    }


def _element_plan_from_page_spec_element(element: Mapping[str, Any], *, processing_type: str) -> ElementPlan:
    element_id = _required_string(element.get("id"), "element.id")
    bbox = _bbox_xywh(element)
    role = str(element.get("role") or element.get("kind") or "image")
    return ElementPlan(
        element_id=element_id,
        source_candidate_ids=tuple(_source_ref_ids(element)) or (element_id,),
        element_type=role,
        bbox=bbox,
        geometry=element.get("geometry") if isinstance(element.get("geometry"), Mapping) else {"kind": "bbox", "bbox": [bbox[0], bbox[1], bbox[0] + bbox[2], bbox[1] + bbox[3]]},
        z_order=int(element.get("z_index") or 0),
        confidence="medium",
        processing_intent=ProcessingIntent(
            object_type=role,
            processing_type=processing_type,
            parameters={
                "prompt": _image_processor_prompt(element, processing_type=processing_type),
                "runtime_config": _image_processor_runtime_config(element),
            },
        ),
        review_status="agent_refined",
        created_by_stage="asset_prepare",
        change_reason=str(_mapping_text(element.get("metadata"), "change_reason") or "PageSpec asset_prepare image processor."),
    )
```

Add prompt helpers that mention bbox, role, text, and placement:

```python
def _source_ref_ids(element: Mapping[str, Any]) -> tuple[str, ...]:
    refs = element.get("source_refs")
    if isinstance(refs, str) or not isinstance(refs, Sequence):
        return ()
    ids: list[str] = []
    for ref in refs:
        if isinstance(ref, Mapping) and isinstance(ref.get("id"), str) and ref["id"]:
            ids.append(str(ref["id"]))
    return tuple(ids)


def _mapping_text(value: Any, key: str) -> str:
    if isinstance(value, Mapping):
        item = value.get(key)
        if isinstance(item, str):
            return item
    return ""


def _image_processor_runtime_config(element: Mapping[str, Any]) -> dict[str, Any]:
    build = element.get("build")
    parameters = build.get("parameters") if isinstance(build, Mapping) else None
    if isinstance(parameters, Mapping):
        runtime_config = parameters.get("runtime_config")
        if isinstance(runtime_config, Mapping):
            return dict(runtime_config)
        allowed = {
            key: parameters[key]
            for key in ("size", "quality", "background", "output_format", "output_compression")
            if key in parameters
        }
        if allowed:
            return allowed
    return {}


def _image_processor_prompt(element: Mapping[str, Any], *, processing_type: str) -> str:
    element_id = _required_string(element.get("id"), "element.id")
    bbox = _bbox_xywh(element)
    role = str(element.get("role") or element.get("kind") or "image")
    text = str(element.get("text") or _mapping_text(element.get("measurement"), "text") or "").strip()
    action = "Generate a clean raster asset" if processing_type == "image_generate" else "Edit the provided source crop into a clean raster asset"
    source_rule = (
        "Synthesize from the semantic description rather than copying source noise."
        if processing_type == "image_generate"
        else "Preserve the original composition, colors, aspect, and visible subject unless cleanup requires minor repair."
    )
    return (
        f"{action} for DrawAI PageSpec element {element_id}. "
        f"Role: {role}. Target box: {bbox[2]:.0f}x{bbox[3]:.0f}px at ({bbox[0]:.0f}, {bbox[1]:.0f}). "
        f"Nearby/source text: {text or 'none'}. {source_rule} "
        "The output will be scaled back into the exact original box, so avoid extra margins, labels, frames, or unrelated background."
    )
```

Update `src/drawai/page_spec_svg.py` so `_render_element()` treats all active materialized raster
assets as image hrefs, not only `crop` and `crop_nobg`:

```python
if processing_type in {"crop", "crop_nobg", "image_generate", "image_edit"} and asset is not None:
```

- [ ] **Step 4: Run tests and verify they pass**

Run:

```bash
uv run --extra dev pytest tests/test_page_spec.py::test_materialize_page_spec_assets_runs_image_generate_and_edit tests/test_page_spec.py::test_draft_semantic_svg_from_materialized_page_spec_uses_active_asset_href -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 2**

```bash
git add src/drawai/page_spec_assets.py src/drawai/page_spec_svg.py tests/test_page_spec.py
git commit -m "feat(processors): materialize page spec image assets"
```

### Task 3: Workbench Provider Routing For Asset Prepare

**Files:**
- Create: `src/drawai/workbench/image_processor_providers.py`
- Modify: `src/drawai/workbench/runner.py`
- Modify: `src/drawai/workbench/api.py`
- Modify: `tests/workbench/test_workflow_api.py`

- [ ] **Step 1: Add failing tests for provider routing**

Add this test to `tests/workbench/test_workflow_api.py`:

```python
def test_asset_prepare_receives_images_api_generate_and_edit_providers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _client(tmp_path)
    preset_response = client.put(
        "/api/workbench/api-presets",
        json={
            "presets": [
                {
                    "id": "apimart_images",
                    "label": "Apimart Images",
                    "type": "images_api",
                    "base_url": "https://api.apimart.example",
                    "model": "gpt-image-2",
                    "api_key": "plain-test-key",
                }
            ]
        },
    )
    assert preset_response.status_code == 200
    settings_response = client.put(
        "/api/workbench/processor-settings",
        json={
            "processors": {
                "image_generate": {
                    "enabled": True,
                    "driver_id": "openai_images_api",
                    "api_preset_id": "apimart_images",
                },
                "image_edit": {
                    "enabled": True,
                    "driver_id": "openai_images_api",
                    "api_preset_id": "apimart_images",
                },
            }
        },
    )
    assert settings_response.status_code == 200

    source = tmp_path / "source.png"
    Image.new("RGBA", (64, 48), (255, 255, 255, 255)).save(source)
    page_spec = {
        "schema": "drawai.page_spec.v1",
        "page_id": "provider-routing",
        "source": {"image": str(source), "width_px": 64, "height_px": 48},
        "canvas": {"width_px": 64, "height_px": 48},
        "background": {},
        "elements": [
            {
                "id": "E001",
                "kind": "image",
                "role": "representation",
                "box_px": [2, 2, 18, 12],
                "z_index": 1,
                "build": {"mode": "asset_ref", "processing_type": "image_generate"},
            },
            {
                "id": "E002",
                "kind": "image",
                "role": "representation",
                "box_px": [24, 2, 18, 12],
                "z_index": 2,
                "build": {"mode": "asset_ref", "processing_type": "image_edit"},
            },
        ],
        "metadata": {},
    }

    upstream_calls: list[str] = []

    def fake_upstream(payload: Mapping[str, object], *, api_url: str, api_key: str | None = None):
        upstream_calls.append(api_url)
        buffer = io.BytesIO()
        Image.new("RGB", (4, 3), "#1f77b4").save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return {"data": [{"id": f"img_{len(upstream_calls)}", "b64_json": encoded}]}

    from drawai.page_spec_assets import materialize_page_spec_assets
    from drawai.workbench import image_processor_providers as provider_module

    monkeypatch.setattr(provider_module, "call_image_generation_upstream", fake_upstream)
    materialized = materialize_page_spec_assets(
        page_spec,
        source_image_path=source,
        output_dir=tmp_path / "bundle",
        **provider_module.asset_prepare_image_providers(tmp_path / "workspace"),
    )

    assert upstream_calls == [
        "https://api.apimart.example/v1/images/generations",
        "https://api.apimart.example/v1/images/edits",
    ]
    assert materialized["elements"][0]["materialization"]["processing_type"] == "image_generate"
    assert materialized["elements"][1]["materialization"]["processing_type"] == "image_edit"
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```bash
uv run --extra dev pytest tests/workbench/test_workflow_api.py::test_asset_prepare_receives_images_api_generate_and_edit_providers -q
```

Expected: FAIL because `asset_prepare_image_providers` and the edit API provider are missing.

- [ ] **Step 3: Implement API preset providers for generate and edit**

Create `src/drawai/workbench/image_processor_providers.py`. Move the existing Images API provider
logic out of `api.py` into this module so `runner.py` can use the same code without importing the
FastAPI app module:

```python
from __future__ import annotations

import base64
import binascii
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable, Mapping

from fastapi import HTTPException
from PIL import Image

from .api_presets import ApiPreset, api_preset_by_id, read_workbench_api_presets
from .processor_settings import require_processor_configured

MAX_GENERATED_IMAGE_BYTES = 50 * 1024 * 1024
urlopen_external = urllib.request.urlopen


def asset_prepare_image_providers(workspace: str | Path) -> dict[str, Any]:
    providers: dict[str, Any] = {}
    for processor in ("image_generate", "image_edit"):
        try:
            setting = require_processor_configured(workspace, processor)
        except ValueError:
            continue
        if setting.driver_id == "openai_images_api":
            preset = _processor_api_preset(workspace, processor, setting.api_preset_id)
            if processor == "image_generate":
                providers["image_generate"] = images_api_generate_provider(preset)
            else:
                providers["image_edit"] = images_api_edit_provider(preset)
    return providers
```

Add provider factories in the same module:

```python
def images_api_generate_provider(preset: ApiPreset) -> Callable[..., Mapping[str, Any]]:
    def generate(
        *,
        prompt: str,
        output_dir: str | Path,
        task_name: str,
        output_stem: str,
        runtime_config: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        output_path = Path(output_dir).expanduser().resolve(strict=False)
        output_path.mkdir(parents=True, exist_ok=True)
        request_payload = _images_api_payload(preset, prompt, runtime_config=runtime_config)
        response_payload = call_image_generation_upstream(
            request_payload,
            api_url=image_generation_api_url(preset.base_url),
            api_key=_api_preset_key(preset),
        )
        image_payload = _materialize_first_images_api_image(response_payload, output_dir=output_path, output_stem=output_stem)
        return _provider_result("generate", preset, prompt, output_path, task_name, image_payload)

    return generate


def images_api_edit_provider(preset: ApiPreset) -> Callable[..., Mapping[str, Any]]:
    def edit(
        *,
        source_image_path: str | Path,
        prompt: str,
        output_dir: str | Path,
        task_name: str,
        output_stem: str,
        runtime_config: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        output_path = Path(output_dir).expanduser().resolve(strict=False)
        output_path.mkdir(parents=True, exist_ok=True)
        request_payload = _images_api_payload(preset, prompt, runtime_config=runtime_config)
        response_payload = call_image_generation_upstream(
            request_payload,
            api_url=image_edit_api_url(preset.base_url),
            api_key=_api_preset_key(preset),
        )
        image_payload = _materialize_first_images_api_image(response_payload, output_dir=output_path, output_stem=output_stem)
        result = _provider_result("edit", preset, prompt, output_path, task_name, image_payload)
        result["source_image_path"] = str(source_image_path)
        return result

    return edit
```

Add URL helpers:

```python
def image_generation_api_url(base_url: Any = None) -> str:
    return _image_api_url(base_url, endpoint="generations")


def image_edit_api_url(base_url: Any = None) -> str:
    return _image_api_url(base_url, endpoint="edits")


def _image_api_url(base_url: Any, *, endpoint: str) -> str:
    parsed = urllib.parse.urlparse(str(base_url or "").strip() or "https://api.openai.com")
    path = parsed.path.rstrip("/")
    suffix = f"/images/{endpoint}"
    if path.endswith(suffix):
        endpoint_path = path
    elif path.endswith("/v1"):
        endpoint_path = f"{path}{suffix}"
    elif path:
        endpoint_path = f"{path}/v1/images/{endpoint}"
    else:
        endpoint_path = f"/v1/images/{endpoint}"
    return urllib.parse.urlunparse(parsed._replace(path=endpoint_path))
```

Add request, materialization, and metadata helpers by moving the existing API code for
`_call_image_generation_upstream`, `_materialize_first_images_api_image`,
`_images_api_record_bytes`, `_images_api_response_metadata`, `_image_generation_payload_records`,
`_api_preset_key`, `_image_suffix_from_mime`, `_safe_download_stem`, and `_unique_upload_path`
into `image_processor_providers.py`. Rename the upstream request function to
`call_image_generation_upstream`. Preserve the existing JSON request body and output shape.

In `src/drawai/workbench/api.py`, import the shared functions and keep the old private names as
aliases so existing tests and endpoints continue to work:

```python
from .image_processor_providers import (
    asset_prepare_image_providers as _asset_prepare_image_providers,
    call_image_generation_upstream as _call_image_generation_upstream,
    image_edit_api_url as _image_edit_api_url,
    image_generation_api_url as _image_generation_api_url,
    images_api_edit_provider as _images_api_edit_provider,
    images_api_generate_provider as _images_api_generate_provider,
)
```

Delete the duplicate local definitions in `api.py` after the aliases are imported.

In `_run_workflow_processor_node()` for `asset_prepare`, pass providers:

```python
from drawai.workbench.image_processor_providers import asset_prepare_image_providers

image_providers = asset_prepare_image_providers(self.store.workspace)
materialized = materialize_page_spec_assets(
    page_spec,
    source_image_path=source_image,
    output_dir=context.output_dir,
    rmbg_config=rmbg_config,
    rmbg_client=rmbg_client,
    image_generate=image_providers.get("image_generate"),
    image_edit=image_providers.get("image_edit"),
)
```

- [ ] **Step 4: Run tests and verify they pass**

Run:

```bash
uv run --extra dev pytest tests/workbench/test_workflow_api.py::test_asset_processor_providers_routes_images_api_generation_driver tests/workbench/test_workflow_api.py::test_asset_prepare_receives_images_api_generate_and_edit_providers -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 3**

```bash
git add src/drawai/workbench/image_processor_providers.py src/drawai/workbench/api.py src/drawai/workbench/runner.py tests/workbench/test_workflow_api.py
git commit -m "feat(workbench): route asset prepare image providers"
```

### Task 4: Asset Prepare Placement Preview

**Files:**
- Modify: `src/drawai/workbench/runner.py`
- Modify: `tests/workbench/test_store_api.py`

- [ ] **Step 1: Add failing test for placement preview output**

Add to `tests/workbench/test_store_api.py`:

```python
def test_workflow_asset_prepare_writes_processor_preview_svg(tmp_path: Path) -> None:
    store = WorkbenchStore(tmp_path / "workspace")
    base_config = _base_config(tmp_path)
    source = tmp_path / "single.png"
    Image.new("RGB", (64, 48), "white").save(source)
    case = store.create_batch("preview", [source]).cases[0]
    runner = WorkbenchRunner(store, _settings(tmp_path, base_config), stage_executor=_deterministic_stage_executor)
    runner._run_stage(case.case_id, "process_assets")

    root = Path(store.get_case(case.case_id).run_root)
    preview = root / "nodes" / "asset_prepare" / "runs" / "001" / "output" / "processor_preview.svg"
    assert preview.is_file()
    assert "data-drawai-source=\"page-spec-svg-draft\"" in preview.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```bash
uv run --extra dev pytest tests/workbench/test_store_api.py::test_workflow_asset_prepare_writes_processor_preview_svg -q
```

Expected: FAIL because `asset_prepare` only writes `page_spec.json`.

- [ ] **Step 3: Write deterministic preview from `asset_prepare`**

In `src/drawai/workbench/runner.py`, import:

```python
from drawai.page_spec_svg import draft_semantic_svg_from_page_spec
```

After writing `output_path = write_page_spec(context.output_dir / "page_spec.json", materialized)`,
add:

```python
preview_svg = context.output_dir / "processor_preview.svg"
draft_semantic_svg_from_page_spec(output_path, preview_svg, href_base_dir=Path(case.run_root) / "svg")
```

Add a second output port to the processor-test template's `asset_prepare` node:

```python
_output(
    "processor_preview",
    "Processor Preview",
    ("semantic_svg",),
    formats=("drawai.semantic_svg.v1",),
    deliverable=True,
    description="Deterministic SVG preview that places processed active assets back into PageSpec boxes.",
)
```

Return both outputs from runner:

```python
return (
    _workflow_output(context, "page_spec", output_path, "page_spec", "drawai.page_spec.v1"),
    _workflow_output(context, "processor_preview", preview_svg, "semantic_svg", "drawai.semantic_svg.v1"),
)
```

- [ ] **Step 4: Run test and verify it passes**

Run:

```bash
uv run --extra dev pytest tests/workbench/test_store_api.py::test_workflow_asset_prepare_writes_processor_preview_svg -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 4**

```bash
git add src/drawai/workbench/runner.py src/drawai/workflow/templates.py tests/workbench/test_store_api.py
git commit -m "feat(workbench): preview asset prepare placements"
```

### Task 5: Parallel Processing Verification

**Files:**
- Modify: `tests/test_page_spec.py`
- Modify: `src/drawai/page_spec_assets.py`

- [ ] **Step 1: Add failing concurrency test**

Add imports to `tests/test_page_spec.py`:

```python
import threading
from concurrent.futures import ThreadPoolExecutor
```

Add to `tests/test_page_spec.py`:

```python
def test_materialize_page_spec_assets_processes_image_elements_in_parallel(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGBA", (96, 64), (255, 255, 255, 255)).save(source)
    started = threading.Barrier(2)
    release = threading.Event()
    calls: list[str] = []

    def blocking_generate(**kwargs):
        calls.append(str(kwargs["prompt"]))
        result_dir = Path(kwargs["output_dir"])
        result_dir.mkdir(parents=True, exist_ok=True)
        started.wait(timeout=2)
        release.wait(timeout=2)
        result_path = result_dir / "generated.png"
        Image.new("RGBA", (8, 8), (20, 90, 220, 255)).save(result_path)
        return _FakeProviderResult("generate", result_dir, result_path)

    page_spec = _page_spec(
        "refine",
        [
            {
                "id": "E001",
                "kind": "image",
                "role": "representation",
                "box_px": [2, 3, 8, 8],
                "z_index": 1,
                "build": {"mode": "asset_ref", "processing_type": "image_generate"},
            },
            {
                "id": "E002",
                "kind": "image",
                "role": "representation",
                "box_px": [12, 3, 8, 8],
                "z_index": 2,
                "build": {"mode": "asset_ref", "processing_type": "image_generate"},
            },
        ],
    )

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(
            materialize_page_spec_assets,
            page_spec,
            source_image_path=source,
            output_dir=tmp_path / "bundle",
            image_generate=blocking_generate,
            processor_workers=2,
        )
        release.set()
        materialized = future.result(timeout=3)

    assert len(calls) == 2
    assert all(element["materialization"]["status"] == "ok" for element in materialized["elements"])
```

- [ ] **Step 2: Run test and verify it fails before parallel implementation, or passes if Task 2 already implemented it**

Run:

```bash
uv run --extra dev pytest tests/test_page_spec.py::test_materialize_page_spec_assets_processes_image_elements_in_parallel -q
```

Expected: PASS after Task 2's ThreadPoolExecutor implementation.

- [ ] **Step 3: Commit Task 5**

```bash
git add tests/test_page_spec.py src/drawai/page_spec_assets.py
git commit -m "test(processors): cover parallel page spec asset processing"
```

### Task 6: Focused Regression Suite And Frontend Build

**Files:**
- No source files expected. If tests fail, change only the approved processor, PageSpec asset,
  Workbench provider, workflow template, or focused test files from Tasks 1-5.

- [ ] **Step 1: Run focused backend tests**

Run:

```bash
uv run --extra dev pytest tests/test_page_spec.py tests/workflow/test_templates.py tests/workbench/test_workflow_api.py tests/workbench/test_store_api.py -q
```

Expected: PASS.

- [ ] **Step 2: Run frontend tests and build**

Run:

```bash
npm --prefix apps/workbench test
npm --prefix apps/workbench run build
```

Expected: PASS.

- [ ] **Step 3: Run lint/checks for touched Python files**

Run:

```bash
uv run --extra dev ruff check src/drawai/page_spec_assets.py src/drawai/page_spec_svg.py src/drawai/workbench/api.py src/drawai/workbench/runner.py src/drawai/workflow/agent_prompt_defaults.py src/drawai/workflow/templates.py tests/test_page_spec.py tests/workflow/test_templates.py tests/workbench/test_workflow_api.py tests/workbench/test_store_api.py
git diff --check
```

Expected: PASS.

### Task 7: Live Workbench And Chrome Verification

**Files:**
- No source files expected. If live verification exposes a bug, change only the approved processor,
  PageSpec asset, Workbench provider, workflow template, or focused test files from Tasks 1-5.

- [ ] **Step 1: Start backend and frontend from this worktree**

Run backend on an unused port:

```bash
DRAWAI_WORKBENCH_WORKSPACE=/tmp/drawai-processor-test-workbench uv run drawai-workbench-api --host 127.0.0.1 --port 8897
```

Run frontend on an unused port:

```bash
DRAWAI_WORKBENCH_API_URL=http://127.0.0.1:8897 npm --prefix apps/workbench run dev -- --host 127.0.0.1 --port 5179
```

Expected: backend serves `/api/health`, frontend serves `http://127.0.0.1:5179/`.

- [ ] **Step 2: Configure Apimart processor settings in Workbench**

Use Chrome to open `http://127.0.0.1:5179/`. In settings:

```text
API preset:
  id: apimart_images
  type: images_api
  base_url: the existing Apimart Images API base URL from current Workbench settings or environment
  model: the existing configured Apimart image model

Processor:
  image_generate enabled, driver openai_images_api, preset apimart_images
  image_edit enabled, driver openai_images_api, preset apimart_images
```

Expected: settings validation marks both processors configured.

- [ ] **Step 3: Run Apimart processor-test DAG**

Create a batch using:

```text
Image: /Users/chunqiu/Downloads/飞书20260608-121226.jpg
Workflow: Processor Test / PageSpec Assets
Execution: auto-run through asset_prepare
```

Expected:

- `page_spec_refine` completes.
- `asset_prepare` completes.
- `asset_prepare` viewer shows a mix of `image_generate`, `image_edit`, `crop`, `crop_nobg`, and `no_process`.
- Most image-like elements in Representation columns 2, 3, 4 and Future representations are `image_generate` or `image_edit`.
- Not all elements are image generated or edited.
- `processor_preview.svg` places active results back into the original boxes.

- [ ] **Step 4: Run Codex built-in processor-test DAG**

Switch processor settings:

```text
image_generate enabled, driver codex_imagegen_builtin
image_edit enabled, driver codex_image_edit_builtin
```

Create a second batch with the same image and workflow.

Expected: same acceptance criteria as the Apimart run.

- [ ] **Step 5: Capture verification evidence**

Record in the final response:

```text
Backend URL
Frontend URL
Apimart case id
Codex case id
Processor distribution after Refine/Asset Prepare
Preview artifact paths
Any residual visual issues
```

### Task 8: Final Commit

**Files:**
- All touched files from implementation tasks.

- [ ] **Step 1: Inspect final diff**

Run:

```bash
git status --short
git diff --stat
git log --oneline --max-count=8
```

Expected: only files in the approved scope are changed, and implementation commits are present after the design and plan commits.

- [ ] **Step 2: Commit any remaining fixes**

If Task 6 or Task 7 produced fixes after the task commits, commit them:

```bash
git add <touched approved files>
git commit -m "fix(processors): harden asset prepare image processing"
```

Expected: clean working tree except running local artifacts that are gitignored.

- [ ] **Step 3: Push if branch has an upstream**

If this detached worktree is moved to a branch or already has an upstream, push it:

```bash
git push
```

Expected: push succeeds. If still detached, report the final commit hashes and do not invent a remote branch without user direction.
