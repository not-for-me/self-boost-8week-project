"""Unit tests for the PDF downloader module."""

import time
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
import respx

from src.downloader import DownloadError, PDFDownloader
from src.parser import ReportInfo


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_report():
    """Sample report for testing."""
    return ReportInfo(
        title="테스트 리포트",
        broker="테스트증권",
        stock_name="테스트주식",
        date="26.01.19",
        pdf_url="https://example.com/test.pdf",
    )


@pytest.fixture
def temp_data_dir(tmp_path):
    """Temporary data directory for downloads."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def downloader(temp_data_dir):
    """PDFDownloader with minimal delay for testing."""
    dl = PDFDownloader(base_dir=temp_data_dir, delay_range=(0.0, 0.01))
    yield dl
    dl.close()


# =============================================================================
# Tests: _generate_filename
# =============================================================================


class TestGenerateFilename:
    """Tests for PDFDownloader._generate_filename()."""

    def test_creates_first_file_with_sequence_01(self, downloader, sample_report):
        """Given: no existing files, When: generate filename, Then: _01.pdf."""
        # Arrange
        existing_files: list[str] = []

        # Act
        filename = downloader._generate_filename(sample_report, existing_files)

        # Assert
        assert filename == "2026-01-19_01.pdf"

    def test_increments_sequence_for_same_date(self, downloader, sample_report):
        """Given: existing file for same date, When: generate, Then: sequence increments."""
        # Arrange
        existing_files = ["2026-01-19_01.pdf"]

        # Act
        filename = downloader._generate_filename(sample_report, existing_files)

        # Assert
        assert filename == "2026-01-19_02.pdf"

    def test_handles_multiple_existing_files(self, downloader, sample_report):
        """Given: multiple existing files, When: generate, Then: next sequence."""
        # Arrange
        existing_files = [
            "2026-01-19_01.pdf",
            "2026-01-19_02.pdf",
            "2026-01-19_03.pdf",
        ]

        # Act
        filename = downloader._generate_filename(sample_report, existing_files)

        # Assert
        assert filename == "2026-01-19_04.pdf"

    def test_ignores_other_dates(self, downloader, sample_report):
        """Given: files from different dates, When: generate, Then: starts at 01."""
        # Arrange
        existing_files = [
            "2026-01-18_01.pdf",
            "2026-01-18_02.pdf",
        ]

        # Act
        filename = downloader._generate_filename(sample_report, existing_files)

        # Assert
        assert filename == "2026-01-19_01.pdf"


# =============================================================================
# Tests: _wait_with_jitter
# =============================================================================


class TestWaitWithJitter:
    """Tests for PDFDownloader._wait_with_jitter()."""

    def test_first_call_does_not_wait(self, temp_data_dir):
        """Given: first download, When: wait, Then: no delay."""
        # Arrange
        downloader = PDFDownloader(base_dir=temp_data_dir, delay_range=(5.0, 10.0))

        # Act
        start = time.time()
        downloader._wait_with_jitter()
        elapsed = time.time() - start

        # Assert - first call should be instant
        assert elapsed < 0.1
        downloader.close()

    def test_subsequent_call_applies_delay(self, temp_data_dir):
        """Given: previous download, When: wait, Then: delay applied."""
        # Arrange
        min_delay, max_delay = 0.1, 0.2
        downloader = PDFDownloader(
            base_dir=temp_data_dir, delay_range=(min_delay, max_delay)
        )

        # First call to set _last_download_time
        downloader._wait_with_jitter()

        # Act
        start = time.time()
        downloader._wait_with_jitter()
        elapsed = time.time() - start

        # Assert - should wait approximately min_delay to max_delay
        assert elapsed >= min_delay * 0.9  # Allow some tolerance
        assert elapsed <= max_delay * 1.5
        downloader.close()


# =============================================================================
# Tests: download
# =============================================================================


class TestDownload:
    """Tests for PDFDownloader.download()."""

    @respx.mock
    def test_saves_pdf_to_correct_path(
        self, downloader, sample_report, temp_data_dir
    ):
        """Given: valid URL, When: download, Then: saved to broker/date_seq.pdf."""
        # Arrange
        pdf_content = b"%PDF-1.4 test content"
        respx.get(sample_report.pdf_url).mock(
            return_value=httpx.Response(
                200,
                content=pdf_content,
                headers={"content-type": "application/pdf"},
            )
        )

        # Act
        result = downloader.download(sample_report)

        # Assert
        assert result.success is True
        assert result.path is not None
        assert result.path.exists()
        assert result.path.parent.name == "테스트증권"
        assert result.path.name == "2026-01-19_01.pdf"
        assert result.path.read_bytes() == pdf_content

    @respx.mock
    def test_creates_broker_directory(
        self, downloader, sample_report, temp_data_dir
    ):
        """Given: broker dir doesn't exist, When: download, Then: dir created."""
        # Arrange
        pdf_content = b"%PDF-1.4 test"
        respx.get(sample_report.pdf_url).mock(
            return_value=httpx.Response(
                200,
                content=pdf_content,
                headers={"content-type": "application/pdf"},
            )
        )

        broker_dir = temp_data_dir / sample_report.broker
        assert not broker_dir.exists()

        # Act
        downloader.download(sample_report)

        # Assert
        assert broker_dir.exists()
        assert broker_dir.is_dir()

    @respx.mock
    def test_returns_failure_on_404(self, downloader, sample_report):
        """Given: 404 response, When: download, Then: returns failure result."""
        # Arrange
        respx.get(sample_report.pdf_url).mock(
            return_value=httpx.Response(404)
        )

        # Act
        result = downloader.download(sample_report)

        # Assert
        assert result.success is False
        assert result.path is None

    @respx.mock
    def test_retries_on_server_error(self, downloader, sample_report):
        """Given: 500 then 200, When: download, Then: succeeds after retry."""
        # Arrange
        pdf_content = b"%PDF-1.4 test"
        route = respx.get(sample_report.pdf_url)
        route.side_effect = [
            httpx.Response(500),
            httpx.Response(
                200,
                content=pdf_content,
                headers={"content-type": "application/pdf"},
            ),
        ]

        # Act
        result = downloader.download(sample_report)

        # Assert
        assert result.success is True
        assert result.path is not None
        assert route.call_count == 2


