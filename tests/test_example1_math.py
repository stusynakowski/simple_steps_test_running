"""
Example 1 — resources, async, concurrency and partial failure.

This is the file that mirrors a real application: a step needs an injected
client, the work is async and fanned out, and some items fail. Everything
asserted here is something a production flow depends on.
"""

from __future__ import annotations

import asyncio

import pytest

from simple_steps_core import Resource, ResourceMissingError, StepStatus

from example1_basic_math_workflow import steps as tools


@pytest.fixture
def flow():
    return tools.build_flow()


@pytest.fixture
def ran(flow):
    workflow = flow.build()
    asyncio.run(workflow.arun())
    return workflow


# ── resources ────────────────────────────────────────────────────────────
@pytest.mark.capability("res.inject", "auth.async")
def test_an_async_step_receives_its_injected_resource(ran):
    """factor=2.0 from the resource, applied to every kept reading."""
    kept = ran["step2"].output.value
    scaled = ran["step3"].output.value.ok
    assert scaled == [v * 2.0 for v in kept if v != tools.POISON]


@pytest.mark.capability("res.hidden")
def test_a_resource_param_is_absent_from_the_input_schema():
    """An agent must never be asked to supply the settings object."""
    definition = tools.build_registry().get_definition("scale_async")
    assert "settings" not in definition.input_schema.get("properties", {})
    assert "settings" in definition.dependencies


@pytest.mark.capability("res.lazy")
def test_declaring_a_resource_does_not_build_it():
    built = []

    def factory():
        built.append(1)
        return tools.MathSettings()

    workflow = tools.build_flow().build()
    workflow.context.resources.register("probe", factory)
    assert built == [], "registering must not construct the resource"
    workflow.context.resources.get("probe")
    assert built == [1]


@pytest.mark.capability("res.check")
def test_a_resource_check_runs_a_hello_world(flow):
    workflow = flow.build()
    result = workflow.context.resources.check("settings")
    assert result.status == "ok", result.error


@pytest.mark.capability("res.declared_missing")
def test_a_workflow_reports_a_missing_resource_before_running():
    """The failure must arrive at validate time, not mid-batch."""
    from capability.flow import StandardFlow

    flow = (
        StandardFlow(tools.build_registry(), session_id="no-resource")
        .source("load_readings", count=3)
        .work("scale_async")
    )                                    # note: no .with_resource(...)
    workflow = flow.build()
    assert "settings" in workflow.missing_resources()


@pytest.mark.capability("res.missing")
def test_a_missing_resource_raises_a_named_error():
    workflow = tools.build_flow().build()
    with pytest.raises(ResourceMissingError) as excinfo:
        workflow.context.resources.get("nonexistent")
    assert "nonexistent" in str(excinfo.value)


@pytest.mark.capability("res.isolation")
def test_two_sessions_do_not_share_a_resource_instance():
    from simple_steps_core import ResourceContainer

    origin = ResourceContainer()
    origin.register("settings", lambda: tools.MathSettings())
    first, second = origin.clone(), origin.clone()
    assert first.get("settings") is not second.get("settings")


# ── orchestration under load ─────────────────────────────────────────────
@pytest.mark.capability("exec.arun_all", "orch.concurrency")
def test_the_async_flow_runs_to_completion(ran):
    assert [s.status for s in ran.steps] == [StepStatus.COMPLETED] * 4


@pytest.mark.capability("orch.on_error_collect", "exec.failure_isolated")
def test_one_poisoned_item_does_not_sink_the_batch(ran):
    result = ran["step3"].output.value
    assert len(result.failed) == 1
    assert "poisoned" in result.failed[0].error
    assert len(result.ok) == 7, "the other seven items must still succeed"
    assert ran["step3"].status is StepStatus.COMPLETED


@pytest.mark.capability("orch.on_error_fail_fast", "exec.failure_isolated")
def test_fail_fast_aborts_the_step_and_records_it():
    """The contract: the step is marked failed AND the error propagates.

    Worth pinning down, because it is not the obvious choice — the step's
    status is recorded before the exception leaves `arun()`, and the steps
    after it stay `pending` rather than being marked failed. A caller that
    wants a report rather than a raise must wrap the call.
    """
    workflow = tools.build_flow(on_error="fail_fast").build()

    with pytest.raises(ValueError, match="poisoned"):
        asyncio.run(workflow.arun())

    assert workflow["step3"].status is StepStatus.FAILED
    assert workflow["step4"].status is StepStatus.PENDING


@pytest.mark.capability("orch.on_error_skip")
def test_skip_drops_the_failure_silently():
    workflow = tools.build_flow(on_error="skip").build()
    asyncio.run(workflow.arun())
    result = workflow["step3"].output.value
    assert len(result.ok) == 7 and result.failed == []


@pytest.mark.capability("orch.shared_args")
def test_a_constant_argument_reaches_every_sub_call(ran):
    """`cutoff` is constant across items while the reading varies."""
    kept = ran["step2"].output.value
    assert kept and all(value >= 12.0 for value in kept)


@pytest.mark.capability("orch.collapse", "flow.field_ref")
def test_a_type_changing_reduce_needs_an_explicit_initial(ran):
    """Items are floats, the accumulator is a dict — so `initial` is required."""
    summary = ran["step4"].output.value
    ok = ran["step3"].output.value.ok
    assert summary["count"] == len(ok) == 7
    assert summary["total"] == sum(ok)
    assert summary["minimum"] == min(ok) and summary["maximum"] == max(ok)


# ── persistence ──────────────────────────────────────────────────────────
@pytest.mark.capability("persist.wf_json", "persist.resources_excluded")
def test_a_workflow_round_trips_through_json_without_its_resources(flow):
    from simple_steps_core import CoreEngine, Workflow

    workflow = flow.build()
    payload = workflow.to_json()
    assert "MathSettings" not in payload, "a snapshot must not carry a resource"
    restored = Workflow.from_json(
        payload, CoreEngine(tools.build_registry()), session_id="restored"
    )
    assert [s.step_id for s in restored.steps] == [s.step_id for s in workflow.steps]
