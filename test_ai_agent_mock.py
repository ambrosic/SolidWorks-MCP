"""
AI Agent Mock Test Suite for SolidWorks MCP
Tests tool routing, parameter validation, spatial tracking, positioning priority,
agent workflow simulation, and error handling — all without requiring SolidWorks.

Run: python test_ai_agent_mock.py
"""

import sys
import types
import traceback

# ---------------------------------------------------------------------------
# Module-level mocking for Windows-only and MCP dependencies
# Must happen BEFORE any solidworks or server imports
# ---------------------------------------------------------------------------

def _setup_module_mocks():
    """Install fake modules for win32com, pythoncom, and mcp so imports succeed on any platform."""

    # --- pythoncom ---
    pythoncom_mock = types.ModuleType("pythoncom")
    pythoncom_mock.VT_ARRAY = 0x2000
    pythoncom_mock.VT_R8 = 5
    pythoncom_mock.VT_DISPATCH = 9
    pythoncom_mock.CoInitialize = lambda: None
    sys.modules["pythoncom"] = pythoncom_mock

    # --- win32com and win32com.client ---
    win32com_mock = types.ModuleType("win32com")
    win32com_client_mock = types.ModuleType("win32com.client")

    class _VARIANT:
        """Minimal VARIANT stub for spline point arrays and COM dispatch."""
        def __init__(self, vt, data):
            self.vt = vt
            self.data = data

    win32com_client_mock.VARIANT = _VARIANT
    win32com_client_mock.GetActiveObject = lambda *a, **kw: None
    win32com_client_mock.Dispatch = lambda *a, **kw: None

    win32com_mock.client = win32com_client_mock
    sys.modules["win32com"] = win32com_mock
    sys.modules["win32com.client"] = win32com_client_mock

    # --- mcp (Model Context Protocol SDK) ---
    mcp_mock = types.ModuleType("mcp")
    mcp_types = types.ModuleType("mcp.types")
    mcp_server_mod = types.ModuleType("mcp.server")
    mcp_server_stdio = types.ModuleType("mcp.server.stdio")

    class _Tool:
        """Minimal Tool stub matching mcp.types.Tool interface."""
        def __init__(self, name="", description="", inputSchema=None):
            self.name = name
            self.description = description
            self.inputSchema = inputSchema or {}

    class _TextContent:
        def __init__(self, type="text", text=""):
            self.type = type
            self.text = text

    mcp_types.Tool = _Tool
    mcp_types.TextContent = _TextContent

    class _Server:
        def __init__(self, name=""):
            self.name = name
        def list_tools(self):
            def decorator(fn): return fn
            return decorator
        def call_tool(self):
            def decorator(fn): return fn
            return decorator

    mcp_server_mod.Server = _Server
    mcp_server_stdio.stdio_server = None

    mcp_mock.types = mcp_types
    mcp_mock.server = mcp_server_mod
    mcp_mock.server.stdio = mcp_server_stdio

    sys.modules["mcp"] = mcp_mock
    sys.modules["mcp.types"] = mcp_types
    sys.modules["mcp.server"] = mcp_server_mod
    sys.modules["mcp.server.stdio"] = mcp_server_stdio

_setup_module_mocks()


# ---------------------------------------------------------------------------
# Mock Infrastructure
# ---------------------------------------------------------------------------

class MockSketchManager:
    """Stubs all SketchManager methods called by SketchingTools"""

    def __init__(self):
        self.calls = []
        self.AddToDB = False
        self.DisplayWhenAdded = True

    def InsertSketch(self, *args):
        self.calls.append(("InsertSketch", args))

    def CreateCornerRectangle(self, *args):
        self.calls.append(("CreateCornerRectangle", args))

    def CreateCircleByRadius(self, *args):
        self.calls.append(("CreateCircleByRadius", args))

    def CreateLine(self, *args):
        self.calls.append(("CreateLine", args))

    def CreateCenterLine(self, *args):
        self.calls.append(("CreateCenterLine", args))

    def CreatePoint(self, *args):
        self.calls.append(("CreatePoint", args))

    def Create3PointArc(self, *args):
        self.calls.append(("Create3PointArc", args))

    def CreateArc(self, *args):
        self.calls.append(("CreateArc", args))

    def CreatePolygon(self, *args):
        self.calls.append(("CreatePolygon", args))

    def CreateEllipse(self, *args):
        self.calls.append(("CreateEllipse", args))

    def CreateSpline2(self, *args):
        self.calls.append(("CreateSpline2", args))

    def CreateSketchSlot(self, *args):
        self.calls.append(("CreateSketchSlot", args))


class MockFeature:
    """Stub for a SolidWorks feature object"""

    def __init__(self, name="Sketch1"):
        self.Name = name

    def Select2(self, *args):
        pass


class MockFeatureManager:
    """Stub for FeatureManager"""

    def __init__(self):
        self.calls = []

    def FeatureExtrusion2(self, *args):
        self.calls.append(("FeatureExtrusion2", args))
        return MockFeature("Boss-Extrude1")

    def FeatureCut4(self, *args):
        self.calls.append(("FeatureCut4", args))
        return MockFeature("Cut-Extrude1")

    def GetFeatureCount(self, *args):
        return 0

    def GetFeatures(self, *args):
        return []


class MockExtension:
    """Stub for doc.Extension"""

    def SelectByID2(self, *args):
        return True


class MockSelectionManager:
    """Stub for doc.SelectionManager"""

    def GetSelectedObject6(self, *args):
        return MockSketchSegment()


class MockSketchSegment:
    """Stub for a sketch segment returned by selection"""

    def __init__(self):
        self.ConstructionGeometry = False


