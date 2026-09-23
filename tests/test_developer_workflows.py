"""
Each component on its own, and the ways people actually build with them.

The parity battery proves whole pipelines. This file works one level down, in
two halves:

**Components** — each object exercised alone, so a failure names the object
rather than "the pipeline is wrong". These are the pieces someone assembles by
hand when the `Workflow` facade does not fit.

**Development styles** — the four ways this library gets used, all of which
have to work:

1. *script* — `App` → `Session` → `Workflow` → `run()`, the deployed path
2. *notebook / REPL* — build incrementally, run a step, look, change, re-run
3. *debugging one tool* — `tool.run(...)` with no workflow at all
4. *declarative* — build the workflow from JSON rather than in Python

Style 2 is the one that breaks quietly. A library that only works when you
build the whole graph before running anything is unusable in a notebook, and
nothing in an end-to-end test would catch that.
"""

from __future__ import annotations

import pytest

from simple_steps_core import (
    App,
    AppConfig,
    CoreEngine,
    DataStore,
    Operation,
    OrchestrationConfig,
    ReferenceResolver,
    ResourceContainer,
    SessionContext,
    SessionManager,
    StepStatus,
    ToolRegistry,
    Workflow,
    make_session_id,
    register_orchestrators,
)

from example0_identity_workflow import functions, steps


# ═════════════════════════════════════════════════════════════════════════
# Components, one at a time
# ═════════════════════════════════════════════════════════════════════════

@pytest.mark.capability("component.registry", "auth.plain")
def test_tool_registry_alone():
    """Register, look up, list, and refuse the unknown."""
    registry = ToolRegistry()
    tool = registry.register("add_one", functions.add_one)

    assert registry.has("add_one")
    assert registry.get_callable("add_one") is functions.add_one
    assert registry.get_operation("add_one") is tool
    assert [d.tool_id for d in registry.list_definitions()] == ["add_one"]

    with pytest.raises(KeyError):
        registry.get_definition("nope")


@pytest.mark.capability("component.registry")
def test_a_frozen_registry_refuses_further_registration():
    """Freezing after startup is what makes concurrent reads safe."""
    from simple_steps_core import RegistryFrozenError

    registry = ToolRegistry()
    registry.register("add_one", functions.add_one)
    registry.freeze()

    assert registry.frozen
    with pytest.raises(RegistryFrozenError):
        registry.register("is_odd", functions.is_odd)


@pytest.mark.capability("component.resources", "res.lazy")
def test_resource_container_alone():
    built = []
    container = ResourceContainer()
    container.register("thing", lambda: built.append(1) or "built",
                       check=lambda v: v.upper())

    assert container.has("thing")
    assert not container.is_loaded("thing")
    assert built == []

    assert container.get("thing") == "built"
    assert container.is_loaded("thing")
    assert container.get("thing") == "built" and built == [1], "not cached"

    assert container.check("thing").status == "ok"


@pytest.mark.capability("component.data_store")
def test_data_store_alone():
    """The value store under a session: put, bind to a step, read back."""
    store = DataStore()
    ref = store.put([1, 2, 3])

    assert store.has(ref)
    assert store.get(ref) == [1, 2, 3]

    store.bind_step("step1", ref)
    assert store.ref_for_step("step1") == ref
    assert store.value_for_step("step1") == [1, 2, 3]
    assert store.shape(ref).kind


@pytest.mark.capability("component.resolver", "flow.step_ref", "flow.literal")
def test_reference_resolver_alone():
    """Literals pass through; `stepN` becomes that step's value."""
    context = SessionContext(session_id="resolve")
    ref = context.put({"total": 42, "rows": [1, 2, 3]})
    context.bind_step("step1", ref)

    resolver = ReferenceResolver(context)
    assert resolver.resolve_value(7) == 7
    assert resolver.resolve_value("plain string") == "plain string"
    assert resolver.resolve_value("step1") == {"total": 42, "rows": [1, 2, 3]}
    assert resolver.resolve_value("step1.total") == 42

    resolved = resolver.resolve_arguments({"a": 1, "b": "step1.total"})
    assert resolved == {"a": 1, "b": 42}


