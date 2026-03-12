"""
Efficiency grader: how much flailing happened?

Measures call count vs budget, detects retry patterns and
consecutive same-tool calls that suggest confusion.
"""

from testHarness.models import EvalSession, TaskSpec


def grade_efficiency(session: EvalSession, spec: TaskSpec) -> tuple[float, dict]:
    """Grade efficiency of tool usage.

    Returns:
        (score, diagnostics) where score is 0.0-1.0 and diagnostics
        contains detailed breakdown of call patterns.
    """
    total = len(session.tool_calls)

    if total == 0:
        return 0.0, {"total_calls": 0, "failed_calls": 0, "retries": [], "over_budget_by": 0}

    failed = [tc for tc in session.tool_calls if not tc.success]

    # Detect retry patterns: same tool called multiple times consecutively
    retries = []
    for i in range(1, total):
        prev = session.tool_calls[i - 1]
        curr = session.tool_calls[i]
        if curr.tool_name == prev.tool_name:
            retries.append({
                "tool": curr.tool_name,
                "attempt_index": i,
                "previous_error": prev.error,
            })

    # Score: ratio of budget to actual calls (capped at 1.0)
    score = min(1.0, spec.max_expected_calls / max(total, 1))

    diagnostics = {
        "total_calls": total,
        "failed_calls": len(failed),
        "retries": retries,
        "over_budget_by": max(0, total - spec.max_expected_calls),
    }
    return score, diagnostics
