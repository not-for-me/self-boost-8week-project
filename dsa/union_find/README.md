# Union-Find (Disjoint Set Union)

> 서로소 집합을 효율적으로 관리하는 자료구조 - 클러스터 병합, Transitive Closure 계산에 필수

---

## 1. 개념

### 문제: Transitive Closure

MinHash + LSH로 유사한 문서 쌍을 찾았다면, 이제 **연결된 모든 문서를 같은 그룹**으로 묶어야 합니다.

```
유사 쌍: (A, B), (B, C), (D, E)

→ 클러스터 1: {A, B, C}  (A-B 유사, B-C 유사 → A-C도 같은 클러스터)
→ 클러스터 2: {D, E}
```

### Naive 접근의 문제

```python
# 그래프 탐색으로 연결 요소 찾기
def find_clusters_naive(pairs):
    # DFS/BFS로 연결 요소 찾기
    # 시간: O(V + E) per query
    # 동적 병합 시: 비효율적
```

### 해결책: Union-Find

- **union(x, y)**: x와 y를 같은 집합으로 병합
- **find(x)**: x가 속한 집합의 대표(루트) 반환
- **경로 압축 + 랭크 기반 합집합**: 거의 O(1) 시간 복잡도

---

## 2. 핵심 최적화

### 경로 압축 (Path Compression)

find 연산 시 만나는 모든 노드를 루트에 직접 연결:

```
Before find(4):        After find(4):
    0                      0
    |                    / | \
    1                   1  2  4
    |                   |
    2                   3
    |
    3
    |
    4
```

### 랭크 기반 합집합 (Union by Rank)

항상 작은 트리를 큰 트리 아래에 붙임:

```
union(small_tree, big_tree):

    [big_tree]
        |
    [small_tree]   ← 깊이가 최소화됨
```

### 시간 복잡도

```
경로 압축 + 랭크 기반 = O(α(n)) ≈ O(1)

α(n) = 역 아커만 함수 (실질적으로 4 이하)
```

---

## 3. 구현

### 기본 구현

```python
from collections import defaultdict


class UnionFind:
    """경로 압축 + 랭크 기반 Union-Find.

    Attributes:
        parent: 각 노드의 부모 노드 인덱스
        rank: 각 노드의 트리 깊이 추정치
    """

    def __init__(self, n: int) -> None:
        """UnionFind 초기화.

        Args:
            n: 원소 개수 (0부터 n-1까지)
        """
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x: int) -> int:
        """x가 속한 집합의 대표(루트) 찾기.

        경로 압축을 적용하여 찾는 과정에서 만나는 모든 노드를
        루트에 직접 연결합니다.

        Args:
            x: 찾을 원소의 인덱스

        Returns:
            x가 속한 집합의 대표(루트) 인덱스
        """
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x: int, y: int) -> bool:
        """x와 y를 같은 집합으로 합치기.

        랭크 기반 합집합을 적용하여 깊이가 낮은 트리를
        깊이가 높은 트리 아래에 붙입니다.

        Args:
            x: 첫 번째 원소의 인덱스
            y: 두 번째 원소의 인덱스

        Returns:
            True: 실제로 병합됨
            False: 이미 같은 집합
        """
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return False

        # 랭크 기반 합집합: 작은 트리를 큰 트리 아래에
        if self.rank[rx] < self.rank[ry]:
            rx, ry = ry, rx
        self.parent[ry] = rx
        if self.rank[rx] == self.rank[ry]:
            self.rank[rx] += 1
        return True

    def connected(self, x: int, y: int) -> bool:
        """x와 y가 같은 집합에 속하는지 확인.

        Args:
            x: 첫 번째 원소의 인덱스
            y: 두 번째 원소의 인덱스

        Returns:
            같은 집합이면 True, 아니면 False
        """
        return self.find(x) == self.find(y)

    def get_groups(self) -> dict[int, list[int]]:
        """모든 집합을 {대표: [멤버들]} 형태로 반환.

        Returns:
            대표 인덱스를 키로, 멤버 인덱스 리스트를 값으로 하는 딕셔너리
        """
        groups: dict[int, list[int]] = defaultdict(list)
        for i in range(len(self.parent)):
            groups[self.find(i)].append(i)
        return dict(groups)
```

---

## 4. 테스트 코드

