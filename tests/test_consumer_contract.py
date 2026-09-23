"""
The contract this repo exists to enforce.

Everything else here tests *what the library does*. This file tests *how this
repo tests it* — the properties that make the results mean anything:

1. The library is installed the way a consumer installs it — a built artifact
   in site-packages, never an editable pointer at a source checkout.
2. This repo only touches the **public** surface. The moment a test reaches
   into `simple_steps_core.operations.registry`, it stops reporting what a
   consumer can do and starts reporting what an insider can do.
3. The install footprint is what it claims to be, so a surprise dependency
   shows up as a failing test rather than a 200MB venv nobody noticed.

If these fail, every other green test in the repo is suspect.
"""

from __future__ import annotations

import ast
import sys
from importlib import metadata
from pathlib import Path

import pytest

import simple_steps_core

from capability import provenance as provenance_module

ROOT = Path(__file__).resolve().parents[1]

#: Directories whose imports must stay on the public surface. `.venv` and the
#: library's own source are obviously excluded.
SCANNED = ("tests", "capability", "example0_identity_workflow",
           "example1_basic_math_workflow")

#: Hard (non-extra) requirements this repo knows about. A new one appearing
#: here is a deliberate decision by the library, so it should be a deliberate
#: update to this list.
EXPECTED_HARD_REQUIRES = {"notebook", "pydantic"}


def python_files() -> list[Path]:
    """Every Python file in this repo that could import the library.

    `is_file()` is not paranoia: this tree contains a *directory* named
    `sample_data.py`, which `rglob("*.py")` happily returns.
    """
    files = [ROOT / "compare.py"]
    for directory in SCANNED:
        files.extend(
            path for path in (ROOT / directory).rglob("*.py")
            if path.is_file() and "__pycache__" not in path.parts
        )
    return [f for f in files if f.is_file()]


# ── 1. installed like a consumer ─────────────────────────────────────────
def test_the_library_is_installed_not_imported_from_a_checkout():
    """A source-tree import would test code no consumer ever receives."""
    location = simple_steps_core.__file__ or ""
    assert "site-packages" in location, (
        f"expected a wheel install, got {location}. Run scripts/rebuild.sh."
    )


def test_the_install_is_not_editable():
    """An editable install silently follows the source tree as you edit it."""
    found = provenance_module.collect()
    assert not found.editable, (
        "an editable install leaked in; this repo must test a built artifact"
    )


def test_the_library_version_is_resolvable():
    """Provenance must never degrade to 'unknown' — a matrix needs a version."""
    found = provenance_module.collect()
    assert found.version != "not installed"
    assert found.install_path, "could not locate the installed package"


def test_the_repo_itself_is_not_an_installed_package():
    """This repo consumes the library; it is not distributable.

    `package = false` in pyproject. If it ever got installed, its modules
    could shadow the real ones.
    """
    with pytest.raises(metadata.PackageNotFoundError):
        metadata.version("simple-steps-test-running")


# ── 2. public surface only ───────────────────────────────────────────────
def _library_imports(path: Path) -> list[tuple[int, str]]:
    """Every `simple_steps_core...` module this file imports, with line numbers."""
    tree = ast.parse(path.read_text(), filename=str(path))
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.split(".")[0] == "simple_steps_core":
                found.append((node.lineno, node.module))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] == "simple_steps_core":
                    found.append((node.lineno, alias.name))
    return found


def test_this_repo_imports_only_the_public_surface():
    """Nothing may import a submodule of the library.

    `from simple_steps_core import X` is the consumer's contract. Reaching
    into `simple_steps_core.operations.registry` tests an internal that the
    library is free to rename, and quietly turns a consumer test bed into a
    white-box one.
    """
    violations = []
    for path in python_files():
        for lineno, module in _library_imports(path):
            if module != "simple_steps_core":
                violations.append(
                    f"{path.relative_to(ROOT)}:{lineno} imports {module}"
                )
    assert not violations, (
        "these reach past the public surface:\n  " + "\n  ".join(violations)
    )


def test_every_name_this_repo_uses_is_exported_in_dunder_all():
    """A name imported here must be one the library promises, not an accident.

    Catches the case where something is importable today only because a
    module happens to expose it — the first refactor takes it away.
    """
    exported = set(getattr(simple_steps_core, "__all__", []))
    assert exported, "the library exports no __all__ to check against"

    violations = []
    for path in python_files():
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            if node.module != "simple_steps_core":
                continue
            for alias in node.names:
                if alias.name not in exported:
                    violations.append(
                        f"{path.relative_to(ROOT)}:{node.lineno} imports "
                        f"{alias.name!r}, which is not in __all__"
                    )
    assert not violations, "\n  ".join(["not promised by the library:"] + violations)


# ── 3. the footprint is what it claims ───────────────────────────────────
def test_the_hard_dependency_set_has_not_changed():
    """A new mandatory dependency is a consumer-visible decision.

    NOTE: `notebook` is a *hard* requirement today, which pulls the whole
    Jupyter stack into every install of a library whose core is a registry
    and an execution engine. That is a finding, not a given — it is listed
    here so that it stays visible rather than becoming invisible.
    """
    found = provenance_module.collect()
    names = {
        requirement.split(">=")[0].split("[")[0].split("==")[0].strip()
        for requirement in found.hard_requires
    }
    assert names == EXPECTED_HARD_REQUIRES, (
        f"hard dependencies changed: {names} != {EXPECTED_HARD_REQUIRES}. "
        "If this is intended, update EXPECTED_HARD_REQUIRES."
    )


def test_importing_the_library_does_not_require_optional_extras():
    """The base install must be usable without the `agent`/`api`/`dashboard` extras."""
    for optional in ("langgraph", "fastapi", "streamlit"):
        assert optional not in sys.modules, (
            f"importing simple_steps_core pulled in {optional}, "
            "which is declared as an optional extra"
        )
