"""Tests for DetectionEvaluator."""

import pytest

from data_evaluator.evaluator import DetectionEvaluator
from data_evaluator.models import BBox, Detection, DetectionSource


def make_prediction(x: float, y: float, w: float, h: float, label: str = "table") -> Detection:
    """Helper to create a prediction detection."""
    return Detection(
        bbox=BBox(x=x, y=y, width=w, height=h),
        label=label,
        source=DetectionSource.PREDICTION,
    )


def make_ground_truth(x: float, y: float, w: float, h: float, label: str = "table") -> Detection:
    """Helper to create a ground truth detection."""
    return Detection(
        bbox=BBox(x=x, y=y, width=w, height=h),
        label=label,
        source=DetectionSource.GROUND_TRUTH,
    )


class TestDetectionEvaluatorInit:
    """Tests for DetectionEvaluator initialization."""

    def test_default_iou_threshold(self) -> None:
        """Given no threshold, should default to 0.5."""
        evaluator = DetectionEvaluator()

        assert evaluator.iou_threshold == 0.5

    def test_custom_iou_threshold(self) -> None:
        """Given custom threshold, should use it."""
        evaluator = DetectionEvaluator(iou_threshold=0.75)

        assert evaluator.iou_threshold == 0.75

    def test_invalid_threshold_below_zero(self) -> None:
        """Given threshold below 0, should raise ValueError."""
        with pytest.raises(ValueError, match="between 0 and 1"):
            DetectionEvaluator(iou_threshold=-0.1)

    def test_invalid_threshold_above_one(self) -> None:
        """Given threshold above 1, should raise ValueError."""
        with pytest.raises(ValueError, match="between 0 and 1"):
            DetectionEvaluator(iou_threshold=1.1)


class TestEvaluatePage:
    """Tests for evaluate_page method."""

    def test_perfect_detection(self) -> None:
        """Given identical predictions and ground truths, should return perfect scores."""
        evaluator = DetectionEvaluator(iou_threshold=0.5)
        predictions = [make_prediction(10, 10, 20, 20)]
        ground_truths = [make_ground_truth(10, 10, 20, 20)]

        result = evaluator.evaluate_page(predictions, ground_truths)

        assert result.tp == 1
        assert result.fp == 0
        assert result.fn == 0
        assert result.precision == 1.0
        assert result.recall == 1.0
        assert result.f1 == 1.0

    def test_false_positive(self) -> None:
        """Given prediction with no matching GT, should count as FP."""
        evaluator = DetectionEvaluator(iou_threshold=0.5)
        predictions = [make_prediction(10, 10, 20, 20)]
        ground_truths = []

        result = evaluator.evaluate_page(predictions, ground_truths)

        assert result.tp == 0
        assert result.fp == 1
        assert result.fn == 0

    def test_false_negative(self) -> None:
        """Given GT with no matching prediction, should count as FN."""
        evaluator = DetectionEvaluator(iou_threshold=0.5)
        predictions = []
        ground_truths = [make_ground_truth(10, 10, 20, 20)]

        result = evaluator.evaluate_page(predictions, ground_truths)

        assert result.tp == 0
        assert result.fp == 0
        assert result.fn == 1

    def test_partial_overlap_above_threshold(self) -> None:
        """Given overlap above threshold, should count as TP."""
        evaluator = DetectionEvaluator(iou_threshold=0.3)
        # These boxes have ~33% IoU
        predictions = [make_prediction(0, 0, 10, 20)]
        ground_truths = [make_ground_truth(5, 0, 10, 20)]

        result = evaluator.evaluate_page(predictions, ground_truths)

        assert result.tp == 1
        assert result.fp == 0
        assert result.fn == 0

    def test_partial_overlap_below_threshold(self) -> None:
        """Given overlap below threshold, should count as FP and FN."""
        evaluator = DetectionEvaluator(iou_threshold=0.5)
        # These boxes have ~33% IoU, below 0.5 threshold
        predictions = [make_prediction(0, 0, 10, 20)]
        ground_truths = [make_ground_truth(5, 0, 10, 20)]

        result = evaluator.evaluate_page(predictions, ground_truths)

        assert result.tp == 0
        assert result.fp == 1
        assert result.fn == 1

    def test_multiple_detections(self) -> None:
        """Given multiple predictions and GTs, should match correctly."""
        evaluator = DetectionEvaluator(iou_threshold=0.5)
        predictions = [
            make_prediction(0, 0, 20, 20),   # matches GT1
            make_prediction(50, 50, 20, 20), # matches GT2
            make_prediction(90, 90, 5, 5),   # no match (FP)
        ]
        ground_truths = [
            make_ground_truth(0, 0, 20, 20),   # matches pred1
            make_ground_truth(50, 50, 20, 20), # matches pred2
            make_ground_truth(25, 25, 10, 10), # no match (FN)
        ]

        result = evaluator.evaluate_page(predictions, ground_truths)

        assert result.tp == 2
        assert result.fp == 1
        assert result.fn == 1

    def test_greedy_matching_prefers_higher_iou(self) -> None:
        """Given multiple possible matches, should prefer highest IoU."""
        evaluator = DetectionEvaluator(iou_threshold=0.5)
        # pred1 could match either GT, but GT1 has higher IoU
        predictions = [make_prediction(0, 0, 20, 20)]
        ground_truths = [
            make_ground_truth(0, 0, 20, 20),   # IoU = 1.0
            make_ground_truth(5, 5, 20, 20),   # Lower IoU
        ]

        result = evaluator.evaluate_page(predictions, ground_truths)

        assert result.tp == 1
        assert result.fn == 1
        assert result.matched_pairs[0].iou == 1.0

    def test_one_to_one_matching(self) -> None:
        """Each GT should only be matched to one prediction."""
        evaluator = DetectionEvaluator(iou_threshold=0.5)
        # Two predictions that both could match the same GT
        predictions = [
            make_prediction(0, 0, 20, 20),
            make_prediction(2, 2, 18, 18),  # slightly offset but still overlaps
        ]
        ground_truths = [make_ground_truth(0, 0, 20, 20)]

        result = evaluator.evaluate_page(predictions, ground_truths)

        assert result.tp == 1
        assert result.fp == 1
        assert result.fn == 0

    def test_matched_pairs_stored(self) -> None:
        """Matched pairs should be stored in result."""
        evaluator = DetectionEvaluator(iou_threshold=0.5)
        predictions = [make_prediction(10, 10, 20, 20, "income_statement")]
        ground_truths = [make_ground_truth(10, 10, 20, 20, "income_statement")]

        result = evaluator.evaluate_page(predictions, ground_truths)

        assert len(result.matched_pairs) == 1
        pair = result.matched_pairs[0]
        assert pair.prediction.label == "income_statement"
        assert pair.ground_truth.label == "income_statement"
        assert pair.iou == 1.0
        assert pair.label_match is True

    def test_empty_inputs(self) -> None:
        """Given empty predictions and GTs, should return zeros."""
        evaluator = DetectionEvaluator()

        result = evaluator.evaluate_page([], [])

        assert result.tp == 0
        assert result.fp == 0
        assert result.fn == 0


