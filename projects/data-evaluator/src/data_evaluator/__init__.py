"""Data Evaluator - Detection evaluation for fin-stat-table-detector."""

from data_evaluator.evaluator import DetectionEvaluator
from data_evaluator.models import BBox, Detection, EvaluationResult

__all__ = [
    "BBox",
    "Detection",
    "DetectionEvaluator",
    "EvaluationResult",
]
