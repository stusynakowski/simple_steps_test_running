"""
Example 1 — the simple-steps layer
==================================

Three of the four functions register unchanged. The fourth does not, and that
is worth stating plainly rather than hiding:

**A resource-injected step cannot be a pure function.** The library discovers
a resource dependency from a parameter *default* — ``settings: MathSettings =
Resource()`` — so a function that takes its settings as a normal argument has
to be re-declared with that default before it can be registered. There is no
way to say "register this existing function, and inject `settings` into it".

The cost is the two-line adapter below. It delegates immediately, so the real
logic still lives in :mod:`functions` and the parity test still means
something. But an application wrapping a third-party function it cannot edit
would have to write one of these per tool. Tracked as capability
`res.adapter_free`.
"""

from __future__ import annotations

from simple_steps_core import Resource

from capability.flow import StandardFlow, new_registry

from . import functions

MathSettings = functions.MathSettings
POISON = functions.POISON
EMPTY_SUMMARY = functions.EMPTY_SUMMARY
FUNCTIONS = functions.FUNCTIONS
run_plain = functions.run_plain


# ── the one adapter ──────────────────────────────────────────────────────
async def scale_async(value: float, settings: MathSettings = Resource()) -> float:
    """Scale a reading by the resource's factor.

    Identical to :func:`functions.scale_async`; the only difference is the
    ``Resource()`` default that makes `settings` injected rather than passed.
    """
    return await functions.scale_async(value, settings)


#: What actually gets registered: the plain functions, with the one adapter
#: swapped in. Keeping this as a dict means the parity test can assert that
#: every plain function is accounted for, adapted or not.
REGISTERED = {**functions.FUNCTIONS, "scale_async": scale_async}

#: The tools that are *not* the untouched plain function. A test asserts this
#: stays small — every entry is a place the library made us write glue.
ADAPTED = {"scale_async"}


def build_registry():
    """Register this example's tools into a registry of its own."""
    registry = new_registry()
    for name, fn in REGISTERED.items():
        registry.register(
            name, fn, type="source" if name == "load_readings" else "raw_output"
        )
    return registry


def build_flow(
    *,
    count: int = 10,
    cutoff: float = 12.0,
    factor: float = 2.0,
    concurrency: int = 4,
    retries: int = 2,
    on_error: str = "collect",
) -> StandardFlow:
    """The four-phase flow. `shape` is skipped: the source is already flat."""
    return (
        StandardFlow(build_registry(), session_id="example1")
        .with_resource(
            "settings",
            lambda: MathSettings(factor=factor, label="example1"),
            check=lambda s: s.describe(),
        )
        .source("load_readings", count=count)
        .select("above_cutoff", args={"cutoff": cutoff})
        .work("scale_async", concurrency=concurrency, retries=retries,
              on_error=on_error)
        .reduce("summarize", initial=dict(EMPTY_SUMMARY))
    )
