"""Table detector modules."""

from fin_stat_table_detector.detectors.base import AbstractDetector
from fin_stat_table_detector.detectors.docling import DoclingDetector
from fin_stat_table_detector.detectors.factory import create_detectors

__all__ = [
    "AbstractDetector",
    "DoclingDetector",
    "create_detectors",
]