```python
"""Tests for UnionFind data structure."""

import pytest
from union_find import UnionFind


class TestUnionFindInitialization:
    """UnionFind 초기화 테스트."""

    def test_initial_state_each_element_is_own_parent(self) -> None:
        """초기 상태에서 각 원소는 자기 자신이 부모."""
        # Given
        uf = UnionFind(5)

        # Then
        for i in range(5):
            assert uf.find(i) == i


class TestUnionOperation:
    """union 연산 테스트."""

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


class TestConnectedOperation:
    """connected 연산 테스트."""

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


class TestGetGroups:
    """get_groups 메서드 테스트."""

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


class TestPathCompression:
    """경로 압축 테스트."""

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


class TestLargeScale:
    """대규모 데이터 테스트."""

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
```

---

## 5. 실전 활용: MinHash와 함께 사용

### 문서 중복 제거 파이프라인

```python
def deduplicate_with_union_find(similar_pairs: list[tuple[str, str]],
                                 all_doc_ids: list[str]) -> dict[str, list[str]]:
    """
    유사 문서 쌍에서 클러스터 생성

    Args:
        similar_pairs: MinHash/LSH로 찾은 유사 쌍 [(doc1, doc2), ...]
        all_doc_ids: 모든 문서 ID

    Returns:
        {대표 문서 ID: [클러스터 멤버들]}
    """
    # 문서 ID → 인덱스 매핑
    id_to_idx = {doc_id: i for i, doc_id in enumerate(all_doc_ids)}
    idx_to_id = {i: doc_id for doc_id, i in id_to_idx.items()}

    # Union-Find 초기화
    uf = UnionFind(len(all_doc_ids))

    # 유사 쌍 병합
    for doc1, doc2 in similar_pairs:
        if doc1 in id_to_idx and doc2 in id_to_idx:
            uf.union(id_to_idx[doc1], id_to_idx[doc2])

    # 클러스터 추출
    clusters = {}
    for root_idx, member_indices in uf.get_groups().items():
        root_id = idx_to_id[root_idx]
        clusters[root_id] = [idx_to_id[i] for i in member_indices]

    return clusters


# 사용 예시
similar_pairs = [
    ("doc_001", "doc_005"),  # 유사
    ("doc_005", "doc_012"),  # 유사 → doc_001, doc_005, doc_012 같은 클러스터
    ("doc_003", "doc_007"),  # 별도 클러스터
]
all_docs = ["doc_001", "doc_003", "doc_005", "doc_007", "doc_012", "doc_099"]

clusters = deduplicate_with_union_find(similar_pairs, all_docs)
# 결과:
# {
#     "doc_001": ["doc_001", "doc_005", "doc_012"],  # Transitive closure
#     "doc_003": ["doc_003", "doc_007"],
#     "doc_099": ["doc_099"],  # 독립 문서
# }
```

---

## 6. fin-stat-table-detector 적용 사례

### 테이블 셀 병합

재무제표 테이블 감지에서 Union-Find를 사용하여 **인접한 셀들을 병합**:

```python
# 테이블 감지 결과에서 겹치는 bbox들을 병합
def merge_overlapping_boxes(boxes: list[BBox], iou_threshold: float = 0.5):
    """IoU가 높은 박스들을 같은 그룹으로 병합"""
    n = len(boxes)
    uf = UnionFind(n)

    for i in range(n):
        for j in range(i + 1, n):
            if calculate_iou(boxes[i], boxes[j]) >= iou_threshold:
                uf.union(i, j)

    return uf.get_groups()
```

---

## 7. 시간/공간 복잡도

| 연산 | 시간 복잡도 | 비고 |
|------|------------|------|
| 초기화 | O(n) | n개 원소 |
| find | O(α(n)) ≈ O(1) | 경로 압축 |
| union | O(α(n)) ≈ O(1) | 랭크 기반 |
| connected | O(α(n)) ≈ O(1) | find 2번 |
| get_groups | O(n × α(n)) | 모든 원소 순회 |

**공간 복잡도**: O(n) - parent, rank 배열

---

## 8. 관련 자료구조

| 자료구조 | 용도 | Union-Find와의 관계 |
|----------|------|---------------------|
| MinHash | 유사 문서 쌍 탐지 | 쌍 → Union-Find로 클러스터링 |
| LSH | 후보 쌍 필터링 | MinHash와 함께 사용 |
| Graph BFS/DFS | 연결 요소 탐색 | Union-Find가 동적 병합에 유리 |

---

## 참고 자료

- [Introduction to Algorithms (CLRS) - Ch.21 Data Structures for Disjoint Sets](https://mitpress.mit.edu/9780262046305/introduction-to-algorithms/)
- [Deduplicating Training Data Makes Language Models Better](https://arxiv.org/abs/2107.06499)
- [Mining of Massive Datasets - Clustering](http://www.mmds.org/)
