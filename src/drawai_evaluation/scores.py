from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def normalized_score(metric: dict) -> float | None:
    if metric.get("status") != "scored":
        return None
    value = metric["score"]
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"invalid score: {metric.get('metric_id')}")
    return round(1.0 - value if metric.get("direction") == "down" else float(value), 6)


def average(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 6) if values else None


def summarize(evaluation_root: Path) -> dict:
    summary = json.loads((evaluation_root / "full_evaluation_summary.json").read_text())
    groups = defaultdict(list)
    for entry in summary["candidates"]:
        evaluation = json.loads(Path(entry["output_json"]).read_text())
        metrics = evaluation["metrics"]
        if len(metrics) != 39 or len({m["metric_id"] for m in metrics}) != 39:
            raise ValueError("each candidate must have exactly 39 unique metrics")
        scores = defaultdict(list)
        for metric in metrics:
            value = normalized_score(metric)
            if value is None:
                continue
            for key in ("overall", metric["primary"]["en"], metric["method"]):
                scores[key].append(value)
        groups[(entry["dag"], entry["lane"])].append({k: average(v) for k, v in scores.items()})
    rows = []
    for (method, model), candidates in sorted(groups.items()):
        row = {"method": method, "model": model, "candidate_count": len(candidates)}
        for key in ("overall", "Reconstruction", "Editability", "rule", "rubric"):
            values = [s[key] for s in candidates if s.get(key) is not None]
            row[key] = round(100 * sum(values) / len(values), 2) if values else None
        rows.append(row)
    result = {"scale": "0-100, higher is better", "partial": summary["partial"], "results": rows}
    coverage_path = evaluation_root / "coverage.json"
    if coverage_path.is_file():
        result["coverage"] = json.loads(coverage_path.read_text())
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate complete 39-metric candidate results.")
    parser.add_argument("--evaluation-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(summarize(args.evaluation_root), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
