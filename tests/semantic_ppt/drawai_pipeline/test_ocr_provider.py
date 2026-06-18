import io
import json
import urllib.error
from email.message import Message
from pathlib import Path

import pytest
from PIL import Image

from drawai.config import load_drawai_config
from drawai.model_runtime import _sanitize_trace_value
from drawai.ocr_provider import (
    FixtureOcrBoxProvider,
    HttpJsonTransport,
    OcrHttpStatusError,
    OcrProviderError,
    RemotePaddleOcrProvider,
    build_ocr_provider,
    clamp_ocr_boxes_to_canvas,
)


def test_fixture_ocr_provider_reads_boxes(tmp_path: Path):
    fixture = tmp_path / "ocr.json"
    fixture.write_text(
        '{"ocr_text_boxes":[{"id":"T001","bbox":[1,2,30,10],"confidence":0.9,"source":"fixture"}]}',
        encoding="utf-8",
    )
    provider = FixtureOcrBoxProvider(fixture)
    assert provider.extract_boxes(tmp_path / "unused.png")["ocr_text_boxes"][0]["id"] == "T001"


def test_fixture_ocr_provider_assigns_missing_ids(tmp_path: Path):
    fixture = tmp_path / "ocr.json"
    fixture.write_text(
        json.dumps(
            [
                {"bbox": [10, 20, 40, 30], "confidence": 0.8},
                {"bbox": [50, 60, 90, 80], "confidence": 0.6},
            ]
        ),
        encoding="utf-8",
    )
    provider = FixtureOcrBoxProvider(fixture)

    result = provider.extract_boxes(tmp_path / "unused.png")

    assert [box["id"] for box in result["ocr_text_boxes"]] == ["T001", "T002"]
    assert [box["source"] for box in result["ocr_text_boxes"]] == ["fixture", "fixture"]


def test_fixture_ocr_provider_skips_malformed_bboxes(tmp_path: Path):
    fixture = tmp_path / "ocr.json"
    fixture.write_text(
        json.dumps(
            {
                "ocr_text_boxes": [
                    {"bbox": [1, 2, 20, 10], "confidence": 0.9},
                    {"bbox": [1, 2, 3], "confidence": 0.7},
                    {"bbox": [10, 10, 5, 20], "confidence": 0.8},
                    {"bbox": ["bad", 2, 30, 10], "confidence": 0.5},
                ]
            }
        ),
        encoding="utf-8",
    )
    provider = FixtureOcrBoxProvider(fixture)

    result = provider.extract_boxes(tmp_path / "unused.png")

    assert len(result["ocr_text_boxes"]) == 1
    assert result["ocr_text_boxes"][0]["bbox"] == [1, 2, 20, 10]


def test_fixture_ocr_provider_rejects_missing_ocr_text_boxes(tmp_path: Path):
    fixture = tmp_path / "ocr.json"
    fixture.write_text("{}", encoding="utf-8")
    provider = FixtureOcrBoxProvider(fixture)

    with pytest.raises(OcrProviderError, match="ocr_text_boxes"):
        provider.extract_boxes(tmp_path / "unused.png")


def test_fixture_ocr_provider_accepts_explicit_empty_ocr_text_boxes(tmp_path: Path):
    fixture = tmp_path / "ocr.json"
    fixture.write_text('{"ocr_text_boxes":[]}', encoding="utf-8")
    provider = FixtureOcrBoxProvider(fixture)

    result = provider.extract_boxes(tmp_path / "unused.png")

    assert result["ocr_text_boxes"] == []


