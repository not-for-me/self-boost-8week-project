"""Parsers for various annotation formats."""

from data_evaluator.parsers.label_studio import (
    parse_annotations,
    parse_predictions,
)

__all__ = ["parse_annotations", "parse_predictions"]
