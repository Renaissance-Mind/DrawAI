"""Locate the same versioned resources in a checkout or an installed wheel."""
from pathlib import Path


def resource_root() -> Path:
    checkout = Path(__file__).resolve().parents[2]
    if (checkout / "pyproject.toml").is_file() and (checkout / "skills").is_dir():
        return checkout
    root = Path(__file__).resolve().parent / "_resources"
    if not root.is_dir():
        raise FileNotFoundError("DrawAI resources are missing; reinstall the complete DrawAI wheel")
    return root


def resource_path(relative: str) -> Path:
    path = resource_root() / relative
    if not path.exists():
        raise FileNotFoundError(f"DrawAI resource is missing: {relative}")
    return path


def presentation_root() -> Path:
    return Path(__file__).resolve().parent.parent / "pptx_skill"
