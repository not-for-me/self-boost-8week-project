"""Main scraper orchestrator for Naver Finance research reports."""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from src.config import (
    BASE_URL,
    DEFAULT_DELAY_RANGE,
    DEFAULT_HEADERS,
    DEFAULT_MIN_BROKERS,
    DEFAULT_MIN_PER_BROKER,
    DEFAULT_TOTAL_TARGET,
    REQUEST_TIMEOUT,
)
from src.downloader import PDFDownloader
from src.metadata import MetadataManager
from src.parser import ReportInfo, get_total_pages, parse_report_list

logger = logging.getLogger(__name__)


@dataclass
class CollectionConfig:
    """Configuration for report collection."""

    total_target: int = DEFAULT_TOTAL_TARGET
    min_brokers: int = DEFAULT_MIN_BROKERS
    min_per_broker: int = DEFAULT_MIN_PER_BROKER
    delay_range: tuple[float, float] = DEFAULT_DELAY_RANGE


@dataclass
class CollectionStats:
    """Statistics for the collection process."""

    total_downloaded: int = 0
    by_broker: dict[str, int] = field(default_factory=dict)
    failed: int = 0
    skipped_url_duplicate: int = 0
    skipped_content_duplicate: int = 0
    existing_count: int = 0  # Count of reports already in metadata before session
    existing_brokers: set[str] = field(default_factory=set)  # Brokers in metadata

    def add_download(self, broker: str) -> None:
        """Record a successful download."""
        self.total_downloaded += 1
        self.by_broker[broker] = self.by_broker.get(broker, 0) + 1

    def add_failure(self) -> None:
        """Record a failed download."""
        self.failed += 1

    def add_skip_url_duplicate(self) -> None:
        """Record a skipped report due to URL duplicate."""
        self.skipped_url_duplicate += 1

    def add_skip_content_duplicate(self) -> None:
        """Record a skipped report due to content duplicate."""
        self.skipped_content_duplicate += 1

    @property
    def total_skipped(self) -> int:
        """Total number of skipped reports."""
        return self.skipped_url_duplicate + self.skipped_content_duplicate

    def get_broker_count(self, broker: str) -> int:
        """Get download count for a specific broker."""
        return self.by_broker.get(broker, 0)

    def get_unique_broker_count(self) -> int:
        """Get number of unique brokers with downloads in current session."""
        return len(self.by_broker)

    def get_total_broker_count(self) -> int:
        """Get total number of unique brokers including existing."""
        all_brokers = self.existing_brokers | set(self.by_broker.keys())
        return len(all_brokers)

    def get_total_count(self) -> int:
        """Get total count including existing reports."""
        return self.existing_count + self.total_downloaded


