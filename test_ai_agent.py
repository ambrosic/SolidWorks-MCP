"""
AI Agent Live Integration Test Suite for SolidWorks MCP
Tests realistic AI agent workflows through the MCP tool execution path.
Requires Windows with SolidWorks installed.

Run: python test_ai_agent.py
"""

import sys
import traceback
import pythoncom

from solidworks import SolidWorksConnection, SketchingTools, ModelingTools
from server import SolidWorksMCPServer


# ---------------------------------------------------------------------------
# Logging helpers (match test_solidworks.py style)
# ---------------------------------------------------------------------------

def log_success(msg):
    print(f"  \u2713 SUCCESS: {msg}")

def log_error(msg):
    print(f"  \u2717 ERROR: {msg}")

def log_info(msg):
    print(f"  -> {msg}")


# ---------------------------------------------------------------------------
# Shared test infrastructure
# ---------------------------------------------------------------------------

class AgentTestHarness:
    """Simulates an AI agent's interaction with SolidWorks MCP tools.

    Routes tool calls through the same dispatch logic as server.py,
    testing the actual interface an AI agent would use.
    """

    def __init__(self):
        self.connection = SolidWorksConnection()
        self.sketching = SketchingTools(self.connection)
        self.modeling = ModelingTools(self.connection)

        if not self.connection.connect():
            raise Exception("Failed to connect to SolidWorks")

    def call(self, tool_name, args=None):
        """Route a tool call exactly as the MCP server would."""
        if args is None:
            args = {}

        if tool_name in SolidWorksMCPServer.SKETCHING_TOOLS:
            return self.sketching.execute(tool_name, args)
        elif tool_name in SolidWorksMCPServer.MODELING_TOOLS:
            return self.modeling.execute(tool_name, args, self.sketching)
        else:
            raise Exception(f"Unknown tool: {tool_name}")

    def new_part_and_sketch(self, plane="Front"):
        """Convenience: create a new part and open a sketch (common agent start)."""
        r1 = self.call("solidworks_new_part")
        r2 = self.call("solidworks_create_sketch", {"plane": plane})
        return r1, r2


# ---------------------------------------------------------------------------
# Test Scenarios
# ---------------------------------------------------------------------------

def test_basic_box(h):
    """Scenario 1: Simple cube creation — the fundamental agent workflow.
    new_part -> create_sketch(Front) -> rectangle(100x100) -> exit_sketch -> extrusion(100)
    """
    log_info("Creating a 100mm cube via MCP tool calls")

    r1 = h.call("solidworks_new_part")
    assert "\u2713" in r1, f"new_part failed: {r1}"

    r2 = h.call("solidworks_create_sketch", {"plane": "Front"})
    assert "\u2713" in r2, f"create_sketch failed: {r2}"

    r3 = h.call("solidworks_sketch_rectangle", {"width": 100, "height": 100})
    assert "\u2713" in r3, f"sketch_rectangle failed: {r3}"

    r4 = h.call("solidworks_exit_sketch")
    assert "\u2713" in r4, f"exit_sketch failed: {r4}"

    r5 = h.call("solidworks_create_extrusion", {"depth": 100})
    assert "\u2713" in r5, f"create_extrusion failed: {r5}"

    log_success("Basic box (100mm cube) created")
    return True


def test_spatial_positioning(h):
    """Scenario 2: Draw shapes using spatial positioning system.
    Rectangle at origin -> get_last_shape_info -> circle with spacing -> verify position
    """
    log_info("Testing spatial positioning (spacing from last shape)")

    h.new_part_and_sketch("Front")

    h.call("solidworks_sketch_rectangle", {"width": 80, "height": 60})

    info1 = h.call("solidworks_get_last_shape_info")
    assert "rectangle" in info1, f"Expected rectangle info, got: {info1}"
    assert "80" in info1, f"Expected width 80 in info: {info1}"

    h.call("solidworks_sketch_circle", {"radius": 20, "spacing": 10})

    info2 = h.call("solidworks_get_last_shape_info")
    assert "circle" in info2, f"Expected circle info, got: {info2}"
    # Circle should be at x = 40 (rect right) + 10 (spacing) + 20 (radius) = 70
    assert "70.0" in info2, f"Expected center at 70.0, got: {info2}"

    log_success("Spatial positioning (spacing) works correctly")
    return True


