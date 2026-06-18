import os
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch

import drawai.local_runtime as local_runtime
from drawai.local_runtime import (
    LocalPaddleOcrProvider,
    LocalRuntimePaths,
    _sam3_cpu_edt_fallback,
    install_sam3_edt_fallback_if_needed,
    _resolve_sam3_torch_device,
    _resolve_torch_device,
    _sam3_torch_factory_device_patch,
    _sam3_torch_runtime_device_patch,
)


def test_sam3_mps_request_falls_back_to_cpu_without_disabling_rmbg_mps():
    assert _resolve_sam3_torch_device("mps") == "cpu"
    assert _resolve_torch_device("mps") == "mps"


def test_sam3_edt_fallback_uses_cpu_distance_transform():
    data = torch.tensor(
        [
            [
                [0, 1, 1],
                [0, 1, 1],
                [0, 0, 0],
            ]
        ],
        dtype=torch.bool,
    )

    result = _sam3_cpu_edt_fallback(data)

    assert result.device.type == "cpu"
    np.testing.assert_allclose(
        result.numpy(),
        np.array(
            [
                [
                    [0.0, 1.0, 2.0],
                    [0.0, 1.0, 1.0],
                    [0.0, 0.0, 0.0],
                ]
            ],
            dtype=np.float32,
        ),
        atol=1e-6,
    )


def test_sam3_edt_fallback_module_installs_when_triton_missing(monkeypatch):
    monkeypatch.delitem(sys.modules, "sam3.model.edt", raising=False)
    monkeypatch.setattr("importlib.util.find_spec", lambda name: None if name == "triton" else object())

    install_sam3_edt_fallback_if_needed()

    module = sys.modules["sam3.model.edt"]
    assert module.edt_triton is _sam3_cpu_edt_fallback


def test_sam3_edt_fallback_module_keeps_existing_module(monkeypatch):
    existing = SimpleNamespace(edt_triton=lambda data: data)
    monkeypatch.setitem(sys.modules, "sam3.model.edt", existing)

    install_sam3_edt_fallback_if_needed()

    assert sys.modules["sam3.model.edt"] is existing


def test_sam3_edt_fallback_module_skips_when_triton_exists(monkeypatch):
    monkeypatch.delitem(sys.modules, "sam3.model.edt", raising=False)
    monkeypatch.setattr("importlib.util.find_spec", lambda name: object())

    install_sam3_edt_fallback_if_needed()

    assert "sam3.model.edt" not in sys.modules


def test_auto_torch_device_prefers_cuda(monkeypatch):
    fake_torch = SimpleNamespace(
        cuda=SimpleNamespace(is_available=lambda: True),
        backends=SimpleNamespace(mps=SimpleNamespace(is_available=lambda: True)),
    )
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    assert _resolve_torch_device("auto") == "cuda"
    assert _resolve_sam3_torch_device("auto") == "cuda"


def test_auto_torch_device_uses_mps_for_supported_models(monkeypatch):
    fake_torch = SimpleNamespace(
        cuda=SimpleNamespace(is_available=lambda: False),
        backends=SimpleNamespace(mps=SimpleNamespace(is_available=lambda: True)),
    )
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    assert _resolve_torch_device("auto") == "mps"
    assert _resolve_sam3_torch_device("auto") == "cpu"


def test_auto_torch_device_falls_back_to_cpu(monkeypatch):
    fake_torch = SimpleNamespace(
        cuda=SimpleNamespace(is_available=lambda: False),
        backends=SimpleNamespace(mps=SimpleNamespace(is_available=lambda: False)),
    )
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    assert _resolve_torch_device("auto") == "cpu"
    assert _resolve_sam3_torch_device("auto") == "cpu"


def test_sam3_torch_factory_patch_redirects_hardcoded_cuda_allocations():
    calls = []

    class FakeTorch:
        def arange(self, *args, **kwargs):
            calls.append(("arange", args, kwargs.get("device")))
            return "arange"

        def zeros(self, shape, **kwargs):
            calls.append(("zeros", (shape,), kwargs.get("device")))
            return "zeros"

    fake_torch = FakeTorch()

    with _sam3_torch_factory_device_patch(fake_torch, "cpu"):
        fake_torch.zeros((1, 1, 4, 4), device="cuda")
        fake_torch.arange(0, 4, device="cuda")
    fake_torch.zeros((1, 1, 4, 4), device="cuda")

    assert calls == [
        ("zeros", ((1, 1, 4, 4),), "cpu"),
        ("arange", (0, 4), "cpu"),
        ("zeros", ((1, 1, 4, 4),), "cuda"),
    ]


