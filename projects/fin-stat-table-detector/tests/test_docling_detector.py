"""Tests for DoclingDetector.

This module tests the DoclingDetector class using mocks to avoid
requiring actual PDF files and the docling dependency.
"""

from unittest.mock import MagicMock, patch
import sys

import pytest

from fin_stat_table_detector.detectors.base import AbstractDetector
from fin_stat_table_detector.detectors.docling_det import DoclingDetector
from fin_stat_table_detector.models import TableCandidate


class TestDoclingDetectorName:
    """DoclingDetector name property tests."""

    def test_name_is_docling(self):
        """name property should return 'docling'.

        Given: A DoclingDetector instance
        When: Accessing the name property
        Then: It should return 'docling'
        """
        # Given
        detector = DoclingDetector()

        # When
        name = detector.name

        # Then
        assert name == "docling"


class TestDoclingDetectorLazyLoading:
    """DoclingDetector lazy loading tests."""

    def test_lazy_loading_converter_is_none_initially(self):
        """_converter should be None after initialization.

        Given: A newly created DoclingDetector instance
        When: Checking the _converter attribute
        Then: It should be None
        """
        # Given / When
        detector = DoclingDetector()

        # Then
        assert detector._converter is None


class TestDoclingDetectorImportError:
    """DoclingDetector import error handling tests."""

    def test_import_error_when_docling_not_installed(self):
        """_get_converter should raise ImportError with clear message when docling is not installed.

        Given: A DoclingDetector instance and docling not available
        When: Calling _get_converter
        Then: It should raise ImportError with a helpful message
        """
        # Given
        detector = DoclingDetector()

        # When / Then
        with patch.dict(
            sys.modules, {"docling": None, "docling.document_converter": None}
        ):
            # Force the import to fail by patching builtins.__import__
            original_import = (
                __builtins__.__import__
                if hasattr(__builtins__, "__import__")
                else __import__
            )

            def mock_import(name, *args, **kwargs):
                if name == "docling.document_converter" or name.startswith("docling"):
                    raise ImportError("No module named 'docling'")
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=mock_import):
                with pytest.raises(ImportError) as exc_info:
                    detector._get_converter()

                # Verify the error message is helpful
                assert "docling이 설치되지 않았습니다" in str(exc_info.value)
                assert "uv sync --extra ml" in str(exc_info.value)


class TestDoclingDetectorInheritance:
    """DoclingDetector inheritance tests."""

    def test_detector_inherits_abstract_detector(self):
        """DoclingDetector should inherit from AbstractDetector.

        Given: The DoclingDetector class
        When: Checking its inheritance
        Then: It should be a subclass of AbstractDetector
        """
        # Given / When / Then
        assert issubclass(DoclingDetector, AbstractDetector)

    def test_detector_instance_is_abstract_detector(self):
        """DoclingDetector instance should be an AbstractDetector.

        Given: A DoclingDetector instance
        When: Checking its type
        Then: It should be an instance of AbstractDetector
        """
        # Given
        detector = DoclingDetector()

        # When / Then
        assert isinstance(detector, AbstractDetector)


