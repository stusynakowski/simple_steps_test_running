"""
The capability catalogue
========================

This is the **template**: one declared row per thing a consumer of
simple-steps-core needs to be able to do. It is deliberately a *wish list*
written from the consumer's seat, not a description of what the library
currently does — that is the whole point. A row exists because an application
would need it, and the assessment tells us whether the library delivers.

Two independent questions are tracked per row, and confusing them is the usual
way a coverage document goes stale:

* **Coverage** — does any example/test actually exercise this?
  Derived from ``@pytest.mark.capability("<id>")`` markers, never hand-written.
* **Verdict**  — when exercised, did it work, work awkwardly, or fail?
  Recorded by the test itself (a passing test asserting the good behaviour
  means ``works``; an ``xfail`` marks a known gap).

A row with no marker anywhere is an **untested claim** — the most dangerous
state, because nothing tells you it broke.

Add a capability here *first*, watch it show up as a gap, then close the gap.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Capability:
    """One declared thing a consumer must be able to do."""

    id: str
    area: str
    capability: str
    #: What breaks in a real application if this does not work.
    why: str
    #: ``core`` - an app cannot be built without it.
    #: ``important`` - an app is meaningfully worse without it.
    #: ``nice`` - convenience; a workaround exists.
    priority: str = "important"
    #: Free-text note: known asymmetries, sharp edges, design questions.
    note: str = ""


def _c(*args, **kwargs) -> Capability:
    return Capability(*args, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Authoring a step
#    Can I take an ordinary Python function and make it a step?
# ─────────────────────────────────────────────────────────────────────────────
AUTHORING = [
    _c("auth.plain", "authoring", "Register a plain sync function as a tool",
       "The baseline. If a normal function cannot become a step, nothing else matters.",
       priority="core"),
    _c("auth.async", "authoring", "Register an async function as a tool",
       "Any real step that calls an API or an LLM is async.",
       priority="core"),
    _c("auth.schema", "authoring", "Type annotations become an input JSON Schema",
       "The frontend and any agent discover arguments from this schema; "
       "a wrong schema means an un-callable tool.",
       priority="core"),
    _c("auth.defaults", "authoring", "Optional params with defaults are non-required",
       "Determines which fields a UI must prompt for.",
       priority="core"),
    _c("auth.dual_mode", "authoring", "A registered tool is callable deferred and immediate",
       "`tool(**kw)` builds a ToolCall for a workflow; `tool.run(**kw)` executes now. "
       "The immediate mode is how you debug a step in isolation.",
       priority="important"),
    _c("auth.docstring", "authoring", "The docstring's first paragraph becomes the description",
       "This is the text an agent reads to choose the tool.",
       priority="important"),
    _c("auth.guardrails", "authoring", "Per-argument guardrails reject bad values",
       "Stops a bad argument before it reaches an expensive call.",
       priority="important"),
    _c("auth.output_schema", "authoring", "The return annotation becomes an output schema",
       "Lets the next step's reference be type-checked before running.",
       priority="important"),
]

# ─────────────────────────────────────────────────────────────────────────────
# 2. Resources
#    Can a step depend on a connection/client without it entering the data flow?
# ─────────────────────────────────────────────────────────────────────────────
RESOURCES = [
    _c("res.inject", "resources", "A `Resource()` param is injected at run time",
       "Steps need DB handles and API clients that must not be serialized as data.",
       priority="core"),
    _c("res.hidden", "resources", "Resource params are absent from the input schema",
       "An agent must never be asked to supply a database connection.",
       priority="core"),
    _c("res.lazy", "resources", "A resource factory is built lazily on first use",
       "Declaring ten resources must not open ten connections at import.",
       priority="core"),
    _c("res.named", "resources", "`Resource(\"key\")` overrides the container key",
       "Lets a step call its param `fs` while binding to the `file_system` resource.",
       priority="important",
       note="Was silently ignored before the resource-binding work; verify on a fresh build."),
    _c("res.missing", "resources", "A missing resource raises a clear, named error",
       "The failure must say which resource and where to register it, not 'KeyError'.",
       priority="core"),
    _c("res.check", "resources", "`check`/`check_all` run a hello-world per resource",
       "Prove credentials work before starting a 3-hour batch.",
       priority="important"),
    _c("res.isolation", "resources", "Each session clones resources, no cross-talk",
       "Two users must not share one connection's state.",
       priority="core"),
    _c("res.declared_missing", "resources", "A workflow reports missing resources before running",
       "`wf.missing_resources()` must catch this at validate time, not step 40.",
       priority="core"),
    _c("res.bound_tools", "resources", "Tools bind exclusively to one resource",
       "A tool bound to `file_system` may use that resource and no other; "
       "the violation is caught at import, not at run time.",
       priority="important",
       note="New. Qualified ids are `<resource>-<tool>`; needs a wheel rebuild to test."),
    _c("res.adapter_free", "resources", "An existing function can be registered as a resource-bound tool",
       "Resource dependencies are discovered from a parameter *default* "
       "(`settings: X = Resource()`), so a pure function must be re-declared "
       "before it can be injected. An app wrapping third-party code it cannot "
       "edit writes one adapter per tool.",
       priority="important",
       note="Example 1 needs one adapter for this reason; see "
            "ExampleSpec.adapted, which is asserted to stay small."),
    _c("res.qualified_ids", "resources", "A bound tool's id is `<resource>-<tool>`",
       "Two resources can each offer a `list` tool without colliding.",
       priority="important",
       note="Breaking for bare orchestrator ids (`map`) unless aliased."),
]

# ─────────────────────────────────────────────────────────────────────────────
# 3. Orchestration
#    Can I fan work out over a collection and survive partial failure?
# ─────────────────────────────────────────────────────────────────────────────
ORCHESTRATION = [
    _c("orch.single", "orchestration", "Run a step once (mode='single')",
       "The default shape; everything else is a variation on it.",
       priority="core"),
    _c("orch.source", "orchestration", "A step with no upstream produces the initial collection",
       "Every flow starts somewhere — a query, a file listing, a literal.",
       priority="core",
       note="Today 'source' is a ToolDefinition *type*, not an orchestrator mode."),
    _c("orch.map", "orchestration", "Apply a tool to each item (mode='map')",
       "The workhorse for per-row processing.",
       priority="core",
       note="ASYMMETRY: map yields a MapResult (ok/failed), while expand and "
            "filter yield flat lists. Consumers must handle both."),
    _c("orch.expand", "orchestration", "Flat-map each item into many (mode='expand')",
       "One document becomes many pages; one batch becomes many readings.",
       priority="core"),
    _c("orch.filter", "orchestration", "Keep items where the tool is truthy (mode='filter')",
       "Drop the rows that do not qualify before paying for the expensive step.",
       priority="core"),
    _c("orch.collapse", "orchestration", "Reduce a collection to one value (mode='collapse')",
       "Aggregate the fan-out back into a single result.",
       priority="core",
       note="Called `collapse`, not `reduce`. Needs a 2-arg combiner, so it "
            "cannot default to `identity` the way map/filter/expand do."),
    _c("orch.identity", "orchestration", "`identity` reshapes with no bespoke tool",
       "`expand(over=x, op=identity)` flattens without writing a throwaway function.",
       priority="important"),
    _c("orch.concurrency", "orchestration", "Bounded concurrency across items",
       "Fan out 500 LLM calls 8 at a time without melting the rate limit.",
       priority="core"),
    _c("orch.retries", "orchestration", "Per-item retries",
       "A flaky API must not fail the whole batch on one timeout.",
       priority="core"),
    _c("orch.on_error_collect", "orchestration", "on_error='collect' isolates per-item failure",
       "499 good rows must survive 1 bad row, and the bad one must be reportable.",
       priority="core"),
    _c("orch.on_error_fail_fast", "orchestration", "on_error='fail_fast' aborts on first failure",
       "For a flow where a single bad item invalidates the run.",
       priority="important"),
    _c("orch.on_error_skip", "orchestration", "on_error='skip' silently drops failures",
       "Best-effort enrichment where a miss is acceptable.",
       priority="important"),
    _c("orch.empty", "orchestration", "An empty collection flows through without error",
       "A filter legitimately keeping nothing must not crash the collapse after it.",
       priority="core"),
    _c("orch.shared_args", "orchestration", "Constant kwargs are passed to every sub-call",
       "`map(over=rows, op='score', args={'model': 'gemma3'})` — the model is "
       "constant, the row varies.",
       priority="core"),
    _c("orch.nested", "orchestration", "An orchestrated step can drive another orchestration",
       "Documents -> pages -> paragraphs is two levels of fan-out.",
       priority="nice",
       note="Unverified. Likely the sharpest edge in the library."),
]

# ─────────────────────────────────────────────────────────────────────────────
# 4. Data flow between steps
# ─────────────────────────────────────────────────────────────────────────────
DATAFLOW = [
    _c("flow.literal", "dataflow", "Literal arguments pass through unchanged",
       "The simplest input.",
       priority="core"),
    _c("flow.step_ref", "dataflow", "`\"step1\"` resolves to that step's output",
       "This is how steps connect at all.",
       priority="core"),
    _c("flow.field_ref", "dataflow", "`\"step1.total\"` resolves a field of an output",
       "Take one number out of a dict result without an unpacking step.",
       priority="core"),
    _c("flow.index_ref", "dataflow", "`\"step1.rows[0]\"` resolves an index",
       "Reach into a list result positionally.",
       priority="important"),
    _c("flow.type_check", "dataflow", "References are type-checked before running",
       "Catch 'you piped a dict into an int param' at validate time.",
       priority="important"),
    _c("flow.unknown_ref", "dataflow", "A reference to a missing step fails validation",
       "A typo'd step id must not surface as a runtime KeyError.",
       priority="core"),
]

# ─────────────────────────────────────────────────────────────────────────────
# 5. Executing a workflow
# ─────────────────────────────────────────────────────────────────────────────
EXECUTION = [
    _c("exec.run_all", "execution", "Run a whole workflow synchronously",
       "The scripted, non-interactive path.",
       priority="core"),
    _c("exec.arun_all", "execution", "Run a whole workflow asynchronously",
       "Required as soon as any step is async.",
       priority="core"),
    _c("exec.step", "execution", "Run one step at a time",
       "An interactive dashboard advances a step per click.",
       priority="core"),
    _c("exec.stage", "execution", "Run a named/numbered stage",
       "Group steps that should advance together.",
       priority="important"),
    _c("exec.failure_isolated", "execution", "A failed step is recorded, not raised",
       "The workflow must report a failed step with its traceback and keep its shape.",
       priority="core"),
    _c("exec.rerun", "execution", "Re-running a step replaces its output",
       "Fix an argument and re-run without rebuilding the workflow.",
       priority="important"),
    _c("exec.sync_in_async", "execution", "Sync `run()` refuses to nest in a running loop",
       "The error must be actionable inside Jupyter/Streamlit, which own the loop.",
       priority="important",
       note="Known sharp edge: notebooks run an event loop already."),
]

# ─────────────────────────────────────────────────────────────────────────────
# 6. Inspecting — the part that decides whether the library is pleasant
# ─────────────────────────────────────────────────────────────────────────────
INSPECTION = [
    _c("inspect.validate", "inspection", "`wf.validate()` checks tools, refs and resources",
       "The single pre-flight that should catch everything cheap.",
       priority="core"),
    _c("inspect.info", "inspection", "Every object has an `info()` summary table",
       "How a developer orients in a notebook.",
       priority="important"),
    _c("inspect.repr", "inspection", "Every object has a dense one-line `__repr__`",
       "What you see when you type the variable name.",
       priority="important"),
    _c("inspect.preview", "inspection", "`wf.preview(step)` shows the first N rows",
       "Check a result without dumping 10k rows into the terminal.",
       priority="important"),
    _c("inspect.shape", "inspection", "A step announces its output shape before running",
       "Lets a UI render a placeholder card, and catches shape mistakes early.",
       priority="important"),
    _c("inspect.tools", "inspection", "The registered tool contracts are listable",
       "Tool discovery for a frontend or an agent.",
       priority="core"),
]

# ─────────────────────────────────────────────────────────────────────────────
# 7. Persistence
# ─────────────────────────────────────────────────────────────────────────────
PERSISTENCE = [
    _c("persist.wf_json", "persistence", "A workflow round-trips through JSON",
       "Save the *recipe* — no data, just the steps.",
       priority="core"),
    _c("persist.session", "persistence", "A session snapshot round-trips with its data",
       "Resume a half-finished run tomorrow.",
       priority="important"),
    _c("persist.codecs", "persistence", "Custom types survive via codecs",
       "A DataFrame or an image must not become an unserializable blob.",
       priority="important"),
    _c("persist.resources_excluded", "persistence", "Resources are never serialized",
       "A snapshot must not contain a live connection or a credential.",
       priority="core"),
]

CATALOGUE: list[Capability] = [
    *AUTHORING, *RESOURCES, *ORCHESTRATION,
    *DATAFLOW, *EXECUTION, *INSPECTION, *PERSISTENCE,
]

BY_ID: dict[str, Capability] = {c.id: c for c in CATALOGUE}

AREAS: list[str] = list(dict.fromkeys(c.area for c in CATALOGUE))

PRIORITIES = ("core", "important", "nice")


def unknown_ids(ids) -> list[str]:
    """Marker ids that name no declared capability (a typo, or a stale row)."""
    return sorted({i for i in ids if i not in BY_ID})
