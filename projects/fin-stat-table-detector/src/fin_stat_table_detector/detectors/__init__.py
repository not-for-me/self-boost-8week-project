"""Table detector modules."""

from fin_stat_table_detector.detectors.base import AbstractDetector
from fin_stat_table_detector.detectors.camelot_det import CamelotDetector
from fin_stat_table_detector.detectors.pdfplumber_det import PdfplumberDetector

__all__ = [
    "AbstractDetector",
    "CamelotDetector",
    "PdfplumberDetector",
]
