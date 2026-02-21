"""
SolidWorks MCP - Unified Test Suite

Combines all tests from test_solidworks.py and the integration suite.

Usage:
    python test.py                          # Run all tests
    python test.py --gui                    # Interactive CLI test picker
    python test.py --category "Sketch Tools"  # Run one category
    python test.py --test sketch_line       # Run one test by name
    python test.py --list                   # List all available tests
"""

import win32com.client
import pythoncom
import glob
import sys
import traceback
import time
import argparse
import math
from dataclasses import dataclass, field
from typing import Callable, Optional

from solidworks import selection_helpers as sel

# Force UTF-8 output so Unicode symbols survive the Windows console
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Test registry
# ---------------------------------------------------------------------------

@dataclass
class TestEntry:
    name: str
    display_name: str
    category: str
    description: str
    func: Callable
    order: int = 0

TEST_REGISTRY: list[TestEntry] = []

CATEGORY_ORDER = ["Basic", "Sketch Tools", "Feature Tools", "MCP Tools", "Integration"]


def register_test(name, display_name, category, description, order=0):
    """Decorator to register a test function."""
    def decorator(func):
        TEST_REGISTRY.append(TestEntry(
            name=name,
            display_name=display_name,
            category=category,
            description=description,
            func=func,
            order=order,
        ))
        return func
    return decorator


# ---------------------------------------------------------------------------
# Global result tracking
# ---------------------------------------------------------------------------

PASS = 0
FAIL = 0
RESULTS = []  # list of (label, ok, detail)


def _result(label, ok, detail=""):
    global PASS, FAIL
    RESULTS.append((label, ok, detail))
    if ok:
        PASS += 1
        print(f"  \u2713 {label}{' \u2014 ' + detail if detail else ''}")
    else:
        FAIL += 1
        print(f"  \u2717 {label}{' \u2014 ' + detail if detail else ''}")
    return ok


def log(message, level="INFO"):
    prefix = "\u2713" if level == "SUCCESS" else "\u274c" if level == "ERROR" else "\u2192"
    print(f"  {prefix} {message}")


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def subsection(title):
    print(f"\n  [{title}]")


# ---------------------------------------------------------------------------
# SolidWorks connection helpers
# ---------------------------------------------------------------------------

def connect_to_solidworks():
    """Connect to an existing or new SolidWorks instance."""
    try:
        sw = win32com.client.GetActiveObject("SldWorks.Application")
        print("  \u2192 Attached to existing SolidWorks instance")
    except Exception:
        print("  \u2192 Launching new SolidWorks instance\u2026")
        sw = win32com.client.Dispatch("SldWorks.Application")
        sw.Visible = True
        for i in range(30):
            try:
                _ = sw.RevisionNumber
                break
            except Exception:
                time.sleep(1)
        else:
            raise RuntimeError("SolidWorks failed to start within 30 s")
    return sw


def find_template():
    """Discover the Part template file."""
    patterns = [
        r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS *\templates\Part.prtdot",
        r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS *\templates\Part.PRTDOT",
    ]
    for pattern in patterns:
        hits = glob.glob(pattern)
        if hits:
            return hits[0]
    return None


def close_all_docs(sw):
    """Close all open SolidWorks documents without saving."""
    try:
        sw.CloseAllDocuments(True)
    except Exception:
        # Fallback: close one-by-one
        while True:
            doc = sw.ActiveDoc
            if not doc:
                break
            title = doc.GetTitle()
            sw.QuitDoc(title)


# ---------------------------------------------------------------------------
# Sketch / modeling helpers
# ---------------------------------------------------------------------------

def new_part(sw, template):
    doc = sw.NewDocument(template, 0, 0, 0)
    if not doc:
        raise RuntimeError("NewDocument returned None")
    return doc


def new_sketch_on_front(sw, template):
    """Create a new part and open a sketch on the Front Plane."""
    model = sw.NewDocument(template, 0, 0, 0)
    front_plane = model.FeatureByName("Front Plane")
    model.ClearSelection2(True)
    front_plane.Select2(False, 0)
    model.SketchManager.InsertSketch(True)
    return model


def select_plane(doc, plane_name):
    """Select a plane — delegates to selection_helpers.select_plane()."""
    ok = sel.select_plane(doc, plane_name)
    if not ok:
        raise RuntimeError(f"Plane not found: {plane_name}")
    return ok


def create_sketch_on_plane(doc, plane_name):
    """Select a plane and open a sketch on it."""
    select_plane(doc, plane_name)
    doc.SketchManager.InsertSketch(True)


def create_sketch_on_face(doc, x_mm, y_mm, z_mm):
    """Select a solid face at (x,y,z) in mm and open a sketch on it."""
    ok = sel.select_face(doc, x_mm, y_mm, z_mm)
    if not ok:
        raise RuntimeError(f"Could not select face at ({x_mm},{y_mm},{z_mm}) mm")
    doc.SketchManager.InsertSketch(True)


def exit_sketch(doc):
    doc.ClearSelection2(True)
    doc.SketchManager.InsertSketch(True)


def select_sketch(doc, sketch_name):
    """Select a sketch by name — delegates to selection_helpers.select_sketch()."""
    ok = sel.select_sketch(doc, sketch_name)
    if not ok:
        raise RuntimeError(f"Sketch not found: {sketch_name}")
    return ok


def get_latest_sketch_name(doc):
    """Mirror the fallback logic in modeling.py._get_latest_sketch_name()."""
    try:
        features = doc.FeatureManager.GetFeatures(True)
        if features:
            for feature in reversed(features):
                if feature.GetTypeName2 == "ProfileFeature":
                    return feature.Name
    except Exception:
        pass
    return "Sketch1"


def extrude(doc, sketch_name, depth_mm, cut=False, reverse=False):
    """Select sketch and create an extrusion or cut-extrusion."""
    select_sketch(doc, sketch_name)
    depth_m = depth_mm / 1000.0

    if cut:
        feature = doc.FeatureManager.FeatureCut4(
            True, reverse, False, 0, 0, depth_m, 0.0,
            False, False, False, False, 0.0, 0.0,
            False, False, False, False, False, False, True,
            False, True, False, 0, 0.0, False, False
        )
        if not feature:
            raise RuntimeError("FeatureCut4 returned None for cut-extrusion")
    else:
        feature = doc.FeatureManager.FeatureExtrusion2(
            True, reverse, False, 0, 0, depth_m, 0.0,
            False, False, False, False, 0.0, 0.0,
            False, False, False, False, True, True, True, 0, 0, False
        )
        if not feature:
            raise RuntimeError("FeatureExtrusion2 returned None for extrusion")
    return feature


