"""
SolidWorks MCP Module
"""

from .connection import SolidWorksConnection
from .sketching import SketchingTools
from .modeling import ModelingTools
from .features import FeatureTools
from .cut_features import CutFeatureTools
from .applied_features import AppliedFeatureTools
from .patterns import PatternTools
from .hole_features import HoleFeatureTools
from .reference_geometry import ReferenceGeometryTools

__all__ = [
    'SolidWorksConnection',
    'SketchingTools',
    'ModelingTools',
    'FeatureTools',
    'CutFeatureTools',
    'AppliedFeatureTools',
    'PatternTools',
    'HoleFeatureTools',
    'ReferenceGeometryTools',
]
