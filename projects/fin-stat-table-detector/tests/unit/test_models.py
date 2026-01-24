"""Tests for data models."""

from fin_stat_table_detector.models import BBox, FinancialTable, TableCandidate


class TestBBox:
    """BBox 데이터 모델 테스트."""

    def test_width_calculation(self) -> None:
        """너비가 올바르게 계산됨."""
        # Given
        bbox = BBox(x0=10, y0=20, x1=110, y1=70)

        # When
        width = bbox.width

        # Then
        assert width == 100

    def test_height_calculation(self) -> None:
        """높이가 올바르게 계산됨."""
        # Given
        bbox = BBox(x0=10, y0=20, x1=110, y1=70)

        # When
        height = bbox.height

        # Then
        assert height == 50

    def test_area_calculation(self) -> None:
        """면적이 올바르게 계산됨."""
        # Given
        bbox = BBox(x0=10, y0=20, x1=110, y1=70)

        # When
        area = bbox.area

        # Then
        assert area == 5000  # 100 * 50

    def test_zero_width_bbox_has_zero_area(self) -> None:
        """너비가 0인 경우 면적도 0."""
        # Given
        bbox = BBox(x0=10, y0=20, x1=10, y1=70)

        # When
        area = bbox.area

        # Then
        assert area == 0

    def test_zero_height_bbox_has_zero_area(self) -> None:
        """높이가 0인 경우 면적도 0."""
        # Given
        bbox = BBox(x0=10, y0=20, x1=110, y1=20)

        # When
        area = bbox.area

        # Then
        assert area == 0


class TestTableCandidate:
    """TableCandidate 데이터 모델 테스트."""

    def test_create_with_required_fields(self) -> None:
        """필수 필드만으로 생성 가능."""
        # Given / When
        candidate = TableCandidate(
            page=1,
            bbox=BBox(0, 0, 100, 100),
            detector="pdfplumber",
        )

        # Then
        assert candidate.page == 1
        assert candidate.detector == "pdfplumber"
        assert candidate.row_count is None
        assert candidate.col_count is None
        assert candidate.text_content is None

    def test_create_with_all_fields(self) -> None:
        """모든 필드를 포함하여 생성 가능."""
        # Given / When
        candidate = TableCandidate(
            page=2,
            bbox=BBox(50, 100, 400, 300),
            detector="camelot_lattice",
            row_count=10,
            col_count=5,
            text_content="매출액 1,234",
        )

        # Then
        assert candidate.page == 2
        assert candidate.row_count == 10
        assert candidate.col_count == 5
        assert candidate.text_content == "매출액 1,234"

    def test_bbox_is_accessible(self) -> None:
        """bbox 속성에 접근 가능."""
        # Given
        bbox = BBox(50, 100, 400, 300)
        candidate = TableCandidate(page=1, bbox=bbox, detector="pdfplumber")

        # Then
        assert candidate.bbox.x0 == 50
        assert candidate.bbox.area == 350 * 200


class TestFinancialTable:
    """FinancialTable 데이터 모델 테스트."""

    def test_create_financial_table(self) -> None:
        """FinancialTable 생성 테스트."""
        # Given / When
        table = FinancialTable(
            page=3,
            bbox=BBox(50, 100, 500, 400),
            category="income_statement",
            confidence=0.85,
            matched_keywords=["매출액", "영업이익", "당기순이익"],
            detector_source="pdfplumber",
        )

        # Then
        assert table.page == 3
        assert table.category == "income_statement"
        assert table.confidence == 0.85
        assert len(table.matched_keywords) == 3
        assert "매출액" in table.matched_keywords
        assert table.detector_source == "pdfplumber"

    def test_bbox_properties_accessible(self) -> None:
        """bbox 속성에 접근 가능."""
        # Given
        table = FinancialTable(
            page=1,
            bbox=BBox(0, 0, 100, 200),
            category="balance_sheet",
            confidence=0.9,
            matched_keywords=["자산총계"],
            detector_source="docling",
        )

        # Then
        assert table.bbox.width == 100
        assert table.bbox.height == 200
        assert table.bbox.area == 20000
