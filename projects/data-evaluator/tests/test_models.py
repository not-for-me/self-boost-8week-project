"""Tests for data models."""

import pytest

from data_evaluator.models import (
    BBox,
    Detection,
    DetectionSource,
    EvaluationResult,
    MatchedPair,
)


class TestBBox:
    """Tests for BBox dataclass."""

    def test_bbox_creation_with_valid_values(self) -> None:
        """Given valid coordinates, BBox should be created successfully."""
        bbox = BBox(x=10.0, y=20.0, width=30.0, height=40.0)

        assert bbox.x == 10.0
        assert bbox.y == 20.0
        assert bbox.width == 30.0
        assert bbox.height == 40.0

    def test_bbox_x1_returns_right_edge(self) -> None:
        """Given a bbox, x1 should return x + width."""
        bbox = BBox(x=10.0, y=20.0, width=30.0, height=40.0)

        assert bbox.x1 == 40.0

    def test_bbox_y1_returns_bottom_edge(self) -> None:
        """Given a bbox, y1 should return y + height."""
        bbox = BBox(x=10.0, y=20.0, width=30.0, height=40.0)

        assert bbox.y1 == 60.0

    def test_bbox_area_calculation(self) -> None:
        """Given a bbox, area should return width * height."""
        bbox = BBox(x=0.0, y=0.0, width=10.0, height=20.0)

        assert bbox.area == 200.0

    def test_bbox_with_zero_dimensions(self) -> None:
        """Given zero width and height, bbox should be valid with zero area."""
        bbox = BBox(x=50.0, y=50.0, width=0.0, height=0.0)

        assert bbox.area == 0.0

    def test_bbox_rejects_negative_width(self) -> None:
        """Given negative width, BBox should raise ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            BBox(x=10.0, y=20.0, width=-5.0, height=10.0)

    def test_bbox_rejects_negative_height(self) -> None:
        """Given negative height, BBox should raise ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            BBox(x=10.0, y=20.0, width=10.0, height=-5.0)


class TestDetection:
    """Tests for Detection dataclass."""

    def test_detection_creation(self) -> None:
        """Given valid inputs, Detection should be created successfully."""
        bbox = BBox(x=10.0, y=20.0, width=30.0, height=40.0)
        detection = Detection(
            bbox=bbox,
            label="income_statement",
            source=DetectionSource.PREDICTION,
            image_id="page_1.png",
        )

        assert detection.bbox == bbox
        assert detection.label == "income_statement"
        assert detection.source == DetectionSource.PREDICTION
        assert detection.image_id == "page_1.png"

    def test_detection_with_default_image_id(self) -> None:
        """Given no image_id, Detection should use empty string."""
        bbox = BBox(x=0.0, y=0.0, width=10.0, height=10.0)
        detection = Detection(
            bbox=bbox,
            label="balance_sheet",
            source=DetectionSource.GROUND_TRUTH,
        )

        assert detection.image_id == ""


class TestMatchedPair:
    """Tests for MatchedPair dataclass."""

    def test_matched_pair_with_matching_labels(self) -> None:
        """Given matching labels, label_match should be True."""
        bbox = BBox(x=10.0, y=10.0, width=20.0, height=20.0)
        pred = Detection(bbox=bbox, label="income_statement", source=DetectionSource.PREDICTION)
        gt = Detection(bbox=bbox, label="income_statement", source=DetectionSource.GROUND_TRUTH)

        pair = MatchedPair(prediction=pred, ground_truth=gt, iou=0.9)

        assert pair.label_match is True

    def test_matched_pair_with_different_labels(self) -> None:
        """Given different labels, label_match should be False."""
        bbox = BBox(x=10.0, y=10.0, width=20.0, height=20.0)
        pred = Detection(bbox=bbox, label="income_statement", source=DetectionSource.PREDICTION)
        gt = Detection(bbox=bbox, label="balance_sheet", source=DetectionSource.GROUND_TRUTH)

        pair = MatchedPair(prediction=pred, ground_truth=gt, iou=0.8)

        assert pair.label_match is False