def make_cube(sw, template, size_mm=100):
    """Create a part with a cube of given size. Returns the model."""
    size_m = size_mm / 1000.0
    model = sw.NewDocument(template, 0, 0, 0)
    front_plane = model.FeatureByName("Front Plane")
    model.ClearSelection2(True)
    front_plane.Select2(False, 0)
    model.SketchManager.InsertSketch(True)
    model.SketchManager.CreateCornerRectangle(0.0, 0.0, 0.0, size_m, size_m, 0.0)
    exit_sketch(model)
    sketch1 = model.FeatureByName("Sketch1")
    model.ClearSelection2(True)
    sketch1.Select2(False, 0)
    feat = model.FeatureManager.FeatureExtrusion2(
        True, False, False, 0, 0, size_m, 0.0,
        False, False, False, False, 0.0, 0.0,
        False, False, False, False, True, True, True,
        0, 0, False
    )
    if not feat:
        raise Exception("Failed to create base cube for test")
    return model


# ===========================================================================
# TEST FUNCTIONS — Basic
# ===========================================================================

@register_test("basic_cube", "Basic Cube (100mm)", "Basic",
               "Create a 100mm cube end-to-end: part, sketch, extrude", order=0)
def test_basic_cube(sw, template):
    try:
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
            log("Extrusion returned None", "ERROR")
            return False

        model.ViewZoomtofit2()
        log("100mm cube created", "SUCCESS")
        return True
    except Exception as e:
        log(f"basic_cube FAILED: {e}", "ERROR")
        traceback.print_exc()
        return False


# ===========================================================================
# TEST FUNCTIONS — Sketch Tools
# ===========================================================================

@register_test("sketch_line", "Sketch Line", "Sketch Tools",
               "Draw a line from (0,0) to (50,50)mm", order=0)
def test_sketch_line(sw, template):
    try:
        model = new_sketch_on_front(sw, template)
        model.SketchManager.CreateLine(0.0, 0.0, 0.0, 0.05, 0.05, 0.0)
        log("Line created", "SUCCESS")
        exit_sketch(model)
        model.ViewZoomtofit2()
        return True
    except Exception as e:
        log(f"sketch_line FAILED: {e}", "ERROR")
        return False


@register_test("sketch_centerline", "Sketch Centerline", "Sketch Tools",
               "Draw a vertical centerline", order=1)
def test_sketch_centerline(sw, template):
    try:
        model = new_sketch_on_front(sw, template)
        model.SketchManager.CreateCenterLine(0.0, -0.05, 0.0, 0.0, 0.05, 0.0)
        log("Centerline created", "SUCCESS")
        exit_sketch(model)
        model.ViewZoomtofit2()
        return True
    except Exception as e:
        log(f"sketch_centerline FAILED: {e}", "ERROR")
        return False


@register_test("sketch_point", "Sketch Point", "Sketch Tools",
               "Create a sketch point at (25,25)mm", order=2)
def test_sketch_point(sw, template):
    try:
        model = new_sketch_on_front(sw, template)
        model.SketchManager.CreatePoint(0.025, 0.025, 0.0)
        log("Point created", "SUCCESS")
        exit_sketch(model)
        model.ViewZoomtofit2()
        return True
    except Exception as e:
        log(f"sketch_point FAILED: {e}", "ERROR")
        return False


@register_test("sketch_arc", "Sketch Arc", "Sketch Tools",
               "Draw a 3-point arc and a center-point arc", order=3)
def test_sketch_arc(sw, template):
    try:
        model = new_sketch_on_front(sw, template)

        model.SketchManager.Create3PointArc(
            0.0, 0.0, 0.0,
            0.05, 0.0, 0.0,
            0.025, 0.02, 0.0
        )
        log("3-point arc created", "SUCCESS")

        model.SketchManager.CreateArc(
            0.0, -0.03, 0.0,
            0.02, -0.03, 0.0,
            -0.02, -0.03, 0.0,
            1
        )
        log("Center-point arc created", "SUCCESS")

        exit_sketch(model)
        model.ViewZoomtofit2()
        return True
    except Exception as e:
        log(f"sketch_arc FAILED: {e}", "ERROR")
        traceback.print_exc()
        return False


@register_test("sketch_polygon", "Sketch Polygon", "Sketch Tools",
               "Draw a hexagon and extrude it", order=4)
def test_sketch_polygon(sw, template):
    try:
        model = new_sketch_on_front(sw, template)

        model.SketchManager.CreatePolygon(
            0.0, 0.0, 0.0,
            0.025, 0.0, 0.0,
            6, False
        )
        log("Hexagon created", "SUCCESS")

        exit_sketch(model)

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


@register_test("sketch_ellipse", "Sketch Ellipse", "Sketch Tools",
               "Draw a 30x20mm ellipse and extrude it", order=5)
def test_sketch_ellipse(sw, template):
    try:
        model = new_sketch_on_front(sw, template)

        cx_m, cy_m = 0.0, 0.0
        major_r_m = 0.03
        minor_r_m = 0.02
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


@register_test("sketch_slot", "Sketch Slot", "Sketch Tools",
               "Draw a 50mm slot and extrude it", order=6)
