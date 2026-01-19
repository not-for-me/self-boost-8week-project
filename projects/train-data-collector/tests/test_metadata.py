"""Unit tests for the metadata module."""

import json
from pathlib import Path

import pytest

from src.metadata import (
    MetadataManager,
    MetadataStore,
    ReportMetadata,
    calculate_file_hash,
    calculate_file_hash_from_path,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_data_dir(tmp_path) -> Path:
    """Temporary data directory for testing."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def sample_metadata() -> ReportMetadata:
    """Sample report metadata for testing."""
    return ReportMetadata(
        pdf_url="https://example.com/test.pdf",
        broker="한화투자증권",
        stock_name="LG화학",
        title="상반기 실적 전망",
        date="2026-01-19",
        local_path="한화투자증권/2026-01-19_01.pdf",
        file_hash="md5:abc123def456",
        downloaded_at="2026-01-19T22:00:00",
    )


# =============================================================================
# Tests: ReportMetadata
# =============================================================================


class TestReportMetadata:
    """Tests for ReportMetadata dataclass."""

    def test_from_dict_creates_metadata(self):
        """Given: dict with all fields, When: from_dict, Then: creates metadata."""
        # Arrange
        data = {
            "pdf_url": "https://example.com/test.pdf",
            "broker": "한화투자증권",
            "stock_name": "LG화학",
            "title": "상반기 실적 전망",
            "date": "2026-01-19",
            "local_path": "한화투자증권/2026-01-19_01.pdf",
            "file_hash": "md5:abc123",
            "downloaded_at": "2026-01-19T22:00:00",
        }

        # Act
        metadata = ReportMetadata.from_dict(data)

        # Assert
        assert metadata.pdf_url == "https://example.com/test.pdf"
        assert metadata.broker == "한화투자증권"
        assert metadata.file_hash == "md5:abc123"

    def test_to_dict_converts_to_dict(self, sample_metadata):
        """Given: metadata, When: to_dict, Then: returns dict."""
        # Act
        result = sample_metadata.to_dict()

        # Assert
        assert result["pdf_url"] == sample_metadata.pdf_url
        assert result["broker"] == sample_metadata.broker
        assert result["file_hash"] == sample_metadata.file_hash


# =============================================================================
# Tests: MetadataStore
# =============================================================================


class TestMetadataStore:
    """Tests for MetadataStore class."""

    def test_add_report_stores_by_url_and_hash(self, sample_metadata):
        """Given: store, When: add_report, Then: accessible by URL and hash."""
        # Arrange
        store = MetadataStore()

        # Act
        store.add_report(sample_metadata)

        # Assert
        assert store.has_url(sample_metadata.pdf_url)
        assert store.has_hash(sample_metadata.file_hash)

    def test_has_url_returns_false_for_unknown(self):
        """Given: empty store, When: has_url, Then: returns False."""
        # Arrange
        store = MetadataStore()

        # Act & Assert
        assert store.has_url("https://unknown.com/test.pdf") is False

    def test_has_hash_returns_false_for_unknown(self):
        """Given: empty store, When: has_hash, Then: returns False."""
        # Arrange
        store = MetadataStore()

        # Act & Assert
        assert store.has_hash("md5:unknown") is False

    def test_get_by_url_returns_metadata(self, sample_metadata):
        """Given: store with metadata, When: get_by_url, Then: returns metadata."""
        # Arrange
        store = MetadataStore()
        store.add_report(sample_metadata)

        # Act
        result = store.get_by_url(sample_metadata.pdf_url)

        # Assert
        assert result == sample_metadata

    def test_get_by_hash_returns_metadata(self, sample_metadata):
        """Given: store with metadata, When: get_by_hash, Then: returns metadata."""
        # Arrange
        store = MetadataStore()
        store.add_report(sample_metadata)

        # Act
        result = store.get_by_hash(sample_metadata.file_hash)

        # Assert
        assert result == sample_metadata

    def test_to_dict_serializes_store(self, sample_metadata):
        """Given: store with data, When: to_dict, Then: serializable dict."""
        # Arrange
        store = MetadataStore()
        store.add_report(sample_metadata)

        # Act
        result = store.to_dict()

        # Assert
        assert sample_metadata.pdf_url in result["reports"]
        assert sample_metadata.file_hash in result["hashes"]

    def test_from_dict_deserializes_store(self, sample_metadata):
        """Given: dict data, When: from_dict, Then: restores store."""
        # Arrange
        store = MetadataStore()
        store.add_report(sample_metadata)
        data = store.to_dict()

        # Act
        restored = MetadataStore.from_dict(data)

        # Assert
        assert restored.has_url(sample_metadata.pdf_url)
        assert restored.has_hash(sample_metadata.file_hash)


# =============================================================================
# Tests: MetadataManager
# =============================================================================


class TestMetadataManager:
    """Tests for MetadataManager class."""

    def test_creates_new_store_if_no_file(self, temp_data_dir):
        """Given: no metadata file, When: init, Then: creates empty store."""
        # Arrange & Act
        manager = MetadataManager(temp_data_dir)

        # Assert
        assert manager.get_total_count() == 0

    def test_loads_existing_metadata(self, temp_data_dir, sample_metadata):
        """Given: existing metadata file, When: init, Then: loads data."""
        # Arrange - create metadata file
        metadata_file = temp_data_dir / "metadata.json"
        store = MetadataStore()
        store.add_report(sample_metadata)
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(store.to_dict(), f)

        # Act
        manager = MetadataManager(temp_data_dir)

        # Assert
        assert manager.get_total_count() == 1
        assert manager.is_duplicate_url(sample_metadata.pdf_url)

    def test_save_creates_metadata_file(self, temp_data_dir):
        """Given: manager with data, When: save, Then: creates file."""
        # Arrange
        manager = MetadataManager(temp_data_dir)
        manager.add_report(
            pdf_url="https://example.com/test.pdf",
            broker="테스트증권",
            stock_name="테스트",
            title="테스트 리포트",
            date="2026-01-19",
            local_path="테스트증권/2026-01-19_01.pdf",
            file_hash="md5:abc123",
        )

        # Act
        manager.save()

        # Assert
        metadata_file = temp_data_dir / "metadata.json"
        assert metadata_file.exists()
        with open(metadata_file, encoding="utf-8") as f:
            data = json.load(f)
        assert "https://example.com/test.pdf" in data["reports"]

    def test_is_duplicate_url_detects_duplicates(self, temp_data_dir):
        """Given: existing URL, When: is_duplicate_url, Then: returns True."""
        # Arrange
        manager = MetadataManager(temp_data_dir)
        manager.add_report(
            pdf_url="https://example.com/test.pdf",
            broker="테스트증권",
            stock_name="테스트",
            title="테스트 리포트",
            date="2026-01-19",
            local_path="테스트증권/2026-01-19_01.pdf",
            file_hash="md5:abc123",
        )

        # Act & Assert
        assert manager.is_duplicate_url("https://example.com/test.pdf") is True
        assert manager.is_duplicate_url("https://example.com/other.pdf") is False

    def test_is_duplicate_hash_detects_duplicates(self, temp_data_dir):
        """Given: existing hash, When: is_duplicate_hash, Then: returns True."""
        # Arrange
        manager = MetadataManager(temp_data_dir)
        manager.add_report(
            pdf_url="https://example.com/test.pdf",
            broker="테스트증권",
            stock_name="테스트",
            title="테스트 리포트",
            date="2026-01-19",
            local_path="테스트증권/2026-01-19_01.pdf",
            file_hash="md5:abc123",
        )

        # Act & Assert
        assert manager.is_duplicate_hash("md5:abc123") is True
        assert manager.is_duplicate_hash("md5:different") is False

    def test_get_existing_report_by_hash(self, temp_data_dir):
        """Given: existing hash, When: get_existing_report_by_hash, Then: returns metadata."""
        # Arrange
        manager = MetadataManager(temp_data_dir)
        manager.add_report(
            pdf_url="https://example.com/test.pdf",
            broker="테스트증권",
            stock_name="테스트",
            title="테스트 리포트",
            date="2026-01-19",
            local_path="테스트증권/2026-01-19_01.pdf",
            file_hash="md5:abc123",
        )

        # Act
        result = manager.get_existing_report_by_hash("md5:abc123")

        # Assert
        assert result is not None
        assert result.pdf_url == "https://example.com/test.pdf"

    def test_get_stats_returns_broker_counts(self, temp_data_dir):
        """Given: multiple reports, When: get_stats, Then: returns counts."""
        # Arrange
        manager = MetadataManager(temp_data_dir)
        for i in range(3):
            manager.add_report(
                pdf_url=f"https://example.com/test{i}.pdf",
                broker="한화투자증권",
                stock_name="테스트",
                title="테스트 리포트",
                date="2026-01-19",
                local_path=f"한화투자증권/2026-01-19_0{i+1}.pdf",
                file_hash=f"md5:hash{i}",
            )
        manager.add_report(
            pdf_url="https://example.com/other.pdf",
            broker="미래에셋증권",
            stock_name="테스트",
            title="테스트 리포트",
            date="2026-01-19",
            local_path="미래에셋증권/2026-01-19_01.pdf",
            file_hash="md5:other",
        )

        # Act
        stats = manager.get_stats()

        # Assert
        assert stats["한화투자증권"] == 3
        assert stats["미래에셋증권"] == 1


# =============================================================================
# Tests: calculate_file_hash
# =============================================================================


class TestCalculateFileHash:
    """Tests for hash calculation functions."""

    def test_calculate_file_hash_returns_md5_format(self):
        """Given: content, When: calculate_file_hash, Then: md5 format."""
        # Arrange
        content = b"test content"

        # Act
        result = calculate_file_hash(content)

        # Assert
        assert result.startswith("md5:")
        assert len(result) == 36  # "md5:" + 32 hex chars

    def test_calculate_file_hash_is_deterministic(self):
        """Given: same content, When: hash twice, Then: same result."""
        # Arrange
        content = b"test content"

        # Act
        hash1 = calculate_file_hash(content)
        hash2 = calculate_file_hash(content)

        # Assert
        assert hash1 == hash2

    def test_calculate_file_hash_differs_for_different_content(self):
        """Given: different content, When: hash, Then: different results."""
        # Arrange
        content1 = b"content 1"
        content2 = b"content 2"

        # Act
        hash1 = calculate_file_hash(content1)
        hash2 = calculate_file_hash(content2)

        # Assert
        assert hash1 != hash2

    def test_calculate_file_hash_from_path(self, tmp_path):
        """Given: file path, When: calculate_file_hash_from_path, Then: returns hash."""
        # Arrange
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"test content")

        # Act
        result = calculate_file_hash_from_path(test_file)

        # Assert
        assert result.startswith("md5:")
        assert result == calculate_file_hash(b"test content")
