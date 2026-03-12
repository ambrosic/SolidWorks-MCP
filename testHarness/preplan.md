For the solidworks mcp server, how do I build an automated testing harness?  I would like to be able to automatically test not just the code but be able to grade the AI on its use of tools as they currently are, to be able to find where issues are going to be.

Mar 7
This is a genuinely hard problem because you're testing two different things simultaneously: whether the tools work correctly and whether the AI uses them correctly. Most testing frameworks only handle one of these. Let me break down how to approach both.

The Two Test Layers
Layer 1 — Tool correctness (deterministic): Does solidworks_create_extrusion actually create the right geometry? This is standard integration testing — you call the tool, query SolidWorks state, assert against expected values. Automatable, fast, repeatable.

Layer 2 — AI behavior (probabilistic): Given a CAD task description, does the model choose the right tools, in the right order, with the right parameters? This is where it gets novel — you're essentially building an eval harness.

The reason to keep these separate is that a flaky tool will make AI behavior look bad even when the model's reasoning is sound, and vice versa.

Layer 1: Tool Integration Tests
The core pattern is: call tool → query state via solidworks_get_state or mass properties → assert.

What to assert on:

Geometry (bounding box, face count, edge count)
Mass properties (volume, surface area — great for catching wrong dimensions)
Feature tree contents and order
Sketch constraints (are they fully defined?)
You want a thin test runner that talks directly to your MCP server over RPC, bypassing Claude entirely. Something like:

python
class SolidWorksToolTest:
    def setup(self):
        self.mcp = MCPClient("ws://localhost:PORT")
        self.mcp.call("solidworks_new_part")

    def test_extrusion_volume(self):
        self.mcp.call("solidworks_sketch_rectangle", 
                      {"width": 50, "height": 30, "plane": "Front"})
        self.mcp.call("solidworks_create_extrusion", {"depth": 20})
        props = self.mcp.call("solidworks_get_mass_properties")
        
        expected_volume = 50 * 30 * 20  # mm³
        assert abs(props["volume"] - expected_volume) < 0.1
The tricky part is teardown — SolidWorks needs to be reset between tests. Options:

Close and reopen the document (slow but clean)
Undo back to a known state (fast but fragile)
Keep a "blank part" template and reload it
Mass properties are your best friend here because they're a single scalar that encodes the entire geometry. A cube with the wrong fillet radius will have a measurably different volume.

Layer 2: AI Behavior Evals
This is closer to what Anthropic does internally for model evaluation. The structure is:

Test case = task description + grading criteria

yaml
- id: cswa_001
  description: "Create a rectangular prism 80mm x 40mm x 25mm with a 5mm fillet on all edges"
  difficulty: basic
  grading:
    geometry:
      volume_mm3: 74200      # approx after fillets
      tolerance: 500
    tool_sequence:
      required_calls: [solidworks_sketch_rectangle, solidworks_create_extrusion, solidworks_fillet]
      forbidden_calls: []    # tools that should NOT be called
    efficiency:
      max_tool_calls: 12     # penalize excessive flailing
```

**The grading pipeline:**
```
Task description → Claude + MCP tools → Tool call log + Final state
                                              ↓               ↓
                                      Sequence grader    Geometry grader
                                              ↓               ↓
                                         Score 0-1        Score 0-1
                                              ↓
                                      Weighted total
```

**Sequence grading** is the most valuable diagnostic. You record every tool call Claude makes and then grade:
- Were required tools called? (correctness)
- Were they called in a sensible order? (planning)
- How many retries/corrections happened? (reliability)
- Were there any clearly wrong calls? (confusion)

You can use a second Claude call as a judge here — give it the tool call log and the task description, ask it to score the approach. This sounds circular but works well in practice because judging is easier than doing.

**The key insight for finding issues**: instead of just pass/fail, you want **error taxonomies**. When Claude fails, is it:
- A *tool parameter error* (wrong value, misunderstood units)
- A *sequencing error* (right tools, wrong order)
- A *selection error* (the edge/face coordinate problem you've hit)
- A *planning error* (chose a fundamentally wrong approach)
- A *tool error* (correct call, tool returned wrong result)

Tagging failures by type tells you whether to fix the tool, fix the prompt/system message, or accept the limitation.

---

## Practical Architecture
```
tests/
  unit/           # Layer 1 - tool correctness, no Claude
    test_sketch.py
    test_extrusion.py
    test_fillet.py
  evals/          # Layer 2 - AI behavior
    tasks/        # YAML task definitions
    graders/      # geometry_grader.py, sequence_grader.py
    runner.py     # orchestrates Claude + records logs
  fixtures/
    blank_part.sldprt
    expected_states/  # saved SolidWorks states for regression
results/
  runs/           # timestamped JSON results per eval run
  dashboard.html  # trend over time
