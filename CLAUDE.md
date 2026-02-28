# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SolidWorks MCP Server bridges Claude AI with SolidWorks CAD via the Model Context Protocol (MCP), enabling natural language creation and manipulation of 3D CAD models. Requires Windows + SolidWorks installed.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests (closes open docs first, then runs Basic + Sketch Tools + Feature Tools + Integration)
python test.py

# Interactive CLI test picker — select tests by number, range, or category
python test.py --gui

# Run a single category
python test.py --category "Sketch Tools"
python test.py --category "Feature Tools"
python test.py --category "Integration"

# Run a single test by name
python test.py --test basic_cube
python test.py --test sketch_line

# List all available tests
python test.py --list

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
server.py                         # MCP server: registers tools, routes calls via dispatch map
solidworks/
  __init__.py                     # Package exports for all modules
  connection.py                   # COM connection to SolidWorks, template discovery, part creation
  sketching.py                    # 2D sketch tools, dimensioning, and constraints with spatial tracking
  modeling.py                     # Core modeling (new_part, extrusion, cut-extrusion, mass_properties, list_features)
  selection_helpers.py            # Shared selection utilities (edge, face, plane, feature, axis)
  features.py                     # Boss/Base features (revolve, sweep, loft, boundary boss)
  cut_features.py                 # Cut features (cut revolve, cut sweep, cut loft, boundary cut)
  applied_features.py             # Applied features (fillet, chamfer, shell, draft, rib, wrap, intersect)
  patterns.py                     # Patterns (linear pattern, circular pattern, mirror)
  hole_features.py                # Hole features (hole wizard, cosmetic thread)
  reference_geometry.py           # Reference geometry (ref plane, ref axis, ref point, coordinate system)
  geometry_query.py               # Geometry inspection (body info, faces, edges, face edges, vertices)
test.py                           # Unified test suite with registry, CLI selector (--gui), category/test filters
clean.py                          # Close all open SolidWorks documents (standalone utility)
```

**Test suite (`test.py`):** Uses a decorator-based test registry with 4 categories (Basic, Sketch Tools, Feature Tools, Integration). Each test is `def test_xxx(sw, template) -> bool`. The runner closes all open docs before starting, and between each test. The Integration category wraps the sequential cut-extrude reliability sub-tests as a single meta-test.

**Data flow:** Claude → MCP tool call → `server.py` → `_route_tool()` (dispatch map) → module → SolidWorks COM API

**Routing:** `server.py` builds a `{tool_name: module}` dispatch map at startup from each module's `get_tool_definitions()`. No static tool lists needed—adding a tool to a module auto-registers it.

**Workflow order:** `new_part` → `create_sketch` → sketch entities → (optional: dimensions/constraints) → `exit_sketch` → feature creation (extrude, revolve, etc.)

## Key Implementation Details

**Units:** All tool inputs/outputs use millimeters. The SolidWorks COM API requires meters, so all values are divided by 1000 internally before API calls. Angles are input in degrees and converted to radians internally.

**Spatial tracking:** `SketchingTools` maintains a `last_shape` dict with the center, edges, width/height/radius of the most recently drawn shape. This enables Claude to position shapes relative to previous ones without needing to track coordinates itself. Entities that update spatial tracking: rectangle, circle, line, arc, polygon, ellipse, spline, slot. Entities that do NOT update tracking: point, centerline, text.

**Positioning priority** in `sketch_rectangle`/`sketch_circle`/`sketch_polygon` (highest wins):
1. Absolute `centerX`/`centerY`
2. `spacing` from last shape edge
3. Relative `relativeX`/`relativeY` offset from last center
4. Default: origin `(0, 0)`

**Loft workflow:** Lofts require profiles on different planes. The `create_sketch` `plane` parameter accepts both standard planes ("Front", "Top", "Right") and custom reference plane names ("Plane1", "Plane2", etc.). Typical workflow:
1. `create_sketch(plane="Front")` → draw first profile → `exit_sketch` (returns sketch name, e.g., "Sketch1")
2. `ref_plane(type="OFFSET", referencePlane="Front", offset=80)` (returns plane name, e.g., "Plane1")
3. `create_sketch(plane="Plane1")` → draw second profile → `exit_sketch` (returns "Sketch2")
4. `loft(profileSketches=["Sketch1", "Sketch2"])`

**Selection helpers** (`selection_helpers.py`): All geometry selection (edges, faces, planes, features, axes, vertices) is centralized here. Functions accept coordinates in mm and convert to meters. Used by all feature modules. Key functions: `select_edge`, `select_face`, `select_plane`, `select_feature`, `select_sketch`, `select_axis`, `select_vertex`, `select_multiple_edges`, `select_multiple_faces`.

**Module pattern:** Each feature module follows the same structure: class with `__init__(self, connection)`, `get_tool_definitions() -> list[Tool]`, and `execute(tool_name, args) -> str`. Return strings prefixed with ✓ on success; raise exceptions on failure.

**Feature name returns:** All tools that create features return the SolidWorks feature name in their success string (e.g., `"✓ Extrusion 'Boss-Extrude1' 50mm created"`). This enables agents to chain operations — e.g., create an extrusion, read its name from the return, then pass it to `fillet`, `mirror`, or `linear_pattern`. Sketch tools return the sketch name (e.g., `"✓ Exited sketch mode (Sketch1)"`), and `ref_plane` returns the plane name (e.g., `"✓ Reference plane 'Plane1' created"`).

**Extrusion end conditions:** Both `create_extrusion` and `create_cut_extrusion` accept an optional `endCondition` parameter: `"BLIND"` (default, extrudes to specified depth) or `"THROUGH_ALL"` (extrudes through entire body). Through All is especially useful for cut-extrusions where the agent doesn't need to calculate exact depth.

### Sketch Tools (18 tools)

`sketch_rectangle`, `sketch_circle`, `sketch_line`, `sketch_centerline`, `sketch_arc` (3-point or center-point), `sketch_spline`, `sketch_ellipse`, `sketch_polygon`, `sketch_slot`, `sketch_point`, `sketch_text`, `sketch_dimension` (add smart dimension with optional driving value), `set_dimension_value` (modify existing dimension), `sketch_constraint`, `sketch_toggle_construction`, `create_sketch`, `exit_sketch`, `get_last_shape_info`.

### Modeling Tools (5 tools)

`new_part`, `create_extrusion`, `create_cut_extrusion`, `get_mass_properties`, `list_features`.

### Boss/Base Features (4 tools)

`revolve` (requires centerline in sketch), `sweep` (profile + path sketches), `loft` (2+ profile sketches), `boundary_boss` (profiles + optional guide curves).

### Cut Features (4 tools)

`cut_revolve`, `cut_sweep`, `cut_loft`, `boundary_cut`. Same params as boss counterparts but remove material.

### Applied Features (7 tools)

`fillet` (edges + radius), `chamfer` (edges + distance), `shell` (faces to remove + thickness), `draft` (neutral plane + faces + angle), `rib` (sketch profile + thickness), `wrap` (emboss/deboss/scribe onto face), `intersect` (overlapping bodies).

### Patterns (3 tools)

`linear_pattern` (features + direction edge + spacing + count, optional 2nd direction), `circular_pattern` (features + axis + count + angle), `mirror` (features + mirror plane).

### Hole Features (2 tools)

`hole_wizard` (FLAGGED: may trigger blocking dialog), `thread` (cosmetic thread on circular edge).

### Reference Geometry (4 tools)

`ref_plane` (offset/angle/through-point), `ref_axis` (two-points/cylindrical-face/edge), `ref_point` (coordinates/arc-center/face-center/on-edge), `coordinate_system` (origin + optional axis edges).

### Geometry Query Tools (5 tools)

`get_body_info` (bounding box, face/edge/vertex counts), `get_faces` (enumerate with type, area, normal, sample point; optional `surfaceType` filter), `get_edges` (enumerate with endpoints, midpoint, length; optional `edgeType` filter), `get_face_edges` (edges of a specific face by coordinate), `get_vertices` (all unique vertex coordinates).

**Recommended workflow:** After creating geometry, call `get_body_info` for an overview, then `get_faces` or `get_edges` to find exact coordinates for fillet, chamfer, shell, draft, and pattern operations. The sample points and midpoints returned by these tools are guaranteed to be on/near the geometry and can be passed directly to selection-based tools.

**Dimensioning tools:** `sketch_dimension` adds a smart dimension to selected sketch entities (1 entity for length/radius, 2 for between-distance), with an optional `value` parameter to set the driving value (mm). `set_dimension_value` modifies an existing dimension by selecting it at its text position. `AddDimension2` triggers a blocking "Modify" dialog; this is handled by a background thread that auto-dismisses the dialog via `win32gui` (finds window class `#32770` title "Modify", sends Enter). `AddToDB=True` / `DisplayWhenAdded=False` reduce UI overhead.

