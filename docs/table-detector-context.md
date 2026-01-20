# Table Detector 프로젝트 컨텍스트

## 프로젝트 개요

**목표**: 증권사 PDF 리포트에서 **재무제표 테이블의 위치(page, bbox)**를 반환하는 모듈 구현

**배경**: 
- 최종 목표는 소형 LLM 기반 재무제표 QA 시스템 구축
- 이 모듈은 PDF에서 재무제표 영역을 탐지하는 첫 번째 단계
- pdfplumber 단독 사용 시 선 없는 표 탐지 불가 → 다중 탐지기 앙상블로 recall 향상

---

## 핵심 설계

### 1. 다중 탐지기 앙상블

단일 라이브러리의 한계를 보완하기 위해 여러 탐지기를 조합합니다.

| 탐지기 | 강점 | 약점 |
|--------|------|------|
| pdfplumber | 선 기반 표 정확도 높음, 가벼움 | 선 없는 표 탐지 불가 |
| camelot (lattice) | 격자형 표 정확 | 설치 의존성 복잡 (ghostscript) |
| camelot (stream) | 선 없는 표 탐지 가능 | false positive 많음 |
| **docling** | ML 기반 레이아웃 분석, 가장 정확 | 무거움 (모델 다운로드 필요), 느림 |

### Docling 소개

