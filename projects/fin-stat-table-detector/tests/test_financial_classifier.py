"""Tests for FinancialTableClassifier.

Tests cover keyword matching, numeric density analysis, temporal pattern
detection, table size validation, and end-to-end classification.
"""

from unittest.mock import MagicMock, patch

import pytest

from fin_stat_table_detector.classifiers.financial import FinancialTableClassifier
from fin_stat_table_detector.models import BBox, FinancialTable, TableCandidate


class TestKeywordMatching:
    """Keyword matching tests."""

    def test_income_statement_detection(self) -> None:
        """Income statement keywords should classify as income_statement."""
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

    def test_balance_sheet_detection(self) -> None:
        """Balance sheet keywords should classify as balance_sheet."""
        # Given
        text = "자산총계 10,000 부채총계 5,000 자본총계 5,000"
        classifier = FinancialTableClassifier()

        # When
        category, _, keywords = classifier._calculate_keyword_score(text)

        # Then
        assert category == "balance_sheet"
        assert "자산총계" in keywords

    def test_cash_flow_detection(self) -> None:
        """Cash flow keywords should classify as cash_flow."""
        # Given
        text = "영업활동 현금흐름 1,000 투자활동 -500 재무활동 200"
        classifier = FinancialTableClassifier()

        # When
        category, _, keywords = classifier._calculate_keyword_score(text)

        # Then
        assert category == "cash_flow"
        assert "영업활동" in keywords
        assert "현금흐름" in keywords

    def test_no_match_returns_none(self) -> None:
        """Insufficient keyword matches should return None."""
        # Given
        text = "이것은 일반 텍스트입니다 매출액만 하나"  # Only 1 match
        classifier = FinancialTableClassifier()

        # When
        category, _, _ = classifier._calculate_keyword_score(text)

        # Then
        assert category is None


class TestNumericDensity:
    """Numeric density tests."""

    def test_numeric_density_pass(self) -> None:
        """Text with 20% or more numeric content should pass."""
        # Given
        text = "매출액 1,234 567 890 123 456"  # 5/6 = 83% numeric
        classifier = FinancialTableClassifier()

        # When
        result = classifier._check_numeric_density(text)

        # Then
        assert result is True

    def test_numeric_density_fail(self) -> None:
        """Text with less than 20% numeric content should fail."""
        # Given
        text = "이것은 설명 텍스트입니다 숫자가 거의 없음 123"  # 1/9 ≈ 11%
        classifier = FinancialTableClassifier()

        # When
        result = classifier._check_numeric_density(text)

        # Then
        assert result is False

    def test_empty_text_returns_false(self) -> None:
        """Empty text should return False."""
        # Given
        classifier = FinancialTableClassifier()

        # When
        result = classifier._check_numeric_density("")

        # Then
        assert result is False


class TestTemporalPatterns:
    """Temporal pattern tests."""

    def test_temporal_columns_detected(self) -> None:
        """Two or more temporal patterns should return True."""
        # Given
        text = "항목 2024 2025E 1Q25 2Q25"
        classifier = FinancialTableClassifier()

        # When
        result = classifier._check_temporal_columns(text)

        # Then
        assert result is True

    def test_single_temporal_not_enough(self) -> None:
        """Single temporal pattern should return False."""
        # Given
        text = "항목 2024"
        classifier = FinancialTableClassifier()

        # When
        result = classifier._check_temporal_columns(text)

        # Then
        assert result is False

    def test_korean_quarter_pattern(self) -> None:
        """Korean quarter patterns should be recognized."""
        # Given
        text = "1분기 2분기 3분기"
        classifier = FinancialTableClassifier()

        # When
        result = classifier._check_temporal_columns(text)

        # Then
        assert result is True


class TestTableSize:
    """Table size validation tests."""

    def test_valid_table_size(self) -> None:
        """Valid table size should pass."""
        # Given
        bbox = BBox(50, 100, 500, 400)  # Area: 450 * 300 = 135,000
        classifier = FinancialTableClassifier()

        # When
        result = classifier._is_valid_table_size(
            bbox,
            page_width=600,
            page_height=800,
            row_count=10,
            col_count=5,
        )

        # Then
        assert result is True  # 135,000 / 480,000 = 28%

    def test_too_small_table_fails(self) -> None:
        """Table smaller than 5% of page should fail."""
        # Given
        bbox = BBox(0, 0, 50, 50)  # Area: 2,500
        classifier = FinancialTableClassifier()

        # When
        result = classifier._is_valid_table_size(
            bbox,
            page_width=600,
            page_height=800,
            row_count=10,
            col_count=5,
        )

        # Then
        assert result is False  # 2,500 / 480,000 = 0.5%

    def test_too_few_rows_fails(self) -> None:
        """Table with less than 3 rows should fail."""
        # Given
        bbox = BBox(50, 100, 500, 400)
        classifier = FinancialTableClassifier()

        # When
        result = classifier._is_valid_table_size(
            bbox,
            page_width=600,
            page_height=800,
            row_count=2,  # Only 2 rows
            col_count=5,
        )

        # Then
        assert result is False

    def test_too_few_cols_fails(self) -> None:
        """Table with less than 2 columns should fail."""
        # Given
        bbox = BBox(50, 100, 500, 400)
        classifier = FinancialTableClassifier()

        # When
        result = classifier._is_valid_table_size(
            bbox,
            page_width=600,
            page_height=800,
            row_count=10,
            col_count=1,  # Only 1 column
        )

        # Then
        assert result is False


