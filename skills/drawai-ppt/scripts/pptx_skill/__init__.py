"""Standalone presentation document authoring and PowerPoint I/O."""

from .io import inspect_pptx, render_pptx, validate_pptx_package
from .document import (
    Document,
    Page,
    Object,
    load_document,
    import_pptx,
    import_svg,
    export_pptx,
    export_svg,
    duplicate_page,
    insert_svg,
)

__all__ = [
    "Document",
    "Page",
    "Object",
    "load_document",
    "import_pptx",
    "import_svg",
    "export_pptx",
    "export_svg",
    "duplicate_page",
    "insert_svg",
    "inspect_pptx",
    "render_pptx",
    "validate_pptx_package",
]
