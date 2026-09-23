"""
The core capabilities the two examples do not naturally exercise.

The parity battery covers everything that falls out of running a pipeline.
These three do not: stepping through a flow one step at a time, rejecting a
typo'd reference, and retrying a flaky item. All three are `core` priority —
an application cannot be built without them — so they get explicit tests
rather than waiting for an example that happens to need them.
"""

from __future__ import annotations

import asyncio

import pytest

from simple_steps_core import (
    CoreEngine,
    Operation,
    OrchestrationConfig,
    StepExecutionConfig,
    StepStatus,
    Workflow,
)

from capability.flow import StandardFlow
from example0_identity_workflow import steps


# ── exec.step ────────────────────────────────────────────────────────────
@pytest.mark.capability("exec.step")
def test_a_flow_can_be_advanced_one_step_at_a_time():
    """What an interactive dashboard does: one step per click.

    The steps after the one just run must stay `pending`, and the values must
    match what running the whole flow at once produces.
    """
    workflow = steps.build_flow().build()
    expected = steps.run_plain()

    assert all(s.status is StepStatus.PENDING for s in workflow.steps)

    for index, step_id in enumerate(["step1", "step2", "step3"]):
        workflow.run_step(step_id)
        assert workflow[step_id].status is StepStatus.COMPLETED
        assert workflow[step_id].output.value == expected[step_id]
        # Nothing downstream was dragged along.
        for later in workflow.steps[index + 1:]:
            assert later.status is StepStatus.PENDING, (
                f"{later.step_id} ran while stepping through {step_id}"
            )


# ── flow.unknown_ref ─────────────────────────────────────────────────────
def _typoed_reference_flow() -> Workflow:
    """step2 maps over `setp1` — a typo for `step1`, which does exist."""
    workflow = Workflow(CoreEngine(steps.build_registry()), session_id="bad-ref")
    workflow["step1"] = Operation(
        step_id="step1", name="make_nested", arguments={"rows": 2, "per_row": 2}
    )
    workflow["step2"] = Operation(
        step_id="step2", name="add_one",
        orchestration=OrchestrationConfig(mode="map", over="setp1"),  # typo
    )
    return workflow


@pytest.mark.capability("flow.unknown_ref", "inspect.validate")
@pytest.mark.xfail(
    strict=True,
    reason="A reference is recognised by its `step` prefix, so any typo that "
           "breaks the prefix stops being a reference and becomes a plain "
           "string literal. Validation reports 'references check out'.",
)
def test_a_reference_to_a_step_that_does_not_exist_fails_validation():
    report = str(_typoed_reference_flow().validate())
    assert "✓ ok" not in report, f"a typo'd reference validated clean:\n{report}"


@pytest.mark.capability("flow.unknown_ref")
def test_a_typoed_reference_degrades_to_a_literal_string(): 
    """Pin down what actually happens today, because it is genuinely bad.

    `over="setp1"` is not a reference, so it is passed through as the literal
    5-character string `"setp1"`. `map` then iterates it **character by
    character**: five items, five failures, and the step still reports
    COMPLETED with an empty result.

    Nothing in the run says "you typed a step id wrong". This test exists so
    that when the behaviour is fixed, it fails and points here.
    """
    workflow = _typoed_reference_flow()
    asyncio.run(workflow.arun())

    result = workflow["step2"].output.value
    assert workflow["step2"].status is StepStatus.COMPLETED
    assert len(result.failed) == len("setp1") == 5, (
        "the literal string was iterated per character"
    )
    assert result.ok == []


# ── orch.retries ─────────────────────────────────────────────────────────
class Flaky:
    """Fails the first *failures* times it sees a value, then succeeds.

    A class rather than a closure so each test gets its own attempt counter
    and the two cases below cannot interfere.
    """

    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.attempts: dict[int, int] = {}

    def __call__(self, value: int) -> int:
        seen = self.attempts.get(value, 0) + 1
        self.attempts[value] = seen
        if seen <= self.failures:
            raise RuntimeError(f"transient failure {seen} for {value}")
        return value * 10


def _flaky_flow(flaky: Flaky, *, retries: int) -> Workflow:
    registry = steps.build_registry()
    registry.register("flaky", flaky)
    return (
        StandardFlow(registry, session_id="retries")
        .source("make_nested", rows=1, per_row=3)      # [[1, 2, 3]]
        .shape()                                       # -> [1, 2, 3]
        .work("flaky", retries=retries, on_error="collect")
    ).build()


@pytest.mark.capability("orch.retries")
def test_a_transient_failure_is_retried_until_it_succeeds():
    flaky = Flaky(failures=2)
    workflow = _flaky_flow(flaky, retries=2)
    asyncio.run(workflow.arun())

    result = workflow["step3"].output.value
    assert result.ok == [10, 20, 30], "every item should survive two retries"
    assert result.failed == []
    # Three attempts each: two failures, then the success.
    assert flaky.attempts == {1: 3, 2: 3, 3: 3}


@pytest.mark.capability("orch.retries", "orch.on_error_collect")
def test_an_item_that_exhausts_its_retries_is_collected_as_a_failure():
    flaky = Flaky(failures=5)                          # more than we allow
    workflow = _flaky_flow(flaky, retries=1)
    asyncio.run(workflow.arun())

    result = workflow["step3"].output.value
    assert result.ok == []
    assert len(result.failed) == 3
    assert "transient failure" in result.failed[0].error
    # Two attempts each: the original plus one retry.
    assert flaky.attempts == {1: 2, 2: 2, 3: 2}