class MockTextFormat:
    def __init__(self):
        self.CharHeight = 0
        self.Escapement = 0


class MockSketchText:
    def GetTextFormat(self):
        return MockTextFormat()

    def SetTextFormat(self, *args):
        pass


class MockDoc:
    """Fake SolidWorks document that records calls without COM"""

    def __init__(self):
        self.SketchManager = MockSketchManager()
        self.FeatureManager = MockFeatureManager()
        self.Extension = MockExtension()
        self.SelectionManager = MockSelectionManager()
        self._features = {"Front Plane": MockFeature("Front Plane"),
                          "Top Plane": MockFeature("Top Plane"),
                          "Right Plane": MockFeature("Right Plane"),
                          "Sketch1": MockFeature("Sketch1"),
                          "Sketch2": MockFeature("Sketch2"),
                          "Sketch3": MockFeature("Sketch3")}

    def ClearSelection2(self, *args):
        pass

    def FeatureByName(self, name):
        return self._features.get(name, MockFeature(name))

    def ViewZoomtofit2(self):
        pass

    def InsertSketchText(self, *args):
        return MockSketchText()

    def AddDimension2(self, *args):
        return None

    def SketchAddConstraints(self, *args):
        pass

    def ForceRebuild3(self, *args):
        pass

    @property
    def GetMassProperties(self):
        # 12-element tuple in SI units for a 100mm cube
        # 100mm = 0.1m, so volume = 0.1^3 = 1e-3 m^3, area = 6*0.1^2 = 6e-2 m^2
        return (0.05, 0.05, 0.05,   # center of mass (m)
                1e-3,                 # volume (m^3) -> 1,000,000 mm^3
                6e-2,                 # surface area (m^2) -> 60,000 mm^2
                7.85,                 # mass (kg)
                0.001, 0.001, 0.001,  # moments of inertia
                0.0, 0.0, 0.0)       # products of inertia


class MockConnection:
    """Fake SolidWorksConnection that provides MockDoc instances"""

    def __init__(self):
        self.app = True  # pretend connected
        self._doc = MockDoc()

    def ensure_connection(self):
        pass

    def connect(self):
        return True

    def get_active_doc(self):
        return self._doc

    def create_new_part(self):
        self._doc = MockDoc()
        return self._doc

    def find_template(self):
        return "C:\\fake\\Part.prtdot"


# ---------------------------------------------------------------------------
# Logging helpers (match test_solidworks.py style)
# ---------------------------------------------------------------------------

def log_success(msg):
    print(f"  SUCCESS: {msg}")

def log_error(msg):
    print(f"  ERROR: {msg}")

def log_info(msg):
    print(f"  -> {msg}")


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def fresh_tools():
    """Create fresh SketchingTools and ModelingTools with mock connection"""
    # Import here so module-level import errors are caught per-test
    from solidworks.sketching import SketchingTools
    from solidworks.modeling import ModelingTools

    conn = MockConnection()
    sketching = SketchingTools(conn)
    modeling = ModelingTools(conn)
    return conn, sketching, modeling


def route_tool(sketching, modeling, name, args=None):
    """Replicate server.py _route_tool() logic"""
    from server import SolidWorksMCPServer
    sketching_tools = SolidWorksMCPServer.SKETCHING_TOOLS
    modeling_tools = SolidWorksMCPServer.MODELING_TOOLS

    if args is None:
        args = {}

    if name in sketching_tools:
        return sketching.execute(name, args)
    elif name in modeling_tools:
        return modeling.execute(name, args, sketching)
    else:
        raise Exception(f"Unknown tool: {name}")


# ---------------------------------------------------------------------------
# Category 1: Tool Routing
# ---------------------------------------------------------------------------

def test_sketching_tools_route():
    """All 16 sketching tool names dispatch through execute() without KeyError"""
    _, sketching, modeling = fresh_tools()

    # Provide minimal valid args for each tool
    tool_args = {
        "solidworks_create_sketch": {"plane": "Front"},
        "solidworks_sketch_rectangle": {"width": 50, "height": 30},
        "solidworks_sketch_circle": {"radius": 25},
        "solidworks_sketch_line": {"x1": 0, "y1": 0, "x2": 50, "y2": 50},
        "solidworks_sketch_centerline": {"x1": -50, "y1": 0, "x2": 50, "y2": 0},
        "solidworks_sketch_arc": {"mode": "3point", "x1": 0, "y1": 0, "x2": 50, "y2": 0, "x3": 25, "y3": 25},
        "solidworks_sketch_spline": {"points": [{"x": 0, "y": 0}, {"x": 50, "y": 50}]},
        "solidworks_sketch_ellipse": {"centerX": 0, "centerY": 0, "majorRadius": 30, "minorRadius": 20},
        "solidworks_sketch_polygon": {"radius": 25, "numSides": 6},
        "solidworks_sketch_slot": {"x1": -25, "y1": 0, "x2": 25, "y2": 0, "width": 20},
        "solidworks_sketch_point": {"x": 10, "y": 10},
        "solidworks_sketch_text": {"x": 0, "y": 0, "text": "Hello", "height": 5},
        "solidworks_sketch_constraint": {"constraintType": "HORIZONTAL",
                                          "entityPoints": [{"x": 25, "y": 25}]},
        "solidworks_sketch_toggle_construction": {"x": 25, "y": 25},
        "solidworks_get_last_shape_info": {},
        "solidworks_exit_sketch": {},
    }

    failed = []
    for tool_name, args in tool_args.items():
        try:
            result = route_tool(sketching, modeling, tool_name, args)
            if not isinstance(result, str):
                failed.append(f"{tool_name}: returned {type(result)}, expected str")
        except Exception as e:
            failed.append(f"{tool_name}: {e}")

    if failed:
        for f in failed:
            log_error(f)
        return False

    log_success("All 16 sketching tools route correctly")
    return True


