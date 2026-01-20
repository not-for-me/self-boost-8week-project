"""Table detector modules."""

from fin_stat_table_detector.detectors.base import AbstractDetector
from fin_stat_table_detector.detectors.docling_det import DoclingDetector

__all__ = [
    "AbstractDetector",
    "DoclingDetector",
]