The eval runner needs to:

Launch a fresh SolidWorks document
Start Claude with your MCP server connected
Feed Claude the task description
Record every tool call (input + output + timestamp)
When Claude signals completion (or times out), extract final state
Run graders, write results
For recording tool calls, the cleanest approach is middleware in your MCP server that logs every call to a structured format before passing through to SolidWorks.

Specific Tests for Known Problem Areas
Based on what you've hit so far, I'd prioritize these as early eval cases:

Edge selection reliability — create a known geometry, attempt to fillet specific edges by coordinate, verify the right edges got filleted (check volume delta matches theoretical). This directly measures your biggest current pain point.

Topology drift — create geometry, modify it (fillet/chamfer), then attempt further operations that reference existing faces. Does Claude successfully use solidworks_get_edges to refresh references, or does it reuse stale coordinates?

Cut extrusion on curved bodies — specifically test the THROUGH_ALL vs depth cases, since you know this fails in certain configurations.

Revolve axis handling — test centerline vs construction line behavior.

These aren't random — they're regression tests for bugs you've already found, which means you can write the grading criteria precisely.

Scoring Toward CSWA
Once you have this infrastructure, CSWA practice problems map directly to eval cases. Each problem gives you a target geometry (with published mass properties you can verify against), which is a perfect objective grading signal. You don't need a judge model for geometry correctness — SolidWorks will tell you the volume to 6 decimal places.

The certification framing is actually useful for calibrating difficulty tiers: if Claude can't reliably pass the "basic" CSWA problems, there's no point testing the "advanced" ones. Structure your eval set as a pyramid — lots of atomic tool tests at the base, fewer but harder integration tests at the top.

Would it help to sketch out the actual runner code structure, or dig into how to implement the sequence grader?

How to implement the sequence grader would be really helpful

Mar 7
The sequence grader is interesting because you're not just checking "did the right tools get called" — you want to capture quality of reasoning, not just correctness. Here's how to build it progressively.

Core Data Structure First
Everything flows from having a clean representation of what happened:

python
from dataclasses import dataclass, field
from typing import Optional
import time

@dataclass
class ToolCall:
    tool_name: str
    inputs: dict
    output: dict
    timestamp: float
    duration_ms: float
    success: bool
    error: Optional[str] = None
    # filled in by grader later
    annotation: Optional[str] = None

@dataclass 
class EvalSession:
    task_id: str
    task_description: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    final_state: Optional[dict] = None
    completed: bool = False
    timed_out: bool = False
Your MCP middleware wraps every call to populate this automatically:

python
class LoggingMCPMiddleware:
    def __init__(self, underlying_server, session: EvalSession):
        self.server = underlying_server
        self.session = session

    def call_tool(self, tool_name: str, inputs: dict) -> dict:
        start = time.time()
        try:
            output = self.server.call_tool(tool_name, inputs)
            success = True
            error = None
        except Exception as e:
            output = {}
            success = False
            error = str(e)
        
        self.session.tool_calls.append(ToolCall(
            tool_name=tool_name,
            inputs=inputs,
            output=output,
            timestamp=start,
            duration_ms=(time.time() - start) * 1000,
            success=success,
            error=error
        ))
        return output
The Grader Structure
Split grading into independent dimensions that can be scored separately. This is the key — a single pass/fail score tells you nothing about where things went wrong.

python
@dataclass
class SequenceGradeResult:
    # 0.0 - 1.0 scores per dimension
    coverage_score: float        # were required tools called?
    order_score: float           # were they called in sensible order?
    efficiency_score: float      # how much flailing happened?
    error_recovery_score: float  # did it recover from failures well?
    forbidden_penalty: float     # 0.0 = clean, negative = penalized
    
    # diagnostic detail
    missing_required: list[str]
    called_forbidden: list[str]
    retry_events: list[dict]
    error_taxonomy: dict         # counts by error type
    
    @property
    def weighted_total(self) -> float:
        base = (
            self.coverage_score    * 0.35 +
            self.order_score       * 0.25 +
            self.efficiency_score  * 0.20 +
            self.error_recovery_score * 0.20
        )
        return max(0.0, base + self.forbidden_penalty)
Each Grading Dimension
Coverage (did required tools get called?)
python
def grade_coverage(
    tool_calls: list[ToolCall], 
    required: list[str]
) -> tuple[float, list[str]]:
    
    called = {tc.tool_name for tc in tool_calls}
    missing = [r for r in required if r not in called]
    
    score = 1.0 - (len(missing) / len(required)) if required else 1.0
    return score, missing
This is binary per tool — either it was called or not. You can make it more nuanced by weighting required tools (a missing fillet is less bad than a missing extrusion).

