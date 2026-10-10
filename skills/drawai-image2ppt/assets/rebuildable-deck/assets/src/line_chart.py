#!/usr/bin/env python3
"""Plot iteration,score CSV data into standalone PNG and SVG assets."""

import argparse
import csv
import math
from itertools import pairwise
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def read_data(path):
    with Path(path).open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["iteration", "score"]:
            raise ValueError("CSV columns must be iteration,score")
        points = [(float(row["iteration"]), float(row["score"])) for row in reader]
    if len(points) < 2 or not all(math.isfinite(v) for p in points for v in p):
        raise ValueError("The chart needs at least two finite data points")
    if any(b[0] <= a[0] for a, b in pairwise(points)):
        raise ValueError("Iterations must be strictly increasing")
    return points


def draw(data, output_dir):
    points = read_data(data)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "svg.fonttype": "none"})
    fig, ax = plt.subplots(figsize=(8, 4), layout="constrained")
    x, y = zip(*points)
    ax.plot(x, y, color="#3168F5", linewidth=2.5, marker="o", markersize=5)
    ax.set_xlabel("Iteration", color="#526070", labelpad=10)
    ax.set_ylabel("Score (a.u.)", color="#526070", labelpad=10)
    ax.set_xticks(x)
    ax.tick_params(colors="#526070", length=0, pad=8)
    ax.grid(axis="y", color="#E5EBF2", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color("#E5EBF2")
    for suffix in ("png", "svg"):
        fig.savefig(output_dir / f"trend.{suffix}", dpi=200, facecolor="white")
    plt.close(fig)
    return points


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    draw(args.data, args.output_dir)


if __name__ == "__main__":
    main()
