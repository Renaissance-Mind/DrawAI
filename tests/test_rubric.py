import json
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace

from drawai_evaluation import rubric as rubric_sdk

EXPECTED_CRITERIA = {
    "global": ("overall_readability", "layout_skeleton", "visual_hierarchy"),
    "text": (
        "position_lines",
        "alignment_spacing",
        "overflow_occlusion",
        "color_emphasis",
        "font_appearance",
        "style_consistency",
    ),
    "shape": (
        "existence_coverage",
        "visual_attributes",
        "neighbor_relation",
        "object_independence",
        "box_placement",
        "conflict_diagnosis",
    ),
    "connector": (
        "path_presence",
        "endpoint_direction",
        "line_style_noise",
        "independent_path",
        "endpoint_control",
        "mis_merge_check",
    ),
    "formula": (
        "symbol_retention",
        "structure_relation",
        "position_readability",
    ),
    "table": (
        "grid_structure",
        "content_ownership",
        "readability_alignment",
        "table_region_independence",
        "editable_grid",
        "text_ownership",
    ),
}


def task(group: str, root: Path, gt_count: int | None = None) -> dict:
    return {
        "task_id": "001",
        "bench_id": "knowledge_maps/human_100/example",
        "dag": "default_drawai_dag",
        "lane": "gpt-5.5_codex",
        "group": group,
        "gt_count": gt_count,
        "gt_page_spec": str(root / "gt.json"),
        "reference_image": str(root / "reference.png"),
        "candidate_svg": str(root / "semantic.svg"),
        "rendered_png": str(root / "rendered.png"),
        "output_json": str(root / "rubric" / f"{group}.json"),
    }


def criterion_score(answer: str) -> dict:
    score = {"yes": 1.0, "partial": 0.5, "no": 0.0, "N/A": None}[answer]
    return {"answer": answer, "score": score}


class RubricContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.assertIsNotNone(rubric_sdk, "implementation module is missing")

    def test_criteria_are_fixed_for_all_six_groups(self) -> None:
        for group, expected in EXPECTED_CRITERIA.items():
            self.assertEqual(tuple(rubric_sdk.criteria_for_group(group)), expected)

    def test_prompt_contains_only_the_explicit_evidence_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            value = rubric_sdk.build_task_prompt(task("text", root, 2))
            for name in ("gt.json", "reference.png", "semantic.svg", "rendered.png", "text.json"):
                self.assertIn(name, value)
            self.assertIn("Do not read or use Memory", value)
            self.assertIn("Do not browse the web", value)
            self.assertIn("Evaluate every one", value)
            self.assertIn("exactly 2 unique GT ids", value)

    def test_global_payload_requires_all_three_criteria(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            row = task("global", root)
            payload = {
                "schema": "drawai_eval_rubric_batch.v1",
                "task_id": "001",
                "bench_id": row["bench_id"],
                "dag": row["dag"],
                "lane": row["lane"],
                "group": "global",
                "model": "gpt-5.6-sol",
                "execution_engine": "codex-python-sdk",
                "aggregate": {
                    key: {**criterion_score("yes"), "reason": "Visible evidence."}
                    for key in EXPECTED_CRITERIA["global"]
                },
                "notes": [],
            }
            self.assertEqual(rubric_sdk.validate_rubric_payload(row, payload, {}), payload)
            del payload["aggregate"]["visual_hierarchy"]
            with self.assertRaisesRegex(ValueError, "aggregate criteria"):
                rubric_sdk.validate_rubric_payload(row, payload, {})

    def test_element_payload_covers_every_gt_id_and_recomputes_aggregates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            row = task("text", root, 2)
            gt = {
                "elements": [
                    {"id": "E1", "kind": "text", "box_px": [0, 0, 10, 10]},
                    {"id": "E2", "kind": "text", "box_px": [10, 0, 10, 10]},
                ]
            }
            per_element = []
            for element_id, answer in (("E1", "yes"), ("E2", "partial")):
                per_element.append(
                    {
                        "gt_id": element_id,
                        "scores": {
                            key: criterion_score(answer) for key in EXPECTED_CRITERIA["text"]
                        },
                    }
                )
            aggregate = {
                key: {
                    "score": 0.75,
                    "valid_count": 2,
                    "yes_count": 1,
                    "partial_count": 1,
                    "no_count": 0,
                    "na_count": 0,
                    "reason": "One exact and one partial match.",
                }
                for key in EXPECTED_CRITERIA["text"]
            }
            payload = {
                "schema": "drawai_eval_rubric_batch.v1",
                "task_id": "001",
                "bench_id": row["bench_id"],
                "dag": row["dag"],
                "lane": row["lane"],
                "group": "text",
                "model": "gpt-5.6-sol",
                "execution_engine": "codex-python-sdk",
                "gt_count": 2,
                "evaluated_ids": ["E1", "E2"],
                "per_element": per_element,
                "aggregate": aggregate,
                "notes": [],
            }
            self.assertEqual(rubric_sdk.validate_rubric_payload(row, payload, gt), payload)
            for value in payload["aggregate"].values():
                value["score"] = 0.75004
            self.assertEqual(rubric_sdk.validate_rubric_payload(row, payload, gt), payload)
            for value in payload["aggregate"].values():
                value["score"] = 0.76
            with self.assertRaisesRegex(ValueError, "aggregate.position_lines.score"):
                rubric_sdk.validate_rubric_payload(row, payload, gt)
            payload["evaluated_ids"] = ["E1"]
            with self.assertRaisesRegex(ValueError, "evaluated_ids"):
                rubric_sdk.validate_rubric_payload(row, payload, gt)


class IsolationAndAuditTest(unittest.TestCase):
    def setUp(self) -> None:
        self.assertIsNotNone(rubric_sdk, "implementation module is missing")

    def test_prepare_isolated_home_copies_only_auth(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            host = root / "host-codex"
            host.mkdir()
            (host / "auth.json").write_text('{"token":"test"}\n')
            (host / "config.toml").write_text('model="wrong"\n')
            prepared = rubric_sdk.prepare_isolated_home(root / "attempt", host)
            codex_home = Path(prepared["codex_home"])
            self.assertTrue((codex_home / "auth.json").is_file())
            self.assertFalse((codex_home / "config.toml").exists())
            self.assertFalse((codex_home / "memories").exists())

    def test_create_attempt_dir_never_overwrites_an_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = rubric_sdk.create_attempt_dir(root, "shape")
            second = rubric_sdk.create_attempt_dir(root, "shape")
            self.assertEqual(first.name, "attempt_001")
            self.assertEqual(second.name, "attempt_002")

    def test_prepare_sdk_task_stages_only_attempt_local_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_root = root / "generation" / "nodes" / "svg_compose" / "output"
            row = task("shape", source_root, 1)
            row["output_json"] = str(root / "evaluation" / "rubric" / "shape.json")
            row["rule_based_eval"] = str(root / "evaluation" / "rule_based_eval.json")
            row["source_sha256"] = "source-hash"
            for key in ("gt_page_spec", "reference_image", "candidate_svg", "rendered_png"):
                path = Path(row[key])
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(f"{key}\n".encode())
            attempt_dir = root / "attempt_001"

            prepared = rubric_sdk.prepare_sdk_task(row, attempt_dir)

            serialized = json.dumps(prepared.task, sort_keys=True)
            self.assertNotIn(str(source_root), serialized)
            self.assertNotIn(str(root / "evaluation"), serialized)
            self.assertNotIn("rule_based_eval", prepared.task)
            self.assertNotIn("source_sha256", prepared.task)
            self.assertEqual(prepared.task["output_json"], str(attempt_dir / "rubric_output.json"))
            recorded = json.loads((attempt_dir / "task.json").read_text(encoding="utf-8"))
            self.assertEqual(recorded, prepared.task)

    def test_finalize_sdk_task_publishes_only_a_valid_isolated_result(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            row = task("global", root)
            Path(row["gt_page_spec"]).write_text("{}", encoding="utf-8")
            for key in ("reference_image", "candidate_svg", "rendered_png"):
                Path(row[key]).write_bytes(f"{key}\n".encode())
            runtime_dir = root / "runtime"
            prepared = rubric_sdk.prepare_sdk_task(row, runtime_dir)
            local_output = Path(prepared.task["output_json"])
            local_output.write_text(
                json.dumps(
                    {
                        "schema": "drawai_eval_rubric_batch.v1",
                        "task_id": "001",
                        "bench_id": row["bench_id"],
                        "dag": row["dag"],
                        "lane": row["lane"],
                        "group": "global",
                        "model": "gpt-5.6-sol",
                        "execution_engine": "codex-python-sdk",
                        "aggregate": {
                            key: {**criterion_score("yes"), "reason": "Visible evidence."}
                            for key in EXPECTED_CRITERIA["global"]
                        },
                        "notes": [],
                    }
                ),
                encoding="utf-8",
            )
            events = runtime_dir / "events.jsonl"
            events.write_text("", encoding="utf-8")
            final_response = runtime_dir / "final_response.txt"
            final_response.write_text("done", encoding="utf-8")
            (runtime_dir / "sdk_result.json").write_text(
                json.dumps(
                    {
                        "schema": "drawbench.codex_sdk_rubric.result.v1",
                        "task_id": "001",
                        "model": "gpt-5.6-sol",
                        "execution_engine": "codex-python-sdk",
                        "turn_completed": True,
                        "turn_status": "completed",
                        "validation_passed": True,
                        "output_json": str(local_output),
                        "output_sha256": rubric_sdk.sha256_file(local_output),
                        "input_sha256": rubric_sdk.task_input_sha256(prepared.task),
                        "events_path": str(events),
                        "final_response_path": str(final_response),
                    }
                ),
                encoding="utf-8",
            )
            record_dir = rubric_sdk.create_attempt_dir(
                Path(row["output_json"]).parent.parent, "global"
            )

            rubric_sdk.finalize_sdk_task_result(row, prepared, record_dir)

            result = json.loads((record_dir / "sdk_result.json").read_text(encoding="utf-8"))
            self.assertEqual(result["output_json"], row["output_json"])
            self.assertEqual(result["input_sha256"], rubric_sdk.task_input_sha256(row))
            self.assertEqual(result["evidence_isolation"]["sandbox"], "workspace_write")
            self.assertTrue(rubric_sdk.inspect_task_completion(row)["complete"])

    def test_privacy_check_ignores_prompt_text_but_rejects_forbidden_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            events = Path(temp_dir) / "events.jsonl"
            rows = [
                {"repr": "AgentMessageThreadItem(text='Do not read /home/tester/.codex/memories')"},
                {"repr": "CommandExecutionThreadItem(command='python read_gt.py')"},
                {
                    "payload": {
                        "item": {
                            "type": "commandExecution",
                            "command": "python read_candidate_svg.py",
                            "aggregatedOutput": "<image href='../nodes/asset/output.png'>",
                        }
                    },
                    "repr": "CommandExecutionThreadItem(command='python read_candidate_svg.py', aggregated_output=\"<image href='../nodes/asset/output.png'>\")",
                },
            ]
            events.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
            report = rubric_sdk.assert_no_forbidden_command_access(events)
            self.assertEqual(report["command_count"], 2)
            self.assertEqual(report["bad_command_hits"], 0)
            rows.append(
                {"repr": "CommandExecutionThreadItem(command='rg x /home/tester/.codex/memories')"}
            )
            events.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
            with self.assertRaisesRegex(RuntimeError, "forbidden paths"):
                rubric_sdk.assert_no_forbidden_command_access(events)


class SchedulerStateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.assertIsNotNone(rubric_sdk, "implementation module is missing")

    def test_sdk_result_must_bind_the_validated_output_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            row = task("global", root)
            output = Path(row["output_json"])
            output.parent.mkdir(parents=True)
            payload = {
                "schema": "drawai_eval_rubric_batch.v1",
                "task_id": "001",
                "bench_id": row["bench_id"],
                "dag": row["dag"],
                "lane": row["lane"],
                "group": "global",
                "model": "gpt-5.6-sol",
                "execution_engine": "codex-python-sdk",
                "aggregate": {
                    key: {**criterion_score("yes"), "reason": "Visible evidence."}
                    for key in EXPECTED_CRITERIA["global"]
                },
                "notes": [],
            }
            output.write_text(json.dumps(payload))
            gt = Path(row["gt_page_spec"])
            gt.write_text("{}")
            for key in ("reference_image", "candidate_svg", "rendered_png"):
                Path(row[key]).write_text(key)
            attempt = rubric_sdk.create_attempt_dir(output.parent.parent, "global")
            result = {
                "schema": "drawbench.codex_sdk_rubric.result.v1",
                "task_id": "001",
                "model": "gpt-5.6-sol",
                "execution_engine": "codex-python-sdk",
                "turn_completed": True,
                "turn_status": "completed",
                "validation_passed": True,
                "output_json": str(output),
                "output_sha256": rubric_sdk.sha256_file(output),
                "input_sha256": rubric_sdk.task_input_sha256(row),
            }
            (attempt / "sdk_result.json").write_text(json.dumps(result))
            complete = rubric_sdk.inspect_task_completion(row)
            self.assertTrue(complete["complete"])
            output.write_text(json.dumps({**payload, "notes": ["changed"]}))
            incomplete = rubric_sdk.inspect_task_completion(row)
            self.assertFalse(incomplete["complete"])
            self.assertIn("SDK result", incomplete["reason"])

    def test_sdk_result_is_invalidated_when_an_input_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            row = task("global", root)
            Path(row["gt_page_spec"]).parent.mkdir(parents=True, exist_ok=True)
            Path(row["gt_page_spec"]).write_text("{}")
            for key in ("reference_image", "candidate_svg", "rendered_png"):
                Path(row[key]).parent.mkdir(parents=True, exist_ok=True)
                Path(row[key]).write_text(key)
            output = Path(row["output_json"])
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(
                json.dumps(
                    {
                        "schema": "drawai_eval_rubric_batch.v1",
                        "task_id": "001",
                        "bench_id": row["bench_id"],
                        "dag": row["dag"],
                        "lane": row["lane"],
                        "group": "global",
                        "model": "gpt-5.6-sol",
                        "execution_engine": "codex-python-sdk",
                        "aggregate": {
                            key: {**criterion_score("yes"), "reason": "Visible evidence."}
                            for key in EXPECTED_CRITERIA["global"]
                        },
                        "notes": [],
                    }
                )
            )
            attempt = rubric_sdk.create_attempt_dir(output.parent.parent, "global")
            result = {
                "schema": "drawbench.codex_sdk_rubric.result.v1",
                "task_id": "001",
                "model": "gpt-5.6-sol",
                "execution_engine": "codex-python-sdk",
                "turn_completed": True,
                "turn_status": "completed",
                "validation_passed": True,
                "output_json": str(output),
                "output_sha256": rubric_sdk.sha256_file(output),
                "input_sha256": rubric_sdk.task_input_sha256(row),
            }
            (attempt / "sdk_result.json").write_text(json.dumps(result))
            first_completion = rubric_sdk.inspect_task_completion(row)
            self.assertTrue(first_completion["complete"], first_completion)
            Path(row["candidate_svg"]).write_text("changed")
            self.assertFalse(rubric_sdk.inspect_task_completion(row)["complete"])

    def test_sdk_result_is_invalidated_when_an_input_disappears(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            row = task("global", root)
            Path(row["gt_page_spec"]).write_text("{}")
            for key in ("reference_image", "candidate_svg", "rendered_png"):
                Path(row[key]).write_text(key)
            output = Path(row["output_json"])
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(
                json.dumps(
                    {
                        "schema": "drawai_eval_rubric_batch.v1",
                        "task_id": "001",
                        "bench_id": row["bench_id"],
                        "dag": row["dag"],
                        "lane": row["lane"],
                        "group": "global",
                        "model": "gpt-5.6-sol",
                        "execution_engine": "codex-python-sdk",
                        "aggregate": {
                            key: {**criterion_score("yes"), "reason": "Visible evidence."}
                            for key in EXPECTED_CRITERIA["global"]
                        },
                        "notes": [],
                    }
                )
            )
            attempt = rubric_sdk.create_attempt_dir(output.parent.parent, "global")
            result = {
                "schema": "drawbench.codex_sdk_rubric.result.v1",
                "task_id": "001",
                "model": "gpt-5.6-sol",
                "execution_engine": "codex-python-sdk",
                "turn_completed": True,
                "turn_status": "completed",
                "validation_passed": True,
                "output_json": str(output),
                "output_sha256": rubric_sdk.sha256_file(output),
                "input_sha256": rubric_sdk.task_input_sha256(row),
            }
            (attempt / "sdk_result.json").write_text(json.dumps(result))
            self.assertTrue(rubric_sdk.inspect_task_completion(row)["complete"])

            Path(row["candidate_svg"]).unlink()
            completion = rubric_sdk.inspect_task_completion(row)
            self.assertFalse(completion["complete"])
            self.assertIn("task input is unavailable", completion["reason"])

    def test_missing_task_input_does_not_escape_the_worker_future(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            row = task("shape", root, 1)
            for key in ("gt_page_spec", "reference_image", "rendered_png"):
                Path(row[key]).write_text("x")
            result = rubric_sdk._run_task_with_retries(
                row,
                host_codex_home=root / "codex-home",
                codex_bin=root / "codex",
                reasoning_effort="high",
                timeout_seconds=1,
                max_attempts=3,
                usage_limit_event=threading.Event(),
            )
            self.assertEqual(result["status"], "input_unavailable")
            self.assertEqual(result["attempts"], [])
            self.assertIn("candidate_svg", result["error"])

    def test_scheduler_records_missing_input_without_aborting_other_work(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            row = task("shape", root, 1)
            manifest = root / "task_manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema": "drawbench_rubric_task_manifest.v1",
                        "task_count": 1,
                        "tasks": [row],
                    }
                )
            )
            exit_code = rubric_sdk.run_scheduler(
                SimpleNamespace(
                    manifest=str(manifest),
                    archive_unverified_outputs=False,
                    task_id=[],
                    no_resume=False,
                    concurrency=1,
                    host_codex_home=str(root / "codex-home"),
                    codex_bin=str(root / "codex"),
                    reasoning_effort="high",
                    timeout_seconds=1,
                    max_attempts=3,
                )
            )
            self.assertEqual(exit_code, 1)
            summary = json.loads((root / "sdk_scheduler_summary.json").read_text())
            self.assertEqual(summary["results"][0]["status"], "input_unavailable")
            self.assertEqual(summary["incomplete_count"], 1)

    def test_select_tasks_respects_ids_and_completed_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            rows = [task("global", root), task("text", root, 1)]
            rows[1]["task_id"] = "002"
            selected = rubric_sdk.select_manifest_tasks(rows, {"002"}, resume=True)
            self.assertEqual([row["task_id"] for row in selected], ["002"])
            with self.assertRaisesRegex(ValueError, "unknown task ids"):
                rubric_sdk.select_manifest_tasks(rows, {"999"}, resume=True)

    def test_validate_task_inputs_requires_all_four_evidence_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            row = task("shape", root, 1)
            for key in ("gt_page_spec", "reference_image", "candidate_svg"):
                Path(row[key]).parent.mkdir(parents=True, exist_ok=True)
                Path(row[key]).write_text("x")
            with self.assertRaisesRegex(FileNotFoundError, "rendered_png"):
                rubric_sdk.validate_task_inputs(row)

    def test_scheduler_concurrency_supports_one_hundred_fifty_workers(self) -> None:
        self.assertEqual(rubric_sdk.validate_concurrency(150), 150)
        with self.assertRaisesRegex(ValueError, "between 1 and 150"):
            rubric_sdk.validate_concurrency(151)

    def test_usage_limit_failure_is_detected_with_retry_time(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            attempt_dir = Path(temp_dir)
            (attempt_dir / "sdk_result.json").write_text(
                json.dumps(
                    {
                        "turn_status": "failed",
                        "error": (
                            "Codex SDK turn failed: You've hit your usage limit. "
                            "Visit https://chatgpt.com/codex/settings/usage to purchase "
                            "more credits or try again at Jul 22nd, 2026 4:37 AM."
                        ),
                    }
                )
            )
            failure = rubric_sdk.inspect_usage_limit_failure(attempt_dir)
            self.assertTrue(failure["limited"])
            self.assertEqual(failure["retry_at"], "2026-07-22T04:37:00+08:00")

    def test_non_usage_failure_does_not_trip_the_circuit_breaker(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            attempt_dir = Path(temp_dir)
            (attempt_dir / "worker.stderr.log").write_text("schema validation failed\n")
            failure = rubric_sdk.inspect_usage_limit_failure(attempt_dir)
            self.assertFalse(failure["limited"])
            self.assertIsNone(failure["retry_at"])

    def test_tripped_usage_limit_skips_a_task_without_starting_an_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            usage_limit_event = threading.Event()
            usage_limit_event.set()
            result = rubric_sdk._run_task_with_retries(
                task("shape", root, 1),
                host_codex_home=root / "codex-home",
                codex_bin=root / "codex",
                reasoning_effort="high",
                timeout_seconds=1,
                max_attempts=3,
                usage_limit_event=usage_limit_event,
            )
            self.assertEqual(result["status"], "usage_limit_cancelled")
            self.assertFalse((root / "sdk_runs").exists())


if __name__ == "__main__":
    unittest.main()
