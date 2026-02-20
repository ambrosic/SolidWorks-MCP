"""
SolidWorks Applied Feature Tools
Fillet, Chamfer, Shell, Draft, Rib, Wrap, Intersect
"""

import logging
import math
from mcp.types import Tool
from . import selection_helpers as sel

logger = logging.getLogger(__name__)


class AppliedFeatureTools:
    """Applied feature operations (fillet, chamfer, shell, draft, rib, wrap, intersect)"""

    def __init__(self, connection):
        self.connection = connection

    def get_tool_definitions(self) -> list[Tool]:
        return [
            Tool(
                name="solidworks_fillet",
                description="Apply a constant-radius fillet to one or more edges of the active part. Select edges by providing 3D coordinates (mm) near each edge.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "radius": {
                            "type": "number",
                            "description": "Fillet radius (mm)"
                        },
                        "edges": {
                            "type": "array",
                            "description": "Array of points on edges to fillet. Each point is {x, y, z} in mm.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "x": {"type": "number", "description": "X coordinate (mm)"},
                                    "y": {"type": "number", "description": "Y coordinate (mm)"},
                                    "z": {"type": "number", "description": "Z coordinate (mm)"}
                                },
                                "required": ["x", "y", "z"]
                            }
                        }
                    },
                    "required": ["radius", "edges"]
                }
            ),
            Tool(
                name="solidworks_chamfer",
                description="Apply a chamfer to one or more edges of the active part. Select edges by providing 3D coordinates (mm) near each edge.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "distance": {
                            "type": "number",
                            "description": "Chamfer distance (mm)"
                        },
                        "edges": {
                            "type": "array",
                            "description": "Array of points on edges to chamfer. Each point is {x, y, z} in mm.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "x": {"type": "number", "description": "X coordinate (mm)"},
                                    "y": {"type": "number", "description": "Y coordinate (mm)"},
                                    "z": {"type": "number", "description": "Z coordinate (mm)"}
                                },
                                "required": ["x", "y", "z"]
                            }
                        },
                        "angle": {
                            "type": "number",
                            "description": "Chamfer angle in degrees (default: 45). Only used with DISTANCE_ANGLE type.",
                            "default": 45
                        },
                        "distance2": {
                            "type": "number",
                            "description": "Second distance (mm) for TWO_DISTANCES chamfer type."
                        },
                        "type": {
                            "type": "string",
                            "enum": ["EQUAL_DISTANCE", "DISTANCE_ANGLE", "TWO_DISTANCES"],
                            "description": "Chamfer type. Default: EQUAL_DISTANCE",
                            "default": "EQUAL_DISTANCE"
                        }
                    },
                    "required": ["distance", "edges"]
                }
            ),
            Tool(
                name="solidworks_shell",
                description="Create a shell feature by hollowing out the active part. Select faces to remove (open) by providing 3D coordinates (mm).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "thickness": {
                            "type": "number",
                            "description": "Shell wall thickness (mm)"
                        },
                        "facesToRemove": {
                            "type": "array",
                            "description": "Array of points on faces to remove (open). Each point is {x, y, z} in mm.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "x": {"type": "number", "description": "X coordinate (mm)"},
                                    "y": {"type": "number", "description": "Y coordinate (mm)"},
                                    "z": {"type": "number", "description": "Z coordinate (mm)"}
                                },
                                "required": ["x", "y", "z"]
                            }
                        },
                        "outward": {
                            "type": "boolean",
                            "description": "Shell outward instead of inward (default: false)",
                            "default": False
                        }
                    },
                    "required": ["thickness", "facesToRemove"]
                }
            ),
            Tool(
                name="solidworks_draft",
                description="Apply a draft angle to one or more faces. Requires a neutral plane and faces to draft.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "angle": {
                            "type": "number",
                            "description": "Draft angle in degrees"
                        },
                        "neutralPlane": {
                            "type": "string",
                            "description": "Neutral plane name ('Front', 'Top', 'Right', or custom plane name)"
                        },
                        "facesToDraft": {
                            "type": "array",
                            "description": "Array of points on faces to apply draft to. Each point is {x, y, z} in mm.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "x": {"type": "number", "description": "X coordinate (mm)"},
                                    "y": {"type": "number", "description": "Y coordinate (mm)"},
                                    "z": {"type": "number", "description": "Z coordinate (mm)"}
                                },
                                "required": ["x", "y", "z"]
                            }
                        },
                        "outward": {
                            "type": "boolean",
                            "description": "Draft outward (default: false)",
                            "default": False
                        }
                    },
                    "required": ["angle", "neutralPlane", "facesToDraft"]
                }
            ),
            Tool(
                name="solidworks_rib",
                description="Create a rib feature from the current sketch. The sketch should be an open profile that intersects the existing body. The rib adds material between the sketch and the body.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "thickness": {
                            "type": "number",
                            "description": "Rib thickness (mm)"
                        },
                        "reverse": {
                            "type": "boolean",
                            "description": "Reverse thickness direction (default: false)",
                            "default": False
                        },
                        "flipSide": {
                            "type": "boolean",
                            "description": "Flip the extrusion side (default: false)",
                            "default": False
                        }
                    },
                    "required": ["thickness"]
                }
            ),
            Tool(
                name="solidworks_wrap",
                description="Wrap a sketch profile onto a face. The sketch should be on a plane tangent to or near the target face. Supports emboss (add material), deboss (remove material), and scribe (split line only).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["EMBOSS", "DEBOSS", "SCRIBE"],
                            "description": "Wrap type: EMBOSS adds material, DEBOSS removes material, SCRIBE creates a split line"
                        },
                        "face": {
                            "type": "object",
                            "description": "Point on the target face to wrap onto ({x, y, z} in mm)",
                            "properties": {
                                "x": {"type": "number"},
                                "y": {"type": "number"},
                                "z": {"type": "number"}
                            },
                            "required": ["x", "y", "z"]
                        },
                        "depth": {
                            "type": "number",
                            "description": "Depth (mm) for emboss/deboss. Not used for scribe."
                        }
                    },
                    "required": ["type", "face"]
                }
            ),
            Tool(
                name="solidworks_intersect",
                description="Create geometry from the intersection of overlapping bodies, surfaces, or planes. Select the bodies/surfaces before calling, or use the current selection.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "merge": {
                            "type": "boolean",
                            "description": "Merge the resulting bodies (default: true)",
                            "default": True
                        },
                        "bodies": {
                            "type": "array",
                            "description": "Names of bodies or features to intersect. If empty, uses current selection.",
                            "items": {"type": "string"}
                        }
                    }
                }
            ),
        ]

    def execute(self, tool_name: str, args: dict) -> str:
        self.connection.ensure_connection()
        dispatch = {
            "solidworks_fillet": lambda: self.fillet(args),
            "solidworks_chamfer": lambda: self.chamfer(args),
            "solidworks_shell": lambda: self.shell(args),
            "solidworks_draft": lambda: self.draft(args),
            "solidworks_rib": lambda: self.rib(args),
            "solidworks_wrap": lambda: self.wrap(args),
            "solidworks_intersect": lambda: self.intersect(args),
        }
        handler = dispatch.get(tool_name)
        if not handler:
            raise Exception(f"Unknown applied feature tool: {tool_name}")
        return handler()

    def fillet(self, args: dict) -> str:
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")

        radius_m = args["radius"] / 1000.0
        edges = args["edges"]

        sel.clear_selection(doc)
        count = sel.select_multiple_edges(doc, edges, mark=1)
        if count == 0:
            raise Exception("No edges could be selected for fillet")

        # FeatureFillet3 parameters:
        # Options (int bitmask), R1, R2, R3, ...
        # For constant-radius fillet: Options=1 (simple fillet), R1=radius
        feature = doc.FeatureManager.FeatureFillet3(
            1,          # Options: 1 = simple constant radius
            radius_m,   # R1: fillet radius
            0.0,        # R2: not used
            0.0,        # R3: not used
            0,          # Rho: not used
            0,          # Ftyp: 0 = constant
            0,          # Overflow: 0 = default
            0,          # Conic: 0 = circular
        )

        if not feature:
            raise Exception("Failed to create fillet. Verify edge coordinates are correct.")

        doc.ViewZoomtofit2()
        logger.info(f"Fillet created: {args['radius']}mm radius on {count} edge(s)")
        return f"✓ Fillet {args['radius']}mm radius applied to {count} edge(s)"

    def chamfer(self, args: dict) -> str:
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")

        distance_m = args["distance"] / 1000.0
        edges = args["edges"]
        chamfer_type = args.get("type", "EQUAL_DISTANCE")
        angle_deg = args.get("angle", 45)
        angle_rad = math.radians(angle_deg)
        distance2_m = args.get("distance2", args["distance"]) / 1000.0

        type_map = {
            "EQUAL_DISTANCE": 0,
            "DISTANCE_ANGLE": 1,
            "TWO_DISTANCES": 2,
        }
        chamfer_type_int = type_map.get(chamfer_type, 0)

        sel.clear_selection(doc)
        count = sel.select_multiple_edges(doc, edges, mark=0)
        if count == 0:
            raise Exception("No edges could be selected for chamfer")

        # InsertFeatureChamfer params:
        # Options, ChamferType, Width, Angle, OtherDist
        feature = doc.FeatureManager.InsertFeatureChamfer(
            4,                  # Options: 4 = select edges
            chamfer_type_int,   # Type: 0=equal, 1=dist-angle, 2=two-dist
            distance_m,         # Width (distance 1)
            angle_rad,          # Angle in radians
            distance2_m,        # Other distance
        )

        if not feature:
            raise Exception("Failed to create chamfer. Verify edge coordinates are correct.")

        doc.ViewZoomtofit2()
        logger.info(f"Chamfer created: {args['distance']}mm on {count} edge(s)")
        return f"✓ Chamfer {args['distance']}mm applied to {count} edge(s)"

    def shell(self, args: dict) -> str:
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")

        thickness_m = args["thickness"] / 1000.0
        faces = args["facesToRemove"]
        outward = args.get("outward", False)

        sel.clear_selection(doc)
        count = sel.select_multiple_faces(doc, faces, mark=0)
        if count == 0:
            raise Exception("No faces could be selected for shell")

        feature = doc.FeatureManager.InsertFeatureShell(
            thickness_m,
            outward
        )

        if not feature:
            raise Exception("Failed to create shell. Verify face coordinates are correct.")

        doc.ViewZoomtofit2()
        logger.info(f"Shell created: {args['thickness']}mm thickness, {count} face(s) removed")
        return f"✓ Shell {args['thickness']}mm created with {count} face(s) removed"

    def draft(self, args: dict) -> str:
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")

        angle_rad = math.radians(args["angle"])
        outward = args.get("outward", False)

        sel.clear_selection(doc)

        # Select neutral plane first
        plane_name = args["neutralPlane"]
        if not sel.select_plane_with_mark(doc, plane_name, mark=1, append=False):
            raise Exception(f"Could not select neutral plane: {plane_name}")

        # Select faces to draft
        faces = args["facesToDraft"]
        count = 0
        for pt in faces:
            if sel.select_face(doc, pt["x"], pt["y"], pt["z"], append=True, mark=0):
                count += 1
        if count == 0:
            raise Exception("No faces could be selected for draft")

        # InsertFeatureDraft: type, angle, outward
        # Type 0 = Neutral plane draft
        feature = doc.FeatureManager.InsertFeatureDraft(
            0,          # DraftType: 0 = Neutral Plane
            angle_rad,  # Draft angle in radians
            outward,    # Draft outward
        )

        if not feature:
            raise Exception("Failed to create draft. Verify selections are correct.")

        doc.ViewZoomtofit2()
        logger.info(f"Draft created: {args['angle']}° on {count} face(s)")
        return f"✓ Draft {args['angle']}° applied to {count} face(s)"

    def rib(self, args: dict) -> str:
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")

        thickness_m = args["thickness"] / 1000.0
        reverse = args.get("reverse", False)
        flip_side = args.get("flipSide", False)

        # Exit current sketch and select it
        doc.ClearSelection2(True)
        doc.SketchManager.InsertSketch(True)

        # Find and select the latest sketch
        features = doc.FeatureManager.GetFeatures(True)
        sketch_name = "Sketch1"
        if features:
            for feature in reversed(features):
                if feature.GetTypeName2 == "ProfileFeature":
                    sketch_name = feature.Name
                    break

        sketch_feature = doc.FeatureByName(sketch_name)
        if not sketch_feature:
            raise Exception(f"Could not find sketch: {sketch_name}")
        doc.ClearSelection2(True)
        sketch_feature.Select2(False, 0)

        # InsertRib params: IsSolid, IsFlipped, Thickness, RibType, Direction, ...
        # RibType: 0 = Linear, 1 = Natural
        feature = doc.FeatureManager.InsertRib(
            True,           # IsSolid
            flip_side,      # IsFlipped
            reverse,        # ReverseThicknessDir
            thickness_m,    # Thickness
            0,              # RibType: 0 = Linear
            False,          # IsDrafted
            0.0,            # DraftAngle
            False,          # DraftOutward
            False,          # IsNatural
        )

        if not feature:
            raise Exception("Failed to create rib. Ensure sketch profile intersects the body.")

        doc.ViewZoomtofit2()
        logger.info(f"Rib created: {args['thickness']}mm thickness")
        return f"✓ Rib {args['thickness']}mm created"

    def wrap(self, args: dict) -> str:
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")

        wrap_type = args["type"]
        face = args["face"]
        depth_m = args.get("depth", 1.0) / 1000.0

        type_map = {
            "EMBOSS": 0,
            "DEBOSS": 1,
            "SCRIBE": 2,
        }
        wrap_type_int = type_map.get(wrap_type, 0)

        # Exit current sketch
        doc.ClearSelection2(True)
        doc.SketchManager.InsertSketch(True)

        # Find and select the latest sketch
        features = doc.FeatureManager.GetFeatures(True)
        sketch_name = "Sketch1"
        if features:
            for feature in reversed(features):
                if feature.GetTypeName2 == "ProfileFeature":
                    sketch_name = feature.Name
                    break

        # Select sketch and face
        sel.clear_selection(doc)
        sel.select_sketch(doc, sketch_name, mark=0, append=False)
        sel.select_face(doc, face["x"], face["y"], face["z"], append=True, mark=1)

        # InsertWrapFeature2 params: Type, Thickness, ReverseDir, ...
        feature = doc.FeatureManager.InsertWrapFeature2(
            wrap_type_int,  # Type: 0=Emboss, 1=Deboss, 2=Scribe
            depth_m,        # Thickness in meters
            False,          # ReverseDir
        )

        if not feature:
            raise Exception("Failed to create wrap feature. Ensure sketch is on a plane near the target face.")

        doc.ViewZoomtofit2()
        logger.info(f"Wrap created: {wrap_type}, depth={args.get('depth', 1.0)}mm")
        return f"✓ Wrap ({wrap_type}) created"

    def intersect(self, args: dict) -> str:
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")

        merge = args.get("merge", True)
        bodies = args.get("bodies", [])

        if bodies:
            sel.clear_selection(doc)
            for i, name in enumerate(bodies):
                sel.select_feature(doc, name, mark=0, append=(i > 0))

        # InsertIntersect params: merge
        feature = doc.FeatureManager.InsertIntersect(
            merge,  # Merge result
        )

        if not feature:
            raise Exception("Failed to create intersect feature. Ensure overlapping bodies exist.")

        doc.ViewZoomtofit2()
        logger.info("Intersect feature created")
        return "✓ Intersect feature created"
