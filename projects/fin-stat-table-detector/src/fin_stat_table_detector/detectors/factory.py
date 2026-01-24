"""Factory functions for creating detector instances."""

from fin_stat_table_detector.detectors.base import AbstractDetector
from fin_stat_table_detector.detectors.docling import DoclingDetector


def create_detectors() -> list[AbstractDetector]:
    """Create detector instances.

    Docling: ML-based table detection (including borderless tables).

    Returns:
        List of detector instances.
    """
    return [
        DoclingDetector(),
    ]
