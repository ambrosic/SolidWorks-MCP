"""
Aggregate grader: combines all individual grader scores into a GradeResult.
"""

from testHarness.models import EvalSession, TaskSpec, GradeResult
from testHarness.graders import coverage, order, efficiency, error_recovery, geometry
from typing import Optional


def grade(
    session: EvalSession,
    spec: TaskSpec,
    server,
    judge_provider=None,
) -> GradeResult:
    """Run all graders and produce an aggregate GradeResult.

    Args:
        session: Completed eval session with recorded tool calls
        spec: Task specification with grading criteria
        server: InstrumentedServer for geometry queries on final state
        judge_provider: Optional LLMProvider for the LLM judge grader
    """
    result = GradeResult()

    # Coverage
    result.coverage_score, result.missing_required = coverage.grade_coverage(session, spec)

    # Order
    result.order_score, result.order_violations = order.grade_order(session, spec)

    # Efficiency
    result.efficiency_score, eff_diag = efficiency.grade_efficiency(session, spec)
    result.retry_events = eff_diag.get("retries", [])

    # Error recovery
    result.error_recovery_score, rec_diag = error_recovery.grade_error_recovery(session, spec)
    result.error_taxonomy = rec_diag.get("taxonomy", {})

    # Geometry
    result.geometry_score, result.geometry_detail = geometry.grade_geometry(session, spec, server)

    # Forbidden tools penalty
    called = {tc.tool_name for tc in session.tool_calls}
    result.called_forbidden = [f for f in spec.forbidden_tools if f in called]
    result.forbidden_penalty = -0.1 * len(result.called_forbidden)

    # Optional LLM judge
    if judge_provider:
        from testHarness.graders.judge import llm_judge
        result.judge_result = llm_judge(session, spec, result, judge_provider)

    return result
