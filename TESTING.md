# How this test bed works

The goal is not "do the tests pass". It is **does the library let a consumer
build what they need, and where does it fight back**. Those are different
questions, and only the second one tells you what to fix next.

## The loop

```
capability/catalogue.py        declare what a consumer must be able to do
        │
        ▼
example*/functions.py          plain Python. The oracle. No library import.
        │
        ▼
example*/steps.py              the same functions, registered as tools
        │
        ▼
capability/parity.py           one ExampleSpec per example
        │
        ▼
tests/test_parity.py           the shared battery, run against every example
        │
        ▼
CAPABILITIES.md                the matrix, regenerated every run
```

Declare the capability **first**. It shows up as `untested`, which is the
backlog. Nothing is ever ticked by hand.

## Every example exists twice

This is the core of the method — **differential testing**.

| file | role |
| --- | --- |
| `functions.py` | ordinary Python, **zero** `simple_steps_core` imports |
| `steps.py` | the same functions registered as tools, assembled into a flow |

`functions.py` also carries `run_plain()`, which walks the same pipeline by
hand and returns every intermediate under the same `step1..stepN` keys the
workflow uses.

Neither side is trusted alone. A test asserting the workflow produced `30` is
only as good as whoever typed `30`. A test asserting the workflow and a plain
Python loop **agree at every phase** is much harder to be wrong about, and it
localises a mismatch to the phase that broke:

```
example0: step3 diverged from plain Python
  plain    : [1, 3, 5, 7, 9]
  workflow : [1, 2, 3, 4, 5, 6, 7, 8, 9]
```

When the two disagree, plain Python is right — it is not the thing under test.

## The coverage template

`capability/parity.py` holds one `ExampleSpec` per example. Writing one gets
you the entire battery; that is what "a template that gives full coverage"
means here — coverage grows when you add an example, with nobody copying a
test file.

```python
ExampleSpec(
    name="example1_math",
    build_registry=example1.build_registry,
    build_flow=example1.build_flow,
    run_plain=example1.run_plain,        # the oracle
    functions=example1.FUNCTIONS,
    phases=("step1", "step2", "step3", "step4"),
    is_async=True,
    adapted={"scale_async": "needs a `Resource()` parameter default"},
    samples={"above_cutoff": [{"value": 12.0}, {"value": 11.9}]},
)
```

Eight checks then run against it automatically:

| check | asserts |
| --- | --- |
| registered | every plain function became a tool |
| adapters | every tool that is *not* the plain function is declared |
| per-function | each tool alone == its plain function, on `samples` |
| validates | the flow passes validation before running |
| completes | every step reaches COMPLETED |
| phases | each phase's value == the reference's |
| deterministic | running twice gives the same answer |
| round-trip | a JSON round-trip still gives the same answer |

The per-function check runs **before** any workflow exists. If it fails, the
pipeline tests are noise — the bug is in one tool, not in the wiring.

The `adapted` field is the interesting one. It records every place the library
forced glue to be written, and a test asserts nothing else drifted onto the
list. Today it has exactly one entry, in example 1.

## The standard flow

Every example has the same skeleton, so a difference between two examples is a
real difference in library behaviour rather than a difference in style:

```
source  ->  shape   ->  select  ->  work  ->  reduce
single      expand      filter      map       collapse
```

Skip any phase you don't need. `source -> work -> reduce` is a legitimate
three-phase flow.

```python
StandardFlow(build_registry(), session_id="example1")
    .with_resource("settings", lambda: MathSettings(factor=2.0))
    .source("load_readings", count=10)
    .select("above_cutoff", args={"cutoff": 12.0})
    .work("scale_async", concurrency=4, retries=2, on_error="collect")
    .reduce("summarize", initial=dict(EMPTY_SUMMARY))
    .build()            # -> a real simple_steps_core.Workflow
```

The builder is thin on purpose. It adds exactly three things, each of which
exists because the raw API has a sharp edge:

1. **A registry per example.** Tools register into a process-global `REGISTRY`
   by default, so two examples defining a `total` tool collide silently and
   the second import wins.
2. **Routing settings to the right config.** The library splits *shape*
   (`OrchestrationConfig`: mode, over, item_arg, initial) from *conduct*
   (`StepExecutionConfig`: concurrency, retries, timeout, on_item_error) and
   rejects a misplaced key with a pydantic error. The builder routes by name.
3. **The `.ok` workaround after a `map`.** See the gap below.