def test_sketch_slot(sw, template):
    try:
        model = new_sketch_on_front(sw, template)

        model.SketchManager.CreateSketchSlot(
            0, 0, 0.02,
            -0.025, 0.0, 0.0,
            0.025, 0.0, 0.0,
            0.0, 0.0, 0.0,
            1, False
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


@register_test("sketch_spline", "Sketch Spline", "Sketch Tools",
               "Draw a spline through 4 points", order=7)
def test_sketch_spline(sw, template):
    try:
        model = new_sketch_on_front(sw, template)

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


@register_test("sketch_text", "Sketch Text", "Sketch Tools",
               "Insert sketch text 'HELLO'", order=8)
def test_sketch_text(sw, template):
    try:
        model = new_sketch_on_front(sw, template)

        sketch_text_obj = model.InsertSketchText(
            0.0, 0.0, 0.0, "HELLO", 1, 0, 0, 1, 0
        )
        if not sketch_text_obj:
            log("InsertSketchText returned None", "ERROR")
            return False
        log("Sketch text 'HELLO' created", "SUCCESS")

        exit_sketch(model)
        model.ViewZoomtofit2()
        return True
    except Exception as e:
        log(f"sketch_text FAILED: {e}", "ERROR")
        traceback.print_exc()
        return False


@register_test("sketch_constraint", "Sketch Constraint", "Sketch Tools",
               "Draw two lines and apply a parallel constraint", order=9)
def test_sketch_constraint(sw, template):
    try:
        model = new_sketch_on_front(sw, template)

        model.SketchManager.CreateLine(0.0, 0.0, 0.0, 0.05, 0.02, 0.0)
        model.SketchManager.CreateLine(0.0, 0.03, 0.0, 0.05, 0.04, 0.0)
        log("Two lines drawn", "SUCCESS")

        callout = win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)
        model.ClearSelection2(True)
        model.Extension.SelectByID2(
            "", "SKETCHSEGMENT", 0.025, 0.01, 0.0,
            False, 0, callout, 0
        )
        model.Extension.SelectByID2(
            "", "SKETCHSEGMENT", 0.025, 0.035, 0.0,
            True, 0, callout, 0
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


@register_test("toggle_construction", "Toggle Construction Geometry", "Sketch Tools",
               "Draw a line and toggle it to construction geometry", order=10)
def test_toggle_construction(sw, template):
    try:
        model = new_sketch_on_front(sw, template)

        model.SketchManager.CreateLine(0.0, 0.0, 0.0, 0.05, 0.0, 0.0)
        log("Line drawn", "SUCCESS")

        callout = win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)
        model.ClearSelection2(True)
        ok = model.Extension.SelectByID2(
            "", "SKETCHSEGMENT", 0.025, 0.0, 0.0,
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


# ===========================================================================
# TEST FUNCTIONS — Feature Tools
# ===========================================================================

@register_test("mass_properties", "Mass Properties", "Feature Tools",
               "Create 100mm cube and verify volume/surface area", order=0)
def test_mass_properties(sw, template):
    try:
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


@register_test("cut_extrusion", "Cut Extrusion", "Feature Tools",
               "Create a cube then cut a circular hole in it", order=1)
def test_cut_extrusion(sw, template):
    try:
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

        callout = win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)
        model.ClearSelection2(True)
        ok = model.Extension.SelectByID2(
            "", "FACE", 0.05, 0.05, 0.0,
            False, 0, callout, 0
        )
        if not ok:
            log("Could not select front face", "ERROR")
            return False

        model.SketchManager.InsertSketch(True)
        model.SketchManager.CreateCircleByRadius(0.05, 0.05, 0.0, 0.02)
        log("Circle drawn on front face for cut", "SUCCESS")

        model.ClearSelection2(True)
        model.SketchManager.InsertSketch(True)

        sketch2 = model.FeatureByName("Sketch2")
        if not sketch2:
            log("Could not find Sketch2", "ERROR")
            return False
        model.ClearSelection2(True)
        sketch2.Select2(False, 0)

        cut_feat = model.FeatureManager.FeatureCut4(
            True, True, False, 0, 0, 0.05, 0.0,
            False, False, False, False, 0.0, 0.0,
            False, False, False, False, False, False, True,
            False, True, False, 0, 0.0, False, False
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


@register_test("fillet", "Fillet", "Feature Tools",
               "Create a cube and fillet one edge (5mm)", order=2)
def test_fillet(sw, template):
    try:
        make_cube(sw, template, 100)
        model = sw.ActiveDoc
        model.ForceRebuild3(True)

        # Select a Z-direction edge (front-right, midpoint at z=0.05)
        callout = win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)
        model.ClearSelection2(True)
        ok = model.Extension.SelectByID2(
            "", "EDGE", 0.1, 0.0, 0.05,
            False, 1, callout, 0
        )
        if not ok:
            log("Could not select edge for fillet", "ERROR")
            return False

        # Options=195 required for SolidWorks 2025+
        feature = model.FeatureManager.FeatureFillet3(
            195, 0.005, 0.0, 0.0, 0, 0, 0, 0,
        )
        if not feature:
            log("FeatureFillet3 returned None", "ERROR")
            return False

        log("Fillet created (5mm radius)", "SUCCESS")
        model.ViewZoomtofit2()
        return True
    except Exception as e:
        log(f"fillet FAILED: {e}", "ERROR")
        traceback.print_exc()
        return False


@register_test("chamfer", "Chamfer", "Feature Tools",
               "Create a cube and chamfer one edge (5mm)", order=3)
def test_chamfer(sw, template):
    try:
        make_cube(sw, template, 100)
        model = sw.ActiveDoc
        model.ForceRebuild3(True)

        # Select a Z-direction edge (front-right, midpoint at z=0.05)
        callout = win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)
        model.ClearSelection2(True)
        ok = model.Extension.SelectByID2(
            "", "EDGE", 0.1, 0.0, 0.05,
            False, 0, callout, 0
        )
        if not ok:
            log("Could not select edge for chamfer", "ERROR")
            return False

        # SolidWorks 2025 requires 8 parameters (3 extra trailing zeros)
        feature = model.FeatureManager.InsertFeatureChamfer(
            4, 0, 0.005, 0.785398, 0.005, 0, 0, 0,
        )
        if not feature:
            log("InsertFeatureChamfer returned None", "ERROR")
            return False

        log("Chamfer created (5mm)", "SUCCESS")
        model.ViewZoomtofit2()
        return True
    except Exception as e:
        log(f"chamfer FAILED: {e}", "ERROR")
        traceback.print_exc()
        return False


@register_test("shell", "Shell", "Feature Tools",
               "Create a cube and shell it (remove top face, 3mm)", order=4)
def test_shell(sw, template):
    try:
        make_cube(sw, template, 100)
        model = sw.ActiveDoc
        model.ForceRebuild3(True)

        # Select top face (y=100mm, center of face)
        callout = win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)
        model.ClearSelection2(True)
        ok = model.Extension.SelectByID2(
            "", "FACE", 0.05, 0.1, 0.05,
            False, 0, callout, 0
        )
        if not ok:
            log("Could not select top face for shell", "ERROR")
            return False

        # In SW2025, InsertFeatureShell lives on the model (IModelDoc2),
        # NOT on FeatureManager. It may return None even on success,
        # so verify by checking the feature tree.
        model._FlagAsMethod("InsertFeatureShell")
        model.InsertFeatureShell(0.003, False)
        model.ForceRebuild3(True)

        # Verify shell was created by checking feature tree
        features = model.FeatureManager.GetFeatures(True)
        shell_found = False
        if features:
            for f in features:
                if "Shell" in f.Name:
                    shell_found = True
                    break
        if not shell_found:
            log("Shell feature not found in feature tree", "ERROR")
            return False

        log("Shell created (3mm thickness, top face removed)", "SUCCESS")
        model.ViewZoomtofit2()
        return True
    except Exception as e:
        log(f"shell FAILED: {e}", "ERROR")
        traceback.print_exc()
        return False


@register_test("revolve", "Revolve", "Feature Tools",
               "Create a half-profile with centerline and revolve 360 deg", order=5)
