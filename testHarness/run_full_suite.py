"""
Run the full SolidWorks MCP test suite via Claude Code CLI.

Each test sends a natural language prompt to `claude --print`, which uses the
SolidWorks MCP tools to accomplish the task.

Reports are saved to testHarness/testResults/ (markdown + optional JSON).
A brief journal entry referencing the report is written to devNotes/<branch>/.

Usage:
    python testHarness/run_full_suite.py                          # Run all tests
    python testHarness/run_full_suite.py --model sonnet            # Specify model
    python testHarness/run_full_suite.py --category "Sketch Tools" # One category
    python testHarness/run_full_suite.py --test basic_cube         # One test
    python testHarness/run_full_suite.py --list                    # List all tests
    python testHarness/run_full_suite.py --max-turns 20            # Override turn limit
    python testHarness/run_full_suite.py --no-devnotes             # Skip devNotes entry
    python testHarness/run_full_suite.py --json                    # Also save JSON results
"""

import subprocess
import sys
import os
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

# Force UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

PROJECT_ROOT = Path(__file__).parent.parent

# Ensure testHarness package is importable when run as a script
sys.path.insert(0, str(Path(__file__).parent))
from test_definitions import get_tests, get_categories, list_all_tests, FULL_TEST_SUITE


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def get_branch_name():
    """Get current git branch name."""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        return result.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def get_git_commit():
    """Get current git short commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        return result.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

def run_test(test: dict, max_turns: int, model: str = None) -> dict:
    """Run a single test via Claude Code CLI and return structured result."""
    name = test["name"]
    prompt = test["prompt"]
    timeout = test.get("timeout", 300)
    turns = test.get("max_turns", max_turns)

    print(f"\n{'─' * 60}")
    print(f"  [{test['category']}] {test['display_name']}")
    if model:
        print(f"  Model: {model}")
    print(f"{'─' * 60}")

    cmd = [
        "claude",
        "--print", prompt,
        "--max-turns", str(turns),
        "--allowedTools", "mcp__solidworks__*",
    ]

    if model:
        cmd.extend(["--model", model])

    start = datetime.now()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
            cwd=str(PROJECT_ROOT),
        )

        duration = (datetime.now() - start).total_seconds()
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        returncode = result.returncode

        # Display output (truncated for readability)
        if stdout:
            lines = stdout.split("\n")
            display_lines = lines[:30]
            print(f"\n  Output ({len(lines)} lines):\n")
            for line in display_lines:
                print(f"    {line}")
            if len(lines) > 30:
                print(f"    ... ({len(lines) - 30} more lines)")

        if stderr and returncode != 0:
            print(f"\n  Stderr:")
            for line in stderr.split("\n")[:5]:
                print(f"    {line}")

        # Verification: check for required keywords
        verify_keywords = test.get("verify", [])
        stdout_lower = stdout.lower()
        keywords_found = []
        keywords_missing = []
        for kw in verify_keywords:
            if kw.lower() in stdout_lower:
                keywords_found.append(kw)
            else:
                keywords_missing.append(kw)

        # Test passes if exit code is 0 AND all verification keywords found
        success = returncode == 0 and len(keywords_missing) == 0

        print(f"\n  Duration: {duration:.1f}s")
        print(f"  Exit code: {returncode}")
        if verify_keywords:
            print(f"  Verify: {len(keywords_found)}/{len(verify_keywords)} keywords found", end="")
            if keywords_missing:
                print(f" (missing: {keywords_missing})", end="")
            print()
        status = "PASS" if success else "FAIL"
        print(f"  Status: {status}")

        return {
            "name": name,
            "display_name": test["display_name"],
            "category": test["category"],
            "model": model or "default",
            "success": success,
            "returncode": returncode,
            "duration_seconds": round(duration, 1),
            "keywords_found": keywords_found,
            "keywords_missing": keywords_missing,
            "stdout": stdout,
            "stderr": stderr[:500] if stderr else "",
        }

    except subprocess.TimeoutExpired:
        duration = (datetime.now() - start).total_seconds()
        print(f"\n  TIMEOUT after {duration:.0f}s")
        return {
            "name": name,
            "display_name": test["display_name"],
            "category": test["category"],
            "model": model or "default",
            "success": False,
            "returncode": -1,
            "duration_seconds": round(duration, 1),
            "keywords_found": [],
            "keywords_missing": test.get("verify", []),
            "stdout": "",
            "stderr": f"Timed out after {timeout}s",
        }
    except FileNotFoundError:
        print("\n  ERROR: 'claude' CLI not found. Install: npm install -g @anthropic-ai/claude-code")
        return {
            "name": name,
            "display_name": test["display_name"],
            "category": test["category"],
            "model": model or "default",
            "success": False,
            "returncode": -1,
            "duration_seconds": 0,
            "keywords_found": [],
            "keywords_missing": test.get("verify", []),
            "stdout": "",
            "stderr": "claude CLI not found",
        }


# ---------------------------------------------------------------------------
# Results logging
# ---------------------------------------------------------------------------

def write_test_report(results: list, model: str, branch: str, commit: str,
                      start_time: datetime, categories_run: str):
    """Write detailed test report to testHarness/testResults/."""
    timestamp = start_time.strftime("%Y-%m-%dT%H%M%S")
    model_tag = (model or "default").replace(":", "-").replace("/", "-")
    filename = f"{timestamp}_{model_tag}.md"

    report_dir = Path(__file__).parent / "testResults"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / filename

    passed = sum(1 for r in results if r["success"])
    total = len(results)
    total_duration = sum(r["duration_seconds"] for r in results)

    lines = [
        f"# Test Suite Report: {model_tag}",
        f"",
        f"- **Date**: {start_time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- **Branch**: {branch}",
        f"- **Commit**: {commit}",
        f"- **Model**: {model or 'default'}",
        f"- **Categories**: {categories_run}",
        f"- **Result**: {passed}/{total} passed",
        f"- **Total Duration**: {total_duration:.1f}s",
        f"",
        f"## Summary",
        f"",
        f"| Status | Test | Category | Duration |",
        f"|--------|------|----------|----------|",
    ]

    for r in results:
        status = "PASS" if r["success"] else "FAIL"
        emoji = "+" if r["success"] else "-"
        lines.append(
            f"| {emoji} {status} | {r['display_name']} | {r['category']} | {r['duration_seconds']}s |"
        )

    lines.append("")

    # Category breakdown
    lines.append("## By Category")
    lines.append("")
    cat_results = {}
    for r in results:
        cat = r["category"]
        if cat not in cat_results:
            cat_results[cat] = {"passed": 0, "total": 0}
        cat_results[cat]["total"] += 1
        if r["success"]:
            cat_results[cat]["passed"] += 1

    for cat, counts in cat_results.items():
        lines.append(f"- **{cat}**: {counts['passed']}/{counts['total']}")
    lines.append("")

    # Failed test details
    failed = [r for r in results if not r["success"]]
    if failed:
        lines.append("## Failed Tests")
        lines.append("")
        for r in failed:
            lines.append(f"### {r['display_name']} (`{r['name']}`)")
            lines.append("")
            if r["keywords_missing"]:
                lines.append(f"- Missing keywords: {r['keywords_missing']}")
            if r["returncode"] != 0:
                lines.append(f"- Exit code: {r['returncode']}")
            if r["stderr"]:
                lines.append(f"- Error: `{r['stderr'][:200]}`")
            # Include last 20 lines of output for debugging
            if r["stdout"]:
                output_lines = r["stdout"].split("\n")[-20:]
                lines.append(f"- Output (last {len(output_lines)} lines):")
                lines.append("```")
                lines.extend(output_lines)
                lines.append("```")
            lines.append("")

    content = "\n".join(lines)
    report_path.write_text(content, encoding="utf-8")
    print(f"\n  Test report: {report_path}")
    return report_path


def write_devnotes_entry(report_path: Path, results: list, model: str,
                         branch: str, commit: str, start_time: datetime,
                         categories_run: str):
    """Write a brief journal entry to devNotes/<branch>/ referencing the report."""
    timestamp = start_time.strftime("%Y-%m-%dT%H%M%S")
    model_tag = (model or "default").replace(":", "-").replace("/", "-")
    filename = f"{timestamp} test-run-{model_tag}.md"

    log_dir = PROJECT_ROOT / "devNotes" / branch
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / filename

    passed = sum(1 for r in results if r["success"])
    total = len(results)
    failed_names = [r["name"] for r in results if not r["success"]]
    total_duration = sum(r["duration_seconds"] for r in results)

    # Make report path relative to project root for the reference
    try:
        rel_report = report_path.relative_to(PROJECT_ROOT)
    except ValueError:
        rel_report = report_path

    lines = [
        f"# Test Run: {model_tag}",
        f"",
        f"Ran {total} tests ({categories_run}) with model **{model or 'default'}** "
        f"on branch `{branch}` @ `{commit}`.",
        f"",
        f"**Result: {passed}/{total} passed** in {total_duration:.1f}s",
        f"",
    ]

    if failed_names:
        lines.append(f"Failed: {', '.join(f'`{n}`' for n in failed_names)}")
        lines.append("")

    lines.append(f"Full report: [`{rel_report}`](../{rel_report})")
    lines.append("")

    content = "\n".join(lines)
    log_path.write_text(content, encoding="utf-8")
    print(f"  DevNotes entry: {log_path}")
    return log_path


def save_json_results(results: list, model: str, start_time: datetime):
    """Save raw results to testHarness/testResults/ as JSON."""
    report_dir = Path(__file__).parent / "testResults"
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = start_time.strftime("%Y%m%dT%H%M%S")
    model_tag = (model or "default").replace(":", "_").replace("/", "_")
    results_file = report_dir / f"full_suite_{timestamp}_{model_tag}.json"

    payload = {
        "timestamp": start_time.isoformat(),
        "model": model or "default",
        "branch": get_branch_name(),
        "commit": get_git_commit(),
        "summary": {
            "passed": sum(1 for r in results if r["success"]),
            "failed": sum(1 for r in results if not r["success"]),
            "total": len(results),
            "total_duration_seconds": round(sum(r["duration_seconds"] for r in results), 1),
        },
        "results": results,
    }

    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"  JSON results: {results_file}")
    return results_file


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Run the full SolidWorks MCP test suite via Claude Code CLI"
    )
    parser.add_argument("--model", type=str, default=None,
                        help="Claude model (e.g. sonnet, haiku, opus, claude-sonnet-4-20250514)")
    parser.add_argument("--category", type=str, default=None,
                        help="Run only tests in this category")
    parser.add_argument("--test", type=str, default=None,
                        help="Run a single test by name")
    parser.add_argument("--max-turns", type=int, default=15,
                        help="Default max agentic turns per test (default: 15)")
    parser.add_argument("--list", action="store_true",
                        help="List all available tests and exit")
    parser.add_argument("--no-devnotes", action="store_true",
                        help="Skip writing devNotes journal entry")
    parser.add_argument("--json", action="store_true",
                        help="Also save JSON results alongside the markdown report")
    args = parser.parse_args()

    # List mode
    if args.list:
        print("\nAvailable tests:")
        list_all_tests()
        print(f"\n  Total: {len(FULL_TEST_SUITE)} tests in {len(get_categories())} categories")
        print(f"\n  Categories: {', '.join(get_categories())}")
        sys.exit(0)

    # Filter tests
    tests = get_tests(category=args.category, test_name=args.test)

    if not tests:
        print(f"No tests found matching criteria.")
        if args.test:
            print(f"  Available test names:")
            for t in FULL_TEST_SUITE:
                print(f"    {t['name']}")
        if args.category:
            print(f"  Available categories: {', '.join(get_categories())}")
        sys.exit(1)

    # Determine what we're running
    if args.test:
        categories_run = tests[0]["category"]
    elif args.category:
        categories_run = args.category
    else:
        categories_run = "All"

    branch = get_branch_name()
    commit = get_git_commit()
    start_time = datetime.now()

    print(f"\n{'=' * 60}")
    print(f"  SolidWorks MCP — Full Test Suite")
    print(f"{'=' * 60}")
    print(f"  Tests:      {len(tests)}")
    print(f"  Categories: {categories_run}")
    print(f"  Model:      {args.model or 'default'}")
    print(f"  Max turns:  {args.max_turns}")
    print(f"  Branch:     {branch}")
    print(f"  Commit:     {commit}")
    print(f"{'=' * 60}")

    # Run tests
    results = []
    for i, test in enumerate(tests, 1):
        print(f"\n  [{i}/{len(tests)}]", end="")
        result = run_test(test, args.max_turns, args.model)
        results.append(result)

    # Summary
    passed = sum(1 for r in results if r["success"])
    failed = sum(1 for r in results if not r["success"])
    total = len(results)
    total_duration = sum(r["duration_seconds"] for r in results)

    print(f"\n{'=' * 60}")
    print(f"  RESULTS: {passed}/{total} passed, {failed} failed")
    print(f"  Total duration: {total_duration:.1f}s")
    print(f"{'=' * 60}")

    # Per-category summary
    cat_results = {}
    for r in results:
        cat = r["category"]
        if cat not in cat_results:
            cat_results[cat] = {"passed": 0, "failed": 0}
        if r["success"]:
            cat_results[cat]["passed"] += 1
        else:
            cat_results[cat]["failed"] += 1

    for cat, counts in cat_results.items():
        total_cat = counts["passed"] + counts["failed"]
        print(f"  {cat:25s}  {counts['passed']}/{total_cat}")

    print()
    for r in results:
        status = "PASS" if r["success"] else "FAIL"
        print(f"  {status}  {r['name']:30s}  {r['category']:20s}  ({r['duration_seconds']}s)")

    # Write report to testHarness/testResults/ (always)
    report_path = write_test_report(
        results, args.model, branch, commit, start_time, categories_run)

    # Write brief journal entry to devNotes/ referencing the report
    if not args.no_devnotes:
        write_devnotes_entry(
            report_path, results, args.model, branch, commit, start_time, categories_run)

    if args.json:
        save_json_results(results, args.model, start_time)

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
