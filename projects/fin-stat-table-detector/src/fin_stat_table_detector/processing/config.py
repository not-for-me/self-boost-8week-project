"""Configuration and result dataclasses for PDF processing."""

from dataclasses import dataclass, field
from pathlib import Path

from fin_stat_table_detector.exporters import PageDimensions
from fin_stat_table_detector.models import FinancialTable


@dataclass
class ProcessingConfig:
    """Configuration for PDF processing.

    Attributes:
        images_dir: Directory to save converted page images.
        dpi: Image resolution (dots per inch).
        summary_only: If True, skip image generation.
    """

    images_dir: Path
    dpi: int = 150
    summary_only: bool = False


@dataclass
class PageResult:
    """Result of processing a single PDF page.

    Attributes:
        page_num: Page number (1-indexed).
        image_path: Path to the converted image file.
        dimensions: Page dimensions for coordinate conversion.
    """

    page_num: int
    image_path: Path
    dimensions: PageDimensions


@dataclass
class ProcessingResult:
    """Result of processing a single PDF file.

    Attributes:
        pdf_path: Path to the processed PDF file.
        pages: Number of pages in the PDF.
        tables: List of detected financial tables.
        page_results: List of page processing results (empty if summary_only).
        error: Error message if processing failed, None otherwise.
    """

    pdf_path: Path
    pages: int = 0
    tables: list[FinancialTable] = field(default_factory=list)
    page_results: list[PageResult] = field(default_factory=list)
    error: str | None = None

    @property
    def tables_detected(self) -> int:
        """Number of tables detected."""
        return len(self.tables)

    @property
    def categories(self) -> dict[str, int]:
        """Count of tables by category."""
        counts: dict[str, int] = {}
        for table in self.tables:
            counts[table.category] = counts.get(table.category, 0) + 1
        return counts

    @property
    def is_success(self) -> bool:
        """Whether processing completed without errors."""
        return self.error is None

    def to_dict(self) -> dict:
        """Convert to dictionary for backward compatibility.

        Returns:
            Dictionary with processing statistics.
        """
        result = {
            "pdf_path": str(self.pdf_path),
            "pages": self.pages,
            "tables_detected": self.tables_detected,
            "categories": self.categories,
            "tables": self.tables,
        }
        if self.page_results:
            result["page_results"] = [
                (pr.page_num, str(pr.image_path), pr.dimensions)
                for pr in self.page_results
            ]
        if self.error:
            result["error"] = self.error
        return result