[Docling](https://docling-project.github.io/docling/)은 IBM Research에서 개발한 AI 기반 문서 파싱 도구입니다.

**장점**:
- ML 레이아웃 모델(YOLO/DETR 계열)로 선 없는 표도 탐지
- 테이블 구조 인식(Table Structure Recognition)까지 내장
- pandas DataFrame으로 직접 export 가능
- 내부적으로 Union-Find + Spatial Index로 중복 bbox 정리

**단점**:
- 첫 실행 시 모델 다운로드 (~2.5분)
- 처리 속도가 rule-based 대비 느림
- GPU 없으면 대량 처리 시 병목

**사용 예시**:
```python
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert("report.pdf")

# 테이블 순회
for table in result.document.tables:
    df = table.export_to_dataframe()
    print(df.to_markdown())
    
    # bbox 정보 접근
    bbox = table.prov[0].bbox  # (x0, y0, x1, y1)
    page = table.prov[0].page_no
```

**권장 사용 전략**:
```
1차: pdfplumber + camelot (빠름, rule-based)
    ↓
2차: 1차에서 재무제표 키워드 없으면 docling으로 재시도 (ML 기반)
    ↓
최종: Union-Find로 모든 결과 병합
```

### 2. 재무제표 분류 로직

모든 표가 아닌 **재무제표 테이블만** 필터링합니다.

**분류 기준**:
1. 키워드 매칭 (카테고리별 가중치)
2. 숫자 밀도 (20% 이상)
3. 시계열 컬럼 존재 여부 (2024, 1Q25 등)
4. 표 크기 유효성

---

## 재무제표 키워드 사전

```python
FINANCIAL_STATEMENT_PATTERNS = {
    # 손익계산서 (Income Statement)
    "income_statement": {
        "keywords": [
            "매출액", "매출원가", "매출총이익", "영업이익", "영업외손익",
            "세전이익", "법인세", "당기순이익", "지배주주순이익", "순이익"
        ],
        "weight": 1.0,
        "min_matches": 2
    },
    # 재무상태표 (Balance Sheet)
    "balance_sheet": {
        "keywords": [
            "자산총계", "부채총계", "자본총계", "유동자산", "비유동자산",
            "유동부채", "비유동부채", "이익잉여금", "자본금"
        ],
        "weight": 1.0,
        "min_matches": 2
    },
    # 현금흐름표 (Cash Flow)
    "cash_flow": {
        "keywords": [
            "영업활동", "투자활동", "재무활동", "현금흐름", "현금증감",
            "FCF", "CAPEX"
        ],
        "weight": 1.0,
        "min_matches": 2
    },
    # 투자지표 (Valuation Metrics)
    "valuation": {
        "keywords": [
            "EPS", "BPS", "PER", "PBR", "ROE", "ROA", "EBITDA",
            "EV/EBITDA", "배당수익률", "DPS"
        ],
        "weight": 0.8,  # 단독으로는 재무제표가 아닐 수 있음
        "min_matches": 3
    },
    # 실적 추이 (Performance Trend) - 보조 지표
    "performance": {
        "keywords": [
            "YoY", "QoQ", "전년비", "성장률", "증감률", "전분기비"
        ],
        "weight": 0.5,
        "min_matches": 2
    }
}
```

---

## 시계열 패턴 (연도/분기 컬럼 탐지)

```python
TEMPORAL_PATTERNS = [
    r'20\d{2}[EFef]?',        # 2024, 2025E, 2025F, 2025e
    r'[1-4][Qq]\d{2}',        # 1Q24, 3Q25, 1q24
    r'\d{1,2}[분반]기',        # 1분기, 상반기
    r'FY\d{2,4}',             # FY24, FY2024
    r'\d{4}년',               # 2024년
]
```

---

## 데이터 모델

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class BBox:
    """좌표 (PDF 좌표계: 좌상단 기준)"""
    x0: float
    y0: float
    x1: float
    y1: float
    
    @property
    def width(self) -> float:
        return self.x1 - self.x0
    
    @property
    def height(self) -> float:
        return self.y1 - self.y0
    
    @property
    def area(self) -> float:
        return self.width * self.height

@dataclass
class TableCandidate:
    """탐지된 표 후보"""
    page: int
    bbox: BBox
    detector: str  # "pdfplumber", "camelot_lattice", "camelot_stream"
    row_count: Optional[int] = None
    col_count: Optional[int] = None
    text_content: Optional[str] = None

@dataclass
class FinancialTable:
    """재무제표로 분류된 표"""
    page: int
    bbox: BBox
    category: str  # "income_statement", "balance_sheet", etc.
    confidence: float  # 0.0 ~ 1.0
    matched_keywords: list[str]
    detector_source: str
```

---

## 모듈 구조

```
projects/table-detector/
├── pyproject.toml
├── README.md
├── src/
│   └── table_detector/
│       ├── __init__.py
│       ├── models.py              # BBox, TableCandidate, FinancialTable
│       ├── detectors/
│       │   ├── __init__.py
│       │   ├── base.py            # AbstractDetector 인터페이스
│       │   ├── pdfplumber_det.py  # PdfplumberDetector
│       │   ├── camelot_det.py     # CamelotDetector (lattice + stream)
│       │   └── docling_det.py     # DoclingDetector (ML 기반)
│       ├── classifiers/
│       │   ├── __init__.py
│       │   └── financial.py       # FinancialTableClassifier
│       ├── utils/
│       │   ├── __init__.py
│       │   ├── union_find.py      # UnionFind 자료구조
│       │   └── spatial_index.py   # SpatialIndex (Interval Tree 기반)
│       └── ensemble.py            # EnsembleDetector (통합 + 중복 제거)
├── tests/
│   ├── __init__.py
│   ├── test_detectors.py
│   ├── test_classifier.py
│   ├── test_union_find.py
│   ├── test_spatial_index.py
│   └── test_ensemble.py
└── docs/
    └── TECH_SPEC_table_detector.md
```

---

## 핵심 인터페이스

### AbstractDetector

```python
from abc import ABC, abstractmethod

class AbstractDetector(ABC):
    """표 탐지기 추상 인터페이스"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """탐지기 이름"""
        pass
    
    @abstractmethod
    def detect(self, pdf_path: str, pages: list[int] | None = None) -> list[TableCandidate]:
        """
        PDF에서 표 후보 탐지
        
        Args:
            pdf_path: PDF 파일 경로
            pages: 탐지할 페이지 번호 리스트 (1-indexed). None이면 전체.
        
        Returns:
            탐지된 TableCandidate 리스트
        """
        pass
```

### FinancialTableClassifier

```python
class FinancialTableClassifier:
    """재무제표 테이블 분류기"""
    
    def classify(self, candidate: TableCandidate) -> FinancialTable | None:
        """
        표 후보가 재무제표인지 분류
        
        Returns:
            재무제표이면 FinancialTable, 아니면 None
        """
        pass
    
    def _extract_text_from_bbox(self, pdf_path: str, page: int, bbox: BBox) -> str:
        """bbox 영역의 텍스트 추출"""
        pass
    
    def _calculate_keyword_score(self, text: str) -> tuple[str, float, list[str]]:
        """키워드 매칭 점수 계산"""
        pass
    
    def _check_numeric_density(self, text: str) -> bool:
        """숫자 밀도 체크 (20% 이상)"""
        pass
    
    def _check_temporal_columns(self, text: str) -> bool:
        """시계열 컬럼 존재 여부"""
        pass
```

### EnsembleDetector

```python
class EnsembleDetector:
    """다중 탐지기 앙상블"""
    
    def __init__(self, detectors: list[AbstractDetector]):
        self.detectors = detectors
        self.classifier = FinancialTableClassifier()
    
    def detect_financial_tables(
        self, 
        pdf_path: str, 
        pages: list[int] | None = None
    ) -> list[FinancialTable]:
        """
        PDF에서 재무제표 테이블 탐지
        
        1. 모든 탐지기로 표 후보 수집
        2. 중복 제거 (IoU 기반)
        3. 재무제표 분류
        4. 결과 반환
        """
        pass
    
    def _merge_candidates(self, candidates: list[TableCandidate]) -> list[TableCandidate]:
        """IoU 기반 중복 제거"""
        pass
    
    def _calculate_iou(self, bbox1: BBox, bbox2: BBox) -> float:
        """Intersection over Union 계산"""
        pass
```

---

## 사용 예시

### 기본 사용 (Rule-based만)

```python
from table_detector import EnsembleDetector, PdfplumberDetector, CamelotDetector

# 탐지기 초기화 (빠름)
detector = EnsembleDetector([
    PdfplumberDetector(),
    CamelotDetector(flavor="lattice"),
    CamelotDetector(flavor="stream"),
])

# 재무제표 탐지
results = detector.detect_financial_tables("report.pdf")

for table in results:
    print(f"Page {table.page}: {table.category}")
    print(f"  위치: ({table.bbox.x0}, {table.bbox.y0}) - ({table.bbox.x1}, {table.bbox.y1})")
    print(f"  신뢰도: {table.confidence:.2f}")
    print(f"  매칭 키워드: {table.matched_keywords}")
```

### ML 기반 포함 (Docling)

```python
from table_detector import EnsembleDetector, PdfplumberDetector, DoclingDetector

# Docling 포함 (더 정확하지만 느림)
detector = EnsembleDetector([
    PdfplumberDetector(),
    DoclingDetector(),  # ML 기반 - 선 없는 표도 탐지
])

results = detector.detect_financial_tables("report.pdf")
```

### Fallback 전략 (권장)

```python
from table_detector import (
    EnsembleDetector, 
    PdfplumberDetector, 
    CamelotDetector,
    DoclingDetector,
    FinancialTableClassifier
)

def detect_with_fallback(pdf_path: str) -> list[FinancialTable]:
    """
    1차: Rule-based (빠름)
    2차: 재무제표 못 찾으면 Docling으로 재시도 (정확함)
    """
    # 1차 시도: Rule-based
    fast_detector = EnsembleDetector([
        PdfplumberDetector(),
        CamelotDetector(flavor="lattice"),
    ])
    results = fast_detector.detect_financial_tables(pdf_path)
    
    if results:
        return results
    
    # 2차 시도: ML 기반 (Docling)
    print(f"Rule-based 탐지 실패, Docling으로 재시도...")
    ml_detector = EnsembleDetector([DoclingDetector()])
    return ml_detector.detect_financial_tables(pdf_path)
```

---

## DoclingDetector 구현

```python
# src/table_detector/detectors/docling_det.py

from typing import Optional
from ..models import BBox, TableCandidate
from .base import AbstractDetector

class DoclingDetector(AbstractDetector):
    """Docling(IBM) ML 기반 테이블 탐지기"""
    
    def __init__(self):
        self._converter = None  # lazy loading
    
    @property
    def name(self) -> str:
        return "docling"
    
    def _get_converter(self):
        """Lazy loading - 첫 사용 시에만 모델 로드"""
        if self._converter is None:
            try:
                from docling.document_converter import DocumentConverter
                self._converter = DocumentConverter()
            except ImportError:
                raise ImportError(
                    "docling이 설치되지 않았습니다. "
                    "`uv sync --extra ml` 또는 `pip install docling`으로 설치하세요."
                )
        return self._converter
    
    def detect(
        self, 
        pdf_path: str, 
        pages: Optional[list[int]] = None
    ) -> list[TableCandidate]:
        """
        Docling으로 테이블 탐지
        
        Note: Docling은 전체 문서를 처리하므로 pages 필터는 후처리로 적용
        """
        converter = self._get_converter()
        result = converter.convert(pdf_path)
        
        candidates = []
        
        for table in result.document.tables:
            # bbox와 페이지 정보 추출
            if not table.prov:
                continue
                
            prov = table.prov[0]
            page_no = prov.page_no  # 1-indexed
            
            # pages 필터 적용
            if pages is not None and page_no not in pages:
                continue
            
            # bbox 추출 (docling은 (l, t, r, b) 형식)
            bbox_data = prov.bbox
            bbox = BBox(
                x0=bbox_data.l,
                y0=bbox_data.t,
                x1=bbox_data.r,
                y1=bbox_data.b
            )
            
            # DataFrame으로 텍스트 추출
            try:
                df = table.export_to_dataframe()
                text_content = df.to_string()
                row_count = len(df)
                col_count = len(df.columns)
            except Exception:
                text_content = None
                row_count = None
                col_count = None
            
            candidates.append(TableCandidate(
                page=page_no,
                bbox=bbox,
                detector=self.name,
                row_count=row_count,
                col_count=col_count,
                text_content=text_content
            ))
        
        return candidates
```

---

## 분류 로직 상세

### 1. 키워드 매칭 점수 계산

```python
def _calculate_keyword_score(self, text: str) -> tuple[str | None, float, list[str]]:
    """
    Returns: (best_category, confidence, matched_keywords)
    """
    scores = {}
    all_matched = {}
    
    for category, config in FINANCIAL_STATEMENT_PATTERNS.items():
        matched = [kw for kw in config["keywords"] if kw in text]
        if len(matched) >= config["min_matches"]:
            scores[category] = len(matched) * config["weight"]
            all_matched[category] = matched
    
    if not scores:
        return None, 0.0, []
    
    best_category = max(scores, key=scores.get)
    # confidence: 매칭 키워드 수에 따라 0.0 ~ 1.0
    confidence = min(scores[best_category] / 6.0, 1.0)
    
    return best_category, confidence, all_matched[best_category]
```

### 2. 숫자 밀도 체크

```python
def _check_numeric_density(self, text: str, threshold: float = 0.2) -> bool:
    """
    텍스트 내 숫자 토큰 비율 계산
    재무제표는 보통 20% 이상이 숫자
    """
    import re
    tokens = text.split()
    if not tokens:
        return False
    
    numeric_pattern = r'^[\d,.\-+()%]+$'
    numeric_count = sum(1 for t in tokens if re.match(numeric_pattern, t))
    
    return (numeric_count / len(tokens)) >= threshold
```

### 3. 시계열 컬럼 체크

```python
def _check_temporal_columns(self, text: str, min_matches: int = 2) -> bool:
    """
    연도/분기 패턴이 2개 이상 있는지 확인
    """
    import re
    total_matches = 0
    
    for pattern in TEMPORAL_PATTERNS:
        matches = re.findall(pattern, text)
        total_matches += len(set(matches))  # 중복 제거
    
    return total_matches >= min_matches
```

### 4. 표 크기 유효성

```python
def _is_valid_table_size(
    self, 
    bbox: BBox, 
    page_width: float, 
    page_height: float,
    row_count: int | None,
    col_count: int | None,
    min_area_ratio: float = 0.05,
    max_area_ratio: float = 0.95
) -> bool:
    """
    표 크기가 유효한지 확인
    - 최소 3행 2열
    - 페이지의 5% ~ 95% 크기
    """
    # 행/열 수 체크
    if row_count is not None and row_count < 3:
        return False
    if col_count is not None and col_count < 2:
        return False
    
    # 면적 비율 체크
    page_area = page_width * page_height
    table_area = bbox.area
    ratio = table_area / page_area
    
    return min_area_ratio <= ratio <= max_area_ratio
```

---

## 중복 제거 (Union-Find + Spatial Index)

여러 탐지기가 같은 표를 탐지할 수 있으므로 **Union-Find** 알고리즘으로 병합합니다.

### 왜 Union-Find인가?

**전이적 중첩 문제**: A↔B 겹침, B↔C 겹침이면 A↔C가 직접 겹치지 않아도 같은 표입니다.

```
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

참고: [Docling의 Union-Find 구현](https://codepointerko.substack.com/p/docling-llm-union-find-spatial-indexing)

### IoU (Intersection over Union)

두 영역이 얼마나 겹치는지 0~1 사이 값으로 측정합니다.

```python
def calculate_iou(bbox1: BBox, bbox2: BBox) -> float:
    """두 bbox의 IoU 계산"""
    # 교집합 영역
    x0 = max(bbox1.x0, bbox2.x0)
    y0 = max(bbox1.y0, bbox2.y0)
    x1 = min(bbox1.x1, bbox2.x1)
    y1 = min(bbox1.y1, bbox2.y1)
    
    if x0 >= x1 or y0 >= y1:
        return 0.0
    
    intersection = (x1 - x0) * (y1 - y0)
    union = bbox1.area + bbox2.area - intersection
    
    return intersection / union if union > 0 else 0.0
```

**IoU 값의 의미**:
- `1.0`: 완전히 동일한 영역
- `0.5`: 절반 정도 겹침
- `0.3`: 일부 겹침 (병합 임계값으로 적합)
- `0.0`: 전혀 겹치지 않음

### Spatial Index (공간 인덱스)

모든 쌍을 비교하면 O(n²)입니다. Interval Tree로 **겹칠 가능성 있는 후보만** O(log n)에 검색합니다.

```python
from intervaltree import IntervalTree

class SpatialIndex:
    """X/Y 축 Interval Tree로 2D 영역 쿼리"""
    
    def __init__(self):
        self.x_tree = IntervalTree()
        self.y_tree = IntervalTree()
    
    def insert(self, idx: int, bbox: BBox):
        """bbox를 인덱스에 추가"""
        self.x_tree.addi(bbox.x0, bbox.x1, idx)
        self.y_tree.addi(bbox.y0, bbox.y1, idx)
    
    def query_overlapping(self, bbox: BBox) -> set[int]:
        """bbox와 겹칠 가능성 있는 후보 인덱스 반환"""
        x_candidates = {iv.data for iv in self.x_tree.overlap(bbox.x0, bbox.x1)}
        y_candidates = {iv.data for iv in self.y_tree.overlap(bbox.y0, bbox.y1)}
        return x_candidates & y_candidates  # X, Y 모두 겹쳐야 실제 겹침
```

### Union-Find 자료구조

경로 압축(Path Compression) + 랭크 기반 합집합(Union by Rank)으로 거의 O(1) 연산을 달성합니다.

```python
class UnionFind:
    """경로 압축 + 랭크 기반 Union-Find"""
    
    def __init__(self, n: int):
        self.parent = list(range(n))  # 각 노드의 부모 (초기: 자기 자신)
        self.rank = [0] * n           # 트리 깊이 추정치
    
    def find(self, x: int) -> int:
        """x가 속한 집합의 대표(루트) 찾기"""
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])  # 경로 압축
        return self.parent[x]
    
    def union(self, x: int, y: int) -> bool:
        """x와 y를 같은 집합으로 합치기"""
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
    
    def get_groups(self) -> dict[int, list[int]]:
        """모든 집합을 {대표: [멤버들]} 형태로 반환"""
        groups = defaultdict(list)
        for i in range(len(self.parent)):
            groups[self.find(i)].append(i)
        return dict(groups)
```

### 통합 병합 로직

```python
def merge_candidates(
    candidates: list[TableCandidate], 
    iou_threshold: float = 0.3
) -> list[TableCandidate]:
    """
    Union-Find + Spatial Index 기반 중복 제거
    
    1. Spatial Index로 겹칠 후보 빠르게 검색 (O(log n))
    2. IoU 계산으로 실제 겹침 확인
    3. Union-Find로 전이적 그룹화
    4. 각 그룹에서 대표 선택
    """
    if not candidates:
        return []
    
    # 페이지별 처리
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
                    continue  # 중복 비교 방지
                
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

### 시간 복잡도 비교

| 방식 | 후보 검색 | 그룹화 | 전체 |
|------|----------|--------|------|
| 단순 IoU 비교 | O(n²) | O(n) | O(n²) |
| Union-Find + Spatial Index | O(n log n) | O(n·α(n)) ≈ O(n) | **O(n log n)** |

n=100개 bbox 기준:
- 단순 방식: ~10,000번 비교
- Union-Find: ~700번 비교 (약 14배 빠름)

---

## 테스트 케이스 예시

### Union-Find 테스트

```python
# tests/test_union_find.py

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

### Spatial Index 테스트

```python
# tests/test_spatial_index.py

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

### 재무제표 분류기 테스트

```python
# tests/test_classifier.py

class TestFinancialTableClassifier:
    """재무제표 분류기 테스트"""
    
    def test_income_statement_detection(self):
        """손익계산서 키워드가 있으면 income_statement로 분류"""
        # Given
        text = "매출액 1,234 영업이익 567 당기순이익 890 2024 2025E"
        classifier = FinancialTableClassifier()
        
        # When
        category, confidence, keywords = classifier._calculate_keyword_score(text)
        
        # Then
        assert category == "income_statement"
        assert confidence > 0.5
        assert "매출액" in keywords
        assert "영업이익" in keywords
    
    def test_numeric_density_pass(self):
        """숫자 비율 20% 이상이면 통과"""
        # Given
        text = "매출액 1,234 567 890 123 456"  # 5/6 = 83% 숫자
        classifier = FinancialTableClassifier()
        
        # When
        result = classifier._check_numeric_density(text)
        
        # Then
        assert result is True
    
    def test_numeric_density_fail(self):
        """숫자 비율 20% 미만이면 실패"""
        # Given
        text = "이것은 설명 텍스트입니다 숫자가 거의 없음 123"  # 1/8 = 12%
        classifier = FinancialTableClassifier()
        
        # When
        result = classifier._check_numeric_density(text)
        
        # Then
        assert result is False
    
    def test_temporal_columns_detected(self):
        """시계열 패턴 2개 이상이면 True"""
        # Given
        text = "항목 2024 2025E 1Q25 2Q25"
        classifier = FinancialTableClassifier()
        
        # When
        result = classifier._check_temporal_columns(text)
        
        # Then
        assert result is True
```

### 통합 병합 테스트

```python
# tests/test_ensemble.py

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
            TableCandidate(page=1, bbox=BBox(70, 70, 170, 170), detector="b"),  # B (A와 겹침)
            TableCandidate(page=1, bbox=BBox(140, 140, 240, 240), detector="c"), # C (B와 겹침, A와 안겹침)
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
```

---

## 의존성

```toml
# pyproject.toml
[project]
name = "table-detector"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "pdfplumber>=0.10.0",
    "camelot-py[cv]>=0.11.0",  # OpenCV 포함
    "ghostscript",              # camelot 의존성
    "intervaltree>=3.1.0",      # Spatial Index용
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=4.0.0",
]
# Docling은 무거우므로 optional로 분리
ml = [
    "docling>=2.0.0",           # ML 기반 테이블 탐지
]
```

**설치 옵션**:
```bash
# 기본 (rule-based만)
uv sync

# ML 기반 포함
uv sync --extra ml
```

---

## 작업 체크리스트

- [ ] 프로젝트 초기화 (`uv init table-detector`)
- [ ] TECH_SPEC 문서 작성
- [ ] 데이터 모델 구현 (`models.py`)
- [ ] PdfplumberDetector 구현
- [ ] CamelotDetector 구현 (lattice + stream)
- [ ] FinancialTableClassifier 구현
- [ ] EnsembleDetector 구현 (통합 + 중복 제거)
- [ ] 단위 테스트 작성 및 통과 확인
- [ ] 샘플 PDF 5개로 통합 테스트
- [ ] README 작성

---

## 참고: 샘플 PDF 위치

기존 수집된 PDF는 `train-data-collector` 프로젝트에서 수집된 파일 사용:
- 경로: `projects/train-data-collector/data/reports/`
- 증권사: 삼성증권, 하나증권, 미래에셋, 교보증권, 대신증권 등
