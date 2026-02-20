"""
Test script for SolidWorks - combining working methods
"""

import win32com.client
import pythoncom
import glob
import sys
import traceback


def log(message, level="INFO"):
    prefix = "✓" if level == "SUCCESS" else "❌" if level == "ERROR" else "→"
    print(f"{prefix} {message}")


def find_template():
    patterns = [
        r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS *\templates\Part.prtdot",
        r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS *\templates\Part.PRTDOT",
    ]
    for pattern in patterns:
        templates = glob.glob(pattern)
        if templates:
            return templates[0]
    return None


def test_solidworks():
    try:
        log("="*60)
        log("SolidWorks MCP Test Suite")
        log("="*60)
        
        log("\n1. Initializing COM...")
        pythoncom.CoInitialize()
        log("OK", "SUCCESS")
        
        log("\n2. Connecting to SolidWorks...")
        sw = win32com.client.Dispatch("SldWorks.Application")
        sw.Visible = True
        log(f"OK - Version {sw.RevisionNumber}", "SUCCESS")
        
        log("\n3. Finding template...")
        template = find_template()
        if not template:
            log("No template found", "ERROR")
            return False
        log("OK", "SUCCESS")
        
        log("\n4. Creating part...")
        model = sw.NewDocument(template, 0, 0, 0)
        log("OK", "SUCCESS")
        
        log("\n5. Selecting Front Plane...")
        # Use FeatureByName instead of SelectByID2 (this works!)
        front_plane = model.FeatureByName("Front Plane")
        model.ClearSelection2(True)
        front_plane.Select2(False, 0)
        log("OK", "SUCCESS")
        
        log("\n6. Creating sketch...")
        model.SketchManager.InsertSketch(True)
        log("OK", "SUCCESS")
        
        log("\n7. Drawing rectangle (100mm x 100mm)...")
        model.SketchManager.CreateCornerRectangle(0.0, 0.0, 0.0, 0.1, 0.1, 0.0)
        log("OK", "SUCCESS")
        
        log("\n8. Exiting sketch...")
        model.ClearSelection2(True)
        model.SketchManager.InsertSketch(True)
        log("OK", "SUCCESS")
        
        log("\n9. Selecting sketch for extrusion...")
        # Use FeatureByName for sketch too
        sketch1 = model.FeatureByName("Sketch1")
        model.ClearSelection2(True)
        sketch1.Select2(False, 0)
        log("OK", "SUCCESS")
        
        log("\n10. Creating extrusion (100mm)...")
        # 23 parameters from the recorded macro
        myFeature = model.FeatureManager.FeatureExtrusion2(
            True,      # Sd
            False,     # Flip
            False,     # Dir
            0,         # T1
            0,         # T2
            0.1,       # D1 (100mm in meters)
            0.0,       # D2
            False,     # DDir
            False,     # Dang
            False,     # OffsetReverse1
            False,     # OffsetReverse2
            0.0,       # Dang1
            0.0,       # Dang2
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
        
        if not myFeature:
            log("Extrusion returned None", "ERROR")
            return False
        
        log("OK", "SUCCESS")
        
        log("\n11. Adjusting view...")
        model.ViewZoomtofit2()
        log("OK", "SUCCESS")
        
        log("\n" + "="*60)
        log("ALL TESTS PASSED! 🎉", "SUCCESS")
        log("="*60)
        log("\nCheck SolidWorks - you should see a 100mm cube!")
        
        return True
        
    except Exception as e:
        log(f"\nERROR: {e}", "ERROR")
        traceback.print_exc()
        return False


def new_sketch_on_front(sw, template):
    """Helper: create a new part and open a sketch on the Front Plane."""
    model = sw.NewDocument(template, 0, 0, 0)
    front_plane = model.FeatureByName("Front Plane")
    model.ClearSelection2(True)
    front_plane.Select2(False, 0)
    model.SketchManager.InsertSketch(True)
    return model


def exit_sketch(model):
    """Helper: exit the active sketch."""
    model.ClearSelection2(True)
    model.SketchManager.InsertSketch(True)


def test_sketch_line(sw, template):
    """Test: draw a line from (0,0) to (50,50)."""
    try:
        log("\n--- Test: sketch_line ---")
        model = new_sketch_on_front(sw, template)
        model.SketchManager.CreateLine(0.0, 0.0, 0.0, 0.05, 0.05, 0.0)
        log("Line created", "SUCCESS")
        exit_sketch(model)
        model.ViewZoomtofit2()
        return True
    except Exception as e:
        log(f"sketch_line FAILED: {e}", "ERROR")
        return False


def test_sketch_centerline(sw, template):
    """Test: draw a centerline."""
    try:
        log("\n--- Test: sketch_centerline ---")
        model = new_sketch_on_front(sw, template)
        model.SketchManager.CreateCenterLine(0.0, -0.05, 0.0, 0.0, 0.05, 0.0)
        log("Centerline created", "SUCCESS")
        exit_sketch(model)
        model.ViewZoomtofit2()
        return True
    except Exception as e:
        log(f"sketch_centerline FAILED: {e}", "ERROR")
        return False


def test_sketch_point(sw, template):
    """Test: create a sketch point."""
    try:
        log("\n--- Test: sketch_point ---")
        model = new_sketch_on_front(sw, template)
        model.SketchManager.CreatePoint(0.025, 0.025, 0.0)
        log("Point created", "SUCCESS")
        exit_sketch(model)
        model.ViewZoomtofit2()
        return True
    except Exception as e:
        log(f"sketch_point FAILED: {e}", "ERROR")
        return False


def test_sketch_arc(sw, template):
    """Test: draw a 3-point arc and a center-point arc."""
    try:
        log("\n--- Test: sketch_arc ---")
        model = new_sketch_on_front(sw, template)

        # 3-point arc: start (0,0), end (0.05,0), midpoint (0.025,0.02)
        model.SketchManager.Create3PointArc(
            0.0, 0.0, 0.0,
            0.05, 0.0, 0.0,
            0.025, 0.02, 0.0
        )
        log("3-point arc created", "SUCCESS")

        # Center-point arc: center (0,-0.03), start (0.02,-0.03), end (-0.02,-0.03)
        model.SketchManager.CreateArc(
            0.0, -0.03, 0.0,
            0.02, -0.03, 0.0,
            -0.02, -0.03, 0.0,
            1  # counter-clockwise
        )
        log("Center-point arc created", "SUCCESS")

        exit_sketch(model)
        model.ViewZoomtofit2()
        return True
    except Exception as e:
        log(f"sketch_arc FAILED: {e}", "ERROR")
        traceback.print_exc()
        return False


def test_sketch_polygon(sw, template):
    """Test: draw a hexagon and extrude it."""
    try:
        log("\n--- Test: sketch_polygon ---")
        model = new_sketch_on_front(sw, template)

        # Hexagon: center (0,0), vertex at (0.025,0), 6 sides, circumscribed
        model.SketchManager.CreatePolygon(
            0.0, 0.0, 0.0,
            0.025, 0.0, 0.0,
            6,
            False
        )
        log("Hexagon created", "SUCCESS")

        exit_sketch(model)

        # Extrude to verify closed profile
        sketch1 = model.FeatureByName("Sketch1")
        model.ClearSelection2(True)
        sketch1.Select2(False, 0)
        feat = model.FeatureManager.FeatureExtrusion2(
            True, False, False, 0, 0, 0.05, 0.0,
            False, False, False, False, 0.0, 0.0,
            False, False, False, False, True, True, True,
            0, 0, False
        )
        if not feat:
            log("Polygon extrusion returned None", "ERROR")
            return False

        log("Hexagon extruded (50mm)", "SUCCESS")
        model.ViewZoomtofit2()
        return True
    except Exception as e:
        log(f"sketch_polygon FAILED: {e}", "ERROR")
        traceback.print_exc()
        return False


def test_sketch_ellipse(sw, template):
    """Test: draw an ellipse and extrude it."""
    try:
        log("\n--- Test: sketch_ellipse ---")
        model = new_sketch_on_front(sw, template)

        import math
        cx_m, cy_m = 0.0, 0.0
        major_r_m = 0.03  # 30mm
        minor_r_m = 0.02  # 20mm
        angle = 0.0

        major_x = cx_m + major_r_m * math.cos(angle)
        major_y = cy_m + major_r_m * math.sin(angle)
        minor_x = cx_m + minor_r_m * math.cos(angle + math.pi / 2)
        minor_y = cy_m + minor_r_m * math.sin(angle + math.pi / 2)

        model.SketchManager.CreateEllipse(
            cx_m, cy_m, 0.0,
            major_x, major_y, 0.0,
            minor_x, minor_y, 0.0
        )
        log("Ellipse created (30x20mm)", "SUCCESS")

        exit_sketch(model)

        sketch1 = model.FeatureByName("Sketch1")
        model.ClearSelection2(True)
        sketch1.Select2(False, 0)
        feat = model.FeatureManager.FeatureExtrusion2(
            True, False, False, 0, 0, 0.04, 0.0,
            False, False, False, False, 0.0, 0.0,
            False, False, False, False, True, True, True,
            0, 0, False
        )
        if not feat:
            log("Ellipse extrusion returned None", "ERROR")
            return False

        log("Ellipse extruded (40mm)", "SUCCESS")
        model.ViewZoomtofit2()
        return True
    except Exception as e:
        log(f"sketch_ellipse FAILED: {e}", "ERROR")
        traceback.print_exc()
        return False


def test_sketch_slot(sw, template):
    """Test: draw a slot and extrude it."""
    try:
        log("\n--- Test: sketch_slot ---")
        model = new_sketch_on_front(sw, template)

        # Slot: from (-25,0) to (25,0), width 20mm
        model.SketchManager.CreateSketchSlot(
            0, 0,              # slotType=straight, lengthType=center-center
            0.02,              # width = 20mm in meters
            -0.025, 0.0, 0.0, # first center
            0.025, 0.0, 0.0,  # second center
            0.0, 0.0, 0.0,    # third point (unused for straight)
            1,                 # centerArcDirection
            False              # addDimension
        )
        log("Slot created (50mm long, 20mm wide)", "SUCCESS")

        exit_sketch(model)

        sketch1 = model.FeatureByName("Sketch1")
        model.ClearSelection2(True)
        sketch1.Select2(False, 0)
        feat = model.FeatureManager.FeatureExtrusion2(
            True, False, False, 0, 0, 0.01, 0.0,
            False, False, False, False, 0.0, 0.0,
            False, False, False, False, True, True, True,
            0, 0, False
        )
        if not feat:
            log("Slot extrusion returned None", "ERROR")
            return False

        log("Slot extruded (10mm)", "SUCCESS")
        model.ViewZoomtofit2()
        return True
    except Exception as e:
        log(f"sketch_slot FAILED: {e}", "ERROR")
        traceback.print_exc()
        return False


def test_sketch_spline(sw, template):
    """Test: draw a spline through 4 points."""
    try:
        log("\n--- Test: sketch_spline ---")
        model = new_sketch_on_front(sw, template)

        # Spline: 4 points forming a wave shape
        point_data = [
            0.0, 0.0, 0.0,
            0.02, 0.01, 0.0,
            0.04, -0.01, 0.0,
            0.06, 0.0, 0.0,
        ]
        point_array = win32com.client.VARIANT(
            pythoncom.VT_ARRAY | pythoncom.VT_R8, point_data
        )
        model.SketchManager.CreateSpline2(point_array, True)
        log("Spline created through 4 points", "SUCCESS")

        exit_sketch(model)
        model.ViewZoomtofit2()
        return True
    except Exception as e:
        log(f"sketch_spline FAILED: {e}", "ERROR")
        traceback.print_exc()
        return False


def test_sketch_text(sw, template):
    """Test: insert sketch text."""
    try:
        log("\n--- Test: sketch_text ---")
        model = new_sketch_on_front(sw, template)

        # InsertSketchText(Ptx, Pty, Ptz, Text, Alignment, FlipDirection,
        #                  HorizontalMirror, WidthFactor, SpaceBetweenChars)
        sketch_text_obj = model.InsertSketchText(
            0.0, 0.0, 0.0,   # position (meters)
            "HELLO",          # text string
            1,                # alignment: left
            0,                # flip direction
            0,                # horizontal mirror
            1,                # width factor
            0                 # space between chars
        )
        if not sketch_text_obj:
            log("InsertSketchText returned None", "ERROR")
            return False
        log("Sketch text 'HELLO' created", "SUCCESS")

        # Note: GetTextFormat/SetTextFormat for height/angle are not accessible
        # via pywin32 dynamic COM dispatch. The text is created with document
        # default formatting. Height can be set in SolidWorks GUI.

        exit_sketch(model)
        model.ViewZoomtofit2()
        return True
    except Exception as e:
        log(f"sketch_text FAILED: {e}", "ERROR")
        traceback.print_exc()
        return False


def test_sketch_dimension(sw, template):
    """Test: draw a rectangle and add a dimension to one edge."""
    try:
        log("\n--- Test: sketch_dimension ---")
        model = new_sketch_on_front(sw, template)

        # Draw a 50x30mm rectangle
        model.SketchManager.CreateCornerRectangle(0.0, 0.0, 0.0, 0.05, 0.03, 0.0)
        log("Rectangle drawn (50x30mm)", "SUCCESS")

        # Select the bottom edge (midpoint at 0.025, 0, 0) and add dimension
        callout = win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)
        model.ClearSelection2(True)
        ok = model.Extension.SelectByID2(
            "", "SKETCHSEGMENT",
            0.025, 0.0, 0.0,    # point on/near the bottom edge
            False, 0, callout, 0
        )
        if not ok:
            log("Could not select edge for dimension", "ERROR")
            return False

        # Suppress the "Modify Dimension" dialog (swInputDimValOnCreate = 86)
        original_pref = sw.GetUserPreferenceToggle(86)
        sw.SetUserPreferenceToggle(86, False)
        try:
            dim_display = model.AddDimension2(0.025, -0.01, 0.0)
        finally:
            sw.SetUserPreferenceToggle(86, original_pref)

        if not dim_display:
            log("AddDimension2 returned None", "ERROR")
            return False
        log("Dimension added to bottom edge", "SUCCESS")

        model.ClearSelection2(True)
        exit_sketch(model)
        model.ViewZoomtofit2()
        return True
    except Exception as e:
        log(f"sketch_dimension FAILED: {e}", "ERROR")
        traceback.print_exc()
        return False


