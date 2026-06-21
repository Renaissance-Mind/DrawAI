import base64
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
from PIL import Image

from drawai.codex_python_sdk_imagegen import (
    CodexPythonSdkImageGenError,
    check_codex_python_sdk_imagegen_capability,
    invoke_codex_python_sdk_image_edit,
    invoke_codex_python_sdk_image_reference_context,
    invoke_codex_python_sdk_imagegen,
)


class FakeAbsolutePathBuf:
    def __init__(self, path: Path):
        self.root = str(path)

    def __str__(self) -> str:
        return f"root={self.root!r}"


def test_codex_python_sdk_imagegen_copies_saved_image_and_sanitizes_archive(
    monkeypatch, tmp_path
):
    seen = {}
    source_holder = {}

    class FakeClient:
        def request(self, method, params, *, response_model):
            seen["capability_method"] = method
            return SimpleNamespace(
                image_generation=True,
                namespace_tools=True,
                web_search=False,
                model_dump=lambda **_kwargs: {
                    "imageGeneration": True,
                    "namespaceTools": True,
                    "webSearch": False,
                },
            )

    class FakeResult:
        id = "turn-imagegen"
        status = SimpleNamespace(value="completed")
        error = None
        started_at = 1
        completed_at = 2
        duration_ms = 12
        final_response = '{"generated": true}'
        usage = {"total": {"totalTokens": 9}}

        def __init__(self, source_path: Path, image_base64: str):
            self.items = [
                SimpleNamespace(root=SimpleNamespace(type="reasoning", id="rs_1")),
                SimpleNamespace(
                    root=SimpleNamespace(
                        type="imageGeneration",
                        id="ig_test",
                        result=image_base64,
                        revised_prompt="blue cube",
                        saved_path=FakeAbsolutePathBuf(source_path),
                        status="completed",
                    )
                ),
                SimpleNamespace(
                    root=SimpleNamespace(
                        type="agentMessage",
                        phase="final_answer",
                        text='{"generated": true}',
                    )
                ),
            ]

    class FakeThread:
        id = "thread-imagegen"

        def run(self, run_input, **kwargs):
            seen["run_input"] = run_input
            seen["run_kwargs"] = kwargs
            codex_home = Path(seen["config"]["env"]["CODEX_HOME"])
            source_path = codex_home / "generated_images" / "turn" / "ig_test.png"
            source_path.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (8, 6), (32, 64, 255)).save(source_path)
            image_base64 = base64.b64encode(source_path.read_bytes()).decode("ascii")
            source_holder["base64"] = image_base64
            return FakeResult(source_path, image_base64)

    class FakeCodex:
        def __init__(self, config):
            seen["config"] = config
            self._client = FakeClient()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            seen["closed"] = True
            return False

        def thread_start(self, **kwargs):
            seen["thread_start_kwargs"] = kwargs
            return FakeThread()

    fake_openai_codex = SimpleNamespace(
        ApprovalMode=SimpleNamespace(deny_all="deny_all"),
        Sandbox=SimpleNamespace(full_access="full_access"),
        Codex=FakeCodex,
        CodexConfig=lambda **kwargs: kwargs,
        TextInput=lambda text: ("text", text),
        generated=SimpleNamespace(
            v2_all=SimpleNamespace(ModelProviderCapabilitiesReadResponse=object)
        ),
    )
    monkeypatch.setitem(sys.modules, "openai_codex", fake_openai_codex)

    result = invoke_codex_python_sdk_imagegen(
        prompt="a blue cube",
        output_dir=tmp_path / "out",
        output_stem="blue-cube",
        runtime_config={"model_name": "fake-model", "timeout_seconds": 1},
        trace_path=tmp_path / "trace.jsonl",
        isolated_cwd=tmp_path / "cwd",
    )

    assert result.runner == "codex_python_sdk_imagegen"
    assert len(result.images) == 1
    generated = result.images[0]
    assert generated.path.name == "blue-cube.png"
    assert generated.path.is_file()
    assert generated.width == 8
    assert generated.height == 6
    assert generated.revised_prompt == "blue cube"
    assert seen["capability_method"] == "modelProvider/capabilities/read"
    assert seen["run_kwargs"]["model"] == "fake-model"
    assert "built-in image generation tool" in seen["run_input"][0][1]
    assert seen["closed"] is True

    summary = json.loads((tmp_path / "out" / "codex_imagegen_result.json").read_text(encoding="utf-8"))
    assert summary["images"][0]["path"] == str(generated.path)
    event_log = (tmp_path / "out" / "codex_session_log" / "codex_session_events.jsonl").read_text(
        encoding="utf-8"
    )
    assert source_holder["base64"] not in event_log
    assert '"base64_chars"' in event_log
    assert '"omitted": true' in event_log


