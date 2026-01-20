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

```python
FINANCIAL_STATEMENT_PATTERNS = {
    # 손익계산서 (Income Statement)
    "income_statement": {
        "keywords": [
            "매출액", "매출원가", "매출총이익", "영업이익", "영업외손익",
            "세전이익", "법인세", "당기순이익", "지배주주순이익", "순이익"
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
            "EPS", "BPS", "PER", "PBR", "ROE", "ROA", "EBITDA",
            "EV/EBITDA", "배당수익률", "DPS"
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

    def _calculate_keyword_score(
        self,
        text: str
    ) -> tuple[str | None, float, list[str]]:
        """
        키워드 매칭 점수 계산

        Returns:
            (best_category, confidence, matched_keywords)
        """
        scores = {}
        all_matched = {}

        for category, config in FINANCIAL_STATEMENT_PATTERNS.items():
            matched = [kw for kw in config["keywords"] if kw in text]
            if len(matched) >= config["min_matches"]:
                scores[category] = len(matched) * config["weight"]
                all_matched[category] = matched

        if not scores:
            return None, 0.0, []

        best_category = max(scores, key=scores.get)
        # confidence: 매칭 키워드 수에 따라 0.0 ~ 1.0
        confidence = min(scores[best_category] / 6.0, 1.0)

        return best_category, confidence, all_matched[best_category]

    def _check_numeric_density(
        self,
        text: str,
        threshold: float | None = None
    ) -> bool:
        """
        텍스트 내 숫자 토큰 비율 계산
        재무제표는 보통 20% 이상이 숫자
        """
        threshold = threshold or self.numeric_density_threshold

        tokens = text.split()
        if not tokens:
            return False

        numeric_pattern = r'^[\d,.\-+()%]+$'
        numeric_count = sum(1 for t in tokens if re.match(numeric_pattern, t))

        return (numeric_count / len(tokens)) >= threshold

    def _check_temporal_columns(
        self,
        text: str,
        min_matches: int | None = None
    ) -> bool:
        """
        연도/분기 패턴이 지정된 개수 이상 있는지 확인
        """
        min_matches = min_matches or self.min_temporal_matches
        total_matches = 0

        for pattern in TEMPORAL_PATTERNS:
            matches = re.findall(pattern, text)
            total_matches += len(set(matches))  # 중복 제거

        return total_matches >= min_matches

    def _is_valid_table_size(
        self,
        bbox: BBox,
        page_width: float,
        page_height: float,
        row_count: int | None,
        col_count: int | None,
        min_area_ratio: float = 0.05,
        max_area_ratio: float = 0.95
    ) -> bool:
        """
        표 크기가 유효한지 확인
        - 최소 3행 2열
        - 페이지의 5% ~ 95% 크기
        """
        # 행/열 수 체크
        if row_count is not None and row_count < 3:
            return False
        if col_count is not None and col_count < 2:
            return False

        # 면적 비율 체크
        page_area = page_width * page_height
        table_area = bbox.area
        ratio = table_area / page_area

        return min_area_ratio <= ratio <= max_area_ratio

    def _calculate_final_confidence(
        self,
        keyword_score: float,
        has_temporal: bool
    ) -> float:
        """최종 신뢰도 계산"""
        confidence = keyword_score

        # 시계열 컬럼이 있으면 보너스
        if has_temporal:
            confidence = min(confidence + 0.1, 1.0)

        return confidence

    def _extract_text_from_bbox(
        self,
        pdf_path: str,
        page: int,
        bbox: BBox
    ) -> str:
        """bbox 영역의 텍스트 추출"""
        import pdfplumber

        with pdfplumber.open(pdf_path) as pdf:
            page_obj = pdf.pages[page - 1]
            cropped = page_obj.within_bbox((bbox.x0, bbox.y0, bbox.x1, bbox.y1))
            text = cropped.extract_text() or ""

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

    def test_balance_sheet_detection(self):
        """재무상태표 키워드가 있으면 balance_sheet로 분류"""
        # Given
        text = "자산총계 10,000 부채총계 5,000 자본총계 5,000"
        classifier = FinancialTableClassifier()

        # When
        category, _, keywords = classifier._calculate_keyword_score(text)

        # Then
        assert category == "balance_sheet"
        assert "자산총계" in keywords

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

    def test_empty_text_returns_false(self):
        """빈 텍스트는 False 반환"""
        # Given
        classifier = FinancialTableClassifier()

        # When
        result = classifier._check_numeric_density("")

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

    def test_single_temporal_not_enough(self):
        """시계열 패턴 1개는 부족"""
        # Given
        text = "항목 2024"
        classifier = FinancialTableClassifier()

        # When
        result = classifier._check_temporal_columns(text)

        # Then
        assert result is False

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

### 7.4 표 크기 테스트

```python
class TestTableSize:
    """표 크기 유효성 테스트"""

    def test_valid_table_size(self):
        """유효한 크기의 표는 통과"""
        # Given
        bbox = BBox(50, 100, 500, 400)  # 면적: 450 * 300 = 135,000
        classifier = FinancialTableClassifier()

        # When
        result = classifier._is_valid_table_size(
            bbox,
            page_width=600,
            page_height=800,
            row_count=10,
            col_count=5
        )

        # Then
        assert result is True  # 135,000 / 480,000 = 28%

    def test_too_small_table_fails(self):
        """너무 작은 표는 실패 (5% 미만)"""
        # Given
        bbox = BBox(0, 0, 50, 50)  # 면적: 2,500
        classifier = FinancialTableClassifier()

        # When
        result = classifier._is_valid_table_size(
            bbox,
            page_width=600,
            page_height=800,
            row_count=10,
            col_count=5
        )

        # Then
        assert result is False  # 2,500 / 480,000 = 0.5%

    def test_too_few_rows_fails(self):
        """행이 3개 미만이면 실패"""
        # Given
        bbox = BBox(50, 100, 500, 400)
        classifier = FinancialTableClassifier()

        # When
        result = classifier._is_valid_table_size(
            bbox,
            page_width=600,
            page_height=800,
            row_count=2,  # 2행
            col_count=5
        )

        # Then
        assert result is False
```

---

## 8. 구현 파일

- **위치**: `src/fin_stat_table_detector/classifiers/financial.py`
- **상수 파일**: `src/fin_stat_table_detector/classifiers/constants.py` (키워드, 패턴 분리 가능)
- **의존성**: pdfplumber (텍스트 추출용), re (정규표현식)