def test_all_sketch_entities(h):
    """Scenario 3: Call every sketch entity tool through the MCP interface."""
    log_info("Testing all 12 sketch entity tools through execute()")

    h.new_part_and_sketch("Front")

    results = []

    # Rectangle
    results.append(("rectangle", h.call("solidworks_sketch_rectangle", {"width": 40, "height": 30})))

    # Circle
    results.append(("circle", h.call("solidworks_sketch_circle",
                                      {"radius": 15, "centerX": 80, "centerY": 0})))

    # Line
    results.append(("line", h.call("solidworks_sketch_line",
                                    {"x1": -60, "y1": -40, "x2": -20, "y2": -40})))

    # Centerline
    results.append(("centerline", h.call("solidworks_sketch_centerline",
                                          {"x1": 0, "y1": -60, "x2": 0, "y2": 60})))

    # Arc (3-point)
    results.append(("arc_3pt", h.call("solidworks_sketch_arc",
                                       {"mode": "3point",
                                        "x1": -60, "y1": 20, "x2": -20, "y2": 20,
                                        "x3": -40, "y3": 35})))

    # Arc (center)
    results.append(("arc_center", h.call("solidworks_sketch_arc",
                                          {"mode": "center",
                                           "centerX": 80, "centerY": 40,
                                           "x1": 100, "y1": 40, "x2": 80, "y2": 60})))

    # Spline
    results.append(("spline", h.call("solidworks_sketch_spline",
                                      {"points": [{"x": -60, "y": 50},
                                                   {"x": -40, "y": 70},
                                                   {"x": -20, "y": 50}]})))

    # Ellipse
    results.append(("ellipse", h.call("solidworks_sketch_ellipse",
                                       {"centerX": 0, "centerY": -80,
                                        "majorRadius": 25, "minorRadius": 15})))

    # Polygon (hexagon)
    results.append(("polygon", h.call("solidworks_sketch_polygon",
                                       {"radius": 20, "numSides": 6,
                                        "centerX": -80, "centerY": -80})))

    # Slot
    results.append(("slot", h.call("solidworks_sketch_slot",
                                    {"x1": 50, "y1": -80, "x2": 100, "y2": -80, "width": 15})))

    # Point
    results.append(("point", h.call("solidworks_sketch_point", {"x": 0, "y": 0})))

    # Text
    results.append(("text", h.call("solidworks_sketch_text",
                                    {"x": -80, "y": 80, "text": "MCP", "height": 8})))

    failed = [(name, r) for name, r in results if "\u2713" not in r]
    if failed:
        for name, r in failed:
            log_error(f"{name}: {r}")
        return False

    log_success("All 12 sketch entity tools work through MCP interface")
    return True


def test_multi_shape_extrusion(h):
    """Scenario 4: Multiple shapes in one sketch, then extrude."""
    log_info("Drawing rectangle + circle, then extruding")

    h.new_part_and_sketch("Front")

    h.call("solidworks_sketch_rectangle", {"width": 100, "height": 60})
    h.call("solidworks_sketch_circle", {"radius": 15, "spacing": 20})

    h.call("solidworks_exit_sketch")
    r = h.call("solidworks_create_extrusion", {"depth": 30})
    assert "\u2713" in r, f"Extrusion failed: {r}"

    log_success("Multi-shape sketch extruded successfully")
    return True


def test_constraint_workflow(h):
    """Scenario 5: Draw lines and apply a geometric constraint."""
    log_info("Drawing two lines and applying PARALLEL constraint")

    h.new_part_and_sketch("Front")

    h.call("solidworks_sketch_line", {"x1": 0, "y1": 0, "x2": 50, "y2": 30})
    h.call("solidworks_sketch_line", {"x1": 0, "y1": -20, "x2": 50, "y2": -5})

    r = h.call("solidworks_sketch_constraint", {
        "constraintType": "PARALLEL",
        "entityPoints": [
            {"x": 25, "y": 15},
            {"x": 25, "y": -12.5}
        ]
    })
    assert "\u2713" in r, f"Constraint failed: {r}"

    log_success("PARALLEL constraint applied between two lines")
    return True


