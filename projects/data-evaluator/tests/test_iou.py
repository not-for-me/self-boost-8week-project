"""Tests for IoU calculation."""

import pytest

from data_evaluator.metrics.iou import (
    calculate_intersection_area,
    calculate_iou,
    calculate_union_area,
)
from data_evaluator.models import BBox


class TestCalculateIntersectionArea:
    """Tests for calculate_intersection_area function."""

    def test_overlapping_boxes_returns_intersection(self) -> None:
        """Given overlapping boxes, should return correct intersection area."""
        # Box1: (0,0) to (20,20) = 400 area
        # Box2: (10,10) to (30,30) = 400 area
        # Intersection: (10,10) to (20,20) = 100 area
        bbox1 = BBox(x=0, y=0, width=20, height=20)
        bbox2 = BBox(x=10, y=10, width=20, height=20)

        result = calculate_intersection_area(bbox1, bbox2)

        assert result == 100.0

    def test_non_overlapping_boxes_returns_zero(self) -> None:
        """Given non-overlapping boxes, should return 0."""
        bbox1 = BBox(x=0, y=0, width=10, height=10)
        bbox2 = BBox(x=20, y=20, width=10, height=10)

        result = calculate_intersection_area(bbox1, bbox2)

        assert result == 0.0

    def test_touching_boxes_returns_zero(self) -> None:
        """Given boxes that touch but don't overlap, should return 0."""
        bbox1 = BBox(x=0, y=0, width=10, height=10)
        bbox2 = BBox(x=10, y=0, width=10, height=10)

        result = calculate_intersection_area(bbox1, bbox2)

        assert result == 0.0

    def test_contained_box_returns_smaller_area(self) -> None:
        """Given one box inside another, should return smaller box area."""
        bbox1 = BBox(x=0, y=0, width=100, height=100)
        bbox2 = BBox(x=25, y=25, width=50, height=50)

        result = calculate_intersection_area(bbox1, bbox2)

        assert result == 2500.0  # 50 * 50

    def test_identical_boxes_returns_full_area(self) -> None:
        """Given identical boxes, should return full area."""
        bbox1 = BBox(x=10, y=10, width=20, height=30)
        bbox2 = BBox(x=10, y=10, width=20, height=30)

        result = calculate_intersection_area(bbox1, bbox2)

        assert result == 600.0  # 20 * 30


class TestCalculateUnionArea:
    """Tests for calculate_union_area function."""

    def test_overlapping_boxes_returns_union(self) -> None:
        """Given overlapping boxes, should return correct union area."""
        # Box1: 400, Box2: 400, Intersection: 100
        # Union = 400 + 400 - 100 = 700
        bbox1 = BBox(x=0, y=0, width=20, height=20)
        bbox2 = BBox(x=10, y=10, width=20, height=20)

        result = calculate_union_area(bbox1, bbox2)

        assert result == 700.0

    def test_non_overlapping_boxes_returns_sum(self) -> None:
        """Given non-overlapping boxes, should return sum of areas."""
        bbox1 = BBox(x=0, y=0, width=10, height=10)
        bbox2 = BBox(x=20, y=20, width=10, height=10)

        result = calculate_union_area(bbox1, bbox2)

        assert result == 200.0  # 100 + 100

    def test_identical_boxes_returns_single_area(self) -> None:
        """Given identical boxes, should return single box area."""
        bbox1 = BBox(x=10, y=10, width=20, height=30)
        bbox2 = BBox(x=10, y=10, width=20, height=30)

        result = calculate_union_area(bbox1, bbox2)

        assert result == 600.0


class TestCalculateIoU:
    """Tests for calculate_iou function."""

    def test_identical_boxes_returns_one(self) -> None:
        """Given identical boxes, IoU should be 1.0."""
        bbox1 = BBox(x=10, y=10, width=20, height=30)
        bbox2 = BBox(x=10, y=10, width=20, height=30)

        result = calculate_iou(bbox1, bbox2)

        assert result == 1.0

    def test_non_overlapping_boxes_returns_zero(self) -> None:
        """Given non-overlapping boxes, IoU should be 0.0."""
        bbox1 = BBox(x=0, y=0, width=10, height=10)
        bbox2 = BBox(x=20, y=20, width=10, height=10)

        result = calculate_iou(bbox1, bbox2)

        assert result == 0.0

    def test_partial_overlap_returns_correct_iou(self) -> None:
        """Given partial overlap, IoU should be intersection/union."""
        # Box1: 400, Box2: 400, Intersection: 100, Union: 700
        # IoU = 100 / 700 ≈ 0.1428
        bbox1 = BBox(x=0, y=0, width=20, height=20)
        bbox2 = BBox(x=10, y=10, width=20, height=20)

        result = calculate_iou(bbox1, bbox2)

        assert result == pytest.approx(100.0 / 700.0)

    def test_fifty_percent_overlap(self) -> None:
        """Given 50% overlap scenario, IoU should be calculated correctly."""
        # Box1: (0,0) to (10,20) = 200
        # Box2: (5,0) to (15,20) = 200
        # Intersection: (5,0) to (10,20) = 100
        # Union: 200 + 200 - 100 = 300
        # IoU = 100/300 = 1/3
        bbox1 = BBox(x=0, y=0, width=10, height=20)
        bbox2 = BBox(x=5, y=0, width=10, height=20)

        result = calculate_iou(bbox1, bbox2)

        assert result == pytest.approx(1.0 / 3.0)

    def test_contained_box_iou(self) -> None:
        """Given one box inside another, IoU should be smaller/larger area."""
        # Large: 10000, Small: 2500, Intersection: 2500, Union: 10000
        # IoU = 2500 / 10000 = 0.25
        bbox_large = BBox(x=0, y=0, width=100, height=100)
        bbox_small = BBox(x=25, y=25, width=50, height=50)

        result = calculate_iou(bbox_large, bbox_small)

        assert result == 0.25

    def test_zero_area_box_returns_zero(self) -> None:
        """Given a zero-area box, IoU should be 0."""
        bbox1 = BBox(x=10, y=10, width=0, height=0)
        bbox2 = BBox(x=10, y=10, width=20, height=20)

        result = calculate_iou(bbox1, bbox2)

        assert result == 0.0

    def test_both_zero_area_boxes_returns_zero(self) -> None:
        """Given both zero-area boxes, IoU should be 0."""
        bbox1 = BBox(x=10, y=10, width=0, height=0)
        bbox2 = BBox(x=10, y=10, width=0, height=0)

        result = calculate_iou(bbox1, bbox2)

        assert result == 0.0