def test_set_dimension_value(sw, template):
    """Test: draw a rectangle, dimension it, then change the dimension value."""
    try:
        log("\n--- Test: set_dimension_value ---")
        model = new_sketch_on_front(sw, template)

        # Draw a 50x30mm rectangle
        model.SketchManager.CreateCornerRectangle(0.0, 0.0, 0.0, 0.05, 0.03, 0.0)
        log("Rectangle drawn (50x30mm)", "SUCCESS")

        # Dimension the bottom edge (suppress dialog)
        callout = win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)
        model.ClearSelection2(True)
        model.Extension.SelectByID2(
            "", "SKETCHSEGMENT",
            0.025, 0.0, 0.0,
            False, 0, callout, 0
        )
        original_pref = sw.GetUserPreferenceToggle(86)
        sw.SetUserPreferenceToggle(86, False)
        try:
            dim_display = model.AddDimension2(0.025, -0.01, 0.0)
        finally:
            sw.SetUserPreferenceToggle(86, original_pref)

        if not dim_display:
            log("Could not add initial dimension", "ERROR")
            return False

        # Change the dimension value to 80mm
        dim = dim_display.GetDimension2(0)
        if not dim:
            log("Could not get Dimension object", "ERROR")
            return False

        dim.SetSystemValue3(0.08, 2, "")  # 80mm in meters
        model.ClearSelection2(True)
        model.ForceRebuild3(True)
        log("Dimension value changed to 80mm", "SUCCESS")

        exit_sketch(model)
        model.ViewZoomtofit2()
        return True
    except Exception as e:
        log(f"set_dimension_value FAILED: {e}", "ERROR")
        traceback.print_exc()
        return False