## The four verdicts

A capability is not binary. The plugin records the **worst** outcome across
every test that claims it:

| | verdict | means |
| --- | --- | --- |
| `OK` | works | a claiming test passed |
| `!!` | awkward | it works, but the test needed a workaround — mark with `@pytest.mark.awkward("why")` |
| `--` | gap | an `xfail`: declared, demonstrably absent |
| `XX` | broken | a claiming test failed outright |
| `??` | untested | nothing claims it — the most dangerous state |

`awkward` is the one that earns its keep. A workaround buried in a green test
is how a library's real ergonomics stay invisible.

## Writing a test

```python
@pytest.mark.capability("orch.filter")
def test_filter_keeps_only_the_items_that_qualify(ran):
    kept = ran["step3"].output.value
    assert kept == [1, 3, 5, 7, 9]
```

Two rules:

- **Assert on shape and value, not status.** `assert step.status is COMPLETED`
  sails straight past a step that completed while producing a tuple instead of
  a list — which is exactly the bug found below.
- **Record a gap as a strict `xfail`, not a comment.** When the library is
  fixed the xfail turns XPASS and the run tells you to promote the row. A gap
  in prose just rots.

## Running it yourself

`compare.py` runs an example both ways and puts the results side by side.
No pytest involved — this is the one to reach for when poking at behaviour.

```bash
uv run python compare.py                        # every example
uv run python compare.py example0_identity      # just one
uv run python compare.py --list                 # what's available
uv run python compare.py -v                     # full values, stacked
uv run python compare.py --set cutoff=17        # override a parameter
uv run python compare.py --plain                # only the plain pipeline
uv run python compare.py --workflow             # only the workflow
```

```
example0_identity  5 phases · sync

  phase  tool          plain                              workflow
  ─────  ────────────  ─────────────────────────────────  ─────────────────────────────────
  step1  make_nested   [[1, 2, 3], [4, 5, 6], [7, 8, 9]]  [[1, 2, 3], [4, 5, 6], [7, 8, 9]]  ✓
  step2  identity      [1, 2, 3, 4, 5, 6, 7, 8, 9]        [1, 2, 3, 4, 5, 6, 7, 8, 9]        ✓
  step3  is_odd        [1, 3, 5, 7, 9]                    [1, 3, 5, 7, 9]                    ✓
  step4  add_one       [3, 5, 7, 9, 11]                   [2, 4, 6, 8, 10]                   ✗
  step5  total         35                                 30                                 ✗

  ✗ diverged — the plain column is the correct one

  step4
    plain    : [3, 5, 7, 9, 11]
    workflow : [2, 4, 6, 8, 10]
```

It exits non-zero on any divergence, so it composes:

```bash
for c in 11 12 17 100; do uv run python compare.py example1_math --set cutoff=$c || break; done
```

`--set` reaches both sides, and each side silently ignores a key it doesn't
declare — so `--set retries=5` tunes the workflow without upsetting the plain
pipeline, which has no such knob.

### What divergence can and cannot catch

`steps.py` imports the *same function objects* from `functions.py`, so editing
a function body changes both columns together and they stay in agreement.
That is deliberate: it means a divergence is never a typo in a duplicated
function, and can only come from the **wiring** — orchestration mode, step
order, reference resolution, resource injection, error handling.

The flip side is that this method cannot tell you a function is wrong, only
that the library mis-ran it. Per-function correctness is the `samples` table
in `capability/parity.py`, checked by `test_each_tool_alone_reproduces_its_plain_function`.

### In a REPL

```python
from example0_identity_workflow import steps

steps.run_plain()                       # {'step1': ..., 'step5': 30}

wf = steps.build_flow().build()
wf.validate()                           # pre-flight
wf.run_step("step1")                    # one step at a time
wf["step1"].output.value
wf.run()                                # the rest
wf.info()
```

For example 1, use `asyncio.run(wf.arun())` — it has an async step.

Remember `unwrap()` from `capability.parity` when reading a `map` step: its
output is a `MapResult`, not a list, and `.ok` is the values.

## Running the tests

```bash
uv run pytest                     # everything, rewrites CAPABILITIES.md
uv run pytest -q tests/test_parity.py
uv run pytest -k example1
```

The end-of-run summary lists untested capabilities by priority — that is the
backlog, in order.

## What it found so far