def test_revolve(sw, template):
    try:
        model = new_sketch_on_front(sw, template)

        model.SketchManager.CreateCenterLine(0.0, -0.03, 0.0, 0.0, 0.03, 0.0)
        model.SketchManager.CreateLine(0.01, -0.02, 0.0, 0.02, -0.02, 0.0)
        model.SketchManager.CreateLine(0.02, -0.02, 0.0, 0.02, 0.02, 0.0)
        model.SketchManager.CreateLine(0.02, 0.02, 0.0, 0.01, 0.02, 0.0)
        model.SketchManager.CreateLine(0.01, 0.02, 0.0, 0.01, -0.02, 0.0)
        log("Half-profile and centerline drawn", "SUCCESS")

        exit_sketch(model)

        sketch1 = model.FeatureByName("Sketch1")
        model.ClearSelection2(True)
        sketch1.Select2(False, 0)

        feature = model.FeatureManager.FeatureRevolve2(
            True, True, False, False, False, False,
            0, 0,
            2 * math.pi,
            0.0,
            False, False, 0.0, 0.0,
            0, 0.0, 0.0,
            True, True, True,
        )
        if not feature:
            log("FeatureRevolve2 returned None", "ERROR")
            return False

        log("Revolve created (360\u00b0)", "SUCCESS")
        model.ViewZoomtofit2()
        return True
    except Exception as e:
        log(f"revolve FAILED: {e}", "ERROR")
        traceback.print_exc()
        return False


@register_test("ref_plane", "Reference Plane", "Feature Tools",
               "Create a 50mm offset reference plane from Front", order=6)
def test_ref_plane(sw, template):
    try:
        make_cube(sw, template, 100)
        model = sw.ActiveDoc
        model.ForceRebuild3(True)

        # In SW2025, SelectByID2 with type "PLANE" works (not "DATUMPLANE")
        callout = win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)
        model.ClearSelection2(True)
        ok = model.Extension.SelectByID2(
            "Front Plane", "PLANE", 0, 0, 0,
            False, 0, callout, 0
        )
        if not ok:
            log("Could not select Front Plane", "ERROR")
            return False

        # flags=5 works reliably in SW2025 for offset planes
        feature = model.FeatureManager.InsertRefPlane(5, 0.05, 0, 0, 0, 0)

        # InsertRefPlane may return None even on success; check feature tree
        if not feature:
            model.ForceRebuild3(True)
            features = model.FeatureManager.GetFeatures(True)
            if features:
                for f in features:
                    if "Plane" in f.Name and f.Name != "Front Plane" \
                            and f.Name != "Top Plane" and f.Name != "Right Plane":
                        feature = f
                        break

        if not feature:
            log("InsertRefPlane returned None and no new plane in feature tree", "ERROR")
            return False

        log("Reference plane created (50mm offset from Front)", "SUCCESS")
        model.ViewZoomtofit2()
        return True
    except Exception as e:
        log(f"ref_plane FAILED: {e}", "ERROR")
        traceback.print_exc()
        return False


@register_test("loft", "Loft (Frustum)", "Feature Tools",
               "Create a frustum via loft between two circles on offset planes", order=7)
def test_loft(sw, template):
    try:
        model = sw.NewDocument(template, 0, 0, 0)

        # Sketch 1: large circle on Front Plane
        create_sketch_on_plane(model, "Front Plane")
        model.SketchManager.CreateCircleByRadius(0.0, 0.0, 0.0, 0.025)  # 25mm radius
        exit_sketch(model)
        sketch1_name = get_latest_sketch_name(model)
        log(f"Sketch 1: {sketch1_name}", "SUCCESS")

        # Create offset reference plane (80mm from Front)
        # Use SelectByID2 with "PLANE" type and flags=5 (proven in SW2025)
        callout = win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)
        model.ClearSelection2(True)
        ok = model.Extension.SelectByID2(
            "Front Plane", "PLANE", 0, 0, 0, False, 0, callout, 0
        )
        if not ok:
            log("Could not select Front Plane for ref plane", "ERROR")
            return False
        ref_feat = model.FeatureManager.InsertRefPlane(5, 0.08, 0, 0, 0, 0)
        if not ref_feat:
            # Fallback: check feature tree for a new plane
            model.ForceRebuild3(True)
            features = model.FeatureManager.GetFeatures(True)
            if features:
                for f in features:
                    if "Plane" in f.Name and f.Name not in (
                        "Front Plane", "Top Plane", "Right Plane"
                    ):
                        ref_feat = f
                        break
        if not ref_feat:
            log("Failed to create reference plane", "ERROR")
            return False
        custom_plane_name = ref_feat.Name
        log(f"Reference plane: {custom_plane_name}", "SUCCESS")

        # Sketch 2: small circle on custom plane
        plane_feat = model.FeatureByName(custom_plane_name)
        if not plane_feat:
            log(f"Could not find plane: {custom_plane_name}", "ERROR")
            return False
        model.ClearSelection2(True)
        plane_feat.Select2(False, 0)
        model.SketchManager.InsertSketch(True)
        model.SketchManager.CreateCircleByRadius(0.0, 0.0, 0.0, 0.01)  # 10mm radius
        exit_sketch(model)
        sketch2_name = get_latest_sketch_name(model)
        log(f"Sketch 2: {sketch2_name}", "SUCCESS")

        # Select both sketches for loft (mark=1)
        callout = win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)
        model.ClearSelection2(True)
        ok1 = model.Extension.SelectByID2(
            sketch1_name, "SKETCH", 0, 0, 0, False, 1, callout, 0
        )
        ok2 = model.Extension.SelectByID2(
            sketch2_name, "SKETCH", 0, 0, 0, True, 1, callout, 0
        )
        if not ok1 or not ok2:
            log(f"Sketch selection failed: {sketch1_name}={ok1}, {sketch2_name}={ok2}", "ERROR")
            return False

        # Create loft using InsertProtrusionBlend2 (18 params for SW2025)
        feature = model.FeatureManager.InsertProtrusionBlend2(
            False,  # Closed
            True,   # KeepTangency
            True,   # ForceNonRational
            1.0,    # TessToleranceFactor
            0,      # StartMatchingType (None)
            0,      # EndMatchingType (None)
            1.0,    # StartTangentLength
            1.0,    # EndTangentLength
            False,  # MaintainTangency
            True,   # Merge
            False,  # IsThinBody
            0.0,    # Thickness1
            0.0,    # Thickness2
            0,      # ThinType
            True,   # UseFeatScope
            True,   # UseAutoSelect
            True,   # Close (feature scope)
            0,      # GuideCurveInfluence
        )
        if not feature:
            log("InsertProtrusionBlend2 returned None", "ERROR")
            return False

        log("Loft (frustum) created successfully", "SUCCESS")
        model.ViewZoomtofit2()
        return True
    except Exception as e:
        log(f"loft FAILED: {e}", "ERROR")
        traceback.print_exc()
        return False


@register_test("list_features", "List Features", "Feature Tools",
               "Create a cube and list the feature tree", order=8)
