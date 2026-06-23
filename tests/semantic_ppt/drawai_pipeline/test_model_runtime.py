import json
import sys
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from drawai import model_runtime


def test_invoke_vision_text_passes_runtime_timeout(monkeypatch, tmp_path: Path):
    image = tmp_path / "figure.png"
    Image.new("RGB", (4, 4), "white").save(image)
    captured = {}

    async def fake_invoke_openai_compatible_response(**kwargs):
        captured["timeout_seconds"] = kwargs["timeout_seconds"]
        captured["model_name"] = kwargs["settings"].model_name
        return "ok"

    monkeypatch.setattr(model_runtime, "_invoke_openai_compatible_response", fake_invoke_openai_compatible_response)

    result = model_runtime.invoke_vision_text(
        image_paths=[image],
        prompt="describe",
        task_name="timeout_test",
        runtime_config={"provider": "fake", "model_name": "fake-model", "timeout_seconds": 900},
    )

    assert result == "ok"
    assert captured["timeout_seconds"] == 900
    assert captured["model_name"] == "fake-model"


def test_invoke_multimodal_text_allows_text_only(monkeypatch):
    captured = {}

    async def fake_invoke_openai_compatible_response(**kwargs):
        captured["input_content"] = kwargs["input_content"]
        captured["model_name"] = kwargs["settings"].model_name
        return "ok"

    monkeypatch.setattr(model_runtime, "_invoke_openai_compatible_response", fake_invoke_openai_compatible_response)

    result = model_runtime.invoke_multimodal_text(
        image_paths=(),
        prompt="return json",
        task_name="text_only",
        runtime_config={"provider": "fake", "model_name": "fake-model"},
    )

    assert result == "ok"
    assert captured["input_content"] == [{"type": "input_text", "text": "return json"}]
    assert captured["model_name"] == "fake-model"


def test_invoke_multimodal_text_can_use_chat_completions_with_extra_body(monkeypatch):
    captured = {}

    async def fake_chat_completion(**kwargs):
        captured["input_content"] = kwargs["input_content"]
        captured["extra_body"] = kwargs["settings"].extra_body
        captured["wire_api"] = kwargs["settings"].wire_api
        return "ok"

    monkeypatch.setattr(model_runtime, "_invoke_openai_compatible_chat_completion", fake_chat_completion)

    result = model_runtime.invoke_multimodal_text(
        image_paths=(),
        prompt="return json",
        task_name="chat_completion",
        runtime_config={
            "provider": "openrouter",
            "model_name": "minimax/minimax-m3",
            "wire_api": "chat_completions",
            "extra_body": {"reasoning": {"enabled": True}},
        },
    )

    assert result == "ok"
    assert captured["input_content"] == [{"type": "input_text", "text": "return json"}]
    assert captured["extra_body"] == {"reasoning": {"enabled": True}}
    assert captured["wire_api"] == "chat_completions"


def test_invoke_multimodal_text_saves_provider_reasoning_details(monkeypatch, tmp_path: Path):
    class FakeCompletions:
        async def create(self, **_kwargs):
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content="ok",
                            reasoning_details=[
                                {"type": "reasoning.text", "text": "kept provider reasoning"}
                            ],
                        )
                    )
                ],
                usage=SimpleNamespace(total_tokens=3),
            )

    class FakeAsyncOpenAI:
        def __init__(self, **_kwargs):
            self.chat = SimpleNamespace(completions=FakeCompletions())

        async def close(self):
            return None

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(AsyncOpenAI=FakeAsyncOpenAI))
    trace_path = tmp_path / "llm_trace.jsonl"

    result = model_runtime.invoke_multimodal_text(
        image_paths=(),
        prompt="return json",
        task_name="reasoning_capture",
        runtime_config={
            "provider": "openrouter",
            "model_name": "minimax/minimax-m3",
            "wire_api": "chat_completions",
        },
        trace_path=trace_path,
    )

    provider_response_path = tmp_path / "llm_provider_response.jsonl"
    provider_response = json.loads(provider_response_path.read_text(encoding="utf-8").splitlines()[0])
    message = provider_response["response"]["choices"][0]["message"]
    assert result == "ok"
    assert message["content"] == "ok"
    assert message["reasoning_details"] == [
        {"type": "reasoning.text", "text": "kept provider reasoning"}
    ]


