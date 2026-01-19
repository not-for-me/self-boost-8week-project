"""PDF downloader for Naver Finance research reports."""

import logging
import random
import re
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

from src.config import (
    DEFAULT_DELAY_RANGE,
    DEFAULT_HEADERS,
    MAX_RETRIES,
    REQUEST_TIMEOUT,
    RETRY_BACKOFF,
)
from src.metadata import MetadataManager, calculate_file_hash
from src.parser import ReportInfo

logger = logging.getLogger(__name__)


class DownloadError(Exception):
    """Raised when PDF download fails after all retries."""

    pass


class DuplicateContentError(Exception):
    """Raised when downloaded content is duplicate of existing file."""

    def __init__(self, message: str, existing_path: str):
        super().__init__(message)
        self.existing_path = existing_path


@dataclass
class DownloadResult:
    """Result of a download operation."""

    success: bool
    path: Path | None = None
    file_hash: str | None = None
    skipped_reason: str | None = None


class PDFDownloader:
    """Downloads PDF files from Naver Finance with rate limiting."""

    def __init__(
        self,
        base_dir: Path,
        delay_range: tuple[float, float] = DEFAULT_DELAY_RANGE,
        metadata_manager: MetadataManager | None = None,
    ):
        """Initialize the downloader.

        Args:
            base_dir: Base directory for saving PDFs (e.g., ../data).
            delay_range: Min and max seconds to wait between downloads.
            metadata_manager: Optional metadata manager for deduplication.
        """
        self.base_dir = Path(base_dir)
        self.delay_range = delay_range
        self.metadata = metadata_manager
        self._client = httpx.Client(headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
        self._last_download_time: float | None = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def download(self, report: ReportInfo) -> DownloadResult:
        """Download PDF and save to appropriate location.

        Args:
            report: ReportInfo containing PDF URL and metadata.

        Returns:
            DownloadResult with success status and details.
        """
        # Apply rate limiting
        self._wait_with_jitter()

        # Prepare target directory
        broker_dir = self.base_dir / report.broker
        broker_dir.mkdir(parents=True, exist_ok=True)

        # Download with retry
        try:
            content = self._download_with_retry(report.pdf_url)
        except DownloadError as e:
            logger.error(f"Failed to download {report.pdf_url}: {e}")
            return DownloadResult(success=False, skipped_reason=str(e))

        # Calculate file hash
        file_hash = calculate_file_hash(content)

        # Check for duplicate content
        if self.metadata:
            existing = self.metadata.get_existing_report_by_hash(file_hash)
            if existing:
                logger.info(
                    f"Duplicate content detected, skipping: {report.pdf_url} "
                    f"(same as {existing.local_path})"
                )
                return DownloadResult(
                    success=False,
                    file_hash=file_hash,
                    skipped_reason=f"duplicate_content:{existing.local_path}",
                )

        # Generate filename (continues from existing sequence)
        existing_files = [f.name for f in broker_dir.glob("*.pdf")]
        filename = self._generate_filename(report, existing_files)
        target_path = broker_dir / filename

        # Save file
        target_path.write_bytes(content)
        logger.info(f"Downloaded: {target_path}")

        # Update metadata
        if self.metadata:
            relative_path = f"{report.broker}/{filename}"
            self.metadata.add_report(
                pdf_url=report.pdf_url,
                broker=report.broker,
                stock_name=report.stock_name,
                title=report.title,
                date=report.get_formatted_date(),
                local_path=relative_path,
                file_hash=file_hash,
            )

        return DownloadResult(success=True, path=target_path, file_hash=file_hash)

    def _generate_filename(self, report: ReportInfo, existing_files: list[str]) -> str:
        """Generate filename in format: {date}_{seq}.pdf.

        Continues from the highest existing sequence number for the same date.

        Args:
            report: ReportInfo with date information.
            existing_files: List of existing filenames in the target directory.

        Returns:
            Generated filename like "2025-01-15_05.pdf".
        """
        formatted_date = report.get_formatted_date()

        # Find the highest existing sequence number for this date
        max_seq = 0
        pattern = re.compile(rf"^{re.escape(formatted_date)}_(\d+)\.pdf$")

        for filename in existing_files:
            match = pattern.match(filename)
            if match:
                seq = int(match.group(1))
                max_seq = max(max_seq, seq)

        # Next sequence number
        next_seq = max_seq + 1
        return f"{formatted_date}_{next_seq:02d}.pdf"

    def _wait_with_jitter(self) -> None:
        """Wait random time between downloads to avoid rate limiting."""
        if self._last_download_time is not None:
            elapsed = time.time() - self._last_download_time
            min_delay, max_delay = self.delay_range
            target_delay = random.uniform(min_delay, max_delay)

            if elapsed < target_delay:
                sleep_time = target_delay - elapsed
                logger.debug(f"Sleeping for {sleep_time:.1f}s")
                time.sleep(sleep_time)

        self._last_download_time = time.time()

    def _download_with_retry(self, url: str) -> bytes:
        """Download URL content with exponential backoff retry.

        Args:
            url: URL to download.

        Returns:
            Downloaded content as bytes.

        Raises:
            DownloadError: If all retries fail.
        """
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES):
            try:
                response = self._client.get(url)
                response.raise_for_status()

                # Validate content type
                content_type = response.headers.get("content-type", "")
                if "pdf" not in content_type.lower() and not url.endswith(".pdf"):
                    raise DownloadError(f"Unexpected content type: {content_type}")

                return response.content

            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code in (400, 401, 403, 404):
                    # Don't retry client errors
                    raise DownloadError(f"HTTP {e.response.status_code}: {url}")
                logger.warning(f"Attempt {attempt + 1}/{MAX_RETRIES} failed: {e}")

            except httpx.RequestError as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1}/{MAX_RETRIES} failed: {e}")

            # Exponential backoff before retry
            if attempt < MAX_RETRIES - 1:
                backoff = RETRY_BACKOFF**attempt
                time.sleep(backoff)

        raise DownloadError(f"All {MAX_RETRIES} attempts failed: {last_error}")
