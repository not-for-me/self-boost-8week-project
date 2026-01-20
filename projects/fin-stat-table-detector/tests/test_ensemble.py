"""Tests for EnsembleDetector and merge logic.

Tests cover IoU calculation, candidate merging with Union-Find and Spatial Index,
and ensemble detection with multiple detectors.
"""

from unittest.mock import MagicMock, patch

import pytest

from fin_stat_table_detector.ensemble import (
    EnsembleDetector,
    calculate_iou,
    merge_candidates,
)
from fin_stat_table_detector.models import BBox, FinancialTable, TableCandidate


class TestCalculateIoU:
    """IoU calculation tests."""

    def test_identical_boxes_return_one(self) -> None:
        """Identical bboxes should return IoU of 1.0."""
        # Given
        bbox1 = BBox(0, 0, 100, 100)
        bbox2 = BBox(0, 0, 100, 100)

        # When
        iou = calculate_iou(bbox1, bbox2)

        # Then
        assert iou == 1.0

    def test_non_overlapping_returns_zero(self) -> None:
        """Non-overlapping bboxes should return IoU of 0.0."""
        # Given
        bbox1 = BBox(0, 0, 100, 100)
        bbox2 = BBox(200, 200, 300, 300)

        # When
        iou = calculate_iou(bbox1, bbox2)

        # Then
        assert iou == 0.0

    def test_partial_overlap(self) -> None:
        """Partially overlapping bboxes should return correct IoU.

        bbox1: (0,0) to (100,100) -> area = 10000
        bbox2: (50,50) to (150,150) -> area = 10000
        intersection: (50,50) to (100,100) -> area = 2500
        union: 10000 + 10000 - 2500 = 17500
        IoU: 2500 / 17500 = 0.1428...
        """
        # Given
        bbox1 = BBox(0, 0, 100, 100)
        bbox2 = BBox(50, 50, 150, 150)

        # When
        iou = calculate_iou(bbox1, bbox2)

        # Then
        assert 0.14 <= iou <= 0.15  # Approximately 0.143

    def test_edge_touching_returns_zero(self) -> None:
        """Boxes touching at edge only should return IoU of 0.0."""
        # Given
        bbox1 = BBox(0, 0, 100, 100)
        bbox2 = BBox(100, 0, 200, 100)  # Touching at x=100

        # When
        iou = calculate_iou(bbox1, bbox2)

        # Then
        assert iou == 0.0

    def test_one_contains_other(self) -> None:
        """When one bbox fully contains the other, IoU equals area ratio."""
        # Given
        bbox1 = BBox(0, 0, 100, 100)  # area = 10000
        bbox2 = BBox(25, 25, 75, 75)  # area = 2500 (contained)
        # intersection = 2500, union = 10000

        # When
        iou = calculate_iou(bbox1, bbox2)

        # Then
        assert iou == 0.25  # 2500 / 10000


