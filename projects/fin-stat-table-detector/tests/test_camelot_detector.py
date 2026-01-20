"""Tests for CamelotDetector."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from fin_stat_table_detector.detectors.base import AbstractDetector
from fin_stat_table_detector.detectors.camelot_det import CamelotDetector
from fin_stat_table_detector.models import BBox


class TestCamelotDetectorName:
    """CamelotDetector name 프로퍼티 테스트."""

    def test_lattice_name(self) -> None:
        """lattice 모드 name이 'camelot_lattice'임."""
        # Given
        detector = CamelotDetector(flavor="lattice")

        # When
        name = detector.name

        # Then
        assert name == "camelot_lattice"

    def test_stream_name(self) -> None:
        """stream 모드 name이 'camelot_stream'임."""
        # Given
        detector = CamelotDetector(flavor="stream")

        # When
        name = detector.name

        # Then
        assert name == "camelot_stream"


class TestCamelotDetectorInit:
    """CamelotDetector 초기화 테스트."""

    def test_invalid_flavor_raises_error(self) -> None:
        """잘못된 flavor 값은 ValueError 발생."""
        # Given
        invalid_flavor = "invalid"

        # When / Then
        with pytest.raises(ValueError) as exc_info:
            CamelotDetector(flavor=invalid_flavor)

        assert "flavor must be 'lattice' or 'stream'" in str(exc_info.value)
        assert "invalid" in str(exc_info.value)

    def test_flavor_property(self) -> None:
        """flavor 프로퍼티 접근 가능."""
        # Given
        detector = CamelotDetector(flavor="stream")

        # When
        flavor = detector.flavor

        # Then
        assert flavor == "stream"

    def test_default_flavor_is_lattice(self) -> None:
        """기본 flavor는 lattice임."""
        # Given / When
        detector = CamelotDetector()

        # Then
        assert detector.flavor == "lattice"


class TestCamelotDetectorInheritance:
    """CamelotDetector 상속 테스트."""

    def test_detector_inherits_abstract_detector(self) -> None:
        """AbstractDetector를 상속."""
        # Given
        detector = CamelotDetector()

        # Then
        assert isinstance(detector, AbstractDetector)


class TestCamelotDetectorFormatPages:
    """CamelotDetector _format_pages 메서드 테스트."""

    def test_format_pages_converts_list_to_string(self) -> None:
        """_format_pages가 페이지 리스트를 문자열로 변환."""
        # Given
        detector = CamelotDetector()
        pages = [1, 2, 5]

        # When
        result = detector._format_pages(pages)

        # Then
        assert result == "1,2,5"

    def test_format_pages_single_page(self) -> None:
        """단일 페이지 변환."""
        # Given
        detector = CamelotDetector()
        pages = [3]

        # When
        result = detector._format_pages(pages)

        # Then
        assert result == "3"

    def test_format_pages_preserves_order(self) -> None:
        """페이지 순서가 보존됨."""
        # Given
        detector = CamelotDetector()
        pages = [5, 1, 3]

        # When
        result = detector._format_pages(pages)

        # Then
        assert result == "5,1,3"


class TestCamelotDetectorConvertBbox:
    """CamelotDetector _convert_bbox 메서드 테스트."""

    def test_bbox_coordinate_conversion(self) -> None:
        """좌표계 변환이 올바르게 동작함."""
        # Given
        detector = CamelotDetector()

        # 모의 camelot 테이블 객체 생성
        mock_table = MagicMock()
        # camelot bbox: (x0, y0, x1, y1) 좌하단 기준
        # 예: 좌하단 기준 (100, 200, 400, 600)
        mock_table._bbox = (100, 200, 400, 600)
        # 페이지 높이 800
        mock_table._page_dimensions = (600, 800)

        # When
        bbox = detector._convert_bbox(mock_table)

        # Then
        # 좌상단 기준으로 변환:
        # x0 = 100 (그대로)
        # y0 = 800 - 600 = 200 (페이지 높이 - 원래 y1)
        # x1 = 400 (그대로)
        # y1 = 800 - 200 = 600 (페이지 높이 - 원래 y0)
        assert bbox.x0 == 100
        assert bbox.y0 == 200
        assert bbox.x1 == 400
        assert bbox.y1 == 600

    def test_bbox_conversion_at_page_top(self) -> None:
        """페이지 상단 영역의 좌표 변환."""
        # Given
        detector = CamelotDetector()

        mock_table = MagicMock()
        # 좌하단 기준: 페이지 상단 (y가 큼)
        mock_table._bbox = (50, 700, 550, 800)
        mock_table._page_dimensions = (600, 800)

        # When
        bbox = detector._convert_bbox(mock_table)

        # Then
        # 좌상단 기준으로 변환: 페이지 상단이므로 y 값이 작아야 함
        assert bbox.y0 == 0  # 800 - 800
        assert bbox.y1 == 100  # 800 - 700

    def test_bbox_conversion_returns_bbox_instance(self) -> None:
        """_convert_bbox가 BBox 인스턴스를 반환."""
        # Given
        detector = CamelotDetector()
        mock_table = MagicMock()
        mock_table._bbox = (0, 0, 100, 100)
        mock_table._page_dimensions = (600, 800)

        # When
        bbox = detector._convert_bbox(mock_table)

        # Then
        assert isinstance(bbox, BBox)


class TestCamelotDetectorExtractText:
    """CamelotDetector _extract_text 메서드 테스트."""

    def test_extract_text_with_dataframe(self) -> None:
        """_extract_text 정상 동작."""
        # Given
        detector = CamelotDetector()

        mock_table = MagicMock()
        # 데이터프레임 생성
        df = pd.DataFrame(
            {
                0: ["항목", "매출액", "영업이익"],
                1: ["2023년", "1,000", "200"],
            }
        )
        mock_table.df = df

        # When
        text = detector._extract_text(mock_table)

        # Then
        assert "항목" in text
        assert "매출액" in text
        assert "영업이익" in text
        assert "2023년" in text
        assert "1,000" in text
        assert "200" in text

    def test_extract_text_skips_empty_cells(self) -> None:
        """빈 셀은 건너뜀."""
        # Given
        detector = CamelotDetector()

        mock_table = MagicMock()
        df = pd.DataFrame(
            {
                0: ["A", "", "C"],
                1: ["", "B", ""],
            }
        )
        mock_table.df = df

        # When
        text = detector._extract_text(mock_table)

        # Then
        assert "A" in text
        assert "B" in text
        assert "C" in text
        # 연속 공백이 없어야 함
        assert "  " not in text

    def test_extract_text_strips_whitespace(self) -> None:
        """셀 내 공백이 제거됨."""
        # Given
        detector = CamelotDetector()

        mock_table = MagicMock()
        df = pd.DataFrame(
            {
                0: ["  hello  ", "\tworld\n"],
            }
        )
        mock_table.df = df

        # When
        text = detector._extract_text(mock_table)

        # Then
        assert text == "hello world"


class TestCamelotDetectorDetect:
    """CamelotDetector detect 메서드 테스트."""

    @patch("fin_stat_table_detector.detectors.camelot_det.camelot")
    def test_detect_calls_read_pdf_with_correct_params(
        self, mock_camelot: MagicMock
    ) -> None:
        """detect가 camelot.read_pdf를 올바른 파라미터로 호출."""
        # Given
        detector = CamelotDetector(flavor="stream")
        mock_camelot.read_pdf.return_value = []

        # When
        detector.detect("test.pdf", pages=[1, 3])

        # Then
        mock_camelot.read_pdf.assert_called_once_with(
            "test.pdf",
            pages="1,3",
            flavor="stream",
        )

    @patch("fin_stat_table_detector.detectors.camelot_det.camelot")
    def test_detect_uses_all_pages_when_none(self, mock_camelot: MagicMock) -> None:
        """pages가 None일 때 'all'을 사용."""
        # Given
        detector = CamelotDetector()
        mock_camelot.read_pdf.return_value = []

        # When
        detector.detect("test.pdf", pages=None)

        # Then
        mock_camelot.read_pdf.assert_called_once_with(
            "test.pdf",
            pages="all",
            flavor="lattice",
        )

    @patch("fin_stat_table_detector.detectors.camelot_det.camelot")
    def test_detect_returns_table_candidates(self, mock_camelot: MagicMock) -> None:
        """detect가 TableCandidate 리스트를 반환."""
        # Given
        detector = CamelotDetector()

        # 모의 테이블 생성
        mock_table = MagicMock()
        mock_table.page = 1
        mock_table._bbox = (50, 100, 450, 500)
        mock_table._page_dimensions = (600, 800)
        mock_table.shape = (5, 3)  # 5 rows, 3 columns
        mock_table.df = pd.DataFrame(
            {
                0: ["Header", "Data1"],
                1: ["Value", "Data2"],
            }
        )

        mock_camelot.read_pdf.return_value = [mock_table]

        # When
        candidates = detector.detect("test.pdf")

        # Then
        assert len(candidates) == 1
        candidate = candidates[0]
        assert candidate.page == 1
        assert candidate.detector == "camelot_lattice"
        assert candidate.row_count == 5
        assert candidate.col_count == 3
        assert isinstance(candidate.bbox, BBox)
        assert candidate.text_content is not None

    @patch("fin_stat_table_detector.detectors.camelot_det.camelot")
    def test_detect_returns_empty_list_when_no_tables(
        self, mock_camelot: MagicMock
    ) -> None:
        """테이블이 없으면 빈 리스트를 반환."""
        # Given
        detector = CamelotDetector()
        mock_camelot.read_pdf.return_value = []

        # When
        candidates = detector.detect("test.pdf")

        # Then
        assert candidates == []

    @patch("fin_stat_table_detector.detectors.camelot_det.camelot")
    def test_detect_handles_multiple_tables(self, mock_camelot: MagicMock) -> None:
        """여러 테이블을 처리."""
        # Given
        detector = CamelotDetector()

        mock_table1 = MagicMock()
        mock_table1.page = 1
        mock_table1._bbox = (50, 100, 450, 300)
        mock_table1._page_dimensions = (600, 800)
        mock_table1.shape = (3, 2)
        mock_table1.df = pd.DataFrame({0: ["A"], 1: ["B"]})

        mock_table2 = MagicMock()
        mock_table2.page = 2
        mock_table2._bbox = (100, 200, 500, 600)
        mock_table2._page_dimensions = (600, 800)
        mock_table2.shape = (10, 5)
        mock_table2.df = pd.DataFrame({0: ["C"], 1: ["D"]})

        mock_camelot.read_pdf.return_value = [mock_table1, mock_table2]

        # When
        candidates = detector.detect("test.pdf")

        # Then
        assert len(candidates) == 2
        assert candidates[0].page == 1
        assert candidates[1].page == 2
