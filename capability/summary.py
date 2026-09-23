"""
The human-readable overview.

`CAPABILITIES.md` is the full matrix — 57 rows, good for reading in a browser
and diffing in a pull request. This renders the same data as something you can
take in at the end of a terminal run: what was tested, how much of it works,
what is broken, and what to do next.

Everything is derived from `capability_report.json`, which a full pytest run
writes. Nothing here is hand-maintained, so the overview cannot drift from
what the tests actually found.

    uv run python -m capability.summary
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .catalogue import AREAS, BY_ID, PRIORITIES
from .report import MARK, VERDICTS

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "capability_report.json"

BOLD, DIM, RESET = "\033[1m", "\033[2m", "\033[0m"
GREEN, YELLOW, RED, BLUE = "\033[32m", "\033[33m", "\033[31m", "\033[34m"

VERDICT_COLOUR = {
    "works": GREEN,
    "awkward": YELLOW,
    "gap": YELLOW,
    "broken": RED,
    "untested": DIM,
}

WIDTH = 74


def _tty() -> bool:
    return sys.stdout.isatty()


def paint(text: str, colour: str) -> str:
    return f"{colour}{text}{RESET}" if _tty() else text


def rule(char: str = "─") -> str:
    return paint(char * WIDTH, DIM)


def heading(text: str) -> str:
    return f"\n{paint(text.upper(), BOLD)}\n{rule()}"


def bar(proven: int, total: int, width: int = 12) -> str:
    """A proportion indicator. Filled = proven, hollow = everything else."""
    if total == 0:
        return " " * width
    filled = round(width * proven / total)
    return paint("█" * filled, GREEN) + paint("░" * (width - filled), DIM)


def load(path: Path = REPORT_PATH) -> dict:
    if not path.exists():
        raise SystemExit(
            f"no {path.name} — run a full `uv run pytest` first, which writes it."
        )
    return json.loads(path.read_text())


def render(report: dict) -> str:
    capabilities = report["capabilities"]
    counts = report["counts"]
    provenance = report.get("provenance", {})
    lines: list[str] = []

    total = len(capabilities)
    proven = counts.get("works", 0)

    # ── what was tested ──────────────────────────────────────────────────
    lines.append(heading("tested against"))
    commit = (provenance.get("commit") or "unknown")[:12]
    install = "EDITABLE — not a consumer install" if provenance.get("editable") \
        else "wheel / site-packages"
    for label, value in [
        ("library", f"simple-steps-core {provenance.get('version', '?')}"),
        ("commit", commit),
        ("install", install),
        ("python", provenance.get("python", "?")),
        ("platform", provenance.get("platform", "?")),
    ]:
        lines.append(f"  {label:10} {value}")

    # ── coverage ─────────────────────────────────────────────────────────
    pct = proven / total * 100 if total else 0
    lines.append(heading(f"coverage — {proven}/{total} proven ({pct:.0f}%)"))

    for area in AREAS:
        rows = [i for i in capabilities if BY_ID[i].area == area]
        if not rows:
            continue
        area_proven = sum(1 for i in rows if capabilities[i]["verdict"] == "works")
        tally = {}
        for i in rows:
            verdict = capabilities[i]["verdict"]
            tally[verdict] = tally.get(verdict, 0) + 1
        detail = "  ".join(
            paint(f"{v} {tally[v]}", VERDICT_COLOUR[v])
            for v in VERDICTS if tally.get(v)
        )
        lines.append(
            f"  {area:14} {bar(area_proven, len(rows))} "
            f"{area_proven:>2}/{len(rows):<3}  {detail}"
        )

    lines.append("")
    lines.append("  " + "  ".join(
        paint(f"{MARK[v]} {v} {counts.get(v, 0)}", VERDICT_COLOUR[v])
        for v in VERDICTS
    ))

    # ── issues ───────────────────────────────────────────────────────────
    problems = [
        i for i in capabilities
        if capabilities[i]["verdict"] in ("broken", "gap", "awkward")
    ]
    if problems:
        lines.append(heading(f"issues found ({len(problems)})"))
        for capability_id in sorted(
            problems, key=lambda i: VERDICTS.index(capabilities[i]["verdict"]),
            reverse=True,
        ):
            entry = capabilities[capability_id]
            capability = BY_ID[capability_id]
            lines.append(
                f"\n  {paint(capability_id, BOLD)} "
                f"{paint('[' + entry['verdict'] + ']', VERDICT_COLOUR[entry['verdict']])} "
                f"{paint('· ' + capability.priority, DIM)}"
            )
            lines.append(f"    {capability.capability}")
            # The reason recorded by the test beats the catalogue note: it is
            # what the run actually observed, not what someone wrote down.
            explanation = entry.get("reason") or capability.note
            if explanation:
                for chunk in _wrap(explanation, WIDTH - 6):
                    lines.append(paint(f"    {chunk}", DIM))

    # ── backlog ──────────────────────────────────────────────────────────
    untested = [i for i in capabilities if capabilities[i]["verdict"] == "untested"]
    if untested:
        lines.append(heading(f"backlog — declared but never exercised ({len(untested)})"))
        for priority in PRIORITIES:
            rows = sorted(i for i in untested if BY_ID[i].priority == priority)
            if not rows:
                continue
            colour = RED if priority == "core" else YELLOW if priority == "important" else DIM
            lines.append(f"\n  {paint(priority, colour)}")
            for chunk in _wrap(", ".join(rows), WIDTH - 6):
                lines.append(f"    {chunk}")

    # ── what to do next ──────────────────────────────────────────────────
    lines.append(heading("next"))
    core_unproven = [
        i for i in capabilities
        if BY_ID[i].priority == "core" and capabilities[i]["verdict"] != "works"
    ]
    if counts.get("broken"):
        lines.append(f"  {paint('!', RED)} {counts['broken']} capability(ies) "
                     "failing outright — start there.")
    if core_unproven:
        lines.append(f"  {paint('!', YELLOW)} {len(core_unproven)} core "
                     "capability(ies) not proven: " + ", ".join(sorted(core_unproven)))
    else:
        lines.append(f"  {paint('✓', GREEN)} every core capability is proven.")
    if untested:
        lines.append(f"  {paint('·', BLUE)} {len(untested)} declared but unexercised — "
                     "write a test, or drop the row if it is not really wanted.")
    lines.append("")
    lines.append(paint("  full matrix: CAPABILITIES.md   ·   method: TESTING.md", DIM))
    lines.append("")

    return "\n".join(lines)


def _wrap(text: str, width: int) -> list[str]:
    """Wrap on word boundaries. No textwrap import for four lines of logic."""
    words, out, current = text.split(), [], ""
    for word in words:
        if current and len(current) + 1 + len(word) > width:
            out.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        out.append(current)
    return out


def main() -> int:
    print(render(load()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
