"""Compatibility module for the shared image API implementation."""
import sys
from .. import image_api as implementation
sys.modules[__name__] = implementation