class TestClassify:
    """End-to-end classification tests."""

    def test_classify_returns_financial_table(self) -> None:
        """Valid input should return FinancialTable."""
        # Given
        classifier = FinancialTableClassifier()
        bbox = BBox(50, 100, 500, 400)
        candidate = TableCandidate(
            page=1,
            bbox=bbox,
            detector="pdfplumber",
            row_count=10,
            col_count=5,
            text_content="매출액 1,234 영업이익 567 당기순이익 890 2024 2025E",
        )

        # When
        result = classifier.classify(
            candidate,
            page_width=600,
            page_height=800,
        )

        # Then
        assert result is not None
        assert isinstance(result, FinancialTable)
        assert result.category == "income_statement"
        assert result.confidence > 0.3
        assert "매출액" in result.matched_keywords
        assert result.detector_source == "pdfplumber"

    def test_classify_returns_none_for_invalid(self) -> None:
        """Invalid input should return None."""
        # Given
        classifier = FinancialTableClassifier()
        bbox = BBox(50, 100, 500, 400)
        candidate = TableCandidate(
            page=1,
            bbox=bbox,
            detector="pdfplumber",
            row_count=10,
            col_count=5,
            text_content="This is regular text without financial keywords 일반 텍스트",
        )

        # When
        result = classifier.classify(
            candidate,
            page_width=600,
            page_height=800,
        )

        # Then
        assert result is None

    def test_classify_returns_none_for_empty_text(self) -> None:
        """Empty text content without pdf_path should return None."""
        # Given
        classifier = FinancialTableClassifier()
        bbox = BBox(50, 100, 500, 400)
        candidate = TableCandidate(
            page=1,
            bbox=bbox,
            detector="pdfplumber",
            row_count=10,
            col_count=5,
            text_content=None,
        )

        # When
        result = classifier.classify(candidate)

        # Then
        assert result is None

    def test_classify_returns_none_for_low_numeric_density(self) -> None:
        """Text with low numeric density should return None."""
        # Given
        classifier = FinancialTableClassifier()
        bbox = BBox(50, 100, 500, 400)
        # Financial keywords but very low numeric density
        candidate = TableCandidate(
            page=1,
            bbox=bbox,
            detector="pdfplumber",
            row_count=10,
            col_count=5,
            text_content="매출액 영업이익 당기순이익 세전이익 법인세 수치없음 텍스트만",
        )

        # When
        result = classifier.classify(
            candidate,
            page_width=600,
            page_height=800,
        )

        # Then
        assert result is None


class TestFinalConfidence:
    """Final confidence calculation tests."""

    def test_temporal_bonus_added(self) -> None:
        """Temporal columns should add 0.1 bonus to confidence."""
        # Given
        classifier = FinancialTableClassifier()

        # When
        confidence_without = classifier._calculate_final_confidence(0.5, False)
        confidence_with = classifier._calculate_final_confidence(0.5, True)

        # Then
        assert confidence_without == 0.5
        assert confidence_with == 0.6

    def test_confidence_capped_at_one(self) -> None:
        """Confidence should not exceed 1.0."""
        # Given
        classifier = FinancialTableClassifier()

        # When
        confidence = classifier._calculate_final_confidence(0.95, True)

        # Then
        assert confidence == 1.0


class TestExtractTextFromBbox:
    """Text extraction tests using mocks."""

    def test_extract_text_from_bbox(self) -> None:
        """Should extract text from PDF using pdfplumber."""
        # Given
        classifier = FinancialTableClassifier()
        bbox = BBox(50, 100, 500, 400)

        # Mock pdfplumber
        mock_page = MagicMock()
        mock_cropped = MagicMock()
        mock_cropped.extract_text.return_value = "매출액 1,234"
        mock_page.within_bbox.return_value = mock_cropped

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)

        with patch("pdfplumber.open", return_value=mock_pdf):
            # When
            result = classifier._extract_text_from_bbox(
                "/path/to/test.pdf",
                page=1,
                bbox=bbox,
            )

        # Then
        assert result == "매출액 1,234"
        mock_page.within_bbox.assert_called_once_with((50, 100, 500, 400))
