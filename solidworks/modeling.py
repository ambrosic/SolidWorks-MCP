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
                        },
                        "endCondition": {
                            "type": "string",
                            "enum": ["BLIND", "THROUGH_ALL"],
                            "description": "End condition. BLIND (default): extrude to depth. THROUGH_ALL: through entire body.",
                            "default": "BLIND"
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
                        },
                        "endCondition": {
                            "type": "string",
                            "enum": ["BLIND", "THROUGH_ALL"],
                            "description": "End condition. BLIND (default): cut to depth. THROUGH_ALL: cut through entire body.",
                            "default": "BLIND"
                        }
                    },
                    "required": ["depth"]
                }
            ),
            Tool(
                name="solidworks_get_mass_properties",
                description="Evaluate and return mass properties of the active part: mass, volume, surface area, center of mass, and moments of inertia. The part must have material assigned for accurate mass; volume and surface area are always available.",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            Tool(
                name="solidworks_list_features",
                description="List all features in the feature tree of the active part. Returns feature names and types. Useful for discovering feature names needed by pattern, mirror, and other operations.",
                inputSchema={
                    "type": "object",
                    "properties": {}
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
                    if feature.GetTypeName2 == "ProfileFeature":
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
        elif tool_name == "solidworks_get_mass_properties":
            return self.get_mass_properties()
        elif tool_name == "solidworks_list_features":
            return self.list_features()
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
        end_condition = args.get("endCondition", "BLIND")
        end_type = {"BLIND": 0, "THROUGH_ALL": 1}.get(end_condition, 0)

        # Create extrusion with all 23 required parameters
        feature = doc.FeatureManager.FeatureExtrusion2(
            True,      # Sd (same direction)
            reverse,   # Flip direction
            False,     # Dir
            end_type,  # T1 (end condition type - 0 = Blind, 1 = Through All)
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

        feature_name = feature.Name
        doc.ViewZoomtofit2()

        logger.info(f"Extrusion '{feature_name}' created: {args['depth']}mm ({end_condition})")
        return f"✓ Extrusion '{feature_name}' {args['depth']}mm created ({end_condition})"

    def create_cut_extrusion(self, args: dict, sketching_tools) -> str:
        """Create cut-extrusion (removes material) from current sketch"""
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")

        # Force rebuild to ensure geometry is fully computed (especially
        # after fillet/chamfer/shell operations that modify the body)
        doc.ForceRebuild3(True)

        # Get current sketch name from sketching tools
        if sketching_tools and sketching_tools.current_sketch_name:
            sketch_name = sketching_tools.current_sketch_name
        else:
            sketch_name = self._get_latest_sketch_name(doc)

        sketch_feature = doc.FeatureByName(sketch_name)
        if not sketch_feature:
            raise Exception(f"Could not find sketch: {sketch_name}")

        doc.ClearSelection2(True)
        sketch_feature.Select2(False, 0)

        # Convert mm to meters
        depth = args["depth"] / 1000.0
        reverse = args.get("reverse", False)
        end_condition = args.get("endCondition", "BLIND")
        end_type = {"BLIND": 0, "THROUGH_ALL": 1}.get(end_condition, 0)

        # FeatureCut4 parameter names from sldworks.tlb (SW 2025 v33, 27 params):
        # Sd, Flip, Dir, T1, T2, D1, D2, Dchk1, Dchk2, Ddir1, Ddir2, Dang1, Dang2,
        # OffsetReverse1, OffsetReverse2, TranslateSurface1, TranslateSurface2,
        # NormalCut, UseFeatScope, UseAutoSelect,
        # AssemblyFeatureScope, AutoSelectComponents, PropagateFeatureToParts,
        # T0, StartOffset, FlipStartOffset, OptimizeGeometry
        feature = doc.FeatureManager.FeatureCut4(
            True,      # Sd
            reverse,   # Flip
            False,     # Dir
            end_type,  # T1 (0=Blind, 1=Through All)
            0,         # T2
            depth,     # D1
            0.0,       # D2
            False,     # Dchk1
            False,     # Dchk2
            False,     # Ddir1
            False,     # Ddir2
            0.0,       # Dang1
            0.0,       # Dang2
            False,     # OffsetReverse1
            False,     # OffsetReverse2
            False,     # TranslateSurface1
            False,     # TranslateSurface2
            False,     # NormalCut
            False,     # UseFeatScope
            True,      # UseAutoSelect
            False,     # AssemblyFeatureScope
            True,      # AutoSelectComponents
            False,     # PropagateFeatureToParts
            0,         # T0
            0.0,       # StartOffset
            False,     # FlipStartOffset
            False      # OptimizeGeometry
        )

        if not feature:
            raise Exception("Failed to create cut-extrusion")

        feature_name = feature.Name
        doc.ViewZoomtofit2()

        logger.info(f"Cut-extrusion '{feature_name}' created: {args['depth']}mm ({end_condition})")
        return f"✓ Cut-extrusion '{feature_name}' {args['depth']}mm created ({end_condition})"

    def get_mass_properties(self) -> str:
        """Evaluate mass properties of the active part"""
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")

        # Rebuild to ensure geometry is up to date
        doc.ForceRebuild3(True)

        # GetMassProperties is a property (not method) returning a 12-element tuple:
        #   [0-2] Center of mass (x, y, z) in meters
        #   [3]   Volume in m^3
        #   [4]   Surface area in m^2
        #   [5]   Mass in kg
        #   [6-8] Principal moments of inertia (Ixx, Iyy, Izz) in kg*m^2
        #   [9-11] Products of inertia (Ixy, Ixz, Iyz) in kg*m^2
        props = doc.GetMassProperties
        if not props or len(props) < 12:
            raise Exception("Failed to get mass properties (no solid body or no material assigned)")

        # Convert from SI to mm-based units
        com_x = props[0] * 1000.0
        com_y = props[1] * 1000.0
        com_z = props[2] * 1000.0
        volume_mm3 = props[3] * 1e9        # m^3 -> mm^3
        surface_area_mm2 = props[4] * 1e6  # m^2 -> mm^2
        mass_kg = props[5]

        # Moments of inertia: kg*m^2 -> kg*mm^2
        ixx = props[6] * 1e6
        iyy = props[7] * 1e6
        izz = props[8] * 1e6
        ixy = props[9] * 1e6
        ixz = props[10] * 1e6
        iyz = props[11] * 1e6

        result = "Mass Properties:\n"
        result += f"  Mass: {mass_kg:.6f} kg\n"
        result += f"  Volume: {volume_mm3:.2f} mm^3\n"
        result += f"  Surface Area: {surface_area_mm2:.2f} mm^2\n"
        result += f"  Center of Mass: ({com_x:.2f}, {com_y:.2f}, {com_z:.2f}) mm\n"
        result += f"  Moments of Inertia (kg*mm^2):\n"
        result += f"    Ixx={ixx:.4f}  Iyy={iyy:.4f}  Izz={izz:.4f}\n"
        result += f"    Ixy={ixy:.4f}  Ixz={ixz:.4f}  Iyz={iyz:.4f}"

        logger.info(f"Mass properties: mass={mass_kg:.6f}kg, volume={volume_mm3:.2f}mm^3")
        return result

    def list_features(self) -> str:
        """List all features in the feature tree"""
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")

        features = doc.FeatureManager.GetFeatures(True)
        if not features:
            return "No features found in the feature tree."

        result = "Feature Tree:\n"
        for feature in features:
            name = feature.Name
            type_name = feature.GetTypeName2
            # Skip origin-level items for cleaner output
            if type_name in ("OriginProfileFeature", "MaterialFolder", "SensorFolder"):
                continue
            result += f"  {name} ({type_name})\n"

        logger.info(f"Listed {len(features)} features")
        return result