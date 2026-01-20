"""PdfplumberDetector implementation for table detection using pdfplumber."""

import pdfplumber

from fin_stat_table_detector.detectors.base import AbstractDetector
from fin_stat_table_detector.models import BBox, TableCandidate


class PdfplumberDetector(AbstractDetector):
    """pdfplumber 기반 표 탐지기.

    pdfplumber 라이브러리를 사용하여 PDF에서 표를 탐지합니다.
    선(line)이 있는 표를 정확하게 탐지하는 것이 강점입니다.
    """

    @property
    def name(self) -> str:
        """탐지기 이름.

        Returns:
            'pdfplumber' 문자열
        """
        return "pdfplumber"

    def detect(
        self,
        pdf_path: str,
        pages: list[int] | None = None,
    ) -> list[TableCandidate]:
        """pdfplumber로 표 탐지.

        내부 동작:
        1. PDF 파일 열기
        2. 지정된 페이지(또는 전체)에서 tables 추출
        3. 각 table의 bbox를 TableCandidate로 변환

        Args:
            pdf_path: PDF 파일 경로
            pages: 탐지할 페이지 번호 리스트 (1-indexed).
                   None이면 전체 페이지.

        Returns:
            탐지된 TableCandidate 리스트
        """
        candidates = []

        with pdfplumber.open(pdf_path) as pdf:
            target_pages = pages or range(1, len(pdf.pages) + 1)

            for page_num in target_pages:
                page = pdf.pages[page_num - 1]  # 0-indexed 변환
                tables = page.find_tables()

                for table in tables:
                    bbox = BBox(
                        x0=table.bbox[0],
                        y0=table.bbox[1],
                        x1=table.bbox[2],
                        y1=table.bbox[3],
                    )

                    # 텍스트 추출 시도
                    extracted = table.extract()
                    text_content = self._flatten_table_text(extracted)

                    candidates.append(
                        TableCandidate(
                            page=page_num,
                            bbox=bbox,
                            detector=self.name,
                            row_count=len(extracted) if extracted else None,
                            col_count=(
                                len(extracted[0])
                                if extracted and extracted[0]
                                else None
                            ),
                            text_content=text_content,
                        )
                    )

        return candidates

    def _flatten_table_text(self, table_data: list[list[str | None]] | None) -> str:
        """2D 테이블 데이터를 단일 문자열로 변환.

        Args:
            table_data: 2D 리스트 형태의 테이블 데이터

        Returns:
            공백으로 구분된 단일 문자열
        """
        if not table_data:
            return ""

        texts = []
        for row in table_data:
            for cell in row:
                if cell:
                    texts.append(str(cell).strip())

        return " ".join(texts)
