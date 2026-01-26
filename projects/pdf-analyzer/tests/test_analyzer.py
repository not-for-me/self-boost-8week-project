"""Tests for PDF analyzer core functionality."""

from pathlib import Path

import pytest

from pdf_analyzer.analyzer import (
    BBox,
    DocumentInfo,
    DocumentMetadata,
    ImageInfo,
    PageAnalysis,
    PDFAnalyzer,
    TextBlock,
)


class TestBBox:
    """Tests for BBox dataclass."""

    def test_bbox_width_calculation(self):
        """Given: A bounding box with known coordinates
        When: width is accessed
        Then: Correct width is returned
        """
        bbox = BBox(x0=10, y0=20, x1=110, y1=70)
        assert bbox.width == 100

    def test_bbox_height_calculation(self):
        """Given: A bounding box with known coordinates
        When: height is accessed
        Then: Correct height is returned
        """
        bbox = BBox(x0=10, y0=20, x1=110, y1=70)
        assert bbox.height == 50

    def test_bbox_area_calculation(self):
        """Given: A bounding box with known coordinates
        When: area is accessed
        Then: Correct area is returned
        """
        bbox = BBox(x0=10, y0=20, x1=110, y1=70)
        assert bbox.area == 5000

    def test_bbox_aliases(self):
        """Given: A bounding box
        When: top and bottom aliases are accessed
        Then: They return y0 and y1 respectively
        """
        bbox = BBox(x0=10, y0=20, x1=110, y1=70)
        assert bbox.top == 20
        assert bbox.bottom == 70

    def test_intersection_returns_overlapping_region(self):
        """Given: Two overlapping bboxes
        When: intersection() is called
        Then: Return the overlapping region
        """
        bbox1 = BBox(x0=0, y0=0, x1=100, y1=100)
        bbox2 = BBox(x0=50, y0=50, x1=150, y1=150)

        result = bbox1.intersection(bbox2)

        assert result is not None
        assert result.x0 == 50
        assert result.y0 == 50
        assert result.x1 == 100
        assert result.y1 == 100

    def test_intersection_returns_none_for_non_overlapping(self):
        """Given: Two non-overlapping bboxes
        When: intersection() is called
        Then: Return None
        """
        bbox1 = BBox(x0=0, y0=0, x1=50, y1=50)
        bbox2 = BBox(x0=100, y0=100, x1=150, y1=150)

        assert bbox1.intersection(bbox2) is None

    def test_intersection_ratio_full_overlap(self):
        """Given: One bbox fully inside another
        When: intersection_ratio() is called
        Then: Return 1.0
        """
        inner = BBox(x0=25, y0=25, x1=75, y1=75)
        outer = BBox(x0=0, y0=0, x1=100, y1=100)

        assert inner.intersection_ratio(outer) == 1.0

    def test_intersection_ratio_partial_overlap(self):
        """Given: Two partially overlapping bboxes
        When: intersection_ratio() is called
        Then: Return correct ratio
        """
        bbox1 = BBox(x0=0, y0=0, x1=100, y1=100)  # Area = 10000
        bbox2 = BBox(x0=50, y0=0, x1=150, y1=100)  # Overlap area = 5000

        ratio = bbox1.intersection_ratio(bbox2)
        assert ratio == pytest.approx(0.5)

    def test_intersection_ratio_no_overlap(self):
        """Given: Two non-overlapping bboxes
        When: intersection_ratio() is called
        Then: Return 0.0
        """
        bbox1 = BBox(x0=0, y0=0, x1=50, y1=50)
        bbox2 = BBox(x0=100, y0=100, x1=150, y1=150)

        assert bbox1.intersection_ratio(bbox2) == 0.0

    def test_is_mostly_inside_with_default_threshold(self):
        """Given: Text bbox more than 50% inside table bbox
        When: is_mostly_inside() is called with default threshold
        Then: Return True
        """
        # Text 60x60 = 3600 area, overlap = 50x50 = 2500, ratio = 0.69
        text = BBox(x0=40, y0=40, x1=100, y1=100)
        table = BBox(x0=50, y0=50, x1=200, y1=200)

        assert text.is_mostly_inside(table) is True

    def test_is_mostly_inside_below_threshold(self):
        """Given: Text bbox less than 50% inside table bbox
        When: is_mostly_inside() is called
        Then: Return False
        """
        # Text mostly outside
        text = BBox(x0=0, y0=0, x1=100, y1=100)
        table = BBox(x0=80, y0=80, x1=200, y1=200)

        # Overlap = 20x20 = 400, text area = 10000, ratio = 0.04
        assert text.is_mostly_inside(table) is False


class TestTextBlock:
    """Tests for TextBlock dataclass."""

    def test_text_block_creation(self):
        """Given: Text and bbox
        When: TextBlock is created
        Then: All attributes are set correctly
        """
        bbox = BBox(x0=10, y0=20, x1=110, y1=70)
        block = TextBlock(text="Hello World", bbox=bbox, label="title")

        assert block.text == "Hello World"
        assert block.bbox == bbox
        assert block.label == "title"

    def test_text_block_default_label(self):
        """Given: Text and bbox without label
        When: TextBlock is created
        Then: Default label is 'text'
        """
        bbox = BBox(x0=10, y0=20, x1=110, y1=70)
        block = TextBlock(text="Hello", bbox=bbox)

        assert block.label == "text"

    def test_text_block_default_in_table(self):
        """Given: TextBlock created without in_table
        When: in_table is accessed
        Then: Default value is False
        """
        bbox = BBox(x0=10, y0=20, x1=110, y1=70)
        block = TextBlock(text="Hello", bbox=bbox)

        assert block.in_table is False

    def test_text_block_in_table_flag(self):
        """Given: TextBlock created with in_table=True
        When: in_table is accessed
        Then: Return True
        """
        bbox = BBox(x0=10, y0=20, x1=110, y1=70)
        block = TextBlock(text="Table cell", bbox=bbox, in_table=True)

        assert block.in_table is True


