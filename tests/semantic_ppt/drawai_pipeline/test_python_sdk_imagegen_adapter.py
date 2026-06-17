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
