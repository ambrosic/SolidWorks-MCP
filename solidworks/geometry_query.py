"""
SolidWorks Geometry Query Tools
Enumerate faces, edges, vertices, and body properties for model inspection.

COM binding notes (pywin32 late binding with SolidWorks 2025):
  - Most IEdge/IFace2/ISurface getters are accessed as PROPERTIES (no parens):
    edge.GetStartVertex, vertex.GetPoint, face.GetArea, face.Normal,
    face.GetUVBounds, face.GetSurface, face.GetEdges, face.GetEdgeCount,
    surface.Identity, surface.PlaneParams, edge.GetCurveParams2, edge.GetCurve
  - Methods that take arguments use parens:
    body.GetBodyBox(), body.GetFaces(), body.GetEdges(),
    edge.GetClosestPointOn(x,y,z), curve.GetLength2(t1,t2),
    surface.Evaluate(u,v,0,0), curve.Evaluate2(t,0)
"""

import logging
from mcp.types import Tool
from . import selection_helpers as sel

logger = logging.getLogger(__name__)

# Surface type constants from ISurface::Identity
SURFACE_TYPES = {
    4001: "Planar",
    4002: "Cylindrical",
    4003: "Conical",
    4004: "Spherical",
    4005: "Toroidal",
    4006: "BSpline",
    4007: "Blend",
    4008: "Offset",
    4009: "Extrusion",
}

SURFACE_TYPE_FILTER = {
    "PLANE": 4001,
    "CYLINDER": 4002,
    "CONE": 4003,
    "SPHERE": 4004,
    "TORUS": 4005,
    "BSPLINE": 4006,
}


