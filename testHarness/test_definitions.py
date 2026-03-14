"""
Test definitions for the full Claude Code test suite.

Each test is a natural language prompt sent to Claude Code via `claude --print`.
Claude uses the SolidWorks MCP tools to accomplish the task, then reports results.

Tests mirror the categories in test.py but are driven by LLM + MCP rather than
direct COM API calls.
"""

# ---------------------------------------------------------------------------
# Test definition structure
# ---------------------------------------------------------------------------
# Each test dict has:
#   name          - unique identifier (matches test.py where applicable)
#   display_name  - human-readable name
#   category      - grouping: Basic, Sketch Tools, Feature Tools, Geometry Query,
#                   Applied Features, Patterns, Advanced, Integration
#   prompt        - natural language instruction for Claude
#   verify        - list of strings that MUST appear in Claude's output (case-insensitive)
#   timeout       - seconds before the test is killed (default 300)
#   max_turns     - max agentic turns for Claude (default 15)
# ---------------------------------------------------------------------------


FULL_TEST_SUITE = [
    # ===================================================================
    # BASIC
    # ===================================================================
    {
        "name": "basic_cube",
        "display_name": "Basic Cube (100mm)",
        "category": "Basic",
        "prompt": (
            "Create a 100mm cube in SolidWorks. "
            "Start with solidworks_new_part, create a sketch on the Front plane, "
            "draw a 100x100mm rectangle, exit the sketch, then extrude it 100mm. "
            "After creating it, call solidworks_get_mass_properties and report the volume. "
            "Expected volume is approximately 1,000,000 mm^3."
        ),
        "verify": ["volume"],
    },
    {
        "name": "basic_prism",
        "display_name": "Basic Prism (80x40x25)",
        "category": "Basic",
        "prompt": (
            "Create an 80mm x 40mm x 25mm rectangular prism in SolidWorks. "
            "Start with solidworks_new_part, create a sketch on the Front plane, "
            "draw an 80x40mm rectangle, exit the sketch, then extrude it 25mm. "
            "Call solidworks_get_mass_properties and report the volume. "
            "Expected volume is approximately 80,000 mm^3."
        ),
        "verify": ["volume"],
    },
    {
        "name": "basic_cylinder",
        "display_name": "Basic Cylinder",
        "category": "Basic",
        "prompt": (
            "Create a cylinder in SolidWorks with radius 25mm and height 50mm. "
            "Start with solidworks_new_part, create a sketch on the Front plane, "
            "draw a circle with radius 25mm centered at (0,0), exit the sketch, "
            "then extrude it 50mm. "
            "Call solidworks_get_mass_properties and report the volume. "
            "Expected volume is approximately 98,175 mm^3 (pi * 25^2 * 50)."
        ),
        "verify": ["volume"],
    },

    # ===================================================================
    # SKETCH TOOLS
    # ===================================================================
    {
        "name": "sketch_line",
        "display_name": "Sketch Line",
        "category": "Sketch Tools",
        "prompt": (
            "In SolidWorks, create a new part, open a sketch on the Front plane, "
            "and draw a line from (0,0) to (50,50) mm. Exit the sketch. "
            "Report whether the line was created successfully."
        ),
        "verify": [],
    },
    {
        "name": "sketch_centerline",
        "display_name": "Sketch Centerline",
        "category": "Sketch Tools",
        "prompt": (
            "In SolidWorks, create a new part, open a sketch on the Front plane, "
            "and draw a vertical centerline from (0,-50) to (0,50) mm. Exit the sketch. "
            "Report whether the centerline was created successfully."
        ),
        "verify": [],
    },
    {
        "name": "sketch_point",
        "display_name": "Sketch Point",
        "category": "Sketch Tools",
        "prompt": (
            "In SolidWorks, create a new part, open a sketch on the Front plane, "
            "and create a sketch point at (25, 25) mm. Exit the sketch. "
            "Report whether the point was created successfully."
        ),
        "verify": [],
    },
    {
        "name": "sketch_arc",
        "display_name": "Sketch Arc",
        "category": "Sketch Tools",
        "prompt": (
            "In SolidWorks, create a new part, open a sketch on the Front plane. "
            "Draw a 3-point arc: start at (0,0), end at (50,0), mid-point at (25,20) mm. "
            "Exit the sketch and report whether the arc was created successfully."
        ),
        "verify": [],
    },
    {
        "name": "sketch_circle",
        "display_name": "Sketch Circle",
        "category": "Sketch Tools",
        "prompt": (
            "In SolidWorks, create a new part, open a sketch on the Front plane, "
            "and draw a circle centered at (0,0) with radius 30mm. Exit the sketch. "
            "Report whether the circle was created successfully."
        ),
        "verify": [],
    },
    {
        "name": "sketch_rectangle",
        "display_name": "Sketch Rectangle",
        "category": "Sketch Tools",
        "prompt": (
            "In SolidWorks, create a new part, open a sketch on the Front plane, "
            "and draw a rectangle 60mm wide by 40mm tall centered at (30, 20). "
            "Exit the sketch. Report whether the rectangle was created successfully."
        ),
        "verify": [],
    },
    {
        "name": "sketch_polygon",
        "display_name": "Sketch Polygon (Hexagon)",
        "category": "Sketch Tools",
        "prompt": (
            "In SolidWorks, create a new part, open a sketch on the Front plane, "
            "and draw a regular hexagon (6 sides) centered at (0,0) with a circumscribed "
            "radius of 25mm. Exit the sketch. Then extrude it 20mm. "
            "Report whether the hexagon was created and extruded successfully."
        ),
        "verify": [],
    },
    {
        "name": "sketch_ellipse",
        "display_name": "Sketch Ellipse",
        "category": "Sketch Tools",
        "prompt": (
            "In SolidWorks, create a new part, open a sketch on the Front plane, "
            "and draw an ellipse centered at (0,0) with semi-major axis 30mm and "
            "semi-minor axis 20mm. Exit the sketch. Then extrude it 15mm. "
            "Report whether the ellipse was created and extruded successfully."
        ),
        "verify": [],
    },
    {
        "name": "sketch_slot",
        "display_name": "Sketch Slot",
        "category": "Sketch Tools",
        "prompt": (
            "In SolidWorks, create a new part, open a sketch on the Front plane, "
            "and draw a straight slot 50mm long and 10mm wide. Exit the sketch. "
            "Then extrude it 10mm. "
            "Report whether the slot was created and extruded successfully."
        ),
        "verify": [],
    },
    {
        "name": "sketch_spline",
        "display_name": "Sketch Spline",
        "category": "Sketch Tools",
        "prompt": (
            "In SolidWorks, create a new part, open a sketch on the Front plane, "
            "and draw a spline through these points: (0,0), (20,30), (40,10), (60,25) mm. "
            "Exit the sketch. Report whether the spline was created successfully."
        ),
        "verify": [],
    },
    {
        "name": "sketch_text",
        "display_name": "Sketch Text",
        "category": "Sketch Tools",
        "prompt": (
            "In SolidWorks, create a new part, open a sketch on the Front plane, "
            "and insert sketch text 'HELLO' at position (0, 0) with height 10mm. "
            "Exit the sketch. Report whether the text was created successfully."
        ),
        "verify": [],
    },
    {
        "name": "sketch_constraint",
        "display_name": "Sketch Constraint",
        "category": "Sketch Tools",
        "prompt": (
            "In SolidWorks, create a new part, open a sketch on the Front plane. "
            "Draw two lines: one from (0,0) to (30,10) and another from (0,20) to (30,30). "
            "Apply a parallel constraint between them. Exit the sketch. "
            "Report whether the constraint was applied successfully."
        ),
        "verify": [],
    },
    {
        "name": "sketch_dimension",
        "display_name": "Sketch Dimension",
        "category": "Sketch Tools",
        "prompt": (
            "In SolidWorks, create a new part, open a sketch on the Front plane. "
            "Draw a horizontal line from (0,0) to (50,0). Add a dimension to the line, "
            "then modify it to 80mm using set_dimension_value. Exit the sketch. "
            "Report the final dimension value."
        ),
        "verify": ["80"],
    },
    {
        "name": "toggle_construction",
        "display_name": "Toggle Construction Geometry",
        "category": "Sketch Tools",
        "prompt": (
            "In SolidWorks, create a new part, open a sketch on the Front plane. "
            "Draw a line from (0,0) to (40,0), then toggle it to construction geometry "
            "using sketch_toggle_construction. Exit the sketch. "
            "Report whether the toggle was successful."
        ),
        "verify": [],
    },

    # ===================================================================
    # FEATURE TOOLS
    # ===================================================================
    {
        "name": "extrusion",
        "display_name": "Extrusion",
        "category": "Feature Tools",
        "prompt": (
            "In SolidWorks, create a new part. Open a sketch on the Front plane, "
            "draw a 50x50mm rectangle, exit the sketch, then extrude it 30mm. "
            "Call solidworks_get_mass_properties and report the volume. "
            "Expected volume is approximately 75,000 mm^3."
        ),
        "verify": ["volume"],
    },
    {
        "name": "cut_extrusion",
        "display_name": "Cut Extrusion",
        "category": "Feature Tools",
        "prompt": (
            "In SolidWorks, create a 100mm cube (sketch rectangle on Front, extrude 100mm). "
            "Then create a sketch on the front face of the cube, draw a circle with radius 20mm "
            "centered at (50,50), exit the sketch, and create a cut-extrusion through all. "
            "Call solidworks_get_mass_properties and report the volume. "
            "It should be less than 1,000,000 mm^3 because of the hole."
        ),
        "verify": ["volume"],
    },
    {
        "name": "fillet",
        "display_name": "Fillet",
        "category": "Feature Tools",
        "prompt": (
            "In SolidWorks, create a 100mm cube. Then apply a 5mm fillet to one edge. "
            "Use solidworks_get_edges first to find edge coordinates if needed. "
            "Call solidworks_list_features and report whether the Fillet feature appears."
        ),
        "verify": ["fillet"],
    },
    {
        "name": "chamfer",
        "display_name": "Chamfer",
        "category": "Feature Tools",
        "prompt": (
            "In SolidWorks, create a 100mm cube. Then apply a 5mm chamfer to one edge. "
            "Use solidworks_get_edges first to find edge coordinates if needed. "
            "Call solidworks_list_features and report whether the Chamfer feature appears."
        ),
        "verify": ["chamfer"],
    },
    {
        "name": "shell",
        "display_name": "Shell",
        "category": "Feature Tools",
        "prompt": (
            "In SolidWorks, create a 100mm cube. Then shell it with 3mm thickness, "
            "removing the top face. Use solidworks_get_faces to find the top face "
            "coordinates if needed. "
            "Call solidworks_list_features and report whether the Shell feature appears."
        ),
        "verify": ["shell"],
    },
    {
        "name": "revolve",
        "display_name": "Revolve",
        "category": "Feature Tools",
        "prompt": (
            "In SolidWorks, create a new part. Open a sketch on the Front plane. "
            "Draw a vertical centerline along the Y-axis from (0,-25) to (0,25). "
            "Draw a closed rectangular profile to the right of the centerline "
            "(e.g., lines from (10,-25) to (30,-25) to (30,25) to (10,25) and back). "
            "Exit the sketch, then revolve it 360 degrees around the centerline. "
            "Call solidworks_get_mass_properties and report the volume."
        ),
        "verify": ["volume"],
    },
    {
        "name": "ref_plane",
        "display_name": "Reference Plane",
        "category": "Feature Tools",
        "prompt": (
            "In SolidWorks, create a new part. Then create an offset reference plane "
            "50mm from the Front Plane using solidworks_ref_plane. "
            "Report whether the reference plane was created successfully."
        ),
        "verify": [],
    },
    {
        "name": "loft",
        "display_name": "Loft (Frustum)",
        "category": "Feature Tools",
        "prompt": (
            "In SolidWorks, create a frustum via loft: "
            "1) Create a sketch on the Front plane, draw a circle radius 40mm at (0,0), exit sketch. "
            "2) Create a reference plane offset 80mm from the Front plane. "
            "3) Create a sketch on that new plane, draw a circle radius 20mm at (0,0), exit sketch. "
            "4) Loft between the two sketches. "
            "Call solidworks_get_mass_properties and report the volume."
        ),
        "verify": ["volume"],
        "max_turns": 20,
    },
    {
        "name": "sweep",
        "display_name": "Sweep",
        "category": "Feature Tools",
        "prompt": (
            "In SolidWorks, create a swept feature: "
            "1) Create a sketch on the Front plane with a circle radius 10mm at (0,0) as the profile. Exit sketch. "
            "2) Create a sketch on the Right plane with a line from (0,0) to (0,100) as the path. Exit sketch. "
            "3) Sweep the profile along the path. "
            "Call solidworks_get_mass_properties and report the volume."
        ),
        "verify": ["volume"],
        "max_turns": 20,
    },
    {
        "name": "draft",
        "display_name": "Draft",
        "category": "Feature Tools",
        "prompt": (
            "In SolidWorks, create a 100mm cube. Then apply a 5-degree draft to one "
            "side face, using the bottom face as the neutral plane. "
            "Use solidworks_get_faces to find face coordinates if needed. "
            "Call solidworks_list_features and report whether the Draft feature appears."
        ),
        "verify": ["draft"],
        "max_turns": 20,
    },
    {
        "name": "rib",
        "display_name": "Rib",
        "category": "Feature Tools",
        "prompt": (
            "In SolidWorks, create a 100mm cube, then shell it (remove top face, 3mm thickness). "
            "Then create a sketch on the Front plane, draw a line across the opening as a rib profile. "
            "Exit the sketch and create a rib with 3mm thickness. "
            "Call solidworks_list_features and report whether the Rib feature appears."
        ),
        "verify": ["rib"],
        "max_turns": 25,
    },

    # ===================================================================
    # PATTERNS
    # ===================================================================
    {
        "name": "linear_pattern",
        "display_name": "Linear Pattern",
        "category": "Patterns",
        "prompt": (
            "In SolidWorks, create a 100mm cube. Fillet one edge with radius 5mm. "
            "Then create a linear pattern of the fillet along one direction: "
            "3 instances, 20mm spacing. Use solidworks_get_edges to find a direction edge. "
            "Call solidworks_list_features and report whether the linear pattern appears."
        ),
        "verify": ["pattern"],
        "max_turns": 25,
    },
    {
        "name": "circular_pattern",
        "display_name": "Circular Pattern",
        "category": "Patterns",
        "prompt": (
            "In SolidWorks, create a cylinder (circle radius 40mm, extrude 30mm). "
            "Then create a small hole: sketch a circle radius 5mm at (25,0) on the top face, "
            "cut-extrude through all. "
            "Create a circular pattern of the cut, 6 instances, 360 degrees, around the Y axis. "
            "Call solidworks_list_features and report whether the circular pattern appears."
        ),
        "verify": ["pattern"],
        "max_turns": 25,
    },
    {
        "name": "mirror",
        "display_name": "Mirror",
        "category": "Patterns",
        "prompt": (
            "In SolidWorks, create a 100mm cube. Fillet one edge with radius 5mm. "
            "Then mirror the fillet across the Right Plane. "
            "Call solidworks_list_features and report whether the Mirror feature appears."
        ),
        "verify": ["mirror"],
        "max_turns": 20,
    },

    # ===================================================================
    # GEOMETRY QUERY
    # ===================================================================
    {
        "name": "get_body_info",
        "display_name": "Get Body Info",
        "category": "Geometry Query",
        "prompt": (
            "In SolidWorks, create a 100mm cube. Then call solidworks_get_body_info. "
            "Report the bounding box, face count (should be 6), edge count (should be 12), "
            "and vertex count (should be 8)."
        ),
        "verify": ["6", "12", "8"],
    },
    {
        "name": "get_faces",
        "display_name": "Get Faces",
        "category": "Geometry Query",
        "prompt": (
            "In SolidWorks, create a 100mm cube. Then call solidworks_get_faces. "
            "Report the total number of faces and their types. "
            "All 6 faces should be planar."
        ),
        "verify": ["planar"],
    },
    {
        "name": "get_edges",
        "display_name": "Get Edges",
        "category": "Geometry Query",
        "prompt": (
            "In SolidWorks, create a 100mm cube. Then call solidworks_get_edges. "
            "Report the total number of edges. Should be 12 line edges."
        ),
        "verify": ["12"],
    },
    {
        "name": "get_face_edges",
        "display_name": "Get Face Edges",
        "category": "Geometry Query",
        "prompt": (
            "In SolidWorks, create a 100mm cube. Then call solidworks_get_face_edges "
            "for the top face (use approximate coordinates of the top face center). "
            "Report the number of edges on that face (should be 4)."
        ),
        "verify": ["4"],
    },
    {
        "name": "get_vertices",
        "display_name": "Get Vertices",
        "category": "Geometry Query",
        "prompt": (
            "In SolidWorks, create a 100mm cube. Then call solidworks_get_vertices. "
            "Report the total number of vertices (should be 8) and list them."
        ),
        "verify": ["8"],
    },
    {
        "name": "geometry_guided_fillet",
        "display_name": "Geometry-Guided Fillet",
        "category": "Geometry Query",
        "prompt": (
            "In SolidWorks, create a 100mm cube. "
            "Call solidworks_get_edges to enumerate all edges and their midpoint coordinates. "
            "Pick one edge midpoint and use those exact coordinates to apply a 5mm fillet. "
            "Call solidworks_list_features and report whether the Fillet appears."
        ),
        "verify": ["fillet"],
        "max_turns": 20,
    },

    # ===================================================================
    # REFERENCE GEOMETRY
    # ===================================================================
    {
        "name": "ref_axis",
        "display_name": "Reference Axis",
        "category": "Reference Geometry",
        "prompt": (
            "In SolidWorks, create a new part. Create a reference axis using two points: "
            "(0,0,0) and (0,100,0). Report whether the axis was created successfully."
        ),
        "verify": [],
    },
    {
        "name": "ref_point",
        "display_name": "Reference Point",
        "category": "Reference Geometry",
        "prompt": (
            "In SolidWorks, create a new part. Create a reference point at coordinates "
            "(50, 50, 50). Report whether the point was created successfully."
        ),
        "verify": [],
    },
    {
        "name": "coordinate_system",
        "display_name": "Coordinate System",
        "category": "Reference Geometry",
        "prompt": (
            "In SolidWorks, create a new part. Create a coordinate system at the origin. "
            "Report whether it was created successfully."
        ),
        "verify": [],
    },

    # ===================================================================
    # INTEGRATION
    # ===================================================================
    {
        "name": "full_integration",
        "display_name": "Full Integration (Cube + Fillet + Cut + Query)",
        "category": "Integration",
        "prompt": (
            "In SolidWorks, perform this multi-step workflow: "
            "1) Create a 100mm cube (new_part, sketch rectangle on Front, extrude 100mm). "
            "2) Apply a 5mm fillet to one edge (use get_edges to find coordinates). "
            "3) Create a cut-extrusion: sketch a circle radius 15mm on the top face, "
            "   cut through all. "
            "4) Call solidworks_list_features — verify Fillet and Cut appear. "
            "5) Call solidworks_get_mass_properties — volume should be less than 1,000,000 mm^3. "
            "Report the feature list and final volume."
        ),
        "verify": ["fillet", "volume"],
        "max_turns": 25,
    },
    {
        "name": "lofted_vase",
        "display_name": "Lofted Vase (Multi-Profile)",
        "category": "Integration",
        "prompt": (
            "In SolidWorks, create a vase shape using a loft with 3 profiles: "
            "1) Front plane: circle radius 30mm at origin. "
            "2) Offset plane 50mm from Front: circle radius 15mm at origin. "
            "3) Offset plane 100mm from Front: circle radius 25mm at origin. "
            "Loft through all three profiles. "
            "Then shell the top with 2mm thickness. "
            "Call solidworks_get_mass_properties and report the volume."
        ),
        "verify": ["volume"],
        "max_turns": 30,
        "timeout": 600,
    },
    {
        "name": "bracket",
        "display_name": "L-Bracket with Holes",
        "category": "Integration",
        "prompt": (
            "In SolidWorks, create an L-shaped bracket: "
            "1) Create a new part. Sketch an L-shape profile on the Front plane "
            "   (e.g., outer boundary 80x60mm, with a 40x40mm cutout in the upper-right). "
            "   Exit sketch and extrude 10mm. "
            "2) Add two through-holes: sketch circles (radius 5mm) on the front face "
            "   at positions in each arm of the L, cut-extrude through all. "
            "3) Fillet the inner corner of the L with radius 5mm. "
            "Call solidworks_list_features and solidworks_get_mass_properties. "
            "Report the feature list and volume."
        ),
        "verify": ["volume"],
        "max_turns": 30,
        "timeout": 600,
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CATEGORY_ORDER = [
    "Basic",
    "Sketch Tools",
    "Feature Tools",
    "Patterns",
    "Geometry Query",
    "Reference Geometry",
    "Integration",
]


def get_tests(category=None, test_name=None):
    """Return filtered test list."""
    tests = FULL_TEST_SUITE
    if category:
        tests = [t for t in tests if t["category"].lower() == category.lower()]
    if test_name:
        tests = [t for t in tests if t["name"] == test_name]
    return tests


def get_categories():
    """Return ordered list of categories that have tests."""
    seen = set()
    cats = []
    for t in FULL_TEST_SUITE:
        if t["category"] not in seen:
            seen.add(t["category"])
            cats.append(t["category"])
    # Sort by CATEGORY_ORDER, then alphabetically for any extras
    def sort_key(c):
        try:
            return CATEGORY_ORDER.index(c)
        except ValueError:
            return len(CATEGORY_ORDER)
    cats.sort(key=sort_key)
    return cats


def list_all_tests():
    """Print all tests grouped by category."""
    for cat in get_categories():
        tests = [t for t in FULL_TEST_SUITE if t["category"] == cat]
        print(f"\n  {cat} ({len(tests)} tests)")
        print(f"  {'─' * 40}")
        for t in tests:
            print(f"    {t['name']:30s} {t['display_name']}")
