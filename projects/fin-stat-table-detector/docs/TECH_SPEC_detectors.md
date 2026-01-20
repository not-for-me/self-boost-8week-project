# TECH_SPEC: Table Detectors

## 1. 개요

본 문서는 PDF에서 표를 탐지하는 Detector 컴포넌트들의 스펙을 정의합니다.

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

## 3. PdfplumberDetector

### 3.1 개요

pdfplumber 라이브러리를 사용한 표 탐지기입니다.

**강점**: 선(line)이 있는 표를 정확하게 탐지
**약점**: 선 없는 표는 탐지 불가

### 3.2 구현 스펙

```python
import pdfplumber
from fin_stat_table_detector.detectors.base import AbstractDetector
from fin_stat_table_detector.models import TableCandidate, BBox

class PdfplumberDetector(AbstractDetector):
    """pdfplumber 기반 표 탐지기"""

    @property
    def name(self) -> str:
        return "pdfplumber"

    def detect(
        self,
        pdf_path: str,
        pages: list[int] | None = None
    ) -> list[TableCandidate]:
        """
        pdfplumber로 표 탐지

        내부 동작:
        1. PDF 파일 열기
        2. 지정된 페이지(또는 전체)에서 tables 추출
        3. 각 table의 bbox를 TableCandidate로 변환
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
                        y1=table.bbox[3]
                    )

                    # 텍스트 추출 시도
                    extracted = table.extract()
                    text_content = self._flatten_table_text(extracted)

                    candidates.append(TableCandidate(
                        page=page_num,
                        bbox=bbox,
                        detector=self.name,
                        row_count=len(extracted) if extracted else None,
                        col_count=len(extracted[0]) if extracted and extracted[0] else None,
                        text_content=text_content
                    ))

        return candidates

    def _flatten_table_text(self, table_data: list[list[str | None]]) -> str:
        """2D 테이블 데이터를 단일 문자열로 변환"""
        if not table_data:
            return ""

        texts = []
        for row in table_data:
            for cell in row:
                if cell:
                    texts.append(str(cell).strip())

        return " ".join(texts)
```

### 3.3 pdfplumber 좌표계

pdfplumber의 bbox는 `(x0, y0, x1, y1)` 형태의 튜플:
- 좌상단 기준 좌표계
- 단위: 포인트(pt)

---

## 4. CamelotDetector

### 4.1 개요

camelot-py 라이브러리를 사용한 표 탐지기입니다.

**lattice 모드**: 격자선이 있는 표에 적합
**stream 모드**: 선 없는 표에 적합 (false positive 주의)

### 4.2 구현 스펙

```python
import camelot
from fin_stat_table_detector.detectors.base import AbstractDetector
from fin_stat_table_detector.models import TableCandidate, BBox

class CamelotDetector(AbstractDetector):
    """camelot 기반 표 탐지기"""

    def __init__(self, flavor: str = "lattice"):
        """
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
        return f"camelot_{self._flavor}"

    @property
    def flavor(self) -> str:
        return self._flavor

    def detect(
        self,
        pdf_path: str,
        pages: list[int] | None = None
    ) -> list[TableCandidate]:
        """
        camelot으로 표 탐지

        내부 동작:
        1. camelot.read_pdf()로 테이블 추출
        2. 각 테이블의 bbox와 데이터를 TableCandidate로 변환

        주의: camelot의 좌표계는 좌하단 기준이므로 변환 필요
        """
        candidates = []

        # 페이지 문자열 생성 (camelot 형식)
        pages_str = self._format_pages(pages) if pages else "all"

        tables = camelot.read_pdf(
            pdf_path,
            pages=pages_str,
            flavor=self._flavor
        )

        for table in tables:
            # camelot bbox: (x0, y0, x1, y1) 좌하단 기준
            # 페이지 높이를 알아야 좌상단 기준으로 변환 가능
            bbox = self._convert_bbox(table)

            candidates.append(TableCandidate(
                page=table.page,
                bbox=bbox,
                detector=self.name,
                row_count=table.shape[0],
                col_count=table.shape[1],
                text_content=self._extract_text(table)
            ))

        return candidates

    def _format_pages(self, pages: list[int]) -> str:
        """페이지 리스트를 camelot 형식 문자열로 변환"""
        # 예: [1, 2, 5] -> "1,2,5"
        return ",".join(str(p) for p in pages)

    def _convert_bbox(self, table) -> BBox:
        """
        camelot bbox를 좌상단 기준 BBox로 변환

        camelot은 좌하단 원점, y가 위로 증가
        우리 시스템은 좌상단 원점, y가 아래로 증가
        """
        # table._bbox: (x0, y0, x1, y1) 좌하단 기준
        x0, y0, x1, y1 = table._bbox
        page_height = table._page_dimensions[1]  # (width, height)

        return BBox(
            x0=x0,
            y0=page_height - y1,  # y 좌표 뒤집기
            x1=x1,
            y1=page_height - y0
        )

    def _extract_text(self, table) -> str:
        """테이블 데이터를 문자열로 추출"""
        df = table.df
        texts = []
        for _, row in df.iterrows():
            for cell in row:
                if cell and str(cell).strip():
                    texts.append(str(cell).strip())
        return " ".join(texts)
```

