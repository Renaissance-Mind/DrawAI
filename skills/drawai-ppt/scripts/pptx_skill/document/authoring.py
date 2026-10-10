"""Construct native objects from author-friendly coordinates."""

import math

from .model import Object


def make_connector(object_id, start, end, *, properties=None):
    """Create a directed connector from two (x, y) endpoints in points."""
    if len(start) != 2 or len(end) != 2:
        raise ValueError("Connector start and end each need two coordinates in points")
    values = [*start, *end]
    if any(
        isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
        for v in values
    ):
        raise ValueError("Connector coordinates must be finite numbers")
    x1, y1 = start
    x2, y2 = end
    if start[0] == end[0] and start[1] == end[1]:
        raise ValueError("Connector endpoints must differ")
    props = dict(properties or {})
    controlled = {"object.frame", "object.flip_horizontal", "object.flip_vertical"}
    if controlled & props.keys():
        raise ValueError(
            "make_connector derives its frame and flips from the endpoints"
        )
    props.setdefault("connector.geometry", "straight")
    props.update(
        {
            "object.frame": {
                "left": min(x1, x2),
                "top": min(y1, y2),
                "width": abs(x2 - x1),
                "height": abs(y2 - y1),
            },
            "object.flip_horizontal": x2 < x1,
            "object.flip_vertical": y2 < y1,
        }
    )
    return Object(id=object_id, kind="connector", properties=props)
