"""
SolidWorks MCP Module
"""

from .connection import SolidWorksConnection
from .sketching import SketchingTools
from .modeling import ModelingTools

__all__ = ['SolidWorksConnection', 'SketchingTools', 'ModelingTools']