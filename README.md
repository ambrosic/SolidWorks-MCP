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
- **SolidWorks 2022 or later** (tested on SolidWorks 2024)
- **Python 3.8+**
- **Claude Desktop App**

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/solidworks-mcp.git
cd solidworks-mcp
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

**requirements.txt:**
```
mcp>=0.9.0
pywin32>=306
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
| `solidworks_create_sketch` | Create a new sketch on Front, Top, or Right plane |
| `solidworks_sketch_rectangle` | Draw a rectangle with specified corner coordinates |
| `solidworks_sketch_circle` | Draw a circle with center point and radius |
| `solidworks_create_extrusion` | Extrude the current sketch to create a 3D feature |
| `solidworks_exit_sketch` | Exit sketch editing mode |

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

### "Failed to connect to SolidWorks"
- Check that SolidWorks is running
- Run Claude Desktop as Administrator
- Verify `pywin32` is installed: `pip install pywin32`

### "No Part template found"
- Check that SolidWorks templates exist at: `C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2024\templates\`
- Update the template path in `server.py` if your templates are elsewhere

### Tool errors in Claude
- Check the log file: `solidworks_mcp.log`
- Restart Claude Desktop
- Verify the config file path is correct

## Project Structure
```
solidworks-mcp/
├── server.py              # Main MCP server
├── test_solidworks.py     # Test script
├── requirements.txt       # Python dependencies
├── README.md             # This file
└── solidworks_mcp.log    # Log file (generated)
```

## Technical Details

### Units
- Input dimensions are in **millimeters (mm)**
- SolidWorks API uses **meters** internally (automatically converted)

### Coordinate System
- Origin (0, 0) is at the center of the sketch plane
- Positive X is right, positive Y is up
- Extrusions go in the positive Z direction (unless reversed)

### Limitations
- Currently supports basic sketches (rectangles and circles)
- One sketch per part (creates new part for each design)
- Limited to Boss-Extrude features

## Future Enhancements

- [ ] Additional sketch tools (lines, arcs, splines)
- [ ] Sketch constraints and dimensions
- [ ] Cut-Extrude features
- [ ] Revolve, Sweep, Loft features
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
- Open an issue on [GitHub](https://github.com/yourusername/solidworks-mcp/issues)
- Check the log file: `solidworks_mcp.log`

---

**Note:** This project is not affiliated with or endorsed by Dassault Systèmes SolidWorks Corporation.