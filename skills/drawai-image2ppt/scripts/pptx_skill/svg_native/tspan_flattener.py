"""Convert positioned SVG tspans to editable text frames or paragraphs."""

from __future__ import annotations

from xml.etree import ElementTree as ET


def flatten_positional_tspans(
    tree: ET.ElementTree,
    merge_paragraphs: bool = False,
) -> bool:
    """Flatten positional ``<tspan>`` elements into independent ``<text>``.

    When ``merge_paragraphs`` is True, mergeable paragraph blocks become
    one text element for downstream multi-paragraph conversion.

    Returns True if any tspan was rewritten.
    """
    from .flatten_tspan import flatten_text_with_tspans
    return flatten_text_with_tspans(tree, merge_paragraphs=merge_paragraphs)
