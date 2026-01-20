"""Spatial Index using Interval Trees.

X/Y 축 Interval Tree를 사용하여 2D 영역 쿼리를 O(log n)에 수행합니다.
"""

from intervaltree import IntervalTree

from fin_stat_table_detector.models import BBox


class SpatialIndex:
    """X/Y 축 Interval Tree로 2D 영역 쿼리.

    두 개의 Interval Tree(X축, Y축)를 사용하여
    겹치는 bbox를 빠르게 검색합니다.

    Attributes:
        x_tree: X축 구간을 저장하는 Interval Tree
        y_tree: Y축 구간을 저장하는 Interval Tree
    """

    def __init__(self) -> None:
        """SpatialIndex 초기화."""
        self.x_tree: IntervalTree = IntervalTree()
        self.y_tree: IntervalTree = IntervalTree()

    def insert(self, idx: int, bbox: BBox) -> None:
        """bbox를 인덱스에 추가.

        Args:
            idx: bbox의 고유 인덱스
            bbox: 추가할 영역
        """
        # intervaltree는 [begin, end) 반개구간 사용
        # 경계 포함을 위해 end에 작은 값 추가
        epsilon = 0.001
        self.x_tree.addi(bbox.x0, bbox.x1 + epsilon, idx)
        self.y_tree.addi(bbox.y0, bbox.y1 + epsilon, idx)

    def query_overlapping(self, bbox: BBox) -> set[int]:
        """bbox와 겹칠 가능성 있는 후보 인덱스 반환.

        X축과 Y축 모두 겹쳐야 실제 2D 영역이 겹침

        Args:
            bbox: 쿼리할 영역

        Returns:
            겹칠 가능성 있는 bbox의 인덱스 집합
        """
        epsilon = 0.001
        x_candidates = {
            iv.data for iv in self.x_tree.overlap(bbox.x0, bbox.x1 + epsilon)
        }
        y_candidates = {
            iv.data for iv in self.y_tree.overlap(bbox.y0, bbox.y1 + epsilon)
        }
        return x_candidates & y_candidates

    def clear(self) -> None:
        """인덱스 초기화."""
        self.x_tree.clear()
        self.y_tree.clear()
