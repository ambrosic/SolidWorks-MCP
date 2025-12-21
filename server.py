"""
SolidWorks MCP Server
Provides tools for creating and manipulating SolidWorks parts via Claude
"""

from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio
import win32com.client
import pythoncom
from typing import Any, Optional
import logging
import sys
import glob
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('solidworks_mcp.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class SolidWorksConnection:
    """Manages connection to SolidWorks application"""
    
    def __init__(self):
        self.app = None
        self.template_path = None
        
    def connect(self) -> bool:
        """Connect to SolidWorks application"""
        try:
            pythoncom.CoInitialize()
            
            # Try to connect to existing instance
            try:
                self.app = win32com.client.GetActiveObject("SldWorks.Application")
                logger.info("Connected to existing SolidWorks instance")
            except:
                # Launch new instance
                self.app = win32com.client.Dispatch("SldWorks.Application")
                self.app.Visible = True
                logger.info("Launched new SolidWorks instance")
            
            version = self.app.RevisionNumber
            logger.info(f"SolidWorks version: {version}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to SolidWorks: {e}")
            return False
    
    def find_template(self) -> Optional[str]:
        """Find Part template automatically"""
        if self.template_path:
            return self.template_path
        
        search_patterns = [
            r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS *\templates\Part.prtdot",
            r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS *\templates\Part.PRTDOT",
        ]
        
        for pattern in search_patterns:
            templates = glob.glob(pattern)
            if templates:
                self.template_path = templates[0]
                logger.info(f"Found template: {self.template_path}")
                return self.template_path
        
        logger.error("No Part template found")
        return None
    
    def create_new_part(self):
        """Always create a brand new part document"""
        template = self.find_template()
        if not template:
            raise Exception("No Part template found. Please create a Part manually in SolidWorks.")
        
        logger.info("Creating new part document")
        doc = self.app.NewDocument(template, 0, 0, 0)
        
        if not doc:
            raise Exception("Failed to create part document")
        
        logger.info("✓ New part document created")
        return doc


class SolidWorksMCPServer:
    """MCP Server for SolidWorks integration"""
    
    def __init__(self):
        self.server = Server("solidworks-mcp")
        self.sw = SolidWorksConnection()
        self.current_sketch_name = None
        self.sketch_counter = 0
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup MCP tool handlers"""
        
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="solidworks_create_sketch",
                    description="Create a new sketch on a specified plane",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "plane": {
                                "type": "string",
                                "enum": ["Front", "Top", "Right"],
                                "description": "Reference plane for sketch"
                            }
                        },
                        "required": ["plane"]
                    }
                ),
                Tool(
                    name="solidworks_sketch_rectangle",
                    description="Draw a rectangle in the active sketch",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "x1": {"type": "number", "description": "First corner X (mm)"},
                            "y1": {"type": "number", "description": "First corner Y (mm)"},
                            "x2": {"type": "number", "description": "Opposite corner X (mm)"},
                            "y2": {"type": "number", "description": "Opposite corner Y (mm)"}
                        },
                        "required": ["x1", "y1", "x2", "y2"]
                    }
                ),
                Tool(
                    name="solidworks_sketch_circle",
                    description="Draw a circle in the active sketch",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "centerX": {"type": "number", "description": "Center X (mm)"},
                            "centerY": {"type": "number", "description": "Center Y (mm)"},
                            "radius": {"type": "number", "description": "Radius (mm)"}
                        },
                        "required": ["centerX", "centerY", "radius"]
                    }
                ),
                Tool(
                    name="solidworks_create_extrusion",
                    description="Extrude the current sketch",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "depth": {"type": "number", "description": "Extrusion depth (mm)"},
                            "reverse": {"type": "boolean", "default": False, "description": "Reverse direction"}
                        },
                        "required": ["depth"]
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
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[TextContent]:
            logger.info(f"Tool called: {name} with arguments: {arguments}")
            
            # Ensure connection
            if not self.sw.app:
                if not self.sw.connect():
                    return [TextContent(
                        type="text",
                        text="❌ Failed to connect to SolidWorks. Please ensure SolidWorks is installed."
                    )]
            
            try:
                # Route to appropriate handler
                if name == "solidworks_create_sketch":
                    result = self.create_sketch(arguments)
                elif name == "solidworks_sketch_rectangle":
                    result = self.sketch_rectangle(arguments)
                elif name == "solidworks_sketch_circle":
                    result = self.sketch_circle(arguments)
                elif name == "solidworks_create_extrusion":
                    result = self.create_extrusion(arguments)
                elif name == "solidworks_exit_sketch":
                    result = self.exit_sketch()
                else:
                    result = f"❌ Unknown tool: {name}"
                
                return [TextContent(type="text", text=result)]
                
            except Exception as e:
                error_msg = f"❌ Error in {name}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                return [TextContent(type="text", text=error_msg)]
    
    def create_sketch(self, args: dict) -> str:
        """Create sketch on specified plane - ALWAYS creates a new part first"""
        plane_name = args["plane"]
        plane_map = {
            "Front": "Front Plane",
            "Top": "Top Plane",
            "Right": "Right Plane"
        }
        
        # ALWAYS create a brand new part document
        logger.info("Creating new part for this sketch...")
        doc = self.sw.create_new_part()
        
        # Reset sketch counter for new part
        self.sketch_counter = 0
        
        # Get the plane feature by name (this method works!)
        plane_feature_name = plane_map[plane_name]
        plane_feature = doc.FeatureByName(plane_feature_name)
        
        if not plane_feature:
            raise Exception(f"Could not find {plane_feature_name}")
        
        # Select and create sketch
        doc.ClearSelection2(True)
        plane_feature.Select2(False, 0)
        doc.SketchManager.InsertSketch(True)
        
        # Track sketch counter for naming
        self.sketch_counter += 1
        self.current_sketch_name = f"Sketch{self.sketch_counter}"
        
        logger.info(f"New part created. Sketch created on {plane_name}: {self.current_sketch_name}")
        
        return f"✓ New part created. Sketch created on {plane_name} plane"
    
    def sketch_rectangle(self, args: dict) -> str:
        """Draw rectangle in active sketch"""
        doc = self.sw.app.ActiveDoc
        if not doc:
            raise Exception("No active document")
        
        # Convert mm to meters
        x1 = args["x1"] / 1000.0
        y1 = args["y1"] / 1000.0
        x2 = args["x2"] / 1000.0
        y2 = args["y2"] / 1000.0
        
        doc.SketchManager.CreateCornerRectangle(x1, y1, 0.0, x2, y2, 0.0)
        
        width = abs(args["x2"] - args["x1"])
        height = abs(args["y2"] - args["y1"])
        
        logger.info(f"Rectangle created: {width}mm x {height}mm")
        return f"✓ Rectangle created: {width}mm x {height}mm"
    
    def sketch_circle(self, args: dict) -> str:
        """Draw circle in active sketch"""
        doc = self.sw.app.ActiveDoc
        if not doc:
            raise Exception("No active document")
        
        # Convert mm to meters
        cx = args["centerX"] / 1000.0
        cy = args["centerY"] / 1000.0
        r = args["radius"] / 1000.0
        
        doc.SketchManager.CreateCircleByRadius(cx, cy, 0.0, r)
        
        logger.info(f"Circle created: center ({args['centerX']}, {args['centerY']}), radius {args['radius']}mm")
        return f"✓ Circle created: radius {args['radius']}mm at ({args['centerX']}, {args['centerY']})"
    
    def create_extrusion(self, args: dict) -> str:
        """Create extrusion from current sketch"""
        doc = self.sw.app.ActiveDoc
        if not doc:
            raise Exception("No active document")
        
        # Exit sketch mode first
        doc.ClearSelection2(True)
        doc.SketchManager.InsertSketch(True)
        
        # Select the sketch we just created
        if not self.current_sketch_name:
            # Try to find the last sketch
            self.current_sketch_name = f"Sketch{self.sketch_counter}"
        
        sketch_feature = doc.FeatureByName(self.current_sketch_name)
        if not sketch_feature:
            raise Exception(f"Could not find sketch: {self.current_sketch_name}")
        
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
        return f"✓ Extrusion created: {args['depth']}mm depth"
    
    def exit_sketch(self) -> str:
        """Exit sketch mode"""
        doc = self.sw.app.ActiveDoc
        if not doc:
            raise Exception("No active document")
        
        doc.SketchManager.InsertSketch(True)
        
        logger.info("Exited sketch mode")
        return "✓ Exited sketch mode"


async def main():
    """Main entry point for MCP server"""
    logger.info("Starting SolidWorks MCP Server...")
    server = SolidWorksMCPServer()
    
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            server.server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())