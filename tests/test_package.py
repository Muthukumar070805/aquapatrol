"""Smoke tests for package layout and metadata."""

import importlib

import pytest

import oilspill

SUBPACKAGES = ["api", "detectors", "hindcast", "pipeline"]


def test_version() -> None:
    assert oilspill.__version__ == "0.1.0"


@pytest.mark.parametrize("name", SUBPACKAGES)
def test_subpackage_imports(name: str) -> None:
    module = importlib.import_module(f"oilspill.{name}")
    assert module.__doc__ is not None