class ReportScraper:
    """Orchestrates the scraping process for research reports."""

    def __init__(self, config: CollectionConfig, data_dir: Path):
        """Initialize the scraper.

        Args:
            config: Collection configuration.
            data_dir: Directory to save downloaded PDFs.
        """
        self.config = config
        self.data_dir = Path(data_dir)
        self._client = httpx.Client(headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
        self._downloader: PDFDownloader | None = None
        self._metadata: MetadataManager | None = None
        self._session_downloaded_urls: set[str] = set()  # Track URLs in current session

    def __enter__(self):
        self._metadata = MetadataManager(self.data_dir)
        self._downloader = PDFDownloader(
            base_dir=self.data_dir,
            delay_range=self.config.delay_range,
            metadata_manager=self._metadata,
        )

        # Log existing metadata stats
        existing_count = self._metadata.get_total_count()
        if existing_count > 0:
            logger.info(f"기존 메타데이터 로드: {existing_count}개 리포트")
            existing_stats = self._metadata.get_stats()
            for broker, count in sorted(
                existing_stats.items(), key=lambda x: x[1], reverse=True
            ):
                logger.debug(f"  - {broker}: {count}개")

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self) -> None:
        """Close HTTP client and downloader, save metadata."""
        self._client.close()
        if self._downloader:
            self._downloader.close()
        if self._metadata:
            self._metadata.save()
            logger.info("메타데이터 저장 완료")

    def run(self) -> CollectionStats:
        """Execute the full collection process.

        Returns:
            CollectionStats with download results.
        """
        if not self._downloader or not self._metadata:
            raise RuntimeError("Scraper must be used as context manager")

        # Calculate effective target (subtract already downloaded)
        existing_count = self._metadata.get_total_count()
        existing_brokers = self._metadata.get_brokers()
        effective_target = max(0, self.config.total_target - existing_count)

        stats = CollectionStats(
            existing_count=existing_count,
            existing_brokers=existing_brokers,
        )

        logger.info(
            f"수집 시작: 목표 {self.config.total_target}개 "
            f"(기존 {existing_count}개, 추가 {effective_target}개 필요), "
            f"최소 {self.config.min_brokers}개 증권사"
        )

        if effective_target == 0:
            logger.info("이미 목표 수량에 도달했습니다.")
            self._log_final_stats(stats)
            return stats

        # Phase 1: Scan pages and collect reports by broker
        reports_by_broker = self._collect_reports_by_broker(effective_target)

        if len(reports_by_broker) < self.config.min_brokers:
            logger.warning(
                f"증권사 수 부족: {len(reports_by_broker)}개 "
                f"(최소 {self.config.min_brokers}개 필요)"
            )

        logger.info(f"발견된 증권사: {len(reports_by_broker)}개")
        for broker, reports in sorted(reports_by_broker.items()):
            logger.debug(f"  - {broker}: {len(reports)}개 리포트")

        # Phase 2: Download with even distribution
        self._download_with_distribution(reports_by_broker, stats, effective_target)

        # Save metadata after completion
        self._metadata.save()

        self._log_final_stats(stats)
        return stats

    def _collect_reports_by_broker(self, target: int) -> dict[str, list[ReportInfo]]:
        """Collect reports grouped by broker from multiple pages.

        Filters out already downloaded URLs during collection.

        Args:
            target: Number of new reports to collect.
        """
        reports_by_broker: dict[str, list[ReportInfo]] = defaultdict(list)
        new_reports_count = 0
        page = 1

        # Get total pages from first page
        first_html = self._fetch_page(1)
        total_pages = get_total_pages(first_html)
        logger.info(f"총 {total_pages} 페이지 발견")

        # Parse first page
        reports = parse_report_list(first_html)
        for report in reports:
            # Skip if already in metadata
            if self._metadata and self._metadata.is_duplicate_url(report.pdf_url):
                continue
            reports_by_broker[report.broker].append(report)
            new_reports_count += 1

        # Continue scanning until we have enough new reports
        # Estimate: need ~target * 1.5 reports to account for failures and distribution
        target_reports = int(target * 1.5)
        page = 2

        while new_reports_count < target_reports and page <= total_pages:
            html = self._fetch_page(page)
            reports = parse_report_list(html)

            if not reports:
                logger.warning(f"페이지 {page}에서 리포트를 찾을 수 없음")
                break

            for report in reports:
                # Skip if already in metadata
                if self._metadata and self._metadata.is_duplicate_url(report.pdf_url):
                    continue
                reports_by_broker[report.broker].append(report)
                new_reports_count += 1

            if page % 10 == 0:
                logger.info(
                    f"페이지 {page} 스캔 완료: "
                    f"{new_reports_count}개 신규 리포트, {len(reports_by_broker)}개 증권사"
                )

            page += 1

        return dict(reports_by_broker)

    def _download_with_distribution(
        self,
        reports_by_broker: dict[str, list[ReportInfo]],
        stats: CollectionStats,
        target: int,
    ) -> None:
        """Download reports with even distribution across brokers.

        Strategy:
        1. First, ensure minimum per broker (min_per_broker)
        2. Then, round-robin to fill remaining quota
        """
        if not self._downloader:
            return

        brokers = list(reports_by_broker.keys())
        broker_indices: dict[str, int] = {b: 0 for b in brokers}

        # Phase 1: Minimum guarantee - ensure each broker gets min_per_broker
        logger.info(f"Phase 1: 증권사별 최소 {self.config.min_per_broker}개 수집")
        for broker in brokers:
            reports = reports_by_broker[broker]
            for _ in range(self.config.min_per_broker):
                if self._should_stop(stats, target):
                    self._save_metadata_checkpoint()
                    return

                idx = broker_indices[broker]
                if idx >= len(reports):
                    break

                report = reports[idx]
                broker_indices[broker] += 1

                if self._download_report(report, stats):
                    self._log_progress(stats, target)

        # Phase 2: Round-robin for remaining quota
        logger.info("Phase 2: 라운드 로빈 방식으로 추가 수집")
        active_brokers = [
            b for b in brokers if broker_indices[b] < len(reports_by_broker[b])
        ]

        while active_brokers and not self._should_stop(stats, target):
            for broker in list(active_brokers):
                if self._should_stop(stats, target):
                    self._save_metadata_checkpoint()
                    return

                reports = reports_by_broker[broker]
                idx = broker_indices[broker]

                if idx >= len(reports):
                    active_brokers.remove(broker)
                    continue

                report = reports[idx]
                broker_indices[broker] += 1

                if self._download_report(report, stats):
                    self._log_progress(stats, target)

    def _download_report(self, report: ReportInfo, stats: CollectionStats) -> bool:
        """Download a single report.

        Returns:
            True if download was attempted (success or failure),
            False if skipped.
        """
        if not self._downloader:
            return False

        # Skip if already downloaded in this session
        if report.pdf_url in self._session_downloaded_urls:
            stats.add_skip_url_duplicate()
            return False

        self._session_downloaded_urls.add(report.pdf_url)

        result = self._downloader.download(report)

        if result.success:
            stats.add_download(report.broker)
            return True
        elif result.skipped_reason and result.skipped_reason.startswith(
            "duplicate_content:"
        ):
            stats.add_skip_content_duplicate()
            logger.debug(f"Content duplicate: {report.pdf_url}")
            return False
        else:
            stats.add_failure()
            return True

    def _fetch_page(self, page: int) -> str:
        """Fetch HTML content for a specific page.

        Args:
            page: Page number to fetch.

        Returns:
            HTML content as string.
        """
        url = f"{BASE_URL}?page={page}"
        response = self._client.get(url)
        response.raise_for_status()
        return response.text

    def _should_stop(self, stats: CollectionStats, target: int) -> bool:
        """Determine if collection should stop.

        Args:
            stats: Current collection statistics.
            target: Target number of downloads.

        Returns:
            True if target reached or should stop.
        """
        return stats.total_downloaded >= target

    def _save_metadata_checkpoint(self) -> None:
        """Save metadata checkpoint during collection."""
        if self._metadata:
            self._metadata.save()
            logger.debug("메타데이터 체크포인트 저장")

    def _log_progress(self, stats: CollectionStats, target: int) -> None:
        """Log progress at regular intervals."""
        if stats.total_downloaded % 10 == 0:
            logger.info(
                f"[{stats.total_downloaded}/{target}] "
                f"증권사 {stats.get_unique_broker_count()}개, "
                f"실패 {stats.failed}개, "
                f"스킵 {stats.total_skipped}개"
            )
            # Save checkpoint every 10 downloads
            self._save_metadata_checkpoint()

    def _log_final_stats(self, stats: CollectionStats) -> None:
        """Log final collection statistics."""
        logger.info("=" * 50)
        logger.info("수집 완료")
        logger.info("=" * 50)
        logger.info(f"총 다운로드: {stats.total_downloaded}개")
        logger.info(f"실패: {stats.failed}개")
        logger.info(
            f"스킵: {stats.total_skipped}개 "
            f"(URL 중복: {stats.skipped_url_duplicate}, "
            f"내용 중복: {stats.skipped_content_duplicate})"
        )
        logger.info(f"증권사별 현황 ({stats.get_unique_broker_count()}개):")
        for broker, count in sorted(
            stats.by_broker.items(), key=lambda x: x[1], reverse=True
        ):
            logger.info(f"  - {broker}: {count}개")

        # Also log total with existing
        if self._metadata:
            total = self._metadata.get_total_count()
            logger.info(f"총 보유 리포트: {total}개")
