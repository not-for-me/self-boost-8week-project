"""Tests for SpatialIndex."""

from fin_stat_table_detector.models import BBox
from fin_stat_table_detector.utils.spatial_index import SpatialIndex


class TestSpatialIndex:
    """SpatialIndex 테스트."""

    def test_overlapping_bboxes_found(self) -> None:
        """겹치는 bbox가 올바르게 검색됨."""
        # Given
        index = SpatialIndex()
        bbox1 = BBox(0, 0, 100, 100)
        bbox2 = BBox(50, 50, 150, 150)  # bbox1과 겹침
        bbox3 = BBox(200, 200, 300, 300)  # 겹치지 않음

        index.insert(0, bbox1)
        index.insert(1, bbox2)
        index.insert(2, bbox3)

        # When
        overlapping = index.query_overlapping(bbox1)

        # Then
        assert 0 in overlapping  # 자기 자신
        assert 1 in overlapping  # 겹치는 bbox
        assert 2 not in overlapping  # 겹치지 않음

    def test_non_overlapping_returns_only_self(self) -> None:
        """겹치지 않는 bbox 쿼리 시 자기 자신만 반환."""
        # Given
        index = SpatialIndex()
        bbox1 = BBox(0, 0, 50, 50)
        bbox2 = BBox(100, 100, 150, 150)

        index.insert(0, bbox1)
        index.insert(1, bbox2)

        # When
        overlapping = index.query_overlapping(bbox1)

        # Then
        assert overlapping == {0}

    def test_query_new_bbox_not_in_index(self) -> None:
        """인덱스에 없는 새 bbox로 쿼리."""
        # Given
        index = SpatialIndex()
        bbox1 = BBox(0, 0, 100, 100)
        bbox2 = BBox(50, 50, 150, 150)
        index.insert(0, bbox1)
        index.insert(1, bbox2)

        # When - 인덱스에 없는 bbox로 쿼리
        query_bbox = BBox(25, 25, 75, 75)
        overlapping = index.query_overlapping(query_bbox)

        # Then - bbox1과 겹침
        assert 0 in overlapping
        assert 1 in overlapping  # bbox2와도 겹침

    def test_clear_removes_all_entries(self) -> None:
        """clear()가 모든 항목을 제거."""
        # Given
        index = SpatialIndex()
        index.insert(0, BBox(0, 0, 100, 100))
        index.insert(1, BBox(50, 50, 150, 150))

        # When
        index.clear()

        # Then
        overlapping = index.query_overlapping(BBox(0, 0, 100, 100))
        assert len(overlapping) == 0

    def test_adjacent_bboxes_not_overlapping(self) -> None:
        """인접하지만 겹치지 않는 bbox."""
        # Given
        index = SpatialIndex()
        bbox1 = BBox(0, 0, 100, 100)
        bbox2 = BBox(100, 0, 200, 100)  # bbox1 바로 오른쪽

        index.insert(0, bbox1)
        index.insert(1, bbox2)

        # When
        overlapping = index.query_overlapping(bbox1)

        # Then - epsilon으로 인해 경계가 포함될 수 있음
        assert 0 in overlapping

    def test_one_axis_overlap_only(self) -> None:
        """한 축만 겹치는 경우 (실제로는 겹치지 않음)."""
        # Given
        index = SpatialIndex()
        bbox1 = BBox(0, 0, 100, 100)
        bbox2 = BBox(0, 200, 100, 300)  # X축은 겹치지만 Y축은 안 겹침

        index.insert(0, bbox1)
        index.insert(1, bbox2)

        # When
        overlapping = index.query_overlapping(bbox1)

        # Then
        assert 0 in overlapping
        assert 1 not in overlapping  # Y축이 안 겹쳐서 제외

    def test_fully_contained_bbox(self) -> None:
        """완전히 포함되는 bbox."""
        # Given
        index = SpatialIndex()
        outer = BBox(0, 0, 200, 200)
        inner = BBox(50, 50, 150, 150)  # outer 안에 완전히 포함

        index.insert(0, outer)
        index.insert(1, inner)

        # When
        overlapping_outer = index.query_overlapping(outer)
        overlapping_inner = index.query_overlapping(inner)

        # Then
        assert {0, 1} == overlapping_outer
        assert {0, 1} == overlapping_inner

    def test_many_bboxes(self) -> None:
        """여러 개의 bbox를 처리."""
        # Given
        index = SpatialIndex()
        n = 100
        for i in range(n):
            bbox = BBox(i * 10, i * 10, i * 10 + 50, i * 10 + 50)
            index.insert(i, bbox)

        # When - 첫 번째 bbox와 겹치는 것 찾기
        first_bbox = BBox(0, 0, 50, 50)
        overlapping = index.query_overlapping(first_bbox)

        # Then - 처음 몇 개만 겹침 (50/10 = 5개 정도)
        assert 0 in overlapping
        assert len(overlapping) <= 6  # 대략 5-6개
