"""
SolidWorks Boss/Base Feature Tools
Revolve, Sweep, Loft, Boundary Boss
"""

import logging
import math
from mcp.types import Tool
from . import selection_helpers as sel

logger = logging.getLogger(__name__)


class FeatureTools:
    """Boss/Base feature operations (revolve, sweep, loft, boundary boss)"""

    def __init__(self, connection):
        self.connection = connection

    def get_tool_definitions(self) -> list[Tool]:
        return [
            Tool(
                name="solidworks_revolve",
                description="Revolve the current sketch around a centerline axis to create a solid of revolution. The sketch MUST contain a centerline that serves as the revolve axis.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "angle": {
                            "type": "number",
                            "description": "Revolve angle in degrees (default: 360 for full revolution)",
                            "default": 360
                        },
                        "reverse": {
                            "type": "boolean",
                            "description": "Reverse revolve direction (default: false)",
                            "default": False
                        }
                    }
                }
            ),
            Tool(
                name="solidworks_sweep",
                description="Create a swept boss/base by sweeping a profile sketch along a path sketch. Both sketches must already exist. The profile sketch defines the cross-section shape and the path sketch defines the sweep trajectory.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "profileSketch": {
                            "type": "string",
                            "description": "Name of the profile sketch (cross-section), e.g. 'Sketch1'"
                        },
                        "pathSketch": {
                            "type": "string",
                            "description": "Name of the path sketch (trajectory), e.g. 'Sketch2'"
                        }
                    },
                    "required": ["profileSketch", "pathSketch"]
                }
            ),
            Tool(
                name="solidworks_loft",
                description="Create a lofted boss/base by blending between two or more profile sketches. The profiles should be closed sketches on different planes. They are connected in the order provided. Workflow: create_sketch on Front plane, draw profile, exit_sketch (returns sketch name); create ref_plane offset from Front (returns plane name e.g. 'Plane1'); create_sketch on that plane name, draw second profile, exit_sketch; then call loft with the sketch names.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "profileSketches": {
                            "type": "array",
                            "description": "Ordered array of profile sketch names to loft between, e.g. ['Sketch1', 'Sketch2', 'Sketch3']",
                            "items": {"type": "string"},
                            "minItems": 2
                        }
                    },
                    "required": ["profileSketches"]
                }
            ),
            Tool(
                name="solidworks_boundary_boss",
                description="Create a boundary boss/base feature from multiple profile sketches with optional guide curves. Similar to loft but with more control over surface curvature.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "profiles": {
                            "type": "array",
                            "description": "Ordered array of direction 1 profile sketch names",
                            "items": {"type": "string"},
                            "minItems": 2
                        },
                        "guideCurves": {
                            "type": "array",
                            "description": "Optional array of direction 2 guide curve sketch names",
                            "items": {"type": "string"}
                        }
                    },
                    "required": ["profiles"]
                }
            ),
        ]

    def execute(self, tool_name: str, args: dict) -> str:
        self.connection.ensure_connection()
        dispatch = {
            "solidworks_revolve": lambda: self.revolve(args),
            "solidworks_sweep": lambda: self.sweep(args),
            "solidworks_loft": lambda: self.loft(args),
            "solidworks_boundary_boss": lambda: self.boundary_boss(args),
        }
        handler = dispatch.get(tool_name)
        if not handler:
            raise Exception(f"Unknown feature tool: {tool_name}")
        return handler()

    def _list_available_sketches(self, doc) -> str:
        """List all sketch names in the feature tree for error messages."""
        try:
            features = doc.FeatureManager.GetFeatures(True)
            if features:
                names = [f.Name for f in features if f.GetTypeName2 == "ProfileFeature"]
                return ", ".join(names) if names else "none found"
        except Exception:
            pass
        return "none found"

    def _get_latest_sketch_name(self, doc) -> str:
        """Walk the feature tree in reverse to find the most recent sketch."""
        try:
            features = doc.FeatureManager.GetFeatures(True)
            if features:
                for feature in reversed(features):
                    if feature.GetTypeName2 == "ProfileFeature":
                        return feature.Name
        except Exception as e:
            logger.warning(f"Could not find latest sketch: {e}")
        return "Sketch1"

    def revolve(self, args: dict) -> str:
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")

        angle_deg = args.get("angle", 360)
        angle_rad = math.radians(angle_deg)
        reverse = args.get("reverse", False)

        # Exit sketch mode and select the sketch
        doc.ClearSelection2(True)
        doc.SketchManager.InsertSketch(True)

        sketch_name = self._get_latest_sketch_name(doc)
        sketch_feature = doc.FeatureByName(sketch_name)
        if not sketch_feature:
            raise Exception(f"Could not find sketch: {sketch_name}")

        doc.ClearSelection2(True)
        sketch_feature.Select2(False, 0)

        # FeatureRevolve2 parameters:
        # SingleDir, IsSolid, IsThin, IsCut, ReverseDir,
        # BothDirectionUpToSameEntity,
        # Dir1Type, Dir2Type, Dir1Angle, Dir2Angle,
        # OffsetReverse1, OffsetReverse2,
        # OffsetDist1, OffsetDist2,
        # ThinType, ThinThickness1, ThinThickness2,
        # Merge, UseFeatScope, UseAutoSelect
        feature = doc.FeatureManager.FeatureRevolve2(
            True,       # SingleDir
            True,       # IsSolid
            False,      # IsThin
            False,      # IsCut
            reverse,    # ReverseDir
            False,      # BothDirectionUpToSameEntity
            0,          # Dir1Type: 0 = Blind
            0,          # Dir2Type: 0 = Blind
            angle_rad,  # Dir1Angle
            0.0,        # Dir2Angle
            False,      # OffsetReverse1
            False,      # OffsetReverse2
            0.0,        # OffsetDist1
            0.0,        # OffsetDist2
            0,          # ThinType: 0 = One Direction
            0.0,        # ThinThickness1
            0.0,        # ThinThickness2
            True,       # Merge
            True,       # UseFeatScope
            True,       # UseAutoSelect
        )

        if not feature:
            raise Exception("Failed to create revolve. Ensure sketch contains a centerline for the axis.")

        feature_name = feature.Name
        doc.ViewZoomtofit2()
        logger.info(f"Revolve '{feature_name}' created: {angle_deg}°")
        return f"✓ Revolve '{feature_name}' {angle_deg}° created"

    def sweep(self, args: dict) -> str:
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")

        profile_name = args["profileSketch"]
        path_name = args["pathSketch"]

        # Exit any active sketch
        doc.ClearSelection2(True)
        doc.SketchManager.InsertSketch(True)

        # Select profile sketch (mark=1) and path sketch (mark=4)
        sel.clear_selection(doc)
        if not sel.select_sketch(doc, profile_name, mark=1, append=False):
            raise Exception(f"Could not select profile sketch: {profile_name}")
        if not sel.select_sketch(doc, path_name, mark=4, append=True):
            raise Exception(f"Could not select path sketch: {path_name}")

        # InsertProtrusionSwept4 parameters (20 params):
        # Propagate, Alignment, TwistCtrlOption, TwistCtrlAngle,
        # PathAlign, ThinType, ThinThickness1, ThinThickness2, Merge,
        # UseFeatScope, UseAutoSelect, StartTangentType, EndTangentType,
        # StartTangentLength, EndTangentLength, MinimizeTwist, ...
        feature = doc.FeatureManager.InsertProtrusionSwept4(
            False,      # Propagate
            False,      # Alignment
            0,          # TwistCtrlOption: 0 = none
            False,      # PathAlign
            False,      # KeepTangency
            0,          # ThinType
            0.0,        # ThinThickness1
            0.0,        # ThinThickness2
            False,      # ThinReverse
            True,       # Merge
            True,       # UseFeatScope
            True,       # UseAutoSelect
            0,          # StartTangentType
            0,          # EndTangentType
            False,      # IsThinBody
            0.0,        # TwistAngle
            False,      # MergeSmoothFaces
        )

        if not feature:
            raise Exception(
                "Failed to create sweep. Ensure profile is a closed sketch "
                "and path is an open sketch on a different plane."
            )

        feature_name = feature.Name
        doc.ViewZoomtofit2()
        logger.info(f"Sweep '{feature_name}' created: profile={profile_name}, path={path_name}")
        return f"✓ Sweep '{feature_name}' created (profile: {profile_name}, path: {path_name})"

    def loft(self, args: dict) -> str:
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")

        profile_names = args["profileSketches"]
        if len(profile_names) < 2:
            raise Exception("At least 2 profile sketches are required for a loft")

        # Exit any active sketch
        doc.ClearSelection2(True)
        doc.SketchManager.InsertSketch(True)

        # Select all profile sketches with mark=1
        sel.clear_selection(doc)
        for i, name in enumerate(profile_names):
            if not sel.select_sketch(doc, name, mark=1, append=(i > 0)):
                available = self._list_available_sketches(doc)
                raise Exception(
                    f"Could not select profile sketch: {name}. "
                    f"Available sketches in feature tree: [{available}]"
                )

        # InsertProtrusionBlend2 parameters (18 params for SW2025):
        # Closed, KeepTangency, ForceNonRational, TessToleranceFactor,
        # StartMatchingType, EndMatchingType,
        # StartTangentLength, EndTangentLength,
        # MaintainTangency, Merge, IsThinBody,
        # Thickness1, Thickness2, ThinType,
        # UseFeatScope, UseAutoSelect, Close, GuideCurveInfluence
        feature = doc.FeatureManager.InsertProtrusionBlend2(
            False,  # Closed
            True,   # KeepTangency
            True,   # ForceNonRational
            1.0,    # TessToleranceFactor
            0,      # StartMatchingType: 0 = None
            0,      # EndMatchingType: 0 = None
            1.0,    # StartTangentLength
            1.0,    # EndTangentLength
            False,  # MaintainTangency
            True,   # Merge
            False,  # IsThinBody
            0.0,    # Thickness1
            0.0,    # Thickness2
            0,      # ThinType
            True,   # UseFeatScope
            True,   # UseAutoSelect
            True,   # Close (feature scope)
            0,      # GuideCurveInfluence
        )

        if not feature:
            raise Exception(
                "Failed to create loft. Ensure profiles are closed sketches on different planes."
            )

        feature_name = feature.Name
        doc.ViewZoomtofit2()
        logger.info(f"Loft '{feature_name}' created from {len(profile_names)} profiles")
        return f"✓ Loft '{feature_name}' created from {len(profile_names)} profiles: {', '.join(profile_names)}"

    def boundary_boss(self, args: dict) -> str:
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")

        profiles = args["profiles"]
        guide_curves = args.get("guideCurves", [])

        if len(profiles) < 2:
            raise Exception("At least 2 profile sketches are required for a boundary boss")

        # Exit any active sketch
        doc.ClearSelection2(True)
        doc.SketchManager.InsertSketch(True)

        # Select profiles (mark=1 for direction 1 profiles)
        sel.clear_selection(doc)
        for i, name in enumerate(profiles):
            if not sel.select_sketch(doc, name, mark=1, append=(i > 0)):
                available = self._list_available_sketches(doc)
                raise Exception(
                    f"Could not select profile sketch: {name}. "
                    f"Available sketches in feature tree: [{available}]"
                )

        # Select guide curves if provided (mark=2 for direction 2)
        for name in guide_curves:
            if not sel.select_sketch(doc, name, mark=2, append=True):
                logger.warning(f"Could not select guide curve: {name}")

        # InsertBoundaryBoss creates the feature from selected profiles
        feature = doc.FeatureManager.InsertBoundaryBoss()

        if not feature:
            raise Exception(
                "Failed to create boundary boss. Ensure profiles are closed sketches on different planes."
            )

        feature_name = feature.Name
        doc.ViewZoomtofit2()
        logger.info(f"Boundary boss '{feature_name}' created from {len(profiles)} profiles")
        return f"✓ Boundary boss '{feature_name}' created from {len(profiles)} profiles"