### 4.3 좌표계 변환

camelot은 PDF의 원래 좌표계(좌하단 원점)를 사용합니다:

```
camelot 좌표계:              우리 시스템 좌표계:
  y ▲                            (0,0) ────► x
    │                              │
    │    ┌───┐                     │  ┌───┐
    │    │   │                     │  │   │
    └────┴───┴──► x                ▼  └───┘
  (0,0)                            y
```

변환 공식:
```python
new_y0 = page_height - old_y1
new_y1 = page_height - old_y0
```

---

## 5. DoclingDetector

### 5.1 개요

[Docling](https://docling-project.github.io/docling/)은 IBM Research에서 개발한 AI 기반 문서 파싱 도구입니다.

**강점**: ML 레이아웃 모델로 선 없는 표도 정확하게 탐지
**약점**: 무거움 (첫 실행 시 모델 다운로드), 느림

### 5.2 구현 스펙

```python
from typing import Optional
from fin_stat_table_detector.detectors.base import AbstractDetector
from fin_stat_table_detector.models import TableCandidate, BBox

class DoclingDetector(AbstractDetector):
    """Docling(IBM) ML 기반 테이블 탐지기"""

    def __init__(self):
        self._converter = None  # lazy loading

    @property
    def name(self) -> str:
        return "docling"

    def _get_converter(self):
        """Lazy loading - 첫 사용 시에만 모델 로드"""
        if self._converter is None:
            try:
                from docling.document_converter import DocumentConverter
                self._converter = DocumentConverter()
            except ImportError:
                raise ImportError(
                    "docling이 설치되지 않았습니다. "
                    "`uv sync --extra ml` 또는 `pip install docling`으로 설치하세요."
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

        candidates = []

        for table in result.document.tables:
            # bbox와 페이지 정보 추출
            if not table.prov:
                continue

            prov = table.prov[0]
            page_no = prov.page_no  # 1-indexed

            # pages 필터 적용
            if pages is not None and page_no not in pages:
                continue

            # bbox 추출 (docling은 (l, t, r, b) 형식)
            bbox_data = prov.bbox
            bbox = BBox(
                x0=bbox_data.l,
                y0=bbox_data.t,
                x1=bbox_data.r,
                y1=bbox_data.b
            )

            # DataFrame으로 텍스트 추출
            try:
                df = table.export_to_dataframe()
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

### 5.3 Lazy Loading 설계

Docling 모델은 무거우므로 lazy loading 패턴을 사용합니다:
- `__init__`에서 모델을 로드하지 않음
- 첫 `detect()` 호출 시에만 모델 로드
- optional dependency이므로 import 실패 시 명확한 에러 메시지 제공

### 5.4 Docling bbox 형식

Docling은 `(l, t, r, b)` (left, top, right, bottom) 형식을 사용:
- 좌상단 기준 좌표계 (변환 불필요)
- 단위: 포인트(pt)

---

## 6. 탐지기 비교 테이블

| 특성 | PdfplumberDetector | CamelotDetector (lattice) | CamelotDetector (stream) | DoclingDetector |
|------|-------------------|---------------------------|--------------------------|-----------------|
| 선 있는 표 | ✅ 정확 | ✅ 정확 | ⚠️ 가능하나 정확도 낮음 | ✅ 정확 |
| 선 없는 표 | ❌ 불가 | ❌ 불가 | ✅ 가능 | ✅ 매우 정확 |
| False Positive | 낮음 | 낮음 | 높음 | 낮음 |
| 속도 | 빠름 | 느림 | 느림 | 매우 느림 |
| 의존성 | pdfplumber | ghostscript 필요 | ghostscript 필요 | docling (optional) |
| 첫 실행 | 즉시 | 즉시 | 즉시 | 모델 다운로드 (~2.5분) |

---

## 7. 테스트 케이스

### 7.1 AbstractDetector 테스트

```python
class TestAbstractDetector:
    """AbstractDetector 인터페이스 테스트"""

    def test_detector_must_have_name(self):
        """탐지기는 name 프로퍼티를 가져야 함"""
        # Given
        detector = PdfplumberDetector()

        # Then
        assert hasattr(detector, 'name')
        assert isinstance(detector.name, str)
        assert len(detector.name) > 0

    def test_detector_must_implement_detect(self):
        """탐지기는 detect 메서드를 구현해야 함"""
        # Given
        detector = PdfplumberDetector()

        # Then
        assert hasattr(detector, 'detect')
        assert callable(detector.detect)
```

### 7.2 PdfplumberDetector 테스트

```python
class TestPdfplumberDetector:
    """PdfplumberDetector 테스트"""

    def test_name_is_pdfplumber(self):
        """name이 'pdfplumber'임"""
        # Given
        detector = PdfplumberDetector()

        # Then
        assert detector.name == "pdfplumber"

    def test_detect_returns_list(self):
        """detect는 리스트를 반환"""
        # Given
        detector = PdfplumberDetector()

        # When
        result = detector.detect("sample.pdf")

        # Then
        assert isinstance(result, list)

    def test_detect_returns_table_candidates(self):
        """detect는 TableCandidate 객체를 반환"""
        # Given
        detector = PdfplumberDetector()

        # When
        result = detector.detect("sample_with_tables.pdf")

        # Then
        for candidate in result:
            assert isinstance(candidate, TableCandidate)
            assert candidate.detector == "pdfplumber"
```

### 7.3 CamelotDetector 테스트

```python
class TestCamelotDetector:
    """CamelotDetector 테스트"""

    def test_lattice_name(self):
        """lattice 모드 name이 'camelot_lattice'임"""
        # Given
        detector = CamelotDetector(flavor="lattice")

        # Then
        assert detector.name == "camelot_lattice"

    def test_stream_name(self):
        """stream 모드 name이 'camelot_stream'임"""
        # Given
        detector = CamelotDetector(flavor="stream")

        # Then
        assert detector.name == "camelot_stream"

    def test_invalid_flavor_raises_error(self):
        """잘못된 flavor 값은 ValueError 발생"""
        # When / Then
        with pytest.raises(ValueError):
            CamelotDetector(flavor="invalid")

    def test_bbox_coordinate_conversion(self):
        """좌표계 변환이 올바르게 동작함"""
        # Given
        detector = CamelotDetector(flavor="lattice")
        # camelot bbox (좌하단 기준): x0=100, y0=200, x1=400, y1=500
        # page_height = 800
        # 예상 결과 (좌상단 기준): x0=100, y0=300, x1=400, y1=600

        # 실제 테스트는 mock 또는 fixture 필요
```

### 7.4 DoclingDetector 테스트

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

    def test_import_error_when_docling_not_installed(self):
        """docling 미설치 시 명확한 에러 메시지"""
        # Given
        detector = DoclingDetector()

        # When / Then
        # docling이 설치되지 않은 환경에서 테스트
        # mock을 사용하여 ImportError 시뮬레이션
        with pytest.raises(ImportError) as exc_info:
            # docling import를 실패하도록 mock
            detector._get_converter()

        assert "uv sync --extra ml" in str(exc_info.value)

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

## 8. 구현 파일

- **위치**: `src/fin_stat_table_detector/detectors/`
  - `base.py`: AbstractDetector
  - `pdfplumber_det.py`: PdfplumberDetector
  - `camelot_det.py`: CamelotDetector
  - `docling_det.py`: DoclingDetector
- **의존성**:
  - 필수: pdfplumber, camelot-py, ghostscript
  - Optional (ML): docling (`uv sync --extra ml`)
