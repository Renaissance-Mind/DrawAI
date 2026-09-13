from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping
from urllib.parse import unquote, urlsplit

from lxml import etree

from drawai_evaluation.dataset import dataset_path, load_dataset_manifest
from drawai_evaluation.renderer import (
    _browser_renderer_path,
    _render_svg_with_browser,
    referenced_asset_hashes,
)

SNAPSHOT_SCHEMA = "drawbench.evaluation_candidate_snapshot.v2"


BATCH_SUMMARY_SCHEMA = "drawbench.full_evaluation_batch.v1"


RUBRIC_MANIFEST_SCHEMA = "drawbench_rubric_task_manifest.v1"


RUBRIC_GROUPS = ("global", "text", "shape", "connector", "formula", "table")


ELEMENT_RUBRIC_GROUPS = RUBRIC_GROUPS[1:]


@dataclass(frozen=True)
class EvaluationCandidate:
    target_id: str
    bench_id: str
    dag: str
    lane: str
    gt_page_spec: Path
    reference_image: Path
    candidate_svg: Path
    rendered_png: Path
    rule_based_eval: Path
    candidate_eval_dir: Path
    source_sha256: str
    gt_source_sha256: str
    kind_counts: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key, value in tuple(payload.items()):
            if isinstance(value, Path):
                payload[key] = str(value)
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> EvaluationCandidate:
        path_fields = {
            "gt_page_spec",
            "reference_image",
            "candidate_svg",
            "rendered_png",
            "rule_based_eval",
            "candidate_eval_dir",
        }
        values = dict(payload)
        for key in path_fields:
            values[key] = Path(str(values[key]))
        values["kind_counts"] = {
            str(key): int(value) for key, value in dict(values["kind_counts"]).items()
        }
        return cls(**values)


@dataclass(frozen=True)
class _CandidateRenderSource:
    href_base_dir: Path
    mode: str
    node_svg: Path | None = None


def required_rubric_groups(kind_counts: Mapping[str, int]) -> tuple[str, ...]:
    return (
        "global",
        *(group for group in ELEMENT_RUBRIC_GROUPS if int(kind_counts.get(group, 0)) > 0),
    )


def stable_task_id(bench_id: str, dag: str, lane: str, group: str) -> str:
    identity = "\0".join((bench_id, dag, lane, group)).encode("utf-8")
    return f"rubric_{hashlib.sha256(identity).hexdigest()[:20]}"


def build_rubric_task_manifest(
    candidates: Iterable[EvaluationCandidate],
    evaluation_root: str | Path,
) -> dict[str, Any]:
    root = Path(evaluation_root).expanduser().resolve(strict=False)
    ordered = sorted(candidates, key=lambda item: item.target_id)
    tasks: list[dict[str, Any]] = []
    for candidate in ordered:
        for group in required_rubric_groups(candidate.kind_counts):
            tasks.append(
                {
                    "task_id": stable_task_id(
                        candidate.bench_id, candidate.dag, candidate.lane, group
                    ),
                    "bench_id": candidate.bench_id,
                    "dag": candidate.dag,
                    "lane": candidate.lane,
                    "group": group,
                    "gt_count": None if group == "global" else candidate.kind_counts[group],
                    "gt_page_spec": str(candidate.gt_page_spec),
                    "reference_image": str(candidate.reference_image),
                    "candidate_svg": str(candidate.candidate_svg),
                    "rendered_png": str(candidate.rendered_png),
                    "rule_based_eval": str(candidate.rule_based_eval),
                    "source_sha256": candidate.source_sha256,
                    "gt_source_sha256": candidate.gt_source_sha256,
                    "output_json": str(candidate.candidate_eval_dir / "rubric" / f"{group}.json"),
                }
            )
    task_ids = [task["task_id"] for task in tasks]
    if len(task_ids) != len(set(task_ids)):
        raise RuntimeError("stable rubric task ids collided")
    return {
        "schema": RUBRIC_MANIFEST_SCHEMA,
        "created_at": _utc_now(),
        "evaluation_root": str(root),
        "candidate_count": len(ordered),
        "task_count": len(tasks),
        "tasks": tasks,
    }


def build_live_merge_command(
    *,
    tools_dir: str | Path,
    manifest_path: str | Path,
    python_executable: str | Path,
    interval_seconds: int | float,
) -> list[str]:
    return [
        str(python_executable),
        str(Path(tools_dir) / "merge.py"),
        "--manifest",
        str(manifest_path),
        "--watch-partial",
        "--watch-interval-seconds",
        str(interval_seconds),
    ]


