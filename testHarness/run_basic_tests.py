"""
Simple script that calls Claude Code non-interactively to run the basic tests.

Invokes `claude -p` with a prompt asking it to use the SolidWorks MCP tools
to create basic geometry, then captures and displays the results.

Usage:
    python testHarness/run_basic_tests.py
    python testHarness/run_basic_tests.py --model sonnet
    python testHarness/run_basic_tests.py --model haiku --max-turns 15
    python testHarness/run_basic_tests.py --json
"""

import subprocess
import sys
import argparse
import json
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

BASIC_TESTS = [
    {
        "name": "basic_cube",
        "prompt": (
            "Create a 100mm cube in SolidWorks. "
            "Start with solidworks_new_part, create a sketch on the Front plane, "
            "draw a 100x100mm rectangle centered at (50,50), then extrude it 100mm. "
            "After creating it, call solidworks_get_mass_properties to verify the volume "
            "is approximately 1,000,000 mm^3. Report the volume you get."
        ),
    },
    {
        "name": "basic_prism",
        "prompt": (
            "Create an 80mm x 40mm x 25mm rectangular prism in SolidWorks. "
            "Start with solidworks_new_part, create a sketch on the Front plane, "
            "draw an 80x40mm rectangle, then extrude it 25mm. "
            "Call solidworks_get_mass_properties to verify the volume "
            "is approximately 80,000 mm^3. Report the volume."
        ),
    },
    {
        "name": "basic_cylinder",
        "prompt": (
            "Create a cylinder in SolidWorks with radius 25mm and height 50mm. "
            "Start with solidworks_new_part, create a sketch on the Front plane, "
            "draw a circle with radius 25mm centered at (0,0), then extrude it 50mm. "
            "Call solidworks_get_mass_properties and report the volume. "
            "Expected volume is approximately 98,175 mm^3 (pi * 25^2 * 50)."
        ),
    },
]


def run_test(test: dict, max_turns: int, output_json: bool, model: str = None) -> dict:
    """Run a single test via Claude Code CLI."""
    name = test["name"]
    prompt = test["prompt"]

    print(f"\n{'─' * 50}")
    print(f"  Running: {name}" + (f"  (model: {model})" if model else ""))
    print(f"{'─' * 50}")

    cmd = [
        "claude",
        "--print", prompt,
        "--max-turns", str(max_turns),
        "--allowedTools", "mcp__solidworks__*",
    ]

    if model:
        cmd.extend(["--model", model])

    if output_json:
        cmd.extend(["--output-format", "json"])

    start = datetime.now()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 min timeout
            cwd=str(PROJECT_ROOT),
        )

        duration = (datetime.now() - start).total_seconds()
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        returncode = result.returncode

        # Display output
        if stdout:
            print(f"\n  Output:\n")
            for line in stdout.split("\n"):
                print(f"    {line}")

        if stderr and returncode != 0:
            print(f"\n  Stderr:\n")
            for line in stderr.split("\n")[:10]:
                print(f"    {line}")

        success = returncode == 0
        print(f"\n  Duration: {duration:.1f}s")
        print(f"  Exit code: {returncode}")
        print(f"  Status: {'PASS' if success else 'FAIL'}")

        return {
            "name": name,
            "model": model or "default",
            "success": success,
            "returncode": returncode,
            "duration_seconds": round(duration, 1),
            "stdout": stdout,
            "stderr": stderr[:500] if stderr else "",
        }

    except subprocess.TimeoutExpired:
        duration = (datetime.now() - start).total_seconds()
        print(f"\n  TIMEOUT after {duration:.0f}s")
        return {
            "name": name,
            "model": model or "default",
            "success": False,
            "returncode": -1,
            "duration_seconds": round(duration, 1),
            "stdout": "",
            "stderr": "Timed out after 300s",
        }
    except FileNotFoundError:
        print("\n  ERROR: 'claude' command not found. Is Claude Code CLI installed?")
        print("  Install with: npm install -g @anthropic-ai/claude-code")
        return {
            "name": name,
            "model": model or "default",
            "success": False,
            "returncode": -1,
            "duration_seconds": 0,
            "stdout": "",
            "stderr": "claude CLI not found",
        }


def main():
    parser = argparse.ArgumentParser(description="Run basic SolidWorks tests via Claude Code CLI")
    parser.add_argument("--max-turns", type=int, default=10,
                        help="Max agentic turns per test (default: 10)")
    parser.add_argument("--json", action="store_true",
                        help="Request JSON output from Claude")
    parser.add_argument("--test", type=str,
                        help="Run a single test by name (basic_cube, basic_prism, basic_cylinder)")
    parser.add_argument("--model", type=str, default=None,
                        help="Claude model to use (e.g. sonnet, haiku, opus, claude-sonnet-4-20250514)")
    parser.add_argument("--save", action="store_true",
                        help="Save results to testHarness/results/")
    args = parser.parse_args()

    tests = BASIC_TESTS
    if args.test:
        tests = [t for t in BASIC_TESTS if t["name"] == args.test]
        if not tests:
            print(f"Unknown test: {args.test}")
            print(f"Available: {[t['name'] for t in BASIC_TESTS]}")
            sys.exit(1)

    print(f"Running {len(tests)} basic test(s) via Claude Code CLI")
    print(f"Max turns per test: {args.max_turns}")
    if args.model:
        print(f"Model: {args.model}")

    results = []
    for test in tests:
        result = run_test(test, args.max_turns, args.json, args.model)
        results.append(result)

    # Summary
    passed = sum(1 for r in results if r["success"])
    total = len(results)
    print(f"\n{'=' * 50}")
    print(f"  SUMMARY: {passed}/{total} passed")
    print(f"{'=' * 50}")
    for r in results:
        status = "PASS" if r["success"] else "FAIL"
        print(f"  {status}  {r['name']:20s}  ({r['duration_seconds']}s)")

    # Save results
    if args.save:
        results_dir = Path(__file__).parent / "results"
        results_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        model_tag = (args.model or "default").replace(":", "_").replace("/", "_")
        results_file = results_dir / f"basic_tests_{timestamp}_{model_tag}.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n  Saved to: {results_file}")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
