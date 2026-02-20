"""
SolidWorks Modeling Tools
Handles 3D feature creation like extrusions, revolves, etc.
"""

import logging
from mcp.types import Tool
from typing import Any

logger = logging.getLogger(__name__)


class ModelingTools:
    """3D modeling feature operations"""
    
    def __init__(self, connection):
        self.connection = connection
    
    def get_tool_definitions(self) -> list[Tool]:
        """Define all modeling tools"""
        return [
            Tool(
                name="solidworks_new_part",
                description="Create a new blank part document. Use this to start a completely new design.",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            Tool(
                name="solidworks_create_extrusion",
                description="Extrude the current sketch to create a 3D feature",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "depth": {
                            "type": "number",
                            "description": "Extrusion depth (mm)"
                        },
                        "reverse": {
                            "type": "boolean",
                            "default": False,
                            "description": "Reverse direction"
                        }
                    },
                    "required": ["depth"]
                }
            ),
            Tool(
                name="solidworks_create_cut_extrusion",
                description="Cut-extrude the current sketch to remove material from an existing 3D body",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "depth": {
                            "type": "number",
                            "description": "Cut depth (mm)"
                        },
                        "reverse": {
                            "type": "boolean",
                            "default": False,
                            "description": "Reverse cut direction"
                        }
                    },
                    "required": ["depth"]
                }
            )
        ]
    
    def _get_latest_sketch_name(self, doc) -> str:
        """Walk the feature tree in reverse to find the most recent sketch feature"""
        try:
            feature_count = doc.FeatureManager.GetFeatureCount(True)
            features = doc.FeatureManager.GetFeatures(True)
            if features:
                for feature in reversed(features):
                    if feature.GetTypeName2() == "ProfileFeature":
                        name = feature.Name
                        logger.info(f"Latest sketch found in feature tree: {name}")
                        return name
        except Exception as e:
            logger.warning(f"Could not enumerate features to find latest sketch: {e}")
        logger.warning("No sketch found in feature tree, falling back to Sketch1")
        return "Sketch1"

    def execute(self, tool_name: str, args: dict, sketching_tools=None) -> str:
        """Execute a modeling tool"""
        self.connection.ensure_connection()
        
        if tool_name == "solidworks_new_part":
            return self.new_part(sketching_tools)
        elif tool_name == "solidworks_create_extrusion":
            return self.create_extrusion(args, sketching_tools)
        elif tool_name == "solidworks_create_cut_extrusion":
            return self.create_cut_extrusion(args, sketching_tools)
        else:
            raise Exception(f"Unknown modeling tool: {tool_name}")
    
    def new_part(self, sketching_tools) -> str:
        """Explicitly create a new part document"""
        doc = self.connection.create_new_part()
        
        # Reset sketch counter if we have access to sketching tools
        if sketching_tools:
            sketching_tools.sketch_counter = 0
            sketching_tools.current_sketch_name = None
        
        logger.info("New part document created")
        return "✓ New part document created and ready"
    
    def create_extrusion(self, args: dict, sketching_tools) -> str:
        """Create extrusion from current sketch"""
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")
        
        # Exit sketch mode
        doc.ClearSelection2(True)
        doc.SketchManager.InsertSketch(True)
        
        # Get current sketch name from sketching tools
        if sketching_tools and sketching_tools.current_sketch_name:
            sketch_name = sketching_tools.current_sketch_name
        else:
            sketch_name = self._get_latest_sketch_name(doc)

        # Select the sketch
        sketch_feature = doc.FeatureByName(sketch_name)
        if not sketch_feature:
            raise Exception(f"Could not find sketch: {sketch_name}")

        doc.ClearSelection2(True)
        sketch_feature.Select2(False, 0)

        # Convert mm to meters
        depth = args["depth"] / 1000.0
        reverse = args.get("reverse", False)

        # Create extrusion with all 23 required parameters
        feature = doc.FeatureManager.FeatureExtrusion2(
            True,      # Sd (same direction)
            reverse,   # Flip direction
            False,     # Dir
            0,         # T1 (end condition type - 0 = Blind)
            0,         # T2
            depth,     # D1 (depth in meters)
            0.0,       # D2
            False,     # DDir
            False,     # Dang
            False,     # OffsetReverse1
            False,     # OffsetReverse2
            0.0,       # Dang1 (draft angle 1)
            0.0,       # Dang2 (draft angle 2)
            False,     # T1UseLen
            False,     # T2UseLen
            False,     # T3UseLen
            False,     # T4UseLen
            True,      # T1UseLen2
            True,      # T2UseLen2
            True,      # T3UseLen2
            0,         # MergeSmooth
            0,         # StartCond
            False      # ContourType
        )
        
        if not feature:
            raise Exception("Failed to create extrusion")
        
        doc.ViewZoomtofit2()
        
        logger.info(f"Extrusion created: {args['depth']}mm")
        return f"✓ Extrusion {args['depth']}mm created"

    def create_cut_extrusion(self, args: dict, sketching_tools) -> str:
        """Create cut-extrusion (removes material) from current sketch"""
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")

        # Exit sketch mode
        doc.ClearSelection2(True)
        doc.SketchManager.InsertSketch(True)

        # Get current sketch name from sketching tools
        if sketching_tools and sketching_tools.current_sketch_name:
            sketch_name = sketching_tools.current_sketch_name
        else:
            sketch_name = self._get_latest_sketch_name(doc)

        # Select the sketch
        sketch_feature = doc.FeatureByName(sketch_name)
        if not sketch_feature:
            raise Exception(f"Could not find sketch: {sketch_name}")

        doc.ClearSelection2(True)
        sketch_feature.Select2(False, 0)

        # Convert mm to meters
        depth = args["depth"] / 1000.0
        reverse = args.get("reverse", False)

        # Create cut-extrusion: Sd=False removes material instead of adding it
        feature = doc.FeatureManager.FeatureExtrusion2(
            False,     # Sd = False → cut (removes material)
            reverse,   # Flip direction
            False,     # Dir
            0,         # T1 (end condition type - 0 = Blind)
            0,         # T2
            depth,     # D1 (depth in meters)
            0.0,       # D2
            False,     # DDir
            False,     # Dang
            False,     # OffsetReverse1
            False,     # OffsetReverse2
            0.0,       # Dang1 (draft angle 1)
            0.0,       # Dang2 (draft angle 2)
            False,     # T1UseLen
            False,     # T2UseLen
            False,     # T3UseLen
            False,     # T4UseLen
            True,      # T1UseLen2
            True,      # T2UseLen2
            True,      # T3UseLen2
            0,         # MergeSmooth
            0,         # StartCond
            False      # ContourType
        )

        if not feature:
            raise Exception("Failed to create cut-extrusion")

        doc.ViewZoomtofit2()

        logger.info(f"Cut-extrusion created: {args['depth']}mm")
        return f"✓ Cut-extrusion {args['depth']}mm created"