def test_modeling_tools_route():
    """All 4 modeling tool names dispatch through execute() without error"""
    _, sketching, modeling = fresh_tools()

    # new_part first, then sketch + extrude
    try:
        route_tool(sketching, modeling, "solidworks_new_part")
        route_tool(sketching, modeling, "solidworks_create_sketch", {"plane": "Front"})
        route_tool(sketching, modeling, "solidworks_sketch_rectangle", {"width": 100, "height": 100})
        route_tool(sketching, modeling, "solidworks_create_extrusion", {"depth": 100})

        # Cut extrusion (sketch is auto-created on face in real SW, but mock allows it)
        route_tool(sketching, modeling, "solidworks_create_sketch", {"plane": "Front"})
        route_tool(sketching, modeling, "solidworks_sketch_circle", {"radius": 20})
        route_tool(sketching, modeling, "solidworks_create_cut_extrusion", {"depth": 50})

        route_tool(sketching, modeling, "solidworks_get_mass_properties")
    except Exception as e:
        log_error(f"Modeling tool routing failed: {e}")
        return False

    log_success("All 4 modeling tools route correctly")
    return True


def test_unknown_tool_raises():
    """Unknown tool name raises Exception"""
    _, sketching, modeling = fresh_tools()
    try:
        route_tool(sketching, modeling, "solidworks_nonexistent_tool", {})
        log_error("Expected exception for unknown tool, got none")
        return False
    except Exception as e:
        if "Unknown tool" in str(e):
            log_success("Unknown tool raises Exception correctly")
            return True
        log_error(f"Wrong exception: {e}")
        return False


def test_tool_definitions_match_lists():
    """Tool definitions returned by modules match SKETCHING_TOOLS / MODELING_TOOLS"""
    from server import SolidWorksMCPServer
    _, sketching, modeling = fresh_tools()

    sketch_defs = {t.name for t in sketching.get_tool_definitions()}
    model_defs = {t.name for t in modeling.get_tool_definitions()}

    expected_sketch = set(SolidWorksMCPServer.SKETCHING_TOOLS)
    expected_model = set(SolidWorksMCPServer.MODELING_TOOLS)

    errors = []
    if sketch_defs != expected_sketch:
        errors.append(f"Sketch mismatch: defs={sketch_defs - expected_sketch}, "
                      f"missing={expected_sketch - sketch_defs}")
    if model_defs != expected_model:
        errors.append(f"Model mismatch: defs={model_defs - expected_model}, "
                      f"missing={expected_model - model_defs}")

    if errors:
        for e in errors:
            log_error(e)
        return False

    log_success("Tool definitions match SKETCHING_TOOLS / MODELING_TOOLS lists")
    return True


def test_sketching_execute_unknown_tool():
    """SketchingTools.execute() raises for unknown tool name"""
    _, sketching, _ = fresh_tools()
    try:
        sketching.execute("solidworks_fake_sketch_tool", {})
        log_error("Expected exception, got none")
        return False
    except Exception as e:
        if "Unknown" in str(e):
            log_success("SketchingTools.execute() raises for unknown tool")
            return True
        log_error(f"Wrong exception: {e}")
        return False


# ---------------------------------------------------------------------------
# Category 2: Parameter Validation
# ---------------------------------------------------------------------------

def test_line_missing_params():
    """sketch_line raises when missing required x1/y1/x2/y2"""
    _, sketching, _ = fresh_tools()
    for missing_key in ["x1", "y1", "x2", "y2"]:
        args = {"x1": 0, "y1": 0, "x2": 50, "y2": 50}
        del args[missing_key]
        try:
            sketching.execute("solidworks_sketch_line", args)
            log_error(f"Expected exception when missing {missing_key}")
            return False
        except Exception:
            pass
    log_success("sketch_line validates required params")
    return True


def test_circle_missing_radius():
    """sketch_circle raises when missing radius"""
    _, sketching, _ = fresh_tools()
    try:
        sketching.execute("solidworks_sketch_circle", {})
        log_error("Expected exception for missing radius")
        return False
    except Exception:
        log_success("sketch_circle validates radius is required")
        return True


def test_ellipse_missing_params():
    """sketch_ellipse raises when missing required params"""
    _, sketching, _ = fresh_tools()
    required = ["centerX", "centerY", "majorRadius", "minorRadius"]
    for missing in required:
        args = {"centerX": 0, "centerY": 0, "majorRadius": 30, "minorRadius": 20}
        del args[missing]
        try:
            sketching.execute("solidworks_sketch_ellipse", args)
            log_error(f"Expected exception when missing {missing}")
            return False
        except Exception:
            pass
    log_success("sketch_ellipse validates required params")
    return True


def test_polygon_missing_params():
    """sketch_polygon raises when missing radius or numSides"""
    _, sketching, _ = fresh_tools()
    for args in [{"numSides": 6}, {"radius": 25}]:
        try:
            sketching.execute("solidworks_sketch_polygon", args)
            log_error(f"Expected exception for args: {args}")
            return False
        except Exception:
            pass
    log_success("sketch_polygon validates required params")
    return True


def test_slot_missing_params():
    """sketch_slot raises when missing required params"""
    _, sketching, _ = fresh_tools()
    required = ["x1", "y1", "x2", "y2", "width"]
    for missing in required:
        args = {"x1": -25, "y1": 0, "x2": 25, "y2": 0, "width": 20}
        del args[missing]
        try:
            sketching.execute("solidworks_sketch_slot", args)
            log_error(f"Expected exception when missing {missing}")
            return False
        except Exception:
            pass
    log_success("sketch_slot validates required params")
    return True


