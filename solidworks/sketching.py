"""
SolidWorks Sketching Tools
Handles sketch creation and drawing operations with spatial tracking
"""

import logging
from mcp.types import Tool
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class SketchingTools:
    """Sketch creation and drawing operations with spatial awareness"""
    
    def __init__(self, connection):
        self.connection = connection
        self.current_sketch_name = None
        self.sketch_counter = 0
        
        # Spatial tracking - stores info about created shapes
        self.created_shapes = []  # List of shape info
        self.last_shape = None    # Most recent shape for "relative to last" positioning
    
    def get_tool_definitions(self) -> list[Tool]:
        """Define all sketching tools"""
        return [
            Tool(
                name="solidworks_create_sketch",
                description="Create a new sketch on a specified plane. If no part exists, creates one automatically.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "plane": {
                            "type": "string",
                            "enum": ["Front", "Top", "Right"],
                            "description": "Reference plane for sketch"
                        },
                        "faceX": {
                            "type": "number",
                            "description": "X coordinate (mm) of a point on the solid face to sketch on. Use with faceY and faceZ to create a sketch on an existing solid face instead of a reference plane."
                        },
                        "faceY": {
                            "type": "number",
                            "description": "Y coordinate (mm) of a point on the solid face to sketch on."
                        },
                        "faceZ": {
                            "type": "number",
                            "description": "Z coordinate (mm) of a point on the solid face to sketch on."
                        }
                    }
                }
            ),
            Tool(
                name="solidworks_sketch_rectangle",
                description="Draw a rectangle in the active sketch. Can specify absolute position or position relative to the last created shape.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "width": {
                            "type": "number",
                            "description": "Width of rectangle (mm)"
                        },
                        "height": {
                            "type": "number",
                            "description": "Height of rectangle (mm)"
                        },
                        "centerX": {
                            "type": "number",
                            "description": "Absolute X position of center (mm)"
                        },
                        "centerY": {
                            "type": "number",
                            "description": "Absolute Y position of center (mm)"
                        },
                        "relativeX": {
                            "type": "number",
                            "description": "X offset from last shape's right edge (mm)"
                        },
                        "relativeY": {
                            "type": "number",
                            "description": "Y offset from last shape's top edge (mm)"
                        },
                        "spacing": {
                            "type": "number",
                            "description": "Spacing from last shape (mm). Automatically calculates position."
                        },
                        "x1": {
                            "type": "number",
                            "description": "Alternative: First corner X (mm)"
                        },
                        "y1": {
                            "type": "number",
                            "description": "Alternative: First corner Y (mm)"
                        },
                        "x2": {
                            "type": "number",
                            "description": "Alternative: Opposite corner X (mm)"
                        },
                        "y2": {
                            "type": "number",
                            "description": "Alternative: Opposite corner Y (mm)"
                        }
                    }
                }
            ),
            Tool(
                name="solidworks_sketch_circle",
                description="Draw a circle in the active sketch. Can specify absolute position or relative to last shape.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "centerX": {
                            "type": "number",
                            "description": "Absolute center X position (mm)"
                        },
                        "centerY": {
                            "type": "number",
                            "description": "Absolute center Y position (mm)"
                        },
                        "radius": {
                            "type": "number",
                            "description": "Radius (mm)"
                        },
                        "relativeX": {
                            "type": "number",
                            "description": "X offset from last shape (mm)"
                        },
                        "relativeY": {
                            "type": "number",
                            "description": "Y offset from last shape (mm)"
                        },
                        "spacing": {
                            "type": "number",
                            "description": "Spacing from last shape (mm)"
                        }
                    },
                    "required": ["radius"]
                }
            ),
            Tool(
                name="solidworks_get_last_shape_info",
                description="Get information about the last created shape (position, size, bounding box)",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            Tool(
                name="solidworks_exit_sketch",
                description="Exit sketch edit mode",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            )
        ]
    
    def execute(self, tool_name: str, args: dict) -> str:
        """Execute a sketching tool"""
        self.connection.ensure_connection()
        
        if tool_name == "solidworks_create_sketch":
            return self.create_sketch(args)
        elif tool_name == "solidworks_sketch_rectangle":
            return self.sketch_rectangle(args)
        elif tool_name == "solidworks_sketch_circle":
            return self.sketch_circle(args)
        elif tool_name == "solidworks_get_last_shape_info":
            return self.get_last_shape_info()
        elif tool_name == "solidworks_exit_sketch":
            return self.exit_sketch()
        else:
            raise Exception(f"Unknown sketching tool: {tool_name}")
    
    def create_sketch(self, args: dict) -> str:
        """Create sketch on a reference plane or a solid face.

        If faceX/faceY/faceZ are provided, selects the solid face at that point
        (in mm, converted to metres internally) and opens a sketch on it.
        Otherwise, uses the named reference plane ("Front", "Top", or "Right").
        Face-based sketches are required for cut-extrusions to work.
        """
        plane_map = {
            "Front": "Front Plane",
            "Top": "Top Plane",
            "Right": "Right Plane"
        }

        face_mode = "faceX" in args and "faceY" in args and "faceZ" in args

        # Check for active document
        doc = self.connection.get_active_doc()

        if not doc:
            logger.info("No active document. Creating new part...")
            doc = self.connection.create_new_part()
            self.sketch_counter = 0
            self.created_shapes = []
            self.last_shape = None
            created_new = True
        else:
            logger.info("Using existing document")
            # Reset shape tracking for new sketch
            self.created_shapes = []
            self.last_shape = None
            created_new = False

        doc.ClearSelection2(True)

        if face_mode:
            # Select solid face by a point on it (coordinates in mm → metres)
            x_m = args["faceX"] / 1000.0
            y_m = args["faceY"] / 1000.0
            z_m = args["faceZ"] / 1000.0
            import win32com.client as _wc
            import pythoncom as _pc
            callout = _wc.VARIANT(_pc.VT_DISPATCH, None)
            ok = doc.Extension.SelectByID2('', 'FACE', x_m, y_m, z_m, False, 0, callout, 0)
            if not ok:
                raise Exception(
                    f"Could not select face at ({args['faceX']}, {args['faceY']}, {args['faceZ']}) mm"
                )
            doc.SketchManager.InsertSketch(True)
            location = f"face at ({args['faceX']}, {args['faceY']}, {args['faceZ']}) mm"
        else:
            plane_name = args.get("plane", "Front")
            plane_feature_name = plane_map.get(plane_name)
            if not plane_feature_name:
                raise Exception(f"Unknown plane: {plane_name}")
            plane_feature = doc.FeatureByName(plane_feature_name)
            if not plane_feature:
                raise Exception(f"Could not find {plane_feature_name}")
            plane_feature.Select2(False, 0)
            doc.SketchManager.InsertSketch(True)
            location = f"{plane_name} plane"

        # Track sketch
        self.sketch_counter += 1
        self.current_sketch_name = f"Sketch{self.sketch_counter}"

        logger.info(f"Sketch created: {self.current_sketch_name} on {location}")

        if created_new:
            return f"✓ New part created. Sketch on {location}"
        else:
            return f"✓ Sketch created on {location}"
    
    def _calculate_position(self, args: dict, shape_width: float, shape_height: float) -> tuple:
        """Calculate position based on absolute or relative coordinates"""
        
        # Priority 1: Explicit absolute position
        if "centerX" in args and "centerY" in args:
            return args["centerX"], args["centerY"]
        
        # Priority 2: Spacing from last shape (horizontal)
        if "spacing" in args and self.last_shape:
            spacing = args["spacing"]
            last_right = self.last_shape["right"]
            center_x = last_right + spacing + (shape_width / 2)
            center_y = self.last_shape["centerY"]
            return center_x, center_y
        
        # Priority 3: Relative offset from last shape
        if ("relativeX" in args or "relativeY" in args) and self.last_shape:
            offset_x = args.get("relativeX", 0)
            offset_y = args.get("relativeY", 0)
            center_x = self.last_shape["centerX"] + offset_x
            center_y = self.last_shape["centerY"] + offset_y
            return center_x, center_y
        
        # Default: Origin
        return 0, 0
    
    def sketch_rectangle(self, args: dict) -> str:
        """Draw rectangle with spatial awareness"""
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")
        
        # Determine dimensions
        if "width" in args and "height" in args:
            width = args["width"]
            height = args["height"]
        elif "x1" in args and "y1" in args and "x2" in args and "y2" in args:
            width = abs(args["x2"] - args["x1"])
            height = abs(args["y2"] - args["y1"])
        else:
            raise Exception("Must provide either (width, height) or (x1, y1, x2, y2)")
        
        # Calculate position (with spatial awareness)
        center_x, center_y = self._calculate_position(args, width, height)
        
        # Convert to meters and calculate corners
        center_x_m = center_x / 1000.0
        center_y_m = center_y / 1000.0
        width_m = width / 1000.0
        height_m = height / 1000.0
        
        x1 = center_x_m - width_m / 2
        y1 = center_y_m - height_m / 2
        x2 = center_x_m + width_m / 2
        y2 = center_y_m + height_m / 2
        
        # Draw rectangle
        doc.SketchManager.CreateCornerRectangle(x1, y1, 0.0, x2, y2, 0.0)
        
        # Track this shape
        shape_info = {
            "type": "rectangle",
            "width": width,
            "height": height,
            "centerX": center_x,
            "centerY": center_y,
            "left": center_x - width / 2,
            "right": center_x + width / 2,
            "bottom": center_y - height / 2,
            "top": center_y + height / 2
        }
        self.created_shapes.append(shape_info)
        self.last_shape = shape_info
        
        logger.info(f"Rectangle: {width}mm x {height}mm at ({center_x:.1f}, {center_y:.1f})")
        return f"✓ Rectangle {width}mm x {height}mm at position ({center_x:.1f}, {center_y:.1f})"
    
    def sketch_circle(self, args: dict) -> str:
        """Draw circle with spatial awareness"""
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")
        
        radius = args["radius"]
        
        # Calculate position (with spatial awareness)
        center_x, center_y = self._calculate_position(args, radius * 2, radius * 2)
        
        # Convert to meters
        cx_m = center_x / 1000.0
        cy_m = center_y / 1000.0
        r_m = radius / 1000.0
        
        # Draw circle
        doc.SketchManager.CreateCircleByRadius(cx_m, cy_m, 0.0, r_m)
        
        # Track this shape
        shape_info = {
            "type": "circle",
            "radius": radius,
            "centerX": center_x,
            "centerY": center_y,
            "left": center_x - radius,
            "right": center_x + radius,
            "bottom": center_y - radius,
            "top": center_y + radius
        }
        self.created_shapes.append(shape_info)
        self.last_shape = shape_info
        
        logger.info(f"Circle: radius {radius}mm at ({center_x:.1f}, {center_y:.1f})")
        return f"✓ Circle radius {radius}mm at position ({center_x:.1f}, {center_y:.1f})"
    
    def get_last_shape_info(self) -> str:
        """Get information about the last created shape"""
        if not self.last_shape:
            return "❌ No shapes have been created yet"
        
        info = self.last_shape
        result = f"Last shape: {info['type']}\n"
        result += f"  Center: ({info['centerX']:.1f}, {info['centerY']:.1f}) mm\n"
        result += f"  Bounds: X=[{info['left']:.1f}, {info['right']:.1f}], Y=[{info['bottom']:.1f}, {info['top']:.1f}]\n"
        
        if info['type'] == 'rectangle':
            result += f"  Size: {info['width']}mm x {info['height']}mm"
        elif info['type'] == 'circle':
            result += f"  Radius: {info['radius']}mm"
        
        return result
    
    def exit_sketch(self) -> str:
        """Exit sketch mode"""
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")
        
        doc.SketchManager.InsertSketch(True)
        
        logger.info("Exited sketch")
        return "✓ Exited sketch mode"
