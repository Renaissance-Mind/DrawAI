from __future__ import annotations

def create_app(*args, **kwargs):
    from .api import create_app as implementation
    return implementation(*args, **kwargs)

__all__ = ["create_app"]
