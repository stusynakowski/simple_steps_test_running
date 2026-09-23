"""
The regression gate.

`pytest` passing already catches a capability going `works -> broken`: that is
a failing test. It does **not** catch the quieter regressions, which are the
ones that actually happen:

* a test is deleted or renamed, and its capability silently becomes
  `untested` — coverage drops with the suite still fully green;
* a capability is demoted to an `xfail` to make a red build go green, turning
  `works -> gap` with no failure anywhere;
* a whole example stops being collected, taking a dozen claims with it.

So the verdicts are committed to `capability_baseline.json` and compared on
every full run. Only *improvements* are allowed to drift silently.

    ./scripts/check-baseline.py            # compare; non-zero on regression
    ./scripts/check-baseline.py --update   # accept the current state
"""

from __future__ import annotations

import json
from pathlib import Path

from .report import VERDICTS

#: Best-to-worst. A move down this list is a regression.
RANK = {verdict: index for index, verdict in enumerate(VERDICTS)}

BASELINE_PATH = Path(__file__).resolve().parents[1] / "capability_baseline.json"


def load(path: Path = BASELINE_PATH) -> dict[str, str]:
    """The committed verdicts. An absent baseline is an empty one."""
    if not path.exists():
        return {}
    return json.loads(path.read_text()).get("capabilities", {})


def save(verdicts: dict[str, str], path: Path = BASELINE_PATH) -> None:
    """Commit the current verdicts as the new floor."""
    path.write_text(json.dumps(
        {
            "_comment": "Committed capability floor. Regenerate with "
                        "scripts/check-baseline.py --update, and review the "
                        "diff: a verdict getting worse is the thing this "
                        "file exists to catch.",
            "capabilities": dict(sorted(verdicts.items())),
        },
        indent=2,
    ) + "\n")


def compare(current: dict[str, str], baseline: dict[str, str]) -> dict[str, list]:
    """Sort the differences into regressions, improvements and new rows."""
    regressions: list[tuple[str, str, str]] = []
    improvements: list[tuple[str, str, str]] = []

    for capability_id, was in baseline.items():
        now = current.get(capability_id)
        if now is None:
            # The row left the catalogue entirely.
            regressions.append((capability_id, was, "removed"))
            continue
        if RANK[now] > RANK[was]:
            regressions.append((capability_id, was, now))
        elif RANK[now] < RANK[was]:
            improvements.append((capability_id, was, now))

    added = sorted(set(current) - set(baseline))
    return {"regressions": regressions, "improvements": improvements,
            "added": added}
