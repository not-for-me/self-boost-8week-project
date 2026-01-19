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
