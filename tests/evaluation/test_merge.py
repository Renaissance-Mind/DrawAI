import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from drawai_evaluation import merge as full_eval_merge


class MetricCatalogTest(unittest.TestCase):
    def setUp(self) -> None:
        self.assertIsNotNone(full_eval_merge, "implementation module is missing")

    def test_catalog_has_exactly_39_unique_bilingual_tertiary_metrics(self) -> None:
        catalog = full_eval_merge.metric_catalog()
        self.assertEqual(len(catalog), 39)
        self.assertEqual(len({row["metric_id"] for row in catalog}), 39)
        for row in catalog:
            for level in ("primary", "secondary", "tertiary"):
                self.assertTrue(row[level]["zh"])
                self.assertTrue(row[level]["en"])
            self.assertIn(row["method"], {"rule", "rubric"})

    def test_catalog_method_split_matches_the_evaluation_rules(self) -> None:
        catalog = full_eval_merge.metric_catalog()
        self.assertEqual(sum(row["method"] == "rule" for row in catalog), 9)
        self.assertEqual(sum(row["method"] == "rubric" for row in catalog), 30)
        by_id = {row["metric_id"]: row for row in catalog}
        self.assertEqual(
            by_id["editability.formula.editable_representation"]["rule_key"],
            "formula_editable_representation",
        )
        self.assertEqual(
            by_id["editability.table.table_regions"]["criterion"],
            "table_region_independence",
        )


class RubricAggregationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.assertIsNotNone(full_eval_merge, "implementation module is missing")

    def test_element_criterion_is_recomputed_from_per_element_scores(self) -> None:
        payload = {
            "per_element": [
                {"gt_id": "E1", "scores": {"position_lines": {"answer": "yes", "score": 1.0}}},
                {"gt_id": "E2", "scores": {"position_lines": {"answer": "partial", "score": 0.5}}},
                {"gt_id": "E3", "scores": {"position_lines": {"answer": "N/A", "score": None}}},
            ]
        }
        value = full_eval_merge.recompute_element_criterion(payload, "position_lines")
        self.assertEqual(value["score"], 0.75)
        self.assertEqual(value["valid_count"], 2)
        self.assertEqual(value["yes_count"], 1)
        self.assertEqual(value["partial_count"], 1)
        self.assertEqual(value["na_count"], 1)

    def test_missing_kind_becomes_explicit_not_applicable(self) -> None:
        row = full_eval_merge.not_applicable_metric(
            full_eval_merge.metric_catalog()[15], "no GT elements of kind formula"
        )
        self.assertEqual(row["status"], "not_applicable")
        self.assertIsNone(row["score"])
        self.assertIn("formula", row["reason"])

    def test_expected_rubric_groups_follow_gt_kinds(self) -> None:
        self.assertEqual(
            full_eval_merge.expected_rubric_groups(
                {"text": 4, "shape": 2, "connector": 0, "formula": 1, "table": 1}
            ),
            {"global", "text", "shape", "formula", "table"},
        )


class PartialMergeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.assertIsNotNone(full_eval_merge, "implementation module is missing")

    def test_partial_merge_publishes_only_fully_validated_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            complete = self._task(root, "complete")
            incomplete = self._task(root, "incomplete")
            self._write_complete_global_result(complete)
            manifest = root / "task_manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema": "drawbench_rubric_task_manifest.v1",
                        "candidate_count": 2,
                        "task_count": 2,
                        "tasks": [complete, incomplete],
                    }
                )
            )

            summary = full_eval_merge.merge_manifest(manifest, allow_partial=True)

            self.assertEqual(summary["candidate_count"], 1)
            self.assertEqual(summary["expected_candidate_count"], 2)
            self.assertTrue(summary["partial"])
            self.assertEqual(summary["candidates"][0]["bench_id"], complete["bench_id"])
            output = Path(complete["output_json"]).parent.parent / "full_evaluation.json"
            self.assertTrue(output.is_file())
            self.assertFalse(
                (Path(incomplete["output_json"]).parent.parent / "full_evaluation.json").exists()
            )

    def _task(self, root: Path, stem: str) -> dict:
        sample_id = "0001" if stem == "complete" else "0002"
        candidate = root / sample_id / "dag" / "lane"
        inputs = candidate / "inputs"
        inputs.mkdir(parents=True)
        gt = inputs / "gt.json"
        reference = inputs / "reference.png"
        svg = inputs / "candidate.svg"
        rendered = candidate / "rendered.png"
        rule = candidate / "rule_based_eval.json"
        gt.write_text('{"elements": []}')
        reference.write_bytes(b"reference")
        svg.write_text("<svg/>")
        rendered.write_bytes(b"rendered")
        rule.write_text(
            json.dumps(
                {
                    "metrics": {
                        "ssim": 0.8,
                        "edge_f1": 0.7,
                        "mse": 0.1,
                    }
                }
            )
        )
        return {
            "task_id": f"rubric_{stem}",
            "bench_id": sample_id,
            "dag": "dag",
            "lane": "lane",
            "group": "global",
            "gt_page_spec": str(gt),
            "reference_image": str(reference),
            "candidate_svg": str(svg),
            "rendered_png": str(rendered),
            "rule_based_eval": str(rule),
            "output_json": str(candidate / "rubric" / "global.json"),
        }

    def _write_complete_global_result(self, task: dict) -> None:
        output = Path(task["output_json"])
        output.parent.mkdir(parents=True)
        output.write_text(
            json.dumps(
                {
                    "schema": "drawai_eval_rubric_batch.v1",
                    "task_id": task["task_id"],
                    "bench_id": task["bench_id"],
                    "dag": task["dag"],
                    "lane": task["lane"],
                    "group": "global",
                    "model": "gpt-5.6-sol",
                    "execution_engine": "codex-python-sdk",
                    "aggregate": {
                        criterion: {
                            "answer": "yes",
                            "score": 1.0,
                            "reason": "Visible evidence.",
                        }
                        for criterion in (
                            "overall_readability",
                            "layout_skeleton",
                            "visual_hierarchy",
                        )
                    },
                    "notes": [],
                }
            )
        )
        result_dir = output.parent.parent / "sdk_runs" / "global" / "attempt_001"
        result_dir.mkdir(parents=True)
        input_sha256 = {
            key: hashlib.sha256(Path(task[key]).read_bytes()).hexdigest()
            for key in (
                "gt_page_spec",
                "reference_image",
                "candidate_svg",
                "rendered_png",
            )
        }
        (result_dir / "sdk_result.json").write_text(
            json.dumps(
                {
                    "schema": "drawbench.codex_sdk_rubric.result.v1",
                    "task_id": task["task_id"],
                    "model": "gpt-5.6-sol",
                    "execution_engine": "codex-python-sdk",
                    "turn_completed": True,
                    "turn_status": "completed",
                    "validation_passed": True,
                    "output_json": str(output),
                    "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                    "input_sha256": input_sha256,
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
