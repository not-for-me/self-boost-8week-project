# TECH_SPEC: Ensemble Detector and Merge Logic

## 1. 개요

본 문서는 다중 탐지기 앙상블과 중복 제거 로직의 스펙을 정의합니다.

---

## 2. 중복 제거의 필요성

### 2.1 문제 상황

여러 탐지기가 동일한 표를 탐지할 수 있습니다:
- pdfplumber와 camelot이 같은 표를 탐지
- 탐지된 bbox가 약간씩 다름 (좌표 오차)

### 2.2 전이적 중첩 문제

단순 쌍별 비교로는 해결할 수 없는 경우가 있습니다:

```
A↔B 겹침, B↔C 겹침 → A↔C는 직접 겹치지 않아도 같은 표

┌─────────┐
│    A    │
│    ┌────┼────┐
│    │ B  │    │
└────┼────┘    │
     │    ┌────┼────┐
     │    │    │ C  │
     └────┼────┼────┘
          └────┘

단순 IoU 비교: A-B 병합, C 별도 (잘못됨)
Union-Find: A, B, C 모두 같은 그룹 (정확함)
```

---

## 3. Union-Find 자료구조

### 3.1 개념

Union-Find(또는 Disjoint Set Union)는 서로소 집합을 효율적으로 관리하는 자료구조입니다.

**주요 연산:**
- `find(x)`: x가 속한 집합의 대표(루트)를 찾음
- `union(x, y)`: x와 y를 같은 집합으로 합침

### 3.2 구현 스펙

```python
from collections import defaultdict

class UnionFind:
    """경로 압축 + 랭크 기반 Union-Find"""

    def __init__(self, n: int):
        """
        Args:
            n: 원소 개수 (0부터 n-1까지)
        """
        self.parent = list(range(n))  # 각 노드의 부모 (초기: 자기 자신)
        self.rank = [0] * n           # 트리 깊이 추정치

    def find(self, x: int) -> int:
        """
        x가 속한 집합의 대표(루트) 찾기

        경로 압축(Path Compression) 적용:
        찾는 과정에서 만나는 모든 노드를 루트에 직접 연결
        """
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])  # 경로 압축
        return self.parent[x]

    def union(self, x: int, y: int) -> bool:
        """
        x와 y를 같은 집합으로 합치기

        랭크 기반 합집합(Union by Rank) 적용:
        깊이가 낮은 트리를 깊이가 높은 트리 아래에 붙임

        Returns:
            True: 실제로 병합됨
            False: 이미 같은 집합
        """
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return False  # 이미 같은 집합

        # 랭크 기반 합집합: 작은 트리를 큰 트리 아래에
        if self.rank[rx] < self.rank[ry]:
            rx, ry = ry, rx
        self.parent[ry] = rx
        if self.rank[rx] == self.rank[ry]:
            self.rank[rx] += 1
        return True

    def connected(self, x: int, y: int) -> bool:
        """x와 y가 같은 집합에 속하는지 확인"""
        return self.find(x) == self.find(y)

    def get_groups(self) -> dict[int, list[int]]:
        """
        모든 집합을 {대표: [멤버들]} 형태로 반환
        """
        groups = defaultdict(list)
        for i in range(len(self.parent)):
            groups[self.find(i)].append(i)
        return dict(groups)
```

### 3.3 시간 복잡도

경로 압축 + 랭크 기반 합집합을 적용하면:
- `find`: O(α(n)) ≈ O(1) (아커만 함수의 역함수)
- `union`: O(α(n)) ≈ O(1)
- `get_groups`: O(n)

---

## 4. Spatial Index (공간 인덱스)

### 4.1 문제

모든 bbox 쌍을 비교하면 O(n²) 시간이 소요됩니다.

### 4.2 해결책

Interval Tree를 사용하여 **겹칠 가능성 있는 후보만** 빠르게 검색합니다.

### 4.3 구현 스펙

```python
from intervaltree import IntervalTree
from fin_stat_table_detector.models import BBox

class SpatialIndex:
    """X/Y 축 Interval Tree로 2D 영역 쿼리"""

    def __init__(self):
        self.x_tree = IntervalTree()
        self.y_tree = IntervalTree()

    def insert(self, idx: int, bbox: BBox) -> None:
        """
        bbox를 인덱스에 추가

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
        """
        bbox와 겹칠 가능성 있는 후보 인덱스 반환

        X축과 Y축 모두 겹쳐야 실제 2D 영역이 겹침
        """
        epsilon = 0.001
        x_candidates = {iv.data for iv in self.x_tree.overlap(bbox.x0, bbox.x1 + epsilon)}
        y_candidates = {iv.data for iv in self.y_tree.overlap(bbox.y0, bbox.y1 + epsilon)}
        return x_candidates & y_candidates  # 교집합

    def clear(self) -> None:
        """인덱스 초기화"""
        self.x_tree.clear()
        self.y_tree.clear()
```