def test_spline_too_few_points():
    """sketch_spline raises with fewer than 2 points"""
    _, sketching, _ = fresh_tools()
    try:
        sketching.execute("solidworks_sketch_spline", {"points": [{"x": 0, "y": 0}]})
        log_error("Expected exception for < 2 points")
        return False
    except Exception:
        log_success("sketch_spline validates min 2 points")
        return True


def test_point_missing_params():
    """sketch_point raises when missing x or y"""
    _, sketching, _ = fresh_tools()
    for args in [{"y": 10}, {"x": 10}]:
        try:
            sketching.execute("solidworks_sketch_point", args)
            log_error(f"Expected exception for args: {args}")
            return False
        except Exception:
            pass
    log_success("sketch_point validates required params")
    return True


def test_text_missing_params():
    """sketch_text raises when missing required params"""
    _, sketching, _ = fresh_tools()
    required = ["x", "y", "text", "height"]
    for missing in required:
        args = {"x": 0, "y": 0, "text": "Hi", "height": 5}
        del args[missing]
        try:
            sketching.execute("solidworks_sketch_text", args)
            log_error(f"Expected exception when missing {missing}")
            return False
        except Exception:
            pass
    log_success("sketch_text validates required params")
    return True


# ---------------------------------------------------------------------------
# Category 3: Spatial Tracking
# ---------------------------------------------------------------------------

def test_rectangle_updates_tracking():
    """Rectangle updates last_shape with correct fields"""
    _, sketching, _ = fresh_tools()
    sketching.execute("solidworks_sketch_rectangle", {"width": 80, "height": 60})

    ls = sketching.last_shape
    if ls is None:
        log_error("last_shape is None after rectangle")
        return False

    errors = []
    if ls["type"] != "rectangle":
        errors.append(f"type={ls['type']}, expected rectangle")
    if ls["width"] != 80:
        errors.append(f"width={ls['width']}, expected 80")
    if ls["height"] != 60:
        errors.append(f"height={ls['height']}, expected 60")
    if ls["centerX"] != 0:
        errors.append(f"centerX={ls['centerX']}, expected 0")
    if ls["centerY"] != 0:
        errors.append(f"centerY={ls['centerY']}, expected 0")
    if ls["left"] != -40:
        errors.append(f"left={ls['left']}, expected -40")
    if ls["right"] != 40:
        errors.append(f"right={ls['right']}, expected 40")
    if ls["bottom"] != -30:
        errors.append(f"bottom={ls['bottom']}, expected -30")
    if ls["top"] != 30:
        errors.append(f"top={ls['top']}, expected 30")

    if errors:
        for e in errors:
            log_error(e)
        return False

    log_success("Rectangle spatial tracking correct")
    return True


def test_circle_updates_tracking():
    """Circle updates last_shape with correct fields"""
    _, sketching, _ = fresh_tools()
    sketching.execute("solidworks_sketch_circle", {"radius": 25})

    ls = sketching.last_shape
    if ls is None:
        log_error("last_shape is None after circle")
        return False

    errors = []
    if ls["type"] != "circle":
        errors.append(f"type={ls['type']}")
    if ls["radius"] != 25:
        errors.append(f"radius={ls['radius']}")
    if ls["centerX"] != 0:
        errors.append(f"centerX={ls['centerX']}")
    if ls["left"] != -25:
        errors.append(f"left={ls['left']}")
    if ls["right"] != 25:
        errors.append(f"right={ls['right']}")

    if errors:
        for e in errors:
            log_error(e)
        return False

    log_success("Circle spatial tracking correct")
    return True


def test_line_updates_tracking():
    """Line updates last_shape with correct fields"""
    _, sketching, _ = fresh_tools()
    sketching.execute("solidworks_sketch_line", {"x1": 10, "y1": 20, "x2": 60, "y2": 80})

    ls = sketching.last_shape
    if ls is None:
        log_error("last_shape is None after line")
        return False

    errors = []
    if ls["type"] != "line":
        errors.append(f"type={ls['type']}")
    if ls["centerX"] != 35:
        errors.append(f"centerX={ls['centerX']}, expected 35")
    if ls["centerY"] != 50:
        errors.append(f"centerY={ls['centerY']}, expected 50")
    if ls["x1"] != 10 or ls["y1"] != 20:
        errors.append(f"start=({ls['x1']},{ls['y1']}), expected (10,20)")
    if ls["x2"] != 60 or ls["y2"] != 80:
        errors.append(f"end=({ls['x2']},{ls['y2']}), expected (60,80)")

    if errors:
        for e in errors:
            log_error(e)
        return False

    log_success("Line spatial tracking correct")
    return True


def test_point_does_not_update_tracking():
    """Point does NOT update last_shape"""
    _, sketching, _ = fresh_tools()
    # Draw a rectangle first to set last_shape
    sketching.execute("solidworks_sketch_rectangle", {"width": 50, "height": 50})
    prev_shape = sketching.last_shape

    # Draw a point
    sketching.execute("solidworks_sketch_point", {"x": 100, "y": 100})

    if sketching.last_shape is not prev_shape:
        log_error("Point changed last_shape (should not)")
        return False

    log_success("Point does not update spatial tracking")
    return True


