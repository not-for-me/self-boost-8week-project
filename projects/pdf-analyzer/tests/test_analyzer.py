"""Tests for PDF analyzer core functionality."""

from pathlib import Path

import pytest

from src.analyzer import (
    CharInfo,
    DocumentInfo,
    LineInfo,
    PageAnalysis,
    PDFAnalyzer,
)


class TestPDFAnalyzerInit:
    """Tests for PDFAnalyzer initialization."""

    def test_init_with_valid_pdf_succeeds(self, basic_pdf: Path):
        """Given: A valid PDF file path
        When: PDFAnalyzer is initialized
        Then: No exception is raised
        """
        analyzer = PDFAnalyzer(basic_pdf)
        assert analyzer.pdf_path == basic_pdf

    def test_init_with_nonexistent_file_raises_error(self, tmp_path: Path):
        """Given: A non-existent file path
        When: PDFAnalyzer is initialized
        Then: FileNotFoundError is raised
        """
        nonexistent = tmp_path / "nonexistent.pdf"
        with pytest.raises(FileNotFoundError):
            PDFAnalyzer(nonexistent)


class TestDocumentInfo:
    """Tests for document information extraction."""

    def test_get_document_info_returns_correct_page_count(self, multipage_pdf: Path):
        """Given: A 3-page PDF file
        When: get_document_info is called
        Then: page_count should be 3
        """
        analyzer = PDFAnalyzer(multipage_pdf)
        doc_info = analyzer.get_document_info()

        assert doc_info.page_count == 3

    def test_get_document_info_returns_correct_file_path(self, basic_pdf: Path):
        """Given: A PDF file
        When: get_document_info is called
        Then: file_path should match the input path
        """
        analyzer = PDFAnalyzer(basic_pdf)
        doc_info = analyzer.get_document_info()

        assert doc_info.file_path == basic_pdf

    def test_get_document_info_returns_positive_file_size(self, basic_pdf: Path):
        """Given: A PDF file
        When: get_document_info is called
        Then: file_size_bytes should be positive
        """
        analyzer = PDFAnalyzer(basic_pdf)
        doc_info = analyzer.get_document_info()

        assert doc_info.file_size_bytes > 0

    def test_get_document_info_includes_page_summaries(self, multipage_pdf: Path):
        """Given: A multi-page PDF
        When: get_document_info is called
        Then: page_summaries should have one entry per page
        """
        analyzer = PDFAnalyzer(multipage_pdf)
        doc_info = analyzer.get_document_info()

        assert len(doc_info.page_summaries) == 3
        assert all(s["page_number"] > 0 for s in doc_info.page_summaries)

    def test_file_size_readable_formats_correctly(self):
        """Given: DocumentInfo with known file sizes
        When: file_size_readable is accessed
        Then: Human-readable format is returned
        """
        doc_info = DocumentInfo(
            file_path=Path("test.pdf"),
            file_size_bytes=1024,
            page_count=1,
            metadata=None,
        )
        assert doc_info.file_size_readable == "1.0 KB"

        doc_info.file_size_bytes = 1024 * 1024 * 2
        assert doc_info.file_size_readable == "2.0 MB"


class TestPageAnalysis:
    """Tests for page analysis functionality."""

    def test_analyze_page_returns_correct_page_number(self, basic_pdf: Path):
        """Given: A PDF file
        When: analyze_page is called with page 1
        Then: page_number in result should be 1
        """
        analyzer = PDFAnalyzer(basic_pdf)
        analysis = analyzer.analyze_page(1)

        assert analysis.page_number == 1

    def test_analyze_page_returns_positive_dimensions(self, basic_pdf: Path):
        """Given: A PDF file
        When: analyze_page is called
        Then: width and height should be positive
        """
        analyzer = PDFAnalyzer(basic_pdf)
        analysis = analyzer.analyze_page(1)

        assert analysis.width > 0
        assert analysis.height > 0

    def test_analyze_page_extracts_characters(self, basic_pdf: Path):
        """Given: A PDF with text content
        When: analyze_page is called
        Then: chars list should not be empty
        """
        analyzer = PDFAnalyzer(basic_pdf)
        analysis = analyzer.analyze_page(1)

        assert len(analysis.chars) > 0
        assert all(isinstance(c, CharInfo) for c in analysis.chars)

    def test_analyze_page_chars_have_coordinates(self, basic_pdf: Path):
        """Given: A PDF with text content
        When: analyze_page is called
        Then: Each character should have valid coordinates
        """
        analyzer = PDFAnalyzer(basic_pdf)
        analysis = analyzer.analyze_page(1)

        for char in analysis.chars[:10]:
            assert char.x0 >= 0
            assert char.top >= 0

    def test_analyze_page_extracts_lines(self, table_pdf: Path):
        """Given: A PDF with table (line objects)
        When: analyze_page is called
        Then: lines list should not be empty
        """
        analyzer = PDFAnalyzer(table_pdf)
        analysis = analyzer.analyze_page(1)

        assert len(analysis.lines) > 0
        assert all(isinstance(ln, LineInfo) for ln in analysis.lines)

    def test_analyze_page_invalid_page_raises_error(self, basic_pdf: Path):
        """Given: A single-page PDF
        When: analyze_page is called with page 99
        Then: ValueError is raised
        """
        analyzer = PDFAnalyzer(basic_pdf)

        with pytest.raises(ValueError, match="out of range"):
            analyzer.analyze_page(99)

    def test_analyze_page_zero_page_raises_error(self, basic_pdf: Path):
        """Given: A PDF file
        When: analyze_page is called with page 0
        Then: ValueError is raised
        """
        analyzer = PDFAnalyzer(basic_pdf)

        with pytest.raises(ValueError, match="out of range"):
            analyzer.analyze_page(0)