def test_sketch_constraint(sw, template):
    """Test: draw two lines and apply a parallel constraint."""
    try:
        log("\n--- Test: sketch_constraint ---")
        model = new_sketch_on_front(sw, template)

        # Draw two non-parallel lines
        model.SketchManager.CreateLine(0.0, 0.0, 0.0, 0.05, 0.02, 0.0)
        model.SketchManager.CreateLine(0.0, 0.03, 0.0, 0.05, 0.04, 0.0)
        log("Two lines drawn", "SUCCESS")

        # Select both lines and apply parallel constraint
        callout = win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)
        model.ClearSelection2(True)
        model.Extension.SelectByID2(
            "", "SKETCHSEGMENT",
            0.025, 0.01, 0.0,   # midpoint of first line
            False, 0, callout, 0
        )
        model.Extension.SelectByID2(
            "", "SKETCHSEGMENT",
            0.025, 0.035, 0.0,  # midpoint of second line
            True, 0, callout, 0  # append = True
        )
        model.SketchAddConstraints("sgPARALLEL")
        log("Parallel constraint applied", "SUCCESS")

        exit_sketch(model)
        model.ViewZoomtofit2()
        return True
    except Exception as e:
        log(f"sketch_constraint FAILED: {e}", "ERROR")
        traceback.print_exc()
        return False


