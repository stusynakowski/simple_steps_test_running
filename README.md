# simple-steps-core test bed

A **consumer** test bed for [`simple-steps-core`](https://github.com/stusynakowski/simple-steps-core).
It installs the library the way a real application would — a built artifact in
`site-packages`, reached through its public API only — and then asks one
question: *can you actually build what you need with it, and where does it
fight back?*

This repo ships no library code of its own and is not installable. Its output
is [`CAPABILITIES.md`](CAPABILITIES.md): 57 declared capabilities, each marked
`works`, `awkward`, `gap`, `broken` or `untested`, regenerated on every full
test run and stamped with the exact library commit it was measured against.

---

## Install

You need [`uv`](https://docs.astral.sh/uv/). Everything else — including the
Python interpreter — is installed for you.

```bash
brew install uv          # or: curl -LsSf https://astral.sh/uv/install.sh | sh

git clone https://github.com/stusynakowski/simple_steps_test_running.git
cd simple_steps_test_running

uv python install        # the pinned interpreter (3.12, see .python-version)
uv sync --locked --all-groups
```

`--locked` fails outright if `uv.lock` is out of date with `pyproject.toml`, so
you can never quietly build a different set of versions than CI does. The
lockfile pins every transitive dependency **and the exact `simple-steps-core`
commit**.

Check what you got:

```bash
uv run python -m capability.provenance
```

```
library      simple-steps-core 0.1.0
commit       b0245a3022d3
source       https://github.com/stusynakowski/simple-steps-core.git
install      wheel / site-packages
python       3.12.13
platform     Darwin arm64
hard deps    notebook>=7.6.0, pydantic>=2.6
```

### Moving to a newer library

The lock points at the library's `main` branch. To pick up new commits:

```bash
uv lock --upgrade-package simple-steps-core
uv sync --all-groups
git diff uv.lock          # review, then commit to pin the new version
```

Or rebuild from scratch exactly the way CI does — this scrubs the venv, clears
the cache and re-downloads everything, so a dependency that has gone missing
fails here rather than silently resolving from a cache:

```bash
./scripts/rebuild.sh              # reproduce uv.lock exactly
./scripts/rebuild.sh --latest     # re-resolve to the newest commit
```

---

## Run the tests

```bash
uv run pytest
```

```
simple-steps-core 0.1.0 @ b0245a3022d3 · python 3.12.13 · wheel
OK works=41  !! awkward=0  -- gap=4  XX broken=0  ?? untested=12
  untested (important): auth.guardrails, auth.output_schema, exec.stage, ...
matrix -> CAPABILITIES.md
```

The summary is the point, not the dots. It says what the library could be
proven to do, and the `untested` line is the backlog in priority order.

A full run rewrites [`CAPABILITIES.md`](CAPABILITIES.md). A narrowed run
(`-k`, `-m`, or an explicit path) deliberately does **not** — it only sees a
fraction of the claims, so writing the matrix from it would wipe out every
capability the selected tests happen not to touch.

### The other two checks

```bash
uv run python scripts/check-baseline.py    # no capability regressed
uv run python compare.py                   # examples match plain Python
```

Both exit non-zero on failure. Together with `pytest` these are exactly what CI
runs, in this order:

```bash
uv run pytest && \
uv run python scripts/check-baseline.py && \
uv run python compare.py
```

---

## Compare an example yourself

Every example exists **twice**: as ordinary Python that imports nothing from
the library (`functions.py`, the oracle) and as the same functions registered
as tools (`steps.py`). `compare.py` runs both and puts them side by side.

```bash
uv run python compare.py                      # every example
uv run python compare.py example0_identity    # just one
uv run python compare.py --list               # what's available
uv run python compare.py -v                   # full values, stacked
uv run python compare.py --set cutoff=17      # override a parameter
```

```
example0_identity  5 phases · sync

  phase  tool          plain                              workflow
  ─────  ────────────  ─────────────────────────────────  ─────────────────────────────────
  step1  make_nested   [[1, 2, 3], [4, 5, 6], [7, 8, 9]]  [[1, 2, 3], [4, 5, 6], [7, 8, 9]]  ✓
  step2  identity      [1, 2, 3, 4, 5, 6, 7, 8, 9]        [1, 2, 3, 4, 5, 6, 7, 8, 9]        ✓
  step3  is_odd        [1, 3, 5, 7, 9]                    [1, 3, 5, 7, 9]                    ✓
  step4  add_one       [2, 4, 6, 8, 10]                   [2, 4, 6, 8, 10]                   ✓
  step5  total         30                                 30                                 ✓

  ✓ all 5 phases agree
```

When the two disagree, **the plain column is right** — it is not the thing
under test.

### In a REPL

```python
from example0_identity_workflow import steps

steps.run_plain()               # {'step1': ..., 'step5': 30}

wf = steps.build_flow().build()
wf.validate()                   # pre-flight
wf.run_step("step1")            # one step at a time
wf["step1"].output.value
wf.run()                        # the rest
```

No path setup needed from the repo root. Example 1 has an async step, so use
`asyncio.run(wf.arun())`.

---

## Layout

```
capability/
  catalogue.py      the 57 declared capabilities — the wish list
  parity.py         one ExampleSpec per example; the coverage template
  flow.py           the standard five-phase flow builder
  provenance.py     what was tested: version, commit, install mode
  report.py         renders CAPABILITIES.md
  baseline.py       the regression gate

example0_identity_workflow/
  functions.py      plain Python. The oracle. No library import.
  steps.py          the same functions registered as tools
example1_basic_math_workflow/
  functions.py      + resources, async, and an item that fails
  steps.py

tests/
  test_parity.py            the shared battery, run against every example
  test_consumer_contract.py public-API-only + install-shape enforcement
  test_core_capabilities.py the core capabilities the examples miss
  test_known_gaps.py        known gaps, as strict xfails
  test_example*.py          per-example detail

compare.py          run an example both ways, side by side
CAPABILITIES.md     generated — the coverage matrix
TESTING.md          how the method works, and what it has found
```

---

## Adding an example

1. Write `functions.py` — plain Python, **zero** `simple_steps_core` imports,
   plus a `run_plain()` that walks the pipeline by hand and returns every
   intermediate keyed `step1..stepN`.
2. Write `steps.py` — register those same function objects, assemble the flow.
3. Add an `ExampleSpec` to `capability/parity.py`.

The whole eight-check battery then runs against it automatically. That is what
"full coverage" means here: coverage grows when you add an example, with nobody
copying a test file.

See [TESTING.md](TESTING.md) for the method in full — the verdict vocabulary,
how to claim a capability, and the findings so far.

---

## Current findings

The full list is in [TESTING.md](TESTING.md). The two worst are the same shape
— a step that reports `COMPLETED` while producing garbage:

- **A typo'd step reference degrades to a literal string.** References are
  recognised by their `step` prefix, so `over="setp1"` stops being a reference
  and becomes a 5-character string that `map` iterates character by character.
  Validation reports "references check out".
- **`map` cannot feed any downstream orchestration.** `MapResult` is a pydantic
  model, so iterating it yields one `("outcomes", [...])` tuple. Use `.ok`.

That shape is why the tests here assert on **value, not status**.

## Requirements

- macOS or Linux
- `uv` (installs Python 3.12 itself)
- No API keys or network services — everything runs locally and offline after
  the initial dependency download.