def test_list_features(sw, template):
    try:
        model = make_cube(sw, template, 100)

        features = model.FeatureManager.GetFeatures(True)
        if not features:
            log("GetFeatures returned None", "ERROR")
            return False

        found_extrude = False
        for feature in features:
            name = feature.Name
            type_name = feature.GetTypeName2
            if "Extrusion" in type_name or "Extrude" in name:
                found_extrude = True

        if not found_extrude:
            log("Could not find extrusion feature in tree", "ERROR")
            return False

        log(f"Feature tree has {len(features)} features, extrusion found", "SUCCESS")
        return True
    except Exception as e:
        log(f"list_features FAILED: {e}", "ERROR")
        traceback.print_exc()
        return False


# ===========================================================================
# TEST FUNCTIONS — MCP Tools (exercise the full MCP _route_tool dispatch)
# ===========================================================================


def create_mcp_server():
    """Create a SolidWorksMCPServer instance for MCP-level testing."""
    from server import SolidWorksMCPServer
    return SolidWorksMCPServer()


def mcp_make_cube(server, size_mm=100):
    """Create a cube end-to-end via MCP tool calls. Returns list of result strings.

    Note: create_extrusion exits sketch mode internally, so we do NOT call
    exit_sketch before it (that would toggle sketch mode back on).
    """
    results = []
    results.append(server._route_tool("solidworks_new_part", {}))
    results.append(server._route_tool("solidworks_create_sketch", {"plane": "Front"}))
    results.append(server._route_tool("solidworks_sketch_rectangle", {
        "centerX": size_mm / 2, "centerY": size_mm / 2,
        "width": size_mm, "height": size_mm
    }))
    results.append(server._route_tool("solidworks_create_extrusion", {"depth": size_mm}))
    return results


def mcp_check_results(results):
    """Verify all MCP results start with ✓. Returns True if all pass."""
    for r in results:
        if not r.startswith("✓"):
            log(f"MCP call failed: {r}", "ERROR")
            return False
    return True


@register_test("mcp_basic_workflow", "MCP Basic Workflow", "MCP Tools",
               "Create a 100mm cube end-to-end via MCP tool calls", order=0)
def test_mcp_basic_workflow(sw, template):
    try:
        server = create_mcp_server()
        results = mcp_make_cube(server, 100)
        if not mcp_check_results(results):
            return False

        extrude_result = results[-1]
        if "Boss-Extrude" not in extrude_result and "Extrusion" not in extrude_result:
            log(f"Extrusion result missing feature name: {extrude_result}", "ERROR")
            return False

        log("MCP basic workflow (cube) succeeded", "SUCCESS")
        return True
    except Exception as e:
        log(f"mcp_basic_workflow FAILED: {e}", "ERROR")
        traceback.print_exc()
        return False


@register_test("mcp_fillet", "MCP Fillet", "MCP Tools",
               "Create cube via MCP, then fillet an edge", order=1)
def test_mcp_fillet(sw, template):
    try:
        server = create_mcp_server()
        results = mcp_make_cube(server, 100)
        if not mcp_check_results(results):
            return False

        r = server._route_tool("solidworks_fillet", {
            "radius": 5,
            "edges": [{"x": 100, "y": 0, "z": 50}]
        })
        if not r.startswith("✓"):
            log(f"Fillet failed: {r}", "ERROR")
            return False
        if "Fillet" not in r:
            log(f"Fillet result missing feature name: {r}", "ERROR")
            return False

        log("MCP fillet succeeded", "SUCCESS")
        return True
    except Exception as e:
        log(f"mcp_fillet FAILED: {e}", "ERROR")
        traceback.print_exc()
        return False


@register_test("mcp_chamfer", "MCP Chamfer", "MCP Tools",
               "Create cube via MCP, then chamfer an edge", order=2)
def test_mcp_chamfer(sw, template):
    try:
        server = create_mcp_server()
        results = mcp_make_cube(server, 100)
        if not mcp_check_results(results):
            return False

        r = server._route_tool("solidworks_chamfer", {
            "distance": 5,
            "edges": [{"x": 100, "y": 0, "z": 50}]
        })
        if not r.startswith("✓"):
            log(f"Chamfer failed: {r}", "ERROR")
            return False
        if "Chamfer" not in r:
            log(f"Chamfer result missing feature name: {r}", "ERROR")
            return False

        log("MCP chamfer succeeded", "SUCCESS")
        return True
    except Exception as e:
        log(f"mcp_chamfer FAILED: {e}", "ERROR")
        traceback.print_exc()
        return False


@register_test("mcp_shell", "MCP Shell", "MCP Tools",
               "Create cube via MCP, then shell (remove top face)", order=3)
def test_mcp_shell(sw, template):
    try:
        server = create_mcp_server()
        results = mcp_make_cube(server, 100)
        if not mcp_check_results(results):
            return False

        r = server._route_tool("solidworks_shell", {
            "thickness": 3,
            "facesToRemove": [{"x": 50, "y": 100, "z": 50}]
        })
        if not r.startswith("✓"):
            log(f"Shell failed: {r}", "ERROR")
            return False
        if "Shell" not in r:
            log(f"Shell result missing feature name: {r}", "ERROR")
            return False

        log("MCP shell succeeded", "SUCCESS")
        return True
    except Exception as e:
        log(f"mcp_shell FAILED: {e}", "ERROR")
        traceback.print_exc()
        return False


@register_test("mcp_cut_extrusion", "MCP Cut-Extrusion", "MCP Tools",
               "Create cube via MCP, then cut a circle through it", order=4)
def test_mcp_cut_extrusion(sw, template):
    try:
        server = create_mcp_server()
        results = mcp_make_cube(server, 100)
        if not mcp_check_results(results):
            return False

        # Sketch on the front face of the cube (z=0 plane)
        r = server._route_tool("solidworks_create_sketch", {
            "faceX": 50, "faceY": 50, "faceZ": 0
        })
        if not r.startswith("✓"):
            log(f"Sketch on face failed: {r}", "ERROR")
            return False

        r = server._route_tool("solidworks_sketch_circle", {
            "centerX": 50, "centerY": 50, "radius": 20
        })
        if not r.startswith("✓"):
            log(f"Circle sketch failed: {r}", "ERROR")
            return False

        # exit_sketch is required before create_cut_extrusion
        r = server._route_tool("solidworks_exit_sketch", {})
        if not r.startswith("✓"):
            log(f"Exit sketch failed: {r}", "ERROR")
            return False

        # reverse=True because the front face (z=0) normal points outward;
        # we need to cut INTO the body
        r = server._route_tool("solidworks_create_cut_extrusion", {
            "depth": 50, "reverse": True
        })
        if not r.startswith("✓"):
            log(f"Cut-extrusion failed: {r}", "ERROR")
            return False
        if "Cut" not in r:
            log(f"Cut result missing feature name: {r}", "ERROR")
            return False

        log("MCP cut-extrusion succeeded", "SUCCESS")
        return True
    except Exception as e:
        log(f"mcp_cut_extrusion FAILED: {e}", "ERROR")
        traceback.print_exc()
        return False


