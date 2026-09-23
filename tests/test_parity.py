"""
The shared battery: plain Python vs the workflow, for every example.

Every test here is parametrized over `capability.parity.EXAMPLES`. Adding an
`ExampleSpec` gets you all of it — that is what "a template that gives full
coverage" means in practice: coverage that grows when you add an example,
without anyone copying a test file.

The assertions all have the same shape: **the workflow must agree with plain
Python**. Where they disagree, plain Python is right.
"""

from __future__ import annotations

import asyncio
import inspect

import pytest

from simple_steps_core import CoreEngine, StepStatus, Workflow

from capability.parity import EXAMPLES, IDS, unwrap

pytestmark = pytest.mark.parametrize("spec", EXAMPLES, ids=IDS)


# ── the functions arrived intact ─────────────────────────────────────────
@pytest.mark.capability("auth.plain", "inspect.tools")
def test_every_plain_function_is_a_registered_tool(spec):
    registered = {d.tool_id for d in spec.build_registry().list_definitions()}
    missing = set(spec.functions) - registered
    assert not missing, f"{spec.name}: plain functions never registered: {missing}"


@pytest.mark.capability("res.adapter_free")
def test_only_declared_adapters_differ_from_the_plain_function(spec):
    """A tool that is not the plain function is glue — it must be declared.

    This is the check that stops adapters accumulating quietly. When the
    library gains a way to inject a resource without redeclaring the
    signature, `adapted` empties out and this test says so.
    """
    registry = spec.build_registry()
    undeclared = [
        name for name, fn in spec.functions.items()
        if registry.get_callable(name) is not fn and name not in spec.adapted
    ]
    assert not undeclared, (
        f"{spec.name}: these tools are not the plain function but are not "
        f"listed in ExampleSpec.adapted: {undeclared}"
    )


@pytest.mark.capability("auth.plain", "auth.async", "auth.dual_mode")
def test_each_tool_alone_reproduces_its_plain_function(spec):
    """Per-function parity, before any workflow is involved.

    If this fails, the pipeline tests below are noise — the problem is in a
    single tool, not in how the steps were wired together.
    """
    registry = spec.build_registry()
    for name, samples in spec.samples.items():
        plain = spec.functions[name]
        tool = registry.get_operation(name)
        for kwargs in samples:
            expected = plain(**kwargs)
            if inspect.isawaitable(expected):
                expected = asyncio.run(expected)
            actual = tool.run(**kwargs)
            if inspect.isawaitable(actual):
                actual = asyncio.run(actual)
            assert actual == expected, f"{spec.name}.{name}({kwargs})"


# ── the pipeline agrees, phase by phase ──────────────────────────────────
@pytest.mark.capability("inspect.validate", "res.declared_missing")
def test_the_flow_validates_before_anything_runs(spec):
    assert "✓ ok" in str(spec.build_flow().build().validate())


@pytest.mark.capability("exec.run_all", "exec.arun_all")
def test_every_step_completes(spec):
    workflow = spec.run_workflow()
    assert [s.status for s in workflow.steps] == [StepStatus.COMPLETED] * len(
        workflow.steps
    )


@pytest.mark.capability("orch.single", "orch.expand", "orch.filter",
                        "orch.map", "orch.collapse", "flow.step_ref")
def test_the_workflow_matches_plain_python_at_every_phase(spec):
    """The central assertion of the whole test bed.

    Compared phase by phase rather than only at the end, so a mismatch names
    the phase that broke instead of just saying the answer is wrong.
    """
    expected = spec.run_plain()
    actual = spec.workflow_values(spec.run_workflow())

    for step_id in spec.phases:
        assert actual[step_id] == expected[step_id], (
            f"{spec.name}: {step_id} diverged from plain Python\n"
            f"  plain    : {expected[step_id]!r}\n"
            f"  workflow : {actual[step_id]!r}"
        )


@pytest.mark.capability("exec.run_all")
def test_the_final_value_matches_plain_python(spec):
    last = spec.phases[-1]
    workflow = spec.run_workflow()
    assert unwrap(workflow[last].output.value) == spec.run_plain()[last]


# ── the result is stable ─────────────────────────────────────────────────
@pytest.mark.capability("exec.rerun")
def test_running_the_same_flow_twice_gives_the_same_answer(spec):
    """Rules out hidden state in the registry, the container or the store."""
    first = spec.workflow_values(spec.run_workflow())
    second = spec.workflow_values(spec.run_workflow())
    assert first == second


@pytest.mark.capability("persist.wf_json", "persist.resources_excluded")
def test_a_json_round_trip_still_produces_the_same_answer(spec):
    """Saving the recipe and reloading it must not change the result."""
    original = spec.build_flow().build()
    restored = Workflow.from_json(
        original.to_json(), CoreEngine(spec.build_registry()), session_id="restored"
    )
    # The recipe travels; the resources do not, so re-register them.
    restored.context.resources = original.context.resources

    if spec.is_async:
        asyncio.run(restored.arun())
    else:
        restored.run()

    expected = {step_id: spec.run_plain()[step_id] for step_id in spec.phases}
    assert spec.workflow_values(restored) == expected
