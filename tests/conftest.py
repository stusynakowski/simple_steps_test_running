"""
Shared harness for the capability test bed.

Two jobs:

1. **Registry isolation.** Tools register into a module-global ``REGISTRY`` by
   default, so two examples that both define a `total` tool would collide and
   the second import would silently win. Every example here builds its own
   :class:`ToolRegistry`, and the ``flow`` fixture hands it out.

2. **Capability evidence.** ``@pytest.mark.capability("orch.map")`` records
   that this test exercises that capability. The plugin below watches the
   outcomes and prints a coverage summary at the end of the run, writing the
   full matrix to ``CAPABILITIES.md``. Nothing about coverage is hand-kept.

Mark a test ``@pytest.mark.awkward("reason")`` when the capability *works* but
only via a workaround — that is a real finding, and it should not hide behind
a green tick.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from capability import provenance as provenance_module  # noqa: E402
from capability import report as capability_report  # noqa: E402
from capability.catalogue import unknown_ids  # noqa: E402

MATRIX_PATH = ROOT / "CAPABILITIES.md"
JSON_PATH = ROOT / "capability_report.json"


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "capability(*ids): capability ids from capability/catalogue.py this test proves",
    )
    config.addinivalue_line(
        "markers",
        "awkward(reason): the capability works, but the ergonomics are bad",
    )
    config._capability_claims = defaultdict(list)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Record the *call*-phase outcome against each claimed capability.

    Taken from the finished report rather than the raw exception, because a
    marker-based ``xfail`` is not an exception the test raised — pytest turns
    the real failure into an xfail while building the report. Reading
    ``call.excinfo`` directly would score every declared gap as ``broken``.
    """
    outcome = yield
    report = outcome.get_result()
    if report.when != "call":
        return
    marker = item.get_closest_marker("capability")
    if marker is None:
        return

    if hasattr(report, "wasxfail") or report.outcome == "skipped":
        # An expected failure: the capability is declared and demonstrably
        # absent. An XPASS arrives as `failed` below, which is what we want —
        # a gap that closed should be loud, not silently green.
        verdict = "gap"
    elif report.passed:
        verdict = "awkward" if item.get_closest_marker("awkward") else "works"
    else:
        verdict = "broken"

    claims = item.config._capability_claims
    for capability_id in marker.args:
        claims[capability_id].append((item.name, verdict))


def is_full_run(config) -> bool:
    """True only when the whole suite ran.

    A narrowed run (`-k`, `-m`, or an explicit path) sees a fraction of the
    claims, so writing the matrix from it would wipe out every capability the
    selected tests happen not to touch. The committed matrix must only ever
    come from a complete run.
    """
    if config.option.keyword or config.option.markexpr:
        return False
    if getattr(config.option, "last_failed", False):
        return False
    # `args` is what was passed on the command line; with nothing passed it
    # falls back to `testpaths` from pyproject.
    given = [a for a in config.args if not a.startswith("-")]
    testpaths = config.getini("testpaths") or []
    defaults = {str(ROOT / p) for p in testpaths} | set(testpaths)
    return not given or set(given) <= defaults


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    claims = dict(getattr(config, "_capability_claims", {}))

    bad = unknown_ids(claims)
    if bad:
        terminalreporter.write_sep("=", "capability: unknown ids", red=True)
        terminalreporter.write_line(
            "These marker ids match nothing in capability/catalogue.py: "
            + ", ".join(bad)
        )
        terminalreporter.write_line(
            "Either fix the typo, or add the row to the catalogue."
        )

    obs = capability_report.observations(claims)
    terminalreporter.write_sep("=", "capability coverage")
    # Say what was tested, every run. A verdict is meaningless without it.
    terminalreporter.write_line(provenance_module.render_terminal(
        provenance_module.collect()))
    for line in capability_report.render_terminal(obs):
        terminalreporter.write_line(line)

    if is_full_run(config):
        MATRIX_PATH.write_text(capability_report.render_markdown(obs))
        capability_report.write_json(obs, JSON_PATH)
        terminalreporter.write_line(f"matrix -> {MATRIX_PATH.relative_to(ROOT)}")
    else:
        terminalreporter.write_line(
            "partial run — matrix not rewritten (it would read as mostly untested)"
        )
