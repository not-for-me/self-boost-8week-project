"""PDF processing modules for table detection.

This package provides classes for processing PDF files to detect financial tables.

Classes:
    ProcessingConfig: Configuration for PDF processing.
    ProcessingResult: Result of processing a single PDF file.
    PageResult: Result of processing a single PDF page.
    PdfProcessor: Processes a single PDF file.
    BatchProcessor: Abstract base class for batch processing.
    SequentialBatchProcessor: Processes files sequentially.
    ParallelBatchProcessor: Processes files in parallel.
"""

from fin_stat_table_detector.processing.batch import (
    BatchProcessor,
    ParallelBatchProcessor,
    SequentialBatchProcessor,
)
from fin_stat_table_detector.processing.config import (
    PageResult,
    ProcessingConfig,
    ProcessingResult,
)
from fin_stat_table_detector.processing.pdf_processor import PdfProcessor

__all__ = [
    "ProcessingConfig",
    "ProcessingResult",
    "PageResult",
    "PdfProcessor",
    "BatchProcessor",
    "SequentialBatchProcessor",
    "ParallelBatchProcessor",
]