@register_test("mcp_mass_properties", "MCP Mass Properties", "MCP Tools",
               "Create cube via MCP, then verify volume via mass properties", order=5)
def test_mcp_mass_properties(sw, template):
    try:
        server = create_mcp_server()
        results = mcp_make_cube(server, 100)
        if not mcp_check_results(results):
            return False

        r = server._route_tool("solidworks_get_mass_properties", {})
        if "Volume" not in r:
            log(f"Mass properties missing volume: {r}", "ERROR")
            return False

        for line in r.split("\n"):
            if "Volume:" in line:
                vol_str = line.split(":")[1].strip().split(" ")[0]
                volume = float(vol_str)
                if abs(volume - 1_000_000) > 1:
                    log(f"Volume mismatch: expected ~1000000, got {volume}", "ERROR")
                    return False
                log(f"Volume verified: {volume:.0f} mm^3", "SUCCESS")
                break

        log("MCP mass properties succeeded", "SUCCESS")
        return True
    except Exception as e:
        log(f"mcp_mass_properties FAILED: {e}", "ERROR")
        traceback.print_exc()
        return False


@register_test("mcp_list_features", "MCP List Features", "MCP Tools",
               "Create cube via MCP, then list features and verify extrusion exists", order=6)
def test_mcp_list_features(sw, template):
    try:
        server = create_mcp_server()
        results = mcp_make_cube(server, 100)
        if not mcp_check_results(results):
            return False

        r = server._route_tool("solidworks_list_features", {})
        if "Feature Tree" not in r and "feature" not in r.lower():
            log(f"Unexpected list_features result: {r}", "ERROR")
            return False
        if "Extrusion" not in r and "Extrude" not in r:
            log(f"Feature tree missing extrusion: {r}", "ERROR")
            return False

        log("MCP list features succeeded", "SUCCESS")
        return True
    except Exception as e:
        log(f"mcp_list_features FAILED: {e}", "ERROR")
        traceback.print_exc()
        return False


@register_test("mcp_full_integration", "MCP Full Integration", "MCP Tools",
               "Multi-step MCP workflow: cube + fillet + cut + list_features + mass_properties",
               order=7)
def test_mcp_full_integration(sw, template):
    try:
        server = create_mcp_server()

        # Step 1: Create cube
        results = mcp_make_cube(server, 100)
        if not mcp_check_results(results):
            return False
        log("Step 1: Cube created", "SUCCESS")

        # Step 2: Fillet one edge
        r = server._route_tool("solidworks_fillet", {
            "radius": 5,
            "edges": [{"x": 100, "y": 0, "z": 50}]
        })
        if not r.startswith("✓"):
            log(f"Fillet failed: {r}", "ERROR")
            return False
        log("Step 2: Fillet created", "SUCCESS")

        # Step 3: Cut-extrusion (hole on top face)
        r = server._route_tool("solidworks_create_sketch", {
            "faceX": 50, "faceY": 100, "faceZ": 50
        })
        if not r.startswith("✓"):
            log(f"Sketch on face failed: {r}", "ERROR")
            return False

        r = server._route_tool("solidworks_sketch_circle", {
            "centerX": 50, "centerY": 50, "radius": 15
        })
        if not r.startswith("✓"):
            log(f"Circle failed: {r}", "ERROR")
            return False

        r = server._route_tool("solidworks_exit_sketch", {})
        if not r.startswith("✓"):
            log(f"Exit sketch failed: {r}", "ERROR")
            return False

        # Cut from top face downward into the body (reverse=True because
        # top face normal points upward, we need to cut INTO the body)
        r = server._route_tool("solidworks_create_cut_extrusion", {
            "depth": 50,
            "reverse": True
        })
        if not r.startswith("✓"):
            log(f"Cut-extrusion failed: {r}", "ERROR")
            return False
        log("Step 3: Through-all cut created", "SUCCESS")

        # Step 4: List features (should have Boss-Extrude, Fillet, Cut-Extrude)
        r = server._route_tool("solidworks_list_features", {})
        if "Fillet" not in r:
            log(f"Feature tree missing Fillet: {r}", "ERROR")
            return False
        log("Step 4: Feature tree verified", "SUCCESS")

        # Step 5: Mass properties (volume should be less than 1,000,000)
        r = server._route_tool("solidworks_get_mass_properties", {})
        if "Volume" not in r:
            log(f"Mass properties missing volume: {r}", "ERROR")
            return False
        for line in r.split("\n"):
            if "Volume:" in line:
                vol_str = line.split(":")[1].strip().split(" ")[0]
                volume = float(vol_str)
                if volume >= 1_000_000:
                    log(f"Volume should be < 1M after cuts, got {volume}", "ERROR")
                    return False
                log(f"Step 5: Volume {volume:.0f} mm^3 (correctly less than original)", "SUCCESS")
                break

        log("MCP full integration passed", "SUCCESS")
        return True
    except Exception as e:
        log(f"mcp_full_integration FAILED: {e}", "ERROR")
        traceback.print_exc()
        return False


# ===========================================================================
# TEST FUNCTIONS — Integration (sequential sub-tests in one document)
# ===========================================================================

@register_test("integration_suite", "Cut-Extrude Reliability Suite", "Integration",
               "18+ sequential sub-tests: sketch lifecycle, extrusion, cuts, units, enumeration",
               order=0)