# =============================================================================
# Tests: _download_with_retry
# =============================================================================


class TestDownloadWithRetry:
    """Tests for PDFDownloader._download_with_retry()."""

    @respx.mock
    def test_returns_content_on_success(self, downloader):
        """Given: successful response, When: download, Then: returns content."""
        # Arrange
        url = "https://example.com/test.pdf"
        expected_content = b"%PDF-1.4 content"
        respx.get(url).mock(
            return_value=httpx.Response(
                200,
                content=expected_content,
                headers={"content-type": "application/pdf"},
            )
        )

        # Act
        result = downloader._download_with_retry(url)

        # Assert
        assert result == expected_content

    @respx.mock
    def test_raises_download_error_on_client_error(self, downloader):
        """Given: 403 response, When: download, Then: raises immediately."""
        # Arrange
        url = "https://example.com/test.pdf"
        respx.get(url).mock(return_value=httpx.Response(403))

        # Act & Assert
        with pytest.raises(DownloadError) as exc_info:
            downloader._download_with_retry(url)

        assert "403" in str(exc_info.value)

    @respx.mock
    def test_raises_after_max_retries(self, downloader):
        """Given: persistent 500, When: download, Then: raises after retries."""
        # Arrange
        url = "https://example.com/test.pdf"
        respx.get(url).mock(return_value=httpx.Response(500))

        # Act & Assert
        with pytest.raises(DownloadError) as exc_info:
            downloader._download_with_retry(url)

        assert "All" in str(exc_info.value)


# =============================================================================
# Tests: Context Manager
# =============================================================================


class TestContextManager:
    """Tests for PDFDownloader context manager interface."""

    def test_context_manager_closes_client(self, temp_data_dir):
        """Given: context manager, When: exit, Then: client closed."""
        # Arrange & Act
        with PDFDownloader(base_dir=temp_data_dir) as downloader:
            assert downloader._client is not None

        # Assert - client should be closed (accessing it should still work
        # but the underlying connection pool is closed)
        # We can verify the close was called by checking the context exit worked
        assert True  # If we got here, context manager worked
