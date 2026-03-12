"""
Task loader: parses YAML task definitions into TaskSpec objects.
"""

import yaml
from pathlib import Path
from testHarness.models import TaskSpec, OrderingConstraint, GeometryExpectation


class TaskLoader:
    """Loads eval task definitions from YAML files."""

    def __init__(self, tasks_dir: str = None):
        if tasks_dir is None:
            tasks_dir = str(Path(__file__).parent / "tasks")
        self.tasks_dir = Path(tasks_dir)

    def load(self, task_id: str) -> TaskSpec:
        """Load a single task by ID (filename without extension)."""
        path = self.tasks_dir / f"{task_id}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"Task file not found: {path}")
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return self._parse(data)

    def load_all(self) -> list[TaskSpec]:
        """Load all tasks from the tasks directory, sorted by filename."""
        specs = []
        for path in sorted(self.tasks_dir.glob("*.yaml")):
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            specs.append(self._parse(data))
        return specs

    def list_tasks(self) -> list[str]:
        """List all available task IDs."""
        return sorted(p.stem for p in self.tasks_dir.glob("*.yaml"))

    def _parse(self, data: dict) -> TaskSpec:
        """Parse a YAML dict into a TaskSpec."""
        constraints = []
        for c in data.get("ordering_constraints", []):
            constraints.append(OrderingConstraint(
                before=c["before"],
                after=c["after"],
                description=c["description"],
            ))

        geom = None
        if "geometry" in data:
            g = data["geometry"]
            geom = GeometryExpectation(
                volume_mm3=g.get("volume_mm3"),
                volume_tolerance=g.get("volume_tolerance", 100.0),
                surface_area_mm2=g.get("surface_area_mm2"),
                surface_area_tolerance=g.get("surface_area_tolerance", 100.0),
                face_count=g.get("face_count"),
                edge_count=g.get("edge_count"),
                vertex_count=g.get("vertex_count"),
            )

        return TaskSpec(
            task_id=data["task_id"],
            description=data["description"],
            difficulty=data.get("difficulty", "basic"),
            required_tools=data.get("required_tools", []),
            forbidden_tools=data.get("forbidden_tools", []),
            ordering_constraints=constraints,
            max_expected_calls=data.get("max_expected_calls", 20),
            geometry=geom,
            system_prompt_addendum=data.get("system_prompt_addendum", ""),
            timeout_seconds=data.get("timeout_seconds", 300.0),
        )
