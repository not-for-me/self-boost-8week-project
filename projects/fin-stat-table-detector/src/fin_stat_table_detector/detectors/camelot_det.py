"""Camelot-based table detector."""

import camelot

from fin_stat_table_detector.detectors.base import AbstractDetector
from fin_stat_table_detector.models import BBox, TableCandidate


class CamelotDetector(AbstractDetector):
    """camelot 기반 표 탐지기.

    Camelot 라이브러리를 사용하여 PDF에서 표를 탐지합니다.
    lattice 모드와 stream 모드를 지원합니다.
    """

    def __init__(self, flavor: str = "lattice") -> None:
        """CamelotDetector 초기화.

        Args:
            flavor: 탐지 모드 ("lattice" 또는 "stream")

        Raises:
            ValueError: 잘못된 flavor 값
        """
        if flavor not in ("lattice", "stream"):
            raise ValueError(f"flavor must be 'lattice' or 'stream', got '{flavor}'")

        self._flavor = flavor

    @property
    def name(self) -> str:
        """탐지기 이름.

        Returns:
            탐지기 식별자 문자열 (예: "camelot_lattice")
        """
        return f"camelot_{self._flavor}"

    @property
    def flavor(self) -> str:
        """탐지 모드.

        Returns:
            현재 설정된 flavor 값 ("lattice" 또는 "stream")
        """
        return self._flavor

    def detect(
        self,
        pdf_path: str,
        pages: list[int] | None = None,
    ) -> list[TableCandidate]:
        """PDF에서 표 후보 탐지.

        camelot으로 표를 탐지합니다.

        내부 동작:
        1. camelot.read_pdf()로 테이블 추출
        2. 각 테이블의 bbox와 데이터를 TableCandidate로 변환

        주의: camelot의 좌표계는 좌하단 기준이므로 변환 필요

        Args:
            pdf_path: PDF 파일 경로
            pages: 탐지할 페이지 번호 리스트 (1-indexed).
                   None이면 전체 페이지.

        Returns:
            탐지된 TableCandidate 리스트
        """
        candidates = []

        # 페이지 문자열 생성 (camelot 형식)
        pages_str = self._format_pages(pages) if pages else "all"

        tables = camelot.read_pdf(
            pdf_path,
            pages=pages_str,
            flavor=self._flavor,
        )

        for table in tables:
            # camelot bbox: (x0, y0, x1, y1) 좌하단 기준
            # 페이지 높이를 알아야 좌상단 기준으로 변환 가능
            bbox = self._convert_bbox(table)

            candidates.append(
                TableCandidate(
                    page=table.page,
                    bbox=bbox,
                    detector=self.name,
                    row_count=table.shape[0],
                    col_count=table.shape[1],
                    text_content=self._extract_text(table),
                )
            )

        return candidates

    def _format_pages(self, pages: list[int]) -> str:
        """페이지 리스트를 camelot 형식 문자열로 변환.

        Args:
            pages: 페이지 번호 리스트 (예: [1, 2, 5])

        Returns:
            camelot 형식 문자열 (예: "1,2,5")
        """
        return ",".join(str(p) for p in pages)

    def _convert_bbox(self, table) -> BBox:
        """camelot bbox를 좌상단 기준 BBox로 변환.

        camelot은 좌하단 원점, y가 위로 증가
        우리 시스템은 좌상단 원점, y가 아래로 증가

        Args:
            table: camelot Table 객체

        Returns:
            좌상단 기준 BBox
        """
        # table._bbox: (x0, y0, x1, y1) 좌하단 기준
        x0, y0, x1, y1 = table._bbox
        page_height = table._page_dimensions[1]  # (width, height)

        return BBox(
            x0=x0,
            y0=page_height - y1,  # y 좌표 뒤집기
            x1=x1,
            y1=page_height - y0,
        )

    def _extract_text(self, table) -> str:
        """테이블 데이터를 문자열로 추출.

        Args:
            table: camelot Table 객체

        Returns:
            테이블 내 모든 셀 텍스트를 공백으로 연결한 문자열
        """
        df = table.df
        texts = []
        for _, row in df.iterrows():
            for cell in row:
                if cell and str(cell).strip():
                    texts.append(str(cell).strip())
        return " ".join(texts)
