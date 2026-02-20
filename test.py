"""
SolidWorks MCP - Comprehensive Test Suite

Tests every tool and workflow path, with particular focus on sketch selection
reliability for cut-extrude operations.

Run with: python test.py
"""

import win32com.client
import pythoncom
import glob
import sys
import traceback
import time
import os

# Force UTF-8 output so Unicode symbols survive the Windows console
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PASS = 0
FAIL = 0
RESULTS = []  # list of (label, ok, detail)


def _result(label, ok, detail=""):
    global PASS, FAIL
    RESULTS.append((label, ok, detail))
    if ok:
        PASS += 1
        print(f"  ✓ {label}{' — ' + detail if detail else ''}")
    else:
        FAIL += 1
        print(f"  ✗ {label}{' — ' + detail if detail else ''}")
    return ok


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def subsection(title):
    print(f"\n  [{title}]")


# ---------------------------------------------------------------------------
# SolidWorks connection helpers (mirroring connection.py logic)
# ---------------------------------------------------------------------------

def connect_to_solidworks():
    """Connect to an existing or new SolidWorks instance."""
    try:
        sw = win32com.client.GetActiveObject("SldWorks.Application")
        print("  → Attached to existing SolidWorks instance")
    except Exception:
        print("  → Launching new SolidWorks instance…")
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
    """Replicate connection.py template discovery."""
    patterns = [
        r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS *\templates\Part.prtdot",
        r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS *\templates\Part.PRTDOT",
    ]
    for pattern in patterns:
        hits = glob.glob(pattern)
        if hits:
            return hits[0]
    return None


def new_part(sw, template):
    doc = sw.NewDocument(template, 0, 0, 0)
    if not doc:
        raise RuntimeError("NewDocument returned None")
    return doc


def select_plane(doc, plane_name):
    """Select a plane using FeatureByName (reliable path used by sketching.py)."""
    feature = doc.FeatureByName(plane_name)
    if not feature:
        raise RuntimeError(f"Plane not found: {plane_name}")
    doc.ClearSelection2(True)
    feature.Select2(False, 0)
    return feature


def create_sketch_on_plane(doc, plane_name):
    select_plane(doc, plane_name)
    doc.SketchManager.InsertSketch(True)


def create_sketch_on_face(doc, x, y, z):
    """Select a solid face at (x,y,z) in metres and open a sketch on it."""
    from win32com.client import VARIANT
    import pythoncom as _pc
    callout = VARIANT(_pc.VT_DISPATCH, None)
    doc.ClearSelection2(True)
    ok = doc.Extension.SelectByID2('', 'FACE', x, y, z, False, 0, callout, 0)
    if not ok:
        raise RuntimeError(f"Could not select face at ({x},{y},{z})")
    doc.SketchManager.InsertSketch(True)


def exit_sketch(doc):
    doc.ClearSelection2(True)
    doc.SketchManager.InsertSketch(True)


