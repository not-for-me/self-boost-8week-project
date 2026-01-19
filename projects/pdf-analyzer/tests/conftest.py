"""Pytest fixtures for PDF analyzer tests."""

from pathlib import Path

import pytest

from tests.fixtures.generate_pdf import generate_all_test_pdfs


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Return the fixtures directory path."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def test_pdfs(fixtures_dir: Path) -> dict[str, Path]:
    """Generate and return all test PDF files.

    This fixture generates PDFs once per test session.
    """
    return generate_all_test_pdfs(fixtures_dir)


@pytest.fixture(scope="session")
def basic_pdf(test_pdfs: dict[str, Path]) -> Path:
    """Return path to basic test PDF."""
    return test_pdfs["basic"]


@pytest.fixture(scope="session")
def multipage_pdf(test_pdfs: dict[str, Path]) -> Path:
    """Return path to multipage test PDF."""
    return test_pdfs["multipage"]


@pytest.fixture(scope="session")
def table_pdf(test_pdfs: dict[str, Path]) -> Path:
    """Return path to table test PDF."""
    return test_pdfs["table"]


@pytest.fixture(scope="session")
def empty_page_pdf(test_pdfs: dict[str, Path]) -> Path:
    """Return path to PDF with empty page."""
    return test_pdfs["empty_page"]
