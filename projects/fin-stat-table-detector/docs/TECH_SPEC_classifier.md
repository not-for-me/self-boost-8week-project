# TECH_SPEC: Financial Table Classifier

## 1. 개요

본 문서는 탐지된 표 후보(TableCandidate)가 재무제표인지 분류하는 FinancialTableClassifier의 스펙을 정의합니다.

---

## 2. 분류 기준

재무제표 테이블은 다음 4가지 기준으로 분류합니다:

| 기준 | 설명 | 필수 여부 |
|------|------|----------|
| 키워드 매칭 | 재무제표 특화 키워드 존재 | 필수 |
| 숫자 밀도 | 텍스트 내 숫자 비율 20% 이상 | 필수 |
| 시계열 컬럼 | 연도/분기 패턴 2개 이상 | 권장 |
| 표 크기 | 최소 3행 2열, 페이지 5~95% | 필수 |

---

## 3. 재무제표 키워드 사전

OCR 결과의 변형을 고려하여 다양한 형태의 키워드를 포함합니다.

```python
FINANCIAL_STATEMENT_PATTERNS = {
    # 손익계산서 (Income Statement)
    "income_statement": {
        "keywords": [
            "매출액", "매출원가", "매출총이익", "영업이익", "영업외손익",
            "세전순이익", "법인세", "당기순이익", "지배주주순이익", "순이익"
        ],
        "weight": 1.0,
        "min_matches": 2
    },
    # 재무상태표 (Balance Sheet)
    "balance_sheet": {
        "keywords": [
            "자산총계", "부채총계", "자본총계", "유동자산", "비유동자산",
            "유동부채", "비유동부채", "이익잉여금", "자본금"
        ],
        "weight": 1.0,
        "min_matches": 2
    },
    # 현금흐름표 (Cash Flow)
    "cash_flow": {
        "keywords": [
            "영업활동", "투자활동", "재무활동", "현금흐름", "현금증감",
            "FCF", "CAPEX"
        ],
        "weight": 1.0,
        "min_matches": 2
    },
    # 투자지표 (Valuation Metrics)
    "valuation": {
        "keywords": [
            "EPS", "BPS", "CFPS",       # Per Share 지표
            "PER", "PBR", "PCR",         # 배수 지표 (한글 약어)
            "P/E", "P/B", "P/CF",        # 배수 지표 (OCR 변형)
            "ROE", "ROA", "ROIC",        # 수익성 지표
            "EBITDA", "EV/EBITDA", "EV/EBIT",  # EV 관련
            "배당수익률", "DPS"
        ],
        "weight": 0.8,  # 단독으로는 재무제표가 아닐 수 있음
        "min_matches": 3
    },
    # 실적 추이 (Performance Trend) - 보조 지표
    "performance": {
        "keywords": [
            "YoY", "QoQ", "전년비", "성장률", "증감률", "전분기비"
        ],
        "weight": 0.5,
        "min_matches": 2
    }
}
```

### 카테고리별 특징

| 카테고리 | weight | min_matches | 특징 |
|----------|--------|-------------|------|
| income_statement | 1.0 | 2 | 핵심 재무제표 |
| balance_sheet | 1.0 | 2 | 핵심 재무제표 |
| cash_flow | 1.0 | 2 | 핵심 재무제표 |
| valuation | 0.8 | 3 | 투자지표만으로는 약한 신호 |
| performance | 0.5 | 2 | 보조 지표 |

### OCR 변형 처리

증권사 리포트의 OCR 결과에서 흔히 나타나는 변형을 처리하기 위해 다양한 형태의 키워드를 포함합니다:

| 원래 형태 | OCR 변형 | 둘 다 포함 |
|----------|---------|-----------|
| PER | P/E, P/E(x) | ✓ |
| PBR | P/B, P/B(x) | ✓ |
| PCR | P/CF | ✓ |
| CFPS | Cash Flow Per Share | CFPS만 |

---

## 4. 시계열 패턴

연도/분기 컬럼을 탐지하기 위한 정규표현식 패턴입니다.

```python
TEMPORAL_PATTERNS = [
    r'20\d{2}[EFef]?',        # 2024, 2025E, 2025F, 2025e
    r'[1-4][Qq]\d{2}',        # 1Q24, 3Q25, 1q24
    r'\d{1,2}[분반]기',        # 1분기, 상반기
    r'FY\d{2,4}',             # FY24, FY2024
    r'\d{4}년',               # 2024년
]
```

