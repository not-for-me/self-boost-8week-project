"""CLI entrypoint for the train-data-collector."""

import argparse
import logging
import sys
from pathlib import Path

from src.config import (
    DEFAULT_DELAY_RANGE,
    DEFAULT_MIN_BROKERS,
    DEFAULT_MIN_PER_BROKER,
    DEFAULT_TOTAL_TARGET,
)
from src.scraper import CollectionConfig, ReportScraper


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the application."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="[%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="네이버 금융 종목분석 리포트 PDF 수집기",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--target",
        type=int,
        default=DEFAULT_TOTAL_TARGET,
        help="수집할 총 PDF 파일 수",
    )

    parser.add_argument(
        "--min-brokers",
        type=int,
        default=DEFAULT_MIN_BROKERS,
        help="최소 증권사 수",
    )

    parser.add_argument(
        "--min-per-broker",
        type=int,
        default=DEFAULT_MIN_PER_BROKER,
        help="증권사별 최소 수집 수",
    )

    parser.add_argument(
        "--delay-min",
        type=float,
        default=DEFAULT_DELAY_RANGE[0],
        help="다운로드 간 최소 대기 시간(초)",
    )

    parser.add_argument(
        "--delay-max",
        type=float,
        default=DEFAULT_DELAY_RANGE[1],
        help="다운로드 간 최대 대기 시간(초)",
    )

    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).parent.parent / "data",
        help="PDF 저장 디렉토리",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="상세 로그 출력",
    )

    return parser.parse_args()


def main() -> int:
    """Main entrypoint for the scraper."""
    args = parse_args()
    setup_logging(args.verbose)

    logger = logging.getLogger(__name__)

    config = CollectionConfig(
        total_target=args.target,
        min_brokers=args.min_brokers,
        min_per_broker=args.min_per_broker,
        delay_range=(args.delay_min, args.delay_max),
    )

    data_dir = Path(args.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"데이터 저장 경로: {data_dir.absolute()}")
    logger.info(f"목표: {config.total_target}개 PDF")
    logger.info(f"최소 증권사: {config.min_brokers}개")
    logger.info(f"증권사별 최소: {config.min_per_broker}개")
    logger.info(f"다운로드 간격: {config.delay_range[0]}-{config.delay_range[1]}초")

    try:
        with ReportScraper(config, data_dir) as scraper:
            stats = scraper.run()

        # Check if minimum requirements were met
        if stats.get_unique_broker_count() < config.min_brokers:
            logger.warning(
                f"최소 증권사 요건 미충족: "
                f"{stats.get_unique_broker_count()}/{config.min_brokers}"
            )
            return 1

        if stats.total_downloaded < config.total_target:
            logger.warning(
                f"목표 수량 미달: {stats.total_downloaded}/{config.total_target}"
            )
            return 1

        return 0

    except KeyboardInterrupt:
        logger.info("\n사용자에 의해 중단됨")
        return 130

    except Exception as e:
        logger.error(f"오류 발생: {e}")
        if args.verbose:
            logger.exception("상세 오류:")
        return 1


if __name__ == "__main__":
    sys.exit(main())
