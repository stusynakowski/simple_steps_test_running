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

from simple_steps_core import StepStatus

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
