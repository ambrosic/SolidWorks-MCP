"""
Order grader: were ordering constraints respected?

Checks whether tools were called in the correct relative order,
using flexible pairwise constraints rather than a strict sequence.
"""

from testHarness.models import EvalSession, TaskSpec


def grade_order(session: EvalSession, spec: TaskSpec) -> tuple[float, list[str]]:
    """Grade tool ordering.

    Returns:
        (score, violations) where score is 0.0-1.0 and violations lists
        ordering constraints that were violated.
    """
    if not spec.ordering_constraints:
        return 1.0, []

    # Build map: tool_name -> list of call indices
    call_indices: dict[str, list[int]] = {}
    for i, tc in enumerate(session.tool_calls):
        call_indices.setdefault(tc.tool_name, []).append(i)

    violations = []
    for constraint in spec.ordering_constraints:
        before_calls = call_indices.get(constraint.before, [])
        after_calls = call_indices.get(constraint.after, [])

        # Only check if both tools were called
        if before_calls and after_calls:
            if min(before_calls) > min(after_calls):
                violations.append(
                    f"{constraint.before} should precede "
                    f"{constraint.after}: {constraint.description}"
                )

    n = len(spec.ordering_constraints)
    score = 1.0 - (len(violations) / n)
    return score, violations
