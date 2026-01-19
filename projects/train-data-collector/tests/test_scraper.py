"""Unit tests for the scraper module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.downloader import DownloadResult
from src.parser import ReportInfo
from src.scraper import CollectionConfig, CollectionStats, ReportScraper


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_reports_by_broker() -> dict[str, list[ReportInfo]]:
    """Sample reports grouped by broker for testing."""
    return {
        "한화투자증권": [
            ReportInfo("t1", "한화투자증권", "LG화학", "26.01.19", "url1.pdf"),
            ReportInfo("t2", "한화투자증권", "삼성전자", "26.01.19", "url2.pdf"),
            ReportInfo("t3", "한화투자증권", "SK하이닉스", "26.01.18", "url3.pdf"),
            ReportInfo("t4", "한화투자증권", "현대차", "26.01.18", "url4.pdf"),
            ReportInfo("t5", "한화투자증권", "NAVER", "26.01.17", "url5.pdf"),
            ReportInfo("t6", "한화투자증권", "카카오", "26.01.17", "url6.pdf"),
        ],
        "미래에셋증권": [
            ReportInfo("t7", "미래에셋증권", "LG화학", "26.01.19", "url7.pdf"),
            ReportInfo("t8", "미래에셋증권", "삼성전자", "26.01.19", "url8.pdf"),
            ReportInfo("t9", "미래에셋증권", "SK하이닉스", "26.01.18", "url9.pdf"),
            ReportInfo("t10", "미래에셋증권", "현대차", "26.01.18", "url10.pdf"),
            ReportInfo("t11", "미래에셋증권", "NAVER", "26.01.17", "url11.pdf"),
            ReportInfo("t12", "미래에셋증권", "카카오", "26.01.17", "url12.pdf"),
        ],
        "키움증권": [
            ReportInfo("t13", "키움증권", "LG화학", "26.01.19", "url13.pdf"),
            ReportInfo("t14", "키움증권", "삼성전자", "26.01.19", "url14.pdf"),
            ReportInfo("t15", "키움증권", "SK하이닉스", "26.01.18", "url15.pdf"),
            ReportInfo("t16", "키움증권", "현대차", "26.01.18", "url16.pdf"),
            ReportInfo("t17", "키움증권", "NAVER", "26.01.17", "url17.pdf"),
        ],
    }


@pytest.fixture
def temp_data_dir(tmp_path) -> Path:
    """Temporary data directory for testing."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def config() -> CollectionConfig:
    """Default collection configuration for testing."""
    return CollectionConfig(
        total_target=10,
        min_brokers=3,
        min_per_broker=2,
        delay_range=(0.0, 0.01),  # Fast for testing
    )


# =============================================================================
# Tests: CollectionStats
# =============================================================================


class TestCollectionStats:
    """Tests for CollectionStats dataclass."""

    def test_add_download_increments_total(self):
        """Given: stats, When: add_download, Then: total increments."""
        # Arrange
        stats = CollectionStats()

        # Act
        stats.add_download("한화투자증권")

        # Assert
        assert stats.total_downloaded == 1

    def test_add_download_tracks_broker(self):
        """Given: stats, When: add_download, Then: broker tracked."""
        # Arrange
        stats = CollectionStats()

        # Act
        stats.add_download("한화투자증권")
        stats.add_download("한화투자증권")
        stats.add_download("미래에셋증권")

        # Assert
        assert stats.by_broker["한화투자증권"] == 2
        assert stats.by_broker["미래에셋증권"] == 1

    def test_add_failure_increments_failed_count(self):
        """Given: stats, When: add_failure, Then: failed increments."""
        # Arrange
        stats = CollectionStats()

        # Act
        stats.add_failure()
        stats.add_failure()

        # Assert
        assert stats.failed == 2

    def test_add_skip_url_duplicate_increments_count(self):
        """Given: stats, When: add_skip_url_duplicate, Then: skipped increments."""
        # Arrange
        stats = CollectionStats()

        # Act
        stats.add_skip_url_duplicate()
        stats.add_skip_content_duplicate()

        # Assert
        assert stats.skipped_url_duplicate == 1
        assert stats.skipped_content_duplicate == 1
        assert stats.total_skipped == 2

    def test_get_broker_count_returns_zero_for_unknown(self):
        """Given: stats, When: get_broker_count unknown, Then: 0."""
        # Arrange
        stats = CollectionStats()

        # Act
        count = stats.get_broker_count("존재하지않는증권")

        # Assert
        assert count == 0

    def test_get_unique_broker_count(self):
        """Given: downloads from multiple brokers, When: get count, Then: correct."""
        # Arrange
        stats = CollectionStats()
        stats.add_download("한화투자증권")
        stats.add_download("미래에셋증권")
        stats.add_download("키움증권")
        stats.add_download("한화투자증권")  # Duplicate broker

        # Act
        count = stats.get_unique_broker_count()

        # Assert
        assert count == 3