### 패턴 설명

| 패턴 | 매칭 예시 |
|------|----------|
| `20\d{2}[EFef]?` | 2024, 2025E, 2025F |
| `[1-4][Qq]\d{2}` | 1Q24, 3Q25, 2q24 |
| `\d{1,2}[분반]기` | 1분기, 2분기, 상반기 |
| `FY\d{2,4}` | FY24, FY2024 |
| `\d{4}년` | 2024년, 2025년 |

---

## 5. FinancialTableClassifier 구현 스펙

```python
import re
from fin_stat_table_detector.models import TableCandidate, FinancialTable, BBox

class FinancialTableClassifier:
    """재무제표 테이블 분류기"""

    def __init__(
        self,
        numeric_density_threshold: float = 0.2,
        min_temporal_matches: int = 2,
        min_confidence: float = 0.3
    ):
        """
        Args:
            numeric_density_threshold: 숫자 밀도 임계값 (기본 20%)
            min_temporal_matches: 최소 시계열 패턴 매칭 수
            min_confidence: 최소 신뢰도 임계값
        """
        self.numeric_density_threshold = numeric_density_threshold
        self.min_temporal_matches = min_temporal_matches
        self.min_confidence = min_confidence

    def classify(
        self,
        candidate: TableCandidate,
        pdf_path: str | None = None,
        page_width: float | None = None,
        page_height: float | None = None
    ) -> FinancialTable | None:
        """
        표 후보가 재무제표인지 분류

        Args:
            candidate: 분류할 TableCandidate
            pdf_path: PDF 경로 (text_content가 없을 때 추출용)
            page_width: 페이지 너비 (크기 검증용)
            page_height: 페이지 높이 (크기 검증용)

        Returns:
            재무제표이면 FinancialTable, 아니면 None
        """
        # 텍스트 가져오기
        text = candidate.text_content
        if not text and pdf_path:
            text = self._extract_text_from_bbox(
                pdf_path, candidate.page, candidate.bbox
            )

        if not text:
            return None

        # 1. 표 크기 유효성 검증
        if page_width and page_height:
            if not self._is_valid_table_size(
                candidate.bbox,
                page_width,
                page_height,
                candidate.row_count,
                candidate.col_count
            ):
                return None

        # 2. 키워드 매칭
        category, keyword_score, matched_keywords = self._calculate_keyword_score(text)
        if category is None:
            return None

        # 3. 숫자 밀도 체크
        if not self._check_numeric_density(text):
            return None

        # 4. 시계열 컬럼 체크 (보너스 점수)
        has_temporal = self._check_temporal_columns(text)

        # 5. 최종 신뢰도 계산
        confidence = self._calculate_final_confidence(
            keyword_score,
            has_temporal
        )

        if confidence < self.min_confidence:
            return None

        return FinancialTable(
            page=candidate.page,
            bbox=candidate.bbox,
            category=category,
            confidence=confidence,
            matched_keywords=matched_keywords,
            detector_source=candidate.detector
        )

    def _extract_text_from_bbox(
        self,
        pdf_path: str,
        page: int,
        bbox: BBox
    ) -> str:
        """bbox 영역의 텍스트 추출 (pypdf 사용)

        Note: pypdf는 bbox 기반 추출을 지원하지 않으므로
        전체 페이지 텍스트를 반환합니다. 키워드 매칭은
        텍스트 내 패턴 검색으로 동작합니다.
        """
        from pypdf import PdfReader

        reader = PdfReader(pdf_path)
        page_obj = reader.pages[page - 1]
        text = page_obj.extract_text() or ""

        return text
```

---

## 6. 분류 플로우차트