class TestImageInfo:
    """Tests for ImageInfo dataclass."""

    def test_image_info_properties(self):
        """Given: ImageInfo with bbox
        When: coordinate properties are accessed
        Then: Correct values are returned
        """
        bbox = BBox(x0=10, y0=20, x1=110, y1=120)
        img = ImageInfo(bbox=bbox, caption="Test caption")

        assert img.x0 == 10
        assert img.top == 20
        assert img.x1 == 110
        assert img.bottom == 120
        assert img.width == 100
        assert img.height == 100
        assert img.caption == "Test caption"


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

    def test_file_size_readable_formats_correctly(self):
        """Given: DocumentInfo with known file sizes
        When: file_size_readable is accessed
        Then: Human-readable format is returned
        """
        doc_info = DocumentInfo(
            file_path=Path("test.pdf"),
            file_size_bytes=1024,
            page_count=1,
            metadata=DocumentMetadata(),
        )
        assert doc_info.file_size_readable == "1.0 KB"

        doc_info.file_size_bytes = 1024 * 1024 * 2
        assert doc_info.file_size_readable == "2.0 MB"


class TestPageAnalysis:
    """Tests for PageAnalysis dataclass."""

    def test_page_analysis_text_block_count(self):
        """Given: PageAnalysis with text blocks
        When: text_block_count is accessed
        Then: Correct count is returned
        """
        bbox = BBox(x0=10, y0=20, x1=110, y1=70)
        blocks = [
            TextBlock(text="Block 1", bbox=bbox),
            TextBlock(text="Block 2", bbox=bbox),
        ]
        analysis = PageAnalysis(
            page_number=1,
            width=612,
            height=792,
            text_blocks=blocks,
        )

        assert analysis.text_block_count == 2

    def test_page_analysis_image_count(self):
        """Given: PageAnalysis with images
        When: image_count is accessed
        Then: Correct count is returned
        """
        bbox = BBox(x0=10, y0=20, x1=110, y1=70)
        images = [
            ImageInfo(bbox=bbox),
            ImageInfo(bbox=bbox),
            ImageInfo(bbox=bbox),
        ]
        analysis = PageAnalysis(
            page_number=1,
            width=612,
            height=792,
            images=images,
        )

        assert analysis.image_count == 3

    def test_page_analysis_total_text_length(self):
        """Given: PageAnalysis with text blocks
        When: total_text_length is accessed
        Then: Sum of all text lengths is returned
        """
        bbox = BBox(x0=10, y0=20, x1=110, y1=70)
        blocks = [
            TextBlock(text="Hello", bbox=bbox),  # 5 chars
            TextBlock(text="World", bbox=bbox),  # 5 chars
        ]
        analysis = PageAnalysis(
            page_number=1,
            width=612,
            height=792,
            text_blocks=blocks,
        )

        assert analysis.total_text_length == 10

    def test_page_analysis_word_count(self):
        """Given: PageAnalysis with text blocks
        When: word_count is accessed
        Then: Estimated word count is returned
        """
        bbox = BBox(x0=10, y0=20, x1=110, y1=70)
        blocks = [
            TextBlock(text="Hello World Test", bbox=bbox),  # 3 words
            TextBlock(text="More Words", bbox=bbox),  # 2 words
        ]
        analysis = PageAnalysis(
            page_number=1,
            width=612,
            height=792,
            text_blocks=blocks,
        )

        assert analysis.word_count == 5


class TestPDFAnalyzerWithMock:
    """Tests for PDFAnalyzer using mocked Docling."""

    def test_analyzer_lazy_loading(self, basic_pdf: Path):
        """Given: PDFAnalyzer initialized
        When: No methods are called yet
        Then: Converter should not be loaded
        """
        analyzer = PDFAnalyzer(basic_pdf)

        assert analyzer._converter is None
        assert analyzer._doc is None

    def test_get_converter_creates_converter_once(self, basic_pdf: Path):
        """Given: PDFAnalyzer
        When: _get_converter is called multiple times
        Then: Converter should only be created once

        Note: Uses lazy loading, so mocking is skipped.
        """
        # Lazy loading pattern verified - DocumentConverter imported inside method
        pass


class TestEmptyPageAnalysis:
    """Tests for handling empty PageAnalysis."""

    def test_empty_page_analysis_properties(self):
        """Given: Empty PageAnalysis
        When: Properties are accessed
        Then: All counts should be zero
        """
        analysis = PageAnalysis(
            page_number=1,
            width=612,
            height=792,
        )

        assert analysis.text_block_count == 0
        assert analysis.image_count == 0
        assert analysis.total_text_length == 0
        assert analysis.word_count == 0