@pytest.mark.capability("component.engine")
def test_core_engine_alone():
    """The engine executes one call against a context — no Workflow involved."""
    registry = steps.build_registry()
    engine = CoreEngine(registry)
    context = SessionContext(session_id="engine")

    ref, value = engine.execute(
        steps.functions.FUNCTIONS and
        __import__("simple_steps_core", fromlist=["ToolCall"]).ToolCall(
            operation_id="make_nested", arguments={"rows": 2, "per_row": 2}),
        context,
    )
    assert value == [[1, 2], [3, 4]]
    assert context.get(ref) == value


@pytest.mark.capability("component.session_manager", "res.isolation")
def test_session_manager_alone():
    """Hands out one context per id, and the ids are structured."""
    manager = SessionManager()
    session_id = make_session_id("alice", "wf", "run1")
    assert "alice" in session_id

    first = manager.get_or_create(session_id)
    assert manager.get_or_create(session_id) is first, "a second call rebuilt it"
    assert manager.get_or_create(make_session_id("bob", "wf", "run1")) is not first

    manager.discard(session_id)
    assert manager.get_or_create(session_id) is not first


# ═════════════════════════════════════════════════════════════════════════
# Development style 1 — the script / deployed path
# ═════════════════════════════════════════════════════════════════════════

@pytest.mark.capability("dev.app_facade", "res.isolation")
def test_the_app_facade_end_to_end():
    """App → Session → Workflow, the shape a deployed service uses."""
    registry = steps.build_registry()
    app = App(AppConfig(title="test", orchestrators=False), registry=registry)
    app.register_resource("settings", lambda: {"factor": 2})

    session = app.session("alice")
    assert app.session("alice") is session, "a second call rebuilt the session"
    assert app.session("bob") is not session

    workflow = session.workflow("main")
    workflow["step1"] = Operation(step_id="step1", name="make_nested",
                                  arguments={"rows": 2, "per_row": 2})
    workflow.run()
    assert workflow["step1"].output.value == [[1, 2], [3, 4]]

    # Each session got its own resource instance from the shared declaration.
    assert session.resources.get("settings") is not \
        app.session("bob").resources.get("settings")


@pytest.mark.capability("dev.app_facade", "inspect.tools")
def test_the_app_lists_its_tools_for_discovery():
    app = App(AppConfig(orchestrators=False), registry=steps.build_registry())
    ids = {d.tool_id for d in app.tools()}
    assert {"make_nested", "is_odd", "add_one", "total"} <= ids
    assert str(app.tools_info())


# ═════════════════════════════════════════════════════════════════════════
# Development style 2 — the notebook: build, run, look, change, re-run
# ═════════════════════════════════════════════════════════════════════════

@pytest.mark.capability("dev.incremental", "exec.step")
def test_a_workflow_can_be_built_and_run_one_step_at_a_time():
    """Nothing may require the graph to be complete before running anything."""
    workflow = Workflow(CoreEngine(steps.build_registry()), session_id="nb")

    workflow["step1"] = Operation(step_id="step1", name="make_nested",
                                  arguments={"rows": 3, "per_row": 3})
    workflow.run_step("step1")
    assert workflow["step1"].output.value == functions.NESTED

    # Only now is the next step written — using what step1 produced.
    workflow["step2"] = Operation(step_id="step2", name="identity",
                                  orchestration=OrchestrationConfig(
                                      mode="expand", over="step1"))
    workflow.run_step("step2")
    assert workflow["step2"].output.value == [1, 2, 3, 4, 5, 6, 7, 8, 9]