def test_centerline_does_not_update_tracking():
    """Centerline does NOT update last_shape"""
    _, sketching, _ = fresh_tools()
    sketching.execute("solidworks_sketch_rectangle", {"width": 50, "height": 50})
    prev_shape = sketching.last_shape

    sketching.execute("solidworks_sketch_centerline", {"x1": -50, "y1": 0, "x2": 50, "y2": 0})

    if sketching.last_shape is not prev_shape:
        log_error("Centerline changed last_shape (should not)")
        return False

    log_success("Centerline does not update spatial tracking")
    return True


def test_text_does_not_update_tracking():
    """Text does NOT update last_shape"""
    _, sketching, _ = fresh_tools()
    sketching.execute("solidworks_sketch_rectangle", {"width": 50, "height": 50})
    prev_shape = sketching.last_shape

    sketching.execute("solidworks_sketch_text", {"x": 0, "y": 0, "text": "Test", "height": 5})

    if sketching.last_shape is not prev_shape:
        log_error("Text changed last_shape (should not)")
        return False

    log_success("Text does not update spatial tracking")
    return True


def test_get_last_shape_info_no_shapes():
    """get_last_shape_info returns error message when no shapes exist"""
    _, sketching, _ = fresh_tools()
    result = sketching.execute("solidworks_get_last_shape_info", {})

    if "No shapes" not in result:
        log_error(f"Expected 'No shapes' message, got: {result}")
        return False

    log_success("get_last_shape_info handles no shapes correctly")
    return True


def test_created_shapes_list_grows():
    """created_shapes list grows with each shape-tracking entity"""
    _, sketching, _ = fresh_tools()

    sketching.execute("solidworks_sketch_rectangle", {"width": 50, "height": 50})
    if len(sketching.created_shapes) != 1:
        log_error(f"Expected 1, got {len(sketching.created_shapes)}")
        return False

    sketching.execute("solidworks_sketch_circle", {"radius": 25, "centerX": 100, "centerY": 0})
    if len(sketching.created_shapes) != 2:
        log_error(f"Expected 2, got {len(sketching.created_shapes)}")
        return False

    # Point should NOT add to list
    sketching.execute("solidworks_sketch_point", {"x": 0, "y": 0})
    if len(sketching.created_shapes) != 2:
        log_error(f"Expected still 2 after point, got {len(sketching.created_shapes)}")
        return False

    sketching.execute("solidworks_sketch_line", {"x1": 0, "y1": 0, "x2": 50, "y2": 50})
    if len(sketching.created_shapes) != 3:
        log_error(f"Expected 3, got {len(sketching.created_shapes)}")
        return False

    log_success("created_shapes list grows correctly")
    return True


# ---------------------------------------------------------------------------
# Category 4: Positioning Priority
# ---------------------------------------------------------------------------

def test_default_position_origin():
    """Default position is (0, 0) with no args and no last_shape"""
    _, sketching, _ = fresh_tools()
    x, y = sketching._calculate_position({}, 50, 30)

    if x != 0 or y != 0:
        log_error(f"Default position ({x}, {y}), expected (0, 0)")
        return False

    log_success("Default position is (0, 0)")
    return True


def test_absolute_position():
    """centerX/centerY provides absolute positioning"""
    _, sketching, _ = fresh_tools()
    x, y = sketching._calculate_position({"centerX": 100, "centerY": -50}, 50, 30)

    if x != 100 or y != -50:
        log_error(f"Absolute position ({x}, {y}), expected (100, -50)")
        return False

    log_success("Absolute positioning works correctly")
    return True


def test_spacing_position():
    """spacing calculates from last shape's right edge"""
    _, sketching, _ = fresh_tools()

    # Create a rectangle to set last_shape
    sketching.execute("solidworks_sketch_rectangle", {"width": 80, "height": 60})
    # last_shape: right=40, centerY=0

    # spacing=10 from right edge, new shape width=40
    # expected: center_x = 40 + 10 + 20 = 70, center_y = 0
    x, y = sketching._calculate_position({"spacing": 10}, 40, 30)

    if x != 70 or y != 0:
        log_error(f"Spacing position ({x}, {y}), expected (70, 0)")
        return False

    log_success("Spacing positioning works correctly")
    return True


def test_relative_position():
    """relativeX/relativeY offsets from last shape's center"""
    _, sketching, _ = fresh_tools()

    # Create shape at origin
    sketching.execute("solidworks_sketch_rectangle", {"width": 80, "height": 60})
    # last_shape: centerX=0, centerY=0

    x, y = sketching._calculate_position({"relativeX": 30, "relativeY": -20}, 40, 30)

    if x != 30 or y != -20:
        log_error(f"Relative position ({x}, {y}), expected (30, -20)")
        return False

    log_success("Relative positioning works correctly")
    return True


def test_position_priority_order():
    """Priority: absolute > spacing > relative > default"""
    _, sketching, _ = fresh_tools()

    # Set up a last_shape for spacing/relative to work
    sketching.execute("solidworks_sketch_rectangle", {"width": 80, "height": 60})
    # last_shape: centerX=0, centerY=0, right=40

    # All positioning args present — absolute should win
    args_all = {
        "centerX": 200, "centerY": 100,
        "spacing": 10,
        "relativeX": 30, "relativeY": -20,
    }
    x, y = sketching._calculate_position(args_all, 40, 30)
    if x != 200 or y != 100:
        log_error(f"Absolute priority failed: ({x}, {y}), expected (200, 100)")
        return False

    # spacing + relative — spacing should win
    args_spacing_relative = {
        "spacing": 10,
        "relativeX": 30, "relativeY": -20,
    }
    x, y = sketching._calculate_position(args_spacing_relative, 40, 30)
    expected_x = 40 + 10 + 20  # right + spacing + half_width
    if x != expected_x or y != 0:
        log_error(f"Spacing priority failed: ({x}, {y}), expected ({expected_x}, 0)")
        return False

    log_success("Positioning priority order is correct")
    return True


