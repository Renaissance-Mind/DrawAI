#!/usr/bin/env python3
"""Run the checkout's Python PPTX tools from any agent or working directory."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--repo-root", type=Path)
    args, remaining = parser.parse_known_args()
    root = (args.repo_root or Path(__file__).resolve().parents[3]).expanduser().resolve()
    if not (root / "src" / "drawai" / "pptx_cli.py").is_file():
        raise SystemExit("DrawAI Python source not found; pass --repo-root /path/to/DrawAI")
    sys.path.insert(0, str(root / "src"))
    from drawai.pptx_cli import pptx_cli

    return pptx_cli(remaining)


if __name__ == "__main__":
    raise SystemExit(main())