def test_invoke_multimodal_text_disables_reasoning_for_direct_outputs(monkeypatch):
    captured = {}

    async def fake_chat_completion(**kwargs):
        captured["extra_body"] = kwargs["settings"].extra_body
        return "ok"

    monkeypatch.setattr(model_runtime, "_invoke_openai_compatible_chat_completion", fake_chat_completion)

    result = model_runtime.invoke_multimodal_text(
        image_paths=(),
        prompt="return json",
        task_name="direct_output",
        runtime_config={
            "provider": "openrouter",
            "model_name": "minimax/minimax-m3",
            "wire_api": "chat_completions",
            "direct_output": True,
            "extra_body": {
                "reasoning": {"enabled": True},
                "thinking": {"type": "adaptive"},
            },
        },
    )

    assert result == "ok"
    assert captured["extra_body"] == {
        "reasoning": {"enabled": False},
        "thinking": {"type": "disabled"},
    }


def test_invoke_multimodal_text_retries_direct_outputs_with_stripped_reasoning(monkeypatch):
    captured = []

    async def fake_chat_completion(**kwargs):
        captured.append(kwargs["settings"].extra_body)
        return "" if len(captured) == 1 else "ok"

    monkeypatch.setattr(model_runtime, "_invoke_openai_compatible_chat_completion", fake_chat_completion)

    result = model_runtime.invoke_multimodal_text(
        image_paths=(),
        prompt="return json",
        task_name="direct_output_retry",
        runtime_config={
            "provider": "openrouter",
            "model_name": "minimax/minimax-m3",
            "wire_api": "chat_completions",
            "direct_output": True,
            "extra_body": {
                "reasoning": {"enabled": True},
                "thinking": {"type": "adaptive"},
                "metadata": {"trace": "keep"},
            },
        },
    )

    assert result == "ok"
    assert captured == [
        {
            "reasoning": {"enabled": False},
            "thinking": {"type": "disabled"},
            "metadata": {"trace": "keep"},
        },
        {"metadata": {"trace": "keep"}},
    ]


def test_invoke_multimodal_text_retries_with_provider_token_cap(monkeypatch):
    captured = []

    async def fake_chat_completion(**kwargs):
        captured.append(kwargs["max_output_tokens"])
        if len(captured) == 1:
            raise RuntimeError("Range of max_tokens should be [1, 32768]")
        return "ok"

    monkeypatch.setattr(model_runtime, "_invoke_openai_compatible_chat_completion", fake_chat_completion)

    result = model_runtime.invoke_multimodal_text(
        image_paths=(),
        prompt="return svg",
        task_name="token_cap_retry",
        runtime_config={
            "provider": "dashscope",
            "model_name": "qwen3-vl-plus",
            "wire_api": "chat_completions",
        },
        max_output_tokens=65536,
    )

    assert result == "ok"
    assert captured == [65536, 32768]


def test_invoke_multimodal_text_retries_rate_limits(monkeypatch):
    captured = []
    sleeps = []

    class FakeRateLimitError(Exception):
        pass

    async def fake_chat_completion(**kwargs):
        captured.append(kwargs["max_output_tokens"])
        if len(captured) == 1:
            raise FakeRateLimitError("429 limit_burst_rate: Request rate increased too quickly")
        return "ok"

    monkeypatch.setattr(model_runtime, "_invoke_openai_compatible_chat_completion", fake_chat_completion)
    monkeypatch.setattr(model_runtime.time, "sleep", lambda seconds: sleeps.append(seconds))

    result = model_runtime.invoke_multimodal_text(
        image_paths=(),
        prompt="return svg",
        task_name="rate_limit_retry",
        runtime_config={
            "provider": "dashscope",
            "model_name": "qwen3-vl-plus",
            "wire_api": "chat_completions",
        },
    )

    assert result == "ok"
    assert captured == [4096, 4096]
    assert sleeps == [10.0]
