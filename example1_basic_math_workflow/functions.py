"""
Example 1 — the plain Python layer
==================================

Same contract as example 0: **no simple_steps_core import**, so this file is
the oracle. It adds the three things example 0 leaves out, because a real
application has all three:

* a **settings object** a step needs but which is not data,
* an **async** step,
* an item that **fails**, so the reference pipeline has to model what
  "collect the failure and keep going" actually means.

That last one is why the reference matters. It is easy to assert a workflow
"handled the error"; it is much harder to be wrong about it when a plain
Python loop next to it says exactly which seven values should survive.

    [10.0 .. 19.0]        load_readings   source
    [12.0 .. 19.0]        above_cutoff    filter   (cutoff=12)
    [24.0 .. 38.0]        scale_async     map      (13.0 raises)
    {...}                 summarize       collapse
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass
class MathSettings:
    """Stand-in for the client or connection a real step would need.

    Passed explicitly here; injected as a `Resource()` in the steps layer.
    That difference is exactly what the parity test pins down.
    """

    factor: float = 2.0
    label: str = "default"

    def describe(self) -> str:
        return f"{self.label}(x{self.factor})"


#: A reading equal to this blows up, on purpose.
POISON = 13.0

#: The seed for the type-changing reduce below. Items are floats and the
#: accumulator is a dict, so `collapse` must be given an explicit `initial` —
#: with none it seeds from the first *item* and the combiner gets a float.
EMPTY_SUMMARY = {"count": 0, "total": 0.0, "minimum": None, "maximum": None}


# ── the steps, as ordinary functions ─────────────────────────────────────
def load_readings(count: int = 10, start: float = 10.0) -> list[float]:
    """Produce a flat list of sensor readings."""
    return [start + index for index in range(count)]


def above_cutoff(value: float, cutoff: float = 12.0) -> bool:
    """Keep readings at or above *cutoff*."""
    return value >= cutoff


async def scale_async(value: float, settings: MathSettings) -> float:
    """Scale a reading by the settings' factor, with a real await in between.

    Raises on the poison value so the per-item error path is exercised.
    """
    await asyncio.sleep(0.01)
    if value == POISON:
        raise ValueError(f"reading {value} is poisoned")
    return value * settings.factor


def summarize(accumulator: dict | None, item: float) -> dict:
    """Fold readings into running statistics. A two-argument combiner."""
    accumulator = accumulator or dict(EMPTY_SUMMARY)
    minimum = accumulator["minimum"]
    maximum = accumulator["maximum"]
    return {
        "count": accumulator["count"] + 1,
        "total": accumulator["total"] + item,
        "minimum": item if minimum is None else min(minimum, item),
        "maximum": item if maximum is None else max(maximum, item),
    }


FUNCTIONS = {
    "load_readings": load_readings,
    "above_cutoff": above_cutoff,
    "scale_async": scale_async,
    "summarize": summarize,
}


# ── the same pipeline, by hand ───────────────────────────────────────────
async def _scale_all(values, settings, *, on_error: str):
    """The plain-Python equivalent of a `map` with per-item error handling.

    Returns ``(ok, failed)``. `collect` and `skip` differ only in whether the
    failures are reported, not in which values survive — pinning that down
    here is what makes the workflow assertion meaningful.
    """
    ok: list[float] = []
    failed: list[str] = []
    for value in values:
        try:
            ok.append(await scale_async(value, settings))
        except Exception as exc:
            if on_error == "fail_fast":
                raise
            if on_error == "collect":
                failed.append(str(exc))
    return ok, failed


def run_plain(
    *,
    count: int = 10,
    cutoff: float = 12.0,
    factor: float = 2.0,
    on_error: str = "collect",
) -> dict[str, object]:
    """Run the four phases in plain Python, keeping every intermediate."""
    settings = MathSettings(factor=factor, label="example1")

    step1 = load_readings(count=count)
    step2 = [v for v in step1 if above_cutoff(v, cutoff=cutoff)]
    step3, failed = asyncio.run(_scale_all(step2, settings, on_error=on_error))

    step4 = dict(EMPTY_SUMMARY)
    for item in step3:
        step4 = summarize(step4, item)

    return {"step1": step1, "step2": step2, "step3": step3,
            "step4": step4, "failed": failed}
