"""Pytest configuration for integration tests."""

import pytest


def pytest_collection_modifyitems(items):
    """Automatically add 'integration' marker to tests in this directory."""
    for item in items:
        if "/integration/" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
