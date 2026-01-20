# TECH_SPEC: Table Detectors

## 1. 개요

본 문서는 PDF에서 표를 탐지하는 Detector 컴포넌트의 스펙을 정의합니다.

현재 구현: **DoclingDetector** (ML 기반 + OCR 지원)

---

## 2. AbstractDetector 인터페이스

모든 탐지기가 구현해야 하는 추상 인터페이스입니다.

```python
from abc import ABC, abstractmethod
from fin_stat_table_detector.models import TableCandidate

class AbstractDetector(ABC):
    """표 탐지기 추상 인터페이스"""

    @property
    @abstractmethod
    def name(self) -> str:
        """
        탐지기 이름

        Returns:
            탐지기 식별자 문자열
        """
        pass

    @abstractmethod
    def detect(
        self,
        pdf_path: str,
        pages: list[int] | None = None
    ) -> list[TableCandidate]:
        """
        PDF에서 표 후보 탐지

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
        pass
```

### 인터페이스 계약

1. `name` 프로퍼티는 고유한 탐지기 식별자를 반환해야 함
2. `detect` 메서드는 반드시 `TableCandidate` 리스트를 반환해야 함
3. 빈 결과도 빈 리스트 `[]`로 반환 (None 반환 금지)
4. 페이지 번호는 1-indexed (첫 페이지 = 1)

---

## 3. DoclingDetector

### 3.1 개요

[Docling](https://docling-project.github.io/docling/)은 IBM Research에서 개발한 AI 기반 문서 파싱 도구입니다.

**강점**:
- ML 레이아웃 모델로 선 없는 표도 정확하게 탐지
- OCR 내장으로 이미지 기반 PDF 지원
- 테이블 구조 인식(Table Structure Recognition) 내장
- pandas DataFrame으로 직접 export 가능

**약점**:
- 첫 실행 시 모델 다운로드 (~2.5분)
- 처리 속도가 rule-based 대비 느림

### 3.2 구현 스펙

```python
from typing import Optional
from fin_stat_table_detector.detectors.base import AbstractDetector
from fin_stat_table_detector.models import TableCandidate, BBox


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
        return "docling"

    def _get_converter(self):
        """Lazy loading - 첫 사용 시에만 모델 로드."""
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
                    "`uv sync` 또는 `pip install docling`으로 설치하세요."
                )
        return self._converter

    def detect(
        self,
        pdf_path: str,
        pages: Optional[list[int]] = None
    ) -> list[TableCandidate]:
        """
        Docling으로 테이블 탐지

        Note: Docling은 전체 문서를 처리하므로 pages 필터는 후처리로 적용
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

            # bbox 추출 (좌표계 정규화)
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

            candidates.append(TableCandidate(
                page=page_no,
                bbox=bbox,
                detector=self.name,
                row_count=row_count,
                col_count=col_count,
                text_content=text_content
            ))

        return candidates
```

### 3.3 OCR 지원

이미지 기반 PDF(텍스트가 이미지로 렌더링된 PDF)를 처리하기 위해 `force_full_page_ocr` 옵션을 사용합니다.

```python
# 기본값: OCR 활성화
detector = DoclingDetector(force_ocr=True)

# 텍스트 기반 PDF만 처리하는 경우 OCR 비활성화 (빠름)
detector = DoclingDetector(force_ocr=False)
```

**OCR이 필요한 경우**:
- 스캔된 PDF
- 텍스트가 작은 이미지로 렌더링된 PDF (증권사 리포트에 흔함)
- pypdf로 텍스트 추출이 안 되는 PDF

### 3.4 Lazy Loading 설계

Docling 모델은 무거우므로 lazy loading 패턴을 사용합니다:
- `__init__`에서 모델을 로드하지 않음
- 첫 `detect()` 호출 시에만 모델 로드
- import 실패 시 명확한 에러 메시지 제공

### 3.5 좌표계 변환

Docling bbox는 `(l, t, r, b)` (left, top, right, bottom) 형식:
- 좌상단 기준 좌표계
- 단위: 포인트(pt)
- 일부 PDF에서 `t > b`인 경우가 있어 min/max로 정규화 필요

```python
# 좌표계 정규화
x0, x1 = min(bbox_data.l, bbox_data.r), max(bbox_data.l, bbox_data.r)
y0, y1 = min(bbox_data.t, bbox_data.b), max(bbox_data.t, bbox_data.b)
```

---

## 4. 테스트 케이스

### 4.1 AbstractDetector 테스트

```python
class TestAbstractDetector:
    """AbstractDetector 인터페이스 테스트"""

    def test_detector_must_have_name(self):
        """탐지기는 name 프로퍼티를 가져야 함"""
        # Given
        detector = DoclingDetector()

        # Then
        assert hasattr(detector, 'name')
        assert isinstance(detector.name, str)
        assert len(detector.name) > 0

    def test_detector_must_implement_detect(self):
        """탐지기는 detect 메서드를 구현해야 함"""
        # Given
        detector = DoclingDetector()

        # Then
        assert hasattr(detector, 'detect')
        assert callable(detector.detect)
```

### 4.2 DoclingDetector 테스트

```python
class TestDoclingDetector:
    """DoclingDetector 테스트"""

    def test_name_is_docling(self):
        """name이 'docling'임"""
        # Given
        detector = DoclingDetector()

        # Then
        assert detector.name == "docling"

    def test_lazy_loading_converter_is_none_initially(self):
        """초기화 시 converter가 None임 (lazy loading)"""
        # Given
        detector = DoclingDetector()

        # Then
        assert detector._converter is None

    def test_force_ocr_default_is_true(self):
        """force_ocr 기본값이 True임"""
        # Given
        detector = DoclingDetector()

        # Then
        assert detector._force_ocr is True

    def test_force_ocr_can_be_disabled(self):
        """force_ocr를 False로 설정 가능"""
        # Given
        detector = DoclingDetector(force_ocr=False)

        # Then
        assert detector._force_ocr is False

    def test_import_error_when_docling_not_installed(self):
        """docling 미설치 시 명확한 에러 메시지"""
        # Given
        detector = DoclingDetector()

        # When / Then
        # docling이 설치되지 않은 환경에서 테스트
        # mock을 사용하여 ImportError 시뮬레이션
        with pytest.raises(ImportError) as exc_info:
            detector._get_converter()

        assert "uv sync" in str(exc_info.value)

    def test_detect_returns_table_candidates(self):
        """detect는 TableCandidate 객체를 반환"""
        # Given
        detector = DoclingDetector()

        # When
        result = detector.detect("sample_with_tables.pdf")

        # Then
        for candidate in result:
            assert isinstance(candidate, TableCandidate)
            assert candidate.detector == "docling"

    def test_pages_filter_applied(self):
        """pages 파라미터로 특정 페이지만 필터링"""
        # Given
        detector = DoclingDetector()

        # When
        result = detector.detect("multi_page.pdf", pages=[1, 3])

        # Then
        for candidate in result:
            assert candidate.page in [1, 3]
```

---

## 5. 구현 파일

- **위치**: `src/fin_stat_table_detector/detectors/`
  - `base.py`: AbstractDetector
  - `docling_det.py`: DoclingDetector
- **의존성**:
  - 필수: docling, opencv-contrib-python-headless
