"""
SolidWorks Pattern and Mirror Tools
Linear Pattern, Circular Pattern, Mirror
"""

import logging
import math
from mcp.types import Tool
from . import selection_helpers as sel

logger = logging.getLogger(__name__)


class PatternTools:
    """Pattern and mirror feature operations"""

    def __init__(self, connection):
        self.connection = connection

    def get_tool_definitions(self) -> list[Tool]:
        return [
            Tool(
                name="solidworks_linear_pattern",
                description="Create a linear pattern of features in one or two directions. Specify features to pattern, a direction edge, spacing, and count.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "features": {
                            "type": "array",
                            "description": "Array of feature names to pattern (e.g. ['Cut-Extrude1', 'Fillet1']). Use solidworks_list_features to discover feature names.",
                            "items": {"type": "string"}
                        },
                        "direction1": {
                            "type": "object",
                            "description": "Point on an edge that defines pattern direction 1 ({x, y, z} in mm)",
                            "properties": {
                                "x": {"type": "number"},
                                "y": {"type": "number"},
                                "z": {"type": "number"}
                            },
                            "required": ["x", "y", "z"]
                        },
                        "spacing1": {
                            "type": "number",
                            "description": "Spacing between instances in direction 1 (mm)"
                        },
                        "count1": {
                            "type": "integer",
                            "description": "Total number of instances in direction 1 (including original)"
                        },
                        "reverseDir1": {
                            "type": "boolean",
                            "description": "Reverse direction 1 (default: false)",
                            "default": False
                        },
                        "direction2": {
                            "type": "object",
                            "description": "Optional: point on an edge defining pattern direction 2 ({x, y, z} in mm)",
                            "properties": {
                                "x": {"type": "number"},
                                "y": {"type": "number"},
                                "z": {"type": "number"}
                            },
                            "required": ["x", "y", "z"]
                        },
                        "spacing2": {
                            "type": "number",
                            "description": "Spacing in direction 2 (mm)"
                        },
                        "count2": {
                            "type": "integer",
                            "description": "Total instances in direction 2"
                        },
                        "reverseDir2": {
                            "type": "boolean",
                            "description": "Reverse direction 2 (default: false)",
                            "default": False
                        }
                    },
                    "required": ["features", "direction1", "spacing1", "count1"]
                }
            ),
            Tool(
                name="solidworks_circular_pattern",
                description="Create a circular pattern of features around an axis. Specify features to pattern, a rotation axis, count, and angular spacing.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "features": {
                            "type": "array",
                            "description": "Array of feature names to pattern. Use solidworks_list_features to discover names.",
                            "items": {"type": "string"}
                        },
                        "axis": {
                            "type": "string",
                            "description": "Name of the axis or edge for rotation. Can be a reference axis name, or a standard axis like 'Top Plane' edge."
                        },
                        "axisEdge": {
                            "type": "object",
                            "description": "Alternative: point on an edge to use as axis ({x, y, z} in mm). Use this instead of 'axis' when selecting by coordinate.",
                            "properties": {
                                "x": {"type": "number"},
                                "y": {"type": "number"},
                                "z": {"type": "number"}
                            },
                            "required": ["x", "y", "z"]
                        },
                        "count": {
                            "type": "integer",
                            "description": "Total number of instances (including original)"
                        },
                        "angle": {
                            "type": "number",
                            "description": "Total angle for pattern in degrees (default: 360)",
                            "default": 360
                        },
                        "equalSpacing": {
                            "type": "boolean",
                            "description": "Space instances equally within the angle (default: true)",
                            "default": True
                        }
                    },
                    "required": ["features", "count"]
                }
            ),
            Tool(
                name="solidworks_mirror",
                description="Mirror one or more features about a reference plane or planar face. Creates a symmetric copy of the selected features.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "features": {
                            "type": "array",
                            "description": "Array of feature names to mirror. Use solidworks_list_features to discover names.",
                            "items": {"type": "string"}
                        },
                        "mirrorPlane": {
                            "type": "string",
                            "description": "Mirror plane name ('Front', 'Top', 'Right', or custom plane name)"
                        },
                        "mirrorFace": {
                            "type": "object",
                            "description": "Alternative: point on a planar face to use as mirror plane ({x, y, z} in mm). Use this instead of 'mirrorPlane'.",
                            "properties": {
                                "x": {"type": "number"},
                                "y": {"type": "number"},
                                "z": {"type": "number"}
                            },
                            "required": ["x", "y", "z"]
                        }
                    },
                    "required": ["features"]
                }
            ),
        ]

    def execute(self, tool_name: str, args: dict) -> str:
        self.connection.ensure_connection()
        dispatch = {
            "solidworks_linear_pattern": lambda: self.linear_pattern(args),
            "solidworks_circular_pattern": lambda: self.circular_pattern(args),
            "solidworks_mirror": lambda: self.mirror(args),
        }
        handler = dispatch.get(tool_name)
        if not handler:
            raise Exception(f"Unknown pattern tool: {tool_name}")
        return handler()

    def linear_pattern(self, args: dict) -> str:
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")

        features = args["features"]
        dir1 = args["direction1"]
        spacing1_m = args["spacing1"] / 1000.0
        count1 = args["count1"]
        reverse1 = args.get("reverseDir1", False)

        # Direction 2 (optional)
        dir2 = args.get("direction2")
        spacing2_m = args.get("spacing2", 0) / 1000.0 if args.get("spacing2") else 0.0
        count2 = args.get("count2", 1)
        reverse2 = args.get("reverseDir2", False)
        use_dir2 = dir2 is not None and count2 > 1

        sel.clear_selection(doc)

        # Select direction 1 edge (mark=1)
        if not sel.select_edge(doc, dir1["x"], dir1["y"], dir1["z"], append=False, mark=1):
            raise Exception("Could not select direction 1 edge")

        # Select direction 2 edge if needed (mark=2)
        if use_dir2:
            if not sel.select_edge(doc, dir2["x"], dir2["y"], dir2["z"], append=True, mark=2):
                raise Exception("Could not select direction 2 edge")

        # Select features to pattern (mark=4)
        for i, name in enumerate(features):
            if not sel.select_feature(doc, name, mark=4, append=True):
                raise Exception(f"Could not select feature: {name}")

        # FeatureLinearPattern4 parameters:
        # D1Num, D1Spc, D1Dir, D1Flip,
        # D2Num, D2Spc, D2Dir, D2Flip,
        # SeedOnly, GeomPattern, VarySketch, ...
        feature = doc.FeatureManager.FeatureLinearPattern4(
            count1,         # D1Num: number of instances
            spacing1_m,     # D1Spc: spacing in meters
            True,           # D1Dir: use direction 1
            reverse1,       # D1Flip: reverse direction 1
            count2,         # D2Num
            spacing2_m,     # D2Spc
            use_dir2,       # D2Dir: use direction 2
            reverse2,       # D2Flip
            True,           # SeedOnly
            False,          # GeomPattern
            False,          # VarySketch
        )

        if not feature:
            raise Exception("Failed to create linear pattern. Verify feature names and direction edge.")

        doc.ViewZoomtofit2()
        total = count1 * count2 if use_dir2 else count1
        logger.info(f"Linear pattern created: {total} instances")
        return f"✓ Linear pattern created: {count1}x{count2 if use_dir2 else 1} = {total} instances"

    def circular_pattern(self, args: dict) -> str:
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")

        features = args["features"]
        count = args["count"]
        angle_deg = args.get("angle", 360)
        angle_rad = math.radians(angle_deg)
        equal_spacing = args.get("equalSpacing", True)

        sel.clear_selection(doc)

        # Select axis (mark=1)
        axis_name = args.get("axis")
        axis_edge = args.get("axisEdge")
        if axis_name:
            if not sel.select_axis(doc, axis_name, mark=1, append=False):
                # Try as edge
                if not sel.select_feature(doc, axis_name, mark=1, append=False):
                    raise Exception(f"Could not select axis: {axis_name}")
        elif axis_edge:
            if not sel.select_edge(doc, axis_edge["x"], axis_edge["y"], axis_edge["z"], append=False, mark=1):
                raise Exception("Could not select axis edge")
        else:
            raise Exception("Either 'axis' or 'axisEdge' must be provided")

        # Select features to pattern (mark=4)
        for i, name in enumerate(features):
            if not sel.select_feature(doc, name, mark=4, append=True):
                raise Exception(f"Could not select feature: {name}")

        # FeatureCircularPattern4 parameters:
        # Num, Spacing, FlipDir, EqualSpacing,
        # SeedOnly, GeomPattern, VarySketch, ...
        feature = doc.FeatureManager.FeatureCircularPattern4(
            count,          # Num: number of instances
            angle_rad,      # Spacing: total angle in radians
            False,          # FlipDir
            equal_spacing,  # EqualSpacing
            True,           # SeedOnly
            False,          # GeomPattern
            False,          # VarySketch
        )

        if not feature:
            raise Exception("Failed to create circular pattern. Verify feature names and axis.")

        doc.ViewZoomtofit2()
        logger.info(f"Circular pattern created: {count} instances over {angle_deg}°")
        return f"✓ Circular pattern created: {count} instances over {angle_deg}°"

    def mirror(self, args: dict) -> str:
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")

        features = args["features"]
        mirror_plane = args.get("mirrorPlane")
        mirror_face = args.get("mirrorFace")

        sel.clear_selection(doc)

        # Select mirror plane (mark=specific value for mirror)
        if mirror_plane:
            if not sel.select_plane_with_mark(doc, mirror_plane, mark=4, append=False):
                raise Exception(f"Could not select mirror plane: {mirror_plane}")
        elif mirror_face:
            if not sel.select_face(doc, mirror_face["x"], mirror_face["y"], mirror_face["z"], append=False, mark=4):
                raise Exception("Could not select mirror face")
        else:
            raise Exception("Either 'mirrorPlane' or 'mirrorFace' must be provided")

        # Select features to mirror (mark=1)
        for i, name in enumerate(features):
            if not sel.select_feature(doc, name, mark=1, append=True):
                raise Exception(f"Could not select feature: {name}")

        # InsertMirrorFeature2 parameters:
        # FaceOrPlane, Options
        feature = doc.FeatureManager.InsertMirrorFeature2(
            True,   # MirrorBody: False = mirror features, True = mirror body
            False,  # GeometryPattern
            False,  # PropagateVisualProps
            True,   # Merge
            False,  # KnitSurface
        )

        if not feature:
            raise Exception("Failed to create mirror feature. Verify plane and feature selections.")

        doc.ViewZoomtofit2()
        logger.info(f"Mirror created for {len(features)} feature(s)")
        return f"✓ Mirror created for {len(features)} feature(s)"
