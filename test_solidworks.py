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


if __name__ == "__main__":
    print("\nStarting test...\n")
    success = test_solidworks()
    
    if success:
        print("\n✓ SUCCESS!")
    else:
        print("\n❌ FAILED!")
    
    input("\nPress Enter to exit...")
    sys.exit(0 if success else 1)