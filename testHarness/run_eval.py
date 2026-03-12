"""
SolidWorks MCP AI Eval Runner - CLI entry point.

Usage:
    python -m testHarness.run_eval                           # Run all tasks
    python -m testHarness.run_eval --task basic_prism        # Run one task
    python -m testHarness.run_eval --list                    # List available tasks
    python -m testHarness.run_eval --model qwen2.5:14b       # Specify model
    python -m testHarness.run_eval --base-url http://...     # Custom API endpoint
    python -m testHarness.run_eval --judge                   # Enable LLM judge
    python -m testHarness.run_eval --runs 3                  # Repeat N times per task
"""

import argparse
import json
import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    parser = argparse.ArgumentParser(
        description="SolidWorks MCP AI Eval Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--task", type=str, help="Run a single task by ID")
    parser.add_argument("--list", action="store_true", help="List available tasks")
    parser.add_argument("--model", type=str, default="qwen2.5:14b",
                        help="LLM model name (default: qwen2.5:14b)")
    parser.add_argument("--base-url", type=str, default="http://localhost:11434/v1",
                        help="OpenAI-compatible API base URL (default: Ollama)")
    parser.add_argument("--api-key", type=str, default="ollama",
                        help="API key (default: ollama)")
    parser.add_argument("--judge", action="store_true",
                        help="Enable LLM judge grader")
    parser.add_argument("--judge-model", type=str, default=None,
                        help="Model for LLM judge (defaults to same as --model)")
    parser.add_argument("--runs", type=int, default=1,
                        help="Number of runs per task (default: 1)")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Output directory for results")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose logging")
    args = parser.parse_args()

    # Setup logging
    import logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stderr)],
    )

    from testHarness.task_loader import TaskLoader

    tasks_dir = Path(__file__).parent / "tasks"
    loader = TaskLoader(str(tasks_dir))

    # List mode
    if args.list:
        specs = loader.load_all()
        print(f"\nAvailable tasks ({len(specs)}):\n")
        for s in specs:
            desc = s.description.strip().replace("\n", " ")[:60]
            print(f"  {s.task_id:30s} [{s.difficulty:12s}] {desc}...")
        print()
        return

    # Initialize COM for SolidWorks
    import pythoncom
    pythoncom.CoInitialize()

    from testHarness.middleware import InstrumentedServer
    from testHarness.runner import EvalRunner
    from testHarness.llm.openai_compat import OpenAICompatProvider
    from testHarness.graders.aggregate import grade

    # Setup LLM provider
    provider = OpenAICompatProvider(
        base_url=args.base_url,
        api_key=args.api_key,
        model=args.model,
    )

    # Setup judge provider if requested
    judge_provider = None
    if args.judge:
        judge_model = args.judge_model or args.model
        judge_provider = OpenAICompatProvider(
            base_url=args.base_url,
            api_key=args.api_key,
            model=judge_model,
        )

    # Setup instrumented server
    print("Connecting to SolidWorks...")
    server = InstrumentedServer()
    runner = EvalRunner(provider, server)

    # Load tasks
    if args.task:
        specs = [loader.load(args.task)]
    else:
        specs = loader.load_all()

    # Output directory
    output_dir = Path(args.output_dir) if args.output_dir else Path(__file__).parent / "results"
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    all_results = []

    for spec in specs:
        for run_idx in range(args.runs):
            print(f"\n{'=' * 60}")
            print(f"  Task:  {spec.task_id} (run {run_idx + 1}/{args.runs})")
            print(f"  Model: {args.model}")
            print(f"  Diff:  {spec.difficulty}")
            print(f"{'=' * 60}")

            session = runner.run(spec)
            grade_result = grade(session, spec, server, judge_provider)

            # Print summary
            print(f"\n  Results:")
            print(f"    Coverage:       {grade_result.coverage_score:.2f}")
            print(f"    Order:          {grade_result.order_score:.2f}")
            print(f"    Efficiency:     {grade_result.efficiency_score:.2f}")
            print(f"    Error Recovery: {grade_result.error_recovery_score:.2f}")
            print(f"    Geometry:       {grade_result.geometry_score:.2f}")
            print(f"    {'─' * 28}")
            print(f"    Weighted Total: {grade_result.weighted_total:.2f}")

            if grade_result.missing_required:
                print(f"    Missing tools:  {grade_result.missing_required}")
            if grade_result.called_forbidden:
                print(f"    Forbidden used: {grade_result.called_forbidden}")
            if grade_result.order_violations:
                print(f"    Order issues:   {len(grade_result.order_violations)}")
            if grade_result.error_taxonomy:
                tax = grade_result.error_taxonomy
                errs = {k: v for k, v in tax.items() if v > 0}
                if errs:
                    print(f"    Error taxonomy: {errs}")

            print(f"\n    Tool calls:  {len(session.tool_calls)}")
            print(f"    Completed:   {session.completed}")
            print(f"    Timed out:   {session.timed_out}")
            if session.git_commit:
                print(f"    Git commit:  {session.git_commit[:8]}")
            if session.git_branch:
                print(f"    Git branch:  {session.git_branch}")

            if session.error:
                print(f"    Error:       {session.error[:100]}")

            if grade_result.judge_result:
                jr = grade_result.judge_result
                if "strategy_score" in jr:
                    print(f"    Judge score: {jr['strategy_score']:.2f}")
                if "top_priority_fix" in jr:
                    print(f"    Top fix:     {jr['top_priority_fix']}")

            # Build result record
            duration = None
            if session.end_time:
                duration = session.end_time - session.start_time

            run_data = {
                "task_id": spec.task_id,
                "model": args.model,
                "run_index": run_idx,
                "timestamp": timestamp,
                "git_commit": session.git_commit,
                "git_branch": session.git_branch,
                "completed": session.completed,
                "timed_out": session.timed_out,
                "total_tool_calls": len(session.tool_calls),
                "duration_seconds": duration,
                "scores": {
                    "coverage": grade_result.coverage_score,
                    "order": grade_result.order_score,
                    "efficiency": grade_result.efficiency_score,
                    "error_recovery": grade_result.error_recovery_score,
                    "geometry": grade_result.geometry_score,
                    "weighted_total": grade_result.weighted_total,
                },
                "diagnostics": {
                    "missing_required": grade_result.missing_required,
                    "called_forbidden": grade_result.called_forbidden,
                    "order_violations": grade_result.order_violations,
                    "error_taxonomy": grade_result.error_taxonomy,
                    "geometry_detail": grade_result.geometry_detail,
                    "retry_events": grade_result.retry_events,
                },
                "tool_calls": [
                    {
                        "index": tc.call_index,
                        "name": tc.tool_name,
                        "inputs": tc.inputs,
                        "output": tc.output[:500],  # truncate large outputs
                        "success": tc.success,
                        "error": tc.error,
                        "duration_ms": round(tc.duration_ms, 1),
                    }
                    for tc in session.tool_calls
                ],
            }

            if grade_result.judge_result:
                run_data["judge"] = grade_result.judge_result

            all_results.append(run_data)

    # Write combined results file
    model_safe = args.model.replace(":", "_").replace("/", "_")
    results_file = output_dir / f"eval_{timestamp}_{model_safe}.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, default=str)

    print(f"\n  Results saved to: {results_file}")

    # Print aggregate summary if multiple runs
    if len(all_results) > 1:
        print(f"\n{'=' * 60}")
        print(f"  AGGREGATE SUMMARY ({len(all_results)} runs)")
        print(f"{'=' * 60}")

        totals = [r["scores"]["weighted_total"] for r in all_results]
        print(f"  Mean score:  {sum(totals) / len(totals):.2f}")
        print(f"  Min:         {min(totals):.2f}")
        print(f"  Max:         {max(totals):.2f}")

        # Per-task breakdown
        task_ids = sorted(set(r["task_id"] for r in all_results))
        if len(task_ids) > 1:
            print()
            for tid in task_ids:
                task_scores = [r["scores"]["weighted_total"] for r in all_results if r["task_id"] == tid]
                avg = sum(task_scores) / len(task_scores)
                print(f"  {tid:30s}  avg={avg:.2f}  n={len(task_scores)}")

    print()


if __name__ == "__main__":
    main()
