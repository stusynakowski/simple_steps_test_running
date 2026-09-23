"""
Example 0 — the plain Python layer
==================================

Ordinary functions and an ordinary pipeline. **Nothing in this file imports
simple_steps_core**, and that is the whole point: this is the *oracle*. When
the workflow version disagrees with this file, the library is wrong, because
this file is just Python and Python is not the thing under test.

Read it top to bottom and you can see exactly what the pipeline does:

    [[1,2,3],[4,5,6],[7,8,9]]   make_nested   the source collection
    [1,2,...,9]                 flatten       expand
    [1,3,5,7,9]                 is_odd        filter
    [2,4,6,8,10]                add_one       map
    30                          total         collapse
"""

from __future__ import annotations

NESTED = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]


# ── the steps, as ordinary functions ─────────────────────────────────────
def make_nested(rows: int = 3, per_row: int = 3) -> list[list[int]]:
    """Produce a nested list of consecutive integers."""
    return [
        [row * per_row + column + 1 for column in range(per_row)]
        for row in range(rows)
    ]


def is_odd(value: int) -> bool:
    """Keep odd numbers only."""
    return value % 2 == 1


def add_one(value: int) -> int:
    """Shift a number by one."""
    return value + 1


def total(accumulator: int, item: int) -> int:
    """Sum items. The two-argument shape a `collapse` combiner must have."""
    return (accumulator or 0) + item


#: Name -> function, so the registry layer never retypes this list and the
#: two layers cannot drift apart.
FUNCTIONS = {
    "make_nested": make_nested,
    "is_odd": is_odd,
    "add_one": add_one,
    "total": total,
}


# ── the same pipeline, by hand ───────────────────────────────────────────
def run_plain(rows: int = 3, per_row: int = 3) -> dict[str, object]:
    """Run the five phases in plain Python, keeping every intermediate.

    Returns one entry per phase under the same `step1..step5` keys the
    workflow uses, so a test can compare the two **phase by phase** rather
    than only at the end — a mismatch then points at the phase that broke.
    """
    step1 = make_nested(rows=rows, per_row=per_row)
    step2 = [item for row in step1 for item in row]        # expand
    step3 = [item for item in step2 if is_odd(item)]       # filter
    step4 = [add_one(item) for item in step3]              # map
    step5 = None                                           # collapse
    for item in step4:
        step5 = total(step5, item)
    return {"step1": step1, "step2": step2, "step3": step3,
            "step4": step4, "step5": step5}
