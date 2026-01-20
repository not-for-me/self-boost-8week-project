"""DoclingDetector implementation for table detection using Docling (IBM).

Docling is an ML-based document understanding library from IBM that can
detect and extract tables from PDF documents.
"""

from typing import Optional

from fin_stat_table_detector.detectors.base import AbstractDetector
from fin_stat_table_detector.models import BBox, TableCandidate


class DoclingDetector(AbstractDetector):
    """Docling(IBM) ML 기반 테이블 탐지기.

    Docling 라이브러리를 사용하여 PDF에서 표를 탐지합니다.
    ML 기반으로 복잡한 레이아웃에서도 테이블을 정확하게 인식합니다.

    Attributes:
        _converter: DocumentConverter 인스턴스 (lazy loading)
        force_ocr: 전체 페이지 OCR 강제 적용 여부 (이미지 기반 PDF용)
    """

    def __init__(self, force_ocr: bool = True):
        """DoclingDetector 초기화.

        Args:
            force_ocr: 전체 페이지 OCR 강제 적용 여부 (기본값: True).
                      이미지 기반 PDF나 스캔된 문서에서 텍스트 추출에 필요.

        _converter는 lazy loading으로 첫 detect() 호출 시 초기화됩니다.
        """
        self._converter = None  # lazy loading
        self._force_ocr = force_ocr

    @property
    def name(self) -> str:
        """탐지기 이름.

        Returns:
            'docling' 문자열
        """
        return "docling"

    def _get_converter(self):
        """Lazy loading - 첫 사용 시에만 모델 로드.

        Returns:
            DocumentConverter 인스턴스

        Raises:
            ImportError: docling이 설치되지 않았을 때
        """
        if self._converter is None:
            try:
                from docling.document_converter import DocumentConverter, PdfFormatOption
                from docling.datamodel.pipeline_options import (
                    OcrAutoOptions,
                    PdfPipelineOptions,
                )

                pipeline_options = PdfPipelineOptions(
                    do_ocr=True,
                    ocr_options=OcrAutoOptions(force_full_page_ocr=self._force_ocr),
                )
                self._converter = DocumentConverter(
                    format_options={
                        "pdf": PdfFormatOption(pipeline_options=pipeline_options),
                    }
                )
            except ImportError:
                raise ImportError(
                    "docling이 설치되지 않았습니다. "
                    "`uv sync --extra ml` 또는 `pip install docling`으로 설치하세요."
                )
        return self._converter

    def detect(
        self,
        pdf_path: str,
        pages: Optional[list[int]] = None,
    ) -> list[TableCandidate]:
        """Docling으로 표 탐지.

        Note: Docling은 전체 문서를 처리하므로 pages 필터는 후처리로 적용

        Args:
            pdf_path: PDF 파일 경로
            pages: 탐지할 페이지 번호 리스트 (1-indexed).
                   None이면 전체 페이지.

        Returns:
            탐지된 TableCandidate 리스트
        """
        converter = self._get_converter()
        result = converter.convert(pdf_path)
        doc = result.document

        candidates = []

        for table in doc.tables:
            # bbox와 페이지 정보 추출
            if not table.prov:
                continue

            prov = table.prov[0]
            page_no = prov.page_no  # 1-indexed

            # pages 필터 적용
            if pages is not None and page_no not in pages:
                continue

            # bbox 추출 (docling은 (l, t, r, b) 형식)
            # 좌표계에 따라 t > b인 경우가 있으므로 정규화 필요
            bbox_data = prov.bbox
            x0, x1 = min(bbox_data.l, bbox_data.r), max(bbox_data.l, bbox_data.r)
            y0, y1 = min(bbox_data.t, bbox_data.b), max(bbox_data.t, bbox_data.b)

            # 유효하지 않은 bbox 건너뛰기
            if x0 >= x1 or y0 >= y1:
                continue

            bbox = BBox(x0=x0, y0=y0, x1=x1, y1=y1)

            # DataFrame으로 텍스트 추출
            try:
                df = table.export_to_dataframe(doc=doc)
                text_content = df.to_string()
                row_count = len(df)
                col_count = len(df.columns)
            except Exception:
                text_content = None
                row_count = None
                col_count = None

            candidates.append(
                TableCandidate(
                    page=page_no,
                    bbox=bbox,
                    detector=self.name,
                    row_count=row_count,
                    col_count=col_count,
                    text_content=text_content,
                )
            )

        return candidates