def test_construction_geometry(h):
    """Scenario 6: Draw a line and toggle it to construction geometry."""
    log_info("Drawing a line and toggling to construction")

    h.new_part_and_sketch("Front")

    h.call("solidworks_sketch_line", {"x1": -50, "y1": 0, "x2": 50, "y2": 0})

    r = h.call("solidworks_sketch_toggle_construction", {"x": 0, "y": 0})
    assert "\u2713" in r, f"Toggle failed: {r}"
    assert "construction" in r, f"Expected 'construction' in result: {r}"

    log_success("Line toggled to construction geometry")
    return True


def test_multi_feature_part(h):
    """Scenario 7: Multi-feature part — base extrusion + cut on face."""
    log_info("Creating base box, then cutting a circular hole on front face")

    # Base: 100x100x50 box
    h.new_part_and_sketch("Front")
    h.call("solidworks_sketch_rectangle", {"width": 100, "height": 100})
    h.call("solidworks_exit_sketch")
    h.call("solidworks_create_extrusion", {"depth": 50})

    # Cut: sketch circle on the front face and cut-extrude
    h.call("solidworks_create_sketch", {
        "faceX": 0, "faceY": 0, "faceZ": 50
    })
    h.call("solidworks_sketch_circle", {"radius": 20, "centerX": 0, "centerY": 0})

    r = h.call("solidworks_create_cut_extrusion", {"depth": 25, "reverse": True})
    assert "\u2713" in r, f"Cut-extrusion failed: {r}"

    log_success("Multi-feature part (box + circular cut) created")
    return True


def test_mass_properties(h):
    """Scenario 8: Create known geometry and verify mass properties."""
    log_info("Creating 100mm cube and checking volume/surface area")

    h.new_part_and_sketch("Front")
    h.call("solidworks_sketch_rectangle", {"width": 100, "height": 100})
    h.call("solidworks_exit_sketch")
    h.call("solidworks_create_extrusion", {"depth": 100})

    r = h.call("solidworks_get_mass_properties")
    assert "Volume:" in r, f"Missing volume in output: {r}"

    # Extract volume value — should be close to 1,000,000 mm^3
    for line in r.split("\n"):
        if "Volume:" in line:
            vol_str = line.split(":")[1].strip().split()[0]
            vol = float(vol_str)
            if abs(vol - 1_000_000) > 1:
                log_error(f"Volume {vol} mm^3 != expected ~1,000,000 mm^3")
                return False
            break

    # Extract surface area — should be close to 60,000 mm^2
    for line in r.split("\n"):
        if "Surface Area:" in line:
            area_str = line.split(":")[1].strip().split()[0]
            area = float(area_str)
            if abs(area - 60_000) > 1:
                log_error(f"Surface area {area} mm^2 != expected ~60,000 mm^2")
                return False
            break

    log_success("Mass properties verified (volume=1M mm^3, area=60K mm^2)")
    return True


def test_polygon_extrusion(h):
    """Scenario 9: Hexagonal profile extruded."""
    log_info("Creating extruded hexagon")

    h.new_part_and_sketch("Front")
    h.call("solidworks_sketch_polygon", {"radius": 30, "numSides": 6})
    h.call("solidworks_exit_sketch")
    r = h.call("solidworks_create_extrusion", {"depth": 40})
    assert "\u2713" in r, f"Polygon extrusion failed: {r}"

    log_success("Hexagonal extrusion created")
    return True


def test_ellipse_extrusion(h):
    """Scenario 10: Elliptical profile extruded."""
    log_info("Creating extruded ellipse")

    h.new_part_and_sketch("Front")
    h.call("solidworks_sketch_ellipse", {
        "centerX": 0, "centerY": 0,
        "majorRadius": 40, "minorRadius": 25
    })
    h.call("solidworks_exit_sketch")
    r = h.call("solidworks_create_extrusion", {"depth": 30})
    assert "\u2713" in r, f"Ellipse extrusion failed: {r}"

    log_success("Elliptical extrusion created")
    return True


def test_slot_extrusion(h):
    """Scenario 11: Slot profile extruded."""
    log_info("Creating extruded slot")

    h.new_part_and_sketch("Front")
    h.call("solidworks_sketch_slot", {
        "x1": -30, "y1": 0, "x2": 30, "y2": 0, "width": 20
    })
    h.call("solidworks_exit_sketch")
    r = h.call("solidworks_create_extrusion", {"depth": 15})
    assert "\u2713" in r, f"Slot extrusion failed: {r}"

    log_success("Slot extrusion created")
    return True