def test_codex_python_sdk_imagegen_rejects_missing_image_item(monkeypatch, tmp_path):
    class FakeClient:
        def request(self, *_args, **_kwargs):
            return SimpleNamespace(model_dump=lambda **_kwargs: {"imageGeneration": True})

    class FakeResult:
        id = "turn-no-image"
        status = SimpleNamespace(value="completed")
        final_response = '{"generated": false}'
        items = [SimpleNamespace(root=SimpleNamespace(type="agentMessage", text="no image"))]
        usage = None
        started_at = None
        completed_at = None
        duration_ms = None

    class FakeThread:
        id = "thread-no-image"

        def run(self, *_args, **_kwargs):
            return FakeResult()

    class FakeCodex:
        def __init__(self, _config):
            self._client = FakeClient()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def thread_start(self, **_kwargs):
            return FakeThread()

    fake_openai_codex = SimpleNamespace(
        ApprovalMode=SimpleNamespace(deny_all="deny_all"),
        Sandbox=SimpleNamespace(full_access="full_access"),
        Codex=FakeCodex,
        CodexConfig=lambda **kwargs: kwargs,
        TextInput=lambda text: ("text", text),
        generated=SimpleNamespace(
            v2_all=SimpleNamespace(ModelProviderCapabilitiesReadResponse=object)
        ),
    )
    monkeypatch.setitem(sys.modules, "openai_codex", fake_openai_codex)

    with pytest.raises(CodexPythonSdkImageGenError, match="did not produce an imageGeneration item"):
        invoke_codex_python_sdk_imagegen(
            prompt="a blue cube",
            output_dir=tmp_path / "out",
            runtime_config={"timeout_seconds": 1},
            isolated_cwd=tmp_path / "cwd",
        )


def test_codex_python_sdk_image_edit_uses_local_image_input(monkeypatch, tmp_path):
    source_image = tmp_path / "source.png"
    Image.new("RGB", (9, 7), (180, 30, 220)).save(source_image)
    seen = {}

    class FakeClient:
        def request(self, *_args, **_kwargs):
            return SimpleNamespace(model_dump=lambda **_kwargs: {"imageGeneration": True})

    class FakeResult:
        id = "turn-edit"
        status = SimpleNamespace(value="completed")
        final_response = '{"edited": true}'
        usage = None
        started_at = None
        completed_at = None
        duration_ms = None

        def __init__(self, edited_path: Path):
            self.items = [
                SimpleNamespace(
                    root=SimpleNamespace(
                        type="imageGeneration",
                        id="ig_edit",
                        result="",
                        revised_prompt="change the center circle to cyan",
                        saved_path=FakeAbsolutePathBuf(edited_path),
                        status="completed",
                    )
                )
            ]

    class FakeThread:
        id = "thread-edit"

        def run(self, run_input, **kwargs):
            seen["run_input"] = run_input
            seen["run_kwargs"] = kwargs
            edited_path = tmp_path / "edited.png"
            Image.new("RGB", (11, 13), (0, 255, 255)).save(edited_path)
            return FakeResult(edited_path)

    class FakeCodex:
        def __init__(self, config):
            seen["config"] = config
            self._client = FakeClient()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def thread_start(self, **kwargs):
            seen["thread_start_kwargs"] = kwargs
            return FakeThread()

    fake_openai_codex = SimpleNamespace(
        ApprovalMode=SimpleNamespace(deny_all="deny_all"),
        Sandbox=SimpleNamespace(full_access="full_access"),
        Codex=FakeCodex,
        CodexConfig=lambda **kwargs: kwargs,
        TextInput=lambda text: ("text", text),
        LocalImageInput=lambda path: ("local_image", path),
        generated=SimpleNamespace(
            v2_all=SimpleNamespace(ModelProviderCapabilitiesReadResponse=object)
        ),
    )
    monkeypatch.setitem(sys.modules, "openai_codex", fake_openai_codex)

    result = invoke_codex_python_sdk_image_edit(
        source_image_path=source_image,
        prompt="change the center circle to cyan",
        output_dir=tmp_path / "out",
        output_stem="edited",
        runtime_config={"timeout_seconds": 1},
        isolated_cwd=tmp_path / "cwd",
    )

    assert result.operation == "edit"
    assert result.source_image_path == source_image.resolve()
    assert result.images[0].path.name == "edited.png"
    assert result.images[0].width == 11
    assert seen["run_input"][0] == ("local_image", str(source_image.resolve()))
    assert "Edit the supplied image" in seen["run_input"][1][1]
    assert "image editing runner" in seen["thread_start_kwargs"]["developer_instructions"]


