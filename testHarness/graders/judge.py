"""
Optional LLM judge grader.

Uses a (preferably strong) LLM to assess the overall strategy quality
of a tool call sequence. This provides qualitative insights that
deterministic graders cannot capture.
"""

import json
import logging
from testHarness.models import EvalSession, TaskSpec, GradeResult
from testHarness.llm.base import LLMProvider

logger = logging.getLogger(__name__)


def llm_judge(
    session: EvalSession,
    spec: TaskSpec,
    deterministic_result: GradeResult,
    judge_provider: LLMProvider,
) -> dict:
    """Use an LLM to assess strategy quality.

    Args:
        session: Completed eval session
        spec: Task specification
        deterministic_result: Scores from deterministic graders
        judge_provider: LLM provider for the judge

    Returns:
        Dict with strategy_score (0-1), observations, and top_priority_fix.
        On failure, returns dict with parse_error=True and raw_response.
    """
    # Format tool call log
    call_log = "\n".join([
        f"{i + 1}. {tc.tool_name}({json.dumps(tc.inputs, default=str)[:150]}) -> "
        f"{'OK' if tc.success else 'FAIL: ' + (tc.error or 'unknown')[:80]}"
        for i, tc in enumerate(session.tool_calls)
    ])

    prompt = f"""You are grading an AI's use of SolidWorks CAD tools.

Task: {spec.description}

Tool call sequence:
{call_log}

Deterministic scores:
- Coverage: {deterministic_result.coverage_score:.2f}
- Order: {deterministic_result.order_score:.2f}
- Efficiency: {deterministic_result.efficiency_score:.2f}
- Error recovery: {deterministic_result.error_recovery_score:.2f}
- Geometry: {deterministic_result.geometry_score:.2f}

Assess:
1. Was the overall strategy sound, even if execution was imperfect?
2. Were there clever adaptations when tools failed?
3. Were there concerning patterns (e.g. guessing coordinates instead of querying)?
4. What is the single most important thing to fix?

Respond in JSON only: {{"strategy_score": 0.0-1.0, "observations": ["..."], "top_priority_fix": "..."}}"""

    messages = [{"role": "user", "content": prompt}]

    try:
        response = judge_provider.chat_completion(
            messages=messages,
            tools=[],  # no tools for the judge
            temperature=0.0,
        )

        content = response["choices"][0]["message"].get("content", "")

        # Try to extract JSON from the response
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to find JSON in the response
            import re
            json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {"raw_response": content, "parse_error": True}

    except Exception as e:
        logger.error(f"LLM judge failed: {e}")
        return {"error": str(e), "parse_error": True}
