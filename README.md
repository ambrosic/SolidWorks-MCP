# SolidWorks MCP Server

A Model Context Protocol (MCP) server that enables Claude to create and manipulate SolidWorks CAD models through natural language commands.

## Overview

This MCP server bridges Claude AI with SolidWorks, allowing you to create 3D CAD models by simply describing what you want. Claude can create sketches, draw shapes, and extrude features directly in SolidWorks.

## Features

- **Automated Part Creation** - Creates a new part document for each design request
- **Sketch Creation** - Create sketches on Front, Top, or Right planes
-  **Drawing Tools** - Draw rectangles and circles with precise dimensions
-  **Extrusion** - Extrude sketches into 3D features with custom depth
- **Natural Language Interface** - Describe what you want, and Claude builds it

## Requirements

- **Windows OS** (SolidWorks only runs on Windows)
- **SolidWorks 2022 or later** (tested on SolidWorks 2025)
- **Python 3.8+**
- **Claude Desktop App**

## Installation

### 1. Clone the Repository
If I were you, I would put this somewhere that isn't a network drive...
```bash
git clone https://github.com/ambrosic/solidworks-mcp.git
cd solidworks-mcp
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```


### 3. Configure Claude Desktop

Add the server to your Claude Desktop configuration file:



**Location:** `%APPDATA%\Claude\claude_desktop_config.json`
```json
{
  "mcpServers": {
    "solidworks": {
      "command": "python",
      "args": [
        "C:\\path\\to\\solidworks-mcp\\server.py"
      ]
    }
  }
}
```

Replace `C:\\path\\to\\solidworks-mcp\\server.py` with the actual path to your `server.py` file.

### 4. Restart Claude Desktop

Close and reopen Claude Desktop to load the MCP server.

## Usage

### Basic Examples

**Create a simple cube:**
```
Create a 100mm cube in SolidWorks
```

**Create a cylinder:**
```
Create a cylinder in SolidWorks with a 50mm radius and 200mm height
```

**Create a rectangular prism:**
```
Make a box in SolidWorks that's 150mm long, 75mm wide, and 50mm tall
```

### How It Works

1. **Claude creates a sketch** on the specified plane (Front, Top, or Right)
2. **Claude draws shapes** (rectangles, circles) with your dimensions
3. **Claude extrudes** the sketch to create a 3D feature
4. **A new part is created** for each request automatically

## Available Tools

The MCP server provides these tools to Claude:

| Tool | Description |
|------|-------------|
| **Modeling** | |
| `new_part` | Create a new part document |
| `create_extrusion` | Extrude a sketch into a 3D feature with optional end condition (BLIND or THROUGH_ALL) |
| `create_cut_extrusion` | Cut material by extruding a sketch |
| `get_mass_properties` | Retrieve mass, volume, and center of mass |
| `list_features` | List all features in the active body |
| **Sketch Tools** | |
| `create_sketch` | Create a new sketch on Front, Top, Right, or custom reference plane |
| `exit_sketch` | Exit sketch editing mode and return sketch name |
| `sketch_rectangle` | Draw a rectangle with optional positioning (absolute, relative, or spacing-based) |
| `sketch_circle` | Draw a circle with center and radius |
| `sketch_line` | Draw a line between two points |
| `sketch_centerline` | Draw a centerline (for revolve operations) |
| `sketch_arc` | Draw an arc (3-point or center-point mode) |
| `sketch_spline` | Draw a spline through multiple points |
| `sketch_ellipse` | Draw an ellipse with center and axes |
| `sketch_polygon` | Draw a regular polygon with center, radius, and side count |
| `sketch_slot` | Draw a rounded slot (rectangle with semicircular ends) |
| `sketch_point` | Add a point at specified coordinates |
| `sketch_text` | Add text to the sketch |
| `sketch_constraint` | Apply constraints (horizontal, vertical, coincident, equal, perpendicular, parallel, tangent, etc.) |
| `sketch_toggle_construction` | Toggle construction mode on sketch entities |
| `get_last_shape_info` | Retrieve center, edges, and dimensions of the last drawn shape |
| **Boss/Base Features** | |
| `revolve` | Create a revolve feature (requires centerline in sketch) |
| `sweep` | Create a sweep feature (profile + path sketches) |
| `loft` | Create a loft feature (2+ profile sketches) |
| `boundary_boss` | Create a boundary boss feature (profiles + optional guide curves) |
| **Cut Features** | |
| `cut_revolve` | Cut using a revolve operation |
| `cut_sweep` | Cut using a sweep operation |
| `cut_loft` | Cut using a loft operation |
| `boundary_cut` | Cut using boundary surfaces |
| **Applied Features** | |
| `fillet` | Round edges with specified radius |
| `chamfer` | Bevel edges with specified distance |
| `shell` | Create a hollow shell by removing faces and adding thickness |
| `draft` | Apply draft to faces relative to a neutral plane |
| `rib` | Create a rib from a sketch profile |
| `wrap` | Emboss, deboss, or scribe geometry onto a face |
| `intersect` | Create intersection of overlapping bodies |
| **Patterns** | |
| `linear_pattern` | Pattern features in linear directions (1D or 2D) |
| `circular_pattern` | Pattern features around an axis |
| `mirror` | Mirror features across a plane |
| **Hole Features** | |
| `hole_wizard` | Create holes with Hole Wizard (may trigger dialog) |
| `thread` | Add cosmetic thread to a circular edge |
| **Reference Geometry** | |
| `ref_plane` | Create an offset, angled, or through-point reference plane |
| `ref_axis` | Create a reference axis from two points, cylindrical face, or edge |
| `ref_point` | Create a reference point at coordinates, arc center, face center, or on edge |
| `coordinate_system` | Create a coordinate system with origin and optional axis edges |
| **Geometry Query** | |
| `get_body_info` | Get bounding box and feature counts |
| `get_faces` | Enumerate faces with type, area, normal, and sample points (optional filter by surface type) |
| `get_edges` | Enumerate edges with endpoints, midpoint, and length (optional filter by edge type) |
| `get_face_edges` | Get all edges of a specific face by coordinate |
| `get_vertices` | Get all unique vertex coordinates in the body |

