"""
Coverage grader: were all required tools called?

Returns a score (0-1) representing the fraction of required tools
that were actually invoked during the eval session.
"""

from testHarness.models import EvalSession, TaskSpec


def grade_coverage(session: EvalSession, spec: TaskSpec) -> tuple[float, list[str]]:
    """Grade tool coverage.

    Returns:
        (score, missing_tools) where score is 0.0-1.0 and missing_tools
        lists required tools that were never called.
    """
    if not spec.required_tools:
        return 1.0, []

    called = {tc.tool_name for tc in session.tool_calls}
    missing = [r for r in spec.required_tools if r not in called]

    score = 1.0 - (len(missing) / len(spec.required_tools))
    return score, missing