# ---------------------------------------------------------------------------
# Category 5: Agent Workflow Simulation
# ---------------------------------------------------------------------------

def test_full_workflow_sequence():
    """Simulate: new_part -> create_sketch -> rectangle -> exit_sketch -> extrusion"""
    _, sketching, modeling = fresh_tools()

    try:
        r1 = route_tool(sketching, modeling, "solidworks_new_part")
        assert "✓" in r1, f"new_part: {r1}"

        r2 = route_tool(sketching, modeling, "solidworks_create_sketch", {"plane": "Front"})
        assert "✓" in r2, f"create_sketch: {r2}"

        r3 = route_tool(sketching, modeling, "solidworks_sketch_rectangle",
                         {"width": 100, "height": 100})
        assert "✓" in r3, f"sketch_rectangle: {r3}"

        r4 = route_tool(sketching, modeling, "solidworks_exit_sketch")
        assert "✓" in r4, f"exit_sketch: {r4}"

        r5 = route_tool(sketching, modeling, "solidworks_create_extrusion", {"depth": 100})
        assert "✓" in r5, f"create_extrusion: {r5}"
    except Exception as e:
        log_error(f"Full workflow failed: {e}")
        return False

    log_success("Full agent workflow (new_part→sketch→rect→exit→extrude) succeeds")
    return True


def test_multi_shape_with_spacing():
    """Rectangle + circle with spacing, verify positions"""
    _, sketching, _ = fresh_tools()

    sketching.execute("solidworks_sketch_rectangle", {"width": 80, "height": 60})
    # rect: centerX=0, right=40

    sketching.execute("solidworks_sketch_circle", {"radius": 20, "spacing": 10})
    # circle center: right(40) + spacing(10) + radius(20) = 70

    ls = sketching.last_shape
    if ls is None:
        log_error("No last_shape after circle")
        return False

    if ls["type"] != "circle":
        log_error(f"Expected circle, got {ls['type']}")
        return False

    if ls["centerX"] != 70:
        log_error(f"Circle centerX={ls['centerX']}, expected 70")
        return False

    if ls["centerY"] != 0:
        log_error(f"Circle centerY={ls['centerY']}, expected 0")
        return False

    log_success("Multi-shape with spacing positions correctly")
    return True


def test_get_last_shape_info_after_creation():
    """get_last_shape_info returns formatted info after shape creation"""
    _, sketching, _ = fresh_tools()

    sketching.execute("solidworks_sketch_rectangle", {"width": 100, "height": 60})
    result = sketching.execute("solidworks_get_last_shape_info", {})

    checks = ["rectangle", "Center:", "Bounds:", "100"]
    for check in checks:
        if check not in result:
            log_error(f"Expected '{check}' in shape info, got: {result}")
            return False

    log_success("get_last_shape_info returns formatted info")
    return True


def test_sketch_counter_increments():
    """Sketch counter increments across multiple sketches"""
    _, sketching, _ = fresh_tools()

    if sketching.sketch_counter != 0:
        log_error(f"Initial counter={sketching.sketch_counter}, expected 0")
        return False

    sketching.execute("solidworks_create_sketch", {"plane": "Front"})
    if sketching.sketch_counter != 1:
        log_error(f"After 1st sketch: counter={sketching.sketch_counter}, expected 1")
        return False

    if sketching.current_sketch_name != "Sketch1":
        log_error(f"Name={sketching.current_sketch_name}, expected Sketch1")
        return False

    sketching.execute("solidworks_create_sketch", {"plane": "Top"})
    if sketching.sketch_counter != 2:
        log_error(f"After 2nd sketch: counter={sketching.sketch_counter}, expected 2")
        return False

    if sketching.current_sketch_name != "Sketch2":
        log_error(f"Name={sketching.current_sketch_name}, expected Sketch2")
        return False

    log_success("Sketch counter increments correctly")
    return True


# ---------------------------------------------------------------------------
# Category 6: Error Handling
# ---------------------------------------------------------------------------

def test_unknown_arc_mode():
    """Unknown arc mode raises Exception"""
    _, sketching, _ = fresh_tools()
    try:
        sketching.execute("solidworks_sketch_arc",
                          {"mode": "invalid", "x1": 0, "y1": 0, "x2": 50, "y2": 0})
        log_error("Expected exception for invalid arc mode")
        return False
    except Exception as e:
        if "Unknown arc mode" in str(e):
            log_success("Unknown arc mode raises correctly")
            return True
        log_error(f"Wrong exception: {e}")
        return False


def test_unknown_constraint_type():
    """Unknown constraint type raises Exception"""
    _, sketching, _ = fresh_tools()
    try:
        sketching.execute("solidworks_sketch_constraint",
                          {"constraintType": "INVALID", "entityPoints": [{"x": 0, "y": 0}]})
        log_error("Expected exception for invalid constraint type")
        return False
    except Exception as e:
        if "Unknown constraint type" in str(e):
            log_success("Unknown constraint type raises correctly")
            return True
        log_error(f"Wrong exception: {e}")
        return False


def test_rectangle_missing_both_param_styles():
    """sketch_rectangle with neither width/height nor x1/y1/x2/y2 raises"""
    _, sketching, _ = fresh_tools()
    try:
        sketching.execute("solidworks_sketch_rectangle", {})
        log_error("Expected exception for missing rect params")
        return False
    except Exception as e:
        if "Must provide" in str(e):
            log_success("Rectangle validates parameter styles")
            return True
        log_error(f"Wrong exception: {e}")
        return False