def test_codex_python_sdk_reference_context_uses_local_image_without_edit_instruction(monkeypatch, tmp_path):
    source_image = tmp_path / "source.png"
    Image.new("RGB", (10, 12), (255, 0, 255)).save(source_image)
    seen = {}

    class FakeItem:
        type = "imageGeneration"

        def __init__(self, saved_path):
            self.id = "turn-image-reference-context"
            self.status = "completed"
            self.saved_path = FakeAbsolutePathBuf(saved_path)
            self.result = ""
            self.revised_prompt = "reference context revised prompt"

    class FakeResult:
        id = "turn"
        status = "completed"
        started_at = "start"
        completed_at = "end"
        duration_ms = 1
        final_response = '{"generated": true}'
        usage = {}

        def __init__(self, saved_path):
            self.items = [FakeItem(saved_path)]

    class FakeClient:
        def request(self, method, params, *, response_model):
            return SimpleNamespace(
                image_generation=True,
                model_dump=lambda **_kwargs: {"imageGeneration": True},
            )

    class FakeThread:
        id = "thread-image-reference-context"

        def run(self, run_input, **kwargs):
            seen["run_input"] = run_input
            seen["run_kwargs"] = kwargs
            generated_path = tmp_path / "reference_context.png"
            Image.new("RGB", (13, 11), (0, 120, 255)).save(generated_path)
            return FakeResult(generated_path)

    class FakeCodex:
        def __init__(self, config):
            seen["config"] = config
            self._client = FakeClient()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def thread_start(self, **kwargs):
            seen["thread_start_kwargs"] = kwargs
            return FakeThread()

    fake_openai_codex = SimpleNamespace(
        ApprovalMode=SimpleNamespace(deny_all="deny_all"),
        Sandbox=SimpleNamespace(full_access="full_access"),
        Codex=FakeCodex,
        CodexConfig=lambda **kwargs: kwargs,
        TextInput=lambda text: ("text", text),
        LocalImageInput=lambda path: ("local_image", path),
        generated=SimpleNamespace(
            v2_all=SimpleNamespace(ModelProviderCapabilitiesReadResponse=object)
        ),
    )
    monkeypatch.setitem(sys.modules, "openai_codex", fake_openai_codex)

    result = invoke_codex_python_sdk_image_reference_context(
        source_image_path=source_image,
        prompt="use this slide as style reference for a new Transformer page",
        output_dir=tmp_path / "out",
        output_stem="reference-context",
        runtime_config={"timeout_seconds": 1},
        isolated_cwd=tmp_path / "cwd",
    )

    assert result.operation == "reference_context"
    assert result.source_image_path == source_image.resolve()
    assert result.images[0].path.name == "reference-context.png"
    assert seen["run_input"][0] == ("local_image", str(source_image.resolve()))
    assert "Generate one new image using the supplied image as visual context/reference" in seen["run_input"][1][1]
    assert "image generation runner with a visual reference image" in seen["thread_start_kwargs"]["developer_instructions"]
    assert "image editing runner" not in seen["thread_start_kwargs"]["developer_instructions"]


def test_codex_python_sdk_imagegen_capability_probe_reports_runtime(monkeypatch, tmp_path):
    class FakeClient:
        def request(self, method, _params, *, response_model):
            assert method == "modelProvider/capabilities/read"
            return SimpleNamespace(
                model_dump=lambda **_kwargs: {
                    "imageGeneration": True,
                    "namespaceTools": True,
                    "webSearch": False,
                }
            )

    class FakeCodex:
        def __init__(self, _config):
            self._client = FakeClient()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    fake_openai_codex = SimpleNamespace(
        Codex=FakeCodex,
        CodexConfig=lambda **kwargs: kwargs,
        generated=SimpleNamespace(
            v2_all=SimpleNamespace(ModelProviderCapabilitiesReadResponse=object)
        ),
    )
    monkeypatch.setitem(sys.modules, "openai_codex", fake_openai_codex)

    capabilities = check_codex_python_sdk_imagegen_capability(
        timeout_seconds=1,
        isolated_cwd=tmp_path / "cwd",
    )

    assert capabilities["imageGeneration"] is True
    assert capabilities["probe_duration_ms"] >= 0
