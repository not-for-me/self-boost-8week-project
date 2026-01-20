"""Abstract base class for table detectors."""

from abc import ABC, abstractmethod

from fin_stat_table_detector.models import TableCandidate


class AbstractDetector(ABC):
    """표 탐지기 추상 인터페이스.

    모든 탐지기가 구현해야 하는 공통 인터페이스를 정의합니다.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """탐지기 이름.

        Returns:
            탐지기 식별자 문자열
        """

    @abstractmethod
    def detect(
        self,
        pdf_path: str,
        pages: list[int] | None = None,
    ) -> list[TableCandidate]:
        """PDF에서 표 후보 탐지.

        Args:
            pdf_path: PDF 파일 경로
            pages: 탐지할 페이지 번호 리스트 (1-indexed).
                   None이면 전체 페이지.

        Returns:
            탐지된 TableCandidate 리스트

        Raises:
            FileNotFoundError: PDF 파일이 존재하지 않을 때
            ValueError: 잘못된 페이지 번호가 주어졌을 때
        """
