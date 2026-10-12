"""Compatibility launcher for the shared DrawAI core."""
from pathlib import Path
import sys
_source = Path(__file__).resolve().parents[3] / "src"
if (_source / "drawai").is_dir():
    sys.path.insert(0, str(_source))
from drawai.visual_deck import save_visual_deck, verify_visual_deck, ratio_value, main
if __name__ == "__main__":
    main()
