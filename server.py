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

from solidworks import (
    SolidWorksConnection,
    SketchingTools,
    ModelingTools,
    FeatureTools,
    CutFeatureTools,
    AppliedFeatureTools,
    PatternTools,
    HoleFeatureTools,
    ReferenceGeometryTools,
)

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
        self.features = FeatureTools(self.connection)
        self.cut_features = CutFeatureTools(self.connection)
        self.applied_features = AppliedFeatureTools(self.connection)
        self.patterns = PatternTools(self.connection)
        self.hole_features = HoleFeatureTools(self.connection)
        self.reference_geometry = ReferenceGeometryTools(self.connection)

        # All modules (order matters for tool listing)
        self._modules = [
            self.sketching,
            self.modeling,
            self.features,
            self.cut_features,
            self.applied_features,
            self.patterns,
            self.hole_features,
            self.reference_geometry,
        ]

        # Build dispatch map: tool_name -> module
        self._route_map = {}
        for module in self._modules:
            for tool_def in module.get_tool_definitions():
                self._route_map[tool_def.name] = module

        self.setup_handlers()

    def setup_handlers(self):
        """Setup MCP tool handlers"""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            tools = []
            for module in self._modules:
                tools.extend(module.get_tool_definitions())
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
        module = self._route_map.get(name)
        if module is None:
            raise Exception(f"Unknown tool: {name}")

        # Modeling and sketching modules that need sketching_tools reference
        if module is self.modeling:
            return module.execute(name, arguments, self.sketching)
        elif module is self.sketching:
            return module.execute(name, arguments)
        else:
            return module.execute(name, arguments)


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
