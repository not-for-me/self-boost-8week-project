"""Single PDF file processor."""

from pathlib import Path

from pypdf import PdfReader

from fin_stat_table_detector.ensemble import EnsembleDetector
from fin_stat_table_detector.processing.config import (
    PageResult,
    ProcessingConfig,
    ProcessingResult,
)
from fin_stat_table_detector.utils.pdf_utils import convert_pdf_to_images


class PdfProcessor:
    """Processes a single PDF file for table detection.

    This class handles the core processing logic for a single PDF:
    - Table detection using the ensemble detector
    - Optional image conversion
    - Result aggregation

    Note:
        This class focuses solely on PDF processing. For exporting results,
        use a ResultExporter implementation (e.g., LabelStudioExporter).

    Attributes:
        detector: EnsembleDetector instance for table detection.
        config: Processing configuration.
    """

    def __init__(
        self,
        detector: EnsembleDetector,
        config: ProcessingConfig,
    ) -> None:
        """Initialize PdfProcessor.

        Args:
            detector: EnsembleDetector instance for table detection.
            config: Processing configuration.
        """
        self._detector = detector
        self._config = config

    @property
    def detector(self) -> EnsembleDetector:
        """The ensemble detector instance."""
        return self._detector

    @property
    def config(self) -> ProcessingConfig:
        """The processing configuration."""
        return self._config

    def process(self, pdf_path: Path) -> ProcessingResult:
        """Process a single PDF file.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            ProcessingResult with detected tables and statistics.
        """
        try:
            return self._process_internal(pdf_path)
        except Exception as e:
            return ProcessingResult(
                pdf_path=pdf_path,
                error=str(e),
            )

    def _process_internal(self, pdf_path: Path) -> ProcessingResult:
        """Internal processing logic.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            ProcessingResult with detected tables and statistics.
        """
        # Detect financial tables
        tables = self._detector.detect_financial_tables(str(pdf_path))

        if self._config.summary_only:
            # Just count pages without image conversion
            reader = PdfReader(pdf_path)
            return ProcessingResult(
                pdf_path=pdf_path,
                pages=len(reader.pages),
                tables=tables,
            )

        # Convert PDF to images
        raw_results = convert_pdf_to_images(
            pdf_path,
            self._config.images_dir,
            self._config.dpi,
        )

        page_results = [
            PageResult(page_num=pn, image_path=ip, dimensions=dims)
            for pn, ip, dims in raw_results
        ]

        return ProcessingResult(
            pdf_path=pdf_path,
            pages=len(page_results),
            tables=tables,
            page_results=page_results,
        )
