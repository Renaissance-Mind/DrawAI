from __future__ import annotations

import os
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

_EVIDENCE_FILENAMES = {
    "gt_page_spec": "gt_page_spec.json",
    "reference_image": "reference.png",
    "candidate_svg": "candidate.svg",
    "rendered_png": "rendered.png",
}
_RUNTIME_TASK_FIELDS = (
    "task_id",
    "bench_id",
    "dag",
    "lane",
    "group",
    "gt_count",
)


@dataclass(frozen=True)
class RubricEvidenceWorkspace:
    task: dict[str, Any]
    published_output: Path


def prepare_rubric_evidence_workspace(
    task: Mapping[str, Any], attempt_dir: str | Path
) -> RubricEvidenceWorkspace:
    attempt = Path(attempt_dir).expanduser().absolute()
    evidence_dir = attempt / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    isolated_task = {field: task[field] for field in _RUNTIME_TASK_FIELDS}
    for field, filename in _EVIDENCE_FILENAMES.items():
        source = Path(str(task[field])).expanduser().resolve(strict=True)
        destination = evidence_dir / filename
        shutil.copyfile(source, destination)
        isolated_task[field] = str(destination)

    published_output = Path(str(task["output_json"])).expanduser().absolute()
    isolated_task["output_json"] = str(attempt / "rubric_output.json")
    return RubricEvidenceWorkspace(
        task=isolated_task,
        published_output=published_output,
    )


def publish_validated_rubric_output(source: str | Path, destination: str | Path) -> None:
    source_path = Path(source).expanduser().resolve(strict=True)
    destination_path = Path(destination).expanduser().resolve(strict=False)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = destination_path.with_name(f".{destination_path.name}.{uuid.uuid4().hex}.tmp")
    shutil.copyfile(source_path, temporary_path)
    os.replace(temporary_path, destination_path)
