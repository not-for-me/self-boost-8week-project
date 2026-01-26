"""PDF analysis core logic using Docling."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class BBox:
    """Bounding box coordinates (PDF coordinate system).

    Attributes:
        x0: Left x coordinate
        y0: Top y coordinate
        x1: Right x coordinate
        y1: Bottom y coordinate
    """

    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        """Width of the bounding box."""
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        """Height of the bounding box."""
        return self.y1 - self.y0

    @property
    def area(self) -> float:
        """Area of the bounding box."""
        return self.width * self.height

    @property
    def top(self) -> float:
        """Top y coordinate (alias for y0)."""
        return self.y0

    @property
    def bottom(self) -> float:
        """Bottom y coordinate (alias for y1)."""
        return self.y1

    def intersection(self, other: "BBox") -> "BBox | None":
        """Calculate the intersection of two bounding boxes.

        Args:
            other: The other bounding box to intersect with.

        Returns:
            New BBox representing the intersection, or None if no overlap.
        """
        x0 = max(self.x0, other.x0)
        y0 = max(self.y0, other.y0)
        x1 = min(self.x1, other.x1)
        y1 = min(self.y1, other.y1)

        if x0 < x1 and y0 < y1:
            return BBox(x0=x0, y0=y0, x1=x1, y1=y1)
        return None

    def intersection_ratio(self, other: "BBox") -> float:
        """Calculate what fraction of this bbox is inside the other bbox.

        Args:
            other: The container bounding box to check against.

        Returns:
            Float between 0.0 and 1.0 representing the overlap ratio.
        """
        if self.area == 0:
            return 0.0

        intersection_bbox = self.intersection(other)
        if intersection_bbox is None:
            return 0.0

        return intersection_bbox.area / self.area

    def is_mostly_inside(self, other: "BBox", threshold: float = 0.5) -> bool:
        """Check if this bbox is mostly (>threshold) inside another bbox.

        Args:
            other: The container bounding box to check against.
            threshold: Minimum overlap ratio to be considered "inside".
                       Default 0.5 means more than half the area must overlap.

        Returns:
            True if this bbox overlaps the other by more than threshold.
        """
        return self.intersection_ratio(other) > threshold


@dataclass
class TextBlock:
    """A text block/paragraph extracted from PDF.

    Attributes:
        text: The text content
        bbox: Bounding box of the text block
        label: Document label (e.g., 'text', 'title', 'section_header')
        in_table: Whether this text block is inside a table region
    """

    text: str
    bbox: BBox
    label: str = "text"
    in_table: bool = False


@dataclass
class ImageInfo:
    """Information about an embedded image in PDF."""

    bbox: BBox
    caption: str | None = None

    @property
    def x0(self) -> float:
        """Left x coordinate."""
        return self.bbox.x0

    @property
    def top(self) -> float:
        """Top y coordinate."""
        return self.bbox.y0

    @property
    def x1(self) -> float:
        """Right x coordinate."""
        return self.bbox.x1

    @property
    def bottom(self) -> float:
        """Bottom y coordinate."""
        return self.bbox.y1

    @property
    def width(self) -> float:
        """Image width in points."""
        return self.bbox.width

    @property
    def height(self) -> float:
        """Image height in points."""
        return self.bbox.height

    @classmethod
    def from_docling(cls, picture: Any, prov: Any) -> "ImageInfo":
        """Create ImageInfo from Docling PictureItem."""
        bbox_data = prov.bbox
        x0, x1 = min(bbox_data.l, bbox_data.r), max(bbox_data.l, bbox_data.r)
        y0, y1 = min(bbox_data.t, bbox_data.b), max(bbox_data.t, bbox_data.b)
        bbox = BBox(x0=x0, y0=y0, x1=x1, y1=y1)
        caption = getattr(picture, "caption_text", None)
        return cls(bbox=bbox, caption=caption)


@dataclass
class TableInfo:
    """Information about a detected table in PDF."""

    page_number: int
    table_index: int
    bbox: BBox
    row_count: int
    col_count: int
    cells: list[list[str | None]]

    @property
    def x0(self) -> float:
        """Left x coordinate."""
        return self.bbox.x0

    @property
    def top(self) -> float:
        """Top y coordinate."""
        return self.bbox.y0

    @property
    def x1(self) -> float:
        """Right x coordinate."""
        return self.bbox.x1

    @property
    def bottom(self) -> float:
        """Bottom y coordinate."""
        return self.bbox.y1

    @property
    def width(self) -> float:
        """Table width in points."""
        return self.bbox.width

    @property
    def height(self) -> float:
        """Table height in points."""
        return self.bbox.height

    @classmethod
    def from_docling(
        cls,
        table: Any,
        doc: Any,
        page_no: int,
        index: int,
    ) -> "TableInfo":
        """Create TableInfo from Docling TableItem."""
        prov = table.prov[0]
        bbox_data = prov.bbox
        x0, x1 = min(bbox_data.l, bbox_data.r), max(bbox_data.l, bbox_data.r)
        y0, y1 = min(bbox_data.t, bbox_data.b), max(bbox_data.t, bbox_data.b)
        bbox = BBox(x0=x0, y0=y0, x1=x1, y1=y1)

        try:
            df = table.export_to_dataframe(doc=doc)
            cells = [list(row) for row in df.values]
            cells.insert(0, list(df.columns))
            row_count = len(cells)
            col_count = len(df.columns) if len(df.columns) > 0 else 0
        except Exception:
            cells = []
            row_count = 0
            col_count = 0

        return cls(
            page_number=page_no,
            table_index=index,
            bbox=bbox,
            row_count=row_count,
            col_count=col_count,
            cells=cells,
        )


@dataclass
class PageAnalysis:
    """Analysis result for a single PDF page."""

    page_number: int
    width: float
    height: float
    text_blocks: list[TextBlock] = field(default_factory=list)
    images: list[ImageInfo] = field(default_factory=list)

    @property
    def text_block_count(self) -> int:
        """Total number of text blocks."""
        return len(self.text_blocks)

    @property
    def image_count(self) -> int:
        """Total number of images."""
        return len(self.images)

    @property
    def total_text_length(self) -> int:
        """Total characters across all text blocks."""
        return sum(len(tb.text) for tb in self.text_blocks)

    @property
    def word_count(self) -> int:
        """Estimated word count."""
        total_text = " ".join(tb.text for tb in self.text_blocks)
        return len(total_text.split())


@dataclass
class DocumentMetadata:
    """PDF document metadata."""

    title: str | None = None
    author: str | None = None
    subject: str | None = None
    creator: str | None = None
    producer: str | None = None
    creation_date: str | None = None
    mod_date: str | None = None


@dataclass
class DocumentInfo:
    """Complete PDF document information."""

    file_path: Path
    file_size_bytes: int
    page_count: int
    metadata: DocumentMetadata
    page_summaries: list[dict[str, Any]] = field(default_factory=list)

    @property
    def file_size_readable(self) -> str:
        """Human-readable file size."""
        size = self.file_size_bytes
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


class PDFAnalyzer:
    """PDF structure analyzer using Docling."""

    def __init__(self, pdf_path: str | Path, force_ocr: bool = False):
        """Initialize analyzer with PDF path.

        Args:
            pdf_path: Path to PDF file.
            force_ocr: Force full page OCR (for scanned PDFs).

        Raises:
            FileNotFoundError: If PDF file does not exist.
        """
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {self.pdf_path}")

        self._converter = None
        self._doc = None
        self._force_ocr = force_ocr

    def _get_converter(self) -> Any:
        """Lazy loading - load Docling converter on first use."""
        if self._converter is None:
            try:
                from docling.datamodel.pipeline_options import (
                    PdfPipelineOptions,
                )
                from docling.document_converter import (
                    DocumentConverter,
                    PdfFormatOption,
                )

                pipeline_options = PdfPipelineOptions(
                    do_ocr=self._force_ocr,
                )
                self._converter = DocumentConverter(
                    format_options={
                        "pdf": PdfFormatOption(pipeline_options=pipeline_options),
                    }
                )
            except ImportError as e:
                raise ImportError(
                    "docling is not installed. Install with: uv add docling"
                ) from e
        return self._converter

    def _get_document(self) -> Any:
        """Get or convert the document (cached)."""
        if self._doc is None:
            converter = self._get_converter()
            result = converter.convert(str(self.pdf_path))
            self._doc = result.document
        return self._doc

    def _get_pages_data(self, doc: Any) -> dict[int, dict[str, Any]]:
        """Extract per-page data from DoclingDocument."""
        pages: dict[int, dict[str, Any]] = {}

        # Initialize pages with default dimensions
        for page_no in range(1, doc.num_pages() + 1):
            page_obj = doc.pages.get(page_no)
            if page_obj and hasattr(page_obj, "size") and page_obj.size:
                width = page_obj.size.width
                height = page_obj.size.height
            else:
                width = 612.0
                height = 792.0

            pages[page_no] = {
                "width": width,
                "height": height,
                "text_blocks": [],
                "images": [],
            }

        # First pass: collect table bboxes per page
        table_bboxes_by_page: dict[int, list[BBox]] = {}
        if hasattr(doc, "tables"):
            for table in doc.tables:
                if not table.prov:
                    continue
                prov = table.prov[0]
                page_no = prov.page_no
                if page_no not in table_bboxes_by_page:
                    table_bboxes_by_page[page_no] = []

                bbox_data = prov.bbox
                x0, x1 = min(bbox_data.l, bbox_data.r), max(
                    bbox_data.l, bbox_data.r
                )
                y0, y1 = min(bbox_data.t, bbox_data.b), max(
                    bbox_data.t, bbox_data.b
                )
                table_bboxes_by_page[page_no].append(
                    BBox(x0=x0, y0=y0, x1=x1, y1=y1)
                )

        # Second pass: iterate through document items for text blocks
        for item, _level in doc.iterate_items(with_groups=False):
            if hasattr(item, "text") and hasattr(item, "prov") and item.prov:
                prov = item.prov[0]
                page_no = prov.page_no
                if page_no in pages:
                    bbox_data = prov.bbox
                    x0, x1 = min(bbox_data.l, bbox_data.r), max(
                        bbox_data.l, bbox_data.r
                    )
                    y0, y1 = min(bbox_data.t, bbox_data.b), max(
                        bbox_data.t, bbox_data.b
                    )
                    bbox = BBox(x0=x0, y0=y0, x1=x1, y1=y1)

                    label = "text"
                    if hasattr(item, "label"):
                        if hasattr(item.label, "value"):
                            label = item.label.value
                        else:
                            label = str(item.label)

                    # Check if text block is inside any table on this page
                    in_table = False
                    if page_no in table_bboxes_by_page:
                        for table_bbox in table_bboxes_by_page[page_no]:
                            if bbox.is_mostly_inside(table_bbox):
                                in_table = True
                                break

                    pages[page_no]["text_blocks"].append(
                        TextBlock(text=item.text, bbox=bbox, label=label, in_table=in_table)
                    )

        # Iterate through pictures
        if hasattr(doc, "pictures"):
            for pic in doc.pictures:
                if pic.prov:
                    prov = pic.prov[0]
                    page_no = prov.page_no
                    if page_no in pages:
                        pages[page_no]["images"].append(
                            ImageInfo.from_docling(pic, prov)
                        )

        return pages

    def get_document_info(self) -> DocumentInfo:
        """Get document-level information.

        Returns:
            DocumentInfo with metadata and page summaries.
        """
        file_size = self.pdf_path.stat().st_size
        doc = self._get_document()

        # Docling provides limited metadata
        metadata = DocumentMetadata()

        # Build page summaries
        pages_data = self._get_pages_data(doc)
        page_summaries = []

        for page_num in sorted(pages_data.keys()):
            data = pages_data[page_num]
            summary = {
                "page_number": page_num,
                "width": data["width"],
                "height": data["height"],
                "text_block_count": len(data["text_blocks"]),
                "image_count": len(data["images"]),
            }
            page_summaries.append(summary)

        return DocumentInfo(
            file_path=self.pdf_path,
            file_size_bytes=file_size,
            page_count=doc.num_pages(),
            metadata=metadata,
            page_summaries=page_summaries,
        )

    def analyze_page(self, page_number: int) -> PageAnalysis:
        """Analyze a specific page in detail.

        Args:
            page_number: 1-indexed page number.

        Returns:
            PageAnalysis with text blocks and images.

        Raises:
            ValueError: If page number is out of range.
        """
        doc = self._get_document()
        pages_data = self._get_pages_data(doc)

        if page_number not in pages_data:
            raise ValueError(
                f"Page {page_number} out of range. "
                f"Document has {doc.num_pages()} pages."
            )

        data = pages_data[page_number]
        return PageAnalysis(
            page_number=page_number,
            width=data["width"],
            height=data["height"],
            text_blocks=data["text_blocks"],
            images=data["images"],
        )

    def extract_tables(
        self,
        page_number: int | None = None,
    ) -> list[TableInfo]:
        """Extract tables from PDF.

        Args:
            page_number: 1-indexed page number. If None, extract from all pages.

        Returns:
            List of TableInfo objects for detected tables.

        Raises:
            ValueError: If page number is out of range.
        """
        doc = self._get_document()

        if page_number is not None and (page_number < 1 or page_number > doc.num_pages()):
            raise ValueError(
                f"Page {page_number} out of range. "
                f"Document has {doc.num_pages()} pages."
            )

        tables: list[TableInfo] = []
        table_index_by_page: dict[int, int] = {}

        for table in doc.tables:
            if not table.prov:
                continue

            prov = table.prov[0]
            page_no = prov.page_no

            if page_number is not None and page_no != page_number:
                continue

            # Track table index per page
            if page_no not in table_index_by_page:
                table_index_by_page[page_no] = 0
            else:
                table_index_by_page[page_no] += 1

            table_info = TableInfo.from_docling(
                table, doc, page_no, table_index_by_page[page_no]
            )
            tables.append(table_info)

        return tables

    def get_table_summary(self) -> dict[int, int]:
        """Get table count per page.

        Returns:
            Dictionary mapping page number to table count.
        """
        doc = self._get_document()
        summary: dict[int, int] = {}

        for table in doc.tables:
            if not table.prov:
                continue
            page_no = table.prov[0].page_no
            summary[page_no] = summary.get(page_no, 0) + 1

        return summary


@dataclass
class PDFStats:
    """Statistics for a single PDF file."""

    file_path: Path
    page_count: int
    total_text_blocks: int
    total_images: int
    total_tables: int
    page_sizes: list[tuple[float, float]]

    @property
    def avg_text_blocks_per_page(self) -> float:
        """Average text blocks per page."""
        return self.total_text_blocks / self.page_count if self.page_count > 0 else 0

    @property
    def avg_images_per_page(self) -> float:
        """Average images per page."""
        return self.total_images / self.page_count if self.page_count > 0 else 0


@dataclass
class CollectionStats:
    """Aggregated statistics for multiple PDF files."""

    file_count: int
    total_pages: int
    page_size_distribution: dict[str, int]
    text_blocks_stats: dict[str, float]
    images_stats: dict[str, float]
    tables_stats: dict[str, float]
    errors: list[tuple[Path, str]]


def analyze_single_pdf(pdf_path: Path) -> PDFStats:
    """Analyze a single PDF and return statistics.

    Args:
        pdf_path: Path to PDF file.

    Returns:
        PDFStats object with file statistics.
    """
    analyzer = PDFAnalyzer(pdf_path)
    doc_info = analyzer.get_document_info()

    total_text_blocks = 0
    total_images = 0
    page_sizes = []

    for summary in doc_info.page_summaries:
        total_text_blocks += summary.get("text_block_count", 0)
        total_images += summary.get("image_count", 0)
        page_sizes.append((summary["width"], summary["height"]))

    total_tables = sum(analyzer.get_table_summary().values())

    return PDFStats(
        file_path=pdf_path,
        page_count=doc_info.page_count,
        total_text_blocks=total_text_blocks,
        total_images=total_images,
        total_tables=total_tables,
        page_sizes=page_sizes,
    )


def _classify_page_size(width: float, height: float) -> str:
    """Classify page size into common formats."""
    if abs(width - 595) < 10 and abs(height - 842) < 10:
        return "A4 Portrait"
    elif abs(width - 842) < 10 and abs(height - 595) < 10:
        return "A4 Landscape"
    elif abs(width - 612) < 10 and abs(height - 792) < 10:
        return "Letter Portrait"
    elif abs(width - 792) < 10 and abs(height - 612) < 10:
        return "Letter Landscape"
    else:
        return f"Other ({width:.0f}x{height:.0f})"


def _calculate_stats(values: list[float]) -> dict[str, float]:
    """Calculate min, max, avg, median for a list of values."""
    if not values:
        return {"min": 0, "max": 0, "avg": 0, "median": 0}

    sorted_values = sorted(values)
    n = len(sorted_values)

    return {
        "min": min(values),
        "max": max(values),
        "avg": sum(values) / n,
        "median": (
            sorted_values[n // 2]
            if n % 2 == 1
            else (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2
        ),
    }


def analyze_collection(
    pdf_paths: list[Path],
    on_progress: callable | None = None,
) -> CollectionStats:
    """Analyze multiple PDF files and return aggregated statistics.

    Args:
        pdf_paths: List of PDF file paths.
        on_progress: Optional callback(current, total, file_path) for progress.

    Returns:
        CollectionStats with aggregated statistics.
    """
    all_stats: list[PDFStats] = []
    errors: list[tuple[Path, str]] = []

    total = len(pdf_paths)

    for i, pdf_path in enumerate(pdf_paths):
        if on_progress:
            on_progress(i + 1, total, pdf_path)

        try:
            stats = analyze_single_pdf(pdf_path)
            all_stats.append(stats)
        except Exception as e:
            errors.append((pdf_path, str(e)))

    if not all_stats:
        return CollectionStats(
            file_count=0,
            total_pages=0,
            page_size_distribution={},
            text_blocks_stats={"min": 0, "max": 0, "avg": 0, "median": 0},
            images_stats={"min": 0, "max": 0, "avg": 0, "median": 0},
            tables_stats={"min": 0, "max": 0, "avg": 0, "median": 0},
            errors=errors,
        )

    # Aggregate page sizes
    page_size_dist: dict[str, int] = {}
    for stats in all_stats:
        for width, height in stats.page_sizes:
            size_name = _classify_page_size(width, height)
            page_size_dist[size_name] = page_size_dist.get(size_name, 0) + 1

    # Calculate per-page statistics
    text_blocks_per_page = []
    images_per_page = []
    tables_per_file = []

    for stats in all_stats:
        if stats.page_count > 0:
            text_blocks_per_page.append(stats.total_text_blocks / stats.page_count)
            images_per_page.append(stats.total_images / stats.page_count)
        tables_per_file.append(stats.total_tables)

    return CollectionStats(
        file_count=len(all_stats),
        total_pages=sum(s.page_count for s in all_stats),
        page_size_distribution=page_size_dist,
        text_blocks_stats=_calculate_stats(text_blocks_per_page),
        images_stats=_calculate_stats(images_per_page),
        tables_stats=_calculate_stats(tables_per_file),
        errors=errors,
    )
