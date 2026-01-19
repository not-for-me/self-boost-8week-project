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
from src.parser import ReportInfo, get_total_pages, get_unique_brokers, parse_report_list

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
    skipped: int = 0

    def add_download(self, broker: str) -> None:
        """Record a successful download."""
        self.total_downloaded += 1
        self.by_broker[broker] = self.by_broker.get(broker, 0) + 1

    def add_failure(self) -> None:
        """Record a failed download."""
        self.failed += 1

    def add_skip(self) -> None:
        """Record a skipped report."""
        self.skipped += 1

    def get_broker_count(self, broker: str) -> int:
        """Get download count for a specific broker."""
        return self.by_broker.get(broker, 0)

    def get_unique_broker_count(self) -> int:
        """Get number of unique brokers with downloads."""
        return len(self.by_broker)


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
        self._downloaded_urls: set[str] = set()

    def __enter__(self):
        self._downloader = PDFDownloader(
            base_dir=self.data_dir,
            delay_range=self.config.delay_range,
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self) -> None:
        """Close HTTP client and downloader."""
        self._client.close()
        if self._downloader:
            self._downloader.close()

    def run(self) -> CollectionStats:
        """Execute the full collection process.

        Returns:
            CollectionStats with download results.
        """
        if not self._downloader:
            raise RuntimeError("Scraper must be used as context manager")

        stats = CollectionStats()
        logger.info(
            f"수집 시작: 목표 {self.config.total_target}개, "
            f"최소 {self.config.min_brokers}개 증권사"
        )

        # Phase 1: Scan pages and collect reports by broker
        reports_by_broker = self._collect_reports_by_broker()

        if len(reports_by_broker) < self.config.min_brokers:
            logger.warning(
                f"증권사 수 부족: {len(reports_by_broker)}개 "
                f"(최소 {self.config.min_brokers}개 필요)"
            )

        logger.info(f"발견된 증권사: {len(reports_by_broker)}개")
        for broker, reports in sorted(reports_by_broker.items()):
            logger.debug(f"  - {broker}: {len(reports)}개 리포트")

        # Phase 2: Download with even distribution
        self._download_with_distribution(reports_by_broker, stats)

        self._log_final_stats(stats)
        return stats

    def _collect_reports_by_broker(self) -> dict[str, list[ReportInfo]]:
        """Collect reports grouped by broker from multiple pages.

        Scans pages until we have enough reports for the target.
        """
        reports_by_broker: dict[str, list[ReportInfo]] = defaultdict(list)
        total_reports = 0
        page = 1

        # Get total pages from first page
        first_html = self._fetch_page(1)
        total_pages = get_total_pages(first_html)
        logger.info(f"총 {total_pages} 페이지 발견")

        # Parse first page
        reports = parse_report_list(first_html)
        for report in reports:
            reports_by_broker[report.broker].append(report)
            total_reports += 1

        # Continue scanning until we have enough reports
        # Estimate: need ~target * 1.5 reports to account for failures and distribution
        target_reports = int(self.config.total_target * 1.5)
        page = 2

        while total_reports < target_reports and page <= total_pages:
            html = self._fetch_page(page)
            reports = parse_report_list(html)

            if not reports:
                logger.warning(f"페이지 {page}에서 리포트를 찾을 수 없음")
                break

            for report in reports:
                reports_by_broker[report.broker].append(report)
                total_reports += 1

            if page % 10 == 0:
                logger.info(
                    f"페이지 {page} 스캔 완료: "
                    f"{total_reports}개 리포트, {len(reports_by_broker)}개 증권사"
                )

            page += 1

        return dict(reports_by_broker)

    def _download_with_distribution(
        self,
        reports_by_broker: dict[str, list[ReportInfo]],
        stats: CollectionStats,
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
                if self._should_stop(stats):
                    return

                idx = broker_indices[broker]
                if idx >= len(reports):
                    break

                report = reports[idx]
                broker_indices[broker] += 1

                if self._download_report(report, stats):
                    self._log_progress(stats)

        # Phase 2: Round-robin for remaining quota
        logger.info("Phase 2: 라운드 로빈 방식으로 추가 수집")
        active_brokers = [b for b in brokers if broker_indices[b] < len(reports_by_broker[b])]

        while active_brokers and not self._should_stop(stats):
            for broker in list(active_brokers):
                if self._should_stop(stats):
                    return

                reports = reports_by_broker[broker]
                idx = broker_indices[broker]

                if idx >= len(reports):
                    active_brokers.remove(broker)
                    continue

                report = reports[idx]
                broker_indices[broker] += 1

                if self._download_report(report, stats):
                    self._log_progress(stats)

    def _download_report(self, report: ReportInfo, stats: CollectionStats) -> bool:
        """Download a single report.

        Returns:
            True if download was attempted (success or failure),
            False if skipped.
        """
        if not self._downloader:
            return False

        # Skip duplicates
        if report.pdf_url in self._downloaded_urls:
            stats.add_skip()
            return False

        self._downloaded_urls.add(report.pdf_url)

        result = self._downloader.download(report)
        if result:
            stats.add_download(report.broker)
            return True
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

    def _should_stop(self, stats: CollectionStats) -> bool:
        """Determine if collection should stop.

        Args:
            stats: Current collection statistics.

        Returns:
            True if target reached or should stop.
        """
        return stats.total_downloaded >= self.config.total_target

    def _log_progress(self, stats: CollectionStats) -> None:
        """Log progress at regular intervals."""
        if stats.total_downloaded % 10 == 0:
            logger.info(
                f"[{stats.total_downloaded}/{self.config.total_target}] "
                f"증권사 {stats.get_unique_broker_count()}개, "
                f"실패 {stats.failed}개"
            )

    def _log_final_stats(self, stats: CollectionStats) -> None:
        """Log final collection statistics."""
        logger.info("=" * 50)
        logger.info("수집 완료")
        logger.info("=" * 50)
        logger.info(f"총 다운로드: {stats.total_downloaded}개")
        logger.info(f"실패: {stats.failed}개")
        logger.info(f"스킵: {stats.skipped}개")
        logger.info(f"증권사별 현황 ({stats.get_unique_broker_count()}개):")
        for broker, count in sorted(
            stats.by_broker.items(), key=lambda x: x[1], reverse=True
        ):
            logger.info(f"  - {broker}: {count}개")