### 4.4 시간 복잡도

- `insert`: O(log n)
- `query_overlapping`: O(log n + k), k는 결과 개수

---

## 5. IoU (Intersection over Union)

### 5.1 개념

두 영역이 얼마나 겹치는지 0~1 사이 값으로 측정합니다.

```
IoU = 교집합 면적 / 합집합 면적
```

### 5.2 구현

```python
def calculate_iou(bbox1: BBox, bbox2: BBox) -> float:
    """
    두 bbox의 IoU 계산

    Returns:
        0.0 ~ 1.0 사이의 값
        - 1.0: 완전히 동일한 영역
        - 0.0: 전혀 겹치지 않음
    """
    # 교집합 영역 계산
    x0 = max(bbox1.x0, bbox2.x0)
    y0 = max(bbox1.y0, bbox2.y0)
    x1 = min(bbox1.x1, bbox2.x1)
    y1 = min(bbox1.y1, bbox2.y1)

    # 겹치지 않는 경우
    if x0 >= x1 or y0 >= y1:
        return 0.0

    intersection = (x1 - x0) * (y1 - y0)
    union = bbox1.area + bbox2.area - intersection

    return intersection / union if union > 0 else 0.0
```

### 5.3 IoU 값의 의미

| IoU 값 | 의미 | 병합 여부 |
|--------|------|----------|
| 1.0 | 완전히 동일 | 병합 |
| 0.5 | 절반 겹침 | 병합 |
| 0.3 | 일부 겹침 | 병합 (임계값) |
| 0.0 | 전혀 안 겹침 | 분리 |

**기본 임계값**: 0.3 (조정 가능)

---

## 6. 통합 병합 알고리즘

### 6.1 알고리즘 개요

```python
def merge_candidates(
    candidates: list[TableCandidate],
    iou_threshold: float = 0.3
) -> list[TableCandidate]:
    """
    Union-Find + Spatial Index 기반 중복 제거

    단계:
    1. 페이지별로 분리
    2. Spatial Index로 겹칠 후보 빠르게 검색
    3. IoU 계산으로 실제 겹침 확인
    4. Union-Find로 전이적 그룹화
    5. 각 그룹에서 대표 선택 (가장 큰 bbox)
    """
    if not candidates:
        return []

    # 페이지별 처리 (다른 페이지는 병합 불가)
    by_page: dict[int, list[tuple[int, TableCandidate]]] = defaultdict(list)
    for i, c in enumerate(candidates):
        by_page[c.page].append((i, c))

    merged = []

    for page, page_items in by_page.items():
        n = len(page_items)
        if n == 1:
            merged.append(page_items[0][1])
            continue

        # 1. Spatial Index 구축
        index = SpatialIndex()
        for local_idx, (_, c) in enumerate(page_items):
            index.insert(local_idx, c.bbox)

        # 2. Union-Find 초기화
        uf = UnionFind(n)

        # 3. 겹치는 쌍 찾아서 union
        for local_idx, (_, c) in enumerate(page_items):
            overlapping = index.query_overlapping(c.bbox)
            for other_idx in overlapping:
                if other_idx <= local_idx:
                    continue  # 중복 비교 방지 (자기 자신 포함)

                other_bbox = page_items[other_idx][1].bbox
                if calculate_iou(c.bbox, other_bbox) > iou_threshold:
                    uf.union(local_idx, other_idx)

        # 4. 그룹별로 대표 선택 (가장 큰 bbox)
        for group_indices in uf.get_groups().values():
            group_candidates = [page_items[i][1] for i in group_indices]
            best = max(group_candidates, key=lambda x: x.bbox.area)
            merged.append(best)

    return merged
```

### 6.2 시간 복잡도 비교

| 방식 | 후보 검색 | 그룹화 | 전체 |
|------|----------|--------|------|
| 단순 IoU 비교 | O(n²) | O(n) | **O(n²)** |
| Union-Find + Spatial Index | O(n log n) | O(n·α(n)) | **O(n log n)** |

n=100개 bbox 기준:
- 단순 방식: ~10,000번 비교
- Union-Find: ~700번 비교 (약 14배 빠름)

---

## 7. EnsembleDetector

### 7.1 개요

