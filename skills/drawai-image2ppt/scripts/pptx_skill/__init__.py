"""Compatibility import: the implementation is installed with DrawAI."""
from pathlib import Path
import sys

_source = Path(__file__).resolve().parents[4] / "src"
if (_source / "drawai").is_dir():
    sys.path.insert(0, str(_source))
from drawai.resources import presentation_root
__path__ = [str(presentation_root())]
exec(compile((presentation_root() / "__init__.py").read_text(encoding="utf-8"), str(presentation_root() / "__init__.py"), "exec"))
