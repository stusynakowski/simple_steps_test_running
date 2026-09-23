"""Smoke checks that the installed simple-steps-core wheel is usable.

This is the seam for the real tests: the workflow installs the library from a
freshly built wheel, so anything importable here is importable for a consumer.
"""

import importlib

import pytest


def test_library_imports():
    mod = importlib.import_module("simple_steps_core")
    assert mod.__file__ is not None


def test_installed_from_wheel_not_source_tree():
    """A wheel install lands in site-packages, not in the checkout."""
    mod = importlib.import_module("simple_steps_core")
    assert "site-packages" in mod.__file__, (
        f"expected a wheel install, got {mod.__file__}"
    )


@pytest.mark.parametrize("name", ["simple_steps_core"])
def test_public_surface_is_non_empty(name):
    mod = importlib.import_module(name)
    public = [n for n in dir(mod) if not n.startswith("_")]
    assert public, f"{name} exposes nothing public"
