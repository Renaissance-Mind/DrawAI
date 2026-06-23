from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


API_PRESETS_SCHEMA = "drawai.workbench.api_presets.v1"
SUPPORTED_API_PRESET_TYPES = ("images_api", "llm_chat_completions", "llm_responses")


@dataclass(frozen=True)
class ApiPreset:
    id: str
    label: str
    type: str
    base_url: str
    model: str
    api_key_env: str = ""
    api_key: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def api_presets_path(workspace: str | Path) -> Path:
    return Path(workspace).expanduser().resolve(strict=False) / "settings" / "api_presets.json"


def read_workbench_api_presets(workspace: str | Path) -> tuple[ApiPreset, ...]:
    path = api_presets_path(workspace)
    if not path.is_file():
        return ()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"Workbench API presets must be a JSON object: {path}")
    return normalize_workbench_api_presets(payload)


def write_workbench_api_presets(workspace: str | Path, payload: Mapping[str, Any]) -> tuple[ApiPreset, ...]:
    presets = normalize_workbench_api_presets(payload)
    path = api_presets_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_api_presets_document(presets), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return presets


def workbench_api_presets_payload(workspace: str | Path) -> dict[str, Any]:
    return _api_presets_document(read_workbench_api_presets(workspace))


def normalize_workbench_api_presets(payload: Mapping[str, Any] | None) -> tuple[ApiPreset, ...]:
    data = dict(payload or {})
    raw_presets = data.get("presets", ())
    if not isinstance(raw_presets, Sequence) or isinstance(raw_presets, str | bytes):
        raise ValueError("API presets payload must contain a presets array")
    presets: list[ApiPreset] = []
    seen: set[str] = set()
    for index, item in enumerate(raw_presets):
        if not isinstance(item, Mapping):
            raise ValueError(f"presets[{index}] must be an object")
        preset = _normalize_api_preset(item, index)
        if preset.id in seen:
            raise ValueError(f"duplicate API preset id: {preset.id}")
        seen.add(preset.id)
        presets.append(preset)
    return tuple(presets)


def api_preset_by_id(presets: Sequence[ApiPreset], preset_id: str) -> ApiPreset | None:
    return next((preset for preset in presets if preset.id == preset_id), None)


def _normalize_api_preset(item: Mapping[str, Any], index: int) -> ApiPreset:
    preset_id = _required_slug(item.get("id"), f"presets[{index}].id")
    preset_type = _required_string(item.get("type"), f"presets[{index}].type")
    if preset_type not in SUPPORTED_API_PRESET_TYPES:
        supported = ", ".join(SUPPORTED_API_PRESET_TYPES)
        raise ValueError(f"unsupported API preset type: {preset_type!r}. Expected one of: {supported}")
    label = str(item.get("label") or preset_id).strip()
    base_url = _required_string(item.get("base_url"), f"presets[{index}].base_url").rstrip("/")
    model = _required_string(item.get("model"), f"presets[{index}].model")
    api_key_env = str(item.get("api_key_env") or "").strip()
    api_key = str(item.get("api_key") or "").strip()
    if not api_key_env and not api_key:
        raise ValueError(f"presets[{index}] must set api_key_env or api_key")
    return ApiPreset(
        id=preset_id,
        label=label,
        type=preset_type,
        base_url=base_url,
        model=model,
        api_key_env=api_key_env,
        api_key=api_key,
    )


def _api_presets_document(presets: Sequence[ApiPreset]) -> dict[str, Any]:
    return {
        "schema": API_PRESETS_SCHEMA,
        "preset_types": list(SUPPORTED_API_PRESET_TYPES),
        "presets": [preset.to_dict() for preset in presets],
    }


def _required_slug(value: Any, field_name: str) -> str:
    text = _required_string(value, field_name)
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
    if any(char not in allowed for char in text):
        raise ValueError(f"{field_name} must contain only letters, numbers, underscore, or hyphen")
    return text


def _required_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


__all__ = [
    "API_PRESETS_SCHEMA",
    "SUPPORTED_API_PRESET_TYPES",
    "ApiPreset",
    "api_preset_by_id",
    "api_presets_path",
    "normalize_workbench_api_presets",
    "read_workbench_api_presets",
    "workbench_api_presets_payload",
    "write_workbench_api_presets",
]
