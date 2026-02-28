"""
SolidWorks Sketching Tools
Handles sketch creation and drawing operations with spatial tracking
"""

import logging
import math
import threading
import time
from mcp.types import Tool
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def dismiss_modify_dialog(delay=0.5, max_wait=10.0):
    """Find and auto-dismiss the SolidWorks 'Modify' dimension dialog.

    AddDimension2 triggers a blocking popup (Win32 class #32770, title
    "Modify").  Call this in a background thread *before* AddDimension2
    so it can dismiss the dialog as soon as it appears.
    """
    import win32gui
    import win32con

    deadline = time.monotonic() + max_wait
    time.sleep(delay)
    while time.monotonic() < deadline:
        try:
            hwnd = win32gui.FindWindow("#32770", "Modify")
            if hwnd and win32gui.IsWindowVisible(hwnd):
                win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
                win32gui.PostMessage(hwnd, win32con.WM_KEYUP, win32con.VK_RETURN, 0)
                logger.info("Auto-dismissed 'Modify' dimension dialog")
                return
        except Exception:
            pass
        time.sleep(0.1)


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
                            "description": "Reference plane name. Standard planes: 'Front', 'Top', 'Right'. Also accepts custom reference plane names like 'Plane1', 'Plane2', etc."
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
                name="solidworks_sketch_line",
                description="Draw a line segment in the active sketch between two points.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "x1": {
                            "type": "number",
                            "description": "Start point X (mm)"
                        },
                        "y1": {
                            "type": "number",
                            "description": "Start point Y (mm)"
                        },
                        "x2": {
                            "type": "number",
                            "description": "End point X (mm)"
                        },
                        "y2": {
                            "type": "number",
                            "description": "End point Y (mm)"
                        }
                    },
                    "required": ["x1", "y1", "x2", "y2"]
                }
            ),
            Tool(
                name="solidworks_sketch_centerline",
                description="Draw a construction centerline in the active sketch. Centerlines are used as axes for mirror/pattern operations and do not form part of the sketch profile.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "x1": {
                            "type": "number",
                            "description": "Start point X (mm)"
                        },
                        "y1": {
                            "type": "number",
                            "description": "Start point Y (mm)"
                        },
                        "x2": {
                            "type": "number",
                            "description": "End point X (mm)"
                        },
                        "y2": {
                            "type": "number",
                            "description": "End point Y (mm)"
                        }
                    },
                    "required": ["x1", "y1", "x2", "y2"]
                }
            ),
            Tool(
                name="solidworks_sketch_arc",
                description="Draw an arc in the active sketch. Supports 3-point mode (start, end, midpoint on arc) or center-point mode (center, start endpoint, end endpoint).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "mode": {
                            "type": "string",
                            "enum": ["3point", "center"],
                            "description": "Arc creation mode. '3point': define by start, end, and midpoint on arc. 'center': define by center point and two endpoints. Default: '3point'"
                        },
                        "x1": {
                            "type": "number",
                            "description": "Start point X (mm) - used in both modes"
                        },
                        "y1": {
                            "type": "number",
                            "description": "Start point Y (mm) - used in both modes"
                        },
                        "x2": {
                            "type": "number",
                            "description": "End point X (mm) - used in both modes"
                        },
                        "y2": {
                            "type": "number",
                            "description": "End point Y (mm) - used in both modes"
                        },
                        "x3": {
                            "type": "number",
                            "description": "Third point X (mm) - 3point mode only: midpoint on arc"
                        },
                        "y3": {
                            "type": "number",
                            "description": "Third point Y (mm) - 3point mode only: midpoint on arc"
                        },
                        "centerX": {
                            "type": "number",
                            "description": "Arc center X (mm) - center mode only"
                        },
                        "centerY": {
                            "type": "number",
                            "description": "Arc center Y (mm) - center mode only"
                        }
                    }
                }
            ),
            Tool(
                name="solidworks_sketch_spline",
                description="Draw a spline curve through a series of points in the active sketch.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "points": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "x": {"type": "number", "description": "X coordinate (mm)"},
                                    "y": {"type": "number", "description": "Y coordinate (mm)"}
                                },
                                "required": ["x", "y"]
                            },
                            "minItems": 2,
                            "description": "Array of points the spline passes through (mm)"
                        }
                    },
                    "required": ["points"]
                }
            ),
            Tool(
                name="solidworks_sketch_ellipse",
                description="Draw an ellipse in the active sketch defined by center, semi-major and semi-minor axis lengths, and optional rotation angle.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "centerX": {
                            "type": "number",
                            "description": "Center X position (mm)"
                        },
                        "centerY": {
                            "type": "number",
                            "description": "Center Y position (mm)"
                        },
                        "majorRadius": {
                            "type": "number",
                            "description": "Semi-major axis length (mm)"
                        },
                        "minorRadius": {
                            "type": "number",
                            "description": "Semi-minor axis length (mm)"
                        },
                        "angle": {
                            "type": "number",
                            "description": "Rotation angle of major axis in degrees counterclockwise from X-axis. Default: 0"
                        }
                    },
                    "required": ["centerX", "centerY", "majorRadius", "minorRadius"]
                }
            ),
            Tool(
                name="solidworks_sketch_polygon",
                description="Draw a regular polygon in the active sketch. Supports relative positioning from last shape.",
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
                            "description": "Distance from center to vertex (mm)"
                        },
                        "numSides": {
                            "type": "integer",
                            "description": "Number of sides (3-100)",
                            "minimum": 3,
                            "maximum": 100
                        },
                        "inscribed": {
                            "type": "boolean",
                            "description": "If true, radius is the inscribed circle radius. Default: false (circumscribed)"
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
                    "required": ["radius", "numSides"]
                }
            ),
            Tool(
                name="solidworks_sketch_slot",
                description="Draw a straight slot shape in the active sketch defined by two center points and a width.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "x1": {
                            "type": "number",
                            "description": "First center point X (mm)"
                        },
                        "y1": {
                            "type": "number",
                            "description": "First center point Y (mm)"
                        },
                        "x2": {
                            "type": "number",
                            "description": "Second center point X (mm)"
                        },
                        "y2": {
                            "type": "number",
                            "description": "Second center point Y (mm)"
                        },
                        "width": {
                            "type": "number",
                            "description": "Total slot width - diameter of end caps (mm)"
                        }
                    },
                    "required": ["x1", "y1", "x2", "y2", "width"]
                }
            ),
            Tool(
                name="solidworks_sketch_point",
                description="Create a sketch point in the active sketch. Useful as a construction reference for dimensions and constraints.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "x": {
                            "type": "number",
                            "description": "X position (mm)"
                        },
                        "y": {
                            "type": "number",
                            "description": "Y position (mm)"
                        }
                    },
                    "required": ["x", "y"]
                }
            ),
            Tool(
                name="solidworks_sketch_text",
                description="Insert sketch text in the active sketch.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "x": {
                            "type": "number",
                            "description": "X position (mm)"
                        },
                        "y": {
                            "type": "number",
                            "description": "Y position (mm)"
                        },
                        "text": {
                            "type": "string",
                            "description": "The text string to insert"
                        },
                        "height": {
                            "type": "number",
                            "description": "Font height (mm)"
                        },
                        "angle": {
                            "type": "number",
                            "description": "Rotation angle in degrees. Default: 0"
                        }
                    },
                    "required": ["x", "y", "text", "height"]
                }
            ),
            Tool(
                name="solidworks_sketch_dimension",
                description="Add a dimension to sketch entities. Select 1 entity for a single dimension (e.g., line length), or 2 entities for a between-dimension (e.g., distance between two lines). The dimension text is placed at (dimX, dimY). Optionally set the driving value immediately.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "entityPoints": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "x": {"type": "number", "description": "X coordinate on/near entity (mm)"},
                                    "y": {"type": "number", "description": "Y coordinate on/near entity (mm)"}
                                },
                                "required": ["x", "y"]
                            },
                            "minItems": 1,
                            "maxItems": 2,
                            "description": "Points to select entities to dimension. 1 point for a single entity (line length, arc radius), 2 points for a between-dimension (distance between two entities)."
                        },
                        "entityTypes": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["SKETCHSEGMENT", "SKETCHPOINT", "EXTSKETCHPOINT"]
                            },
                            "description": "Selection type for each entity point. Default: SKETCHSEGMENT."
                        },
                        "dimX": {
                            "type": "number",
                            "description": "X position (mm) for the dimension text placement"
                        },
                        "dimY": {
                            "type": "number",
                            "description": "Y position (mm) for the dimension text placement"
                        },
                        "value": {
                            "type": "number",
                            "description": "Optional driving value (mm) to set on the dimension. If provided, the dimension becomes a driving dimension that constrains the geometry to this value."
                        }
                    },
                    "required": ["entityPoints", "dimX", "dimY"]
                }
            ),
            Tool(
                name="solidworks_set_dimension_value",
                description="Set the value of an existing dimension by selecting it at its text location. Changes the driving value of the dimension, which updates the sketch geometry accordingly.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "dimX": {
                            "type": "number",
                            "description": "X coordinate (mm) on/near the dimension text to select"
                        },
                        "dimY": {
                            "type": "number",
                            "description": "Y coordinate (mm) on/near the dimension text to select"
                        },
                        "value": {
                            "type": "number",
                            "description": "New dimension value (mm)"
                        }
                    },
                    "required": ["dimX", "dimY", "value"]
                }
            ),
            Tool(
                name="solidworks_sketch_constraint",
                description="Add a geometric constraint (relation) between selected sketch entities.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "constraintType": {
                            "type": "string",
                            "enum": ["COINCIDENT", "CONCENTRIC", "TANGENT", "PARALLEL",
                                     "PERPENDICULAR", "HORIZONTAL", "VERTICAL", "EQUAL",
                                     "SYMMETRIC", "MIDPOINT", "COLLINEAR", "CORADIAL"],
                            "description": "Type of geometric constraint to apply"
                        },
                        "entityPoints": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "x": {"type": "number", "description": "X coordinate on/near entity (mm)"},
                                    "y": {"type": "number", "description": "Y coordinate on/near entity (mm)"}
                                },
                                "required": ["x", "y"]
                            },
                            "minItems": 1,
                            "maxItems": 3,
                            "description": "Points to select entities. 1 for single-entity constraints (Horizontal, Vertical), 2 for pair constraints (Parallel, Equal), 3 for Symmetric (entity, entity, centerline)."
                        },
                        "entityTypes": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["SKETCHSEGMENT", "SKETCHPOINT", "EXTSKETCHPOINT"]
                            },
                            "description": "Selection type for each entity point. Default: SKETCHSEGMENT."
                        }
                    },
                    "required": ["constraintType", "entityPoints"]
                }
            ),
            Tool(
                name="solidworks_sketch_toggle_construction",
                description="Toggle the construction geometry flag on a selected sketch entity. Construction geometry is for reference only and does not form part of the extrusion profile.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "x": {
                            "type": "number",
                            "description": "X coordinate on/near entity to toggle (mm)"
                        },
                        "y": {
                            "type": "number",
                            "description": "Y coordinate on/near entity to toggle (mm)"
                        }
                    },
                    "required": ["x", "y"]
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

        dispatch = {
            "solidworks_create_sketch": lambda: self.create_sketch(args),
            "solidworks_sketch_rectangle": lambda: self.sketch_rectangle(args),
            "solidworks_sketch_circle": lambda: self.sketch_circle(args),
            "solidworks_sketch_line": lambda: self.sketch_line(args),
            "solidworks_sketch_centerline": lambda: self.sketch_centerline(args),
            "solidworks_sketch_arc": lambda: self.sketch_arc(args),
            "solidworks_sketch_spline": lambda: self.sketch_spline(args),
            "solidworks_sketch_ellipse": lambda: self.sketch_ellipse(args),
            "solidworks_sketch_polygon": lambda: self.sketch_polygon(args),
            "solidworks_sketch_slot": lambda: self.sketch_slot(args),
            "solidworks_sketch_point": lambda: self.sketch_point(args),
            "solidworks_sketch_text": lambda: self.sketch_text(args),
            "solidworks_sketch_dimension": lambda: self.sketch_dimension(args),
            "solidworks_set_dimension_value": lambda: self.set_dimension_value(args),
            "solidworks_sketch_constraint": lambda: self.sketch_constraint(args),
            "solidworks_sketch_toggle_construction": lambda: self.toggle_construction(args),
            "solidworks_get_last_shape_info": lambda: self.get_last_shape_info(),
            "solidworks_exit_sketch": lambda: self.exit_sketch(),
        }

        handler = dispatch.get(tool_name)
        if not handler:
            raise Exception(f"Unknown sketching tool: {tool_name}")
        return handler()
    
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
            plane_feature_name = plane_map.get(plane_name, plane_name)
            plane_feature = doc.FeatureByName(plane_feature_name)
            if not plane_feature:
                raise Exception(
                    f"Could not find plane: {plane_name}. "
                    f"Use 'Front', 'Top', 'Right', or a custom reference plane name like 'Plane1'."
                )
            plane_feature.Select2(False, 0)
            doc.SketchManager.InsertSketch(True)
            location = f"{plane_name} plane"

        # Track sketch
        self.sketch_counter += 1
        self.current_sketch_name = f"Sketch{self.sketch_counter}"

        logger.info(f"Sketch created: {self.current_sketch_name} on {location}")

        if created_new:
            return f"✓ New part created. Sketch '{self.current_sketch_name}' on {location}"
        else:
            return f"✓ Sketch '{self.current_sketch_name}' created on {location}"
    
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

    def sketch_line(self, args: dict) -> str:
        """Draw a line segment in the active sketch"""
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")

        for key in ["x1", "y1", "x2", "y2"]:
            if key not in args:
                raise Exception(f"sketch_line requires {key}")

        x1, y1 = args["x1"], args["y1"]
        x2, y2 = args["x2"], args["y2"]

        doc.SketchManager.CreateLine(
            x1 / 1000.0, y1 / 1000.0, 0.0,
            x2 / 1000.0, y2 / 1000.0, 0.0
        )

        shape_info = {
            "type": "line",
            "centerX": (x1 + x2) / 2,
            "centerY": (y1 + y2) / 2,
            "left": min(x1, x2),
            "right": max(x1, x2),
            "bottom": min(y1, y2),
            "top": max(y1, y2),
            "width": abs(x2 - x1),
            "height": abs(y2 - y1),
            "x1": x1, "y1": y1, "x2": x2, "y2": y2
        }
        self.created_shapes.append(shape_info)
        self.last_shape = shape_info

        logger.info(f"Line: ({x1}, {y1}) to ({x2}, {y2}) mm")
        return f"✓ Line from ({x1:.1f}, {y1:.1f}) to ({x2:.1f}, {y2:.1f}) mm"

    def sketch_centerline(self, args: dict) -> str:
        """Draw a construction centerline in the active sketch"""
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")

        for key in ["x1", "y1", "x2", "y2"]:
            if key not in args:
                raise Exception(f"sketch_centerline requires {key}")

        x1, y1 = args["x1"], args["y1"]
        x2, y2 = args["x2"], args["y2"]

        doc.SketchManager.CreateCenterLine(
            x1 / 1000.0, y1 / 1000.0, 0.0,
            x2 / 1000.0, y2 / 1000.0, 0.0
        )

        # Centerlines are construction geometry - don't update last_shape
        logger.info(f"Centerline: ({x1}, {y1}) to ({x2}, {y2}) mm")
        return f"✓ Centerline from ({x1:.1f}, {y1:.1f}) to ({x2:.1f}, {y2:.1f}) mm"

    def sketch_point(self, args: dict) -> str:
        """Create a sketch point"""
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")

        for key in ["x", "y"]:
            if key not in args:
                raise Exception(f"sketch_point requires {key}")

        x, y = args["x"], args["y"]

        doc.SketchManager.CreatePoint(x / 1000.0, y / 1000.0, 0.0)

        # Points are zero-dimensional - don't update last_shape
        logger.info(f"Point: ({x}, {y}) mm")
        return f"✓ Point at ({x:.1f}, {y:.1f}) mm"

    def sketch_arc(self, args: dict) -> str:
        """Draw an arc in the active sketch (3-point or center-point mode)"""
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")

        mode = args.get("mode", "3point")

        if mode == "3point":
            for key in ["x1", "y1", "x2", "y2", "x3", "y3"]:
                if key not in args:
                    raise Exception(f"3-point arc requires {key}")

            x1, y1 = args["x1"], args["y1"]
            x2, y2 = args["x2"], args["y2"]
            x3, y3 = args["x3"], args["y3"]

            doc.SketchManager.Create3PointArc(
                x1 / 1000.0, y1 / 1000.0, 0.0,
                x2 / 1000.0, y2 / 1000.0, 0.0,
                x3 / 1000.0, y3 / 1000.0, 0.0
            )

            all_x = [x1, x2, x3]
            all_y = [y1, y2, y3]
            shape_info = {
                "type": "arc",
                "centerX": (min(all_x) + max(all_x)) / 2,
                "centerY": (min(all_y) + max(all_y)) / 2,
                "left": min(all_x),
                "right": max(all_x),
                "bottom": min(all_y),
                "top": max(all_y),
            }
            self.created_shapes.append(shape_info)
            self.last_shape = shape_info

            logger.info(f"3-point arc: ({x1},{y1}), ({x2},{y2}), ({x3},{y3}) mm")
            return f"✓ 3-point arc through ({x1:.1f},{y1:.1f}), ({x2:.1f},{y2:.1f}), ({x3:.1f},{y3:.1f}) mm"

        elif mode == "center":
            for key in ["centerX", "centerY", "x1", "y1", "x2", "y2"]:
                if key not in args:
                    raise Exception(f"Center-point arc requires {key}")

            cx, cy = args["centerX"], args["centerY"]
            x1, y1 = args["x1"], args["y1"]
            x2, y2 = args["x2"], args["y2"]

            doc.SketchManager.CreateArc(
                cx / 1000.0, cy / 1000.0, 0.0,
                x1 / 1000.0, y1 / 1000.0, 0.0,
                x2 / 1000.0, y2 / 1000.0, 0.0,
                1  # direction: 1 = counter-clockwise
            )

            radius = math.sqrt((x1 - cx) ** 2 + (y1 - cy) ** 2)
            shape_info = {
                "type": "arc",
                "centerX": cx,
                "centerY": cy,
                "radius": radius,
                "left": cx - radius,
                "right": cx + radius,
                "bottom": cy - radius,
                "top": cy + radius,
            }
            self.created_shapes.append(shape_info)
            self.last_shape = shape_info

            logger.info(f"Center-point arc: center ({cx},{cy}), radius {radius:.1f} mm")
            return f"✓ Center-point arc at ({cx:.1f},{cy:.1f}), radius {radius:.1f}mm"

        else:
            raise Exception(f"Unknown arc mode: {mode}. Use '3point' or 'center'")

    def sketch_polygon(self, args: dict) -> str:
        """Draw a regular polygon in the active sketch"""
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")

        if "radius" not in args:
            raise Exception("sketch_polygon requires radius")
        if "numSides" not in args:
            raise Exception("sketch_polygon requires numSides")

        radius = args["radius"]
        num_sides = args["numSides"]
        inscribed = args.get("inscribed", False)

        # Use _calculate_position for relative positioning support
        center_x, center_y = self._calculate_position(args, radius * 2, radius * 2)

        cx_m = center_x / 1000.0
        cy_m = center_y / 1000.0
        r_m = radius / 1000.0

        # Edge point: vertex on the circumscribed circle, directly to the right
        edge_x = cx_m + r_m
        edge_y = cy_m

        doc.SketchManager.CreatePolygon(
            cx_m, cy_m, 0.0,
            edge_x, edge_y, 0.0,
            num_sides,
            inscribed
        )

        shape_info = {
            "type": "polygon",
            "centerX": center_x,
            "centerY": center_y,
            "radius": radius,
            "numSides": num_sides,
            "left": center_x - radius,
            "right": center_x + radius,
            "bottom": center_y - radius,
            "top": center_y + radius,
        }
        self.created_shapes.append(shape_info)
        self.last_shape = shape_info

        logger.info(f"Polygon: {num_sides} sides, radius {radius}mm at ({center_x:.1f}, {center_y:.1f})")
        return f"✓ {num_sides}-sided polygon, radius {radius}mm at ({center_x:.1f}, {center_y:.1f})"

    def sketch_ellipse(self, args: dict) -> str:
        """Draw an ellipse in the active sketch"""
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")

        for key in ["centerX", "centerY", "majorRadius", "minorRadius"]:
            if key not in args:
                raise Exception(f"sketch_ellipse requires {key}")

        cx = args["centerX"]
        cy = args["centerY"]
        major_r = args["majorRadius"]
        minor_r = args["minorRadius"]
        angle_deg = args.get("angle", 0)
        angle_rad = math.radians(angle_deg)

        cx_m = cx / 1000.0
        cy_m = cy / 1000.0
        major_r_m = major_r / 1000.0
        minor_r_m = minor_r / 1000.0

        # Major axis endpoint rotated by angle
        major_x = cx_m + major_r_m * math.cos(angle_rad)
        major_y = cy_m + major_r_m * math.sin(angle_rad)

        # Minor axis endpoint perpendicular to major axis
        minor_x = cx_m + minor_r_m * math.cos(angle_rad + math.pi / 2)
        minor_y = cy_m + minor_r_m * math.sin(angle_rad + math.pi / 2)

        doc.SketchManager.CreateEllipse(
            cx_m, cy_m, 0.0,
            major_x, major_y, 0.0,
            minor_x, minor_y, 0.0
        )

        extent = max(major_r, minor_r)
        shape_info = {
            "type": "ellipse",
            "centerX": cx,
            "centerY": cy,
            "majorRadius": major_r,
            "minorRadius": minor_r,
            "left": cx - extent,
            "right": cx + extent,
            "bottom": cy - extent,
            "top": cy + extent,
        }
        self.created_shapes.append(shape_info)
        self.last_shape = shape_info

        logger.info(f"Ellipse: {major_r}x{minor_r}mm at ({cx:.1f}, {cy:.1f}), angle {angle_deg}")
        return f"✓ Ellipse {major_r}mm x {minor_r}mm at ({cx:.1f}, {cy:.1f})"

    def sketch_spline(self, args: dict) -> str:
        """Draw a spline through a series of points"""
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")

        if "points" not in args:
            raise Exception("sketch_spline requires points array")

        points = args["points"]
        if len(points) < 2:
            raise Exception("Spline requires at least 2 points")

        import win32com.client
        import pythoncom

        # Build flat coordinate array: [x1,y1,z1, x2,y2,z2, ...]
        point_data = []
        for p in points:
            point_data.extend([p["x"] / 1000.0, p["y"] / 1000.0, 0.0])

        point_array = win32com.client.VARIANT(
            pythoncom.VT_ARRAY | pythoncom.VT_R8, point_data
        )
        doc.SketchManager.CreateSpline2(point_array, True)

        xs = [p["x"] for p in points]
        ys = [p["y"] for p in points]
        shape_info = {
            "type": "spline",
            "centerX": (min(xs) + max(xs)) / 2,
            "centerY": (min(ys) + max(ys)) / 2,
            "left": min(xs),
            "right": max(xs),
            "bottom": min(ys),
            "top": max(ys),
            "width": max(xs) - min(xs),
            "height": max(ys) - min(ys),
        }
        self.created_shapes.append(shape_info)
        self.last_shape = shape_info

        logger.info(f"Spline: {len(points)} points")
        return f"✓ Spline through {len(points)} points"

    def sketch_slot(self, args: dict) -> str:
        """Draw a slot shape in the active sketch"""
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")

        for key in ["x1", "y1", "x2", "y2", "width"]:
            if key not in args:
                raise Exception(f"sketch_slot requires {key}")

        x1, y1 = args["x1"], args["y1"]
        x2, y2 = args["x2"], args["y2"]
        width = args["width"]

        doc.SketchManager.CreateSketchSlot(
            0,                                   # slotType: straight (center line)
            0,                                   # lengthType: center-to-center
            width / 1000.0,                      # slot width in meters
            x1 / 1000.0, y1 / 1000.0, 0.0,     # first center point
            x2 / 1000.0, y2 / 1000.0, 0.0,     # second center point
            0.0, 0.0, 0.0,                       # third point (unused for straight)
            1,                                    # centerArcDirection
            False                                 # addDimension
        )

        half_w = width / 2
        shape_info = {
            "type": "slot",
            "centerX": (x1 + x2) / 2,
            "centerY": (y1 + y2) / 2,
            "left": min(x1, x2) - half_w,
            "right": max(x1, x2) + half_w,
            "bottom": min(y1, y2) - half_w,
            "top": max(y1, y2) + half_w,
            "width": max(x1, x2) - min(x1, x2) + width,
            "height": max(y1, y2) - min(y1, y2) + width,
        }
        self.created_shapes.append(shape_info)
        self.last_shape = shape_info

        logger.info(f"Slot: ({x1},{y1}) to ({x2},{y2}), width {width}mm")
        return f"✓ Slot from ({x1:.1f},{y1:.1f}) to ({x2:.1f},{y2:.1f}), width {width}mm"

    def sketch_text(self, args: dict) -> str:
        """Insert sketch text in the active sketch"""
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")

        for key in ["x", "y", "text", "height"]:
            if key not in args:
                raise Exception(f"sketch_text requires {key}")

        x, y = args["x"], args["y"]
        text = args["text"]
        height = args["height"]
        angle_rad = math.radians(args.get("angle", 0))

        # InsertSketchText signature (9 params):
        #   Ptx, Pty, Ptz, Text, Alignment, FlipDirection,
        #   HorizontalMirror, WidthFactor, SpaceBetweenChars
        # Height and angle are set separately via ITextFormat
        sketch_text_obj = doc.InsertSketchText(
            x / 1000.0, y / 1000.0, 0.0,
            text,
            1,     # Alignment: left
            0,     # FlipDirection
            0,     # HorizontalMirror
            1,     # WidthFactor
            0      # SpaceBetweenChars
        )

        if sketch_text_obj:
            try:
                tf = sketch_text_obj.GetTextFormat()
                if tf:
                    tf.CharHeight = height / 1000.0
                    if angle_rad != 0:
                        tf.Escapement = angle_rad
                    sketch_text_obj.SetTextFormat(False, tf)
            except Exception:
                # GetTextFormat not available in dynamic COM dispatch
                logger.warning("Could not set text format (ITextFormat not available via dynamic COM)")

        # Text doesn't update last_shape
        logger.info(f"Text: '{text}' at ({x}, {y}) mm, height {height}mm")
        return f"✓ Text '{text}' at ({x:.1f}, {y:.1f}) mm, height {height}mm"

    def sketch_dimension(self, args: dict) -> str:
        """Add a smart dimension to selected sketch entities"""
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")

        if "entityPoints" not in args:
            raise Exception("sketch_dimension requires entityPoints")
        for key in ["dimX", "dimY"]:
            if key not in args:
                raise Exception(f"sketch_dimension requires {key}")

        import win32com.client
        import pythoncom

        entity_points = args["entityPoints"]
        entity_types = args.get("entityTypes", ["SKETCHSEGMENT"] * len(entity_points))

        doc.ClearSelection2(True)
        callout = win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)

        for i, pt in enumerate(entity_points):
            append = i > 0
            success = doc.Extension.SelectByID2(
                "", entity_types[i],
                pt["x"] / 1000.0, pt["y"] / 1000.0, 0.0,
                append, 0, callout, 0
            )
            if not success:
                raise Exception(f"Failed to select entity at ({pt['x']}, {pt['y']}) mm")

        # AddDimension2 triggers a blocking "Modify" dialog in SolidWorks.
        # A background thread auto-dismisses it (see dismiss_modify_dialog).
        dismiss_thread = threading.Thread(target=dismiss_modify_dialog, daemon=True)
        dismiss_thread.start()

        sm = doc.SketchManager
        sm.AddToDB = True
        sm.DisplayWhenAdded = False

        try:
            dim_display = doc.AddDimension2(
                args["dimX"] / 1000.0,
                args["dimY"] / 1000.0,
                0.0
            )

            if not dim_display:
                raise Exception("Failed to add dimension. Ensure valid entities are selected.")

            result_msg = f"Dimension added at ({args['dimX']:.1f}, {args['dimY']:.1f}) mm"

            # Optionally set the dimension value to drive geometry
            if "value" in args:
                value_m = args["value"] / 1000.0
                dim = dim_display.GetDimension2(0)
                if dim:
                    dim.SetSystemValue3(value_m, 2, "")
                    result_msg += f", value set to {args['value']}mm"

            doc.ClearSelection2(True)
        finally:
            sm.AddToDB = False
            sm.DisplayWhenAdded = True
            dismiss_thread.join(timeout=2)

        if "value" in args:
            doc.ForceRebuild3(True)

        logger.info(result_msg)
        return f"✓ {result_msg}"

    def set_dimension_value(self, args: dict) -> str:
        """Set the value of an existing dimension by selecting it"""
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")

        for key in ["dimX", "dimY", "value"]:
            if key not in args:
                raise Exception(f"set_dimension_value requires {key}")

        import win32com.client
        import pythoncom

        doc.ClearSelection2(True)
        callout = win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)

        success = doc.Extension.SelectByID2(
            "", "DIMENSION",
            args["dimX"] / 1000.0, args["dimY"] / 1000.0, 0.0,
            False, 0, callout, 0
        )
        if not success:
            raise Exception(f"No dimension found at ({args['dimX']}, {args['dimY']}) mm")

        sel_mgr = doc.SelectionManager
        dim_display = sel_mgr.GetSelectedObject6(1, -1)
        dim = dim_display.GetDimension2(0)

        value_m = args["value"] / 1000.0
        dim.SetSystemValue3(value_m, 2, "")
        doc.ClearSelection2(True)
        doc.ForceRebuild3(True)

        logger.info(f"Dimension value set to {args['value']}mm at ({args['dimX']}, {args['dimY']})")
        return f"✓ Dimension value set to {args['value']}mm"

    # Constraint type mapping: user-friendly name -> SolidWorks API string
    CONSTRAINT_MAP = {
        "COINCIDENT": "sgCOINCIDENT",
        "CONCENTRIC": "sgCONCENTRIC",
        "TANGENT": "sgTANGENT",
        "PARALLEL": "sgPARALLEL",
        "PERPENDICULAR": "sgPERPENDICULAR",
        "HORIZONTAL": "sgHORIZONTAL2D",
        "VERTICAL": "sgVERTICAL2D",
        "EQUAL": "sgEQUAL",
        "SYMMETRIC": "sgSYMMETRIC",
        "MIDPOINT": "sgMIDPOINT",
        "COLLINEAR": "sgCOLLINEAR",
        "CORADIAL": "sgCORADIAL",
    }

    def sketch_constraint(self, args: dict) -> str:
        """Add a geometric constraint between selected sketch entities"""
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")

        if "constraintType" not in args:
            raise Exception("sketch_constraint requires constraintType")
        if "entityPoints" not in args:
            raise Exception("sketch_constraint requires entityPoints")

        constraint_type = args["constraintType"]
        if constraint_type not in self.CONSTRAINT_MAP:
            raise Exception(
                f"Unknown constraint type: {constraint_type}. "
                f"Valid: {list(self.CONSTRAINT_MAP.keys())}"
            )

        import win32com.client
        import pythoncom

        entity_points = args["entityPoints"]
        entity_types = args.get("entityTypes", ["SKETCHSEGMENT"] * len(entity_points))

        doc.ClearSelection2(True)
        callout = win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)

        for i, pt in enumerate(entity_points):
            append = i > 0
            success = doc.Extension.SelectByID2(
                "", entity_types[i],
                pt["x"] / 1000.0, pt["y"] / 1000.0, 0.0,
                append, 0, callout, 0
            )
            if not success:
                raise Exception(f"Failed to select entity at ({pt['x']}, {pt['y']}) mm")

        doc.SketchAddConstraints(self.CONSTRAINT_MAP[constraint_type])

        logger.info(f"Constraint '{constraint_type}' applied")
        return f"✓ Constraint '{constraint_type}' applied"

    def toggle_construction(self, args: dict) -> str:
        """Toggle construction geometry flag on a sketch entity"""
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")

        for key in ["x", "y"]:
            if key not in args:
                raise Exception(f"toggle_construction requires {key}")

        import win32com.client
        import pythoncom

        doc.ClearSelection2(True)
        callout = win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)

        success = doc.Extension.SelectByID2(
            "", "SKETCHSEGMENT",
            args["x"] / 1000.0, args["y"] / 1000.0, 0.0,
            False, 0, callout, 0
        )
        if not success:
            raise Exception(f"No sketch segment found at ({args['x']}, {args['y']}) mm")

        sel_mgr = doc.SelectionManager
        sketch_seg = sel_mgr.GetSelectedObject6(1, -1)

        current = sketch_seg.ConstructionGeometry
        sketch_seg.ConstructionGeometry = not current

        new_state = "construction" if not current else "normal"
        logger.info(f"Entity at ({args['x']}, {args['y']}) mm toggled to {new_state}")
        return f"✓ Entity at ({args['x']:.1f}, {args['y']:.1f}) mm is now {new_state} geometry"

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
        elif info['type'] == 'line':
            result += f"  From: ({info['x1']:.1f}, {info['y1']:.1f}) To: ({info['x2']:.1f}, {info['y2']:.1f})"
        elif info['type'] == 'arc':
            if 'radius' in info:
                result += f"  Radius: {info['radius']:.1f}mm"
        elif info['type'] == 'ellipse':
            result += f"  Major: {info['majorRadius']}mm, Minor: {info['minorRadius']}mm"
        elif info['type'] == 'polygon':
            result += f"  Sides: {info['numSides']}, Radius: {info['radius']}mm"
        elif info['type'] == 'slot':
            result += f"  Size: {info.get('width', 0):.1f}mm x {info.get('height', 0):.1f}mm"
        elif info['type'] == 'spline':
            result += f"  Span: {info.get('width', 0):.1f}mm x {info.get('height', 0):.1f}mm"

        return result
    
    def exit_sketch(self) -> str:
        """Exit sketch mode"""
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")

        doc.SketchManager.InsertSketch(True)

        # Find the actual sketch name from the feature tree
        actual_name = None
        try:
            features = doc.FeatureManager.GetFeatures(True)
            if features:
                for feature in reversed(features):
                    if feature.GetTypeName2 == "ProfileFeature":
                        actual_name = feature.Name
                        break
        except Exception as e:
            logger.warning(f"Could not verify sketch name: {e}")

        if actual_name:
            self.current_sketch_name = actual_name
            logger.info(f"Exited sketch: {actual_name}")
            return f"✓ Exited sketch mode ({actual_name})"
        else:
            logger.warning("Exited sketch but could not find it in feature tree")
            return "✓ Exited sketch mode"
