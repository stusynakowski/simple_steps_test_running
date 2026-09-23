"""
Known gaps, written as executable claims.

A gap recorded as an `xfail` is worth far more than a gap recorded in a
document: when the library is fixed, the xfail turns XPASS and the test run
tells you to promote the row. A gap in prose just rots.

Each test here asserts the behaviour we **want**, and is expected to fail
today. `strict=True` on purpose — an XPASS should be loud.
"""

from __future__ import annotations

import pytest

from simple_steps_core import CoreEngine, Operation, OrchestrationConfig, Workflow

from example0_identity_workflow import steps as tools


def _map_then(mode: str, op: str, over: str, **orchestration) -> Workflow:
    """step1 source -> step2 map -> step3 <mode> over *over*."""
    workflow = Workflow(CoreEngine(tools.build_registry()), session_id="gap")
    workflow["step1"] = Operation(
        step_id="step1", name="make_nested", arguments={"rows": 2, "per_row": 2}
    )
    workflow["step2"] = Operation(
        step_id="step2", name="identity",
        orchestration=OrchestrationConfig(mode="expand", over="step1"),
    )
    workflow["step3"] = Operation(
        step_id="step3", name="add_one",
        orchestration=OrchestrationConfig(mode="map", over="step2"),
    )
    workflow["step4"] = Operation(
        step_id="step4", name=op,
        orchestration=OrchestrationConfig(mode=mode, over=over, **orchestration),
    )
    return workflow


@pytest.mark.capability("orch.map")
@pytest.mark.xfail(
    strict=True,
    reason="A MapResult is a pydantic model, so iterating it yields one "
           "('outcomes', [...]) tuple. Orchestrating over a bare map step "
           "produces a WRONG ANSWER with no error. Should either iterate as "
           "its ok-values or refuse at validate time.",
)
def test_orchestrating_over_a_bare_map_step_should_not_silently_corrupt():
    workflow = _map_then("collapse", "total", over="step3")
    workflow.run()
    # items are [2,3,3,4]; a correct collapse totals them.
    assert workflow["step4"].output.value == 12


@pytest.mark.capability("orch.map", "inspect.validate")
@pytest.mark.xfail(
    strict=True,
    reason="Validation passes a reference to a bare map step even though the "
           "collapse will receive a tuple. The reference type check should "
           "catch MapResult -> collection.",
)
def test_validation_should_reject_a_collapse_over_a_bare_map_step():
    workflow = _map_then("collapse", "total", over="step3")
    assert "✓ ok" not in str(workflow.validate())


@pytest.mark.capability("orch.nested")
@pytest.mark.xfail(
    strict=True,
    reason="Two levels of fan-out (documents -> pages -> paragraphs). "
           "Unverified territory; recorded so it is not mistaken for working.",
)
def test_a_map_can_drive_a_nested_orchestration():
    raise NotImplementedError(
        "Write this once the intended nesting syntax is decided."
    )


def _indexed_reference_flow(ref: str) -> Workflow:
    """step2 echoes whatever `ref` resolves to."""
    registry = tools.build_registry()
    registry.register("echo", lambda value: value)
    workflow = Workflow(CoreEngine(registry), session_id="index")
    workflow["step1"] = Operation(
        step_id="step1", name="make_nested", arguments={"rows": 3, "per_row": 3}
    )
    workflow["step2"] = Operation(
        step_id="step2", name="echo", arguments={"value": ref}
    )
    return workflow


@pytest.mark.capability("flow.index_ref")
@pytest.mark.xfail(
    strict=True,
    reason="Bracket indexers are parsed out of a reference and then dropped: "
           "`step1[0]` resolves to the whole of step1. Even an out-of-range "
           "index like `step1[99]` returns the full value instead of raising.",
)
def test_a_bracket_index_selects_one_element_of_a_step_output():
    workflow = _indexed_reference_flow("step1[0]")
    workflow.run()
    assert workflow["step2"].output.value == [1, 2, 3]


@pytest.mark.capability("flow.index_ref")
def test_a_bracket_index_is_currently_ignored_entirely():
    """Pin down today's behaviour, including the out-of-range case.

    `step1[99]` returning the whole collection rather than raising is the
    part that turns a typo into a silent wrong answer downstream.
    """
    whole = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    for ref in ("step1[0]", "step1[1]", "step1[99]"):
        workflow = _indexed_reference_flow(ref)
        workflow.run()
        assert workflow["step2"].output.value == whole, f"{ref} behaved differently"