class TestDoclingDetectorDetect:
    """DoclingDetector detect method tests."""

    def test_detect_returns_list(self):
        """detect method should return a list.

        Given: A DoclingDetector instance
        When: Calling detect with a mocked converter (no tables)
        Then: It should return an empty list
        """
        # Given
        detector = DoclingDetector()

        # Create mock result with no tables
        mock_document = MagicMock()
        mock_document.tables = []

        mock_result = MagicMock()
        mock_result.document = mock_document

        mock_converter = MagicMock()
        mock_converter.convert.return_value = mock_result

        # Inject mock converter
        detector._converter = mock_converter

        # When
        result = detector.detect("fake.pdf")

        # Then
        assert isinstance(result, list)
        assert result == []

    def test_detect_returns_table_candidates_with_correct_attributes(self):
        """detect should return TableCandidate objects with correct attributes.

        Given: A DoclingDetector and a mocked converter with one table
        When: Calling detect
        Then: It should return a list with TableCandidate objects
              containing correct page, bbox, detector name, and table info
        """
        # Given
        detector = DoclingDetector()

        # Create mock bbox
        mock_bbox = MagicMock()
        mock_bbox.l = 10.0  # left
        mock_bbox.t = 20.0  # top
        mock_bbox.r = 200.0  # right
        mock_bbox.b = 300.0  # bottom

        # Create mock prov (provenance)
        mock_prov = MagicMock()
        mock_prov.page_no = 1
        mock_prov.bbox = mock_bbox

        # Create mock DataFrame
        mock_df = MagicMock()
        mock_df.to_string.return_value = "Header1 Header2\nData1 Data2"
        mock_df.__len__ = MagicMock(return_value=2)
        mock_df.columns = ["Header1", "Header2"]

        # Create mock table
        mock_table = MagicMock()
        mock_table.prov = [mock_prov]
        mock_table.export_to_dataframe.return_value = mock_df

        # Create mock document
        mock_document = MagicMock()
        mock_document.tables = [mock_table]

        mock_result = MagicMock()
        mock_result.document = mock_document

        mock_converter = MagicMock()
        mock_converter.convert.return_value = mock_result

        # Inject mock converter
        detector._converter = mock_converter

        # When
        result = detector.detect("fake.pdf")

        # Then
        assert len(result) == 1
        candidate = result[0]
        assert isinstance(candidate, TableCandidate)
        assert candidate.page == 1
        assert candidate.bbox.x0 == 10.0
        assert candidate.bbox.y0 == 20.0
        assert candidate.bbox.x1 == 200.0
        assert candidate.bbox.y1 == 300.0
        assert candidate.detector == "docling"
        assert candidate.row_count == 2
        assert candidate.col_count == 2
        assert "Header1" in candidate.text_content

    def test_pages_filter_applied(self):
        """detect should filter tables by specified pages.

        Given: A DoclingDetector and a mocked converter with tables on pages 1, 2, and 3
        When: Calling detect with pages=[2]
        Then: It should only return tables from page 2
        """
        # Given
        detector = DoclingDetector()

        # Create mock tables for different pages
        tables = []
        for page_no in [1, 2, 3]:
            mock_bbox = MagicMock()
            mock_bbox.l = 0.0
            mock_bbox.t = 0.0
            mock_bbox.r = 100.0
            mock_bbox.b = 100.0

            mock_prov = MagicMock()
            mock_prov.page_no = page_no
            mock_prov.bbox = mock_bbox

            mock_df = MagicMock()
            mock_df.to_string.return_value = f"Page{page_no}"
            mock_df.__len__ = MagicMock(return_value=1)
            mock_df.columns = ["Col1"]

            mock_table = MagicMock()
            mock_table.prov = [mock_prov]
            mock_table.export_to_dataframe.return_value = mock_df

            tables.append(mock_table)

        # Create mock document
        mock_document = MagicMock()
        mock_document.tables = tables

        mock_result = MagicMock()
        mock_result.document = mock_document

        mock_converter = MagicMock()
        mock_converter.convert.return_value = mock_result

        # Inject mock converter
        detector._converter = mock_converter

        # When
        result = detector.detect("fake.pdf", pages=[2])

        # Then
        assert len(result) == 1
        assert result[0].page == 2
        assert "Page2" in result[0].text_content

    def test_detect_skips_tables_without_prov(self):
        """detect should skip tables without provenance information.

        Given: A DoclingDetector and a table without prov
        When: Calling detect
        Then: It should skip that table
        """
        # Given
        detector = DoclingDetector()

        # Create mock table without prov
        mock_table_no_prov = MagicMock()
        mock_table_no_prov.prov = []  # Empty prov

        # Create mock table with prov
        mock_bbox = MagicMock()
        mock_bbox.l = 10.0
        mock_bbox.t = 20.0
        mock_bbox.r = 100.0
        mock_bbox.b = 100.0

        mock_prov = MagicMock()
        mock_prov.page_no = 1
        mock_prov.bbox = mock_bbox

        mock_df = MagicMock()
        mock_df.to_string.return_value = "Valid table"
        mock_df.__len__ = MagicMock(return_value=1)
        mock_df.columns = ["Col1"]

        mock_table_with_prov = MagicMock()
        mock_table_with_prov.prov = [mock_prov]
        mock_table_with_prov.export_to_dataframe.return_value = mock_df

        # Create mock document with both tables
        mock_document = MagicMock()
        mock_document.tables = [mock_table_no_prov, mock_table_with_prov]

        mock_result = MagicMock()
        mock_result.document = mock_document

        mock_converter = MagicMock()
        mock_converter.convert.return_value = mock_result

        # Inject mock converter
        detector._converter = mock_converter

        # When
        result = detector.detect("fake.pdf")

        # Then
        assert len(result) == 1
        assert "Valid table" in result[0].text_content

    def test_detect_handles_dataframe_export_error(self):
        """detect should handle errors when exporting to DataFrame.

        Given: A DoclingDetector and a table that fails to export to DataFrame
        When: Calling detect
        Then: It should still return a TableCandidate with None values for row/col count and text
        """
        # Given
        detector = DoclingDetector()

        mock_bbox = MagicMock()
        mock_bbox.l = 10.0
        mock_bbox.t = 20.0
        mock_bbox.r = 100.0
        mock_bbox.b = 100.0

        mock_prov = MagicMock()
        mock_prov.page_no = 1
        mock_prov.bbox = mock_bbox

        mock_table = MagicMock()
        mock_table.prov = [mock_prov]
        mock_table.export_to_dataframe.side_effect = Exception(
            "DataFrame export failed"
        )

        mock_document = MagicMock()
        mock_document.tables = [mock_table]

        mock_result = MagicMock()
        mock_result.document = mock_document

        mock_converter = MagicMock()
        mock_converter.convert.return_value = mock_result

        # Inject mock converter
        detector._converter = mock_converter

        # When
        result = detector.detect("fake.pdf")

        # Then
        assert len(result) == 1
        candidate = result[0]
        assert candidate.page == 1
        assert candidate.row_count is None
        assert candidate.col_count is None
        assert candidate.text_content is None

    def test_detect_with_multiple_pages_filter(self):
        """detect should filter tables by multiple specified pages.

        Given: A DoclingDetector and tables on pages 1, 2, 3, 4
        When: Calling detect with pages=[1, 3]
        Then: It should return tables from pages 1 and 3 only
        """
        # Given
        detector = DoclingDetector()

        tables = []
        for page_no in [1, 2, 3, 4]:
            mock_bbox = MagicMock()
            mock_bbox.l = 0.0
            mock_bbox.t = 0.0
            mock_bbox.r = 100.0
            mock_bbox.b = 100.0

            mock_prov = MagicMock()
            mock_prov.page_no = page_no
            mock_prov.bbox = mock_bbox

            mock_df = MagicMock()
            mock_df.to_string.return_value = f"Page{page_no}"
            mock_df.__len__ = MagicMock(return_value=1)
            mock_df.columns = ["Col1"]

            mock_table = MagicMock()
            mock_table.prov = [mock_prov]
            mock_table.export_to_dataframe.return_value = mock_df

            tables.append(mock_table)

        mock_document = MagicMock()
        mock_document.tables = tables

        mock_result = MagicMock()
        mock_result.document = mock_document

        mock_converter = MagicMock()
        mock_converter.convert.return_value = mock_result

        detector._converter = mock_converter

        # When
        result = detector.detect("fake.pdf", pages=[1, 3])

        # Then
        assert len(result) == 2
        pages_found = [c.page for c in result]
        assert 1 in pages_found
        assert 3 in pages_found
        assert 2 not in pages_found
        assert 4 not in pages_found