def test_integration_suite(sw, template):
    """Full integration test from original test.py, adapted to accept sw/template."""
    global PASS, FAIL

    # --- Part creation + plane selection ---
    subsection("Part creation & plane selection")
    close_all_docs(sw)
    doc = new_part(sw, template)
    ok = doc is not None
    _result("NewDocument returned a document", ok)
    if not ok:
        return False

    for plane in ("Front Plane", "Top Plane", "Right Plane"):
        try:
            feat = doc.FeatureByName(plane)
            _result(f"Select {plane}", feat is not None)
        except Exception:
            _result(f"Select {plane}", False)

    # --- Sketch lifecycle ---
    subsection("Sketch lifecycle (create \u2192 draw \u2192 exit)")
    try:
        create_sketch_on_plane(doc, "Front Plane")
        _result("InsertSketch on Front Plane", True)
    except Exception as e:
        _result("InsertSketch on Front Plane", False, str(e))
        return False

    try:
        doc.SketchManager.CreateCornerRectangle(0.0, 0.0, 0.0, 0.1, 0.1, 0.0)
        _result("CreateCornerRectangle 100x100 mm", True)
    except Exception as e:
        _result("CreateCornerRectangle 100x100 mm", False, str(e))
        return False

    try:
        exit_sketch(doc)
        _result("Exit sketch", True)
    except Exception as e:
        _result("Exit sketch", False, str(e))
        return False

    try:
        feat = doc.FeatureByName("Sketch1")
        _result("Sketch1 discoverable after exit", feat is not None)
    except Exception as e:
        _result("Sketch1 discoverable after exit", False, str(e))
        return False

    # Feature type check
    try:
        feat = doc.FeatureByName("Sketch1")
        type_name = feat.GetTypeName2 if feat else None
        _result("GetTypeName2 == 'ProfileFeature'", type_name == "ProfileFeature",
                f"got '{type_name}'" if type_name else "feature not found")
    except Exception as e:
        _result("GetTypeName2()", False, str(e))

    # Sketch counter
    try:
        found = get_latest_sketch_name(doc)
        _result(f"Latest sketch = '{found}'", found == "Sketch1")
    except Exception as e:
        _result("Feature enumeration", False, str(e))

    # Select by name
    try:
        feat = select_sketch(doc, "Sketch1")
        _result("FeatureByName('Sketch1') found", feat is not None)
    except Exception as e:
        _result("FeatureByName('Sketch1') found", False, str(e))

    # ClearSelection2 regression
    try:
        doc.ClearSelection2(True)
        feat = doc.FeatureByName("Sketch1")
        result = feat.Select2(False, 0) if feat else False
        _result("Select2 returned True", bool(result))
        doc.ClearSelection2(True)
    except Exception as e:
        _result("Select2 call", False, str(e))

    # --- Extrusion ---
    subsection("Extrusion (add material)")
    try:
        feat = extrude(doc, "Sketch1", 100.0, cut=False)
        _result("FeatureExtrusion2 (add material)", feat is not None)
        doc.ViewZoomtofit2()
    except Exception as e:
        _result("FeatureExtrusion2 (add material)", False, str(e))
        return False

    # Sketch still selectable after extrusion
    try:
        feat = doc.FeatureByName("Sketch1")
        _result("FeatureByName('Sketch1') post-extrusion", feat is not None)
    except Exception as e:
        _result("FeatureByName('Sketch1') post-extrusion", False, str(e))

    # --- Cut-extrusion ---
    subsection("Cut-extrusion (remove material)")
    try:
        create_sketch_on_face(doc, 50, 50, 100)
        _result("InsertSketch on top face of solid", True)
    except Exception as e:
        _result("InsertSketch on top face of solid", False, str(e))
        return False

    try:
        doc.SketchManager.CreateCircleByRadius(0.05, 0.05, 0.1, 0.01)
        _result("CreateCircleByRadius 10mm radius on top face", True)
    except Exception as e:
        _result("CreateCircleByRadius 10mm radius on top face", False, str(e))
        return False

    try:
        exit_sketch(doc)
        _result("Exit second sketch", True)
    except Exception as e:
        _result("Exit second sketch", False, str(e))
        return False

    try:
        feat = doc.FeatureByName("Sketch2")
        _result("Sketch2 exists after exit", feat is not None)
    except Exception as e:
        _result("Sketch2 exists after exit", False, str(e))

    # Feature type & selection checks for Sketch2
    try:
        feat = doc.FeatureByName("Sketch2")
        type_name = feat.GetTypeName2 if feat else None
        _result("Sketch2 GetTypeName2 == 'ProfileFeature'", type_name == "ProfileFeature")
    except Exception:
        pass

    try:
        found = get_latest_sketch_name(doc)
        _result(f"Latest sketch = '{found}'", found == "Sketch2")
    except Exception:
        pass

    try:
        feat = select_sketch(doc, "Sketch2")
        _result("FeatureByName('Sketch2') found", feat is not None)
    except Exception as e:
        _result("FeatureByName('Sketch2') found", False, str(e))

    try:
        feat = extrude(doc, "Sketch2", 50.0, cut=True, reverse=False)
        _result("FeatureCut4 (cut material)", feat is not None)
        doc.ViewZoomtofit2()
    except Exception as e:
        _result("FeatureCut4 (cut material)", False, str(e))

    # --- Cut-extrusion reversed ---
    subsection("Cut-extrusion reversed direction")
    try:
        create_sketch_on_face(doc, 30, 30, 0)
        doc.SketchManager.CreateCornerRectangle(0.01, 0.01, 0.0, 0.04, 0.04, 0.0)
        exit_sketch(doc)
        feat = extrude(doc, "Sketch3", 30.0, cut=True, reverse=True)
        _result("Cut-extrusion reversed 30mm", feat is not None)
        doc.ViewZoomtofit2()
    except Exception as e:
        _result("Cut-extrusion reversed 30mm", False, str(e))

    # --- Multiple sequential cuts ---
    subsection("Multiple sequential cut-extrusions")
    for i in range(2):
        sn = 4 + i
        sketch_name = f"Sketch{sn}"
        cx_mm = 20 + i * 50
        cx_m = cx_mm / 1000.0
        try:
            create_sketch_on_face(doc, cx_mm, 50, 100)
            doc.SketchManager.CreateCircleByRadius(cx_m, 0.05, 0.1, 0.005)
            exit_sketch(doc)
            feat = extrude(doc, sketch_name, 15.0, cut=True, reverse=False)
            _result(f"Cut #{i+1} using {sketch_name}", feat is not None)
        except Exception as e:
            _result(f"Cut #{i+1} using {sketch_name}", False, str(e))

    # --- Unit conversion validation ---
    subsection("Unit conversion: 50x30mm rectangle")
    try:
        create_sketch_on_plane(doc, "Right Plane")
        doc.SketchManager.CreateCornerRectangle(-0.025, -0.015, 0.0, 0.025, 0.015, 0.0)
        exit_sketch(doc)
        _result("50x30mm rectangle sketch created", True)
    except Exception as e:
        _result("50x30mm rectangle sketch created", False, str(e))

    subsection("Unit conversion: circle radius=10mm")
    try:
        create_sketch_on_plane(doc, "Top Plane")
        doc.SketchManager.CreateCircleByRadius(0.0, 0.0, 0.0, 0.01)
        exit_sketch(doc)
        _result("10mm-radius circle sketch created", True)
    except Exception as e:
        _result("10mm-radius circle sketch created", False, str(e))

    # --- Feature-tree enumeration ---
    subsection("Feature-tree enumeration robustness")
    try:
        features = doc.FeatureManager.GetFeatures(True)
        sketches = [f.Name for f in features if f.GetTypeName2 == "ProfileFeature"]
        _result(f"Found {len(sketches)} sketch(es) in feature tree", len(sketches) > 0,
                ", ".join(sketches))
        for name in sketches:
            feat = doc.FeatureByName(name)
            _result(f"FeatureByName('{name}') round-trip", feat is not None)
    except Exception as e:
        _result("Feature enumeration", False, str(e))

    # --- Final zoom ---
    try:
        doc.ViewZoomtofit2()
        _result("ViewZoomtofit2()", True)
    except Exception as e:
        _result("ViewZoomtofit2()", False, str(e))

    return True


# ===========================================================================
# Test runner
# ===========================================================================