def sync_rule_evaluations(
    candidates: Iterable[EvaluationCandidate],
    *,
    evaluation_tools_dir: str | Path,
    concurrency: int,
    python_executable: str | Path = sys.executable,
    force: bool = False,
) -> dict[str, Any]:
    if concurrency < 1:
        raise ValueError("rule concurrency must be positive")
    tools_dir = Path(evaluation_tools_dir).expanduser().resolve(strict=True)
    evaluator = tools_dir / "rule_based.py"
    if not evaluator.is_file():
        raise FileNotFoundError(f"rule evaluator is missing: {evaluator}")
    ordered = list(candidates)
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        future_to_candidate = {
            executor.submit(
                _sync_one_rule_evaluation,
                candidate,
                evaluator=evaluator,
                python_executable=Path(python_executable).expanduser(),
                force=force,
            ): candidate
            for candidate in ordered
        }
        for future in as_completed(future_to_candidate):
            candidate = future_to_candidate[future]
            try:
                result = future.result()
            except Exception as error:  # Batch processing records per-candidate failures.
                result = {
                    "target_id": candidate.target_id,
                    "status": "failed",
                    "error_type": error.__class__.__name__,
                    "error": str(error),
                }
            results.append(result)
            finished = len(results)
            if finished % 10 == 0 or finished == len(ordered):
                failed = sum(row["status"] == "failed" for row in results)
                print(
                    f"[evaluation-rule] finished={finished}/{len(ordered)} failed={failed}",
                    flush=True,
                )
    return {
        "candidate_count": len(ordered),
        "completed_count": sum(row["status"] in {"completed", "reused"} for row in results),
        "rendered_count": sum(row["status"] == "completed" for row in results),
        "reused_count": sum(row["status"] == "reused" for row in results),
        "failed_count": sum(row["status"] == "failed" for row in results),
        "results": sorted(results, key=lambda row: row["target_id"]),
    }


def _sync_one_rule_evaluation(
    candidate: EvaluationCandidate,
    *,
    evaluator: Path,
    python_executable: Path,
    force: bool,
) -> dict[str, Any]:
    provenance_path = candidate.candidate_eval_dir / "rule_provenance.json"
    input_hashes = {
        "gt_page_spec": _sha256_file(candidate.gt_page_spec),
        "reference_image": _sha256_file(candidate.reference_image),
        "candidate_svg": _sha256_file(candidate.candidate_svg),
        "evaluator": _sha256_file(evaluator),
        "renderer": _sha256_file(Path(__file__).with_name("renderer.py")),
        "assets": hashlib.sha256(
            json.dumps(referenced_asset_hashes(candidate.candidate_svg), sort_keys=True).encode()
        ).hexdigest(),
    }
    if not force and _rule_evaluation_is_current(candidate, provenance_path, input_hashes):
        return {"target_id": candidate.target_id, "status": "reused"}

    candidate.candidate_eval_dir.mkdir(parents=True, exist_ok=True)
    render = render_candidate_svg(candidate.candidate_svg, candidate.rendered_png)

    command = build_rule_evaluator_command(
        candidate,
        evaluator=evaluator,
        python_executable=python_executable,
    )
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            f"rule evaluator failed for {candidate.target_id}: "
            f"{(completed.stderr or completed.stdout).strip()}"
        )
    payload = _read_json(candidate.rule_based_eval)
    if payload.get("schema") != "drawai_eval_rule_based.v1":
        raise ValueError(
            f"unexpected rule schema for {candidate.target_id}: {payload.get('schema')!r}"
        )
    provenance = {
        "schema": "drawbench.rule_provenance.v1",
        "generated_at": _utc_now(),
        "target_id": candidate.target_id,
        "input_sha256": {
            **input_hashes,
            "rendered_png": _sha256_file(candidate.rendered_png),
            "rule_based_eval": _sha256_file(candidate.rule_based_eval),
        },
        "renderer": render,
    }
    _write_json(provenance_path, provenance)
    return {"target_id": candidate.target_id, "status": "completed"}


def render_candidate_svg(candidate_svg: Path, rendered_png: Path) -> dict[str, str]:
    browser = _browser_renderer_path()
    if browser is None:
        raise FileNotFoundError("DrawAI could not locate Google Chrome or Chromium")
    root = etree.fromstring(
        candidate_svg.read_bytes(),
        parser=etree.XMLParser(resolve_entities=False, no_network=True),
    )
    source = _resolve_candidate_render_source(candidate_svg, root=root)
    error = _render_svg_with_browser(root, source.href_base_dir, rendered_png, browser)
    if error is not None:
        raise RuntimeError(f"DrawAI Chromium renderer failed for {candidate_svg}: {error}")
    if not rendered_png.is_file():
        raise RuntimeError(f"DrawAI Chromium renderer did not create {rendered_png}")
    provenance = {
        "backend": "browser",
        "executable": str(browser),
        "asset_resolution": source.mode,
        "href_base_dir": str(source.href_base_dir),
    }
    if source.node_svg is not None:
        provenance["byte_identical_node_svg"] = str(source.node_svg)
    return provenance