**Hole Wizard (flagged):** May trigger a blocking PropertyManager dialog similar to the dimensioning issue. Uses `AddToDB=True` / `DisplayWhenAdded=False` as mitigation. If it fails, use sketch circle + cut-extrude as a workaround.

**SolidWorks COM:** Uses `win32com.client` via `pywin32`. `connection.py` attempts to connect to an already-running SolidWorks instance first, then launches a new one. Template path is discovered by glob: `C:\ProgramData\SOLIDWORKS\SOLIDWORKS *\templates\Part.prtdot`.

**Key COM APIs:**
- `FeatureExtrusion2` (23 params) - see `modeling.py`
- `FeatureCut4` (27 params) - see `modeling.py`
- `FeatureRevolve2` (20 params) - see `features.py` / `cut_features.py`
- `InsertProtrusionSwept4` / `InsertCutSwept5` - see `features.py` / `cut_features.py`
- `InsertProtrusionBlend2` (18 params for SW2025) / `InsertCutBlend2` (18 params for SW2025) - see `features.py` / `cut_features.py`
- `FeatureFillet3`, `InsertFeatureChamfer`, `InsertFeatureShell`, `InsertFeatureDraft` - see `applied_features.py`
- `FeatureLinearPattern4`, `FeatureCircularPattern4`, `InsertMirrorFeature2` - see `patterns.py`
- `InsertRefPlane`, `InsertRefAxis`, `InsertReferencePoint`, `InsertCoordinateSystem` - see `reference_geometry.py`
- `IBody2::GetBodyBox`, `IBody2::GetFaces`, `IBody2::GetEdges`, `IFace2::GetArea`, `IFace2::GetUVBounds`, `ISurface::Evaluate`, `IEdge::GetStartVertex`, `IEdge::GetEndVertex`, `IEdge::GetClosestPointOn` - see `geometry_query.py`

**Logging:** Written to `solidworks_mcp.log` in the project root and to stdout. Log level is INFO.

## Platform Constraint

This project only runs on Windows with SolidWorks installed. There is no mock/stub for the COM layer—any test or development requires a live SolidWorks instance.
