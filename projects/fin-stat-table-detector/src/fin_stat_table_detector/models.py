"""Data models for table detection.

BBox, TableCandidate, FinancialTable 데이터 클래스를 정의합니다.
"""

from dataclasses import dataclass


@dataclass
class BBox:
    """좌표 (PDF 좌표계: 좌상단 기준).

    Attributes:
        x0: 좌측 x 좌표
        y0: 상단 y 좌표
        x1: 우측 x 좌표
        y1: 하단 y 좌표
    """

    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        """영역의 너비."""
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        """영역의 높이."""
        return self.y1 - self.y0

    @property
    def area(self) -> float:
        """영역의 면적."""
        return self.width * self.height


@dataclass
class TableCandidate:
    """탐지된 표 후보.

    Attributes:
        page: 페이지 번호 (1-indexed)
        bbox: 표의 위치 좌표
        detector: 탐지기 이름 ("pdfplumber", "camelot_lattice", "camelot_stream", "docling")
        row_count: 행 개수 (선택)
        col_count: 열 개수 (선택)
        text_content: 표 내 텍스트 (선택)
    """

    page: int
    bbox: BBox
    detector: str
    row_count: int | None = None
    col_count: int | None = None
    text_content: str | None = None


@dataclass
class FinancialTable:
    """재무제표로 분류된 표.

    Attributes:
        page: 페이지 번호 (1-indexed)
        bbox: 표의 위치 좌표
        category: 재무제표 카테고리 ("income_statement", "balance_sheet", etc.)
        confidence: 신뢰도 (0.0 ~ 1.0)
        matched_keywords: 매칭된 키워드 목록
        detector_source: 원본 탐지기 이름
    """

    page: int
    bbox: BBox
    category: str
    confidence: float
    matched_keywords: list[str]
    detector_source: str