def test_toggle_construction(sw, template):
    """Test: draw a line and toggle it to construction geometry."""
    try:
        log("\n--- Test: toggle_construction ---")
        model = new_sketch_on_front(sw, template)

        # Draw a line
        model.SketchManager.CreateLine(0.0, 0.0, 0.0, 0.05, 0.0, 0.0)
        log("Line drawn", "SUCCESS")

        # Select the line and toggle construction
        callout = win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)
        model.ClearSelection2(True)
        ok = model.Extension.SelectByID2(
            "", "SKETCHSEGMENT",
            0.025, 0.0, 0.0,
            False, 0, callout, 0
        )
        if not ok:
            log("Could not select line", "ERROR")
            return False

        sel_mgr = model.SelectionManager
        sketch_seg = sel_mgr.GetSelectedObject6(1, -1)
        was_construction = sketch_seg.ConstructionGeometry
        sketch_seg.ConstructionGeometry = not was_construction
        is_construction = sketch_seg.ConstructionGeometry

        if is_construction == was_construction:
            log("Construction flag did not toggle", "ERROR")
            return False

        log(f"Toggled: was {was_construction}, now {is_construction}", "SUCCESS")

        exit_sketch(model)
        model.ViewZoomtofit2()
        return True
    except Exception as e:
        log(f"toggle_construction FAILED: {e}", "ERROR")
        traceback.print_exc()
        return False


