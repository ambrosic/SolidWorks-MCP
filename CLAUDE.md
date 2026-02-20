# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SolidWorks MCP Server bridges Claude AI with SolidWorks CAD via the Model Context Protocol (MCP), enabling natural language creation and manipulation of 3D CAD models. Requires Windows + SolidWorks installed.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the original integration test (creates a 100mm cube in SolidWorks)
python test_solidworks.py

# Run the new sketch tools test suite
python test_solidworks.py --new

# Run the server directly (normally launched by Claude Desktop)
python server.py
```

## Claude Desktop Configuration

The server is registered in `%APPDATA%\Claude\claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "solidworks": {
      "command": "python",
      "args": ["C:\\path\\to\\solidworks-mcp\\server.py"]
    }
  }
}
```

## Architecture

```
server.py                  # MCP server: registers tools, routes calls, handles logging
solidworks/
  connection.py            # COM connection to SolidWorks, template discovery, part creation
  sketching.py             # 2D sketch tools, dimensioning, and constraints with spatial tracking
  modeling.py              # 3D feature tools (new_part, extrusion)
test_solidworks.py         # End-to-end integration test (no pytest, plain script)
```

**Data flow:** Claude → MCP tool call → `server.py` → `_route_tool()` → sketching or modeling module → SolidWorks COM API

**Workflow order:** `new_part` → `create_sketch` → sketch entities → (optional: dimensions/constraints) → `exit_sketch` → `create_extrusion`

## Key Implementation Details

**Units:** All tool inputs/outputs use millimeters. The SolidWorks COM API requires meters, so all values are divided by 1000 internally before API calls.

**Spatial tracking:** `SketchingTools` maintains a `last_shape` dict with the center, edges, width/height/radius of the most recently drawn shape. This enables Claude to position shapes relative to previous ones without needing to track coordinates itself. Entities that update spatial tracking: rectangle, circle, line, arc, polygon, ellipse, spline, slot. Entities that do NOT update tracking: point, centerline, text.

**Positioning priority** in `sketch_rectangle`/`sketch_circle`/`sketch_polygon` (highest wins):
1. Absolute `centerX`/`centerY`
2. `spacing` from last shape edge
3. Relative `relativeX`/`relativeY` offset from last center
4. Default: origin `(0, 0)`

**Sketch entity tools:** `sketch_rectangle`, `sketch_circle`, `sketch_line`, `sketch_centerline`, `sketch_arc` (3-point or center-point), `sketch_spline`, `sketch_ellipse`, `sketch_polygon`, `sketch_slot`, `sketch_point`, `sketch_text`.

**Dimensioning tools:** `sketch_dimension` and `set_dimension_value`. These use coordinate-based entity selection via `SelectByID2`. Provide points on or near sketch entities to select them, then specify where to place dimension text. The `value` parameter drives geometry.

**Constraint tools:** `sketch_constraint` applies geometric relations (COINCIDENT, CONCENTRIC, TANGENT, PARALLEL, PERPENDICULAR, HORIZONTAL, VERTICAL, EQUAL, SYMMETRIC, MIDPOINT, COLLINEAR, CORADIAL). `sketch_toggle_construction` toggles entities between normal and construction geometry.

**SolidWorks COM:** Uses `win32com.client` via `pywin32`. `connection.py` attempts to connect to an already-running SolidWorks instance first, then launches a new one. Template path is discovered by glob: `C:\ProgramData\SOLIDWORKS\SOLIDWORKS *\templates\Part.prtdot`.

**Extrusion API:** `FeatureExtrusion2` requires exactly 23 positional parameters. See `modeling.py:create_extrusion()` for the required argument order.

**Logging:** Written to `solidworks_mcp.log` in the project root and to stdout. Log level is INFO.

## Platform Constraint

This project only runs on Windows with SolidWorks installed. There is no mock/stub for the COM layer—any test or development requires a live SolidWorks instance.