여러 탐지기를 조합하여 재무제표 테이블을 탐지하는 통합 클래스입니다.

### 7.2 구현 스펙

```python
from fin_stat_table_detector.detectors.base import AbstractDetector
from fin_stat_table_detector.classifiers.financial import FinancialTableClassifier
from fin_stat_table_detector.models import TableCandidate, FinancialTable

class EnsembleDetector:
    """다중 탐지기 앙상블"""

    def __init__(
        self,
        detectors: list[AbstractDetector],
        iou_threshold: float = 0.3,
        classifier: FinancialTableClassifier | None = None
    ):
        """
        Args:
            detectors: 사용할 탐지기 리스트
            iou_threshold: 중복 제거 IoU 임계값
            classifier: 재무제표 분류기 (None이면 기본값 사용)
        """
        if not detectors:
            raise ValueError("At least one detector is required")

        self.detectors = detectors
        self.iou_threshold = iou_threshold
        self.classifier = classifier or FinancialTableClassifier()

    def detect_all_tables(
        self,
        pdf_path: str,
        pages: list[int] | None = None
    ) -> list[TableCandidate]:
        """
        모든 탐지기로 표 후보 탐지 (분류 없이)

        Returns:
            중복 제거된 TableCandidate 리스트
        """
        all_candidates = []

        # 1. 모든 탐지기 실행
        for detector in self.detectors:
            try:
                candidates = detector.detect(pdf_path, pages)
                all_candidates.extend(candidates)
            except Exception as e:
                # 개별 탐지기 실패는 로깅하고 계속 진행
                print(f"Warning: {detector.name} failed: {e}")

        # 2. 중복 제거
        merged = merge_candidates(all_candidates, self.iou_threshold)

        return merged

    def detect_financial_tables(
        self,
        pdf_path: str,
        pages: list[int] | None = None
    ) -> list[FinancialTable]:
        """
        PDF에서 재무제표 테이블 탐지

        단계:
        1. 모든 탐지기로 표 후보 수집
        2. 중복 제거 (IoU 기반)
        3. 재무제표 분류
        4. 결과 반환

        Returns:
            재무제표로 분류된 FinancialTable 리스트
        """
        # 1-2. 표 후보 탐지 및 중복 제거
        candidates = self.detect_all_tables(pdf_path, pages)

        # 3. 재무제표 분류
        financial_tables = []
        for candidate in candidates:
            result = self.classifier.classify(candidate, pdf_path)
            if result is not None:
                financial_tables.append(result)

        # 4. 신뢰도 순 정렬
        financial_tables.sort(key=lambda x: (-x.confidence, x.page))

        return financial_tables
```

---

## 8. 테스트 케이스

### 8.1 Union-Find 테스트

```python
class TestUnionFind:
    """Union-Find 자료구조 테스트"""

    def test_initial_state_each_element_is_own_parent(self):
        """초기 상태에서 각 원소는 자기 자신이 부모"""
        # Given
        uf = UnionFind(5)

        # Then
        for i in range(5):
            assert uf.find(i) == i

    def test_union_merges_two_sets(self):
        """union 연산으로 두 집합이 병합됨"""
        # Given
        uf = UnionFind(5)

        # When
        uf.union(0, 1)

        # Then
        assert uf.find(0) == uf.find(1)

    def test_transitive_union(self):
        """전이적 병합: A-B 병합, B-C 병합 → A, B, C 같은 그룹"""
        # Given
        uf = UnionFind(5)

        # When
        uf.union(0, 1)  # {0, 1}
        uf.union(1, 2)  # {0, 1, 2}

        # Then
        assert uf.find(0) == uf.find(2)  # A와 C도 같은 그룹

    def test_get_groups_returns_all_sets(self):
        """get_groups()가 모든 집합을 올바르게 반환"""
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
```

### 8.2 Spatial Index 테스트

```python
class TestSpatialIndex:
    """Spatial Index 테스트"""

    def test_overlapping_bboxes_found(self):
        """겹치는 bbox가 올바르게 검색됨"""
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

    def test_non_overlapping_returns_only_self(self):
        """겹치지 않는 bbox 쿼리 시 자기 자신만 반환"""
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
```

### 8.3 IoU 계산 테스트

