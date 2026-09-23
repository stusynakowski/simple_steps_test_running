"""
Render the coverage matrix from observed test outcomes.

The input is *evidence* — what the test run actually did — not a hand-kept
list. That is the only way the matrix stays honest: a capability is covered
because a test claimed it with ``@pytest.mark.capability("<id>")`` and that
test ran, not because someone remembered to tick a box.

Verdict per capability, worst outcome wins:

    ``works``    every claiming test passed
    ``awkward``  passed, but the test is marked ``awkward`` (it works, the
                 ergonomics are bad — a workaround was needed)
    ``gap``      an xfail: the capability is declared and demonstrably absent
    ``broken``   a claiming test failed outright
    ``untested`` nothing claims it
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from . import provenance as provenance_module
from .catalogue import AREAS, BY_ID, CATALOGUE, PRIORITIES

#: Worst-wins ordering, best first.
VERDICTS = ("works", "awkward", "gap", "broken", "untested")

MARK = {
    "works": "OK",
    "awkward": "!!",
    "gap": "--",
    "broken": "XX",
    "untested": "??",
}


@dataclass
class Observation:
    """What the test run saw for one capability."""

    id: str
    tests: list[str] = field(default_factory=list)
    verdicts: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    @property
    def verdict(self) -> str:
        if not self.verdicts:
            return "untested"
        return max(self.verdicts, key=VERDICTS.index)

    @property
    def reason(self) -> str:
        """The explanation attached to the *worst* outcome, which is the
        one the verdict reflects."""
        worst = self.verdict
        for verdict, reason in zip(self.verdicts, self.reasons):
            if verdict == worst and reason:
                return " ".join(reason.split())
        return ""


def observations(claims: dict[str, list[tuple[str, str]]]) -> dict[str, Observation]:
    """Fold raw ``{capability_id: [(test_name, verdict), ...]}`` into a report."""
    out: dict[str, Observation] = {}
    for capability in CATALOGUE:
        obs = Observation(capability.id)
        for test_name, verdict, reason in claims.get(capability.id, []):
            obs.tests.append(test_name)
            obs.verdicts.append(verdict)
            obs.reasons.append(reason)
        out[capability.id] = obs
    return out


def summary_counts(obs: dict[str, Observation]) -> dict[str, int]:
    counts = dict.fromkeys(VERDICTS, 0)
    for o in obs.values():
        counts[o.verdict] += 1
    return counts


def render_markdown(obs: dict[str, Observation]) -> str:
    """The coverage matrix as a Markdown document."""
    found = provenance_module.collect()
    lines: list[str] = [
        "# Capability coverage",
        "",
        "Generated from the test run — do not edit by hand. Declare capabilities in",
        "`capability/catalogue.py`; claim them with `@pytest.mark.capability(\"<id>\")`.",
        "",
        # A matrix with no version on it is a rumour: the same table means
        # something different against a different build.
        provenance_module.render_markdown(found),
        "",
    ]

    counts = summary_counts(obs)
    total = len(obs)
    lines += [
        "| verdict | count | share |",
        "| --- | ---: | ---: |",
    ]
    for verdict in VERDICTS:
        n = counts[verdict]
        lines.append(f"| {verdict} | {n} | {n / total * 100:.0f}% |")
    lines += ["", f"**{total} declared capabilities.**", ""]

    # The list that actually drives work: core capabilities that are not proven.
    unproven = [
        BY_ID[i] for i, o in obs.items()
        if BY_ID[i].priority == "core" and o.verdict != "works"
    ]
    if unproven:
        lines += ["## Core capabilities not yet proven", ""]
        for capability in unproven:
            lines.append(
                f"- `{capability.id}` — {capability.capability} "
                f"(**{obs[capability.id].verdict}**)"
            )
        lines.append("")

    for area in AREAS:
        rows = [c for c in CATALOGUE if c.area == area]
        lines += [
            f"## {area}",
            "",
            "| | id | capability | priority | verdict | exercised by |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for capability in rows:
            o = obs[capability.id]
            tests = ", ".join(f"`{t}`" for t in sorted(set(o.tests))) or "—"
            lines.append(
                f"| {MARK[o.verdict]} | `{capability.id}` | {capability.capability} "
                f"| {capability.priority} | {o.verdict} | {tests} |"
            )
        lines.append("")
        notes = [c for c in rows if c.note]
        if notes:
            lines.append("<details><summary>Notes &amp; sharp edges</summary>")
            lines.append("")
            for c in notes:
                lines.append(f"- `{c.id}` — {c.note}")
            lines += ["", "</details>", ""]

    return "\n".join(lines)


def render_terminal(obs: dict[str, Observation]) -> list[str]:
    """A compact end-of-test-run summary."""
    counts = summary_counts(obs)
    head = "  ".join(f"{MARK[v]} {v}={counts[v]}" for v in VERDICTS)
    lines = [head]
    for priority in PRIORITIES:
        missing = [
            i for i, o in obs.items()
            if BY_ID[i].priority == priority and o.verdict == "untested"
        ]
        if missing:
            lines.append(f"  untested ({priority}): {', '.join(sorted(missing))}")
    return lines


def as_payload(obs: dict[str, Observation]) -> dict:
    """The machine-readable report: provenance plus one entry per capability."""
    return {
        "provenance": provenance_module.collect().to_dict(),
        "counts": summary_counts(obs),
        "capabilities": {
            i: {
                "verdict": o.verdict,
                "reason": o.reason,
                "tests": sorted(set(o.tests)),
                "priority": BY_ID[i].priority,
                "area": BY_ID[i].area,
            }
            for i, o in obs.items()
        },
    }


def write_json(obs: dict[str, Observation], path) -> None:
    path.write_text(json.dumps(as_payload(obs), indent=2, sort_keys=True))
