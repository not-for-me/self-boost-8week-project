"""Tests for PdfplumberDetector.

This module tests the PdfplumberDetector class using mocks to avoid
requiring actual PDF files.
"""

from unittest.mock import MagicMock, patch

import pytest

from fin_stat_table_detector.detectors.base import AbstractDetector
from fin_stat_table_detector.detectors.pdfplumber_det import PdfplumberDetector


class TestPdfplumberDetectorName:
    """PdfplumberDetector name property tests."""

    def test_name_is_pdfplumber(self):
        """name property should return 'pdfplumber'.

        Given: A PdfplumberDetector instance
        When: Accessing the name property
        Then: It should return 'pdfplumber'
        """
        # Given
        detector = PdfplumberDetector()

        # When
        name = detector.name

        # Then
        assert name == "pdfplumber"


class TestPdfplumberDetectorInheritance:
    """PdfplumberDetector inheritance tests."""

    def test_detector_inherits_abstract_detector(self):
        """PdfplumberDetector should inherit from AbstractDetector.

        Given: The PdfplumberDetector class
        When: Checking its inheritance
        Then: It should be a subclass of AbstractDetector
        """
        # Given / When / Then
        assert issubclass(PdfplumberDetector, AbstractDetector)

    def test_detector_instance_is_abstract_detector(self):
        """PdfplumberDetector instance should be an AbstractDetector.

        Given: A PdfplumberDetector instance
        When: Checking its type
        Then: It should be an instance of AbstractDetector
        """
        # Given
        detector = PdfplumberDetector()

        # When / Then
        assert isinstance(detector, AbstractDetector)


class TestPdfplumberDetectorDetect:
    """PdfplumberDetector detect method tests."""

    def test_detect_returns_list(self):
        """detect method should return a list.

        Given: A PdfplumberDetector instance
        When: Calling detect with a mocked PDF (no tables)
        Then: It should return an empty list
        """
        # Given
        detector = PdfplumberDetector()

        # Create mock PDF with no tables
        mock_page = MagicMock()
        mock_page.find_tables.return_value = []

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)

        # When
        with patch("pdfplumber.open", return_value=mock_pdf):
            result = detector.detect("fake.pdf")

        # Then
        assert isinstance(result, list)
        assert result == []

    def test_detect_returns_table_candidates_with_correct_attributes(self):
        """detect should return TableCandidate objects with correct attributes.

        Given: A PdfplumberDetector and a mocked PDF with one table
        When: Calling detect
        Then: It should return a list with TableCandidate objects
              containing correct page, bbox, detector name, and table info
        """
        # Given
        detector = PdfplumberDetector()

        # Create mock table
        mock_table = MagicMock()
        mock_table.bbox = (10.0, 20.0, 200.0, 300.0)
        mock_table.extract.return_value = [
            ["Header1", "Header2"],
            ["Data1", "Data2"],
        ]

        # Create mock page
        mock_page = MagicMock()
        mock_page.find_tables.return_value = [mock_table]

        # Create mock PDF
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)

        # When
        with patch("pdfplumber.open", return_value=mock_pdf):
            result = detector.detect("fake.pdf")

        # Then
        assert len(result) == 1
        candidate = result[0]
        assert candidate.page == 1
        assert candidate.bbox.x0 == 10.0
        assert candidate.bbox.y0 == 20.0
        assert candidate.bbox.x1 == 200.0
        assert candidate.bbox.y1 == 300.0
        assert candidate.detector == "pdfplumber"
        assert candidate.row_count == 2
        assert candidate.col_count == 2
        assert "Header1" in candidate.text_content
        assert "Data2" in candidate.text_content

    def test_detect_with_specific_pages(self):
        """detect should only process specified pages.

        Given: A PdfplumberDetector and a mocked 3-page PDF
        When: Calling detect with pages=[2]
        Then: It should only process page 2
        """
        # Given
        detector = PdfplumberDetector()

        # Create mock tables for each page
        mock_table_1 = MagicMock()
        mock_table_1.bbox = (0, 0, 100, 100)
        mock_table_1.extract.return_value = [["Page1"]]

        mock_table_2 = MagicMock()
        mock_table_2.bbox = (0, 0, 100, 100)
        mock_table_2.extract.return_value = [["Page2"]]

        mock_table_3 = MagicMock()
        mock_table_3.bbox = (0, 0, 100, 100)
        mock_table_3.extract.return_value = [["Page3"]]

        # Create mock pages
        mock_page_1 = MagicMock()
        mock_page_1.find_tables.return_value = [mock_table_1]

        mock_page_2 = MagicMock()
        mock_page_2.find_tables.return_value = [mock_table_2]

        mock_page_3 = MagicMock()
        mock_page_3.find_tables.return_value = [mock_table_3]

        # Create mock PDF
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page_1, mock_page_2, mock_page_3]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)

        # When
        with patch("pdfplumber.open", return_value=mock_pdf):
            result = detector.detect("fake.pdf", pages=[2])

        # Then
        assert len(result) == 1
        assert result[0].page == 2
        assert "Page2" in result[0].text_content


class TestFlattenTableText:
    """Tests for _flatten_table_text helper method."""

    def test_flatten_table_text_with_valid_data(self):
        """_flatten_table_text should join all cell values with spaces.

        Given: A PdfplumberDetector and valid 2D table data
        When: Calling _flatten_table_text
        Then: It should return a space-separated string of all cell values
        """
        # Given
        detector = PdfplumberDetector()
        table_data = [
            ["Header1", "Header2"],
            ["Value1", "Value2"],
        ]

        # When
        result = detector._flatten_table_text(table_data)

        # Then
        assert result == "Header1 Header2 Value1 Value2"

    def test_flatten_table_text_with_empty_data(self):
        """_flatten_table_text should return empty string for empty data.

        Given: A PdfplumberDetector and an empty list
        When: Calling _flatten_table_text
        Then: It should return an empty string
        """
        # Given
        detector = PdfplumberDetector()
        table_data: list[list[str | None]] = []

        # When
        result = detector._flatten_table_text(table_data)

        # Then
        assert result == ""

    def test_flatten_table_text_with_none_cells(self):
        """_flatten_table_text should skip None cells.

        Given: A PdfplumberDetector and table data with None values
        When: Calling _flatten_table_text
        Then: It should only include non-None values in the result
        """
        # Given
        detector = PdfplumberDetector()
        table_data: list[list[str | None]] = [
            ["Header1", None, "Header3"],
            [None, "Value2", None],
        ]

        # When
        result = detector._flatten_table_text(table_data)

        # Then
        assert result == "Header1 Header3 Value2"

    def test_flatten_table_text_with_none_input(self):
        """_flatten_table_text should return empty string for None input.

        Given: A PdfplumberDetector and None as input
        When: Calling _flatten_table_text
        Then: It should return an empty string
        """
        # Given
        detector = PdfplumberDetector()

        # When
        result = detector._flatten_table_text(None)

        # Then
        assert result == ""

    def test_flatten_table_text_strips_whitespace(self):
        """_flatten_table_text should strip whitespace from cell values.

        Given: A PdfplumberDetector and table data with whitespace
        When: Calling _flatten_table_text
        Then: It should strip leading/trailing whitespace from each cell
        """
        # Given
        detector = PdfplumberDetector()
        table_data = [
            ["  Header1  ", "Header2\n"],
            ["\tValue1", "Value2  "],
        ]

        # When
        result = detector._flatten_table_text(table_data)

        # Then
        assert result == "Header1 Header2 Value1 Value2"