class TestEvaluateDataset:
    """Tests for evaluate_dataset method."""

    def test_combines_multiple_pages(self) -> None:
        """Given multiple pages, should combine results."""
        evaluator = DetectionEvaluator(iou_threshold=0.5)
        predictions = {
            "page_1.png": [make_prediction(0, 0, 20, 20)],
            "page_2.png": [make_prediction(0, 0, 20, 20), make_prediction(50, 50, 10, 10)],
        }
        ground_truths = {
            "page_1.png": [make_ground_truth(0, 0, 20, 20)],
            "page_2.png": [make_ground_truth(0, 0, 20, 20)],
        }

        result = evaluator.evaluate_dataset(predictions, ground_truths)

        assert result.tp == 2
        assert result.fp == 1
        assert result.fn == 0

    def test_handles_missing_predictions(self) -> None:
        """Given page with only GT, should count all as FN."""
        evaluator = DetectionEvaluator(iou_threshold=0.5)
        predictions = {}
        ground_truths = {
            "page_1.png": [make_ground_truth(0, 0, 20, 20)],
        }

        result = evaluator.evaluate_dataset(predictions, ground_truths)

        assert result.tp == 0
        assert result.fp == 0
        assert result.fn == 1

    def test_handles_missing_ground_truths(self) -> None:
        """Given page with only predictions, should count all as FP."""
        evaluator = DetectionEvaluator(iou_threshold=0.5)
        predictions = {
            "page_1.png": [make_prediction(0, 0, 20, 20)],
        }
        ground_truths = {}

        result = evaluator.evaluate_dataset(predictions, ground_truths)

        assert result.tp == 0
        assert result.fp == 1
        assert result.fn == 0

    def test_empty_dataset(self) -> None:
        """Given empty dataset, should return zeros."""
        evaluator = DetectionEvaluator()

        result = evaluator.evaluate_dataset({}, {})

        assert result.tp == 0
        assert result.fp == 0
        assert result.fn == 0

    def test_category_accuracy_across_pages(self) -> None:
        """Category accuracy should be calculated across all matched pairs."""
        evaluator = DetectionEvaluator(iou_threshold=0.5)
        predictions = {
            "page_1.png": [make_prediction(0, 0, 20, 20, "income_statement")],
            "page_2.png": [make_prediction(0, 0, 20, 20, "balance_sheet")],
        }
        ground_truths = {
            "page_1.png": [make_ground_truth(0, 0, 20, 20, "income_statement")],
            "page_2.png": [make_ground_truth(0, 0, 20, 20, "income_statement")],  # mismatch
        }

        result = evaluator.evaluate_dataset(predictions, ground_truths)

        assert result.category_accuracy == 0.5