class TestEvaluationResult:
    """Tests for EvaluationResult dataclass."""

    def test_precision_with_all_correct_predictions(self) -> None:
        """Given all TPs, precision should be 1.0."""
        result = EvaluationResult(tp=10, fp=0, fn=5)

        assert result.precision == 1.0

    def test_precision_with_some_false_positives(self) -> None:
        """Given some FPs, precision should be TP/(TP+FP)."""
        result = EvaluationResult(tp=8, fp=2, fn=0)

        assert result.precision == 0.8

    def test_precision_with_no_predictions(self) -> None:
        """Given no predictions (TP=0, FP=0), precision should be 0."""
        result = EvaluationResult(tp=0, fp=0, fn=5)

        assert result.precision == 0.0

    def test_recall_with_all_detected(self) -> None:
        """Given all ground truths detected, recall should be 1.0."""
        result = EvaluationResult(tp=10, fp=5, fn=0)

        assert result.recall == 1.0

    def test_recall_with_some_missed(self) -> None:
        """Given some FNs, recall should be TP/(TP+FN)."""
        result = EvaluationResult(tp=7, fp=0, fn=3)

        assert result.recall == 0.7

    def test_recall_with_no_ground_truths(self) -> None:
        """Given no ground truths (TP=0, FN=0), recall should be 0."""
        result = EvaluationResult(tp=0, fp=5, fn=0)

        assert result.recall == 0.0

    def test_f1_score_perfect_detection(self) -> None:
        """Given perfect detection, F1 should be 1.0."""
        result = EvaluationResult(tp=10, fp=0, fn=0)

        assert result.f1 == 1.0

    def test_f1_score_balanced_errors(self) -> None:
        """Given balanced precision/recall, F1 should equal both."""
        result = EvaluationResult(tp=5, fp=5, fn=5)

        assert result.precision == 0.5
        assert result.recall == 0.5
        assert result.f1 == 0.5

    def test_f1_score_with_zero_predictions(self) -> None:
        """Given no detections at all, F1 should be 0."""
        result = EvaluationResult(tp=0, fp=0, fn=10)

        assert result.f1 == 0.0

    def test_category_accuracy_all_correct(self) -> None:
        """Given all label matches, category accuracy should be 1.0."""
        bbox = BBox(x=10.0, y=10.0, width=20.0, height=20.0)
        pred = Detection(bbox=bbox, label="income_statement", source=DetectionSource.PREDICTION)
        gt = Detection(bbox=bbox, label="income_statement", source=DetectionSource.GROUND_TRUTH)

        result = EvaluationResult(
            tp=2,
            fp=0,
            fn=0,
            matched_pairs=[
                MatchedPair(prediction=pred, ground_truth=gt, iou=0.9),
                MatchedPair(prediction=pred, ground_truth=gt, iou=0.8),
            ],
        )

        assert result.category_accuracy == 1.0

    def test_category_accuracy_with_mismatches(self) -> None:
        """Given some label mismatches, category accuracy should reflect ratio."""
        bbox = BBox(x=10.0, y=10.0, width=20.0, height=20.0)
        pred1 = Detection(bbox=bbox, label="income_statement", source=DetectionSource.PREDICTION)
        gt1 = Detection(bbox=bbox, label="income_statement", source=DetectionSource.GROUND_TRUTH)
        pred2 = Detection(bbox=bbox, label="income_statement", source=DetectionSource.PREDICTION)
        gt2 = Detection(bbox=bbox, label="balance_sheet", source=DetectionSource.GROUND_TRUTH)

        result = EvaluationResult(
            tp=2,
            fp=0,
            fn=0,
            matched_pairs=[
                MatchedPair(prediction=pred1, ground_truth=gt1, iou=0.9),
                MatchedPair(prediction=pred2, ground_truth=gt2, iou=0.8),
            ],
        )

        assert result.category_accuracy == 0.5

    def test_category_accuracy_with_no_matches(self) -> None:
        """Given no matched pairs, category accuracy should be None."""
        result = EvaluationResult(tp=0, fp=5, fn=3)

        assert result.category_accuracy is None

    def test_add_combines_results(self) -> None:
        """Given two results, __add__ should combine counts and pairs."""
        result1 = EvaluationResult(tp=5, fp=2, fn=3, iou_threshold=0.5)
        result2 = EvaluationResult(tp=3, fp=1, fn=2, iou_threshold=0.5)

        combined = result1 + result2

        assert combined.tp == 8
        assert combined.fp == 3
        assert combined.fn == 5

    def test_add_fails_with_different_thresholds(self) -> None:
        """Given different IoU thresholds, __add__ should raise ValueError."""
        result1 = EvaluationResult(tp=5, fp=2, fn=3, iou_threshold=0.5)
        result2 = EvaluationResult(tp=3, fp=1, fn=2, iou_threshold=0.75)

        with pytest.raises(ValueError, match="different IoU thresholds"):
            result1 + result2
