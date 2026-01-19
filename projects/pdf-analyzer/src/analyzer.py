"""PDF analysis core logic using pdfplumber."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pdfplumber


@dataclass
class CharInfo:
    """Information about a single character in PDF."""

    text: str
    x0: float
    top: float
    x1: float
    bottom: float
    font_name: str | None
    font_size: float | None

    @classmethod
    def from_pdfplumber(cls, char: dict[str, Any]) -> "CharInfo":
        """Create CharInfo from pdfplumber char dict."""
        return cls(
            text=char.get("text", ""),
            x0=char.get("x0", 0.0),
            top=char.get("top", 0.0),
            x1=char.get("x1", 0.0),
            bottom=char.get("bottom", 0.0),
            font_name=char.get("fontname"),
            font_size=char.get("size"),
        )


@dataclass
class LineInfo:
    """Information about a line object in PDF."""

    x0: float
    top: float
    x1: float
    bottom: float
    width: float | None
    stroke_color: Any | None

    @property
    def is_horizontal(self) -> bool:
        """Check if line is horizontal (within 1pt tolerance)."""
        return abs(self.top - self.bottom) < 1.0

    @property
    def is_vertical(self) -> bool:
        """Check if line is vertical (within 1pt tolerance)."""
        return abs(self.x0 - self.x1) < 1.0

    @classmethod
    def from_pdfplumber(cls, line: dict[str, Any]) -> "LineInfo":
        """Create LineInfo from pdfplumber line dict."""
        return cls(
            x0=line.get("x0", 0.0),
            top=line.get("top", 0.0),
            x1=line.get("x1", 0.0),
            bottom=line.get("bottom", 0.0),
            width=line.get("linewidth") or line.get("width"),
            stroke_color=line.get("stroking_color"),
        )


@dataclass
class RectInfo:
    """Information about a rectangle object in PDF."""

    x0: float
    top: float
    x1: float
    bottom: float
    width: float
    height: float
    stroke_color: Any | None
    fill_color: Any | None

    @classmethod
    def from_pdfplumber(cls, rect: dict[str, Any]) -> "RectInfo":
        """Create RectInfo from pdfplumber rect dict."""
        x0 = rect.get("x0", 0.0)
        top = rect.get("top", 0.0)
        x1 = rect.get("x1", 0.0)
        bottom = rect.get("bottom", 0.0)
        return cls(
            x0=x0,
            top=top,
            x1=x1,
            bottom=bottom,
            width=x1 - x0,
            height=bottom - top,
            stroke_color=rect.get("stroking_color"),
            fill_color=rect.get("non_stroking_color"),
        )


@dataclass
class ImageInfo:
    """Information about an embedded image in PDF."""

    x0: float
    top: float
    x1: float
    bottom: float
    width: float
    height: float
    name: str | None

    @classmethod
    def from_pdfplumber(cls, img: dict[str, Any]) -> "ImageInfo":
        """Create ImageInfo from pdfplumber image dict."""
        return cls(
            x0=img.get("x0", 0.0),
            top=img.get("top", 0.0),
            x1=img.get("x1", 0.0),
            bottom=img.get("bottom", 0.0),
            width=img.get("width", 0.0),
            height=img.get("height", 0.0),
            name=img.get("name"),
        )


@dataclass
class TableInfo:
    """Information about a detected table in PDF."""

    page_number: int
    table_index: int
    bbox: tuple[float, float, float, float]  # (x0, top, x1, bottom)
    row_count: int
    col_count: int
    cells: list[list[str | None]]  # 2D array of cell contents

    @property
    def x0(self) -> float:
        """Left x coordinate."""
        return self.bbox[0]

    @property
    def top(self) -> float:
        """Top y coordinate."""
        return self.bbox[1]

    @property
    def x1(self) -> float:
        """Right x coordinate."""
        return self.bbox[2]

    @property
    def bottom(self) -> float:
        """Bottom y coordinate."""
        return self.bbox[3]

    @property
    def width(self) -> float:
        """Table width in points."""
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self) -> float:
        """Table height in points."""
        return self.bbox[3] - self.bbox[1]


@dataclass
class PageAnalysis:
    """Analysis result for a single PDF page."""

    page_number: int
    width: float
    height: float
    chars: list[CharInfo] = field(default_factory=list)
    lines: list[LineInfo] = field(default_factory=list)
    rects: list[RectInfo] = field(default_factory=list)
    images: list[ImageInfo] = field(default_factory=list)

    @property
    def char_count(self) -> int:
        """Total number of characters."""
        return len(self.chars)

    @property
    def word_count(self) -> int:
        """Estimated word count (non-space characters / 5)."""
        non_space = sum(1 for c in self.chars if c.text.strip())
        return max(1, non_space // 5) if non_space > 0 else 0

    @property
    def line_count(self) -> int:
        """Total number of line objects."""
        return len(self.lines)

    @property
    def horizontal_lines(self) -> int:
        """Count of horizontal lines."""
        return sum(1 for line in self.lines if line.is_horizontal)

    @property
    def vertical_lines(self) -> int:
        """Count of vertical lines."""
        return sum(1 for line in self.lines if line.is_vertical)

    @property
    def rect_count(self) -> int:
        """Total number of rectangles."""
        return len(self.rects)

    @property
    def image_count(self) -> int:
        """Total number of images."""
        return len(self.images)

    def get_font_usage(self) -> dict[str, int]:
        """Get font usage statistics.

        Returns:
            Dictionary mapping font name to character count.
        """
        font_counts: dict[str, int] = {}
        for char in self.chars:
            font = char.font_name or "Unknown"
            font_counts[font] = font_counts.get(font, 0) + 1
        return dict(sorted(font_counts.items(), key=lambda x: -x[1]))


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

    @classmethod
    def from_pdfplumber(cls, metadata: dict[str, Any] | None) -> "DocumentMetadata":
        """Create DocumentMetadata from pdfplumber metadata."""
        if not metadata:
            return cls()
        return cls(
            title=metadata.get("Title"),
            author=metadata.get("Author"),
            subject=metadata.get("Subject"),
            creator=metadata.get("Creator"),
            producer=metadata.get("Producer"),
            creation_date=metadata.get("CreationDate"),
            mod_date=metadata.get("ModDate"),
        )


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
    """PDF structure analyzer."""

    def __init__(self, pdf_path: str | Path):
        """Initialize analyzer with PDF path.

        Args:
            pdf_path: Path to PDF file.

        Raises:
            FileNotFoundError: If PDF file does not exist.
        """
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {self.pdf_path}")

    def get_document_info(self) -> DocumentInfo:
        """Get document-level information.

        Returns:
            DocumentInfo with metadata and page summaries.
        """
        file_size = self.pdf_path.stat().st_size

        with pdfplumber.open(self.pdf_path) as pdf:
            metadata = DocumentMetadata.from_pdfplumber(pdf.metadata)
            page_count = len(pdf.pages)

            # Quick summary of each page
            page_summaries = []
            for i, page in enumerate(pdf.pages):
                summary = {
                    "page_number": i + 1,
                    "width": page.width,
                    "height": page.height,
                    "char_count": len(page.chars) if page.chars else 0,
                    "line_count": len(page.lines) if page.lines else 0,
                    "rect_count": len(page.rects) if page.rects else 0,
                    "image_count": len(page.images) if page.images else 0,
                }
                page_summaries.append(summary)

        return DocumentInfo(
            file_path=self.pdf_path,
            file_size_bytes=file_size,
            page_count=page_count,
            metadata=metadata,
            page_summaries=page_summaries,
        )

    def analyze_page(self, page_number: int) -> PageAnalysis:
        """Analyze a specific page in detail.

        Args:
            page_number: 1-indexed page number.

        Returns:
            PageAnalysis with all page elements.

        Raises:
            ValueError: If page number is out of range.
        """
        with pdfplumber.open(self.pdf_path) as pdf:
            if page_number < 1 or page_number > len(pdf.pages):
                raise ValueError(
                    f"Page {page_number} out of range. "
                    f"Document has {len(pdf.pages)} pages."
                )

            page = pdf.pages[page_number - 1]

            chars = [
                CharInfo.from_pdfplumber(c) for c in (page.chars or [])
            ]
            lines = [
                LineInfo.from_pdfplumber(ln) for ln in (page.lines or [])
            ]
            rects = [
                RectInfo.from_pdfplumber(r) for r in (page.rects or [])
            ]
            images = [
                ImageInfo.from_pdfplumber(img) for img in (page.images or [])
            ]

            return PageAnalysis(
                page_number=page_number,
                width=page.width,
                height=page.height,
                chars=chars,
                lines=lines,
                rects=rects,
                images=images,
            )

    def get_all_fonts(self) -> dict[str, int]:
        """Get font usage across entire document.

        Returns:
            Dictionary mapping font name to total character count.
        """
        all_fonts: dict[str, int] = {}

        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                for char in page.chars or []:
                    font = char.get("fontname", "Unknown")
                    all_fonts[font] = all_fonts.get(font, 0) + 1

        return dict(sorted(all_fonts.items(), key=lambda x: -x[1]))

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
        tables: list[TableInfo] = []

        with pdfplumber.open(self.pdf_path) as pdf:
            if page_number is not None:
                if page_number < 1 or page_number > len(pdf.pages):
                    raise ValueError(
                        f"Page {page_number} out of range. "
                        f"Document has {len(pdf.pages)} pages."
                    )
                pages_to_process = [(page_number, pdf.pages[page_number - 1])]
            else:
                pages_to_process = [
                    (i + 1, page) for i, page in enumerate(pdf.pages)
                ]

            for page_num, page in pages_to_process:
                page_tables = page.find_tables()

                for table_idx, table in enumerate(page_tables):
                    # Extract table data
                    extracted = table.extract()
                    if not extracted:
                        continue

                    # Get bounding box
                    bbox = table.bbox  # (x0, top, x1, bottom)

                    # Count rows and columns
                    row_count = len(extracted)
                    col_count = max(len(row) for row in extracted) if extracted else 0

                    # Normalize cells (ensure all rows have same column count)
                    normalized_cells: list[list[str | None]] = []
                    for row in extracted:
                        normalized_row = list(row) + [None] * (col_count - len(row))
                        normalized_cells.append(normalized_row)

                    tables.append(
                        TableInfo(
                            page_number=page_num,
                            table_index=table_idx,
                            bbox=bbox,
                            row_count=row_count,
                            col_count=col_count,
                            cells=normalized_cells,
                        )
                    )

        return tables

    def get_table_summary(self) -> dict[int, int]:
        """Get table count per page.

        Returns:
            Dictionary mapping page number to table count.
        """
        summary: dict[int, int] = {}

        with pdfplumber.open(self.pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_num = i + 1
                table_count = len(page.find_tables())
                if table_count > 0:
                    summary[page_num] = table_count

        return summary


@dataclass
class PDFStats:
    """Statistics for a single PDF file."""

    file_path: Path
    page_count: int
    total_chars: int
    total_lines: int
    total_images: int
    total_tables: int
    page_sizes: list[tuple[float, float]]  # List of (width, height)
    fonts: dict[str, int]

    @property
    def avg_chars_per_page(self) -> float:
        """Average characters per page."""
        return self.total_chars / self.page_count if self.page_count > 0 else 0

    @property
    def avg_lines_per_page(self) -> float:
        """Average lines per page."""
        return self.total_lines / self.page_count if self.page_count > 0 else 0


@dataclass
class CollectionStats:
    """Aggregated statistics for multiple PDF files."""

    file_count: int
    total_pages: int
    page_size_distribution: dict[str, int]  # e.g., "A4 Portrait": 120
    chars_stats: dict[str, float]  # min, max, avg, median
    lines_stats: dict[str, float]
    images_stats: dict[str, float]
    tables_stats: dict[str, float]
    font_usage: dict[str, int]  # font name -> file count
    errors: list[tuple[Path, str]]  # Files that failed to process


def analyze_single_pdf(pdf_path: Path) -> PDFStats:
    """Analyze a single PDF and return statistics.

    Args:
        pdf_path: Path to PDF file.

    Returns:
        PDFStats object with file statistics.
    """
    analyzer = PDFAnalyzer(pdf_path)

    total_chars = 0
    total_lines = 0
    total_images = 0
    page_sizes = []
    all_fonts: dict[str, int] = {}

    with pdfplumber.open(pdf_path) as pdf:
        page_count = len(pdf.pages)

        for page in pdf.pages:
            total_chars += len(page.chars) if page.chars else 0
            total_lines += len(page.lines) if page.lines else 0
            total_images += len(page.images) if page.images else 0
            page_sizes.append((page.width, page.height))

            for char in page.chars or []:
                font = char.get("fontname", "Unknown")
                all_fonts[font] = all_fonts.get(font, 0) + 1

    # Count tables
    total_tables = sum(analyzer.get_table_summary().values())

    return PDFStats(
        file_path=pdf_path,
        page_count=page_count,
        total_chars=total_chars,
        total_lines=total_lines,
        total_images=total_images,
        total_tables=total_tables,
        page_sizes=page_sizes,
        fonts=all_fonts,
    )


def _classify_page_size(width: float, height: float) -> str:
    """Classify page size into common formats."""
    # A4: 595 x 842 pt (with some tolerance)
    if abs(width - 595) < 10 and abs(height - 842) < 10:
        return "A4 Portrait"
    elif abs(width - 842) < 10 and abs(height - 595) < 10:
        return "A4 Landscape"
    # Letter: 612 x 792 pt
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
        "median": sorted_values[n // 2] if n % 2 == 1
        else (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2,
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
            chars_stats={"min": 0, "max": 0, "avg": 0, "median": 0},
            lines_stats={"min": 0, "max": 0, "avg": 0, "median": 0},
            images_stats={"min": 0, "max": 0, "avg": 0, "median": 0},
            tables_stats={"min": 0, "max": 0, "avg": 0, "median": 0},
            font_usage={},
            errors=errors,
        )

    # Aggregate page sizes
    page_size_dist: dict[str, int] = {}
    for stats in all_stats:
        for width, height in stats.page_sizes:
            size_name = _classify_page_size(width, height)
            page_size_dist[size_name] = page_size_dist.get(size_name, 0) + 1

    # Calculate per-page statistics
    chars_per_page = []
    lines_per_page = []
    images_per_page = []
    tables_per_file = []

    for stats in all_stats:
        if stats.page_count > 0:
            chars_per_page.append(stats.total_chars / stats.page_count)
            lines_per_page.append(stats.total_lines / stats.page_count)
            images_per_page.append(stats.total_images / stats.page_count)
        tables_per_file.append(stats.total_tables)

    # Aggregate font usage (count files using each font)
    font_file_count: dict[str, int] = {}
    for stats in all_stats:
        for font in stats.fonts.keys():
            font_file_count[font] = font_file_count.get(font, 0) + 1

    # Sort by usage
    font_file_count = dict(
        sorted(font_file_count.items(), key=lambda x: -x[1])
    )

    return CollectionStats(
        file_count=len(all_stats),
        total_pages=sum(s.page_count for s in all_stats),
        page_size_distribution=page_size_dist,
        chars_stats=_calculate_stats(chars_per_page),
        lines_stats=_calculate_stats(lines_per_page),
        images_stats=_calculate_stats(images_per_page),
        tables_stats=_calculate_stats(tables_per_file),
        font_usage=font_file_count,
        errors=errors,
    )