```
┌─────────────────────────────────────────┐
│           TableCandidate 입력            │
└────────────────────┬────────────────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │   텍스트 존재 여부 확인   │
        └────────────┬───────────┘
                     │
            ┌────────┴────────┐
            │                 │
        텍스트 있음         텍스트 없음
            │                 │
            │         ┌───────▼───────┐
            │         │  PDF에서 추출  │
            │         │  (pypdf)      │
            │         └───────┬───────┘
            │                 │
            └────────┬────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │   표 크기 유효성 검증    │──── 실패 ──► None
        └────────────┬───────────┘
                     │ 통과
                     ▼
        ┌────────────────────────┐
        │    키워드 매칭 분석     │──── 실패 ──► None
        │ (카테고리, 점수, 키워드) │
        └────────────┬───────────┘
                     │ 통과
                     ▼
        ┌────────────────────────┐
        │   숫자 밀도 체크 (≥20%) │──── 실패 ──► None
        └────────────┬───────────┘
                     │ 통과
                     ▼
        ┌────────────────────────┐
        │  시계열 패턴 체크 (보너스)│
        └────────────┬───────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │   최종 신뢰도 계산      │──── < 0.3 ──► None
        └────────────┬───────────┘
                     │ ≥ 0.3
                     ▼
        ┌────────────────────────┐
        │    FinancialTable 반환  │
        └─────────────────────────┘
```

---

## 7. 테스트 케이스

### 7.1 키워드 매칭 테스트

```python
class TestKeywordMatching:
    """키워드 매칭 테스트"""

    def test_income_statement_detection(self):
        """손익계산서 키워드가 있으면 income_statement로 분류"""
        # Given
        text = "매출액 1,234 영업이익 567 당기순이익 890 2024 2025E"
        classifier = FinancialTableClassifier()

        # When
        category, confidence, keywords = classifier._calculate_keyword_score(text)

        # Then
        assert category == "income_statement"
        assert confidence > 0.5
        assert "매출액" in keywords
        assert "영업이익" in keywords

    def test_valuation_with_ocr_variants(self):
        """OCR 변형 키워드도 인식"""
        # Given
        text = "P/E 10.5 P/B 1.2 ROE 15% EPS 1,234"
        classifier = FinancialTableClassifier()

        # When
        category, confidence, keywords = classifier._calculate_keyword_score(text)

        # Then
        assert category == "valuation"
        assert "P/E" in keywords
        assert "P/B" in keywords
        assert "ROE" in keywords
        assert "EPS" in keywords

    def test_no_match_returns_none(self):
        """매칭 키워드가 부족하면 None 반환"""
        # Given
        text = "이것은 일반 텍스트입니다 매출액만 하나"  # 1개만 매칭
        classifier = FinancialTableClassifier()

        # When
        category, _, _ = classifier._calculate_keyword_score(text)

        # Then
        assert category is None
```

### 7.2 숫자 밀도 테스트

```python
class TestNumericDensity:
    """숫자 밀도 테스트"""

    def test_numeric_density_pass(self):
        """숫자 비율 20% 이상이면 통과"""
        # Given
        text = "매출액 1,234 567 890 123 456"  # 5/6 = 83% 숫자
        classifier = FinancialTableClassifier()

        # When
        result = classifier._check_numeric_density(text)

        # Then
        assert result is True

    def test_numeric_density_fail(self):
        """숫자 비율 20% 미만이면 실패"""
        # Given
        text = "이것은 설명 텍스트입니다 숫자가 거의 없음 123"  # 1/9 ≈ 11%
        classifier = FinancialTableClassifier()

        # When
        result = classifier._check_numeric_density(text)

        # Then
        assert result is False
```

### 7.3 시계열 패턴 테스트

```python
class TestTemporalPatterns:
    """시계열 패턴 테스트"""

    def test_temporal_columns_detected(self):
        """시계열 패턴 2개 이상이면 True"""
        # Given
        text = "항목 2024 2025E 1Q25 2Q25"
        classifier = FinancialTableClassifier()

        # When
        result = classifier._check_temporal_columns(text)

        # Then
        assert result is True

    def test_korean_quarter_pattern(self):
        """한국어 분기 패턴 인식"""
        # Given
        text = "1분기 2분기 3분기"
        classifier = FinancialTableClassifier()

        # When
        result = classifier._check_temporal_columns(text)

        # Then
        assert result is True
```

---

## 8. 구현 파일

- **위치**: `src/fin_stat_table_detector/classifiers/`
  - `constants.py`: 키워드, 패턴 상수
  - `financial.py`: FinancialTableClassifier
- **의존성**: pypdf (텍스트 추출용), re (정규표현식)
