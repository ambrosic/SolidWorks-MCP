"""
SolidWorks State Query Tools
MCP tools for querying the tracked state of features, sketches, and entities.
"""

import json
import logging
from mcp.types import Tool
from .state_tracker import SketchEntityRecord, SketchRecord, FeatureRecord, RefGeometryRecord

logger = logging.getLogger(__name__)


def _json_result(result, **extra):
    d = {"result": result}
    d.update(extra)
    return json.dumps(d)


class StateQueryTools:
    """Tools for querying the state tracker."""

    def __init__(self, tracker):
        self.tracker = tracker

    def get_tool_definitions(self) -> list[Tool]:
        return [
            Tool(
                name="solidworks_get_state",
                description="Get a summary of all tracked objects in the current session: features, sketches, sketch entities, and reference geometry with their IDs.",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            Tool(
                name="solidworks_get_entity",
                description="Get detailed information about a tracked object by its ID. Accepts feature IDs (feat:...), sketch IDs (sketch:...), entity IDs (entity:...), or reference IDs (ref:...).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "The stable ID of the object to query (e.g., 'feat:Boss-Extrude1', 'sketch:Sketch1', 'entity:Sketch1/line_0')"
                        }
                    },
                    "required": ["id"]
                }
            ),
            Tool(
                name="solidworks_get_sketch_entities",
                description="List all tracked sketch entities in a specific sketch. Returns entity IDs, types, and coordinates.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "sketchId": {
                            "type": "string",
                            "description": "Sketch ID (e.g., 'sketch:Sketch1') or just the sketch name (e.g., 'Sketch1')"
                        }
                    },
                    "required": ["sketchId"]
                }
            ),
        ]

    def execute(self, tool_name: str, args: dict) -> str:
        if tool_name == "solidworks_get_state":
            return self._get_state()
        elif tool_name == "solidworks_get_entity":
            return self._get_entity(args)
        elif tool_name == "solidworks_get_sketch_entities":
            return self._get_sketch_entities(args)
        else:
            raise Exception(f"Unknown state query tool: {tool_name}")

    def _get_state(self) -> str:
        summary = self.tracker.format_state_summary()
        return json.dumps({"result": "✓ Session state", **summary})

    def _get_entity(self, args: dict) -> str:
        id_str = args["id"]
        record = self.tracker.resolve_id(id_str)
        if not record:
            return _json_result(f"No object found with ID: {id_str}")

        if isinstance(record, FeatureRecord):
            data = {
                "id": record.feature_id,
                "name": record.sw_name,
                "type": record.feature_type,
            }
            if record.source_sketch:
                data["sourceSketch"] = record.source_sketch
            if record.parameters:
                data["parameters"] = record.parameters
            return json.dumps({"result": f"✓ Feature: {record.sw_name}", **data})

        elif isinstance(record, SketchRecord):
            data = {
                "id": record.sketch_id,
                "name": record.sw_name,
                "plane": record.plane,
                "entityCount": len(record.entities),
                "entities": [
                    {"id": e.entity_id, "type": e.entity_type}
                    for e in record.entities
                ],
            }
            return json.dumps({"result": f"✓ Sketch: {record.sw_name}", **data})

        elif isinstance(record, SketchEntityRecord):
            data = {
                "id": record.entity_id,
                "sketchName": record.sketch_name,
                "type": record.entity_type,
                "coordinates": record.coordinates,
                "shapeInfo": record.shape_info,
            }
            return json.dumps({"result": f"✓ Entity: {record.entity_id}", **data})

        elif isinstance(record, RefGeometryRecord):
            data = {
                "id": record.ref_id,
                "name": record.sw_name,
                "type": record.ref_type,
            }
            if record.parameters:
                data["parameters"] = record.parameters
            return json.dumps({"result": f"✓ Ref geometry: {record.sw_name}", **data})

        return _json_result(f"Unknown record type for ID: {id_str}")

    def _get_sketch_entities(self, args: dict) -> str:
        sketch_id = args["sketchId"]
        entities = self.tracker.get_sketch_entities(sketch_id)
        if not entities:
            return _json_result(f"No entities found in sketch: {sketch_id}")

        entity_list = []
        for e in entities:
            entity_list.append({
                "id": e.entity_id,
                "type": e.entity_type,
                "coordinates": e.coordinates,
            })

        return json.dumps({
            "result": f"✓ {len(entities)} entities in {sketch_id}",
            "sketchId": sketch_id,
            "entities": entity_list,
        })