def test_sam3_torch_factory_patch_leaves_cuda_runtime_unchanged():
    calls = []

    class FakeTorch:
        def zeros(self, shape, **kwargs):
            calls.append((shape, kwargs.get("device")))
            return "tensor"

    fake_torch = FakeTorch()

    with _sam3_torch_factory_device_patch(fake_torch, "cuda"):
        fake_torch.zeros((1, 1, 4, 4), device="cuda")

    assert calls == [((1, 1, 4, 4), "cuda")]


def test_sam3_torch_runtime_patch_disables_pin_memory_for_cpu():
    calls = []

    class FakeTensor:
        def pin_memory(self):
            calls.append("original")
            return "pinned"

    fake_tensor = FakeTensor()
    original_pin_memory = FakeTensor.pin_memory
    fake_torch = SimpleNamespace(Tensor=FakeTensor)

    with _sam3_torch_runtime_device_patch(fake_torch, "cpu"):
        assert fake_tensor.pin_memory() is fake_tensor
    assert fake_tensor.pin_memory() == "pinned"
    assert FakeTensor.pin_memory is original_pin_memory
    assert calls == ["original"]


def test_sam3_torch_runtime_patch_keeps_pin_memory_for_cuda():
    calls = []

    class FakeTensor:
        def pin_memory(self):
            calls.append("original")
            return "pinned"

    fake_tensor = FakeTensor()
    fake_torch = SimpleNamespace(Tensor=FakeTensor)

    with _sam3_torch_runtime_device_patch(fake_torch, "cuda"):
        assert fake_tensor.pin_memory() == "pinned"

    assert calls == ["original"]


def test_local_paddle_ocr_restores_home_after_model_initialization(monkeypatch, tmp_path):
    original_home = tmp_path / "home"
    original_home.mkdir()
    monkeypatch.setenv("HOME", str(original_home))
    paths = LocalRuntimePaths(runtime_root=tmp_path / "runtime")
    (paths.paddlex_official_models / "PP-OCRv5_server_det").mkdir(parents=True)
    (paths.paddlex_official_models / "PP-OCRv5_server_rec").mkdir(parents=True)

    class FakePaddle:
        def set_device(self, device):
            self.device = device

    class FakePaddleOCR:
        def __init__(self, **kwargs):
            assert os.environ["HOME"] == str(paths.paddle_home)
            assert kwargs["text_detection_model_dir"] == str(
                paths.paddlex_official_models / "PP-OCRv5_server_det"
            )
            assert kwargs["text_recognition_model_dir"] == str(
                paths.paddlex_official_models / "PP-OCRv5_server_rec"
            )

        def predict(self, _path):
            return []

    monkeypatch.setitem(sys.modules, "paddle", FakePaddle())
    monkeypatch.setitem(sys.modules, "paddleocr", SimpleNamespace(PaddleOCR=FakePaddleOCR))

    provider = LocalPaddleOcrProvider(paths=paths, device="cpu")
    provider._ocr_runtime()

    assert os.environ["HOME"] == str(original_home)


def test_local_paddle_ocr_uses_windows_junction_when_symlink_is_not_allowed(monkeypatch, tmp_path):
    paths = LocalRuntimePaths(runtime_root=tmp_path / "runtime")
    paths.paddlex_official_models.mkdir(parents=True)
    provider = LocalPaddleOcrProvider(paths=paths, device="cpu")
    model_root = paths.paddle_home / ".paddlex" / "official_models"
    calls = []

    def fake_symlink_to(self: Path, target: Path, *, target_is_directory: bool = False):
        calls.append(("symlink", self, target, target_is_directory))
        raise OSError(1314, "A required privilege is not held by the client")

    def fake_create_junction(link_path: Path, target_path: Path) -> bool:
        calls.append(("junction", link_path, target_path))
        link_path.mkdir(parents=True)
        return True

    monkeypatch.setattr(Path, "symlink_to", fake_symlink_to)
    monkeypatch.setattr(local_runtime.os, "name", "nt")
    monkeypatch.setattr(local_runtime, "_create_windows_junction", fake_create_junction)

    provider._prepare_paddle_model_home()

    assert model_root.exists()
    assert calls == [
        ("symlink", model_root, paths.paddlex_official_models, True),
        ("junction", model_root, paths.paddlex_official_models),
    ]
