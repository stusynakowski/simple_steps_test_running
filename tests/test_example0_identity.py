"""
Example 0 — the identity flow, asserted phase by phase.

Each test claims the capabilities it proves. The claim is what puts a row in
CAPABILITIES.md; an unclaimed capability reads as `untested` no matter how
much code happens to touch it.

Assert on **shape and value**, not just status: a step that completes while
producing the wrong type is the failure mode that actually bites, and
`assert step.status is COMPLETED` sails straight past it.
"""

from __future__ import annotations

import pytest

from simple_steps_core import CoreEngine, Operation, StepStatus, Workflow

from example0_identity_workflow import steps as tools


@pytest.fixture
def flow():
    return tools.build_flow()


@pytest.fixture
def ran(flow):
    workflow = flow.build()
    workflow.run()
    return workflow


# ── authoring ────────────────────────────────────────────────────────────
@pytest.mark.capability("auth.plain", "inspect.tools")
def test_plain_functions_become_listable_tools():
    registry = tools.build_registry()
    ids = {d.tool_id for d in registry.list_definitions()}
    assert {"make_nested", "is_odd", "add_one", "total"} <= ids


@pytest.mark.capability("auth.schema", "auth.defaults", "auth.docstring")
def test_annotations_become_a_schema_with_optional_params():
    definition = tools.build_registry().get_definition("make_nested")
    schema = definition.input_schema
    assert schema["properties"]["rows"]["type"] == "integer"
    # Both params have defaults, so neither is required.
    assert not schema.get("required")
    assert definition.description.startswith("Produce a nested list")


@pytest.mark.capability("auth.dual_mode")
def test_a_tool_runs_immediately_and_defers():
    tool = tools.build_registry().get_operation("add_one")
    assert tool.run(value=1) == 2                       # immediate
    call = tool(value=1)                                # deferred
    assert call.operation_id == "add_one" and call.arguments == {"value": 1}


# ── the five phases ──────────────────────────────────────────────────────
@pytest.mark.capability("inspect.validate", "flow.step_ref")
def test_the_flow_validates_before_anything_runs(flow):
    assert "✓ ok" in str(flow.build().validate())


@pytest.mark.capability("orch.single", "orch.source", "flow.literal")
def test_source_runs_once_and_yields_the_nested_collection(ran):
    value = ran["step1"].output.value
    assert value == tools.NESTED
    assert len(value) == 3 and all(len(row) == 3 for row in value)


@pytest.mark.capability("orch.expand", "orch.identity")
def test_expand_flattens_one_level_without_a_bespoke_tool(ran):
    assert ran["step2"].output.value == [1, 2, 3, 4, 5, 6, 7, 8, 9]


@pytest.mark.capability("orch.filter")
def test_filter_keeps_only_the_items_that_qualify(ran):
    kept = ran["step3"].output.value
    assert kept == [1, 3, 5, 7, 9]
    assert set(kept) <= set(ran["step2"].output.value)


@pytest.mark.capability("orch.map")
@pytest.mark.awkward("map yields a MapResult, not a list; downstream needs .ok")
def test_map_yields_per_item_outcomes_rather_than_a_list(ran):
    result = ran["step4"].output.value
    assert not isinstance(result, list), "map's result is a MapResult, not a list"
    assert result.ok == [2, 4, 6, 8, 10]
    assert result.failed == []


@pytest.mark.capability("orch.collapse")
def test_collapse_reduces_the_collection_to_one_value(ran):
    assert ran["step5"].output.value == sum([2, 4, 6, 8, 10])


@pytest.mark.capability("exec.run_all")
def test_every_step_completes(ran):
    assert [s.status for s in ran.steps] == [StepStatus.COMPLETED] * 5


# ── edges ────────────────────────────────────────────────────────────────
@pytest.mark.capability("orch.empty")
def test_a_filter_that_keeps_nothing_does_not_break_the_steps_after_it():
    """A legitimately empty collection must flow through, not raise."""
    from capability.flow import StandardFlow

    # `is_even` never matches, so the filter keeps nothing and the map and
    # collapse after it both see an empty collection.
    registry = tools.build_registry()
    registry.register("is_even", lambda value: value % 2 == 0)

    workflow = (
        StandardFlow(registry, session_id="empty")
        .source("make_nested", rows=1, per_row=1)        # [[1]] -> [1], all odd
        .shape()
        .select("is_even")
        .work("add_one")
        .reduce("total")
    ).build()
    workflow.run()

    assert workflow["step3"].output.value == []
    assert all(s.status is StepStatus.COMPLETED for s in workflow.steps)


