"""
Geometry grader: does the final geometry match expectations?

Calls solidworks_get_mass_properties and solidworks_get_body_info
on the final state to compare against expected values.
"""

import json
import re
import logging
from testHarness.models import EvalSession, TaskSpec
from typing import Optional

logger = logging.getLogger(__name__)


def grade_geometry(session: EvalSession, spec: TaskSpec, server) -> tuple[float, dict]:
    """Grade final geometry against expected values.

    Args:
        session: The completed eval session
        spec: Task specification with geometry expectations
        server: InstrumentedServer instance (for querying final state)

    Returns:
        (score, detail) where score is 0.0-1.0 and detail contains
        per-check pass/fail with actual vs expected values.
    """
    if not spec.geometry:
        return 1.0, {"skipped": True}

    geom = spec.geometry
    detail = {}
    checks_passed = 0
    checks_total = 0

    # Get mass properties for volume/surface area
    try:
        mp_result = server.route_tool("solidworks_get_mass_properties", {})
        volume = _extract_volume(mp_result)
        if volume is not None and geom.volume_mm3 is not None:
            checks_total += 1
            delta = abs(volume - geom.volume_mm3)
            detail["volume_actual"] = volume
            detail["volume_expected"] = geom.volume_mm3
            detail["volume_delta"] = delta
            detail["volume_tolerance"] = geom.volume_tolerance
            if delta <= geom.volume_tolerance:
                checks_passed += 1
                detail["volume_pass"] = True
            else:
                detail["volume_pass"] = False

        surface_area = _extract_surface_area(mp_result)
        if surface_area is not None and geom.surface_area_mm2 is not None:
            checks_total += 1
            delta = abs(surface_area - geom.surface_area_mm2)
            detail["surface_area_actual"] = surface_area
            detail["surface_area_expected"] = geom.surface_area_mm2
            detail["surface_area_delta"] = delta
            if delta <= geom.surface_area_tolerance:
                checks_passed += 1
                detail["surface_area_pass"] = True
            else:
                detail["surface_area_pass"] = False
    except Exception as e:
        detail["mass_properties_error"] = str(e)
        logger.warning(f"Failed to get mass properties: {e}")

    # Get body info for face/edge/vertex counts
    try:
        bi_result = server.route_tool("solidworks_get_body_info", {})
        counts = _extract_counts(bi_result)

        for prop, expected in [
            ("face_count", geom.face_count),
            ("edge_count", geom.edge_count),
            ("vertex_count", geom.vertex_count),
        ]:
            if expected is not None and prop in counts:
                checks_total += 1
                actual = counts[prop]
                detail[f"{prop}_actual"] = actual
                detail[f"{prop}_expected"] = expected
                if actual == expected:
                    checks_passed += 1
                    detail[f"{prop}_pass"] = True
                else:
                    detail[f"{prop}_pass"] = False
    except Exception as e:
        detail["body_info_error"] = str(e)
        logger.warning(f"Failed to get body info: {e}")

    score = checks_passed / checks_total if checks_total > 0 else 0.0
    return score, detail


def _extract_volume(result_str: str) -> Optional[float]:
    """Extract volume (mm3) from mass properties result."""
    # Try JSON parse first
    try:
        data = json.loads(result_str)
        if "volume_mm3" in data:
            return float(data["volume_mm3"])
        if "result" in data:
            result_str = data["result"]
    except (json.JSONDecodeError, TypeError):
        pass

    # Parse from text output
    for line in result_str.split("\n"):
        lower = line.lower()
        if "volume" in lower:
            numbers = re.findall(r'[\d.]+', line.split(":", 1)[-1] if ":" in line else line)
            if numbers:
                return float(numbers[0])
    return None


def _extract_surface_area(result_str: str) -> Optional[float]:
    """Extract surface area (mm2) from mass properties result."""
    try:
        data = json.loads(result_str)
        if "surface_area_mm2" in data:
            return float(data["surface_area_mm2"])
        if "result" in data:
            result_str = data["result"]
    except (json.JSONDecodeError, TypeError):
        pass

    for line in result_str.split("\n"):
        lower = line.lower()
        if "surface" in lower and "area" in lower:
            numbers = re.findall(r'[\d.]+', line.split(":", 1)[-1] if ":" in line else line)
            if numbers:
                return float(numbers[0])
    return None


def _extract_counts(result_str: str) -> dict:
    """Extract face/edge/vertex counts from body info result."""
    counts = {}

    # Try JSON parse first
    try:
        data = json.loads(result_str)
        if isinstance(data, dict):
            for key in ["face_count", "edge_count", "vertex_count"]:
                if key in data:
                    counts[key] = int(data[key])
            # Also check nested "result" field
            if "result" in data and isinstance(data["result"], str):
                result_str = data["result"]
            elif counts:
                return counts
    except (json.JSONDecodeError, TypeError):
        pass

    # Parse from text output
    patterns = {
        "face_count": r'[Ff]aces?:\s*(\d+)',
        "edge_count": r'[Ee]dges?:\s*(\d+)',
        "vertex_count": r'[Vv]ert(?:ices|ex(?:es)?):\s*(\d+)',
    }
    for key, pattern in patterns.items():
        m = re.search(pattern, result_str)
        if m:
            counts[key] = int(m.group(1))

    return counts