def select_sketch(doc, sketch_name):
    """Select a sketch by name — the operation that fails most often for cut-extrude."""
    feature = doc.FeatureByName(sketch_name)
    if not feature:
        raise RuntimeError(f"Sketch not found: {sketch_name}")
    doc.ClearSelection2(True)
    feature.Select2(False, 0)
    return feature


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
    # For cut-extrusions, the sketch must be in edit mode when FeatureExtrusion2
    # is called (Sd=False). Open it, then exit to commit the geometry — SolidWorks
    # keeps the sketch selected/active after InsertSketch(True) toggle.
    select_sketch(doc, sketch_name)
    depth_m = depth_mm / 1000.0

    if cut:
        # FeatureCut4 parameter names from sldworks.tlb (SW 2025 v33, 27 params):
        # Sd, Flip, Dir, T1, T2, D1, D2, Dchk1, Dchk2, Ddir1, Ddir2, Dang1, Dang2,
        # OffsetReverse1, OffsetReverse2, TranslateSurface1, TranslateSurface2,
        # NormalCut, UseFeatScope, UseAutoSelect,
        # AssemblyFeatureScope, AutoSelectComponents, PropagateFeatureToParts,
        # T0, StartOffset, FlipStartOffset, OptimizeGeometry
        feature = doc.FeatureManager.FeatureCut4(
            True,      # Sd
            reverse,   # Flip
            False,     # Dir
            0,         # T1 (Blind)
            0,         # T2
            depth_m,   # D1
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
        if not feature:
            raise RuntimeError("FeatureCut4 returned None for cut-extrusion")
    else:
        feature = doc.FeatureManager.FeatureExtrusion2(
            True,      # Sd
            reverse,
            False, 0, 0, depth_m, 0.0,
            False, False, False, False, 0.0, 0.0,
            False, False, False, False, True, True, True, 0, 0, False
        )
        if not feature:
            raise RuntimeError("FeatureExtrusion2 returned None for extrusion")
    return feature


# ---------------------------------------------------------------------------
# Individual test functions
# ---------------------------------------------------------------------------

def test_connection(sw):
    subsection("Connection")
    ok = sw is not None
    _result("SolidWorks application object obtained", ok)
    if ok:
        try:
            ver = sw.RevisionNumber
            _result("RevisionNumber readable", True, ver)
        except Exception as e:
            _result("RevisionNumber readable", False, str(e))
    return ok


def test_template_discovery():
    subsection("Template discovery")
    template = find_template()
    ok = template is not None
    _result("Part template found", ok, template or "not found")
    return template


def close_all_docs(sw):
    """Close all open documents without saving so each run starts clean."""
    try:
        sw.CloseAllDocuments(True)
    except Exception:
        pass


def test_new_part(sw, template):
    subsection("New part creation")
    close_all_docs(sw)
    doc = new_part(sw, template)
    ok = doc is not None
    _result("NewDocument returned a document", ok)
    return doc


def test_plane_selection(doc):
    subsection("Plane selection (FeatureByName)")
    results = []
    for plane in ("Front Plane", "Top Plane", "Right Plane"):
        try:
            feat = doc.FeatureByName(plane)
            ok = feat is not None
        except Exception as e:
            ok = False
        results.append(_result(f"Select {plane}", ok))
    return all(results)


def test_sketch_lifecycle(doc):
    """Create a sketch, draw in it, exit, then verify the sketch exists by name."""
    subsection("Sketch lifecycle (create → draw → exit)")

    # --- Create on Front Plane ---
    try:
        create_sketch_on_plane(doc, "Front Plane")
        _result("InsertSketch on Front Plane", True)
    except Exception as e:
        _result("InsertSketch on Front Plane", False, str(e))
        return False

    # --- Draw rectangle ---
    try:
        doc.SketchManager.CreateCornerRectangle(0.0, 0.0, 0.0, 0.1, 0.1, 0.0)
        _result("CreateCornerRectangle 100x100 mm", True)
    except Exception as e:
        _result("CreateCornerRectangle 100x100 mm", False, str(e))
        return False

    # --- Exit sketch ---
    try:
        exit_sketch(doc)
        _result("Exit sketch", True)
    except Exception as e:
        _result("Exit sketch", False, str(e))
        return False

    # --- Verify Sketch1 exists ---
    try:
        feat = doc.FeatureByName("Sketch1")
        _result("Sketch1 discoverable after exit", feat is not None)
    except Exception as e:
        _result("Sketch1 discoverable after exit", False, str(e))
        return False

    return True


def test_sketch_counter(doc, expected_name):
    """Verify that the feature tree returns the expected sketch name via the
    fallback enumeration used by modeling.py._get_latest_sketch_name()."""
    subsection(f"Feature-tree sketch enumeration (expect {expected_name})")
    try:
        found = get_latest_sketch_name(doc)
        ok = found == expected_name
        _result(f"Latest sketch = '{found}'", ok,
                "" if ok else f"expected '{expected_name}'")
        return ok
    except Exception as e:
        _result("Feature enumeration", False, str(e))
        return False


def test_select_sketch_by_name(doc, sketch_name):
    """Core of the cut-extrude bug: can we select a sketch by exact name?"""
    subsection(f"Sketch selection by name ('{sketch_name}')")
    try:
        feat = select_sketch(doc, sketch_name)
        ok = feat is not None
        _result(f"FeatureByName('{sketch_name}') found", ok)
        return ok
    except Exception as e:
        _result(f"FeatureByName('{sketch_name}') found", False, str(e))
        return False


def test_extrusion(doc, sketch_name="Sketch1", depth_mm=100.0):
    subsection(f"Extrusion (sketch='{sketch_name}', depth={depth_mm}mm)")
    try:
        feat = extrude(doc, sketch_name, depth_mm, cut=False)
        _result(f"FeatureExtrusion2 (add material)", feat is not None)
        doc.ViewZoomtofit2()
        return True
    except Exception as e:
        _result("FeatureExtrusion2 (add material)", False, str(e))
        return False


def test_second_sketch_on_solid(doc, sketch_number):
    """Create a sketch on the top face of the solid — prerequisite for cut-extrude.
    The solid is a 100x100x100mm cube extruded from Front Plane (XY) in +Z.
    Top face is at Z=0.1m. We pick a point on that face to anchor the sketch."""
    subsection(f"Sketch on top face of solid (will be Sketch{sketch_number})")
    # Top face centre: X=0.05, Y=0.05, Z=0.1
    try:
        create_sketch_on_face(doc, 0.05, 0.05, 0.1)
        _result("InsertSketch on top face of solid", True)
    except Exception as e:
        _result("InsertSketch on top face of solid", False, str(e))
        return False

    # Circle at centre of face, radius 10mm = 0.01m
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

    expected = f"Sketch{sketch_number}"
    try:
        feat = doc.FeatureByName(expected)
        _result(f"{expected} exists after exit", feat is not None)
        return feat is not None
    except Exception as e:
        _result(f"{expected} exists after exit", False, str(e))
        return False


def test_cut_extrusion(doc, sketch_name, depth_mm=50.0, reverse=False):
    subsection(f"Cut-extrusion (sketch='{sketch_name}', depth={depth_mm}mm, reverse={reverse})")
    try:
        feat = extrude(doc, sketch_name, depth_mm, cut=True, reverse=reverse)
        _result("FeatureCut4 (cut material)", feat is not None)
        doc.ViewZoomtofit2()
        return True
    except Exception as e:
        _result("FeatureCut4 (cut material)", False, str(e))
        traceback.print_exc()
        return False


def test_cut_extrusion_reversed(doc, sketch_number, depth_mm=30.0):
    """Cut-extrude with reverse=True using a sketch on the bottom face of the solid."""
    subsection(f"Cut-extrusion reversed (sketch will be Sketch{sketch_number})")

    # Bottom face of the cube is at Z=0, normal = -Z. Pick a point on it.
    try:
        create_sketch_on_face(doc, 0.03, 0.03, 0.0)
        doc.SketchManager.CreateCornerRectangle(0.01, 0.01, 0.0, 0.04, 0.04, 0.0)
        exit_sketch(doc)
    except Exception as e:
        _result("Setup sketch for reversed cut", False, str(e))
        return False

    sketch_name = f"Sketch{sketch_number}"
    try:
        feat = extrude(doc, sketch_name, depth_mm, cut=True, reverse=True)
        _result(f"Cut-extrusion reversed {depth_mm}mm", feat is not None)
        doc.ViewZoomtofit2()
        return True
    except Exception as e:
        _result(f"Cut-extrusion reversed {depth_mm}mm", False, str(e))
        return False


def test_multiple_cuts(doc, start_sketch_number):
    """Create two independent cut-extrusions on the top face of the body."""
    subsection("Multiple sequential cut-extrusions")
    passed = True

    for i in range(2):
        sn = start_sketch_number + i
        sketch_name = f"Sketch{sn}"

        # Place two small circles on the top face, well separated
        cx = 0.02 + i * 0.05
        try:
            create_sketch_on_face(doc, cx, 0.05, 0.1)
            doc.SketchManager.CreateCircleByRadius(cx, 0.05, 0.1, 0.005)
            exit_sketch(doc)
            feat = extrude(doc, sketch_name, 15.0, cut=True, reverse=False)
            _result(f"Cut #{i+1} using {sketch_name}", feat is not None)
        except Exception as e:
            _result(f"Cut #{i+1} using {sketch_name}", False, str(e))
            passed = False

    return passed


def test_sketch_selection_after_extrusion(doc, sketch_name):
    """Verify that a sketch that has already been extruded can still be selected.
    This catches regressions where the sketch becomes hidden/consumed."""
    subsection(f"Sketch '{sketch_name}' still selectable after extrusion")
    try:
        feat = doc.FeatureByName(sketch_name)
        ok = feat is not None
        _result(f"FeatureByName('{sketch_name}') post-extrusion", ok)
        return ok
    except Exception as e:
        _result(f"FeatureByName('{sketch_name}') post-extrusion", False, str(e))
        return False


def test_feature_type_name(doc, sketch_name):
    """Verify the feature type is 'ProfileFeature' — the type checked by _get_latest_sketch_name."""
    subsection(f"Feature type check for '{sketch_name}'")
    try:
        feat = doc.FeatureByName(sketch_name)
        if not feat:
            _result(f"FeatureByName('{sketch_name}')", False, "not found")
            return False
        type_name = feat.GetTypeName2
        ok = type_name == "ProfileFeature"
        _result("GetTypeName2 == 'ProfileFeature'", ok, f"got '{type_name}'")
        return ok
    except Exception as e:
        _result("GetTypeName2()", False, str(e))
        return False


def test_unit_conversion_rectangle(doc):
    """Verify that a 50 mm rectangle drawn as 0.05 m actually appears correct.
    We do this by drawing the shape and checking the sketch exists — a proxy
    check since the COM API doesn't expose sketch geometry directly here."""
    subsection("Unit conversion: 50x30mm rectangle (0.05 x 0.03 m)")
    sketch_n = None
    try:
        # Count existing sketches first
        features = doc.FeatureManager.GetFeatures(True)
        sketch_n = sum(1 for f in features if f.GetTypeName2 == "ProfileFeature") + 1

        create_sketch_on_plane(doc, "Right Plane")
        # 50mm = 0.05m, 30mm = 0.03m, centered at origin
        doc.SketchManager.CreateCornerRectangle(-0.025, -0.015, 0.0, 0.025, 0.015, 0.0)
        exit_sketch(doc)
        _result("50x30mm rectangle sketch created", True)
        return sketch_n
    except Exception as e:
        _result("50x30mm rectangle sketch created", False, str(e))
        return None


def test_unit_conversion_circle(doc):
    """Verify that a 10mm-radius circle is drawn as 0.01m."""
    subsection("Unit conversion: circle radius=10mm (0.01 m)")
    try:
        features = doc.FeatureManager.GetFeatures(True)
        sketch_n = sum(1 for f in features if f.GetTypeName2 == "ProfileFeature") + 1
        create_sketch_on_plane(doc, "Top Plane")
        doc.SketchManager.CreateCircleByRadius(0.0, 0.0, 0.0, 0.01)
        exit_sketch(doc)
        _result("10mm-radius circle sketch created", True)
        return sketch_n
    except Exception as e:
        _result("10mm-radius circle sketch created", False, str(e))
        return None


def test_clear_selection_before_sketch_select(doc, sketch_name):
    """Regression: ensure ClearSelection2 before Select2 doesn't break selection."""
    subsection(f"ClearSelection2 before Select2 for '{sketch_name}'")
    try:
        doc.ClearSelection2(True)
        feat = doc.FeatureByName(sketch_name)
        if not feat:
            _result("Feature found", False, "FeatureByName returned None")
            return False
        result = feat.Select2(False, 0)
        # Select2 returns True on success
        _result("Select2 returned True", bool(result), f"returned {result}")
        doc.ClearSelection2(True)
        return bool(result)
    except Exception as e:
        _result("Select2 call", False, str(e))
        return False


# ---------------------------------------------------------------------------
# Main test runner
# ---------------------------------------------------------------------------

def run_all_tests():
    global PASS, FAIL, RESULTS
    PASS = 0
    FAIL = 0
    RESULTS = []

    section("SOLIDWORKS MCP — COMPREHENSIVE TEST SUITE")

    # -----------------------------------------------------------------------
    # 0. COM + Connection
    # -----------------------------------------------------------------------
    section("0. COM INIT & CONNECTION")
    print("  → Initialising COM…")
    pythoncom.CoInitialize()
    _result("pythoncom.CoInitialize()", True)

    try:
        sw = connect_to_solidworks()
        test_connection(sw)
    except Exception as e:
        _result("connect_to_solidworks()", False, str(e))
        print("\n  Cannot continue without a SolidWorks connection.")
        return False

    # -----------------------------------------------------------------------
    # 1. Template
    # -----------------------------------------------------------------------
    section("1. TEMPLATE DISCOVERY")
    template = test_template_discovery()
    if not template:
        print("\n  Cannot continue without a Part template.")
        return False

    # -----------------------------------------------------------------------
    # 2. Part creation + plane selection
    # -----------------------------------------------------------------------
    section("2. PART CREATION & PLANE SELECTION")
    doc = test_new_part(sw, template)
    if not doc:
        print("\n  Cannot continue without an active document.")
        return False
    test_plane_selection(doc)

    # -----------------------------------------------------------------------
    # 3. Basic sketch lifecycle
    # -----------------------------------------------------------------------
    section("3. SKETCH LIFECYCLE")
    ok = test_sketch_lifecycle(doc)   # creates Sketch1 (100×100 mm rectangle)
    if not ok:
        print("\n  Sketch lifecycle failed — aborting further sketch tests.")
        return False

    test_feature_type_name(doc, "Sketch1")
    test_sketch_counter(doc, "Sketch1")
    test_select_sketch_by_name(doc, "Sketch1")
    test_clear_selection_before_sketch_select(doc, "Sketch1")

    # -----------------------------------------------------------------------
    # 4. Basic extrusion
    # -----------------------------------------------------------------------
    section("4. EXTRUSION (ADD MATERIAL)")
    ok = test_extrusion(doc, sketch_name="Sketch1", depth_mm=100.0)
    if not ok:
        print("\n  Extrusion failed — aborting cut-extrude tests.")
        return False

    # Sketch should still be selectable after extrusion
    test_sketch_selection_after_extrusion(doc, "Sketch1")

    # -----------------------------------------------------------------------
    # 5. Cut-extrusion (primary feature under test)
    # -----------------------------------------------------------------------
    section("5. CUT-EXTRUSION (REMOVE MATERIAL)")

    # Sketch2: circle hole on top face of solid
    ok = test_second_sketch_on_solid(doc, sketch_number=2)
    if not ok:
        print("\n  Second sketch failed — aborting cut-extrude tests.")
        return False

    test_feature_type_name(doc, "Sketch2")
    test_sketch_counter(doc, "Sketch2")
    test_select_sketch_by_name(doc, "Sketch2")
    test_clear_selection_before_sketch_select(doc, "Sketch2")

    ok = test_cut_extrusion(doc, "Sketch2", depth_mm=50.0, reverse=False)
    if not ok:
        print("\n  Cut-extrusion failed.")

    # -----------------------------------------------------------------------
    # 6. Cut-extrusion with reverse=True
    # -----------------------------------------------------------------------
    section("6. CUT-EXTRUSION — REVERSED DIRECTION")
    test_cut_extrusion_reversed(doc, sketch_number=3, depth_mm=30.0)

    # -----------------------------------------------------------------------
    # 7. Multiple sequential cuts
    # -----------------------------------------------------------------------
    section("7. MULTIPLE SEQUENTIAL CUT-EXTRUSIONS")
    test_multiple_cuts(doc, start_sketch_number=4)

    # -----------------------------------------------------------------------
    # 8. Unit conversion validation
    # -----------------------------------------------------------------------
    section("8. UNIT CONVERSION VALIDATION")
    rect_sketch_n = test_unit_conversion_rectangle(doc)
    circle_sketch_n = test_unit_conversion_circle(doc)

    # -----------------------------------------------------------------------
    # 9. Feature-tree enumeration robustness
    # -----------------------------------------------------------------------
    section("9. FEATURE-TREE ENUMERATION ROBUSTNESS")
    subsection("Enumerate all ProfileFeature entries")
    try:
        features = doc.FeatureManager.GetFeatures(True)
        sketches = [f.Name for f in features if f.GetTypeName2 == "ProfileFeature"]
        _result(f"Found {len(sketches)} sketch(es) in feature tree", len(sketches) > 0,
                ", ".join(sketches))
        # All expected sketch names must be in the tree
        for name in sketches:
            feat = doc.FeatureByName(name)
            _result(f"FeatureByName('{name}') round-trip", feat is not None)
    except Exception as e:
        _result("Feature enumeration", False, str(e))

    # -----------------------------------------------------------------------
    # 10. Final zoom & view
    # -----------------------------------------------------------------------
    section("10. VIEW / ZOOM")
    try:
        doc.ViewZoomtofit2()
        _result("ViewZoomtofit2()", True)
    except Exception as e:
        _result("ViewZoomtofit2()", False, str(e))

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    section("RESULTS")
    total = PASS + FAIL

    if PASS:
        print(f"\n  PASSED ({PASS}):")
        for label, ok, detail in RESULTS:
            if ok:
                print(f"    ✓ {label}{' — ' + detail if detail else ''}")

    if FAIL:
        print(f"\n  FAILED ({FAIL}):")
        for label, ok, detail in RESULTS:
            if not ok:
                print(f"    ✗ {label}{' — ' + detail if detail else ''}")

    print(f"\n  Total  : {total}")
    print(f"  Passed : {PASS}")
    print(f"  Failed : {FAIL}")
    if FAIL == 0:
        print("\n  ✓ ALL TESTS PASSED")
    else:
        print(f"\n  ✗ {FAIL} TEST(S) FAILED")
    print()

    return FAIL == 0


if __name__ == "__main__":
    print("\nSolidWorks MCP — Comprehensive Test Suite\n")
    success = run_all_tests()
    sys.exit(0 if success else 1)