def test_no_active_doc_raises():
    """Operations on no active document raise Exception"""
    from solidworks.sketching import SketchingTools

    conn = MockConnection()
    conn._doc = None  # No active document
    sketching = SketchingTools(conn)

    try:
        sketching.execute("solidworks_sketch_rectangle", {"width": 50, "height": 50})
        log_error("Expected exception for no active document")
        return False
    except Exception as e:
        if "No active document" in str(e):
            log_success("No active document raises correctly")
            return True
        log_error(f"Wrong exception: {e}")
        return False


# ---------------------------------------------------------------------------
# Category 7: Spatial Tracking for Additional Entities
# ---------------------------------------------------------------------------

def test_arc_3point_updates_tracking():
    """3-point arc updates last_shape"""
    _, sketching, _ = fresh_tools()
    sketching.execute("solidworks_sketch_arc", {
        "mode": "3point",
        "x1": 0, "y1": 0, "x2": 50, "y2": 0, "x3": 25, "y3": 25
    })
    ls = sketching.last_shape
    if ls is None or ls["type"] != "arc":
        log_error(f"Expected arc, got {ls}")
        return False
    log_success("3-point arc updates spatial tracking")
    return True


def test_arc_center_updates_tracking():
    """Center-point arc updates last_shape with radius"""
    _, sketching, _ = fresh_tools()
    sketching.execute("solidworks_sketch_arc", {
        "mode": "center",
        "centerX": 0, "centerY": 0, "x1": 25, "y1": 0, "x2": 0, "y2": 25
    })
    ls = sketching.last_shape
    if ls is None or ls["type"] != "arc":
        log_error(f"Expected arc, got {ls}")
        return False
    if "radius" not in ls:
        log_error("Center arc missing radius in last_shape")
        return False
    if abs(ls["radius"] - 25) > 0.01:
        log_error(f"radius={ls['radius']}, expected 25")
        return False
    log_success("Center-point arc updates spatial tracking with radius")
    return True


def test_polygon_updates_tracking():
    """Polygon updates last_shape"""
    _, sketching, _ = fresh_tools()
    sketching.execute("solidworks_sketch_polygon", {"radius": 30, "numSides": 6})
    ls = sketching.last_shape
    if ls is None or ls["type"] != "polygon":
        log_error(f"Expected polygon, got {ls}")
        return False
    if ls["numSides"] != 6:
        log_error(f"numSides={ls['numSides']}, expected 6")
        return False
    if ls["radius"] != 30:
        log_error(f"radius={ls['radius']}, expected 30")
        return False
    log_success("Polygon spatial tracking correct")
    return True


def test_ellipse_updates_tracking():
    """Ellipse updates last_shape"""
    _, sketching, _ = fresh_tools()
    sketching.execute("solidworks_sketch_ellipse", {
        "centerX": 10, "centerY": 20, "majorRadius": 30, "minorRadius": 15
    })
    ls = sketching.last_shape
    if ls is None or ls["type"] != "ellipse":
        log_error(f"Expected ellipse, got {ls}")
        return False
    if ls["majorRadius"] != 30 or ls["minorRadius"] != 15:
        log_error(f"radii={ls['majorRadius']},{ls['minorRadius']}, expected 30,15")
        return False
    log_success("Ellipse spatial tracking correct")
    return True


def test_slot_updates_tracking():
    """Slot updates last_shape"""
    _, sketching, _ = fresh_tools()
    sketching.execute("solidworks_sketch_slot", {
        "x1": -25, "y1": 0, "x2": 25, "y2": 0, "width": 20
    })
    ls = sketching.last_shape
    if ls is None or ls["type"] != "slot":
        log_error(f"Expected slot, got {ls}")
        return False
    if ls["centerX"] != 0 or ls["centerY"] != 0:
        log_error(f"center=({ls['centerX']},{ls['centerY']}), expected (0,0)")
        return False
    log_success("Slot spatial tracking correct")
    return True


def test_spline_updates_tracking():
    """Spline updates last_shape"""
    _, sketching, _ = fresh_tools()
    sketching.execute("solidworks_sketch_spline", {
        "points": [{"x": 0, "y": 0}, {"x": 50, "y": 30}, {"x": 100, "y": 0}]
    })
    ls = sketching.last_shape
    if ls is None or ls["type"] != "spline":
        log_error(f"Expected spline, got {ls}")
        return False
    if ls["centerX"] != 50 or ls["centerY"] != 15:
        log_error(f"center=({ls['centerX']},{ls['centerY']}), expected (50,15)")
        return False
    log_success("Spline spatial tracking correct")
    return True


# ---------------------------------------------------------------------------
# Category 8: Tool Return Messages
# ---------------------------------------------------------------------------

def test_success_messages_contain_checkmark():
    """All shape tools return messages with checkmark"""
    _, sketching, _ = fresh_tools()

    tools_and_args = [
        ("solidworks_sketch_rectangle", {"width": 50, "height": 30}),
        ("solidworks_sketch_circle", {"radius": 20}),
        ("solidworks_sketch_line", {"x1": 0, "y1": 0, "x2": 50, "y2": 50}),
        ("solidworks_sketch_centerline", {"x1": -50, "y1": 0, "x2": 50, "y2": 0}),
        ("solidworks_sketch_point", {"x": 10, "y": 10}),
        ("solidworks_sketch_polygon", {"radius": 25, "numSides": 6}),
        ("solidworks_sketch_ellipse", {"centerX": 0, "centerY": 0, "majorRadius": 30, "minorRadius": 20}),
        ("solidworks_sketch_slot", {"x1": -25, "y1": 0, "x2": 25, "y2": 0, "width": 20}),
    ]

    for tool_name, args in tools_and_args:
        result = sketching.execute(tool_name, args)
        if "✓" not in result:
            log_error(f"{tool_name} missing checkmark: {result}")
            return False

    log_success("All shape tools return checkmark messages")
    return True