def _resolve_candidate_render_source(
    candidate_svg: Path, *, root: etree._Element | None = None
) -> _CandidateRenderSource:
    return _CandidateRenderSource(
        href_base_dir=candidate_svg.resolve(strict=True).parent,
        mode="declared_candidate_svg",
    )


def _unresolved_local_image_hrefs(root: etree._Element, href_base_dir: Path) -> tuple[str, ...]:
    unresolved: list[str] = []
    for element in root.iter():
        if not isinstance(element.tag, str):
            continue
        if etree.QName(element).localname != "image":
            continue
        href = element.get("href") or element.get("{http://www.w3.org/1999/xlink}href")
        if not href:
            continue
        parsed = urlsplit(href)
        if (
            not parsed.path
            or parsed.scheme
            or parsed.netloc
            or parsed.query
            or parsed.fragment
            or parsed.path.startswith("/")
            or "\\" in parsed.path
        ):
            continue
        relative_path = PurePosixPath(unquote(parsed.path))
        asset_path = href_base_dir.joinpath(*relative_path.parts)
        if not asset_path.is_file():
            unresolved.append(href)
    return tuple(unresolved)


def build_rule_evaluator_command(
    candidate: EvaluationCandidate,
    *,
    evaluator: Path,
    python_executable: Path,
) -> list[str]:
    return [
        str(python_executable),
        str(evaluator),
        "--gt-spec",
        str(candidate.gt_page_spec),
        "--reference-image",
        str(candidate.reference_image),
        "--candidate-svg",
        str(candidate.candidate_svg),
        "--rendered-png",
        str(candidate.rendered_png),
        "--output-json",
        str(candidate.rule_based_eval),
        "--case-id",
        candidate.target_id,
        "--bench-id",
        candidate.bench_id,
        "--skip-render",
    ]


def _rule_evaluation_is_current(
    candidate: EvaluationCandidate,
    provenance_path: Path,
    input_hashes: Mapping[str, str],
) -> bool:
    if not (
        candidate.rendered_png.is_file()
        and candidate.rule_based_eval.is_file()
        and provenance_path.is_file()
    ):
        return False
    try:
        provenance = _read_json(provenance_path)
        rule_payload = _read_json(candidate.rule_based_eval)
    except (OSError, json.JSONDecodeError, ValueError):
        return False
    recorded = provenance.get("input_sha256")
    return (
        provenance.get("schema") == "drawbench.rule_provenance.v1"
        and isinstance(recorded, Mapping)
        and all(recorded.get(key) == value for key, value in input_hashes.items())
        and recorded.get("rendered_png") == _sha256_file(candidate.rendered_png)
        and recorded.get("rule_based_eval") == _sha256_file(candidate.rule_based_eval)
        and provenance.get("renderer", {}).get("backend") == "browser"
        and rule_payload.get("schema") == "drawai_eval_rule_based.v1"
    )