**A typo'd step reference degrades to a literal string.** A reference is
recognised by its `step` prefix, so `over="setp1"` (a typo for `step1`) stops
being a reference and becomes a plain 5-character string. `map` then iterates
it **character by character**: five items, five failures, and the step still
reports `COMPLETED` with an empty result. Validation says
"references check out". Nothing anywhere says you typed a step id wrong.
This is the worst one found so far.

**`map` cannot feed any downstream orchestration.** `MapResult` is a pydantic
model, so iterating it yields a single `("outcomes", [...])` tuple. A
`collapse` over a bare map step produces a **wrong answer with no error**.
The workaround is to reference `step3.ok`; `capability/flow.py` applies it
automatically.

**A resource-injected step cannot be a pure function.** The dependency is
discovered from a parameter *default* (`settings: X = Resource()`), so an
existing function must be re-declared before it can be injected — there is no
"register this function and inject `settings` into it". Example 1 pays for
this with one adapter. An app wrapping code it cannot edit pays per tool.

**A type-changing reduce must declare `initial`.** With none, collapse seeds
the accumulator with the *first item*, so a combiner folding floats into a
dict receives a float.

**`run()`/`arun()` raise on a failed step** while also recording it. Steps
after the failure stay `pending`. A caller wanting a report rather than an
exception has to wrap the call.

Note the shape of the first two: both are steps that report `COMPLETED` while
producing garbage. That is why the tests here assert on **value, not status** —
`assert step.status is COMPLETED` passes cleanly on both.

## What makes this a consumer test bed

This repo tests the library the way a consumer receives it. Four properties
make the results mean anything, and each is enforced by a test in
`tests/test_consumer_contract.py` rather than by convention:

| property | why it matters |
| --- | --- |
| installed from a built artifact, in `site-packages` | a source-tree import tests code no consumer ever gets |
| never editable | an editable install silently follows your edits |
| **public surface only** | `from simple_steps_core import X` is the contract; reaching into `simple_steps_core.operations.registry` quietly turns this into a white-box suite |
| the hard dependency set is pinned in a test | a surprise mandatory dependency shows up as a red test, not a 200MB venv nobody noticed |

The third is the one that decays without enforcement. Today the repo imports
nothing but the top-level package, and two tests keep it that way — one bans
submodule imports outright, the other checks every imported name against the
library's `__all__`, so a name that works today only by accident is caught
before it becomes load-bearing.

## Provenance

Every report stamps what it was generated against — version, commit, install
mode, python, platform, hard dependencies:

```
simple-steps-core 0.1.0 @ b0245a3022d3 · python 3.12.13 · wheel
```

A capability matrix with no version on it is a rumour; the same table means
something different against a different build. `uv run python -m
capability.provenance` prints it on its own.

## The regression gate

`pytest` passing already catches `works -> broken` — that is a failing test.
It does not catch the quiet ones, which are the ones that actually happen:

- a test is deleted or renamed and its capability drops to `untested`;
- a red result is demoted to an `xfail`, turning `works -> gap`;
- an example stops being collected, taking a dozen claims with it.

All three leave the suite fully green. So the verdicts are committed to
`capability_baseline.json` and compared on every full run:

```bash
uv run python scripts/check-baseline.py            # exits 1 on regression
uv run python scripts/check-baseline.py --update   # accept the current state
```

Only improvements drift silently. A regression prints what moved and fails.

**The baseline is version-specific.** It records what a particular build could
do. Installing a *newer* library and seeing regressions is a real finding.
Installing an *older* one will report false regressions — the provenance line
at the top of the output tells you which situation you are in.

A partial run (`-k`, `-m`, or an explicit path) never rewrites
`CAPABILITIES.md`: it only sees a fraction of the claims, so writing the matrix
from it would wipe out every capability the selected tests happen not to touch.
Those runs say `partial run — matrix not rewritten` instead.

## The full local check, in CI order

```bash
uv run pytest                                      # suite + matrix
uv run python scripts/check-baseline.py            # no quiet regressions
uv run python compare.py                           # examples match plain Python
```

## Known staleness

The installed wheel is built from `simple-steps-core` `main`. It currently
predates two things already in that repo:

- the **resource-binding** work (`Resource("name")` overrides, `<resource>-<tool>`
  qualified ids, exclusive binding) — `res.named`, `res.bound_tools`,
  `res.qualified_ids` cannot be tested until a rebuild;
- the **`group`** orchestrator, which is not in the catalogue yet.

Run `scripts/rebuild.sh` to pick them up, then add the rows.