class TestMergeCandidates:
    """Candidate merging tests."""

    def test_overlapping_candidates_merged(self) -> None:
        """Overlapping candidates should be merged into one."""
        # Given
        candidates = [
            TableCandidate(
                page=1,
                bbox=BBox(0, 0, 100, 100),
                detector="detector_a",
            ),
            TableCandidate(
                page=1,
                bbox=BBox(20, 20, 120, 120),  # High overlap
                detector="detector_b",
            ),
        ]

        # When
        result = merge_candidates(candidates, iou_threshold=0.3)

        # Then
        assert len(result) == 1

    def test_transitive_overlap_merged(self) -> None:
        """Transitive overlap should be merged (A<->B, B<->C -> A,B,C merged)."""
        # Given
        candidates = [
            TableCandidate(
                page=1,
                bbox=BBox(0, 0, 100, 100),  # A
                detector="detector_a",
            ),
            TableCandidate(
                page=1,
                bbox=BBox(50, 50, 150, 150),  # B: overlaps with A
                detector="detector_b",
            ),
            TableCandidate(
                page=1,
                bbox=BBox(100, 100, 200, 200),  # C: overlaps with B, not A
                detector="detector_c",
            ),
        ]

        # When
        result = merge_candidates(candidates, iou_threshold=0.1)

        # Then
        assert len(result) == 1  # All three merged transitively

    def test_different_pages_not_merged(self) -> None:
        """Candidates on different pages should not be merged."""
        # Given
        candidates = [
            TableCandidate(
                page=1,
                bbox=BBox(0, 0, 100, 100),
                detector="detector_a",
            ),
            TableCandidate(
                page=2,  # Different page
                bbox=BBox(0, 0, 100, 100),  # Same bbox coordinates
                detector="detector_b",
            ),
        ]

        # When
        result = merge_candidates(candidates, iou_threshold=0.3)

        # Then
        assert len(result) == 2

    def test_largest_bbox_selected_as_representative(self) -> None:
        """The largest bbox should be selected as group representative."""
        # Given
        small_bbox = BBox(0, 0, 50, 50)  # area = 2500
        medium_bbox = BBox(10, 10, 80, 80)  # area = 4900
        large_bbox = BBox(0, 0, 100, 100)  # area = 10000 (largest)

        candidates = [
            TableCandidate(page=1, bbox=small_bbox, detector="small"),
            TableCandidate(page=1, bbox=medium_bbox, detector="medium"),
            TableCandidate(page=1, bbox=large_bbox, detector="large"),
        ]

        # When
        result = merge_candidates(candidates, iou_threshold=0.1)

        # Then
        assert len(result) == 1
        assert result[0].bbox == large_bbox
        assert result[0].detector == "large"

    def test_empty_candidates_returns_empty(self) -> None:
        """Empty candidate list should return empty list."""
        # Given
        candidates: list[TableCandidate] = []

        # When
        result = merge_candidates(candidates)

        # Then
        assert result == []

    def test_single_candidate_returns_itself(self) -> None:
        """Single candidate should return as-is."""
        # Given
        candidate = TableCandidate(
            page=1,
            bbox=BBox(0, 0, 100, 100),
            detector="solo",
        )
        candidates = [candidate]

        # When
        result = merge_candidates(candidates)

        # Then
        assert len(result) == 1
        assert result[0] == candidate

    def test_non_overlapping_candidates_preserved(self) -> None:
        """Non-overlapping candidates should all be preserved."""
        # Given
        candidates = [
            TableCandidate(page=1, bbox=BBox(0, 0, 100, 100), detector="a"),
            TableCandidate(page=1, bbox=BBox(200, 0, 300, 100), detector="b"),
            TableCandidate(page=1, bbox=BBox(0, 200, 100, 300), detector="c"),
        ]

        # When
        result = merge_candidates(candidates, iou_threshold=0.3)

        # Then
        assert len(result) == 3


