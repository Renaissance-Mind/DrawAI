#!/usr/bin/env python3
"""Run the self-contained PPTX toolkit from any working directory."""

from __future__ import annotations

from pathlib import Path
import sys


def main() -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from pptx_skill.cli import pptx_cli

    return pptx_cli(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