Order (were tools called sensibly?)
This is where it gets interesting. You define ordering constraints rather than a strict sequence, because there are often multiple valid orderings:

python
@dataclass
class OrderingConstraint:
    before: str    # this tool must be called before...
    after: str     # ...this tool
    description: str  # human-readable reason

def grade_order(
    tool_calls: list[ToolCall],
    constraints: list[OrderingConstraint]
) -> tuple[float, list[str]]:
    
    # build a map of tool_name -> list of call indices
    call_indices: dict[str, list[int]] = {}
    for i, tc in enumerate(tool_calls):
        call_indices.setdefault(tc.tool_name, []).append(i)
    
    violations = []
    for constraint in constraints:
        before_calls = call_indices.get(constraint.before, [])
        after_calls = call_indices.get(constraint.after, [])
        
        # if both were called, the earliest 'before' must precede
        # the earliest 'after'
        if before_calls and after_calls:
            if min(before_calls) > min(after_calls):
                violations.append(
                    f"{constraint.before} should precede "
                    f"{constraint.after}: {constraint.description}"
                )
    
    score = 1.0 - (len(violations) / len(constraints)) if constraints else 1.0
    return score, violations
Example constraint set for a simple extruded part with a fillet:

python
constraints = [
    OrderingConstraint(
        before="solidworks_sketch_rectangle",
        after="solidworks_create_extrusion",
        description="sketch must exist before extruding"
    ),
    OrderingConstraint(
        before="solidworks_create_extrusion", 
        after="solidworks_fillet",
        description="body must exist before filleting"
    ),
    OrderingConstraint(
        before="solidworks_get_edges",
        after="solidworks_fillet",
        description="edges should be queried before attempting fillet"
    ),
]
That last constraint is particularly useful for you — it detects whether Claude is attempting blind-coordinate fillets vs. querying edges first, which you know is the reliable pattern.

Efficiency (how much flailing happened?)
python
def grade_efficiency(
    tool_calls: list[ToolCall],
    max_expected_calls: int
) -> tuple[float, dict]:
    
    total_calls = len(tool_calls)
    failed_calls = [tc for tc in tool_calls if not tc.success]
    
    # detect retry patterns: same tool called multiple times in a row
    retries = []
    for i in range(1, len(tool_calls)):
        if tool_calls[i].tool_name == tool_calls[i-1].tool_name:
            retries.append({
                "tool": tool_calls[i].tool_name,
                "attempt": i,
                "previous_error": tool_calls[i-1].error
            })
    
    # detect backtracking: using undo or re-opening sketch after 
    # having moved forward
    backtrack_tools = {"solidworks_undo", "solidworks_edit_sketch"}
    backtracks = [tc for tc in tool_calls if tc.tool_name in backtrack_tools]
    
    efficiency_score = min(1.0, max_expected_calls / max(total_calls, 1))
    
    # bonus: did it succeed despite being over budget?
    # don't penalize as harshly if the final result was correct
    
    diagnostics = {
        "total_calls": total_calls,
        "failed_calls": len(failed_calls),
        "retries": retries,
        "backtracks": len(backtracks),
        "over_budget_by": max(0, total_calls - max_expected_calls)
    }
    
    return efficiency_score, diagnostics
Error Recovery (did it handle failures gracefully?)
This is the most diagnostic dimension for finding where your tools are causing problems vs. where the model reasoning is poor:

python
def grade_error_recovery(
    tool_calls: list[ToolCall]
) -> tuple[float, dict]:
    
    taxonomy = {
        "parameter_error": 0,     # wrong value passed
        "selection_error": 0,     # coordinate/face/edge not found
        "sequence_error": 0,      # tool called in wrong state
        "tool_error": 0,          # tool itself failed (your bug)
        "unrecovered_failure": 0, # failed and didn't try again
        "recovered_failure": 0,   # failed but successfully recovered
    }
    
    recovery_events = []
    
    for i, tc in enumerate(tool_calls):
        if not tc.success:
            # classify the error
            error_type = classify_error(tc.error, tc.tool_name, tc.inputs)
            taxonomy[error_type] += 1
            
            # did the model recover? look at subsequent calls
            subsequent = tool_calls[i+1:]
            recovered = check_recovery(tc, subsequent)
            
            if recovered:
                taxonomy["recovered_failure"] += 1
                recovery_events.append({
                    "failed_call": tc.tool_name,
                    "error_type": error_type,
                    "recovery_strategy": recovered
                })
            else:
                taxonomy["unrecovered_failure"] += 1
    
    failures = sum(1 for tc in tool_calls if not tc.success)
    recoveries = taxonomy["recovered_failure"]
    
    if failures == 0:
        score = 1.0
    else:
        score = recoveries / failures
    
    return score, {"taxonomy": taxonomy, "recovery_events": recovery_events}