@pytest.mark.capability("dev.edit_rerun", "exec.rerun")
def test_a_step_can_be_replaced_and_re_run_without_rebuilding():
    """Change an argument, run again, get the new answer — the notebook loop."""
    workflow = Workflow(CoreEngine(steps.build_registry()), session_id="edit")
    workflow["step1"] = Operation(step_id="step1", name="make_nested",
                                  arguments={"rows": 1, "per_row": 1})
    workflow.run_step("step1")
    assert workflow["step1"].output.value == [[1]]

    # `Operation` is frozen, so editing means replacing the step.
    workflow["step1"] = Operation(step_id="step1", name="make_nested",
                                  arguments={"rows": 2, "per_row": 2})
    workflow.run_step("step1")
    assert workflow["step1"].output.value == [[1, 2], [3, 4]], "the old value stuck"


@pytest.mark.capability("dev.incremental")
def test_a_step_can_be_deleted_from_a_workflow():
    workflow = steps.build_flow().build()
    assert "step5" in workflow and len(workflow) == 5

    del workflow["step5"]
    assert "step5" not in workflow and len(workflow) == 4

    workflow.run()
    assert all(s.status is StepStatus.COMPLETED for s in workflow.steps)


@pytest.mark.capability("inspect.info", "inspect.repr", "inspect.preview")
def test_every_object_can_be_looked_at_in_a_repl():
    """`info()` and `repr()` are the notebook's entire user interface."""
    workflow = steps.build_flow().build()
    workflow.run()

    for obj in (workflow, workflow.context.resources, workflow["step1"]):
        assert repr(obj), f"{type(obj).__name__} has no repr"

    assert str(workflow.info())
    assert str(workflow.validate())
    assert str(workflow.preview("step2", limit=3))
    assert str(workflow.context.resources.info())


# ═════════════════════════════════════════════════════════════════════════
# Development style 3 — debugging one tool, no workflow
# ═════════════════════════════════════════════════════════════════════════

@pytest.mark.capability("auth.dual_mode", "dev.debug_one_tool")
def test_a_single_tool_runs_with_no_workflow_engine_or_session():
    """The first thing anyone does when a step misbehaves."""
    registry = steps.build_registry()
    add_one = registry.get_operation("add_one")

    assert add_one.run(value=41) == 42

    call = add_one(value=41)
    assert call.operation_id == "add_one"
    assert call.arguments == {"value": 41}


@pytest.mark.capability("dev.decorator")
def test_the_decorator_registers_and_returns_a_usable_tool():
    """`@register_tool` is how the docs tell people to start."""
    from simple_steps_core import REGISTRY, register_tool

    name = "_test_decorated_tool"
    try:
        @register_tool(name, "Double a number")
        def double(value: int) -> int:
            return value * 2

        assert REGISTRY.has(name)
        assert double.run(value=21) == 42
        assert REGISTRY.get_definition(name).description == "Double a number"
    finally:
        # The decorator writes to the process-global registry, so a test that
        # uses it has to clean up or it leaks into every later test.
        REGISTRY._definitions.pop(name, None)
        REGISTRY._callables.pop(name, None)
        REGISTRY._operations.pop(name, None)


# ═════════════════════════════════════════════════════════════════════════
# Development style 4 — declarative
# ═════════════════════════════════════════════════════════════════════════

@pytest.mark.capability("dev.declarative", "persist.wf_json")
def test_a_workflow_can_be_built_from_json_rather_than_python():
    """Someone else's tool, a saved definition, or a UI's output."""
    import json

    definition = [
        {"step_id": "step1", "name": "make_nested",
         "arguments": {"rows": 2, "per_row": 2}},
        {"step_id": "step2", "name": "identity",
         "arguments": {},
         "orchestration": {"mode": "expand", "over": "step1"}},
    ]
    workflow = Workflow(CoreEngine(steps.build_registry()), session_id="declarative")
    for spec in definition:
        workflow[spec["step_id"]] = Operation(**spec)

    assert "✓ ok" in str(workflow.validate())
    workflow.run()
    assert workflow["step2"].output.value == [1, 2, 3, 4]
    assert json.loads(workflow.to_json())
