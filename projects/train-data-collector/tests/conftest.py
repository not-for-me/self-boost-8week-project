"""Pytest configuration and fixtures.

This module provides:
- Auto-markers for unit/integration tests based on directory
- Shared fixtures used across test modules
"""

import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Automatically apply markers based on test directory.

    - tests/unit/ -> @pytest.mark.unit
    - tests/integration/ -> @pytest.mark.integration
    """
    for item in items:
        test_path = str(item.fspath)

        if "/unit/" in test_path:
            item.add_marker(pytest.mark.unit)
        elif "/integration/" in test_path:
            item.add_marker(pytest.mark.integration)
