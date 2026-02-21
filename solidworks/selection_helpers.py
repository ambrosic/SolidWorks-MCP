"""
SolidWorks Selection Helpers
Shared utilities for selecting edges, faces, planes, features, and axes.
All coordinate inputs are in millimeters; converted to meters internally.
"""

import logging
import win32com.client
import pythoncom

logger = logging.getLogger(__name__)


def make_callout():
    """Create the standard VT_DISPATCH None callout used in SelectByID2."""
    return win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)


def clear_selection(doc):
    """Clear all selections."""
    doc.ClearSelection2(True)


def select_face(doc, x_mm, y_mm, z_mm, append=False, mark=0):
    """Select a face at the given point (mm). Returns True/False."""
    callout = make_callout()
    ok = doc.Extension.SelectByID2(
        "", "FACE",
        x_mm / 1000.0, y_mm / 1000.0, z_mm / 1000.0,
        append, mark, callout, 0
    )
    if not ok:
        logger.warning(f"Failed to select face at ({x_mm}, {y_mm}, {z_mm}) mm")
    return ok


def select_edge(doc, x_mm, y_mm, z_mm, append=False, mark=0):
    """Select an edge at the given point (mm). Returns True/False."""
    callout = make_callout()
    ok = doc.Extension.SelectByID2(
        "", "EDGE",
        x_mm / 1000.0, y_mm / 1000.0, z_mm / 1000.0,
        append, mark, callout, 0
    )
    if not ok:
        logger.warning(f"Failed to select edge at ({x_mm}, {y_mm}, {z_mm}) mm")
    return ok


def select_multiple_edges(doc, edge_points, mark=1):
    """Select multiple edges from a list of {x, y, z} dicts (mm).

    Args:
        doc: SolidWorks document COM object
        edge_points: list of dicts with x, y, z keys (mm)
        mark: mark value for selection (default 1)
    Returns:
        Number of successfully selected edges
    """
    count = 0
    for i, pt in enumerate(edge_points):
        append = i > 0
        if select_edge(doc, pt["x"], pt["y"], pt["z"], append=append, mark=mark):
            count += 1
    return count


def select_multiple_faces(doc, face_points, mark=0):
    """Select multiple faces from a list of {x, y, z} dicts (mm).

    Args:
        doc: SolidWorks document COM object
        face_points: list of dicts with x, y, z keys (mm)
        mark: mark value for selection (default 0)
    Returns:
        Number of successfully selected faces
    """
    count = 0
    for i, pt in enumerate(face_points):
        append = i > 0
        if select_face(doc, pt["x"], pt["y"], pt["z"], append=append, mark=mark):
            count += 1
    return count


def select_plane(doc, plane_name):
    """Select a reference plane by name ('Front', 'Top', 'Right', or custom).
    Returns True/False.
    """
    # Map short names to SolidWorks full names
    plane_map = {
        "Front": "Front Plane",
        "Top": "Top Plane",
        "Right": "Right Plane",
        "Front Plane": "Front Plane",
        "Top Plane": "Top Plane",
        "Right Plane": "Right Plane",
    }
    full_name = plane_map.get(plane_name, plane_name)

    feature = doc.FeatureByName(full_name)
    if not feature:
        logger.warning(f"Plane '{full_name}' not found")
        return False
    doc.ClearSelection2(True)
    return feature.Select2(False, 0)


def select_plane_with_mark(doc, plane_name, mark=0, append=False):
    """Select a reference plane by name with a specific mark value.
    Uses SelectByID2 for mark support.
    Returns True/False.
    """
    plane_map = {
        "Front": "Front Plane",
        "Top": "Top Plane",
        "Right": "Right Plane",
        "Front Plane": "Front Plane",
        "Top Plane": "Top Plane",
        "Right Plane": "Right Plane",
    }
    full_name = plane_map.get(plane_name, plane_name)
    callout = make_callout()
    ok = doc.Extension.SelectByID2(
        full_name, "DATUMPLANE",
        0, 0, 0,
        append, mark, callout, 0
    )
    if not ok:
        logger.warning(f"Failed to select plane '{full_name}' with mark={mark}")
    return ok


def select_feature(doc, feature_name, mark=0, append=False):
    """Select a feature by name in the feature tree.
    Returns True/False.
    """
    callout = make_callout()
    ok = doc.Extension.SelectByID2(
        feature_name, "BODYFEATURE",
        0, 0, 0,
        append, mark, callout, 0
    )
    if not ok:
        logger.warning(f"Failed to select feature '{feature_name}'")
    return ok


def select_multiple_features(doc, feature_names, mark=4):
    """Select multiple features by name.

    Args:
        doc: SolidWorks document COM object
        feature_names: list of feature name strings
        mark: mark value for selection (default 4 for pattern operations)
    Returns:
        Number of successfully selected features
    """
    count = 0
    for i, name in enumerate(feature_names):
        append = i > 0
        if select_feature(doc, name, mark=mark, append=append):
            count += 1
    return count


def select_sketch(doc, sketch_name, mark=0, append=False):
    """Select a sketch by name for sweep/loft operations.
    Returns True/False.
    """
    callout = make_callout()
    ok = doc.Extension.SelectByID2(
        sketch_name, "SKETCH",
        0, 0, 0,
        append, mark, callout, 0
    )
    if not ok:
        logger.warning(f"Failed to select sketch '{sketch_name}'")
    return ok


def select_axis(doc, axis_name, mark=0, append=False):
    """Select a reference axis by name.
    Returns True/False.
    """
    callout = make_callout()
    ok = doc.Extension.SelectByID2(
        axis_name, "AXIS",
        0, 0, 0,
        append, mark, callout, 0
    )
    if not ok:
        logger.warning(f"Failed to select axis '{axis_name}'")
    return ok


def select_axis_by_point(doc, x_mm, y_mm, z_mm, mark=0, append=False):
    """Select an axis by a point near it (mm).
    Returns True/False.
    """
    callout = make_callout()
    ok = doc.Extension.SelectByID2(
        "", "AXIS",
        x_mm / 1000.0, y_mm / 1000.0, z_mm / 1000.0,
        append, mark, callout, 0
    )
    if not ok:
        logger.warning(f"Failed to select axis at ({x_mm}, {y_mm}, {z_mm}) mm")
    return ok


def select_vertex(doc, x_mm, y_mm, z_mm, mark=0, append=False):
    """Select a vertex at the given point (mm).
    Returns True/False.
    """
    callout = make_callout()
    ok = doc.Extension.SelectByID2(
        "", "VERTEX",
        x_mm / 1000.0, y_mm / 1000.0, z_mm / 1000.0,
        append, mark, callout, 0
    )
    if not ok:
        logger.warning(f"Failed to select vertex at ({x_mm}, {y_mm}, {z_mm}) mm")
    return ok


def exit_sketch_and_select(doc, sketch_name):
    """Exit the current sketch and select it by name for feature creation.
    Returns the sketch feature or raises an exception.
    """
    doc.ClearSelection2(True)
    doc.SketchManager.InsertSketch(True)

    sketch_feature = doc.FeatureByName(sketch_name)
    if not sketch_feature:
        raise Exception(f"Sketch '{sketch_name}' not found in feature tree")

    doc.ClearSelection2(True)
    sketch_feature.Select2(False, 0)
    return sketch_feature