def test_mass_properties(sw, template):
    """Test: create a 100mm cube and verify mass properties."""
    try:
        log("\n--- Test: mass_properties ---")

        # Create part with a 100mm cube
        model = sw.NewDocument(template, 0, 0, 0)
        front_plane = model.FeatureByName("Front Plane")
        model.ClearSelection2(True)
        front_plane.Select2(False, 0)
        model.SketchManager.InsertSketch(True)
        model.SketchManager.CreateCornerRectangle(0.0, 0.0, 0.0, 0.1, 0.1, 0.0)
        exit_sketch(model)

        sketch1 = model.FeatureByName("Sketch1")
        model.ClearSelection2(True)
        sketch1.Select2(False, 0)
        feat = model.FeatureManager.FeatureExtrusion2(
            True, False, False, 0, 0, 0.1, 0.0,
            False, False, False, False, 0.0, 0.0,
            False, False, False, False, True, True, True,
            0, 0, False
        )
        if not feat:
            log("Extrusion failed for mass properties test", "ERROR")
            return False
        log("100mm cube created", "SUCCESS")

        # Get mass properties
        model.ForceRebuild3(True)
        props = model.GetMassProperties
        if not props or len(props) < 12:
            log("GetMassProperties returned invalid data", "ERROR")
            return False

        volume_mm3 = props[3] * 1e9
        surface_area_mm2 = props[4] * 1e6
        com_x = props[0] * 1000.0
        com_y = props[1] * 1000.0
        com_z = props[2] * 1000.0

        log(f"Volume: {volume_mm3:.0f} mm^3 (expected 1000000)", "SUCCESS")
        log(f"Surface Area: {surface_area_mm2:.0f} mm^2 (expected 60000)", "SUCCESS")
        log(f"Center of Mass: ({com_x:.1f}, {com_y:.1f}, {com_z:.1f}) mm", "SUCCESS")

        # Validate expected values for 100mm cube
        if abs(volume_mm3 - 1_000_000) > 1:
            log(f"Volume mismatch: expected 1000000, got {volume_mm3:.2f}", "ERROR")
            return False
        if abs(surface_area_mm2 - 60_000) > 1:
            log(f"Surface area mismatch: expected 60000, got {surface_area_mm2:.2f}", "ERROR")
            return False

        log("Mass properties validated", "SUCCESS")
        model.ViewZoomtofit2()
        return True
    except Exception as e:
        log(f"mass_properties FAILED: {e}", "ERROR")
        traceback.print_exc()
        return False


