"""
SolidWorks MCP Server - Modular Edition
Organized with separate modules for better maintainability
"""

from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio
from typing import Any
import logging
import sys
import asyncio
from pathlib import Path
import pythoncom

from solidworks import SolidWorksConnection, SketchingTools, ModelingTools

# Configure logging
_log_path = Path(__file__).parent / 'solidworks_mcp.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(_log_path),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)


class SolidWorksMCPServer:
    """MCP Server for SolidWorks with modular architecture"""
    
    def __init__(self):
        self.server = Server("solidworks-mcp")
        
        # Initialize connection and tool modules
        self.connection = SolidWorksConnection()
        self.sketching = SketchingTools(self.connection)
        self.modeling = ModelingTools(self.connection)
        
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup MCP tool handlers"""
        
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            tools = []
            
            # Add all tool definitions from modules
            tools.extend(self.sketching.get_tool_definitions())
            tools.extend(self.modeling.get_tool_definitions())
            
            return tools
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[TextContent]:
            logger.info(f"Tool called: {name} with arguments: {arguments}")
            
            # Ensure connection
            if not self.connection.app:
                if not self.connection.connect():
                    return [TextContent(
                        type="text",
                        text="❌ Failed to connect to SolidWorks"
                    )]
            
            try:
                # Route to appropriate module
                result = self._route_tool(name, arguments)
                return [TextContent(type="text", text=result)]
                
            except Exception as e:
                error_msg = f"❌ Error in {name}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                return [TextContent(type="text", text=error_msg)]
    
    def _route_tool(self, name: str, arguments: Any) -> str:
        """Route tool calls to appropriate module"""
        
        # Sketching tools
        if name in ["solidworks_create_sketch", "solidworks_sketch_rectangle",
                   "solidworks_sketch_circle", "solidworks_exit_sketch",
                   "solidworks_get_last_shape_info"]:
            return self.sketching.execute(name, arguments)
        
        # Modeling tools
        elif name in ["solidworks_new_part", "solidworks_create_extrusion"]:
            return self.modeling.execute(name, arguments, self.sketching)
        
        else:
            raise Exception(f"Unknown tool: {name}")


async def main():
    """Main entry point"""
    logger.info("Starting SolidWorks MCP Server (Modular Edition)...")
    server = SolidWorksMCPServer()
    
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            server.server.create_initialization_options()
        )


if __name__ == "__main__":
    pythoncom.CoInitialize()
    asyncio.run(main())