def test_fixture_ocr_provider_rejects_legacy_model_stub_boxes(tmp_path: Path):
    fixture = tmp_path / "ocr.json"
    fixture.write_text(
        json.dumps(
            {
                "ocr_text_boxes": [
                    {
                        "id": "T001",
                        "bbox": [1, 2, 30, 10],
                        "confidence": 0.9,
                        "source": "model_stub",
                        "text": "legacy",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    provider = FixtureOcrBoxProvider(fixture)

    with pytest.raises(OcrProviderError, match="model_stub"):
        provider.extract_boxes(tmp_path / "unused.png")


def test_remote_paddleocr_provider_posts_image(tmp_path: Path):
    image = tmp_path / "figure.png"
    Image.new("RGB", (20, 10), "white").save(image)
    calls = []

    class FakeTransport:
        def post_json(self, path, payload, timeout_s):
            calls.append((path, payload, timeout_s))
            return {"ocr_text_boxes": [{"bbox": [1, 1, 5, 5], "confidence": 0.8}]}, 10.0

    provider = RemotePaddleOcrProvider(base_url="http://ocr.local", timeout_seconds=3, transport=FakeTransport())
    result = provider.extract_boxes(image)
    assert calls[0][0] == "/v1/ocr/boxes"
    assert result["ocr_text_boxes"][0]["source"] == "remote_paddleocr"


def test_remote_paddleocr_provider_retries_transient_concurrency_limit(tmp_path: Path):
    image = tmp_path / "figure.png"
    Image.new("RGB", (20, 10), "white").save(image)
    calls = []
    sleeps = []

    class FakeTransport:
        def post_json(self, path, payload, timeout_s):
            calls.append((path, payload, timeout_s))
            if len(calls) < 3:
                raise OcrHttpStatusError(
                    "Remote PaddleOCR HTTP error; http_status=429; body_excerpt='concurrency limit 3'",
                    http_status=429,
                    body_excerpt="concurrency limit 3",
                )
            return {"ocr_text_boxes": [{"bbox": [1, 1, 5, 5], "confidence": 0.8}]}, 10.0

    provider = RemotePaddleOcrProvider(
        base_url="http://ocr.local",
        timeout_seconds=3,
        transport=FakeTransport(),
        retry_base_delay_seconds=0.5,
        retry_max_delay_seconds=2.0,
        sleep=sleeps.append,
    )

    result = provider.extract_boxes(image)

    assert len(calls) == 3
    assert sleeps == [0.5, 1.0]
    assert result["ocr_text_boxes"][0]["source"] == "remote_paddleocr"


def test_http_json_transport_retries_model_busy_without_counting_queue_as_inference_timeout(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return b'{"ocr_text_boxes":[]}'

    calls = []
    sleeps = []

    def fake_urlopen(request, timeout):
        calls.append((request.full_url, timeout))
        if len(calls) == 1:
            headers = Message()
            headers.add_header("Retry-After", "0")
            headers.add_header("X-DrawAI-Queue", "model-busy")
            raise urllib.error.HTTPError(
                request.full_url,
                503,
                "Service Unavailable",
                headers,
                io.BytesIO(b'{"detail":{"code":"model_busy","retry_after_seconds":0}}'),
            )
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr("drawai.ocr_provider.time.sleep", sleeps.append)
    transport = HttpJsonTransport("http://ocr.test")

    payload, _elapsed_ms = transport.post_json("/v1/ocr/boxes", {"x": 1}, 7)

    assert payload["ocr_text_boxes"] == []
    assert calls == [
        ("http://ocr.test/v1/ocr/boxes", 7),
        ("http://ocr.test/v1/ocr/boxes", 7),
    ]
    assert sleeps == [0.0]


def test_remote_paddleocr_provider_rejects_missing_ocr_text_boxes(tmp_path: Path):
    image = tmp_path / "figure.png"
    Image.new("RGB", (20, 10), "white").save(image)

    class FakeTransport:
        def post_json(self, path, payload, timeout_s):
            return {"error": "service unavailable"}, 10.0

    provider = RemotePaddleOcrProvider(base_url="http://ocr.local", timeout_seconds=3, transport=FakeTransport())

    with pytest.raises(OcrProviderError, match="ocr_text_boxes"):
        provider.extract_boxes(image)


def test_remote_paddleocr_provider_rejects_legacy_model_stub_boxes(tmp_path: Path):
    image = tmp_path / "figure.png"
    Image.new("RGB", (20, 10), "white").save(image)

    class FakeTransport:
        def post_json(self, path, payload, timeout_s):
            return {
                "ocr_text_boxes": [
                    {"id": "T001", "bbox": [1, 1, 5, 5], "confidence": 0.8, "source": "model_stub"}
                ]
            }, 10.0

    provider = RemotePaddleOcrProvider(base_url="http://ocr.local", timeout_seconds=3, transport=FakeTransport())

    with pytest.raises(OcrProviderError, match="model_stub"):
        provider.extract_boxes(image)


def test_remote_paddleocr_result_does_not_include_full_base64(tmp_path: Path):
    image = tmp_path / "figure.png"
    Image.new("RGB", (20, 10), "white").save(image)
    calls = []

    class FakeTransport:
        def post_json(self, path, payload, timeout_s):
            calls.append((path, payload, timeout_s))
            return {
                "ocr_text_boxes": [{"bbox": [1, 1, 5, 5], "confidence": 0.8}],
                "image_base64": payload["image_base64"],
            }, 10.0

    provider = RemotePaddleOcrProvider(base_url="http://ocr.local", timeout_seconds=3, transport=FakeTransport())
    result = provider.extract_boxes(image)

    sent_base64 = calls[0][1]["image_base64"]
    assert sent_base64
    assert "image_base64" in calls[0][1]
    assert "image_base64" not in result
    assert sent_base64 not in json.dumps(result)


def test_clamp_ocr_boxes_to_canvas_clamps_overflow_and_drops_collapsed_boxes():
    payload = {
        "provider": "fixture",
        "ocr_text_boxes": [
            {"id": "T001", "bbox": [-10, 5, 120, 50], "text": "wide"},
            {"id": "T002", "bbox": [95, 10, 120, 40], "text": "edge"},
            {"id": "T003", "bbox": [105, 10, 120, 40], "text": "outside"},
        ],
    }

    result = clamp_ocr_boxes_to_canvas(payload, canvas_width=100, canvas_height=80)

    assert result["provider"] == "fixture"
    assert [box["id"] for box in result["ocr_text_boxes"]] == ["T001", "T002"]
    assert result["ocr_text_boxes"][0]["bbox"] == [0, 5, 100, 50]
    assert result["ocr_text_boxes"][1]["bbox"] == [95, 10, 100, 40]


def test_model_runtime_trace_sanitizes_secret_and_base64_patterns():
    raw_base64 = "QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVo="
    event = {
        "message": (
            "provider failed api-key: SECRET4 "
            "Authorization: Basic dXNlcjpwYXNz "
            f"payload={raw_base64} data:image/png;base64,{raw_base64}"
        ),
        "headers": {
            "x-api-key": "SECRET",
            "api-key": "SECRET3",
            "ordinary": "kept",
        },
        "payload": raw_base64,
    }

    serialized = json.dumps(_sanitize_trace_value(event), ensure_ascii=False)

    assert "SECRET" not in serialized
    assert "SECRET3" not in serialized
    assert "SECRET4" not in serialized
    assert "dXNlcjpwYXNz" not in serialized
    assert raw_base64 not in serialized
    assert "data:image/png;base64" not in serialized
    assert "kept" in serialized


def test_default_config_loads_ocr_nested_settings():
    cfg = load_drawai_config("configs/drawai/config.yaml", validate_input_exists=False)

    assert cfg.ocr.provider == "remote_paddleocr"
    assert cfg.ocr.remote_paddleocr.base_url == "http://127.0.0.1:18080"
    assert cfg.ocr.remote_paddleocr.timeout_seconds == 600


def test_model_stub_is_not_a_supported_ocr_provider():
    class Config:
        provider = "model_stub"

    with pytest.raises(OcrProviderError, match="Unsupported OCR provider"):
        build_ocr_provider(Config())
