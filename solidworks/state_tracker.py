"""
SolidWorks MCP State Tracker
Centralized registry for features, sketches, and sketch entities.
Provides stable IDs for referencing objects across tool calls.

ID format:
  feat:<sw_feature_name>       e.g. feat:Boss-Extrude1
  sketch:<sw_sketch_name>      e.g. sketch:Sketch1
  entity:<sketch>/<type>_<idx> e.g. entity:Sketch1/rect_0
  ref:<sw_feature_name>        e.g. ref:Plane1
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SketchEntityRecord:
    """A tracked sketch entity (line, circle, arc, rectangle, etc.)"""
    entity_id: str
    sketch_name: str
    entity_type: str
    index: int
    coordinates: Dict
    shape_info: Dict


@dataclass
class SketchRecord:
    """A tracked sketch"""
    sketch_id: str
    sw_name: str
    plane: str
    entities: List[SketchEntityRecord] = field(default_factory=list)
    entity_counter: Dict[str, int] = field(default_factory=dict)


@dataclass
class FeatureRecord:
    """A tracked feature (extrusion, fillet, revolve, etc.)"""
    feature_id: str
    sw_name: str
    feature_type: str
    source_sketch: Optional[str] = None
    parameters: Dict = field(default_factory=dict)


@dataclass
class RefGeometryRecord:
    """A tracked reference geometry element"""
    ref_id: str
    sw_name: str
    ref_type: str
    parameters: Dict = field(default_factory=dict)


class StateTracker:
    """Centralized state tracker for the MCP session."""

    def __init__(self):
        self.features: Dict[str, FeatureRecord] = {}
        self.sketches: Dict[str, SketchRecord] = {}
        self.entities: Dict[str, SketchEntityRecord] = {}
        self.ref_geometry: Dict[str, RefGeometryRecord] = {}
        self._active_sketch: Optional[str] = None

        # Spatial tracking (shared with SketchingTools)
        self.last_shape: Optional[Dict] = None
        self.created_shapes: List[Dict] = []

    def reset(self):
        """Reset all state (called on new_part)."""
        self.features.clear()
        self.sketches.clear()
        self.entities.clear()
        self.ref_geometry.clear()
        self._active_sketch = None
        self.last_shape = None
        self.created_shapes = []

    # --- Sketch tracking ---

    def register_sketch(self, sw_name: str, plane: str) -> str:
        sketch_id = f"sketch:{sw_name}"
        record = SketchRecord(sketch_id=sketch_id, sw_name=sw_name, plane=plane)
        self.sketches[sketch_id] = record
        self._active_sketch = sketch_id
        self.created_shapes = []
        self.last_shape = None
        logger.info(f"Registered sketch: {sketch_id} on {plane}")
        return sketch_id

    def close_sketch(self, actual_sw_name: str) -> str:
        if self._active_sketch:
            record = self.sketches.get(self._active_sketch)
            if record and record.sw_name != actual_sw_name:
                old_id = self._active_sketch
                del self.sketches[old_id]
                old_sw_name = record.sw_name
                record.sw_name = actual_sw_name
                record.sketch_id = f"sketch:{actual_sw_name}"
                self.sketches[record.sketch_id] = record
                self._rebase_entity_ids(old_sw_name, actual_sw_name, record)
            sketch_id = record.sketch_id if record else f"sketch:{actual_sw_name}"
            self._active_sketch = None
            return sketch_id
        return f"sketch:{actual_sw_name}"

    def _rebase_entity_ids(self, old_sw_name: str, new_sw_name: str, sketch_record: SketchRecord):
        prefix = f"entity:{old_sw_name}/"
        to_update = [eid for eid in self.entities if eid.startswith(prefix)]
        for old_eid in to_update:
            record = self.entities.pop(old_eid)
            suffix = old_eid.split("/", 1)[1]
            new_eid = f"entity:{new_sw_name}/{suffix}"
            record.entity_id = new_eid
            record.sketch_name = new_sw_name
            self.entities[new_eid] = record
        # Update entity list in sketch record
        for entity in sketch_record.entities:
            if entity.sketch_name == old_sw_name:
                suffix = entity.entity_id.split("/", 1)[1]
                entity.entity_id = f"entity:{new_sw_name}/{suffix}"
                entity.sketch_name = new_sw_name

    @property
    def active_sketch_id(self) -> Optional[str]:
        return self._active_sketch

    @property
    def active_sketch_name(self) -> Optional[str]:
        if self._active_sketch:
            record = self.sketches.get(self._active_sketch)
            return record.sw_name if record else None
        return None

    # --- Sketch entity tracking ---

    def register_entity(self, entity_type: str, coordinates: Dict,
                        shape_info: Dict, update_spatial: bool = True) -> str:
        if not self._active_sketch:
            logger.warning("No active sketch for entity registration")
            return ""

        sketch_record = self.sketches[self._active_sketch]
        sw_name = sketch_record.sw_name

        idx = sketch_record.entity_counter.get(entity_type, 0)
        sketch_record.entity_counter[entity_type] = idx + 1

        entity_id = f"entity:{sw_name}/{entity_type}_{idx}"
        record = SketchEntityRecord(
            entity_id=entity_id,
            sketch_name=sw_name,
            entity_type=entity_type,
            index=idx,
            coordinates=coordinates,
            shape_info=shape_info,
        )
        self.entities[entity_id] = record
        sketch_record.entities.append(record)

        if update_spatial:
            self.created_shapes.append(shape_info)
            self.last_shape = shape_info

        logger.info(f"Registered entity: {entity_id}")
        return entity_id

    # --- Feature tracking ---

    def register_feature(self, sw_name: str, feature_type: str,
                         source_sketch: Optional[str] = None,
                         parameters: Optional[Dict] = None) -> str:
        feature_id = f"feat:{sw_name}"
        record = FeatureRecord(
            feature_id=feature_id,
            sw_name=sw_name,
            feature_type=feature_type,
            source_sketch=source_sketch,
            parameters=parameters or {},
        )
        self.features[feature_id] = record
        logger.info(f"Registered feature: {feature_id} ({feature_type})")
        return feature_id

    # --- Reference geometry tracking ---

    def register_ref_geometry(self, sw_name: str, ref_type: str,
                              parameters: Optional[Dict] = None) -> str:
        ref_id = f"ref:{sw_name}"
        record = RefGeometryRecord(
            ref_id=ref_id,
            sw_name=sw_name,
            ref_type=ref_type,
            parameters=parameters or {},
        )
        self.ref_geometry[ref_id] = record
        logger.info(f"Registered ref geometry: {ref_id} ({ref_type})")
        return ref_id

    # --- Lookup / query ---

    def resolve_id(self, id_str: str) -> Optional[Any]:
        if id_str in self.features:
            return self.features[id_str]
        if id_str in self.sketches:
            return self.sketches[id_str]
        if id_str in self.entities:
            return self.entities[id_str]
        if id_str in self.ref_geometry:
            return self.ref_geometry[id_str]
        return None

    def get_sw_name(self, id_str: str) -> Optional[str]:
        record = self.resolve_id(id_str)
        if record is None:
            return None
        return getattr(record, 'sw_name', None)

    def resolve_name(self, name_or_id: str) -> str:
        """Resolve a prefixed ID to a SolidWorks name, or return as-is with warning."""
        if name_or_id.startswith(("feat:", "sketch:", "ref:")):
            sw_name = self.get_sw_name(name_or_id)
            if not sw_name:
                raise Exception(f"Unknown ID: {name_or_id}")
            return sw_name
        else:
            logger.warning(
                f"Raw SolidWorks name '{name_or_id}' used — consider using tracked ID instead"
            )
            return name_or_id

    def get_id_by_sw_name(self, sw_name: str) -> Optional[str]:
        """Look up a tracked ID by SolidWorks feature name."""
        for fid, rec in self.features.items():
            if rec.sw_name == sw_name:
                return fid
        for sid, rec in self.sketches.items():
            if rec.sw_name == sw_name:
                return sid
        for rid, rec in self.ref_geometry.items():
            if rec.sw_name == sw_name:
                return rid
        return None

    def get_entity_coordinates(self, entity_id: str) -> Optional[Dict]:
        record = self.entities.get(entity_id)
        return record.coordinates if record else None

    def get_sketch_entities(self, sketch_id: str) -> List[SketchEntityRecord]:
        record = self.sketches.get(sketch_id)
        if not record:
            record = self.sketches.get(f"sketch:{sketch_id}")
        return record.entities if record else []

    def format_state_summary(self) -> Dict:
        """Format a structured state summary."""
        summary = {"sketches": [], "features": [], "refGeometry": []}

        for sid, s in self.sketches.items():
            sketch_data = {
                "id": sid,
                "name": s.sw_name,
                "plane": s.plane,
                "entityCount": len(s.entities),
                "entities": [
                    {"id": e.entity_id, "type": e.entity_type}
                    for e in s.entities
                ],
            }
            summary["sketches"].append(sketch_data)

        for fid, f in self.features.items():
            feat_data = {
                "id": fid,
                "name": f.sw_name,
                "type": f.feature_type,
            }
            if f.source_sketch:
                feat_data["sourceSketch"] = f.source_sketch
            if f.parameters:
                feat_data["parameters"] = f.parameters
            summary["features"].append(feat_data)

        for rid, r in self.ref_geometry.items():
            ref_data = {
                "id": rid,
                "name": r.sw_name,
                "type": r.ref_type,
            }
            if r.parameters:
                ref_data["parameters"] = r.parameters
            summary["refGeometry"].append(ref_data)

        return summary
