#!/usr/bin/env python
"""
Run an example both ways and compare them, phase by phase.

    uv run python compare.py                      # every example
    uv run python compare.py example0_identity    # just one
    uv run python compare.py -v                   # full values, not truncated
    uv run python compare.py --set cutoff=15      # override a parameter
    uv run python compare.py --plain              # only the plain pipeline
    uv run python compare.py --workflow           # only the workflow

Every example exists twice: `functions.py` is ordinary Python that imports
nothing from the library, and `steps.py` registers those same functions as
tools. This script runs both and puts the results next to each other.

When they disagree, the plain column is right — it is not the thing under
test. Exits non-zero on any divergence, so it composes with a shell loop.
"""

from __future__ import annotations

import argparse
import inspect
import sys

from capability.parity import EXAMPLES, unwrap

BOLD, DIM, GREEN, RED, RESET = "\033[1m", "\033[2m", "\033[32m", "\033[31m", "\033[0m"


def _plain(text: str) -> str:
    """Strip colour when stdout is redirected, so diffs and pipes stay clean."""
    return text if sys.stdout.isatty() else ""


def paint(text: str, colour: str) -> str:
    return f"{_plain(colour)}{text}{_plain(RESET)}"


def show(value: object, *, width: int, verbose: bool) -> str:
    """One-line rendering of a value, truncated unless -v."""
    text = repr(value)
    if verbose or len(text) <= width:
        return text
    return text[: width - 1] + "…"


def accepted(fn, kwargs: dict) -> dict:
    """Keep only the kwargs *fn* actually declares.

    `build_flow` takes workflow-only knobs (`concurrency`, `retries`) that the
    plain pipeline has no equivalent for, so the same --set can reach both
    sides without either one blowing up on an unexpected keyword.
    """
    parameters = inspect.signature(fn).parameters
    if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in parameters.values()):
        return dict(kwargs)
    return {k: v for k, v in kwargs.items() if k in parameters}


def parse_value(text: str):
    """`15` -> 15, `15.0` -> 15.0, `collect` -> "collect"."""
    for cast in (int, float):
        try:
            return cast(text)
        except ValueError:
            continue
    return text


def tool_names(spec) -> dict[str, str]:
    """step id -> the tool that step runs, for the middle column."""
    return {step.step_id: step.name for step in spec.build_flow()._steps}


def compare(spec, *, overrides: dict, verbose: bool,
            run_plain: bool, run_workflow: bool) -> bool:
    """Print one example's comparison. True when the two sides agree."""
    mode = "async" if spec.is_async else "sync"
    header = f"{spec.name}"
    print(f"\n{paint(header, BOLD)}  {paint(f'{len(spec.phases)} phases · {mode}', DIM)}")
    if overrides:
        print(paint(f"  overrides: {overrides}", DIM))

    expected = actual = None
    if run_plain:
        expected = spec.run_plain(**accepted(spec.run_plain, overrides))
    if run_workflow:
        workflow = spec.run_workflow(**accepted(spec.build_flow, overrides))
        actual = spec.workflow_values(workflow)

    # Tool names come from the flow *definition*, so they are available even
    # when only the plain side is being run.
    tools = tool_names(spec)
    width = 34 if (run_plain and run_workflow) else 72

    if verbose:
        # Full values never fit in columns, so stack them per phase instead of
        # letting a long list shove the next column off the screen.
        agreed = True
        for step_id in spec.phases:
            print(f"\n  {paint(step_id, BOLD)}  {paint(tools.get(step_id, '—'), DIM)}")
            if run_plain:
                print(f"    plain    : {expected[step_id]!r}")
            if run_workflow:
                print(f"    workflow : {actual[step_id]!r}")
            if run_plain and run_workflow:
                same = expected[step_id] == actual[step_id]
                agreed &= same
                print(f"    {paint('✓ agree', GREEN) if same else paint('✗ DIVERGED', RED)}")
        print()
        if run_plain and run_workflow:
            print("  " + (paint(f"✓ all {len(spec.phases)} phases agree", GREEN)
                          if agreed else
                          paint("✗ diverged — the plain column is correct", RED)))
        print()
        return agreed

    columns = ["phase", "tool"]
    if run_plain:
        columns.append("plain")
    if run_workflow:
        columns.append("workflow")
    widths = [7, 14] + [width + 2] * (len(columns) - 2)
    print()
    print("  " + "".join(c.ljust(w) for c, w in zip(columns, widths)))
    print("  " + paint("".join("─" * (w - 2) + "  " for w in widths), DIM))

    agreed = True
    for step_id in spec.phases:
        row = [step_id, tools.get(step_id, "—")]
        if run_plain:
            row.append(show(expected[step_id], width=width, verbose=verbose))
        if run_workflow:
            row.append(show(actual[step_id], width=width, verbose=verbose))

        if run_plain and run_workflow:
            same = expected[step_id] == actual[step_id]
            agreed &= same
            mark = paint("✓", GREEN) if same else paint("✗", RED)
        else:
            mark = " "
        print("  " + "".join(str(c).ljust(w) for c, w in zip(row, widths)) + mark)

    if not (run_plain and run_workflow):
        print()
        return True

    print()
    if agreed:
        print("  " + paint(f"✓ all {len(spec.phases)} phases agree", GREEN))
    else:
        print("  " + paint("✗ diverged — the plain column is the correct one", RED))
        for step_id in spec.phases:
            if expected[step_id] != actual[step_id]:
                print(f"\n  {paint(step_id, BOLD)}")
                print(f"    plain    : {expected[step_id]!r}")
                print(f"    workflow : {actual[step_id]!r}")
    return agreed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run each example as plain Python and as a workflow, and "
                    "compare them phase by phase.")
    parser.add_argument("example", nargs="*",
                        help="example name(s); default: all of them")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="print values in full instead of truncating")
    parser.add_argument("--set", dest="overrides", action="append", default=[],
                        metavar="KEY=VALUE",
                        help="override a parameter, e.g. --set cutoff=15")
    parser.add_argument("--plain", action="store_true",
                        help="run only the plain-Python pipeline")
    parser.add_argument("--workflow", action="store_true",
                        help="run only the workflow")
    parser.add_argument("--list", action="store_true",
                        help="list the available examples and exit")
    args = parser.parse_args()

    if args.list:
        for spec in EXAMPLES:
            mode = "async" if spec.is_async else "sync"
            print(f"{spec.name:24} {len(spec.phases)} phases  {mode}")
        return 0

    chosen = EXAMPLES
    if args.example:
        chosen = [s for s in EXAMPLES if s.name in args.example]
        unknown = set(args.example) - {s.name for s in EXAMPLES}
        if unknown:
            print(f"unknown example(s): {', '.join(sorted(unknown))}", file=sys.stderr)
            print(f"available: {', '.join(s.name for s in EXAMPLES)}", file=sys.stderr)
            return 2

    overrides = dict(
        (key, parse_value(value))
        for key, _, value in (o.partition("=") for o in args.overrides)
    )

    # Neither flag given means both sides; either one given means just that one.
    run_plain = args.plain or not args.workflow
    run_workflow = args.workflow or not args.plain

    agreed = True
    for spec in chosen:
        agreed &= compare(spec, overrides=overrides, verbose=args.verbose,
                          run_plain=run_plain, run_workflow=run_workflow)
    print()
    return 0 if agreed else 1


if __name__ == "__main__":
    raise SystemExit(main())