class TestDoclingDetectorGetConverter:
    """DoclingDetector _get_converter method tests."""

    def test_get_converter_returns_same_instance(self):
        """_get_converter should return the same converter instance on subsequent calls.

        Given: A DoclingDetector with a mock converter already set
        When: Calling _get_converter multiple times
        Then: It should return the same instance
        """
        # Given
        detector = DoclingDetector()
        mock_converter = MagicMock()
        detector._converter = mock_converter

        # When
        result1 = detector._get_converter()
        result2 = detector._get_converter()

        # Then
        assert result1 is result2
        assert result1 is mock_converter

    def test_get_converter_creates_converter_when_none(self):
        """_get_converter should create a new converter when _converter is None.

        Given: A DoclingDetector with _converter as None
        When: Calling _get_converter with mocked DocumentConverter
        Then: It should create and store a new converter
        """
        # Given
        detector = DoclingDetector()
        assert detector._converter is None

        mock_converter_instance = MagicMock()
        mock_converter_class = MagicMock(return_value=mock_converter_instance)

        # When
        with patch.dict(
            sys.modules,
            {"docling": MagicMock(), "docling.document_converter": MagicMock()},
        ):
            with patch(
                "fin_stat_table_detector.detectors.docling_det.DoclingDetector._get_converter"
            ) as mock_get:
                # Simulate successful import and creation
                mock_get.return_value = mock_converter_instance
                result = detector._get_converter()

        # Then - verify through the mock
        assert result is mock_converter_instance
