"""
What exactly was tested
=======================

A capability matrix with no version on it is a rumour. This module captures
the identity of the library under test so every generated report can say which
build produced it — and so a matrix committed last month can be told apart
from one generated today.

Everything here reads *installed distribution metadata*, never the source
tree. That is deliberate: this repo tests the artifact a consumer receives,
so the provenance has to describe that artifact.
"""

from __future__ import annotations

import json
import platform
import sys
from dataclasses import asdict, dataclass
from importlib import metadata

DIST = "simple-steps-core"
PACKAGE = "simple_steps_core"


@dataclass(frozen=True)
class Provenance:
    """The identity of the library under test."""

    version: str
    commit: str
    source: str
    install_path: str
    editable: bool
    python: str
    platform: str
    hard_requires: tuple[str, ...]

    @property
    def short_commit(self) -> str:
        return self.commit[:12] if self.commit else "unknown"

    def as_rows(self) -> list[tuple[str, str]]:
        return [
            ("library", f"{DIST} {self.version}"),
            ("commit", self.short_commit),
            ("source", self.source),
            ("install", "EDITABLE (not a consumer install)" if self.editable
                        else "wheel / site-packages"),
            ("python", self.python),
            ("platform", self.platform),
            ("hard deps", ", ".join(self.hard_requires) or "none"),
        ]

    def to_dict(self) -> dict:
        return asdict(self)


def _direct_url() -> dict:
    """VCS/URL provenance pip records at install time, when there is any."""
    try:
        raw = metadata.distribution(DIST).read_text("direct_url.json")
    except Exception:
        return {}
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def collect() -> Provenance:
    """Describe the installed library. Never raises; reports what it can."""
    try:
        version = metadata.version(DIST)
    except metadata.PackageNotFoundError:
        version = "not installed"

    direct = _direct_url()
    vcs = direct.get("vcs_info") or {}
    commit = vcs.get("commit_id", "")
    source = direct.get("url", "") or "index (PyPI or equivalent)"
    editable = bool((direct.get("dir_info") or {}).get("editable"))

    try:
        module = __import__(PACKAGE)
        install_path = module.__file__ or ""
    except Exception:
        install_path = ""

    try:
        requires = metadata.requires(DIST) or []
    except metadata.PackageNotFoundError:
        requires = []
    hard = tuple(r for r in requires if "extra ==" not in r)

    return Provenance(
        version=version,
        commit=commit,
        source=source,
        install_path=install_path,
        editable=editable,
        python=platform.python_version(),
        platform=f"{platform.system()} {platform.machine()}",
        hard_requires=hard,
    )


def render_markdown(p: Provenance) -> str:
    """The provenance block stamped at the top of CAPABILITIES.md."""
    lines = ["| tested against | |", "| --- | --- |"]
    lines += [f"| {label} | {value} |" for label, value in p.as_rows()]
    return "\n".join(lines)


def render_terminal(p: Provenance) -> str:
    return (f"{DIST} {p.version} @ {p.short_commit} · "
            f"python {p.python} · "
            f"{'EDITABLE' if p.editable else 'wheel'}")


if __name__ == "__main__":
    found = collect()
    for label, value in found.as_rows():
        print(f"{label:12} {value}")
    sys.exit(0)