def run_evaluation_candidates(
    args: argparse.Namespace,
    *,
    snapshot_path: str | Path,
    candidates: Iterable[EvaluationCandidate],
) -> int:
    snapshot = Path(snapshot_path).expanduser().resolve(strict=True)
    evaluation_root = snapshot.parent
    ordered_candidates = sorted(candidates, key=lambda item: item.target_id)
    print(
        f"[evaluation-batch] snapshot={snapshot} candidates={len(ordered_candidates)}",
        flush=True,
    )
    rule_summary = sync_rule_evaluations(
        ordered_candidates,
        evaluation_tools_dir=args.evaluation_tools_dir,
        concurrency=args.rule_concurrency,
        python_executable=args.rule_python,
        force=args.force_rule,
    )
    manifest = build_rubric_task_manifest(ordered_candidates, evaluation_root)
    manifest_path = evaluation_root / "task_manifest.json"
    _write_json(manifest_path, manifest)
    batch_summary_path = evaluation_root / "batch_evaluation_summary.json"
    batch_summary: dict[str, Any] = {
        "schema": BATCH_SUMMARY_SCHEMA,
        "updated_at": _utc_now(),
        "snapshot": str(snapshot),
        "manifest": str(manifest_path),
        "candidate_count": len(ordered_candidates),
        "rubric_task_count": manifest["task_count"],
        "rule": rule_summary,
        "rubric": {"status": "not_started"},
        "merge": {"status": "not_started"},
    }
    _write_json(batch_summary_path, batch_summary)
    if rule_summary["failed_count"]:
        return 1
    if args.rule_only:
        return 0

    tools_dir = Path(args.evaluation_tools_dir).expanduser().resolve(strict=True)
    rubric_command = [
        sys.executable,
        str(tools_dir / "rubric.py"),
        "--manifest",
        str(manifest_path),
        "--concurrency",
        str(args.rubric_concurrency),
        "--max-attempts",
        str(args.rubric_max_attempts),
        "--timeout-seconds",
        str(args.rubric_timeout_seconds),
        "--reasoning-effort",
        args.reasoning_effort,
        "--host-codex-home",
        str(args.host_codex_home),
    ]
    if args.codex_bin:
        rubric_command.extend(["--codex-bin", str(args.codex_bin)])
    live_merge_log_path = evaluation_root / "live_merge.log"
    live_merge_command = build_live_merge_command(
        tools_dir=tools_dir,
        manifest_path=manifest_path,
        python_executable=sys.executable,
        interval_seconds=30,
    )
    with live_merge_log_path.open("a", encoding="utf-8") as live_merge_log:
        live_merge_process = subprocess.Popen(
            live_merge_command,
            stdout=live_merge_log,
            stderr=subprocess.STDOUT,
        )
        try:
            rubric_result = subprocess.run(rubric_command, check=False)
        finally:
            if live_merge_process.poll() is None:
                live_merge_process.terminate()
            live_merge_return_code = live_merge_process.wait()
    batch_summary["updated_at"] = _utc_now()
    batch_summary["live_merge"] = {
        "status": "completed"
        if live_merge_return_code == 0
        else "stopped"
        if live_merge_return_code < 0
        else "failed",
        "return_code": live_merge_return_code,
        "log": str(live_merge_log_path),
        "summary": str(evaluation_root / "full_evaluation_summary.json"),
    }
    batch_summary["rubric"] = {
        "status": "completed" if rubric_result.returncode == 0 else "incomplete",
        "return_code": rubric_result.returncode,
        "summary": str(evaluation_root / "sdk_scheduler_summary.json"),
    }
    _write_json(batch_summary_path, batch_summary)
    if rubric_result.returncode != 0:
        return rubric_result.returncode

    merge_command = [
        sys.executable,
        str(tools_dir / "merge.py"),
        "--manifest",
        str(manifest_path),
    ]
    merge_result = subprocess.run(merge_command, check=False)
    batch_summary["updated_at"] = _utc_now()
    batch_summary["merge"] = {
        "status": "completed" if merge_result.returncode == 0 else "failed",
        "return_code": merge_result.returncode,
        "summary": str(evaluation_root / "full_evaluation_summary.json"),
    }
    _write_json(batch_summary_path, batch_summary)
    return merge_result.returncode


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_completed_candidates(
    dataset_root: Path, candidate_manifest: Path, evaluation_root: Path
) -> tuple[list[EvaluationCandidate], dict[str, int]]:
    dataset = load_dataset_manifest(dataset_root)
    cases = {row["bench_id"]: row for row in dataset["cases"]}
    content = candidate_manifest.read_text(encoding="utf-8")
    if candidate_manifest.suffix == ".jsonl":
        entries = [json.loads(line) for line in content.splitlines() if line.strip()]
    else:
        payload = json.loads(content)
        entries = payload if isinstance(payload, list) else payload["candidates"]
    candidates = []
    seen = set()
    skipped = 0
    for row in entries:
        if row.get("status") != "completed":
            skipped += 1
            continue
        bench_id = row["bench_id"]
        if bench_id not in cases:
            raise ValueError(f"unknown benchmark case: {bench_id}")
        method, model = row["method"], row["model"]
        for label in (method, model):
            if (
                not isinstance(label, str)
                or not label
                or label in {".", ".."}
                or any(c in label for c in ("/", "\\", "\0"))
            ):
                raise ValueError(f"method and model must be non-empty path components: {label!r}")
        target_id = f"{method}/{model}/{bench_id}"
        if target_id in seen:
            raise ValueError(f"duplicate completed candidate: {target_id}")
        seen.add(target_id)
        case = cases[bench_id]
        svg = Path(row["candidate_svg"]).expanduser()
        if not svg.is_absolute():
            svg = candidate_manifest.parent / svg
        svg = svg.resolve(strict=True)
        xml = etree.fromstring(
            svg.read_bytes(), etree.XMLParser(resolve_entities=False, no_network=True)
        )
        if etree.QName(xml).localname != "svg":
            raise ValueError(f"candidate must be an SVG: {svg}")
        directory = evaluation_root / bench_id / method / model
        candidates.append(
            EvaluationCandidate(
                target_id=target_id,
                bench_id=bench_id,
                dag=method,
                lane=model,
                gt_page_spec=dataset_path(dataset_root, case["annotation"]),
                reference_image=dataset_path(dataset_root, case["image"]),
                candidate_svg=svg,
                rendered_png=directory / "rendered.png",
                rule_based_eval=directory / "rule_based_eval.json",
                candidate_eval_dir=directory,
                source_sha256=case["image_sha256"],
                gt_source_sha256=case["image_sha256"],
                kind_counts=case["kind_counts"],
            )
        )
    return sorted(candidates, key=lambda c: c.target_id), {
        "listed_count": len(entries),
        "completed_count": len(candidates),
        "skipped_unfinished_count": skipped,
        "dataset_case_count": len(cases),
    }