**All dimensions are in millimeters (mm).** Angles are in degrees. Selection coordinates are converted to meters internally for the SolidWorks COM API.

## Testing

Run the included test script to verify your setup:
```bash
python test_solidworks.py
```

This will:
1. Connect to SolidWorks
2. Create a new part
3. Draw a 100mm x 100mm rectangle
4. Extrude it 100mm to create a cube

If successful, you'll see a cube in SolidWorks!

## Troubleshooting

### SolidWorks doesn't launch
- Ensure SolidWorks is installed and activated
- Try launching SolidWorks manually first
- This generally works if Solidworks is launched before Claude is.

### "Failed to connect to SolidWorks"
- Check that SolidWorks is running
- Run Claude Desktop as Administrator
- Verify `pywin32` is installed: `pip install pywin32`

### "No Part template found"
- Check that SolidWorks templates exist at: `C:\ProgramData\SOLIDWORKS\SOLIDWORKS <YOUR YEAR>\templates\`
- Update the template path in `server.py` if your templates are elsewhere

### Tool errors in Claude
- Check the log file: `solidworks_mcp.log`
- Restart Claude Desktop
- Verify the config file path is correct


## Technical Details

### Units
- Input dimensions are in **millimeters (mm)**
- SolidWorks API uses **meters** internally (automatically converted)

### Coordinate System
- Origin (0, 0) is at the center of the sketch plane
- Positive X is right, positive Y is up
- Extrusions go in the positive Z direction (unless reversed)

### Limitations
- ~~Currently supports basic sketches (rectangles and circles)~~
  - fixed in v0.2
- ~~One sketch per part (creates new part for each design)~~
  - fixed in v0.2
- ~~Limited to Boss-Extrude features~~
  - fixed in v0.2
- AI Agent has minimal context about what it's doing, and is basically building half-blind 

## Future Enhancements

- [x] Additional sketch tools (lines, arcs, splines)
- [x] Sketch constraints and dimensions
- [x] Cut-Extrude features
- [x] Revolve, Sweep, Loft features
- [ ] Assembly creation
- [ ] Drawing generation
- [ ] File save/export functionality

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Built with [Model Context Protocol](https://modelcontextprotocol.io/)
- Powered by [Anthropic's Claude](https://www.anthropic.com/claude)
- Uses [SolidWorks API](https://www.solidworks.com/api)

## Support

For issues and questions:
- Open an issue on [GitHub](https://github.com/ambrosic/solidworks-mcp/issues)
- Check the log file: `solidworks_mcp.log`

---

**Note:** This project is not affiliated with or endorsed by Dassault Systèmes SolidWorks Corporation.