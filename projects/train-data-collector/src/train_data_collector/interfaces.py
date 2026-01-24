"""Abstract interfaces for dependency injection.

This module defines Protocol interfaces to enable dependency inversion.
Concrete implementations should implement these protocols.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from train_data_collector.downloader import DownloadResult
    from train_data_collector.metadata import ReportMetadata
    from train_data_collector.parser import ReportInfo


class IMetadataManager(Protocol):
    """Interface for metadata management.

    Provides methods for tracking downloaded reports and preventing duplicates.
    """

    def is_duplicate_url(self, pdf_url: str) -> bool:
        """Check if URL is already downloaded."""
        ...

    def is_duplicate_hash(self, file_hash: str) -> bool:
        """Check if file hash already exists."""
        ...

    def add_report(
        self,
        pdf_url: str,
        broker: str,
        stock_name: str,
        title: str,
        date: str,
        local_path: str,
        file_hash: str,
    ) -> ReportMetadata:
        """Add a new report to metadata."""
        ...

    def get_existing_report_by_hash(self, file_hash: str) -> ReportMetadata | None:
        """Get existing report with same content hash."""
        ...

    def get_total_count(self) -> int:
        """Get total number of downloaded reports."""
        ...

    def get_broker_count(self) -> int:
        """Get number of unique brokers in metadata."""
        ...

    def get_brokers(self) -> set[str]:
        """Get set of unique broker names in metadata."""
        ...

    def get_stats(self) -> dict[str, int]:
        """Get statistics about stored metadata."""
        ...

    def save(self) -> None:
        """Save metadata to file."""
        ...


class IDownloader(Protocol):
    """Interface for PDF downloading.

    Provides methods for downloading PDFs with rate limiting and retry logic.
    """

    def download(self, report: ReportInfo) -> DownloadResult:
        """Download PDF and save to appropriate location."""
        ...

    def close(self) -> None:
        """Close the HTTP client."""
        ...


class IDownloaderFactory(Protocol):
    """Factory interface for creating downloaders.

    Allows dependency injection of downloader creation logic.
    """

    def create(
        self,
        base_dir: Path,
        delay_range: tuple[float, float],
        metadata_manager: IMetadataManager | None,
    ) -> IDownloader:
        """Create a new downloader instance."""
        ...