class TestPageAnalysisProperties:
    """Tests for PageAnalysis computed properties."""

    def test_char_count_matches_chars_length(self, basic_pdf: Path):
        """Given: A page analysis result
        When: char_count is accessed
        Then: It should equal len(chars)
        """
        analyzer = PDFAnalyzer(basic_pdf)
        analysis = analyzer.analyze_page(1)

        assert analysis.char_count == len(analysis.chars)

    def test_line_count_matches_lines_length(self, table_pdf: Path):
        """Given: A page analysis result
        When: line_count is accessed
        Then: It should equal len(lines)
        """
        analyzer = PDFAnalyzer(table_pdf)
        analysis = analyzer.analyze_page(1)

        assert analysis.line_count == len(analysis.lines)

    def test_horizontal_vertical_lines_sum_correctly(self, table_pdf: Path):
        """Given: A page with table lines
        When: horizontal_lines and vertical_lines are accessed
        Then: Their sum should not exceed total line_count
        """
        analyzer = PDFAnalyzer(table_pdf)
        analysis = analyzer.analyze_page(1)

        total_categorized = analysis.horizontal_lines + analysis.vertical_lines
        assert total_categorized <= analysis.line_count

    def test_get_font_usage_returns_dict(self, basic_pdf: Path):
        """Given: A page with text
        When: get_font_usage is called
        Then: A dictionary mapping fonts to counts is returned
        """
        analyzer = PDFAnalyzer(basic_pdf)
        analysis = analyzer.analyze_page(1)

        fonts = analysis.get_font_usage()

        assert isinstance(fonts, dict)
        assert len(fonts) > 0
        assert all(isinstance(count, int) for count in fonts.values())


class TestLineInfo:
    """Tests for LineInfo helper methods."""

    def test_horizontal_line_detection(self):
        """Given: A horizontal line (same top and bottom)
        When: is_horizontal is checked
        Then: It should return True
        """
        line = LineInfo(
            x0=0, top=100, x1=200, bottom=100,
            width=1.0, stroke_color=None
        )
        assert line.is_horizontal is True
        assert line.is_vertical is False

    def test_vertical_line_detection(self):
        """Given: A vertical line (same x0 and x1)
        When: is_vertical is checked
        Then: It should return True
        """
        line = LineInfo(
            x0=100, top=0, x1=100, bottom=200,
            width=1.0, stroke_color=None
        )
        assert line.is_vertical is True
        assert line.is_horizontal is False

    def test_diagonal_line_detection(self):
        """Given: A diagonal line
        When: is_horizontal and is_vertical are checked
        Then: Both should return False
        """
        line = LineInfo(
            x0=0, top=0, x1=100, bottom=100,
            width=1.0, stroke_color=None
        )
        assert line.is_horizontal is False
        assert line.is_vertical is False


class TestEmptyPage:
    """Tests for handling empty pages."""

    def test_analyze_empty_page_returns_empty_lists(self, empty_page_pdf: Path):
        """Given: A PDF with an empty page (page 2)
        When: analyze_page is called for page 2
        Then: All element lists should be empty
        """
        analyzer = PDFAnalyzer(empty_page_pdf)
        analysis = analyzer.analyze_page(2)

        assert analysis.char_count == 0
        assert analysis.line_count == 0
        assert analysis.image_count == 0