@pytest.mark.capability("inspect.preview", "inspect.info", "inspect.repr")
def test_a_workflow_can_be_inspected_without_running_it(flow):
    workflow = flow.build()
    assert "Workflow" in repr(workflow) or len(workflow) == 5
    assert str(workflow.info())


# ─────────────────────────────────────────────────────────────────────────
# Capabilities example 0 can reach without resources
#
# Everything below needs only plain data, which is exactly what example 0
# has. They live here rather than in example 1 because proving them against
# integers keeps the assertion about the library instead of about floats,
# async, or an injected client.
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.capability("auth.output_schema")
def test_the_return_annotation_becomes_an_output_schema():
    """`-> list[list[int]]` must survive into the contract.

    This is what lets the next step's reference be type-checked before
    anything runs.
    """
    schema = tools.build_registry().get_definition("make_nested").output_schema
    result = schema["properties"]["result"]
    assert result["type"] == "array"
    assert result["items"]["items"]["type"] == "integer", "nesting was flattened"


@pytest.mark.capability("auth.guardrails")
def test_a_guardrail_rejects_a_bad_argument_before_the_tool_runs():
    from simple_steps_core import ArgGuardrail, Guardrails, ValidationError

    registry = tools.build_registry()
    registry.register(
        "bounded", lambda value: value * 2,
        guardrails=Guardrails(arguments={"value": ArgGuardrail(minimum=0, maximum=10)}),
    )
    workflow = Workflow(CoreEngine(registry), session_id="guarded")
    workflow["step1"] = Operation(step_id="step1", name="bounded",
                                  arguments={"value": 99})

    with pytest.raises(ValidationError, match="above maximum"):
        workflow.run()

    # And a value inside the range is untouched.
    workflow["step1"] = Operation(step_id="step1", name="bounded",
                                  arguments={"value": 4})
    workflow.run()
    assert workflow["step1"].output.value == 8


@pytest.mark.capability("exec.stage")
def test_steps_can_be_grouped_into_stages_and_run_a_stage_at_a_time():
    registry = tools.build_registry()
    workflow = Workflow(CoreEngine(registry), session_id="staged")
    workflow["step1"] = Operation(step_id="step1", name="make_nested",
                                  arguments={"rows": 2, "per_row": 2}, stage=1)
    workflow["step2"] = Operation(step_id="step2", name="identity",
                                  arguments={"value": 7}, stage=2)

    assert workflow.stages() == [1, 2]
    workflow.run_stage(1)
    assert workflow["step1"].status is StepStatus.COMPLETED
    assert workflow["step2"].status is StepStatus.PENDING, "stage 2 ran early"

    workflow.run_stage(2)
    assert workflow["step2"].status is StepStatus.COMPLETED


@pytest.mark.capability("exec.sync_in_async")
def test_sync_run_refuses_to_drive_an_orchestrator_inside_a_running_loop():
    """The error a notebook or Streamlit app hits, since both own the loop.

    It must be actionable — naming `aexecute` — rather than a bare
    "this event loop is already running".
    """
    import asyncio

    async def inside_a_loop():
        workflow = tools.build_flow().build()
        with pytest.raises(RuntimeError) as excinfo:
            workflow.run()
        return str(excinfo.value)

    message = asyncio.run(inside_a_loop())
    assert "running event loop" in message
    assert "aexecute" in message, f"the error must say what to do instead: {message}"


@pytest.mark.capability("flow.type_check")
def test_references_are_type_checked_before_the_workflow_runs():
    from simple_steps_core import check_reference_types

    registry = tools.build_registry()
    assert check_reference_types(tools.build_flow().build(), registry) == [], (
        "the example's own flow must type-check clean"
    )


@pytest.mark.capability("inspect.shape")
def test_a_step_can_be_inspected_before_it_has_run():
    """A UI renders a placeholder card from this, before any value exists."""
    workflow = tools.build_flow().build()
    preview = str(workflow.preview("step1"))
    assert "step1" in preview
    assert "pending" in preview, "an unrun step must announce that it is pending"


@pytest.mark.capability("persist.session")
def test_a_session_snapshot_round_trips_with_its_data():
    """Not just the recipe — the values a half-finished run already produced."""
    workflow = tools.build_flow().build()
    workflow.run_step("step1")
    workflow.run_step("step2")

    restored = Workflow.import_session(
        workflow.export_session(), CoreEngine(tools.build_registry())
    )
    expected = tools.run_plain()
    assert restored["step1"].output.value == expected["step1"]
    assert restored["step2"].output.value == expected["step2"]

    # And the restored session can carry on from where it stopped.
    restored.run()
    assert restored["step5"].output.value == expected["step5"]
