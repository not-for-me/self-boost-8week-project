"""Tests for UnionFind data structure."""

from fin_stat_table_detector.utils.union_find import UnionFind


class TestUnionFind:
    """UnionFind 자료구조 테스트."""

    def test_initial_state_each_element_is_own_parent(self) -> None:
        """초기 상태에서 각 원소는 자기 자신이 부모."""
        # Given
        uf = UnionFind(5)

        # Then
        for i in range(5):
            assert uf.find(i) == i

    def test_union_merges_two_sets(self) -> None:
        """union 연산으로 두 집합이 병합됨."""
        # Given
        uf = UnionFind(5)

        # When
        result = uf.union(0, 1)

        # Then
        assert result is True
        assert uf.find(0) == uf.find(1)

    def test_union_returns_false_if_already_same_set(self) -> None:
        """이미 같은 집합이면 False 반환."""
        # Given
        uf = UnionFind(5)
        uf.union(0, 1)

        # When
        result = uf.union(0, 1)

        # Then
        assert result is False

    def test_transitive_union(self) -> None:
        """전이적 병합: A-B 병합, B-C 병합 → A, B, C 같은 그룹."""
        # Given
        uf = UnionFind(5)

        # When
        uf.union(0, 1)  # {0, 1}
        uf.union(1, 2)  # {0, 1, 2}

        # Then
        assert uf.find(0) == uf.find(2)  # A와 C도 같은 그룹

    def test_connected_returns_true_for_same_set(self) -> None:
        """같은 집합에 속하면 connected가 True."""
        # Given
        uf = UnionFind(5)
        uf.union(0, 1)

        # When / Then
        assert uf.connected(0, 1) is True

    def test_connected_returns_false_for_different_sets(self) -> None:
        """다른 집합에 속하면 connected가 False."""
        # Given
        uf = UnionFind(5)
        uf.union(0, 1)

        # When / Then
        assert uf.connected(0, 2) is False

    def test_get_groups_returns_all_sets(self) -> None:
        """get_groups()가 모든 집합을 올바르게 반환."""
        # Given
        uf = UnionFind(5)
        uf.union(0, 1)
        uf.union(2, 3)
        # 4는 독립

        # When
        groups = uf.get_groups()

        # Then
        group_sets = [set(members) for members in groups.values()]
        assert {0, 1} in group_sets
        assert {2, 3} in group_sets
        assert {4} in group_sets

    def test_get_groups_single_element(self) -> None:
        """단일 원소도 그룹으로 반환."""
        # Given
        uf = UnionFind(3)

        # When
        groups = uf.get_groups()

        # Then
        assert len(groups) == 3
        for members in groups.values():
            assert len(members) == 1

    def test_path_compression_works(self) -> None:
        """경로 압축이 동작함."""
        # Given
        uf = UnionFind(4)
        uf.union(0, 1)
        uf.union(1, 2)
        uf.union(2, 3)

        # When - find(3)을 호출하면 경로 압축 발생
        root = uf.find(3)

        # Then - 모든 원소가 같은 루트를 가짐
        for i in range(4):
            assert uf.find(i) == root

    def test_large_union_find(self) -> None:
        """큰 크기의 UnionFind도 정상 동작."""
        # Given
        n = 1000
        uf = UnionFind(n)

        # When - 모든 짝수를 하나의 집합으로
        for i in range(0, n - 2, 2):
            uf.union(i, i + 2)

        # Then
        groups = uf.get_groups()
        even_group = None
        for root, members in groups.items():
            if 0 in members:
                even_group = set(members)
                break

        assert even_group is not None
        assert all(x % 2 == 0 for x in even_group)
        assert len(even_group) == n // 2
