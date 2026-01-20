"""Union-Find (Disjoint Set Union) data structure.

경로 압축(Path Compression)과 랭크 기반 합집합(Union by Rank)을 적용하여
거의 O(1) 시간 복잡도로 동작합니다.
"""

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