def test_cut_extrusion(sw, template):
    """Test: create a cube then cut a hole in it."""
    try:
        log("\n--- Test: cut_extrusion ---")

        # Create a 100mm cube
        model = sw.NewDocument(template, 0, 0, 0)
        front_plane = model.FeatureByName("Front Plane")
        model.ClearSelection2(True)
        front_plane.Select2(False, 0)
        model.SketchManager.InsertSketch(True)
        model.SketchManager.CreateCornerRectangle(0.0, 0.0, 0.0, 0.1, 0.1, 0.0)
        exit_sketch(model)

        sketch1 = model.FeatureByName("Sketch1")
        model.ClearSelection2(True)
        sketch1.Select2(False, 0)
        feat = model.FeatureManager.FeatureExtrusion2(
            True, False, False, 0, 0, 0.1, 0.0,
            False, False, False, False, 0.0, 0.0,
            False, False, False, False, True, True, True,
            0, 0, False
        )
        if not feat:
            log("Base extrusion failed", "ERROR")
            return False
        log("100mm cube created", "SUCCESS")

        # Select the front face and sketch a circle for the cut
        callout = win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)
        model.ClearSelection2(True)
        ok = model.Extension.SelectByID2(
            "", "FACE",
            0.05, 0.05, 0.0,  # front face center
            False, 0, callout, 0
        )
        if not ok:
            log("Could not select front face", "ERROR")
            return False

        model.SketchManager.InsertSketch(True)
        model.SketchManager.CreateCircleByRadius(0.05, 0.05, 0.0, 0.02)  # 20mm radius circle at center
        log("Circle drawn on front face for cut", "SUCCESS")

        # Exit sketch and select it for cut
        model.ClearSelection2(True)
        model.SketchManager.InsertSketch(True)

        sketch2 = model.FeatureByName("Sketch2")
        if not sketch2:
            log("Could not find Sketch2", "ERROR")
            return False
        model.ClearSelection2(True)
        sketch2.Select2(False, 0)

        # Cut-extrude 50mm deep (reverse=True to cut into the solid)
        cut_feat = model.FeatureManager.FeatureCut4(
            True,      # Sd
            True,      # Flip (reverse into the solid)
            False,     # Dir
            0,         # T1 (Blind)
            0,         # T2
            0.05,      # D1 (50mm)
            0.0,       # D2
            False,     # Dchk1
            False,     # Dchk2
            False,     # Ddir1
            False,     # Ddir2
            0.0,       # Dang1
            0.0,       # Dang2
            False,     # OffsetReverse1
            False,     # OffsetReverse2
            False,     # TranslateSurface1
            False,     # TranslateSurface2
            False,     # NormalCut
            False,     # UseFeatScope
            True,      # UseAutoSelect
            False,     # AssemblyFeatureScope
            True,      # AutoSelectComponents
            False,     # PropagateFeatureToParts
            0,         # T0
            0.0,       # StartOffset
            False,     # FlipStartOffset
            False      # OptimizeGeometry
        )
        if not cut_feat:
            log("Cut-extrusion returned None", "ERROR")
            return False

        log("Cut-extrusion created (50mm deep hole)", "SUCCESS")
        model.ViewZoomtofit2()
        return True
    except Exception as e:
        log(f"cut_extrusion FAILED: {e}", "ERROR")
        traceback.print_exc()
        return False