def classify_error(error: str, tool_name: str, inputs: dict) -> str:
    """
    Heuristic classification based on error message patterns
    from your actual MCP server errors.
    """
    error_lower = error.lower()
    
    if any(kw in error_lower for kw in ["not found", "no edge", "no face", "coordinate"]):
        return "selection_error"
    elif any(kw in error_lower for kw in ["invalid parameter", "out of range", "expected"]):
        return "parameter_error"  
    elif any(kw in error_lower for kw in ["no active sketch", "no body", "invalid state"]):
        return "sequence_error"
    elif any(kw in error_lower for kw in ["com error", "solidworks", "internal"]):
        return "tool_error"
    else:
        return "parameter_error"  # safe default


def check_recovery(
    failed_call: ToolCall, 
    subsequent_calls: list[ToolCall]
) -> Optional[str]:
    """
    Returns a description of the recovery strategy if found, else None.
    """
    if not subsequent_calls:
        return None
    
    next_call = subsequent_calls[0]
    
    # strategy 1: queried state then retried
    if next_call.tool_name in ("solidworks_get_state", "solidworks_get_edges"):
        if len(subsequent_calls) > 1:
            retry = subsequent_calls[1]
            if retry.tool_name == failed_call.tool_name and retry.success:
                return "queried_then_retried"
    
    # strategy 2: tried a different approach entirely
    if next_call.tool_name != failed_call.tool_name and next_call.success:
        return "alternative_approach"
    
    # strategy 3: retried with different parameters
    if (next_call.tool_name == failed_call.tool_name and 
        next_call.inputs != failed_call.inputs and 
        next_call.success):
        return "retried_with_different_params"
    
    return None
Putting It Together
python
@dataclass
class TaskSpec:
    task_id: str
    description: str
    required_tools: list[str]
    forbidden_tools: list[str]
    ordering_constraints: list[OrderingConstraint]
    max_expected_calls: int

def grade_sequence(
    session: EvalSession, 
    spec: TaskSpec
) -> SequenceGradeResult:
    
    calls = session.tool_calls
    
    coverage, missing = grade_coverage(calls, spec.required_tools)
    order, violations = grade_order(calls, spec.ordering_constraints)
    efficiency, eff_diag = grade_efficiency(calls, spec.max_expected_calls)
    recovery, rec_diag = grade_error_recovery(calls)
    
    called_names = {tc.tool_name for tc in calls}
    called_forbidden = [f for f in spec.forbidden_tools if f in called_names]
    forbidden_penalty = -0.1 * len(called_forbidden)
    
    return SequenceGradeResult(
        coverage_score=coverage,
        order_score=order,
        efficiency_score=efficiency,
        error_recovery_score=recovery,
        forbidden_penalty=forbidden_penalty,
        missing_required=missing,
        called_forbidden=called_forbidden,
        retry_events=eff_diag["retries"],
        error_taxonomy=rec_diag["taxonomy"],
    )
The LLM Judge Layer
For cases that are hard to grade deterministically — like "did it use a sensible approach even if it took an unusual path?" — add a judge call on top:

python
def llm_judge_sequence(
    session: EvalSession,
    spec: TaskSpec,
    deterministic_result: SequenceGradeResult
) -> dict:
    
    # format the tool call log for the judge
    call_log = "\n".join([
        f"{i+1}. {tc.tool_name}({tc.inputs}) -> "
        f"{'OK' if tc.success else 'FAIL: ' + tc.error}"
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

Please assess:
1. Was the overall strategy sound, even if execution was imperfect?
2. Were there any clever adaptations when tools failed?
3. Were there any concerning patterns (e.g. guessing coordinates instead of querying)?
4. What is the single most important thing to fix?

Respond in JSON: {{"strategy_score": 0.0-1.0, "observations": [...], "top_priority_fix": "..."}}"""

    # call Claude API here as judge
    response = anthropic_client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return json.loads(response.content[0].text)
```

---

## What This Gets You

After a few eval runs, your results will look like:
```
Task: cswa_001_basic_prism
  coverage:    1.00  (all required tools called)
  order:       0.67  (filleted before querying edges - known issue)
  efficiency:  0.71  (18 calls vs expected 12)
  recovery:    0.50  (recovered 2/4 failures)
  ───────────────────
  total:       0.74

Error taxonomy:
  selection_error:      3   ← coordinate picking failing post-fillet
  sequence_error:       1   ← tried to fillet before body existed
  tool_error:           0   ← your tools are clean here
  recovered_failure:    2
  unrecovered_failure:  2
The taxonomy breakdown is the real payoff — when selection_error dominates, that's your coordinate-picking problem. When tool_error spikes, something broke in your MCP server. When sequence_error appears, the model's planning is off. Each category points to a different fix.