class TestEnsembleDetector:
    """EnsembleDetector tests."""

    def test_requires_at_least_one_detector(self) -> None:
        """Empty detector list should raise ValueError."""
        # Given
        detectors: list = []

        # When/Then
        with pytest.raises(ValueError, match="At least one detector is required"):
            EnsembleDetector(detectors)

    def test_detect_all_tables_returns_candidates(self) -> None:
        """detect_all_tables should return TableCandidate list."""
        # Given
        mock_detector = MagicMock()
        mock_detector.name = "mock_detector"
        mock_detector.detect.return_value = [
            TableCandidate(
                page=1,
                bbox=BBox(0, 0, 100, 100),
                detector="mock_detector",
            )
        ]

        ensemble = EnsembleDetector([mock_detector])

        # When
        result = ensemble.detect_all_tables("/path/to/test.pdf")

        # Then
        assert len(result) == 1
        assert isinstance(result[0], TableCandidate)
        mock_detector.detect.assert_called_once_with("/path/to/test.pdf", None)

    def test_detect_financial_tables_returns_classified(self) -> None:
        """detect_financial_tables should return FinancialTable list."""
        # Given
        mock_detector = MagicMock()
        mock_detector.name = "mock_detector"
        mock_detector.detect.return_value = [
            TableCandidate(
                page=1,
                bbox=BBox(50, 100, 500, 400),
                detector="mock_detector",
                text_content="매출액 1,234 영업이익 567 당기순이익 890 2024 2025E",
            )
        ]

        mock_classifier = MagicMock()
        mock_classifier.classify.return_value = FinancialTable(
            page=1,
            bbox=BBox(50, 100, 500, 400),
            category="income_statement",
            confidence=0.8,
            matched_keywords=["매출액", "영업이익"],
            detector_source="mock_detector",
        )

        ensemble = EnsembleDetector([mock_detector], classifier=mock_classifier)

        # When
        result = ensemble.detect_financial_tables("/path/to/test.pdf")

        # Then
        assert len(result) == 1
        assert isinstance(result[0], FinancialTable)
        assert result[0].category == "income_statement"

    def test_detector_failure_handled_gracefully(self) -> None:
        """Individual detector failure should not stop other detectors."""
        # Given
        failing_detector = MagicMock()
        failing_detector.name = "failing_detector"
        failing_detector.detect.side_effect = Exception("Detector error")

        working_detector = MagicMock()
        working_detector.name = "working_detector"
        working_detector.detect.return_value = [
            TableCandidate(
                page=1,
                bbox=BBox(0, 0, 100, 100),
                detector="working_detector",
            )
        ]

        ensemble = EnsembleDetector([failing_detector, working_detector])

        # When
        result = ensemble.detect_all_tables("/path/to/test.pdf")

        # Then
        assert len(result) == 1
        assert result[0].detector == "working_detector"

    def test_results_sorted_by_confidence(self) -> None:
        """Results should be sorted by confidence (descending), then page."""
        # Given
        mock_detector = MagicMock()
        mock_detector.name = "mock_detector"
        mock_detector.detect.return_value = [
            TableCandidate(page=1, bbox=BBox(0, 0, 100, 100), detector="mock"),
            TableCandidate(page=2, bbox=BBox(0, 0, 100, 100), detector="mock"),
            TableCandidate(page=3, bbox=BBox(0, 0, 100, 100), detector="mock"),
        ]

        mock_classifier = MagicMock()
        # Return different confidence for each call
        mock_classifier.classify.side_effect = [
            FinancialTable(
                page=1,
                bbox=BBox(0, 0, 100, 100),
                category="income_statement",
                confidence=0.5,
                matched_keywords=[],
                detector_source="mock",
            ),
            FinancialTable(
                page=2,
                bbox=BBox(0, 0, 100, 100),
                category="balance_sheet",
                confidence=0.9,  # Highest
                matched_keywords=[],
                detector_source="mock",
            ),
            FinancialTable(
                page=3,
                bbox=BBox(0, 0, 100, 100),
                category="cash_flow",
                confidence=0.7,
                matched_keywords=[],
                detector_source="mock",
            ),
        ]

        ensemble = EnsembleDetector([mock_detector], classifier=mock_classifier)

        # When
        result = ensemble.detect_financial_tables("/path/to/test.pdf")

        # Then
        assert len(result) == 3
        assert result[0].confidence == 0.9  # Highest first
        assert result[1].confidence == 0.7
        assert result[2].confidence == 0.5

    def test_same_confidence_sorted_by_page(self) -> None:
        """Results with same confidence should be sorted by page ascending."""
        # Given
        mock_detector = MagicMock()
        mock_detector.name = "mock_detector"
        mock_detector.detect.return_value = [
            TableCandidate(page=3, bbox=BBox(0, 0, 100, 100), detector="mock"),
            TableCandidate(page=1, bbox=BBox(200, 0, 300, 100), detector="mock"),
            TableCandidate(page=2, bbox=BBox(400, 0, 500, 100), detector="mock"),
        ]

        mock_classifier = MagicMock()
        mock_classifier.classify.side_effect = [
            FinancialTable(
                page=3,
                bbox=BBox(0, 0, 100, 100),
                category="a",
                confidence=0.8,
                matched_keywords=[],
                detector_source="mock",
            ),
            FinancialTable(
                page=1,
                bbox=BBox(200, 0, 300, 100),
                category="b",
                confidence=0.8,  # Same confidence
                matched_keywords=[],
                detector_source="mock",
            ),
            FinancialTable(
                page=2,
                bbox=BBox(400, 0, 500, 100),
                category="c",
                confidence=0.8,  # Same confidence
                matched_keywords=[],
                detector_source="mock",
            ),
        ]

        ensemble = EnsembleDetector([mock_detector], classifier=mock_classifier)

        # When
        result = ensemble.detect_financial_tables("/path/to/test.pdf")

        # Then
        assert len(result) == 3
        assert result[0].page == 1
        assert result[1].page == 2
        assert result[2].page == 3

    def test_none_classifications_filtered_out(self) -> None:
        """Candidates that don't classify as financial tables should be filtered."""
        # Given
        mock_detector = MagicMock()
        mock_detector.name = "mock_detector"
        mock_detector.detect.return_value = [
            TableCandidate(page=1, bbox=BBox(0, 0, 100, 100), detector="mock"),
            TableCandidate(page=2, bbox=BBox(0, 0, 100, 100), detector="mock"),
        ]

        mock_classifier = MagicMock()
        mock_classifier.classify.side_effect = [
            None,  # First candidate not classified
            FinancialTable(
                page=2,
                bbox=BBox(0, 0, 100, 100),
                category="income_statement",
                confidence=0.8,
                matched_keywords=[],
                detector_source="mock",
            ),
        ]

        ensemble = EnsembleDetector([mock_detector], classifier=mock_classifier)

        # When
        result = ensemble.detect_financial_tables("/path/to/test.pdf")

        # Then
        assert len(result) == 1
        assert result[0].page == 2

    def test_multiple_detectors_results_merged(self) -> None:
        """Results from multiple detectors should be merged."""
        # Given
        detector_a = MagicMock()
        detector_a.name = "detector_a"
        detector_a.detect.return_value = [
            TableCandidate(
                page=1,
                bbox=BBox(0, 0, 100, 100),
                detector="detector_a",
            )
        ]

        detector_b = MagicMock()
        detector_b.name = "detector_b"
        detector_b.detect.return_value = [
            TableCandidate(
                page=1,
                bbox=BBox(10, 10, 110, 110),  # Overlapping with detector_a
                detector="detector_b",
            ),
            TableCandidate(
                page=2,
                bbox=BBox(0, 0, 100, 100),  # Different page
                detector="detector_b",
            ),
        ]

        ensemble = EnsembleDetector([detector_a, detector_b])

        # When
        result = ensemble.detect_all_tables("/path/to/test.pdf")

        # Then
        # Overlapping candidates on page 1 merged, page 2 separate
        assert len(result) == 2

    def test_pages_parameter_passed_to_detectors(self) -> None:
        """Pages parameter should be passed to all detectors."""
        # Given
        mock_detector = MagicMock()
        mock_detector.name = "mock_detector"
        mock_detector.detect.return_value = []

        ensemble = EnsembleDetector([mock_detector])

        # When
        ensemble.detect_all_tables("/path/to/test.pdf", pages=[1, 3, 5])

        # Then
        mock_detector.detect.assert_called_once_with("/path/to/test.pdf", [1, 3, 5])

    def test_default_classifier_used_when_none_provided(self) -> None:
        """Default FinancialTableClassifier should be used when not provided."""
        # Given
        mock_detector = MagicMock()
        mock_detector.name = "mock_detector"
        mock_detector.detect.return_value = []

        # When
        ensemble = EnsembleDetector([mock_detector])

        # Then
        from fin_stat_table_detector.classifiers.financial import (
            FinancialTableClassifier,
        )

        assert isinstance(ensemble.classifier, FinancialTableClassifier)

    def test_custom_iou_threshold(self) -> None:
        """Custom IoU threshold should be used for merging."""
        # Given
        mock_detector = MagicMock()
        mock_detector.name = "mock_detector"
        # Two candidates with partial overlap
        mock_detector.detect.return_value = [
            TableCandidate(
                page=1,
                bbox=BBox(0, 0, 100, 100),
                detector="mock",
            ),
            TableCandidate(
                page=1,
                bbox=BBox(80, 80, 180, 180),  # Low overlap
                detector="mock",
            ),
        ]

        # High threshold - won't merge
        ensemble_high = EnsembleDetector([mock_detector], iou_threshold=0.5)
        result_high = ensemble_high.detect_all_tables("/test.pdf")

        # Low threshold - will merge
        mock_detector.detect.return_value = [
            TableCandidate(
                page=1,
                bbox=BBox(0, 0, 100, 100),
                detector="mock",
            ),
            TableCandidate(
                page=1,
                bbox=BBox(80, 80, 180, 180),  # Low overlap
                detector="mock",
            ),
        ]
        ensemble_low = EnsembleDetector([mock_detector], iou_threshold=0.01)
        result_low = ensemble_low.detect_all_tables("/test.pdf")

        # Then
        assert len(result_high) == 2  # Not merged with high threshold
        assert len(result_low) == 1  # Merged with low threshold
