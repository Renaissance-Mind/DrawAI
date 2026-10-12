"""Compatibility launcher for the shared DrawAI core."""
from pathlib import Path
import sys
_source = Path(__file__).resolve().parents[3] / "src"
if (_source / "drawai").is_dir():
    sys.path.insert(0, str(_source))
from drawai.session_plan import create_plan, identify_model, main
if __name__ == "__main__":
    main()
