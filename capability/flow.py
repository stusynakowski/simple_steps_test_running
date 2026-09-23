"""
The standard flow
=================

Every example in this test bed is written in the **same five phases**, in the
same order. That is the point: when two examples have the same skeleton, a
difference between them is a real difference in the library's behaviour rather
than a difference in how somebody happened to write the script.

    source  ->  shape  ->  select  ->  work  ->  reduce
      |          |           |          |          |
      |          |           |          |          `- collapse: many -> one
      |          |           |          `- map:     one -> one, per item
      |          |           `- filter:  drop items that do not qualify
      |          `- expand:   one -> many (flatten)
      `- single:  the initial collection

Not every flow needs all five. A phase you skip is simply not added, and the
next phase reads from whatever came last — so `source -> work -> reduce` is a
legitimate three-phase flow.

This builder is deliberately **thin**: it returns a plain
:class:`~simple_steps_core.Workflow` built from the public API, with no
behaviour of its own. Anything you can do here you can do by hand; an example
that needs a shape this does not cover should build the Workflow directly
rather than growing this file.
"""

from __future__ import annotations

from simple_steps_core import (
    CoreEngine,
    Operation,
    OrchestrationConfig,
    StepExecutionConfig,
    ToolRegistry,
    Workflow,
    register_orchestrators,
)

#: The library splits a step's settings in two, and enforces the split (see
#: docs/config-isolation.md). **Shape** — how data fans out and comes back —
#: lives on OrchestrationConfig; **conduct** — how the work is carried out —
#: lives on StepExecutionConfig. Passing `concurrency` to the former is a
#: pydantic error, so the builder routes each keyword to its owner.
_SHAPE_KEYS = set(OrchestrationConfig.model_fields) - {"mode", "over"}
_CONDUCT_KEYS = set(StepExecutionConfig.model_fields)

#: `on_error` reads better at a call site than the model's `on_item_error`.
_ALIASES = {"on_error": "on_item_error"}

#: Phase name -> the orchestration mode it uses.
PHASES = {
    "source": "single",
    "shape": "expand",
    "select": "filter",
    "work": "map",
    "reduce": "collapse",
}


def new_registry(*, orchestrators: bool = True) -> ToolRegistry:
    """A registry of this example's own — never the process-global one.

    Sharing ``REGISTRY`` across examples makes tool-name collisions silent:
    the last import wins and the earlier example quietly tests the wrong tool.
    """
    registry = ToolRegistry()
    if orchestrators:
        register_orchestrators(registry)
    return registry


class StandardFlow:
    """Assemble the five standard phases into a real Workflow."""

    def __init__(self, registry: ToolRegistry, *, session_id: str = "flow") -> None:
        self.registry = registry
        self.session_id = session_id
        self._steps: list[Operation] = []
        self._resources: dict[str, object] = {}

    # ── resources ────────────────────────────────────────────────────────
    def with_resource(self, name: str, factory, *, check=None) -> "StandardFlow":
        """Declare a resource the steps will need. Built lazily at run time."""
        self._resources[name] = (factory, check)
        return self

    # ── phases ───────────────────────────────────────────────────────────
    def _add(self, phase: str, tool: str, *, mode: str | None, args: dict,
             orchestration: dict) -> "StandardFlow":
        step_id = f"step{len(self._steps) + 1}"
        mode = mode or PHASES[phase]
        extra: dict = {}
        if mode != "single":
            previous = self._steps[-1] if self._steps else None
            if previous is None:
                raise ValueError(
                    f"phase {phase!r} orchestrates over the previous step, but "
                    "this flow has none yet — start with .source(...)"
                )
            over = orchestration.pop("over", None) or self._over(previous)
            shape, conduct = self._split_settings(orchestration)
            extra["orchestration"] = OrchestrationConfig(mode=mode, over=over, **shape)
            if conduct:
                extra["execution"] = StepExecutionConfig(**conduct)
        # `orchestration` must be absent, not None: the model rejects an
        # explicit null but happily defaults a missing key to single-shot.
        self._steps.append(
            Operation(step_id=step_id, name=tool, arguments=dict(args), **extra)
        )
        return self

    @staticmethod
    def _split_settings(settings: dict) -> tuple[dict, dict]:
        """Route each keyword to the config that owns it, shape vs conduct."""
        shape: dict = {}
        conduct: dict = {}
        for key, value in settings.items():
            key = _ALIASES.get(key, key)
            if key in _SHAPE_KEYS:
                shape[key] = value
            elif key in _CONDUCT_KEYS:
                conduct[key] = value
            else:
                raise TypeError(
                    f"unknown step setting {key!r}. "
                    f"shape: {sorted(_SHAPE_KEYS)}; conduct: {sorted(_CONDUCT_KEYS)}"
                )
        return shape, conduct

    @staticmethod
    def _over(previous: Operation) -> str:
        """The reference that yields *previous*'s items as a flat collection.

        A `map` step's output is a ``MapResult``, not a list. It is a pydantic
        model, so iterating it yields one ``("outcomes", [...])`` tuple — which
        means a downstream orchestration over a bare map step silently produces
        a **wrong answer instead of an error**. ``.ok`` is the flat list of
        successful values, and is what a caller almost always means.

        Encoded here once so no example has to remember it. See capability
        `orch.map` in the catalogue.
        """
        previous_mode = (
            previous.orchestration.mode if previous.orchestration else "single"
        )
        if previous_mode == "map":
            return f"{previous.step_id}.ok"
        return previous.step_id

    def source(self, tool: str, **args) -> "StandardFlow":
        """Phase 1 — produce the initial collection. Runs once."""
        return self._add("source", tool, mode="single", args=args, orchestration={})

    def shape(self, tool: str = "identity", **orchestration) -> "StandardFlow":
        """Phase 2 — flat-map: each item becomes many. Defaults to `identity`."""
        return self._add("shape", tool, mode="expand", args={},
                         orchestration=orchestration)

    def select(self, tool: str, *, args: dict | None = None,
               **orchestration) -> "StandardFlow":
        """Phase 3 — keep the items for which *tool* returns truthy."""
        return self._add("select", tool, mode="filter", args=args or {},
                         orchestration=orchestration)

    def work(self, tool: str, *, args: dict | None = None,
             **orchestration) -> "StandardFlow":
        """Phase 4 — the real per-item work. Where concurrency/retries belong."""
        return self._add("work", tool, mode="map", args=args or {},
                         orchestration=orchestration)

    def reduce(self, tool: str, *, args: dict | None = None,
               **orchestration) -> "StandardFlow":
        """Phase 5 — collapse the collection to a single value."""
        return self._add("reduce", tool, mode="collapse", args=args or {},
                         orchestration=orchestration)

    def then(self, tool: str, **args) -> "StandardFlow":
        """An extra single-shot step, for flows that do not fit the five phases."""
        return self._add("source", tool, mode="single", args=args, orchestration={})

    # ── build ────────────────────────────────────────────────────────────
    def build(self) -> Workflow:
        """Materialize a real Workflow with its resources registered."""
        workflow = Workflow(CoreEngine(self.registry), session_id=self.session_id)
        for name, (factory, check) in self._resources.items():
            workflow.context.resources.register(name, factory, check=check)
        for step in self._steps:
            workflow[step.step_id] = step
        return workflow

    def __repr__(self) -> str:
        chain = " -> ".join(s.name for s in self._steps) or "(empty)"
        return f"<StandardFlow {self.session_id!r} {chain}>"
