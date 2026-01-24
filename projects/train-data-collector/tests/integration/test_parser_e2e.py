"""End-to-end tests for the HTML parser with real Naver Finance pages.

These tests actually fetch data from the Naver Finance website.
Run with: uv run pytest tests/test_parser_e2e.py -v -s
"""

import pytest
import httpx

from train_data_collector.config import BASE_URL, DEFAULT_HEADERS
from train_data_collector.parser import (
    ReportInfo,
    get_total_pages,
    get_unique_brokers,
    parse_report_list,
)


# Mark all tests in this module as e2e (can be skipped with -m "not e2e")
pytestmark = pytest.mark.e2e


def fetch_page(page: int = 1) -> str:
    """Fetch a single page from Naver Finance."""
    url = f"{BASE_URL}?page={page}"
    response = httpx.get(url, headers=DEFAULT_HEADERS, timeout=30.0)
    response.raise_for_status()
    return response.text


class TestE2EParseReportList:
    """E2E tests for parsing real Naver Finance pages."""

    def test_parses_first_page_successfully(self):
        """Given: real page 1, When: parse, Then: reports extracted."""
        # Arrange
        html = fetch_page(1)

        # Act
        reports = parse_report_list(html)

        # Assert
        assert len(reports) > 0, "Should extract at least one report from page 1"
        for report in reports:
            assert report.stock_name, "Stock name should not be empty"
            assert report.title, "Title should not be empty"
            assert report.broker, "Broker should not be empty"
            assert report.date, "Date should not be empty"
            assert report.pdf_url.endswith(".pdf"), "PDF URL should end with .pdf"

    def test_parses_second_page_successfully(self):
        """Given: real page 2, When: parse, Then: reports extracted."""
        # Arrange
        html = fetch_page(2)

        # Act
        reports = parse_report_list(html)

        # Assert
        assert len(reports) > 0, "Should extract at least one report from page 2"

    def test_pdf_urls_are_valid_static_urls(self):
        """Given: real page, When: parse, Then: PDF URLs are valid static URLs."""
        # Arrange
        html = fetch_page(1)
        reports = parse_report_list(html)

        # Assert
        for report in reports:
            assert report.pdf_url.startswith("https://"), "PDF URL should be HTTPS"
            assert ".pdf" in report.pdf_url, "PDF URL should contain .pdf"
            # Static URLs should be from pstatic.net
            assert "pstatic.net" in report.pdf_url or "naver" in report.pdf_url

    def test_date_format_is_parseable(self):
        """Given: real page, When: parse, Then: dates can be formatted."""
        # Arrange
        html = fetch_page(1)
        reports = parse_report_list(html)

        # Assert
        for report in reports:
            formatted = report.get_formatted_date()
            # Should be in YYYY-MM-DD format
            parts = formatted.split("-")
            assert len(parts) == 3, f"Date should have 3 parts: {formatted}"
            year, month, day = parts
            assert len(year) == 4, f"Year should be 4 digits: {year}"
            assert year.startswith("20"), f"Year should start with 20: {year}"


class TestE2EGetTotalPages:
    """E2E tests for pagination extraction."""

    def test_extracts_total_pages_from_real_page(self):
        """Given: real page, When: get_total_pages, Then: reasonable number."""
        # Arrange
        html = fetch_page(1)

        # Act
        total = get_total_pages(html)

        # Assert
        # Naver Finance has thousands of pages of reports
        assert total > 100, f"Should have many pages, got {total}"


class TestE2EMinimumBrokerRequirement:
    """E2E tests to verify minimum broker requirement can be met."""

    def test_collects_minimum_8_brokers_from_first_pages(self):
        """Given: first 2 pages, When: collect brokers, Then: at least 8 unique brokers."""
        # Arrange
        all_reports: list[ReportInfo] = []

        # Act - Fetch first 2 pages
        for page in range(1, 3):
            html = fetch_page(page)
            reports = parse_report_list(html)
            all_reports.extend(reports)

        brokers = get_unique_brokers(all_reports)

        # Assert
        print(f"\n수집된 증권사 목록 ({len(brokers)}개):")
        for broker in sorted(brokers):
            count = sum(1 for r in all_reports if r.broker == broker)
            print(f"  - {broker}: {count}개")

        assert len(brokers) >= 8, (
            f"Should have at least 8 unique brokers, got {len(brokers)}: {brokers}"
        )

    def test_each_broker_has_pdf_urls(self):
        """Given: first 2 pages, When: collect, Then: each broker has valid PDF URLs."""
        # Arrange
        all_reports: list[ReportInfo] = []

        # Act
        for page in range(1, 3):
            html = fetch_page(page)
            reports = parse_report_list(html)
            all_reports.extend(reports)

        brokers = get_unique_brokers(all_reports)

        # Assert - each broker should have at least one valid PDF URL
        for broker in brokers:
            broker_reports = [r for r in all_reports if r.broker == broker]
            assert len(broker_reports) > 0
            for report in broker_reports:
                assert report.pdf_url.endswith(".pdf"), (
                    f"{broker}'s report should have valid PDF URL"
                )


class TestE2EReportDataQuality:
    """E2E tests for data quality verification."""

    def test_no_duplicate_pdf_urls_on_same_page(self):
        """Given: single page, When: parse, Then: no duplicate PDF URLs."""
        # Arrange
        html = fetch_page(1)

        # Act
        reports = parse_report_list(html)
        pdf_urls = [r.pdf_url for r in reports]

        # Assert
        assert len(pdf_urls) == len(set(pdf_urls)), "Should have no duplicate PDF URLs"

    def test_reports_have_consistent_structure(self):
        """Given: real page, When: parse, Then: all reports have same fields."""
        # Arrange
        html = fetch_page(1)

        # Act
        reports = parse_report_list(html)

        # Assert
        for report in reports:
            assert isinstance(report.title, str)
            assert isinstance(report.broker, str)
            assert isinstance(report.stock_name, str)
            assert isinstance(report.date, str)
            assert isinstance(report.pdf_url, str)
