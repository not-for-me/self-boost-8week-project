# TECH_SPEC: Data Models

## 1. 개요

본 문서는 재무제표 테이블 탐지 시스템에서 사용되는 핵심 데이터 모델을 정의합니다.

---

## 2. 데이터 모델 정의

### 2.1 BBox (Bounding Box)

PDF 내 영역의 좌표를 나타내는 클래스입니다.

```python
from dataclasses import dataclass

@dataclass
class BBox:
    """
    좌표 (PDF 좌표계: 좌상단 기준)

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
        """영역의 너비"""
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        """영역의 높이"""
        return self.y1 - self.y0

    @property
    def area(self) -> float:
        """영역의 면적"""
        return self.width * self.height
```

#### 좌표계 설명

- PDF 좌표계는 **좌상단이 원점 (0, 0)**
- x 값은 오른쪽으로 증가
- y 값은 아래쪽으로 증가
- 모든 좌표는 포인트(pt) 단위 (1pt = 1/72 inch)

```
(0, 0) ────────────────► x
  │
  │    ┌───────────┐
  │    │  (x0,y0)  │
  │    │           │
  │    │  (x1,y1)  │
  │    └───────────┘
  ▼
  y
```

### 2.2 TableCandidate

탐지기가 찾아낸 표 후보를 나타내는 클래스입니다.

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class TableCandidate:
    """
    탐지된 표 후보

    Attributes:
        page: 페이지 번호 (1-indexed)
        bbox: 표의 위치 좌표
        detector: 탐지기 이름 ("pdfplumber", "camelot_lattice", "camelot_stream")
        row_count: 행 개수 (선택)
        col_count: 열 개수 (선택)
        text_content: 표 내 텍스트 (선택)
    """
    page: int
    bbox: BBox
    detector: str
    row_count: Optional[int] = None
    col_count: Optional[int] = None
    text_content: Optional[str] = None
```

#### detector 값 종류

| 값 | 설명 |
|----|------|
| `"pdfplumber"` | pdfplumber 라이브러리로 탐지 |
| `"camelot_lattice"` | camelot lattice 모드로 탐지 |
| `"camelot_stream"` | camelot stream 모드로 탐지 |

### 2.3 FinancialTable

재무제표로 분류된 최종 결과를 나타내는 클래스입니다.

```python
from dataclasses import dataclass

@dataclass
class FinancialTable:
    """
    재무제표로 분류된 표

    Attributes:
        page: 페이지 번호 (1-indexed)
        bbox: 표의 위치 좌표
        category: 재무제표 카테고리
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
```

#### category 값 종류

| 값 | 설명 |
|----|------|
| `"income_statement"` | 손익계산서 |
| `"balance_sheet"` | 재무상태표 |
| `"cash_flow"` | 현금흐름표 |
| `"valuation"` | 투자지표 |
| `"performance"` | 실적 추이 (보조 지표) |

---

## 3. 모델 관계도

```
┌──────────────────┐
│  TableCandidate  │
│                  │
│  - page: int     │
│  - bbox: BBox ───┼───────┐
│  - detector: str │       │
│  - row_count     │       │
│  - col_count     │       │
│  - text_content  │       │
└────────┬─────────┘       │
         │                 │
         │ 분류 후          │
         ▼                 │
┌──────────────────┐       │
│  FinancialTable  │       │
│                  │       │
│  - page: int     │       │
│  - bbox: BBox ───┼───────┤
│  - category: str │       │
│  - confidence    │       │
│  - matched_kw    │       │
│  - detector_src  │       │
└──────────────────┘       │
                           │
         ┌─────────────────┘
         │
         ▼
    ┌─────────────┐
    │    BBox     │
    │             │
    │  - x0, y0   │
    │  - x1, y1   │
    │  + width    │
    │  + height   │
    │  + area     │
    └─────────────┘
```

---

## 4. 테스트 케이스

### 4.1 BBox 테스트

```python
class TestBBox:
    """BBox 데이터 모델 테스트"""

    def test_width_calculation(self):
        """너비가 올바르게 계산됨"""
        # Given
        bbox = BBox(x0=10, y0=20, x1=110, y1=70)

        # When
        width = bbox.width

        # Then
        assert width == 100

    def test_height_calculation(self):
        """높이가 올바르게 계산됨"""
        # Given
        bbox = BBox(x0=10, y0=20, x1=110, y1=70)

        # When
        height = bbox.height

        # Then
        assert height == 50

    def test_area_calculation(self):
        """면적이 올바르게 계산됨"""
        # Given
        bbox = BBox(x0=10, y0=20, x1=110, y1=70)

        # When
        area = bbox.area

        # Then
        assert area == 5000  # 100 * 50

    def test_zero_area_bbox(self):
        """너비나 높이가 0인 경우 면적도 0"""
        # Given
        bbox = BBox(x0=10, y0=20, x1=10, y1=70)  # 너비 0

        # When
        area = bbox.area

        # Then
        assert area == 0
```

### 4.2 TableCandidate 테스트

```python
class TestTableCandidate:
    """TableCandidate 데이터 모델 테스트"""

    def test_create_with_required_fields(self):
        """필수 필드만으로 생성 가능"""
        # Given / When
        candidate = TableCandidate(
            page=1,
            bbox=BBox(0, 0, 100, 100),
            detector="pdfplumber"
        )

        # Then
        assert candidate.page == 1
        assert candidate.detector == "pdfplumber"
        assert candidate.row_count is None
        assert candidate.col_count is None
        assert candidate.text_content is None

    def test_create_with_all_fields(self):
        """모든 필드를 포함하여 생성 가능"""
        # Given / When
        candidate = TableCandidate(
            page=2,
            bbox=BBox(50, 100, 400, 300),
            detector="camelot_lattice",
            row_count=10,
            col_count=5,
            text_content="매출액 1,234"
        )

        # Then
        assert candidate.row_count == 10
        assert candidate.col_count == 5
        assert candidate.text_content == "매출액 1,234"
```

### 4.3 FinancialTable 테스트

```python
class TestFinancialTable:
    """FinancialTable 데이터 모델 테스트"""

    def test_create_financial_table(self):
        """FinancialTable 생성 테스트"""
        # Given / When
        table = FinancialTable(
            page=3,
            bbox=BBox(50, 100, 500, 400),
            category="income_statement",
            confidence=0.85,
            matched_keywords=["매출액", "영업이익", "당기순이익"],
            detector_source="pdfplumber"
        )

        # Then
        assert table.page == 3
        assert table.category == "income_statement"
        assert table.confidence == 0.85
        assert len(table.matched_keywords) == 3
        assert "매출액" in table.matched_keywords
```

---

## 5. 구현 파일

- **위치**: `src/fin_stat_table_detector/models.py`
- **의존성**: Python 3.12+ (dataclasses 내장)