```python
class TestCalculateIoU:
    """IoU 계산 테스트"""

    def test_identical_boxes_return_one(self):
        """동일한 bbox는 IoU 1.0"""
        # Given
        bbox = BBox(0, 0, 100, 100)

        # When
        iou = calculate_iou(bbox, bbox)

        # Then
        assert iou == 1.0

    def test_non_overlapping_returns_zero(self):
        """겹치지 않으면 IoU 0.0"""
        # Given
        bbox1 = BBox(0, 0, 100, 100)
        bbox2 = BBox(200, 200, 300, 300)

        # When
        iou = calculate_iou(bbox1, bbox2)

        # Then
        assert iou == 0.0

    def test_partial_overlap(self):
        """부분 겹침 IoU 계산"""
        # Given
        bbox1 = BBox(0, 0, 100, 100)    # 면적: 10,000
        bbox2 = BBox(50, 50, 150, 150)  # 면적: 10,000
        # 교집합: (50,50)-(100,100) = 50*50 = 2,500
        # 합집합: 10,000 + 10,000 - 2,500 = 17,500
        # IoU: 2,500 / 17,500 ≈ 0.143

        # When
        iou = calculate_iou(bbox1, bbox2)

        # Then
        assert 0.14 < iou < 0.15
```

### 8.4 병합 로직 테스트

```python
class TestMergeCandidates:
    """중복 제거 병합 테스트"""

    def test_overlapping_candidates_merged(self):
        """겹치는 후보들이 하나로 병합됨"""
        # Given
        candidates = [
            TableCandidate(page=1, bbox=BBox(50, 100, 400, 300), detector="pdfplumber"),
            TableCandidate(page=1, bbox=BBox(48, 98, 402, 305), detector="camelot"),
        ]

        # When
        merged = merge_candidates(candidates, iou_threshold=0.3)

        # Then
        assert len(merged) == 1

    def test_transitive_overlap_merged(self):
        """전이적 겹침도 하나로 병합 (A↔B, B↔C → A,B,C 병합)"""
        # Given
        candidates = [
            TableCandidate(page=1, bbox=BBox(0, 0, 100, 100), detector="a"),    # A
            TableCandidate(page=1, bbox=BBox(70, 70, 170, 170), detector="b"),  # B
            TableCandidate(page=1, bbox=BBox(140, 140, 240, 240), detector="c"), # C
        ]

        # When
        merged = merge_candidates(candidates, iou_threshold=0.1)

        # Then
        assert len(merged) == 1  # 전이적으로 모두 같은 그룹

    def test_different_pages_not_merged(self):
        """다른 페이지의 후보는 병합되지 않음"""
        # Given
        candidates = [
            TableCandidate(page=1, bbox=BBox(50, 100, 400, 300), detector="a"),
            TableCandidate(page=2, bbox=BBox(50, 100, 400, 300), detector="b"),
        ]

        # When
        merged = merge_candidates(candidates, iou_threshold=0.3)

        # Then
        assert len(merged) == 2  # 페이지가 달라서 병합 안됨

    def test_largest_bbox_selected_as_representative(self):
        """그룹 내 가장 큰 bbox가 대표로 선택됨"""
        # Given
        small = TableCandidate(page=1, bbox=BBox(55, 55, 95, 95), detector="a")   # 40*40
        large = TableCandidate(page=1, bbox=BBox(50, 50, 100, 100), detector="b")  # 50*50
        candidates = [small, large]

        # When
        merged = merge_candidates(candidates, iou_threshold=0.3)

        # Then
        assert len(merged) == 1
        assert merged[0].bbox.area == large.bbox.area
```

### 8.5 EnsembleDetector 테스트

```python
class TestEnsembleDetector:
    """EnsembleDetector 테스트"""

    def test_requires_at_least_one_detector(self):
        """최소 하나의 탐지기가 필요"""
        # When / Then
        with pytest.raises(ValueError):
            EnsembleDetector(detectors=[])

    def test_detect_all_tables_returns_candidates(self):
        """detect_all_tables가 TableCandidate 리스트 반환"""
        # Given
        mock_detector = MockDetector()
        ensemble = EnsembleDetector([mock_detector])

        # When
        result = ensemble.detect_all_tables("sample.pdf")

        # Then
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, TableCandidate)

    def test_detect_financial_tables_returns_classified(self):
        """detect_financial_tables가 FinancialTable 리스트 반환"""
        # Given
        mock_detector = MockDetector()
        ensemble = EnsembleDetector([mock_detector])

        # When
        result = ensemble.detect_financial_tables("sample.pdf")

        # Then
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, FinancialTable)
```

---

## 9. 구현 파일

- **위치**:
  - `src/fin_stat_table_detector/utils/union_find.py`: UnionFind
  - `src/fin_stat_table_detector/utils/spatial_index.py`: SpatialIndex
  - `src/fin_stat_table_detector/ensemble.py`: EnsembleDetector, merge_candidates, calculate_iou
- **의존성**: intervaltree