def test_all_new_tools():
    """Run all new sketch tool tests."""
    try:
        log("="*60)
        log("New Sketch Tools Test Suite")
        log("="*60)

        pythoncom.CoInitialize()
        sw = win32com.client.Dispatch("SldWorks.Application")
        sw.Visible = True
        log(f"Connected to SolidWorks {sw.RevisionNumber}", "SUCCESS")

        template = find_template()
        if not template:
            log("No template found", "ERROR")
            return False

        results = []
        results.append(("line", test_sketch_line(sw, template)))
        results.append(("centerline", test_sketch_centerline(sw, template)))
        results.append(("point", test_sketch_point(sw, template)))
        results.append(("arc", test_sketch_arc(sw, template)))
        results.append(("polygon", test_sketch_polygon(sw, template)))
        results.append(("ellipse", test_sketch_ellipse(sw, template)))
        results.append(("slot", test_sketch_slot(sw, template)))
        results.append(("spline", test_sketch_spline(sw, template)))
        results.append(("text", test_sketch_text(sw, template)))
        results.append(("dimension", test_sketch_dimension(sw, template)))
        results.append(("set_dimension_value", test_set_dimension_value(sw, template)))
        results.append(("constraint", test_sketch_constraint(sw, template)))
        results.append(("toggle_construction", test_toggle_construction(sw, template)))
        results.append(("mass_properties", test_mass_properties(sw, template)))
        results.append(("cut_extrusion", test_cut_extrusion(sw, template)))

        log("\n" + "="*60)
        log("RESULTS:")
        passed = 0
        for name, ok in results:
            status = "PASS" if ok else "FAIL"
            log(f"  {name}: {status}", "SUCCESS" if ok else "ERROR")
            if ok:
                passed += 1

        log(f"\n{passed}/{len(results)} tests passed")
        log("="*60)
        return passed == len(results)

    except Exception as e:
        log(f"Test suite error: {e}", "ERROR")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\nStarting test...\n")

    if len(sys.argv) > 1 and sys.argv[1] == "--new":
        success = test_all_new_tools()
    else:
        success = test_solidworks()

    if success:
        print("\n✓ SUCCESS!")
    else:
        print("\n❌ FAILED!")

    input("\nPress Enter to exit...")
    sys.exit(0 if success else 1)