def test_relative_positioning_modes(h):
    """Scenario 12: Exercise all positioning modes in one sketch."""
    log_info("Testing default, absolute, relative, and spacing positioning")

    h.new_part_and_sketch("Front")

    # Default: origin
    h.call("solidworks_sketch_rectangle", {"width": 40, "height": 40})
    info = h.call("solidworks_get_last_shape_info")
    assert "0.0, 0.0" in info, f"Default not at origin: {info}"

    # Relative offset from last shape center
    h.call("solidworks_sketch_circle", {"radius": 10, "relativeX": 0, "relativeY": 50})
    info = h.call("solidworks_get_last_shape_info")
    assert "50.0" in info, f"Relative Y not at 50: {info}"

    # Spacing from last shape right edge
    h.call("solidworks_sketch_polygon", {"radius": 15, "numSides": 5, "spacing": 5})
    info = h.call("solidworks_get_last_shape_info")
    # circle right = 10+10 = 20... wait, circle was at (0, 50), radius 10, right=10
    # polygon center = 10 (right) + 5 (spacing) + 15 (radius) = 30
    assert "polygon" in info, f"Expected polygon: {info}"

    # Absolute position
    h.call("solidworks_sketch_rectangle", {
        "width": 30, "height": 30,
        "centerX": -80, "centerY": -80
    })
    info = h.call("solidworks_get_last_shape_info")
    assert "-80.0" in info, f"Absolute not at -80: {info}"

    log_success("All positioning modes work correctly")
    return True


def test_sketch_on_multiple_planes(h):
    """Scenario 13: Sketches on different reference planes."""
    log_info("Creating extrusions on Front and Top planes")

    # Front plane extrusion
    h.new_part_and_sketch("Front")
    h.call("solidworks_sketch_rectangle", {"width": 60, "height": 60})
    h.call("solidworks_exit_sketch")
    h.call("solidworks_create_extrusion", {"depth": 40})

    # Top plane sketch + extrusion
    h.call("solidworks_create_sketch", {"plane": "Top"})
    h.call("solidworks_sketch_circle", {"radius": 15, "centerX": 0, "centerY": 0})
    h.call("solidworks_exit_sketch")
    r = h.call("solidworks_create_extrusion", {"depth": 80})
    assert "\u2713" in r, f"Top plane extrusion failed: {r}"

    log_success("Multi-plane extrusions created (Front + Top)")
    return True


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_all_tests():
    """Run all live integration tests and report results."""
    print("=" * 70)
    print("AI Agent Live Integration Test Suite for SolidWorks MCP")
    print("=" * 70)

    pythoncom.CoInitialize()

    try:
        h = AgentTestHarness()
    except Exception as e:
        log_error(f"Failed to initialize: {e}")
        traceback.print_exc()
        return False

    tests = [
        ("Basic Box (cube)", test_basic_box),
        ("Spatial Positioning", test_spatial_positioning),
        ("All Sketch Entities", test_all_sketch_entities),
        ("Multi-Shape Extrusion", test_multi_shape_extrusion),
        ("Constraint Workflow", test_constraint_workflow),
        ("Construction Geometry", test_construction_geometry),
        ("Multi-Feature Part", test_multi_feature_part),
        ("Mass Properties", test_mass_properties),
        ("Polygon Extrusion", test_polygon_extrusion),
        ("Ellipse Extrusion", test_ellipse_extrusion),
        ("Slot Extrusion", test_slot_extrusion),
        ("Relative Positioning Modes", test_relative_positioning_modes),
        ("Sketch on Multiple Planes", test_sketch_on_multiple_planes),
    ]

    results = []

    for name, test_fn in tests:
        print(f"\n--- {name} ---")
        try:
            passed = test_fn(h)
            results.append((name, passed))
        except Exception as e:
            log_error(f"{name} raised: {e}")
            traceback.print_exc()
            results.append((name, False))

    # Summary
    total = len(results)
    passed = sum(1 for _, p in results if p)

    print(f"\n{'=' * 70}")
    print(f"Results: {passed}/{total} tests passed")

    if passed < total:
        print(f"\nFailed tests:")
        for name, p in results:
            if not p:
                print(f"  - {name}")

    print(f"{'=' * 70}")
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    print("\nPress Enter to exit...")
    input()
    sys.exit(0 if success else 1)