# =============================================================================
# Tests: CollectionConfig
# =============================================================================


class TestCollectionConfig:
    """Tests for CollectionConfig dataclass."""

    def test_default_values(self):
        """Given: no args, When: create config, Then: defaults applied."""
        # Arrange & Act
        config = CollectionConfig()

        # Assert
        assert config.total_target == 500
        assert config.min_brokers == 8
        assert config.min_per_broker == 5
        assert config.delay_range == (5.0, 10.0)

    def test_custom_values(self):
        """Given: custom args, When: create config, Then: values set."""
        # Arrange & Act
        config = CollectionConfig(
            total_target=100,
            min_brokers=4,
            min_per_broker=3,
            delay_range=(1.0, 2.0),
        )

        # Assert
        assert config.total_target == 100
        assert config.min_brokers == 4
        assert config.min_per_broker == 3
        assert config.delay_range == (1.0, 2.0)


# =============================================================================
# Tests: ReportScraper._should_stop
# =============================================================================


class TestScraperShouldStop:
    """Tests for ReportScraper._should_stop method."""

    def test_returns_false_when_below_target(self, config, temp_data_dir):
        """Given: below target, When: _should_stop, Then: False."""
        # Arrange
        scraper = ReportScraper(config, temp_data_dir)
        stats = CollectionStats(total_downloaded=5)

        # Act
        result = scraper._should_stop(stats, target=10)

        # Assert
        assert result is False
        scraper.close()

    def test_returns_true_when_at_target(self, config, temp_data_dir):
        """Given: at target, When: _should_stop, Then: True."""
        # Arrange
        scraper = ReportScraper(config, temp_data_dir)
        stats = CollectionStats(total_downloaded=10)

        # Act
        result = scraper._should_stop(stats, target=10)

        # Assert
        assert result is True
        scraper.close()

    def test_returns_true_when_above_target(self, config, temp_data_dir):
        """Given: above target, When: _should_stop, Then: True."""
        # Arrange
        scraper = ReportScraper(config, temp_data_dir)
        stats = CollectionStats(total_downloaded=15)

        # Act
        result = scraper._should_stop(stats, target=10)

        # Assert
        assert result is True
        scraper.close()


# =============================================================================
# Tests: ReportScraper._download_report
# =============================================================================


class TestScraperDownloadReport:
    """Tests for ReportScraper._download_report method."""

    def test_skips_duplicate_urls(self, config, temp_data_dir):
        """Given: already downloaded URL, When: download, Then: skip."""
        # Arrange
        report = ReportInfo("t1", "한화투자증권", "LG화학", "26.01.19", "url1.pdf")

        with ReportScraper(config, temp_data_dir) as scraper:
            scraper._session_downloaded_urls.add("url1.pdf")
            stats = CollectionStats()

            # Act
            result = scraper._download_report(report, stats)

            # Assert
            assert result is False
            assert stats.skipped_url_duplicate == 1
            assert stats.total_downloaded == 0

    def test_tracks_downloaded_urls(self, config, temp_data_dir):
        """Given: new URL, When: download, Then: URL tracked."""
        # Arrange
        report = ReportInfo("t1", "한화투자증권", "LG화학", "26.01.19", "url1.pdf")

        with ReportScraper(config, temp_data_dir) as scraper:
            # Mock successful download
            scraper._downloader.download = MagicMock(
                return_value=DownloadResult(success=True, path=Path("/fake/path.pdf"))
            )
            stats = CollectionStats()

            # Act
            scraper._download_report(report, stats)

            # Assert
            assert "url1.pdf" in scraper._session_downloaded_urls

    def test_records_success_on_successful_download(self, config, temp_data_dir):
        """Given: successful download, When: download, Then: success recorded."""
        # Arrange
        report = ReportInfo("t1", "한화투자증권", "LG화학", "26.01.19", "url1.pdf")

        with ReportScraper(config, temp_data_dir) as scraper:
            scraper._downloader.download = MagicMock(
                return_value=DownloadResult(success=True, path=Path("/fake/path.pdf"))
            )
            stats = CollectionStats()

            # Act
            result = scraper._download_report(report, stats)

            # Assert
            assert result is True
            assert stats.total_downloaded == 1
            assert stats.by_broker["한화투자증권"] == 1

    def test_records_failure_on_failed_download(self, config, temp_data_dir):
        """Given: failed download, When: download, Then: failure recorded."""
        # Arrange
        report = ReportInfo("t1", "한화투자증권", "LG화학", "26.01.19", "url1.pdf")

        with ReportScraper(config, temp_data_dir) as scraper:
            scraper._downloader.download = MagicMock(
                return_value=DownloadResult(success=False, skipped_reason="download error")
            )
            stats = CollectionStats()

            # Act
            result = scraper._download_report(report, stats)

            # Assert
            assert result is True
            assert stats.failed == 1
            assert stats.total_downloaded == 0


