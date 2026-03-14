# Add Full Test Suite Runner via Claude Code CLI

## What changed

Created `testHarness/run_full_suite.py` — a script that runs the full SolidWorks MCP test suite by sending natural language prompts to Claude Code CLI (`claude --print`). Each test asks Claude to use the MCP tools to accomplish a CAD task, then verifies keywords in the output.

### New files
- `testHarness/test_definitions.py` — 43 test definitions across 7 categories (Basic, Sketch Tools, Feature Tools, Patterns, Geometry Query, Reference Geometry, Integration). Each test has a name, prompt, and verification keywords.
- `testHarness/run_full_suite.py` — CLI runner with `--model`, `--category`, `--test`, `--list`, `--json`, `--no-log` flags. Automatically logs results to `devNotes/<branch>/<timestamp> <title>.md`.

### Modified files
- `CLAUDE.md` — Added development journal instructions and documented the new runner commands.

## Design decisions

- Tests are natural language prompts (not direct COM calls) to test the full LLM + MCP pipeline.
- Verification uses keyword matching in Claude's output (e.g., "volume", "fillet", "chamfer").
- Results are logged as markdown in `devNotes/` for human readability, with optional JSON export for analysis.
- Test definitions are separate from the runner for maintainability.

## Test count: 43 tests in 7 categories
- Basic: 3
- Sketch Tools: 14
- Feature Tools: 11
- Patterns: 3
- Geometry Query: 6
- Reference Geometry: 3
- Integration: 3
