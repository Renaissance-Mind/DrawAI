import tempfile
import unittest
from pathlib import Path

from PIL import Image

from drawai_evaluation.rule_based import evaluate_case


class EvaluateCaseMetricApplicabilityTest(unittest.TestCase):
    def test_kind_scoped_metrics_are_none_without_matching_gt_kind(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            reference = root / "reference.png"
            rendered = root / "rendered.png"
            candidate = root / "candidate.svg"
            gt_spec_path = root / "gt_page_spec.json"

            Image.new("RGB", (16, 16), "white").save(reference)
            Image.new("RGB", (16, 16), "white").save(rendered)
            candidate.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"/>\n',
                encoding="utf-8",
            )

            result = evaluate_case(
                gt_spec={"canvas": {"width_px": 16, "height_px": 16}, "elements": []},
                gt_spec_path=gt_spec_path,
                reference_image=reference,
                candidate_svg=candidate,
                rendered_png=rendered,
                case_id="empty",
                bench_id="empty",
                image_mse_threshold=0.02,
                image_iou_threshold=0.5,
                text_box_iou_threshold=0.5,
                text_sim_threshold=0.8,
                edge_canny_low=50,
                edge_canny_high=100,
                edge_blur_kernel=0,
                edge_dilation=1,
            )

            for metric_name in (
                "text_box_recall",
                "text_precision",
                "text_recall",
                "text_f1",
                "image_object_recall",
                "image_recall",
                "image_miou",
                "image_region_mse",
                "image_region_mse_median",
                "image_region_mse_pass_rate",
                "formula_editable_representation",
            ):
                self.assertIsNone(result["metrics"][metric_name], metric_name)

    def test_formula_editable_representation_recalls_native_text_by_bbox(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            reference = root / "reference.png"
            rendered = root / "rendered.png"
            candidate = root / "candidate.svg"
            Image.new("RGB", (32, 16), "white").save(reference)
            Image.new("RGB", (32, 16), "white").save(rendered)
            candidate.write_text(
                """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 16">
  <text x="2" y="12" font-size="10" data-drawai-element-id="F1">x² + y²</text>
  <image x="16" y="0" width="16" height="16" href="data:image/png;base64,"/>
</svg>
""",
                encoding="utf-8",
            )

            result = evaluate_case(
                gt_spec={
                    "canvas": {"width_px": 32, "height_px": 16},
                    "elements": [
                        {"id": "F1", "kind": "formula", "box_px": [0, 0, 16, 16]},
                        {"id": "F2", "kind": "formula", "box_px": [16, 0, 16, 16]},
                    ],
                },
                gt_spec_path=root / "gt_page_spec.json",
                reference_image=reference,
                candidate_svg=candidate,
                rendered_png=rendered,
                case_id="formula-editability",
                bench_id="formula-editability",
                image_mse_threshold=0.02,
                image_iou_threshold=0.5,
                text_box_iou_threshold=0.5,
                text_sim_threshold=0.8,
                edge_canny_low=50,
                edge_canny_high=100,
                edge_blur_kernel=0,
                edge_dilation=1,
            )

            self.assertEqual(result["counts"]["gt_formula"], 2)
            self.assertEqual(result["counts"]["editable_formula_matches"], 1)
            self.assertEqual(result["metrics"]["formula_editable_representation"], 0.5)

    def test_image_miou_includes_zero_for_unmatched_gt_images(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            reference = root / "reference.png"
            rendered = root / "rendered.png"
            candidate = root / "candidate.svg"

            Image.new("RGB", (32, 16), "white").save(reference)
            Image.new("RGB", (32, 16), "white").save(rendered)
            candidate.write_text(
                """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 16">
  <image id="candidate-image" x="0" y="0" width="8" height="8" href="data:image/png;base64,"/>
</svg>
""",
                encoding="utf-8",
            )

            result = evaluate_case(
                gt_spec={
                    "canvas": {"width_px": 32, "height_px": 16},
                    "elements": [
                        {"id": "E1", "kind": "image", "box_px": [0, 0, 8, 8]},
                        {"id": "E2", "kind": "image", "box_px": [16, 0, 8, 8]},
                    ],
                },
                gt_spec_path=root / "gt_page_spec.json",
                reference_image=reference,
                candidate_svg=candidate,
                rendered_png=rendered,
                case_id="partial-image-match",
                bench_id="partial-image-match",
                image_mse_threshold=0.02,
                image_iou_threshold=0.5,
                text_box_iou_threshold=0.5,
                text_sim_threshold=0.8,
                edge_canny_low=50,
                edge_canny_high=100,
                edge_blur_kernel=0,
                edge_dilation=1,
            )

            self.assertEqual(result["counts"]["gt_image"], 2)
            self.assertEqual(result["counts"]["object_matched_images"], 1)
            self.assertAlmostEqual(result["metrics"]["image_miou"], 0.5)

    def test_text_box_recall_uses_spatial_iou_without_text_or_id_bypass(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            reference = root / "reference.png"
            rendered = root / "rendered.png"
            candidate = root / "candidate.svg"
            Image.new("RGB", (100, 100), "white").save(reference)
            Image.new("RGB", (100, 100), "white").save(rendered)
            candidate.write_text(
                """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <text x="10" y="20" font-size="10" textLength="40">different content</text>
  <text x="70" y="80" font-size="10" textLength="20" data-drawai-element-id="E2">same content</text>
</svg>
""",
                encoding="utf-8",
            )

            result = evaluate_case(
                gt_spec={
                    "canvas": {"width_px": 100, "height_px": 100},
                    "elements": [
                        {"id": "E1", "kind": "text", "box_px": [10, 10, 40, 12], "text": "hello"},
                        {
                            "id": "E2",
                            "kind": "text",
                            "box_px": [10, 50, 20, 12],
                            "text": "same content",
                        },
                    ],
                },
                gt_spec_path=root / "gt_page_spec.json",
                reference_image=reference,
                candidate_svg=candidate,
                rendered_png=rendered,
                case_id="text-box-spatial-only",
                bench_id="text-box-spatial-only",
                image_mse_threshold=0.02,
                image_iou_threshold=0.5,
                text_box_iou_threshold=0.5,
                text_sim_threshold=0.8,
                edge_canny_low=50,
                edge_canny_high=100,
                edge_blur_kernel=0,
                edge_dilation=1,
            )

            self.assertEqual(result["counts"]["matched_text_boxes"], 1)
            self.assertEqual(result["metrics"]["text_box_recall"], 0.5)
            self.assertEqual(result["matches"]["text_boxes"][0]["gt_id"], "E1")
            self.assertGreaterEqual(result["matches"]["text_boxes"][0]["iou"], 0.5)

    def test_text_box_recall_aggregates_split_lines_after_canvas_normalization(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            reference = root / "reference.png"
            rendered = root / "rendered.png"
            candidate = root / "candidate.svg"
            Image.new("RGB", (200, 100), "white").save(reference)
            Image.new("RGB", (200, 100), "white").save(rendered)
            candidate.write_text(
                """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">
  <text id="line-1" x="10" y="20" font-size="10" textLength="20">first</text>
  <text id="line-2" x="10" y="40" font-size="10" textLength="20">second</text>
</svg>
""",
                encoding="utf-8",
            )

            result = evaluate_case(
                gt_spec={
                    "canvas": {"width_px": 200, "height_px": 100},
                    "elements": [
                        {
                            "id": "E1",
                            "kind": "text",
                            "box_px": [20, 10, 40, 32],
                            "text": "first\nsecond",
                        },
                    ],
                },
                gt_spec_path=root / "gt_page_spec.json",
                reference_image=reference,
                candidate_svg=candidate,
                rendered_png=rendered,
                case_id="text-box-multiline",
                bench_id="text-box-multiline",
                image_mse_threshold=0.02,
                image_iou_threshold=0.5,
                text_box_iou_threshold=0.5,
                text_sim_threshold=0.8,
                edge_canny_low=50,
                edge_canny_high=100,
                edge_blur_kernel=0,
                edge_dilation=1,
            )

            self.assertEqual(result["metrics"]["text_box_recall"], 1.0)
            match = result["matches"]["text_boxes"][0]
            self.assertEqual(match["candidate_ids"], ["line-1", "line-2"])
            self.assertGreaterEqual(match["iou"], 0.5)


if __name__ == "__main__":
    unittest.main()