# =============================================================================
# Tests: ReportScraper._download_with_distribution
# =============================================================================


class TestScraperDownloadWithDistribution:
    """Tests for ReportScraper._download_with_distribution method."""

    def test_ensures_minimum_per_broker(
        self, config, temp_data_dir, sample_reports_by_broker
    ):
        """Given: config with min_per_broker=2, When: distribute, Then: each broker gets 2+."""
        # Arrange
        config.total_target = 100  # High target to not stop early
        config.min_per_broker = 2

        with ReportScraper(config, temp_data_dir) as scraper:
            scraper._downloader.download = MagicMock(
                return_value=DownloadResult(success=True, path=Path("/fake.pdf"))
            )
            stats = CollectionStats()

            # Act
            scraper._download_with_distribution(sample_reports_by_broker, stats, target=100)

            # Assert - each broker should have at least min_per_broker
            for broker in sample_reports_by_broker.keys():
                assert stats.get_broker_count(broker) >= config.min_per_broker

    def test_stops_at_target(self, config, temp_data_dir, sample_reports_by_broker):
        """Given: target=6, When: distribute, Then: stops at 6."""
        # Arrange
        config.total_target = 6
        config.min_per_broker = 1

        with ReportScraper(config, temp_data_dir) as scraper:
            scraper._downloader.download = MagicMock(
                return_value=DownloadResult(success=True, path=Path("/fake.pdf"))
            )
            stats = CollectionStats()

            # Act
            scraper._download_with_distribution(sample_reports_by_broker, stats, target=6)

            # Assert
            assert stats.total_downloaded == 6

    def test_distributes_across_brokers(
        self, config, temp_data_dir, sample_reports_by_broker
    ):
        """Given: multiple brokers, When: distribute, Then: even distribution."""
        # Arrange
        config.total_target = 9
        config.min_per_broker = 2

        with ReportScraper(config, temp_data_dir) as scraper:
            scraper._downloader.download = MagicMock(
                return_value=DownloadResult(success=True, path=Path("/fake.pdf"))
            )
            stats = CollectionStats()

            # Act
            scraper._download_with_distribution(sample_reports_by_broker, stats, target=9)

            # Assert - should have downloads from all 3 brokers
            assert stats.get_unique_broker_count() == 3
            # Distribution should be relatively even (3 each for 9 total)
            for broker in sample_reports_by_broker.keys():
                assert stats.get_broker_count(broker) >= 2


# =============================================================================
# Tests: ReportScraper context manager
# =============================================================================


class TestScraperContextManager:
    """Tests for ReportScraper context manager interface."""

    def test_context_manager_initializes_downloader(self, config, temp_data_dir):
        """Given: context manager, When: enter, Then: downloader initialized."""
        # Arrange & Act
        with ReportScraper(config, temp_data_dir) as scraper:
            # Assert
            assert scraper._downloader is not None

    def test_run_without_context_manager_raises(self, config, temp_data_dir):
        """Given: no context manager, When: run, Then: raises RuntimeError."""
        # Arrange
        scraper = ReportScraper(config, temp_data_dir)

        # Act & Assert
        with pytest.raises(RuntimeError, match="context manager"):
            scraper.run()

        scraper.close()
