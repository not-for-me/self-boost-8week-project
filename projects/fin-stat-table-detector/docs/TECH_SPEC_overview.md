# TECH_SPEC: Financial Statement Table Detector - Overview

## 1. 프로젝트 개요

### 1.1 목적

증권사 PDF 리포트에서 **재무제표 테이블의 위치(page, bbox)**를 반환하는 모듈 구현

### 1.2 배경

- 최종 목표: 소형 LLM 기반 재무제표 QA 시스템 구축
- 본 모듈의 역할: PDF에서 재무제표 영역을 탐지하는 첫 번째 단계
- 문제점: pdfplumber 단독 사용 시 선 없는 표 탐지 불가
- 해결책: 다중 탐지기 앙상블로 recall 향상

### 1.3 핵심 설계 원칙

1. **다중 탐지기 앙상블**: 단일 라이브러리의 한계를 보완
2. **재무제표 특화 분류**: 모든 표가 아닌 재무제표만 필터링
3. **효율적 중복 제거**: Union-Find + Spatial Index로 O(n log n) 병합

---

## 2. 시스템 아키텍처

### 2.1 모듈 구조

```
projects/fin-stat-table-detector/
├── pyproject.toml
├── README.md
├── docs/
│   ├── TECH_SPEC_overview.md      # 본 문서
│   ├── TECH_SPEC_models.md        # 데이터 모델 스펙
│   ├── TECH_SPEC_detectors.md     # 탐지기 스펙
│   ├── TECH_SPEC_classifier.md    # 분류기 스펙
│   └── TECH_SPEC_ensemble.md      # 앙상블 및 병합 스펙
├── src/
│   └── fin_stat_table_detector/
│       ├── __init__.py
│       ├── models.py              # BBox, TableCandidate, FinancialTable
│       ├── detectors/
│       │   ├── __init__.py
│       │   ├── base.py            # AbstractDetector 인터페이스
│       │   ├── pdfplumber_det.py  # PdfplumberDetector
│       │   └── camelot_det.py     # CamelotDetector (lattice + stream)
│       ├── classifiers/
│       │   ├── __init__.py
│       │   └── financial.py       # FinancialTableClassifier
│       ├── utils/
│       │   ├── __init__.py
│       │   ├── union_find.py      # UnionFind 자료구조
│       │   └── spatial_index.py   # SpatialIndex (Interval Tree 기반)
│       └── ensemble.py            # EnsembleDetector (통합 + 중복 제거)
└── tests/
    ├── __init__.py
    ├── test_models.py
    ├── test_detectors.py
    ├── test_classifier.py
    ├── test_union_find.py
    ├── test_spatial_index.py
    └── test_ensemble.py
```

### 2.2 데이터 흐름

```
┌─────────────┐
│   PDF 파일   │
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────────────┐
│           EnsembleDetector               │
│  ┌─────────────────────────────────────┐ │
│  │         1. 다중 탐지기 실행          │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────┐ │ │
│  │  │pdfplumber│ │ camelot  │ │camelot│ │ │
│  │  │          │ │ lattice  │ │stream │ │ │
│  │  └────┬─────┘ └────┬─────┘ └───┬──┘ │ │
│  │       │            │           │    │ │
│  │       └────────────┼───────────┘    │ │
│  │                    ▼                │ │
│  │         TableCandidate[]            │ │
│  └─────────────────────────────────────┘ │
│  ┌─────────────────────────────────────┐ │
│  │      2. 중복 제거 (IoU 기반)         │ │
│  │  Union-Find + Spatial Index         │ │
│  └─────────────────────────────────────┘ │
│  ┌─────────────────────────────────────┐ │
│  │   3. 재무제표 분류                   │ │
│  │  FinancialTableClassifier           │ │
│  └─────────────────────────────────────┘ │
└──────────────────────┬───────────────────┘
                       │
                       ▼
              ┌────────────────┐
              │ FinancialTable[] │
              │ (page, bbox,    │
              │  category,      │
              │  confidence)    │
              └────────────────┘
```

---

## 3. 탐지기 비교

| 탐지기 | 강점 | 약점 |
|--------|------|------|
| pdfplumber | 선 기반 표 정확도 높음 | 선 없는 표 탐지 불가 |
| camelot (lattice) | 격자형 표 정확 | 설치 의존성 복잡 |
| camelot (stream) | 선 없는 표 탐지 가능 | false positive 많음 |

**앙상블 전략**: 각 탐지기의 결과를 수집하고, IoU 기반으로 중복을 제거하여 recall을 극대화

---

## 4. 의존성

```toml
[project]
name = "fin-stat-table-detector"
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
```

---

## 5. 사용 예시

```python
from fin_stat_table_detector import EnsembleDetector, PdfplumberDetector, CamelotDetector

# 탐지기 초기화
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

---

## 6. 구현 순서

1. **Phase 1**: 데이터 모델 구현 (`models.py`)
2. **Phase 2**: 유틸리티 구현 (`union_find.py`, `spatial_index.py`)
3. **Phase 3**: PdfplumberDetector 구현
4. **Phase 4**: CamelotDetector 구현 (lattice + stream)
5. **Phase 5**: FinancialTableClassifier 구현
6. **Phase 6**: EnsembleDetector 구현 (통합 + 중복 제거)
7. **Phase 7**: 통합 테스트 및 샘플 PDF 검증

---

## 7. 테스트 데이터

기존 수집된 PDF는 `train-data-collector` 프로젝트에서 수집된 파일 사용:
- 경로: `projects/train-data-collector/data/reports/`
- 증권사: 삼성증권, 하나증권, 미래에셋, 교보증권, 대신증권 등
