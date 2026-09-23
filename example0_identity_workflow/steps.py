"""
Example 0 — the simple-steps layer
==================================

Takes the functions from :mod:`functions` **unchanged** and registers them as
tools. Nothing is rewritten, wrapped or adapted here: if a function had to
change shape to become a step, that itself would be a finding, and the
registration below is where it would show up.

The pairing with `functions.run_plain` is the point — see
`tests/test_parity.py`, which asserts the two produce identical values at
every phase.
"""

from __future__ import annotations

from capability.flow import StandardFlow, new_registry

from . import functions

#: Re-exported so tests and notebooks have one import for the example.
NESTED = functions.NESTED
FUNCTIONS = functions.FUNCTIONS
run_plain = functions.run_plain


def build_registry():
    """Register this example's plain functions into a registry of its own.

    Iterating `functions.FUNCTIONS` rather than listing names again means a
    function added there is registered here automatically — the two layers
    cannot drift.
    """
    registry = new_registry()
    for name, fn in functions.FUNCTIONS.items():
        registry.register(name, fn, type="source" if name == "make_nested" else "raw_output")
    return registry


def build_flow(*, rows: int = 3, per_row: int = 3) -> StandardFlow:
    """The five-phase flow — the same pipeline `run_plain` walks by hand."""
    return (
        StandardFlow(build_registry(), session_id="example0")
        .source("make_nested", rows=rows, per_row=per_row)
        .shape()                      # identity: flatten the nesting
        .select("is_odd")
        .work("add_one")
        .reduce("total")
    )
