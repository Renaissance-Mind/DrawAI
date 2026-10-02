from .model import Document, Page, Object, load_document
from .export import export_pptx
from .importer import import_pptx, import_svg
from .svg import export_svg
from .editing import duplicate_page
from .insert import insert_svg

__all__ = [
    "Document",
    "Page",
    "Object",
    "load_document",
    "export_pptx",
    "export_svg",
    "import_pptx",
    "import_svg",
    "duplicate_page",
    "insert_svg",
]