def run_selected_tests(entries):
    """Run a list of TestEntry items. Returns True if all pass."""
    global PASS, FAIL, RESULTS
    PASS, FAIL, RESULTS = 0, 0, []

    section("SOLIDWORKS MCP \u2014 TEST SUITE")

    print("  \u2192 Initialising COM\u2026")
    pythoncom.CoInitialize()

    try:
        sw = connect_to_solidworks()
        ver = sw.RevisionNumber
        print(f"  \u2713 Connected to SolidWorks {ver}")
    except Exception as e:
        print(f"  \u2717 Failed to connect: {e}")
        return False

    template = find_template()
    if not template:
        print("  \u2717 No Part template found. Aborting.")
        return False
    print(f"  \u2713 Template: {template}")

    print("  \u2192 Closing all open documents\u2026")
    close_all_docs(sw)

    overall_results = []
    for entry in entries:
        section(f"{entry.category}: {entry.display_name}")
        try:
            ok = entry.func(sw, template)
            overall_results.append((entry.display_name, ok))
            if ok:
                log(f"{entry.display_name} \u2014 PASSED", "SUCCESS")
            else:
                log(f"{entry.display_name} \u2014 FAILED", "ERROR")
        except Exception as e:
            overall_results.append((entry.display_name, False))
            log(f"{entry.display_name} \u2014 EXCEPTION: {e}", "ERROR")
            traceback.print_exc()

        # Close docs between independent tests to prevent accumulation
        close_all_docs(sw)

    # --- Summary ---
    section("RESULTS")
    total = len(overall_results)
    passed = sum(1 for _, ok in overall_results if ok)
    failed = total - passed

    if passed:
        print(f"\n  PASSED ({passed}):")
        for name, ok in overall_results:
            if ok:
                print(f"    \u2713 {name}")

    if failed:
        print(f"\n  FAILED ({failed}):")
        for name, ok in overall_results:
            if not ok:
                print(f"    \u2717 {name}")

    print(f"\n  Total  : {total}")
    print(f"  Passed : {passed}")
    print(f"  Failed : {failed}")
    if failed == 0:
        print("\n  \u2713 ALL TESTS PASSED")
    else:
        print(f"\n  \u2717 {failed} TEST(S) FAILED")
    print()

    return failed == 0


# ===========================================================================
# Interactive CLI selector (--gui)
# ===========================================================================

def interactive_selector():
    """Print numbered test list, accept user selection, run chosen tests."""

    # Group tests by category
    categories = {}
    for entry in TEST_REGISTRY:
        categories.setdefault(entry.category, []).append(entry)

    # Sort categories by defined order, tests by their order field
    sorted_cats = sorted(categories.keys(),
                         key=lambda c: CATEGORY_ORDER.index(c) if c in CATEGORY_ORDER else 999)

    # Build numbered list
    numbered = []
    print("\n  SolidWorks MCP Test Suite \u2014 Interactive Selector")
    print("  " + "=" * 54)

    for cat in sorted_cats:
        entries = sorted(categories[cat], key=lambda e: e.order)
        print(f"\n  {cat}:")
        for entry in entries:
            numbered.append(entry)
            idx = len(numbered)
            print(f"    [{idx:2d}] {entry.display_name}")

    print(f"\n  Enter selection:")
    print(f"    Numbers/ranges : 1,3-5,13")
    print(f"    Category name  : Sketch Tools")
    print(f"    Run everything : all")
    print(f"    Quit           : q")
    print()

    try:
        raw = input("  > ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n  Cancelled.")
        return

    if not raw or raw.lower() == "q":
        print("  Cancelled.")
        return

    if raw.lower() == "all":
        selected = list(numbered)
    else:
        # Check if input matches a category name (case-insensitive)
        cat_match = None
        for cat in sorted_cats:
            if raw.lower() == cat.lower():
                cat_match = cat
                break

        if cat_match:
            selected = [e for e in numbered if e.category == cat_match]
        else:
            # Parse as numbers/ranges: "1,3-5,13"
            indices = set()
            for part in raw.split(","):
                part = part.strip()
                if "-" in part:
                    try:
                        lo, hi = part.split("-", 1)
                        for i in range(int(lo), int(hi) + 1):
                            indices.add(i)
                    except ValueError:
                        print(f"  Invalid range: {part}")
                        return
                else:
                    try:
                        indices.add(int(part))
                    except ValueError:
                        print(f"  Invalid input: {part}")
                        return

            selected = []
            for idx in sorted(indices):
                if 1 <= idx <= len(numbered):
                    selected.append(numbered[idx - 1])
                else:
                    print(f"  Index out of range: {idx}")
                    return

    if not selected:
        print("  No tests selected.")
        return

    print(f"\n  Running {len(selected)} test(s)...\n")
    success = run_selected_tests(selected)
    sys.exit(0 if success else 1)


# ===========================================================================
# CLI entry point
# ===========================================================================

def list_tests():
    """Print all registered tests grouped by category."""
    categories = {}
    for entry in TEST_REGISTRY:
        categories.setdefault(entry.category, []).append(entry)

    sorted_cats = sorted(categories.keys(),
                         key=lambda c: CATEGORY_ORDER.index(c) if c in CATEGORY_ORDER else 999)

    for cat in sorted_cats:
        entries = sorted(categories[cat], key=lambda e: e.order)
        print(f"\n  {cat}:")
        for e in entries:
            print(f"    {e.name:30s} {e.description}")


def main():
    parser = argparse.ArgumentParser(description="SolidWorks MCP Test Suite")
    parser.add_argument("--gui", action="store_true",
                        help="Launch interactive CLI test picker")
    parser.add_argument("--category", type=str, default=None,
                        help="Run only tests in this category")
    parser.add_argument("--test", type=str, default=None,
                        help="Run a single test by name")
    parser.add_argument("--list", action="store_true",
                        help="List all available tests and exit")
    args = parser.parse_args()

    if args.list:
        list_tests()
        sys.exit(0)

    if args.gui:
        interactive_selector()
        return

    # Determine which tests to run
    if args.test:
        selected = [e for e in TEST_REGISTRY if e.name == args.test]
        if not selected:
            print(f"  Unknown test: {args.test}")
            print("  Use --list to see available tests.")
            sys.exit(1)
    elif args.category:
        selected = [e for e in TEST_REGISTRY
                    if e.category.lower() == args.category.lower()]
        if not selected:
            print(f"  Unknown category: {args.category}")
            print("  Available: " + ", ".join(CATEGORY_ORDER))
            sys.exit(1)
        selected.sort(key=lambda e: e.order)
    else:
        # Run all tests in category order, then by test order
        selected = sorted(TEST_REGISTRY,
                          key=lambda e: (CATEGORY_ORDER.index(e.category)
                                         if e.category in CATEGORY_ORDER else 999,
                                         e.order))

    success = run_selected_tests(selected)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