def test_create_sketch_returns_plane_info():
    """create_sketch return message includes plane name"""
    _, sketching, _ = fresh_tools()
    for plane in ["Front", "Top", "Right"]:
        result = sketching.execute("solidworks_create_sketch", {"plane": plane})
        if plane not in result:
            log_error(f"Missing plane name '{plane}' in: {result}")
            return False

    log_success("create_sketch returns plane info in message")
    return True


# ---------------------------------------------------------------------------
# Category 9: Mass Properties Through MCP Interface
# ---------------------------------------------------------------------------

def test_mass_properties_format():
    """get_mass_properties returns formatted string with expected fields"""
    _, sketching, modeling = fresh_tools()

    result = route_tool(sketching, modeling, "solidworks_get_mass_properties")

    expected_fields = ["Mass Properties:", "Mass:", "Volume:", "Surface Area:",
                       "Center of Mass:", "Moments of Inertia"]
    for field in expected_fields:
        if field not in result:
            log_error(f"Missing '{field}' in mass properties output")
            return False

    # Check volume ~ 1,000,000 mm^3 (from mock)
    if "1000000" not in result:
        log_error(f"Expected volume ~1000000 in output: {result}")
        return False

    log_success("Mass properties format is correct")
    return True


# ---------------------------------------------------------------------------
# Category 10: Shape Tracking Reset on New Sketch
# ---------------------------------------------------------------------------

def test_new_sketch_resets_tracking():
    """Creating a new sketch resets last_shape and created_shapes"""
    _, sketching, _ = fresh_tools()

    # Draw some shapes
    sketching.execute("solidworks_sketch_rectangle", {"width": 50, "height": 50})
    sketching.execute("solidworks_sketch_circle", {"radius": 20, "centerX": 100, "centerY": 0})

    if len(sketching.created_shapes) != 2:
        log_error(f"Expected 2 shapes before reset, got {len(sketching.created_shapes)}")
        return False

    # Create a new sketch — should reset tracking
    sketching.execute("solidworks_create_sketch", {"plane": "Top"})

    if sketching.last_shape is not None:
        log_error("last_shape should be None after new sketch")
        return False
    if len(sketching.created_shapes) != 0:
        log_error(f"created_shapes should be empty, got {len(sketching.created_shapes)}")
        return False

    log_success("New sketch resets spatial tracking")
    return True


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_all_tests():
    """Run all mock-based tests and report results"""
    print("=" * 70)
    print("AI Agent Mock Test Suite for SolidWorks MCP")
    print("=" * 70)

    categories = [
        ("Tool Routing", [
            test_sketching_tools_route,
            test_modeling_tools_route,
            test_unknown_tool_raises,
            test_tool_definitions_match_lists,
            test_sketching_execute_unknown_tool,
        ]),
        ("Parameter Validation", [
            test_line_missing_params,
            test_circle_missing_radius,
            test_ellipse_missing_params,
            test_polygon_missing_params,
            test_slot_missing_params,
            test_spline_too_few_points,
            test_point_missing_params,
            test_text_missing_params,
        ]),
        ("Spatial Tracking", [
            test_rectangle_updates_tracking,
            test_circle_updates_tracking,
            test_line_updates_tracking,
            test_point_does_not_update_tracking,
            test_centerline_does_not_update_tracking,
            test_text_does_not_update_tracking,
            test_get_last_shape_info_no_shapes,
            test_created_shapes_list_grows,
        ]),
        ("Positioning Priority", [
            test_default_position_origin,
            test_absolute_position,
            test_spacing_position,
            test_relative_position,
            test_position_priority_order,
        ]),
        ("Agent Workflow Simulation", [
            test_full_workflow_sequence,
            test_multi_shape_with_spacing,
            test_get_last_shape_info_after_creation,
            test_sketch_counter_increments,
        ]),
        ("Error Handling", [
            test_unknown_arc_mode,
            test_unknown_constraint_type,
            test_rectangle_missing_both_param_styles,
            test_no_active_doc_raises,
        ]),
        ("Additional Entity Tracking", [
            test_arc_3point_updates_tracking,
            test_arc_center_updates_tracking,
            test_polygon_updates_tracking,
            test_ellipse_updates_tracking,
            test_slot_updates_tracking,
            test_spline_updates_tracking,
        ]),
        ("Tool Return Messages", [
            test_success_messages_contain_checkmark,
            test_create_sketch_returns_plane_info,
        ]),
        ("Mass Properties", [
            test_mass_properties_format,
        ]),
        ("Tracking Reset", [
            test_new_sketch_resets_tracking,
        ]),
    ]

    total_pass = 0
    total_fail = 0
    failed_tests = []

    for category_name, tests in categories:
        print(f"\n--- {category_name} ---")
        for test_fn in tests:
            test_name = test_fn.__name__
            try:
                passed = test_fn()
                if passed:
                    total_pass += 1
                else:
                    total_fail += 1
                    failed_tests.append(test_name)
            except Exception as e:
                total_fail += 1
                failed_tests.append(test_name)
                log_error(f"{test_name} raised unexpected exception: {e}")
                traceback.print_exc()

    total = total_pass + total_fail
    print(f"\n{'=' * 70}")
    print(f"Results: {total_pass}/{total} tests passed")

    if failed_tests:
        print(f"\nFailed tests:")
        for name in failed_tests:
            print(f"  - {name}")

    print(f"{'=' * 70}")
    return total_fail == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
