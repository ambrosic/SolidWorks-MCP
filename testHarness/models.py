"""
Core data structures for the test harness.

All graders, the runner, and the CLI reference these dataclasses.
"""

from dataclasses import dataclass, field
from typing import Optional, Any
import time


@dataclass
class ToolCall:
    """Record of a single MCP tool invocation."""
    tool_name: str
    inputs: dict
    output: str               # raw JSON string from _route_tool
    timestamp: float          # time.time() when call started
    duration_ms: float        # wall-clock duration
    success: bool             # True if output contains checkmark, no exception
    error: Optional[str] = None
    call_index: int = 0       # position in sequence (0-based)
    annotation: Optional[str] = None  # filled by grader


@dataclass
class OrderingConstraint:
    """Declares that `before` tool must be called before `after` tool."""
    before: str
    after: str
    description: str


@dataclass
class GeometryExpectation:
    """Expected geometry outcome for grading."""
    volume_mm3: Optional[float] = None
    volume_tolerance: float = 100.0       # mm3
    surface_area_mm2: Optional[float] = None
    surface_area_tolerance: float = 100.0
    face_count: Optional[int] = None
    edge_count: Optional[int] = None
    vertex_count: Optional[int] = None


@dataclass
class TaskSpec:
    """Definition of an eval task loaded from YAML."""
    task_id: str
    description: str                                       # natural language prompt for the LLM
    difficulty: str = "basic"                              # basic, intermediate, advanced
    required_tools: list[str] = field(default_factory=list)
    forbidden_tools: list[str] = field(default_factory=list)
    ordering_constraints: list[OrderingConstraint] = field(default_factory=list)
    max_expected_calls: int = 20
    geometry: Optional[GeometryExpectation] = None
    system_prompt_addendum: str = ""                       # extra context for the LLM
    timeout_seconds: float = 300.0                         # 5 min default


@dataclass
class EvalSession:
    """Complete record of a single eval run."""
    task_id: str
    task_description: str
    model_name: str
    git_commit: str = ""
    git_branch: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    final_state: Optional[dict] = None          # from solidworks_get_state
    completed: bool = False
    timed_out: bool = False
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    llm_messages: list[dict] = field(default_factory=list)  # full conversation log
    error: Optional[str] = None


@dataclass
class GradeResult:
    """Aggregate grading output across all dimensions."""
    coverage_score: float = 0.0
    order_score: float = 0.0
    efficiency_score: float = 0.0
    error_recovery_score: float = 0.0
    geometry_score: float = 0.0
    forbidden_penalty: float = 0.0

    missing_required: list[str] = field(default_factory=list)
    called_forbidden: list[str] = field(default_factory=list)
    order_violations: list[str] = field(default_factory=list)
    retry_events: list[dict] = field(default_factory=list)
    error_taxonomy: dict = field(default_factory=dict)
    geometry_detail: dict = field(default_factory=dict)

    judge_result: Optional[dict] = None  # from LLM judge, if used

    @property
    def weighted_total(self) -> float:
        base = (
            self.coverage_score       * 0.25 +
            self.order_score          * 0.15 +
            self.efficiency_score     * 0.15 +
            self.error_recovery_score * 0.15 +
            self.geometry_score       * 0.30
        )
        return max(0.0, base + self.forbidden_penalty)
