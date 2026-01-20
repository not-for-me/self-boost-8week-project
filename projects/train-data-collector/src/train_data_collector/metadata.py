"""Metadata manager for tracking downloaded reports and preventing duplicates."""

import hashlib
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

METADATA_FILENAME = "metadata.json"


@dataclass
class ReportMetadata:
    """Metadata for a downloaded report."""

    pdf_url: str
    broker: str
    stock_name: str
    title: str
    date: str  # yyyy-mm-dd format
    local_path: (
        str  # Relative path from data_dir (e.g., "한화투자증권/2026-01-19_01.pdf")
    )
    file_hash: str  # Format: "md5:{hash}"
    downloaded_at: str  # ISO format timestamp

    @classmethod
    def from_dict(cls, data: dict) -> "ReportMetadata":
        """Create ReportMetadata from dictionary."""
        return cls(**data)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class MetadataStore:
    """Storage structure for all metadata."""

    reports: dict[str, ReportMetadata] = field(
        default_factory=dict
    )  # pdf_url -> metadata
    hashes: dict[str, str] = field(default_factory=dict)  # file_hash -> pdf_url

    def add_report(self, metadata: ReportMetadata) -> None:
        """Add a report to the store."""
        self.reports[metadata.pdf_url] = metadata
        self.hashes[metadata.file_hash] = metadata.pdf_url

    def has_url(self, pdf_url: str) -> bool:
        """Check if URL already exists."""
        return pdf_url in self.reports

    def has_hash(self, file_hash: str) -> bool:
        """Check if file hash already exists."""
        return file_hash in self.hashes

    def get_by_url(self, pdf_url: str) -> ReportMetadata | None:
        """Get metadata by URL."""
        return self.reports.get(pdf_url)

    def get_by_hash(self, file_hash: str) -> ReportMetadata | None:
        """Get metadata by file hash."""
        pdf_url = self.hashes.get(file_hash)
        if pdf_url:
            return self.reports.get(pdf_url)
        return None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "reports": {url: meta.to_dict() for url, meta in self.reports.items()},
            "hashes": self.hashes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MetadataStore":
        """Create MetadataStore from dictionary."""
        store = cls()
        for url, meta_dict in data.get("reports", {}).items():
            store.reports[url] = ReportMetadata.from_dict(meta_dict)
        store.hashes = data.get("hashes", {})
        return store


class MetadataManager:
    """Manages metadata for downloaded reports."""

    def __init__(self, data_dir: Path):
        """Initialize the metadata manager.

        Args:
            data_dir: Base directory for data storage.
        """
        self.data_dir = Path(data_dir)
        self.metadata_path = self.data_dir / METADATA_FILENAME
        self._store: MetadataStore | None = None

    @property
    def store(self) -> MetadataStore:
        """Lazy load the metadata store."""
        if self._store is None:
            self._store = self._load()
        return self._store

    def _load(self) -> MetadataStore:
        """Load metadata from file."""
        if not self.metadata_path.exists():
            logger.debug("No existing metadata file, creating new store")
            return MetadataStore()

        try:
            with open(self.metadata_path, encoding="utf-8") as f:
                data = json.load(f)
            store = MetadataStore.from_dict(data)
            logger.info(f"Loaded metadata: {len(store.reports)} reports")
            return store
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to load metadata, creating new store: {e}")
            return MetadataStore()

    def save(self) -> None:
        """Save metadata to file."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with open(self.metadata_path, "w", encoding="utf-8") as f:
            json.dump(self.store.to_dict(), f, ensure_ascii=False, indent=2)
        logger.debug(f"Saved metadata: {len(self.store.reports)} reports")

    def is_duplicate_url(self, pdf_url: str) -> bool:
        """Check if URL is already downloaded.

        Args:
            pdf_url: PDF URL to check.

        Returns:
            True if already downloaded.
        """
        return self.store.has_url(pdf_url)

    def is_duplicate_hash(self, file_hash: str) -> bool:
        """Check if file hash already exists.

        Args:
            file_hash: File hash to check.

        Returns:
            True if duplicate content exists.
        """
        return self.store.has_hash(file_hash)

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
        """Add a new report to metadata.

        Args:
            pdf_url: Original PDF URL.
            broker: Broker name.
            stock_name: Stock name.
            title: Report title.
            date: Report date (yyyy-mm-dd format).
            local_path: Relative path to saved file.
            file_hash: MD5 hash of file content.

        Returns:
            Created ReportMetadata.
        """
        metadata = ReportMetadata(
            pdf_url=pdf_url,
            broker=broker,
            stock_name=stock_name,
            title=title,
            date=date,
            local_path=local_path,
            file_hash=file_hash,
            downloaded_at=datetime.now().isoformat(),
        )
        self.store.add_report(metadata)
        return metadata

    def get_existing_report_by_hash(self, file_hash: str) -> ReportMetadata | None:
        """Get existing report with same content hash.

        Args:
            file_hash: File hash to check.

        Returns:
            ReportMetadata if duplicate found, None otherwise.
        """
        return self.store.get_by_hash(file_hash)

    def get_stats(self) -> dict[str, int]:
        """Get statistics about stored metadata.

        Returns:
            Dictionary with counts by broker.
        """
        stats: dict[str, int] = {}
        for metadata in self.store.reports.values():
            stats[metadata.broker] = stats.get(metadata.broker, 0) + 1
        return stats

    def get_total_count(self) -> int:
        """Get total number of downloaded reports."""
        return len(self.store.reports)

    def get_broker_count(self) -> int:
        """Get number of unique brokers in metadata."""
        return len(self.get_stats())

    def get_brokers(self) -> set[str]:
        """Get set of unique broker names in metadata."""
        return set(self.get_stats().keys())


def calculate_file_hash(content: bytes) -> str:
    """Calculate MD5 hash of file content.

    Args:
        content: File content as bytes.

    Returns:
        Hash string in format "md5:{hash}".
    """
    md5_hash = hashlib.md5(content).hexdigest()
    return f"md5:{md5_hash}"


def calculate_file_hash_from_path(file_path: Path) -> str:
    """Calculate MD5 hash of a file.

    Args:
        file_path: Path to file.

    Returns:
        Hash string in format "md5:{hash}".
    """
    content = file_path.read_bytes()
    return calculate_file_hash(content)