class GeometryQueryTools:
    """Geometry inspection tools for querying faces, edges, vertices, and body info."""

    def __init__(self, connection):
        self.connection = connection

    def get_tool_definitions(self) -> list[Tool]:
        return [
            Tool(
                name="solidworks_get_body_info",
                description="Get a high-level overview of the active part body: bounding box dimensions, face count, edge count, and vertex count. Use this as a quick check of model state before querying individual faces or edges.",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            Tool(
                name="solidworks_get_faces",
                description="Enumerate all faces on the active part body. Returns each face's surface type, area, normal/axis info, a sample point (usable for selection in fillet/chamfer/shell/draft), and edge count. Use the optional surfaceType filter to narrow results.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "surfaceType": {
                            "type": "string",
                            "enum": ["PLANE", "CYLINDER", "CONE", "SPHERE", "TORUS", "BSPLINE"],
                            "description": "Optional: filter faces by surface type. If omitted, returns all faces."
                        }
                    }
                }
            ),
            Tool(
                name="solidworks_get_edges",
                description="Enumerate all edges on the active part body. Returns each edge's type (Line/Circle/Arc/Curve), start and end vertex coordinates, a midpoint (usable for selection in fillet/chamfer/pattern direction), and length. Use the optional edgeType filter to narrow results.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "edgeType": {
                            "type": "string",
                            "enum": ["LINE", "CIRCLE", "ARC", "ELLIPSE", "SPLINE"],
                            "description": "Optional: filter edges by curve type. If omitted, returns all edges."
                        }
                    }
                }
            ),
            Tool(
                name="solidworks_get_face_edges",
                description="Get detailed information about a specific face and its bounding edges. Select the face by providing a 3D point on or near it. Returns face properties and each edge's endpoints and midpoint. Use this to drill down into a face found via get_faces.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "x": {"type": "number", "description": "X coordinate on/near the face (mm)"},
                        "y": {"type": "number", "description": "Y coordinate on/near the face (mm)"},
                        "z": {"type": "number", "description": "Z coordinate on/near the face (mm)"}
                    },
                    "required": ["x", "y", "z"]
                }
            ),
            Tool(
                name="solidworks_get_vertices",
                description="List all unique vertex (corner) positions on the active part body. Returns 3D coordinates in mm, sorted by (x, y, z). Useful for understanding model geometry and as reference points.",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
        ]

    def execute(self, tool_name: str, args: dict) -> str:
        self.connection.ensure_connection()
        dispatch = {
            "solidworks_get_body_info": lambda: self.get_body_info(),
            "solidworks_get_faces": lambda: self.get_faces(args),
            "solidworks_get_edges": lambda: self.get_edges(args),
            "solidworks_get_face_edges": lambda: self.get_face_edges(args),
            "solidworks_get_vertices": lambda: self.get_vertices(),
        }
        handler = dispatch.get(tool_name)
        if not handler:
            raise Exception(f"Unknown geometry query tool: {tool_name}")
        return handler()

    # --- Helper methods ---

    def _get_bodies(self, doc):
        """Get solid bodies from the active document."""
        doc.ForceRebuild3(True)
        bodies = doc.GetBodies2(0, True)  # 0 = swSolidBody
        if not bodies:
            raise Exception("No solid bodies found in the active document")
        return bodies

    def _face_sample_point(self, face):
        """Compute a reliable sample point on a face using UV midpoint evaluation.
        Returns (x_mm, y_mm, z_mm).
        """
        try:
            uv = face.GetUVBounds  # property: (umin, umax, vmin, vmax)
            u_mid = (uv[0] + uv[1]) / 2.0
            v_mid = (uv[2] + uv[3]) / 2.0
            surface = face.GetSurface  # property: ISurface COM object
            result = surface.Evaluate(u_mid, v_mid, 0, 0)  # method: returns (x,y,z,...)
            return (result[0] * 1000.0, result[1] * 1000.0, result[2] * 1000.0)
        except Exception:
            return self._face_centroid_from_edges(face)

    def _face_centroid_from_edges(self, face):
        """Fallback: approximate face centroid by averaging edge vertex positions."""
        edges = face.GetEdges  # property: tuple of edge COM objects
        if not edges:
            return (0.0, 0.0, 0.0)
        pts = []
        for edge in edges:
            for v in (edge.GetStartVertex, edge.GetEndVertex):  # properties
                if v:
                    p = v.GetPoint  # property: (x, y, z) in meters
                    pts.append((p[0], p[1], p[2]))
        if not pts:
            return (0.0, 0.0, 0.0)
        n = len(pts)
        return (
            sum(p[0] for p in pts) / n * 1000.0,
            sum(p[1] for p in pts) / n * 1000.0,
            sum(p[2] for p in pts) / n * 1000.0,
        )

    def _edge_midpoint(self, edge):
        """Compute a selectable midpoint on an edge. Returns (x_mm, y_mm, z_mm)."""
        start_v = edge.GetStartVertex  # property: vertex COM object or None
        end_v = edge.GetEndVertex      # property: vertex COM object or None
        if start_v and end_v:
            sp = start_v.GetPoint  # property: (x, y, z) in meters
            ep = end_v.GetPoint
            mid_x = (sp[0] + ep[0]) / 2.0
            mid_y = (sp[1] + ep[1]) / 2.0
            mid_z = (sp[2] + ep[2]) / 2.0
            # Snap to actual edge for curved edges
            try:
                closest = edge.GetClosestPointOn(mid_x, mid_y, mid_z)  # method
                return (closest[0] * 1000.0, closest[1] * 1000.0, closest[2] * 1000.0)
            except Exception:
                return (mid_x * 1000.0, mid_y * 1000.0, mid_z * 1000.0)
        else:
            # Closed edge (circle etc.) -- use parametric midpoint
            try:
                params = edge.GetCurveParams2  # property: tuple
                t_mid = (params[6] + params[7]) / 2.0
                curve = edge.GetCurve  # property: ICurve COM object
                pt = curve.Evaluate2(t_mid, 0)  # method
                return (pt[0] * 1000.0, pt[1] * 1000.0, pt[2] * 1000.0)
            except Exception:
                try:
                    params = edge.GetCurveParams2
                    return (params[0] * 1000.0, params[1] * 1000.0, params[2] * 1000.0)
                except Exception:
                    return (0.0, 0.0, 0.0)

    def _edge_endpoints(self, edge):
        """Get start and end vertex coordinates.
        Returns ((sx,sy,sz), (ex,ey,ez)) in mm, or None for closed edges.
        """
        start_v = edge.GetStartVertex
        end_v = edge.GetEndVertex
        if start_v and end_v:
            sp = start_v.GetPoint
            ep = end_v.GetPoint
            return (
                (sp[0] * 1000.0, sp[1] * 1000.0, sp[2] * 1000.0),
                (ep[0] * 1000.0, ep[1] * 1000.0, ep[2] * 1000.0),
            )
        return None

    def _edge_length(self, edge):
        """Get edge length in mm."""
        try:
            params = edge.GetCurveParams2  # property
            curve = edge.GetCurve          # property
            length_m = curve.GetLength2(params[6], params[7])  # method
            return length_m * 1000.0
        except Exception:
            return 0.0

    def _edge_type_str(self, edge):
        """Classify edge curve type."""
        start_v = edge.GetStartVertex
        end_v = edge.GetEndVertex

        # Closed edge (no start/end vertex) = circle
        if not start_v or not end_v:
            return "Circle"

        sp = start_v.GetPoint
        ep = end_v.GetPoint
        try:
            params = edge.GetCurveParams2
            curve = edge.GetCurve
            arc_len = curve.GetLength2(params[6], params[7])
            chord_len = ((ep[0] - sp[0])**2 + (ep[1] - sp[1])**2 + (ep[2] - sp[2])**2)**0.5
            if chord_len > 0 and abs(arc_len - chord_len) / chord_len < 1e-6:
                return "Line"
            else:
                return "Arc"
        except Exception:
            return "Line"

    def _surface_type_str(self, face):
        """Get human-readable surface type string."""
        try:
            surface = face.GetSurface  # property
            identity = surface.Identity  # property
            return SURFACE_TYPES.get(identity, f"Unknown({identity})")
        except Exception:
            return "Unknown"

    def _surface_identity(self, face):
        """Get raw surface identity integer."""
        try:
            surface = face.GetSurface
            return surface.Identity
        except Exception:
            return -1

    def _surface_details(self, face):
        """Get type-specific surface details (normal for planes, axis+radius for cylinders)."""
        try:
            surface = face.GetSurface
            identity = surface.Identity
            if identity == 4001:  # Plane
                params = surface.PlaneParams  # property: (nx,ny,nz, px,py,pz)
                nx, ny, nz = params[0], params[1], params[2]
                return f"normal=({nx:.2f}, {ny:.2f}, {nz:.2f})"
            elif identity == 4002:  # Cylinder
                params = surface.CylinderParams  # property: (ox,oy,oz, ax,ay,az, radius)
                r_mm = params[6] * 1000.0
                ax, ay, az = params[3], params[4], params[5]
                return f"axis=({ax:.2f}, {ay:.2f}, {az:.2f}) radius={r_mm:.2f}"
            elif identity == 4003:  # Cone
                return "cone"
            elif identity == 4004:  # Sphere
                try:
                    params = surface.SphereParams
                    r_mm = params[3] * 1000.0
                    return f"radius={r_mm:.2f}"
                except Exception:
                    return "sphere"
            elif identity == 4005:  # Torus
                return "torus"
        except Exception:
            pass
        return ""

    def _count_unique_vertices(self, bodies):
        """Count unique vertices across all bodies."""
        coords = []
        for body in bodies:
            edges = body.GetEdges()  # method
            if not edges:
                continue
            for edge in edges:
                for v in (edge.GetStartVertex, edge.GetEndVertex):  # properties
                    if v:
                        p = v.GetPoint  # property
                        coords.append((p[0] * 1000.0, p[1] * 1000.0, p[2] * 1000.0))
        return len(self._deduplicate_points(coords))

    def _deduplicate_points(self, points, tolerance=1e-4):
        """Deduplicate points by coordinate proximity (tolerance in mm)."""
        unique = []
        for pt in points:
            is_dup = False
            for u in unique:
                if all(abs(a - b) < tolerance for a, b in zip(pt, u)):
                    is_dup = True
                    break
            if not is_dup:
                unique.append(pt)
        return unique

    def _format_edge_line(self, idx, edge):
        """Format a single edge as a compact one-liner."""
        etype = self._edge_type_str(edge)
        endpoints = self._edge_endpoints(edge)
        mid = self._edge_midpoint(edge)
        length = self._edge_length(edge)
        mid_str = f"({mid[0]:.2f}, {mid[1]:.2f}, {mid[2]:.2f})"

        if endpoints:
            s, e = endpoints
            start_str = f"({s[0]:.2f}, {s[1]:.2f}, {s[2]:.2f})"
            end_str = f"({e[0]:.2f}, {e[1]:.2f}, {e[2]:.2f})"
            return f"  [{idx}] {etype} | {start_str}-{end_str} | mid={mid_str} | length={length:.2f}"
        else:
            return f"  [{idx}] {etype} | closed | mid={mid_str} | length={length:.2f}"

    # --- Tool implementations ---

    def get_body_info(self) -> str:
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")

        bodies = self._get_bodies(doc)

        total_faces = 0
        total_edges = 0
        bb_min = [float('inf')] * 3
        bb_max = [float('-inf')] * 3

        for body in bodies:
            # Bounding box
            try:
                box = body.GetBodyBox()  # method: returns (xmin,ymin,zmin, xmax,ymax,zmax) in meters
                if box:
                    for i in range(3):
                        bb_min[i] = min(bb_min[i], box[i] * 1000.0)
                        bb_max[i] = max(bb_max[i], box[i + 3] * 1000.0)
            except Exception:
                pass

            faces = body.GetFaces()  # method
            if faces:
                total_faces += len(faces)
            edges = body.GetEdges()  # method
            if edges:
                total_edges += len(edges)

        total_vertices = self._count_unique_vertices(bodies)

        size_x = bb_max[0] - bb_min[0]
        size_y = bb_max[1] - bb_min[1]
        size_z = bb_max[2] - bb_min[2]

        result = "✓ Body Info:\n"
        result += f"  Bounding Box: ({bb_min[0]:.2f}, {bb_min[1]:.2f}, {bb_min[2]:.2f}) to ({bb_max[0]:.2f}, {bb_max[1]:.2f}, {bb_max[2]:.2f}) mm\n"
        result += f"  Size: {size_x:.2f} x {size_y:.2f} x {size_z:.2f} mm\n"
        result += f"  Faces: {total_faces}\n"
        result += f"  Edges: {total_edges}\n"
        result += f"  Vertices: {total_vertices}"

        logger.info(f"Body info: {total_faces} faces, {total_edges} edges, {total_vertices} vertices")
        return result

    def get_faces(self, args: dict) -> str:
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")

        bodies = self._get_bodies(doc)
        filter_type = args.get("surfaceType")
        filter_id = SURFACE_TYPE_FILTER.get(filter_type) if filter_type else None

        all_faces = []
        for body in bodies:
            faces = body.GetFaces()  # method
            if faces:
                all_faces.extend(faces)

        # Apply filter
        if filter_id is not None:
            all_faces = [f for f in all_faces if self._surface_identity(f) == filter_id]

        if not all_faces:
            filter_note = f" (filter: {filter_type})" if filter_type else ""
            return f"✓ No faces found{filter_note}."

        lines = [f"✓ Faces ({len(all_faces)} total):"]
        for idx, face in enumerate(all_faces):
            type_str = self._surface_type_str(face)
            try:
                area_mm2 = face.GetArea * 1e6  # property: area in m^2
            except Exception:
                area_mm2 = 0.0
            details = self._surface_details(face)
            sample = self._face_sample_point(face)
            sample_str = f"({sample[0]:.2f}, {sample[1]:.2f}, {sample[2]:.2f})"
            try:
                edge_count = face.GetEdgeCount  # property: int
            except Exception:
                edge_count = 0

            detail_part = f" | {details}" if details else ""
            lines.append(
                f"  [{idx}] {type_str} face | area={area_mm2:.2f} mm^2{detail_part} | point={sample_str} | edges={edge_count}"
            )

        result = "\n".join(lines)
        logger.info(f"get_faces: returned {len(all_faces)} faces")
        return result

    def get_edges(self, args: dict) -> str:
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")

        bodies = self._get_bodies(doc)
        filter_type = args.get("edgeType")

        # Map filter to expected edge type string
        edge_type_map = {
            "LINE": "Line",
            "CIRCLE": "Circle",
            "ARC": "Arc",
            "ELLIPSE": "Curve",
            "SPLINE": "Curve",
        }
        filter_str = edge_type_map.get(filter_type) if filter_type else None

        all_edges = []
        for body in bodies:
            edges = body.GetEdges()  # method
            if edges:
                all_edges.extend(edges)

        # Classify and optionally filter
        edge_data = []
        for edge in all_edges:
            etype = self._edge_type_str(edge)
            if filter_str and etype != filter_str:
                continue
            edge_data.append((edge, etype))

        if not edge_data:
            filter_note = f" (filter: {filter_type})" if filter_type else ""
            return f"✓ No edges found{filter_note}."

        lines = [f"✓ Edges ({len(edge_data)} total):"]
        for idx, (edge, etype) in enumerate(edge_data):
            lines.append(self._format_edge_line(idx, edge))

        result = "\n".join(lines)
        logger.info(f"get_edges: returned {len(edge_data)} edges")
        return result

    def get_face_edges(self, args: dict) -> str:
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")

        x = args["x"]
        y = args["y"]
        z = args["z"]

        # Select the face
        doc.ClearSelection2(True)
        ok = sel.select_face(doc, x, y, z)
        if not ok:
            raise Exception(f"No face found at ({x}, {y}, {z}) mm")

        # Get the selected face object
        sel_mgr = doc.SelectionManager
        face = sel_mgr.GetSelectedObject6(1, -1)
        if not face:
            raise Exception("Could not retrieve the selected face object")

        # Face info
        type_str = self._surface_type_str(face)
        try:
            area_mm2 = face.GetArea * 1e6  # property
        except Exception:
            area_mm2 = 0.0
        details = self._surface_details(face)
        sample = self._face_sample_point(face)
        sample_str = f"({sample[0]:.2f}, {sample[1]:.2f}, {sample[2]:.2f})"

        lines = [
            f"✓ Face at ({x:.2f}, {y:.2f}, {z:.2f}):",
            f"  Type: {type_str}",
            f"  Area: {area_mm2:.2f} mm^2",
        ]
        if details:
            lines.append(f"  {details}")
        lines.append(f"  Sample point: {sample_str}")

        # Face edges
        edges = face.GetEdges  # property: tuple of edge COM objects
        if edges:
            lines.append(f"  Edges ({len(edges)}):")
            for idx, edge in enumerate(edges):
                lines.append(f"  {self._format_edge_line(idx, edge)}")
        else:
            lines.append("  Edges: 0")

        doc.ClearSelection2(True)

        result = "\n".join(lines)
        logger.info(f"get_face_edges at ({x}, {y}, {z}): {type_str}, {len(edges) if edges else 0} edges")
        return result

    def get_vertices(self) -> str:
        doc = self.connection.get_active_doc()
        if not doc:
            raise Exception("No active document")

        bodies = self._get_bodies(doc)

        coords = []
        for body in bodies:
            edges = body.GetEdges()  # method
            if not edges:
                continue
            for edge in edges:
                for v in (edge.GetStartVertex, edge.GetEndVertex):  # properties
                    if v:
                        p = v.GetPoint  # property
                        coords.append((p[0] * 1000.0, p[1] * 1000.0, p[2] * 1000.0))

        unique = self._deduplicate_points(coords)
        unique.sort(key=lambda p: (p[0], p[1], p[2]))

        if not unique:
            return "✓ No vertices found (model may only have closed-edge geometry)."

        lines = [f"✓ Vertices ({len(unique)} total):"]
        for idx, pt in enumerate(unique):
            lines.append(f"  [{idx}] ({pt[0]:.2f}, {pt[1]:.2f}, {pt[2]:.2f})")

        result = "\n".join(lines)
        logger.info(f"get_vertices: {len(unique)} unique vertices")
        return result
