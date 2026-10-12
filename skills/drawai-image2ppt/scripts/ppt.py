#!/usr/bin/env python3
"""Compatibility launcher for DrawAI's installed presentation core."""

from __future__ import annotations

from pathlib import Path
import sys


def main() -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    source = Path(__file__).resolve().parents[3] / "src"
    if (source / "drawai").is_dir():
        sys.path.insert(0, str(source))
    from pptx_skill.cli import pptx_cli

    return pptx_cli(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
