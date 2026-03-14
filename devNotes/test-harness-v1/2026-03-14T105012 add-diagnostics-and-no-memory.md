# Add Diagnostics Reporting & Disable Memory for Test Agents

## Changes to `testHarness/run_full_suite.py`

### Diagnostics reporting
- Added `DIAGNOSTIC_SUFFIX` appended to every test prompt — asks the sub-agent to output a `## DIAGNOSTICS` section when tool calls fail, listing tool name, error, and suspected root cause / suggested fix.
- Added `_parse_diagnostics()` to extract that section from stdout.
- Result dict now includes a `diagnostics` field.
- Console prints diagnostics inline during the run.
- Markdown report shows "Agent diagnostics" block for failed tests, above the raw output tail.

### No memory for sub-agents
- Added `--no-memory` flag to the `claude` CLI invocation so test sub-agents don't read or write memory.
