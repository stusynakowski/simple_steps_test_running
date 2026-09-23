#!/usr/bin/env python
"""
Compare the last full test run against the committed capability floor.

    uv run python scripts/check-baseline.py            # compare
    uv run python scripts/check-baseline.py --update    # accept current state

Reads `capability_report.json`, which a full `pytest` run writes. Exits 1 on
any regression, so CI can gate on it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from capability import baseline as baseline_module  # noqa: E402

REPORT_PATH = ROOT / "capability_report.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update", action="store_true",
                        help="accept the current verdicts as the new floor")
    args = parser.parse_args()

    if not REPORT_PATH.exists():
        print(f"no {REPORT_PATH.name}; run a full `pytest` first", file=sys.stderr)
        return 2

    report = json.loads(REPORT_PATH.read_text())
    current = {i: entry["verdict"] for i, entry in report["capabilities"].items()}
    provenance = report.get("provenance", {})
    print(f"tested against: {provenance.get('version', '?')} @ "
          f"{(provenance.get('commit') or '?')[:12]}")

    if args.update:
        baseline_module.save(current)
        print(f"baseline updated: {len(current)} capabilities")
        return 0

    diff = baseline_module.compare(current, baseline_module.load())

    for capability_id, was, now in diff["improvements"]:
        print(f"  improved  {capability_id}: {was} -> {now}")
    for capability_id in diff["added"]:
        print(f"  new       {capability_id}: {current[capability_id]}")

    if diff["regressions"]:
        print("\nREGRESSIONS:", file=sys.stderr)
        for capability_id, was, now in diff["regressions"]:
            print(f"  {capability_id}: {was} -> {now}", file=sys.stderr)
        print("\nIf this is intended, rerun with --update and commit the diff.",
              file=sys.stderr)
        return 1

    print(f"\nno regressions ({len(current)} capabilities)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
