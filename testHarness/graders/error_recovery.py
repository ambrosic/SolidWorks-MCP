"""
Error recovery grader: how well did the LLM handle failures?

Classifies each error by type (selection, parameter, sequence, tool)
and detects whether the LLM recovered via query-then-retry, parameter
adjustment, or alternative approach.
"""

from testHarness.models import EvalSession, TaskSpec, ToolCall
from typing import Optional


def classify_error(error_str: Optional[str], tool_name: str, inputs: dict) -> str:
    """Heuristic classification based on actual MCP server error patterns."""
    if not error_str:
        return "unknown"

    err = error_str.lower()

    if any(kw in err for kw in ["not found", "no edge", "no face", "could not select",
                                 "failed to select", "select"]):
        return "selection_error"
    elif any(kw in err for kw in ["invalid", "out of range", "expected", "missing",
                                   "required", "must be"]):
        return "parameter_error"
    elif any(kw in err for kw in ["no active sketch", "no body", "no part",
                                   "sketch is not", "not in sketch", "no document"]):
        return "sequence_error"
    elif any(kw in err for kw in ["com error", "solidworks", "internal",
                                   "none", "exception", "win32"]):
        return "tool_error"
    else:
        return "parameter_error"  # safe default


def check_recovery(
    failed_call: ToolCall,
    subsequent_calls: list[ToolCall]
) -> Optional[str]:
    """Check if the LLM recovered from a failure.

    Returns a description of the recovery strategy, or None if no recovery detected.
    """
    if not subsequent_calls:
        return None

    next_call = subsequent_calls[0]

    # Strategy 1: queried state then retried
    query_tools = {
        "solidworks_get_state", "solidworks_get_edges", "solidworks_get_faces",
        "solidworks_get_body_info", "solidworks_get_face_edges",
        "solidworks_get_vertices",
    }
    if next_call.tool_name in query_tools:
        if len(subsequent_calls) > 1 and subsequent_calls[1].success:
            return "queried_then_retried"

    # Strategy 2: retried with different parameters
    if (next_call.tool_name == failed_call.tool_name
            and next_call.inputs != failed_call.inputs
            and next_call.success):
        return "retried_with_different_params"

    # Strategy 3: tried a different approach
    if (next_call.tool_name != failed_call.tool_name
            and next_call.tool_name not in query_tools
            and next_call.success):
        return "alternative_approach"

    return None


def grade_error_recovery(session: EvalSession, spec: TaskSpec) -> tuple[float, dict]:
    """Grade error recovery behavior.

    Returns:
        (score, diagnostics) where score is 0.0-1.0 and diagnostics
        contains error taxonomy and recovery events.
    """
    taxonomy = {
        "parameter_error": 0,
        "selection_error": 0,
        "sequence_error": 0,
        "tool_error": 0,
        "unknown": 0,
        "recovered": 0,
        "unrecovered": 0,
    }
    recovery_events = []

    calls = session.tool_calls
    for i, tc in enumerate(calls):
        if not tc.success:
            error_type = classify_error(tc.error, tc.tool_name, tc.inputs)
            taxonomy[error_type] += 1

            recovered = check_recovery(tc, calls[i + 1:])
            if recovered:
                taxonomy["recovered"] += 1
                recovery_events.append({
                    "failed_tool": tc.tool_name,
                    "error_type": error_type,
                    "recovery_strategy": recovered,
                    "call_index": tc.call_index,
                })
            else:
                taxonomy["unrecovered"] += 1

    failures = sum(1 for tc in calls if not tc.success)
    if failures == 0:
        score = 1.0
    else:
        score = taxonomy["recovered"] / failures

    return score, {"taxonomy": taxonomy, "recovery_events": recovery_events}