def write_asset_audit(candidates: list[EvaluationCandidate], snapshot: Path) -> dict:
    rows = []
    for candidate in candidates:
        xml = etree.fromstring(
            candidate.candidate_svg.read_bytes(),
            etree.XMLParser(resolve_entities=False, no_network=True),
        )
        missing = _unresolved_local_image_hrefs(xml, candidate.candidate_svg.parent)
        rows.append(
            {
                "target_id": candidate.target_id,
                "candidate_svg": str(candidate.candidate_svg),
                "unresolved_local_image_hrefs": list(missing),
            }
        )
    result = {
        "schema": "drawbench.asset_resolution_audit.v1",
        "generated_at": _utc_now(),
        "snapshot": str(snapshot),
        "candidate_count": len(candidates),
        "missing_candidate_svg_count": 0,
        "unresolved_local_image_href_count": sum(
            len(r["unresolved_local_image_hrefs"]) for r in rows
        ),
        "candidates": rows,
    }
    _write_json(snapshot.parent / "asset_resolution_audit.json", result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate completed SVG predictions with 39 metrics."
    )
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--rule-concurrency", type=int, default=8)
    parser.add_argument("--rubric-concurrency", type=int, default=40)
    parser.add_argument("--rubric-max-attempts", type=int, default=3)
    parser.add_argument("--rubric-timeout-seconds", type=float, default=1800)
    parser.add_argument("--reasoning-effort", default="high")
    parser.add_argument("--codex-bin", type=Path)
    parser.add_argument("--host-codex-home", type=Path, default=Path.home() / ".codex")
    parser.add_argument("--rule-only", action="store_true")
    args = parser.parse_args(argv)
    if args.rule_concurrency < 1 or not 1 <= args.rubric_concurrency <= 150:
        parser.error("Rule concurrency must be positive and Rubric concurrency must be 1-150")
    if args.rubric_max_attempts < 1 or args.rubric_timeout_seconds <= 0:
        parser.error("retry count and timeout must be positive")
    args.dataset = args.dataset.expanduser().resolve(strict=True)
    args.candidates = args.candidates.expanduser().resolve(strict=True)
    args.output_root = args.output_root.expanduser().resolve()
    args.output_root.mkdir(parents=True, exist_ok=True)
    args.evaluation_tools_dir = Path(__file__).parent
    args.rule_python = sys.executable
    args.force_rule = False
    if args.codex_bin:
        args.codex_bin = args.codex_bin.expanduser().resolve(strict=True)
    with (args.output_root / ".evaluation.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError("another batch already owns this evaluation root") from error
        candidates, coverage = load_completed_candidates(
            args.dataset, args.candidates, args.output_root
        )
        if not candidates:
            print("No completed candidates in the input manifest.")
            return 0
        snapshot = args.output_root / "candidate_snapshot.json"
        _write_json(
            snapshot,
            {
                "schema": SNAPSHOT_SCHEMA,
                "created_at": _utc_now(),
                "dataset_root": str(args.dataset),
                "coverage": coverage,
                "candidate_count": len(candidates),
                "candidates": [c.to_dict() for c in candidates],
            },
        )
        audit = write_asset_audit(candidates, snapshot)
        print(
            f"completed_candidates={len(candidates)} skipped_unfinished={coverage['skipped_unfinished_count']} unresolved_images={audit['unresolved_local_image_href_count']}",
            flush=True,
        )
        return run_evaluation_candidates(args, snapshot_path=snapshot, candidates=candidates)


if __name__ == "__main__":
    raise SystemExit(main())
