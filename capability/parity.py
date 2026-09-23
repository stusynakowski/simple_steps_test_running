"""
The parity template
===================

One description of an example; one shared battery of checks that runs against
every example that provides it. Adding an example means writing an
:class:`ExampleSpec` — the whole battery then applies to it automatically, so
coverage grows by construction rather than by remembering to copy tests.

The method is **differential testing**. Each example exists twice:

* ``functions.py`` — plain Python, importing nothing from the library. The
  *oracle*.
* ``steps.py``     — the same functions registered as tools and assembled
  into a Workflow.

Neither is trusted on its own. A test that asserts a workflow produced
``30`` is only as good as whoever typed ``30``; a test that asserts the
workflow and a plain Python loop *agree at every phase* is much harder to be
wrong about, and it localises the disagreement to the phase that broke.

What the battery covers, per example:

    parity.registered      every plain function is a registered tool
    parity.per_function    each tool alone == its plain function
    parity.validates       the flow passes validation before running
    parity.phases          each phase's value == the reference's
    parity.end_to_end      the final value == the reference's
    parity.deterministic   running twice gives the same answer
    parity.round_trip      a JSON round-trip still gives the same answer
    parity.adapters        every tool that is not the plain function is declared
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


def unwrap(value: Any) -> Any:
    """Normalize a step's output for comparison with plain Python.

    A ``map`` step yields a ``MapResult`` rather than a list, so every
    comparison against a plain list would fail on type alone. ``.ok`` is the
    list of successful values, which is what the plain pipeline produced.
    Done here, once, so no test has to remember it.
    """
    return value.ok if hasattr(value, "ok") else value


@dataclass(frozen=True)
class ExampleSpec:
    """Everything the shared battery needs to test one example."""

    #: Short id, used in test ids.
    name: str
    #: Builds a fresh ToolRegistry with this example's tools.
    build_registry: Callable[[], Any]
    #: Builds a StandardFlow. Must accept no required arguments.
    build_flow: Callable[..., Any]
    #: The plain-Python pipeline. Returns {"step1": ..., "step2": ..., ...}.
    run_plain: Callable[..., dict]
    #: name -> plain function, the oracle's own table.
    functions: dict[str, Callable]
    #: Step ids to compare, in order. Anything not listed is skipped.
    phases: tuple[str, ...]
    #: Tools registered as something other than the untouched plain function,
    #: with the reason. Every entry is glue the library made us write.
    adapted: dict[str, str] = field(default_factory=dict)
    #: True when the flow must be driven with `arun()` rather than `run()`.
    is_async: bool = False
    #: Per-function sample inputs for the per-function parity check:
    #: name -> list of kwargs dicts. A function with no entry is skipped.
    samples: dict[str, list[dict]] = field(default_factory=dict)

    def run_workflow(self, **kwargs) -> Any:
        """Build and run the flow, returning the executed Workflow."""
        workflow = self.build_flow(**kwargs).build()
        if self.is_async:
            asyncio.run(workflow.arun())
        else:
            workflow.run()
        return workflow

    def workflow_values(self, workflow) -> dict[str, Any]:
        """The workflow's per-phase values, normalized for comparison."""
        return {
            step_id: unwrap(workflow[step_id].output.value)
            for step_id in self.phases
        }


def load_examples() -> list[ExampleSpec]:
    """Every example registered with the battery.

    Imported lazily so a broken example surfaces as that example's failure
    rather than a collection error that hides the whole suite.
    """
    from example0_identity_workflow import steps as example0
    from example1_basic_math_workflow import steps as example1

    return [
        ExampleSpec(
            name="example0_identity",
            build_registry=example0.build_registry,
            build_flow=example0.build_flow,
            run_plain=example0.run_plain,
            functions=example0.FUNCTIONS,
            phases=("step1", "step2", "step3", "step4", "step5"),
            is_async=False,
            samples={
                "make_nested": [{"rows": 1, "per_row": 1}, {"rows": 3, "per_row": 3}],
                "is_odd": [{"value": 1}, {"value": 2}, {"value": 0}, {"value": -3}],
                "add_one": [{"value": 0}, {"value": -1}, {"value": 99}],
                "total": [{"accumulator": 0, "item": 5},
                          {"accumulator": None, "item": 5}],
            },
        ),
        ExampleSpec(
            name="example1_math",
            build_registry=example1.build_registry,
            build_flow=example1.build_flow,
            run_plain=example1.run_plain,
            functions=example1.FUNCTIONS,
            phases=("step1", "step2", "step3", "step4"),
            is_async=True,
            adapted={
                "scale_async":
                    "needs a `Resource()` parameter default, which a pure "
                    "function cannot carry",
            },
            samples={
                "load_readings": [{"count": 1}, {"count": 10, "start": 0.0}],
                "above_cutoff": [{"value": 12.0}, {"value": 11.9},
                                 {"value": 50.0, "cutoff": 100.0}],
                "summarize": [{"accumulator": None, "item": 3.0},
                              {"accumulator": dict(example1.EMPTY_SUMMARY),
                               "item": 3.0}],
            },
        ),
    ]


EXAMPLES = load_examples()
IDS = [spec.name for spec in EXAMPLES]
